"""
Core financial calculation services for India-specific tax optimization
"""

class HRAOptimization:
    """
    HRA Exemption Calculation for India
    Formula: min(HRA received, 50%/40% of salary, rent - 10% of salary)
    """
    
    @staticmethod
    def calculate_hra_exemption(hra_received: float, basic_salary: float, 
                                rent_paid: float, city_type: str = "metro") -> tuple:
        """
        Calculate max HRA exemption and taxable amount
        city_type: "metro" (50%) or "non_metro" (40%)
        Returns: (hra_exemption, hra_taxable, savings)
        """
        
        salary_percentage = 0.50 if city_type == "metro" else 0.40
        salary_limit = basic_salary * salary_percentage
        rent_limit = rent_paid - (basic_salary * 0.10)
        
        # HRA exemption = min of three values
        hra_exemption = min(hra_received, salary_limit, max(0, rent_limit))
        hra_taxable = max(0, hra_received - hra_exemption)
        
        # Tax savings (assuming 30% tax bracket)
        tax_rate = 0.30
        savings = hra_exemption * tax_rate
        
        return hra_exemption, hra_taxable, savings
    
    @staticmethod
    def suggest_partner_optimization(user1_hra: float, user2_hra: float,
                                     user1_salary: float, user2_salary: float,
                                     rent_paid: float, city_type: str = "metro") -> dict:
        """
        Recommend which partner should claim HRA for maximum tax saving
        """
        u1_exemption, u1_taxable, u1_savings = HRAOptimization.calculate_hra_exemption(
            user1_hra, user1_salary, rent_paid, city_type
        )
        
        u2_exemption, u2_taxable, u2_savings = HRAOptimization.calculate_hra_exemption(
            user2_hra, user2_salary, rent_paid, city_type
        )
        
        total_savings = u1_savings + u2_savings
        
        return {
            "recommend_user1_hra": u1_savings >= u2_savings,
            "recommend_user2_hra": u2_savings > u1_savings,
            "user1_potential_saving": u1_savings,
            "user2_potential_saving": u2_savings,
            "total_potential_saving": total_savings,
            "suggestion": f"User {'1' if u1_savings >= u2_savings else '2'} should claim HRA for max saving of ₹{max(u1_savings, u2_savings):.0f}"
        }


class TaxOptimization:
    """
    Old vs New Tax Regime Comparison
    """
    
    OLD_TAX_SLABS = [
        (250000, 0.00),
        (500000, 0.05),
        (1000000, 0.20),
        (float('inf'), 0.30)
    ]
    
    @staticmethod
    def calculate_tax_old_regime(gross_income: float, deductions: float = 0) -> float:
        """
        Calculate tax under old regime with 80C deductions
        Deductions: 80C (₹1.5L), 80CCD(1B) (₹50K), Health Insurance, etc.
        """
        taxable_income = max(0, gross_income - deductions)
        tax = 0
        prev_limit = 0
        
        for limit, rate in TaxOptimization.OLD_TAX_SLABS:
            if taxable_income <= prev_limit:
                break
            taxable_in_slab = min(taxable_income, limit) - prev_limit
            tax += taxable_in_slab * rate
            prev_limit = limit
        
        cess = tax * 0.04  # 4% cess
        return tax + cess
    
    @staticmethod
    def calculate_tax_new_regime(gross_income: float) -> float:
        """
        Calculate tax under new regime (no deductions, lower rates)
        """
        NEW_TAX_SLABS = [
            (300000, 0.00),
            (600000, 0.05),
            (900000, 0.10),
            (1200000, 0.15),
            (1500000, 0.20),
            (float('inf'), 0.30)
        ]
        
        tax = 0
        prev_limit = 0
        
        for limit, rate in NEW_TAX_SLABS:
            if gross_income <= prev_limit:
                break
            taxable_in_slab = min(gross_income, limit) - prev_limit
            tax += taxable_in_slab * rate
            prev_limit = limit
        
        cess = tax * 0.04
        return tax + cess
    
    @staticmethod
    def recommend_tax_regime(gross_income: float, deductions: float = 0) -> dict:
        """
        Compare both regimes and recommend the better one
        """
        old_tax = TaxOptimization.calculate_tax_old_regime(gross_income, deductions)
        new_tax = TaxOptimization.calculate_tax_new_regime(gross_income)
        
        savings = abs(old_tax - new_tax)
        recommended = "old" if old_tax < new_tax else "new"
        
        return {
            "old_regime_tax": old_tax,
            "new_regime_tax": new_tax,
            "recommended_regime": recommended,
            "potential_savings": savings,
            "deductions_to_claim": deductions if recommended == "old" else 0,
            "suggestion": f"Switching to {recommended} regime can save ₹{savings:.0f} in taxes"
        }


