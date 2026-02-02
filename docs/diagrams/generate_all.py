#!/usr/bin/env python
"""Generate all SignalForge diagrams."""
import os
import subprocess
import sys

SCRIPTS = [
    "generate_system_context.py",
    "generate_component_architecture.py",
    "generate_dfd.py",
    "generate_deployment.py",
    "generate_threat_boundaries.py",
    "generate_sequence_plantuml.py",  # PlantUML sequence diagram
]


def main() -> None:
    print("=" * 60)
    print("Generating all SignalForge diagrams...")
    print("=" * 60)

    base = os.path.dirname(__file__)
    for script in SCRIPTS:
        script_name = script.replace("generate_", "").replace(".py", "").replace("_", " ").title()
        print(f"\n[{script_name}] Generating...")

        path = os.path.join(base, script)
        result = subprocess.run([sys.executable, path], check=False, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[{script_name}] ✗ Error")
            if result.stderr:
                print(result.stderr, file=sys.stderr)
        else:
            print(f"[{script_name}] ✓ Complete")
            if result.stdout and "✓" in result.stdout:
                print(result.stdout.strip())

    print("\n" + "=" * 60)
    print("All diagrams generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
