"""
Detection Pipeline Orchestrator

Complete end-to-end pipeline orchestrating all detection modules.
Implements the cascaded hybrid detection architecture.
"""

import time
from typing import Iterator, Optional

from .capture import TrafficCapture, create_capture
from .deterministic import DeterministicDetector
from .evaluation import EvaluationMetrics
from .features import FeatureExtractor
from .flow import FlowConstructor, construct_flows
from .fusion import DecisionFusion, FinalDecision
from .logging import DetectionLogger
from .statistical import StatisticalDetector


class DetectionPipeline:
    """
    Complete hybrid detection pipeline

    Orchestrates:
    1. Traffic capture
    2. Flow construction
    3. Feature extraction
    4. Deterministic detection
    5. Statistical detection
    6. Decision fusion
    7. Logging and evaluation
    """

    def __init__(
        self,
        capture_source: str,
        deterministic_rules_path: Optional[str] = None,
        statistical_baseline_path: Optional[str] = None,
        log_dir: Optional[str] = None,
        enable_logging: bool = True,
        enable_evaluation: bool = True,
    ):
        """
        Initialize detection pipeline

        Args:
            capture_source: PCAP file path or network interface
            deterministic_rules_path: Path to detection rules JSON
            statistical_baseline_path: Path to statistical baseline
            log_dir: Directory for logs
            enable_logging: Enable structured logging
            enable_evaluation: Enable evaluation metrics
        """
        # Initialize components
        self.capture = create_capture(capture_source)
        self.flow_constructor = FlowConstructor()
        self.feature_extractor = FeatureExtractor()
        self.deterministic_detector = DeterministicDetector(deterministic_rules_path)
        self.statistical_detector = StatisticalDetector()
        self.decision_fusion = DecisionFusion()

        # Load statistical baseline if provided
        if statistical_baseline_path:
            self.statistical_detector.load_baseline(statistical_baseline_path)

        # Logging
        self.enable_logging = enable_logging
        if self.enable_logging:
            self.logger = DetectionLogger(log_dir=log_dir)

        # Evaluation
        self.enable_evaluation = enable_evaluation
        if self.enable_evaluation:
            self.evaluator = EvaluationMetrics()

        self._flows_processed = 0

    def run(self) -> Iterator[FinalDecision]:
        """
        Run the complete detection pipeline

        Yields FinalDecision objects for each detected flow.
        """
        print(f"[Pipeline] Starting detection pipeline on {self.capture}")
        start_time = time.time()

        # Start capture
        self.capture.start()

        # Construct flows from packets
        flows = construct_flows(self.capture)

        for flow in flows:
            self._flows_processed += 1

            # Track pipeline timing
            pipeline_start = time.time()
            timings = {}

            # Feature extraction
            t0 = time.time()
            features = self.feature_extractor.extract(flow)
            timings["feature_extraction"] = (time.time() - t0) * 1000

            # Deterministic detection
            t0 = time.time()
            det_result = self.deterministic_detector.detect(features)
            timings["deterministic"] = (time.time() - t0) * 1000

            # Statistical detection (only on suspicious/uncertain flows for efficiency)
            t0 = time.time()
            stat_result = self.statistical_detector.detect(features)
            timings["statistical"] = (time.time() - t0) * 1000

            # Decision fusion
            t0 = time.time()
            final_decision = self.decision_fusion.fuse(features, det_result, stat_result)
            timings["fusion"] = (time.time() - t0) * 1000

            # Total processing time
            processing_time = (time.time() - pipeline_start) * 1000

            # Logging
            if self.enable_logging:
                self.logger.log_pipeline_execution(features, det_result, stat_result, final_decision)

            # Evaluation
            if self.enable_evaluation:
                self.evaluator.evaluate_decision(final_decision, processing_time)
                self.evaluator.add_module_timing(**timings)

            # Yield decision
            yield final_decision

        # Stop capture
        self.capture.stop()

        # Print summary
        elapsed = time.time() - start_time
        print(f"[Pipeline] Processed {self._flows_processed} flows in {elapsed:.2f}s")
        print(f"[Pipeline] Throughput: {self._flows_processed / elapsed:.2f} flows/sec")

    def train_statistical_detector(self, training_pcap: str) -> None:
        """
        Train statistical detector on benign traffic

        Args:
            training_pcap: Path to PCAP file with known benign traffic
        """
        print(f"[Pipeline] Training statistical detector on {training_pcap}")

        # Create temporary capture
        training_capture = create_capture(training_pcap)
        training_capture.start()

        # Extract features from training flows
        training_features = []
        for flow in construct_flows(training_capture):
            features = self.feature_extractor.extract(flow)
            training_features.append(features)

        training_capture.stop()

        # Train detector
        self.statistical_detector.train(training_features)
        print(f"[Pipeline] Trained on {len(training_features)} benign flows")

    def get_evaluation_report(self) -> dict:
        """Get evaluation report"""
        if not self.enable_evaluation:
            return {"error": "Evaluation not enabled"}

        return self.evaluator.generate_report()

    def export_logs(self, output_path: str) -> None:
        """Export logs to file"""
        if not self.enable_logging:
            print("[Pipeline] Logging not enabled")
            return

        self.logger.export_logs(output_path)

    def add_ground_truth(self, flow_id: str, is_malicious: bool) -> None:
        """Add ground truth label for evaluation"""
        if self.enable_evaluation:
            self.evaluator.add_ground_truth(flow_id, is_malicious)

    def load_ground_truth(self, file_path: str) -> None:
        """Load ground truth labels from file"""
        if self.enable_evaluation:
            self.evaluator.load_ground_truth_from_file(file_path)

    @property
    def flows_processed(self) -> int:
        """Number of flows processed"""
        return self._flows_processed


def run_detection(
    pcap_path: str,
    rules_path: Optional[str] = None,
    baseline_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """
    Convenience function to run detection on a PCAP file

    Args:
        pcap_path: Path to PCAP file
        rules_path: Optional path to detection rules
        baseline_path: Optional path to statistical baseline
        output_dir: Optional output directory for logs
    """
    pipeline = DetectionPipeline(
        capture_source=pcap_path,
        deterministic_rules_path=rules_path,
        statistical_baseline_path=baseline_path,
        log_dir=output_dir,
    )

    print(f"Running detection on {pcap_path}")
    print("=" * 60)

    threat_counts = {"benign": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}

    for decision in pipeline.run():
        threat_counts[decision.threat_level.value] += 1

        # Print alerts for non-benign threats
        if decision.threat_level.value != "benign":
            print(f"\n[ALERT] {decision.threat_level.value.upper()}")
            print(f"  Flow: {decision.flow_id}")
            print(f"  Confidence: {decision.confidence:.2%}")
            print(f"  Explanation: {decision.explanation}")

    print("\n" + "=" * 60)
    print("Detection Summary:")
    for level, count in threat_counts.items():
        print(f"  {level.upper()}: {count}")

    # Generate evaluation report
    report = pipeline.get_evaluation_report()
    print(f"\nPerformance:")
    print(f"  Avg Processing Time: {report['performance']['avg_processing_time_ms']:.2f}ms")
    print(f"  Throughput: {report['performance']['throughput_flows_per_second']:.2f} flows/sec")

    if "metrics" in report:
        metrics = report["metrics"]
        print(f"\nDetection Metrics:")
        print(f"  Precision: {metrics['precision']:.2%}")
        print(f"  Recall: {metrics['recall']:.2%}")
        print(f"  F1 Score: {metrics['f1_score']:.2%}")
