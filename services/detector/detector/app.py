import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import redis
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
    update,
)
from sqlalchemy.engine import Engine

STREAM = os.getenv("REDIS_STREAM", "flows")
REDIS_ADDR = os.getenv("REDIS_ADDR", "redis:6379")
REDIS_GROUP = os.getenv("REDIS_GROUP", "detector")
REDIS_CONSUMER = os.getenv("REDIS_CONSUMER", "detector-1")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge",
)

metadata = MetaData()

flows_table = Table(
    "flows",
    metadata,
    Column("id", String, primary_key=True),
    Column("start_time", DateTime, nullable=False),
    Column("end_time", DateTime, nullable=False),
    Column("src_ip", String, nullable=False),
    Column("dst_ip", String, nullable=False),
    Column("src_port", Integer, nullable=False),
    Column("dst_port", Integer, nullable=False),
    Column("protocol", String, nullable=False),
    Column("packet_count", Integer, nullable=False),
    Column("byte_count", Integer, nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("packet_rate", Float, nullable=False),
    Column("fwd_packets", Integer, nullable=False),
    Column("bwd_packets", Integer, nullable=False),
    Column("fwd_bytes", Integer, nullable=False),
    Column("bwd_bytes", Integer, nullable=False),
    Column("raw", Text, nullable=False),
)

detections_table = Table(
    "detections",
    metadata,
    Column("id", String, primary_key=True),
    Column("flow_id", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("rules_triggered", Text, nullable=False),
    Column("anomaly_score", Float, nullable=False),
    Column("baseline", Text, nullable=False),
    Column("explanation", Text, nullable=False),
)

alerts_table = Table(
    "alerts",
    metadata,
    Column("id", String, primary_key=True),
    Column("detection_id", String, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("severity", String, nullable=False),
    Column("status", String, nullable=False),
    Column("summary", Text, nullable=False),
)

baselines_table = Table(
    "baselines",
    metadata,
    Column("id", String, primary_key=True),
    Column("key", String, nullable=False),
    Column("count", Integer, nullable=False),
    Column("mean", Float, nullable=False),
    Column("m2", Float, nullable=False),
    Column("ewma", Float, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

audit_logs_table = Table(
    "audit_logs",
    metadata,
    Column("id", String, primary_key=True),
    Column("event", String, nullable=False),
    Column("actor", String, nullable=False),
    Column("occurred_at", DateTime, nullable=False),
    Column("metadata", Text, nullable=False),
)

evaluations_table = Table(
    "evaluations",
    metadata,
    Column("id", String, primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("flow_count", Integer, nullable=False),
    Column("alert_count", Integer, nullable=False),
    Column("high_severity", Integer, nullable=False),
    Column("notes", Text, nullable=False),
)


@dataclass
class Flow:
    flow_id: str
    start_time: datetime
    end_time: datetime
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    packet_count: int
    byte_count: int
    duration_ms: int
    packet_rate: float
    fwd_packets: int
    bwd_packets: int
    fwd_bytes: int
    bwd_bytes: int
    tcp_flags: str


@dataclass
class RuleDef:
    name: str
    severity: str
    description: str
    conditions: List[Dict[str, Any]]
    enabled: bool = True


@dataclass
class DetectorConfig:
    # Statistical scoring tunables.
    z_score_divisor: float = 6.0
    ewma_delta_divisor: float = 500.0
    min_baseline_count: int = 20

    # Cascaded execution policy.
    statistical_on_classes: set[str] = field(default_factory=lambda: {"suspicious", "uncertain"})
    deterministic_weight: float = 0.6
    statistical_weight: float = 0.4

    # Alerting and evaluation thresholds.
    alert_min_score: float = 0.5
    eval_malicious_threshold: float = 0.5

    # Severity mapping.
    severity_high_threshold: float = 0.8
    severity_medium_threshold: float = 0.5

    rules: List[RuleDef] = field(default_factory=list)


def _default_rules() -> List[RuleDef]:
    # Defaults tuned for research-lab encrypted-flow behavior.
    # All values are overridable via DETECTOR_CONFIG_PATH.
    # Complete 8-rule library per SRS requirements.
    return [
        RuleDef(
            name="syn_flood",
            severity="high",
            description="SYN-heavy traffic with elevated packet rate",
            conditions=[
                {"field": "tcp_flags", "operator": "contains", "value": "S", "source": "flow"},
                {"field": "packet_rate", "operator": "gt", "value": 200.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="port_scan",
            severity="medium",
            description="High-rate probes to common scanned ports",
            conditions=[
                {"field": "dst_port", "operator": "in", "value": [22, 23, 53, 80, 443, 445, 3389], "source": "flow"},
                {"field": "packet_rate", "operator": "gt", "value": 120.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="high_fanout",
            severity="high",
            description="Very short, bursty high-packet flows",
            conditions=[
                {"field": "flow_duration_ms", "operator": "lt", "value": 1000.0, "source": "features"},
                {"field": "packet_count", "operator": "gt", "value": 500, "source": "flow"},
            ],
        ),
        RuleDef(
            name="low_response",
            severity="medium",
            description="Strongly asymmetric forward traffic",
            conditions=[
                {"field": "fwd_bwd_ratio", "operator": "gt", "value": 10.0, "source": "features"},
                {"field": "packet_rate", "operator": "gt", "value": 80.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="c2_beaconing",
            severity="critical",
            description="Periodic connection pattern consistent with C2 beaconing",
            conditions=[
                {"field": "packet_count", "operator": "lt", "value": 50, "source": "flow"},
                {"field": "flow_duration_ms", "operator": "gt", "value": 5000.0, "source": "features"},
                {"field": "fwd_bwd_ratio", "operator": "lt", "value": 3.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="data_exfiltration",
            severity="critical",
            description="Sustained high outbound volume with low inbound",
            conditions=[
                {"field": "fwd_bwd_ratio", "operator": "gt", "value": 20.0, "source": "features"},
                {"field": "byte_rate", "operator": "gt", "value": 1000000.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="dns_tunneling",
            severity="high",
            description="Abnormal DNS query patterns suggesting tunneling",
            conditions=[
                {"field": "dst_port", "operator": "eq", "value": 53, "source": "flow"},
                {"field": "packet_rate", "operator": "gt", "value": 50.0, "source": "features"},
                {"field": "bytes_per_packet", "operator": "gt", "value": 200.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="persistent_connection",
            severity="medium",
            description="Long-lived low-bandwidth connection",
            conditions=[
                {"field": "flow_duration_ms", "operator": "gt", "value": 300000.0, "source": "features"},
                {"field": "packet_rate", "operator": "lt", "value": 10.0, "source": "features"},
                {"field": "byte_rate", "operator": "lt", "value": 10000.0, "source": "features"},
            ],
        ),
        RuleDef(
            name="burst_attack",
            severity="high",
            description="High-intensity packet burst indicating flooding or amplification",
            conditions=[
                {"field": "burst_intensity", "operator": "gt", "value": 500.0, "source": "features"},
                {"field": "flow_duration_ms", "operator": "lt", "value": 2000.0, "source": "features"},
            ],
        ),
    ]


def load_config() -> DetectorConfig:
    """
    Load detector configuration from file or use defaults.

    Reads configuration from DETECTOR_CONFIG_PATH environment variable.
    If not set or file missing, returns default configuration.

    Returns:
        DetectorConfig: Fully initialized configuration with rules

    Environment Variables:
        DETECTOR_CONFIG_PATH: Path to JSON configuration file

    Configuration File Format:
        See config/detector_config.example.json for schema
    """
    cfg = DetectorConfig(rules=_default_rules())
    cfg_path = os.getenv("DETECTOR_CONFIG_PATH")
    if not cfg_path:
        return cfg

    path = Path(cfg_path)
    if not path.exists():
        log_json("detector_config_missing", {"path": cfg_path})
        return cfg

    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        log_json("detector_config_invalid", {"path": cfg_path, "error": str(exc)})
        return cfg

    cfg.z_score_divisor = float(payload.get("z_score_divisor", cfg.z_score_divisor))
    cfg.ewma_delta_divisor = float(payload.get("ewma_delta_divisor", cfg.ewma_delta_divisor))
    cfg.min_baseline_count = int(payload.get("min_baseline_count", cfg.min_baseline_count))
    cfg.deterministic_weight = float(payload.get("deterministic_weight", cfg.deterministic_weight))
    cfg.statistical_weight = float(payload.get("statistical_weight", cfg.statistical_weight))
    cfg.alert_min_score = float(payload.get("alert_min_score", cfg.alert_min_score))
    cfg.eval_malicious_threshold = float(
        payload.get("eval_malicious_threshold", cfg.eval_malicious_threshold)
    )
    cfg.severity_high_threshold = float(
        payload.get("severity_high_threshold", cfg.severity_high_threshold)
    )
    cfg.severity_medium_threshold = float(
        payload.get("severity_medium_threshold", cfg.severity_medium_threshold)
    )
    classes = payload.get("statistical_on_classes")
    if isinstance(classes, list):
        cfg.statistical_on_classes = {str(c) for c in classes}

    if isinstance(payload.get("rules"), list):
        parsed_rules: List[RuleDef] = []
        for raw_rule in payload["rules"]:
            if not isinstance(raw_rule, dict):
                continue
            parsed_rules.append(
                RuleDef(
                    name=str(raw_rule.get("name", "unknown")),
                    severity=str(raw_rule.get("severity", "medium")),
                    description=str(raw_rule.get("description", "")),
                    conditions=list(raw_rule.get("conditions", [])),
                    enabled=bool(raw_rule.get("enabled", True)),
                )
            )
        if parsed_rules:
            cfg.rules = parsed_rules

    return cfg


def main() -> None:
    cfg = load_config()
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    init_db(engine)

    r = redis.Redis.from_url(f"redis://{REDIS_ADDR}", decode_responses=True)
    ensure_group(r)

    last_eval = 0.0
    eval_interval = int(os.getenv("EVAL_INTERVAL_SEC", "60"))

    while True:
        resp = r.xreadgroup(
            REDIS_GROUP,
            REDIS_CONSUMER,
            {STREAM: ">"},
            count=10,
            block=5000,
        )
        if not resp:
            ran = maybe_run_evaluation(engine, cfg, eval_interval, last_eval)
            if ran:
                last_eval = time.time()
            continue

        for _, messages in resp:
            for msg_id, data in messages:
                try:
                    envelope = json.loads(data.get("event", "{}"))
                    payload = envelope.get("payload", {})
                    flow = parse_flow(payload)
                    features = extract_features(flow)
                    baseline_before = load_baseline(engine, flow)
                    detection = evaluate(flow, features, baseline_before, cfg)
                    persist(engine, flow, payload, features, detection, cfg)
                    update_baseline(engine, flow, features, baseline_before)
                    r.xack(STREAM, REDIS_GROUP, msg_id)
                except Exception as exc:
                    log_json("detector_error", {"error": str(exc), "message_id": msg_id})
                    write_audit(
                        engine,
                        event="detector_error",
                        actor="detector",
                        metadata={"error": str(exc), "message_id": msg_id},
                    )
        ran = maybe_run_evaluation(engine, cfg, eval_interval, last_eval)
        if ran:
            last_eval = time.time()


def maybe_run_evaluation(engine: Engine, cfg: DetectorConfig, interval: int, last_eval: float) -> bool:
    if time.time() - last_eval < interval:
        return False
    confusion = compute_confusion_matrix(engine, cfg.eval_malicious_threshold)
    metrics = compute_eval_metrics(confusion) if confusion["labeled_flows"] > 0 else None
    notes_payload: Dict[str, Any]
    if metrics:
        notes_payload = {
            "confusion_matrix": {
                "true_positives": confusion["true_positives"],
                "false_positives": confusion["false_positives"],
                "true_negatives": confusion["true_negatives"],
                "false_negatives": confusion["false_negatives"],
            },
            "metrics": metrics,
            "labeled_flows": confusion["labeled_flows"],
            "unlabeled_flows": confusion["unlabeled_flows"],
            "eval_malicious_threshold": cfg.eval_malicious_threshold,
        }
    else:
        notes_payload = {
            "periodic_evaluation": True,
            "reason": "no_ground_truth_labels",
            "labeled_flows": 0,
            "unlabeled_flows": confusion["unlabeled_flows"],
        }

    with engine.begin() as conn:
        flow_count = conn.execute(select(func.count()).select_from(flows_table)).scalar_one()
        alert_count = conn.execute(select(func.count()).select_from(alerts_table)).scalar_one()
        high_sev = conn.execute(
            select(func.count()).select_from(alerts_table).where(alerts_table.c.severity == "high")
        ).scalar_one()
        conn.execute(
            evaluations_table.insert().values(
                id=f"eval-{int(time.time() * 1000)}",
                created_at=datetime.now(timezone.utc),
                flow_count=flow_count,
                alert_count=alert_count,
                high_severity=high_sev,
                notes=json.dumps(notes_payload),
            )
        )
    log_json(
        "evaluation_written",
        {
            "flow_count": flow_count,
            "alert_count": alert_count,
            "labeled_flows": confusion["labeled_flows"],
        },
    )
    return True


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)


def ensure_group(r: redis.Redis) -> None:
    try:
        r.xgroup_create(STREAM, REDIS_GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            return
        raise


def parse_flow(payload: dict) -> Flow:
    return Flow(
        flow_id=payload["flow_id"],
        start_time=parse_ts(payload["start_time"]),
        end_time=parse_ts(payload["end_time"]),
        src_ip=payload["src_ip"],
        dst_ip=payload["dst_ip"],
        src_port=int(payload["src_port"]),
        dst_port=int(payload["dst_port"]),
        protocol=payload.get("protocol", "TCP"),
        packet_count=int(payload["packet_count"]),
        byte_count=int(payload["byte_count"]),
        duration_ms=int(payload["duration_ms"]),
        packet_rate=float(payload["packet_rate"]),
        fwd_packets=int(payload.get("fwd_packets", 0)),
        bwd_packets=int(payload.get("bwd_packets", 0)),
        fwd_bytes=int(payload.get("fwd_bytes", 0)),
        bwd_bytes=int(payload.get("bwd_bytes", 0)),
        tcp_flags=str(payload.get("tcp_flags", "")),
    )


def extract_features(flow: Flow) -> Dict[str, float]:
    """
    Extract encrypted-traffic-safe features from flow metadata.

    SRS Section 3.3 compliant: No payload inspection, metadata only.
    Includes packet statistics, timing, directionality, burst/idle behavior.
    """
    duration_s = max(flow.duration_ms / 1000.0, 0.001)
    bpp = flow.byte_count / max(flow.packet_count, 1)
    fwd_bwd_ratio = (flow.fwd_packets + 1) / max(flow.bwd_packets, 1)

    # Burst detection: flows with high packet rate relative to duration
    # are considered bursty (>100 pkt in <1s = burst)
    is_burst = flow.packet_count > 100 and duration_s < 1.0
    burst_intensity = (flow.packet_count / duration_s) if is_burst else 0.0

    # Idle detection: long duration with low packet count suggests gaps
    # Conservative estimate: flow duration > 10s with <10 packets = idle periods
    idle_ratio = 0.0
    if duration_s > 10.0 and flow.packet_count < 50:
        # Estimate idle as proportion of time with no packets
        # Assume packets evenly distributed; gaps = duration - (packet_count * avg_interval)
        avg_packet_interval = duration_s / max(flow.packet_count, 1)
        active_time = flow.packet_count * 0.1  # Assume 100ms per packet transmission
        idle_ratio = max((duration_s - active_time) / duration_s, 0.0)

    # Session frequency: for long-lived flows, estimate periodic activity
    # Count "micro-sessions" as bursts of packets separated by >1s gaps
    # Conservative: approximate as fwd_packets / (duration_s / 60) for periodic flows
    session_frequency = 0.0
    if duration_s > 60.0:
        # Flows >1min with bidirectional traffic suggest periodic sessions
        if flow.bwd_packets > 0:
            session_frequency = (flow.fwd_packets + flow.bwd_packets) / (duration_s / 60.0)

    return {
        "packet_rate": flow.packet_rate,
        "byte_rate": flow.byte_count / duration_s,
        "flow_duration_ms": float(flow.duration_ms),
        "bytes_per_packet": bpp,
        "fwd_bwd_ratio": float(fwd_bwd_ratio),
        # SRS Section 3.3 required features
        "burst_intensity": burst_intensity,
        "idle_ratio": idle_ratio,
        "session_frequency": session_frequency,
    }


def evaluate(flow: Flow, features: Dict[str, float], baseline: Dict[str, float], cfg: DetectorConfig) -> Dict[str, object]:
    triggered_rules = evaluate_rules(flow, features, cfg.rules)
    det_class = deterministic_classification(
        triggered_rules,
        int(baseline.get("count", 0)),
        cfg.min_baseline_count,
    )
    det_score = deterministic_score(triggered_rules, det_class)

    # SRS-compliant cascaded policy: statistical analysis validates ALL flows
    # to complement (not replace) deterministic detection, but weighted by class.
    baseline_count = int(baseline.get("count", 0))
    has_baseline = baseline_count >= cfg.min_baseline_count

    stat_score = 0.0
    z = 0.0
    ewma_delta = 0.0
    stat_reason = "insufficient_baseline"

    if has_baseline:
        # Always compute statistical analysis when baseline is available
        z = zscore(features["packet_rate"], baseline)
        ewma_delta = abs(features["packet_rate"] - baseline.get("ewma", 0.0))
        stat_score = min(
            max((abs(z) / cfg.z_score_divisor) + (ewma_delta / cfg.ewma_delta_divisor), 0.0),
            1.0,
        )
        stat_reason = "computed"

        # Dynamic weight adjustment based on deterministic class
        # High-confidence deterministic results get lower statistical weight
        det_weight = cfg.deterministic_weight
        stat_weight = cfg.statistical_weight

        if det_class == "benign":
            # Benign flows: reduce statistical influence but still validate
            det_weight = 0.75
            stat_weight = 0.25
        elif det_class == "malicious":
            # Malicious: high deterministic confidence, but allow stat to confirm
            det_weight = 0.70
            stat_weight = 0.30
        # suspicious/uncertain: use configured weights (typically 60/40)

        final_score = min(max((det_weight * det_score) + (stat_weight * stat_score), 0.0), 1.0)
        decision_path = (
            f"deterministic={det_class},det_score={det_score:.2f},weight={det_weight:.2f}"
            f"|statistical={stat_reason},stat_score={stat_score:.2f},weight={stat_weight:.2f}"
        )
    else:
        # Insufficient baseline: rely purely on deterministic
        final_score = det_score
        decision_path = (
            f"deterministic={det_class},det_score={det_score:.2f}"
            f"|statistical={stat_reason},stat_score=0.00"
        )

    explanation = (
        f"rules={','.join(rule.name for rule in triggered_rules) or 'none'}; "
        f"packet_rate={features['packet_rate']:.2f}/s; z={z:.2f}; "
        f"ewma={baseline.get('ewma', 0.0):.2f}; duration_ms={flow.duration_ms}; "
        f"baseline_count={baseline_count}; "
        f"path={decision_path}"
    )

    return {
        "rules_triggered": [rule.name for rule in triggered_rules],
        "rules_triggered_meta": [
            {"name": rule.name, "severity": rule.severity, "description": rule.description}
            for rule in triggered_rules
        ],
        "deterministic_class": det_class,
        "deterministic_score": det_score,
        "statistical_score": stat_score,
        "statistical_reason": stat_reason,
        "anomaly_score": final_score,
        "baseline": baseline,
        "decision_path": decision_path,
        "explanation": explanation,
    }


def zscore(value: float, baseline: Dict[str, float]) -> float:
    """
    Calculate Z-score for statistical anomaly detection.

    Args:
        value: Observed metric value (e.g., packet_rate)
        baseline: Statistical baseline with mean and variance

    Returns:
        float: Standardized Z-score (standard deviations from mean)

    Z-Score Interpretation:
        |Z| < 2: Normal (within 95% confidence interval)
        |Z| 2-3: Mild anomaly
        |Z| > 3: Strong anomaly
        |Z| > 6: Extreme anomaly (used as normalization divisor)

    Notes:
        Uses population standard deviation (sqrt of variance).
        Defaults to std=1.0 if variance is zero to avoid division by zero.
    """
    mean = baseline.get("mean", 0.0)
    variance = baseline.get("variance", 0.0)
    std = variance ** 0.5 if variance > 0 else 1.0
    return (value - mean) / std


def evaluate_rules(flow: Flow, features: Dict[str, float], rules: List[RuleDef]) -> List[RuleDef]:
    """
    Evaluate all enabled rules against flow and return matching rules.

    Args:
        flow: Network flow metadata
        features: Extracted behavioral features
        rules: List of rule definitions to evaluate

    Returns:
        List[RuleDef]: Rules that matched (triggered) for this flow

    Rule Matching:
        All conditions in a rule must be satisfied (AND logic).
        Uses operators: gt, gte, lt, lte, eq, in, contains
    """
    return [rule for rule in rules if rule.enabled and rule_matches(rule, flow, features)]


def rule_matches(rule: RuleDef, flow: Flow, features: Dict[str, float]) -> bool:
    for condition in rule.conditions:
        source = condition.get("source", "features")
        field = condition.get("field")
        operator = condition.get("operator")
        expected = condition.get("value")
        if not field or not operator:
            return False

        if source == "flow":
            actual = getattr(flow, field, None)
        else:
            actual = features.get(field)

        if not compare_condition(actual, operator, expected):
            return False
    return True


def compare_condition(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "eq":
        return actual == expected
    if operator == "in":
        return actual in expected if isinstance(expected, list) else False
    if operator == "contains":
        return isinstance(actual, str) and str(expected) in actual
    return False


def deterministic_classification(rules: List[RuleDef], baseline_count: int, min_baseline_count: int) -> str:
    """
    Classify flow based on triggered rules and baseline availability.

    Args:
        rules: List of rules that triggered for this flow
        baseline_count: Number of observations in statistical baseline
        min_baseline_count: Minimum observations for reliable baseline

    Returns:
        str: Classification category: malicious, suspicious, uncertain, or benign

    Classification Logic:
        - malicious: Any critical/high severity rule triggered
        - suspicious: Medium/low severity rules triggered
        - uncertain: No rules triggered but insufficient baseline
        - benign: No rules triggered and sufficient baseline
    """
    if any(rule.severity in {"critical", "high"} for rule in rules):
        return "malicious"
    if rules:
        return "suspicious"
    if baseline_count < min_baseline_count:
        return "uncertain"
    return "benign"


def deterministic_score(rules: List[RuleDef], det_class: str) -> float:
    if det_class == "malicious":
        return 1.0
    if det_class == "suspicious":
        return min(0.7 + (0.1 * len(rules)), 0.95)
    if det_class == "uncertain":
        return 0.35
    return 0.05


def baseline_key(flow: Flow) -> str:
    return f"dst:{flow.dst_ip}"


def load_baseline(engine: Engine, flow: Flow) -> Dict[str, float]:
    key = baseline_key(flow)
    with engine.begin() as conn:
        row = conn.execute(select(baselines_table).where(baselines_table.c.key == key)).mappings().first()
    if not row:
        return {"mean": 0.0, "variance": 0.0, "ewma": 0.0, "count": 0}
    variance = row["m2"] / max(row["count"] - 1, 1)
    return {"mean": row["mean"], "variance": variance, "ewma": row["ewma"], "count": row["count"]}


def update_baseline(engine: Engine, flow: Flow, features: Dict[str, float], baseline: Dict[str, float]) -> None:
    """
    Update statistical baseline using Welford's online algorithm.

    Incrementally updates mean, variance (via M2), and EWMA for the entity
    associated with this flow. Uses Welford's numerically stable algorithm
    for variance computation.

    Args:
        engine: SQLAlchemy database engine
        flow: Network flow (used to determine baseline key)
        features: Extracted features (uses packet_rate for baseline)
        baseline: Current baseline statistics

    Algorithm:
        Welford's method for variance (1962):
        - count += 1
        - delta = value - mean
        - mean += delta / count
        - delta2 = value - mean
        - M2 += delta * delta2
        - variance = M2 / (count - 1)

        EWMA trend tracking:
        - ewma = alpha * value + (1 - alpha) * ewma
        - alpha = 0.2 (20% weight to new value, 80% to history)

    Database:
        Updates or inserts row in baselines table keyed by baseline_key(flow)
    """
    key = baseline_key(flow)
    value = features["packet_rate"]
    count = int(baseline.get("count", 0))
    mean = float(baseline.get("mean", 0.0))
    m2 = float(baseline.get("variance", 0.0)) * max(count - 1, 1)
    ewma = float(baseline.get("ewma", 0.0))

    count += 1
    delta = value - mean
    mean += delta / count
    delta2 = value - mean
    m2 += delta * delta2
    ewma = 0.2 * value + 0.8 * ewma

    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        existing = conn.execute(select(baselines_table).where(baselines_table.c.key == key)).mappings().first()
        if existing:
            conn.execute(
                update(baselines_table)
                .where(baselines_table.c.key == key)
                .values(count=count, mean=mean, m2=m2, ewma=ewma, updated_at=now)
            )
        else:
            conn.execute(
                baselines_table.insert().values(
                    id=f"baseline-{key}",
                    key=key,
                    count=count,
                    mean=mean,
                    m2=m2,
                    ewma=ewma,
                    updated_at=now,
                )
            )


def persist(
    engine: Engine,
    flow: Flow,
    raw_payload: dict,
    features: Dict[str, float],
    detection: Dict[str, object],
    cfg: DetectorConfig,
) -> None:
    detection_id = f"det-{int(time.time() * 1000)}"
    alert_id: Optional[str] = None
    created_at = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(
            flows_table.insert().values(
                id=flow.flow_id,
                start_time=flow.start_time,
                end_time=flow.end_time,
                src_ip=flow.src_ip,
                dst_ip=flow.dst_ip,
                src_port=flow.src_port,
                dst_port=flow.dst_port,
                protocol=flow.protocol,
                packet_count=flow.packet_count,
                byte_count=flow.byte_count,
                duration_ms=flow.duration_ms,
                packet_rate=flow.packet_rate,
                fwd_packets=flow.fwd_packets,
                bwd_packets=flow.bwd_packets,
                fwd_bytes=flow.fwd_bytes,
                bwd_bytes=flow.bwd_bytes,
                raw=json.dumps(raw_payload),
            )
        )

        conn.execute(
            detections_table.insert().values(
                id=detection_id,
                flow_id=flow.flow_id,
                created_at=created_at,
                rules_triggered=json.dumps(detection["rules_triggered"]),
                anomaly_score=detection["anomaly_score"],
                baseline=json.dumps(detection["baseline"]),
                explanation=detection["explanation"],
            )
        )

        if float(detection["anomaly_score"]) >= cfg.alert_min_score:
            alert_id = f"alert-{int(time.time() * 1000)}"
            conn.execute(
                alerts_table.insert().values(
                    id=alert_id,
                    detection_id=detection_id,
                    created_at=created_at,
                    severity=severity_from_score(float(detection["anomaly_score"]), cfg),
                    status="open",
                    summary=detection["explanation"],
                )
            )

    write_audit(
        engine,
        event="detection_created",
        actor="detector",
        metadata={
            "flow_id": flow.flow_id,
            "detection_id": detection_id,
            "alert_id": alert_id,
            "deterministic_class": detection["deterministic_class"],
            "deterministic_score": detection["deterministic_score"],
            "statistical_score": detection["statistical_score"],
            "final_score": detection["anomaly_score"],
        },
    )
    write_audit(
        engine,
        event="pipeline_trace",
        actor="detector",
        metadata={
            "flow_id": flow.flow_id,
            "features": features,
            "deterministic": {
                "class": detection["deterministic_class"],
                "score": detection["deterministic_score"],
                "rules": detection["rules_triggered_meta"],
            },
            "statistical": {
                "score": detection["statistical_score"],
                "reason": detection["statistical_reason"],
            },
            "fusion": {
                "final_score": detection["anomaly_score"],
                "path": detection["decision_path"],
            },
            "ground_truth": extract_ground_truth(raw_payload),
        },
    )

    log_json("detector_persisted", {"flow_id": flow.flow_id, "detection_id": detection_id})


def severity_from_score(score: float, cfg: DetectorConfig) -> str:
    if score > cfg.severity_high_threshold:
        return "high"
    if score > cfg.severity_medium_threshold:
        return "medium"
    return "low"


def extract_ground_truth(payload: Dict[str, Any]) -> Optional[bool]:
    if "is_malicious" in payload:
        val = payload["is_malicious"]
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            return val.strip().lower() in {"1", "true", "yes", "malicious"}

    label = payload.get("label")
    if isinstance(label, str):
        label_norm = label.strip().lower()
        if label_norm in {"benign", "normal", "0", "false"}:
            return False
        if label_norm:
            return True
    return None


def compute_confusion_matrix(engine: Engine, pred_threshold: float) -> Dict[str, int]:
    """
    Compute confusion matrix from ground truth labels and predictions.

    Compares ground truth labels (from flow metadata) against predicted
    malicious status (anomaly_score >= threshold) to calculate TP, FP, TN, FN.

    Args:
        engine: SQLAlchemy database engine
        pred_threshold: Score threshold for malicious prediction (typically 0.5)

    Returns:
        Dict with keys:
            - true_positives: Correctly identified malicious flows
            - false_positives: Benign flows incorrectly flagged
            - true_negatives: Correctly identified benign flows
            - false_negatives: Malicious flows missed
            - labeled_flows: Total flows with ground truth
            - unlabeled_flows: Flows without ground truth

    Ground Truth Sources:
        Extracts from flow.raw payload fields:
        - is_malicious (boolean/int/string)
        - label (string: benign/normal vs. attack names)

    Notes:
        Only flows with ground truth labels contribute to confusion matrix.
        Unlabeled flows are counted separately for transparency.
    """
    with engine.begin() as conn:
        rows = (
            conn.execute(
                select(flows_table.c.raw, detections_table.c.anomaly_score)
                .select_from(
                    flows_table.join(
                        detections_table, detections_table.c.flow_id == flows_table.c.id
                    )
                )
            )
            .mappings()
            .all()
        )

    tp = fp = tn = fn = labeled = unlabeled = 0
    for row in rows:
        try:
            raw_payload = json.loads(row["raw"])
        except Exception:
            raw_payload = {}
        truth = extract_ground_truth(raw_payload)
        predicted_malicious = float(row["anomaly_score"]) >= pred_threshold
        if truth is None:
            unlabeled += 1
            continue
        labeled += 1
        if predicted_malicious and truth:
            tp += 1
        elif predicted_malicious and not truth:
            fp += 1
        elif (not predicted_malicious) and truth:
            fn += 1
        else:
            tn += 1

    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "labeled_flows": labeled,
        "unlabeled_flows": unlabeled,
    }


def compute_eval_metrics(confusion: Dict[str, int]) -> Dict[str, float]:
    tp = float(confusion["true_positives"])
    fp = float(confusion["false_positives"])
    tn = float(confusion["true_negatives"])
    fn = float(confusion["false_negatives"])
    precision = tp / max(tp + fp, 1.0)
    recall = tp / max(tp + fn, 1.0)
    f1 = (2 * precision * recall) / max(precision + recall, 1e-9)
    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1.0)
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "accuracy": accuracy,
        "false_positive_rate": fp / max(fp + tn, 1.0),
        "false_negative_rate": fn / max(fn + tp, 1.0),
    }


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def write_audit(engine: Engine, event: str, actor: str, metadata: dict) -> None:
    with engine.begin() as conn:
        conn.execute(
            audit_logs_table.insert().values(
                id=f"audit-{int(time.time() * 1000)}",
                event=event,
                actor=actor,
                occurred_at=datetime.now(timezone.utc),
                metadata=json.dumps(metadata),
            )
        )


def log_json(event: str, fields: dict) -> None:
    payload = {"event": event, "ts": datetime.now(timezone.utc).isoformat()}
    payload.update(fields)
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    main()
