"""
Detection API Endpoints

REST API endpoints for the hybrid detection system.
"""

import csv
import io
import json
import os
import tempfile
import time as time_module
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, create_engine, select

from .auth import require_scope
from .detection.pipeline import DetectionPipeline
from .detection.datasets import create_dataset_parser

router = APIRouter(prefix="/detection", tags=["detection"])

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
jobs_metadata = MetaData()
detection_jobs = Table(
    "detection_jobs",
    jobs_metadata,
    Column("id", String, primary_key=True),
    Column("created_at", DateTime, nullable=False),
    Column("actor", String, nullable=False),
    Column("job_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("input_meta", Text, nullable=False),
    Column("result_json", Text, nullable=True),
    Column("error", Text, nullable=True),
)
jobs_metadata.create_all(engine)


class DetectionConfig(BaseModel):
    """Configuration for detection job"""

    rules_path: Optional[str] = None
    baseline_path: Optional[str] = None
    enable_logging: bool = True
    enable_evaluation: bool = True


class TrainingConfig(BaseModel):
    """Configuration for statistical training"""

    training_data_path: str
    baseline_output_path: str


# In-memory detection jobs (in production, use proper job queue)
DETECTION_JOBS = {}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_job(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": row["id"],
        "created_at": row["created_at"].isoformat(),
        "actor": row["actor"],
        "job_type": row["job_type"],
        "status": row["status"],
        "input": json.loads(row["input_meta"]) if row["input_meta"] else {},
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error": row["error"],
    }


def _persist_job(
    job_id: str,
    actor: str,
    job_type: str,
    status_value: str,
    input_meta: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            detection_jobs.insert().values(
                id=job_id,
                created_at=now_utc(),
                actor=actor,
                job_type=job_type,
                status=status_value,
                input_meta=json.dumps(jsonable_encoder(input_meta)),
                result_json=json.dumps(jsonable_encoder(result)) if result is not None else None,
                error=error,
            )
        )


@router.post("/upload-pcap")
async def upload_pcap(
    file: UploadFile = File(...),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Upload a PCAP file for analysis

    Returns file path for use in detection requests.
    """
    if not file.filename.endswith((".pcap", ".pcapng")):
        raise HTTPException(status_code=400, detail="Only PCAP files are supported")

    # Save to temporary location
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"upload_{user['username']}_{file.filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "file_path": file_path,
        "size_bytes": len(content),
    }


@router.post("/upload-ground-truth")
async def upload_ground_truth(
    file: UploadFile = File(...),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Upload ground-truth labels for evaluation.

    Expected JSON format:
    {
      "flow-id-1": true,
      "flow-id-2": false
    }
    """
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON ground truth files are supported")

    content = await file.read()
    try:
        payload = json.loads(content.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Ground truth must be an object of flow_id -> boolean")

    invalid = [k for k, v in payload.items() if not isinstance(k, str) or not isinstance(v, bool)]
    if invalid:
        raise HTTPException(status_code=400, detail="Ground truth values must be booleans keyed by flow_id")

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"ground_truth_{user['username']}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "status": "uploaded",
        "filename": file.filename,
        "file_path": file_path,
        "size_bytes": len(content),
        "labels_count": len(payload),
    }


@router.post("/analyze")
async def analyze_pcap(
    pcap_path: str = Form(...),
    rules_path: Optional[str] = Form(None),
    baseline_path: Optional[str] = Form(None),
    ground_truth_path: Optional[str] = Form(None),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Run detection analysis on a PCAP file

    This starts a detection job and returns job ID for status checking.
    """
    # Normalize optional inputs so callers can omit labels cleanly.
    rules_path = (rules_path or "").strip() or None
    baseline_path = (baseline_path or "").strip() or None
    ground_truth_path = (ground_truth_path or "").strip() or None

    # Validate paths
    if not os.path.exists(pcap_path):
        raise HTTPException(status_code=404, detail="PCAP file not found")

    if rules_path and not os.path.exists(rules_path):
        raise HTTPException(status_code=404, detail="Rules file not found")

    if baseline_path and not os.path.exists(baseline_path):
        raise HTTPException(status_code=404, detail="Baseline file not found")
    if ground_truth_path and not os.path.exists(ground_truth_path):
        raise HTTPException(status_code=404, detail="Ground truth file not found")

    job_id = f"job-{int(time_module.time() * 1000)}"

    # In production, this would be queued to a background worker
    # For now, we'll execute synchronously (not ideal for production)

    try:
        # Create pipeline
        pipeline = DetectionPipeline(
            capture_source=pcap_path,
            deterministic_rules_path=rules_path,
            statistical_baseline_path=baseline_path,
            enable_logging=True,
            enable_evaluation=True,
        )
        if ground_truth_path:
            pipeline.load_ground_truth(ground_truth_path)

        # Run detection
        decisions = []
        for decision in pipeline.run():
            decisions.append(decision.to_dict())

        # Get evaluation report
        report = pipeline.get_evaluation_report()

        result = {
            "job_id": job_id,
            "status": "completed",
            "flows_processed": pipeline.flows_processed,
            "decisions": decisions,
            "evaluation": report,
        }

        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="analyze",
            status_value="completed",
            input_meta={
                "pcap_path": pcap_path,
                "rules_path": rules_path,
                "baseline_path": baseline_path,
                "ground_truth_path": ground_truth_path,
            },
            result=result,
        )
        DETECTION_JOBS[job_id] = result
        return result

    except Exception as e:
        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="analyze",
            status_value="failed",
            input_meta={
                "pcap_path": pcap_path,
                "rules_path": rules_path,
                "baseline_path": baseline_path,
                "ground_truth_path": ground_truth_path,
            },
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.post("/train-statistical")
async def train_statistical_detector(
    training_pcap: str = Form(...),
    output_path: str = Form(...),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Train statistical detector on benign traffic

    Args:
        training_pcap: Path to PCAP with known benign traffic
        output_path: Where to save the trained baseline
    """
    if not os.path.exists(training_pcap):
        raise HTTPException(status_code=404, detail="Training PCAP not found")

    job_id = f"job-{int(time_module.time() * 1000)}"
    try:
        pipeline = DetectionPipeline(
            capture_source=training_pcap,
            enable_logging=False,
            enable_evaluation=False,
        )

        pipeline.train_statistical_detector(training_pcap)
        pipeline.statistical_detector.save_baseline(output_path)

        profile_summary = pipeline.statistical_detector.get_profile_summary()

        result = {
            "job_id": job_id,
            "status": "trained",
            "baseline_path": output_path,
            "profile_summary": profile_summary,
        }
        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="train-statistical",
            status_value="completed",
            input_meta={"training_pcap": training_pcap, "output_path": output_path},
            result=result,
        )
        DETECTION_JOBS[job_id] = result
        return result

    except Exception as e:
        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="train-statistical",
            status_value="failed",
            input_meta={"training_pcap": training_pcap, "output_path": output_path},
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/parse-dataset")
async def parse_dataset(
    dataset_type: str = Form(...),  # "cicids", "ctu13", "unsw-nb15"
    dataset_path: str = Form(...),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Parse a standard research dataset

    Extracts flows and ground truth labels.
    """
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")

    job_id = f"job-{int(time_module.time() * 1000)}"
    try:
        parser = create_dataset_parser(dataset_type)

        # Parse flows (limit to first 1000 for API response)
        flows = []
        for idx, flow in enumerate(parser.parse(dataset_path)):
            if idx >= 1000:
                break
            flows.append({
                "flow_id": flow.flow_id,
                "src_ip": flow.src_ip,
                "dst_ip": flow.dst_ip,
                "label": flow.label,
                "is_malicious": flow.is_malicious,
            })

        # Get ground truth
        ground_truth = parser.get_ground_truth(dataset_path)

        result = {
            "job_id": job_id,
            "dataset_type": dataset_type,
            "flows_parsed": len(flows),
            "total_ground_truth": len(ground_truth),
            "sample_flows": flows[:10],  # First 10 flows
            "malicious_count": sum(1 for v in ground_truth.values() if v),
            "benign_count": sum(1 for v in ground_truth.values() if not v),
        }
        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="parse-dataset",
            status_value="completed",
            input_meta={"dataset_type": dataset_type, "dataset_path": dataset_path},
            result=result,
        )
        DETECTION_JOBS[job_id] = result
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        _persist_job(
            job_id=job_id,
            actor=user["username"],
            job_type="parse-dataset",
            status_value="failed",
            input_meta={"dataset_type": dataset_type, "dataset_path": dataset_path},
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.get("/rules")
async def list_rules(user: dict = Depends(require_scope("detections:read"))):
    """List all detection rules"""
    from .detection.deterministic import DeterministicDetector

    detector = DeterministicDetector()

    rules = [
        {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "severity": rule.severity,
            "category": rule.category,
            "enabled": rule.enabled,
        }
        for rule in detector.rules
    ]

    return {"rules": rules, "total": len(rules)}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, user: dict = Depends(require_scope("detections:read"))):
    """Get detection job status and results"""
    with engine.begin() as conn:
        row = conn.execute(select(detection_jobs).where(detection_jobs.c.id == job_id)).mappings().first()
    if row:
        return _serialize_job(dict(row))
    if job_id in DETECTION_JOBS:
        return DETECTION_JOBS[job_id]
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs")
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    job_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    user: dict = Depends(require_scope("detections:read")),
):
    filters = []
    if job_type:
        filters.append(detection_jobs.c.job_type == job_type)
    if status_filter:
        filters.append(detection_jobs.c.status == status_filter)

    with engine.begin() as conn:
        rows = (
            conn.execute(
                select(detection_jobs)
                .where(*filters)
                .order_by(detection_jobs.c.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .mappings()
            .all()
        )

    return {
        "items": [_serialize_job(dict(row)) for row in rows],
        "limit": limit,
        "offset": offset,
    }


@router.get("/jobs/{job_id}/export")
async def export_job(
    job_id: str,
    format: str = "json",
    user: dict = Depends(require_scope("detections:read")),
):
    with engine.begin() as conn:
        row = conn.execute(select(detection_jobs).where(detection_jobs.c.id == job_id)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    item = _serialize_job(dict(row))
    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "job_id",
                "created_at",
                "actor",
                "job_type",
                "status",
                "error",
                "flows_processed",
                "decision_count",
            ],
        )
        writer.writeheader()
        result = item.get("result") or {}
        decisions = result.get("decisions") or []
        writer.writerow(
            {
                "job_id": item["job_id"],
                "created_at": item["created_at"],
                "actor": item["actor"],
                "job_type": item["job_type"],
                "status": item["status"],
                "error": item["error"] or "",
                "flows_processed": result.get("flows_processed", ""),
                "decision_count": len(decisions) if isinstance(decisions, list) else "",
            }
        )
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{job_id}.csv"'},
        )

    return item
