#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Citation Detector v1 (MVP)
==============================

A zero-cost, dependency-light Generative-Engine-Optimisation (GEO) monitor.
It probes web search engines for AI-style answers and counts how often
consumer brands are mentioned across a curated set of long-tail queries.

Why this exists
---------------
The major LLMs (Gemini / ChatGPT / Claude / Perplexity) increasingly serve
as the first touchpoint of consumer product research. Whether your brand
gets *cited* inside those answers is the new SEO. This script provides a
lightweight, fully transparent baseline that any small team can run on a
laptop with no paid API keys.

Pipeline (5 modules, top-to-bottom)
-----------------------------------
1. load_queries   -- read queries.json (50 long-tail Q&A prompts).
2. fetch_ai_answer -- pull text that *approximates* an LLM answer.
                      v1 uses a search-engine snippet provider as a proxy;
                      v2 will swap in real LLM APIs (Gemini/OpenAI/Claude).
3. extract_brands  -- dictionary-based recognition per category. Trades
                      recall for precision; keeps the tool explainable.
4. aggregate_stats -- per-category brand counter + mention-rate %.
5. generate_report -- emits a Markdown weekly report.

v1 limitations (be honest about them)
-------------------------------------
* Search-engine snippets are a *proxy* for LLM answers, not the real
  thing. Treat the numbers as directional, not absolute.
* Brand recognition is dictionary-based; long-tail / new brands are
  missed by design. Update BRAND_DICTIONARY when a new SKU lands.
* Polite by default: 2-second sleep between calls, robots.txt honoured
  via urllib.robotparser, custom User-Agent string identifying the tool.
* No paid API is called anywhere in v1. All TODO[paid] markers are
  no-ops until you uncomment them and supply a key.

License: MIT. Educational and personal research use only.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib import robotparser
from urllib.parse import urlparse

# ``requests`` is optional. The tool still runs in --demo mode without it.
try:
    import requests  # type: ignore
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("geo-detector")

USER_AGENT = (
    "LLM-Citation-Detector/1.0 "
    "(+https://github.com/  ; educational research use only)"
)

# ===========================================================================
# Module 1 -- Query loader
# ===========================================================================

