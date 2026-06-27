<p align="center">
  <img src="./images/logo.svg" alt="LLM Radar" width="92">
</p>

<h1 align="center">LLM Radar</h1>

<p align="center">
  <strong>The live LLM landscape</strong> — pricing, context windows, and capabilities of 300+ models, auto-updated daily.
</p>

<p align="center">
  <a href="https://ronaldmego.github.io/llm-radar"><img src="https://img.shields.io/badge/live%20demo-llm--radar-1f3a5f?style=for-the-badge" alt="Live demo"></a>
  <a href="https://github.com/ronaldmego/llm-radar/actions/workflows/publish.yml"><img src="https://github.com/ronaldmego/llm-radar/actions/workflows/publish.yml/badge.svg" alt="Publish"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT"></a>
</p>

<p align="center">
  <img src="./screenshots/dashboard.png" alt="LLM Radar dashboard" width="820">
</p>

## Why

The LLM landscape moves weekly — new models, shifting prices, bigger context windows. Comparing them usually means juggling a dozen pricing pages. **LLM Radar** pulls the whole catalog into one view and keeps it current automatically, so you can see at a glance what's new, what's cheap, and what fits your context needs.

## What it shows

- **At-a-glance stats** — models tracked, providers, new this week, biggest context window, free models.
- **Newest models** — what was just added to the catalog.
- **Cheapest capable** — lowest input price among models with ≥100K context.
- **Full catalog** — a searchable, sortable table of every model: provider, context, `$/1M` in/out, modalities, date added.

Capability flags: 🧠 reasoning · 🖼️ multimodal · 🔧 tools.

## How it works

```
OpenRouter API  →  Python (pandas + great-tables)  →  Quarto dashboard  →  GitHub Pages
        \__________________ refreshed daily by GitHub Actions __________________/
```

**Zero server, zero cost, no API key.** The model catalog endpoint is public, so a daily GitHub Actions cron re-fetches the data, re-renders the dashboard, and redeploys to GitHub Pages — no secrets, no backend.

## Run locally

Requires [uv](https://docs.astral.sh/uv/) and [Quarto](https://quarto.org) 1.8+.

```bash
git clone https://github.com/ronaldmego/llm-radar.git
cd llm-radar
uv run quarto preview index.qmd
```

To check the data pipeline alone:

```bash
uv run python src/data_processor.py
```

## Data source

[OpenRouter](https://openrouter.ai) — the public `/api/v1/models` catalog. LLM Radar is an independent project and is not affiliated with OpenRouter.

## License

MIT — see [LICENSE](LICENSE).
