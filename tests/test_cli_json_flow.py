from unittest.mock import patch

from typer.testing import CliRunner

import cli.app as cli_app


def _json_new_input(convert_pdf: bool) -> str:
    lines = [
        "",
        "2026-01-10",
        "2026-01-09",
        "2026-02-10",
        "",
        "o",
        "Dev prestation",
        "1",
        "100",
        "",
        "n",
        "o" if convert_pdf else "n",
    ]
    return "\n".join(lines) + "\n"


def _json_new_input_due_date_empty(convert_pdf: bool) -> str:
    lines = [
        "",
        "2026-01-10",
        "2026-01-09",
        "",
        "",
        "o",
        "Dev prestation",
        "1",
        "100",
        "",
        "n",
        "o" if convert_pdf else "n",
    ]
    return "\n".join(lines) + "\n"


def test_json_new_without_pdf(tmp_path):
    runner = CliRunner()
    base_dir = tmp_path
    invoices_dir = base_dir / "invoices"
    output_dir = base_dir / "output"
    clients_dir = base_dir / "clients"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    clients_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(cli_app, "BASE_DIR", base_dir), patch.object(
        cli_app, "INVOICES_DIR", invoices_dir
    ), patch.object(cli_app, "OUTPUT_DIR", output_dir), patch.object(
        cli_app, "CLIENTS_DIR", clients_dir
    ), patch.object(
        cli_app, "_resolve_client"
    ) as resolve_client, patch.object(
        cli_app, "generate_invoice"
    ) as generate_invoice:
        result = runner.invoke(
            cli_app.app,
            ["json", "new"],
            input=_json_new_input(convert_pdf=False),
        )

    assert result.exit_code == 0
    assert "Facture enregistree:" in result.stdout
    assert not resolve_client.called
    assert not generate_invoice.called
    assert len(list(invoices_dir.glob("*.json"))) == 1
    assert len(list(output_dir.glob("*.pdf"))) == 0


def test_json_new_with_pdf_conversion(tmp_path):
    runner = CliRunner()
    base_dir = tmp_path
    invoices_dir = base_dir / "invoices"
    output_dir = base_dir / "output"
    clients_dir = base_dir / "clients"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    clients_dir.mkdir(parents=True, exist_ok=True)

    fake_client = {
        "path": clients_dir / "client.json",
        "data": {"id": "client"},
    }

    with patch.object(cli_app, "BASE_DIR", base_dir), patch.object(
        cli_app, "INVOICES_DIR", invoices_dir
    ), patch.object(cli_app, "OUTPUT_DIR", output_dir), patch.object(
        cli_app, "CLIENTS_DIR", clients_dir
    ), patch.object(
        cli_app, "_resolve_client", return_value=fake_client
    ) as resolve_client, patch.object(
        cli_app,
        "generate_invoice",
        return_value={"output_pdf": str(output_dir / "invoice.pdf")},
    ) as generate_invoice:
        result = runner.invoke(
            cli_app.app,
            ["json", "new"],
            input=_json_new_input(convert_pdf=True),
        )

    assert result.exit_code == 0
    assert "Facture générée" in result.stdout
    assert resolve_client.called
    assert generate_invoice.called


def test_json_new_due_date_defaults_to_issue_date_plus_20_days(tmp_path):
    runner = CliRunner()
    base_dir = tmp_path
    invoices_dir = base_dir / "invoices"
    output_dir = base_dir / "output"
    clients_dir = base_dir / "clients"
    invoices_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    clients_dir.mkdir(parents=True, exist_ok=True)

    with patch.object(cli_app, "BASE_DIR", base_dir), patch.object(
        cli_app, "INVOICES_DIR", invoices_dir
    ), patch.object(cli_app, "OUTPUT_DIR", output_dir), patch.object(
        cli_app, "CLIENTS_DIR", clients_dir
    ), patch.object(
        cli_app, "_resolve_client"
    ) as resolve_client, patch.object(
        cli_app, "generate_invoice"
    ) as generate_invoice:
        result = runner.invoke(
            cli_app.app,
            ["json", "new"],
            input=_json_new_input_due_date_empty(convert_pdf=False),
        )

    assert result.exit_code == 0
    assert not resolve_client.called
    assert not generate_invoice.called

    files = list(invoices_dir.glob("*.json"))
    assert len(files) == 1
    payload = files[0].read_text(encoding="utf-8")
    assert '"due_date": "2026-01-30"' in payload
