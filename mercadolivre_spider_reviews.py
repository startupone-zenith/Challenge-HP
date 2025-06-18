import requests
import logging
import re
import json
import time
import random
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# USER_AGENTS list for API requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
]

class MercadoLivreReviewsAPI:
    """
    Cliente otimizado para API de Reviews do Mercado Livre
    OTIMIZADO PARA ALTA PERFORMANCE com requisições concorrentes e cache
    """
    
    def __init__(self, product_id):
        self.product_id = product_id
        self.base_url = "https://api.mercadolibre.com"
        self.max_limit = 30  # Máximo por requisição da API (baseado na API real)
        self.max_offset = 200  # Limite máximo de offset da API (baseado na API real)
        
        # ============================================================================
        # CONFIGURAÇÃO DE SESSÃO HTTP OTIMIZADA
        # ============================================================================
        
        # Criar sessão HTTP com pool de conexões otimizado
        self.session = requests.Session()
        
        # Configurar retry strategy otimizada
        retry_strategy = Retry(
            total=3,  # Máximo 3 tentativas
            backoff_factor=0.5,  # Backoff exponencial mais agressivo
            status_forcelist=[429, 500, 502, 503, 504],  # Códigos para retry
            allowed_methods=["GET"]  # Apenas GET requests
        )
        
        # Configurar adaptador HTTP com pool de conexões
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,  # Pool de conexões maior
            pool_maxsize=50,      # Máximo de conexões por pool
            pool_block=False      # Não bloquear quando pool estiver cheio
        )
        
        # Montar adaptadores para HTTP e HTTPS
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers otimizados para performance
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # Cache local para evitar requisições duplicadas
        self._cache = {}
        self._cache_ttl = 300  # 5 minutos de cache

    def get_reviews(self, limit=15, offset=0, rating_filter=None):
        """
        Busca reviews da API com otimizações de performance
        """
        # Gerar chave de cache
        cache_key = f"{self.product_id}_{limit}_{offset}_{rating_filter}"
        
        # Verificar cache local
        if cache_key in self._cache:
            cache_data = self._cache[cache_key]
            if time.time() - cache_data['timestamp'] < self._cache_ttl:
                logging.debug(f"Cache hit para {cache_key}")
                return cache_data['data']
        
        # Construir URL da API (baseado na estrutura real do ML)
        url = f"https://www.mercadolivre.com.br/noindex/catalog/reviews/{self.product_id}/search"
        
        # Parâmetros otimizados baseados na API real
        params = {
            'objectId': self.product_id,
            'siteId': 'MLB',
            'isItem': 'false',
            'limit': min(limit, 30),  # Limite máximo observado: 30
            'offset': offset,
            'x-is-webview': 'false',
            'controlled': 'true'
        }
        
        if rating_filter:
            params['rating'] = rating_filter
        
        try:
            # Requisição HTTP com timeout otimizado
            response = self.session.get(
                url, 
                params=params, 
                timeout=(5, 15)  # (connect_timeout, read_timeout)
            )
            
            if response.status_code == 200:
                api_data = response.json()
                
                # Log da estrutura de resposta
                reviews_count = len(api_data.get('reviews', [])) if api_data else 0
                logging.debug(f"✅ API retornou {reviews_count} reviews para produto {self.product_id}")
                
                # Salvar no cache local
                self._cache[cache_key] = {
                    'data': api_data,
                    'timestamp': time.time()
                }
                
                return api_data
            else:
                logging.warning(f"❌ API retornou status {response.status_code} para produto {self.product_id}")
                logging.warning(f"Resposta: {response.text[:500]}...")
                return None
                
        except requests.exceptions.Timeout:
            logging.error(f"Timeout na requisição para produto {self.product_id} (offset: {offset})")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição para produto {self.product_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Erro ao decodificar JSON para produto {self.product_id}: {e}")
            return None

    def parse_reviews_data(self, api_data):
        """
        Processa dados da API de forma otimizada
        """
        if not api_data or 'reviews' not in api_data:
            return None
        
        processed_reviews = []
        
        for review_data in api_data.get('reviews', []):
            try:
                # Extrair dados baseado na estrutura real da API do ML
                title_text = ''
                if review_data.get('title') and isinstance(review_data['title'], dict):
                    title_text = review_data['title'].get('text', '').strip()
                
                comment_text = ''
                comment_date = ''
                if review_data.get('comment'):
                    comment = review_data['comment']
                    if comment.get('content') and isinstance(comment['content'], dict):
                        comment_text = comment['content'].get('text', '').strip()
                    comment_date = comment.get('date', '')
                
                # Contagem de "útil"
                helpful_count = 0
                if review_data.get('actions'):
                    for action in review_data['actions']:
                        if action.get('type') == 'LIKE':
                            helpful_count = action.get('value', 0)
                            break
                
                # Processar review individual
                processed_review = {
                    'id': review_data.get('id', ''),
                    'rating': str(review_data.get('rating', 0)),
                    'title': title_text,
                    'text': comment_text,
                    'date': self._format_date(comment_date),
                    'helpful_count': str(helpful_count),
                    'reviewer_id': '',  # Não disponível na nova API
                    'status': review_data.get('type', '')
                }
                
                # Validar review (menos restritivo - aceitar reviews mesmo sem texto)
                if processed_review['rating'] and str(processed_review['rating']) != '0':
                    processed_reviews.append(processed_review)
                    
            except Exception as e:
                logging.warning(f"Erro ao processar review individual: {e}")
                continue
        
        return {
            'reviews': processed_reviews,
            'total_reviews_count': api_data.get('paging', {}).get('total', len(processed_reviews)),
            'has_more': len(processed_reviews) == self.max_limit
        }

    def _format_date(self, date_str):
        """
        Formata data de forma otimizada
        """
        if not date_str:
            return 'N/A'
        
        try:
            # Formato esperado: 2023-12-15T10:30:00.000-03:00
            if 'T' in date_str:
                date_part = date_str.split('T')[0]
                return date_part
            return date_str[:10] if len(date_str) >= 10 else date_str
        except Exception:
            return 'N/A'

    def get_all_reviews(self, max_reviews=200, rating_limits=None):
        """
        Método principal otimizado para coletar reviews com alta performance
        Usa requisições concorrentes para máxima velocidade
        """
        if rating_limits:
            return self._collect_reviews_by_rating_concurrent(rating_limits)
        else:
            return self._collect_reviews_general_concurrent(max_reviews)

    def _collect_reviews_general_concurrent(self, max_reviews):
        """
        Coleta reviews gerais usando requisições CONCORRENTES para alta performance
        """
        all_reviews = []
        
        # Calcular requisições necessárias
        reviews_per_request = self.max_limit
        max_requests = min((max_reviews + reviews_per_request - 1) // reviews_per_request, 
                          (self.max_offset // reviews_per_request) + 1)
        
        offsets_to_try = [i * reviews_per_request for i in range(max_requests) 
                         if i * reviews_per_request <= self.max_offset]
        
        logging.info(f"Estratégia concorrente: {len(offsets_to_try)} requisições paralelas")
        
        # ============================================================================
        # EXECUÇÃO CONCORRENTE DAS REQUISIÇÕES
        # ============================================================================
        
        def fetch_reviews_batch(offset):
            """Função para executar uma requisição individual"""
            try:
                current_limit = min(self.max_limit, max_reviews - len(all_reviews))
                if current_limit <= 0:
                    return []
                
                logging.debug(f"Requisição concorrente: offset={offset}, limit={current_limit}")
                api_data = self.get_reviews(limit=current_limit, offset=offset)
                
                if api_data and 'reviews' in api_data:
                    processed_data = self.parse_reviews_data(api_data)
                    if processed_data and processed_data.get('reviews'):
                        return processed_data['reviews']
                
                return []
                
            except Exception as e:
                logging.error(f"Erro na requisição concorrente offset {offset}: {e}")
                return []
        
        # Executar requisições em paralelo com ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:  # 8 threads concorrentes
            # Submeter todas as tarefas
            future_to_offset = {
                executor.submit(fetch_reviews_batch, offset): offset 
                for offset in offsets_to_try
            }
            
            # Coletar resultados conforme completam
            for future in as_completed(future_to_offset):
                offset = future_to_offset[future]
                try:
                    batch_reviews = future.result(timeout=20)  # Timeout por batch
                    if batch_reviews:
                        # Filtrar duplicatas antes de adicionar
                        new_reviews = self._filter_duplicates(batch_reviews, all_reviews)
                        all_reviews.extend(new_reviews)
                        logging.info(f"Batch offset {offset}: +{len(new_reviews)} reviews únicas")
                        
                        # Verificar se já temos reviews suficientes
                        if len(all_reviews) >= max_reviews:
                            logging.info(f"Limite de {max_reviews} reviews atingido")
                            break
                            
                except Exception as e:
                    logging.error(f"Erro ao processar batch offset {offset}: {e}")
        
        # Limitar ao máximo solicitado
        all_reviews = all_reviews[:max_reviews]
        
        logging.info(f"Coleta concorrente finalizada: {len(all_reviews)} reviews coletadas")
        
        return {
            'reviews': all_reviews,
            'total_reviews_count': len(all_reviews),
            'collection_method': 'concurrent_general'
        }

    def _collect_reviews_by_rating_concurrent(self, rating_limits):
        """
        Coleta reviews por rating usando requisições CONCORRENTES
        """
        all_reviews = []
        rating_stats = {}
        
        def fetch_rating_batch(rating, offset, limit_remaining):
            """Função para executar requisição de um rating específico"""
            try:
                current_limit = min(self.max_limit, limit_remaining)
                if current_limit <= 0:
                    return []
                
                logging.debug(f"Requisição rating {rating}⭐: offset={offset}, limit={current_limit}")
                api_data = self.get_reviews(limit=current_limit, offset=offset, rating_filter=rating)
                
                if api_data and 'reviews' in api_data:
                    processed_data = self.parse_reviews_data(api_data)
                    if processed_data and processed_data.get('reviews'):
                        # Filtrar por rating (dupla verificação)
                        filtered_reviews = [
                            review for review in processed_data['reviews'] 
                            if review.get('rating') == str(rating)
                        ]
                        return filtered_reviews
                
                return []
                
            except Exception as e:
                logging.error(f"Erro na requisição rating {rating}⭐ offset {offset}: {e}")
                return []
        
        # Executar coleta para cada rating em paralelo
        with ThreadPoolExecutor(max_workers=6) as executor:  # 6 threads para ratings
            rating_futures = []
            
            for rating, limit in rating_limits.items():
                if limit <= 0:
                    continue
                
                logging.info(f"Iniciando coleta concorrente para {rating}⭐: {limit} reviews")
                
                # Calcular offsets necessários para este rating
                reviews_per_request = self.max_limit
                max_requests = min((limit + reviews_per_request - 1) // reviews_per_request, 
                                  (self.max_offset // reviews_per_request) + 1)
                
                offsets_to_try = [i * reviews_per_request for i in range(max_requests) 
                                 if i * reviews_per_request <= self.max_offset]
                
                # Submeter tarefas para este rating
                for offset in offsets_to_try:
                    remaining = limit - rating_stats.get(rating, 0)
                    if remaining <= 0:
                        break
                    
                    future = executor.submit(fetch_rating_batch, rating, offset, remaining)
                    rating_futures.append((future, rating, offset))
            
            # Coletar resultados
            for future, rating, offset in rating_futures:
                try:
                    batch_reviews = future.result(timeout=20)
                    if batch_reviews:
                        # Filtrar duplicatas
                        existing_rating_reviews = [r for r in all_reviews if r.get('rating') == str(rating)]
                        new_reviews = self._filter_duplicates(batch_reviews, existing_rating_reviews)
                        
                        # Verificar limite do rating
                        current_count = rating_stats.get(rating, 0)
                        limit_for_rating = rating_limits.get(rating, 0)
                        
                        if current_count < limit_for_rating:
                            reviews_to_add = new_reviews[:limit_for_rating - current_count]
                            all_reviews.extend(reviews_to_add)
                            rating_stats[rating] = current_count + len(reviews_to_add)
                            
                            logging.info(f"Rating {rating}⭐ offset {offset}: +{len(reviews_to_add)} reviews")
                        
                except Exception as e:
                    logging.error(f"Erro ao processar rating {rating}⭐ offset {offset}: {e}")
        
        # Log do resumo final
        logging.info(f"Coleta por rating finalizada: {rating_stats}")
        
        return {
            'reviews': all_reviews,
            'total_reviews_count': len(all_reviews),
            'rating_stats': rating_stats,
            'collection_method': 'concurrent_by_rating'
        }

    def _filter_duplicates(self, new_reviews, existing_reviews):
        """
        Filtra reviews duplicadas de forma otimizada usando sets
        """
        if not existing_reviews:
            return new_reviews
        
        # Criar set de identificadores únicos das reviews existentes
        existing_signatures = {
            f"{review.get('text', '')}_{review.get('date', '')}_{review.get('rating', '')}"
            for review in existing_reviews
        }
        
        # Filtrar reviews novas
        unique_reviews = []
        for new_review in new_reviews:
            signature = f"{new_review.get('text', '')}_{new_review.get('date', '')}_{new_review.get('rating', '')}"
            if signature not in existing_signatures:
                unique_reviews.append(new_review)
                existing_signatures.add(signature)  # Adicionar para evitar duplicatas dentro do próprio batch
        
        return unique_reviews
    
    def __del__(self):
        """
        Cleanup da sessão HTTP
        """
        if hasattr(self, 'session'):
            self.session.close()

def _run_review_api_process(product_id, results_queue, max_reviews=200):
    """
    Função interna para executar a API de reviews em um processo separado
    e colocar o resultado em uma queue.
    """
    try:
        logging.info(f"Iniciando coleta de reviews para produto {product_id}")
        
        # Criar instância da API
        api_client = MercadoLivreReviewsAPI(product_id)
        
        # Obter todas as reviews disponíveis
        reviews_data = api_client.get_all_reviews(max_reviews=max_reviews)
        
        if reviews_data:
            results_queue.put(reviews_data)
            logging.info(f"Reviews coletadas com sucesso para produto {product_id}: {len(reviews_data.get('reviews', []))} reviews")
        else:
            results_queue.put(None)
            logging.warning(f"Nenhuma review encontrada para produto {product_id}")

    except Exception as e:
        logging.error(f"Erro no processo de coleta de reviews para produto '{product_id}': {e}", exc_info=True)
        results_queue.put(None)

def run_review_spider(product_id, max_reviews=200, rating_limits=None):
    """
    Executa a coleta de reviews via API para um product_id específico
    e retorna os dados das reviews.
    
    Args:
        product_id (str): ID do produto no Mercado Livre
        max_reviews (int): Número máximo de reviews para coletar (se rating_limits for None)
        rating_limits (dict): Limites por rating {1: 40, 2: 40, 3: 20, 4: 80, 5: 100}
        
    Returns:
        dict: Dados das reviews ou None se houver erro
    """
    if not product_id:
        logging.error("run_review_spider chamado sem product_id")
        return None

    # Para execução local (sem multiprocessing por enquanto, já que a API é mais rápida)
    try:
        logging.info(f"Coletando reviews para produto {product_id}")
        
        # Criar instância da API
        api_client = MercadoLivreReviewsAPI(product_id)
        
        # Obter todas as reviews disponíveis
        reviews_data = api_client.get_all_reviews(max_reviews=max_reviews, rating_limits=rating_limits)
        
        if reviews_data:
            logging.info(f"Reviews coletadas com sucesso: {len(reviews_data.get('reviews', []))} reviews")
            return reviews_data
        else:
            logging.warning(f"Nenhuma review encontrada para produto {product_id}")
            return None
            
    except Exception as e:
        logging.error(f"Erro na coleta de reviews para produto '{product_id}': {e}", exc_info=True)
        return None

# Exemplo de uso da nova API de Reviews
if __name__ == "__main__":
    # Configurar logging para teste
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Testar com um produto específico
    test_product_id = "MLB36751072"  # ID do exemplo fornecido
    print(f"Testando coleta de reviews para produto: {test_product_id}")
    
    reviews_result = run_review_spider(test_product_id, max_reviews=50)
    
    if reviews_result:
        print(f"✅ Sucesso! Coletadas {len(reviews_result.get('reviews', []))} reviews")
        print(f"📊 Total de reviews: {reviews_result.get('total_reviews_count', 0)}")
        
        # Mostrar algumas reviews como exemplo
        for i, review in enumerate(reviews_result.get('reviews', [])[:3]):  # Primeiras 3 reviews
            print(f"\n--- Review {i+1} ---")
            print(f"Rating: {review.get('rating', 'N/A')} estrelas")
            print(f"Data: {review.get('date', 'N/A')}")
            print(f"Texto: {review.get('text', 'N/A')[:100]}...")
            print(f"Útil: {review.get('helpful_count', '0')} pessoas")
    else:
        print("❌ Falha na coleta de reviews")
