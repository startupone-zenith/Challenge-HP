# -*- coding: utf-8 -*-
"""
Gerador de Links de Cartuchos HP para o Pipeline Sprint 1/2
===========================================================

Este script utiliza a lógica de busca do mercadolivre_spider do Challenge-HP
para gerar listas de links de produtos de cartuchos HP para processamento com:
- generativa_sprint1.py (extração de dados estruturados)
- sprint2_llm_classifier.py (classificação de autenticidade)

Autor: Integração Sprint_GENAI
Data: 2024
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

# Configura o logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# User agents para rotação (do Challenge-HP)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
]

class HPCartridgeLinkGenerator:
    """Gera links de produtos de cartuchos HP a partir do Mercado Livre"""
    
    def __init__(self):
        self.base_url = "https://lista.mercadolivre.com.br/"
        self.session = requests.Session()
        self.links_collected = []
        
    def construct_search_url(self, query: str, sort_by: str = 'relevance', 
                           condition: str = 'all', offset: int = 0) -> str:
        """
        Constrói a URL de busca do Mercado Livre com base nos parâmetros
        Adaptado da lógica de construção de URL do spider do Challenge-HP
        """
        # Slug do caminho a partir da query (ex: "cartucho-hp-667" -> "cartucho-hp-667")
        path_slug = query.replace(' ', '-').lower()
        
        # Inicializa os componentes da URL
        url_path_segments = [path_slug]
        url_query_params = {}
        url_fragment_dict = {'A': quote(query)}
        
        # Aplica a ordenação
        if sort_by == 'relevance':
            url_query_params['sb'] = 'all_mercadolibre'
        elif sort_by == 'price_asc':
            url_path_segments.append("_OrderId_PRICE")
            url_fragment_dict['O'] = 'PRICE_ASC'
        elif sort_by == 'price_desc':
            url_path_segments.append("_OrderId_PRICE")
            url_fragment_dict['O'] = 'PRICE_DESC'
            
        # Aplica o filtro de condição
        condition_map = {
            'new': '2230284',
            'used': '2230581',
        }
        if condition and condition != 'all' and condition in condition_map:
            url_path_segments.append(f"_ITEM*CONDITION_{condition_map[condition]}")
            
        # Adiciona o deslocamento de paginação
        if offset > 0:
            url_path_segments.append(f"_Desde_{offset}")
            
        # Junta os segmentos do caminho
        final_path = url_path_segments[0]
        if len(url_path_segments) > 1:
            final_path += "".join([segment for segment in url_path_segments[1:]])
            
        # Constrói a string de fragmento: D[K:V,K:V]
        fragment_string = "D[" + ",".join([f"{k}:{v}" for k, v in url_fragment_dict.items()]) + "]"
        
        # Monta a URL final
        url = self.base_url + final_path
        if url_query_params:
            url += "?" + urlencode(url_query_params)
        url += "#" + fragment_string
        
        return url
        
    def extract_product_links(self, html_content: str) -> List[Dict[str, str]]:
        """
        Extrai links de produtos e informações básicas do HTML dos resultados da busca
        Baseado na lógica de parsing do spider do Challenge-HP
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        # Tenta múltiplos seletores (do spider do Challenge-HP)
        selectors = [
            'li.ui-search-layout__item',
            'div.andes-card.poly-card',
            'div.ui-search-result__wrapper'
        ]
        
        items = []
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.info(f"Encontrados {len(items)} itens com o seletor: {selector}")
                break
                
        if not items:
            logger.warning("Nenhum produto encontrado nos resultados da busca")
            return products
            
        # Pula os 2 primeiros itens (geralmente patrocinados)
        items_to_process = items[2:] if len(items) > 2 else items
        
        for item in items_to_process:
            # Extrai o link
            link_elem = (item.select_one('a.ui-search-item__group__element') or 
                        item.select_one('a.ui-search-link') or
                        item.select_one('h3.poly-component__title-wrapper a.poly-component__title'))
            
            if link_elem and link_elem.get('href'):
                link = link_elem['href']
                
                # Extrai o título
                title_elem = (item.select_one('h2.ui-search-item__title') or
                             item.select_one('.ui-search-item__title') or
                             item.select_one('h3.poly-component__title-wrapper a.poly-component__title'))
                
                title = title_elem.get_text(strip=True) if title_elem else "Desconhecido"
                
                # Extrai o ID do produto do link
                match_id = re.search(r'/p/([^#?]+)', link)
                product_id = match_id.group(1) if match_id else None
                
                # Extrai o preço
                price_elem = item.select_one('.andes-money-amount__fraction')
                price = price_elem.get_text(strip=True) if price_elem else "N/A"
                
                # Extrai o vendedor
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
        Busca por cartuchos HP e coleta os links dos produtos
        
        Args:
            queries: Lista de consultas de busca (ex: ["cartucho hp 667", "cartucho hp 664"])
            max_results_per_query: Máximo de resultados a coletar por consulta
            sort_by: Método de ordenação ('relevance', 'price_asc', 'price_desc')
            condition: Condição do produto ('all', 'new', 'used')
            delay_range: Intervalo de atraso aleatório entre as requisições (min, max) em segundos
            
        Returns:
            Lista de dicionários de produtos com URLs e metadados
        """
        all_products = []
        
        for query in queries:
            logger.info(f"Buscando por: {query}")
            query_products = []
            offset = 0
            page = 1
            
            while len(query_products) < max_results_per_query:
                # Constrói a URL de busca
                url = self.construct_search_url(query, sort_by, condition, offset)
                logger.info(f"Buscando página {page} de: {url}")
                
                # Faz a requisição com um user agent aleatório
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
                    
                    # Extrai os produtos da página
                    products = self.extract_product_links(response.text)
                    
                    if not products:
                        logger.warning(f"Não foram encontrados mais produtos para a consulta: {query}")
                        break
                        
                    # Adiciona informações da consulta aos produtos
                    for product in products:
                        product['search_query'] = query
                        product['search_page'] = page
                        
                    query_products.extend(products)
                    logger.info(f"Coletados {len(products)} produtos da página {page}")
                    
                    # Verifica se já temos o suficiente
                    if len(query_products) >= max_results_per_query:
                        query_products = query_products[:max_results_per_query]
                        break
                        
                    # Prepara para a próxima página
                    offset += 50  # O Mercado Livre geralmente mostra 50 resultados por página
                    page += 1
                    
                    # Atraso aleatório para evitar bloqueio
                    delay = random.uniform(*delay_range)
                    logger.info(f"Aguardando {delay:.1f} segundos antes da próxima requisição...")
                    time.sleep(delay)
                    
                except requests.RequestException as e:
                    logger.error(f"Erro ao buscar a página {page} para a consulta '{query}': {e}")
                    break
                    
            all_products.extend(query_products)
            logger.info(f"Total coletado para '{query}': {len(query_products)} produtos")
            
            # Atraso entre consultas diferentes
            if query != queries[-1]:  # Não é a última consulta
                delay = random.uniform(*delay_range)
                logger.info(f"Aguardando {delay:.1f} segundos antes da próxima consulta...")
                time.sleep(delay)
                
        self.links_collected = all_products
        return all_products
        
    def save_results(self, output_dir: str = "data"):
        """Salva os links coletados em múltiplos formatos"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salva como JSON (dados completos)
        json_file = output_path / f"hp_cartridge_links_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.links_collected, f, ensure_ascii=False, indent=2)
        logger.info(f"Salvos {len(self.links_collected)} produtos em {json_file}")
        
        # Salva como arquivo de texto (apenas URLs para processamento fácil)
        txt_file = output_path / f"hp_cartridge_urls_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            for product in self.links_collected:
                f.write(product['url'] + '\n')
        logger.info(f"Salvas {len(self.links_collected)} URLs em {txt_file}")
        
        # Salva um resumo em CSV
        csv_file = output_path / f"hp_cartridge_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if self.links_collected:
                import csv
                fieldnames = ['url', 'title', 'product_id', 'price', 'seller', 'search_query']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for product in self.links_collected:
                    writer.writerow({k: product.get(k, '') for k in fieldnames})
        logger.info(f"Resumo salvo em {csv_file}")
        
        return {
            'json_file': str(json_file),
            'txt_file': str(txt_file),
            'csv_file': str(csv_file),
            'total_links': len(self.links_collected)
        }


