import scrapy
import random
import logging
import time
import json
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import quote_plus, quote, urlencode
import re
import threading
import multiprocessing
import sys
from twisted.internet import asyncioreactor
import asyncio  # for setting Windows selector event loop policy

# Importar configurações padronizadas
from ..core.shared_scraping_config import (
    USER_AGENTS_2025,
    STANDARD_BROWSER_HEADERS,
    MERCADOLIVRE_SELECTORS,
    ANTI_BOT_DELAYS,
    get_random_user_agent,
    get_browser_specific_headers,
    get_scrapy_settings,
    calculate_adaptive_delay,
    setup_standard_logging
)

# Manter compatibilidade com código existente
USER_AGENTS = USER_AGENTS_2025  # Alias para compatibilidade
BROWSER_HEADERS = STANDARD_BROWSER_HEADERS  # Alias para compatibilidade

# Lista de proxies públicos para rotação (opcional - usar com cuidado)
# Deixando vazio por enquanto - pode ser preenchido com proxies válidos se necessário
ROTATING_PROXIES = [
    # Exemplo: 'http://proxy1:port',
    # Adicione proxies válidos aqui se necessário
]

class MercadoLivreSpider(scrapy.Spider):
    name = 'mercadolivre'
    STEP = 50
    
    def get_random_headers(self):
        """Gera headers aleatórios usando configuração padronizada"""
        ua = get_random_user_agent()
        headers = get_browser_specific_headers(ua)
        
        # Adicionar viewport aleatório
        viewports = ['1920,1080', '1366,768', '1536,864', '1440,900', '1280,720']
        headers['Viewport-Width'] = random.choice(viewports).split(',')[0]
        
        # Simular referrer ocasional
        if random.random() < 0.4:  # 40% chance de ter referrer
            referrers = [
                'https://www.google.com.br/',
                'https://www.google.com/',
                'https://www.bing.com/',
                'https://duckduckgo.com/'
            ]
            headers['Referer'] = random.choice(referrers)
        
        # Gerenciar sessão usando configuração padronizada
        if not hasattr(self, '_session_start'):
            self._session_start = time.time()
        
        # Usar configuração padronizada para renovação de sessão
        session_duration = time.time() - self._session_start
        if session_duration > ANTI_BOT_DELAYS['session_renewal']:
            self._session_start = time.time()
            logging.info("Renovando sessão para simular comportamento humano")
        
        return headers 
    
    def __init__(self, query=None, results_list=None, extract_images=True, 
                 sort_by='relevance', condition='all', max_items=None, custom_url=None, *args, **kwargs):
        super(MercadoLivreSpider, self).__init__(*args, **kwargs)
        self.query = query
        self.results_list = results_list
        self.extract_images = extract_images
        self.sort_by = sort_by
        self.condition = condition
        self.max_items = int(max_items) if max_items else 0  # 0 unlimited  # Default to 50 if not specified
        self.custom_url = custom_url  # URL customizada para usar como base
        self.used_urls = [] # Track URLs that were actually used
        self.html_saved_for_debug = False # Flag to save HTML only once
        self.items_collected = 0  # Counter for collected items

        if not query and not custom_url:
            raise ValueError("A search query or custom URL must be provided to the MercadoLivreSpider.")

        # --- Use custom URL if provided, otherwise construct URL from query ---
        if custom_url:
            # Use the custom URL directly
            self.start_urls = [custom_url]
            logging.info(f"Usando URL customizada: {custom_url}")
        else:
            # --- Construct the primary URL based on query and filters ---
            base_url = "https://lista.mercadolivre.com.br/"
            
            # Path slug from query (e.g., "cartucho-hp")
            path_slug = query.replace(' ', '-').lower() 
            
            # Initialize parts for the final URL
            url_path_segments = [path_slug]
            url_query_params = {}
            # Fragment parts: D[A:query_encoded, O:order_encoded, etc.]
            # Always include the query in the fragment, percent-encoded
            url_fragment_dict = {'A': quote(query)} 

            # Apply sorting options
            if self.sort_by == 'relevance':
                # For relevance, Mercado Livre often uses ?sb=all_mercadolibre or specific fragment orders
                # Based on user's provided URL, ?sb=all_mercadolibre is a good bet.
                url_query_params['sb'] = 'all_mercadolibre'
                # Sometimes relevance implies a sort order in fragment like 'O:BEST_SELLERS' or no 'O' param.
                # We'll rely on 'sb' for now and see if ML adds an 'O' by default.
            elif self.sort_by == 'price_asc':
                url_path_segments.append("_OrderId_PRICE") # Path segment for price ordering
                url_fragment_dict['O'] = 'PRICE_ASC'    # Fragment for ascending price
            elif self.sort_by == 'price_desc':
                url_path_segments.append("_OrderId_PRICE") # Path segment for price ordering
                url_fragment_dict['O'] = 'PRICE_DESC'   # Fragment for descending price

            # Apply condition filter
            condition_map = {
                'new': '2230284',
                'used': '2230581',
                # 'refurbished': '2230582' # Can be added if needed
            }
            if self.condition and self.condition != 'all' and self.condition in condition_map:
                # Conditions are typically path segments like _ITEM*CONDITION_2230284
                url_path_segments.append(f"_ITEM*CONDITION_{condition_map[self.condition]}")

            # Join path segments (e.g., cartucho-hp_OrderId_PRICE_ITEM*CONDITION_2230284)
            # The first segment (path_slug) is directly part of the path, subsequent ones are joined by '_'
            final_path = url_path_segments[0]
            if len(url_path_segments) > 1:
                final_path += "".join([segment for segment in url_path_segments[1:]]) # Segments already contain '_' prefix

            # Construct fragment string: D[K:V,K:V]
            fragment_string = "D[" + ",".join([f"{k}:{v}" for k, v in url_fragment_dict.items()]) + "]"
            
            # Assemble the final URL
            self.start_urls = [base_url + final_path]
            if url_query_params:
                self.start_urls[0] += "?" + urlencode(url_query_params)
            self.start_urls[0] += "#" + fragment_string
            
            logging.info(f"Spider initialized for query='{self.query}', sort_by='{self.sort_by}', condition='{self.condition}', max_items={self.max_items}. Start URL: {self.start_urls[0]}")
        
        # --- End of URL construction ---

    def start_requests(self):
        if not self.query and not self.custom_url:
            logging.error("Spider started without a query or custom URL.")
            return
        
        # We now have a single start_urls[0] constructed in __init__
        if self.start_urls:
            url_to_try = self.start_urls[0]
            logging.info(f"Attempting to scrape URL: {url_to_try}")
            
            # Atraso inicial aleatório para simular comportamento humano
            initial_delay = random.uniform(3.0, 8.0)
            logging.info(f"Aguardando {initial_delay:.1f}s antes da primeira requisição...")
            
            # Implementar delay inteligente baseado no histórico
            if not hasattr(self, '_request_times'):
                self._request_times = []
            
            current_time = time.time()
            self._request_times.append(current_time)
            
            # Manter apenas as últimas 10 requisições
            if len(self._request_times) > 10:
                self._request_times.pop(0)
            
            # Se fizemos muitas requisições recentemente, aumentar delay
            if len(self._request_times) >= 3:
                recent_requests = [t for t in self._request_times if current_time - t < 60]  # últimos 60s
                if len(recent_requests) >= 3:
                    extra_delay = random.uniform(10.0, 20.0)
                    initial_delay += extra_delay
                    logging.info(f"Muitas requisições recentes, aguardando extra {extra_delay:.1f}s...")
            
            time.sleep(initial_delay)
            
            yield scrapy.Request(
                url=url_to_try,
                callback=self.parse,
                errback=self.handle_error,
                headers=self.get_random_headers(),  # Headers mais sofisticados
                meta={
                    'page_number': 1,
                    'download_delay': initial_delay,
                    'dont_cache': True,  # Evitar cache
                    'handle_httpstatus_list': [302, 403, 429, 503]  # Lidar com redirects e bloqueios
                }
            )
        else:
            logging.error(f"No start URL generated for query: {self.query}")

    def extract_detailed_product_info(self, response):
        """
        Extrai informações detalhadas do produto usando dados estruturados (JSON-LD) e HTML
        Baseado na análise da página real do MercadoLivre
        """
        try:
            # Dicionário para armazenar informações detalhadas do produto
            detailed_info = {
                'url': response.url,
                'timestamp': datetime.now().isoformat(),
            }
            
            # Extrair product_id da URL (usando regex para capturar apenas o ID)
            import re
            match_id = re.search(r'/(?:p|up)/(MLB[A-Z0-9]+)', response.url)
            if match_id:
                product_id = match_id.group(1)
                detailed_info['product_id'] = product_id
                detailed_info['ID_PRODUTO'] = product_id  # Para compatibilidade
                logging.info(f"Product ID extraído da URL: {product_id}")
            else:
                # Fallback: tentar capturar qualquer ID após /p/ ou /up/
                fallback_match = re.search(r'/(?:p|up)/([A-Z0-9]+)', response.url)
                if fallback_match:
                    product_id = fallback_match.group(1)
                    detailed_info['product_id'] = product_id
                    detailed_info['ID_PRODUTO'] = product_id
                    logging.info(f"Product ID extraído da URL (fallback): {product_id}")
                else:
                    logging.warning(f"Não foi possível extrair product_id da URL: {response.url}")

            # 1. EXTRAIR DADOS ESTRUTURADOS (JSON-LD e JavaScript)
            json_ld_scripts = response.css('script[type="application/ld+json"]::text').getall()
            structured_data = {}
            event_data = {}
            
            # Processar JSON-LD
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.strip())
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        structured_data = data
                        logging.info(f"Dados estruturados JSON-LD encontrados: {data.get('name', 'N/A')}")
                        break
                except json.JSONDecodeError:
                    continue
            
            # Extrair dados do event_data no JavaScript (linha 2727 da página analisada)
            # Padrão melhorado para capturar JSON completo incluindo reviews
            event_data_pattern = r'melidata\("add",\s*"event_data",\s*(\{.*?\})\s*\)'
            event_match = re.search(event_data_pattern, response.text, re.DOTALL)
            if event_match:
                try:
                    # Extrair a parte JSON do match
                    json_str = event_match.group(1)
                    # Balancear chaves se necessário
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    if open_braces > close_braces:
                        json_str += '}' * (open_braces - close_braces)
                    elif close_braces > open_braces:
                        # Se há mais fechamento, truncar no último válido
                        brace_level = 0
                        valid_end = 0
                        for i, char in enumerate(json_str):
                            if char == '{':
                                brace_level += 1
                            elif char == '}':
                                brace_level -= 1
                                if brace_level == 0:
                                    valid_end = i + 1
                                    break
                        if valid_end > 0:
                            json_str = json_str[:valid_end]
                    
                    event_data = json.loads(json_str)
                    logging.info(f"Event data encontrados: seller={event_data.get('seller_name', 'N/A')}, reviews={event_data.get('reviews', {})}")
                except (json.JSONDecodeError, AttributeError) as e:
                    logging.warning(f"Erro ao processar event_data: {e}")
                    # Tentar padrão mais simples se o primeiro falhar
                    simple_pattern = r'melidata\("add",\s*"event_data",\s*\{[^{}]*"reviews":\{[^{}]*\}[^}]*\}'
                    simple_match = re.search(simple_pattern, response.text, re.DOTALL)
                    if simple_match:
                        try:
                            json_str = simple_match.group(0).split('{', 1)[1].rsplit('}', 1)[0] + '}'
                            event_data = json.loads('{' + json_str)
                            logging.info(f"Event data extraídos com padrão simples")
                        except Exception as e2:
                            logging.warning(f"Falha também no padrão simples: {e2}")

            # 2. EXTRAIR CAMPOS DETALHADOS SOLICITADOS
            
            # Nome do produto
            detailed_info['nome_produto'] = (
                structured_data.get('name') or 
                response.css('h1.ui-pdp-title::text, h1::text').get('').strip() or
                'N/A'
            )

            # Condição do produto
            condition = structured_data.get('itemCondition', '')
            if 'NewCondition' in condition:
                detailed_info['condicao_produto'] = 'Novo'
            elif 'UsedCondition' in condition:
                detailed_info['condicao_produto'] = 'Usado'
            else:
                condition_text = response.css('.ui-pdp-subtitle::text').get('')
                if condition_text and ('novo' in condition_text.lower() or 'new' in condition_text.lower()):
                    detailed_info['condicao_produto'] = 'Novo'
                elif condition_text and ('usado' in condition_text.lower() or 'used' in condition_text.lower()):
                    detailed_info['condicao_produto'] = 'Usado'
                else:
                    detailed_info['condicao_produto'] = condition_text.strip() if condition_text else 'N/A'

            # Preço
            offers = structured_data.get('offers', {}) if structured_data else {}
            price = (offers.get('price') if isinstance(offers, dict) else None) or event_data.get('price') or event_data.get('localItemPrice')
            currency = (offers.get('priceCurrency') if isinstance(offers, dict) else None) or event_data.get('currency_id', 'BRL')
            
            if price:
                detailed_info['preco'] = f"{currency} {price}"
            else:
                price_text = response.css('.andes-money-amount__fraction::text').get('')
                detailed_info['preco'] = f"BRL {price_text.strip()}" if price_text else 'N/A'

            # Desconto (verificar se há preço original diferente)
            original_price = response.css('.ui-pdp-price__original-value .andes-money-amount__fraction::text').get()
            if original_price and price:
                try:
                    orig = float(str(original_price).replace(',', '.').replace('.', ''))
                    curr = float(str(price).replace(',', '.').replace('.', ''))
                    if orig > curr:
                        discount = ((orig - curr) / orig) * 100
                        detailed_info['desconto'] = f"{discount:.1f}%"
                    else:
                        detailed_info['desconto'] = 'Sem desconto'
                except (ValueError, TypeError):
                    detailed_info['desconto'] = 'N/A'
            else:
                detailed_info['desconto'] = 'Sem desconto'

            # Frete Grátis
            free_shipping = (
                event_data.get('free_shipping', False) if event_data else False
            ) or bool(response.css('.ui-pdp-media__title:contains("Frete grátis"), .ui-shipping-title:contains("grátis")').get())
            
            detailed_info['frete_gratis'] = 'Sim' if free_shipping else 'Não'

            # Tempo de entrega
            shipping_details = offers.get('shippingDetails', {}) if isinstance(offers, dict) else {}
            delivery_time = shipping_details.get('deliveryTime', {})
            
            if delivery_time:
                handling = delivery_time.get('handlingTime', {})
                transit = delivery_time.get('transitTime', {})
                min_days = (handling.get('minValue', 0) or 0) + (transit.get('minValue', 0) or 0)
                max_days = (handling.get('maxValue', 0) or 0) + (transit.get('maxValue', 0) or 0)
                if min_days > 0 or max_days > 0:
                    detailed_info['tempo_entrega'] = f"{min_days}-{max_days} dias úteis"
                else:
                    detailed_info['tempo_entrega'] = 'Consultar no site'
            else:
                # Extrair do HTML se disponível
                delivery_text = response.css('.ui-pdp-shipping__subtitle::text, .shipping-info::text').get('')
                detailed_info['tempo_entrega'] = delivery_text.strip() if delivery_text else 'Consultar no site'

            # Nome da loja
            detailed_info['nome_loja'] = (
                event_data.get('seller_name') if event_data else None
            ) or response.css('.ui-pdp-seller__header__title::text').get('').strip() or 'N/A'

            # Quantidade de vendas do produto
            sales_text = response.css('.ui-pdp-subtitle:contains("vendidos")::text').get('')
            if sales_text:
                sales_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mil)?\s*vendidos?', sales_text.lower())
                if sales_match:
                    sales = sales_match.group(1)
                    if 'mil' in sales_text.lower():
                        try:
                            sales_num = float(sales) * 1000
                            detailed_info['vendas_produto'] = str(int(sales_num))
                        except ValueError:
                            detailed_info['vendas_produto'] = f"{sales}k"
                    else:
                        detailed_info['vendas_produto'] = sales
                else:
                    detailed_info['vendas_produto'] = 'N/A'
            else:
                detailed_info['vendas_produto'] = 'N/A'
            
            # Quantidade de vendas da loja (não sempre disponível)
            detailed_info['vendas_loja'] = event_data.get('seller_sales') if event_data else 'N/A'

            # Devolução grátis
            return_policy = offers.get('hasMerchantReturnPolicy', {}) if isinstance(offers, dict) else {}
            free_return = (
                return_policy.get('returnFees') == 'https://schema.org/FreeReturn'
            ) or bool(response.css('[data-testid="return-policy"]:contains("grátis"), .return-info:contains("grátis")').get())
            
            detailed_info['devolucao_gratis'] = 'Sim' if free_return else 'N/A'

            # Compra Garantida (MercadoLivre sempre oferece)
            detailed_info['compra_garantida'] = 'Sim'

            # Tempo de garantia
            guarantee_days = return_policy.get('merchantReturnDays') if return_policy else 30
            detailed_info['tempo_garantia'] = f"{guarantee_days} dias" if guarantee_days else '30 dias'

            # Descrição do produto - MELHORADA para capturar informações técnicas detalhadas
            description = structured_data.get('description', '') if structured_data else ''
            detailed_technical_info = {}
            
            if not description:
                # Buscar na descrição principal do produto 
                desc_paragraphs = response.css('p[data-testid="content"]::text, .ui-pdp-description__content p::text, .ui-pdp-description p::text').getall()
                description = ' '.join([p.strip() for p in desc_paragraphs if p.strip()])
            
            # NOVO: Extrair informações técnicas específicas da descrição
            if description:
                text_lower = description.lower()
                
                # Extrair tipos de tinta
                ink_patterns = [
                    r'tipo(?:s)? de tinta[:：]\s*([^<\n\r]+)',
                    r'tinta[:：]\s*([^<\n\r]*(?:pigment|corante|dye)[^<\n\r]*)',
                    r'(?:tinta\s+)?(?:à base de|base de)\s+([^<\n\r]+)',
                    r'impressão de cores consumíveis[:：]\s*([^<\n\r]+)'
                ]
                
                for pattern in ink_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        detailed_technical_info['tipo_tinta'] = match.group(1).strip()[:100]
                        break
                
                # Extrair rendimento de páginas
                page_yield_patterns = [
                    r'rendimento[^:]*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:páginas?|folhas?)',
                    r'rende?\s*(?:até\s*)?(\d+(?:\.\d+)?)\s*(?:páginas?|folhas?)',
                    r'(?:páginas?|folhas?)[:：]?\s*(\d+(?:\.\d+)?)',
                    r'(\d+(?:\.\d+)?)\s*páginas?'
                ]
                
                for pattern in page_yield_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        detailed_technical_info['rendimento_paginas'] = f"{match.group(1)} páginas"
                        break
                
                # Extrair temperaturas
                temp_patterns = [
                    r'temperatura.*operacional[^:]*[:：]?\s*([^<\n\r]+)',
                    r'faixa de temperatura[^:]*[:：]?\s*([^<\n\r]+)',
                    r'temperatura[^:]*armazen[^:]*[:：]?\s*([^<\n\r]+)'
                ]
                
                for pattern in temp_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        temp_info = match.group(1).strip()[:100]
                        if 'operacion' in pattern:
                            detailed_technical_info['temperatura_operacional'] = temp_info
                        elif 'armazen' in pattern:
                            detailed_technical_info['temperatura_armazenamento'] = temp_info
                        else:
                            detailed_technical_info['temperatura'] = temp_info
                
                # Extrair volume/capacidade
                volume_patterns = [
                    r'(?:volume|capacidade)[^:]*[:：]?\s*(\d+(?:\.\d+)?)\s*ml',
                    r'(\d+(?:\.\d+)?)\s*ml',
                    r'conteúdo[^:]*[:：]?\s*(\d+(?:\.\d+)?)\s*ml'
                ]
                
                for pattern in volume_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        detailed_technical_info['volume_ml'] = f"{match.group(1)} ml"
                        break
                
                # Extrair umidade
                humidity_patterns = [
                    r'umidade[^:]*[:：]?\s*([^<\n\r]+)',
                    r'(\d+(?:\.\d+)?)\s*(?:a|até)\s*(\d+(?:\.\d+)?)\s*%\s*ur'
                ]
                
                for pattern in humidity_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        if len(match.groups()) > 1:
                            detailed_technical_info['umidade'] = f"{match.group(1)}-{match.group(2)}% UR"
                        else:
                            detailed_technical_info['umidade'] = match.group(1).strip()[:100]
                        break
                
                # Extrair impressoras compatíveis
                compatible_patterns = [
                    r'impressoras?\s*compatíveis?[:：]?\s*([^<\n\r]+)',
                    r'compatível\s*com[:：]?\s*([^<\n\r]+)',
                    r'para\s*(?:impressoras?)?[:：]?\s*(hp\s+[^<\n\r]*)',
                ]
                
                for pattern in compatible_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        printers = match.group(1).strip()[:300]
                        # Limpar texto desnecessário
                        printers = re.sub(r'<[^>]+>', '', printers)
                        detailed_technical_info['impressoras_compativeis'] = printers
                        break
            
            detailed_info['descricao_produto'] = description[:1000] if description else 'N/A'
            detailed_info['especificacoes_tecnicas'] = detailed_technical_info if detailed_technical_info else 'N/A'

            # Características Principais
            specs = []
            spec_rows = response.css('.andes-table tbody tr, .ui-vpp-highlighted-specs table tbody tr')
            
            for row in spec_rows:
                label = row.css('th::text, .andes-table__header--left::text').get('').strip()
                value = row.css('td::text, .andes-table__column--value::text').get('').strip()
                if label and value:
                    specs.append(f"{label}: {value}")
            
            detailed_info['caracteristicas_principais'] = specs[:10] if specs else ['N/A']

            # Outros (informações adicionais do event_data)
            additional_info = {}
            if event_data:
                additional_info.update({
                    'seller_id': event_data.get('seller_id'),
                    'reputation_level': event_data.get('reputation_level'),
                    'power_seller_status': event_data.get('power_seller_status'),
                    'loyalty_level': event_data.get('loyalty_level'),
                    'shipping_mode': event_data.get('shipping_mode'),
                    'review_rate': event_data.get('review_rate')
                })
            
            if structured_data:
                additional_info.update({
                    'brand': structured_data.get('brand'),
                    'sku': structured_data.get('sku'),
                    'product_id': structured_data.get('productID')
                })
            
            # Filtrar valores não nulos
            detailed_info['outros'] = {k: v for k, v in additional_info.items() if v is not None}

            # Fotos do produto
            images = []
            main_image = structured_data.get('image') if structured_data else None
            if main_image:
                images.append(main_image)
            
            # Extrair outras imagens da galeria
            gallery_images = response.css('.ui-pdp-gallery__figure__image::attr(src), .gallery-img::attr(src)').getall()
            for img in gallery_images:
                if img and img not in images:
                    images.append(img)
            
            detailed_info['fotos_produto'] = images[:10] if images else ['N/A']

            # AVALIAÇÕES MELHORADAS - Extração completa da estrutura de reviews
            rating_info = structured_data.get('aggregateRating', {}) if structured_data else {}
            reviews_data = event_data.get('reviews', {}) if event_data else {}
            
            # Inicializar estrutura completa de reviews
            reviews_completos = {
                'rating_medio': 'N/A',
                'total_reviews': 'N/A',
                'tem_reviews': False,
                'distribuicao_estrelas': {
                    'estrelas_5': {'quantidade': 0, 'percentual': '0%'},
                    'estrelas_4': {'quantidade': 0, 'percentual': '0%'}, 
                    'estrelas_3': {'quantidade': 0, 'percentual': '0%'},
                    'estrelas_2': {'quantidade': 0, 'percentual': '0%'},
                    'estrelas_1': {'quantidade': 0, 'percentual': '0%'}
                },
                'reviews_com_texto': 0,
                'reviews_com_imagens': 0,
                'avaliacoes_positivas': 0,
                'avaliacoes_negativas': 0,
                'avaliacoes_neutras': 0
            }
            
            # Dados do JSON-LD estruturado
            if rating_info:
                reviews_completos['rating_medio'] = rating_info.get('ratingValue', 'N/A')
                reviews_completos['total_reviews'] = rating_info.get('ratingCount', 0)
                reviews_completos['tem_reviews'] = bool(rating_info.get('ratingCount', 0))
            
            # Dados de reviews do event_data
            if reviews_data:
                reviews_completos['rating_medio'] = reviews_data.get('rate', reviews_completos['rating_medio'])
                reviews_completos['total_reviews'] = reviews_data.get('count', reviews_completos['total_reviews'])
                reviews_completos['tem_reviews'] = bool(reviews_data.get('count', 0))
                reviews_completos['reviews_com_texto'] = reviews_data.get('reviews_with_comment', 0)
                reviews_completos['reviews_com_imagens'] = reviews_data.get('pictures_quantity', 0)
            
            # Fallback para review_rate simples se não encontrou nada
            if not reviews_completos.get('rating_medio') or reviews_completos['rating_medio'] == 'N/A':
                if event_data.get('review_rate'):
                    reviews_completos['rating_medio'] = event_data.get('review_rate')
                    reviews_completos['tem_reviews'] = True
            
            # NOVO: Extrair distribuição de estrelas do HTML (estrutura completa como fornecida pelo usuário)
            try:
                # Buscar pelo componente de rating com data-testid="rating-component"
                rating_component = response.css('div[data-testid="rating-component"]').get()
                
                if rating_component:
                    # Extrair rating médio do componente visual
                    avg_rating = response.css('p.ui-review-capability__rating__average::text').get()
                    if avg_rating:
                        reviews_completos['rating_medio'] = float(avg_rating.strip())
                    
                    # Extrair total de avaliações
                    total_label = response.css('p.ui-review-capability__rating__label::text').get()
                    if total_label:
                        # Buscar número no formato "4.931 avaliações"
                        total_match = re.search(r'([\d.,]+)\s*avali', total_label.lower())
                        if total_match:
                            total_str = total_match.group(1).replace('.', '').replace(',', '')
                            reviews_completos['total_reviews'] = int(total_str)
                            reviews_completos['tem_reviews'] = True
                    
                    # Extrair distribuição detalhada por estrelas
                    star_levels = response.css('li.ui-review-capability-rating__level')
                    total_reviews_num = reviews_completos.get('total_reviews', 0)
                    
                    if star_levels and isinstance(total_reviews_num, int) and total_reviews_num > 0:
                        for i, level in enumerate(star_levels):
                            star_num = 5 - i  # 5, 4, 3, 2, 1
                            
                            # Extrair percentual da barra de progresso
                            fill_style = level.css('.ui-review-capability-rating__level__progress-bar__fill-background::attr(style)').get()
                            if fill_style:
                                width_match = re.search(r'width:\s*([\d.]+)%', fill_style)
                                if width_match:
                                    percentual = float(width_match.group(1))
                                    quantidade = int((percentual / 100.0) * total_reviews_num)
                                    
                                    reviews_completos['distribuicao_estrelas'][f'estrelas_{star_num}'] = {
                                        'quantidade': quantidade,
                                        'percentual': f'{percentual:.2f}%'
                                    }
                        
                        # Calcular avaliações positivas/negativas/neutras
                        estrelas_5 = reviews_completos['distribuicao_estrelas']['estrelas_5']['quantidade']
                        estrelas_4 = reviews_completos['distribuicao_estrelas']['estrelas_4']['quantidade']
                        estrelas_3 = reviews_completos['distribuicao_estrelas']['estrelas_3']['quantidade']
                        estrelas_2 = reviews_completos['distribuicao_estrelas']['estrelas_2']['quantidade']
                        estrelas_1 = reviews_completos['distribuicao_estrelas']['estrelas_1']['quantidade']
                        
                        reviews_completos['avaliacoes_positivas'] = estrelas_5 + estrelas_4
                        reviews_completos['avaliacoes_neutras'] = estrelas_3
                        reviews_completos['avaliacoes_negativas'] = estrelas_2 + estrelas_1
                
                logging.info(f"Reviews estruturados extraídos: rating={reviews_completos.get('rating_medio')}, total={reviews_completos.get('total_reviews')}, distribuição={len([k for k,v in reviews_completos['distribuicao_estrelas'].items() if v['quantidade'] > 0])} níveis")
                
            except Exception as e:
                logging.warning(f"Erro ao extrair distribuição de estrelas: {e}")
            
            detailed_info['reviews_detalhados'] = reviews_completos

            # 4. EXTRAIR CARACTERÍSTICAS DO PRODUTO
            logging.info("  [CARACTERÍSTICAS] Iniciando extração de características do produto...")
            detailed_info['main_characteristics'] = {}
            detailed_info['other_characteristics'] = {}
            
            try:
                # Extrair Características Principais - Seletores baseados na estrutura real
                main_chars_selectors = [
                    # Seletor baseado na estrutura observada na imagem
                    '.ui-vpp-striped-specs_table table.andes-table tbody tr',
                    # Seletores alternativos para diferentes layouts
                    '#highlighted_specs_attrs .ui-vpp-striped-specs_table table.andes-table tbody tr',
                    '.ui-pdp-specs .ui-vpp-striped-specs_table table.andes-table tbody tr',
                    # Seletores mais genéricos como fallback
                    '.andes-table tbody tr',
                    '[data-testid="specifications"] table tbody tr'
                ]
                
                main_chars_rows = None
                used_selector = None
                
                for selector in main_chars_selectors:
                    main_chars_rows = response.css(selector)
                    if main_chars_rows:
                        used_selector = selector
                        logging.info(f"  [CARACTERÍSTICAS PRINCIPAIS] Usando seletor: {selector}")
                        break
                
                if main_chars_rows:
                    logging.info(f"  [CARACTERÍSTICAS PRINCIPAIS] Encontradas {len(main_chars_rows)} características")
                    for i, row in enumerate(main_chars_rows):
                        # Seletores precisos baseados na estrutura HTML observada
                        char_name = (row.css('th .andes-table_header_container::text').get() or
                                    row.css('th div::text').get() or 
                                    row.css('th::text').get() or
                                    row.css('th span::text').get() or
                                    row.css('.andes-table__header--left div::text').get() or
                                    row.css('.ui-vpp-striped-specs_row_column--id div::text').get())
                        
                        # Seletores precisos para valor baseados na estrutura observada
                        char_value = (row.css('td .andes-table_column--value::text').get() or
                                     row.css('td span[id$="-value"]::text').get() or
                                     row.css('td .andes-table_column--value span::text').get() or
                                     row.css('td div::text').get() or 
                                     row.css('td::text').get() or
                                     row.css('td span::text').get())
                        
                        if char_name and char_value:
                            detailed_info['main_characteristics'][char_name.strip()] = char_value.strip()
                            logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                        else:
                            logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
                else:
                    logging.warning("  [CARACTERÍSTICAS PRINCIPAIS] Tabela não encontrada com nenhum seletor")
                
                # Extrair Outras Características - Usar abordagem mais simples (sem nth-of-type)
                other_chars_selectors = [
                    # Seletores alternativos para layout de duas colunas
                    '#highlighted_specs_attrs > div.ui-pdp-container__row.ui-pdp-container__row--technical-specifications > div > div > div > div:nth-child(2) > div > table > tbody tr',
                    # Procurar por divs adicionais com características
                    '.ui-pdp-specs .andes-table tbody tr',
                    '#highlighted_specs_attrs .andes-table tbody tr'
                ]
                
                other_chars_rows = None
                used_other_selector = None
                
                for selector in other_chars_selectors:
                    other_chars_rows = response.css(selector)
                    if other_chars_rows:
                        used_other_selector = selector
                        logging.info(f"  [OUTRAS CARACTERÍSTICAS] Usando seletor: {selector}")
                        break
                
                if other_chars_rows:
                    logging.info(f"  [OUTRAS CARACTERÍSTICAS] Encontradas {len(other_chars_rows)} características")
                    for i, row in enumerate(other_chars_rows):
                        # Usar os mesmos seletores precisos
                        char_name = (row.css('th .andes-table_header_container::text').get() or
                                    row.css('th div::text').get() or 
                                    row.css('th::text').get() or
                                    row.css('th span::text').get() or
                                    row.css('.andes-table__header--left div::text').get() or
                                    row.css('.ui-vpp-striped-specs_row_column--id div::text').get())
                        
                        char_value = (row.css('td .andes-table_column--value::text').get() or
                                     row.css('td span[id$="-value"]::text').get() or
                                     row.css('td .andes-table_column--value span::text').get() or
                                     row.css('td div::text').get() or 
                                     row.css('td::text').get() or
                                     row.css('td span::text').get())
                        
                        if char_name and char_value:
                            detailed_info['other_characteristics'][char_name.strip()] = char_value.strip()
                            logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                        else:
                            logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
                else:
                    logging.warning("  [OUTRAS CARACTERÍSTICAS] Tabela não encontrada com nenhum seletor")
                
                # Log do resumo
                total_chars = len(detailed_info['main_characteristics']) + len(detailed_info['other_characteristics'])
                logging.info(f"  [CARACTERÍSTICAS] Extração concluída: {total_chars} características encontradas")
                    
            except Exception as e:
                logging.error(f"  [CARACTERÍSTICAS] Erro durante extração: {str(e)}")
                detailed_info['main_characteristics'] = {}
                detailed_info['other_characteristics'] = {}

            logging.info(f"Extração detalhada concluída para: {detailed_info.get('nome_produto', 'N/A')}")
            return detailed_info
            
        except Exception as e:
            logging.error(f"Erro na extração detalhada de {response.url}: {str(e)}")
            return None

    def handle_error(self, failure):
        logging.error(f"Failed to fetch or process {failure.request.url}: {failure.value}")
        # Since we moved to a single, precisely constructed URL,
        # we won't automatically try other base URLs here.
        # The spider will simply finish if this request fails.
        # If self.results_list is not None and not self.results_list: # Original condition
        #     pass
        # Consider if any specific action is needed on error, e.g. returning empty results if a queue is used

    def parse(self, response):
        # Verificar se fomos redirecionados para página de verificação ou outras páginas de bloqueio
        verification_indicators = [
            'account-verification',
            'gz/account-verification', 
            'captcha',
            'blocked',
            'robot',
            'security-check',
            'rate-limited'
        ]
        
        is_blocked = any(indicator in response.url.lower() for indicator in verification_indicators)
        
        if is_blocked:
            logging.warning(f"Detectada página de verificação/bloqueio: {response.url}")
            
            # Tentar estratégias avançadas para contornar
            if not hasattr(self, '_verification_attempts'):
                self._verification_attempts = 0
            
            self._verification_attempts += 1
            
            if self._verification_attempts <= 8:  # Mais tentativas com estratégias diferentes
                logging.info(f"Tentativa {self._verification_attempts}/8 de contornar verificação...")
                
                # Delay progressivamente maior com variação aleatória
                base_delay = 15.0 + (self._verification_attempts * 10.0)  # 25s, 35s, 45s, etc.
                delay = random.uniform(base_delay, base_delay + 15.0)
                logging.info(f"Aguardando {delay:.1f}s antes de tentar novamente...")
                
                # Estratégias diferentes baseadas na tentativa
                if self._verification_attempts <= 2:
                    # Primeiras tentativas: URLs alternativas mais diretas
                    alternative_urls = [
                        f"https://www.mercadolivre.com.br/categoria/MLB1648_InformaticaEletronicos_ComponentesPC_Impressoras_Cartuchos#DEAL_ID=MLB1648&S=landingHubkeyword&V=18&L=TOP_CATEGORIES_HUB",
                        f"https://lista.mercadolivre.com.br/informatica/impressoras-scanners/impressoras/cartuchos-tinta/hp",
                        f"https://lista.mercadolivre.com.br/cartucho-hp"
                    ]
                    original_url = alternative_urls[min(self._verification_attempts - 1, len(alternative_urls) - 1)]
                elif self._verification_attempts <= 4:
                    # Tentativas intermediárias: URLs com parâmetros diferentes
                    if self.query:
                        query_variants = [
                            self.query.replace(' ', '+'),
                            self.query.replace(' ', '%20'),
                            self.query.lower().replace(' ', '-')
                        ]
                        variant = query_variants[(self._verification_attempts - 3) % len(query_variants)]
                        original_url = f"https://lista.mercadolivre.com.br/{variant}"
                    else:
                        original_url = "https://lista.mercadolivre.com.br/cartucho-impressora"
                elif self._verification_attempts <= 6:
                    # Tentativas avançadas: simulação de navegação orgânica
                    original_url = "https://www.mercadolivre.com.br/"
                else:
                    # Últimas tentativas: voltar à URL original com delay maior
                    original_url = self.start_urls[0] if self.start_urls else response.url
                
                # Headers ainda mais realistas com simulação de comportamento humano
                headers = self.get_random_headers()
                
                # Simular diferentes fontes de tráfego
                referrer_sources = [
                    'https://www.google.com.br/search?q=cartucho+hp+mercadolivre',
                    'https://www.bing.com/search?q=cartucho+impressora+hp',
                    'https://www.google.com/search?q=mercadolivre+cartucho',
                    'https://www.mercadolivre.com.br/',
                    'https://lista.mercadolivre.com.br/'
                ]
                headers['Referer'] = random.choice(referrer_sources)
                
                # Adicionar headers adicionais para parecer mais humano
                if random.random() < 0.3:  # 30% das vezes
                    headers['X-Requested-With'] = 'XMLHttpRequest'
                
                # Simular sessão com cookies
                headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
                
                yield scrapy.Request(
                    url=original_url,
                    callback=self.parse,
                    headers=headers,
                    meta={
                        'page_number': response.meta.get('page_number', 1),
                        'download_delay': delay,
                        'dont_cache': True,
                        'handle_httpstatus_list': [200, 302, 403, 429, 503],
                        'max_retry_times': 3
                    }
                )
                return
            else:
                logging.error("Múltiplas tentativas de contornar verificação falharam - implementando fallback")
                # Tentar uma última estratégia com URL mínima
                if self.query and not hasattr(self, '_final_fallback_attempted'):
                    self._final_fallback_attempted = True
                    fallback_url = f"https://www.mercadolivre.com.br/categoria/MLB1648"
                    logging.info(f"Tentativa final com URL de categoria: {fallback_url}")
                    
                    yield scrapy.Request(
                        url=fallback_url,
                        callback=self.parse,
                        headers=self.get_random_headers(),
                        meta={
                            'page_number': 1,
                            'download_delay': random.uniform(30.0, 45.0),
                            'dont_cache': True
                        }
                    )
                    return
                else:
                    logging.error("Todas as estratégias de contorno falharam")
                    return

        # Store the URL that is successfully parsed
        if response.url not in self.used_urls:
            self.used_urls.append(response.url)
        
        page_number = response.meta.get('page_number', 1)
        logging.info(f"Processing URL: {response.url} (Page {page_number})")

        if not self.html_saved_for_debug: # Only save HTML for the first processed response
            try:
                page_filename = "scraped_page_content_debug.html"
                with open(page_filename, 'wb') as f:
                    f.write(response.body)
                logging.info(f"HTML da primeira página de resultados ({response.url}) salvo em {page_filename} para depuração.")
                self.html_saved_for_debug = True
            except Exception as e:
                logging.error(f"Falha ao salvar HTML de depuração: {e}")

        # Seletores atualizados para 2025 - múltiplos fallbacks
        product_selectors = [
            # Seletores modernos do MercadoLivre
            '.ui-search-results .ui-search-result',
            'ol.ui-search-results li.ui-search-layout__item',
            '.ui-search-layout__item .andes-card.poly-card',
            'div.andes-card.poly-card',
            '.ui-search-layout__item',
            
            # Seletores alternativos mais específicos
            '[data-testid="search-result"]',
            '.ui-search-result__wrapper',
            '.poly-component__card',
            '.ui-search-item',
            
            # Seletores genéricos como última opção
            'article[data-testid]',
            'div[class*="ui-search"]',
            'li[class*="ui-search"]',
            'div[class*="product"]',
            'article[class*="card"]'
        ]
        
        products_found = []
        successful_selector = None
        
        # Tentar cada seletor em ordem de prioridade
        for selector in product_selectors:
            products = response.css(selector)
            if products and len(products) > 0:
                products_found = products
                successful_selector = selector
                logging.info(f"Encontrados {len(products)} produtos com seletor: {selector}")
                break
        
        # Se ainda não encontrou produtos, tentar com XPath
        if not products_found:
            xpath_selectors = [
                "//li[contains(@class, 'ui-search-layout__item')]",
                "//div[contains(@class, 'ui-search-result__wrapper')]/parent::*",
                "//div[contains(@class, 'andes-card') and contains(@class, 'poly-card')]",
                "//article[contains(@class, 'ui-search-result')]",
                "//div[contains(@class, 'ui-search-item')]",
                "//li[contains(@class, 'search-result')]",
                "//div[@data-testid]//div[contains(@class, 'card')]"
            ]
            
            for xpath_sel in xpath_selectors:
                products = response.xpath(xpath_sel)
                if products and len(products) > 0:
                    products_found = products
                    successful_selector = f"XPath: {xpath_sel}"
                    logging.info(f"Encontrados {len(products)} produtos com seletor XPath: {xpath_sel}")
                    break
        
        if not products_found:
            logging.warning(f"Nenhum container de produto encontrado com nenhum seletor na URL: {response.url}")
            # Salvar HTML para debug
            debug_filename = f"debug_no_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(debug_filename, 'wb') as f:
                f.write(response.body)
            logging.info(f"HTML salvo para debug: {debug_filename}")
            return
        
        item_containers_to_process = products_found
        logging.info(f"Usando seletor bem-sucedido: {successful_selector}")

        if not item_containers_to_process:
            xpath_selectors_container = [
                "//li[contains(@class, 'ui-search-layout__item')]",
                "//div[contains(@class, 'ui-search-result__wrapper')]/parent::li",
                "//div[contains(@class, 'andes-card poly-card')]/ancestor-or-self::li[contains(@class, 'ui-search-layout__item')]",
                "//div[contains(@class, 'andes-card poly-card')]"
            ]
            for xpath_sel in xpath_selectors_container:
                item_containers_to_process = response.xpath(xpath_sel)
                if item_containers_to_process:
                    logging.info(f"Encontrados {len(item_containers_to_process)} containers de produto com seletor XPath: {xpath_sel}")
                    products_poly = item_containers_to_process
                    break
            
            if not products_poly:
                logging.warning(f"Nenhum produto encontrado com CSS ou XPath na URL: {response.url}")
                page_filename = f"debug_page_no_products_{self.query.replace(' ', '_')}_{page_number}.html"
                with open(page_filename, 'wb') as f:
                    f.write(response.body)
                logging.info(f"HTML da página de busca salvo em {page_filename} para depuração.")
                return # If no products found after all attempts (CSS, XPath), then return

        logging.info(f"Processando {len(item_containers_to_process)} containers de produto encontrados em {response.url}")
        
        processed_count = 0
        skipped_sponsored = 0
        for i, item_container in enumerate(item_containers_to_process):
            # Pular os 2 primeiros itens (patrocinados)
            if skipped_sponsored < 2:
                skipped_sponsored += 1
                logging.info(f"--- Pulando container {i+1} (item patrocinado {skipped_sponsored}/2) ---")
                continue
            
            # Check if we've reached the maximum number of items
            if self.max_items and self.items_collected >= self.max_items:
                logging.info(f"Limite de {self.max_items} itens atingido. Parando a extração.")
                return
                
            logging.info(f"--- Processando container de produto {i+1}/{len(item_containers_to_process)} (total coletado: {self.items_collected}, pulados: {skipped_sponsored}) ---")
            product = {}
            
            # Seletores de título atualizados e expandidos - 2025
            title_selectors = [
                # Seletores modernos prioritários
                'h2.ui-search-item__title::text',
                '.ui-search-item__title::text',
                '.ui-search-item__title span::text',
                '.ui-search-item__title a::text',
                
                # Seletores poly-card
                'h3.poly-component__title-wrapper a.poly-component__title::text',
                '.poly-component__title::text',
                '.poly-card__content .poly-component__title::text',
                
                # Seletores alternativos
                '[data-testid="item-title"]::text',
                '.ui-search-result__title::text',
                'h3[class*="title"]::text',
                'h2[class*="title"]::text',
                'a[class*="title"]::text',
                
                # Seletores genéricos como última opção
                'h1::text',
                'h2::text', 
                'h3::text',
                'a[href*="/p/"]::text',
                '.title::text',
                '[title]::attr(title)',
                'span[class*="name"]::text'
            ]
            
            title_element = None
            for title_selector in title_selectors:
                title_element = item_container.css(title_selector).get()
                if title_element and title_element.strip():
                    break

            # Seletores de link atualizados e expandidos - 2025
            link_selectors = [
                # Links de produto prioritários
                'a.ui-search-item__group__element::attr(href)',
                'a.ui-search-link::attr(href)',
                'a[href*="/p/"]::attr(href)',
                
                # Links poly-card
                'h3.poly-component__title-wrapper a.poly-component__title::attr(href)',
                '.poly-component__title::attr(href)',
                '.poly-card__content a::attr(href)',
                
                # Links alternativos
                '[data-testid="item-link"]::attr(href)',
                '.ui-search-result__title a::attr(href)',
                '.ui-search-item__title a::attr(href)',
                'h2 a::attr(href)',
                'h3 a::attr(href)',
                
                # Links de imagem que podem ser links de produto
                '.ui-search-result-image a::attr(href)',
                'a[class*="image"]::attr(href)',
                
                # Seletores genéricos
                'a::attr(href)'
            ]
            
            link_element = None
            for link_selector in link_selectors:
                links = item_container.css(link_selector).getall()
                # Filtrar apenas links que parecem ser de produtos
                for link in links:
                    if link and ('/p/' in link or '/produto/' in link or 'MLB' in link):
                        link_element = link
                        break
                if link_element:
                    break

            if title_element:
                product['TITULO PRODUTO'] = title_element.strip()
                logging.info(f"  [TÍTULO] Encontrado: '{product['TITULO PRODUTO']}'")
            else:
                logging.warning(f"  [TÍTULO] Não encontrado para o container {i+1}.")
                # Save HTML of container if title is missing for debugging
                with open(f"debug_container_no_title_{self.query.replace(' ', '_')}_{page_number}_{i+1}.html", "w", encoding="utf-8") as f:
                    f.write(item_container.get())
                logging.info(f"HTML do container {i+1} (sem título) salvo em debug_container_no_title_{self.query.replace(' ', '_')}_{page_number}_{i+1}.html")
                continue # Essential data missing

            if link_element:
                product['LINK'] = response.urljoin(link_element)
                logging.info(f"  [LINK] Encontrado: '{product['LINK']}'")

                # --- Extrair ID do Produto do Link ---
                # Regex melhorado para capturar ID do produto em diferentes formatos
                # Padrão 1: /p/MLB + números/letras
                match_id = re.search(r'/(?:p|up)/(MLB[A-Z0-9]+)', product['LINK'])
                if match_id:
                    product['ID_PRODUTO'] = match_id.group(1)
                    logging.info(f"  [ID PRODUTO] Encontrado: '{product['ID_PRODUTO']}'")
                else:
                    # Fallback: tentar capturar qualquer ID após /p/ ou /up/ mas antes de parâmetros
                    fallback_match = re.search(r'/(?:p|up)/([A-Z0-9]+)', product['LINK'])
                    if fallback_match:
                        product['ID_PRODUTO'] = fallback_match.group(1)
                        logging.info(f"  [ID PRODUTO] Encontrado (fallback): '{product['ID_PRODUTO']}'")
                    else:
                        product['ID_PRODUTO'] = 'N/A'
                        logging.warning(f"  [ID PRODUTO] Não encontrado no link: {product['LINK']}")
                # --- Fim da Extração do ID ---
            else:
                product['LINK'] = 'N/A'
                product['ID_PRODUTO'] = 'N/A' # Se não há link, não há ID
                logging.warning(f"  [LINK] Não encontrado para o container {i+1}.")

            # Price - Prioritize general selectors
            price_main_fraction = item_container.css('.ui-search-price__second-line .andes-money-amount__fraction::text').get()
            price_main_currency = item_container.css('.ui-search-price__second-line .andes-money-amount__currency-symbol::text').get()
            price_main_cents = item_container.css('.ui-search-price__second-line .andes-money-amount__cents::text').get()

            if price_main_fraction:
                product_price = f"{price_main_currency or 'R$'} {price_main_fraction.strip()}"
                if price_main_cents:
                    product_price += f",{price_main_cents.strip()}"
                product['PREÇO'] = product_price
                logging.info(f"  [PREÇO] Encontrado (general): '{product['PREÇO']}'")
            else:
                # Fallback to poly-card specific price
                price_fraction_poly = item_container.css('.poly-price__current .andes-money-amount__fraction::text').get()
                price_cents_poly = item_container.css('.poly-price__current .andes-money-amount__cents::text').get()
                price_currency_poly = item_container.css('.poly-price__current .andes-money-amount__currency-symbol::text').get()
                if price_fraction_poly:
                    product_price = f"{price_currency_poly or 'R$'} {price_fraction_poly.strip()}"
                    if price_cents_poly:
                        product_price += f",{price_cents_poly.strip()}"
                    product['PREÇO'] = product_price
                    logging.info(f"  [PREÇO] Encontrado (poly-card fallback): '{product['PREÇO']}'")
                else:
                    # Broader general selector as last resort for price
                    price_fraction_broad = item_container.css('.andes-money-amount__fraction::text').get() # Might be multiple, pick first
                    price_currency_broad = item_container.css('.andes-money-amount__currency-symbol::text').get()
                    price_cents_broad = item_container.css('.andes-money-amount__cents::text').get()
                    if price_fraction_broad:
                        product_price = f"{price_currency_broad or 'R$'} {price_fraction_broad.strip()}"
                        if price_cents_broad:
                             product_price += f",{price_cents_broad.strip()}"
                        product['PREÇO'] = product_price
                        logging.info(f"  [PREÇO] Encontrado (broad fallback): '{product['PREÇO']}'")
                    else:
                        product['PREÇO'] = 'N/A'
                        logging.warning(f"  [PREÇO] Não encontrado para o container {i+1}.")

            # Old Price - Prioritize general selectors
            old_price_fraction_general = item_container.css('.ui-search-price__original-value .andes-money-amount__fraction::text').get()
            old_price_currency_general = item_container.css('.ui-search-price__original-value .andes-money-amount__currency-symbol::text').get()

            if old_price_fraction_general:
                product['PREÇO ANTERIOR'] = f"{old_price_currency_general or 'R$'} {old_price_fraction_general.strip()}"
                logging.info(f"  [PREÇO ANTERIOR] Encontrado (general): '{product['PREÇO ANTERIOR']}'")
            else:
                # Fallback to poly-card specific old price
                old_price_fraction_poly = item_container.css('s.andes-money-amount--previous .andes-money-amount__fraction::text').get()
                old_price_currency_poly = item_container.css('s.andes-money-amount--previous .andes-money-amount__currency-symbol::text').get()
                if old_price_fraction_poly:
                    product['PREÇO ANTERIOR'] = f"{old_price_currency_poly or 'R$'} {old_price_fraction_poly.strip()}"
                    logging.info(f"  [PREÇO ANTERIOR] Encontrado (poly-card fallback): '{product['PREÇO ANTERIOR']}'")
                else:
                    product['PREÇO ANTERIOR'] = 'N/A'
            
            # Brand - Prioritize general selectors
            brand_general = item_container.css('span.ui-search-item__brand-discoverability::text').get() or \
                            item_container.css('.ui-search-item__brand::text').get() # Less specific general brand
            if brand_general:
                product['MARCA'] = brand_general.strip()
                logging.info(f"  [MARCA] Encontrada (general): '{product['MARCA']}'")
            else:
                # Fallback to poly-card specific brand
                brand_poly_debug = item_container.css('span.poly-component__brand::text').get()
                if brand_poly_debug:
                    product['MARCA'] = brand_poly_debug.strip()
                    logging.info(f"  [MARCA] Encontrada (poly-card fallback): '{product['MARCA']}'")
                else:
                    product['MARCA'] = 'N/A'
                    logging.info(f"  [MARCA] Não encontrada (general/poly).")

            if self.extract_images:
                # Prioritize general image selectors
                image_url_general = item_container.css('img.ui-search-result-image__element::attr(data-src)').get() or \
                                    item_container.css('img.ui-search-result-image__element::attr(src)').get() or \
                                    item_container.css('.slick-slide img::attr(data-src)').get() or \
                                    item_container.css('.slick-slide img::attr(src)').get() or \
                                    item_container.css('div.ui-search-result-image img::attr(data-src)').get() or \
                                    item_container.css('div.ui-search-result-image img::attr(src)').get()

                if image_url_general:
                    product['IMAGEM'] = image_url_general
                    logging.info(f"  [IMAGEM] URL da imagem (general): {product['IMAGEM']}")
                else:
                    # Fallback to poly-card specific image
                    image_url_poly_debug = item_container.css('div.poly-card__portada img.poly-component__picture::attr(data-src)').get() or \
                                           item_container.css('div.poly-card__portada img.poly-component__picture::attr(src)').get()
                    if image_url_poly_debug:
                        product['IMAGEM'] = image_url_poly_debug
                        logging.info(f"  [IMAGEM] URL da imagem (poly-card fallback): {product['IMAGEM']}")
                    else:
                        product['IMAGEM'] = 'N/A'
                        logging.warning(f"  [IMAGEM] Não encontrada para o container {i+1} (extração habilitada).")
            else:
                product['IMAGEM'] = 'N/A (imagens desabilitadas)'
                logging.info("  [IMAGEM] Extração de imagens desabilitada pelo usuário.")

            # Seller - Prioritize general selectors
            seller_official_store = item_container.css('a.ui-search-official-store-item__link::text').get() # e.g., "Por Eshop"
            if seller_official_store:
                seller_name = seller_official_store.replace("Por ", "").strip()
                product['VENDEDOR'] = seller_name
                logging.info(f"  [VENDEDOR] Loja Oficial encontrada (general): '{product['VENDEDOR']}'")
            else:
                seller_general = item_container.css('.ui-search-seller__name::text').get()
                if seller_general:
                    product['VENDEDOR'] = seller_general.strip()
                    logging.info(f"  [VENDEDOR] Encontrado (general): '{product['VENDEDOR']}'")
                else:
                    # Fallback to poly-card specific seller
                    seller_poly_debug_raw = item_container.css('span.poly-component__seller::text').get()
                    if seller_poly_debug_raw:
                        seller_name_poly = seller_poly_debug_raw.replace("Por ", "").strip()
                        product['VENDEDOR'] = seller_name_poly
                        logging.info(f"  [VENDEDOR] Encontrado (poly-card fallback): '{product['VENDEDOR']}'")
                    else:
                        product['VENDEDOR'] = 'N/A'
                        logging.info(f"  [VENDEDOR] Não encontrado para o container {i+1}.")
            
            # Ratings - Prioritize general selectors
            rating_average_general = item_container.css('.ui-search-reviews__rating-number::text').get()
            rating_total_general = item_container.css('.ui-search-reviews__amount::text').get() # Example: "(1530)"

            if rating_average_general:
                product['MÉDIA AVALIAÇÕES'] = rating_average_general.strip()
                logging.info(f"  [MÉDIA AVALIAÇÕES] Encontrada (general): '{product['MÉDIA AVALIAÇÕES']}'")
                if rating_total_general:
                    match_general = re.search(r'\((\d+(?:\.\d+)?k?)\)', rating_total_general) # Handles "1.5k" or "1530"
                    if match_general:
                        product['TOTAL AVALIAÇÕES'] = match_general.group(1)
                        logging.info(f"  [TOTAL AVALIAÇÕES] Encontrado (general): '{product['TOTAL AVALIAÇÕES']}'")
                    else:
                        product['TOTAL AVALIAÇÕES'] = rating_total_general.strip() # Fallback if regex fails
                else:
                    product['TOTAL AVALIAÇÕES'] = 'N/A' 
            else:
                # Fallback to poly-card specific ratings
                rating_average_poly_debug = item_container.css('.poly-reviews__rating::text').get()
                rating_total_poly_debug = item_container.css('.poly-reviews__total::text').get()
                if rating_average_poly_debug:
                    product['MÉDIA AVALIAÇÕES'] = rating_average_poly_debug.strip()
                    logging.info(f"  [MÉDIA AVALIAÇÕES] Encontrada (poly-card fallback): '{product['MÉDIA AVALIAÇÕES']}'")
                    if rating_total_poly_debug:
                        match_debug = re.search(r'\((\d+(?:\.\d+)?k?)\)', rating_total_poly_debug)
                        if match_debug:
                            product['TOTAL AVALIAÇÕES'] = match_debug.group(1)
                            logging.info(f"  [TOTAL AVALIAÇÕES] Encontrado (poly-card fallback): '{product['TOTAL AVALIAÇÕES']}'")
                        else:
                            product['TOTAL AVALIAÇÕES'] = rating_total_poly_debug.strip()
                    else:
                        product['TOTAL AVALIAÇÕES'] = 'N/A'
                else:
                    product['MÉDIA AVALIAÇÕES'] = 'N/A'
                    product['TOTAL AVALIAÇÕES'] = 'N/A'

            # Delivery Text - Prioritize general selectors
            delivery_info_general = item_container.css('p.ui-search-shipping__text::text').get()
            delivery_info_alt_general = item_container.css('.ui-search-item__shipping--full::text').get() or \
                                        item_container.css('.ui-search-item__shipping::text').get() or \
                                        item_container.css('span[class*="shipping"]::text').getall() # Can be list

            delivery_info = 'N/A'
            if delivery_info_general:
                delivery_info = delivery_info_general.strip()
                product['ENTREGA'] = delivery_info if delivery_info else 'N/A'
                logging.info(f"  [ENTREGA] Texto encontrado (p.ui-search-shipping__text): '{product['ENTREGA']}'")
            elif delivery_info_alt_general:
                if isinstance(delivery_info_alt_general, list):
                    delivery_info = " ".join(s.strip() for s in delivery_info_alt_general if s.strip()).strip()
                else:
                    delivery_info = delivery_info_alt_general.strip()
                product['ENTREGA'] = delivery_info if delivery_info else 'N/A'
                logging.info(f"  [ENTREGA] Texto encontrado (general alt): '{product['ENTREGA']}'")
            else:
                # Fallback to poly-card specific delivery text
                shipping_text_poly_debug = item_container.css('.poly-component__shipping::text').get()
                if shipping_text_poly_debug:
                    delivery_info = shipping_text_poly_debug.strip()
                    product['ENTREGA'] = delivery_info if delivery_info else 'N/A'
                    logging.info(f"  [ENTREGA] Texto encontrado (poly-card fallback): '{product['ENTREGA']}'")
                # else: # Ensure it's set if nothing found
                #     product['ENTREGA'] = 'N/A'
                #     logging.info("  [ENTREGA] Informação de entrega não encontrada.")

            # Ensure 'ENTREGA' field is populated if not already or default to N/A
            if product.get('ENTREGA', 'N/A') == 'N/A' and delivery_info != 'N/A':
                 product['ENTREGA'] = delivery_info
            elif product.get('ENTREGA', 'N/A') == 'N/A':
                 product['ENTREGA'] = 'N/A'


            is_full = False
            # Check for FULL indicator (SVG or text) - Prioritize general ones
            full_indicator_svg_general = item_container.css('svg.ui-pb-icon--full') or \
                                         item_container.css('svg[class*="ui-search-icon-full"]') # General icon
            full_indicator_text_general = item_container.css('span.ui-pb-label--TYPE_ADAS_FULL_LABEL_ONLY::text').get() # General label

            if full_indicator_svg_general:
                is_full = True
                logging.info("  [ENTREGA FULL] Indicador FULL encontrado (general SVG).")
            elif full_indicator_text_general and "full" in full_indicator_text_general.lower():
                is_full = True
                logging.info("  [ENTREGA FULL] Indicador FULL encontrado (general label text).")
            elif "full" in delivery_info.lower() and delivery_info != 'N/A': # Check delivery text as well
                is_full = True
                logging.info("  [ENTREGA FULL] 'full' detectado no texto da entrega.")
            else:
                # Fallback to poly-card specific FULL indicator
                shipped_from_svg_poly_debug = item_container.css('span.poly-component__shipped-from svg use[href="#poly_full"]') 
                if shipped_from_svg_poly_debug:
                    is_full = True
                    logging.info("  [ENTREGA FULL] Indicador FULL encontrado (poly-card fallback SVG).")
            
            product['ENTREGA FULL'] = "Sim" if is_full else "Não"
            
            logging.info(f"Produto processado: {product.get('TITULO PRODUTO')}")
            if self.results_list is not None:
                self.results_list.append(product)
            processed_count += 1
            self.items_collected += 1  # Increment total items collected counter
            yield product
            
            # If we've hit the max items limit, stop processing
            if self.max_items and self.items_collected >= self.max_items:
                logging.info(f"Limite de {self.max_items} itens atingido durante o processamento da página. Parando.")
                return
        
        if processed_count > 0:
            logging.info(f"Total de {processed_count} itens processados e yieldados nesta página ({response.url}).")
            
            # Se já atingiu o limite definido pelo usuário, para aqui
            if self.max_items and self.items_collected >= self.max_items:
                logging.info(
                    f"Limite de {self.max_items} itens atingido; spider termina."
                )
                return

            # -------------------- NOVA LÓGICA DE PAGINAÇÃO --------------------
            match_offset   = re.search(r'_Desde_(\d+)', response.url)
            current_offset = int(match_offset.group(1)) if match_offset else 0
            next_offset    = current_offset + self.STEP     # 0→50→100…
            first_item     = next_offset + 1                # 1→51→101…

            # Se o usuário definiu um limite menor, aborta aqui
            if self.max_items and first_item > self.max_items:
                return

            base, _, frag  = response.url.partition('#')
            qsplit         = base.split('?', 1)
            path_only      = qsplit[0]
            query          = f'?{qsplit[1]}' if len(qsplit) > 1 else ''

            if '_Desde_' in base:
                next_base = re.sub(
                    r'_Desde_\d+(?:_NoIndex_True)?',
                    f'_Desde_{first_item}_NoIndex_True',
                    base
                )
            else:
                next_base = f'{path_only}_Desde_{first_item}_NoIndex_True{query}'

            next_url = f'{next_base}#{frag}' if frag else next_base
            logging.info(f"Próxima página gerada: {next_url}")

            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                meta={'page_number': response.meta.get('page_number', 1) + 1}
            )
            # ------------------------------------------------------------------

        else:
            logging.warning(
                f"Nenhum item foi efetivamente processado e yieldado nesta "
                f"página ({response.url}), apesar de "
                f"{len(item_containers_to_process)} containers terem sido encontrados."
            )
            page_filename_no_yield = (
                f"debug_page_no_yield_{self.query.replace(' ', '_')}_{page_number}.html"
            )
            with open(page_filename_no_yield, 'wb') as f:
                f.write(response.body)
            logging.info(
                f"HTML da página de busca (sem yield) salvo em "
                f"{page_filename_no_yield} para depuração."
            )

