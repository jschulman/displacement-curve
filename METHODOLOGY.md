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
| CES6054120001 | Accounting, Tax Preparation, Bookkeeping, Payroll Services |
| CES6054160001 | Management, Scientific, and Technical Consulting |
| CES6054110001 | Legal Services |
| CES6054150001 | Computer Systems Design and Related Services |
| CES6000000001 | Total Professional and Business Services (supersector 60) |

All series are seasonally adjusted "all employees, thousands". Before May
2026 the project used IDs starting with `55` (Financial Activities
supersector) and `50` (Information supersector), which returned either
empty results or the wrong sector entirely; the headline "Professional
Services Employment" number was tracking the Information supersector
(~3 million workers) rather than the much larger Professional and
Business Services supersector (~22 million workers). Verified against
FRED: CES6054120001, CES6054160001, CES6054150001, CES6000000001.

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

### Staffing Canary Status

As of May 2026, the staffing-firm canary panels (KFRC, RHI, MAN) carry empty
`annual` arrays in `data/sec/processed/workforce.json`. The 10-K collector has
not yet been pointed at those tickers. Until the canary is populated, treat
its absence as "no signal," not "no displacement" — the slot is reserved, not
disproved.

---

## Signal 5b: Corporate AI Layoff Attribution

**Source:** Public layoff announcements, 10-Q filings, post-announcement
financial disclosures.
**Update Cadence:** Event-driven.

### Why This Exists

Through 2025-2026, "AI" has become a load-bearing word in layoff press
releases. A December 2025 survey of 1,000 hiring managers found 59% admit they
emphasize AI in layoff announcements because it "plays better with
stakeholders" than admitting weak demand or over-hiring. Oxford Economics has
characterized the pattern as "convenient corporate fiction." Treating every
AI-attributed layoff as a displacement data point would import that
narrative noise directly into the composite.

This signal does not feed the composite. It flags layoff events on the
timeline with an **attribution quality** label, so readers can distinguish
narrative-led announcements from those corroborated by financial signals.

### Attribution Quality Categories

| Quality | Definition | Treatment |
|---------|------------|-----------|
| `validated` | AI cited AND ≥2 of: rising revenue per remaining employee, measurable internal AI usage data, prior AI-tied product disclosures in 10-Q, stock-price impact suggesting the market took it as real | Annotated on the curve; counts toward "displacement" reading |
| `marketing` | AI cited primarily in CEO memo / press release without corroborating financial disclosure | Annotated on the curve as a separate marker; does not count toward displacement reading |
| `mixed` | Some corroboration but layoff also overlaps with broader restructuring, sector headwinds, or a missed quarter | Annotated; treated as ambiguous |

### Worked Examples

**Coinbase — 2026-05-05 — `marketing`.** 700 layoffs (~14% of workforce).
CEO Brian Armstrong's 6:55 AM email framed the cut as becoming "lean, fast,
and AI-native" and was paired with a "tiny teams" / player-coach
restructuring. Crypto-sector headwinds and prior cost-cutting cycles at
Coinbase make AI an over-determined explanation. Scale AI's Jason Droege and
other observers explicitly flagged it as an "AI excuse" framing. No
disclosed internal AI usage metrics tied to the affected roles.

