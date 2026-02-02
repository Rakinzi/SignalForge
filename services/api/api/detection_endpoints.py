"""
Detection API Endpoints

REST API endpoints for the hybrid detection system.
"""

import os
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from .auth import require_scope
from .detection.pipeline import DetectionPipeline, run_detection
from .detection.datasets import create_dataset_parser

router = APIRouter(prefix="/detection", tags=["detection"])


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


@router.post("/upload-pcap")
async def upload_pcap(
    file: UploadFile = File(...),
    user: dict = Depends(require_scope("flows:read")),
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


@router.post("/analyze")
async def analyze_pcap(
    pcap_path: str = Form(...),
    rules_path: Optional[str] = Form(None),
    baseline_path: Optional[str] = Form(None),
    user: dict = Depends(require_scope("detections:read")),
):
    """
    Run detection analysis on a PCAP file

    This starts a detection job and returns job ID for status checking.
    """
    # Validate paths
    if not os.path.exists(pcap_path):
        raise HTTPException(status_code=404, detail="PCAP file not found")

    if rules_path and not os.path.exists(rules_path):
        raise HTTPException(status_code=404, detail="Rules file not found")

    if baseline_path and not os.path.exists(baseline_path):
        raise HTTPException(status_code=404, detail="Baseline file not found")

    # Create job ID
    import time as time_module
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

        DETECTION_JOBS[job_id] = result

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@router.post("/train-statistical")
async def train_statistical_detector(
    training_pcap: str = Form(...),
    output_path: str = Form(...),
    user: dict = Depends(require_scope("config:read")),
):
    """
    Train statistical detector on benign traffic

    Args:
        training_pcap: Path to PCAP with known benign traffic
        output_path: Where to save the trained baseline
    """
    if not os.path.exists(training_pcap):
        raise HTTPException(status_code=404, detail="Training PCAP not found")

    try:
        pipeline = DetectionPipeline(
            capture_source=training_pcap,
            enable_logging=False,
            enable_evaluation=False,
        )

        pipeline.train_statistical_detector(training_pcap)
        pipeline.statistical_detector.save_baseline(output_path)

        profile_summary = pipeline.statistical_detector.get_profile_summary()

        return {
            "status": "trained",
            "baseline_path": output_path,
            "profile_summary": profile_summary,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.post("/parse-dataset")
async def parse_dataset(
    dataset_type: str = Form(...),  # "cicids", "ctu13", "unsw-nb15"
    dataset_path: str = Form(...),
    user: dict = Depends(require_scope("flows:read")),
):
    """
    Parse a standard research dataset

    Extracts flows and ground truth labels.
    """
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")

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

        return {
            "dataset_type": dataset_type,
            "flows_parsed": len(flows),
            "total_ground_truth": len(ground_truth),
            "sample_flows": flows[:10],  # First 10 flows
            "malicious_count": sum(1 for v in ground_truth.values() if v),
            "benign_count": sum(1 for v in ground_truth.values() if not v),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.get("/rules")
async def list_rules(user: dict = Depends(require_scope("config:read"))):
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
    if job_id not in DETECTION_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    return DETECTION_JOBS[job_id]
