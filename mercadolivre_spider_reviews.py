import scrapy
import logging
import random
import re
import json
import multiprocessing
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from urllib.parse import urlparse, parse_qs

# Lista de User Agents para simular diferentes navegadores
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
]

class ReviewItem(scrapy.Item):
    rating = scrapy.Field()
    date = scrapy.Field()
    comment = scrapy.Field()
    helpful_count = scrapy.Field()
    source_url = scrapy.Field()

class MercadoLivreReviewsSpider(scrapy.Spider):
    name = 'mercadolivre_reviews'
    
    # Nova URL da API descoberta pelo usuário - formato direto
    API_REVIEWS_URL_TEMPLATE = "https://www.mercadolivre.com.br/noindex/catalog/reviews/{object_id}/search?objectId={object_id}&siteId=MLB&isItem=false&order=relevance&offset={offset}&limit={limit}&x-is-webview=false&controlled=true"
    
    # Limite máximo de reviews por requisição (definido pela API)
    REVIEWS_PER_PAGE = 30
    
    # Offset máximo permitido pela API
    MAX_OFFSET = 200
    
    # Limite de reviews a buscar
    MAX_REVIEWS_TO_FETCH = 500

    def __init__(self, review_url=None, results_list=None, *args, **kwargs):
        super(MercadoLivreReviewsSpider, self).__init__(*args, **kwargs)
        if not review_url:
            raise ValueError("A URL de reviews deve ser fornecida para o MercadoLivreReviewsSpider.")
        
        self.input_review_url = review_url
        self.results_list = results_list if results_list is not None else []
        self.reviews_fetched_count = 0
        
        self.object_id = self._extract_object_id(review_url)
        if not self.object_id:
            raise ValueError(f"Não foi possível extrair o object_id da URL: {review_url}")

        logging.info(f"Spider de reviews inicializado para URL: {review_url}, ObjectID: {self.object_id}")

    def _extract_object_id(self, url):
        # Prioridade 1: Padrão /reviews/MLBXXXXX
        match = re.search(r'/reviews/(MLB\d+)', url)
        if match:
            return match.group(1)
        
        # Prioridade 2: Padrão /p/MLBXXXXXX (de páginas de produto)
        match_product_page = re.search(r'/p/(MLB\d+)', url)
        if match_product_page:
            return match_product_page.group(1)
            
        # Prioridade 3: URLa da API que o usuário descobriu
        match_api = re.search(r'objectId=(MLB\d+)', url)
        if match_api:
            return match_api.group(1)
            
        # Fallback para URLs de produto mais antigas /MLBXXXXX-nome-produto
        match_old_product = re.search(r'/(MLB\d+)[^\d]', url) 
        if match_old_product:
            return match_old_product.group(1)
            
        # Fallback para objectId no query param (caso a URL seja a da API diretamente)
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'objectId' in query_params and query_params['objectId'][0].startswith('MLB'):
            return query_params['objectId'][0]
            
        logging.warning(f"Não foi possível extrair um object_id padrão (MLBxxxx) da URL: {url}. Verifique o formato.")
        return None

    def _get_api_headers(self):
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': f'https://www.mercadolivre.com.br/noindex/catalog/reviews/{self.object_id}?noIndex=true&access=view_all&modal=false&controlled=true',
            'X-Requested-With': 'XMLHttpRequest',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-client-name': 'desktop',
            'x-client-version': '0.5',
            'x-meli-trace-site': 'MLB',
        }

    def start_requests(self):
        if not self.object_id:
            logging.error("ObjectID não encontrado, não é possível iniciar as requisições de reviews.")
            return

        # Iniciar com a primeira página de reviews via API
        first_api_url = self.API_REVIEWS_URL_TEMPLATE.format(
            object_id=self.object_id,
            offset=0,
            limit=self.REVIEWS_PER_PAGE
        )
        
        logging.info(f"Iniciando busca de reviews pela API direta: {first_api_url}")
        yield scrapy.Request(
            url=first_api_url,
            callback=self.parse_api_direct,
            errback=self.handle_error,
            headers=self._get_api_headers(),
            meta={'current_offset': 0}
        )

    def handle_error(self, failure):
        logging.error(f"Falha ao buscar ou processar reviews via API {failure.request.url}: {failure.value}. Tentando fallback para HTML se aplicável.")
        
        # Se a primeira chamada da API falhar, tentar com o método HTML
        current_offset = failure.request.meta.get('current_offset', -1)
        if current_offset == 0 and hasattr(self, 'input_review_url') and '.mercadolivre.com.br/' in self.input_review_url:
            logging.info(f"Primeira chamada da API falhou. Tentando fallback para parsing HTML da URL original: {self.input_review_url}")
            yield scrapy.Request(
                url=self.input_review_url,
                callback=self.parse_html_reviews,
                errback=self.handle_html_fallback_error,
                headers={'User-Agent': random.choice(USER_AGENTS)}
            )
    
    def handle_html_fallback_error(self, failure):
        logging.error(f"Falha também no fallback para HTML da URL {failure.request.url}: {failure.value}")

    def parse_api_direct(self, response):
        """
        Parser para a API direta que retorna JSON com reviews.
        Esta é a API descoberta pelo usuário que retorna até 30 reviews por vez.
        """
        current_offset = response.meta.get('current_offset', 0)
        logging.info(f"Processando resposta da API direta para offset {current_offset}: {response.url} (Status: {response.status})")

        if response.status != 200:
            logging.error(f"API retornou status não-200 ({response.status}) para {response.url}. Conteúdo: {response.text[:200]}")
            if current_offset == 0:
                # Se for a primeira requisição que falhou, tentar o fallback para HTML
                if hasattr(self, 'input_review_url') and '.mercadolivre.com.br/' in self.input_review_url:
                    logging.info(f"Primeira chamada da API direta falhou. Tentando fallback para parsing HTML: {self.input_review_url}")
                    yield scrapy.Request(
                        url=self.input_review_url,
                        callback=self.parse_html_reviews,
                        errback=self.handle_html_fallback_error,
                        headers={'User-Agent': random.choice(USER_AGENTS)}
                    )
            return

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            logging.error(f"Falha ao decodificar JSON da API direta: {response.url}. Conteúdo: {response.text[:200]}")
            if current_offset == 0:
                # Se for a primeira requisição que falhou, tentar o fallback para HTML
                if hasattr(self, 'input_review_url') and '.mercadolivre.com.br/' in self.input_review_url:
                    logging.info(f"Primeira chamada da API direta falhou ao decodificar JSON. Tentando fallback para HTML.")
                    yield scrapy.Request(
                        url=self.input_review_url,
                        callback=self.parse_html_reviews,
                        errback=self.handle_html_fallback_error,
                        headers={'User-Agent': random.choice(USER_AGENTS)}
                    )
            return

        # Extrair a lista de reviews do JSON
        reviews_list = data.get('reviews', [])
        if not reviews_list:
            logging.info(f"Nenhuma review encontrada na resposta da API direta para offset {current_offset}.")
            return
        
        logging.info(f"Encontradas {len(reviews_list)} reviews na resposta da API direta para offset {current_offset}.")
        
        # Processar cada review
        for review in reviews_list:
            if self.reviews_fetched_count >= self.MAX_REVIEWS_TO_FETCH:
                logging.info(f"Limite máximo de {self.MAX_REVIEWS_TO_FETCH} reviews atingido.")
                return
            
            # Extrair os campos relevantes do JSON
            review_item = {}
            review_item['ESTRELAS'] = review.get('rating', 0)
            
            # Extrair a data da avaliação
            comment = review.get('comment', {})
            date = comment.get('date', 'N/A')
            review_item['DATA'] = date
            
            # Extrair o texto do comentário
            content = comment.get('content', {})
            text = content.get('text', 'N/A') if isinstance(content, dict) else 'N/A'
            review_item['COMENTARIO'] = text
            
            # Extrair as curtidas
            actions = review.get('actions', [])
            likes = 0
            for action in actions:
                if action.get('id') == 'LIKE':
                    likes = action.get('value', 0)
                    break
            review_item['CURTIDAS'] = str(likes)
            
            # Adicionar à lista de resultados e incrementar o contador
            self.results_list.append(review_item)
            self.reviews_fetched_count += 1
            yield review_item

        # Verificar se devemos continuar com a próxima página
        # Limitado pelo offset máximo permitido pela API do Mercado Livre (200)
        next_offset = current_offset + self.REVIEWS_PER_PAGE
        if next_offset <= self.MAX_OFFSET and len(reviews_list) >= self.REVIEWS_PER_PAGE and self.reviews_fetched_count < self.MAX_REVIEWS_TO_FETCH:
            next_api_url = self.API_REVIEWS_URL_TEMPLATE.format(
                object_id=self.object_id,
                offset=next_offset,
                limit=self.REVIEWS_PER_PAGE
            )
            logging.info(f"Buscando próxima página de reviews da API direta: {next_api_url}")
            yield scrapy.Request(
                url=next_api_url,
                callback=self.parse_api_direct,
                errback=self.handle_error,
                headers=self._get_api_headers(),
                meta={'current_offset': next_offset}
            )
        else:
            logging.info(f"Fim da paginação (offset={current_offset+self.REVIEWS_PER_PAGE} > {self.MAX_OFFSET}) ou todas as reviews já obtidas. Total: {self.reviews_fetched_count}")

    def parse_html_reviews(self, response):
        """
        Método de fallback para extrair reviews do HTML caso a API falhe.
        """
        logging.info(f"Processando reviews via HTML fallback: {response.url} (Status: {response.status})")
        if response.status != 200:
            logging.error(f"HTML fallback falhou ao carregar página {response.url} com status {response.status}")
            return

        review_cards = response.css('div.ui-review-capability-comments > div > article.ui-review-capability-comments__comment')
        if not review_cards:
            review_cards = response.xpath("//article[contains(@class, 'ui-review-capability-comments__comment')]")
            if review_cards: logging.info(f"Encontrados {len(review_cards)} cards de review usando XPath (HTML fallback).")
            else:
                logging.warning(f"Nenhum card de review encontrado (HTML fallback): {response.url}.")
                return

        for i, card in enumerate(review_cards):
            if self.reviews_fetched_count >= self.MAX_REVIEWS_TO_FETCH:
                logging.info(f"Limite máximo de {self.MAX_REVIEWS_TO_FETCH} reviews atingido (HTML fallback).")
                return
            review_item = {}
            star_elements = card.css('div.ui-review-capability-comments__comment__header div div svg.ui-review-capability-comments__comment__rating__star')
            filled_stars = sum(1 for star in star_elements if not star.css('.ui-review-capability-comments__comment__rating__star-empty'))
            review_item['ESTRELAS'] = filled_stars
            date_text = card.css('div.ui-review-capability-comments__comment__header > div > span::text').get()
            review_item['DATA'] = date_text.strip() if date_text else 'N/A'
            comment_text = card.css('p.ui-review-capability-comments__comment__text::text').get()
            if not comment_text: comment_text = card.css('article > p::text').get()
            review_item['COMENTARIO'] = comment_text.strip() if comment_text else 'N/A'
            helpful_button = card.css('div.ui-review-capability-comments__comment__footer button[aria-label*="acharam útil"], div.ui-review-capability-comments__comment__footer button[aria-label*="achou útil"]')
            likes_count = '0'
            if helpful_button:
                aria_label = helpful_button.attrib.get('aria-label', '')
                match = re.search(r'(\d+)', aria_label)
                if match: likes_count = match.group(1)
            review_item['CURTIDAS'] = likes_count
            self.results_list.append(review_item)
            self.reviews_fetched_count += 1
            yield review_item
        logging.info(f"HTML fallback parsing concluído para {response.url}. Total de reviews até agora: {self.reviews_fetched_count}")