class InvestmentAllocator:
    """
    Intelligent SIP allocation based on risk profile and tax optimization
    """
    
    ALLOCATION_MATRIX = {
        "conservative": {
            "elss": 0.20,      # 20% - Tax advantage + Moderate growth
            "ppf": 0.50,       # 50% - Safe, low risk, tax-free returns
            "nps": 0.20,       # 20% - Tax benefit + Retirement corpus
            "other": 0.10      # 10% - Liquid savings
        },
        "moderate": {
            "elss": 0.40,      # 40% - Equity growth + Tax benefit
            "ppf": 0.30,       # 30% - Safe portion
            "nps": 0.20,       # 20% - Retirement benefit
            "other": 0.10
        },
        "aggressive": {
            "elss": 0.60,      # 60% - High growth equity
            "ppf": 0.10,       # 10% - Small safe portion
            "nps": 0.20,       # 20% - Long-term compound
            "other": 0.10
        }
    }
    
    @staticmethod
    def allocate_sip(monthly_savings: float, risk_profile: str = "moderate") -> dict:
        """
        Allocate monthly SIP amount across investment vehicles
        """
        allocation = InvestmentAllocator.ALLOCATION_MATRIX.get(risk_profile, InvestmentAllocator.ALLOCATION_MATRIX["moderate"])
        
        return {
            "monthly_savings": monthly_savings,
            "risk_profile": risk_profile,
            "elss": monthly_savings * allocation["elss"],
            "ppf": monthly_savings * allocation["ppf"],
            "nps": monthly_savings * allocation["nps"],
            "other": monthly_savings * allocation["other"],
            "annual_elss_24_months": monthly_savings * allocation["elss"] * 24,  # 80C limit check
            "annual_nps": monthly_savings * allocation["nps"] * 12,
            "tax_benefit": (monthly_savings * allocation["elss"] * 12) * 0.30  # 80C tax saving
        }
    
    @staticmethod
    def calculate_corpus(monthly_amount: float, annual_return: float, years: int) -> float:
        """
        Calculate SIP corpus using Future Value formula
        FV = PMT × [((1 + r)^n - 1) / r]
        where r is monthly rate, n is number of months
        """
        monthly_rate = annual_return / 100 / 12
        months = years * 12
        
        if monthly_rate == 0:
            return monthly_amount * months
        
        fv = monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        return fv


class NetWorthCalculator:
    """
    Calculate and track couple's combined net worth
    """
    
    @staticmethod
    def calculate_net_worth(assets: list, liabilities: list) -> dict:
        """
        Calculate net worth from assets and liabilities
        assets: [{"name": "Cash", "value": 100000}, ...]
        liabilities: [{"name": "Car Loan", "amount": 500000}, ...]
        """
        total_assets = sum(asset["value"] for asset in assets)
        total_liabilities = sum(liability["amount"] for liability in liabilities)
        net_worth = total_assets - total_liabilities
        
        return {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "net_worth": net_worth
        }
    
    @staticmethod
    def calculate_savings_rate(monthly_income: float, monthly_expenses: float) -> dict:
        """
        Calculate savings rate and monthly savings
        """
        monthly_savings = monthly_income - monthly_expenses
        savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0
        
        return {
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "monthly_savings": max(0, monthly_savings),
            "savings_rate_percentage": max(0, savings_rate)
        }


class InsuranceRecommender:
    """
    Rule-based insurance recommendations
    """
    
    @staticmethod
    def recommend_term_insurance(annual_income: float, dependents: int = 1) -> dict:
        """
        Term insurance = Annual income × 10-15
        Typically: 10x for conservative, 15x for aggressive
        """
        conservative = annual_income * 10
        moderate = annual_income * 12
        aggressive = annual_income * 15
        
        return {
            "conservative_coverage": conservative,
            "moderate_coverage": moderate,
            "aggressive_coverage": aggressive,
            "recommended": moderate,
            "annual_premium_estimate": (moderate * 0.01) / 12,  # Rough estimate
            "suggestion": f"Get ₹{moderate:.0f} term insurance coverage"
        }
    
    @staticmethod
    def recommend_health_insurance(household_size: int, annual_income: float) -> dict:
        """
        Recommend health insurance coverage and type
        """
        coverage_per_person = 500000  # 5 Lakhs per person
        total_coverage = coverage_per_person * household_size
        
        # Check if joint or individual is better
        joint_cost_estimate = total_coverage * 0.005  # 0.5% of coverage
        individual_cost_estimate = total_coverage * 0.006  # 0.6% of coverage
        
        return {
            "total_coverage_needed": total_coverage,
            "coverage_per_person": coverage_per_person,
            "household_size": household_size,
            "recommended_type": "joint" if joint_cost_estimate < individual_cost_estimate else "individual",
            "annual_premium_estimate": min(joint_cost_estimate, individual_cost_estimate),
            "suggestion": f"Joint health insurance with ₹{total_coverage:.0f} coverage is more cost-effective"
        }


class GoalPlanner:
    """
    Track and calculate progress towards financial goals
    """
    
    @staticmethod
    def calculate_monthly_required(target_amount: float, deadline_months: int, 
                                   current_amount: float = 0, annual_return: float = 8) -> dict:
        """
        Calculate monthly SIP needed to reach goal
        Using FV of annuity formula
        """
        remaining_amount = target_amount - current_amount
        monthly_rate = annual_return / 100 / 12
        
        if monthly_rate == 0:
            monthly_required = remaining_amount / deadline_months if deadline_months > 0 else 0
        else:
            # FV = PMT × [((1 + r)^n - 1) / r]
            # PMT = FV / [((1 + r)^n - 1) / r]
            monthly_required = remaining_amount / (((1 + monthly_rate) ** deadline_months - 1) / monthly_rate)
        
        progress = (current_amount / target_amount * 100) if target_amount > 0 else 0
        
        return {
            "target_amount": target_amount,
            "current_amount": current_amount,
            "remaining_amount": max(0, remaining_amount),
            "deadline_months": deadline_months,
            "monthly_required": max(0, monthly_required),
            "progress_percentage": min(100, max(0, progress)),
            "projected_amount": current_amount + (monthly_required * deadline_months)
        }
