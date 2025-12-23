def compute_items(items_raw):
    items = []
    total_ht = 0.0

    for row in items_raw:
        line_total = row["quantity"] * row["unit_price"]
        total_ht += line_total

        items.append({
            **row,
            "line_total": line_total
        })

    return items, total_ht


def compute_totals(total_ht, vat_rate):
    vat_amount = total_ht * vat_rate / 100
    total_ttc = total_ht + vat_amount

    return {
        "total_ht": total_ht,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "total_ttc": total_ttc
    }
