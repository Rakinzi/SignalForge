#!/usr/bin/env python3
"""
Example: Running the Hybrid Detection Pipeline

This script demonstrates how to use the complete detection system.
"""

from api.detection.pipeline import DetectionPipeline
from api.detection.fusion import ThreatLevel


def main():
    print("=" * 70)
    print("SignalForge - Hybrid Malware Detection System")
    print("=" * 70)
    print()

    # Example 1: Analyze a PCAP file
    print("[Example 1] Analyzing PCAP file...")
    print("-" * 70)

    # NOTE: Replace with actual PCAP file path
    pcap_file = "example_traffic.pcap"

    try:
        pipeline = DetectionPipeline(
            capture_source=pcap_file,
            enable_logging=True,
            enable_evaluation=True,
        )

        # Run detection
        threat_counts = {level.value: 0 for level in ThreatLevel}
        critical_alerts = []

        for decision in pipeline.run():
            threat_counts[decision.threat_level.value] += 1

            # Collect critical alerts
            if decision.threat_level == ThreatLevel.CRITICAL:
                critical_alerts.append(decision)

            # Print high-severity alerts
            if decision.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                print(f"\n⚠️  ALERT: {decision.threat_level.value.upper()}")
                print(f"   Flow: {decision.flow_id}")
                print(f"   Confidence: {decision.confidence:.1%}")
                print(f"   Explanation: {decision.explanation}")

        # Print summary
        print("\n" + "=" * 70)
        print("Detection Summary:")
        print("-" * 70)
        for level, count in threat_counts.items():
            symbol = "✓" if level == "benign" else ("⚠️" if count > 0 else "○")
            print(f"  {symbol} {level.upper():<12} {count:>6} flows")

        # Print evaluation metrics
        report = pipeline.get_evaluation_report()
        print("\n" + "-" * 70)
        print("Performance Metrics:")
        print("-" * 70)
        perf = report["performance"]
        print(f"  Flows Processed: {pipeline.flows_processed}")
        print(f"  Avg Time/Flow:   {perf['avg_processing_time_ms']:.2f} ms")
        print(f"  Throughput:      {perf['throughput_flows_per_second']:.1f} flows/sec")

        if "metrics" in report:
            print("\n" + "-" * 70)
            print("Detection Accuracy (with ground truth):")
            print("-" * 70)
            metrics = report["metrics"]
            print(f"  Precision:  {metrics['precision']:.2%}")
            print(f"  Recall:     {metrics['recall']:.2%}")
            print(f"  F1-Score:   {metrics['f1_score']:.2%}")
            print(f"  Accuracy:   {metrics['accuracy']:.2%}")

        print("\n" + "=" * 70)
        print("Analysis complete!")
        print("=" * 70)

    except FileNotFoundError:
        print(f"❌ Error: PCAP file not found: {pcap_file}")
        print("\nTo run this example:")
        print("  1. Place a PCAP file in the current directory")
        print("  2. Update 'pcap_file' variable in this script")
        print("  3. Run: python example_detection.py")
        print("\nAlternatively, use the API endpoints:")
        print("  POST /detection/upload-pcap")
        print("  POST /detection/analyze")


    # Example 2: Training statistical detector
    print("\n\n[Example 2] Training Statistical Detector")
    print("-" * 70)
    print("To train the statistical detector on benign traffic:")
    print()
    print("  from api.detection.pipeline import DetectionPipeline")
    print()
    print("  pipeline = DetectionPipeline(capture_source='benign.pcap')")
    print("  pipeline.train_statistical_detector('benign.pcap')")
    print("  pipeline.statistical_detector.save_baseline('baseline.json')")
    print()
    print("Then use the baseline in detection:")
    print()
    print("  pipeline = DetectionPipeline(")
    print("      capture_source='test.pcap',")
    print("      statistical_baseline_path='baseline.json'")
    print("  )")


    # Example 3: Custom rules
    print("\n\n[Example 3] Adding Custom Detection Rules")
    print("-" * 70)
    print("You can add custom behavioral rules:")
    print()
    print("  from api.detection.deterministic import Rule")
    print()
    print("  custom_rule = Rule(")
    print("      rule_id='R999',")
    print("      name='High Volume Upload',")
    print("      severity='critical',")
    print("      category='exfiltration',")
    print("      conditions=[")
    print("          {'field': 'fwd_bwd_byte_ratio', 'operator': 'gt', 'value': 50},")
    print("          {'field': 'byte_rate', 'operator': 'gt', 'value': 1000000}")
    print("      ]")
    print("  )")
    print()
    print("  detector.add_rule(custom_rule)")


if __name__ == "__main__":
    main()
