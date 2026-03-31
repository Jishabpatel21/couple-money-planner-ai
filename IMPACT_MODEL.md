# Couple's Money Planner: Impact Model

## Objective

Estimate business impact from deploying the Couple's Money Planner in terms of:
- Time saved
- Cost reduced
- Revenue recovered

This is a back-of-envelope model with explicit assumptions and traceable math.

## Assumptions

1. Monthly active couples: 1,200
2. Baseline manual planning effort: 90 minutes per couple per month
3. Effort after product adoption: 25 minutes per couple per month
4. Advisor or analyst blended cost: Rs 800 per hour
5. Recommendation adoption rate: 35% of active couples
6. Average annual financial benefit for adopters (tax + better allocation): Rs 18,000 per couple
7. Paid customer base: 1,500 users
8. ARPU: Rs 299 per month
9. Annual churn before reliability controls: 5.0%
10. Annual churn after reliability controls (AI fallback + graceful degradation): 2.0%

## 1) Time Saved

### Formula

- Time saved per couple per month = 90 - 25 = 65 minutes
- Total minutes saved per month = 1,200 x 65 = 78,000 minutes
- Total hours saved per month = 78,000 / 60 = 1,300 hours

### Result

- Time saved: 1,300 hours per month
- Time saved: 15,600 hours per year

## 2) Cost Reduced

### Formula

- Monthly operating cost reduction = 1,300 hours x Rs 800 = Rs 1,040,000
- Annual operating cost reduction = Rs 1,040,000 x 12 = Rs 12,480,000

### Result

- Cost reduced: Rs 1,040,000 per month
- Cost reduced: Rs 12,480,000 per year

## 3) Revenue Recovered

This section estimates revenue retained due to better reliability and lower churn.

### Formula

- Churn avoided = 1,500 x (5% - 2%) = 45 users
- Monthly revenue recovered = 45 x Rs 299 = Rs 13,455
- Annual revenue recovered = Rs 13,455 x 12 = Rs 161,460

### Result

- Revenue recovered: Rs 13,455 per month
- Revenue recovered: Rs 161,460 per year

## Additional Economic Value (Customer Side)

This is not company P&L savings, but value created for customers.

### Formula

- Active adopters = 1,200 x 35% = 420 couples
- Annual customer benefit = 420 x Rs 18,000 = Rs 7,560,000

### Result

- Customer financial benefit enabled: Rs 7,560,000 per year

## Summary Table

| Metric | Monthly | Annual |
|---|---:|---:|
| Time saved | 1,300 hours | 15,600 hours |
| Internal cost reduced | Rs 1,040,000 | Rs 12,480,000 |
| Revenue recovered | Rs 13,455 | Rs 161,460 |
| Customer value enabled | N/A | Rs 7,560,000 |

## Sensitivity Check (Quick)

If adoption is lower or effort reduction is smaller, impact still remains meaningful.

Scenario A (Conservative):
- Active couples = 800
- Time saved per couple = 45 minutes
- Monthly hours saved = 800 x 45 / 60 = 600 hours
- Monthly cost reduced = 600 x Rs 800 = Rs 480,000

Scenario B (Upside):
- Active couples = 1,500
- Time saved per couple = 70 minutes
- Monthly hours saved = 1,500 x 70 / 60 = 1,750 hours
- Monthly cost reduced = 1,750 x Rs 800 = Rs 1,400,000

## Notes and Boundaries

1. This model is directional and intended for planning.
2. Replace assumptions with production telemetry for board-level reporting.
3. Suggested telemetry for refinement:
- Monthly active couples by cohort
- Median handling time before and after adoption
- Recommendation click-through and execution rates
- Churn by AI provider uptime and fallback usage
