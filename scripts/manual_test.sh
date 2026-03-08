#!/usr/bin/env bash
set -euo pipefail

# Manual test script for Typer CLI
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

echo "CLI help:"
uv run python -m scripts.invoice --help >/dev/null

echo "Listing existing clients:"
uv run python -m scripts.invoice clients

echo ""
echo "Listing existing invoices:"
uv run python -m scripts.invoice list

echo ""
echo "Validating example invoice JSON:"
uv run python -m scripts.invoice json validate --invoice invoices/invoice.example.json

echo ""
echo "Generating invoice PDF from JSON file:"
uv run python -m scripts.invoice pdf from-json \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output "${base}_from_json.pdf"
assert_file "${base}_from_json.pdf"

echo ""
echo "Generating invoice PDF using deprecated alias generate (compat):"
uv run python -m scripts.invoice generate \
  --invoice invoices/invoice.example.json \
  --client clients/client.example.json \
  --output "${base}_generate_alias.pdf"
assert_file "${base}_generate_alias.pdf"
