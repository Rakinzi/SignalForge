#!/usr/bin/env python
"""
Generate DOCX documentation from Markdown with embedded diagrams.
Requires: pandoc (install via: brew install pandoc)
"""
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


def check_pandoc() -> bool:
    """Check if pandoc is installed."""
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.split('\n')[0]
        print(f"✓ pandoc found: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_file_size(filepath: Path) -> str:
    """Get human-readable file size."""
    size = filepath.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def main() -> None:
    print("=" * 60)
    print("SignalForge Documentation Generator")
    print("=" * 60)
    print()

    # Paths
    docs_dir = Path(__file__).parent
    diagrams_dir = docs_dir / "diagrams"
    markdown_file = docs_dir / "Network_Detection_Platform.md"
    output_file = docs_dir / "SignalForge_Platform_Documentation.docx"

    # Check pandoc
    if not check_pandoc():
        print("\n✗ Error: pandoc is not installed", file=sys.stderr)
        print("Install with:", file=sys.stderr)
        print("  macOS:  brew install pandoc", file=sys.stderr)
        print("  Linux:  apt-get install pandoc", file=sys.stderr)
        print("  Windows: choco install pandoc", file=sys.stderr)
        print("Or download from: https://pandoc.org/installing.html", file=sys.stderr)
        sys.exit(1)

    print()

    # Check markdown file
    if not markdown_file.exists():
        print(f"✗ Error: Markdown file not found: {markdown_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Input:  {markdown_file}")
    print(f"Output: {output_file}")
    print()

    # Build pandoc command
    cmd = [
        "pandoc",
        str(markdown_file),
        "--from", "markdown",
        "--to", "docx",
        "--output", str(output_file),
        "--dpi=300",  # High-quality images
        "--standalone",
        "--toc",  # Table of contents
        "--toc-depth=3",
        "--number-sections",
        "--highlight-style=tango",
        f"--metadata=title:SignalForge Platform Documentation",
        f"--metadata=author:SignalForge Team",
        f"--metadata=date:{date.today().isoformat()}",
        f"--resource-path={docs_dir}:{diagrams_dir}",
    ]

    # Convert
    print("Converting to DOCX...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout:
            print(result.stdout)

        print()
        print("=" * 60)
        print("✓ Documentation generated successfully!")
        print("=" * 60)
        print(f"Output: {output_file}")
        print(f"Size:   {get_file_size(output_file)}")
        print()

    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error generating documentation", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
