from __future__ import annotations

import math
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.ai import generate_ai_recommendations
from utils.hra import calculate_hra, suggest_best_claimant
from utils.investment import (
    calculate_net_worth,
    calculate_savings_score,
    insurance_recommendation,
    suggest_nps_optimization,
    suggest_sip_split,
)
from utils.storage import add_goal, delete_goal, init_db, list_goals, load_latest_profile, save_profile
from utils.storage import authenticate_user, create_user, request_password_reset, reset_password_with_token
from utils.storage import count_users, delete_user_and_data, fetch_table_rows, get_user_overview, list_db_tables
from utils.tax import compare_tax_regime, get_tax_breakdown


st.set_page_config(page_title="Couple's Money Planner", page_icon="IN", layout="wide")


def inject_ui_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-1: #f2f8ff;
            --bg-2: #ffffff;
            --bg-3: #f7fff6;
            --card-bg-1: #ffffff;
            --card-bg-2: #f8fbff;
            --card-border: #dfe7f3;
            --title: #133b5c;
            --sub: #3b5875;
            --kpi-bg: #ffffff;
            --kpi-border: #dbe5f1;
            --kpi-label: #516a87;
            --kpi-value: #102f4a;
            --note-bg: #f5faff;
            --note-text: #34526f;
        }

        .stApp {
            background: radial-gradient(circle at 20% 20%, var(--bg-1) 0%, var(--bg-2) 45%, var(--bg-3) 100%);
        }
        .hero-card {
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 16px 20px;
            background: linear-gradient(135deg, var(--card-bg-1) 0%, var(--card-bg-2) 100%);
            box-shadow: 0 4px 16px rgba(28, 52, 84, 0.08);
            margin-bottom: 10px;
        }
        .hero-title {
            font-size: 22px;
            font-weight: 700;
            color: var(--title);
            margin-bottom: 6px;
        }
        .hero-sub {
            font-size: 14px;
            color: var(--sub);
        }
        .kpi-box {
            border-radius: 14px;
            padding: 12px 14px;
            border: 1px solid var(--kpi-border);
            background: var(--kpi-bg);
            box-shadow: 0 2px 8px rgba(20, 40, 70, 0.08);
            margin-bottom: 8px;
        }
        .kpi-label {
            color: var(--kpi-label);
            font-size: 12px;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }
        .kpi-value {
            color: var(--kpi-value);
            font-size: 22px;
            font-weight: 700;
            margin-top: 2px;
        }
        .section-note {
            border-left: 4px solid #2f80ed;
            background: var(--note-bg);
            padding: 8px 10px;
            border-radius: 8px;
            color: var(--note-text);
            font-size: 13px;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_box(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-box">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def rupee(x: float) -> str:
    return f"Rs {x:,.0f}"


def annual_income(partner: dict) -> float:
    return (
        partner.get("basic", 0.0)
        + partner.get("hra", 0.0)
        + partner.get("bonus", 0.0)
        + partner.get("other_income", 0.0)
    )


def derive_assets_from_profile(profile: dict, years: int = 1, annual_return: float = 0.0) -> dict:
    partner_a = profile.get("partner_a", {})
    partner_b = profile.get("partner_b", {})

    combined_income = annual_income(partner_a) + annual_income(partner_b)
    monthly_expenses = float(partner_a.get("monthly_expense", 0.0)) + float(partner_b.get("monthly_expense", 0.0))
    annual_expenses = monthly_expenses * 12.0
    annual_sip = max(0.0, float(profile.get("total_monthly_sip", 0.0))) * 12.0
    years = max(1, int(years))
    annual_return = max(0.0, float(annual_return))

    # Cash is modeled as what remains after expenses and SIP contributions.
    annual_cash_saving = max(0.0, combined_income - annual_expenses - annual_sip)
    derived_cash = annual_cash_saving * years

    # Existing investments entered by both partners are treated as current corpus.
    starting_investments = max(0.0, float(partner_a.get("investments", 0.0)) + float(partner_b.get("investments", 0.0)))
    if annual_return > 0:
        sip_growth = annual_sip * ((((1 + annual_return) ** years) - 1) / annual_return)
        corpus_growth = starting_investments * ((1 + annual_return) ** years)
        derived_investments = corpus_growth + sip_growth
    else:
        derived_investments = starting_investments + (annual_sip * years)

    return {
        "cash": float(derived_cash),
        "investments": float(derived_investments),
    }


def default_profile() -> dict:
    return {
        "metro": False,
        "partner_a": {
            "name": "",
            "basic": 0.0,
            "hra": 0.0,
            "bonus": 0.0,
            "rent_monthly": 0.0,
            "other_income": 0.0,
            "investments": 0.0,
            "monthly_expense": 0.0,
        },
        "partner_b": {
            "name": "",
            "basic": 0.0,
            "hra": 0.0,
            "bonus": 0.0,
            "rent_monthly": 0.0,
            "other_income": 0.0,
            "investments": 0.0,
            "monthly_expense": 0.0,
        },
        "deductions_a": 0.0,
        "deductions_b": 0.0,
        "total_monthly_sip": 0.0,
        "risk_profile": "moderate",
        "dependents": 0,
    }


def ensure_profile_state(user_id: int) -> None:
    if "profile" not in st.session_state:
        latest = load_latest_profile(user_id)
        st.session_state.profile = latest if latest else default_profile()


def render_authentication() -> None:
    st.title("Couple's Money Planner - Login")
    st.caption("Sign up or log in to access your private financial dashboard")

    login_tab, signup_tab, forgot_tab = st.tabs(["Login", "Sign Up", "Forgot Password"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Login"):
                user = authenticate_user(email, password)
                if user:
                    st.session_state.auth_user = user
                    st.session_state.pop("profile", None)
                    st.success("Login successful.")
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.form_submit_button("Create Account"):
                if password != confirm:
                    st.error("Passwords do not match.")
                else:
                    ok, message = create_user(name, email, password, initial_profile=None)
                    if ok:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)

    with forgot_tab:
        st.caption("Generate a reset token, then use it to set a new password.")
        with st.form("forgot_password_request_form"):
            email_for_token = st.text_input("Registered Email", key="forgot_email")
            if st.form_submit_button("Generate Reset Token"):
                ok, message, token = request_password_reset(email_for_token)
                if ok and token:
                    st.success(message)
                    st.info(f"Your reset token: {token}")
                else:
                    st.error(message)

        with st.form("forgot_password_reset_form"):
            reset_email = st.text_input("Email", key="reset_email")
            reset_token = st.text_input("Reset Token", key="reset_token")
            new_password = st.text_input("New Password", type="password", key="reset_new_password")
            confirm_new_password = st.text_input(
                "Confirm New Password",
                type="password",
                key="reset_confirm_new_password",
            )
            if st.form_submit_button("Reset Password"):
                if new_password != confirm_new_password:
                    st.error("Passwords do not match.")
                else:
                    ok, message = reset_password_with_token(reset_email, reset_token, new_password)
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)


init_db()
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    render_authentication()
    st.stop()

ensure_profile_state(st.session_state.auth_user["id"])
inject_ui_styles()

if "assets" not in st.session_state:
    derived_assets = derive_assets_from_profile(st.session_state.profile)
    st.session_state.assets = {
        "cash": derived_assets["cash"],
        "investments": derived_assets["investments"],
        "property": 0.0,
    }
if "liabilities" not in st.session_state:
    st.session_state.liabilities = {
        "home_loan": 2500000.0,
        "other_loans": 300000.0,
    }

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">Couple's Money Planner</div>
        <div class="hero-sub">India-focused joint financial planning with tax optimization, investment strategy, and AI-driven suggestions.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.success(f"Logged in as: {st.session_state.auth_user['name']}")

overview = get_user_overview(st.session_state.auth_user["id"])
st.sidebar.markdown("### Account Center")
st.sidebar.caption(f"Email: {st.session_state.auth_user['email']}")
st.sidebar.caption(f"Total registered users: {count_users()}")
st.sidebar.caption(f"Your saved profiles: {overview['profiles']}")
st.sidebar.caption(f"Your goals: {overview['goals']}")

with st.sidebar.expander("Add another user"):
    with st.form("sidebar_signup_form"):
        su_name = st.text_input("Name", key="sidebar_signup_name")
        su_email = st.text_input("Email", key="sidebar_signup_email")
        su_pass = st.text_input("Password", type="password", key="sidebar_signup_password")
        if st.form_submit_button("Add user"):
            ok, msg = create_user(su_name, su_email, su_pass, initial_profile=None)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

with st.sidebar.expander("Forgot Password"):
    st.caption("Generate a reset token and set a new password.")
    with st.form("sidebar_forgot_password_request_form"):
        fp_email = st.text_input("Registered Email", key="sidebar_forgot_email")
        if st.form_submit_button("Generate Reset Token"):
            ok, message, token = request_password_reset(fp_email)
            if ok and token:
                st.success(message)
                st.info(f"Reset token: {token}")
            else:
                st.error(message)

    with st.form("sidebar_forgot_password_reset_form"):
        fp_reset_email = st.text_input("Email", key="sidebar_reset_email")
        fp_token = st.text_input("Reset Token", key="sidebar_reset_token")
        fp_new_password = st.text_input("New Password", type="password", key="sidebar_reset_new_password")
        fp_confirm_password = st.text_input(
            "Confirm New Password",
            type="password",
            key="sidebar_reset_confirm_new_password",
        )
        if st.form_submit_button("Reset Password"):
            if fp_new_password != fp_confirm_password:
                st.error("Passwords do not match.")
            else:
                ok, message = reset_password_with_token(fp_reset_email, fp_token, fp_new_password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)

with st.sidebar.expander("Delete Account"):
    st.warning("This permanently deletes this user account and all related goals/profiles.")
    confirm_delete = st.checkbox("I understand, delete this account", key="confirm_delete_user")
    if st.button("Delete Account", key="delete_user_btn", type="secondary", disabled=not confirm_delete):
        delete_user_and_data(st.session_state.auth_user["id"])
        st.session_state.auth_user = None
        st.session_state.pop("profile", None)
        st.success("Account deleted.")
        st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.auth_user = None
    st.session_state.pop("profile", None)
    st.rerun()

with st.sidebar.expander("Admin Table Viewer"):
    st.caption("Read-only view of database tables.")
    available_tables = list_db_tables()
    if available_tables:
        selected_table = st.selectbox("Table", options=available_tables, key="admin_table_name")
        row_limit = st.slider("Rows", min_value=10, max_value=200, value=25, step=5, key="admin_table_limit")
        columns, rows = fetch_table_rows(selected_table, row_limit)
        if columns:
            st.caption(f"Showing {len(rows)} row(s) from {selected_table}")
            st.dataframe(pd.DataFrame(rows, columns=columns), use_container_width=True)
        else:
            st.info("No rows found for selected table.")
    else:
        st.info("No database tables available.")


tab_input, tab_tax, tab_invest, tab_dashboard, tab_ai = st.tabs(
    ["Input", "Tax Optimization", "Investments", "Dashboard", "AI Suggestions"]
)

with tab_input:
    st.subheader("Partner Input Section")
    with st.form("partner_input_form"):
        metro = st.checkbox("Metro City", value=st.session_state.profile.get("metro", True))
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### Partner A")
            a_name = st.text_input("Name A", value=st.session_state.profile["partner_a"]["name"])
            a_basic = st.number_input("Basic Salary A (annual)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["basic"]))
            a_hra = st.number_input("HRA A (annual)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["hra"]))
            a_bonus = st.number_input("Bonus A (annual)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["bonus"]))
            a_rent = st.number_input("Rent A (monthly)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["rent_monthly"]))
            a_other = st.number_input("Other Income A (annual)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["other_income"]))
            a_inv = st.number_input("Existing Investments A (annual)", min_value=0.0, value=float(st.session_state.profile["partner_a"]["investments"]))
            a_exp = st.number_input("Monthly Expense A", min_value=0.0, value=float(st.session_state.profile["partner_a"]["monthly_expense"]))

        with col_b:
            st.markdown("### Partner B")
            b_name = st.text_input("Name B", value=st.session_state.profile["partner_b"]["name"])
            b_basic = st.number_input("Basic Salary B (annual)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["basic"]))
            b_hra = st.number_input("HRA B (annual)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["hra"]))
            b_bonus = st.number_input("Bonus B (annual)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["bonus"]))
            b_rent = st.number_input("Rent B (monthly)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["rent_monthly"]))
            b_other = st.number_input("Other Income B (annual)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["other_income"]))
            b_inv = st.number_input("Existing Investments B (annual)", min_value=0.0, value=float(st.session_state.profile["partner_b"]["investments"]))
            b_exp = st.number_input("Monthly Expense B", min_value=0.0, value=float(st.session_state.profile["partner_b"]["monthly_expense"]))

        col3, col4, col5, col6 = st.columns(4)
        ded_a = col3.number_input("Deductions A (annual)", min_value=0.0, value=float(st.session_state.profile.get("deductions_a", 150000.0)))
        ded_b = col4.number_input("Deductions B (annual)", min_value=0.0, value=float(st.session_state.profile.get("deductions_b", 120000.0)))
        sip_total = col5.number_input("Total Monthly SIP", min_value=0.0, value=float(st.session_state.profile.get("total_monthly_sip", 30000.0)))
        dependents = int(col6.number_input("Dependents", min_value=0, value=int(st.session_state.profile.get("dependents", 1))))

        risk_profile = st.selectbox(
            "Risk Profile",
            ["conservative", "moderate", "aggressive"],
            index=["conservative", "moderate", "aggressive"].index(st.session_state.profile.get("risk_profile", "moderate")),
        )

        action_col1, action_col2, action_col3 = st.columns(3)
        submitted = action_col1.form_submit_button("Save Partner Data", use_container_width=True)
        reload_saved = action_col2.form_submit_button("Reload Last Saved", use_container_width=True)
        reset_defaults = action_col3.form_submit_button("Reset to Defaults", use_container_width=True)

        if submitted:
            new_profile = {
                "metro": metro,
                "partner_a": {
                    "name": a_name,
                    "basic": a_basic,
                    "hra": a_hra,
                    "bonus": a_bonus,
                    "rent_monthly": a_rent,
                    "other_income": a_other,
                    "investments": a_inv,
                    "monthly_expense": a_exp,
                },
                "partner_b": {
                    "name": b_name,
                    "basic": b_basic,
                    "hra": b_hra,
                    "bonus": b_bonus,
                    "rent_monthly": b_rent,
                    "other_income": b_other,
                    "investments": b_inv,
                    "monthly_expense": b_exp,
                },
                "deductions_a": ded_a,
                "deductions_b": ded_b,
                "total_monthly_sip": sip_total,
                "risk_profile": risk_profile,
                "dependents": dependents,
            }
            st.session_state.profile = new_profile
            derived_assets = derive_assets_from_profile(new_profile)
            st.session_state.assets["cash"] = derived_assets["cash"]
            st.session_state.assets["investments"] = derived_assets["investments"]
            save_profile(st.session_state.profile, st.session_state.auth_user["id"])
            st.success("Partner data saved.")
        elif reload_saved:
            latest = load_latest_profile(st.session_state.auth_user["id"])
            st.session_state.profile = latest if latest else default_profile()
            derived_assets = derive_assets_from_profile(st.session_state.profile)
            st.session_state.assets["cash"] = derived_assets["cash"]
            st.session_state.assets["investments"] = derived_assets["investments"]
            st.info("Reloaded your latest saved values.")
            st.rerun()
        elif reset_defaults:
            st.session_state.profile = default_profile()
            derived_assets = derive_assets_from_profile(st.session_state.profile)
            st.session_state.assets["cash"] = derived_assets["cash"]
            st.session_state.assets["investments"] = derived_assets["investments"]
            st.session_state.assets["property"] = 0.0
            st.info("Reset values to defaults. Click Save Partner Data to store them.")
            st.rerun()

profile = st.session_state.profile
partner_a = profile["partner_a"]
partner_b = profile["partner_b"]
metro = profile["metro"]

a_income = annual_income(partner_a)
b_income = annual_income(partner_b)
combined_income = a_income + b_income
combined_rent_annual = (partner_a["rent_monthly"] + partner_b["rent_monthly"]) * 12

hra_a = calculate_hra(partner_a["hra"], partner_a["basic"], partner_a["rent_monthly"] * 12, metro)
hra_b = calculate_hra(partner_b["hra"], partner_b["basic"], partner_b["rent_monthly"] * 12, metro)
hra_suggest = suggest_best_claimant(hra_a, hra_b)

tax_a = compare_tax_regime(a_income, profile["deductions_a"])
tax_b = compare_tax_regime(b_income, profile["deductions_b"])
sip_plan = suggest_sip_split(
    total_monthly_sip=profile["total_monthly_sip"],
    partner_a_income=a_income,
    partner_b_income=b_income,
    risk_profile=profile["risk_profile"],
)
ins = insurance_recommendation(a_income, b_income, profile["dependents"])

assets = [
    {"name": "Cash", "value": st.session_state.assets["cash"]},
    {"name": "Investments", "value": st.session_state.assets["investments"]},
    {"name": "Property", "value": st.session_state.assets["property"]},
]
liabilities = [
    {"name": "Home Loan", "value": st.session_state.liabilities["home_loan"]},
    {"name": "Other Loans", "value": st.session_state.liabilities["other_loans"]},
]
net = calculate_net_worth(assets, liabilities)
total_expenses = (partner_a["monthly_expense"] + partner_b["monthly_expense"]) * 12
annual_surplus = combined_income - total_expenses
savings_rate = 0.0 if combined_income <= 0 else (annual_surplus / combined_income) * 100

# Global KPI strip for quick understanding of financial health.
k1, k2, k3, k4 = st.columns(4)
with k1:
    render_kpi_box("Combined Annual Income", rupee(combined_income))
with k2:
    render_kpi_box("Annual Surplus", rupee(max(0.0, annual_surplus)))
with k3:
    render_kpi_box("Current Net Worth", rupee(net["net_worth"]))
with k4:
    render_kpi_box("Savings Rate", f"{savings_rate:.1f}%")

st.markdown('<div class="section-note">Tip: Update values in Input and Dashboard tabs to instantly refresh all calculations and visuals.</div>', unsafe_allow_html=True)

with tab_tax:
    st.subheader("HRA Calculator (India-specific)")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"HRA Exemption - {partner_a['name']}", rupee(hra_a["hra_exemption"]))
    c2.metric(f"HRA Exemption - {partner_b['name']}", rupee(hra_b["hra_exemption"]))
    c3.metric("Best Claimant", hra_suggest["best_claimant"])

    st.info(
        f"Estimated tax saving if optimized: {rupee(hra_suggest['best_possible_saving'])}"
    )

    st.subheader("Tax Comparison (Old vs New)")
    st.caption("Deductions are applied to Old Regime. New Regime is shown without these deductions for comparison.")
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"### {partner_a['name']}")
        st.caption(f"Old taxable income after deductions: {rupee(tax_a['old_taxable_income'])}")
        st.write(f"Old Regime: {rupee(tax_a['old_regime_tax'])}")
        st.write(f"New Regime: {rupee(tax_a['new_regime_tax'])}")
        st.success(
            f"Best: {tax_a['recommended_regime'].upper()} | Savings: {rupee(tax_a['potential_savings'])}"
        )

    with t2:
        st.markdown(f"### {partner_b['name']}")
        st.caption(f"Old taxable income after deductions: {rupee(tax_b['old_taxable_income'])}")
        st.write(f"Old Regime: {rupee(tax_b['old_regime_tax'])}")
        st.write(f"New Regime: {rupee(tax_b['new_regime_tax'])}")
        st.success(
            f"Best: {tax_b['recommended_regime'].upper()} | Savings: {rupee(tax_b['potential_savings'])}"
        )

    tax_df = pd.DataFrame(
        {
            "Partner": [partner_a["name"], partner_a["name"], partner_b["name"], partner_b["name"]],
            "Regime": ["Old", "New", "Old", "New"],
            "Tax": [tax_a["old_regime_tax"], tax_a["new_regime_tax"], tax_b["old_regime_tax"], tax_b["new_regime_tax"]],
        }
    )
    st.plotly_chart(
        px.bar(tax_df, x="Partner", y="Tax", color="Regime", barmode="group", title="Old vs New Regime Tax"),
        use_container_width=True,
    )

    st.subheader("Tax Breakdown (Slab-wise)")
    st.caption("Shows exact slab tax, rebate, cess, and total for the currently recommended regime.")

    partner_a_breakdown = get_tax_breakdown(
        a_income,
        profile["deductions_a"],
        regime=tax_a["recommended_regime"],
    )
    partner_b_breakdown = get_tax_breakdown(
        b_income,
        profile["deductions_b"],
        regime=tax_b["recommended_regime"],
    )

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f"#### {partner_a['name']} ({partner_a_breakdown['regime'].upper()} Regime)")
        st.dataframe(pd.DataFrame(partner_a_breakdown["rows"]), use_container_width=True)
        st.write(f"Taxable Income: {rupee(partner_a_breakdown['taxable_income'])}")
        st.write(f"Base Tax: {rupee(partner_a_breakdown['base_tax'])}")
        st.write(f"Rebate: {rupee(partner_a_breakdown['rebate'])}")
        st.write(f"Cess (4%): {rupee(partner_a_breakdown['cess'])}")
        st.success(f"Final Tax: {rupee(partner_a_breakdown['total_tax'])}")

    with b2:
        st.markdown(f"#### {partner_b['name']} ({partner_b_breakdown['regime'].upper()} Regime)")
        st.dataframe(pd.DataFrame(partner_b_breakdown["rows"]), use_container_width=True)
        st.write(f"Taxable Income: {rupee(partner_b_breakdown['taxable_income'])}")
        st.write(f"Base Tax: {rupee(partner_b_breakdown['base_tax'])}")
        st.write(f"Rebate: {rupee(partner_b_breakdown['rebate'])}")
        st.write(f"Cess (4%): {rupee(partner_b_breakdown['cess'])}")
        st.success(f"Final Tax: {rupee(partner_b_breakdown['total_tax'])}")

    with st.expander("What-if tax planner"):
        w1, w2 = st.columns(2)
        scenario_ded_a = w1.slider("Scenario Deductions A", min_value=0, max_value=300000, value=int(profile["deductions_a"]), step=5000)
        scenario_ded_b = w2.slider("Scenario Deductions B", min_value=0, max_value=300000, value=int(profile["deductions_b"]), step=5000)
        sc_a = compare_tax_regime(a_income, float(scenario_ded_a))
        sc_b = compare_tax_regime(b_income, float(scenario_ded_b))
        st.write(
            f"Scenario savings: {partner_a['name']} {rupee(sc_a['potential_savings'])} + "
            f"{partner_b['name']} {rupee(sc_b['potential_savings'])}"
        )

        scenario_df = pd.DataFrame(
            {
                "Scenario": ["Current", "What-if"],
                "Combined Tax": [
                    tax_a["recommended_tax"] + tax_b["recommended_tax"],
                    sc_a["recommended_tax"] + sc_b["recommended_tax"],
                ],
            }
        )
        st.plotly_chart(
            px.line(scenario_df, x="Scenario", y="Combined Tax", markers=True, title="Combined Tax Impact"),
            use_container_width=True,
        )

with tab_invest:
    st.subheader("Investment Planner")

    c1, c2 = st.columns(2)
    c1.metric(f"Monthly SIP - {partner_a['name']}", rupee(sip_plan["partner_a_monthly_sip"]))
    c2.metric(f"Monthly SIP - {partner_b['name']}", rupee(sip_plan["partner_b_monthly_sip"]))

    alloc_df = pd.DataFrame(
        {
            "Instrument": list(sip_plan["allocation_amounts"].keys()),
            "Amount": list(sip_plan["allocation_amounts"].values()),
        }
    )
    fig_alloc = px.pie(alloc_df, names="Instrument", values="Amount", title="Monthly Investment Distribution")
    st.plotly_chart(fig_alloc, use_container_width=True)

    sip_ratio_df = pd.DataFrame(
        {
            "Partner": [partner_a["name"], partner_b["name"]],
            "Monthly SIP": [sip_plan["partner_a_monthly_sip"], sip_plan["partner_b_monthly_sip"]],
        }
    )
    st.plotly_chart(
        px.bar(sip_ratio_df, x="Partner", y="Monthly SIP", title="SIP Split by Income Ratio"),
        use_container_width=True,
    )

    with st.expander("SIP growth simulator"):
        sim_col1, sim_col2 = st.columns(2)
        expected_return = sim_col1.slider("Expected annual return (%)", min_value=1.0, max_value=20.0, value=10.0, step=0.5)
        years = sim_col2.slider("Investment horizon (years)", min_value=1, max_value=30, value=10)
        month_rate = expected_return / 100 / 12
        months = years * 12
        monthly = profile["total_monthly_sip"]
        corpus = monthly * (((1 + month_rate) ** months - 1) / month_rate) if month_rate > 0 else monthly * months
        st.success(f"Projected corpus in {years} years: {rupee(corpus)}")

        growth_points = []
        for y in range(1, years + 1):
            m = y * 12
            val = monthly * (((1 + month_rate) ** m - 1) / month_rate) if month_rate > 0 else monthly * m
            growth_points.append({"Year": y, "Corpus": val})
        growth_df = pd.DataFrame(growth_points)
        st.plotly_chart(px.area(growth_df, x="Year", y="Corpus", title="Projected SIP Corpus Growth"), use_container_width=True)

    st.subheader("NPS Optimization")
    nps_cap = 50000.0
    nps_a = suggest_nps_optimization(a_income)
    nps_b = suggest_nps_optimization(b_income)

    ded_a_current = float(profile.get("deductions_a", 0.0))
    ded_b_current = float(profile.get("deductions_b", 0.0))
    ded_a_with_nps = ded_a_current + nps_cap
    ded_b_with_nps = ded_b_current + nps_cap

    old_tax_a_current = compare_tax_regime(a_income, ded_a_current)["old_regime_tax"]
    old_tax_b_current = compare_tax_regime(b_income, ded_b_current)["old_regime_tax"]
    old_tax_a_nps = compare_tax_regime(a_income, ded_a_with_nps)["old_regime_tax"]
    old_tax_b_nps = compare_tax_regime(b_income, ded_b_with_nps)["old_regime_tax"]

    nps_saving_a = max(0.0, old_tax_a_current - old_tax_a_nps)
    nps_saving_b = max(0.0, old_tax_b_current - old_tax_b_nps)

    n1, n2 = st.columns(2)
    n1.info(
        f"{partner_a['name']}: Current deductions {rupee(ded_a_current)} -> with NPS {rupee(ded_a_with_nps)} | "
        f"Extra deduction {rupee(nps_cap)} | Estimated tax saving {rupee(nps_saving_a)}"
    )
    n2.info(
        f"{partner_b['name']}: Current deductions {rupee(ded_b_current)} -> with NPS {rupee(ded_b_with_nps)} | "
        f"Extra deduction {rupee(nps_cap)} | Estimated tax saving {rupee(nps_saving_b)}"
    )
    st.caption(
        "NPS benefit is computed as incremental Old Regime tax reduction after adding extra Rs 50,000 deduction under Section 80CCD(1B)."
    )

    st.subheader("Insurance Suggestion")
    i1, i2, i3 = st.columns(3)
    i1.metric("Term Cover Partner A", rupee(ins["term_partner_a"]))
    i2.metric("Term Cover Partner B", rupee(ins["term_partner_b"]))
    i3.metric("Health Policy Type", ins["health_policy_type"].title())
    st.write(f"Recommended health cover: {rupee(ins['health_cover_recommended'])}")

with tab_dashboard:
    st.subheader("Net Worth Dashboard")

    st.markdown("#### Projection Settings")
    p1, p2 = st.columns(2)
    projection_years = p1.slider("Projection Horizon (years)", min_value=1, max_value=30, value=1, step=1)
    expected_return = p2.slider(
        "Expected Annual Return on Investments (%)",
        min_value=0.0,
        max_value=20.0,
        value=10.0,
        step=0.5,
    )

    computed_assets = derive_assets_from_profile(
        profile,
        years=projection_years,
        annual_return=expected_return / 100.0,
    )

    st.markdown("#### Assets (Auto-calculated from Partner Input)")
    a1, a2, a3 = st.columns(3)
    a1.metric("Cash Saved", rupee(computed_assets["cash"]))
    a2.metric("Investments (Existing + SIP)", rupee(computed_assets["investments"]))
    st.session_state.assets["property"] = a3.number_input(
        "Property", min_value=0.0, value=float(st.session_state.assets["property"])
    )

    st.markdown("#### Liabilities")
    l1, l2 = st.columns(2)
    st.session_state.liabilities["home_loan"] = l1.number_input(
        "Home Loan", min_value=0.0, value=float(st.session_state.liabilities["home_loan"])
    )
    st.session_state.liabilities["other_loans"] = l2.number_input(
        "Other Loans", min_value=0.0, value=float(st.session_state.liabilities["other_loans"])
    )

    assets = [
        {"name": "Cash", "value": computed_assets["cash"]},
        {"name": "Investments", "value": computed_assets["investments"]},
        {"name": "Property", "value": st.session_state.assets["property"]},
    ]
    liabilities = [
        {"name": "Home Loan", "value": st.session_state.liabilities["home_loan"]},
        {"name": "Other Loans", "value": st.session_state.liabilities["other_loans"]},
    ]
    net = calculate_net_worth(assets, liabilities)

    d1, d2, d3 = st.columns(3)
    d1.metric(f"Combined Net Worth ({projection_years}Y)", rupee(net["net_worth"]))
    d2.metric("Annual Savings Rate", f"{savings_rate:.1f}%")
    d3.metric("Annual Surplus", rupee(max(0.0, annual_surplus)))

    emergency_months = 0.0
    if (partner_a["monthly_expense"] + partner_b["monthly_expense"]) > 0:
        emergency_months = computed_assets["cash"] / (partner_a["monthly_expense"] + partner_b["monthly_expense"])

    tax_optimized = tax_a["potential_savings"] + tax_b["potential_savings"] > 0
    insurance_covered = ins["term_combined"] >= combined_income * 10
    score = calculate_savings_score(savings_rate, emergency_months, insurance_covered, tax_optimized)
    st.progress(score / 100)
    st.caption(f"Savings Score: {score}/100")

    chart_df = pd.DataFrame(
        {
            "Category": ["Assets", "Liabilities"],
            "Amount": [net["total_assets"], net["total_liabilities"]],
        }
    )
    st.plotly_chart(
        px.bar(chart_df, x="Category", y="Amount", title="Assets vs Liabilities", color="Category"),
        use_container_width=True,
    )

    ie_df = pd.DataFrame(
        {
            "Type": ["Income", "Expenses", "Savings"],
            "Amount": [combined_income, total_expenses, max(0.0, annual_surplus)],
        }
    )
    st.plotly_chart(px.pie(ie_df, names="Type", values="Amount", title="Income vs Expenses vs Savings"), use_container_width=True)

    st.subheader("Financial Goals")
    with st.form("goal_form"):
        g1, g2, g3, g4 = st.columns(4)
        goal_name = g1.text_input("Goal Name", value="House")
        goal_target = g2.number_input("Target Amount", min_value=1.0, value=2000000.0)
        goal_current = g3.number_input("Current Amount", min_value=0.0, value=200000.0)
        goal_monthly = g4.number_input("Monthly Contribution", min_value=0.0, value=25000.0)

        remaining_amount = max(0.0, float(goal_target) - float(goal_current))
        if remaining_amount <= 0:
            calculated_months = 0
            st.caption("This goal is already achieved based on current amount.")
        elif goal_monthly > 0:
            calculated_months = int(math.ceil(remaining_amount / float(goal_monthly)))
            st.caption(f"Auto-calculated target months: {calculated_months}")
        else:
            calculated_months = None
            st.warning("Monthly contribution must be greater than 0 to calculate target months.")

        if st.form_submit_button("Add Goal"):
            if calculated_months is None:
                st.error("Cannot add goal: set monthly contribution greater than 0.")
            else:
                add_goal(
                    goal_name,
                    goal_target,
                    goal_current,
                    goal_monthly,
                    int(calculated_months),
                    st.session_state.auth_user["id"],
                )
                st.success(f"Goal added. Estimated time to target: {calculated_months} month(s).")

    goals = list_goals(st.session_state.auth_user["id"])
    if goals:
        goals_df = pd.DataFrame(goals)
        st.dataframe(goals_df[["name", "target_amount", "current_amount", "monthly_contribution", "target_months", "progress"]], use_container_width=True)
        st.plotly_chart(px.bar(goals_df, x="name", y="progress", title="Goal Progress (%)"), use_container_width=True)

        st.markdown("### Manage Goals")
        mg_col1, mg_col2 = st.columns([2, 1])
        selected_goal_id = mg_col1.selectbox(
            "Choose goal to delete",
            options=[goal["id"] for goal in goals],
            format_func=lambda gid: next(
                (
                    f"{goal['name']} - {rupee(goal['target_amount'])} target"
                    for goal in goals
                    if goal["id"] == gid
                ),
                str(gid),
            ),
            key="delete_goal_select",
        )
        confirm_goal_delete = mg_col1.checkbox(
            "I understand this goal will be permanently deleted",
            key="confirm_delete_goal",
        )
        delete_clicked = mg_col2.button(
            "Delete Selected Goal",
            key="delete_goal_btn",
            type="secondary",
            use_container_width=True,
            disabled=not confirm_goal_delete,
        )
        if delete_clicked:
            was_deleted = delete_goal(int(selected_goal_id), st.session_state.auth_user["id"])
            if was_deleted:
                st.success("Goal deleted from database and dashboard.")
                st.rerun()
            else:
                st.error("Could not delete goal. Please try again.")
    else:
        st.info("No goals added yet.")

with tab_ai:
    st.subheader("AI Recommendation Section")

    tax_savings_total = tax_a["potential_savings"] + tax_b["potential_savings"]
    before_tax = tax_a["old_regime_tax"] + tax_b["old_regime_tax"]
    after_tax = before_tax - tax_savings_total

    before_after = pd.DataFrame(
        {
            "Scenario": ["Before Optimization", "After Optimization"],
            "Tax Outgo": [before_tax, max(0.0, after_tax)],
        }
    )
    st.plotly_chart(px.bar(before_after, x="Scenario", y="Tax Outgo", title="Before vs After Optimization"), use_container_width=True)

    payload = {
        "partner_a": partner_a,
        "partner_b": partner_b,
        "goals": list_goals(st.session_state.auth_user["id"]),
        "metro": metro,
        "total_income": combined_income,
        "total_rent": combined_rent_annual,
        "existing_investments_total": float(partner_a.get("investments", 0.0) + partner_b.get("investments", 0.0)),
        "hra_best_claimant": hra_suggest["best_claimant"],
        "tax_recommendation_a": tax_a["recommended_regime"],
        "tax_recommendation_b": tax_b["recommended_regime"],
        "tax_savings_total": tax_savings_total,
        "total_monthly_sip": profile["total_monthly_sip"],
        "risk_profile": profile["risk_profile"],
        "sip_split": sip_plan,
        "net_worth": net,
        "savings_rate": savings_rate,
    }

    if st.button("Generate AI Suggestions"):
        ai_result = generate_ai_recommendations(payload)
        st.success(f"Model: {ai_result['model']}")
        for idx, item in enumerate(ai_result["recommendations"], start=1):
            st.markdown(f"**{idx}.** {item}")

        investment_lines = [
            line for line in ai_result["recommendations"] if any(k in line.lower() for k in ["sip", "elss", "ppf", "nps", "invest"])
        ]
        if investment_lines:
            st.info("Top investment-focused suggestions")
            for line in investment_lines[:3]:
                st.write(f"- {line}")

st.markdown("---")
st.caption("Run command: streamlit run main.py")
