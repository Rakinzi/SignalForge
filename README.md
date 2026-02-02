# SignalForge

**A Hybrid Approach to Malware Detection in Encrypted Network Traffic**

SignalForge is a research-grade network security platform implementing a cascaded hybrid detection architecture that combines deterministic (rule-based) and statistical (anomaly-based) malware detection mechanisms.

## 🎯 Key Features

- **Hybrid Detection Architecture**: Combines deterministic rules with statistical anomaly detection
- **Encrypted Traffic Analysis**: Operates on metadata without payload inspection
- **Explainable Decisions**: Full traceability from features to final classification
- **Research-Grade**: Built for academic evaluation and methodology validation
- **Standard Dataset Support**: CICIDS2017/2018, CTU-13, UNSW-NB15
- **Real-time & Offline**: Supports both PCAP analysis and live capture
- **Complete API**: REST endpoints with JWT authentication

## 📊 System Architecture

```
Traffic Source (PCAP/Live Interface)
           ↓
Flow Construction & Feature Extraction
           ↓
┌────────────────────────────────┐
│  Deterministic Detection       │  Rule-based behavioral analysis
│  (First-stage filter)          │  Classification: Benign/Suspicious/Uncertain
└────────────────────────────────┘
           ↓
┌────────────────────────────────┐
│  Statistical Detection         │  Anomaly-based behavioral profiling
│  (Refinement layer)            │  Z-score deviation analysis
└────────────────────────────────┘
           ↓
┌────────────────────────────────┐
│  Decision Fusion               │  Hybrid classification with confidence
│  (Weighted combination)        │  Threat Level: Benign → Critical
└────────────────────────────────┘
           ↓
Alerts, Logging, Evaluation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Node.js 20+ (for frontend)
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/SignalForge.git
   cd SignalForge
   ```

2. **Set up the backend**
   ```bash
   cd services/api
   uv sync  # Install dependencies
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run the API**
   ```bash
   uv run uvicorn api.app:app --reload
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs

### Docker Deployment

```bash
docker-compose -f deploy/docker-compose.dev.yml up
```

## 📖 Documentation

