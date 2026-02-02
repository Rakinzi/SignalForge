"""
Hybrid Malware Detection System for Encrypted Network Traffic

This package implements a cascaded detection architecture combining:
- Deterministic rule-based detection
- Statistical anomaly detection
- Decision fusion and correlation

All detection operates on encrypted-traffic-safe features without payload inspection.
"""

from .capture import TrafficCapture, PCAPCapture, LiveCapture
from .flow import FlowConstructor, Flow
from .features import FeatureExtractor, FlowFeatures
from .deterministic import DeterministicDetector, DetectionResult
from .statistical import StatisticalDetector, AnomalyScore
from .fusion import DecisionFusion, FinalDecision
from .logging import DetectionLogger
from .evaluation import EvaluationMetrics

__all__ = [
    "TrafficCapture",
    "PCAPCapture",
    "LiveCapture",
    "FlowConstructor",
    "Flow",
    "FeatureExtractor",
    "FlowFeatures",
    "DeterministicDetector",
    "DetectionResult",
    "StatisticalDetector",
    "AnomalyScore",
    "DecisionFusion",
    "FinalDecision",
    "DetectionLogger",
    "EvaluationMetrics",
]
