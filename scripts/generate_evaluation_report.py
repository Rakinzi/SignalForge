#!/usr/bin/env python3
"""
Generate evaluation report from SignalForge detection results.

Usage:
    python scripts/generate_evaluation_report.py --database-url postgresql://... --output report.md

This script queries the evaluations table and formats results for the baseline report.
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from sqlalchemy import create_engine, select, Table, MetaData, Column, String, Integer, DateTime, Float, Text
except ImportError:
    print("Error: SQLAlchemy not installed. Run: pip install sqlalchemy psycopg", file=sys.stderr)
    sys.exit(1)


def get_latest_evaluation(database_url: str) -> Optional[Dict[str, Any]]:
    """Fetch the most recent evaluation from the database."""
    engine = create_engine(database_url, pool_pre_ping=True)
    metadata = MetaData()

    evaluations = Table(
        "evaluations",
        metadata,
        Column("id", String, primary_key=True),
        Column("created_at", DateTime, nullable=False),
        Column("flow_count", Integer, nullable=False),
        Column("alert_count", Integer, nullable=False),
        Column("high_severity", Integer, nullable=False),
        Column("notes", Text, nullable=False),
    )

    with engine.begin() as conn:
        result = conn.execute(
            select(evaluations).order_by(evaluations.c.created_at.desc()).limit(1)
        ).mappings().first()

    if not result:
        return None

    return dict(result)


def parse_evaluation_notes(notes_str: str) -> Dict[str, Any]:
    """Parse the JSON notes field from evaluation record."""
    try:
        return json.loads(notes_str)
    except json.JSONDecodeError:
        return {}


def format_confusion_matrix(confusion: Dict[str, int]) -> str:
    """Format confusion matrix as markdown table."""
    tp = confusion.get("true_positives", 0)
    fp = confusion.get("false_positives", 0)
    tn = confusion.get("true_negatives", 0)
    fn = confusion.get("false_negatives", 0)

    return f"""
### Confusion Matrix

|  | **Predicted Benign** | **Predicted Malicious** | **Total** |
|---|---|---|---|
| **Actual Benign** | {tn:,} (TN) | {fp:,} (FP) | {tn + fp:,} |
| **Actual Malicious** | {fn:,} (FN) | {tp:,} (TP) | {fn + tp:,} |
| **Total** | {tn + fn:,} | {tp + fp:,} | **{tp + fp + tn + fn:,}** |

**Interpretation**:
- **True Negatives ({tn:,})**: Benign traffic correctly identified
- **True Positives ({tp:,})**: Attacks correctly detected
- **False Positives ({fp:,})**: Benign traffic incorrectly flagged ({100 * fp / max(fp + tn, 1):.1f}% FPR)
- **False Negatives ({fn:,})**: Attacks missed ({100 * fn / max(fn + tp, 1):.1f}% FNR)
"""


def format_metrics(metrics: Dict[str, float]) -> str:
    """Format detection metrics as markdown table."""
    precision = metrics.get("precision", 0)
    recall = metrics.get("recall", 0)
    f1 = metrics.get("f1_score", 0)
    accuracy = metrics.get("accuracy", 0)
    fpr = metrics.get("false_positive_rate", 0)
    fnr = metrics.get("false_negative_rate", 0)

    return f"""
### Detection Metrics

| Metric | Formula | Value | Interpretation |
|--------|---------|-------|----------------|
| **Precision** | TP / (TP + FP) | {precision * 100:.1f}% | {precision * 100:.1f}% of alerts are true threats |
| **Recall** | TP / (TP + FN) | {recall * 100:.1f}% | {recall * 100:.1f}% of attacks are detected |
| **F1-Score** | 2 × (P × R) / (P + R) | {f1 * 100:.1f}% | Balanced detection performance |
| **Accuracy** | (TP + TN) / Total | {accuracy * 100:.1f}% | Overall correctness |
| **FPR** | FP / (FP + TN) | {fpr * 100:.2f}% | False alarm rate |
| **FNR** | FN / (FN + TP) | {fnr * 100:.2f}% | Miss rate |

**Benchmark Comparison**:
- Target F1 for research systems: >92% {"✅" if f1 >= 0.92 else "❌"}
- Target Precision: >95% {"✅" if precision >= 0.95 else "❌"}
- Target Recall: >90% {"✅" if recall >= 0.90 else "❌"}
"""


def generate_report(database_url: str, output_path: Optional[str] = None) -> str:
    """Generate evaluation report from database."""
    print("Fetching latest evaluation from database...", file=sys.stderr)
    evaluation = get_latest_evaluation(database_url)

    if not evaluation:
        print("Error: No evaluation data found in database", file=sys.stderr)
        sys.exit(1)

    print(f"Found evaluation from {evaluation['created_at']}", file=sys.stderr)

    notes = parse_evaluation_notes(evaluation["notes"])
    confusion = notes.get("confusion_matrix", {})
    metrics = notes.get("metrics", {})

    if not confusion or not metrics:
        print("Error: Evaluation data missing confusion matrix or metrics", file=sys.stderr)
        print(f"Notes content: {notes}", file=sys.stderr)
        sys.exit(1)

    report = f"""# Evaluation Results

**Generated**: {datetime.now().isoformat()}
**Evaluation Date**: {evaluation['created_at']}
**Total Flows**: {evaluation['flow_count']:,}
**Total Alerts**: {evaluation['alert_count']:,}
**High Severity Alerts**: {evaluation['high_severity']:,}

---

## Results Summary

- **F1-Score**: {metrics.get('f1_score', 0) * 100:.1f}%
- **Precision**: {metrics.get('precision', 0) * 100:.1f}%
- **Recall**: {metrics.get('recall', 0) * 100:.1f}%
- **Accuracy**: {metrics.get('accuracy', 0) * 100:.1f}%

---

{format_confusion_matrix(confusion)}

---

{format_metrics(metrics)}

---

## Dataset Information

- **Labeled Flows**: {notes.get('labeled_flows', 0):,}
- **Unlabeled Flows**: {notes.get('unlabeled_flows', 0):,}
- **Evaluation Threshold**: {notes.get('eval_malicious_threshold', 0.5)}

---

## Next Steps

1. Copy this report to `docs/EVALUATION_BASELINE.md`
2. Add dataset description (name, source, attack types)
3. Add configuration details (commit SHA, parameter values)
4. Add performance metrics (throughput, latency, memory)
5. Add error analysis (FP/FN examples)
6. Add discussion and comparison with related work

Use the template in `docs/EVALUATION_BASELINE_TEMPLATE.md` as a guide.
"""

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report written to {output_path}", file=sys.stderr)
    else:
        print(report)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate evaluation report from SignalForge database"
    )
    parser.add_argument(
        "--database-url",
        required=True,
        help="PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/dbname)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args()

    try:
        generate_report(args.database_url, args.output)
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
