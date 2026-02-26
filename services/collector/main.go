package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"log"
	"net"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/gopacket"
	"github.com/google/gopacket/layers"
	"github.com/google/gopacket/pcap"
	"github.com/redis/go-redis/v9"
)

type FlowKey struct {
	AIP   string
	BIP   string
	APort uint16
	BPort uint16
	Proto string
}

type FlowAgg struct {
	Key         FlowKey
	Start       time.Time
	LastSeen    time.Time
	FwdPackets  int
	BwdPackets  int
	FwdBytes    int
	BwdBytes    int
	FwdTcpFlags string
	BwdTcpFlags string
}

type FlowSummary struct {
	SchemaVersion string  `json:"schema_version"`
	FlowID        string  `json:"flow_id"`
	StartTime     string  `json:"start_time"`
	EndTime       string  `json:"end_time"`
	SrcIP         string  `json:"src_ip"`
	DstIP         string  `json:"dst_ip"`
	SrcPort       int     `json:"src_port"`
	DstPort       int     `json:"dst_port"`
	Protocol      string  `json:"protocol"`
	PacketCount   int     `json:"packet_count"`
	ByteCount     int     `json:"byte_count"`
	TcpFlags      string  `json:"tcp_flags"`
	Direction     string  `json:"direction"`
	DurationMs    int64   `json:"duration_ms"`
	PacketRate    float64 `json:"packet_rate"`
	FwdPackets    int     `json:"fwd_packets"`
	BwdPackets    int     `json:"bwd_packets"`
	FwdBytes      int     `json:"fwd_bytes"`
	BwdBytes      int     `json:"bwd_bytes"`
}

type EventEnvelope struct {
	SchemaVersion string      `json:"schema_version"`
	EventType     string      `json:"event_type"`
	OccurredAt    string      `json:"occurred_at"`
	Payload       interface{} `json:"payload"`
}

func main() {
	var (
		mode      = getenv("CAPTURE_MODE", "auto")
		iface     = getenv("CAPTURE_IFACE", "")
		pcapPath  = getenv("PCAP_PATH", "")
		bpf       = getenv("BPF_FILTER", "")
		idleStr   = getenv("FLOW_IDLE_TIMEOUT", "10s")
		maxStr    = getenv("FLOW_MAX_DURATION", "5m")
		flushStr  = getenv("FLUSH_INTERVAL", "2s")
		stream    = getenv("REDIS_STREAM", "flows")
		addr      = getenv("REDIS_ADDR", "redis:6379")
		bufferStr = getenv("EMIT_BUFFER", "10000")
		loopStr   = getenv("PCAP_LOOP", "1")
	)

	flag.Parse()

	idleTimeout := mustDuration(idleStr)
	maxDuration := mustDuration(maxStr)
	flushInterval := mustDuration(flushStr)
	bufferSize, _ := strconv.Atoi(bufferStr)
	if bufferSize < 100 {
		bufferSize = 100
	}
	loopCount, _ := strconv.Atoi(loopStr)
	if loopCount < 1 {
		loopCount = 1
	}

	ctx := context.Background()
	rdb := redis.NewClient(&redis.Options{Addr: addr})

	events := make(chan FlowSummary, bufferSize)
	var emitDone sync.WaitGroup
	emitDone.Add(1)
	go func() {
		defer emitDone.Done()
		emitLoop(ctx, rdb, stream, events)
	}()

	logJSON("collector_start", map[string]interface{}{
		"mode":         mode,
		"iface":        iface,
		"pcap":         pcapPath,
		"loop":         loopCount,
		"idle_timeout": idleTimeout.String(),
		"max_duration": maxDuration.String(),
		"bpf":          bpf,
	})

	if mode == "auto" || mode == "" {
		if pcapPath != "" {
			mode = "pcap"
		} else {
			mode = "live"
		}
	}

	flows := make(map[FlowKey]*FlowAgg)
	var mu sync.Mutex
	var packetTime time.Time

	// Flusher uses packet timestamps so PCAP replay works regardless of capture age.
	go func() {
		ticker := time.NewTicker(flushInterval)
		defer ticker.Stop()
		for range ticker.C {
			mu.Lock()
			now := packetTime
			if now.IsZero() {
				mu.Unlock()
				continue
			}
			for k, f := range flows {
				if now.Sub(f.LastSeen) >= idleTimeout || now.Sub(f.Start) >= maxDuration {
					summary := finalizeFlow(f)
					nonBlockingSend(events, summary)
					delete(flows, k)
				}
			}
			mu.Unlock()
		}
	}()

	if mode != "pcap" {
		if iface == "" {
			iface = defaultIface()
		}
		handle, err := pcap.OpenLive(iface, 65535, true, pcap.BlockForever)
		if err != nil {
			log.Fatal(err)
		}
		defer handle.Close()
		if bpf != "" {
			if err := handle.SetBPFFilter(bpf); err != nil {
				log.Fatal(err)
			}
		}
		readPackets(handle, flows, &mu, &packetTime)
	} else {
		if pcapPath == "" {
			log.Fatal("PCAP_PATH required for pcap mode")
		}
		for i := 0; i < loopCount; i++ {
			handle, err := pcap.OpenOffline(pcapPath)
			if err != nil {
				log.Fatal(err)
			}
			if bpf != "" {
				if err := handle.SetBPFFilter(bpf); err != nil {
					log.Fatal(err)
				}
			}
			logJSON("collector_pass", map[string]interface{}{"pass": i + 1, "of": loopCount})
			readPackets(handle, flows, &mu, &packetTime)
			handle.Close()

			// Flush all in-memory flows between passes, tagging with pass index
			// so each pass produces unique flow IDs even with identical packet timestamps.
			mu.Lock()
			for k, f := range flows {
				s := finalizeFlow(f)
				s.FlowID = strconv.Itoa(i) + "-" + s.FlowID
				events <- s
				delete(flows, k)
			}
			mu.Unlock()
		}
	}

	// Final flush then drain the emit channel before exiting.
	mu.Lock()
	remaining := len(flows)
	for k, f := range flows {
		events <- finalizeFlow(f)
		delete(flows, k)
	}
	mu.Unlock()
	logJSON("collector_done", map[string]interface{}{"final_flush": remaining})
	close(events)
	emitDone.Wait()
}

