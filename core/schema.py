from dataclasses import dataclass


@dataclass(frozen=True)
class Issuer:
    company_name: str
    address: str
    email: str
    siren: str
    representative: str | None = None
    phone: str | None = None
    vat_number: str | None = None
    payment_method: str | None = None
    iban: str | None = None
    bic: str | None = None


@dataclass(frozen=True)
class Client:
    id: str
    name: str
    address: str
    siren: str
    vat_number: str | None = None
    email: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class InvoiceItem:
    description: str
    quantity: int
    unit_price: float
    date: str


@dataclass(frozen=True)
class Invoice:
    number: str
    issue_date: str
    service_date: str
    due_date: str
    items: list[InvoiceItem]
    vat_rate: float = 20.0
