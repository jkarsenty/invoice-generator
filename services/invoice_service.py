import json
import re
from datetime import datetime
from pathlib import Path

from core.errors import InvalidInputError, RenderError, ValidationError
from core.loader import load_json
from core.renderer import render_invoice, render_invoice_data
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
    pattern = re.compile(r"INV-(\\d{4})-(\\d{4})")
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


def create_invoice(
    *,
    invoice_data: dict,
    invoice_label: str,
    client_path: Path,
    base_dir: Path,
    invoices_dir: Path,
    output_dir: Path,
    no_pdf: bool,
) -> dict:
    if not invoice_data.get("number"):
        invoice_data["number"] = _generate_invoice_number(invoices_dir)

    try:
        validate_invoice_data(invoice_data, invoice_label)
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None

    invoice_path = invoices_dir / _make_invoice_filename(invoice_data["number"])
    output_path = output_dir / _make_output_filename(invoice_data["number"])

    if invoice_path.exists():
        raise InvalidInputError(f"Erreur: le fichier existe deja: {invoice_path}")
    if not no_pdf and output_path.exists():
        raise InvalidInputError(f"Erreur: le PDF existe deja: {output_path}")

    invoices_dir.mkdir(parents=True, exist_ok=True)
    with open(invoice_path, "w", encoding="utf-8") as f:
        json.dump(invoice_data, f, indent=4, ensure_ascii=False)

    if no_pdf:
        return {
            "invoice_path": str(invoice_path),
            "output_pdf": None,
            "invoice_number": invoice_data["number"],
            "warnings": [],
        }

    if output_path.exists():
        raise InvalidInputError(f"Erreur: le PDF existe deja: {output_path}")

    try:
        render_invoice(
            invoice_path=invoice_path,
            client_path=client_path,
            output_pdf_path=output_path,
            base_dir=base_dir,
        )
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None
    except Exception as exc:
        raise RenderError(str(exc) or "Erreur inconnue lors du rendu du PDF.") from None

    return {
        "invoice_path": str(invoice_path),
        "output_pdf": str(output_path),
        "invoice_number": invoice_data["number"],
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
) -> dict:
    if not isinstance(invoice_data, dict):
        raise ValidationError(
            str(CoreValidationError(invoice_label, "<racine>", "mauvais type (objet JSON attendu)"))
        )

    if not invoice_data.get("number"):
        invoice_data["number"] = _generate_invoice_number(invoices_dir)

    try:
        validate_invoice_data(invoice_data, invoice_label)
    except CoreValidationError as exc:
        raise ValidationError(str(exc)) from None

    resolved_output = output_path
    if resolved_output is None:
        resolved_output = output_dir / _make_output_filename(invoice_data["number"])
    if not resolved_output.is_absolute():
        resolved_output = base_dir / resolved_output

    if resolved_output.exists():
        raise InvalidInputError(f"Erreur: le PDF existe deja: {resolved_output}")

    try:
        render_invoice_data(
            invoice_data=invoice_data,
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
        "invoice_number": invoice_data["number"],
        "invoice_label": invoice_label,
        "warnings": [],
    }