// readPackets reads all packets from handle into the shared flow table.
func readPackets(handle *pcap.Handle, flows map[FlowKey]*FlowAgg, mu *sync.Mutex, packetTime *time.Time) {
	src := gopacket.NewPacketSource(handle, handle.LinkType())
	for packet := range src.Packets() {
		netLayer := packet.NetworkLayer()
		transLayer := packet.TransportLayer()
		if netLayer == nil || transLayer == nil {
			continue
		}
		srcIP, dstIP := parseIPs(netLayer)
		if srcIP == "" || dstIP == "" {
			continue
		}
		proto := strings.ToUpper(transLayer.LayerType().String())
		srcPort, dstPort, flags := parsePortsFlags(transLayer)
		if srcPort == 0 && dstPort == 0 {
			continue
		}
		key, direction := canonicalKey(srcIP, dstIP, srcPort, dstPort, proto)
		length := len(packet.Data())
		ts := packet.Metadata().Timestamp

		mu.Lock()
		*packetTime = ts.UTC()
		flow, ok := flows[key]
		if !ok {
			flow = &FlowAgg{Key: key, Start: ts.UTC(), LastSeen: ts.UTC()}
			flows[key] = flow
		}
		flow.LastSeen = ts.UTC()
		if direction == "fwd" {
			flow.FwdPackets++
			flow.FwdBytes += length
			flow.FwdTcpFlags += flags
		} else {
			flow.BwdPackets++
			flow.BwdBytes += length
			flow.BwdTcpFlags += flags
		}
		mu.Unlock()
	}
}

func emitLoop(ctx context.Context, rdb *redis.Client, stream string, ch <-chan FlowSummary) {
	for flow := range ch {
		env := EventEnvelope{
			SchemaVersion: "1.0",
			EventType:     "FlowEnded",
			OccurredAt:    time.Now().UTC().Format(time.RFC3339Nano),
			Payload:       flow,
		}
		b, err := json.Marshal(env)
		if err != nil {
			logJSON("collector_marshal_error", map[string]interface{}{"error": err.Error()})
			continue
		}
		_, err = rdb.XAdd(ctx, &redis.XAddArgs{
			Stream: stream,
			Values: map[string]interface{}{"event": string(b)},
		}).Result()
		if err != nil {
			logJSON("collector_emit_error", map[string]interface{}{"error": err.Error()})
		}
	}
}

