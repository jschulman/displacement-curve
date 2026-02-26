# Contributing to The Displacement Curve

Thanks for your interest in contributing. This project tracks AI's displacement of human labor using publicly available data — every contribution should maintain that standard.

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your change (`git checkout -b feature/my-signal`)
3. **Follow existing patterns** — see the `collectors/` and `data/` directories for structure
4. **Test locally** by serving `docs/` and verifying the dashboard renders correctly
5. **Submit a PR** with a clear description of what changed and why

## Adding a New Signal

New signals must meet these criteria:

- **Free, public data source** — no proprietary APIs or paywalls
- **Reliable and ongoing** — the source must be reasonably expected to continue publishing
- **Relevant to professional services displacement** — not general AI hype metrics
- **Documented** — add an entry to [METHODOLOGY.md](METHODOLOGY.md) covering the source, collection method, and normalization approach

A new signal collector should:

- Live in `collectors/` as a standalone Python script
- Support `--mock` mode for offline development
- Output JSON to `data/{signal}/processed/` following the existing schema patterns
- Include a corresponding GitHub Actions workflow for automated collection

## Code Style

- Python: standard library + `requests`. No heavy frameworks.
- JavaScript: vanilla JS, no build step, no transpilation.
- Keep it simple. This project is intentionally low-dependency.

## Reporting Issues

Open an issue describing:
- What you expected to happen
- What actually happened
- Steps to reproduce (if applicable)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
