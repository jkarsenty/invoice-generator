#!/usr/bin/env bash
set -euo pipefail

# Manual test script for CLI (Phase 0)
# Creates PDFs in output/ with a timestamp to avoid collisions.

stamp=$(date +%Y%m%d%H%M%S)
base="output/manual_test_${stamp}"

echo "Listing existing clients:"
uv run python -m scripts.invoice clients

echo "Listing existing invoices:"
uv run python -m scripts.invoice list

echo "Generating invoice PDFs from invoice file and client file:"
uv run python -m scripts.invoice generate \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output "${base}_generate.pdf"

echo "Generating invoice PDF from stdin input:"
cat invoices/invoice.example.json | uv run python -m scripts.invoice generate \
  --stdin \
  --client clients/client.example.json \
  --output "${base}_stdin.pdf"

echo "Generating invoice PDF using legacy command (old version):"
uv run python -m scripts.generate_invoice \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output "${base}_legacy.pdf"

# Optional interactive flow:
# echo "Starting interactive invoice creation..."
# uv run python -m scripts.invoice new


