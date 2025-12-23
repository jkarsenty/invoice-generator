import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from core.loader import load_json
from core.schema import Client, Invoice, InvoiceItem, Issuer


class ValidationError(Exception):
    def __init__(self, file_label: str, field: str, reason: str):
        self.file_label = file_label
        self.field = field
        self.reason = reason
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return f"Erreur dans {self.file_label}: champ '{self.field}' {self.reason}."


def load_and_validate(
    issuer_path: Path,
    client_path: Path,
    invoice_path: Path
) -> tuple[Issuer, Client, Invoice]:
    issuer_raw = _load_json_checked(issuer_path, "config/issuer.json")
    client_raw = _load_json_checked(client_path, client_path.as_posix())
    invoice_raw = _load_json_checked(invoice_path, invoice_path.as_posix())

    issuer = _validate_issuer(issuer_raw, "config/issuer.json")
    client = _validate_client(client_raw, client_path.as_posix())
    invoice = _validate_invoice(invoice_raw, invoice_path.as_posix())

    return issuer, client, invoice


def as_dict(obj: Any) -> dict:
    return asdict(obj)


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


def _validate_issuer(data: dict, file_label: str) -> Issuer:
    required = {"company_name", "address", "email", "siren"}
    optional = {
        "representative",
        "phone",
        "vat_number",
        "payment_method",
        "iban",
        "bic",
    }
    _ensure_known_keys(data, required | optional, file_label)
    values = _validate_string_fields(data, required, optional, file_label)
    return Issuer(**values)


def _validate_client(data: dict, file_label: str) -> Client:
    required = {"id", "name", "address", "siren"}
    optional = {"vat_number", "email", "notes"}
    _ensure_known_keys(data, required | optional, file_label)
    values = _validate_string_fields(data, required, optional, file_label)
    return Client(**values)


def _validate_invoice(data: dict, file_label: str) -> Invoice:
    required = {"number", "issue_date", "service_date", "due_date", "items"}
    optional = {"vat_rate"}
    _ensure_known_keys(data, required | optional, file_label)

    values = _validate_string_fields(
        data,
        {"number", "issue_date", "service_date", "due_date"},
        set(),
        file_label,
    )
    _require_iso_date(values["issue_date"], file_label, "issue_date")
    _require_iso_date(values["service_date"], file_label, "service_date")
    _require_iso_date(values["due_date"], file_label, "due_date")

    items_raw = data.get("items")
    if items_raw is None:
        raise ValidationError(file_label, "items", "manquant")
    if not isinstance(items_raw, list):
        raise ValidationError(file_label, "items", "mauvais type (liste attendue)")
    if len(items_raw) == 0:
        raise ValidationError(file_label, "items", "vide")

    items: list[InvoiceItem] = []
    for index, item_raw in enumerate(items_raw):
        if not isinstance(item_raw, dict):
            raise ValidationError(file_label, f"items[{index}]", "mauvais type (objet attendu)")
        items.append(
            _validate_invoice_item(item_raw, file_label, index, values["service_date"])
        )

    vat_rate = data.get("vat_rate", 20)
    if vat_rate is None:
        vat_rate = 20
    _validate_number(file_label, "vat_rate", vat_rate, allow_int=True)
    if vat_rate < 0 or vat_rate > 100:
        raise ValidationError(file_label, "vat_rate", "valeur invalide (0-100)")

    return Invoice(
        number=values["number"],
        issue_date=values["issue_date"],
        service_date=values["service_date"],
        due_date=values["due_date"],
        items=items,
        vat_rate=float(vat_rate),
    )


