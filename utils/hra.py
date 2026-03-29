from __future__ import annotations


def calculate_hra(
    hra_received: float,
    basic_salary: float,
    rent_paid: float,
    metro: bool = True,
) -> dict:
    """Calculate India HRA exemption details."""
    salary_cap = 0.50 * basic_salary if metro else 0.40 * basic_salary
    rent_minus_ten_percent = max(0.0, rent_paid - 0.10 * basic_salary)

    exemption = min(hra_received, salary_cap, rent_minus_ten_percent)
    taxable_hra = max(0.0, hra_received - exemption)

    return {
        "hra_received": float(hra_received),
        "basic_salary": float(basic_salary),
        "rent_paid": float(rent_paid),
        "salary_cap": float(salary_cap),
        "rent_minus_ten_percent": float(rent_minus_ten_percent),
        "hra_exemption": float(exemption),
        "hra_taxable": float(taxable_hra),
    }


def suggest_best_claimant(partner_a_hra: dict, partner_b_hra: dict, tax_rate: float = 0.30) -> dict:
    """Suggest which partner should maximize HRA claim."""
    a_saving = partner_a_hra["hra_exemption"] * tax_rate
    b_saving = partner_b_hra["hra_exemption"] * tax_rate

    if a_saving >= b_saving:
        claimant = "Partner A"
        best_saving = a_saving
    else:
        claimant = "Partner B"
        best_saving = b_saving

    return {
        "best_claimant": claimant,
        "partner_a_tax_saving": float(a_saving),
        "partner_b_tax_saving": float(b_saving),
        "best_possible_saving": float(best_saving),
    }
