import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

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


RULES = [
    ("syn_flood", lambda f, feats: "S" in f.tcp_flags and feats["packet_rate"] > 200),
    ("port_scan", lambda f, feats: f.dst_port in {22, 23, 53} and feats["packet_rate"] > 120),
    ("high_fanout", lambda f, feats: feats["flow_duration_ms"] < 1000 and f.packet_count > 500),
    ("low_response", lambda f, feats: feats["fwd_bwd_ratio"] > 10 and feats["packet_rate"] > 80),
]


def main() -> None:
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
            ran = maybe_run_evaluation(engine, eval_interval, last_eval)
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
                    detection = evaluate(flow, features, baseline_before)
                    persist(engine, flow, payload, detection)
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
        ran = maybe_run_evaluation(engine, eval_interval, last_eval)
        if ran:
            last_eval = time.time()


def maybe_run_evaluation(engine: Engine, interval: int, last_eval: float) -> bool:
    if time.time() - last_eval < interval:
        return False
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
                notes="periodic_evaluation",
            )
        )
    log_json("evaluation_written", {"flow_count": flow_count, "alert_count": alert_count})
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
    duration_s = max(flow.duration_ms / 1000.0, 0.001)
    bpp = flow.byte_count / max(flow.packet_count, 1)
    fwd_bwd_ratio = (flow.fwd_packets + 1) / max(flow.bwd_packets, 1)
    return {
        "packet_rate": flow.packet_rate,
        "byte_rate": flow.byte_count / duration_s,
        "flow_duration_ms": float(flow.duration_ms),
        "bytes_per_packet": bpp,
        "fwd_bwd_ratio": float(fwd_bwd_ratio),
    }


def evaluate(flow: Flow, features: Dict[str, float], baseline: Dict[str, float]) -> Dict[str, object]:
    rules = []
    for name, predicate in RULES:
        if predicate(flow, features):
            rules.append(name)

    z = zscore(features["packet_rate"], baseline)
    ewma_delta = abs(features["packet_rate"] - baseline.get("ewma", 0.0))
    anomaly_score = min(max((abs(z) / 6.0) + (ewma_delta / 500.0), 0.0), 1.0)

    explanation = (
        f"rules={','.join(rules) or 'none'}; packet_rate={features['packet_rate']:.2f}/s; "
        f"z={z:.2f}; ewma={baseline.get('ewma', 0.0):.2f}; duration_ms={flow.duration_ms}"
    )

    return {
        "rules_triggered": rules,
        "anomaly_score": anomaly_score,
        "baseline": baseline,
        "explanation": explanation,
    }


def zscore(value: float, baseline: Dict[str, float]) -> float:
    mean = baseline.get("mean", 0.0)
    variance = baseline.get("variance", 0.0)
    std = variance ** 0.5 if variance > 0 else 1.0
    return (value - mean) / std


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


def persist(engine: Engine, flow: Flow, raw_payload: dict, detection: Dict[str, object]) -> None:
    detection_id = f"det-{int(time.time() * 1000)}"
    alert_id = f"alert-{int(time.time() * 1000)}"
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

        conn.execute(
            alerts_table.insert().values(
                id=alert_id,
                detection_id=detection_id,
                created_at=created_at,
                severity=severity_from_score(float(detection["anomaly_score"])),
                status="open",
                summary=detection["explanation"],
            )
        )

    write_audit(
        engine,
        event="detection_created",
        actor="detector",
        metadata={"flow_id": flow.flow_id, "detection_id": detection_id, "alert_id": alert_id},
    )

    log_json("detector_persisted", {"flow_id": flow.flow_id, "detection_id": detection_id})


def severity_from_score(score: float) -> str:
    if score > 0.8:
        return "high"
    if score > 0.5:
        return "medium"
    return "low"


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
