"""
Statistical Detection Layer

Statistical anomaly detection based on behavioral profiling.
Operates on suspicious/uncertain traffic from deterministic layer.

Complies with SRS Section 3.5: Statistical Detection Layer
"""

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .features import FlowFeatures


@dataclass
class StatisticalProfile:
    """Statistical profile for normal behavior"""

    feature_name: str
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0  # For Welford's online variance algorithm
    min_val: float = float("inf")
    max_val: float = float("-inf")

    @property
    def variance(self) -> float:
        """Compute variance"""
        if self.count < 2:
            return 0.0
        return self.m2 / self.count

    @property
    def std(self) -> float:
        """Compute standard deviation"""
        return math.sqrt(self.variance)

    def update(self, value: float) -> None:
        """
        Update profile with new value using Welford's online algorithm

        This allows incremental updates without storing all values.
        """
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)

    def z_score(self, value: float) -> float:
        """
        Calculate z-score for a value

        Z-score measures how many standard deviations away from mean.
        """
        if self.std == 0:
            return 0.0
        return abs(value - self.mean) / self.std

    def is_outlier(self, value: float, threshold: float = 3.0) -> bool:
        """Check if value is an outlier using z-score"""
        return self.z_score(value) > threshold


@dataclass
class AnomalyScore:
    """Anomaly score from statistical analysis"""

    flow_id: str
    overall_score: float  # 0.0 = normal, 1.0 = highly anomalous
    feature_scores: Dict[str, float] = field(default_factory=dict)
    anomalous_features: List[str] = field(default_factory=list)
    score_band: str = "normal"
    explanation: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "flow_id": self.flow_id,
            "overall_score": self.overall_score,
            "feature_scores": self.feature_scores,
            "anomalous_features": self.anomalous_features,
            "score_band": self.score_band,
            "explanation": self.explanation,
        }


