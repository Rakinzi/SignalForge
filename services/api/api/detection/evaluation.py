"""
Evaluation Module

Metrics and evaluation for detection system performance.
Supports ground-truth comparison and performance monitoring.

Complies with SRS Section 3.8: Evaluation Module
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .fusion import FinalDecision, ThreatLevel


@dataclass
class ConfusionMatrix:
    """Confusion matrix for binary classification"""

    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """F1 Score = 2 * (Precision * Recall) / (Precision + Recall)"""
        p = self.precision
        r = self.recall
        return (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        """Accuracy = (TP + TN) / (TP + TN + FP + FN)"""
        total = self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        """FPR = FP / (FP + TN)"""
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom > 0 else 0.0

    @property
    def false_negative_rate(self) -> float:
        """FNR = FN / (FN + TP)"""
        denom = self.false_negatives + self.true_positives
        return self.false_negatives / denom if denom > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "false_positives": self.false_positives,
                "true_negatives": self.true_negatives,
                "false_negatives": self.false_negatives,
            },
            "metrics": {
                "precision": self.precision,
                "recall": self.recall,
                "f1_score": self.f1_score,
                "accuracy": self.accuracy,
                "false_positive_rate": self.false_positive_rate,
                "false_negative_rate": self.false_negative_rate,
            },
        }


@dataclass
class PerformanceMetrics:
    """Performance and resource utilization metrics"""

    total_flows: int = 0
    processing_times: List[float] = field(default_factory=list)

    # Per-module timing
    capture_time: List[float] = field(default_factory=list)
    flow_construction_time: List[float] = field(default_factory=list)
    feature_extraction_time: List[float] = field(default_factory=list)
    deterministic_time: List[float] = field(default_factory=list)
    statistical_time: List[float] = field(default_factory=list)
    fusion_time: List[float] = field(default_factory=list)

    @property
    def avg_processing_time(self) -> float:
        """Average end-to-end processing time (ms)"""
        return sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0.0

    @property
    def max_processing_time(self) -> float:
        """Maximum processing time (ms)"""
        return max(self.processing_times) if self.processing_times else 0.0

    @property
    def min_processing_time(self) -> float:
        """Minimum processing time (ms)"""
        return min(self.processing_times) if self.processing_times else 0.0

    @property
    def throughput(self) -> float:
        """Flows per second"""
        if not self.processing_times:
            return 0.0
        total_time = sum(self.processing_times) / 1000.0  # Convert to seconds
        return self.total_flows / total_time if total_time > 0 else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "total_flows": self.total_flows,
            "performance": {
                "avg_processing_time_ms": self.avg_processing_time,
                "max_processing_time_ms": self.max_processing_time,
                "min_processing_time_ms": self.min_processing_time,
                "throughput_flows_per_second": self.throughput,
            },
            "module_timing": {
                "capture_avg_ms": sum(self.capture_time) / len(self.capture_time) if self.capture_time else 0,
                "flow_construction_avg_ms": (
                    sum(self.flow_construction_time) / len(self.flow_construction_time)
                    if self.flow_construction_time
                    else 0
                ),
                "feature_extraction_avg_ms": (
                    sum(self.feature_extraction_time) / len(self.feature_extraction_time)
                    if self.feature_extraction_time
                    else 0
                ),
                "deterministic_avg_ms": (
                    sum(self.deterministic_time) / len(self.deterministic_time) if self.deterministic_time else 0
                ),
                "statistical_avg_ms": (
                    sum(self.statistical_time) / len(self.statistical_time) if self.statistical_time else 0
                ),
                "fusion_avg_ms": sum(self.fusion_time) / len(self.fusion_time) if self.fusion_time else 0,
            },
        }


@dataclass
class EvaluationResults:
    """Complete evaluation results"""

    confusion_matrix: ConfusionMatrix
    performance_metrics: PerformanceMetrics
    threat_distribution: Dict[str, int] = field(default_factory=dict)
    investigation_required: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            **self.confusion_matrix.to_dict(),
            **self.performance_metrics.to_dict(),
            "threat_distribution": self.threat_distribution,
            "flows_requiring_investigation": self.investigation_required,
        }


@dataclass
class EvaluationProtocol:
    """Evaluation protocol metadata for reproducible research reporting."""

    split_strategy: str = "cross-dataset-holdout"
    train_set: str = "unknown"
    validation_set: str = "unknown"
    test_sets: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "split_strategy": self.split_strategy,
            "train_set": self.train_set,
            "validation_set": self.validation_set,
            "test_sets": self.test_sets,
        }


@dataclass
class EvaluationProvenance:
    """Run provenance metadata for reproducibility and auditability."""

    dataset_hash: str = "unknown"
    config_hash: str = "unknown"
    commit_sha: str = "unknown"
    run_timestamp: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "dataset_hash": self.dataset_hash,
            "config_hash": self.config_hash,
            "commit_sha": self.commit_sha,
            "run_timestamp": self.run_timestamp,
        }


class EvaluationMetrics:
    """
    Evaluation system for detection pipeline

    Compares predictions against ground truth and tracks performance.
    """

    def __init__(self):
        self.confusion_matrix = ConfusionMatrix()
        self.performance_metrics = PerformanceMetrics()
        self.threat_distribution: Dict[str, int] = defaultdict(int)
        self.investigation_count = 0
        self.protocol = EvaluationProtocol()
        self.provenance = EvaluationProvenance()

        # Decision history
        self.decisions: List[FinalDecision] = []
        self.ground_truth: Dict[str, bool] = {}  # flow_id -> is_malicious

    def add_ground_truth(self, flow_id: str, is_malicious: bool) -> None:
        """Add ground truth label for a flow"""
        self.ground_truth[flow_id] = is_malicious

    def add_ground_truth_batch(self, labels: Dict[str, bool]) -> None:
        """Add multiple ground truth labels"""
        self.ground_truth.update(labels)

    def set_protocol(
        self,
        split_strategy: str = "cross-dataset-holdout",
        train_set: str = "unknown",
        validation_set: str = "unknown",
        test_sets: Optional[List[str]] = None,
    ) -> None:
        """Set evaluation protocol metadata."""
        self.protocol = EvaluationProtocol(
            split_strategy=split_strategy,
            train_set=train_set,
            validation_set=validation_set,
            test_sets=test_sets or [],
        )

    def set_provenance(
        self,
        dataset_hash: str = "unknown",
        config_hash: str = "unknown",
        commit_sha: str = "unknown",
        run_timestamp: str = "unknown",
    ) -> None:
        """Set evaluation provenance metadata."""
        self.provenance = EvaluationProvenance(
            dataset_hash=dataset_hash,
            config_hash=config_hash,
            commit_sha=commit_sha,
            run_timestamp=run_timestamp,
        )

    def evaluate_decision(
        self,
        decision: FinalDecision,
        processing_time_ms: float,
        ground_truth: Optional[bool] = None,
    ) -> None:
        """
        Evaluate a detection decision

        Args:
            decision: Final detection decision
            processing_time_ms: Time taken to process this flow (milliseconds)
            ground_truth: True if flow is malicious, False if benign (optional)
        """
        # Store decision
        self.decisions.append(decision)

        # Update performance metrics
        self.performance_metrics.total_flows += 1
        self.performance_metrics.processing_times.append(processing_time_ms)

        # Update threat distribution
        self.threat_distribution[decision.threat_level.value] += 1

        # Track investigation requirements
        if decision.requires_investigation:
            self.investigation_count += 1

        # Update confusion matrix if ground truth available
        if ground_truth is not None:
            self._update_confusion_matrix(decision, ground_truth)
        elif decision.flow_id in self.ground_truth:
            self._update_confusion_matrix(decision, self.ground_truth[decision.flow_id])

    def _update_confusion_matrix(self, decision: FinalDecision, is_malicious: bool) -> None:
        """Update confusion matrix based on prediction and ground truth"""
        # Consider threat levels medium, high, critical as "malicious" prediction
        predicted_malicious = decision.threat_level in [
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL,
        ]

        if is_malicious and predicted_malicious:
            self.confusion_matrix.true_positives += 1
        elif is_malicious and not predicted_malicious:
            self.confusion_matrix.false_negatives += 1
        elif not is_malicious and predicted_malicious:
            self.confusion_matrix.false_positives += 1
        else:  # not is_malicious and not predicted_malicious
            self.confusion_matrix.true_negatives += 1

    def add_module_timing(
        self,
        capture: float = 0.0,
        flow_construction: float = 0.0,
        feature_extraction: float = 0.0,
        deterministic: float = 0.0,
        statistical: float = 0.0,
        fusion: float = 0.0,
    ) -> None:
        """Add timing information for individual modules"""
        if capture > 0:
            self.performance_metrics.capture_time.append(capture)
        if flow_construction > 0:
            self.performance_metrics.flow_construction_time.append(flow_construction)
        if feature_extraction > 0:
            self.performance_metrics.feature_extraction_time.append(feature_extraction)
        if deterministic > 0:
            self.performance_metrics.deterministic_time.append(deterministic)
        if statistical > 0:
            self.performance_metrics.statistical_time.append(statistical)
        if fusion > 0:
            self.performance_metrics.fusion_time.append(fusion)

    def get_results(self) -> EvaluationResults:
        """Get evaluation results"""
        return EvaluationResults(
            confusion_matrix=self.confusion_matrix,
            performance_metrics=self.performance_metrics,
            threat_distribution=dict(self.threat_distribution),
            investigation_required=self.investigation_count,
        )

    def generate_report(self, output_path: Optional[str] = None) -> dict:
        """
        Generate comprehensive evaluation report

        Args:
            output_path: Optional path to save report as JSON

        Returns:
            Report dictionary
        """
        results = self.get_results()
        report = {
            "evaluation_summary": {
                "total_flows_evaluated": self.performance_metrics.total_flows,
                "flows_with_ground_truth": len(self.ground_truth),
                "flows_requiring_investigation": self.investigation_count,
            },
            **results.to_dict(),
            "detection_rate": self.confusion_matrix.recall,
            "false_positive_rate": self.confusion_matrix.false_positive_rate,
            "false_negative_rate": self.confusion_matrix.false_negative_rate,
            "protocol": self.protocol.to_dict(),
            "provenance": self.provenance.to_dict(),
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report

    def load_ground_truth_from_file(self, file_path: str) -> None:
        """
        Load ground truth labels from JSON file

        Expected format:
        {
            "flow-123": true,  // malicious
            "flow-456": false, // benign
            ...
        }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {file_path}")

        with open(path, "r") as f:
            labels = json.load(f)

        self.add_ground_truth_batch(labels)

    def reset(self) -> None:
        """Reset all metrics"""
        self.confusion_matrix = ConfusionMatrix()
        self.performance_metrics = PerformanceMetrics()
        self.threat_distribution = defaultdict(int)
        self.investigation_count = 0
        self.decisions = []
        self.ground_truth = {}
        self.protocol = EvaluationProtocol()
        self.provenance = EvaluationProvenance()
