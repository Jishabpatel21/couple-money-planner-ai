from __future__ import annotations


OLD_SLABS = [
    (250000.0, 0.00),
    (500000.0, 0.05),
    (1000000.0, 0.20),
    (float("inf"), 0.30),
]

NEW_SLABS = [
    (300000.0, 0.00),
    (600000.0, 0.05),
    (900000.0, 0.10),
    (1200000.0, 0.15),
    (1500000.0, 0.20),
    (float("inf"), 0.30),
]


def _slab_tax(income: float, slabs: list[tuple[float, float]]) -> float:
    tax = 0.0
    previous = 0.0
    for limit, rate in slabs:
        if income <= previous:
            break
        taxable = min(income, limit) - previous
        tax += taxable * rate
        previous = limit
    return tax


def _apply_cess(base_tax: float, cess_rate: float = 0.04) -> float:
    return base_tax * (1 + cess_rate)


def _apply_rebate(base_tax: float, taxable_income: float, regime: str) -> float:
    # Section 87A rebate (simplified):
    # old regime: up to Rs 12,500 rebate when taxable income <= Rs 5,00,000
    # new regime: up to Rs 25,000 rebate when taxable income <= Rs 7,00,000
    if regime == "old" and taxable_income <= 500000.0:
        return max(0.0, base_tax - min(base_tax, 12500.0))
    if regime == "new" and taxable_income <= 700000.0:
        return max(0.0, base_tax - min(base_tax, 25000.0))
    return base_tax


def calculate_tax_old_regime(gross_income: float, deductions: float) -> float:
    taxable_income = max(0.0, gross_income - max(0.0, deductions))
    base_tax = _slab_tax(taxable_income, OLD_SLABS)
    base_after_rebate = _apply_rebate(base_tax, taxable_income, regime="old")
    return _apply_cess(base_after_rebate)


def calculate_tax_new_regime(gross_income: float) -> float:
    taxable_income = max(0.0, gross_income)
    base_tax = _slab_tax(taxable_income, NEW_SLABS)
    base_after_rebate = _apply_rebate(base_tax, taxable_income, regime="new")
    return _apply_cess(base_after_rebate)


def compare_tax_regime(gross_income: float, deductions: float = 0.0) -> dict:
    gross_income = max(0.0, float(gross_income))
    deductions = max(0.0, float(deductions))

    old_taxable_income = max(0.0, gross_income - deductions)
    new_taxable_income = gross_income

    old_tax = calculate_tax_old_regime(gross_income, deductions)
    new_tax = calculate_tax_new_regime(gross_income)

    if old_tax <= new_tax:
        better = "old"
        savings = new_tax - old_tax
        recommended_tax = old_tax
    else:
        better = "new"
        savings = old_tax - new_tax
        recommended_tax = new_tax

    return {
        "gross_income": float(gross_income),
        "deductions": float(deductions),
        "old_taxable_income": float(old_taxable_income),
        "new_taxable_income": float(new_taxable_income),
        "old_regime_tax": float(old_tax),
        "new_regime_tax": float(new_tax),
        "recommended_tax": float(recommended_tax),
        "recommended_regime": better,
        "potential_savings": float(savings),
    }


def get_tax_breakdown(gross_income: float, deductions: float = 0.0, regime: str = "old") -> dict:
    gross_income = max(0.0, float(gross_income))
    deductions = max(0.0, float(deductions))

    if regime not in {"old", "new"}:
        raise ValueError("regime must be 'old' or 'new'")

    taxable_income = max(0.0, gross_income - deductions) if regime == "old" else gross_income
    slabs = OLD_SLABS if regime == "old" else NEW_SLABS

    rows = []
    previous = 0.0
    base_tax = 0.0
    for limit, rate in slabs:
        if taxable_income <= previous:
            break
        slab_upper = taxable_income if limit == float("inf") else min(taxable_income, limit)
        slab_amount = max(0.0, slab_upper - previous)
        slab_tax = slab_amount * rate
        rows.append(
            {
                "slab_range": f"Rs {previous:,.0f} - {'Above' if limit == float('inf') else f'Rs {limit:,.0f}'}",
                "rate_pct": rate * 100,
                "amount_in_slab": float(slab_amount),
                "tax_for_slab": float(slab_tax),
            }
        )
        base_tax += slab_tax
        previous = limit

    base_after_rebate = _apply_rebate(base_tax, taxable_income, regime=regime)
    rebate_amount = max(0.0, base_tax - base_after_rebate)
    cess_amount = base_after_rebate * 0.04
    total_tax = base_after_rebate + cess_amount

    return {
        "regime": regime,
        "gross_income": float(gross_income),
        "deductions_used": float(deductions if regime == "old" else 0.0),
        "taxable_income": float(taxable_income),
        "rows": rows,
        "base_tax": float(base_tax),
        "rebate": float(rebate_amount),
        "cess": float(cess_amount),
        "total_tax": float(total_tax),
    }
