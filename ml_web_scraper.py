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
import pandas as pd
import time
import sys

def ensure_package_installed(package_name):
    """Verifica se um pacote está instalado e o instala se necessário"""
    try:
        __import__(package_name)
        print(f"Pacote {package_name} já está instalado")
        return True
    except ImportError:
        print(f"Instalando pacote {package_name}...")
        try:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"Pacote {package_name} instalado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao instalar o pacote {package_name}: {str(e)}")
            return False

# Garantir que os pacotes necessários estão instalados
for package in ['requests', 'beautifulsoup4', 'pandas', 'lxml']:
    if not ensure_package_installed(package):
        print(f"Não foi possível instalar {package}. Saindo...")
        sys.exit(1)

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

def scrape_mercado_livre(search_term, site_code="MLB", max_results=50):
    """
    Faz web scraping do Mercado Livre para buscar produtos
    
    Args:
        search_term (str): Termo de busca
        site_code (str): Código do país (MLB para Brasil, MLA para Argentina, etc.)
        max_results (int): Número máximo de resultados a retornar
        
    Returns:
        list: Lista de dicionários com dados dos produtos
    """
    print(f"Iniciando web scraping para: {search_term}")
    
    # Formatar o termo de busca para URL (substituir espaços por hífen)
    search_url_term = search_term.replace(" ", "-")
    
    # URL base para busca
    base_url = f"https://lista.mercadolivre.com.br/{search_url_term}"
    if site_code != "MLB":
        # Ajustar URL para outros países
        domain = site_code.replace("ML", "").lower()
        base_url = f"https://listado.mercadolibre.com.{domain}/{search_url_term}"
    
    print(f"URL de busca: {base_url}")
    
    # Headers para simular um navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    products = []
    page = 1
    total_collected = 0
    
    try:
        while total_collected < max_results:
            # Adicionar parâmetro de página se não for a primeira página
            current_url = base_url
            if page > 1:
                current_url = f"{base_url}_Desde_{(page-1)*50+1}"
            
            print(f"Acessando página {page}: {current_url}")
            
            # Fazer a requisição HTTP
            response = requests.get(current_url, headers=headers)
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code != 200:
                print(f"Erro ao acessar a página {page}. Status code: {response.status_code}")
                break
            
            # Parsear o HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Encontrar os elementos de produto
            # A classe pode variar, então tentamos diferentes seletores
            product_elements = soup.select('.ui-search-layout__item')
            if not product_elements:
                product_elements = soup.select('.ui-search-result')
            if not product_elements:
                product_elements = soup.select('.ui-search-result__wrapper')
            
            if not product_elements:
                print("Não foi possível encontrar produtos na página. Estrutura do site pode ter mudado.")
                break
            
            print(f"Encontrados {len(product_elements)} produtos na página {page}")
            
            # Extrair informações de cada produto
            for product in product_elements:
                if total_collected >= max_results:
                    break
                
                try:
                    # Tentar diferentes seletores para o título
                    title_element = product.select_one('.ui-search-item__title') or product.select_one('h2')
                    title = title_element.text.strip() if title_element else "Título não encontrado"
                    
                    # Tentar diferentes seletores para o link
                    link_element = product.select_one('.ui-search-link') or product.select_one('a')
                    link = link_element['href'] if link_element else "#"
                    
                    # Tentar diferentes seletores para o preço
                    price_element = product.select_one('.price-tag-fraction')
                    price = price_element.text.strip() if price_element else "Preço não encontrado"
                    
                    # Tentar obter o vendedor
                    seller_element = product.select_one('.ui-search-official-store-label') or product.select_one('.ui-search-item__brand-discoverability')
                    seller = seller_element.text.strip() if seller_element else "Vendedor não especificado"
                    
                    # Tentar obter a condição do produto
                    condition_element = product.select_one('.ui-search-item__highlight-label__text')
                    condition = condition_element.text.strip() if condition_element else "Não especificado"
                    
                    # Adicionar à lista de produtos
                    products.append({
                        'title': title,
                        'link': link,
                        'price': price,
                        'seller': seller,
                        'condition': condition,
                        'site_code': site_code
                    })
                    
                    total_collected += 1
                    
                except Exception as e:
                    print(f"Erro ao extrair informações do produto: {str(e)}")
            
            # Verificar se há mais páginas
            next_page = soup.select_one('.andes-pagination__button--next a')
            if not next_page or not product_elements:
                print("Não há mais páginas para navegar.")
                break
            
            # Avançar para a próxima página
            page += 1
            
            # Esperar um pouco para evitar bloqueio
            time.sleep(2)
    
    except Exception as e:
        print(f"Erro durante o web scraping: {str(e)}")
    
    print(f"Total de produtos coletados: {len(products)}")
    return products