def load_queries(path: str | Path) -> Dict[str, List[str]]:
    """Load queries.json and strip the ``_meta`` key.

    The returned dict is ``{category_key: [query, ...]}``. Category keys are
    snake_case English identifiers so they double as filesystem-safe slugs.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"queries.json not found at {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


# ===========================================================================
# Module 2 -- Fetch AI answer (LLM proxy)
# ===========================================================================
#
# v1 strategy
# -----------
# Real LLM API calls cost money. As a stop-gap, this module ships with two
# providers:
#   * ``demo_provider``       -- hard-coded sample answers, no network.
#   * ``duckduckgo_provider`` -- HTML scrape of DuckDuckGo's lite endpoint.
#     Honours robots.txt, sleeps between calls, identifies itself in UA.
#
# v2 strategy (TODO[paid])
# ------------------------
# When a budget exists, swap in one of:
#   import google.generativeai as genai
#   genai.configure(api_key=os.environ["GEMINI_API_KEY"])
#   model = genai.GenerativeModel("gemini-1.5-pro")
#   return model.generate_content(query).text
#
#   from openai import OpenAI
#   client = OpenAI()
#   return client.responses.create(model="gpt-4o-mini",
#                                  input=query).output_text
#
#   import anthropic
#   client = anthropic.Anthropic()
#   return client.messages.create(model="claude-3-5-sonnet-latest",
#                                 max_tokens=1024,
#                                 messages=[{"role":"user","content":query}]
#                                ).content[0].text
# ---------------------------------------------------------------------------

# Hard-coded fixtures used by ``demo_provider``. The strings below were
# *paraphrased* from publicly available 2026 review articles; they are kept
# short, contain no copyrighted creative content, and exist purely so that
# the end-to-end pipeline can be demonstrated offline.
_DEMO_FIXTURES: Dict[str, str] = {
    "outdoor_backpack": (
        "For 2026, reviewers consistently rate the Osprey Aura AG 50 and "
        "Osprey Eja 58 as the top women's hiking backpacks, with the "
        "Gregory Deva 70 and Deuter Aircontact Lite right behind. The REI "
        "Co-op Flash 55 wins the budget category, while Granite Gear and "
        "Mountain Hardwear also receive honourable mentions. Patagonia and "
        "The North Face remain reliable mainstream picks."
    ),
    "yoga_mat": (
        "The Manduka PRO is widely regarded as the best overall yoga mat "
        "in 2026. For grip-focused practitioners, the Liforme Original and "
        "the Jade Yoga Harmony are strong alternatives. Lululemon's The "
        "Mat appeals to design-conscious buyers, Gaiam covers the budget "
        "tier, and Alo Yoga rounds out the premium lifestyle segment."
    ),
    "electric_toothbrush": (
        "Top 2026 electric toothbrush picks include the Oral-B Pro 1000 "
        "(best overall), Philips Sonicare 4100 (best value) and Philips "
        "Sonicare 6400 (premium). Chinese contenders such as usmile and "
        "Laifen have gained traction in cross-border markets, with Quip "
        "and Foreo serving the design / sensitive-teeth niches."
    ),
    "noise_cancelling_headphones": (
        "The Sony WH-1000XM6 and Bose QuietComfort Ultra (2nd gen) lead "
        "the 2026 noise-cancelling-headphone shortlists. Apple AirPods Max "
        "remains the go-to for iOS households, while Sennheiser Momentum 4 "
        "and Shokz OpenFit Pro cover audiophile and open-ear use-cases. "
        "Edifier NeoBuds Pro 3 and Anker Soundcore Liberty 4 NC dominate "
        "the sub-1000-RMB tier."
    ),
    "coffee_machine": (
        "The Breville Bambino Plus is the most cited home espresso machine "
        "for 2026, followed by the Breville Barista Express Impress. "
        "De'Longhi Stilosa wins the budget category; Gaggia Classic Pro "
        "appeals to enthusiasts. Nespresso and Keurig remain the dominant "
        "capsule choices, while Jura and La Marzocco cover the premium tier."
    ),
}


def demo_provider(query: str, category: Optional[str] = None) -> str:
    """Offline stub used by ``--demo``.

    Returns a category-appropriate paragraph of brand-rich text. The
    fixtures live in ``_DEMO_FIXTURES`` and are paraphrased from public 2026
    review articles so the script can prove the pipeline end-to-end without
    network access.
    """
    if category and category in _DEMO_FIXTURES:
        return _DEMO_FIXTURES[category]
    # Last-resort fallback so callers without a category still get a result.
    return next(iter(_DEMO_FIXTURES.values()))


# --- DuckDuckGo HTML provider (zero-cost, polite) --------------------------

_ROBOTS_CACHE: Dict[str, robotparser.RobotFileParser] = {}


def _robots_allow(url: str, user_agent: str = USER_AGENT) -> bool:
    """Cache and consult robots.txt for the host of ``url``."""
    try:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        rp = _ROBOTS_CACHE.get(host)
        if rp is None:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception:  # pragma: no cover - network may be flaky
                # If robots.txt is unreachable we conservatively *allow*
                # the request; pair this with the 2-second sleep below.
                return True
            _ROBOTS_CACHE[host] = rp
        return rp.can_fetch(user_agent, url)
    except Exception:  # pragma: no cover
        return True


def duckduckgo_provider(
    query: str, category: Optional[str] = None, timeout: int = 10
) -> str:
    """Query DuckDuckGo's HTML endpoint and return the concatenated snippets.

    DuckDuckGo's ``/html`` endpoint is the closest zero-cost stand-in for an
    LLM answer: it returns search snippets that an LLM would likely cite.
    We honour robots.txt, identify ourselves with a descriptive User-Agent,
    and never scrape beyond the first results page.
    """
    if requests is None:
        log.warning("'requests' not installed; falling back to demo_provider")
        return demo_provider(query, category)

    endpoint = "https://duckduckgo.com/html/"
    if not _robots_allow(endpoint):
        log.info("robots.txt disallows %s, skipping", endpoint)
        return ""

    try:
        resp = requests.get(
            endpoint,
            params={"q": query},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en,zh;q=0.8"},
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - network errors are expected
        log.warning("DuckDuckGo fetch failed for %r: %s", query, exc)
        return ""

    # Cheap HTML-to-text: extract the visible search-result snippets only.
    # We deliberately avoid bs4 to keep the dependency tree to one package.
    html = resp.text
    snippets = re.findall(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = " ".join(re.sub(r"<[^>]+>", " ", s) for s in snippets)
    return re.sub(r"\s+", " ", text).strip()


def fetch_ai_answer(
    query: str,
    category: Optional[str] = None,
    provider_fn: Optional[Callable[..., str]] = None,
    sleep_seconds: float = 2.0,
) -> str:
    """Public entry point used by ``run_detection``.

    Parameters
    ----------
    query : str
        Long-tail question to look up.
    category : str, optional
        Category slug, passed to the provider so demo fixtures can match.
    provider_fn : callable, optional
        Provider function. Defaults to ``demo_provider`` so the script is
        always runnable.
    sleep_seconds : float
        Politeness delay applied *after* the call.
    """
    provider_fn = provider_fn or demo_provider
    try:
        # Providers may or may not accept the ``category`` kwarg.
        text = provider_fn(query, category=category)  # type: ignore[arg-type]
    except TypeError:
        text = provider_fn(query)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return text or ""


# ===========================================================================
# Module 3 -- Brand extraction
# ===========================================================================
#
# Dictionary-based recognition. We accept that this trades recall for
# precision -- a new SKU won't be picked up until added here -- but the
# trade-off keeps the tool fully explainable to clients.
#
# Aliases handle:
#   * brand vs. brand-and-product strings ("Sony" / "Sony WH-1000XM6")
#   * apostrophe / accent variants ("De'Longhi" / "Delonghi")
#   * Chinese <-> English crossovers ("飞利浦" / "Philips")
# ---------------------------------------------------------------------------

BRAND_DICTIONARY: Dict[str, Dict[str, List[str]]] = {
    "outdoor_backpack": {
        "Osprey": ["Osprey"],
        "Gregory": ["Gregory"],
        "Deuter": ["Deuter"],
        "REI Co-op": ["REI Co-op", "REI Coop", "REI Flash"],
        "Granite Gear": ["Granite Gear"],
        "The North Face": ["The North Face", "TNF", "北面"],
        "Patagonia": ["Patagonia", "巴塔哥尼亚"],
        "Arc'teryx": ["Arc'teryx", "Arcteryx", "始祖鸟"],
        "Mystery Ranch": ["Mystery Ranch"],
        "Mountain Hardwear": ["Mountain Hardwear"],
        "NEMO Equipment": ["NEMO Equipment", "NEMO "],
        "Naturehike": ["Naturehike", "挪客"],
        "Kailas": ["Kailas", "凯乐石"],
        "Gossamer Gear": ["Gossamer Gear"],
        "WATERFLY": ["WATERFLY", "Waterfly"],
    },
    "yoga_mat": {
        "Manduka": ["Manduka", "曼杜卡"],
        "Lululemon": ["Lululemon", "lululemon", "露露乐蒙"],
        "Liforme": ["Liforme"],
        "Jade Yoga": ["Jade Yoga", "JadeYoga", "Jade Harmony"],
        "Gaiam": ["Gaiam"],
        "Alo Yoga": ["Alo Yoga", "Alo "],
        "Hugger Mugger": ["Hugger Mugger"],
        "Prana": ["Prana"],
        "Sweaty Betty": ["Sweaty Betty"],
        "Yoloha": ["Yoloha"],
        "Iuga": ["Iuga"],
        "BalanceFrom": ["BalanceFrom"],
        "Keep": ["Keep瑜伽", "Keep 瑜伽", "Keep官方", "Keep天然"],
        "Decathlon": ["Decathlon", "迪卡侬"],
        "佑美": ["佑美", "Yottoy", "YOTTOY"],
    },
    "electric_toothbrush": {
        "Philips Sonicare": ["Philips Sonicare", "Sonicare", "飞利浦", "Philips"],
        "Oral-B": ["Oral-B", "Oral B", "OralB", "欧乐B", "欧乐-B", "欧乐b"],
        "usmile": ["usmile", "笑容加"],
        "Laifen": ["Laifen", "徕芬"],
        "Quip": ["Quip "],
        "Foreo": ["Foreo"],
        "Xiaomi": ["Xiaomi", "小米"],
        "Soocas": ["Soocas", "素士"],
        "Colgate Hum": ["Colgate Hum", "Colgate"],
        "Bitvae": ["Bitvae"],
        "Aquasonic": ["Aquasonic"],
        "舒客": ["舒客"],
    },
    "noise_cancelling_headphones": {
        "Sony": ["Sony", "索尼", "WH-1000XM", "WF-1000XM"],
        "Bose": ["Bose", "QuietComfort", "QC Ultra"],
        "Apple": ["Apple ", "AirPods"],
        "Sennheiser": ["Sennheiser", "森海塞尔", "Momentum"],
        "Beats": ["Beats "],
        "Anker Soundcore": ["Anker", "Soundcore"],
        "JBL": ["JBL "],
        "Bowers & Wilkins": ["Bowers & Wilkins", "B&W "],
        "Shokz": ["Shokz", "韶音", "OpenFit"],
        "Jabra": ["Jabra"],
        "Edifier": ["Edifier", "漫步者", "NeoBuds"],
    },
    "coffee_machine": {
        "Breville": ["Breville", "Bambino", "Barista Express"],
        "De'Longhi": ["De'Longhi", "DeLonghi", "Delonghi", "德龙"],
        "Nespresso": ["Nespresso"],
        "Keurig": ["Keurig"],
        "Jura": ["Jura "],
        "Gaggia": ["Gaggia"],
        "Rancilio": ["Rancilio"],
        "La Marzocco": ["La Marzocco"],
        "Philips": ["Philips Baristina", "Philips 3200", "Philips 5400"],
        "Smeg": ["Smeg "],
        "Capresso": ["Capresso"],
        "Midea": ["Midea", "美的"],
        "Fellow": ["Fellow "],
    },
}


def extract_brands(
    text: str,
    category: str,
    dictionary: Dict[str, Dict[str, List[str]]] = BRAND_DICTIONARY,
) -> List[str]:
    """Return the deduplicated list of brand names mentioned in ``text``.

    Matching rules
    --------------
    * Case-insensitive substring match for English aliases.
    * Exact substring match for Chinese aliases (no case folding needed).
    * Multiple aliases for the same brand collapse to the canonical name.
    """
    if not text:
        return []
    hits: List[str] = []
    lowered = text.lower()
    for canonical, aliases in dictionary.get(category, {}).items():
        for alias in aliases:
            if re.search(r"[\u4e00-\u9fff]", alias):
                found = alias in text
            else:
                found = alias.lower() in lowered
            if found:
                hits.append(canonical)
                break  # one canonical brand counts once per answer
    return hits


# ===========================================================================
# Module 4 -- Aggregation
# ===========================================================================

def aggregate_stats(results: List[dict]) -> Dict[str, dict]:
    """Group per-query results by category and compute mention rates."""
    by_cat: Dict[str, dict] = defaultdict(
        lambda: {"queries": 0, "answered": 0, "counter": Counter()}
    )
    for r in results:
        cat = r["category"]
        by_cat[cat]["queries"] += 1
        if r.get("answer_text"):
            by_cat[cat]["answered"] += 1
        for b in r.get("brands", []):
            by_cat[cat]["counter"][b] += 1

    out: Dict[str, dict] = {}
    for cat, agg in by_cat.items():
        n_answered = agg["answered"] or 1
        top = agg["counter"].most_common(10)
        out[cat] = {
            "total_queries": agg["queries"],
            "answered_queries": agg["answered"],
            "top_brands": [
                {
                    "rank": i + 1,
                    "brand": brand,
                    "count": count,
                    # Mention rate = how often the brand showed up among
                    # *answered* queries. Using ``answered`` (not ``queries``)
                    # avoids penalising a brand when an upstream fetch fails.
                    "mention_rate": round(count / n_answered * 100, 1),
                }
                for i, (brand, count) in enumerate(top)
            ],
        }
    return out


# ===========================================================================
# Module 5 -- Report generator
# ===========================================================================

# Human-readable display names for the 5 categories.
CATEGORY_DISPLAY: Dict[str, str] = {
    "outdoor_backpack": "户外背包 / Outdoor Backpack",
    "yoga_mat": "瑜伽垫 / Yoga Mat",
    "electric_toothbrush": "电动牙刷 / Electric Toothbrush",
    "noise_cancelling_headphones": "降噪耳机 / Noise-Cancelling Headphones",
    "coffee_machine": "咖啡机 / Coffee Machine",
}


def generate_report(
    stats: Dict[str, dict],
    out_path: str | Path,
    *,
    week_label: str,
    demo: bool,
    provider_name: str,
) -> Path:
    """Write a Markdown weekly report to ``out_path``.

    The report is intentionally short -- ~one A4 page per category -- so it
    can be consumed by a non-technical product owner in under 5 minutes.
    The full narrative (1500-2500 words) lives in ``reports/`` and is
    written by hand on top of these tables.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append(f"# GEO Citation Weekly - {week_label}")
    lines.append("")
    lines.append(
        f"_Generated by LLM Citation Detector v1 ({provider_name} provider"
        f"{' / DEMO MODE' if demo else ''})._"
    )
    lines.append("")
    lines.append(
        "> **Disclaimer.** This is a baseline GEO snapshot. Numbers are "
        "directional and educational; they are produced by a search-engine "
        "proxy and do **not** represent a paid LLM API call."
    )
    lines.append("")

    for cat_key, agg in stats.items():
        display = CATEGORY_DISPLAY.get(cat_key, cat_key)
        lines.append(f"## {display}")
        lines.append("")
        lines.append(
            f"- Queries probed: **{agg['total_queries']}** "
            f"(answered: {agg['answered_queries']})"
        )
        lines.append("")
        lines.append("| Rank | Brand | Mentions | Mention Rate |")
        lines.append("| ---: | :---- | -------: | -----------: |")
        if not agg["top_brands"]:
            lines.append("| — | _no brands detected_ | 0 | 0.0% |")
        for row in agg["top_brands"]:
            lines.append(
                f"| {row['rank']} | {row['brand']} | "
                f"{row['count']} | {row['mention_rate']}% |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Report written to %s", out_path)
    return out_path


