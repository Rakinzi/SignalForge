#!/usr/bin/env python
"""
Generate sequence diagram PNG from PlantUML file.
Requires: pip install plantuml
"""
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    script_dir = Path(__file__).parent
    plantuml_file = script_dir / "sequence.puml"
    output_file = script_dir / "sequence.png"

    if not plantuml_file.exists():
        print(f"Error: {plantuml_file} not found", file=sys.stderr)
        sys.exit(1)

    # Try using plantuml Python package
    try:
        from plantuml import PlantUML

        # Use public PlantUML server
        plantuml = PlantUML(url="http://www.plantuml.com/plantuml/img/")

        with open(plantuml_file, "r") as f:
            plantuml_code = f.read()

        # Generate PNG
        print(f"Generating sequence diagram from {plantuml_file}...")
        result = plantuml.processes(plantuml_code)

        with open(output_file, "wb") as f:
            f.write(result)

        print(f"✓ Sequence diagram generated: {output_file}")
        return

    except ImportError:
        print("plantuml package not found, trying plantuml jar...")

    # Fallback: try plantuml.jar
    try:
        result = subprocess.run(
            ["java", "-jar", "plantuml.jar", "-tpng", str(plantuml_file)],
            capture_output=True,
            text=True,
            cwd=script_dir,
        )

        if result.returncode == 0:
            print(f"✓ Sequence diagram generated: {output_file}")
            return
        else:
            print(f"Error: {result.stderr}", file=sys.stderr)

    except FileNotFoundError:
        pass

    # Fallback: use online plantuml service via curl
    print("Attempting to use PlantUML web service...")
    try:
        import base64
        import zlib
        import requests

        with open(plantuml_file, "r") as f:
            plantuml_code = f.read()

        # Encode for PlantUML server
        compressed = zlib.compress(plantuml_code.encode("utf-8"))
        encoded = base64.b64encode(compressed).decode("ascii")

        url = f"http://www.plantuml.com/plantuml/png/{encoded}"

        response = requests.get(url)
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            print(f"✓ Sequence diagram generated: {output_file}")
            return

    except Exception as e:
        print(f"Error using web service: {e}", file=sys.stderr)

    print("\nFailed to generate sequence diagram. Please install one of:", file=sys.stderr)
    print("  1. pip install plantuml", file=sys.stderr)
    print("  2. Download plantuml.jar from https://plantuml.com/download", file=sys.stderr)
    print("  3. Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
