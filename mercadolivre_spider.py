import scrapy
import random
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import quote_plus, quote, urlencode
import re
import threading
import multiprocessing

# Adicionar freeze_support() para Windows
if __name__ == '__main__': # Embora o spider seja importado, é uma boa prática
    multiprocessing.freeze_support()
else: # Garante que freeze_support seja chamado quando o módulo é importado por um subprocesso
    multiprocessing.freeze_support()

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
        logging.info(f"MercadoLivreSpider __init__ chamado com query: {query}, max_items: {max_items}")

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
        for i, item_container in enumerate(item_containers_to_process):
            # Check if we've reached the maximum number of items
            if self.max_items and self.items_collected >= self.max_items:
                logging.info(f"Limite de {self.max_items} itens atingido. Parando a extração.")
                return
                
            logging.info(f"--- Processando container de produto {i+1}/{len(item_containers_to_process)} (total coletado: {self.items_collected}) ---")
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
            else:
                product['LINK'] = 'N/A'
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
                    # Infer from title as last resort
                    if product.get('TITULO PRODUTO'):
                        title_words = product['TITULO PRODUTO'].split()
                        potential_brands = ["HP", "SAMSUNG", "LG", "SONY", "PHILIPS", "DELL", "LENOVO", "ACER", "ASUS", "XIAOMI", "APPLE", "MOTOROLA", "EPSON", "CANON", "BROTHER"]
                        found_brand_in_title = None
                        for word in title_words:
                            if word.upper() in potential_brands:
                                found_brand_in_title = word
                                break
                        if found_brand_in_title:
                             product['MARCA'] = found_brand_in_title
                             logging.info(f"  [MARCA] Inferida do título: '{product['MARCA']}'")
                        else:
                            product['MARCA'] = 'N/A'
                            logging.info(f"  [MARCA] Não encontrada diretamente (general/poly) nem inferida do título.")
                    else:
                        product['MARCA'] = 'N/A'
                        logging.info(f"  [MARCA] Não encontrada (título indisponível para inferência).")

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

def _run_spider_process(query, extract_images, results_queue, sort_by='relevance', condition='all', max_items=None):
    """
    Função interna para rodar o spider em um processo separado
    e colocar os resultados em uma fila.
    """
    logging.info(f"_run_spider_process iniciado para query: {query}, max_items: {max_items}")
    results_container = [] # Inicializa o container de resultados
    used_urls_container = [] # Inicializa o container de URLs usadas
    try:
        settings = get_project_settings()
        # Configurações padrão para o spider
        settings.set('TWISTED_REACTOR', 'twisted.internet.asyncioreactor.AsyncioSelectorReactor')
        settings.set('REQUEST_FINGERPRINTER_IMPLEMENTATION', '2.7')
        settings.set('TELNETCONSOLE_ENABLED', False) # Desabilitar console Telnet
        settings.set('LOG_LEVEL', 'INFO') # Nível de log INFO ou DEBUG
        # settings.set('ROBOTSTXT_OBEY', False) # Considerar se necessário
        # settings.set('DOWNLOAD_DELAY', random.uniform(0.5, 1.5)) # Delay entre requisições
        # settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', 8) # Requisições concorrentes

        process = CrawlerProcess(settings)
        
        # Passa results_list (que é o results_container aqui) e used_urls_list
        crawler = process.create_crawler(MercadoLivreSpider)
        process.crawl(crawler, 
                      query=query, 
                      results_list=results_container, 
                      extract_images=extract_images,
                      sort_by=sort_by,
                      condition=condition,
                      max_items=max_items)
        
        logging.info(f"Iniciando o processo Scrapy para query: {query}")
        process.start()  # Bloqueia até que o crawling termine
        logging.info(f"Processo Scrapy para query: {query} finalizado.")
        
        # Após process.start() retornar, o results_container deve estar populado pelo spider
        # O spider também deve ter populado used_urls_container se tivermos passado uma lista para ele
        # Vamos assumir que o spider anexa as URLs usadas à lista passada no construtor.
        # Para obter as URLs usadas, precisamos que o spider as adicione a uma lista.
        # O crawler.spider.used_urls pode ser acessado aqui se a instância do spider for mantida.
        # No entanto, é mais simples se o próprio spider preencher a lista `used_urls_container`.
        # Vamos assumir que o spider_instance.used_urls contém as URLs.

        # Verifica se o crawler e o spider existem antes de tentar acessá-los
        spider_instance = crawler.spider if crawler else None
        if spider_instance and hasattr(spider_instance, 'used_urls'):
            used_urls_container = spider_instance.used_urls
            logging.info(f"URLs usadas recuperadas do spider: {len(used_urls_container)}")
        else:
            logging.warning("Não foi possível recuperar used_urls da instância do spider.")
            
        results_queue.put((results_container, used_urls_container))

    except Exception as e:
        logging.error(f"Erro crítico no processo Scrapy para query \'{query}\': {e}", exc_info=True)
        results_queue.put(([], [])) # Envia tupla vazia em caso de erro

