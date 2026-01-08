#!/usr/bin/env bash
set -euo pipefail

# Manual test script for CLI (Phase 0)
# Creates PDFs in output/ with a timestamp to avoid collisions.

stamp=$(date +%Y%m%d%H%M%S)
base="output/manual_test_${stamp}"
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib:${DYLD_FALLBACK_LIBRARY_PATH:-}"

issuer_example="config/issuer.example.json"
issuer_current="config/issuer.json"
issuer_backup=""

restore_issuer() {
  if [[ -n "${issuer_backup}" ]]; then
    mv "${issuer_backup}" "${issuer_current}"
  fi
}

prepare_issuer() {
  if [[ -f "${issuer_current}" ]]; then
    issuer_backup="${issuer_current}.bak_${stamp}"
    cp "${issuer_current}" "${issuer_backup}"
  fi
  cp "${issuer_example}" "${issuer_current}"
}

assert_file() {
  local path="$1"
  if [[ ! -f "${path}" ]]; then
    echo "Missing file: ${path}" >&2
    exit 1
  fi
  if [[ ! -s "${path}" ]]; then
    echo "Empty file: ${path}" >&2
    exit 1
  fi
}

trap restore_issuer EXIT

assert_file "invoices/invoice.example.json"
assert_file "clients/client.example.json"
assert_file "${issuer_example}"
prepare_issuer

echo "Listing existing clients:"
uv run python -m scripts.invoice clients

echo ""
echo "Listing existing invoices:"
uv run python -m scripts.invoice list

echo ""
echo "Generating invoice PDFs from invoice file and client file:"
uv run python -m scripts.invoice generate \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output "${base}_generate.pdf"
assert_file "${base}_generate.pdf"

echo ""
echo "Generating invoice PDF from stdin input:"
cat invoices/invoice.example.json | uv run python -m scripts.invoice generate \
  --stdin \
  --client clients/client.example.json \
  --output "${base}_stdin.pdf"
assert_file "${base}_stdin.pdf"


# Optional interactive flow:
# echo "Starting interactive invoice creation..."
# uv run python -m scripts.invoice new

