from __future__ import annotations


RISK_ALLOCATIONS = {
    "conservative": {"ELSS": 0.20, "PPF": 0.50, "NPS": 0.20, "Other": 0.10},
    "moderate": {"ELSS": 0.40, "PPF": 0.30, "NPS": 0.20, "Other": 0.10},
    "aggressive": {"ELSS": 0.60, "PPF": 0.10, "NPS": 0.20, "Other": 0.10},
}


def suggest_sip_split(
    total_monthly_sip: float,
    partner_a_income: float,
    partner_b_income: float,
    risk_profile: str = "moderate",
) -> dict:
    """Split SIP by income ratio and suggest ELSS/PPF/NPS allocation."""
    total_income = max(0.0, partner_a_income) + max(0.0, partner_b_income)
    if total_income == 0:
        a_ratio = 0.5
        b_ratio = 0.5
    else:
        a_ratio = max(0.0, partner_a_income) / total_income
        b_ratio = max(0.0, partner_b_income) / total_income

    allocations = RISK_ALLOCATIONS.get(risk_profile, RISK_ALLOCATIONS["moderate"])

    a_sip = total_monthly_sip * a_ratio
    b_sip = total_monthly_sip * b_ratio

    return {
        "risk_profile": risk_profile,
        "partner_a_ratio": float(a_ratio),
        "partner_b_ratio": float(b_ratio),
        "partner_a_monthly_sip": float(a_sip),
        "partner_b_monthly_sip": float(b_sip),
        "allocation_percent": allocations,
        "allocation_amounts": {
            k: float(total_monthly_sip * v) for k, v in allocations.items()
        },
    }


def suggest_nps_optimization(annual_income: float, tax_rate: float = 0.30) -> dict:
    additional_deduction = 50000.0
    tax_saved = additional_deduction * tax_rate
    return {
        "additional_nps_deduction": additional_deduction,
        "estimated_tax_saved": tax_saved,
        "note": "Use section 80CCD(1B) for extra NPS deduction up to Rs 50,000.",
    }


def insurance_recommendation(
    annual_income_a: float,
    annual_income_b: float,
    dependents_count: int,
) -> dict:
    term_a = max(0.0, annual_income_a) * 10
    term_b = max(0.0, annual_income_b) * 10
    combined_term = term_a + term_b

    household_size = max(2, 2 + max(0, dependents_count))
    health_per_person = 500000.0
    joint_health_cover = household_size * health_per_person

    joint_estimated_premium = joint_health_cover * 0.005
    individual_estimated_premium = joint_health_cover * 0.006
    policy_type = "joint" if joint_estimated_premium <= individual_estimated_premium else "individual"

    return {
        "term_partner_a": float(term_a),
        "term_partner_b": float(term_b),
        "term_combined": float(combined_term),
        "health_cover_recommended": float(joint_health_cover),
        "health_policy_type": policy_type,
        "estimated_annual_health_premium": float(min(joint_estimated_premium, individual_estimated_premium)),
    }


def calculate_net_worth(assets: list[dict], liabilities: list[dict]) -> dict:
    total_assets = float(sum(item.get("value", 0.0) for item in assets))
    total_liabilities = float(sum(item.get("value", 0.0) for item in liabilities))
    net_worth = max(0.0, total_assets - total_liabilities)
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": float(net_worth),
    }


def calculate_savings_score(
    savings_rate_pct: float,
    emergency_months: float,
    insurance_covered: bool,
    tax_optimized: bool,
) -> int:
    """Simple hackathon scoring model from 0-100."""
    score = 0.0
    score += min(40.0, max(0.0, savings_rate_pct * 1.6))
    score += min(25.0, max(0.0, emergency_months * 4.0))
    score += 20.0 if insurance_covered else 0.0
    score += 15.0 if tax_optimized else 0.0
    return int(round(min(100.0, score)))
