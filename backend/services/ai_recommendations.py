"""
AI-powered recommendation engine using OpenAI API
"""
import json
from typing import List, Optional

class AIRecommendationEngine:
    """
    Generate AI-powered financial recommendations using OpenAI API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        
        if api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                print("OpenAI SDK not installed. Using fallback recommendations.")
    
    def generate_recommendations(self, financial_data: dict) -> dict:
        """
        Generate personalized recommendations based on financial data
        
        financial_data should contain:
        - gross_income
        - current_savings
        - tax_regime
        - hra_received
        - investments
        - net_worth
        - goals
        """
        
        if self.client:
            return self._generate_with_openai(financial_data)
        else:
            return self._generate_fallback_recommendations(financial_data)
    
    def _generate_with_openai(self, financial_data: dict) -> dict:
        """Generate recommendations using OpenAI API"""
        try:
            prompt = self._build_prompt(financial_data)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an India-focused financial advisor. Provide specific, actionable recommendations for tax optimization, investments, and financial planning."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            recommendations_text = response.choices[0].message.content
            return self._parse_recommendations(recommendations_text)
        
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._generate_fallback_recommendations(financial_data)
    
    def _build_prompt(self, financial_data: dict) -> str:
        """Build prompt for OpenAI"""
        return f"""
        Analyze this financial profile and provide 5-7 specific recommendations:
        
        Annual Gross Income: ₹{financial_data.get('gross_income', 0)}
        Current Tax Regime: {financial_data.get('tax_regime', 'old')}
        HRA Received: ₹{financial_data.get('hra_received', 0)}
        Rent Paid: ₹{financial_data.get('rent_paid', 0)}
        Current Savings: ₹{financial_data.get('current_savings', 0)}
        Monthly Savings Capacity: ₹{financial_data.get('monthly_savings', 0)}
        Current Investments: {json.dumps(financial_data.get('investments', {}))}
        Net Worth: ₹{financial_data.get('net_worth', 0)}
        Financial Goals: {json.dumps(financial_data.get('goals', []))}
        
        Provide recommendations in this format:
        1. [Recommendation]
        2. [Recommendation]
        etc.
        
        Also include potential annual savings achievable through all recommendations.
        """
    
    def _parse_recommendations(self, text: str) -> dict:
        """Parse OpenAI response into structured format"""
        recommendations = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and line[0].isdigit():
                # Remove numbering and clean up
                rec = line.split('.', 1)[-1].strip()
                if rec:
                    recommendations.append(rec)
        
        # Extract potential savings if mentioned
        potential_savings = 0
        for line in lines:
            if "saving" in line.lower() and "₹" in line:
                try:
                    # Simple extraction of rupee amounts
                    import re
                    amounts = re.findall(r'₹\s*([\d,]+)', line)
                    if amounts:
                        potential_savings = float(amounts[-1].replace(',', ''))
                        break
                except:
                    pass
        
        return {
            "recommendations": recommendations[:7],
            "total_potential_savings": potential_savings,
            "priority": ["HRA Optimization", "Tax Regime Selection", "Investment Planning"]
        }
    
    def _generate_fallback_recommendations(self, financial_data: dict) -> dict:
        """Generate recommendations without OpenAI (fallback logic)"""
        recommendations = []
        potential_savings = 0
        
        gross_income = financial_data.get('gross_income', 0)
        tax_regime = financial_data.get('tax_regime', 'old')
        hra_received = financial_data.get('hra_received', 0)
        monthly_savings = financial_data.get('monthly_savings', 0)
        current_investments = financial_data.get('current_investments', 0)
        
        # Rule 1: HRA Optimization
        if hra_received > 0:
            recommendations.append("✓ Ensure HRA exemption is maximized - claim min(HRA, 50% salary, rent-10% salary)")
            potential_savings += hra_received * 0.30  # 30% tax saving
        
        # Rule 2: Tax Regime
        if tax_regime == "old":
            potential_80c = 150000  # 80C max
            tax_saving = potential_80c * 0.30
            recommendations.append(f"→ Consider switching to new tax regime for saving up to ₹{tax_saving:.0f} if no deductions claimed")
        
        # Rule 3: SIP Investment
        if monthly_savings > 5000:
            elss_amount = monthly_savings * 0.40
            annual_elss = elss_amount * 12
            if annual_elss <= 150000:
                tax_benefit = annual_elss * 0.30
                recommendations.append(f"→ Invest ₹{elss_amount:.0f}/month in ELSS for ₹{tax_benefit:.0f} tax saving + growth")
                potential_savings += tax_benefit
        
        # Rule 4: NPS
        nps_deduction = 50000  # 80CCD(1B)
        nps_saving = nps_deduction * 0.30
        recommendations.append(f"→ Add ₹50,000/year to NPS (80CCD 1B) for tax saving of ₹{nps_saving:.0f}")
        potential_savings += nps_saving
        
        # Rule 5: PPF
        if current_investments < 500000:
            recommendations.append("→ Open PPF account (7.5% returns + tax-free) - invest ₹10,000-15,000/year")
        
        # Rule 6: Insurance
        term_coverage = gross_income * 12  # 12x annual income
        recommendations.append(f"→ Buy term insurance of ₹{term_coverage:.0f} (covers ~12 years income)")
        
        # Rule 7: Emergency Fund
        if monthly_savings > 0:
            recommendations.append("→ Build 6-12 months emergency fund in savings account before investing")
        
        return {
            "recommendations": recommendations[:7],
            "total_potential_savings": potential_savings,
            "priority": ["HRA Optimization", "Tax Regime Selection", "Investment Planning", "NPS & Insurance"]
        }
