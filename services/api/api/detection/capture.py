"""
Traffic Capture Module

Implements dual-mode traffic capture:
1. PCAP file ingestion for offline analysis
2. Live network interface capture for real-time detection

Complies with SRS Section 3.1: Traffic Capture Module
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

try:
    from scapy.all import IP, TCP, UDP, PcapReader, sniff
    from scapy.layers.inet import Packet

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    Packet = object  # type: ignore


@dataclass
class PacketMetadata:
    """Metadata extracted from a captured packet"""

    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str  # "TCP" or "UDP"
    size: int
    flags: Optional[str] = None  # TCP flags if applicable
    raw_packet: Optional[object] = None  # For advanced analysis


class TrafficCapture(ABC):
    """Abstract base class for traffic capture mechanisms"""

    @abstractmethod
    def __iter__(self) -> Iterator[PacketMetadata]:
        """Iterate over captured packets"""
        pass

    @abstractmethod
    def start(self) -> None:
        """Start capturing traffic"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing traffic"""
        pass


class PCAPCapture(TrafficCapture):
    """
    PCAP file ingestion for offline analysis

    Reads packets from PCAP files captured by tcpdump, Wireshark, or similar tools.
    Supports standard PCAP and PCAP-NG formats.
    """

    def __init__(self, pcap_path: str):
        if not SCAPY_AVAILABLE:
            raise RuntimeError("scapy is required for PCAP capture. Install with: pip install scapy")

        self.pcap_path = Path(pcap_path)
        if not self.pcap_path.exists():
            raise FileNotFoundError(f"PCAP file not found: {pcap_path}")

        self._reader: Optional[PcapReader] = None
        self._packet_count = 0

    def start(self) -> None:
        """Open PCAP file for reading"""
        self._reader = PcapReader(str(self.pcap_path))
        self._packet_count = 0

    def stop(self) -> None:
        """Close PCAP file"""
        if self._reader:
            self._reader.close()
            self._reader = None

    def __iter__(self) -> Iterator[PacketMetadata]:
        """Iterate over packets in PCAP file"""
        if not self._reader:
            self.start()

        try:
            for pkt in self._reader:  # type: ignore
                metadata = self._extract_metadata(pkt)
                if metadata:
                    self._packet_count += 1
                    yield metadata
        finally:
            self.stop()

    def _extract_metadata(self, pkt: Packet) -> Optional[PacketMetadata]:
        """Extract metadata from scapy packet"""
        # Only process TCP and UDP packets
        if not (TCP in pkt or UDP in pkt):
            return None

        if IP not in pkt:
            return None

        ip_layer = pkt[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst

        if TCP in pkt:
            transport = pkt[TCP]
            protocol = "TCP"
            flags = transport.sprintf("%TCP.flags%")
        else:
            transport = pkt[UDP]
            protocol = "UDP"
            flags = None

        return PacketMetadata(
            timestamp=float(pkt.time),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=transport.sport,
            dst_port=transport.dport,
            protocol=protocol,
            size=len(pkt),
            flags=flags,
            raw_packet=pkt,
        )

    @property
    def packet_count(self) -> int:
        """Total packets processed"""
        return self._packet_count


class LiveCapture(TrafficCapture):
    """
    Live network interface capture for real-time detection

    Captures packets from a network interface in real-time.
    Requires elevated privileges (root/admin).
    """

    def __init__(
        self,
        interface: str = "eth0",
        filter_expression: str = "tcp or udp",
        packet_count: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        if not SCAPY_AVAILABLE:
            raise RuntimeError("scapy is required for live capture. Install with: pip install scapy")

        self.interface = interface
        self.filter_expression = filter_expression
        self.packet_count = packet_count
        self.timeout = timeout
        self._stop_capture = False
        self._packets_captured = 0

    def start(self) -> None:
        """Start live capture"""
        self._stop_capture = False
        self._packets_captured = 0

    def stop(self) -> None:
        """Stop live capture"""
        self._stop_capture = True

    def __iter__(self) -> Iterator[PacketMetadata]:
        """Iterate over live captured packets"""
        self.start()

        def packet_handler(pkt: Packet):
            """Process each captured packet"""
            if self._stop_capture:
                return True  # Stop sniffing

            metadata = self._extract_metadata(pkt)
            if metadata:
                self._packets_captured += 1
                return metadata
            return None

        try:
            packets = sniff(
                iface=self.interface,
                filter=self.filter_expression,
                prn=packet_handler,
                store=False,
                count=self.packet_count,
                timeout=self.timeout,
            )

            # Process captured packets
            for pkt in packets:
                metadata = self._extract_metadata(pkt)
                if metadata:
                    yield metadata

        except PermissionError as e:
            raise PermissionError(
                f"Insufficient permissions for live capture on {self.interface}. "
                "Run with sudo/administrator privileges."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Live capture failed: {e}") from e
        finally:
            self.stop()

    def _extract_metadata(self, pkt: Packet) -> Optional[PacketMetadata]:
        """Extract metadata from scapy packet"""
        if not (TCP in pkt or UDP in pkt):
            return None

        if IP not in pkt:
            return None

        ip_layer = pkt[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst

        if TCP in pkt:
            transport = pkt[TCP]
            protocol = "TCP"
            flags = transport.sprintf("%TCP.flags%")
        else:
            transport = pkt[UDP]
            protocol = "UDP"
            flags = None

        return PacketMetadata(
            timestamp=float(pkt.time) if hasattr(pkt, "time") else time.time(),
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=transport.sport,
            dst_port=transport.dport,
            protocol=protocol,
            size=len(pkt),
            flags=flags,
            raw_packet=pkt,
        )

    @property
    def packets_captured(self) -> int:
        """Total packets captured"""
        return self._packets_captured


def create_capture(source: str, **kwargs) -> TrafficCapture:
    """
    Factory function to create appropriate capture instance

    Args:
        source: Either a PCAP file path or interface name (e.g., "eth0", "wlan0")
        **kwargs: Additional arguments passed to capture constructor

    Returns:
        TrafficCapture instance

    Examples:
        >>> capture = create_capture("traffic.pcap")
        >>> capture = create_capture("eth0", filter_expression="tcp")
    """
    if Path(source).exists() and Path(source).suffix in [".pcap", ".pcapng"]:
        return PCAPCapture(source, **kwargs)
    else:
        return LiveCapture(source, **kwargs)
