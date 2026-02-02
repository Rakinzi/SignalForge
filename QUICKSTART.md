# SignalForge - Quick Start Guide

This guide will get you running detection analysis in under 5 minutes.

## Prerequisites

- Python 3.11+ installed
- PostgreSQL running
- A PCAP file to analyze (or use sample datasets)

## Step 1: Install Dependencies

```bash
cd services/api
uv sync
```

This installs:
- FastAPI (REST API)
- Scapy (packet parsing)
- SQLAlchemy (database)
- All detection dependencies

## Step 2: Set Environment Variables

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/signalforge"
export JWT_SECRET="your-secret-key-change-me"
```

## Step 3: Start the API

```bash
uv run uvicorn api.app:app --reload
```

The API will be available at http://localhost:8000

## Step 4: Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=researcher&email=researcher@uni.edu&password=research123&role=analyst"
```

## Step 5: Get an Access Token

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=researcher&password=research123"
```

Save the `access_token` from the response.

## Step 6: Run Detection (via API)

### Upload PCAP
```bash
curl -X POST http://localhost:8000/detection/upload-pcap \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@traffic.pcap"
```

### Analyze PCAP
```bash
curl -X POST http://localhost:8000/detection/analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pcap_path=/path/to/traffic.pcap"
```

## Step 7: Run Detection (Python Script)

Create `my_analysis.py`:

```python
from api.detection.pipeline import DetectionPipeline
from api.detection.fusion import ThreatLevel

# Create pipeline
pipeline = DetectionPipeline(
    capture_source="traffic.pcap",
    enable_logging=True,
    enable_evaluation=True
)

# Run detection
alerts = []
for decision in pipeline.run():
    if decision.threat_level != ThreatLevel.BENIGN:
        alerts.append(decision)
        print(f"\n⚠️  ALERT: {decision.threat_level.value.upper()}")
        print(f"   Confidence: {decision.confidence:.1%}")
        print(f"   {decision.explanation}")

# Print summary
print(f"\n\nTotal flows: {pipeline.flows_processed}")
print(f"Alerts generated: {len(alerts)}")

# Get evaluation report
report = pipeline.get_evaluation_report()
print(f"\nAvg processing time: {report['performance']['avg_processing_time_ms']:.2f}ms")
print(f"Throughput: {report['performance']['throughput_flows_per_second']:.1f} flows/sec")
```

Run it:
```bash
python my_analysis.py
```

## Step 8: Train Statistical Detector (Optional)

If you have a PCAP with known benign traffic:

```python
from api.detection.pipeline import DetectionPipeline

pipeline = DetectionPipeline(capture_source="benign.pcap")
pipeline.train_statistical_detector("benign.pcap")
pipeline.statistical_detector.save_baseline("my_baseline.json")
```

Then use it in detection:
```python
pipeline = DetectionPipeline(
    capture_source="test.pcap",
    statistical_baseline_path="my_baseline.json"
)
```

## Step 9: Use Research Datasets

### Parse CICIDS2017
```python
from api.detection.datasets import create_dataset_parser

parser = create_dataset_parser("cicids")
ground_truth = parser.get_ground_truth("CICIDS2017_Monday.csv")

# Use in evaluation
pipeline.evaluator.add_ground_truth_batch(ground_truth)
```

### Parse CTU-13
```python
parser = create_dataset_parser("ctu13")
flows = list(parser.parse("capture20110810.binetflow"))
```

### Parse UNSW-NB15
```python
parser = create_dataset_parser("unsw-nb15")
flows = list(parser.parse("UNSW-NB15.csv"))
```

## Step 10: View Results

### Via API
```bash
# List alerts
curl http://localhost:8000/alerts \
  -H "Authorization: Bearer YOUR_TOKEN"

# List detections
curl http://localhost:8000/detections \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get metrics
curl http://localhost:8000/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get reports
curl http://localhost:8000/reports \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Via Logs
Check `logs/` directory:
- `features.jsonl` - Extracted features
- `deterministic.jsonl` - Rule-based detection results
- `statistical.jsonl` - Anomaly detection results
- `decisions.jsonl` - Final decisions
- `alerts.jsonl` - Generated alerts

## Common Issues

### "scapy not found"
```bash
uv sync --reinstall
```

### "Database connection error"
Make sure PostgreSQL is running and DATABASE_URL is correct:
```bash
psql $DATABASE_URL -c "SELECT 1"
```

### "PCAP file not found"
Use absolute paths:
```python
import os
pcap_path = os.path.abspath("traffic.pcap")
```

### "Permission denied" (live capture)
Live capture requires root privileges:
```bash
sudo uv run python my_script.py
```

## Next Steps

1. **Read the full documentation**: [DETECTION_SYSTEM.md](./DETECTION_SYSTEM.md)
2. **Explore the API**: http://localhost:8000/docs
3. **Customize detection rules**: Edit detection rules in `deterministic.py`
4. **Integrate with your research**: Use the evaluation metrics for your analysis

## Example: Complete Analysis Workflow

```python
from api.detection.pipeline import DetectionPipeline
from api.detection.datasets import create_dataset_parser

# 1. Parse dataset to get ground truth
parser = create_dataset_parser("cicids")
ground_truth = parser.get_ground_truth("CICIDS2017.csv")

# 2. Create pipeline
pipeline = DetectionPipeline(
    capture_source="CICIDS2017.pcap",
    enable_evaluation=True
)

# 3. Add ground truth for evaluation
pipeline.evaluator.add_ground_truth_batch(ground_truth)

# 4. Run detection
for decision in pipeline.run():
    pass  # Processing...

# 5. Generate evaluation report
report = pipeline.get_evaluation_report()

# 6. Print results
print(f"Precision: {report['metrics']['precision']:.2%}")
print(f"Recall: {report['metrics']['recall']:.2%}")
print(f"F1-Score: {report['metrics']['f1_score']:.2%}")
print(f"Accuracy: {report['metrics']['accuracy']:.2%}")

# 7. Export for your paper
import json
with open("evaluation_results.json", "w") as f:
    json.dump(report, f, indent=2)
```

## Getting Help

- Check [DETECTION_SYSTEM.md](./DETECTION_SYSTEM.md) for detailed module documentation
- Review code comments in each module
- Use the interactive API docs at `/docs`
- Run the example script: `python services/api/example_detection.py`

---

You're now ready to analyze encrypted traffic with SignalForge! 🚀
