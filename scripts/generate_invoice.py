import argparse
from pathlib import Path

from core.renderer import render_invoice


def main():
    parser = argparse.ArgumentParser(description="Générateur de factures PDF")

    parser.add_argument(
        "--invoice",
        required=True,
        help="Fichier invoice JSON (ex: invoices/invoice_0001.json)"
    )

    parser.add_argument(
        "--client",
        required=True,
        help="Fichier client JSON (ex: clients/<client_name>.json)"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Chemin du PDF de sortie (ex: output/invoice_0001.pdf)"
    )

    args = parser.parse_args()

    # Project root (parent of scripts/)
    base_dir = Path(__file__).resolve().parents[1]

    render_invoice(
        invoice_path=base_dir / args.invoice,
        client_path=base_dir / args.client,
        output_pdf_path=base_dir / args.output,
        base_dir=base_dir
    )


if __name__ == "__main__":
    main()
