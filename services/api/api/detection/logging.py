"""
Alerting and Logging Module

Comprehensive logging of detection pipeline:
- Raw features
- Intermediate outputs
- Final decisions
- Traceable decision paths

Complies with SRS Section 3.7: Alerting and Logging Module
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .deterministic import DetectionResult
from .features import FlowFeatures
from .fusion import FinalDecision
from .statistical import AnomalyScore


class DetectionLogger:
    """
    Structured logging for the detection pipeline

    Logs all stages of detection with full traceability.
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        log_to_file: bool = True,
        log_to_console: bool = True,
        export_format: str = "jsonl",  # jsonl or csv
    ):
        """
        Initialize detection logger

        Args:
            log_dir: Directory for log files
            log_to_file: Enable file logging
            log_to_console: Enable console logging
            export_format: Export format (jsonl or csv)
        """
        self.log_dir = Path(log_dir) if log_dir else Path("./logs")
        self.log_to_file = log_to_file
        self.log_to_console = log_to_console
        self.export_format = export_format

        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_loggers()

        # Session tracking
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._detection_count = 0

    def _setup_loggers(self):
        """Setup structured loggers for different pipeline stages"""
        self.feature_logger = self._create_logger("features")
        self.deterministic_logger = self._create_logger("deterministic")
        self.statistical_logger = self._create_logger("statistical")
        self.decision_logger = self._create_logger("decisions")
        self.alert_logger = self._create_logger("alerts")

    def _create_logger(self, name: str) -> logging.Logger:
        """Create a logger with file and console handlers"""
        logger = logging.getLogger(f"detection.{name}")
        logger.setLevel(logging.INFO)
        logger.handlers = []  # Clear existing handlers

        # File handler
        if self.log_to_file:
            log_file = self.log_dir / f"{name}.{self.export_format}"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(file_handler)

        # Console handler
        if self.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(console_handler)

        return logger

    def log_features(self, features: FlowFeatures) -> None:
        """Log extracted features"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": "feature_extraction",
            "flow_id": features.flow_id,
            "features": features.to_dict(),
        }
        self.feature_logger.info(json.dumps(entry))

    def log_deterministic(self, result: DetectionResult) -> None:
        """Log deterministic detection result"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": "deterministic_detection",
            "flow_id": result.flow_id,
            "result": result.to_dict(),
        }
        self.deterministic_logger.info(json.dumps(entry))

    def log_statistical(self, score: AnomalyScore) -> None:
        """Log statistical detection result"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": "statistical_detection",
            "flow_id": score.flow_id,
            "result": score.to_dict(),
        }
        self.statistical_logger.info(json.dumps(entry))

    def log_decision(self, decision: FinalDecision) -> None:
        """Log final detection decision"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "stage": "final_decision",
            "flow_id": decision.flow_id,
            "detection_number": self._detection_count,
            "decision": decision.to_dict(),
        }
        self.decision_logger.info(json.dumps(entry))
        self._detection_count += 1

    def log_alert(
        self,
        decision: FinalDecision,
        severity: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log security alert

        Args:
            decision: Final detection decision
            severity: Alert severity (low, medium, high, critical)
            additional_context: Additional context information
        """
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "alert_id": f"alert-{self.session_id}-{self._detection_count}",
            "flow_id": decision.flow_id,
            "threat_level": decision.threat_level.value,
            "confidence": decision.confidence,
            "severity": severity,
            "explanation": decision.explanation,
            "decision_path": decision.decision_path,
            "requires_investigation": decision.requires_investigation,
            "deterministic": {
                "classification": decision.deterministic_classification,
                "rules": decision.deterministic_rules,
            },
            "statistical": {
                "score": decision.statistical_score,
                "anomalies": decision.statistical_anomalies,
            },
        }

        if additional_context:
            alert["context"] = additional_context

        self.alert_logger.info(json.dumps(alert))

    def log_pipeline_execution(
        self,
        features: FlowFeatures,
        det_result: DetectionResult,
        stat_result: AnomalyScore,
        decision: FinalDecision,
    ) -> None:
        """
        Log complete pipeline execution for a single flow

        Provides full traceability from features to final decision.
        """
        self.log_features(features)
        self.log_deterministic(det_result)
        self.log_statistical(stat_result)
        self.log_decision(decision)

        # Generate alert if threat detected
        if decision.threat_level.value != "benign":
            severity = self._map_threat_to_severity(decision.threat_level.value)
            self.log_alert(decision, severity)

    def _map_threat_to_severity(self, threat_level: str) -> str:
        """Map threat level to alert severity"""
        mapping = {
            "benign": "info",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "critical": "critical",
        }
        return mapping.get(threat_level, "medium")

    def export_logs(self, output_path: str, stage: Optional[str] = None) -> None:
        """
        Export logs to specified path

        Args:
            output_path: Output file path
            stage: Specific stage to export (None = all)
        """
        # This would consolidate logs from the log directory
        # Implementation depends on desired export format
        pass

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current logging session"""
        return {
            "session_id": self.session_id,
            "detection_count": self._detection_count,
            "log_directory": str(self.log_dir),
            "export_format": self.export_format,
        }
