import sys
from datetime import datetime, timedelta
from pathlib import Path

import typer

from core.errors import InvoiceGeneratorError
from services.client_service import list_clients, resolve_client_selector
from services.invoice_service import (
    create_invoice,
    generate_invoice,
    list_invoices,
    load_invoice_from_path,
    parse_invoice_json,
    validate_invoice_file,
)


app = typer.Typer(add_completion=False)
json_app = typer.Typer(help="Commandes JSON (creation et validation).")
pdf_app = typer.Typer(help="Commandes PDF (conversion depuis JSON valide).")
app.add_typer(json_app, name="json")
app.add_typer(pdf_app, name="pdf")

BASE_DIR = Path(__file__).resolve().parents[1]
CLIENTS_DIR = BASE_DIR / "clients"
INVOICES_DIR = BASE_DIR / "invoices"
OUTPUT_DIR = BASE_DIR / "output"


def _exit_error(message: str, code: int) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=code)


def _load_json_file(path: Path, label: str) -> dict:
    try:
        return load_invoice_from_path(path)
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)


def _load_json_stdin(label: str) -> dict:
    raw = sys.stdin.read()
    try:
        return parse_invoice_json(raw, label)
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)


def _list_clients() -> tuple[list[dict], list[str]]:
    listed = list_clients(CLIENTS_DIR)
    return listed["clients"], listed["errors"]


def _print_clients(clients: list[dict], errors: list[str]) -> None:
    if not clients:
        print("Aucun client valide dans clients/.")
    else:
        for index, client in enumerate(clients, start=1):
            print(
                f"[{index}] {client['name']} ({client['id']}) - {client['filename']}"
            )
    for err in errors:
        print(f"[invalide] {err}")


def _resolve_client(selector: str | None) -> dict:
    clients, errors = _list_clients()
    if not clients:
        for err in errors:
            print(f"[invalide] {err}")
        _exit_error("Aucun client valide disponible.", 1)

    if selector is None:
        _print_clients(clients, errors)
        while True:
            choice = input("Selectionnez un client (index, id, nom): ").strip()
            if not choice:
                continue
            try:
                return resolve_client_selector(
                    choice,
                    base_dir=BASE_DIR,
                    clients_dir=CLIENTS_DIR,
                )
            except InvoiceGeneratorError as exc:
                print(str(exc))
                continue

    try:
        return resolve_client_selector(
            selector,
            base_dir=BASE_DIR,
            clients_dir=CLIENTS_DIR,
        )
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)


def _prompt_non_empty(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("Valeur obligatoire.")


def _prompt_optional(label: str) -> str | None:
    value = input(f"{label} (optionnel): ").strip()
    return value if value else None


def _prompt_date(label: str) -> str:
    while True:
        value = _prompt_non_empty(label)
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            try:
                datetime.strptime(value, "%Y/%m/%d")
                return value
            except ValueError:
                print("Format attendu: YYYY-MM-DD ou YYYY/MM/DD")


def _prompt_date_optional(label: str) -> str | None:
    while True:
        value = _prompt_optional(label)
        if value is None:
            return None
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            try:
                datetime.strptime(value, "%Y/%m/%d")
                return value
            except ValueError:
                print("Format attendu: YYYY-MM-DD ou YYYY/MM/DD")


def _default_due_date_from_issue_date(issue_date: str) -> str:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            issue = datetime.strptime(issue_date, fmt)
            return (issue + timedelta(days=20)).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("issue_date invalide pour calcul de date d'echeance")


def _prompt_int(label: str) -> int:
    while True:
        raw = _prompt_non_empty(label)
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
        print("Valeur attendue: entier > 0")


def _prompt_float(label: str) -> float:
    while True:
        raw = _prompt_non_empty(label).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            print("Valeur attendue: nombre")
            continue
        if value <= 0:
            print("Valeur attendue: nombre > 0")
            continue
        return value


def _prompt_vat_rate() -> float:
    raw = input("Taux TVA (defaut 20): ").strip().replace(",", ".")
    if not raw:
        return 20.0
    try:
        value = float(raw)
    except ValueError:
        print("Valeur attendue: nombre")
        return _prompt_vat_rate()
    if value < 0 or value > 100:
        print("Valeur attendue: 0-100")
        return _prompt_vat_rate()
    return value


def _collect_items() -> list[dict]:
    items = []
    while True:
        add = input("Ajouter une ligne? (o/n): ").strip().lower()
        if add in {"n", "non", "no"}:
            if not items:
                print("Au moins une ligne est requise.")
                continue
            break
        if add not in {"o", "oui", "y", "yes"}:
            continue

        description = _prompt_non_empty("Description")
        quantity = _prompt_int("Quantite")
        unit_price = _prompt_float("Prix unitaire")
        date = _prompt_optional("Date (YYYY-MM-DD ou YYYY/MM/DD)")
        item = {
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
        }
        if date:
            item["date"] = date
        items.append(item)
    return items


def _confirm_pdf_conversion() -> bool:
    value = input("Convertir en PDF maintenant ? (o/N): ").strip().lower()
    return value in {"o", "oui", "y", "yes"}


def _validate_generate_options(invoice: str | None, stdin: bool) -> None:
    if invoice and stdin:
        raise typer.BadParameter(
            "argument --stdin: not allowed with argument --invoice",
            param_hint="--stdin",
        )
    if not invoice and not stdin:
        raise typer.BadParameter(
            "one of the arguments --invoice --stdin is required",
            param_hint="--invoice/--stdin",
        )


@pdf_app.command("from-json")
def pdf_from_json_command(
    invoice: str = typer.Option(
        ...,
        "--invoice",
        help="Chemin vers un fichier invoice.json",
    ),
    client: str | None = typer.Option(
        None,
        "--client",
        help="Client (index, id, nom ou chemin)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        help="Chemin du PDF de sortie",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ecraser le PDF de sortie s'il existe deja.",
    ),
) -> None:
    client_data = _resolve_client(client)
    invoice_path = (BASE_DIR / invoice).resolve()
    invoice_data = _load_json_file(invoice_path, invoice_path.as_posix())

    output_path = Path(output) if output else None
    try:
        result = generate_invoice(
            invoice_data=invoice_data,
            invoice_label=invoice_path.as_posix(),
            client_data=client_data["data"],
            client_label=client_data["path"].as_posix(),
            output_path=output_path,
            base_dir=BASE_DIR,
            invoices_dir=INVOICES_DIR,
            output_dir=OUTPUT_DIR,
            force=force,
        )
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)

    print(f"Facture générée : {result['output_pdf']}")


