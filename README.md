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

### Phase 1
| Signal | Source | Frequency |
|--------|--------|-----------|
| Professional Services Employment | Bureau of Labor Statistics | Monthly |
| AI Search Interest | Google Trends | Daily |
| Open Source AI Activity | GitHub API | Daily |

### Phase 2
| Signal | Source | Frequency |
|--------|--------|-----------|
| AI Revenue Reporting | SEC EDGAR / Earnings Transcripts | Quarterly |
| Revenue Per Employee (SEC Workforce) | SEC EDGAR 10-K | Quarterly |

### Phase 3
| Signal | Source | Frequency |
|--------|--------|-----------|
| VC Funding: AI Services | SEC Form D | Quarterly |
| AI vs Traditional Hiring | Indeed Hiring Lab / LinkedIn | Monthly |

### Phase 4 (Current)
| Signal | Source | Frequency |
|--------|--------|-----------|
| Regulatory Guidance | Fed / OCC / FDIC / CFPB / SEC / EU / NIST | Quarterly |
| Composite Displacement Index | All signals (weighted) | Monthly |

The **Composite Displacement Index** is the flagship feature: a single 0-100 score synthesizing all eight signals into one answer to "where are we on the curve?" The hero section displays the current score and phase, while the timeline chart shows the full trajectory with annotated events.

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

Contributions welcome. To contribute:

1. **Fork** the repository
2. **Create a branch** for your change (`git checkout -b feature/my-signal`)
3. **Follow existing patterns** for data format (see `data/` directory structure)
4. **Test locally** by serving `docs/` and verifying the dashboard renders
5. **Submit a PR** with a clear description of the change

For new signal collectors, see [METHODOLOGY.md](METHODOLOGY.md) for the documentation standard each signal must meet.

## License

MIT — see [LICENSE](LICENSE)