class StatisticalDetector:
    """
    Statistical anomaly detector using behavioral profiling

    Builds profiles of normal behavior and detects deviations.
    Multiple statistical methods: z-score, IQR, isolation-based.
    """

    SCORE_BANDS = {
        "normal": (0.0, 0.30),
        "elevated": (0.30, 0.70),
        "anomalous": (0.70, 1.0),
    }

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_samples: int = 100,
    ):
        """
        Initialize statistical detector

        Args:
            z_score_threshold: Z-score threshold for outlier detection
            iqr_multiplier: IQR multiplier for outlier detection
            min_samples: Minimum samples needed for reliable profiling
        """
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_samples = min_samples

        self.profiles: Dict[str, StatisticalProfile] = {}
        self._is_trained = False

        # Features to profile
        self.tracked_features = [
            "duration",
            "total_packets",
            "total_bytes",
            "packet_rate",
            "byte_rate",
            "fwd_bwd_packet_ratio",
            "fwd_bwd_byte_ratio",
            "fwd_packet_size_mean",
            "fwd_packet_size_std",
            "bwd_packet_size_mean",
            "bwd_packet_size_std",
            "fwd_iat_mean",
            "fwd_iat_std",
            "bwd_iat_mean",
            "bwd_iat_std",
            "fwd_burst_count",
            "bwd_burst_count",
        ]

    def train(self, training_features: List[FlowFeatures]) -> None:
        """
        Train detector on normal (benign) traffic

        Args:
            training_features: List of flow features from known benign traffic
        """
        # Initialize profiles
        for feature_name in self.tracked_features:
            self.profiles[feature_name] = StatisticalProfile(feature_name)

        # Update profiles with training data
        for features in training_features:
            for feature_name in self.tracked_features:
                value = getattr(features, feature_name, None)
                if value is not None and not math.isinf(value) and not math.isnan(value):
                    self.profiles[feature_name].update(float(value))

        # Check if we have enough samples
        sample_count = min(profile.count for profile in self.profiles.values())
        self._is_trained = sample_count >= self.min_samples

    def detect(self, features: FlowFeatures) -> AnomalyScore:
        """
        Detect anomalies in flow features

        Returns anomaly score with feature-level explanations.
        """
        if not self._is_trained:
            return AnomalyScore(
                flow_id=features.flow_id,
                overall_score=0.0,
                score_band="normal",
                explanation="Detector not trained - insufficient baseline data",
            )

        feature_scores = {}
        anomalous_features = []

        # Calculate anomaly score for each feature
        for feature_name in self.tracked_features:
            value = getattr(features, feature_name, None)
            if value is None or math.isinf(value) or math.isnan(value):
                continue

            profile = self.profiles[feature_name]
            z_score = profile.z_score(float(value))

            # Normalize z-score to [0, 1] range
            # z=0 → 0.0, z=3 → 0.5, z=6 → 0.75, z→∞ → 1.0
            normalized_score = 1.0 - (1.0 / (1.0 + (z_score / 3.0)))

            feature_scores[feature_name] = normalized_score

            if profile.is_outlier(float(value), self.z_score_threshold):
                anomalous_features.append(feature_name)

        # Calculate overall anomaly score
        if feature_scores:
            # Use weighted combination: mean + max for sensitivity
            mean_score = statistics.mean(feature_scores.values())
            max_score = max(feature_scores.values())
            overall_score = (mean_score * 0.6) + (max_score * 0.4)
        else:
            overall_score = 0.0

        # Generate explanation
        if anomalous_features:
            top_anomalies = sorted(
                [(f, feature_scores[f]) for f in anomalous_features],
                key=lambda x: x[1],
                reverse=True,
            )[:3]
            explanation = f"Anomalous features detected: {', '.join(f for f, _ in top_anomalies)}"
        else:
            explanation = "Flow within normal behavioral profile"

        return AnomalyScore(
            flow_id=features.flow_id,
            overall_score=overall_score,
            feature_scores=feature_scores,
            anomalous_features=anomalous_features,
            score_band=self._score_band(overall_score),
            explanation=explanation,
        )

    def _score_band(self, score: float) -> str:
        """Categorize anomaly score into deterministic reporting bands."""
        if score >= self.SCORE_BANDS["anomalous"][0]:
            return "anomalous"
        if score >= self.SCORE_BANDS["elevated"][0]:
            return "elevated"
        return "normal"

    def update_baseline(self, features: FlowFeatures) -> None:
        """
        Incrementally update baseline with new benign flow

        Use this to adapt baseline to evolving normal behavior.
        """
        for feature_name in self.tracked_features:
            value = getattr(features, feature_name, None)
            if value is not None and not math.isinf(value) and not math.isnan(value):
                if feature_name in self.profiles:
                    self.profiles[feature_name].update(float(value))

    def save_baseline(self, path: str) -> None:
        """Save baseline profiles to file"""
        baseline_data = {
            "z_score_threshold": self.z_score_threshold,
            "iqr_multiplier": self.iqr_multiplier,
            "min_samples": self.min_samples,
            "is_trained": self._is_trained,
            "profiles": {
                name: {
                    "feature_name": prof.feature_name,
                    "count": prof.count,
                    "mean": prof.mean,
                    "m2": prof.m2,
                    "min_val": prof.min_val,
                    "max_val": prof.max_val,
                }
                for name, prof in self.profiles.items()
            },
        }

        with open(path, "w") as f:
            json.dump(baseline_data, f, indent=2)

    def load_baseline(self, path: str) -> None:
        """Load baseline profiles from file"""
        baseline_path = Path(path)
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline file not found: {path}")

        with open(baseline_path, "r") as f:
            baseline_data = json.load(f)

        self.z_score_threshold = baseline_data["z_score_threshold"]
        self.iqr_multiplier = baseline_data["iqr_multiplier"]
        self.min_samples = baseline_data["min_samples"]
        self._is_trained = baseline_data["is_trained"]

        self.profiles = {}
        for name, prof_data in baseline_data["profiles"].items():
            profile = StatisticalProfile(
                feature_name=prof_data["feature_name"],
                count=prof_data["count"],
                mean=prof_data["mean"],
                m2=prof_data["m2"],
                min_val=prof_data["min_val"],
                max_val=prof_data["max_val"],
            )
            self.profiles[name] = profile

    @property
    def is_trained(self) -> bool:
        """Check if detector has been trained"""
        return self._is_trained

    def get_profile_summary(self) -> Dict[str, dict]:
        """Get summary of all profiles"""
        return {
            name: {
                "count": prof.count,
                "mean": prof.mean,
                "std": prof.std,
                "min": prof.min_val,
                "max": prof.max_val,
            }
            for name, prof in self.profiles.items()
        }
