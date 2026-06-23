# LLM Citation Detector

> A zero-cost, dependency-light **Generative-Engine-Optimisation (GEO) monitor**.
> Track how often consumer brands get cited in AI-style search answers across long-tail queries.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)]()

## 1. What this is

Major LLMs (Gemini, ChatGPT, Claude, Perplexity) are rapidly becoming the *first touchpoint* for consumer product research. Whether your brand is cited inside those answers is the new SEO — call it **GEO** (Generative Engine Optimisation).

This repo ships a **minimum-viable** GEO monitor that any small team can run on a laptop with **no paid API keys**:

- Define a set of long-tail buyer questions per product category.
- Pull text that approximates an LLM answer (via free search-engine snippets in v1; via real LLM APIs once you wire one up).
- Recognise brand mentions through a curated, fully explainable dictionary.
- Aggregate per-category Top-N tables and emit a Markdown weekly report.

Five product categories ship out of the box (outdoor backpacks, yoga mats, electric toothbrushes, noise-cancelling headphones, coffee machines) with 50 bilingual long-tail queries.

## 2. Why dictionary-based extraction?

We deliberately picked dictionary matching over a trained NER model:

- **Explainable.** A non-technical product owner can audit every match.
- **Zero infra.** No GPU, no model download, no hosted endpoint.
- **Trade-off accepted.** Recall is bounded by the dictionary. New SKUs need to be added by hand; we treat that as a *feature* (it forces the operator to keep a fresh competitor map).

## 3. Quick start

```bash
git clone <this repo>
cd llm-citation-detector
python3 -m pip install -r requirements.txt

# offline smoke test (no network, no keys)
python3 main.py --provider demo --limit-per-category 1 --sleep 0 \
                --out reports/smoke.md

# zero-cost online run via DuckDuckGo HTML endpoint
python3 main.py --provider duckduckgo --limit-per-category 3 \
                --out reports/weekly.md
```

Output:

- `reports/<name>.md` — Markdown report with Top-10 brand citation tables per category.
- `reports/<name>.raw.json` — raw `(category, query, answer_text, brands)` rows for downstream analysis.

## 4. Project layout

```
.
├── main.py                 # 5-module pipeline (load / fetch / extract / aggregate / report)
├── seed_real_samples.py    # auxiliary: feeds hand-captured real snippets through the pipeline
├── queries.json            # 5 categories × 10 long-tail queries (bilingual)
├── requirements.txt        # one runtime dep: requests
├── LICENSE                 # MIT
├── README.md               # this file
└── reports/                # generated reports + raw JSON
```

The 5 modules inside `main.py` are clearly delimited by banner comments:

1. **Query loader** — parses `queries.json`.
2. **Answer fetcher** — `demo_provider`, `duckduckgo_provider`, plus `TODO[paid]` placeholders for Gemini / OpenAI / Anthropic.
3. **Brand extractor** — dictionary-based, supports English + Chinese aliases.
4. **Aggregator** — per-category Counter + mention-rate %.
5. **Report writer** — Markdown emitter.

## 5. Configuration

### Adding a new category

1. Append a `(category_key, [queries...])` entry to `queries.json`.
2. Append a sibling block to `BRAND_DICTIONARY` in `main.py` with `{canonical: [aliases...]}`.
3. Re-run. Done.

### Adding a paid LLM provider (when budget allows)

Open `main.py`, find the `TODO[paid]` markers inside the *Module 2* docstring, and uncomment the SDK block of your choice. Then expose it as a new value for `--provider`. Three reference snippets are pre-written for Gemini, OpenAI and Anthropic.

## 6. Compliance & politeness

- **robots.txt is honoured** before every fetch via `urllib.robotparser`.
- A descriptive **User-Agent** identifies the tool and its purpose.
- A **2-second sleep** is applied between calls by default (`--sleep N` to tune).
- v1 never scrapes beyond the first results page.
- We do not capture, store or redistribute upstream copyrighted text — only the brand-token counts derived from it.

## 7. Roadmap

- **v1.0 (this release)** — 5 categories, demo + DuckDuckGo providers, Markdown report.
- **v1.1** — Gemini provider plug-in (free-tier friendly), full 50-query weekly cron.
- **v1.2** — Brand dictionary expansion to 30+ per category; entry/exit deltas week-over-week.
- **v1.3** — "Citation gap vs. competitor" view for a user-supplied SKU.
- **v2.0** — Optional NER model (spaCy / GLiNER) as a recall booster, with confidence scoring.
- **v2.1** — Web dashboard, scheduled jobs, multi-language report templates.

Issues and PRs welcome — see the open issues for help-wanted tasks.

## 8. Known limitations (be honest about them)

1. **Search-engine snippets are a proxy for LLM answers.** Numbers are directional; pair them with a paid-LLM run for production decisions.
2. **Dictionary recall is finite.** New brands are silently missed until added.
3. **No anti-hallucination check.** If an LLM invents a brand, we'll happily count it. v2.0 will cross-reference with a brand registry.
4. **No language-specific tokenisation.** Chinese matching is naïve substring; CJK word boundaries are not enforced.

## 9. Disclaimer

This software and its output are provided **for educational and personal research use only**. The tool does not provide investment, marketing, legal or medical advice. Brand citation counts are statistical signals, not endorsements. Respect the Terms of Service of any upstream search engine or LLM provider you plug in. The authors accept no liability for downstream business decisions made on the basis of this tool's output.

## 10. License

[MIT](./LICENSE) © 2026 LLM Citation Detector contributors.
