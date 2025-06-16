import scrapy
import random
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import quote_plus, quote, urlencode
import re
import threading
import multiprocessing
import sys
from twisted.internet import asyncioreactor
import asyncio  # for setting Windows selector event loop policy

# Mesma lista de User Agents do arquivo original
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

class MercadoLivreSpider(scrapy.Spider):
    name = 'mercadolivre'
    STEP = 50 
    
    def __init__(self, query=None, results_list=None, extract_images=True, 
                 sort_by='relevance', condition='all', max_items=None, *args, **kwargs):
        super(MercadoLivreSpider, self).__init__(*args, **kwargs)
        self.query = query
        self.results_list = results_list
        self.extract_images = extract_images
        self.sort_by = sort_by
        self.condition = condition
        self.max_items = int(max_items) if max_items else 0  # 0 unlimited  # Default to 50 if not specified
        self.used_urls = [] # Track URLs that were actually used
        self.html_saved_for_debug = False # Flag to save HTML only once
        self.items_collected = 0  # Counter for collected items

        if not query:
            raise ValueError("A search query must be provided to the MercadoLivreSpider.")

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
        if not self.query:
            logging.error("Spider started without a query.")
            return
        
        # We now have a single start_urls[0] constructed in __init__
        if self.start_urls:
            url_to_try = self.start_urls[0]
            logging.info(f"Attempting to scrape URL: {url_to_try}")
            yield scrapy.Request(
                url=url_to_try,
                callback=self.parse,
                errback=self.handle_error, # Keep general error handling for this single request
                headers={'User-Agent': random.choice(USER_AGENTS)},
                meta={'page_number': 1} # Track page number for logging
            )
        else:
            logging.error(f"No start URL generated for query: {self.query}")

    def handle_error(self, failure):
        logging.error(f"Failed to fetch or process {failure.request.url}: {failure.value}")
        # Since we moved to a single, precisely constructed URL,
        # we won't automatically try other base URLs here.
        # The spider will simply finish if this request fails.
        # If self.results_list is not None and not self.results_list: # Original condition
        #     pass
        # Consider if any specific action is needed on error, e.g. returning empty results if a queue is used

    def parse(self, response):
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

        product_container_selector_poly = '.ui-search-layout__item .andes-card.poly-card'
        product_container_selector_poly_fallback = 'div.andes-card.poly-card'
        product_container_selector_general = '.ui-search-layout__item'

        products_poly = response.css(product_container_selector_poly)
        if not products_poly:
            products_poly = response.css(product_container_selector_poly_fallback)
            if products_poly:
                logging.info(f"Encontrados {len(products_poly)} produtos com seletor CSS alternativo (poly-card direto): {product_container_selector_poly_fallback}")
        
        if not products_poly:
            products_general = response.css(product_container_selector_general)
            if products_general:
                logging.info(f"Encontrados {len(products_general)} produtos com seletor CSS geral: {product_container_selector_general}")
                products_poly = products_general
            else:
                logging.warning(f"Nenhum container de produto encontrado com seletores poly-card ou geral na URL: {response.url}")
                return # If no products found after all attempts (CSS, XPath), then return
        
        item_containers_to_process = products_poly if products_poly else []

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
            
            # General selectors (from user-provided HTML and common structures)
            title_element = item_container.css('h2.ui-search-item__title::text').get() or \
                            item_container.css('.ui-search-item__title::text').get() or \
                            item_container.css('.ui-search-item__title span::text').get() or \
                            item_container.css('span.ui-search-item__title::text').get() # For titles wrapped in span directly
            
            # Poly-card specific title fallback
            if not title_element:
                title_element = item_container.css('h3.poly-component__title-wrapper a.poly-component__title::text').get()

            link_element = item_container.css('a.ui-search-item__group__element::attr(href)').get() or \
                           item_container.css('a.ui-search-link::attr(href)').get() # Image link can also be a product link sometimes
            
            # Poly-card specific link fallback
            if not link_element:
                link_element = item_container.css('h3.poly-component__title-wrapper a.poly-component__title::attr(href)').get()

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
                match_id = re.search(r'/p/([^#?]+)', product['LINK'])
                if match_id:
                    product['ID_PRODUTO'] = match_id.group(1)
                    logging.info(f"  [ID PRODUTO] Encontrado: '{product['ID_PRODUTO']}'")
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
            
            # Extrair Características Principais
            main_chars_table_selector = '#highlighted_specs_attrs > div.ui-pdp-container__row.ui-pdp-container__row--technical-specifications > div > div > div > div:nth-child(1) > div > table > tbody'
            main_chars_rows = response.css(main_chars_table_selector + ' tr')
            
            if main_chars_rows:
                logging.info(f"  [CARACTERÍSTICAS PRINCIPAIS] Encontradas {len(main_chars_rows)} características")
                for i, row in enumerate(main_chars_rows):
                    # Múltiplos seletores para nome da característica
                    char_name = (row.css('th div::text').get() or 
                                row.css('th::text').get() or
                                row.css('th span::text').get() or
                                row.css('.andes-table__header--left div::text').get())
                    
                    # Múltiplos seletores para valor da característica  
                    char_value = (row.css('td div::text').get() or 
                                 row.css('td::text').get() or
                                 row.css('td span::text').get() or
                                 row.css('.andes-table__column--value div::text').get() or
                                 row.css('.andes-table__column--value span::text').get())
                    
                    if char_name and char_value:
                        product_details['main_characteristics'][char_name.strip()] = char_value.strip()
                        logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                    else:
                        logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
            else:
                logging.warning("  [CARACTERÍSTICAS PRINCIPAIS] Tabela não encontrada")
            
            # Extrair Outras Características
            other_chars_table_selector = '#highlighted_specs_attrs > div.ui-pdp-container__row.ui-pdp-container__row--technical-specifications > div > div > div > div:nth-child(2) > div > table > tbody'
            other_chars_rows = response.css(other_chars_table_selector + ' tr')
            
            if other_chars_rows:
                logging.info(f"  [OUTRAS CARACTERÍSTICAS] Encontradas {len(other_chars_rows)} características")
                for i, row in enumerate(other_chars_rows):
                    # Múltiplos seletores para nome da característica
                    char_name = (row.css('th div::text').get() or 
                                row.css('th::text').get() or
                                row.css('th span::text').get() or
                                row.css('.andes-table__header--left div::text').get())
                    
                    # Múltiplos seletores para valor da característica
                    char_value = (row.css('td div::text').get() or 
                                 row.css('td::text').get() or
                                 row.css('td span::text').get() or
                                 row.css('.andes-table__column--value div::text').get() or
                                 row.css('.andes-table__column--value span::text').get())
                    
                    if char_name and char_value:
                        product_details['other_characteristics'][char_name.strip()] = char_value.strip()
                        logging.info(f"    - {char_name.strip()}: {char_value.strip()}")
                    else:
                        logging.warning(f"    - Row {i+1}: char_name='{char_name}', char_value='{char_value}' (skipped)")
            else:
                logging.warning("  [OUTRAS CARACTERÍSTICAS] Tabela não encontrada")
            
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

