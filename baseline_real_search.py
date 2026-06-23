#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baseline_real_search.py
========================

Real-data baseline generator. Feeds *real* search-engine snippets
(captured 2026-06-23 from the operator's general-purpose search tool)
through the same extract/aggregate pipeline as ``main.py``.

This complements ``seed_real_samples.py``: it uses fresh 2026-06 data
captured today and aggregates per-category into a fresh weekly report
that does not depend on DuckDuckGo HTTP access (which is unreachable
from some networks).

Educational and personal research use only.
"""
from __future__ import annotations

import json
from pathlib import Path

from main import (
    aggregate_stats,
    extract_brands,
    generate_report,
)

# Each entry: (category_slug, query, real_text_blob).
# The text below is condensed from public 2026 review articles indexed
# by the operator's search tool on 2026-06-23.
REAL_SAMPLES = [
    (
        "outdoor_backpack",
        "2026 best women hiking backpack recommendations",
        # Sources: mytrailwear.com, travelandleisure.com, peakgearguide.com,
        # outdoorgearlab.com (all 2026-04 to 2026-05 review cycles).
        "Across the 2026 women's hiking backpack review cycle the most "
        "cited names are the Osprey Eja 58, Osprey Aura AG 50, Osprey Aura "
        "AG 65, Osprey Renn 65, Osprey Tempest 26 and the women-specific "
        "Osprey Mira. The Gregory Deva 70, Gregory Deva 60, Gregory Maven "
        "58 and Gregory Jade 53 appear in every multi-day list. Deuter is "
        "represented by the Deuter Speed Lite Pro 28 SL, Deuter Aircontact "
        "Lite 45+10 SL and Deuter Aircontact Core 60+10 SL. The budget "
        "shortlists feature the REI Co-op Flash 55 and the Teton 55L. "
        "Granite Gear Crown 3 60L and Granite Gear Blaze 60 anchor the "
        "thru-hiking weight-to-capacity charts. NEMO Equipment Resolve, "
        "Gossamer Gear Loris 25, Mountain Hardwear and Hyperlite Mountain "
        "Gear round out the high-end longer lists, with Patagonia and The "
        "North Face routinely surfacing as mainstream alternatives."
    ),
    (
        "yoga_mat",
        "best non slip yoga mat 2026 brand Manduka Lululemon review",
        # Sources: outdoorgearlab.com, shape.com, taekwondoking.com,
        # smzdm.com, shop.manduka.jp (2026-03 to 2026-06).
        "The Manduka PRO and Manduka GRP Adapt 2.0 dominate the 2026 "
        "non-slip yoga mat coverage. Lululemon The Mat (5mm) and the "
        "Lululemon Reversible Big Mat are the design-led picks. Liforme "
        "Original is the alignment-focused premium choice. Jade Yoga "
        "Harmony 2.0 leads the natural-rubber category. Gaiam Premium "
        "6mm and Gaiam Classic Solid 5mm dominate the budget shortlists. "
        "Iuga Eco Friendly Non Slip is repeatedly called the 'best value "
        "upgrade'. Alo Yoga Warrior Mat is the lifestyle / hot-yoga pick. "
        "Hugger Mugger and Prana are veteran options. Stakt The Mat, "
        "Yoloha cork mats and BalanceFrom round out the budget end. "
        "Chinese review sources highlight Keep 瑜伽 and 佑美 (YOTTOY) as "
        "domestic alternatives. Decathlon's house brand also gets shouts "
        "in the entry-level Chinese review feeds."
    ),
    (
        "electric_toothbrush",
        "best electric toothbrush 2026 Philips Oral-B Sonicare review",
        # Sources: goodhousekeeping.com, brushreview.com,
        # buyingnerd.com, news.xnnews.com.cn (2026-02 to 2026-06).
        "The flagship slot in 2026 electric-toothbrush coverage is split "
        "between the Oral-B iO Series 11 and the Philips Sonicare "
        "DiamondClean Prestige 9900. Other widely-cited Philips models "
        "include the Philips Sonicare 6400, Philips Sonicare 9900 "
        "Prestige and the Philips Sonicare ProtectiveClean 5100. Oral-B "
        "is also represented by the Oral-B iO Series 10, Oral-B iO 5 and "
        "the workhorse Oral-B Pro 3000. Quip Smart Electric Toothbrush "
        "appears as the minimalist contender. Chinese reviews put 飞利浦 "
        "钻石 9 系 and 欧乐 B iO5 at the top, with 徕芬 (Laifen) and "
        "usmile / 笑容加 as the most-cited domestic challengers. Xiaomi "
        "(小米) and Soocas (素士) show up as the budget Chinese stack, "
        "with Colgate Hum, Bitvae, Aquasonic and 舒客 covering the rest "
        "of the long tail."
    ),
    (
        "noise_cancelling_headphones",
        "best noise cancelling headphones 2026 Sony Bose Apple review",
        # Sources: priceandpick.com, faroway.ai, bestreviews.com,
        # smzdm.com (all 2026-04 to 2026-06).
        "The 2026 over-ear ANC headline is the head-to-head between Sony "
        "WH-1000XM5 (still the most-cited overall pick) and Bose "
        "QuietComfort Ultra (the comfort & low-frequency-noise winner). "
        "The newer Sony WH-1000XM6 begins appearing in late-spring "
        "reviews as the 2026 update. Apple AirPods Max (USB-C) is "
        "uniformly listed as the iPhone-ecosystem pick. Sennheiser "
        "Momentum 4 is the consistent sound-quality / battery-marathon "
        "choice. Bose QuietComfort 45 covers the mid-range. Anker "
        "Soundcore Space Q45 and Soundcore by Anker Q30 dominate the "
        "sub-$100 / sub-budget tier. Sennheiser Accentum Plus and Jabra "
        "Evolve2 85 fill out the work-from-home / call-quality slots. "
        "Chinese cross-border reviewers also flag Edifier (漫步者) "
        "NeoBuds and Shokz / 韶音 OpenFit on the open-ear side."
    ),
    (
        "coffee_machine",
        "best espresso machine 2026 home use brand",
        # Sources: nbcnews.com Select, goodhousekeeping.com,
        # seriouseats.com, foodnetwork.com (2026-02 to 2026-05).
        "Breville is by far the most-cited espresso brand in 2026 home "
        "reviews. Specific Breville machines repeatedly mentioned are "
        "the Breville Bambino Plus, Breville Bambino, Breville Barista "
        "Express, Breville Barista Express Impress, Breville Barista "
        "Pro and the Breville Dual Boiler. De'Longhi follows closely "
        "with the De'Longhi Stilosa (budget), De'Longhi Magnifica Evo "
        "with LatteCrema System (super-automatic) and the Dedica line. "
        "KitchenAid KF8 Fully Automatic earns a Good Housekeeping top "
        "spot. Gaggia Classic Pro and Rancilio Silvia are the "
        "enthusiast single-boiler picks. Lelit MaraX and Lelit "
        "Elizabeth cover the prosumer dual-boiler bracket. Nespresso "
        "appears for the Nespresso Vertuo Pop+, Nespresso VertuoPlus "
        "and Nespresso Essenza Mini Espresso Machine by Breville. Café "
        "(GE) Affetto and Café Bellissimo land in the smart / connected "
        "tier. Meraki, Thyme & Table Barista Mini and Fellow Espresso "
        "Series 1 are the newer-entrant talking points."
    ),
]


def main() -> None:
    root = Path(__file__).parent
    out_md = root / "reports" / "20260623_baseline_real_search.md"
    out_json = root / "reports" / "_baseline_real_search_stats.json"

    rows = []
    for category, query, text in REAL_SAMPLES:
        brands = extract_brands(text, category)
        rows.append(
            {
                "category": category,
                "query": query,
                "answer_text": text,
                "brands": brands,
            }
        )

    stats = aggregate_stats(rows)

    # Dump stats JSON.
    out_json.write_text(
        json.dumps(
            {
                "_meta": {
                    "captured_at": "2026-06-23",
                    "provider": "search_web (general)",
                    "samples": len(REAL_SAMPLES),
                    "note": (
                        "Educational and personal research use only. "
                        "Each sample is one real long-tail query whose "
                        "answer text is condensed from publicly indexed "
                        "review articles."
                    ),
                },
                "per_query": [
                    {
                        "category": r["category"],
                        "query": r["query"],
                        "brand_hits": r["brands"],
                        "source_text_len": len(r["answer_text"]),
                    }
                    for r in rows
                ],
                "stats": stats,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Markdown report via main.py's writer.
    generate_report(
        stats,
        out_md,
        week_label="Week 2 — Real-search baseline (5 categories × 1 query)",
        demo=False,
        provider_name="search_web (general, captured 2026-06-23)",
    )

    print(f"[OK] Markdown -> {out_md}")
    print(f"[OK] JSON     -> {out_json}")
    print(f"[STATS] categories scanned: {len(stats)}")
    total_brands = sum(len(v.get('top_brands', [])) for v in stats.values())
    print(f"[STATS] total brand rows  : {total_brands}")


if __name__ == "__main__":
    main()