**Cloudflare — 2026-05-07/08 — `validated`.** 1,100 layoffs (~20% of
workforce); first mass layoff in the company's 16-year history.
Corroborating signals: (a) disclosed >600% increase in internal AI usage in
the prior three months with role-level mapping ("roles AI agents are already
performing"); (b) record-high revenue announced in the same earnings call,
ruling out demand collapse as the driver; (c) ~24% stock drop on the news,
indicating the market read the restructuring as substantive rather than
cosmetic; (d) CEO's stated expectation that headcount returns to growth in
2027 — consistent with a productivity step-change, not a demand cut.

### Method

Each layoff event is recorded in the `events` array of
`data/composite/displacement_index.json` with:

```
{
  "date": "YYYY-MM",
  "label": "<Company> -N (X%) ...",
  "type": "layoff",
  "attribution_quality": "validated" | "marketing" | "mixed"
}
```

### Interpretation

A rising count of `validated` layoffs at firms with **growing** revenue is
the cleanest direct evidence of displacement (productivity gain absorbed by
headcount reduction rather than reinvested in hiring). A rising count of
`marketing` layoffs is a signal about narrative, not labor — useful context
for why the discourse runs ahead of the BLS prints, but not evidence of
displacement on its own.

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

- **Openings Index:** Total openings in Professional & Business Services indexed to Nov 2022 = 1.0 (sourced from BLS JOLTS, `JTS540099000000000JOL`)
- **Total Postings Index:** Same value, scaled to baseline = 100, for chart-friendly display
- **Hires / Separations / Quits:** Raw JOLTS series for context

### A note on what this signal cannot measure

The METHODOLOGY originally described an "AI vs traditional postings ratio,"
but JOLTS does not publish an AI / non-AI breakdown of openings. The
underlying data is the total number of professional-services openings; a
true AI-vs-traditional breakdown would require a different source (Indeed
Hiring Lab text-keyword counts, LinkedIn Economic Graph, Lightcast, etc.).
Until such a source is added, this signal functions as a labor-demand
proxy: declining openings → softening demand for professional-services
labor, which is consistent with — but not direct evidence of — displacement.

The collector's output field is `openings_index`. Legacy data may still
carry the name `ai_to_traditional_ratio`; consumers read whichever is
present.

### Interpretation

Falling `openings_index` alongside flat or rising hires-to-openings rates
indicates demand softening (firms posting fewer roles but still filling
what they post). A demand softening that lingers across multiple quarters
is one of the canonical leading indicators of structural change in a
sector.

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

## Signal 9: The Apprenticeship Collapse

**Source:** `displacement-signals` engine (scans professional-services firms' public job postings)
**Update Cadence:** Weekly

### What It Measures

The one thing every other signal here is blind to: **the seniority composition of
hiring.** Signal 7 explicitly notes JOLTS cannot break openings down by level, and
BLS headcount (Signal 1) is an aggregate. But the central claim of the displacement
thesis for professional services — that AI eliminates the *junior* work first, and
with it the apprenticeship that produces senior judgment — is only observable at the
job-posting level.

This signal scans the public careers postings of a cohort of professional-services
firms, classifies each posting's seniority from its title (entry / mid / senior),
filters to US roles, and computes the **junior:senior ratio** (entry-tier postings ÷
senior/review-tier postings). A healthy apprenticeship pipeline posts many entry
roles per senior role; a falling ratio is the apprenticeship tier thinning.

### Cohort

Three buckets, so the signal is a contrast, not an absolute:

- **Treatment** — firms whose business model *is* the audit/tax/advisory apprenticeship: Deloitte, EY, PwC, Accenture, Grant Thornton, Baker Tilly, Protiviti, RSM.
- **Control** — a large non-professional-services white-collar employer (Walmart corporate), to separate the professional-services apprenticeship effect from generic white-collar hiring trends.
- **Insulated** — professional services but structurally shielded from the collapse (e.g. Booz Allen: federal/cleared staff-augmentation, headcount-billed, slow AI adoption). Reported separately; excluded from the composite-feeding median.

The headline value fed to the composite is the **treatment-cohort median junior:senior ratio.**

### Method

- Postings pulled from each firm's public ATS (Workday, Oracle Recruiting, Avature, Radancy, SuccessFactors) — public endpoints only, robots-respecting.
- Seniority classified from the posting title (every ATS encodes the level: "Audit Associate", "Senior Manager, Tax").
- A separate **campus / early-career** pass captures the entry tier that experienced-hire boards route to dedicated portals, so the junior rung is measured directly rather than inferred.

### Interpretation

The ratio **falls** as the apprenticeship thins, so the composite **inverts** it
(lower ratio → higher displacement reading), the same treatment as employment. A
single month normalizes to zero by construction; the signal becomes informative once
the weekly snapshots accumulate a multi-month series. Because it leads the lagging
BLS print, its newest points wait for the BLS-anchored month axis to extend.

---

## Composite Displacement Index

The Composite Displacement Index synthesizes all nine signals into a single score (0-100) indicating where professional services stand on the displacement curve.

### Weights

Adding the Apprenticeship Collapse signal (0.15) rescales the original seven by 0.85
so the set still sums to 1.0 and the existing signals keep their relative importance.

| Signal | Weight | Rationale |
|--------|--------|-----------|
| Professional Services Employment | 0.2125 | The definitive lagging indicator of displacement |
| Revenue Per Employee | 0.17 | Efficiency gains preceding headcount reduction |
| VC Funding: AI Services | 0.1275 | Capital conviction in AI-native replacements |
| AI vs Traditional Hiring | 0.1275 | Real-time labor market composition shift |
| **Apprenticeship Collapse** | **0.15** | **Direct posting-level measure of the junior-tier thinning** |
| AI Search Interest | 0.085 | Cultural awareness and behavioral intent |
| Open Source AI Activity | 0.085 | Developer tooling leading commercial products |
| Regulatory Guidance | 0.0425 | Policy response to displacement concerns |

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

*Last updated: May 2026*
