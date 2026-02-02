"""
Decision Fusion Module

Combines deterministic and statistical detection outputs into a single decision.
Implements hybrid detection with configurable weighting and explanation.

Complies with SRS Section 3.6: Decision Fusion and Correlation Module
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .deterministic import DetectionClass, DetectionResult
from .features import FlowFeatures
from .statistical import AnomalyScore


class ThreatLevel(Enum):
    """Final threat classification"""

    BENIGN = "benign"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FinalDecision:
    """
    Final detection decision combining deterministic and statistical analysis

    This is the output of the hybrid detection system.
    """

    flow_id: str
    threat_level: ThreatLevel
    confidence: float  # 0.0 to 1.0

    # Component decisions
    deterministic_classification: str
    deterministic_confidence: float
    deterministic_rules: list

    statistical_score: float
    statistical_anomalies: list

    # Explanation
    explanation: str
    decision_path: str  # How the decision was reached

    # Metadata
    requires_investigation: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "flow_id": self.flow_id,
            "threat_level": self.threat_level.value,
            "confidence": self.confidence,
            "deterministic": {
                "classification": self.deterministic_classification,
                "confidence": self.deterministic_confidence,
                "triggered_rules": self.deterministic_rules,
            },
            "statistical": {
                "anomaly_score": self.statistical_score,
                "anomalous_features": self.statistical_anomalies,
            },
            "explanation": self.explanation,
            "decision_path": self.decision_path,
            "requires_investigation": self.requires_investigation,
        }


class DecisionFusion:
    """
    Fuses deterministic and statistical detection outputs

    Implements configurable hybrid detection logic with explainability.
    """

    def __init__(
        self,
        deterministic_weight: float = 0.6,
        statistical_weight: float = 0.4,
        statistical_threshold: float = 0.7,
        confidence_threshold: float = 0.75,
    ):
        """
        Initialize decision fusion

        Args:
            deterministic_weight: Weight for deterministic component (0-1)
            statistical_weight: Weight for statistical component (0-1)
            statistical_threshold: Anomaly score threshold for statistical detection
            confidence_threshold: Minimum confidence for high-confidence decisions
        """
        if not math.isclose(deterministic_weight + statistical_weight, 1.0):
            raise ValueError("Weights must sum to 1.0")

        self.deterministic_weight = deterministic_weight
        self.statistical_weight = statistical_weight
        self.statistical_threshold = statistical_threshold
        self.confidence_threshold = confidence_threshold

    def fuse(
        self,
        features: FlowFeatures,
        deterministic_result: DetectionResult,
        statistical_result: AnomalyScore,
    ) -> FinalDecision:
        """
        Fuse deterministic and statistical results into final decision

        Args:
            features: Flow features (for context)
            deterministic_result: Result from rule-based detection
            statistical_result: Result from statistical anomaly detection

        Returns:
            Final detection decision with explanation
        """
        flow_id = features.flow_id

        # Extract component information
        det_class = deterministic_result.classification
        det_conf = deterministic_result.confidence
        det_rules = [
            {"id": r.rule_id, "name": r.name, "severity": r.severity, "category": r.category}
            for r in deterministic_result.triggered_rules
        ]

        stat_score = statistical_result.overall_score
        stat_anomalies = statistical_result.anomalous_features

        # Decision fusion logic
        threat_level, confidence, decision_path = self._compute_threat_level(
            det_class, det_conf, stat_score
        )

        # Generate explanation
        explanation = self._generate_explanation(
            deterministic_result, statistical_result, threat_level, confidence
        )

        # Determine if manual investigation needed
        requires_investigation = self._requires_investigation(
            threat_level, confidence, det_class, stat_score
        )

        return FinalDecision(
            flow_id=flow_id,
            threat_level=threat_level,
            confidence=confidence,
            deterministic_classification=det_class.value,
            deterministic_confidence=det_conf,
            deterministic_rules=det_rules,
            statistical_score=stat_score,
            statistical_anomalies=stat_anomalies,
            explanation=explanation,
            decision_path=decision_path,
            requires_investigation=requires_investigation,
        )

    def _compute_threat_level(
        self,
        det_class: DetectionClass,
        det_conf: float,
        stat_score: float,
    ) -> tuple[ThreatLevel, float, str]:
        """
        Compute final threat level using fusion logic

        Returns (threat_level, confidence, decision_path)
        """
        decision_path = []

        # Stage 1: Deterministic classification
        if det_class == DetectionClass.MALICIOUS:
            # High-confidence malicious detection
            threat_level = ThreatLevel.CRITICAL
            confidence = det_conf * self.deterministic_weight + stat_score * self.statistical_weight
            decision_path.append("Deterministic: MALICIOUS → CRITICAL")

            # Statistical confirmation increases confidence
            if stat_score >= self.statistical_threshold:
                confidence = min(confidence + 0.1, 1.0)
                decision_path.append(f"Statistical confirmation (score={stat_score:.2f}) → confidence boost")

        elif det_class == DetectionClass.SUSPICIOUS:
            # Suspicious behavior - check statistical
            if stat_score >= self.statistical_threshold:
                # Both agree: suspicious
                threat_level = ThreatLevel.HIGH
                confidence = (det_conf * self.deterministic_weight) + (stat_score * self.statistical_weight)
                decision_path.append(f"Deterministic: SUSPICIOUS + Statistical anomaly ({stat_score:.2f}) → HIGH")
            else:
                # Only deterministic suspicious
                threat_level = ThreatLevel.MEDIUM
                confidence = det_conf * self.deterministic_weight
                decision_path.append("Deterministic: SUSPICIOUS, Statistical: normal → MEDIUM")

        elif det_class == DetectionClass.UNCERTAIN:
            # Uncertain - rely more on statistical
            if stat_score >= self.statistical_threshold:
                threat_level = ThreatLevel.MEDIUM
                confidence = stat_score * self.statistical_weight
                decision_path.append(f"Deterministic: UNCERTAIN, Statistical anomaly ({stat_score:.2f}) → MEDIUM")
            else:
                threat_level = ThreatLevel.LOW
                confidence = 0.3
                decision_path.append("Deterministic: UNCERTAIN, Statistical: normal → LOW")

        else:  # BENIGN
            # Benign classification - check for statistical anomaly
            if stat_score >= self.statistical_threshold:
                # Statistical disagrees
                threat_level = ThreatLevel.MEDIUM
                confidence = stat_score * self.statistical_weight
                decision_path.append(f"Deterministic: BENIGN, but Statistical anomaly ({stat_score:.2f}) → MEDIUM")
            else:
                # Both agree: benign
                threat_level = ThreatLevel.BENIGN
                confidence = (1.0 - det_conf) * self.deterministic_weight + (
                    1.0 - stat_score
                ) * self.statistical_weight
                decision_path.append("Both components agree: BENIGN")

        return threat_level, confidence, " | ".join(decision_path)

    def _generate_explanation(
        self,
        det_result: DetectionResult,
        stat_result: AnomalyScore,
        threat_level: ThreatLevel,
        confidence: float,
    ) -> str:
        """Generate human-readable explanation"""
        parts = []

        # Threat assessment
        parts.append(f"Threat Level: {threat_level.value.upper()} (confidence: {confidence:.2%})")

        # Deterministic analysis
        if det_result.triggered_rules:
            rule_count = len(det_result.triggered_rules)
            rule_names = [r.name for r in det_result.triggered_rules[:2]]
            parts.append(f"Triggered {rule_count} detection rule(s): {', '.join(rule_names)}")
        else:
            parts.append("No detection rules triggered")

        # Statistical analysis
        if stat_result.anomalous_features:
            parts.append(
                f"Statistical analysis detected {len(stat_result.anomalous_features)} "
                f"anomalous feature(s) (score: {stat_result.overall_score:.2f})"
            )
        else:
            parts.append("No statistical anomalies detected")

        return ". ".join(parts) + "."

    def _requires_investigation(
        self,
        threat_level: ThreatLevel,
        confidence: float,
        det_class: DetectionClass,
        stat_score: float,
    ) -> bool:
        """Determine if flow requires manual investigation"""
        # Critical threats always require investigation
        if threat_level == ThreatLevel.CRITICAL:
            return True

        # Low confidence decisions need review
        if confidence < self.confidence_threshold and threat_level != ThreatLevel.BENIGN:
            return True

        # Contradictory signals (deterministic says benign, statistical says anomaly)
        if det_class == DetectionClass.BENIGN and stat_score >= self.statistical_threshold:
            return True

        # High statistical anomaly with uncertain deterministic
        if det_class == DetectionClass.UNCERTAIN and stat_score >= 0.8:
            return True

        return False


# Import math for isclose
import math
