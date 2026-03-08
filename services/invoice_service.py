import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from core.errors import InvalidInputError, RenderError, ValidationError
from core.loader import load_json
from core.renderer import render_invoice_data
from core.validate import ValidationError as CoreValidationError
from core.validate import validate_invoice_data


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def _make_invoice_filename(number: str) -> str:
    safe = _sanitize_filename(number)
    return f"invoice_{safe}.json"


def _make_output_filename(number: str) -> str:
    safe = _sanitize_filename(number)
    return f"invoice_{safe}.pdf"


def _load_json_file(path: Path, label: str) -> dict:
    try:
        data = load_json(path)
    except FileNotFoundError:
        raise CoreValidationError(label, "<fichier>", "introuvable") from None
    except json.JSONDecodeError:
        raise CoreValidationError(label, "<fichier>", "JSON invalide") from None

    if not isinstance(data, dict):
        raise CoreValidationError(label, "<racine>", "mauvais type (objet JSON attendu)")

    return data


def _generate_invoice_number(invoices_dir: Path) -> str:
    year = datetime.now().strftime("%Y")
    pattern = re.compile(r"INV-(\d{4})-(\d{4})")
    max_index = 0
    for path in sorted(invoices_dir.glob("*.json")):
        try:
            data = _load_json_file(path, path.as_posix())
        except CoreValidationError:
            continue
        number = data.get("number")
        if not isinstance(number, str):
            continue
        match = pattern.fullmatch(number.strip())
        if not match:
            continue
        if match.group(1) != year:
            continue
        max_index = max(max_index, int(match.group(2)))
    return f"INV-{year}-{max_index + 1:04d}"


def _validated_invoice_data(invoice_data: dict, invoice_label: str, invoices_dir: Path) -> dict:
    if not isinstance(invoice_data, dict):
        raise ValidationError(
            str(
                CoreValidationError(
                    invoice_label,
                    "<racine>",
                    "mauvais type (objet JSON attendu)",
                )
            )
        )

    candidate = deepcopy(invoice_data)
    if not candidate.get("number"):
        candidate["number"] = _generate_invoice_number(invoices_dir)

    try:
        validate_invoice_data(candidate, invoice_label)
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None

    return candidate


def _check_target_path(path: Path, label: str, force: bool) -> None:
    if path.exists() and not force:
        raise InvalidInputError(
            f"Erreur: {label} existe deja: {path}. Utilisez --force pour ecraser."
        )


def load_invoice_from_path(path: Path) -> dict:
    try:
        return _load_json_file(path, path.as_posix())
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None


def parse_invoice_json(raw: str, label: str) -> dict:
    content = raw.strip()
    if not content:
        raise InvalidInputError("Erreur: stdin vide, aucun JSON recu.")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValidationError(
            str(CoreValidationError(label, "<fichier>", "JSON invalide"))
        ) from None
    if not isinstance(data, dict):
        raise ValidationError(
            str(CoreValidationError(label, "<racine>", "mauvais type (objet JSON attendu)"))
        ) from None
    return data


def list_invoices(invoices_dir: Path) -> dict:
    entries = []
    for path in sorted(invoices_dir.glob("*.json")):
        try:
            data = _load_json_file(path, path.as_posix())
            invoice = validate_invoice_data(data, path.as_posix())
            number = invoice.number
            issue_date = invoice.issue_date
            status = "ok"
        except CoreValidationError as exc:
            number = "-"
            issue_date = "-"
            status = f"invalide: {exc}"
        entries.append(
            {
                "filename": path.name,
                "number": number,
                "issue_date": issue_date,
                "status": status,
            }
        )
    return {"entries": entries}


def validate_invoice_file(invoice_path: Path, invoices_dir: Path) -> dict:
    try:
        raw = _load_json_file(invoice_path, invoice_path.as_posix())
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None

    validated = _validated_invoice_data(raw, invoice_path.as_posix(), invoices_dir)
    return {
        "invoice_number": validated["number"],
        "invoice_data": validated,
        "invoice_label": invoice_path.as_posix(),
    }


def create_invoice(
    *,
    invoice_data: dict,
    invoice_label: str,
    invoices_dir: Path,
    force: bool,
) -> dict:
    validated = _validated_invoice_data(invoice_data, invoice_label, invoices_dir)
    invoice_path = invoices_dir / _make_invoice_filename(validated["number"])

    _check_target_path(invoice_path, "le fichier JSON", force)

    invoices_dir.mkdir(parents=True, exist_ok=True)
    with open(invoice_path, "w", encoding="utf-8") as f:
        json.dump(validated, f, indent=4, ensure_ascii=False)

    return {
        "invoice_path": str(invoice_path),
        "invoice_number": validated["number"],
        "invoice_data": validated,
        "warnings": [],
    }


def generate_invoice(
    *,
    invoice_data: dict,
    invoice_label: str,
    client_data: dict,
    client_label: str,
    output_path: Path | None,
    base_dir: Path,
    invoices_dir: Path,
    output_dir: Path,
    force: bool,
) -> dict:
    validated = _validated_invoice_data(invoice_data, invoice_label, invoices_dir)

    resolved_output = output_path
    if resolved_output is None:
        resolved_output = output_dir / _make_output_filename(validated["number"])
    if not resolved_output.is_absolute():
        resolved_output = base_dir / resolved_output

    _check_target_path(resolved_output, "le PDF", force)

    try:
        render_invoice_data(
            invoice_data=validated,
            client_data=client_data,
            output_pdf_path=resolved_output,
            base_dir=base_dir,
            invoice_label=invoice_label,
            client_label=client_label,
        )
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None
    except Exception as exc:
        raise RenderError(str(exc) or "Erreur inconnue lors du rendu du PDF.") from None

    return {
        "output_pdf": str(resolved_output),
        "invoice_number": validated["number"],
        "invoice_label": invoice_label,
        "warnings": [],
    }
