# Workforce Pulse — Analytical Requirements

**Context (simulation):** Data Analyst, People Data & Systems. Stakeholder: HR management team.
**Data:** IBM HR Analytics Employee Attrition & Performance — a *fictional* dataset created by IBM data scientists.
Findings describe this synthetic sample only; they are not claims about any real organization.

## Business questions

| # | Business question | Analytical method | Expected output | Phase |
|---|---|---|---|---|
| Q1 | What is the organization's attrition rate? | KPI calculation | Attrition rate, retention rate | P3 |
| Q2 | Which departments / job roles have the highest turnover? | Group rates + counts | Ranked rate table (with group size) | P3, P4 |
| Q3 | Which workforce characteristics are associated with leaving? | Univariate comparison, model drivers | Driver ranking | P4, P5 |
| Q4 | Is overtime associated with higher attrition? | Rate comparison + significance test | OT vs non-OT rate, difference | P4 |
| Q5 | How do satisfaction, work-life balance and compensation relate to retention? | Rate by level, income distributions | Charts + findings | P4 |
| Q6 | Can we identify employees with elevated predicted attrition risk? | LR vs XGBoost classifier | PR-AUC, recall @ threshold, risk bands | P5 |
| Q7 | What retention scenarios could management explore? | Descriptive scenarios + model sensitivity | Power BI simulator page | P7 |

## Out of scope / interpretation boundaries
- **Causation.** All findings are associations. No feature is claimed to *cause* attrition.
- **Forward-looking retention.** The data is a single cross-sectional snapshot with no time window, so
  "attrition rate" is historical prevalence in the sample, not an annualized turnover rate.
- **Individual decisions.** Risk scores are a decision-support prototype and must never be used to rank
  employees for dismissal, promotion, pay or any other employment decision.

## Success criteria
- Every business question answered with a traceable number or chart.
- Model beats a no-skill baseline on PR-AUC (baseline PR-AUC = prevalence ≈ 0.16).
- Fairness audit reported across Gender, Age band and MaritalStatus, including disparities found.
- Management can read the dashboard and deck without technical background.
