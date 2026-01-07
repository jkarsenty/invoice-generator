import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from core.calculator import compute_items, compute_totals
from core.formatter import eur
from core.loader import load_json
from core.validate import (
    ValidationError,
    as_dict,
    load_and_validate,
    validate_client_data,
    validate_invoice_data,
    validate_issuer_data,
)


def render_invoice(
    invoice_path: Path,
    client_path: Path,
    output_pdf_path: Path,
    base_dir: Path
):
    try:
        issuer_obj, client_obj, invoice_obj = load_and_validate(
            issuer_path=base_dir / "config" / "issuer.json",
            client_path=client_path,
            invoice_path=invoice_path,
        )
    except ValidationError as exc:
        raise SystemExit(str(exc))

    _render_invoice(
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
        issuer_obj = validate_issuer_data(issuer_raw, "config/issuer.json")
        client_obj = validate_client_data(client_data, client_label)
        invoice_obj = validate_invoice_data(invoice_data, invoice_label)
    except FileNotFoundError:
        raise SystemExit(
            str(ValidationError("config/issuer.json", "<fichier>", "introuvable"))
        ) from None
    except json.JSONDecodeError:
        raise SystemExit(
            str(ValidationError("config/issuer.json", "<fichier>", "JSON invalide"))
        ) from None
    except ValidationError as exc:
        raise SystemExit(str(exc))

    _render_invoice(
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
    issuer = as_dict(issuer_obj)
    client = as_dict(client_obj)
    invoice_data = as_dict(invoice_obj)

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

    print(f"Facture générée : {output_pdf_path}")
