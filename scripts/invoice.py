import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from core.loader import load_json
from core.renderer import render_invoice, render_invoice_data
from core.validate import ValidationError, validate_client_data, validate_invoice_data


BASE_DIR = Path(__file__).resolve().parents[1]
CLIENTS_DIR = BASE_DIR / "clients"
INVOICES_DIR = BASE_DIR / "invoices"
OUTPUT_DIR = BASE_DIR / "output"


def _load_json_file(path: Path, label: str) -> dict:
    try:
        data = load_json(path)
    except FileNotFoundError:
        raise ValidationError(label, "<fichier>", "introuvable") from None
    except json.JSONDecodeError:
        raise ValidationError(label, "<fichier>", "JSON invalide") from None

    if not isinstance(data, dict):
        raise ValidationError(label, "<racine>", "mauvais type (objet JSON attendu)")

    return data


def _load_json_stdin(label: str) -> dict:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Erreur: stdin vide, aucun JSON recu.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValidationError(label, "<fichier>", "JSON invalide") from None
    if not isinstance(data, dict):
        raise ValidationError(label, "<racine>", "mauvais type (objet JSON attendu)")
    return data


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")


def _make_invoice_filename(number: str) -> str:
    safe = _sanitize_filename(number)
    return f"invoice_{safe}.json"


def _make_output_filename(number: str) -> str:
    safe = _sanitize_filename(number)
    return f"invoice_{safe}.pdf"


def _generate_invoice_number(invoices_dir: Path) -> str:
    year = datetime.now().strftime("%Y")
    pattern = re.compile(r"INV-(\\d{4})-(\\d{4})")
    max_index = 0
    for path in sorted(invoices_dir.glob("*.json")):
        try:
            data = _load_json_file(path, path.as_posix())
        except ValidationError:
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


def _list_clients() -> tuple[list[dict], list[str]]:
    clients = []
    errors = []
    for path in sorted(CLIENTS_DIR.glob("*.json")):
        try:
            data = _load_json_file(path, path.as_posix())
            client = validate_client_data(data, path.as_posix())
        except ValidationError as exc:
            errors.append(str(exc))
            continue
        clients.append(
            {
                "path": path,
                "id": client.id,
                "name": client.name,
                "data": data,
                "filename": path.name,
            }
        )
    return clients, errors


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
                return _resolve_client(choice)
            except SystemExit as exc:
                print(str(exc))
                continue
    else:
        if selector.isdigit():
            index = int(selector)
            if 1 <= index <= len(clients):
                return clients[index - 1]
            raise SystemExit("Index client invalide.")

        candidate = Path(selector)
        if not candidate.is_absolute():
            candidate = BASE_DIR / selector
        if candidate.exists():
            data = _load_json_file(candidate, candidate.as_posix())
            client = validate_client_data(data, candidate.as_posix())
            return {
                "path": candidate,
                "id": client.id,
                "name": client.name,
                "data": data,
                "filename": candidate.name,
            }

        candidate = CLIENTS_DIR / selector
        if candidate.exists():
            data = _load_json_file(candidate, candidate.as_posix())
            client = validate_client_data(data, candidate.as_posix())
            return {
                "path": candidate,
                "id": client.id,
                "name": client.name,
                "data": data,
                "filename": candidate.name,
            }

        selector_lower = selector.lower()
        for client in clients:
            if (
                client["id"].lower() == selector_lower
                or client["name"].lower() == selector_lower
                or client["filename"].lower() == selector_lower
                or client["filename"].lower().removesuffix(".json") == selector_lower
            ):
                return client

        raise SystemExit("Client introuvable.")

    raise SystemExit("Client introuvable.")


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

    if not invoice_data.get("number"):
        invoice_data["number"] = _generate_invoice_number(INVOICES_DIR)

    try:
        validate_invoice_data(invoice_data, invoice_label)
    except ValidationError as exc:
        raise SystemExit(str(exc)) from None

    output_path = Path(args.output) if args.output else None
    if output_path is None:
        output_path = OUTPUT_DIR / _make_output_filename(invoice_data["number"])
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    if output_path.exists():
        raise SystemExit(f"Erreur: le PDF existe deja: {output_path}")

    render_invoice_data(
        invoice_data=invoice_data,
        client_data=client["data"],
        output_pdf_path=output_path,
        base_dir=BASE_DIR,
        invoice_label=invoice_label,
        client_label=client["path"].as_posix(),
    )


def _new_command(args: argparse.Namespace) -> None:
    client = _resolve_client(None)

    number = _prompt_optional("Numero de facture")
    if not number:
        number = _generate_invoice_number(INVOICES_DIR)

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
        validate_invoice_data(invoice_data, "<nouvelle facture>")
    except ValidationError as exc:
        raise SystemExit(str(exc)) from None

    invoice_path = INVOICES_DIR / _make_invoice_filename(number)
    output_path = OUTPUT_DIR / _make_output_filename(number)
    if invoice_path.exists():
        raise SystemExit(f"Erreur: le fichier existe deja: {invoice_path}")
    if not args.no_pdf and output_path.exists():
        raise SystemExit(f"Erreur: le PDF existe deja: {output_path}")

    INVOICES_DIR.mkdir(parents=True, exist_ok=True)
    with open(invoice_path, "w", encoding="utf-8") as f:
        json.dump(invoice_data, f, indent=4, ensure_ascii=False)

    print(f"Facture enregistree: {invoice_path}")

    if args.no_pdf:
        return

    if output_path.exists():
        raise SystemExit(f"Erreur: le PDF existe deja: {output_path}")

    render_invoice(
        invoice_path=invoice_path,
        client_path=client["path"],
        output_pdf_path=output_path,
        base_dir=BASE_DIR,
    )


def _list_command(_: argparse.Namespace) -> None:
    paths = sorted(INVOICES_DIR.glob("*.json"))
    if not paths:
        print("Aucune facture dans invoices/.")
        return

    for path in paths:
        try:
            data = _load_json_file(path, path.as_posix())
            invoice = validate_invoice_data(data, path.as_posix())
            number = invoice.number
            issue_date = invoice.issue_date
            status = "ok"
        except ValidationError as exc:
            number = "-"
            issue_date = "-"
            status = f"invalide: {exc}"
        print(f"{path.name} | {number} | {issue_date} | {status}")


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
