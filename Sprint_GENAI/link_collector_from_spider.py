#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Link Collector (Spider Wrapper)
==============================

This utility wraps Challenge-HP's `mercadolivre_spider.run_spider` helper so we
can easily harvest product URLs and feed them to:
  • generativa_sprint1.py (structured extraction)
  • sprint2_llm_classifier copy.py (classification)

It keeps Challenge-HP code untouched – we merely import and orchestrate.

Usage (examples)
----------------
# Default cartridge model queries (667/664/662)
python link_collector_from_spider.py

# Custom queries + 30 items each
python link_collector_from_spider.py --max 30 "cartucho hp 667" "cartucho hp compatível"

Output files are written to Sprint_GENAI/data/
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from datetime import datetime
import csv
import json

# Add Challenge-HP folder to import path
import sys
from pathlib import Path as _P
challenge_path = _P(__file__).resolve().parents[1] / "Challenge-HP"
if str(challenge_path) not in sys.path:
    sys.path.append(str(challenge_path))

try:
    from mercadolivre_spider import run_spider  # type: ignore
except ImportError as exc:
    raise SystemExit("❌ Could not import mercadolivre_spider from Challenge-HP.\nCheck that the repository folder is present and dependencies installed.") from exc

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("link_collector")


def collect_links(queries: list[str], max_items: int = 20) -> list[str]:
    """Collect product links for each query using Challenge-HP spider."""
    all_links: list[str] = []
    for q in queries:
        logger.info(f"▶ Running spider for query: '{q}' (max {max_items})")
        raw_results = run_spider(
            query=q,
            extract_images=False,
            sort_by='relevance',
            condition='all',
            max_items=max_items,
        )
        # Flatten in case run_spider returns a list of lists
        flat_results = []
        for item in raw_results:
            if isinstance(item, dict):
                flat_results.append(item)
            elif isinstance(item, list):
                flat_results.extend([p for p in item if isinstance(p, dict)])

        for prod in flat_results:
            link = prod.get("LINK") or prod.get("url") or prod.get("link")
            if link and link not in all_links:
                all_links.append(link)
        logger.info(f"  ↳ Collected {len(flat_results)} items, total unique links: {len(all_links)}")
    return all_links


def save_links(links: list[str]) -> Path:
    """Save links to txt & JSON inside data/ and return txt path."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = data_dir / f"ml_hp_urls_{ts}.txt"
    json_path = data_dir / f"ml_hp_urls_{ts}.json"

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(links))
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"links": links}, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ Saved {len(links)} URLs to {txt_path}")
    return txt_path


def main():
    parser = argparse.ArgumentParser(description="Collect Mercado Livre HP cartridge URLs using Challenge-HP spider.")
    parser.add_argument("queries", nargs="*", help="Search queries (default common HP models)")
    parser.add_argument("--max", type=int, default=20, help="Max items per query (default 20)")
    args = parser.parse_args()

    default_queries = [
        "cartucho hp 667",
        "cartucho hp 664",
        "cartucho hp 662",
    ]
    queries = args.queries if args.queries else default_queries
    links = collect_links(queries, max_items=args.max)

    if not links:
        logger.error("No links collected. Aborting.")
        return

    txt_file = save_links(links)

    print("\n🚀 NEXT STEPS:")
    print(f"  1) Extract structured data: python generativa_sprint1.py {txt_file}")
    print(f"  2) Classify ads:          python 'sprint2_llm_classifier copy.py'")


if __name__ == "__main__":
    main() 