"""
Feature Extraction Module

Extracts encrypted-traffic-safe features from network flows.
NO PAYLOAD INSPECTION - metadata only.

Complies with SRS Section 3.3: Feature Extraction Module
"""

import math
import statistics
from dataclasses import dataclass
from typing import List, Optional

from .flow import Flow


@dataclass
class FlowFeatures:
    """
    Encrypted-traffic-safe features extracted from a network flow

    All features are derived from observable metadata without payload inspection.
    """

    flow_id: str

    # Basic flow characteristics
    duration: float
    total_packets: int
    total_bytes: int
    protocol: str

    # Rate metrics
    packet_rate: float  # packets per second
    byte_rate: float  # bytes per second

    # Directionality
    fwd_packets: int
    bwd_packets: int
    fwd_bytes: int
    bwd_bytes: int
    fwd_bwd_packet_ratio: float
    fwd_bwd_byte_ratio: float

    # Packet size statistics (forward)
    fwd_packet_size_mean: float
    fwd_packet_size_std: float
    fwd_packet_size_min: int
    fwd_packet_size_max: int

    # Packet size statistics (backward)
    bwd_packet_size_mean: float
    bwd_packet_size_std: float
    bwd_packet_size_min: int
    bwd_packet_size_max: int

    # Inter-arrival time statistics (forward)
    fwd_iat_mean: float
    fwd_iat_std: float
    fwd_iat_min: float
    fwd_iat_max: float

    # Inter-arrival time statistics (backward)
    bwd_iat_mean: float
    bwd_iat_std: float
    bwd_iat_min: float
    bwd_iat_max: float

    # Burst behavior
    fwd_burst_count: int  # Number of packet bursts
    bwd_burst_count: int
    max_fwd_burst_size: int  # Largest burst
    max_bwd_burst_size: int

    # Idle behavior
    idle_time_mean: float
    idle_time_std: float
    idle_time_max: float

    # TCP-specific features (if applicable)
    tcp_flags_syn_count: int
    tcp_flags_fin_count: int
    tcp_flags_rst_count: int

    # Connection characteristics
    is_bidirectional: bool
    is_long_lived: bool  # duration > 60 seconds
    is_high_throughput: bool  # byte_rate > 1MB/s

    def to_dict(self) -> dict:
        """Convert features to dictionary"""
        return {
            "flow_id": self.flow_id,
            "duration": self.duration,
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "protocol": self.protocol,
            "packet_rate": self.packet_rate,
            "byte_rate": self.byte_rate,
            "fwd_packets": self.fwd_packets,
            "bwd_packets": self.bwd_packets,
            "fwd_bytes": self.fwd_bytes,
            "bwd_bytes": self.bwd_bytes,
            "fwd_bwd_packet_ratio": self.fwd_bwd_packet_ratio,
            "fwd_bwd_byte_ratio": self.fwd_bwd_byte_ratio,
            "fwd_packet_size_mean": self.fwd_packet_size_mean,
            "fwd_packet_size_std": self.fwd_packet_size_std,
            "fwd_packet_size_min": self.fwd_packet_size_min,
            "fwd_packet_size_max": self.fwd_packet_size_max,
            "bwd_packet_size_mean": self.bwd_packet_size_mean,
            "bwd_packet_size_std": self.bwd_packet_size_std,
            "bwd_packet_size_min": self.bwd_packet_size_min,
            "bwd_packet_size_max": self.bwd_packet_size_max,
            "fwd_iat_mean": self.fwd_iat_mean,
            "fwd_iat_std": self.fwd_iat_std,
            "fwd_iat_min": self.fwd_iat_min,
            "fwd_iat_max": self.fwd_iat_max,
            "bwd_iat_mean": self.bwd_iat_mean,
            "bwd_iat_std": self.bwd_iat_std,
            "bwd_iat_min": self.bwd_iat_min,
            "bwd_iat_max": self.bwd_iat_max,
            "fwd_burst_count": self.fwd_burst_count,
            "bwd_burst_count": self.bwd_burst_count,
            "max_fwd_burst_size": self.max_fwd_burst_size,
            "max_bwd_burst_size": self.max_bwd_burst_size,
            "idle_time_mean": self.idle_time_mean,
            "idle_time_std": self.idle_time_std,
            "idle_time_max": self.idle_time_max,
            "tcp_flags_syn_count": self.tcp_flags_syn_count,
            "tcp_flags_fin_count": self.tcp_flags_fin_count,
            "tcp_flags_rst_count": self.tcp_flags_rst_count,
            "is_bidirectional": self.is_bidirectional,
            "is_long_lived": self.is_long_lived,
            "is_high_throughput": self.is_high_throughput,
        }


