"""
Dataset Ingestion Module

Support for standard research datasets:
- CICIDS2017/2018
- CTU-13
- UNSW-NB15

Handles format parsing, ground truth extraction, and mapping to internal flow format.

Complies with SRS Section 3.2 (Dataset Support)
"""

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from .capture import PacketMetadata


@dataclass
class DatasetFlow:
    """Flow record from a dataset"""

    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    timestamp: float
    duration: float
    total_packets: int
    total_bytes: int
    fwd_packets: int
    bwd_packets: int
    label: str  # Original dataset label
    is_malicious: bool  # Binary classification


class DatasetParser(ABC):
    """Abstract base class for dataset parsers"""

    @abstractmethod
    def parse(self, file_path: str) -> Iterator[DatasetFlow]:
        """Parse dataset file and yield flow records"""
        pass

    @abstractmethod
    def get_ground_truth(self, file_path: str) -> Dict[str, bool]:
        """Extract ground truth labels (flow_id -> is_malicious)"""
        pass


class CICIDSParser(DatasetParser):
    """
    Parser for CICIDS2017 and CICIDS2018 datasets

    These datasets use CSV format with extensive flow features.
    """

    # CICIDS benign labels
    BENIGN_LABELS = {"BENIGN", "Benign"}

    # Common field name variations
    FIELD_MAPPINGS = {
        "Flow ID": "flow_id",
        " Source IP": "src_ip",
        "Source IP": "src_ip",
        " Destination IP": "dst_ip",
        "Destination IP": "dst_ip",
        " Source Port": "src_port",
        "Source Port": "src_port",
        " Destination Port": "dst_port",
        "Destination Port": "dst_port",
        " Protocol": "protocol",
        "Protocol": "protocol",
        " Timestamp": "timestamp",
        "Timestamp": "timestamp",
        " Flow Duration": "duration",
        "Flow Duration": "duration",
        " Total Fwd Packets": "fwd_packets",
        "Total Fwd Packets": "fwd_packets",
        " Total Backward Packets": "bwd_packets",
        "Total Backward Packets": "bwd_packets",
        "Total Length of Fwd Packets": "fwd_bytes",
        " Total Length of Fwd Packets": "fwd_bytes",
        "Total Length of Bwd Packets": "bwd_bytes",
        " Total Length of Bwd Packets": "bwd_bytes",
        " Label": "label",
        "Label": "label",
    }

    def parse(self, file_path: str) -> Iterator[DatasetFlow]:
        """Parse CICIDS CSV file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader):
                try:
                    flow = self._parse_row(row, idx)
                    if flow:
                        yield flow
                except Exception as e:
                    # Log parsing errors but continue
                    print(f"Warning: Failed to parse row {idx}: {e}")
                    continue

    def _parse_row(self, row: Dict[str, str], idx: int) -> Optional[DatasetFlow]:
        """Parse a single CSV row into DatasetFlow"""
        # Map field names
        mapped_row = {}
        for orig_name, value in row.items():
            mapped_name = self.FIELD_MAPPINGS.get(orig_name, orig_name.strip().lower().replace(" ", "_"))
            mapped_row[mapped_name] = value.strip() if isinstance(value, str) else value

        # Extract required fields
        try:
            src_ip = mapped_row.get("src_ip", mapped_row.get("source_ip", ""))
            dst_ip = mapped_row.get("dst_ip", mapped_row.get("destination_ip", ""))
            src_port = int(mapped_row.get("src_port", mapped_row.get("source_port", 0)))
            dst_port = int(mapped_row.get("dst_port", mapped_row.get("destination_port", 0)))
            protocol = str(mapped_row.get("protocol", "TCP"))
            label = mapped_row.get("label", "Unknown")

            # Handle timestamp - CICIDS uses string timestamps
            timestamp_str = mapped_row.get("timestamp", "")
            try:
                dt = datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
                timestamp = dt.timestamp()
            except:
                timestamp = float(idx)  # Fallback to index

            # Extract flow statistics
            duration = float(mapped_row.get("duration", 0))
            fwd_packets = int(mapped_row.get("fwd_packets", 0))
            bwd_packets = int(mapped_row.get("bwd_packets", 0))
            total_packets = fwd_packets + bwd_packets

            fwd_bytes = int(mapped_row.get("fwd_bytes", 0))
            bwd_bytes = int(mapped_row.get("bwd_bytes", 0))
            total_bytes = fwd_bytes + bwd_bytes

            # Generate flow ID
            flow_id = f"cicids-{idx}-{src_ip}-{dst_ip}"

            # Determine if malicious
            is_malicious = label not in self.BENIGN_LABELS

            return DatasetFlow(
                flow_id=flow_id,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                timestamp=timestamp,
                duration=duration,
                total_packets=total_packets,
                total_bytes=total_bytes,
                fwd_packets=fwd_packets,
                bwd_packets=bwd_packets,
                label=label,
                is_malicious=is_malicious,
            )

        except Exception as e:
            return None

    def get_ground_truth(self, file_path: str) -> Dict[str, bool]:
        """Extract ground truth labels from CICIDS dataset"""
        labels = {}
        for flow in self.parse(file_path):
            labels[flow.flow_id] = flow.is_malicious
        return labels


class CTU13Parser(DatasetParser):
    """
    Parser for CTU-13 dataset

    CTU-13 uses NetFlow-based format with binetflow files.
    """

    MALICIOUS_LABELS = {"Botnet", "CC", "C&C"}

    def parse(self, file_path: str) -> Iterator[DatasetFlow]:
        """Parse CTU-13 binetflow file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader):
                try:
                    flow = self._parse_row(row, idx)
                    if flow:
                        yield flow
                except Exception as e:
                    print(f"Warning: Failed to parse row {idx}: {e}")
                    continue

    def _parse_row(self, row: Dict[str, str], idx: int) -> Optional[DatasetFlow]:
        """Parse CTU-13 row"""
        try:
            src_ip = row.get("SrcAddr", "").strip()
            dst_ip = row.get("DstAddr", "").strip()
            src_port = int(row.get("Sport", 0))
            dst_port = int(row.get("Dport", 0))
            protocol = row.get("Proto", "TCP").strip()
            label = row.get("Label", "").strip()

            # Parse start time
            start_time_str = row.get("StartTime", "")
            try:
                dt = datetime.strptime(start_time_str, "%Y/%m/%d %H:%M:%S.%f")
                timestamp = dt.timestamp()
            except:
                timestamp = float(idx)

            duration = float(row.get("Dur", 0))
            total_packets = int(row.get("TotPkts", 0))
            total_bytes = int(row.get("TotBytes", 0))

            # CTU-13 doesn't always have directional stats
            fwd_packets = total_packets // 2
            bwd_packets = total_packets - fwd_packets

            flow_id = f"ctu13-{idx}-{src_ip}-{dst_ip}"

            # Determine if malicious based on label
            is_malicious = any(mal_label in label for mal_label in self.MALICIOUS_LABELS)

            return DatasetFlow(
                flow_id=flow_id,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                timestamp=timestamp,
                duration=duration,
                total_packets=total_packets,
                total_bytes=total_bytes,
                fwd_packets=fwd_packets,
                bwd_packets=bwd_packets,
                label=label,
                is_malicious=is_malicious,
            )

        except Exception as e:
            return None

    def get_ground_truth(self, file_path: str) -> Dict[str, bool]:
        """Extract ground truth from CTU-13"""
        labels = {}
        for flow in self.parse(file_path):
            labels[flow.flow_id] = flow.is_malicious
        return labels


