from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from core.loader import load_json
from core.calculator import compute_items, compute_totals
from core.formatter import eur


def render_invoice(
    invoice_path: Path,
    client_path: Path,
    output_pdf_path: Path,
    base_dir: Path
):
    
    # LOAD JSON 
    issuer = load_json(base_dir / "config" / "issuer.example.json")
    client = load_json(client_path)
    invoice_data = load_json(invoice_path)

    # PREPARE ITEMS
    items, total_ht = compute_items(invoice_data["items"])
    totals_raw = compute_totals(
        total_ht,
        invoice_data.get("vat_rate", 20)
    )

    # Format pour affichage
    for item in items:
        item["unit_price_fmt"] = eur(item["unit_price"])
        item["line_total_fmt"] = eur(item["line_total"])

    # TOTALS
    totals = {
        "ht": eur(totals_raw["total_ht"]),
        "vat_rate": totals_raw["vat_rate"],
        "vat_amount": eur(totals_raw["vat_amount"]),
        "ttc": eur(totals_raw["total_ttc"])
    }

    # INVOICE META
    invoice = {
        "number": invoice_data["number"],
        "issue_date": invoice_data["issue_date"],
        "service_date": invoice_data["service_date"],
        "due_date": invoice_data["due_date"]
    }

    # JINJA RENDER
    env = Environment(
        loader=FileSystemLoader(str(base_dir / "templates")),
        autoescape=True
    )

    template = env.get_template("invoice.html")

    html = template.render(
        issuer=issuer,
        client=client,
        invoice=invoice,
        items=items,
        totals=totals
    )

    # ENSURE OUTPUT DIR
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # HTML → PDF
    HTML(
        string=html,
        base_url=str(base_dir)
    ).write_pdf(str(output_pdf_path))

    print(f"Facture générée : {output_pdf_path}")