class FeatureExtractor:
    """
    Extracts features from network flows

    All features are metadata-based and safe for encrypted traffic analysis.
    """

    def __init__(
        self,
        burst_threshold: float = 0.01,  # 10ms between packets = burst
        idle_threshold: float = 1.0,  # 1 second = idle period
        long_lived_threshold: float = 60.0,  # 60 seconds
        high_throughput_threshold: float = 1_000_000,  # 1 MB/s
    ):
        self.burst_threshold = burst_threshold
        self.idle_threshold = idle_threshold
        self.long_lived_threshold = long_lived_threshold
        self.high_throughput_threshold = high_throughput_threshold

    def extract(self, flow: Flow) -> FlowFeatures:
        """Extract features from a flow"""

        # Basic statistics
        duration = flow.duration if flow.duration > 0 else 0.001  # Avoid division by zero
        total_packets = flow.total_packets
        total_bytes = flow.total_bytes
        packet_rate = flow.packet_rate
        byte_rate = flow.byte_rate

        # Directionality
        fwd_bwd_packet_ratio = self._safe_ratio(flow.fwd_packets, flow.bwd_packets)
        fwd_bwd_byte_ratio = self._safe_ratio(flow.fwd_bytes, flow.bwd_bytes)

        # Packet size statistics
        fwd_size_stats = self._compute_statistics(flow.fwd_packet_sizes)
        bwd_size_stats = self._compute_statistics(flow.bwd_packet_sizes)

        # Inter-arrival time statistics
        fwd_iat_stats = self._compute_statistics(flow.fwd_iat)
        bwd_iat_stats = self._compute_statistics(flow.bwd_iat)

        # Burst detection
        fwd_bursts = self._detect_bursts(flow.fwd_iat)
        bwd_bursts = self._detect_bursts(flow.bwd_iat)

        # Idle time analysis
        all_iat = flow.fwd_iat + flow.bwd_iat
        idle_times = [iat for iat in all_iat if iat >= self.idle_threshold]
        idle_stats = self._compute_statistics(idle_times) if idle_times else {"mean": 0.0, "std": 0.0, "max": 0.0}

        # Connection characteristics
        is_bidirectional = flow.bwd_packets > 0
        is_long_lived = duration >= self.long_lived_threshold
        is_high_throughput = byte_rate >= self.high_throughput_threshold

        # TCP flags
        tcp_syn = flow.fwd_syn + flow.bwd_syn
        tcp_fin = flow.fwd_fin + flow.bwd_fin
        tcp_rst = flow.fwd_rst + flow.bwd_rst

        return FlowFeatures(
            flow_id=flow.flow_id,
            duration=duration,
            total_packets=total_packets,
            total_bytes=total_bytes,
            protocol=flow.protocol,
            packet_rate=packet_rate,
            byte_rate=byte_rate,
            fwd_packets=flow.fwd_packets,
            bwd_packets=flow.bwd_packets,
            fwd_bytes=flow.fwd_bytes,
            bwd_bytes=flow.bwd_bytes,
            fwd_bwd_packet_ratio=fwd_bwd_packet_ratio,
            fwd_bwd_byte_ratio=fwd_bwd_byte_ratio,
            fwd_packet_size_mean=fwd_size_stats["mean"],
            fwd_packet_size_std=fwd_size_stats["std"],
            fwd_packet_size_min=int(fwd_size_stats["min"]),
            fwd_packet_size_max=int(fwd_size_stats["max"]),
            bwd_packet_size_mean=bwd_size_stats["mean"],
            bwd_packet_size_std=bwd_size_stats["std"],
            bwd_packet_size_min=int(bwd_size_stats["min"]),
            bwd_packet_size_max=int(bwd_size_stats["max"]),
            fwd_iat_mean=fwd_iat_stats["mean"],
            fwd_iat_std=fwd_iat_stats["std"],
            fwd_iat_min=fwd_iat_stats["min"],
            fwd_iat_max=fwd_iat_stats["max"],
            bwd_iat_mean=bwd_iat_stats["mean"],
            bwd_iat_std=bwd_iat_stats["std"],
            bwd_iat_min=bwd_iat_stats["min"],
            bwd_iat_max=bwd_iat_stats["max"],
            fwd_burst_count=fwd_bursts["count"],
            bwd_burst_count=bwd_bursts["count"],
            max_fwd_burst_size=fwd_bursts["max_size"],
            max_bwd_burst_size=bwd_bursts["max_size"],
            idle_time_mean=idle_stats["mean"],
            idle_time_std=idle_stats["std"],
            idle_time_max=idle_stats["max"],
            tcp_flags_syn_count=tcp_syn,
            tcp_flags_fin_count=tcp_fin,
            tcp_flags_rst_count=tcp_rst,
            is_bidirectional=is_bidirectional,
            is_long_lived=is_long_lived,
            is_high_throughput=is_high_throughput,
        )

    def _safe_ratio(self, numerator: float, denominator: float) -> float:
        """Safely compute ratio, handling division by zero"""
        if denominator == 0:
            return float("inf") if numerator > 0 else 0.0
        return numerator / denominator

    def _compute_statistics(self, values: List[float]) -> dict:
        """Compute mean, std, min, max of values"""
        if not values:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0
        min_val = min(values)
        max_val = max(values)

        return {"mean": mean, "std": std, "min": min_val, "max": max_val}

    def _detect_bursts(self, iat_values: List[float]) -> dict:
        """
        Detect packet bursts based on inter-arrival times

        A burst is a sequence of packets with IAT < burst_threshold
        """
        if not iat_values:
            return {"count": 0, "max_size": 0}

        burst_count = 0
        max_burst_size = 0
        current_burst_size = 1  # Start with 1 packet

        for iat in iat_values:
            if iat < self.burst_threshold:
                current_burst_size += 1
            else:
                if current_burst_size > 1:
                    burst_count += 1
                    max_burst_size = max(max_burst_size, current_burst_size)
                current_burst_size = 1

        # Check last burst
        if current_burst_size > 1:
            burst_count += 1
            max_burst_size = max(max_burst_size, current_burst_size)

        return {"count": burst_count, "max_size": max_burst_size}


def extract_features_batch(flows: List[Flow]) -> List[FlowFeatures]:
    """
    Extract features from multiple flows

    Args:
        flows: List of Flow objects

    Returns:
        List of FlowFeatures
    """
    extractor = FeatureExtractor()
    return [extractor.extract(flow) for flow in flows]