def export_to_csv(products, search_term, site_code):
    """
    Exporta os produtos para um arquivo CSV
    
    Args:
        products (list): Lista de dicionários com dados dos produtos
        search_term (str): Termo de busca usado
        site_code (str): Código do site (país)
        
    Returns:
        str: Caminho do arquivo CSV gerado
    """
    if not products:
        print("Nenhum produto para exportar.")
        return None
    
    # Criar diretório para exportação se não existir
    export_dir = "ml_data_exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    # Criar DataFrame
    df = pd.DataFrame(products)
    
    # Gerar nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_search = search_term.replace(" ", "_").lower()
    filename = f"{export_dir}/mercadolivre_{clean_search}_{site_code}_{timestamp}.csv"
    
    # Exportar para CSV
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"Dados exportados para: {filename}")
    return filename

def extract_product_details(products, site_code="MLB"):
    """
    Extrai detalhes adicionais de cada produto: preço, média de avaliações e ratio de avaliações 5/1 estrelas
    
    Args:
        products (list): Lista de produtos com links
        site_code (str): Código do site (país)
        
    Returns:
        list: Lista de produtos com informações adicionais
    """
    print(f"\nExtraindo detalhes adicionais de {len(products)} produtos...")
    
    # Headers para simular um navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    detailed_products = []
    
    for i, product in enumerate(products):
        try:
            # Obter o link do produto
            product_link = product.get('link')
            if not product_link:
                print(f"Produto {i+1}/{len(products)} não possui link, pulando...")
                detailed_products.append(product)
                continue
            
            print(f"Acessando detalhes do produto {i+1}/{len(products)}: {product_link}")
            
            # Fazer a requisição HTTP para a página de detalhes
            response = requests.get(product_link, headers=headers)
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code != 200:
                print(f"Erro ao acessar a página de detalhes. Status code: {response.status_code}")
                detailed_products.append(product)
                continue
            
            # Parsear o HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Opcional: Salvar HTML para debug
            debug_html_path = os.path.join("ml_data_exports", f"debug_produto_{i+1}.html")
            with open(debug_html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Extrair o preço
            price = None
            price_selectors = [
                '.andes-money-amount__fraction',
                '.price-tag-fraction',
                'span[class*="price"]',
                '.ui-pdp-price__second-line .andes-money-amount__fraction'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price = price_element.text.strip()
                    # Remover separadores de milhares
                    price = price.replace('.', '')
                    break
            
            # Extrair média de avaliações
            avg_rating = None
            rating_selectors = [
                '.ui-pdp-reviews__rating__summary__average',
                '.ui-pdp-review__rating-average',
                'span[class*="rating-average"]',
                '.review-summary-average'
            ]
            
            for selector in rating_selectors:
                rating_element = soup.select_one(selector)
                if rating_element:
                    try:
                        avg_rating = float(rating_element.text.strip().replace(',', '.'))
                    except ValueError:
                        # Tentar extrair números da string
                        rating_match = re.search(r'(\d+[,.]?\d*)', rating_element.text)
                        if rating_match:
                            avg_rating = float(rating_match.group(1).replace(',', '.'))
                    break
            
            # 1. Usar o seletor específico para obter o total de avaliações
            total_reviews = 0
            total_reviews_selector = "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div.ui-review-capability__rating > div.ui-review-capability__rating__start-content > div:nth-child(2) > p"
            total_reviews_element = soup.select_one(total_reviews_selector)
            
            if total_reviews_element:
                # Extrair número do texto (ex: "65 avaliações" -> 65)
                review_count_match = re.search(r'(\d+)', total_reviews_element.text)
                if review_count_match:
                    total_reviews = int(review_count_match.group(1))
                    product['total_avaliacoes'] = total_reviews
            
            # Se não encontrou pelo seletor específico, tentar métodos alternativos
            if not total_reviews:
                # Procurar script JSON com dados de avaliações
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        json_data = json.loads(script.string)
                        if 'aggregateRating' in json_data:
                            if not avg_rating:  # Só atualiza se não foi encontrado ainda
                                avg_rating = float(json_data['aggregateRating'].get('ratingValue', 0))
                            # Extrair total de avaliações
                            total_reviews = int(json_data['aggregateRating'].get('reviewCount', 0))
                            product['total_avaliacoes'] = total_reviews
                            break
                    except (json.JSONDecodeError, AttributeError):
                        pass
                
                # Se ainda não tem total, tentar outros seletores comuns
                if not total_reviews:
                    review_count_selectors = [
                        '.ui-pdp-reviews__amount',
                        '.ui-pdp-review__amount',
                        'span[class*="review-count"]'
                    ]
                    for selector in review_count_selectors:
                        count_element = soup.select_one(selector)
                        if count_element:
                            count_match = re.search(r'(\d+)', count_element.text)
                            if count_match:
                                total_reviews = int(count_match.group(1))
                                product['total_avaliacoes'] = total_reviews
                                break
            
            # Inicializar contadores e porcentagens por estrela
            star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            star_percentages = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
            
            # 2. Usar os seletores específicos para as barras de progresso
            # Lista de seletores para as barras de progresso (5 estrelas a 1 estrela)
            progress_bar_selectors = [
                "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > ul > li:nth-child(1) > div.ui-review-capability-rating__level__column.ui-review-capability-rating__level__progress-bar-container > div > span.ui-review-capability-rating__level__progress-bar__fill-background",
                "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > ul > li:nth-child(2) > div.ui-review-capability-rating__level__column.ui-review-capability-rating__level__progress-bar-container > div > span.ui-review-capability-rating__level__progress-bar__fill-background",
                "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > ul > li:nth-child(3) > div.ui-review-capability-rating__level__column.ui-review-capability-rating__level__progress-bar-container > div > span.ui-review-capability-rating__level__progress-bar__fill-background",
                "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > ul > li:nth-child(4) > div.ui-review-capability-rating__level__column.ui-review-capability-rating__level__progress-bar-container > div > span.ui-review-capability-rating__level__progress-bar__fill-background",
                "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > ul > li:nth-child(5) > div.ui-review-capability-rating__level__column.ui-review-capability-rating__level__progress-bar-container > div > span.ui-review-capability-rating__level__progress-bar__fill-background"
            ]
            
            # Mapear seletores para número de estrelas (5 estrelas, 4 estrelas, etc.)
            star_mapping = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1}
            
            # Extrair porcentagens das barras de progresso
            for idx, selector in enumerate(progress_bar_selectors):
                progress_bar = soup.select_one(selector)
                if progress_bar:
                    # Extrair a porcentagem da largura do estilo da barra
                    style = progress_bar.get('style', '')
                    width_match = re.search(r'width:\s*([\d,.]+)%', style)
                    
                    if width_match:
                        percentage = float(width_match.group(1).replace(',', '.'))
                        star_num = star_mapping[idx]  # Mapear índice para número de estrelas
                        star_percentages[star_num] = percentage
                        
                        # Calcular número de avaliações com essa estrela
                        if total_reviews > 0:
                            star_counts[star_num] = int(round(total_reviews * percentage / 100))
            
            # Se os seletores específicos não funcionaram, tentar um método mais genérico
            if all(p == 0 for p in star_percentages.values()):
                # Tentar encontrar as barras de progresso de maneira mais genérica
                rating_rows = soup.select('.ui-review-capability-rating__level')
                if not rating_rows:
                    rating_rows = soup.select('.ui-pdp-reviews__rating__distribution__row')
                
                if rating_rows:
                    for row in rating_rows:
                        # Identificar qual estrela essa linha representa
                        star_element = row.select_one('.ui-review-capability-rating__level_star-label') or \
                                      row.select_one('.ui-pdp-reviews__rating__distribution__star-number')
                        
                        if not star_element:
                            continue
                        
                        star_text = star_element.text.strip()
                        try:
                            star_number = int(star_text)
                        except ValueError:
                            continue
                        
                        # Encontrar a barra de progresso
                        progress_bar = row.select_one('.ui-review-capability-rating__level_progress-bar-fill') or \
                                      row.select_one('.ui-pdp-reviews__rating__distribution__progress-bar')
                        
                        if progress_bar:
                            # Extrair a porcentagem da largura do estilo da barra
                            style = progress_bar.get('style', '')
                            width_match = re.search(r'width:\s*([\d,.]+)%', style)
                            
                            if width_match:
                                percentage = float(width_match.group(1).replace(',', '.'))
                                star_percentages[star_number] = percentage
                                
                                # Calcular número de avaliações com essa estrela
                                if total_reviews > 0:
                                    star_counts[star_number] = int(round(total_reviews * percentage / 100))
            
            # Se ainda não conseguimos pelos métodos anteriores e temos média e total, fazer uma estimativa
            if all(p == 0 for p in star_percentages.values()) and avg_rating and total_reviews > 0:
                # Distribuição padrão baseada na média de avaliações
                if avg_rating >= 4.75:
                    star_percentages = {5: 85, 4: 10, 3: 3, 2: 1, 1: 1}
                elif avg_rating >= 4.5:
                    star_percentages = {5: 70, 4: 20, 3: 5, 2: 3, 1: 2}
                elif avg_rating >= 4.0:
                    star_percentages = {5: 50, 4: 30, 3: 10, 2: 5, 1: 5}
                elif avg_rating >= 3.5:
                    star_percentages = {5: 40, 4: 20, 3: 20, 2: 10, 1: 10}
                elif avg_rating >= 3.0:
                    star_percentages = {5: 30, 4: 20, 3: 20, 2: 15, 1: 15}
                elif avg_rating >= 2.5:
                    star_percentages = {5: 20, 4: 15, 3: 20, 2: 25, 1: 20}
                elif avg_rating >= 2.0:
                    star_percentages = {5: 10, 4: 15, 3: 20, 2: 30, 1: 25}
                else:
                    star_percentages = {5: 5, 4: 10, 3: 15, 2: 30, 1: 40}
                
                # Calcular os números aproximados com base nas porcentagens estimadas
                for star in range(1, 6):
                    star_counts[star] = int(round(total_reviews * star_percentages[star] / 100))
            
            # Ajuste para garantir que a soma de todas as avaliações seja igual ao total
            total_calculated = sum(star_counts.values())
            if total_calculated != total_reviews and total_reviews > 0:
                # Ajustar para a diferença
                diff = total_reviews - total_calculated
                # Distribuir a diferença começando das 5 estrelas (mais comum) até 1 estrela
                for star in range(5, 0, -1):
                    if diff == 0:
                        break
                    if diff > 0:
                        star_counts[star] += 1
                        diff -= 1
                    else:
                        if star_counts[star] > 0:
                            star_counts[star] -= 1
                            diff += 1
            
            # Calcular ratio 5/1 estrelas
            ratio_5_to_1 = 0
            if star_counts[1] > 0:
                ratio_5_to_1 = star_counts[5] / star_counts[1]
            elif star_counts[5] > 0:
                ratio_5_to_1 = float('inf')  # Infinito se há avaliações 5 estrelas mas nenhuma 1 estrela
            
            # Adicionar as informações ao produto
            product['preco'] = price or "Preço não encontrado"
            product['avaliacao_media'] = avg_rating or 0
            product['total_avaliacoes'] = total_reviews
            product['estrelas_5'] = star_counts[5]
            product['estrelas_4'] = star_counts[4]
            product['estrelas_3'] = star_counts[3]
            product['estrelas_2'] = star_counts[2]
            product['estrelas_1'] = star_counts[1]
            product['porcentagem_5_estrelas'] = star_percentages[5]
            product['porcentagem_4_estrelas'] = star_percentages[4]
            product['porcentagem_3_estrelas'] = star_percentages[3] 
            product['porcentagem_2_estrelas'] = star_percentages[2]
            product['porcentagem_1_estrela'] = star_percentages[1]
            product['ratio_5_to_1'] = ratio_5_to_1
            
            detailed_products.append(product)
            
            # Esperar um pouco entre requisições para evitar bloqueio
            time.sleep(1.5)
            
        except Exception as e:
            print(f"Erro ao processar detalhes do produto: {str(e)}")
            # Print stack trace para debug
            import traceback
            traceback.print_exc()
            # Adicionar o produto sem os detalhes adicionais
            detailed_products.append(product)
    
    print(f"Extração de detalhes concluída para {len(detailed_products)} produtos.")
    return detailed_products

if __name__ == "__main__":
    print("=== MERCADO LIVRE WEB SCRAPER ===")
    
    # Obter termo de busca
    search_term = input("Digite o termo de busca: ")
    if not search_term:
        print("Termo de busca é obrigatório. Saindo...")
        sys.exit(1)
    
    # Obter código do site
    print("\nSites disponíveis:")
    print("MLB - Brasil")
    print("MLA - Argentina")
    print("MLM - México")
    print("MCO - Colômbia")
    print("MLU - Uruguai")
    print("MLC - Chile")
    print("MPE - Peru")
    print("MLV - Venezuela")
    site_code = input("Código do site (padrão: MLB para Brasil): ").upper() or "MLB"
    
    # Obter número máximo de resultados
    try:
        max_results = int(input("Número máximo de resultados (padrão: 50): ") or "50")
    except ValueError:
        print("Valor inválido, usando padrão: 50")
        max_results = 50
    
    # Fazer scraping
    products = scrape_mercado_livre(search_term, site_code, max_results)
    
    # Perguntar se deseja extrair detalhes adicionais
    extract_details = input("\nDeseja extrair detalhes adicionais (preço, avaliações)? (s/n): ").lower() == 's'
    
    if extract_details and products:
        # Limitar o número de produtos para detalhes para evitar bloqueios
        max_details = min(len(products), 10)
        extract_products = input(f"\nQuantos produtos deseja detalhar (máx {len(products)}, recomendado 10)? ") or "10"
        try:
            max_details = min(len(products), int(extract_products))
        except ValueError:
            max_details = min(len(products), 10)
            
        # Extrair detalhes adicionais
        products = extract_product_details(products[:max_details], site_code)
    
    # Exportar resultados
    if products:
        export_to_csv(products, search_term, site_code)
    else:
        print("Nenhum produto encontrado para exportar.")
    
    print("\n=== WEB SCRAPING CONCLUÍDO ===") 