import requests
import logging
import re
import json
import time
import random

# USER_AGENTS list for API requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
]

class MercadoLivreReviewsAPI:
    """
    Cliente para acessar as reviews via API REST do Mercado Livre
    """
    def __init__(self, product_id):
        if not product_id:
            raise ValueError("A product_id must be provided.")
        
        self.product_id = product_id
        self.base_url = f"https://www.mercadolivre.com.br/noindex/catalog/reviews/{self.product_id}/search"
        self.max_limit = 30   # Limite máximo por requisição (corrigido)
        self.max_offset = 200 # Offset máximo permitido (corrigido)
        logging.info(f"MercadoLivreReviewsAPI initialized for product_id: {self.product_id}")

    def get_reviews(self, limit=15, offset=0, rating_filter=None):
        """
        Faz uma requisição para obter reviews
        
        Args:
            limit (int): Número de reviews por página (máximo 30)
            offset (int): Offset para paginação (máximo 200)
            rating_filter (int): Filtro por rating (1-5 estrelas), None para todas
            
        Returns:
            dict: Dados das reviews ou None se houver erro
        """
        # Validar limites
        if limit > self.max_limit:
            limit = self.max_limit
            logging.warning(f"Limit reduzido para o máximo permitido: {self.max_limit}")
            
        if offset > self.max_offset:
            offset = self.max_offset
            logging.warning(f"Offset reduzido para o máximo permitido: {self.max_offset}")

        params = {
            'objectId': self.product_id,
            'siteId': 'MLB',
            'isItem': 'false',
            'offset': offset,
            'limit': limit,
            'x-is-webview': 'false',
            'controlled': 'true'
        }
        
        # Adicionar filtro de rating se especificado
        if rating_filter is not None and 1 <= rating_filter <= 5:
            params['rating'] = str(rating_filter)
            logging.info(f"Filtro de rating aplicado: {rating_filter} estrelas")
        
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Referer': f'https://www.mercadolivre.com.br/',
            'Origin': 'https://www.mercadolivre.com.br'
        }
        
        try:
            logging.info(f"Fazendo requisição para reviews: limit={limit}, offset={offset}")
            logging.info(f"URL base: {self.base_url}")
            logging.info(f"Parâmetros: {params}")
            
            response = requests.get(self.base_url, params=params, headers=headers, timeout=30)
            
            logging.info(f"URL completa da requisição: {response.url}")
            logging.info(f"Status da resposta: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logging.info(f"Requisição bem-sucedida. Reviews obtidas: {len(data.get('reviews', []))}")
                return data
            else:
                logging.error(f"Erro na requisição: Status {response.status_code}")
                logging.error(f"Conteúdo da resposta: {response.text[:500]}...")  # Primeiros 500 chars
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Erro ao decodificar JSON: {e}")
            logging.error(f"Conteúdo da resposta (JSON inválido): {response.text[:500]}...")
            return None

    def parse_reviews_data(self, api_data):
        """
        Processa os dados JSON da API e extrai as informações das reviews
        
        Args:
            api_data (dict): Dados JSON da API
            
        Returns:
            dict: Dados estruturados das reviews
        """
        if not api_data or 'reviews' not in api_data:
            logging.warning(f"Dados da API inválidos para produto {self.product_id}")
            return None
            
        logging.info(f"Processando dados da API para produto ID {self.product_id}")
        
        product_reviews_summary = {
            'product_id': self.product_id,
            'overall_rating': None,
            'total_reviews_count': None,
            'characteristics_ratings': [],
            'reviews': []
        }
        
        # Processar as reviews individuais
        reviews_data = api_data.get('reviews', [])
        logging.info(f"Encontradas {len(reviews_data)} reviews na resposta da API")
        
        for i, review in enumerate(reviews_data):
            review_item = {}
            
            # Extrair rating
            rating = review.get('rating', 'N/A')
            review_item['rating'] = str(rating) if rating != 'N/A' else 'N/A'
            
            # Extrair data
            comment_data = review.get('comment', {})
            time_data = comment_data.get('time', {})
            date_text = time_data.get('text', 'N/A')
            review_item['date'] = date_text if date_text else 'N/A'
            
            # Extrair texto do comentário
            content_data = comment_data.get('content', {})
            comment_text = content_data.get('text', '')
            
            # Se não há texto no comentário, tentar o título
            if not comment_text:
                title_data = review.get('title', {})
                comment_text = title_data.get('text', '')
            
            review_item['text'] = comment_text.strip() if comment_text else 'N/A'
            
            # Extrair contagem de útil
            actions = review.get('actions', [])
            helpful_count = '0'
            for action in actions:
                if action.get('type') == 'LIKE':
                    helpful_count = str(action.get('value', 0))
                    break
            review_item['helpful_count'] = helpful_count
            
            # Adicionar apenas reviews com texto válido
            if review_item['text'] != 'N/A' and review_item['text']:
                product_reviews_summary['reviews'].append(review_item)
                logging.info(f"    Review {i+1}: Rating '{review_item['rating']}', Date '{review_item['date']}', Helpful '{review_item['helpful_count']}', Text: \"{review_item['text'][:50]}...\"")
        
        return product_reviews_summary
    
    def get_all_reviews(self, max_reviews=200, rating_limits=None):
        """
        Obtém o máximo de reviews possível respeitando os limites da API
        
        Args:
            max_reviews (int): Número máximo de reviews a obter (usado se rating_limits for None)
            rating_limits (dict): Limites por rating {1: 40, 2: 40, 3: 20, 4: 80, 5: 100}
            
        Returns:
            dict: Dados completos das reviews
        """
        all_reviews = []
        
        # Decidir estratégia baseada nos parâmetros
        if rating_limits:
            # Coleta por rating específico
            logging.info(f"Coletando reviews por rating: {rating_limits}")
            all_reviews = self._collect_reviews_by_rating(rating_limits)
        else:
            # Coleta geral (método original)
            logging.info(f"Coletando reviews gerais: até {max_reviews} reviews")
            all_reviews = self._collect_reviews_general(max_reviews)
        
        # Criar resultado final
        final_result = {
            'product_id': self.product_id,
            'overall_rating': None,
            'total_reviews_count': len(all_reviews),
            'characteristics_ratings': [],
            'reviews': all_reviews[:max_reviews]  # Limitar ao máximo solicitado
        }
        
        logging.info(f"Total de reviews únicas coletadas: {len(all_reviews)}")
        return final_result
    
    def _collect_reviews_general(self, max_reviews):
        """
        Coleta reviews sem filtro de rating (método original)
        """
        all_reviews = []
        
        # Estratégia: usar múltiplos offsets para maximizar coleta
        reviews_per_request = self.max_limit  # 30 reviews por requisição
        max_requests = min((max_reviews + reviews_per_request - 1) // reviews_per_request, 
                          (self.max_offset // reviews_per_request) + 1)
        
        offsets_to_try = [i * reviews_per_request for i in range(max_requests) 
                         if i * reviews_per_request <= self.max_offset]
        
        logging.info(f"Estratégia geral: {len(offsets_to_try)} requisições com offsets: {offsets_to_try}")
        
        for current_offset in offsets_to_try:
            if len(all_reviews) >= max_reviews:
                break
                
            # Calcular quantas reviews pedir nesta requisição
            remaining_reviews = max_reviews - len(all_reviews)
            current_limit = min(self.max_limit, remaining_reviews)
            
            logging.info(f"Buscando reviews gerais: offset={current_offset}, limit={current_limit}")
            api_data = self.get_reviews(limit=current_limit, offset=current_offset)
            
            if not api_data or 'reviews' not in api_data:
                logging.warning(f"Não foi possível obter reviews no offset {current_offset}")
                continue
            
            # Processar esta leva de reviews
            processed_data = self.parse_reviews_data(api_data)
            if processed_data and processed_data.get('reviews'):
                # Evitar duplicatas
                new_reviews = self._filter_duplicates(processed_data['reviews'], all_reviews)
                all_reviews.extend(new_reviews)
                logging.info(f"Adicionadas {len(new_reviews)} reviews únicas do offset {current_offset}")
            
            # Pequena pausa entre requisições
            time.sleep(0.5)
        
        return all_reviews
    
    def _collect_reviews_by_rating(self, rating_limits):
        """
        Coleta reviews filtradas por rating específico
        """
        all_reviews = []
        rating_stats = {}
        
        for rating, limit in rating_limits.items():
            if limit <= 0:
                continue
                
            logging.info(f"Coletando até {limit} reviews de {rating} estrelas")
            rating_reviews = []
            
            # Calcular offsets para este rating
            reviews_per_request = self.max_limit
            max_requests = min((limit + reviews_per_request - 1) // reviews_per_request, 
                              (self.max_offset // reviews_per_request) + 1)
            
            offsets_to_try = [i * reviews_per_request for i in range(max_requests) 
                             if i * reviews_per_request <= self.max_offset]
            
            for current_offset in offsets_to_try:
                if len(rating_reviews) >= limit:
                    break
                    
                remaining = limit - len(rating_reviews)
                current_limit = min(self.max_limit, remaining)
                
                logging.info(f"Buscando {rating}⭐: offset={current_offset}, limit={current_limit}")
                api_data = self.get_reviews(limit=current_limit, offset=current_offset, rating_filter=rating)
                
                if not api_data or 'reviews' not in api_data:
                    logging.warning(f"Não foi possível obter reviews {rating}⭐ no offset {current_offset}")
                    continue
                
                # Processar reviews desta leva
                processed_data = self.parse_reviews_data(api_data)
                if processed_data and processed_data.get('reviews'):
                    # Filtrar por rating (dupla verificação) e evitar duplicatas
                    filtered_reviews = []
                    for review in processed_data['reviews']:
                        if review.get('rating') == str(rating):
                            filtered_reviews.append(review)
                    
                    new_reviews = self._filter_duplicates(filtered_reviews, rating_reviews)
                    rating_reviews.extend(new_reviews)
                    logging.info(f"Adicionadas {len(new_reviews)} reviews únicas de {rating}⭐")
                
                # Pausa entre requisições
                time.sleep(0.5)
            
            rating_stats[rating] = len(rating_reviews)
            all_reviews.extend(rating_reviews)
            logging.info(f"Total coletado para {rating}⭐: {len(rating_reviews)}/{limit}")
        
        # Log do resumo final
        logging.info(f"Resumo da coleta por rating: {rating_stats}")
        return all_reviews
    
    def _filter_duplicates(self, new_reviews, existing_reviews):
        """
        Filtra reviews duplicadas comparando texto, data e rating
        """
        unique_reviews = []
        for new_review in new_reviews:
            is_duplicate = False
            for existing_review in existing_reviews:
                if (new_review.get('text') == existing_review.get('text') and 
                    new_review.get('date') == existing_review.get('date') and
                    new_review.get('rating') == existing_review.get('rating')):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_reviews.append(new_review)
        return unique_reviews

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