# ===========================================================================
# Orchestration
# ===========================================================================

def run_detection(
    queries: Dict[str, List[str]],
    provider_fn: Callable[..., str],
    sleep_seconds: float,
    limit_per_category: Optional[int] = None,
) -> List[dict]:
    """Iterate over all (category, query) pairs and assemble result rows."""
    results: List[dict] = []
    for category, q_list in queries.items():
        if limit_per_category is not None:
            q_list = q_list[:limit_per_category]
        for query in q_list:
            log.info("[%s] %s", category, query)
            text = fetch_ai_answer(
                query,
                category=category,
                provider_fn=provider_fn,
                sleep_seconds=sleep_seconds,
            )
            brands = extract_brands(text, category)
            log.info("  -> %d brand(s): %s", len(brands), ", ".join(brands) or "—")
            results.append(
                {
                    "category": category,
                    "query": query,
                    "answer_text": text,
                    "brands": brands,
                }
            )
    return results


# ===========================================================================
# CLI
# ===========================================================================

def _provider_by_name(name: str) -> Callable[..., str]:
    if name == "demo":
        return demo_provider
    if name == "duckduckgo":
        return duckduckgo_provider
    raise SystemExit(f"unknown provider: {name}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm-citation-detector",
        description="Detect brand citations in AI-style search answers.",
    )
    p.add_argument(
        "--queries",
        default=str(Path(__file__).parent / "queries.json"),
        help="path to queries.json (default: ./queries.json)",
    )
    p.add_argument(
        "--provider",
        default="demo",
        choices=["demo", "duckduckgo"],
        help=(
            "answer source. 'demo' uses bundled fixtures (offline); "
            "'duckduckgo' scrapes the public HTML endpoint."
        ),
    )
    p.add_argument(
        "--limit-per-category",
        type=int,
        default=None,
        help="run only the first N queries per category (smoke test).",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="seconds to sleep between requests (default 2).",
    )
    p.add_argument(
        "--out",
        default=str(Path(__file__).parent / "reports" / "latest_weekly.md"),
        help="output Markdown report path.",
    )
    p.add_argument(
        "--week-label",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="label used in the report header.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    queries = load_queries(args.queries)
    provider_fn = _provider_by_name(args.provider)
    results = run_detection(
        queries,
        provider_fn=provider_fn,
        sleep_seconds=args.sleep,
        limit_per_category=args.limit_per_category,
    )
    stats = aggregate_stats(results)
    generate_report(
        stats,
        args.out,
        week_label=args.week_label,
        demo=(args.provider == "demo"),
        provider_name=args.provider,
    )
    # Also dump the raw rows next to the report so downstream tooling
    # (notebooks, dashboards) doesn't have to re-run the crawl.
    raw_path = Path(args.out).with_suffix(".raw.json")
    raw_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("Raw rows written to %s", raw_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
