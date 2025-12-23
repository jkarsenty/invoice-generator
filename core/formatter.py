def eur(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ").replace(".", ",")
