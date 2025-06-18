# -*- coding: utf-8 -*-
# REVISED FOR SPRINT 2 COMPATIBILITY -------------------------------------------------
"""
Sprint 1 – Structured Data Extraction for HP Cartridge Ads (Revised v2)
======================================================================
This script harvests HP cartridge advertisement pages (e.g. Mercado Livre) and
produces fully-structured JSON/CSV outputs that align with the fields consumed
by `sprint2_llm_classifier.py`.

Key improvements over the initial prototype:
1. Field parity – All attributes expected by the Sprint 2 `CartuchoAnuncio` model
   are now extracted (`seller_name`, `seller_reputation`, `listing_age_days`, …).
2. Batch processing – Pass a text file with one URL per line or a list via
   command-line; each page is fetched and processed in sequence.
3. OpenAI JSON mode – Uses the Chat Completion "json_object" response format for
   reliable structured output from the LLM. A robust Pydantic schema validates
   the response.
4. Persistence – Results are saved in `data/extracted_ads.json` and
   `data/extracted_ads.csv` for immediate consumption by Sprint 2.
5. Logging & retries – Built-in logging plus simple retry logic for network/LLM
   hiccups.

Example
-------
$ python generativa_sprint1.py urls.txt
"""

import os
import sys
import csv
import json
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable not set.")

HEADERS = {"User-Agent": "Mozilla/5.0 (Sprint1 Extractor)"}
REQUEST_RETRIES = 3
REQUEST_BACKOFF = 2  # seconds
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "extractor.log", encoding="utf-8")
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model (must match Sprint 2)
# ---------------------------------------------------------------------------
class CartuchoAnuncio(BaseModel):
    titulo: Optional[str] = Field(None, description="Product title")
    marca: Optional[str] = Field(None, description="Brand name")
    modelo: Optional[str] = Field(None, description="Model number (e.g., 667)")
    preco: Optional[float] = Field(None, description="Price in BRL")
    cor: Optional[str] = Field(None, description="Color (preto/color)")
    qualidade_descricao: Optional[str] = Field(None, description="Full textual description")
    quantidade_reviews: Optional[int] = Field(None, description="Number of user reviews")
    avaliacao: Optional[float] = Field(None, description="Average rating (0-5)")
    quantidade_fotos: Optional[int] = Field(None, description="Number of images on listing")
    seller_name: Optional[str] = Field(None, description="Name of the seller")
    seller_reputation: Optional[str] = Field(None, description="Reputation tier (novo/bronze/silver/gold/platinum)")
    listing_age_days: Optional[int] = Field(None, description="Days since the listing was created")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_html(url: str) -> str:
    """Fetch page HTML with basic retry logic."""
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning(f"[{attempt}/{REQUEST_RETRIES}] Failed to fetch {url}: {exc}")
            time.sleep(REQUEST_BACKOFF * attempt)
    raise ConnectionError(f"Could not retrieve {url} after {REQUEST_RETRIES} attempts.")

def extract_text(html: str) -> str:
    """Return readable text from raw HTML for LLM analysis."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")

def call_llm_for_structured_data(page_text: str) -> CartuchoAnuncio:
    """Invoke OpenAI ChatCompletion with JSON mode to parse ad details."""
    system_prompt = (
        "Você é um assistente especialista em classificar e extrair atributos de anúncios "
        "de cartuchos de impressora HP no Mercado Livre. Extraia os seguintes campos "
        "em formato JSON (use chaves exatamente como abaixo):\n\n"
        "titulo, marca, modelo, preco, cor, qualidade_descricao, quantidade_reviews, "
        "avaliacao, quantidade_fotos, seller_name, seller_reputation, listing_age_days."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": page_text[:30_000]},  # safeguard token limit
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # fast & inexpensive; adjust as needed
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=512,
    )

    raw_json = response.choices[0].message.content
    try:
        data = json.loads(raw_json)
        return CartuchoAnuncio(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error(f"Failed to parse/validate LLM output: {exc}. Raw output: {raw_json}")
        raise

# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def process_urls(urls: List[str]) -> List[Dict]:
    """Fetch, parse and structure ads from a list of URLs."""
    structured_ads: List[Dict] = []
    for idx, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue
        logger.info(f"[{idx}/{len(urls)}] Processing {url}")
        try:
            html = fetch_html(url)
            page_text = extract_text(html)
            cartucho = call_llm_for_structured_data(page_text)
            record = cartucho.dict()
            record["source_url"] = url  # keep provenance
            structured_ads.append(record)
        except Exception as exc:
            logger.error(f"Skipping {url} due to error: {exc}")
    return structured_ads


def save_outputs(records: List[Dict]):
    """Persist outputs to JSON and CSV for later use by Sprint 2."""
    if not records:
        logger.warning("No records to save.")
        return

    json_path = OUTPUT_DIR / "extracted_ads.json"
    csv_path = OUTPUT_DIR / "extracted_ads.csv"

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(records, jf, ensure_ascii=False, indent=2)
    logger.info(f"Saved JSON dataset to {json_path} ({len(records)} records)")

    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Saved CSV dataset to {csv_path}")

# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.info("No URL list provided, defaulting to hard-coded single demo URL.")
        demo_url = "https://www.mercadolivre.com.br/cartucho-hp-667-preto-2376-2776-6476/p/MLB22022306"
        urls_to_process = [demo_url]
    else:
        input_arg = sys.argv[1]
        if Path(input_arg).is_file():
            urls_to_process = Path(input_arg).read_text(encoding="utf-8").splitlines()
        else:
            # Treat remaining CLI args as URLs
            urls_to_process = sys.argv[1:]

    dataset = process_urls(urls_to_process)
    save_outputs(dataset)

    logger.info("Extraction complete.")