func finalizeFlow(f *FlowAgg) FlowSummary {
	packetCount := f.FwdPackets + f.BwdPackets
	byteCount := f.FwdBytes + f.BwdBytes
	duration := f.LastSeen.Sub(f.Start)
	if duration <= 0 {
		duration = time.Millisecond
	}
	rate := float64(packetCount) / duration.Seconds()
	return FlowSummary{
		SchemaVersion: "1.0",
		FlowID:        flowID(f),
		StartTime:     f.Start.UTC().Format(time.RFC3339Nano),
		EndTime:       f.LastSeen.UTC().Format(time.RFC3339Nano),
		SrcIP:         f.Key.AIP,
		DstIP:         f.Key.BIP,
		SrcPort:       int(f.Key.APort),
		DstPort:       int(f.Key.BPort),
		Protocol:      f.Key.Proto,
		PacketCount:   packetCount,
		ByteCount:     byteCount,
		TcpFlags:      f.FwdTcpFlags + "|" + f.BwdTcpFlags,
		Direction:     "bidirectional",
		DurationMs:    duration.Milliseconds(),
		PacketRate:    rate,
		FwdPackets:    f.FwdPackets,
		BwdPackets:    f.BwdPackets,
		FwdBytes:      f.FwdBytes,
		BwdBytes:      f.BwdBytes,
	}
}

func canonicalKey(srcIP, dstIP string, srcPort, dstPort uint16, proto string) (FlowKey, string) {
	left := net.ParseIP(srcIP)
	right := net.ParseIP(dstIP)
	if left == nil || right == nil {
		return FlowKey{AIP: srcIP, BIP: dstIP, APort: srcPort, BPort: dstPort, Proto: proto}, "fwd"
	}
	if bytesCompare(left, right) < 0 || (left.Equal(right) && srcPort <= dstPort) {
		return FlowKey{AIP: srcIP, BIP: dstIP, APort: srcPort, BPort: dstPort, Proto: proto}, "fwd"
	}
	return FlowKey{AIP: dstIP, BIP: srcIP, APort: dstPort, BPort: srcPort, Proto: proto}, "bwd"
}

func bytesCompare(a, b net.IP) int {
	return bytes.Compare(a.To16(), b.To16())
}

func parseIPs(nl gopacket.NetworkLayer) (string, string) {
	switch v := nl.(type) {
	case *layers.IPv4:
		return v.SrcIP.String(), v.DstIP.String()
	case *layers.IPv6:
		return v.SrcIP.String(), v.DstIP.String()
	default:
		return "", ""
	}
}

func parsePortsFlags(tl gopacket.TransportLayer) (uint16, uint16, string) {
	switch v := tl.(type) {
	case *layers.TCP:
		return uint16(v.SrcPort), uint16(v.DstPort), tcpFlags(v)
	case *layers.UDP:
		return uint16(v.SrcPort), uint16(v.DstPort), ""
	default:
		return 0, 0, ""
	}
}

func tcpFlags(t *layers.TCP) string {
	var flags []string
	if t.SYN {
		flags = append(flags, "S")
	}
	if t.ACK {
		flags = append(flags, "A")
	}
	if t.FIN {
		flags = append(flags, "F")
	}
	if t.RST {
		flags = append(flags, "R")
	}
	if t.PSH {
		flags = append(flags, "P")
	}
	if t.URG {
		flags = append(flags, "U")
	}
	return strings.Join(flags, "")
}

func flowID(f *FlowAgg) string {
	return strconv.FormatInt(f.Start.UnixNano(), 10) + "-" + f.Key.AIP + "-" + f.Key.BIP
}

func nonBlockingSend(ch chan<- FlowSummary, summary FlowSummary) {
	select {
	case ch <- summary:
	default:
		logJSON("collector_drop", map[string]interface{}{"flow_id": summary.FlowID})
	}
}

func defaultIface() string {
	ifaces, err := net.Interfaces()
	if err != nil {
		return ""
	}
	for _, iface := range ifaces {
		if (iface.Flags&net.FlagUp) != 0 && (iface.Flags&net.FlagLoopback) == 0 {
			return iface.Name
		}
	}
	return ""
}

func mustDuration(s string) time.Duration {
	d, err := time.ParseDuration(s)
	if err != nil {
		panic(err)
	}
	return d
}

func getenv(key, def string) string {
	v := os.Getenv(key)
	if v == "" {
		return def
	}
	return v
}

func logJSON(event string, fields map[string]interface{}) {
	fields["event"] = event
	fields["ts"] = time.Now().UTC().Format(time.RFC3339Nano)
	b, _ := json.Marshal(fields)
	log.Print(string(b))
}