@app.command(
    "generate",
    help="DEPRECATED: utilisez `invoice pdf from-json`.",
    deprecated=True,
)
def generate_command(
    invoice: str | None = typer.Option(
        None,
        "--invoice",
        help="Chemin vers un fichier invoice.json",
    ),
    stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Lire la facture JSON depuis stdin",
    ),
    client: str | None = typer.Option(
        None,
        "--client",
        help="Client (index, id, nom ou chemin)",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        help="Chemin du PDF de sortie",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Ecraser le PDF de sortie s'il existe deja.",
    ),
) -> None:
    _validate_generate_options(invoice, stdin)
    client_data = _resolve_client(client)
    if stdin:
        invoice_data = _load_json_stdin("<stdin>")
        invoice_label = "<stdin>"
    else:
        invoice_path = (BASE_DIR / invoice).resolve()
        invoice_data = _load_json_file(invoice_path, invoice_path.as_posix())
        invoice_label = invoice_path.as_posix()

    output_path = Path(output) if output else None
    try:
        result = generate_invoice(
            invoice_data=invoice_data,
            invoice_label=invoice_label,
            client_data=client_data["data"],
            client_label=client_data["path"].as_posix(),
            output_path=output_path,
            base_dir=BASE_DIR,
            invoices_dir=INVOICES_DIR,
            output_dir=OUTPUT_DIR,
            force=force,
        )
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)

    print(f"Facture générée : {result['output_pdf']}")


@json_app.command("validate")
def json_validate_command(
    invoice: str = typer.Option(
        ...,
        "--invoice",
        help="Chemin vers un fichier invoice.json",
    )
) -> None:
    invoice_path = (BASE_DIR / invoice).resolve()
    try:
        result = validate_invoice_file(invoice_path, INVOICES_DIR)
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)

    print(f"Facture JSON valide : {invoice_path}")
    print(f"Numero: {result['invoice_number']}")


@json_app.command("new")
def json_new_command(
    force: bool = typer.Option(
        False,
        "--force",
        help="Ecraser le fichier JSON et/ou PDF s'ils existent deja.",
    ),
) -> None:
    number = _prompt_optional("Numero de facture")
    issue_date = _prompt_date("Date d'emission")
    service_date = _prompt_date("Date de service")
    due_date = _prompt_date_optional("Date d'echeance")
    if due_date is None:
        due_date = _default_due_date_from_issue_date(issue_date)
    vat_rate = _prompt_vat_rate()
    items = _collect_items()

    invoice_data = {
        "number": number,
        "issue_date": issue_date,
        "service_date": service_date,
        "due_date": due_date,
        "vat_rate": vat_rate,
        "items": items,
    }

    try:
        result = create_invoice(
            invoice_data=invoice_data,
            invoice_label="<nouvelle facture>",
            invoices_dir=INVOICES_DIR,
            force=force,
        )
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)

    print(f"Facture enregistree: {result['invoice_path']}")

    if not _confirm_pdf_conversion():
        return

    client = _resolve_client(None)
    try:
        pdf_result = generate_invoice(
            invoice_data=result["invoice_data"],
            invoice_label=result["invoice_path"],
            client_data=client["data"],
            client_label=client["path"].as_posix(),
            output_path=None,
            base_dir=BASE_DIR,
            invoices_dir=INVOICES_DIR,
            output_dir=OUTPUT_DIR,
            force=force,
        )
    except InvoiceGeneratorError as exc:
        _exit_error(str(exc), 1)

    print(f"Facture générée : {pdf_result['output_pdf']}")


@app.command("list", help="Lister les factures JSON presentes dans invoices/.")
def list_command() -> None:
    result = list_invoices(INVOICES_DIR)
    entries = result["entries"]
    if not entries:
        print("Aucune facture dans invoices/.")
        return

    for entry in entries:
        print(
            f"{entry['filename']} | {entry['number']} | {entry['issue_date']} | {entry['status']}"
        )


@app.command("clients", help="Lister les clients valides et signaler les clients invalides.")
def clients_command() -> None:
    clients, errors = _list_clients()
    _print_clients(clients, errors)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
