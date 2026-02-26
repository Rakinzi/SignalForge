"""
Decision Fusion Module

Combines deterministic and statistical detection outputs into a single decision.
Implements hybrid detection with configurable weighting and explanation.

Complies with SRS Section 3.6: Decision Fusion and Correlation Module
"""

import math
from dataclasses import dataclass, field
from enum import Enum

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
    Final detection decision combining deterministic and statistical analysis.

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
    decision_path: str  # Backward-compatible string path
    decision_path_steps: list[str] = field(default_factory=list)

    # Metadata
    requires_investigation: bool = False
    fusion_policy_version: str = "v1.1"
    explanation_fields_complete: bool = True

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
            "decision_path_steps": self.decision_path_steps,
            "requires_investigation": self.requires_investigation,
            "fusion_policy_version": self.fusion_policy_version,
            "explanation_fields_complete": self.explanation_fields_complete,
        }


class DecisionFusion:
    """
    Fuses deterministic and statistical detection outputs.

    Implements configurable hybrid detection logic with explainability.

    Deterministic score semantics:
      - benign: [0.00, 0.35]
      - uncertain: (0.35, 0.60]
      - suspicious: (0.60, 0.85]
      - malicious: (0.85, 1.00]

    Statistical score semantics:
      - normal: [0.00, 0.30)
      - elevated: [0.30, 0.70)
      - anomalous: [0.70, 1.00]
    """

    DETERMINISTIC_SCORE_BANDS = {
        "benign": (0.00, 0.35),
        "uncertain": (0.35, 0.60),
        "suspicious": (0.60, 0.85),
        "malicious": (0.85, 1.00),
    }

    STATISTICAL_SCORE_BANDS = {
        "normal": (0.00, 0.30),
        "elevated": (0.30, 0.70),
        "anomalous": (0.70, 1.00),
    }

    def __init__(
        self,
        deterministic_weight: float = 0.6,
        statistical_weight: float = 0.4,
        statistical_threshold: float = 0.7,
        confidence_threshold: float = 0.75,
        fusion_policy_version: str = "v1.1",
    ):
        """
        Initialize decision fusion.

        Args:
            deterministic_weight: Weight for deterministic component (0-1)
            statistical_weight: Weight for statistical component (0-1)
            statistical_threshold: Anomaly score threshold for statistical detection
            confidence_threshold: Minimum confidence for high-confidence decisions
            fusion_policy_version: Policy identifier emitted in all final decisions
        """
        if not math.isclose(deterministic_weight + statistical_weight, 1.0):
            raise ValueError("Weights must sum to 1.0")

        self.deterministic_weight = deterministic_weight
        self.statistical_weight = statistical_weight
        self.statistical_threshold = statistical_threshold
        self.confidence_threshold = confidence_threshold
        self.fusion_policy_version = fusion_policy_version

    def fuse(
        self,
        features: FlowFeatures,
        deterministic_result: DetectionResult,
        statistical_result: AnomalyScore,
    ) -> FinalDecision:
        """
        Fuse deterministic and statistical results into final decision.

        Args:
            features: Flow features (for context)
            deterministic_result: Result from rule-based detection
            statistical_result: Result from statistical anomaly detection

        Returns:
            Final detection decision with explanation
        """
        flow_id = features.flow_id

        det_class = deterministic_result.classification
        det_conf = deterministic_result.confidence
        det_rules = [
            {"id": r.rule_id, "name": r.name, "severity": r.severity, "category": r.category}
            for r in deterministic_result.triggered_rules
        ]

        stat_score = statistical_result.overall_score
        stat_anomalies = statistical_result.anomalous_features

        threat_level, confidence, decision_path_steps = self._compute_threat_level(
            det_class, det_conf, stat_score
        )

        confidence = min(max(confidence, 0.0), 1.0)

        explanation = self._generate_explanation(
            deterministic_result, statistical_result, threat_level, confidence
        )

        requires_investigation = self._requires_investigation(
            threat_level, confidence, det_class, stat_score
        )

        decision_path = " | ".join(decision_path_steps)

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
            decision_path_steps=decision_path_steps,
            requires_investigation=requires_investigation,
            fusion_policy_version=self.fusion_policy_version,
            explanation_fields_complete=self._has_complete_explanation(
                det_rules, stat_anomalies, explanation, decision_path_steps
            ),
        )

    def _compute_threat_level(
        self,
        det_class: DetectionClass,
        det_conf: float,
        stat_score: float,
    ) -> tuple[ThreatLevel, float, list[str]]:
        """
        Compute final threat level using fusion logic.

        Tie-break order:
          1) MALICIOUS deterministic classification dominates -> CRITICAL
          2) SUSPICIOUS + anomalous statistical score -> HIGH
          3) Contradiction (BENIGN + anomalous score) -> MEDIUM + investigation
          4) UNCERTAIN cases rely on statistical thresholding
          5) Dual benign signal -> BENIGN

        Returns (threat_level, confidence, decision_path_steps)
        """
        decision_path_steps: list[str] = []

        if det_class == DetectionClass.MALICIOUS:
            threat_level = ThreatLevel.CRITICAL
            confidence = (det_conf * self.deterministic_weight) + (stat_score * self.statistical_weight)
            decision_path_steps.append("deterministic=malicious => threat=critical")

            if stat_score >= self.statistical_threshold:
                confidence = min(confidence + 0.1, 1.0)
                decision_path_steps.append("statistical anomaly confirms deterministic malicious verdict")

            return threat_level, confidence, decision_path_steps

        if det_class == DetectionClass.SUSPICIOUS:
            if stat_score >= self.statistical_threshold:
                threat_level = ThreatLevel.HIGH
                confidence = (det_conf * self.deterministic_weight) + (stat_score * self.statistical_weight)
                decision_path_steps.append("deterministic=suspicious and statistical=anomalous => threat=high")
            else:
                threat_level = ThreatLevel.MEDIUM
                confidence = det_conf * self.deterministic_weight
                decision_path_steps.append("deterministic=suspicious and statistical=non-anomalous => threat=medium")

            return threat_level, confidence, decision_path_steps

        if det_class == DetectionClass.UNCERTAIN:
            if stat_score >= self.statistical_threshold:
                threat_level = ThreatLevel.MEDIUM
                confidence = (0.2 * self.deterministic_weight) + (stat_score * self.statistical_weight)
                decision_path_steps.append("deterministic=uncertain and statistical=anomalous => threat=medium")
            else:
                threat_level = ThreatLevel.LOW
                confidence = 0.3
                decision_path_steps.append("deterministic=uncertain and statistical=non-anomalous => threat=low")

            return threat_level, confidence, decision_path_steps

        # BENIGN path
        if stat_score >= self.statistical_threshold:
            threat_level = ThreatLevel.MEDIUM
            confidence = (0.1 * self.deterministic_weight) + (stat_score * self.statistical_weight)
            decision_path_steps.append("deterministic=benign but statistical=anomalous => contradiction => threat=medium")
        else:
            threat_level = ThreatLevel.BENIGN
            confidence = ((1.0 - det_conf) * self.deterministic_weight) + (
                (1.0 - stat_score) * self.statistical_weight
            )
            decision_path_steps.append("deterministic=benign and statistical=non-anomalous => threat=benign")

        return threat_level, confidence, decision_path_steps

    def _generate_explanation(
        self,
        det_result: DetectionResult,
        stat_result: AnomalyScore,
        threat_level: ThreatLevel,
        confidence: float,
    ) -> str:
        """Generate human-readable explanation"""
        parts = [f"Threat Level: {threat_level.value.upper()} (confidence: {confidence:.2%})"]

        if det_result.triggered_rules:
            rule_count = len(det_result.triggered_rules)
            rule_names = [r.name for r in det_result.triggered_rules[:3]]
            parts.append(f"Deterministic: {rule_count} rule(s) triggered: {', '.join(rule_names)}")
        else:
            parts.append("Deterministic: no rules triggered")

        if stat_result.anomalous_features:
            parts.append(
                "Statistical: "
                f"{len(stat_result.anomalous_features)} anomalous feature(s) "
                f"(score: {stat_result.overall_score:.2f})"
            )
        else:
            parts.append(f"Statistical: no anomalous features (score: {stat_result.overall_score:.2f})")

        return ". ".join(parts) + "."

    def _has_complete_explanation(
        self,
        deterministic_rules: list,
        statistical_anomalies: list,
        explanation: str,
        decision_path_steps: list[str],
    ) -> bool:
        """Validate mandatory explainability fields are present for downstream audits."""
        return bool(explanation and decision_path_steps is not None and deterministic_rules is not None and statistical_anomalies is not None)

    def _requires_investigation(
        self,
        threat_level: ThreatLevel,
        confidence: float,
        det_class: DetectionClass,
        stat_score: float,
    ) -> bool:
        """Determine if flow requires manual investigation"""
        if threat_level == ThreatLevel.CRITICAL:
            return True

        if confidence < self.confidence_threshold and threat_level != ThreatLevel.BENIGN:
            return True

        if det_class == DetectionClass.BENIGN and stat_score >= self.statistical_threshold:
            return True

        if det_class == DetectionClass.UNCERTAIN and stat_score >= 0.8:
            return True

        return False
