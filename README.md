# The Displacement Curve

Tracking AI's displacement of human labor in professional services — with data, not opinion.

**[View the live dashboard →](https://jschulman.github.io/displacement-curve)**

## What Is This?

An open-source dashboard that aggregates publicly available market signals to answer one question: **Where are we on the displacement curve?**

The **Composite Displacement Index** synthesizes eight independent signals into a single 0-100 score:

| Score | Phase | What It Means |
|-------|-------|---------------|
| 0–25 | Pre-disruption | AI is a topic, not a force |
| 26–50 | Productivity | AI making firms more efficient; employment stable |
| 51–75 | Erosion | Revenue per employee diverging from headcount |
| 76–100 | Displacement | Employment declining; funding pouring into replacements |

## Signals

| Signal | Source | Frequency | What It Measures |
|--------|--------|-----------|-----------------|
| Professional Services Employment | BLS (CES) | Monthly | Sector headcount trends |
| AI Search Interest | Google Trends | Daily | Public attention to AI tools |
| Open Source AI Activity | GitHub API | Daily | Developer momentum in AI |
| AI Revenue Reporting | SEC EDGAR (XBRL) | Quarterly | How firms report AI revenue |
| Revenue Per Employee | SEC EDGAR (10-K) | Quarterly | Productivity divergence signal |
| VC Funding: AI Services | SEC Form D | Quarterly | Capital flowing to AI replacements |
| AI vs Traditional Hiring | BLS JOLTS | Monthly | Job opening mix shift |
| Regulatory Guidance | Fed / OCC / SEC / NIST / EU | Quarterly | Government response velocity |

Every signal uses **free, public data sources** — no proprietary APIs, no paywalls.

## Design Principles

- **Data, not opinion.** The dashboard presents signals. It does not editorialize.
- **Reproducible.** Every data point traces to its source. Every collector is open source.
- **Automated.** GitHub Actions collects fresh data on schedule.
- **Durable.** Only signals with reliable, ongoing public sources are included.
- **Accessible.** Single page. No login. No paywall. Mobile-friendly.

## Architecture

```
collectors/          Python scripts for each data source
normalizers/         Derived metrics (composite index, earnings normalization)
data/                Versioned JSON (raw + processed)
docs/                Static dashboard (HTML/JS/CSS — GitHub Pages)
.github/workflows/   Automated collection schedules
```

| Layer | Technology |
|-------|-----------|
| Dashboard | Vanilla HTML/JS/CSS |
| Charts | Chart.js (CDN) |
| Collectors | Python 3 + requests |
| Scheduling | GitHub Actions (cron) |
| Hosting | GitHub Pages |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Generate mock data for development
python3 data/generate_mock_data.py

# Or run a live collector (example: BLS employment)
python3 collectors/bls_employment.py --api-key YOUR_BLS_KEY

# Serve the dashboard
cd docs && python3 -m http.server 8000
```

All collectors support `--mock` for offline development.

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for detailed documentation of data sources, collection methods, normalization, and composite index weights.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Short version: fork, branch, follow existing patterns, test locally, submit a PR.

## License

MIT — see [LICENSE](LICENSE)
