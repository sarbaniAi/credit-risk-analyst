# Credit Analyst Decision Logic Playbook — Indian Banking Operations

## 1. Customer Segmentation Rules

Customers are segmented into four tiers for credit decisioning:

- **Tier 1 — Premium**: Annual income > INR 15,00,000, Total assets > INR 50,00,000, CIBIL score > 750. Eligible for all products with priority processing.
- **Tier 2 — Standard**: Annual income INR 5,00,000–15,00,000, Assets INR 10,00,000–50,00,000, CIBIL 650–750. Eligible for Personal Loan, Home Loan, Credit Card, Vehicle Loan.
- **Tier 3 — Basic**: Annual income INR 2,00,000–5,00,000, Assets INR 2,00,000–10,00,000, CIBIL 550–650. Eligible for limited Personal Loan, Secured Credit Card, Gold Loan.
- **Tier 4 — Underbanked**: Annual income < INR 2,00,000, Assets < INR 2,00,000, CIBIL < 550 or no score. Eligible for Microfinance, Gold Loan, JLG Loans only.

Customers with no CIBIL score (new-to-credit) are classified as Tier 4 by default but may be upgraded to Tier 3 if employment stability exceeds 24 months and income verification is confirmed.

## 2. Priority Scoring Framework

The composite Risk Score ranges from 0 (lowest risk) to 100 (highest risk), calculated as:

**Risk Score = (Payment_Score × 0.30) + (Income_Score × 0.20) + (Asset_Score × 0.15) + (Txn_Score × 0.15) + (OD_Score × 0.10) + (Tenure_Score × 0.10)**

| Factor | Weight | Low Risk (Score 0) | Medium Risk (Score 50) | High Risk (Score 100) |
|--------|--------|-------------------|----------------------|---------------------|
| Payment Delays (12m) | 30% | 0 delays | 1–2 delays | > 5 delays |
| Income Stability | 20% | Employment > 60 months | 24–60 months | < 12 months |
| Asset Coverage Ratio | 15% | Assets > 5× income | 2–5× income | < 1× income |
| Transaction Trend (3m vs 12m) | 15% | Ratio > 0.30 | 0.20–0.30 | < 0.15 (declining) |
| Overdraft Exposure | 10% | No overdraft | OD < 20% of balance | OD > 50% of balance |
| Tenure & Stability | 10% | Address > 48m + Bank > 60m | 24–48m each | < 12m either |

The system prediction field maps as: prediction=1 → Risk Score > 50 (HIGH RISK), prediction=0 → Risk Score ≤ 50 (LOW RISK).

## 3. Credit Decision Matrix

| Decision | Risk Score | Conditions | Authority Level |
|----------|-----------|------------|----------------|
| APPROVE | < 30 | Income > 5L, 0 delays in 12m, Tier 1–2 | L1 Credit Analyst |
| APPROVE WITH CONDITIONS | 30–50 | Improving delay trend, collateral available, or strong co-applicant | L2 Credit Analyst |
| MANUAL REVIEW | 50–70 | Mixed signals requiring deeper analysis | Credit Manager |
| DECLINE | > 70 | Multiple delays, negative trend, low assets, high overdraft, or NPA history | Auto-decline (appeal to Branch Manager) |

Override Policy:
- L1 analysts may NOT override a DECLINE.
- L2 analysts may upgrade MANUAL REVIEW to APPROVE WITH CONDITIONS (documented justification required).
- Branch Managers may override DECLINE for amounts up to INR 10,00,000 with documented rationale.
- All overrides must be logged in the audit trail within 24 hours.