def _run_spider_reviews_process(review_url, results_queue):
    """
    Função interna para rodar o spider de reviews em um processo separado
    e colocar os resultados em uma fila.
    """
    try:
        results_container = []
    settings = get_project_settings()
    settings.set('TWISTED_REACTOR', 'twisted.internet.asyncioreactor.AsyncioSelectorReactor')
    settings.set('REQUEST_FINGERPRINTER_IMPLEMENTATION', '2.7')
        settings.set('TELNETCONSOLE_ENABLED', False)
        settings.set('LOG_LEVEL', 'INFO')  

    process = CrawlerProcess(settings)
        crawler = process.create_crawler(MercadoLivreReviewsSpider)
        process.crawl(crawler, review_url=review_url, results_list=results_container)
        process.start()
        results_queue.put(results_container)
    except Exception as e:
        logging.error(f"Erro no processo Scrapy para reviews da URL '{review_url}': {e}", exc_info=True)
        results_queue.put([])

def run_spider_reviews(review_url: str):
    """
    Executa o spider de reviews em um processo separado e retorna os resultados.
    """
    if not review_url or not ("mercadolivre.com.br/" in review_url or "mercadolibre.com/" in review_url) : # Checagem básica de URL
        logging.error(f"URL de review inválida ou não é do Mercado Livre: {review_url}")
        return []

    results_queue = multiprocessing.Queue()
    
    scrapy_process = multiprocessing.Process(
        target=_run_spider_reviews_process, 
        args=(review_url, results_queue)
    )
    
    logging.info(f"Iniciando processo Scrapy para reviews da URL: {review_url}")
    scrapy_process.start()
    
    try:
        results = results_queue.get(timeout=240) # Timeout aumentado para 4 minutos
        logging.info(f"Processo Scrapy para reviews da URL {review_url} retornou {len(results)} resultados.")
    except multiprocessing.queues.Empty:
        logging.error(f"Processo Scrapy para reviews da URL {review_url} timed out.")
        results = []
    except Exception as e:
        logging.error(f"Erro ao obter resultados da fila do Scrapy para reviews da URL '{review_url}': {e}")
        results = []

    scrapy_process.join(timeout=20)
    if scrapy_process.is_alive():
        logging.warning(f"Processo Scrapy para reviews da URL '{review_url}' não terminou, tentando forçar.")
        scrapy_process.terminate()
        scrapy_process.join()

    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    multiprocessing.freeze_support()

    # Teste com a API direta descoberta pelo usuário
    test_api_url = "https://www.mercadolivre.com.br/noindex/catalog/reviews/MLB36751072/search?objectId=MLB36751072&siteId=MLB&isItem=false&rating=2&order=relevance&offset=0&limit=30&x-is-webview=false&controlled=true"
    
    print(f"Buscando reviews usando a API direta: {test_api_url}")
    
    results = run_spider_reviews(test_api_url)
    print(f"Encontrados {len(results)} reviews.")
    for i, review in enumerate(results[:10], 1): # Mostra até 10 reviews
        print(f"Review {i}: Estrelas: {review.get('ESTRELAS', 'N/A')}, Data: {review.get('DATA', 'N/A')}, Curtidas: {review.get('CURTIDAS', 'N/A')}, Comentário: '{review.get('COMENTARIO', 'N/A')[:50]}...'")