def _run_spider_process(query, extract_images, results_queue, sort_by='relevance', condition='all', max_items=None):
    """
    Internal function to run the spider in a separate process 
    and put results into a queue.
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
        # No longer setting TWISTED_REACTOR here as it's manually installed
        settings.set('REQUEST_FINGERPRINTER_IMPLEMENTATION', '2.7')
        settings.set('TELNETCONSOLE_ENABLED', False)
        settings.set('LOG_ENABLED', True)
        settings.set('LOG_LEVEL', 'INFO')
        
        process = CrawlerProcess(settings)
        
        crawler = process.create_crawler(MercadoLivreSpider)
        process.crawl(crawler, query=query, results_list=results_container, 
                      extract_images=extract_images, sort_by=sort_by, 
                      condition=condition, max_items=max_items)
        process.start() 
        
        result_data = {
            'results': results_container,
            'urls_used': crawler.spider.used_urls if hasattr(crawler.spider, 'used_urls') else []
        }
        results_queue.put(result_data)
    except Exception as e:
        logging.error(f"Error in Scrapy process for query '{query}': {e}", exc_info=True)
        results_queue.put({'results': [], 'urls_used': []})

def run_spider(query, extract_images=True, sort_by='relevance', condition='all', max_items=None):
    """
    Executa o spider em um processo separado e retorna os resultados via uma Queue.
    """
    results_queue = multiprocessing.Queue()
    
    scrapy_process = multiprocessing.Process(
        target=_run_spider_process, 
        args=(query, extract_images, results_queue, sort_by, condition, max_items)
    )
    scrapy_process.start()
    
    try:
        result_data = results_queue.get(timeout=180)  # Increased timeout to 3 minutes for processing more items
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

def _run_product_details_spider_process(product_url, results_queue):
    """
    Internal function to run the product details spider in a separate process 
    and put results into a queue.
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
        settings.set('REQUEST_FINGERPRINTER_IMPLEMENTATION', '2.7')
        settings.set('TELNETCONSOLE_ENABLED', False)
        settings.set('LOG_ENABLED', True)
        settings.set('LOG_LEVEL', 'INFO')
        
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
        result_data = results_queue.get(timeout=60)  # 1 minute timeout for product details
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

    scrapy_process.join(timeout=10)
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
            print(f"\n🔍 Testando extração de detalhes do produto...")
            print(f"URL do produto: {product_url}")
            
            detalhes = run_product_details_spider(product_url)
            if detalhes:
                print("✅ Detalhes extraídos com sucesso!")
                print(f"📝 Descrição: {detalhes.get('description', 'N/A')[:100]}...")
                print(f"🔧 Características principais: {len(detalhes.get('main_characteristics', {}))}")
                print(f"📋 Outras características: {len(detalhes.get('other_characteristics', {}))}")
                
                # Mostrar algumas características como exemplo
                main_chars = detalhes.get('main_characteristics', {})
                if main_chars:
                    print("📊 Exemplos de características principais:")
                    for i, (key, value) in enumerate(list(main_chars.items())[:3]):
                        print(f"  - {key}: {value}")
            else:
                print("❌ Falha na extração de detalhes")

    # print("\nURLs usadas:") # Commented out as individual URLs are printed above
    # print("Com imagens:", urls_usadas_com_imagens)
    # print("Sem imagens:", urls_usadas_sem_imagens) 