def _validate_invoice_item(
    data: dict,
    file_label: str,
    index: int,
    service_date: str,
) -> InvoiceItem:
    required = {"description", "quantity", "unit_price"}
    optional = {"date"}
    _ensure_known_keys(data, required | optional, file_label, f"items[{index}].")

    description = _require_string(
        data, "description", file_label, f"items[{index}]."
    )
    quantity = data.get("quantity")
    if quantity is None:
        raise ValidationError(file_label, f"items[{index}].quantity", "manquant")
    if not _is_int(quantity):
        raise ValidationError(
            file_label, f"items[{index}].quantity", "mauvais type (entier attendu)"
        )
    if quantity <= 0:
        raise ValidationError(file_label, f"items[{index}].quantity", "valeur invalide (> 0)")

    unit_price = data.get("unit_price")
    if unit_price is None:
        raise ValidationError(file_label, f"items[{index}].unit_price", "manquant")
    _validate_number(file_label, f"items[{index}].unit_price", unit_price, allow_int=True)
    if unit_price <= 0:
        raise ValidationError(
            file_label, f"items[{index}].unit_price", "valeur invalide (> 0)"
        )

    if "date" in data:
        date_raw = _require_string(data, "date", file_label, f"items[{index}].")
        date = _normalize_item_date(date_raw, file_label, f"items[{index}].date")
    else:
        date = _format_date_dmy_from_iso(service_date, file_label, "service_date")

    return InvoiceItem(
        description=description,
        quantity=int(quantity),
        unit_price=float(unit_price),
        date=date,
    )


def _require_iso_date(value: str, file_label: str, field: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        try:
            datetime.strptime(value, "%Y/%m/%d")
        except ValueError:
            raise ValidationError(
                file_label,
                field,
                "format invalide (YYYY-MM-DD ou YYYY/MM/DD attendu)",
            ) from None


def _format_date_dmy_from_iso(value: str, file_label: str, field: str) -> str:
    try:
        date_obj = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        try:
            date_obj = datetime.strptime(value, "%Y/%m/%d")
        except ValueError:
            raise ValidationError(
                file_label,
                field,
                "format invalide (YYYY-MM-DD ou YYYY/MM/DD attendu pour date par defaut)",
            ) from None
    return date_obj.strftime("%d-%m-%Y")


def _normalize_item_date(value: str, file_label: str, field: str) -> str:
    try:
        date_obj = datetime.strptime(value, "%Y-%m-%d")
        return date_obj.strftime("%d-%m-%Y")
    except ValueError:
        pass

    try:
        date_obj = datetime.strptime(value, "%Y/%m/%d")
        return date_obj.strftime("%d-%m-%Y")
    except ValueError:
        pass

    try:
        date_obj = datetime.strptime(value, "%d-%m-%Y")
        return date_obj.strftime("%d-%m-%Y")
    except ValueError:
        pass

    try:
        date_obj = datetime.strptime(value, "%d/%m/%Y")
        return date_obj.strftime("%d-%m-%Y")
    except ValueError:
        raise ValidationError(
            file_label,
            field,
            "format invalide (YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY ou DD/MM/YYYY attendu)",
        ) from None


def _ensure_known_keys(
    data: dict,
    allowed: set[str],
    file_label: str,
    prefix: str = "",
) -> None:
    for key in data.keys():
        if key not in allowed:
            raise ValidationError(file_label, f"{prefix}{key}", "inconnu")


def _validate_string_fields(
    data: dict,
    required: set[str],
    optional: set[str],
    file_label: str,
) -> dict:
    values: dict[str, str | None] = {}

    for field in required:
        values[field] = _require_string(data, field, file_label)

    for field in optional:
        if field in data:
            values[field] = _require_string(data, field, file_label)
        else:
            values[field] = None

    return values


def _require_string(
    data: dict,
    field: str,
    file_label: str,
    prefix: str = "",
) -> str:
    if field not in data:
        raise ValidationError(file_label, f"{prefix}{field}", "manquant")
    value = data.get(field)
    if not isinstance(value, str):
        raise ValidationError(file_label, f"{prefix}{field}", "mauvais type (string attendu)")
    if value.strip() == "":
        raise ValidationError(file_label, f"{prefix}{field}", "vide")
    return value


def _validate_number(
    file_label: str,
    field: str,
    value: Any,
    allow_int: bool = False,
) -> None:
    if _is_bool(value):
        raise ValidationError(file_label, field, "mauvais type (nombre attendu)")
    if allow_int and isinstance(value, int):
        return
    if not isinstance(value, (int, float)):
        raise ValidationError(file_label, field, "mauvais type (nombre attendu)")


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
