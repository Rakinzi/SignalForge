"""
Deterministic Detection Layer

Rule-based behavioral detection using predefined conditions.
Acts as first-stage filter before statistical analysis.

Complies with SRS Section 3.4: Deterministic Detection Layer
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .features import FlowFeatures


class DetectionClass(Enum):
    """Detection classification"""

    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    UNCERTAIN = "uncertain"
    MALICIOUS = "malicious"


@dataclass
class Rule:
    """
    Behavioral detection rule

    A rule consists of conditions that must be met for the rule to trigger.
    """

    rule_id: str
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    conditions: List[Dict[str, Any]]
    category: str  # e.g., "C2", "exfiltration", "scanning", "DDoS"
    enabled: bool = True

    def evaluate(self, features: FlowFeatures) -> bool:
        """
        Evaluate rule against flow features

        All conditions must be True for rule to trigger (AND logic).
        """
        if not self.enabled:
            return False

        for condition in self.conditions:
            if not self._evaluate_condition(condition, features):
                return False

        return True

    def _evaluate_condition(self, condition: Dict[str, Any], features: FlowFeatures) -> bool:
        """Evaluate a single condition"""
        field_name = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        if not all([field_name, operator, value is not None]):
            return False

        # Get feature value
        feature_value = getattr(features, field_name, None)
        if feature_value is None:
            return False

        # Apply operator
        if operator == "gt":
            return feature_value > value
        elif operator == "gte":
            return feature_value >= value
        elif operator == "lt":
            return feature_value < value
        elif operator == "lte":
            return feature_value <= value
        elif operator == "eq":
            return feature_value == value
        elif operator == "neq":
            return feature_value != value
        elif operator == "in":
            return feature_value in value
        elif operator == "not_in":
            return feature_value not in value
        else:
            return False


@dataclass
class DetectionResult:
    """Result from deterministic detection"""

    flow_id: str
    classification: DetectionClass
    triggered_rules: List[Rule] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "flow_id": self.flow_id,
            "classification": self.classification.value,
            "triggered_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "severity": rule.severity,
                    "category": rule.category,
                }
                for rule in self.triggered_rules
            ],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class DeterministicDetector:
    """
    Rule-based detector using behavioral conditions

    Classifies flows as benign, suspicious, or uncertain for downstream processing.
    """

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize detector with rules

        Args:
            rules_path: Path to JSON file containing rules
        """
        self.rules: List[Rule] = []

        if rules_path:
            self.load_rules(rules_path)
        else:
            self._load_default_rules()

    def load_rules(self, rules_path: str) -> None:
        """Load rules from JSON file"""
        path = Path(rules_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {rules_path}")

        with open(path, "r") as f:
            rules_data = json.load(f)

        self.rules = []
        for rule_data in rules_data.get("rules", []):
            rule = Rule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                description=rule_data["description"],
                severity=rule_data["severity"],
                conditions=rule_data["conditions"],
                category=rule_data.get("category", "general"),
                enabled=rule_data.get("enabled", True),
            )
            self.rules.append(rule)

    def _load_default_rules(self) -> None:
        """Load default detection rules"""
        self.rules = [
            # C2 Beacon Detection
            Rule(
                rule_id="R001",
                name="Periodic Beaconing",
                description="Detects periodic connections characteristic of C2 beaconing",
                severity="high",
                category="C2",
                conditions=[
                    {"field": "fwd_iat_std", "operator": "lt", "value": 1.0},  # Low variance in timing
                    {"field": "fwd_packet_size_std", "operator": "lt", "value": 50},  # Consistent packet sizes
                    {"field": "duration", "operator": "gt", "value": 60},  # Long-lived connection
                    {"field": "is_bidirectional", "operator": "eq", "value": True},
                ],
            ),
            # Data Exfiltration
            Rule(
                rule_id="R002",
                name="High Outbound Volume",
                description="Detects unusually high outbound data transfer",
                severity="critical",
                category="exfiltration",
                conditions=[
                    {"field": "fwd_bwd_byte_ratio", "operator": "gt", "value": 10.0},  # Much more upload than download
                    {"field": "byte_rate", "operator": "gt", "value": 500000},  # > 500 KB/s
                    {"field": "duration", "operator": "gt", "value": 10},
                ],
            ),
            # Port Scanning
            Rule(
                rule_id="R003",
                name="SYN Scan Pattern",
                description="Detects TCP SYN scanning behavior",
                severity="medium",
                category="scanning",
                conditions=[
                    {"field": "protocol", "operator": "eq", "value": "TCP"},
                    {"field": "tcp_flags_syn_count", "operator": "gt", "value": 0},
                    {"field": "tcp_flags_fin_count", "operator": "eq", "value": 0},
                    {"field": "fwd_packets", "operator": "lte", "value": 2},  # Few packets
                    {"field": "bwd_packets", "operator": "eq", "value": 0},  # No response
                ],
            ),
            # DDoS/Flooding
            Rule(
                rule_id="R004",
                name="High Packet Rate",
                description="Detects flooding or DDoS behavior",
                severity="high",
                category="DDoS",
                conditions=[
                    {"field": "packet_rate", "operator": "gt", "value": 1000},  # > 1000 pps
                    {"field": "fwd_packet_size_mean", "operator": "lt", "value": 100},  # Small packets
                ],
            ),
            # Suspicious DNS-like Traffic
            Rule(
                rule_id="R005",
                name="DNS Tunneling Pattern",
                description="Detects potential DNS tunneling",
                severity="medium",
                category="tunneling",
                conditions=[
                    {"field": "protocol", "operator": "eq", "value": "UDP"},
                    {"field": "fwd_packet_size_mean", "operator": "gt", "value": 200},  # Large DNS queries
                    {"field": "packet_rate", "operator": "gt", "value": 10},
                    {"field": "duration", "operator": "gt", "value": 30},
                ],
            ),
            # Long-Duration Low-Volume Connection
            Rule(
                rule_id="R006",
                name="Persistent Connection",
                description="Detects long-lived, low-bandwidth connections",
                severity="low",
                category="persistence",
                conditions=[
                    {"field": "is_long_lived", "operator": "eq", "value": True},
                    {"field": "byte_rate", "operator": "lt", "value": 1000},  # < 1 KB/s
                    {"field": "packet_rate", "operator": "lt", "value": 1},
                ],
            ),
            # Asymmetric Traffic
            Rule(
                rule_id="R007",
                name="Asymmetric Traffic Pattern",
                description="Detects highly asymmetric bidirectional traffic",
                severity="medium",
                category="anomalous",
                conditions=[
                    {"field": "is_bidirectional", "operator": "eq", "value": True},
                    {"field": "fwd_bwd_packet_ratio", "operator": "gt", "value": 20},
                ],
            ),
            # Burst Transfer
            Rule(
                rule_id="R008",
                name="Bursty Data Transfer",
                description="Detects bursty traffic patterns",
                severity="low",
                category="anomalous",
                conditions=[
                    {"field": "fwd_burst_count", "operator": "gt", "value": 5},
                    {"field": "max_fwd_burst_size", "operator": "gt", "value": 20},
                ],
            ),
        ]

    def detect(self, features: FlowFeatures) -> DetectionResult:
        """
        Perform rule-based detection on flow features

        Returns detection result with classification and triggered rules.
        """
        triggered_rules = []

        # Evaluate all rules
        for rule in self.rules:
            if rule.evaluate(features):
                triggered_rules.append(rule)

        # Classify based on triggered rules
        classification, confidence, reasoning = self._classify(triggered_rules)

        return DetectionResult(
            flow_id=features.flow_id,
            classification=classification,
            triggered_rules=triggered_rules,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _classify(self, triggered_rules: List[Rule]) -> tuple[DetectionClass, float, str]:
        """
        Classify flow based on triggered rules

        Returns (classification, confidence, reasoning)
        """
        if not triggered_rules:
            return DetectionClass.BENIGN, 1.0, "No rules triggered"

        # Count severity levels
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        categories = set()

        for rule in triggered_rules:
            severity_counts[rule.severity] += 1
            categories.add(rule.category)

        # Classification logic
        if severity_counts["critical"] > 0:
            classification = DetectionClass.MALICIOUS
            confidence = 0.95
        elif severity_counts["high"] >= 2:
            classification = DetectionClass.SUSPICIOUS
            confidence = 0.85
        elif severity_counts["high"] == 1:
            classification = DetectionClass.SUSPICIOUS
            confidence = 0.75
        elif severity_counts["medium"] >= 2:
            classification = DetectionClass.SUSPICIOUS
            confidence = 0.65
        elif severity_counts["medium"] == 1:
            classification = DetectionClass.UNCERTAIN
            confidence = 0.50
        else:
            classification = DetectionClass.UNCERTAIN
            confidence = 0.40

        # Generate reasoning
        rule_names = [rule.name for rule in triggered_rules[:3]]  # Top 3
        reasoning = f"Triggered {len(triggered_rules)} rule(s): {', '.join(rule_names)}"
        if len(triggered_rules) > 3:
            reasoning += f" and {len(triggered_rules) - 3} more"

        reasoning += f". Categories: {', '.join(sorted(categories))}"

        return classification, confidence, reasoning

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule"""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < initial_count

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def export_rules(self, output_path: str) -> None:
        """Export rules to JSON file"""
        rules_data = {
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "description": rule.description,
                    "severity": rule.severity,
                    "category": rule.category,
                    "conditions": rule.conditions,
                    "enabled": rule.enabled,
                }
                for rule in self.rules
            ]
        }

        with open(output_path, "w") as f:
            json.dump(rules_data, f, indent=2)
