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

## Signal 6: VC Funding in AI Services

**Source:** SEC Form D Filings, Crunchbase, PitchBook
**Update Cadence:** Quarterly

### What It Measures

Capital flows into AI-native competitors to traditional professional services firms. Rising VC investment in AI-native audit, legal, consulting, compliance, and staffing startups signals investor conviction that these markets are ripe for disruption.

### Categories Tracked

| Category Key | Description |
|-------------|-------------|
| ai_audit | AI-Native Audit/Accounting startups |
| ai_legal | AI Legal Services startups |
| ai_consulting | AI Consulting/Strategy startups |
| ai_compliance | AI Compliance/Regulatory startups |
| ai_staffing | AI-Native Staffing startups |
| horizontal_ai | Horizontal AI Agents (cross-sector) |

### Metrics

- **Total Funding ($M):** Aggregate quarterly funding across all tracked categories
- **Deal Count:** Number of funding rounds per quarter
- **Cumulative Funding ($M):** Running total of all capital deployed
- **Category Breakdown:** Funding by vertical (stacked bar chart)

### Interpretation

Accelerating VC investment in AI-native professional services companies indicates smart money believes displacement is imminent. The category breakdown reveals which professional services verticals are attracting the most disruptive investment.

---

## Signal 7: Job Posting Trends

**Source:** Indeed Hiring Lab, LinkedIn Economic Graph
**Update Cadence:** Monthly

### What It Measures

Structural shifts in hiring patterns across professional services. Tracks the ratio of AI-related job postings to traditional role postings, revealing whether firms are replacing traditional hiring with AI-focused roles.

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

### Metrics

- **AI Postings %:** Percentage of job postings requiring AI/ML skills
- **Traditional Postings %:** Percentage of traditional (non-AI) role postings
- **AI-to-Traditional Ratio:** Direct ratio of AI to traditional postings (key displacement indicator)
- **Total Postings Index:** Overall posting volume indexed to baseline

### Interpretation

A rising AI-to-traditional ratio indicates firms are structurally shifting their workforce composition toward AI skills. When AI postings rise while traditional postings decline, it signals active displacement of traditional roles rather than net new hiring.

---

## Signal 8: Regulatory Guidance Cadence

**Source:** Federal Reserve, OCC, FDIC, CFPB, SEC, EU AI Act Framework, NIST AI RMF
**Update Cadence:** Quarterly

### Regulators Tracked

| Key | Regulator | Jurisdiction |
|-----|-----------|-------------|
| fed | Federal Reserve | US |
| occ | Office of the Comptroller of the Currency | US |
| fdic | Federal Deposit Insurance Corporation | US |
| cfpb | Consumer Financial Protection Bureau | US |
| sec | Securities and Exchange Commission | US |
| eu | EU AI Act | EU |
| nist | National Institute of Standards and Technology | US |

### Metrics

- **Document Count:** Total AI-related guidance documents issued per quarter per regulator
- **Enforcement Count:** Enforcement actions referencing AI per quarter
- **Guidance Count:** Non-enforcement guidance (frameworks, best practices, comment requests)
- **Cumulative Documents:** Running total across all regulators

### Interpretation

Accelerating regulatory output signals that AI displacement has become a policy concern. Early-stage regulatory activity (guidance, frameworks) suggests awareness. Enforcement actions indicate the regulatory posture is shifting from observation to intervention. A rapid increase in cumulative documents marks the transition from a permissive to a structured regulatory environment.

---

## Composite Displacement Index

The Composite Displacement Index synthesizes all eight signals into a single score (0-100) indicating where professional services stand on the displacement curve.

### Weights

| Signal | Weight | Rationale |
|--------|--------|-----------|
| Professional Services Employment | 0.25 | The definitive lagging indicator of displacement |
| Revenue Per Employee | 0.20 | Efficiency gains preceding headcount reduction |
| VC Funding: AI Services | 0.15 | Capital conviction in AI-native replacements |
| AI vs Traditional Hiring | 0.15 | Real-time labor market composition shift |
| AI Search Interest | 0.10 | Cultural awareness and behavioral intent |
| Open Source AI Activity | 0.10 | Developer tooling leading commercial products |
| Regulatory Guidance | 0.05 | Policy response to displacement concerns |

### Normalization

Each signal is normalized to a 0-100 scale relative to its observed range over the tracking period. This ensures signals with different units (employment in thousands, funding in millions, ratios) are comparable.

### Phase Ranges

| Score Range | Phase | Description |
|-------------|-------|-------------|
| 0-25 | Pre-disruption | AI is a topic, not a force. Business as usual. |
| 26-50 | Productivity | AI is making firms more efficient. Employment stable or growing. |
| 51-75 | Erosion | Revenue per employee diverging from headcount. Job mix shifting. |
| 76-100 | Displacement | Employment declining. Funding pouring into replacements. |

### Caveats

- The composite index is a simplification. It compresses eight distinct signals into a single number.
- Weight assignments are based on editorial judgment, not statistical optimization.
- Phase boundaries are fixed thresholds, not data-driven breakpoints.
- The index is designed for directional insight, not precision. A score of 42 vs 44 is noise. A score of 25 vs 50 is signal.

---

*Last updated: February 2026*
