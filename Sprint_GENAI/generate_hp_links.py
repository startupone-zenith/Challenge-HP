# -*- coding: utf-8 -*-
"""
HP Cartridge Link Generator for Sprint 1/2 Pipeline
===================================================

This script leverages the search logic from Challenge-HP's mercadolivre_spider
to generate lists of HP cartridge product links for processing with:
- generativa_sprint1.py (structured data extraction)
- sprint2_llm_classifier.py (authenticity classification)

Author: Sprint_GENAI Integration
Date: 2024
"""

import requests
import re
import logging
import time
import random
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# User agents for rotating (from Challenge-HP)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
]

class HPCartridgeLinkGenerator:
    """Generate HP cartridge product links from Mercado Livre"""
    
    def __init__(self):
        self.base_url = "https://lista.mercadolivre.com.br/"
        self.session = requests.Session()
        self.links_collected = []
        
    def construct_search_url(self, query: str, sort_by: str = 'relevance', 
                           condition: str = 'all', offset: int = 0) -> str:
        """
        Construct Mercado Livre search URL based on parameters
        Adapted from Challenge-HP's spider URL construction logic
        """
        # Path slug from query (e.g., "cartucho-hp-667" -> "cartucho-hp-667")
        path_slug = query.replace(' ', '-').lower()
        
        # Initialize URL components
        url_path_segments = [path_slug]
        url_query_params = {}
        url_fragment_dict = {'A': quote(query)}
        
        # Apply sorting
        if sort_by == 'relevance':
            url_query_params['sb'] = 'all_mercadolibre'
        elif sort_by == 'price_asc':
            url_path_segments.append("_OrderId_PRICE")
            url_fragment_dict['O'] = 'PRICE_ASC'
        elif sort_by == 'price_desc':
            url_path_segments.append("_OrderId_PRICE")
            url_fragment_dict['O'] = 'PRICE_DESC'
            
        # Apply condition filter
        condition_map = {
            'new': '2230284',
            'used': '2230581',
        }
        if condition and condition != 'all' and condition in condition_map:
            url_path_segments.append(f"_ITEM*CONDITION_{condition_map[condition]}")
            
        # Add pagination offset
        if offset > 0:
            url_path_segments.append(f"_Desde_{offset}")
            
        # Join path segments
        final_path = url_path_segments[0]
        if len(url_path_segments) > 1:
            final_path += "".join([segment for segment in url_path_segments[1:]])
            
        # Construct fragment string: D[K:V,K:V]
        fragment_string = "D[" + ",".join([f"{k}:{v}" for k, v in url_fragment_dict.items()]) + "]"
        
        # Assemble final URL
        url = self.base_url + final_path
        if url_query_params:
            url += "?" + urlencode(url_query_params)
        url += "#" + fragment_string
        
        return url
        
    def extract_product_links(self, html_content: str) -> List[Dict[str, str]]:
        """
        Extract product links and basic info from search results HTML
        Based on Challenge-HP's spider parsing logic
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # Try multiple selectors (from Challenge-HP spider)
        selectors = [
            'li.ui-search-layout__item',
            'div.andes-card.poly-card',
            'div.ui-search-result__wrapper'
        ]
        
        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.info(f"Found {len(items)} items with selector: {selector}")
                break
                
        if not items:
            logger.warning("No products found in search results")
            return products
            
        # Skip first 2 items (usually sponsored)
        items_to_process = items[2:] if len(items) > 2 else items
        
        for item in items_to_process:
            # Extract link
            link_elem = (item.select_one('a.ui-search-item__group__element') or 
                        item.select_one('a.ui-search-link') or
                        item.select_one('h3.poly-component__title-wrapper a.poly-component__title'))
            
            if link_elem and link_elem.get('href'):
                link = link_elem['href']
                
                # Extract title
                title_elem = (item.select_one('h2.ui-search-item__title') or
                             item.select_one('.ui-search-item__title') or
                             item.select_one('h3.poly-component__title-wrapper a.poly-component__title'))
                
                title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                
                # Extract product ID from link
                match_id = re.search(r'/p/([^#?]+)', link)
                product_id = match_id.group(1) if match_id else None
                
                # Extract price
                price_elem = item.select_one('.andes-money-amount__fraction')
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                
                # Extract seller
                seller_elem = (item.select_one('a.ui-search-official-store-item__link') or
                              item.select_one('.ui-search-seller__name') or
                              item.select_one('span.poly-component__seller'))
                
                seller = "N/A"
                if seller_elem:
                    seller = seller_elem.get_text(strip=True).replace("Por ", "")
                
                products.append({
                    'url': link,
                    'title': title,
                    'product_id': product_id,
                    'price': price,
                    'seller': seller
                })
                
        return products
        
    def search_hp_cartridges(self, queries: List[str], max_results_per_query: int = 50,
                           sort_by: str = 'relevance', condition: str = 'all',
                           delay_range: tuple = (1, 3)) -> List[Dict[str, str]]:
        """
        Search for HP cartridges and collect product links
        
        Args:
            queries: List of search queries (e.g., ["cartucho hp 667", "cartucho hp 664"])
            max_results_per_query: Maximum results to collect per query
            sort_by: Sort method ('relevance', 'price_asc', 'price_desc')
            condition: Product condition ('all', 'new', 'used')
            delay_range: Random delay range between requests (min, max) in seconds
            
        Returns:
            List of product dictionaries with URLs and metadata
        """
        all_products = []
        
        for query in queries:
            logger.info(f"Searching for: {query}")
            query_products = []
            offset = 0
            page = 1
            
            while len(query_products) < max_results_per_query:
                # Construct search URL
                url = self.construct_search_url(query, sort_by, condition, offset)
                logger.info(f"Fetching page {page} from: {url}")
                
                # Make request with random user agent
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                }
                
                try:
                    response = self.session.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Extract products from page
                    products = self.extract_product_links(response.text)
                    
                    if not products:
                        logger.warning(f"No more products found for query: {query}")
                        break
                        
                    # Add query info to products
                    for product in products:
                        product['search_query'] = query
                        product['search_page'] = page
                        
                    query_products.extend(products)
                    logger.info(f"Collected {len(products)} products from page {page}")
                    
                    # Check if we have enough
                    if len(query_products) >= max_results_per_query:
                        query_products = query_products[:max_results_per_query]
                        break
                        
                    # Prepare for next page
                    offset += 50  # Mercado Livre typically shows 50 results per page
                    page += 1
                    
                    # Random delay to avoid being blocked
                    delay = random.uniform(*delay_range)
                    logger.info(f"Waiting {delay:.1f} seconds before next request...")
                    time.sleep(delay)
                    
                except requests.RequestException as e:
                    logger.error(f"Error fetching page {page} for query '{query}': {e}")
                    break
                    
            all_products.extend(query_products)
            logger.info(f"Total collected for '{query}': {len(query_products)} products")
            
            # Delay between different queries
            if query != queries[-1]:  # Not the last query
                delay = random.uniform(*delay_range)
                logger.info(f"Waiting {delay:.1f} seconds before next query...")
                time.sleep(delay)
                
        self.links_collected = all_products
        return all_products
        
    def save_results(self, output_dir: str = "data"):
        """Save collected links in multiple formats"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON (full data)
        json_file = output_path / f"hp_cartridge_links_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.links_collected, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.links_collected)} products to {json_file}")
        
        # Save as text file (just URLs for easy processing)
        txt_file = output_path / f"hp_cartridge_urls_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            for product in self.links_collected:
                f.write(product['url'] + '\n')
        logger.info(f"Saved {len(self.links_collected)} URLs to {txt_file}")
        
        # Save summary CSV
        csv_file = output_path / f"hp_cartridge_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if self.links_collected:
                import csv
                fieldnames = ['url', 'title', 'product_id', 'price', 'seller', 'search_query']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for product in self.links_collected:
                    writer.writerow({k: product.get(k, '') for k in fieldnames})
        logger.info(f"Saved summary to {csv_file}")
        
        return {
            'json_file': str(json_file),
            'txt_file': str(txt_file),
            'csv_file': str(csv_file),
            'total_links': len(self.links_collected)
        }


