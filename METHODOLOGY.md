# Methodology

This document describes the data sources, collection methods, and processing for each signal tracked by The Displacement Curve.

## General Principles

- All data comes from publicly available sources
- Collection scripts are open source and auditable
- Raw data is preserved alongside processed data
- All timestamps are UTC
- Historical data begins November 2022 (ChatGPT public release)

## Signal 1: Professional Services Employment

**Source:** Bureau of Labor Statistics (BLS) Current Employment Statistics (CES)
**URL:** https://www.bls.gov/ces/
**API:** BLS Public Data API v1
**Update Cadence:** Monthly (first Friday of each month)

### Series Tracked

| Series ID | Description |
|-----------|-------------|
| CES5541200001 | Accounting, Tax Preparation, Bookkeeping, Payroll Services |
| CES5541600001 | Management, Scientific, and Technical Consulting |
| CES5541100001 | Legal Services |
| CES5541500001 | Computer Systems Design and Related Services |
| CES5000000001 | Total Professional and Business Services |

### Processing
- Raw BLS API responses saved to `data/bls/raw/`
- Employment numbers reported in thousands (BLS standard)
- Month-over-month and year-over-year changes computed
- Deviation from pre-COVID (February 2020) trend line calculated

### Interpretation
Employment in professional services is the foundational macro signal. Growth suggests displacement is early. Flat or declining employment alongside GDP growth suggests displacement is underway.

---

## Signal 2: AI Search Interest

**Source:** Google Trends
**Library:** pytrends
**Update Cadence:** Daily (rolling 7-day average)

### Search Terms

| Category | Terms |
|----------|-------|
| AI Adoption | "AI agent for accounting", "AI audit tool", "AI compliance software" |
| Disruption Anxiety | "AI replacing consultants", "AI replacing accountants", "AI replacing lawyers" |
| Upskilling | "AI certification accounting", "AI for CPAs", "prompt engineering for consultants" |
| Tool Adoption | "ChatGPT for audit", "Claude for accounting", "AI tax preparation" |

### Processing
- All terms indexed to baseline period (January 2023 = 100)
- 12-week rolling average applied to smooth weekly noise
- Category composites computed as simple average of constituent terms
- Geographic breakdown: US, UK, India

### Interpretation
Search interest is a proxy for collective awareness and behavior. Rising "AI replacing [profession]" searches indicate cultural awareness preceding behavioral change.

---

## Signal 3: Open Source AI Activity

**Source:** GitHub REST API
**Update Cadence:** Daily

### Topics Monitored

| Category | GitHub Topics |
|----------|--------------|
| AI Accounting | `ai-accounting`, `ai-audit`, `ai-bookkeeping` |
| AI Legal | `ai-legal`, `legal-ai`, `contract-analysis` |
| AI Compliance | `ai-compliance`, `regtech`, `ai-governance` |
| LLM Agents | `ai-agent`, `autonomous-agent` |
| AI Automation | `ai-automation`, `llm-workflow` |

### Metrics
- New repositories created per month
- Cumulative star count (adoption velocity)
- Contributor count (community investment)
- Fork count

### Interpretation
Open source activity is a leading indicator of commercial tooling. Developer activity in AI-for-professional-services predicts commercial products by 12-18 months.

---

## Signal 4: AI Revenue Reporting

**Source:** SEC EDGAR, Earnings Transcripts
**Update Cadence:** Quarterly (following earnings releases)

### Firms Tracked

| Ticker | Firm | Sector |
|--------|------|--------|
| ACN | Accenture | IT Consulting |
| CTSH | Cognizant | IT Consulting |
| INFY | Infosys | IT Consulting |
| WIT | Wipro | IT Consulting |
| EPAM | EPAM Systems | IT Consulting |
| GLOB | Globant | IT Consulting |
| IT | Gartner | Advisory |
| BAH | Booz Allen Hamilton | Government Consulting |

### The Accenture Normalization Problem

Accenture dominates reported "AI revenue" in this cohort and frequently relabels existing digital/cloud services as AI-enabled. This creates a measurement challenge: are firms genuinely growing AI revenue, or relabeling existing work? We address this with the Relabeling Index.

### Relabeling Index

A ratio comparing a firm's reported AI revenue growth rate to its total revenue growth rate. An index of 1.0 means AI revenue grows at the same rate as total revenue (no signal). Values above 1.5 suggest genuine AI-specific growth. Values below 1.0 suggest relabeling may exceed actual new work.

### Metrics

- **AI Revenue ($M):** Total AI-attributed revenue across tracked firms
- **AI Revenue %:** AI revenue as a percentage of total revenue
- **Revenue Per Employee ($K):** Quarterly revenue divided by headcount (efficiency proxy)
- **Relabeling Index:** Ratio of AI rev growth to total rev growth

### Interpretation

Rising AI revenue alongside flat or declining headcount is the core displacement signal. The relabeling index helps distinguish genuine AI-driven efficiency from marketing rebranding.

---

## Signal 5: SEC Workforce Disclosures

**Source:** SEC EDGAR 10-K Annual Reports, Item 1 (Human Capital)
**Update Cadence:** Quarterly (following 10-K/10-Q filings)

### Firms Tracked

| Ticker | Firm | Sector |
|--------|------|--------|
| ACN | Accenture | IT Consulting |
| CTSH | Cognizant | IT Consulting |
| INFY | Infosys | IT Consulting |
| WIT | Wipro | IT Consulting |
| EPAM | EPAM Systems | IT Consulting |
| GLOB | Globant | IT Consulting |
| IT | Gartner | Advisory |
| BAH | Booz Allen Hamilton | Government Consulting |
| KFRC | Kforce | Staffing |
| RHI | Robert Half | Staffing |
| MAN | ManpowerGroup | Staffing |

### Metrics

- **Headcount:** Total reported employees
- **YoY Change:** Year-over-year headcount change (%)
- **Contractor %:** Estimated contractor/contingent workforce as percentage of total
- **Revenue Per Employee ($K):** Annual revenue divided by headcount

### Interpretation

SEC filings provide the most reliable headcount data. Declining headcount at IT services firms while revenue grows indicates productivity gains (potentially AI-driven). Staffing firms (KFRC, RHI, MAN) serve as a canary — declining placements suggest reduced demand for human labor.

---

## Planned Signals

The following signals are planned for future phases:

- **VC Funding:** Capital flows into AI-native professional services competitors
- **Job Posting Trends:** Structural shifts in hiring patterns
- **Regulatory Guidance:** Rate of AI-related regulatory issuance

## Composite Index

A weighted composite index (0-100) synthesizing all signals is planned. See the project README for current status.

---

*Last updated: February 2026*
