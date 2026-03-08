import json
from datetime import datetime
from unittest.mock import patch

import pytest

from core.errors import InvalidInputError
from services import invoice_service


def _valid_invoice(number=None):
    return {
        "number": number,
        "issue_date": "2026-01-10",
        "service_date": "2026-01-09",
        "due_date": "2026-02-10",
        "vat_rate": 20,
        "items": [
            {"description": "Dev", "quantity": 2, "unit_price": 100},
        ],
    }


def test_create_invoice_auto_number(tmp_path):
    invoices_dir = tmp_path / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    year = datetime.now().strftime("%Y")

    with open(invoices_dir / "one.json", "w", encoding="utf-8") as f:
        json.dump({"number": f"INV-{year}-0002"}, f)
    with open(invoices_dir / "old.json", "w", encoding="utf-8") as f:
        json.dump({"number": "INV-2020-0099"}, f)

    result = invoice_service.create_invoice(
        invoice_data=_valid_invoice(number=None),
        invoice_label="<test>",
        invoices_dir=invoices_dir,
        force=False,
    )

    assert result["invoice_number"] == f"INV-{year}-0003"
    assert (invoices_dir / f"invoice_INV-{year}-0003.json").exists()


def test_create_invoice_force_overwrite(tmp_path):
    invoices_dir = tmp_path / "invoices"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    target = invoices_dir / "invoice_INV-2026-0001.json"
    target.write_text('{"number": "INV-2026-0001"}', encoding="utf-8")

    with pytest.raises(InvalidInputError):
        invoice_service.create_invoice(
            invoice_data=_valid_invoice(number="INV-2026-0001"),
            invoice_label="<test>",
            invoices_dir=invoices_dir,
            force=False,
        )

    result = invoice_service.create_invoice(
        invoice_data=_valid_invoice(number="INV-2026-0001"),
        invoice_label="<test>",
        invoices_dir=invoices_dir,
        force=True,
    )

    assert result["invoice_number"] == "INV-2026-0001"
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["items"][0]["description"] == "Dev"


def test_generate_invoice_force_overwrite(tmp_path):
    base_dir = tmp_path
    output_dir = base_dir / "output"
    invoices_dir = base_dir / "invoices"
    output_dir.mkdir(parents=True, exist_ok=True)
    invoices_dir.mkdir(parents=True, exist_ok=True)

    target_pdf = output_dir / "invoice_INV-2026-0007.pdf"
    target_pdf.write_text("existing", encoding="utf-8")

    def fake_render_invoice_data(**kwargs):
        path = kwargs["output_pdf_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pdf", encoding="utf-8")

    with patch(
        "services.invoice_service.render_invoice_data",
        side_effect=fake_render_invoice_data,
    ):
        with pytest.raises(InvalidInputError):
            invoice_service.generate_invoice(
                invoice_data=_valid_invoice(number="INV-2026-0007"),
                invoice_label="<test>",
                client_data={"id": "c"},
                client_label="<client>",
                output_path=None,
                base_dir=base_dir,
                invoices_dir=invoices_dir,
                output_dir=output_dir,
                force=False,
            )

        result = invoice_service.generate_invoice(
            invoice_data=_valid_invoice(number="INV-2026-0007"),
            invoice_label="<test>",
            client_data={"id": "c"},
            client_label="<client>",
            output_path=None,
            base_dir=base_dir,
            invoices_dir=invoices_dir,
            output_dir=output_dir,
            force=True,
        )

    assert result["output_pdf"] == str(target_pdf)
    assert target_pdf.read_text(encoding="utf-8") == "pdf"
