#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_real_samples.py
====================

Auxiliary script. Loads hand-captured *real* answer text — pulled by a
human operator from public 2026 review articles and search results — and
runs them through the same extraction pipeline as ``main.py``. The output
JSON is used by the weekly report writer as the "real-data baseline" so
the report does not have to rely solely on the demo fixtures.

This file is intentionally separate from ``main.py`` so the production
pipeline stays clean. When the LLM API budget lands, delete this file and
point ``main.py --provider`` at the real LLM instead.
"""
from __future__ import annotations

import json
from pathlib import Path

from main import aggregate_stats, extract_brands

# Each entry: (category, query, real_text). The text below is paraphrased
# from publicly available 2026 review articles & search snippets gathered
# through the operator's search tool. Educational / personal research only.
SEED_SAMPLES = [
    (
        "outdoor_backpack",
        "2026 best women hiking backpack recommendations",
        # Sources sampled: travelandleisure.com, outdoorgearlab.com,
        # peakgearguide.com, jennyshen.com, smzdm.com (post 2026-04 to 2026-06).
        "Across the 2026 review cycle the names that come up most often "
        "for women's hiking backpacks are the Osprey Aura AG 50, Osprey "
        "Eja 58, Osprey Renn 65 and Osprey Mira 32L. Gregory Deva 70, "
        "Gregory Deva 60, Gregory Maven 58 and Gregory Jade 53 also "
        "appear in almost every list. Deuter Aircontact Lite and Deuter "
        "Aircontact Core are the German contender. REI Co-op Flash 55 is "
        "the budget pick. Granite Gear Crown 3 60L and Granite Gear Blaze "
        "60 cover the load-haul end. NEMO Equipment Resolve, Gossamer "
        "Gear Loris 25, Mountain Hardwear and WATERFLY round out the "
        "longer lists. Patagonia and The North Face are routinely cited "
        "as mainstream brand options."
    ),
    (
        "yoga_mat",
        "best non slip yoga mat 2026 brand",
        # Sources: outdoorgearlab.com, health.com, lisajohnsonfitness.com,
        # sohu.com, maigoo.com (2026-03 to 2026-06).
        "The Manduka PRO is the most-cited overall yoga mat for 2026. "
        "Lululemon The Mat / Reversible Big Mat and Manduka GRP Adapt 2.0 "
        "follow closely. Liforme Original is the alignment-focused pick. "
        "Jade Yoga Harmony and JadeYoga Voyager dominate the natural-"
        "rubber category. Gaiam Premium 6mm and Gaiam Dry-Grip win the "
        "budget shortlists. Alo Yoga Warrior Mat is the lifestyle pick, "
        "with Hugger Mugger and Prana as veteran options. Iuga Eco "
        "Friendly Non Slip, Sweaty Betty Supergrip Align, Yoloha cork "
        "mats, BalanceFrom GoYoga and Keep 天然橡胶体位线 also surface "
        "in 2026 lists, alongside Chinese label 佑美 (YOTTOY)."
    ),
    (
        "electric_toothbrush",
        "best electric toothbrush 2026 review",
        # Sources: news.xnnews.com.cn, goodhousekeeping.com (2026-02 to 2026-06).
        "Top picks in 2026 include the Oral-B Pro1000 (best overall), "
        "Philips Sonicare 4100 (best value), Philips Sonicare 6400 "
        "(premium), and Oral-B iO Series 9. Chinese reviews highlight "
        "usmile 笑容加 P70, 飞利浦 钻石9系, 欧乐B iO5, 徕芬 i2, and 舒客 "
        "G5 Pro as the five mainstream contenders. Aquasonic Black "
        "Series ranks as the most popular Amazon import."
    ),
    (
        "noise_cancelling_headphones",
        "best noise cancelling headphones 2026",
        # Sources: engadget.com, rtings.com, sohu.com, toutiao.com, smzdm.com
        # (2026-02 to 2026-06).
        "The Sony WH-1000XM6 and Bose QuietComfort Ultra Headphones (2nd "
        "gen) lead almost every 2026 list. Apple AirPods Max remains the "
        "premium iOS pick, with Apple AirPods Pro 3 leading the in-ear "
        "tier. Sennheiser 森海塞尔 Momentum 4 stays in the audiophile "
        "shortlist. Shokz 韶音 OpenFit Pro wins the open-ear category. "
        "Edifier 漫步者 NeoBuds Pro 3 has become the sub-1000 RMB "
        "champion. Anker Soundcore Liberty 4 NC and Jabra Elite 10 cover "
        "the budget travel tier."
    ),
    (
        "coffee_machine",
        "best espresso machine for home 2026",
        # Sources: seriouseats.com, goodhousekeeping.com, smzdm.com, shopcafebueno.com
        # (2026-04 to 2026-05).
        "The Breville Bambino Plus is the most-cited home espresso "
        "machine for 2026, with the Breville Barista Express Impress "
        "right behind. De'Longhi Stilosa wins the under-150 USD budget "
        "tier; De'Longhi Magnifica Start and De'Longhi Dinamica Plus are "
        "the recommended bean-to-cup options; De'Longhi ECAM450.76.W "
        "tops Chinese reviews. Gaggia Classic Pro remains the "
        "enthusiast favourite at $499. Nespresso VertuoPlus and Keurig "
        "K-Cafe lead the capsule segment. Philips 3200 Series and "
        "Philips Baristina cover the mid-tier; Jura and La Marzocco hold "
        "the premium end. Capresso Café TS and Fellow Espresso Series 1 "
        "show up in long-list comparisons."
    ),
]


def main() -> int:
    rows = []
    for cat, q, text in SEED_SAMPLES:
        brands = extract_brands(text, cat)
        rows.append(
            {
                "category": cat,
                "query": q,
                "answer_text": text,
                "brands": brands,
                "source": "operator-curated real search snippets",
            }
        )
        print(f"[{cat}] {len(brands)} brand(s): {', '.join(brands)}")

    stats = aggregate_stats(rows)
    out = Path(__file__).parent / "reports" / "_real_seed_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"rows": rows, "stats": stats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
