# The Displacement Curve

Tracking AI's displacement of human labor in professional services — with data, not opinion.

## What Is This?

An open-source dashboard that aggregates publicly available market signals to answer one question: **Where are we on the displacement curve?**

[View the dashboard →](https://jschulman.github.io/displacement-curve)

## Design Principles

- **Data, not opinion.** The dashboard presents signals. It does not editorialize.
- **Reproducible.** Every data point links to its source. Every collection script is open source.
- **Automated.** Data collection runs on GitHub Actions.
- **Durable.** Only signals with reliable, ongoing public sources are included.
- **Accessible.** A single page. No login. No paywall. Mobile-friendly.

## Signals Tracked

### Phase 1 (Current)
| Signal | Source | Frequency |
|--------|--------|-----------|
| Professional Services Employment | Bureau of Labor Statistics | Monthly |
| AI Search Interest | Google Trends | Daily |
| Open Source AI Activity | GitHub API | Daily |

### Planned
- AI Revenue Reporting (Earnings Transcripts)
- SEC Workforce Disclosures
- VC Funding in AI-Native Competitors
- Job Posting Trends
- Regulatory Guidance Cadence

## Methodology

See [METHODOLOGY.md](METHODOLOGY.md) for detailed documentation of every data source, collection method, and normalization approach.

## Architecture

- **Collectors:** Python scripts in `collectors/`
- **Scheduling:** GitHub Actions (daily, weekly, monthly, quarterly cron)
- **Data:** JSON files in `data/` (version-controlled)
- **Dashboard:** Static HTML/JS in `docs/` (GitHub Pages)
- **Charts:** Chart.js (no framework dependency)

## Running Locally

```bash
# Generate mock data for development
python3 data/generate_mock_data.py

# Serve the dashboard locally
cd docs && python3 -m http.server 8000
```

## Contributing

This project is in active development. Contributions welcome — especially for new signal collectors.

## License

MIT — see [LICENSE](LICENSE)
