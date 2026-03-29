from __future__ import annotations

import json
import os
from urllib import error, request

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _fallback_recommendations(financial_data: dict) -> dict:
    recommendations = []

    total_income = financial_data.get("total_income", 0.0)
    rent = financial_data.get("total_rent", 0.0)
    total_sip = financial_data.get("total_monthly_sip", 0.0)
    tax_savings = financial_data.get("tax_savings_total", 0.0)
    best_claimant = financial_data.get("hra_best_claimant", "Partner A")
    tax_a = str(financial_data.get("tax_recommendation_a", "old")).upper()
    tax_b = str(financial_data.get("tax_recommendation_b", "old")).upper()
    savings_rate = float(financial_data.get("savings_rate", 0.0))
    risk_profile = str(financial_data.get("risk_profile", "moderate")).lower()

    partner_a = financial_data.get("partner_a", {})
    partner_b = financial_data.get("partner_b", {})
    a_name = partner_a.get("name", "Partner A")
    b_name = partner_b.get("name", "Partner B")

    sip_split = financial_data.get("sip_split", {})
    a_sip = float(sip_split.get("partner_a_monthly_sip", 0.0))
    b_sip = float(sip_split.get("partner_b_monthly_sip", 0.0))
    allocation_amounts = sip_split.get("allocation_amounts", {})
    elss_amt = float(allocation_amounts.get("ELSS", 0.0))
    ppf_amt = float(allocation_amounts.get("PPF", 0.0))
    nps_amt = float(allocation_amounts.get("NPS", 0.0))

    if rent > 0:
        recommendations.append(f"Shift HRA claim focus to {best_claimant} and maintain rent proof documents.")

    recommendations.append(f"Tax regime recommendation: {a_name} -> {tax_a}, {b_name} -> {tax_b}.")

    if total_sip < max(5000.0, total_income * 0.10 / 12):
        target = max(5000.0, total_income * 0.10 / 12)
        recommendations.append(f"Increase combined SIP by about Rs {max(0.0, target - total_sip):,.0f} per month to reach 10% savings.")

    if a_sip > 0 and b_sip > 0:
        recommendations.append(f"Suggested SIP split: {a_name} Rs {a_sip:,.0f}/month, {b_name} Rs {b_sip:,.0f}/month.")

    # Always include investment-specific guidance.
    recommendations.append(
        f"Investment plan ({risk_profile.title()}): ELSS Rs {elss_amt:,.0f}, PPF Rs {ppf_amt:,.0f}, NPS Rs {nps_amt:,.0f} per month."
    )

    annual_elss = elss_amt * 12
    if annual_elss < 150000:
        top_up = (150000 - annual_elss) / 12
        recommendations.append(
            f"Top up ELSS by about Rs {top_up:,.0f}/month to fully utilize 80C limit (if cashflow allows)."
        )

    annual_nps = nps_amt * 12
    if annual_nps < 50000:
        nps_top_up = (50000 - annual_nps) / 12
        recommendations.append(
            f"Add around Rs {nps_top_up:,.0f}/month to NPS to capture full extra Rs 50,000 deduction under 80CCD(1B)."
        )

    if tax_savings > 0:
        recommendations.append(f"Adopt recommended regimes to capture estimated annual tax savings of about Rs {tax_savings:,.0f}.")

    if savings_rate < 20:
        recommendations.append("Current savings rate is low; target at least 20% using expense controls and automatic SIP.")
    else:
        recommendations.append("Savings rate is healthy; continue and redirect increments toward long-term goals.")

    recommendations.append("Build emergency fund equal to 6 months of household expenses.")
    recommendations.append("Use NPS extra deduction (80CCD 1B) for additional tax optimization.")

    return {
        "model": "fallback-rules",
        "recommendations": recommendations[:10],
    }


def _ensure_investment_advice(recommendations: list[str], financial_data: dict) -> list[str]:
    text_blob = " ".join(recommendations).lower()
    has_investment_hint = any(k in text_blob for k in ["sip", "elss", "ppf", "nps", "invest"])

    if has_investment_hint:
        return recommendations

    sip_split = financial_data.get("sip_split", {})
    allocation_amounts = sip_split.get("allocation_amounts", {})
    elss_amt = float(allocation_amounts.get("ELSS", 0.0))
    ppf_amt = float(allocation_amounts.get("PPF", 0.0))
    nps_amt = float(allocation_amounts.get("NPS", 0.0))

    recommendations.append(
        f"Investment action: allocate monthly SIP as ELSS Rs {elss_amt:,.0f}, PPF Rs {ppf_amt:,.0f}, NPS Rs {nps_amt:,.0f}."
    )
    return recommendations


def _extract_recommendation_lines(text: str, max_items: int = 10) -> list[str]:
    lines = [line.strip("- *\t ") for line in text.splitlines() if line.strip()]
    cleaned = [line for line in lines if len(line) > 8]
    return cleaned[:max_items]


def _generate_with_huggingface(financial_data: dict) -> dict | None:
    token = os.getenv("HF_API_TOKEN", "").strip()
    model = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2").strip()
    if not model:
        return None

    prompt = (
        "You are an India-focused personal finance advisor. "
        "Based on the JSON below, return 6 to 10 concise bullet recommendations. "
        "Must include tax optimization, SIP allocation, and emergency fund guidance.\n\n"
        f"Financial data:\n{json.dumps(financial_data, ensure_ascii=True, indent=2)}"
    )

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 420,
            "temperature": 0.2,
            "return_full_text": False,
        },
    }
    body = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(
        url=f"https://api-inference.huggingface.co/models/{model}",
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)

        generated_text = ""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            generated_text = str(data[0].get("generated_text", ""))
        elif isinstance(data, dict):
            generated_text = str(data.get("generated_text", ""))

        if not generated_text:
            return None

        recommendations = _extract_recommendation_lines(generated_text, max_items=10)
        recommendations = _ensure_investment_advice(recommendations, financial_data)
        if not recommendations:
            return None

        return {
            "model": f"huggingface:{model}",
            "recommendations": recommendations[:10],
        }
    except error.HTTPError:
        return None
    except Exception:
        return None


def generate_ai_recommendations(financial_data: dict) -> dict:
    """Generate recommendations using configured provider (OpenAI/Hugging Face/fallback)."""
    provider = os.getenv("AI_PROVIDER", "auto").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    if provider == "fallback":
        return _fallback_recommendations(financial_data)

    if provider in {"huggingface", "auto"}:
        hf_result = _generate_with_huggingface(financial_data)
        if hf_result:
            return hf_result

    if provider == "huggingface":
        return _fallback_recommendations(financial_data)

    if not api_key:
        return _fallback_recommendations(financial_data)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        prompt = (
            "Given the following financial data of a couple in India:\n"
            f"{json.dumps(financial_data, ensure_ascii=True, indent=2)}\n\n"
            "Suggest best tax-saving, investment, and financial strategies. "
            "Return concise bullet points tailored to Indian tax rules and couple planning. "
            "Mandatory: include at least 3 investment actions with specific SIP/ELSS/PPF/NPS amounts."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Indian personal finance advisor.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        text = response.choices[0].message.content or ""
        recommendations = _extract_recommendation_lines(text, max_items=8)

        recommendations = _ensure_investment_advice(recommendations, financial_data)

        if not recommendations:
            return _fallback_recommendations(financial_data)

        return {
            "model": model,
            "recommendations": recommendations[:10],
        }
    except Exception:
        return _fallback_recommendations(financial_data)
