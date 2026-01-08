import argparse
import sys
from datetime import datetime
from pathlib import Path

from core.errors import InvoiceGeneratorError
from services.client_service import list_clients, resolve_client_selector
from services.invoice_service import (
    create_invoice,
    generate_invoice,
    list_invoices,
    load_invoice_from_path,
    parse_invoice_json,
)


BASE_DIR = Path(__file__).resolve().parents[1]
CLIENTS_DIR = BASE_DIR / "clients"
INVOICES_DIR = BASE_DIR / "invoices"
OUTPUT_DIR = BASE_DIR / "output"


def _load_json_file(path: Path, label: str) -> dict:
    try:
        return load_invoice_from_path(path)
    except InvoiceGeneratorError as exc:
        raise SystemExit(str(exc)) from None


def _load_json_stdin(label: str) -> dict:
    raw = sys.stdin.read()
    try:
        return parse_invoice_json(raw, label)
    except InvoiceGeneratorError as exc:
        raise SystemExit(str(exc)) from None


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
        raise SystemExit("Aucun client valide disponible.")

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
        raise SystemExit(str(exc)) from None


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


def _generate_command(args: argparse.Namespace) -> None:
    client = _resolve_client(args.client)
    if args.stdin:
        invoice_data = _load_json_stdin("<stdin>")
        invoice_label = "<stdin>"
    else:
        invoice_path = (BASE_DIR / args.invoice).resolve()
        invoice_data = _load_json_file(invoice_path, invoice_path.as_posix())
        invoice_label = invoice_path.as_posix()

    output_path = Path(args.output) if args.output else None
    try:
        result = generate_invoice(
            invoice_data=invoice_data,
            invoice_label=invoice_label,
            client_data=client["data"],
            client_label=client["path"].as_posix(),
            output_path=output_path,
            base_dir=BASE_DIR,
            invoices_dir=INVOICES_DIR,
            output_dir=OUTPUT_DIR,
        )
    except InvoiceGeneratorError as exc:
        raise SystemExit(str(exc)) from None

    print(f"Facture générée : {result['output_pdf']}")


def _new_command(args: argparse.Namespace) -> None:
    client = _resolve_client(None)

    number = _prompt_optional("Numero de facture")
    issue_date = _prompt_date("Date d'emission")
    service_date = _prompt_date("Date de service")
    due_date = _prompt_date("Date d'echeance")
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
            client_path=client["path"],
            base_dir=BASE_DIR,
            invoices_dir=INVOICES_DIR,
            output_dir=OUTPUT_DIR,
            no_pdf=args.no_pdf,
        )
    except InvoiceGeneratorError as exc:
        raise SystemExit(str(exc)) from None

    print(f"Facture enregistree: {result['invoice_path']}")
    if result["output_pdf"]:
        print(f"Facture générée : {result['output_pdf']}")


def _list_command(_: argparse.Namespace) -> None:
    result = list_invoices(INVOICES_DIR)
    entries = result["entries"]
    if not entries:
        print("Aucune facture dans invoices/.")
        return

    for entry in entries:
        print(
            f"{entry['filename']} | {entry['number']} | {entry['issue_date']} | {entry['status']}"
        )


def _clients_command(_: argparse.Namespace) -> None:
    clients, errors = _list_clients()
    _print_clients(clients, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI metier de facturation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Creation guidee d'une facture")
    new_parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Ne pas generer le PDF apres creation",
    )
    new_parser.set_defaults(func=_new_command)

    generate_parser = subparsers.add_parser(
        "generate", help="Generer un PDF a partir d'une facture"
    )
    generate_group = generate_parser.add_mutually_exclusive_group(required=True)
    generate_group.add_argument(
        "--invoice",
        help="Chemin vers un fichier invoice.json",
    )
    generate_group.add_argument(
        "--stdin",
        action="store_true",
        help="Lire la facture JSON depuis stdin",
    )
    generate_parser.add_argument(
        "--client",
        help="Client (index, id, nom ou chemin)",
    )
    generate_parser.add_argument(
        "--output",
        help="Chemin du PDF de sortie",
    )
    generate_parser.set_defaults(func=_generate_command)

    list_parser = subparsers.add_parser("list", help="Lister les factures")
    list_parser.set_defaults(func=_list_command)

    clients_parser = subparsers.add_parser("clients", help="Lister les clients")
    clients_parser.set_defaults(func=_clients_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
