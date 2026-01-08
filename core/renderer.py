import json
from dataclasses import asdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from core.loader import load_json
from core.validate import ValidationError, validate_client_data, validate_invoice_data, validate_issuer_data


def render_invoice(
    invoice_path: Path,
    client_path: Path,
    output_pdf_path: Path,
    base_dir: Path,
):
    issuer_obj, client_obj, invoice_obj = _load_and_validate(
        issuer_path=base_dir / "config" / "issuer.json",
        client_path=client_path,
        invoice_path=invoice_path,
    )

    return _render_invoice(
        issuer_obj=issuer_obj,
        client_obj=client_obj,
        invoice_obj=invoice_obj,
        output_pdf_path=output_pdf_path,
        base_dir=base_dir,
    )


def render_invoice_data(
    invoice_data: dict,
    client_data: dict,
    output_pdf_path: Path,
    base_dir: Path,
    invoice_label: str = "<invoice>",
    client_label: str = "<client>",
):
    try:
        issuer_raw = load_json(base_dir / "config" / "issuer.json")
    except FileNotFoundError:
        raise ValidationError("config/issuer.json", "<fichier>", "introuvable") from None
    except json.JSONDecodeError:
        raise ValidationError("config/issuer.json", "<fichier>", "JSON invalide") from None

    issuer_obj = validate_issuer_data(issuer_raw, "config/issuer.json")
    client_obj = validate_client_data(client_data, client_label)
    invoice_obj = validate_invoice_data(invoice_data, invoice_label)

    return _render_invoice(
        issuer_obj=issuer_obj,
        client_obj=client_obj,
        invoice_obj=invoice_obj,
        output_pdf_path=output_pdf_path,
        base_dir=base_dir,
    )


def _render_invoice(
    issuer_obj,
    client_obj,
    invoice_obj,
    output_pdf_path: Path,
    base_dir: Path,
):
    issuer = asdict(issuer_obj)
    client = asdict(client_obj)
    invoice_data = asdict(invoice_obj)

    items, total_ht = compute_items(invoice_data["items"])
    totals_raw = compute_totals(
        total_ht,
        invoice_data.get("vat_rate", 20),
    )

    for item in items:
        item["unit_price_fmt"] = eur(item["unit_price"])
        item["line_total_fmt"] = eur(item["line_total"])

    totals = {
        "ht": eur(totals_raw["total_ht"]),
        "vat_rate": totals_raw["vat_rate"],
        "vat_amount": eur(totals_raw["vat_amount"]),
        "ttc": eur(totals_raw["total_ttc"]),
    }

    invoice = {
        "number": invoice_data["number"],
        "issue_date": invoice_data["issue_date"],
        "service_date": invoice_data["service_date"],
        "due_date": invoice_data["due_date"],
    }

    env = Environment(
        loader=FileSystemLoader(str(base_dir / "templates")),
        autoescape=True,
    )

    template = env.get_template("invoice.html")

    html = template.render(
        issuer=issuer,
        client=client,
        invoice=invoice,
        items=items,
        totals=totals,
    )

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    HTML(
        string=html,
        base_url=str(base_dir),
    ).write_pdf(str(output_pdf_path))

    return output_pdf_path


def _load_json_checked(path: Path, file_label: str) -> dict:
    try:
        data = load_json(path)
    except FileNotFoundError:
        raise ValidationError(file_label, "<fichier>", "introuvable") from None
    except json.JSONDecodeError:
        raise ValidationError(file_label, "<fichier>", "JSON invalide") from None

    if not isinstance(data, dict):
        raise ValidationError(file_label, "<racine>", "mauvais type (objet JSON attendu)")

    return data


def _load_and_validate(
    issuer_path: Path,
    client_path: Path,
    invoice_path: Path,
):
    issuer_raw = _load_json_checked(issuer_path, "config/issuer.json")
    client_raw = _load_json_checked(client_path, client_path.as_posix())
    invoice_raw = _load_json_checked(invoice_path, invoice_path.as_posix())

    issuer = validate_issuer_data(issuer_raw, "config/issuer.json")
    client = validate_client_data(client_raw, client_path.as_posix())
    invoice = validate_invoice_data(invoice_raw, invoice_path.as_posix())

    return issuer, client, invoice


def compute_items(items_raw):
    items = []
    total_ht = 0.0

    for row in items_raw:
        line_total = row["quantity"] * row["unit_price"]
        total_ht += line_total

        items.append({
            **row,
            "line_total": line_total
        })

    return items, total_ht


def compute_totals(total_ht, vat_rate):
    vat_amount = total_ht * vat_rate / 100
    total_ttc = total_ht + vat_amount

    return {
        "total_ht": total_ht,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "total_ttc": total_ttc
    }


def eur(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")