def run_spider(query, extract_images=True, sort_by='relevance', condition='all', max_items=None):
    """
    Executa o spider em um processo separado e retorna os resultados e URLs usadas.
    """
    logging.info(f"run_spider chamado com query: {query}, max_items: {max_items}")

    if not query:
        logging.error("Tentativa de rodar spider sem query.")
        return [], []

    results_queue = multiprocessing.Queue()
    
    scrapy_process = multiprocessing.Process(
        target=_run_spider_process, 
        args=(query, extract_images, results_queue, sort_by, condition, max_items)
    )
    
    logging.info(f"Iniciando processo multiprocessing para Scrapy (query: {query})")
    scrapy_process.start()
    
    results = []
    used_urls = []
    try:
        # Aumentar o timeout, pois o Scrapy pode levar tempo
        # O valor ideal de timeout depende da complexidade da busca e número de itens
        timeout_seconds = 240 # 4 minutos, ajuste conforme necessário
        logging.info(f"Aguardando resultados do processo Scrapy por até {timeout_seconds} segundos (query: {query})")
        
        # Espera que a fila retorne uma tupla (results_list, used_urls_list)
        queue_output = results_queue.get(timeout=timeout_seconds) 
        if isinstance(queue_output, tuple) and len(queue_output) == 2:
            results, used_urls = queue_output
            logging.info(f"Processo Scrapy para query \'{query}\' retornou {len(results)} resultados e {len(used_urls)} URLs usadas.")
        else:
            logging.error(f"Saída inesperada da fila do Scrapy para query \'{query}\': {type(queue_output)}. Esperava uma tupla de (list, list).")
            results = [] # Garante que seja uma lista
            used_urls = []
            
    except multiprocessing.queues.Empty: # Nome correto da exceção é queues.Empty
        logging.error(f"Processo Scrapy para query \'{query}\' timed out após {timeout_seconds} segundos.")
        results = [] # Garante que seja uma lista
        used_urls = []
    except Exception as e:
        logging.error(f"Erro ao obter resultados da fila do Scrapy para query \'{query}\': {e}", exc_info=True)
        results = [] # Garante que seja uma lista
        used_urls = []

    finally:
        # Garante que o processo seja finalizado
        if scrapy_process.is_alive():
            logging.warning(f"Processo Scrapy para query \'{query}\' ainda está vivo após obter resultados ou timeout. Tentando terminar...")
            scrapy_process.terminate() # Tenta terminar de forma mais abrupta
            scrapy_process.join(timeout=10) # Espera um pouco para terminar
            if scrapy_process.is_alive():
                logging.error(f"Processo Scrapy para query \'{query}\' não pôde ser terminado. Pode haver recursos presos.")
        else:
            logging.info(f"Processo Scrapy para query \'{query}\' terminou corretamente.")

    return results, used_urls

# Bloco de teste para rodar o spider diretamente (opcional)
if __name__ == '__main__':
    # Configuração de logging para teste direto
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
    
    # multiprocessing.freeze_support() # Já chamado no início do arquivo

    # Exemplo de como chamar a função run_spider
    test_query = "placa de video rtx 3060"
    max_test_items = 10 # Para um teste rápido
    
    print(f"Iniciando teste direto do spider para query: '{test_query}' com max_items={max_test_items}")
    
    # Chamar run_spider como seria chamado pela aplicação Flask
    # A função _run_spider_process não deve ser chamada diretamente aqui para teste, 
    # pois ela espera uma Queue.
    produtos_encontrados, urls_coletadas = run_spider(
        query=test_query, 
        extract_images=False, # Desabilitar imagens para teste rápido
        sort_by='relevance', 
        condition='all',
        max_items=max_test_items
    )
    
    print(f"\n--- Resultados do Teste Direto do Spider ---")
    print(f"Query: {test_query}")
    print(f"Total de produtos encontrados: {len(produtos_encontrados)}")
    print(f"Total de URLs usadas: {len(urls_coletadas)}")
    if urls_coletadas:
        print("Primeira URL usada:", urls_coletadas[0])

    if produtos_encontrados:
        print("\nPrimeiros produtos encontrados:")
        for i, produto in enumerate(produtos_encontrados[:5]): # Mostra os primeiros 5
            print(f"  Produto {i+1}:")
            print(f"    Título: {produto.get('TITULO PRODUTO', 'N/A')}")
            print(f"    Preço: {produto.get('PREÇO', 'N/A')}")
            print(f"    Link: {produto.get('LINK', 'N/A')}")
    else:
        print("Nenhum produto encontrado no teste.")

    print("\n--- Fim do Teste Direto do Spider ---") 