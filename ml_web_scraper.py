#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import csv
import os
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote

class MercadoLivreWebScraper:
    """Classe para fazer scraping de produtos no Mercado Livre quando a API falha"""
    
    def __init__(self, output_dir="ml_data_exports"):
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Criar diretório de output se não existir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def search_items(self, query, site_id="MLB", limit=50):
        """Buscar produtos usando web scraping
        
        Args:
            query (str): Termo de busca
            site_id (str): ID do site (MLB, MLA, etc.)
            limit (int): Número máximo de resultados
            
        Returns:
            list: Lista de produtos encontrados
        """
        site_domains = {
            "MLB": "mercadolivre.com.br",
            "MLA": "mercadolibre.com.ar",
            "MLM": "mercadolibre.com.mx",
            "MCO": "mercadolibre.com.co",
            "MLU": "mercadolibre.com.uy",
            "MLC": "mercadolibre.cl",
            "MPE": "mercadolibre.com.pe",
            "MLV": "mercadolibre.com.ve"
        }
        
        domain = site_domains.get(site_id, "mercadolivre.com.br")
        encoded_query = quote(query)
        
        # URL correta para buscas no Mercado Livre (testada em maio 2025)
        url = f"https://{domain}/ofertas.html?q={encoded_query}"
        
        # URLs alternativas caso a primeira falhe
        alternate_urls = [
            f"https://{domain}/busca/{encoded_query}",
            f"https://lista.{domain}/{encoded_query}",
            f"https://{domain}/{encoded_query}",
            f"https://{domain}/ofertas"
        ]
        
        print(f"Buscando '{query}' via web scraping: {url}")
        
        # Tentar a URL principal
        response = None
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                print(f"Erro ao acessar a URL principal: {response.status_code}")
                
                # Tentar URLs alternativas
                for alt_url in alternate_urls:
                    print(f"Tentando URL alternativa: {alt_url}")
                    try:
                        response = requests.get(alt_url, headers=self.headers, timeout=30)
                        if response.status_code == 200:
                            print(f"URL alternativa funcionou: {alt_url}")
                            url = alt_url  # Atualiza a URL para a que funcionou
                            break
                    except Exception as e:
                        print(f"Erro na URL alternativa: {str(e)}")
                
                # Se ainda não temos resposta válida
                if not response or response.status_code != 200:
                    print("Todas as URLs falharam.")
                    return None
                
        except Exception as e:
            print(f"Erro ao acessar a página: {str(e)}")
            return None
        
        try:
            # Salvar o HTML para debug (opcional)
            debug_file = os.path.join(self.output_dir, "debug_html.txt")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(response.text[:20000])  # Salvar apenas os primeiros 20K caracteres
            print(f"Salvou amostra do HTML em {debug_file} para debug")
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair produtos - o Mercado Livre tem uma estrutura complexa que muda frequentemente
            products = []
            
            # Tentar diferentes seletores para capturar os itens
            # Novas estruturas do Mercado Livre para 2025
            product_items = []
            
            # Verificar vários seletores comuns
            selectors = [
                '.ui-search-layout__item',                  # Layout comum
                '.ui-search-result__wrapper',               # Layout alternativo
                '.andes-card',                              # Cartões
                'li.ui-search-layout__item',                # Itens em lista
                '.shops__item',                             # Lojas oficiais
                'div[class*="search-result"]',              # Qualquer resultado de busca
                '.ui-search-result',                        # Mais genérico
                'div[data-testid="search-result-item"]',    # Testid específico
                '.promotion-item',                          # Itens de promoção
                '.item__info',                              # Informação do item
                'div[class*="item"]'                        # Qualquer item
            ]
            
            # Tentar todos os seletores
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    print(f"Encontrados {len(items)} itens com o seletor: {selector}")
                    product_items.extend(items)
                    
            # Remover duplicados (caso algum item seja capturado por mais de um seletor)
            unique_items = []
            item_ids = set()
            
            for item in product_items:
                # Tentar encontrar um ID único para o item
                item_id = None
                
                # Buscar o link e extrair o ID
                link_tag = item.select_one('a[href*="/MLB"]') or \
                          item.select_one('a[href*="/p/"]') or \
                          item.select_one('a.ui-search-link') or \
                          item.select_one('a[href*="mercado"]')
                
                if link_tag and link_tag.get('href'):
                    # Extrair ID do produto do link
                    id_match = re.search(r'/([A-Z]{3}\d+)', link_tag.get('href'))
                    if id_match:
                        item_id = id_match.group(1)
                
                # Se não conseguiu um ID, gera um baseado na posição
                if not item_id:
                    item_id = f"item_{len(unique_items)}"
                
                # Só adiciona se não for duplicado
                if item_id not in item_ids:
                    item_ids.add(item_id)
                    unique_items.append(item)
            
            print(f"Encontrados {len(unique_items)} produtos únicos na página.")
            
            # Se não encontrou produtos, tenta extrair de forma mais simples
            if not unique_items:
                print("Tentando extrair links diretos...")
                # Buscar todos os links que possam ser de produtos
                all_links = soup.select('a[href*="/MLB"]')
                unique_links = {}
                
                for link in all_links:
                    href = link.get('href', '')
                    if 'MLB' in href and href not in unique_links:
                        # Verificar se parece um link de produto
                        if re.search(r'/MLB\d+', href):
                            title_element = link.select_one('span') or link
                            title = title_element.get_text(strip=True) or "Produto"
                            unique_links[href] = {
                                'link': href,
                                'nome_produto': title or "Produto Mercado Livre",
                                'vendedor': "Vendedor Mercado Livre"
                            }
                
                if unique_links:
                    print(f"Encontrados {len(unique_links)} links de produtos.")
                    unique_items = list(unique_links.values())
            
            # Processar apenas o limite solicitado
            unique_items = unique_items[:limit]
            
            for item in unique_items:
                # Se já é um dicionário com os campos necessários, adiciona diretamente
                if isinstance(item, dict) and 'link' in item and 'nome_produto' in item:
                    products.append(item)
                    continue
                    
                # Tentar extrair as informações principais
                product = {}
                
                # Link e ID do produto - tentar vários seletores comuns
                link_tag = None
                link_selectors = [
                    'a.ui-search-link',
                    'a.ui-search-item__group__element',
                    'a[href*="/MLB"]',
                    'a[href*="/p/"]',
                    'a.ui-search-result__content',
                    'a.shops__item-title',
                    'a.ui-search-item__title',
                    'a[data-testid="link-product"]'
                ]
                
                for link_selector in link_selectors:
                    link_tag = item.select_one(link_selector)
                    if link_tag and link_tag.get('href'):
                        product['link'] = link_tag.get('href')
                        break
                
                # Se encontrou link, extrair ID
                if 'link' in product:
                    id_match = re.search(r'/([A-Z]{3}\d+)', product['link'])
                    if id_match:
                        product['id'] = id_match.group(1)
                
                # Nome do produto - tentar vários seletores comuns
                title_tag = None
                title_selectors = [
                    'h2.ui-search-item__title',
                    '.ui-search-item__title',
                    '.ui-search-item__group__element h2',
                    '.ui-search-result-product__title',
                    '.shops__item-title',
                    'h2[class*="title"]',
                    'span[class*="title"]',
                    '.ui-search-result__content-title'
                ]
                
                for title_selector in title_selectors:
                    title_tag = item.select_one(title_selector)
                    if title_tag:
                        product['nome_produto'] = title_tag.text.strip()
                        break
                        
                # Se não encontrou título mas tem link, tenta extrair do link
                if 'nome_produto' not in product and 'link' in product:
                    # Usar regex para tentar extrair o título da URL
                    title_match = re.search(r'/([\w-]+)-(?:[A-Z]{3}\d+)', product['link'])
                    if title_match:
                        title = title_match.group(1).replace('-', ' ').title()
                        product['nome_produto'] = title
                
                # Vendedor - mais difícil de extrair via scraping
                seller_tag = None
                seller_selectors = [
                    '.ui-search-official-store-label',
                    '.ui-search-item__brand-discoverability',
                    '.ui-search-item__brand',
                    '.ui-search-result__content-seller',
                    '.ui-search-seller-info',
                    'span[class*="seller"]',
                    'p[class*="seller"]'
                ]
                
                for seller_selector in seller_selectors:
                    seller_tag = item.select_one(seller_selector)
                    if seller_tag:
                        product['vendedor'] = seller_tag.text.strip()
                        break
                
                # Se não encontrou vendedor, usa padrão
                if 'vendedor' not in product:
                    product['vendedor'] = "Vendedor Mercado Livre"
                
                # Adicionar o produto se tiver pelo menos link e nome
                if 'link' in product and ('nome_produto' in product or 'id' in product):
                    # Se tem ID mas não tem nome, usa ID como nome
                    if 'nome_produto' not in product and 'id' in product:
                        product['nome_produto'] = f"Produto {product['id']}"
                        
                    # Se não tem vendedor, adiciona um padrão    
                    if 'vendedor' not in product:
                        product['vendedor'] = "Vendedor Mercado Livre"
                        
                    products.append(product)
            
            print(f"Extraídos dados de {len(products)} produtos.")
            return products
            
        except Exception as e:
            print(f"Erro ao fazer scraping: {str(e)}")
            # Print stack trace para debug
            import traceback
            traceback.print_exc()
            return None
    
    def export_to_csv(self, products, query, site_id="MLB"):
        """Exportar produtos para CSV
        
        Args:
            products (list): Lista de produtos
            query (str): Termo de busca
            site_id (str): ID do site
            
        Returns:
            str: Caminho do arquivo CSV
        """
        if not products:
            print("Nenhum produto para exportar.")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_term_slug = query.replace(" ", "_").lower()
        csv_filename = f"simple_{search_term_slug}_{site_id}_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, csv_filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['link', 'nome_produto', 'vendedor']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for product in products:
                    # Garantir que temos todos os campos
                    row = {
                        'link': product.get('link', ''),
                        'nome_produto': product.get('nome_produto', 'Sem título'),
                        'vendedor': product.get('vendedor', 'N/A')
                    }
                    writer.writerow(row)
            
            print(f"Dados exportados para {filepath}")
            print(f"Total de {len(products)} produtos exportados.")
            return filepath
            
        except Exception as e:
            print(f"Erro ao salvar CSV: {str(e)}")
            return None

if __name__ == "__main__":
    # Teste do scraper
    scraper = MercadoLivreWebScraper()
    products = scraper.search_items("notebook", "MLB", 20)
    
    if products:
        scraper.export_to_csv(products, "notebook", "MLB") 