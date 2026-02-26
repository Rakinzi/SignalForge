import unittest
from types import SimpleNamespace

from api.detection.deterministic import DetectionClass, DetectionResult
from api.detection.evaluation import EvaluationMetrics
from api.detection.fusion import DecisionFusion, ThreatLevel
from api.detection.statistical import AnomalyScore, StatisticalDetector


def _decision_inputs(det_class: DetectionClass, det_conf: float, stat_score: float):
    features = SimpleNamespace(flow_id="flow-1")
    det_result = DetectionResult(
        flow_id="flow-1",
        classification=det_class,
        triggered_rules=[],
        confidence=det_conf,
        reasoning="unit test",
    )
    stat_result = AnomalyScore(flow_id="flow-1", overall_score=stat_score)
    return features, det_result, stat_result


class DetectionPolicyTests(unittest.TestCase):
    def test_fusion_weights_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            DecisionFusion(deterministic_weight=0.7, statistical_weight=0.4)

    def test_malicious_deterministic_dominates_tiebreak(self):
        fusion = DecisionFusion()
        features, det_result, stat_result = _decision_inputs(DetectionClass.MALICIOUS, 0.95, 0.2)

        decision = fusion.fuse(features, det_result, stat_result)

        self.assertEqual(decision.threat_level, ThreatLevel.CRITICAL)
        self.assertIn("deterministic=malicious", " ".join(decision.decision_path_steps))

    def test_benign_plus_statistical_anomaly_requires_investigation(self):
        fusion = DecisionFusion(statistical_threshold=0.7)
        features, det_result, stat_result = _decision_inputs(DetectionClass.BENIGN, 1.0, 0.95)

        decision = fusion.fuse(features, det_result, stat_result)

        self.assertEqual(decision.threat_level, ThreatLevel.MEDIUM)
        self.assertTrue(decision.requires_investigation)

    def test_final_decision_includes_policy_metadata(self):
        fusion = DecisionFusion(fusion_policy_version="v-test")
        features, det_result, stat_result = _decision_inputs(DetectionClass.SUSPICIOUS, 0.8, 0.9)

        decision = fusion.fuse(features, det_result, stat_result)
        payload = decision.to_dict()

        self.assertEqual(payload["fusion_policy_version"], "v-test")
        self.assertIsInstance(payload["decision_path_steps"], list)
        self.assertIn("explanation_fields_complete", payload)

    def test_statistical_score_bands(self):
        detector = StatisticalDetector()

        self.assertEqual(detector._score_band(0.1), "normal")
        self.assertEqual(detector._score_band(0.45), "elevated")
        self.assertEqual(detector._score_band(0.9), "anomalous")

    def test_evaluation_report_contains_protocol_and_provenance(self):
        evaluator = EvaluationMetrics()
        evaluator.set_protocol(
            split_strategy="cross-dataset-holdout",
            train_set="train-a",
            validation_set="val-b",
            test_sets=["test-c"],
        )
        evaluator.set_provenance(
            dataset_hash="dataset-hash",
            config_hash="config-hash",
            commit_sha="abc1234",
            run_timestamp="2026-02-26T00:00:00Z",
        )

        report = evaluator.generate_report()

        self.assertEqual(report["protocol"]["split_strategy"], "cross-dataset-holdout")
        self.assertEqual(report["protocol"]["test_sets"], ["test-c"])
        self.assertEqual(report["provenance"]["commit_sha"], "abc1234")


if __name__ == "__main__":
    unittest.main()