class UNSWNB15Parser(DatasetParser):
    """
    Parser for UNSW-NB15 dataset

    Uses CSV format with attack categories.
    """

    def parse(self, file_path: str) -> Iterator[DatasetFlow]:
        """Parse UNSW-NB15 CSV file"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for idx, row in enumerate(reader):
                try:
                    flow = self._parse_row(row, idx)
                    if flow:
                        yield flow
                except Exception as e:
                    print(f"Warning: Failed to parse row {idx}: {e}")
                    continue

    def _parse_row(self, row: Dict[str, str], idx: int) -> Optional[DatasetFlow]:
        """Parse UNSW-NB15 row"""
        try:
            src_ip = row.get("srcip", row.get("saddr", "")).strip()
            dst_ip = row.get("dstip", row.get("daddr", "")).strip()
            src_port = int(row.get("sport", 0))
            dst_port = int(row.get("dsport", 0))
            protocol = row.get("proto", "tcp").strip().upper()
            label = row.get("attack_cat", row.get("label", "normal")).strip()

            # UNSW-NB15 timestamps are Unix timestamps
            timestamp = float(row.get("stime", idx))
            duration = float(row.get("dur", 0))

            # Packet and byte counts
            src_packets = int(row.get("spkts", 0))
            dst_packets = int(row.get("dpkts", 0))
            total_packets = src_packets + dst_packets

            src_bytes = int(row.get("sbytes", 0))
            dst_bytes = int(row.get("dbytes", 0))
            total_bytes = src_bytes + dst_bytes

            flow_id = f"unsw-{idx}-{src_ip}-{dst_ip}"

            # Binary classification: 0 = normal, 1 = attack
            attack_flag = int(row.get("attack_flag", row.get("label", 0)))
            is_malicious = attack_flag == 1 or label.lower() != "normal"

            return DatasetFlow(
                flow_id=flow_id,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                timestamp=timestamp,
                duration=duration,
                total_packets=total_packets,
                total_bytes=total_bytes,
                fwd_packets=src_packets,
                bwd_packets=dst_packets,
                label=label,
                is_malicious=is_malicious,
            )

        except Exception as e:
            return None

    def get_ground_truth(self, file_path: str) -> Dict[str, bool]:
        """Extract ground truth from UNSW-NB15"""
        labels = {}
        for flow in self.parse(file_path):
            labels[flow.flow_id] = flow.is_malicious
        return labels


def create_dataset_parser(dataset_type: str) -> DatasetParser:
    """
    Factory function to create dataset parser

    Args:
        dataset_type: One of "cicids", "ctu13", "unsw-nb15"

    Returns:
        Appropriate dataset parser
    """
    parsers = {
        "cicids": CICIDSParser,
        "ctu13": CTU13Parser,
        "unsw-nb15": UNSWNB15Parser,
    }

    parser_class = parsers.get(dataset_type.lower())
    if not parser_class:
        raise ValueError(
            f"Unknown dataset type: {dataset_type}. " f"Supported types: {', '.join(parsers.keys())}"
        )

    return parser_class()
