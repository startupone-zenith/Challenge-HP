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
import random

# Lista de User Agents para rotação
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36 Edg/94.0.992.47',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'
]

def get_random_user_agent():
    """Retorna um User-Agent aleatório da lista"""
    return random.choice(USER_AGENTS)

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
    max_attempts = 5  # Número máximo de tentativas para acessar uma página
    max_pages = 200   # Limite de segurança para número máximo de páginas a processar
    
    try:
        while total_collected < max_results and page <= max_pages:
            # Adicionar parâmetro de página se não for a primeira página
            current_url = base_url
            if page > 1:
                # Formato de URL para paginação no Mercado Livre
                current_url = f"{base_url}_Desde_{(page-1)*48+1}_NoIndex_True"
            
            print(f"Acessando página {page}: {current_url}")
            
            # Fazer a requisição HTTP com retry
            response = None
            for attempt in range(max_attempts):
                try:
                    response = requests.get(current_url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        break
                    print(f"Tentativa {attempt+1}/{max_attempts} - Status code: {response.status_code}")
                    time.sleep(2 * (attempt + 1))  # Espera progressivamente mais tempo
                except Exception as e:
                    print(f"Erro na tentativa {attempt+1}/{max_attempts}: {str(e)}")
                    time.sleep(2 * (attempt + 1))
            
            # Verificar se a requisição foi bem-sucedida
            if not response or response.status_code != 200:
                print(f"Falha ao acessar a página {page} após {max_attempts} tentativas. Encerrando.")
                break
            
            # Parsear o HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Encontrar os elementos de produto (tentando diferentes seletores)
            product_elements = []
            selectors = [
                '.ui-search-layout__item',
                '.ui-search-result',
                '.ui-search-result__wrapper',
                'li.shops__item',
                'div[class*="search-results-list"] > div'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    product_elements = elements
                    print(f"Encontrados {len(elements)} produtos usando seletor: {selector}")
                    break
            
            if not product_elements:
                print("Não foi possível encontrar produtos na página. Estrutura do site pode ter mudado.")
                # Tentativa de debug - salvar HTML da página
                debug_file = f"ml_data_exports/debug_page_{page}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"HTML da página salvo em {debug_file} para debug")
                
                # Se é a primeira página e não encontrou nada, encerra
                if page == 1:
                    break
                # Se não é a primeira página, pode ser o fim dos resultados
                else:
                    print("Fim dos resultados ou mudança na estrutura do site.")
                    break
            
            print(f"Encontrados {len(product_elements)} produtos na página {page}")
            
            # Extrair informações de cada produto
            products_on_page = 0
            for product in product_elements:
                if total_collected >= max_results:
                    break
                
                try:
                    # Tentar diferentes seletores para o título
                    title_element = product.select_one('.ui-search-item__title') or \
                                    product.select_one('h2') or \
                                    product.select_one('.shops__item-title')
                    title = title_element.text.strip() if title_element else "Título não encontrado"
                    
                    # Tentar diferentes seletores para o link
                    link_element = product.select_one('.ui-search-link') or \
                                   product.select_one('a[href*="/p/"]') or \
                                   product.select_one('a[href*="/MLB"]') or \
                                   product.select_one('a')
                    link = link_element['href'] if link_element else "#"
                    
                    # Tentar diferentes seletores para o preço
                    price_element = product.select_one('.price-tag-fraction') or \
                                    product.select_one('.ui-search-price__part--medium .price-tag-fraction') or \
                                    product.select_one('span[class*="price"]')
                    price = price_element.text.strip() if price_element else "Preço não encontrado"
                    
                    # Tentar obter o vendedor
                    seller_element = product.select_one('.ui-search-official-store-label') or \
                                     product.select_one('.ui-search-item__brand-discoverability') or \
                                     product.select_one('p[class*="seller"]')
                    seller = seller_element.text.strip() if seller_element else "Vendedor não especificado"
                    
                    # Tentar obter a condição do produto
                    condition_element = product.select_one('.ui-search-item__highlight-label__text') or \
                                        product.select_one('span[class*="condition"]')
                    condition = condition_element.text.strip() if condition_element else "Não especificado"
                    
                    # Adicionar à lista de produtos
                    products.append({
                        'title': title,
                        'link': link,
                        'price': price,
                        'seller': seller,
                        'condition': condition,
                        'site_code': site_code,
                        'pagina': page  # Adicionando número da página para rastreabilidade
                    })
                    
                    total_collected += 1
                    products_on_page += 1
                    
                except Exception as e:
                    print(f"Erro ao extrair informações do produto: {str(e)}")
            
            print(f"Extraídos {products_on_page} produtos da página {page}")
            print(f"Total coletado até agora: {total_collected}/{max_results}")
            
            # Verificar se há mais páginas
            next_page = soup.select_one('.andes-pagination__button--next a') or \
                        soup.select_one('li.andes-pagination__button--next') or \
                        soup.select_one('a[title*="Próxima"]') or \
                        soup.select_one('a[title*="Seguinte"]')
            
            if not next_page:
                print("Não há mais páginas para navegar.")
                break
            
            # Alternativa para verificar o fim dos resultados
            if products_on_page == 0:
                print("Nenhum produto encontrado nesta página. Fim dos resultados.")
                break
            
            # Avançar para a próxima página
            page += 1
            
            # Esperar um pouco entre as páginas para evitar bloqueio
            if page <= max_pages and total_collected < max_results:
                delay = 2 + random.random() * 2  # Entre 2 e 4 segundos
                print(f"Aguardando {delay:.1f}s antes de acessar a próxima página...")
                time.sleep(delay)
    
    except Exception as e:
        print(f"Erro durante o web scraping: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print(f"Coleta finalizada! Total de produtos: {len(products)}")
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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
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
            response = requests.get(product_link, headers=headers, timeout=30)
            
            # Verificar se a requisição foi bem-sucedida
            if response.status_code != 200:
                print(f"Erro ao acessar a página de detalhes. Status code: {response.status_code}")
                detailed_products.append(product)
                continue
            
            # Parsear o HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Opcional: Salvar HTML para debug
            debug_html_path = os.path.join("ml_data_exports", f"ml_debug_{i+1}.html")
            with open(debug_html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            # Inicializar ou copiar produto existente
            produto_detalhado = product.copy()
            
            # Extrair o título usando try/except para lidar com elementos ausentes
            try:
                title_selectors = [
                    "#header-octopus > div > div.ui-pdp-header__title-container > h1",
                    "h1.ui-pdp-title",
                    ".ui-pdp-title",
                    "h1[class*='title']",
                    "h1"
                ]
                
                for selector in title_selectors:
                    title_element = soup.select_one(selector)
                    if title_element and title_element.text.strip():
                        produto_detalhado['title'] = title_element.text.strip()
                        break
                else:
                    # Se chegou aqui, nenhum seletor funcionou
                    produto_detalhado['title'] = produto_detalhado.get('title', '') or 'Título não disponível'
            except Exception as e:
                print(f"Erro ao extrair título: {str(e)}")
                produto_detalhado['title'] = produto_detalhado.get('title', '') or 'Título não disponível'
            
            # Extrair o preço usando try/except
            try:
                price_selectors = [
                    "#price > div > div.ui-pdp-price__main-container > div.ui-pdp-price__second-line > span:nth-child(1) > span",
                    ".andes-money-amount__fraction",
                    ".price-tag-fraction",
                    ".ui-pdp-price__part .andes-money-amount__fraction",
                    "span[class*='price']"
                ]
                
                price = None
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element and price_element.text.strip():
                        price = price_element.text.strip()
                        # Remover separadores de milhares
                        price = price.replace('.', '')
                        break
                
                # Adicionar símbolo da moeda
                currency = ""
                currency_element = soup.select_one(".andes-money-amount__currency-symbol")
                if currency_element:
                    currency = currency_element.text.strip()
                    if currency == 'R$' and price and price.startswith('R$'):
                        price = price[2:].strip()
                
                if price:
                    produto_detalhado['preco'] = f"{currency} {price}".strip()
                else:
                    produto_detalhado['preco'] = produto_detalhado.get('preco', '') or "Preço não disponível"
            except Exception as e:
                print(f"Erro ao extrair preço: {str(e)}")
                produto_detalhado['preco'] = produto_detalhado.get('preco', '') or "Preço não disponível"
            
            # Extrair a condição do produto usando try/except
            try:
                condition_selectors = [
                    "#header-octopus > div > div.ui-pdp-header__subtitle > span",
                    ".ui-pdp-subtitle",
                    "span[class*='condition']",
                    ".ui-pdp-header__subtitle span"
                ]
                
                condition = None
                for selector in condition_selectors:
                    condition_element = soup.select_one(selector)
                    if condition_element and condition_element.text.strip():
                        condition = condition_element.text.strip()
                        break
                
                if condition:
                    produto_detalhado['condicao'] = condition
                else:
                    produto_detalhado['condicao'] = produto_detalhado.get('condicao', '') or "Condição não disponível"
            except Exception as e:
                print(f"Erro ao extrair condição: {str(e)}")
                produto_detalhado['condicao'] = produto_detalhado.get('condicao', '') or "Condição não disponível"
            
            # Extrair informações do vendedor usando try/except
            try:
                # Nome do vendedor
                seller_selectors = [
                    "#ui-pdp-main-container > div.ui-pdp-container__col.col-1.ui-pdp-container--column-right.mt-24.pr-24.ui-pdp--relative > div > div.ui-pdp-container__row.ui-pdp-component-list.pr-16.pl-16 > div > div.ui-pdp-seller.mb-20.mt-24.ui-pdp-seller__with-logo > div > div > div.ui-pdp-seller__header__info-container__title > div > button > span:nth-child(2)",
                    ".ui-pdp-seller__header__title",
                    ".ui-pdp-seller__header__info-container__title span",
                    ".ui-pdp-action-modal__link span",
                    "a[href*='seller'] span",
                    ".store-info .store-info__name",
                    "span[class*='seller']"
                ]
                
                seller_name = None
                for selector in seller_selectors:
                    seller_element = soup.select_one(selector)
                    if seller_element and seller_element.text.strip():
                        seller_name = seller_element.text.strip()
                        break
                
                if seller_name:
                    produto_detalhado['vendedor_nome'] = seller_name
                else:
                    produto_detalhado['vendedor_nome'] = produto_detalhado.get('vendedor_nome', '') or "Vendedor não identificado"
            except Exception as e:
                print(f"Erro ao extrair nome do vendedor: {str(e)}")
                produto_detalhado['vendedor_nome'] = produto_detalhado.get('vendedor_nome', '') or "Vendedor não identificado"
            
            # Extrair avaliação do vendedor usando try/except
            try:
                seller_rating_selectors = [
                    "#seller_data > div > div:nth-child(2) > div > div.ui-seller-data-status__info-container > div:nth-child(1)",
                    ".ui-seller-data-status__title",
                    ".ui-seller-info__status-info",
                    ".ui-pdp-seller__reputation-info",
                    ".ui-pdp-seller__status-label",
                    "p[class*='reputation']"
                ]
                
                seller_rating = None
                for selector in seller_rating_selectors:
                    seller_rating_element = soup.select_one(selector)
                    if seller_rating_element and seller_rating_element.text.strip():
                        seller_rating = seller_rating_element.text.strip()
                        # Remover espaços extras e quebras de linha
                        seller_rating = ' '.join(seller_rating.split())
                        break
                
                # Verificar se o texto da avaliação contém MercadoLíder
                if seller_rating and 'MercadoLíder' in seller_rating:
                    # Separar o texto para melhor formatação
                    if 'Platinum' in seller_rating:
                        seller_rating = 'MercadoLíder Platinum'
                    elif 'Gold' in seller_rating:
                        seller_rating = 'MercadoLíder Gold'
                    else:
                        seller_rating = 'MercadoLíder'
                
                if seller_rating:
                    produto_detalhado['vendedor_avaliacao'] = seller_rating
                else:
                    produto_detalhado['vendedor_avaliacao'] = produto_detalhado.get('vendedor_avaliacao', '') or "Avaliação não disponível"
            except Exception as e:
                print(f"Erro ao extrair avaliação do vendedor: {str(e)}")
                produto_detalhado['vendedor_avaliacao'] = produto_detalhado.get('vendedor_avaliacao', '') or "Avaliação não disponível"
            
            # Tentar extrair mais detalhes sobre o vendedor usando try/except
            try:
                seller_reputation_selectors = [
                    ".ui-pdp-seller__reputation-score",
                    ".seller-reputation-data",
                    "div[class*='reputation']",
                    ".reputation-data"
                ]
                
                for selector in seller_reputation_selectors:
                    seller_reputation_items = soup.select(selector)
                    if seller_reputation_items:
                        for item in seller_reputation_items:
                            try:
                                # Tentar diferentes seletores para título e valor
                                label_element = item.select_one('.ui-pdp-seller__reputation-title') or \
                                                item.select_one('span[class*="title"]') or \
                                                item.select_one('p[class*="title"]')
                                
                                value_element = item.select_one('.ui-pdp-seller__reputation-value') or \
                                                item.select_one('span[class*="value"]') or \
                                                item.select_one('p[class*="value"]')
                                
                                if label_element and value_element:
                                    label = label_element.text.strip().lower()
                                    value = value_element.text.strip()
                                    
                                    if 'vendas' in label or 'venda' in label:
                                        produto_detalhado['vendedor_vendas_concluidas'] = value
                                    elif 'atendimento' in label:
                                        produto_detalhado['vendedor_qualidade_atendimento'] = value
                                    elif 'prazo' in label or 'entrega' in label:
                                        produto_detalhado['vendedor_entrega_nos_prazos'] = value
                            except Exception as e:
                                print(f"Erro ao extrair métrica de reputação: {str(e)}")
                                continue
            except Exception as e:
                print(f"Erro ao extrair métricas de reputação do vendedor: {str(e)}")
            
            # Extrair ID do vendedor usando try/except
            try:
                # Primeira tentativa: buscar na URL
                seller_id_match = re.search(r'seller_id=(\d+)', response.url)
                if seller_id_match:
                    produto_detalhado['vendedor_id'] = seller_id_match.group(1)
                else:
                    # Segunda tentativa: buscar nos scripts da página
                    scripts = soup.find_all('script', type='text/javascript')
                    for script in scripts:
                        if script.string and 'seller_id' in script.string:
                            match = re.search(r'seller_id["\']?\s*:\s*["\']?(\d+)', script.string)
                            if match:
                                produto_detalhado['vendedor_id'] = match.group(1)
                                break
                    
                    # Terceira tentativa: buscar no HTML geral
                    if 'vendedor_id' not in produto_detalhado:
                        html_text = str(soup)
                        seller_id_match = re.search(r'seller[_-]id["\'=]\s*["\':]?\s*["\'=]?([\w\d]+)["\']', html_text)
                        if seller_id_match:
                            produto_detalhado['vendedor_id'] = seller_id_match.group(1)
            except Exception as e:
                print(f"Erro ao extrair ID do vendedor: {str(e)}")
            
            # 1. Extrair total de avaliações usando try/except
            try:
                total_reviews = 0
                total_reviews_selectors = [
                    "#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div.ui-review-capability__rating > div.ui-review-capability__rating__start-content > div:nth-child(2) > p",
                    '.ui-pdp-reviews__amount',
                    '.ui-pdp-review__amount',
                    'span[class*="review-count"]',
                    'p[class*="reviews"]',
                    'p.ui-pdp-reviews__header__subtitle',
                    '.ui-review-view-header__rating__count'
                ]
                
                for selector in total_reviews_selectors:
                    total_reviews_element = soup.select_one(selector)
                    if total_reviews_element:
                        # Extrair número do texto (ex: "65 avaliações" -> 65)
                        review_count_match = re.search(r'(\d+)', total_reviews_element.text)
                        if review_count_match:
                            total_reviews = int(review_count_match.group(1))
                            produto_detalhado['total_avaliacoes'] = total_reviews
                            break
                
                # Se não encontrou nos seletores específicos, buscar com seletores mais genéricos
                if not total_reviews:
                    # Buscar elementos que contenham textos como "X avaliações" ou "X opiniões"
                    for element in soup.find_all(['span', 'p', 'div']):
                        if element.text:
                            match = re.search(r'(\d+)\s+(?:avaliações|opiniões|reviews)', element.text.lower())
                            if match:
                                total_reviews = int(match.group(1))
                                produto_detalhado['total_avaliacoes'] = total_reviews
                                break
                
                # Se ainda não encontrou, tentar scripts JSON
                if not total_reviews:
                    script_tags = soup.find_all('script', {'type': ['application/ld+json', 'application/json']})
                    for script in script_tags:
                        try:
                            if script.string:
                                json_data = json.loads(script.string)
                                if isinstance(json_data, dict):
                                    # Verificar diferentes caminhos possíveis no JSON
                                    if 'aggregateRating' in json_data:
                                        total_reviews = int(json_data['aggregateRating'].get('reviewCount', 0))
                                    elif 'review' in json_data and 'reviewCount' in json_data:
                                        total_reviews = int(json_data['reviewCount'])
                                    
                                    if total_reviews > 0:
                                        produto_detalhado['total_avaliacoes'] = total_reviews
                                        break
                        except (json.JSONDecodeError, AttributeError, ValueError, TypeError):
                            continue
                
                # Se ainda não encontrou e tem elementos de vendas, fazer uma estimativa
                if not total_reviews and 'vendedor_vendas_concluidas' in produto_detalhado:
                    vendas_texto = produto_detalhado['vendedor_vendas_concluidas']
                    # Extrair números e identificar multiplicadores (mil, milhão)
                    vendas_match = re.search(r'(\d+)(?:\s*|\+)?(?:mil|k|m)', vendas_texto.lower())
                    if vendas_match:
                        vendas_base = int(vendas_match.group(1))
                        multiplicador = 1
                        if 'mil' in vendas_texto.lower() or 'k' in vendas_texto.lower():
                            multiplicador = 1000
                        elif 'm' in vendas_texto.lower():
                            multiplicador = 1000000
                        
                        # Estimar o total de avaliações como 1-5% das vendas
                        estimated_reviews = int(vendas_base * multiplicador * 0.03)  # 3% das vendas
                        total_reviews = estimated_reviews
                        produto_detalhado['total_avaliacoes'] = total_reviews
                        produto_detalhado['avaliacao_estimada'] = True
            except Exception as e:
                print(f"Erro ao extrair total de avaliações: {str(e)}")
                total_reviews = produto_detalhado.get('total_avaliacoes', 0)
            
            # 2. Extrair média de avaliações usando try/except
            try:
                avg_rating = 0
                rating_selectors = [
                    '.ui-pdp-reviews__rating__summary__average',
                    '.ui-pdp-review__rating-average',
                    'span[class*="rating-average"]',
                    '.review-summary-average',
                    'p[class*="reviews"]',
                    'p.ui-pdp-review__rating__summary__average',
                    'div.ui-pdp-reviews__rating div span',
                    '.ui-review-capability__rating__average'
                ]
                
                for selector in rating_selectors:
                    rating_element = soup.select_one(selector)
                    if rating_element and rating_element.text:
                        try:
                            # Extrair qualquer número da string
                            rating_match = re.search(r'(\d+[,.]?\d*)', rating_element.text)
                            if rating_match:
                                avg_rating = float(rating_match.group(1).replace(',', '.'))
                                break
                        except ValueError:
                            continue
                
                # Segunda tentativa: buscar em outros elementos
                if avg_rating == 0:
                    # Procurar textos que contenham "X de 5" ou "X/5" estrelas
                    for element in soup.find_all(['span', 'p', 'div']):
                        if element.text:
                            match = re.search(r'(\d+[,.]?\d*)\s*(?:de|\/)\s*5', element.text)
                            if match:
                                avg_rating = float(match.group(1).replace(',', '.'))
                                break
                
                # Terceira tentativa: verificar scripts JSON-LD
                if avg_rating == 0:
                    script_tags = soup.find_all('script', {'type': ['application/ld+json', 'application/json']})
                    for script in script_tags:
                        try:
                            if script.string:
                                data = json.loads(script.string)
                                if isinstance(data, dict):
                                    if 'aggregateRating' in data:
                                        avg_rating = float(data['aggregateRating'].get('ratingValue', 0))
                                    elif 'review' in data and 'reviewRating' in data['review']:
                                        avg_rating = float(data['review']['reviewRating'].get('ratingValue', 0))
                                    
                                    if avg_rating > 0:
                                        break
                        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                            continue
                
                # Quarta tentativa: se tem total de avaliações e não conseguiu a média, estimar com base nas vendas
                if avg_rating == 0 and total_reviews > 0:
                    # Maioria dos produtos no Mercado Livre tem boa avaliação, então uma estimativa razoável
                    avg_rating = 4.5  # Estimativa padrão se não conseguiu extrair
                    produto_detalhado['avaliacao_estimada'] = True
                
                # Atualizar no produto
                if avg_rating > 0:
                    produto_detalhado['avaliacao_media'] = avg_rating
                else:
                    produto_detalhado['avaliacao_media'] = 0
            except Exception as e:
                print(f"Erro ao extrair média de avaliações: {str(e)}")
                produto_detalhado['avaliacao_media'] = 0
            
            # 3. Extrair distribuição de avaliações usando try/except
            try:
                # Inicializar contadores e porcentagens por estrela
                star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
                star_percentages = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
                
                # Usar os seletores específicos para as barras de progresso
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
                progress_bars_found = False
                for idx, selector in enumerate(progress_bar_selectors):
                    progress_bar = soup.select_one(selector)
                    if progress_bar:
                        progress_bars_found = True
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
                
                # Se os seletores específicos não funcionaram, tentar método mais genérico
                if not progress_bars_found and total_reviews > 0:
                    rating_rows_selectors = [
                        '.ui-review-capability-rating__level',
                        '.ui-pdp-reviews__rating__distribution__row',
                        'li[class*="rating-level"]',
                        '.review-level'
                    ]
                    
                    for rows_selector in rating_rows_selectors:
                        rating_rows = soup.select(rows_selector)
                        if rating_rows:
                            for row in rating_rows:
                                # Identificar qual estrela essa linha representa
                                star_element = (
                                    row.select_one('.ui-review-capability-rating__level_star-label') or
                                    row.select_one('.ui-pdp-reviews__rating__distribution__star-number') or
                                    row.select_one('span[class*="star"]')
                                )
                                
                                if not star_element:
                                    continue
                                
                                star_text = star_element.text.strip()
                                try:
                                    star_number = int(re.search(r'(\d+)', star_text).group(1))
                                except (ValueError, AttributeError):
                                    continue
                                
                                # Encontrar a barra de progresso
                                progress_bar = (
                                    row.select_one('.ui-review-capability-rating__level_progress-bar-fill') or
                                    row.select_one('.ui-pdp-reviews__rating__distribution__progress-bar') or
                                    row.select_one('span[class*="fill"]') or
                                    row.select_one('div[class*="fill"]')
                                )
                                
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
                            
                            # Se encontrou informações nesse seletor, encerra o loop
                            if any(p > 0 for p in star_percentages.values()):
                                break
                
                # Se não encontrou as distribuições e temos total_reviews e avaliação média, estimar
                if not any(p > 0 for p in star_percentages.values()) and total_reviews > 0 and produto_detalhado['avaliacao_media'] > 0:
                    avg = produto_detalhado['avaliacao_media']
                    # Distribuição estimada com base na média
                    if avg >= 4.7:
                        star_percentages = {5: 85, 4: 10, 3: 3, 2: 1, 1: 1}
                    elif avg >= 4.5:
                        star_percentages = {5: 70, 4: 20, 3: 5, 2: 3, 1: 2}
                    elif avg >= 4.0:
                        star_percentages = {5: 50, 4: 30, 3: 10, 2: 5, 1: 5}
                    elif avg >= 3.5:
                        star_percentages = {5: 40, 4: 20, 3: 20, 2: 10, 1: 10}
                    elif avg >= 3.0:
                        star_percentages = {5: 30, 4: 20, 3: 20, 2: 15, 1: 15}
                    elif avg >= 2.5:
                        star_percentages = {5: 20, 4: 15, 3: 20, 2: 25, 1: 20}
                    elif avg >= 2.0:
                        star_percentages = {5: 10, 4: 15, 3: 20, 2: 30, 1: 25}
                    else:
                        star_percentages = {5: 5, 4: 10, 3: 15, 2: 30, 1: 40}
                    
                    # Calcular contagens com base nas porcentagens estimadas
                    for star in range(1, 6):
                        star_counts[star] = int(round(total_reviews * star_percentages[star] / 100))
                    
                    produto_detalhado['distribuicao_estimada'] = True
                
                # Ajustar as contagens para garantir que a soma seja igual ao total de avaliações
                if total_reviews > 0:
                    total_calculated = sum(star_counts.values())
                    if total_calculated != total_reviews:
                        # Distribuir a diferença
                        diff = total_reviews - total_calculated
                        for star in sorted(range(1, 6), key=lambda s: star_counts[s], reverse=(diff > 0)):
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
                produto_detalhado['estrelas_5'] = star_counts[5]
                produto_detalhado['estrelas_4'] = star_counts[4]
                produto_detalhado['estrelas_3'] = star_counts[3]
                produto_detalhado['estrelas_2'] = star_counts[2]
                produto_detalhado['estrelas_1'] = star_counts[1]
                produto_detalhado['porcentagem_5_estrelas'] = star_percentages[5]
                produto_detalhado['porcentagem_4_estrelas'] = star_percentages[4]
                produto_detalhado['porcentagem_3_estrelas'] = star_percentages[3] 
                produto_detalhado['porcentagem_2_estrelas'] = star_percentages[2]
                produto_detalhado['porcentagem_1_estrela'] = star_percentages[1]
                produto_detalhado['ratio_5_to_1'] = ratio_5_to_1
            except Exception as e:
                print(f"Erro ao extrair distribuição de avaliações: {str(e)}")
                # Garantir que pelo menos as chaves existam
                for star in range(1, 6):
                    produto_detalhado[f'estrelas_{star}'] = 0
                    produto_detalhado[f'porcentagem_{star}_estrela{"s" if star > 1 else ""}'] = 0
                produto_detalhado['ratio_5_to_1'] = 0
            
            # Adicionar produto à lista
            detailed_products.append(produto_detalhado)
            
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

def scrape_mercado_livre_lotes(search_term, site_code="MLB", max_results=1000, lote_size=50, delay_entre_lotes=30):
    """
    Versão otimizada para extrair grandes volumes (1000+) de produtos do Mercado Livre em lotes
    
    Args:
        search_term (str): Termo de busca
        site_code (str): Código do país (MLB para Brasil, MLA para Argentina, etc.)
        max_results (int): Número máximo de resultados desejados
        lote_size (int): Tamanho de cada lote para processamento
        delay_entre_lotes (int): Tempo de espera entre lotes em segundos
        
    Returns:
        list: Lista de dicionários com dados dos produtos
    """
    print(f"Iniciando extração em lotes para: {search_term}")
    print(f"Meta: {max_results} produtos, em lotes de {lote_size}")
    
    # Formatar o termo de busca para URL
    search_url_term = search_term.replace(" ", "-")
    
    # URL base para busca
    base_url = f"https://lista.mercadolivre.com.br/{search_url_term}"
    if site_code != "MLB":
        # Ajustar URL para outros países
        domain = site_code.replace("ML", "").lower()
        base_url = f"https://listado.mercadolibre.com.{domain}/{search_url_term}"
    
    # Configurações para lidar com bloqueios
    max_attempts_por_pagina = 5
    max_pages = (max_results // 48) + 5  # 48 é o número padrão de produtos por página no ML
    
    # Contador de bloqueios para adaptação dinâmica
    bloqueios_consecutivos = 0
    max_bloqueios_permitidos = 5
    
    # Lista para armazenar todos os produtos
    all_products = []
    
    # Diretório para salvar resultados parciais
    export_dir = "ml_data_exports"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    # Extração por lotes de páginas
    lote_atual = 1
    pagina_inicial = 1
    
    while len(all_products) < max_results and bloqueios_consecutivos < max_bloqueios_permitidos:
        print(f"\n--- Processando lote {lote_atual} ---")
        
        products_lote = []
        pagina_atual = pagina_inicial
        paginas_processadas = 0
        max_paginas_por_lote = 10  # Limitar número de páginas por lote
        
        # Processar páginas até completar o lote ou chegar ao máximo de páginas
        while (len(products_lote) < lote_size and 
               pagina_atual <= max_pages and 
               paginas_processadas < max_paginas_por_lote):
            
            # Criar URL da página atual
            if pagina_atual == 1:
                current_url = base_url
            else:
                current_url = f"{base_url}_Desde_{(pagina_atual-1)*48+1}_NoIndex_True"
            
            print(f"Acessando página {pagina_atual}: {current_url}")
            
            # Rotacionar User-Agent para cada requisição
            headers = {
                'User-Agent': get_random_user_agent(),
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Fazer a requisição com retry
            response = None
            for attempt in range(max_attempts_por_pagina):
                try:
                    # Adicionar delay adaptativo com jitter
                    if attempt > 0:
                        delay = 3 * (attempt + 1) + random.random() * 2
                        print(f"Tentativa {attempt+1}/{max_attempts_por_pagina} - Aguardando {delay:.1f}s...")
                        time.sleep(delay)
                    
                    response = requests.get(current_url, headers=headers, timeout=30)
                    
                    # Verificar se foi bloqueado (captcha ou erro 429)
                    if response.status_code == 429 or "captcha" in response.text.lower():
                        print(f"Detectado bloqueio temporário na tentativa {attempt+1}")
                        bloqueios_consecutivos += 1
                        continue
                    
                    if response.status_code == 200:
                        # Reset do contador de bloqueios consecutivos
                        bloqueios_consecutivos = 0
                        break
                        
                    print(f"Tentativa {attempt+1}/{max_attempts_por_pagina} - Status: {response.status_code}")
                    
                except Exception as e:
                    print(f"Erro na requisição (tentativa {attempt+1}): {str(e)}")
            
            # Verificar se conseguiu acessar a página
            if not response or response.status_code != 200:
                print(f"Falha ao acessar a página {pagina_atual} após várias tentativas.")
                
                # Se tiver muitos bloqueios consecutivos, interrompe
                if bloqueios_consecutivos >= max_bloqueios_permitidos:
                    print("Muitos bloqueios consecutivos. Interrompendo a extração.")
                    break
                
                # Salvar HTML para debug se tiver resposta
                if response:
                    debug_file = os.path.join(export_dir, f"debug_bloqueio_pagina{pagina_atual}.html")
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    print(f"HTML do bloqueio salvo em {debug_file}")
                
                pagina_atual += 1
                paginas_processadas += 1
                continue
            
            # Parsear o HTML com lxml parser (mais rápido)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Encontrar os elementos de produto com diferentes seletores
            product_elements = []
            selectors = [
                '.ui-search-layout__item',
                '.ui-search-result',
                '.ui-search-result__wrapper',
                'li.shops__item',
                'div[class*="search-results-list"] > div'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    product_elements = elements
                    print(f"Página {pagina_atual}: {len(elements)} produtos encontrados com seletor: {selector}")
                    break
            
            # Se não encontrou produtos, verifica se chegou ao fim ou se mudou a estrutura
            if not product_elements:
                print(f"Nenhum produto encontrado na página {pagina_atual}.")
                
                # Verifica mensagens de "não encontrado"
                empty_selectors = [
                    '.ui-search-rescue__title',
                    '.ui-search-rescue__message',
                    '.ui-search-no-result__title'
                ]
                
                for selector in empty_selectors:
                    empty_message = soup.select_one(selector)
                    if empty_message and empty_message.text.strip():
                        print(f"Mensagem encontrada: {empty_message.text.strip()}")
                        print("Fim dos resultados disponíveis.")
                        pagina_atual = max_pages + 1  # Forçar saída do loop
                        break
                
                # Se não é a última página, salva para debug
                debug_file = os.path.join(export_dir, f"debug_pagina{pagina_atual}.html")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"HTML da página sem produtos salvo em {debug_file}")
                
                # Avança para a próxima página
                pagina_atual += 1
                paginas_processadas += 1
                continue
            
            # Extrair dados dos produtos
            page_products = []
            for product in product_elements:
                try:
                    # Extrair título
                    title_element = (
                        product.select_one('.ui-search-item__title') or
                        product.select_one('h2') or
                        product.select_one('.shops__item-title')
                    )
                    title = title_element.text.strip() if title_element else "Título não encontrado"
                    
                    # Extrair link
                    link_element = (
                        product.select_one('.ui-search-link') or
                        product.select_one('a[href*="/p/"]') or
                        product.select_one('a[href*="/MLB"]') or
                        product.select_one('a')
                    )
                    link = link_element['href'] if link_element else "#"
                    
                    # Extrair preço
                    price_element = (
                        product.select_one('.price-tag-fraction') or
                        product.select_one('.ui-search-price__part--medium .price-tag-fraction') or
                        product.select_one('span[class*="price"]')
                    )
                    price = price_element.text.strip() if price_element else "Preço não encontrado"
                    
                    # Extrair vendedor
                    seller_element = (
                        product.select_one('.ui-search-official-store-label') or
                        product.select_one('.ui-search-item__brand-discoverability') or
                        product.select_one('p[class*="seller"]')
                    )
                    seller = seller_element.text.strip() if seller_element else "Vendedor não especificado"
                    
                    # Extrair condição
                    condition_element = (
                        product.select_one('.ui-search-item__highlight-label__text') or
                        product.select_one('span[class*="condition"]')
                    )
                    condition = condition_element.text.strip() if condition_element else "Não especificado"
                    
                    # Adicionar produto ao lote
                    page_products.append({
                        'title': title,
                        'link': link,
                        'price': price,
                        'seller': seller,
                        'condition': condition,
                        'site_code': site_code,
                        'pagina': pagina_atual,
                        'lote': lote_atual
                    })
                except Exception as e:
                    print(f"Erro ao extrair dados do produto: {str(e)}")
            
            print(f"Extraídos {len(page_products)} produtos da página {pagina_atual}")
            
            # Adicionar os produtos da página ao lote
            products_lote.extend(page_products)
            
            # Verificar se há mais páginas
            next_page = (
                soup.select_one('.andes-pagination__button--next a') or
                soup.select_one('li.andes-pagination__button--next') or
                soup.select_one('a[title*="Próxima"]') or
                soup.select_one('a[title*="Seguinte"]')
            )
            
            if not next_page or not page_products:
                print("Não há mais páginas disponíveis.")
                pagina_atual = max_pages + 1  # Forçar saída do loop
            else:
                # Avançar para a próxima página
                pagina_atual += 1
                paginas_processadas += 1
                
                # Delay adaptativo entre páginas para evitar bloqueio
                delay = 2 + random.random() * 3  # Entre 2 e 5 segundos
                print(f"Aguardando {delay:.1f}s antes da próxima página...")
                time.sleep(delay)
        
        # Processar e salvar o lote atual
        print(f"\nLote {lote_atual} concluído: {len(products_lote)} produtos")
        all_products.extend(products_lote)
        
        # Salvar o lote como CSV parcial
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lote_file = os.path.join(export_dir, f"ml_lote{lote_atual}_{timestamp}.csv")
        
        df_lote = pd.DataFrame(products_lote)
        df_lote.to_csv(lote_file, index=False, encoding='utf-8-sig')
        print(f"Lote {lote_atual} salvo em: {lote_file}")
        
        # Atualizar contadores para o próximo lote
        lote_atual += 1
        pagina_inicial = pagina_atual
        
        # Verificar progresso geral
        print(f"\nProgresso geral: {len(all_products)}/{max_results} produtos")
        
        if len(all_products) >= max_results:
            print("Atingido número máximo de resultados solicitados.")
            break
        
        # Se já processou produtos mas ainda não atingiu o máximo, perguntar se quer continuar
        if products_lote and len(all_products) < max_results:
            print(f"Aguardando {delay_entre_lotes}s antes do próximo lote...")
            time.sleep(delay_entre_lotes)
    
    # Limitar ao número máximo solicitado
    all_products = all_products[:max_results]
    
    print(f"\n=== Extração concluída: {len(all_products)} produtos ===")
    return all_products

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