class MercadoLivreProductDetailsSpider(scrapy.Spider):
    """
    Spider para extrair detalhes específicos de produtos individuais do Mercado Livre
    """
    name = 'mercadolivre_details'
    
    def __init__(self, product_url=None, results_list=None, *args, **kwargs):
        super(MercadoLivreProductDetailsSpider, self).__init__(*args, **kwargs)
        self.product_url = product_url
        self.results_list = results_list
        
        if not product_url:
            raise ValueError("A product_url must be provided to the MercadoLivreProductDetailsSpider.")
        
        self.start_urls = [product_url]
        logging.info(f"ProductDetailsSpider initialized for URL: {self.product_url}")
    
    def start_requests(self):
        if self.product_url:
            logging.info(f"Fetching product details from: {self.product_url}")
            yield scrapy.Request(
                url=self.product_url,
                callback=self.parse_product_details,
                errback=self.handle_error,
                headers={'User-Agent': random.choice(USER_AGENTS)},
                meta={'product_url': self.product_url}
            )
    
    def handle_error(self, failure):
        logging.error(f"Failed to fetch product details from {failure.request.url}: {failure.value}")
        if self.results_list is not None:
            self.results_list.append(None)
    
    def parse_product_details(self, response):
        """
        Extrai descrição e características detalhadas do produto
        """
        logging.info(f"Parsing product details from: {response.url}")
        
        product_details = {
            'url': response.url,
            'description': None,
            'main_characteristics': {},
            'other_characteristics': {},
            'review_stats': {
                'total_reviews': None,
                'star_distribution': {}
            },
            'extraction_success': False
        }
        
        try:
            # Extrair Descrição - Capturar todos os parágrafos
            description_container_selector = '#ui-pdp-main-container > div.ui-pdp-container__col.col-3.ui-pdp-container--column-center.pb-40 > div > div:nth-child(7) > div > div > div > div'
            description_paragraphs = response.css(description_container_selector + ' p::text').getall()
            
            if description_paragraphs:
                # Juntar todos os parágrafos com quebras de linha
                full_description = '\n\n'.join([p.strip() for p in description_paragraphs if p.strip()])
                product_details['description'] = full_description
                logging.info(f"  [DESCRIÇÃO] Encontrada ({len(description_paragraphs)} parágrafos): '{product_details['description'][:100]}...'")
            else:
                # Fallback: tentar seletores alternativos para descrição
                alt_description_selectors = [
                    '.ui-pdp-description__content p::text',
                    '.ui-pdp-description p::text',
                    '[data-testid="product-description"] p::text',
                    '.ui-pdp-description__content::text',
                    '.ui-pdp-collapsable__content p::text'
                ]
                
                description_found = False
                for alt_selector in alt_description_selectors:
                    alt_paragraphs = response.css(alt_selector).getall()
                    if alt_paragraphs:
                        full_description = '\n\n'.join([p.strip() for p in alt_paragraphs if p.strip()])
                        product_details['description'] = full_description
                        logging.info(f"  [DESCRIÇÃO] Encontrada (fallback {alt_selector}): '{product_details['description'][:100]}...'")
                        description_found = True
                        break
                
                if not description_found:
                    # Último fallback: tentar capturar todo o texto do container
                    description_all_text = response.css(description_container_selector + '::text').getall()
                    if description_all_text:
                        full_description = '\n'.join([t.strip() for t in description_all_text if t.strip()])
                        product_details['description'] = full_description
                        logging.info(f"  [DESCRIÇÃO] Encontrada (texto completo): '{product_details['description'][:100]}...'")
                    else:
                        product_details['description'] = 'N/A'
                        logging.warning("  [DESCRIÇÃO] Não encontrada")
            
            # Extrair Estatísticas de Reviews
            total_reviews_selector = '#reviews_capability_v3 > div > section > div > div:nth-child(1) > div:nth-child(1) > div.ui-review-capability__rating > div.ui-review-capability__rating__start-content > div:nth-child(2) > p'
            total_reviews_text = response.css(total_reviews_selector + '::text').get()
            
            if total_reviews_text:
                # Extrair número do texto (ex: "1.234 opiniões" -> 1234)
                import re
                total_match = re.search(r'([\d.,]+)', total_reviews_text.replace('.', '').replace(',', ''))
                if total_match:
                    total_reviews = int(total_match.group(1))
                    product_details['review_stats']['total_reviews'] = total_reviews
                    logging.info(f"  [TOTAL REVIEWS] Encontrado: {total_reviews}")
                    
                    # Extrair distribuição por estrelas
                    star_levels = response.css('#reviews_capability_v3 ul li')
                    logging.info(f"  [DISTRIBUIÇÃO ESTRELAS] Encontrados {len(star_levels)} níveis de estrela")
                    
                    for i, star_level in enumerate(star_levels):
                        star_number = 5 - i  # 5 estrelas é o primeiro, 1 estrela é o último
                        
                        # Extrair porcentagem da barra de progresso
                        progress_bar_selector = '.ui-review-capability-rating__level__progress-bar__fill-background'
                        progress_element = star_level.css(progress_bar_selector)
                        
                        if progress_element:
                            # Tentar extrair do atributo style (width: X%)
                            style_attr = progress_element.css('::attr(style)').get()
                            if style_attr:
                                width_match = re.search(r'width:\s*([\d.]+)%', style_attr)
                                if width_match:
                                    percentage = float(width_match.group(1))
                                    star_count = int((percentage / 100) * total_reviews)
                                    product_details['review_stats']['star_distribution'][star_number] = {
                                        'percentage': percentage,
                                        'count': star_count
                                    }
                                    logging.info(f"    - {star_number}⭐: {percentage}% ({star_count} reviews)")
                                else:
                                    logging.warning(f"    - {star_number}⭐: Não foi possível extrair porcentagem do style")
                            else:
                                logging.warning(f"    - {star_number}⭐: Atributo style não encontrado")
                        else:
                            logging.warning(f"    - {star_number}⭐: Elemento de progresso não encontrado")
                else:
                    logging.warning(f"  [TOTAL REVIEWS] Não foi possível extrair número de: '{total_reviews_text}'")
            else:
                logging.warning("  [TOTAL REVIEWS] Seletor não encontrou elemento")
                
                # Fallback: tentar seletores alternativos para reviews
                alt_review_selectors = [
                    '.ui-review-capability__rating p::text',
                    '.ui-pdp-review-summary__rating-count::text',
                    '[data-testid="review-summary"] p::text'
                ]
                
                for alt_selector in alt_review_selectors:
                    alt_reviews_text = response.css(alt_selector).get()
                    if alt_reviews_text:
                        total_match = re.search(r'([\d.,]+)', alt_reviews_text.replace('.', '').replace(',', ''))
                        if total_match:
                            total_reviews = int(total_match.group(1))
                            product_details['review_stats']['total_reviews'] = total_reviews
                            logging.info(f"  [TOTAL REVIEWS] Encontrado (fallback): {total_reviews}")
                            break
            
            # Extrair Características Principais - Seletores baseados na estrutura real
            main_chars_selectors = [
                # Seletor baseado na estrutura observada na imagem
                '.ui-vpp-striped-specs_table table.andes-table tbody tr',
                # Seletores alternativos para diferentes layouts
                '#highlighted_specs_attrs .ui-vpp-striped-specs_table table.andes-table tbody tr',
                '.ui-pdp-specs .ui-vpp-striped-specs_table table.andes-table tbody tr',
                # Seletores mais genéricos como fallback
                '.andes-table tbody tr',
                '[data-testid="specifications"] table tbody tr'
            ]
            
            main_chars_rows = None
            used_selector = None
            
            for selector in main_chars_selectors:
                main_chars_rows = response.css(selector)
                if main_chars_rows:
                    used_selector = selector
                    logging.info(f"  [CARACTERÍSTICAS PRINCIPAIS] Usando seletor: {selector}")
                    break
            
            if main_chars_rows:
                logging.info(f"  [CARACTERÍSTICAS PRINCIPAIS] Encontradas {len(main_chars_rows)} características")
                for i, row in enumerate(main_chars_rows):
                    # Seletores precisos baseados na estrutura HTML observada
                    char_name = (row.css('th .andes-table_header_container::text').get() or
                                row.css('th div::text').get() or 
                                row.css('th::text').get() or
                                row.css('th span::text').get() or
                                row.css('.andes-table__header--left div::text').get() or
                                row.css('.ui-vpp-striped-specs_row_column--id div::text').get())
                    
                    # Seletores precisos para valor baseados na estrutura observada
                    char_value = (row.css('td .andes-table_column--value::text').get() or
                                 row.css('td span[id$="-value"]::text').get() or
                                 row.css('td .andes-table_column--value span::text').get() or
                                 row.css('td div::text').get() or 
                                 row.css('td::text').get() or
                                 row.css('td span::text').get())
                    
                    if char_name and char_value:
                        product_details['main_characteristics'][char_name.strip()] = char_value.strip()
                        logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                    else:
                        logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
            else:
                logging.warning("  [CARACTERÍSTICAS PRINCIPAIS] Tabela não encontrada com nenhum seletor")
            
            # Extrair Outras Características - Usar mesma abordagem precisa
            other_chars_selectors = [
                # Procurar por segunda tabela de características
                '.ui-vpp-striped-specs_table:nth-of-type(2) table.andes-table tbody tr',
                '#highlighted_specs_attrs .ui-vpp-striped-specs_table:nth-of-type(2) table.andes-table tbody tr',
                '.ui-pdp-specs .ui-vpp-striped-specs_table:nth-of-type(2) table.andes-table tbody tr',
                # Seletores alternativos para layout de duas colunas
                '#highlighted_specs_attrs > div.ui-pdp-container__row.ui-pdp-container__row--technical-specifications > div > div > div > div:nth-child(2) > div > table > tbody tr',
                # Seletores genéricos como fallback
                '.andes-table:nth-of-type(2) tbody tr',
                '[data-testid="specifications"] table:nth-of-type(2) tbody tr'
            ]
            
            other_chars_rows = None
            used_other_selector = None
            
            for selector in other_chars_selectors:
                other_chars_rows = response.css(selector)
                if other_chars_rows:
                    used_other_selector = selector
                    logging.info(f"  [OUTRAS CARACTERÍSTICAS] Usando seletor: {selector}")
                    break
            
            if other_chars_rows:
                logging.info(f"  [OUTRAS CARACTERÍSTICAS] Encontradas {len(other_chars_rows)} características")
                for i, row in enumerate(other_chars_rows):
                    # Usar os mesmos seletores precisos
                    char_name = (row.css('th .andes-table_header_container::text').get() or
                                row.css('th div::text').get() or 
                                row.css('th::text').get() or
                                row.css('th span::text').get() or
                                row.css('.andes-table__header--left div::text').get() or
                                row.css('.ui-vpp-striped-specs_row_column--id div::text').get())
                    
                    char_value = (row.css('td .andes-table_column--value::text').get() or
                                 row.css('td span[id$="-value"]::text').get() or
                                 row.css('td .andes-table_column--value span::text').get() or
                                 row.css('td div::text').get() or 
                                 row.css('td::text').get() or
                                 row.css('td span::text').get())
                    
                    if char_name and char_value:
                        product_details['other_characteristics'][char_name.strip()] = char_value.strip()
                        logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                    else:
                        logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
            else:
                logging.warning("  [OUTRAS CARACTERÍSTICAS] Tabela não encontrada com nenhum seletor")
            
            # Fallback: tentar seletores alternativos para características
            if not product_details['main_characteristics'] and not product_details['other_characteristics']:
                logging.info("  [CARACTERÍSTICAS] Tentando seletores alternativos...")
                
                # Tentar seletores mais genéricos baseados na estrutura HTML observada
                alt_specs_selectors = [
                    '.ui-pdp-specs table tbody tr',
                    '.ui-vpp-highlighted-specs table tbody tr',
                    '.ui-vpp-striped-specs table tbody tr',
                    '.andes-table tbody tr',
                    '[data-testid="specifications"] table tbody tr',
                    '#highlighted_specs_attrs table tbody tr'  # Seletor mais genérico
                ]
                
                for alt_selector in alt_specs_selectors:
                    specs_rows = response.css(alt_selector)
                    if specs_rows:
                        logging.info(f"    Encontradas {len(specs_rows)} características com seletor alternativo: {alt_selector}")
                        for i, row in enumerate(specs_rows):
                            # Múltiplos seletores para nome
                            char_name = (row.css('th div::text').get() or 
                                        row.css('th::text').get() or
                                        row.css('th span::text').get() or
                                        row.css('td:first-child::text').get() or
                                        row.css('td:first-child div::text').get() or
                                        row.css('.andes-table__header div::text').get())
                            
                            # Múltiplos seletores para valor
                            char_value = (row.css('td:last-child div::text').get() or
                                         row.css('td:last-child::text').get() or
                                         row.css('td:last-child span::text').get() or
                                         row.css('.andes-table__column--value div::text').get() or
                                         row.css('.andes-table__column--value span::text').get())
                            
                            if char_name and char_value:
                                product_details['main_characteristics'][char_name.strip()] = char_value.strip()
                                logging.info(f"      - {char_name.strip()}: {char_value.strip()}")
                            else:
                                logging.debug(f"      - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
                        break
            
            # Marcar como sucesso se pelo menos uma informação foi extraída
            if (product_details['description'] != 'N/A' or 
                product_details['main_characteristics'] or 
                product_details['other_characteristics'] or
                product_details['review_stats']['total_reviews'] is not None):
                product_details['extraction_success'] = True
                logging.info("  [EXTRAÇÃO] Sucesso - Informações detalhadas extraídas")
            else:
                logging.warning("  [EXTRAÇÃO] Falha - Nenhuma informação detalhada encontrada")
            
        except Exception as e:
            logging.error(f"  [ERRO] Erro durante extração de detalhes: {str(e)}")
            product_details['extraction_success'] = False
        
        # Salvar HTML para debug se necessário
        if not product_details['extraction_success']:
            debug_filename = f"debug_product_details_{response.url.split('/')[-1]}.html"
            try:
                with open(debug_filename, 'wb') as f:
                    f.write(response.body)
                logging.info(f"  [DEBUG] HTML salvo em {debug_filename} para análise")
            except Exception as e:
                logging.error(f"  [DEBUG] Erro ao salvar HTML: {str(e)}")
        
        if self.results_list is not None:
            self.results_list.append(product_details)
        
        yield product_details

# Configurações básicas do Scrapy usando configuração padronizada
def get_basic_scrapy_settings():
    """Retorna configurações padronizadas anti-detecção"""
    return get_scrapy_settings()

def _run_spider_process(query, extract_images, results_queue, sort_by='relevance', condition='all', max_items=None, custom_url=None, request_delay=2.0):
    """
    Internal function to run the spider in a separate process 
    and put results into a queue.
    OTIMIZADO COM CONFIGURAÇÕES CENTRALIZADAS DE ALTA PERFORMANCE.
    
    Args:
        custom_url (str): URL específica do Mercado Livre para usar como base da busca
    """
    try:
        # On Windows, set the event loop policy to SelectorEventLoopPolicy for Twisted
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Explicitly install asyncioreactor at the beginning of the subprocess
        if 'twisted.internet.reactor' in sys.modules:
            del sys.modules['twisted.internet.reactor']
        asyncioreactor.install()

        results_container = []
        settings = get_project_settings()
        
        # ============================================================================
        # APLICAR CONFIGURAÇÕES OTIMIZADAS CENTRALIZADAS
        # ============================================================================
        
        # Obter configurações básicas do Scrapy
        optimized_settings = get_basic_scrapy_settings()
        
        # Aplicar delay configurado pelo usuário
        from ..core.shared_scraping_config import calculate_user_delay
        
        # Calcular delays baseados no parâmetro do usuário
        base_delay = calculate_user_delay(request_delay, 'request')
        page_delay = calculate_user_delay(request_delay, 'page')
        
        # Atualizar configurações com delays personalizados
        optimized_settings.update({
            'DOWNLOAD_DELAY': base_delay,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            'AUTOTHROTTLE_START_DELAY': base_delay,
            'AUTOTHROTTLE_MAX_DELAY': page_delay,
            'DOWNLOAD_TIMEOUT': 60,  # Timeout aumentado
        })
        
        # Aplicar todas as configurações de uma vez
        settings.update(optimized_settings)
        
        # Log de performance para monitoramento
        logging.info(f"Spider iniciado com configurações otimizadas:")
        logging.info(f"   CONCURRENT_REQUESTS: {settings.get('CONCURRENT_REQUESTS')}")
        logging.info(f"   CONCURRENT_REQUESTS_PER_DOMAIN: {settings.get('CONCURRENT_REQUESTS_PER_DOMAIN')}")
        logging.info(f"   DOWNLOAD_DELAY: {settings.get('DOWNLOAD_DELAY')}s (baseado em {request_delay}s)")
        logging.info(f"   AUTOTHROTTLE_MAX_DELAY: {settings.get('AUTOTHROTTLE_MAX_DELAY')}s")
        logging.info(f"   DOWNLOAD_TIMEOUT: {settings.get('DOWNLOAD_TIMEOUT')}s")
        logging.info(f"   HTTPCACHE_ENABLED: {settings.get('HTTPCACHE_ENABLED')}")
        
        process = CrawlerProcess(settings)
        
        crawler = process.create_crawler(MercadoLivreSpider)
        process.crawl(crawler, query=query, results_list=results_container, 
                      extract_images=extract_images, sort_by=sort_by, 
                      condition=condition, max_items=max_items, custom_url=custom_url)
        process.start() 
        
        result_data = {
            'results': results_container,
            'urls_used': crawler.spider.used_urls if hasattr(crawler.spider, 'used_urls') else []
        }
        results_queue.put(result_data)
    except Exception as e:
        logging.error(f"Error in Scrapy process for query '{query}': {e}", exc_info=True)
        results_queue.put({'results': [], 'urls_used': []})

def run_spider(query, extract_images=True, sort_by='relevance', condition='all', max_items=None, custom_url=None, request_delay=2.0):
    """
    Executa o spider em um processo separado e retorna os resultados via uma Queue.
    OTIMIZADO PARA ALTA PERFORMANCE.
    
    Args:
        query (str): Termo de busca ou URL customizada
        extract_images (bool): Se deve extrair imagens
        sort_by (str): Ordenação dos resultados
        condition (str): Condição dos produtos
        max_items (int): Número máximo de itens
        custom_url (str): URL específica do Mercado Livre para usar como base
        request_delay (float): Delay entre requisições em segundos
    """
    results_queue = multiprocessing.Queue()
    
    scrapy_process = multiprocessing.Process(
        target=_run_spider_process, 
        args=(query, extract_images, results_queue, sort_by, condition, max_items, custom_url, request_delay)
    )
    scrapy_process.start()
    
    try:
        # Timeout ajustado baseado no número de itens
        base_timeout = 60  # 1 minuto base
        if max_items:
            # Timeout dinâmico: 60s base + 2s por item (máximo 300s)
            dynamic_timeout = min(base_timeout + (max_items * 2), 300)
        else:
            dynamic_timeout = 180  # 3 minutos para busca sem limite
            
        result_data = results_queue.get(timeout=dynamic_timeout)
        results = result_data.get('results', [])
        urls_used = result_data.get('urls_used', [])
        
    except multiprocessing.queues.Empty:
        logging.error(f"Scrapy process timed out for query: {query}")
        results = []
        urls_used = []
    except Exception as e:
        logging.error(f"Error retrieving results from Scrapy process queue for query '{query}': {e}")
        results = []
        urls_used = []

    scrapy_process.join(timeout=10)
    if scrapy_process.is_alive():
        logging.warning(f"Scrapy process for query '{query}' did not terminate, attempting to kill.")
        scrapy_process.terminate()
        scrapy_process.join()

    return results, urls_used


# Middlewares removidos - funcionalidade integrada diretamente no spider para evitar problemas de multiprocessing

def _run_product_details_spider_process(product_url, results_queue):
    """
    Internal function to run the product details spider in a separate process 
    and put results into a queue. 
    OTIMIZADO COM CONFIGURAÇÕES CENTRALIZADAS DE ALTA PERFORMANCE.
    """
    try:
        # On Windows, set the event loop policy to SelectorEventLoopPolicy for Twisted
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Explicitly install asyncioreactor at the beginning of the subprocess
        if 'twisted.internet.reactor' in sys.modules:
            del sys.modules['twisted.internet.reactor']
        asyncioreactor.install()

        results_container = []
        settings = get_project_settings()
        
        # ============================================================================
        # APLICAR CONFIGURAÇÕES OTIMIZADAS PARA DETALHES DE PRODUTO
        # ============================================================================
        
        optimized_settings = get_basic_scrapy_settings()
        settings.update(optimized_settings)
        
        # Log de performance específico para detalhes
        logging.info(f"Product details spider iniciado com configurações otimizadas")
        logging.info(f"   CONCURRENT_REQUESTS: {settings.get('CONCURRENT_REQUESTS')}")
        logging.info(f"   DOWNLOAD_TIMEOUT: {settings.get('DOWNLOAD_TIMEOUT')}s")
        logging.info(f"   HTTPCACHE_EXPIRATION: {settings.get('HTTPCACHE_EXPIRATION_SECS')}s")
        
        process = CrawlerProcess(settings)
        
        crawler = process.create_crawler(MercadoLivreProductDetailsSpider)
        process.crawl(crawler, product_url=product_url, results_list=results_container)
        process.start() 
        
        result_data = {
            'details': results_container[0] if results_container else None,
            'success': len(results_container) > 0
        }
        results_queue.put(result_data)
    except Exception as e:
        logging.error(f"Error in product details Scrapy process for URL '{product_url}': {e}", exc_info=True)
        results_queue.put({'details': None, 'success': False})

def run_product_details_spider(product_url):
    """
    Executa o spider de detalhes do produto em um processo separado e retorna os resultados via uma Queue.
    OTIMIZADO PARA ALTA PERFORMANCE.
    
    Args:
        product_url (str): URL do produto para extrair detalhes
        
    Returns:
        dict: Dados detalhados do produto ou None se houver erro
    """
    if not product_url:
        logging.error("run_product_details_spider chamado sem product_url")
        return None
    
    results_queue = multiprocessing.Queue()
    
    scrapy_process = multiprocessing.Process(
        target=_run_product_details_spider_process, 
        args=(product_url, results_queue)
    )
    scrapy_process.start()
    
    try:
        # Timeout otimizado para produto individual
        result_data = results_queue.get(timeout=30)  # Reduzido de 60s para 30s
        details = result_data.get('details', None)
        success = result_data.get('success', False)
    except multiprocessing.queues.Empty:
        logging.error(f"Product details Scrapy process timed out for URL: {product_url}")
        details = None
        success = False
    except Exception as e:
        logging.error(f"Error retrieving product details from Scrapy process queue for URL '{product_url}': {e}")
        details = None
        success = False

    scrapy_process.join(timeout=5)  # Reduzido de 10s para 5s
    if scrapy_process.is_alive():
        logging.warning(f"Product details Scrapy process for URL '{product_url}' did not terminate, attempting to kill.")
        scrapy_process.terminate()
        scrapy_process.join()

    return details if success else None

if __name__ == "__main__":
    # Configure basic logging for testing the spider directly
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(processName)s - %(message)s')
    
    # Required for Windows if you're using multiprocessing in a __main__ block
    # and you want to be able to create new processes from the main process.
    # For other OS or if not running from __main__ directly (e.g. as a library),
    # this might not be strictly necessary or could be handled differently.
    multiprocessing.freeze_support() 

    search_term = "cartucho hp"
    print(f"Buscando por '{search_term}' com imagens, relevance, all conditions, max 10 itens...")
    resultados_com_imagens, urls_usadas_com_imagens = run_spider(search_term, extract_images=True, max_items=10)
    if resultados_com_imagens:
        print(f"Encontrados {len(resultados_com_imagens)} produtos.")
        print(f"URL usada: {urls_usadas_com_imagens[0] if urls_usadas_com_imagens else 'Nenhuma URL usada'}")
    else:
        print("Nenhum produto encontrado.")

    print(f"\nBuscando por '{search_term}' SEM imagens, price_asc, new, max 20 itens...")
    resultados_sem_imagens, urls_usadas_sem_imagens = run_spider(search_term, extract_images=False, sort_by='price_asc', condition='new', max_items=20)
    if resultados_sem_imagens:
        print(f"Encontrados {len(resultados_sem_imagens)} produtos.")
        print(f"URL usada: {urls_usadas_sem_imagens[0] if urls_usadas_sem_imagens else 'Nenhuma URL usada'}")
    else:
        print("Nenhum produto encontrado.")
        
    print(f"\nBuscando por 'tinta epson l3150' COM imagens, price_desc, used...")
    resultados_outra_busca, urls_outra_busca = run_spider("tinta epson l3150", extract_images=True, sort_by='price_desc', condition='used')
    if resultados_outra_busca:
        print(f"Encontrados {len(resultados_outra_busca)} produtos.")
        print(f"URL usada: {urls_outra_busca[0] if urls_outra_busca else 'Nenhuma URL usada'}")
    else:
        print("Nenhum produto encontrado.")

    # Testar spider de detalhes do produto
    if resultados_com_imagens:
        primeiro_produto = resultados_com_imagens[0]
        product_url = primeiro_produto.get('LINK')
        if product_url and product_url != 'N/A':
            print(f"\nTestando extração de detalhes do produto...")
            print(f"URL do produto: {product_url}")
            
            detalhes = run_product_details_spider(product_url)
            if detalhes:
                print("Detalhes extraídos com sucesso!")
                print(f"📝 Descrição: {detalhes.get('description', 'N/A')[:100]}...")
                print(f"🔧 Características principais: {len(detalhes.get('main_characteristics', {}))}")
                print(f"Outras características: {len(detalhes.get('other_characteristics', {}))}")
                
                # Mostrar algumas características como exemplo
                main_chars = detalhes.get('main_characteristics', {})
                if main_chars:
                    print("Exemplos de características principais:")
                    for i, (key, value) in enumerate(list(main_chars.items())[:3]):
                        print(f"  - {key}: {value}")
            else:
                print("Falha na extração de detalhes")

    # print("\nURLs usadas:") # Commented out as individual URLs are printed above
    # print("Com imagens:", urls_usadas_com_imagens)
    # print("Sem imagens:", urls_usadas_sem_imagens) 