def main():
    """Exemplo de uso"""
    # Inicializa o gerador
    generator = HPCartridgeLinkGenerator()
    
    # Define as consultas de busca para cartuchos HP
    # Baseado nos modelos de cartuchos HP comuns do Challenge-HP
    queries = [
        "cartucho hp 667 preto",
        "cartucho hp 667 colorido",
        "cartucho hp 664 preto",
        "cartucho hp 664 colorido",
        "cartucho hp 662",
        "cartucho hp 954",
        "cartucho hp gt"
    ]
    
    # Você também pode buscar por condições específicas ou anúncios suspeitos
    # queries = ["cartucho hp compatível", "cartucho hp genérico", "cartucho hp barato"]
    
    # Busca e coleta os links
    logger.info("Iniciando a coleta de links de cartuchos HP...")
    products = generator.search_hp_cartridges(
        queries=queries,
        max_results_per_query=20,  # Ajuste conforme necessário
        sort_by='relevance',        # Opções: 'relevance', 'price_asc', 'price_desc'
        condition='all',            # Opções: 'all', 'new', 'used'
        delay_range=(1, 3)          # Atraso aleatório entre requisições
    )
    
    # Salva os resultados
    if products:
        results = generator.save_results()
        print(f"\n✅ Coleta de links concluída!")
        print(f"📊 Total de links coletados: {results['total_links']}")
        print(f"📁 Arquivos salvos:")
        print(f"   - URLs: {results['txt_file']}")
        print(f"   - Dados completos: {results['json_file']}")
        print(f"   - Resumo: {results['csv_file']}")
        print(f"\n🚀 Próximos passos:")
        print(f"   1. Execute: python generativa_sprint1.py {results['txt_file']}")
        print(f"   2. Em seguida: python 'sprint2_llm_classifier copy.py'")
    else:
        print("❌ Nenhum link foi coletado. Verifique os logs para erros.")


if __name__ == "__main__":
    main() 