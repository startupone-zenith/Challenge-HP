# -*- coding: utf-8 -*-
# REVISED FOR SPRINT 2 COMPATIBILITY -------------------------------------------------
"""
Sprint 1 – Extração de Dados Estruturados para Anúncios de Cartuchos HP (Revisado v2)
===================================================================================
Este script coleta páginas de anúncios de cartuchos HP (ex. Mercado Livre) e
produz saídas JSON/CSV totalmente estruturadas que se alinham com os campos consumidos
pelo `sprint2_llm_classifier.py`.

Principais melhorias em relação ao protótipo inicial:
1. Paridade de campos – Todos os atributos esperados pelo modelo `CartuchoAnuncio` do Sprint 2
   agora são extraídos (`seller_name`, `seller_reputation`, `listing_age_days`, …).
2. Processamento em lote – Passe um arquivo de texto com uma URL por linha ou uma lista
   via linha de comando; cada página é buscada e processada em sequência.
3. Modo JSON do OpenAI – Utiliza o formato de resposta "json_object" do Chat Completion para
   saída estruturada confiável do LLM. Um esquema Pydantic robusto valida
   a resposta.
4. Persistência – Os resultados são salvos em `data/extracted_ads.json` e
   `data/extracted_ads.csv` para consumo imediato pelo Sprint 2.
5. Logging e retentativas – Logging integrado mais lógica simples de retentativa para
   problemas de rede/LLM.

Exemplo
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
# Configuração
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise EnvironmentError("A variável de ambiente OPENAI_API_KEY não está definida.")

HEADERS = {"User-Agent": "Mozilla/5.0 (Sprint1 Extractor)"}
REQUEST_RETRIES = 3
REQUEST_BACKOFF = 2  # segundos
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
# Modelo de dados (deve corresponder ao do Sprint 2)
# ---------------------------------------------------------------------------
class CartuchoAnuncio(BaseModel):
    titulo: Optional[str] = Field(None, description="Título do produto")
    marca: Optional[str] = Field(None, description="Nome da marca")
    modelo: Optional[str] = Field(None, description="Número do modelo (ex: 667)")
    preco: Optional[float] = Field(None, description="Preço em BRL")
    cor: Optional[str] = Field(None, description="Cor (preto/color)")
    qualidade_descricao: Optional[str] = Field(None, description="Descrição textual completa")
    quantidade_reviews: Optional[int] = Field(None, description="Número de avaliações de usuários")
    avaliacao: Optional[float] = Field(None, description="Avaliação média (0-5)")
    quantidade_fotos: Optional[int] = Field(None, description="Número de imagens no anúncio")
    seller_name: Optional[str] = Field(None, description="Nome do vendedor")
    seller_reputation: Optional[str] = Field(None, description="Nível de reputação (novo/bronze/silver/gold/platinum)")
    listing_age_days: Optional[int] = Field(None, description="Dias desde que o anúncio foi criado")

# ---------------------------------------------------------------------------
# Funções Auxiliares
# ---------------------------------------------------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_html(url: str) -> str:
    """Busca o HTML da página com lógica básica de retentativa."""
    for attempt in range(1, REQUEST_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.warning(f"[{attempt}/{REQUEST_RETRIES}] Falha ao buscar {url}: {exc}")
            time.sleep(REQUEST_BACKOFF * attempt)
    raise ConnectionError(f"Não foi possível obter {url} após {REQUEST_RETRIES} tentativas.")

def extract_text(html: str) -> str:
    """Retorna texto legível do HTML bruto para análise do LLM."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")

def call_llm_for_structured_data(page_text: str) -> CartuchoAnuncio:
    """Invoca o ChatCompletion do OpenAI com modo JSON para analisar detalhes do anúncio."""
    system_prompt = (
        "Você é um assistente especialista em classificar e extrair atributos de anúncios "
        "de cartuchos de impressora HP no Mercado Livre. Extraia os seguintes campos "
        "em formato JSON (use chaves exatamente como abaixo). IMPORTANTE: para valores numéricos "
        "(preço, avaliação, quantidades) utilize ponto como separador decimal e não use símbolo 'R$'.\n\n"
        "Campos esperados: titulo, marca, modelo, preco, cor, qualidade_descricao, "
        "quantidade_reviews, avaliacao, quantidade_fotos, seller_name, seller_reputation, "
        "listing_age_days."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": page_text[:30_000]},  # protege o limite de tokens
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # rápido e barato; ajuste conforme necessário
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=512,
    )

    raw_json = response.choices[0].message.content
    try:
        data = json.loads(raw_json)

        # --- Normalização --------------------------------------------------
        def _to_float(val):
            if isinstance(val, (float, int)):
                return float(val)
            if isinstance(val, str):
                val = val.replace("R$", "").replace(" ", "").replace(",", ".")
                try:
                    return float(val)
                except ValueError:
                    return None
            return None

        data["preco"] = _to_float(data.get("preco"))
        data["avaliacao"] = _to_float(data.get("avaliacao"))

        for key in ["quantidade_reviews", "quantidade_fotos", "listing_age_days"]:
            if key in data and isinstance(data[key], str):
                cleaned = data[key].replace(".", "").replace(",", "")
                data[key] = int(cleaned) if cleaned.isdigit() else None

        return CartuchoAnuncio(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error(f"Falha ao analisar/validar a saída do LLM: {exc}. Saída bruta: {raw_json}")
        raise

# ---------------------------------------------------------------------------
# Rotina Principal
# ---------------------------------------------------------------------------

def process_urls(urls: List[str]) -> List[Dict]:
    """Busca, analisa e estrutura anúncios de uma lista de URLs."""
    structured_ads: List[Dict] = []
    for idx, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue
        logger.info(f"[{idx}/{len(urls)}] Processando {url}")
        try:
            html = fetch_html(url)
            page_text = extract_text(html)
            cartucho = call_llm_for_structured_data(page_text)
            record = cartucho.dict()
            record["source_url"] = url  # mantém a proveniência
            structured_ads.append(record)
        except Exception as exc:
            logger.error(f"Pulando {url} devido a erro: {exc}")
    return structured_ads


def save_outputs(records: List[Dict]):
    """Persiste as saídas em JSON e CSV para uso posterior pelo Sprint 2."""
    if not records:
        logger.warning("Nenhum registro para salvar.")
        return

    json_path = OUTPUT_DIR / "extracted_ads.json"
    csv_path = OUTPUT_DIR / "extracted_ads.csv"

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(records, jf, ensure_ascii=False, indent=2)
    logger.info(f"Dataset JSON salvo em {json_path} ({len(records)} registros)")

    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"Dataset CSV salvo em {csv_path}")

# ---------------------------------------------------------------------------
# Ponto de Entrada
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) == 1:
        logger.info("Nenhuma lista de URLs fornecida, usando URL de demonstração única.")
        demo_url = "https://www.mercadolivre.com.br/cartucho-hp-667-preto-2376-2776-6476/p/MLB22022306"
        urls_to_process = [demo_url]
    else:
        input_arg = sys.argv[1]
        if Path(input_arg).is_file():
            urls_to_process = Path(input_arg).read_text(encoding="utf-8").splitlines()
        else:
            # Trata os argumentos restantes da CLI como URLs
            urls_to_process = sys.argv[1:]

    dataset = process_urls(urls_to_process)
    save_outputs(dataset)

    logger.info("Extração concluída.")