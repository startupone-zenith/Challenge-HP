#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick test script to generate a small set of HP cartridge links for testing the pipeline
"""

from generate_hp_links import HPCartridgeLinkGenerator
import logging

logging.basicConfig(level=logging.INFO)

# Create generator
generator = HPCartridgeLinkGenerator()

# Search for just a few HP 667 cartridges (the same model from our test)
print("🔍 Searching for HP 667 cartridges...")

products = generator.search_hp_cartridges(
    queries=["cartucho hp 667"],  # Just one query
    max_results_per_query=5,       # Just 5 results
    sort_by='relevance',
    delay_range=(1, 2)
)

# Save results
if products:
    results = generator.save_results()
    print(f"\n✅ Found {results['total_links']} HP cartridge links!")
    print(f"\n📄 URLs saved to: {results['txt_file']}")
    print("\n🚀 Ready to process with:")
    print(f"   python generativa_sprint1.py {results['txt_file']}")
else:
    print("❌ No links found. Check your internet connection.") 