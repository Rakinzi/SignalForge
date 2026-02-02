"""
Flow Construction Engine

Aggregates packets into bidirectional network flows using 5-tuple identification.
Maintains flow state, computes flow statistics, and handles flow timeout/cleanup.

Complies with SRS Section 3.2: Flow Construction Module
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterator, List, Optional, Tuple

from .capture import PacketMetadata


@dataclass
class Flow:
    """
    Bidirectional network flow

    Identified by 5-tuple: (src_ip, dst_ip, src_port, dst_port, protocol)
    Tracks both forward (initiator -> responder) and backward direction.
    """

    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str

    start_time: float
    end_time: float

    # Packet counts
    fwd_packets: int = 0
    bwd_packets: int = 0

    # Byte counts
    fwd_bytes: int = 0
    bwd_bytes: int = 0

    # Packet sizes (for statistics)
    fwd_packet_sizes: List[int] = field(default_factory=list)
    bwd_packet_sizes: List[int] = field(default_factory=list)

    # Inter-arrival times (for statistics)
    fwd_iat: List[float] = field(default_factory=list)
    bwd_iat: List[float] = field(default_factory=list)

    # TCP-specific
    fwd_syn: int = 0
    fwd_fin: int = 0
    fwd_rst: int = 0
    bwd_syn: int = 0
    bwd_fin: int = 0
    bwd_rst: int = 0

    # Flow state
    last_packet_time: float = 0.0
    is_terminated: bool = False

    @property
    def duration(self) -> float:
        """Flow duration in seconds"""
        return self.end_time - self.start_time

    @property
    def total_packets(self) -> int:
        """Total packets in both directions"""
        return self.fwd_packets + self.bwd_packets

    @property
    def total_bytes(self) -> int:
        """Total bytes in both directions"""
        return self.fwd_bytes + self.bwd_bytes

    @property
    def packet_rate(self) -> float:
        """Packets per second"""
        if self.duration > 0:
            return self.total_packets / self.duration
        return 0.0

    @property
    def byte_rate(self) -> float:
        """Bytes per second"""
        if self.duration > 0:
            return self.total_bytes / self.duration
        return 0.0

    @property
    def fwd_bwd_ratio(self) -> float:
        """Ratio of forward to backward packets"""
        if self.bwd_packets > 0:
            return self.fwd_packets / self.bwd_packets
        return float("inf") if self.fwd_packets > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert flow to dictionary for serialization"""
        return {
            "flow_id": self.flow_id,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "start_time": datetime.fromtimestamp(self.start_time, tz=timezone.utc).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time, tz=timezone.utc).isoformat(),
            "duration": self.duration,
            "fwd_packets": self.fwd_packets,
            "bwd_packets": self.bwd_packets,
            "total_packets": self.total_packets,
            "fwd_bytes": self.fwd_bytes,
            "bwd_bytes": self.bwd_bytes,
            "total_bytes": self.total_bytes,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "fwd_bwd_ratio": self.fwd_bwd_ratio,
            "fwd_syn": self.fwd_syn,
            "fwd_fin": self.fwd_fin,
            "fwd_rst": self.fwd_rst,
            "bwd_syn": self.bwd_syn,
            "bwd_fin": self.bwd_fin,
            "bwd_rst": self.bwd_rst,
            "is_terminated": self.is_terminated,
        }


