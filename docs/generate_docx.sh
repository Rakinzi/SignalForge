#!/bin/bash
#
# Generate DOCX documentation from Markdown with embedded diagrams
# Requires: pandoc (install via: brew install pandoc)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_DIR="$SCRIPT_DIR"
DIAGRAMS_DIR="$DOCS_DIR/diagrams"
OUTPUT_FILE="$DOCS_DIR/SignalForge_Platform_Documentation.docx"
MARKDOWN_FILE="$DOCS_DIR/Network_Detection_Platform.md"

echo "=========================================="
echo "SignalForge Documentation Generator"
echo "=========================================="
echo

# Check if pandoc is installed
if ! command -v pandoc &> /dev/null; then
    echo "Error: pandoc is not installed"
    echo "Install with: brew install pandoc (macOS) or apt-get install pandoc (Linux)"
    exit 1
fi

echo "✓ pandoc found: $(pandoc --version | head -n1)"
echo

# Check if markdown file exists
if [ ! -f "$MARKDOWN_FILE" ]; then
    echo "Error: Markdown file not found: $MARKDOWN_FILE"
    exit 1
fi

echo "Input:  $MARKDOWN_FILE"
echo "Output: $OUTPUT_FILE"
echo

# Convert markdown to docx with high-quality images
echo "Converting to DOCX..."
pandoc "$MARKDOWN_FILE" \
    --from markdown \
    --to docx \
    --output "$OUTPUT_FILE" \
    --dpi=300 \
    --standalone \
    --toc \
    --toc-depth=3 \
    --number-sections \
    --highlight-style=tango \
    --metadata title="SignalForge Platform Documentation" \
    --metadata author="SignalForge Team" \
    --metadata date="$(date '+%Y-%m-%d')" \
    --resource-path="$DOCS_DIR:$DIAGRAMS_DIR"

if [ $? -eq 0 ]; then
    echo
    echo "=========================================="
    echo "✓ Documentation generated successfully!"
    echo "=========================================="
    echo "Output: $OUTPUT_FILE"
    echo "Size:   $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo
else
    echo "✗ Error generating documentation"
    exit 1
fi
