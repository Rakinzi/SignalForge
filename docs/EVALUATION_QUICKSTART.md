# Evaluation Quick Start Guide

**Purpose**: Run baseline evaluation on standard dataset for Chapter 4 results

---

## Prerequisites

1. **Dataset**: Download CICIDS2017 or CTU-13
   - CICIDS2017: https://www.unb.ca/cic/datasets/ids-2017.html
   - CTU-13: https://www.stratosphereips.org/datasets-ctu13

2. **System Running**: API and detector services operational

3. **Configuration**: `config/detector_config.json` set up

4. **Default Protocol**: Cross-dataset holdout (research default)
   - Train baseline on benign-heavy subset from Dataset A
   - Tune thresholds on Dataset B
   - Test on disjoint scenarios from Dataset C/D

---

## Quick Evaluation (CLI)

### Option 1: Using Detection Pipeline

```bash
cd services/api

# Set configuration
export DETECTOR_CONFIG_PATH=/path/to/detector_config.json

# Run detection on dataset
python -m api.detection.pipeline \
  --dataset /path/to/CICIDS2017.csv \
  --dataset-type cicids \
  --output-report evaluation_results.json

# Extract metrics
cat evaluation_results.json | jq '.metrics'
```

### Option 2: Using API Endpoints

```bash
# 1. Upload dataset
curl -X POST http://localhost:8000/detection/parse-dataset \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@CICIDS2017.csv" \
  -F "dataset_type=cicids"

# 2. Wait for processing (monitor logs)
tail -f /path/to/detector.log

# 3. Get evaluation metrics
curl -X GET http://localhost:8000/reports \
  -H "Authorization: Bearer $TOKEN" | jq '.evaluation_metrics'
```

---

## Understanding Evaluation Output

### Confusion Matrix

```json
{
  "confusion_matrix": {
    "true_positives": 1234,   // Correctly detected attacks
    "false_positives": 56,     // Benign flows flagged as malicious
    "true_negatives": 8765,    // Correctly identified benign
    "false_negatives": 43      // Missed attacks
  }
}
```

### Metrics

```json
{
  "metrics": {
    "precision": 0.9565,      // TP / (TP + FP) - accuracy of alerts
    "recall": 0.9663,          // TP / (TP + FN) - attack detection rate
    "f1_score": 0.9614,        // Harmonic mean of precision & recall
    "accuracy": 0.9901,        // (TP + TN) / total
    "false_positive_rate": 0.0063,  // FP / (FP + TN)
    "false_negative_rate": 0.0337   // FN / (FN + TP)
  }
}
```

### Protocol + Provenance (Required for reproducibility)

```json
{
  "protocol": {
    "split_strategy": "cross-dataset-holdout",
    "train_set": "dataset-a-benign",
    "validation_set": "dataset-b-tuning",
    "test_sets": ["dataset-c-main-test", "dataset-d-robustness"]
  },
  "provenance": {
    "dataset_hash": "sha256...",
    "config_hash": "sha256...",
    "commit_sha": "abc1234",
    "run_timestamp": "2026-02-26T12:34:56Z"
  }
}
```

---

## Expected Results (Reference)

Based on similar research-grade systems on CICIDS2017:

| Metric | Expected Range | Target |
|--------|----------------|--------|
| Precision | 90-98% | >95% |
| Recall | 85-95% | >90% |
| F1-Score | 87-96% | >92% |
| Accuracy | 95-99% | >97% |
| FPR | 1-5% | <3% |

**Notes**:
- Higher precision = fewer false alarms
- Higher recall = fewer missed attacks
- F1-Score balances both
- Your results will vary based on:
  - Dataset composition (% malicious)
  - Configuration tuning
  - Rule coverage

---

## Interpretation for Report

### Good Results (F1 > 92%)
"The hybrid detection system achieved X% precision and Y% recall on CICIDS2017,
demonstrating effective malware detection in encrypted traffic. The F1-score
of Z% indicates balanced performance between false positive reduction and
attack detection coverage."

### Moderate Results (F1 = 85-92%)
"The system achieved X% F1-score on CICIDS2017. Precision of Y% indicates
low false alarm rate, while recall of Z% suggests room for improvement in
novel attack detection. Future work will explore [additional features/rules]."