class FlowConstructor:
    """
    Constructs bidirectional flows from packet stream

    Maintains active flows, handles timeouts, and produces complete flow records.
    """

    def __init__(
        self,
        flow_timeout: float = 120.0,  # 2 minutes
        activity_timeout: float = 15.0,  # 15 seconds
        max_flows: int = 100000,
    ):
        """
        Initialize flow constructor

        Args:
            flow_timeout: Maximum flow duration before forced termination (seconds)
            activity_timeout: Timeout for inactive flows (seconds)
            max_flows: Maximum concurrent flows (prevents memory exhaustion)
        """
        self.flow_timeout = flow_timeout
        self.activity_timeout = activity_timeout
        self.max_flows = max_flows

        self._active_flows: Dict[str, Flow] = {}
        self._flow_count = 0

    def process_packet(self, packet: PacketMetadata) -> Optional[Flow]:
        """
        Process a packet and update flows

        Returns completed flow if packet terminates a flow, None otherwise.
        """
        # Generate flow key
        flow_key = self._get_flow_key(packet)

        # Check if flow exists
        if flow_key in self._active_flows:
            flow = self._active_flows[flow_key]
            terminated_flow = self._update_flow(flow, packet)
            if terminated_flow:
                del self._active_flows[flow_key]
                return terminated_flow
            return None
        else:
            # Check flow limit
            if len(self._active_flows) >= self.max_flows:
                # Evict oldest flow
                oldest_key = min(self._active_flows.keys(), key=lambda k: self._active_flows[k].last_packet_time)
                terminated_flow = self._active_flows[oldest_key]
                terminated_flow.is_terminated = True
                del self._active_flows[oldest_key]
                # Note: we lose this flow but prevent memory exhaustion
                # In production, this would trigger an alert

            # Create new flow
            flow = self._create_flow(packet)
            self._active_flows[flow_key] = flow
            self._flow_count += 1
            return None

    def expire_flows(self, current_time: Optional[float] = None) -> List[Flow]:
        """
        Expire inactive flows based on timeout

        Returns list of expired flows.
        """
        if current_time is None:
            current_time = time.time()

        expired = []
        to_remove = []

        for flow_key, flow in self._active_flows.items():
            # Check activity timeout
            inactive_time = current_time - flow.last_packet_time
            if inactive_time >= self.activity_timeout:
                flow.is_terminated = True
                expired.append(flow)
                to_remove.append(flow_key)
                continue

            # Check absolute timeout
            if flow.duration >= self.flow_timeout:
                flow.is_terminated = True
                expired.append(flow)
                to_remove.append(flow_key)

        # Remove expired flows
        for key in to_remove:
            del self._active_flows[key]

        return expired

    def get_all_flows(self) -> List[Flow]:
        """Get all active flows and clear state"""
        flows = list(self._active_flows.values())
        for flow in flows:
            flow.is_terminated = True
        self._active_flows.clear()
        return flows

    def _get_flow_key(self, packet: PacketMetadata) -> str:
        """
        Generate bidirectional flow key

        Normalizes 5-tuple so both directions map to same key.
        """
        # Sort IPs and ports to make bidirectional
        if packet.src_ip < packet.dst_ip:
            ip1, ip2 = packet.src_ip, packet.dst_ip
            port1, port2 = packet.src_port, packet.dst_port
        elif packet.src_ip > packet.dst_ip:
            ip1, ip2 = packet.dst_ip, packet.src_ip
            port1, port2 = packet.dst_port, packet.src_port
        else:
            # Same IP, sort by port
            if packet.src_port <= packet.dst_port:
                ip1, ip2 = packet.src_ip, packet.dst_ip
                port1, port2 = packet.src_port, packet.dst_port
            else:
                ip1, ip2 = packet.dst_ip, packet.src_ip
                port1, port2 = packet.dst_port, packet.src_port

        return f"{ip1}:{port1}-{ip2}:{port2}-{packet.protocol}"

    def _create_flow(self, packet: PacketMetadata) -> Flow:
        """Create new flow from first packet"""
        flow_id = f"flow-{self._flow_count}-{int(packet.timestamp * 1000)}"

        # Determine flow direction (first packet defines forward direction)
        flow = Flow(
            flow_id=flow_id,
            src_ip=packet.src_ip,
            dst_ip=packet.dst_ip,
            src_port=packet.src_port,
            dst_port=packet.dst_port,
            protocol=packet.protocol,
            start_time=packet.timestamp,
            end_time=packet.timestamp,
            last_packet_time=packet.timestamp,
        )

        # Add first packet
        flow.fwd_packets = 1
        flow.fwd_bytes = packet.size
        flow.fwd_packet_sizes.append(packet.size)

        # Check TCP flags
        if packet.flags:
            if "S" in packet.flags:
                flow.fwd_syn = 1
            if "F" in packet.flags:
                flow.fwd_fin = 1
            if "R" in packet.flags:
                flow.fwd_rst = 1

        return flow

    def _update_flow(self, flow: Flow, packet: PacketMetadata) -> Optional[Flow]:
        """
        Update flow with new packet

        Returns flow if terminated, None otherwise.
        """
        # Update end time
        flow.end_time = packet.timestamp

        # Determine direction
        is_forward = (packet.src_ip == flow.src_ip and packet.src_port == flow.src_port)

        # Calculate inter-arrival time
        if flow.last_packet_time > 0:
            iat = packet.timestamp - flow.last_packet_time
            if is_forward:
                flow.fwd_iat.append(iat)
            else:
                flow.bwd_iat.append(iat)

        flow.last_packet_time = packet.timestamp

        # Update statistics
        if is_forward:
            flow.fwd_packets += 1
            flow.fwd_bytes += packet.size
            flow.fwd_packet_sizes.append(packet.size)

            # TCP flags
            if packet.flags:
                if "S" in packet.flags:
                    flow.fwd_syn += 1
                if "F" in packet.flags:
                    flow.fwd_fin += 1
                if "R" in packet.flags:
                    flow.fwd_rst += 1
        else:
            flow.bwd_packets += 1
            flow.bwd_bytes += packet.size
            flow.bwd_packet_sizes.append(packet.size)

            # TCP flags
            if packet.flags:
                if "S" in packet.flags:
                    flow.bwd_syn += 1
                if "F" in packet.flags:
                    flow.bwd_fin += 1
                if "R" in packet.flags:
                    flow.bwd_rst += 1

        # Check termination conditions
        if packet.flags and ("F" in packet.flags or "R" in packet.flags):
            flow.is_terminated = True
            return flow

        return None

    @property
    def active_flow_count(self) -> int:
        """Number of currently active flows"""
        return len(self._active_flows)

    @property
    def total_flow_count(self) -> int:
        """Total flows created"""
        return self._flow_count


def construct_flows(
    packets: Iterator[PacketMetadata],
    flow_timeout: float = 120.0,
    activity_timeout: float = 15.0,
) -> Iterator[Flow]:
    """
    Convenience function to construct flows from packet iterator

    Args:
        packets: Iterator of PacketMetadata
        flow_timeout: Maximum flow duration (seconds)
        activity_timeout: Inactivity timeout (seconds)

    Yields:
        Completed Flow objects
    """
    constructor = FlowConstructor(flow_timeout=flow_timeout, activity_timeout=activity_timeout)

    last_expire_check = time.time()
    expire_check_interval = 5.0  # Check for expired flows every 5 seconds

    for packet in packets:
        # Process packet
        completed_flow = constructor.process_packet(packet)
        if completed_flow:
            yield completed_flow

        # Periodically check for expired flows
        current_time = packet.timestamp
        if current_time - last_expire_check >= expire_check_interval:
            expired_flows = constructor.expire_flows(current_time)
            for flow in expired_flows:
                yield flow
            last_expire_check = current_time

    # Yield remaining flows
    remaining_flows = constructor.get_all_flows()
    for flow in remaining_flows:
        yield flow