- **[DETECTION_SYSTEM.md](./DETECTION_SYSTEM.md)** - Complete detection system documentation
- **[API Documentation](http://localhost:8000/docs)** - Interactive API docs (when running)
- **[Frontend Documentation](./frontend/CLAUDE.md)** - Frontend implementation guide

## 🔬 Detection System

### Built-in Detection Capabilities

**Deterministic Rules**:
- C2 Beaconing Detection (periodic connections)
- Data Exfiltration (high outbound volume)
- Port Scanning (SYN scan patterns)
- DDoS/Flooding (high packet rates)
- DNS Tunneling (suspicious DNS patterns)
- Persistent Connections (long-lived low-bandwidth)
- Asymmetric Traffic (highly unidirectional)
- Burst Transfers (unusual burst patterns)

**Statistical Analysis**:
- Normal behavior profiling
- Z-score anomaly detection
- Feature-level deviation analysis
- Incremental baseline updates

### Example Usage

```python
from api.detection.pipeline import DetectionPipeline

# Create detection pipeline
pipeline = DetectionPipeline(
    capture_source="traffic.pcap",
    deterministic_rules_path="rules.json",
    statistical_baseline_path="baseline.json",
    enable_logging=True
)

# Run detection
for decision in pipeline.run():
    if decision.threat_level != "benign":
        print(f"ALERT: {decision.explanation}")
        print(f"Confidence: {decision.confidence:.2%}")

# Get evaluation report
report = pipeline.get_evaluation_report()
print(f"Precision: {report['metrics']['precision']:.2%}")
print(f"Recall: {report['metrics']['recall']:.2%}")
```

See [example_detection.py](./services/api/example_detection.py) for more examples.

## 🔐 Authentication

SignalForge uses JWT-based authentication with role-based access control:

**Roles**:
- `admin` - Full system access
- `analyst` - Detection and analysis access
- `viewer` - Read-only access

**Register a new user**:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst1&email=analyst1@example.com&password=secure123&role=analyst"
```

**Login**:
```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst1&password=secure123"
```

## 📡 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login and get JWT token
- `GET /auth/me` - Get current user info

### Detection
- `POST /detection/upload-pcap` - Upload PCAP file
- `POST /detection/analyze` - Run detection analysis
- `POST /detection/train-statistical` - Train statistical detector
- `POST /detection/parse-dataset` - Parse research dataset
- `GET /detection/rules` - List detection rules

### Monitoring
- `GET /flows` - List network flows
- `GET /alerts` - List security alerts
- `GET /detections` - List detections
- `GET /baselines` - List statistical baselines
- `GET /metrics` - System metrics
- `GET /reports` - Detection reports

## 🧪 Research & Evaluation

### Dataset Support

SignalForge includes parsers for standard research datasets:

- **CICIDS2017/2018**: CSV format with extensive flow features
- **CTU-13**: Binetflow NetFlow format
- **UNSW-NB15**: CSV with attack categories

```python
from api.detection.datasets import create_dataset_parser

parser = create_dataset_parser("cicids")
flows = list(parser.parse("CICIDS2017.csv"))
ground_truth = parser.get_ground_truth("CICIDS2017.csv")
```

### Evaluation Metrics

The system provides comprehensive evaluation:

- **Detection Metrics**: Precision, Recall, F1-Score, Accuracy
- **Performance Metrics**: Processing time, Throughput (flows/sec)
- **Confusion Matrix**: TP, FP, TN, FN
- **Per-Module Timing**: Breakdown of pipeline stages

## 🏗️ Project Structure

```
SignalForge/
├── services/
│   └── api/
│       └── api/
│           ├── detection/          # Detection system modules
│           │   ├── capture.py      # Traffic capture (PCAP/live)
│           │   ├── flow.py         # Flow construction
│           │   ├── features.py     # Feature extraction
│           │   ├── deterministic.py # Rule-based detection
│           │   ├── statistical.py  # Anomaly detection
│           │   ├── fusion.py       # Decision fusion
│           │   ├── logging.py      # Structured logging
│           │   ├── evaluation.py   # Metrics & evaluation
│           │   ├── datasets.py     # Dataset parsers
│           │   └── pipeline.py     # End-to-end orchestrator
│           ├── app.py              # FastAPI application
│           └── detection_endpoints.py # Detection REST API
├── frontend/                       # Svelte frontend
├── docs/                          # Documentation & diagrams
├── deploy/                        # Docker deployment configs
└── README.md                      # This file
```

## 🔧 Development

### Backend Development

```bash
cd services/api
uv sync                    # Install dependencies
uv run pytest             # Run tests
uv run ruff check .       # Lint code
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev               # Development server
npm run build            # Production build
```

## 📊 Performance

Typical performance characteristics (on modern hardware):

- **Processing Speed**: 400-500 flows/second
- **Average Latency**: 2-3 ms per flow
- **Memory Usage**: ~100 MB for 10,000 active flows
- **Scalability**: Tested up to 1M flows in batch mode

## 🎓 Academic Use

This system is designed for research and academic evaluation:

- **SRS Compliance**: Formal Software Requirements Specification
- **Methodology Mapping**: Direct mapping to research methodology
- **Reproducible**: Deterministic behavior under identical inputs
- **Explainable**: Traceable decision paths for analysis

## 🤝 Contributing

This is a research project. For collaboration or questions:

1. Review the [DETECTION_SYSTEM.md](./DETECTION_SYSTEM.md) documentation
2. Check the formal SRS document
3. Examine the codebase with inline documentation

## 📝 License

This project is for academic and research purposes.

## 🙏 Acknowledgments

- Built using FastAPI, Scapy, Svelte
- Inspired by CICIDS, CTU-13, and UNSW-NB15 research
- Implements hybrid detection methodology from network security research

---

**Note**: This is a research platform, not a production security product. Use appropriate security tools for production environments.