### Lower Results (F1 < 85%)
"Initial evaluation yielded X% F1-score. Analysis revealed [false positives
from benign P2P traffic / false negatives from slow exfiltration]. Tuning
[parameter Y] and adding [rule Z] are expected to improve performance."

---

## Performance Metrics

Also collect system performance:

```bash
# Monitor during evaluation
docker stats

# Or query metrics API
curl -X GET http://localhost:8000/metrics \
  -H "Authorization: Bearer $TOKEN"
```

Expected output:
```json
{
  "flows_per_second": 450,
  "packets_per_second": 12000,
  "latency_ms": 2.3,
  "uptime_seconds": 3600
}
```

**Report these as**:
- "Processing throughput: 450 flows/sec"
- "Average detection latency: 2.3 ms per flow"
- "Memory usage: ~100 MB for 10,000 active flows"

---

## Troubleshooting

### Low Recall (<80%)
**Cause**: Missing attacks
**Fix**: Add more rules or lower alert_min_score threshold

### Low Precision (<80%)
**Cause**: Too many false positives
**Fix**: Increase alert_min_score or tighten rule conditions

### Imbalanced Dataset
**Cause**: 99% benign traffic inflates accuracy
**Fix**: Report precision/recall/F1 separately, don't rely on accuracy alone

### Missing Provenance Block
**Cause**: Run was executed outside standard pipeline path
**Fix**: Re-run with DetectionPipeline and verify `protocol` and `provenance` exist in report JSON

### No Ground Truth Labels
**Cause**: Dataset missing "Label" or "is_malicious" column
**Fix**: Verify dataset format matches parser expectations

---

## Creating Evaluation Report

Use this template for `docs/EVALUATION_BASELINE.md`:

```markdown
# Baseline Evaluation Report

## Dataset
- **Name**: CICIDS2017 (Monday subset)
- **Size**: 10,000 flows (8,500 benign, 1,500 malicious)
- **Attack Types**: Port scan, DDoS, botnet, infiltration

## Configuration
- **File**: config/detector_config.json (commit SHA: abc123)
- **Parameters**:
  - det_weight = 0.6, stat_weight = 0.4
  - z_score_divisor = 6.0
  - alert_min_score = 0.5
  - Rules: 9 enabled (all)

## Results

### Confusion Matrix
| | Predicted Benign | Predicted Malicious |
|---|---|---|
| **Actual Benign** | 8,432 (TN) | 68 (FP) |
| **Actual Malicious** | 45 (FN) | 1,455 (TP) |

### Metrics
- **Precision**: 95.5% (1455 / (1455 + 68))
- **Recall**: 97.0% (1455 / (1455 + 45))
- **F1-Score**: 96.2%
- **Accuracy**: 99.0% ((1455 + 8432) / 10000)
- **FPR**: 0.8% (68 / (68 + 8432))
- **FNR**: 3.0% (45 / (45 + 1455))

### Performance
- **Throughput**: 450 flows/sec
- **Latency**: 2.3 ms/flow average
- **Memory**: 98 MB peak
- **Duration**: 22.2 seconds for 10,000 flows

## Analysis

### Strengths
- High precision (95.5%) indicates low false alarm rate
- High recall (97.0%) demonstrates effective attack detection
- Balanced F1-score (96.2%) shows hybrid approach effectiveness

### Weaknesses
- 45 false negatives: Missed [attack types]
- 68 false positives: Benign [traffic patterns] flagged

### Rule Effectiveness
| Rule | Triggers | True Positives | False Positives |
|------|----------|----------------|-----------------|
| c2_beaconing | 234 | 228 | 6 |
| port_scan | 456 | 450 | 6 |
| dns_tunneling | 123 | 115 | 8 |
| ... | ... | ... | ... |

## Conclusion
The hybrid detection system achieves research-grade performance (F1=96.2%)
on CICIDS2017, validating the cascaded architecture and rule-statistical
fusion approach.
```

---

## For Your Report

Copy the completed `docs/EVALUATION_BASELINE.md` content into **Chapter 4: Evaluation**.

Include:
1. Table: Confusion matrix
2. Table: Metrics (Precision, Recall, F1, Accuracy)
3. Table: Per-rule effectiveness
4. Figure: Precision-Recall curve (optional)
5. Discussion: Strengths, weaknesses, comparison to baseline

---

**Next Step**: Run evaluation on your chosen dataset and fill in the template.