def main():
    """Example usage"""
    # Initialize generator
    generator = HPCartridgeLinkGenerator()
    
    # Define HP cartridge search queries
    # Based on common HP cartridge models from Challenge-HP
    queries = [
        "cartucho hp 667 preto",
        "cartucho hp 667 colorido",
        "cartucho hp 664 preto",
        "cartucho hp 664 colorido",
        "cartucho hp 662",
        "cartucho hp 954",
        "cartucho hp gt"
    ]
    
    # You can also search for specific conditions or suspicious listings
    # queries = ["cartucho hp compatível", "cartucho hp genérico", "cartucho hp barato"]
    
    # Search and collect links
    logger.info("Starting HP cartridge link collection...")
    products = generator.search_hp_cartridges(
        queries=queries,
        max_results_per_query=20,  # Adjust as needed
        sort_by='relevance',        # Options: 'relevance', 'price_asc', 'price_desc'
        condition='all',            # Options: 'all', 'new', 'used'
        delay_range=(1, 3)          # Random delay between requests
    )
    
    # Save results
    if products:
        results = generator.save_results()
        print(f"\n✅ Link collection complete!")
        print(f"📊 Total links collected: {results['total_links']}")
        print(f"📁 Files saved:")
        print(f"   - URLs: {results['txt_file']}")
        print(f"   - Full data: {results['json_file']}")
        print(f"   - Summary: {results['csv_file']}")
        print(f"\n🚀 Next steps:")
        print(f"   1. Run: python generativa_sprint1.py {results['txt_file']}")
        print(f"   2. Then: python 'sprint2_llm_classifier copy.py'")
    else:
        print("❌ No links collected. Check logs for errors.")


if __name__ == "__main__":
    main() 