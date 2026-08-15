<p align="center">
  <img src="./images/logo.svg" alt="LLM Radar" width="92">
</p>

<h1 align="center">LLM Radar</h1>

<p align="center">
  <strong>The full LLM landscape</strong> — hosted pricing & context (300+ models) plus open-weights adoption & licenses, auto-updated daily.
</p>

<p align="center">
  <strong>See the live dashboard here → <a href="https://ronaldmego.github.io/llm-radar">ronaldmego.github.io/llm-radar</a></strong>
</p>

<p align="center">
  <a href="https://github.com/ronaldmego/llm-radar/actions/workflows/publish.yml"><img src="https://github.com/ronaldmego/llm-radar/actions/workflows/publish.yml/badge.svg" alt="Publish"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT"></a>
</p>

<p align="center">
  <img src="./screenshots/dashboard.png" alt="LLM Radar dashboard" width="820">
</p>

## Why

The LLM landscape moves weekly — new models, shifting prices, bigger context windows. Comparing them usually means juggling a dozen pricing pages. **LLM Radar** pulls the whole catalog into one view and keeps it current automatically, so you can see at a glance what's new, what's cheap, and what fits your context needs.

Two tabs — the **commercial** side you pay to call, and the **open** side you can self-host:

### Hosted (OpenRouter)
- **The market on one plane** — every priced model plotted by context window against output price, both axes logarithmic, coloured by what it can be fed. Filled markers are models whose weights you could also self-host; hollow ones are closed.
- **At-a-glance stats** — models tracked, providers, new this week, biggest context window, free models.
- **Newest models** · **Cheapest capable** (≥100K context, lowest input price) · **Full catalog** — searchable table with provider, context, `$/1M` in/out, modalities, date added.
- Capability flags: 🧠 reasoning · 🖼️ multimodal · 🔧 tools.

### Open-weights (Hugging Face)
- **Traction against release date** — likes on a log axis against publication date, bubble size = 30-day downloads. New and loved but not yet installed shows up as *far right, high, small*: the corner no download ranking can display.
- **At-a-glance stats** — open models tracked, **permissive-license share**, **gated** (acceptance-required) count, multimodal count, new this week.
- **Just landed** (last 45 days, by likes) · **Most downloaded** · **Community favorites** · **Catalog** — searchable, with org, type, 30-day downloads, likes, **license**, date.
- License and the gated flag are first-class: they're what decide whether a model can be self-hosted for data-residency or used commercially.

**The universe is text *and* multimodal *and* vision/OCR**, and it is built from two rankings per type: 30-day downloads for established adoption, plus the Hub's trending signal for what landed this week. Downloads alone are a rear-view mirror — the counter needs weeks to move, so a model published two days ago sits at zero however important it is, and a catalog ranked only by downloads can never show it.

## How it works

```
OpenRouter API  ┐
                ├─►  Python (pandas + great-tables + plotly)  →  Quarto dashboard  →  GitHub Pages
Hugging Face API ┘
        \____________________ refreshed daily by GitHub Actions ____________________/
```

**Zero server, zero cost, no API key.** Both catalog endpoints are public, so a daily GitHub Actions cron re-fetches the data, re-renders the dashboard, and redeploys to GitHub Pages — no secrets, no backend.

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

## Data sources

- [OpenRouter](https://openrouter.ai) — the public `/api/v1/models` catalog (hosted tab).
- [Hugging Face Hub](https://huggingface.co/models) — the public model listing API (open-weights tab).

LLM Radar is an independent project and is not affiliated with OpenRouter or Hugging Face.

## License

MIT — see [LICENSE](LICENSE).
