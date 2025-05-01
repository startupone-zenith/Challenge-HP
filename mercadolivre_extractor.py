import requests
import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys

class MercadoLivreAPI:
    def __init__(self, access_token, refresh_token, client_id, client_secret, user_id):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.token_expiry = datetime.now() + timedelta(seconds=21600)  # Default expiry 6 hours
        self.base_url = "https://api.mercadolibre.com"
        
    def _check_token(self):
        """Check if token is about to expire and refresh if needed"""
        if datetime.now() >= self.token_expiry - timedelta(minutes=10):
            self._refresh_token()
    
    def _refresh_token(self):
        """Refresh the access token using refresh token"""
        print("Refreshing access token...")
        url = f"{self.base_url}/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]  # Save new refresh token
            self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"])
            print("Token refreshed successfully")
        else:
            print(f"Error refreshing token: {response.status_code}")
            print(response.text)
            raise Exception("Failed to refresh token")
    
    def _make_request(self, method, endpoint, params=None, data=None, auth_required=True, headers=None):
        """Make a request to the API, with or without authentication"""
        # Always check token regardless of auth_required
        self._check_token()
        
        url = f"{self.base_url}{endpoint}"
        
        # Always include Authorization header
        request_headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Add custom headers if provided
        if headers and isinstance(headers, dict):
            request_headers.update(headers)
        elif method.upper() != "GET":
            # Default content type for non-GET requests
            request_headers["Content-Type"] = "application/json"
        
        # Implement exponential backoff for rate limiting
        max_retries = 5
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, params=params, data=json.dumps(data) if data else None)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=request_headers, params=params, data=json.dumps(data) if data else None)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 429:  # Too Many Requests
                wait_time = retry_delay * (2 ** attempt)
                print(f"Rate limit exceeded. Waiting for {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            return response
        
        raise Exception("Max retries exceeded due to rate limiting")
    
    def get_user_info(self):
        """Get information about the authenticated user"""
        response = self._make_request("GET", "/users/me", auth_required=True)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    
    def search_items(self, query=None, seller_id=None, category=None, limit=50, offset=0, site_id="MLB"):
        """Search for items with various filters
        Note: This endpoint requires authentication despite being public data
        """
        # Tentaremos uma abordagem diferente para evitar o erro 403
        # Primeiro tentamos uma abordagem diferente para evitar o erro 403
        # Primeiro tentamos com o endpoint de busca padrão
        params = {"limit": limit, "offset": offset}
        
        if query:
            params["q"] = query
        if seller_id:
            params["seller_id"] = seller_id
        if category:
            params["category"] = category
            
        # Primeira tentativa com o endpoint original
        print("Tentando busca com o endpoint principal...")
        response = self._make_request("GET", f"/sites/{site_id}/search", params=params, auth_required=True)
        
        # Se recebermos 403, tentamos uma abordagem alternativa
        if response.status_code == 403 or response.status_code == 401:
            print("Primeira abordagem retornou erro, tentando método alternativo...")
            
            # Abordagem alternativa 1: Buscar usando o endpoint /highlights/MLB/item
            alt_params = {"status": "active", "site_id": site_id}
            
            if query:
                alt_params["terms"] = query
                
            # Definir um limit padrão (diferente do endpoint anterior)
            alt_params["limit"] = min(limit, 50)  # API limita a 50 itens por página
            
            print("Tentando busca com endpoint de destaques...")
            alt_response = self._make_request("GET", f"/highlights/{site_id}/item", params=alt_params, auth_required=True)
            
            # Se ainda tivermos 403, tentamos o endpoint de tendências
            if alt_response.status_code == 403 or alt_response.status_code == 401:
                print("Segunda abordagem retornou erro, tentando com endpoint de tendências...")
                
                # Tentamos com o endpoint de trending items, que costuma ser mais acessível
                print("Tentando busca com endpoint de tendências...")
                third_response = self._make_request("GET", f"/trends/{site_id}", params={"limit": limit}, auth_required=True)
                
                if third_response.status_code == 200:
                    print("Busca com endpoint de tendências bem-sucedida!")
                    data = third_response.json()
                    
                    # Verificamos se temos dados
                    if not data:
                        print("O endpoint de tendências retornou uma lista vazia.")
                        # Tentamos uma quarta abordagem usando a biblioteca oficial do ML
                        return self._fallback_search(query, site_id, limit)
                    
                    # Extrair os IDs dos itens em tendência
                    item_ids = []
                    for item in data:
                        if "item_id" in item and len(item_ids) < limit:
                            item_ids.append(item["item_id"])
                    
                    # Se temos IDs, buscamos os detalhes
                    if item_ids:
                        print(f"Encontrados {len(item_ids)} itens em tendência, buscando detalhes...")
                        details_response = self.get_item_details(item_ids[:20])  # Máximo de 20 por vez
                        
                        if details_response:
                            results = []
                            for item in details_response:
                                if item.get('code') == 200 and item.get('body'):
                                    results.append(item.get('body'))
                            
                            if results:
                                print(f"Detalhes obtidos com sucesso para {len(results)} itens!")
                                return {
                                    "results": results,
                                    "paging": {
                                        "total": len(results),
                                        "offset": 0,
                                        "limit": limit
                                    },
                                    "search_type": "trending"  # Indicamos que é uma busca por tendências
                                }
                            else:
                                print("Não foi possível obter detalhes dos itens em tendência.")
                        else:
                            print("Falha ao buscar detalhes dos itens em tendência.")
                    else:
                        print("Nenhum item em tendência encontrado.")
                
                # Se todas as abordagens falharam, tentamos uma abordagem final
                print("Todas as abordagens padrão falharam. Tentando método alternativo final...")
                return self._fallback_search(query, site_id, limit)
            
            # Se a segunda abordagem funcionou
            if alt_response.status_code == 200:
                print("Busca com endpoint de destaques bem-sucedida!")
                return alt_response.json()
                
            # Se ainda não conseguimos, tentamos a última abordagem
            print("Método alternativo falhou. Tentando abordagem final...")
            return self._fallback_search(query, site_id, limit)
        
        # Se a abordagem original funcionou
        if response.status_code == 200:
            print("Busca com endpoint principal bem-sucedida!")
            return response.json()
        else:
            print(f"Erro {response.status_code} na busca principal.")
            print(response.text)
            # Tentamos a abordagem final
            return self._fallback_search(query, site_id, limit)
            
    def _fallback_search(self, query, site_id="MLB", limit=20):
        """Método de fallback que usa uma abordagem alternativa para buscar produtos
        quando todas as outras abordagens falharam"""
        print("Executando método de fallback para busca...")
        
        if not query:
            print("É necessário um termo de busca para o método de fallback.")
            return None
            
        # Busca por produtos específicos com termos simples sem filtros adicionais
        # Este endpoint é mais permissivo
        fallback_params = {
            "q": query,
            "limit": min(limit, 20)  # Limitamos a 20 para evitar problemas
        }
        
        # Tentativa usando o endpoint mais básico e estável
        fallback_response = self._make_request(
            "GET", 
            f"/sites/{site_id}/search", 
            params=fallback_params,
            auth_required=True
        )
        
        if fallback_response.status_code == 200:
            print("Busca de fallback bem-sucedida!")
            return fallback_response.json()
            
        # Se ainda falhar, tentamos buscar itens populares na categoria mais relevante
        print("Tentando buscar itens populares relacionados...")
        
        # Buscar as categorias principais do site
        categories_response = self._make_request("GET", f"/sites/{site_id}/categories", auth_required=True)
        
        if categories_response.status_code == 200:
            categories = categories_response.json()
            if categories and len(categories) > 0:
                # Pegamos a primeira categoria (normalmente uma categoria geral)
                category_id = categories[0]["id"]
                print(f"Buscando itens populares na categoria {category_id}...")
                
                # Buscar itens populares nesta categoria
                popular_response = self._make_request(
                    "GET", 
                    f"/highlights/{site_id}/category/{category_id}", 
                    params={"limit": limit},
                    auth_required=True
                )
                
                if popular_response.status_code == 200:
                    print("Busca de itens populares bem-sucedida!")
                    popular_data = popular_response.json()
                    
                    # Verificamos se temos conteúdo nos dados populares
                    if "content" in popular_data and popular_data["content"]:
                        # Extrair IDs de produtos para buscar detalhes
                        item_ids = []
                        for item in popular_data.get("content", []):
                            if "id" in item and isinstance(item["id"], str):
                                item_ids.append(item["id"])
                        
                        # Se temos IDs, buscar detalhes mais completos
                        if item_ids:
                            print(f"Encontrados {len(item_ids)} produtos populares. Buscando detalhes completos...")
                            
                            # Criar uma resposta formatada com detalhes dos produtos populares
                            formatted_data = self._fetch_items_details(item_ids, limit)
                            
                            if formatted_data and formatted_data.get('results'):
                                print(f"Detalhes obtidos com sucesso para {len(formatted_data.get('results', []))} produtos!")
                                return formatted_data
                        
                        print("Voltando para lista básica de produtos populares")
                        # Se não conseguiu obter detalhes completos, retorna os dados básicos
                        return {
                            "results": popular_data.get("content", []),
                            "paging": {
                                "total": len(popular_data.get("content", [])),
                                "offset": 0,
                                "limit": limit
                            },
                            "search_type": "popular"
                        }
        
        # Se chegamos aqui, todas as tentativas falharam
        print("Todas as tentativas de busca falharam. Não foi possível obter resultados.")
        return None
        
    def _fetch_items_details(self, item_ids, limit):
        """Busca detalhes completos para uma lista de IDs de itens"""
        if not item_ids:
            return None
            
        # Limitar a quantidade de IDs para não sobrecarregar a API
        item_ids = item_ids[:min(len(item_ids), limit, 20)]
        
        try:
            # Buscar detalhes dos itens usando o endpoint multiget
            details = self.get_item_details(item_ids)
            
            if not details:
                return None
                
            # Processar os detalhes retornados
            enriched_items = []
            
            for item in details:
                # Verificar se o item foi retornado com sucesso
                if isinstance(item, dict) and item.get('code') == 200 and 'body' in item:
                    body = item['body']
                    
                    # Log para debug
                    print(f"Processando item com ID: {body.get('id', 'N/A')}")
                    print(f"Título: {body.get('title', 'Sem título')}")
                    
                    # Criar um objeto enriquecido com os detalhes do produto
                    enriched_item = {
                        'id': body.get('id', ''),
                        'title': body.get('title', 'Sem título'),
                        'permalink': body.get('permalink', f"https://produto.mercadolivre.com.br/{body.get('id', '')}"),
                        'seller_id': body.get('seller_id', ''),
                        'price': body.get('price', 0),
                        'currency_id': body.get('currency_id', 'BRL'),
                        'available_quantity': body.get('available_quantity', 0),
                        'sold_quantity': body.get('sold_quantity', 0),
                        'condition': body.get('condition', 'new'),
                        'thumbnail': body.get('thumbnail', '')
                    }
                    
                    # Adicionar informações do vendedor se disponíveis
                    if 'seller' in body and isinstance(body['seller'], dict):
                        enriched_item['seller'] = body['seller']
                        
                    enriched_items.append(enriched_item)
            
            # Retornar os dados em um formato estruturado
            return {
                'results': enriched_items,
                'paging': {
                    'total': len(enriched_items),
                    'offset': 0,
                    'limit': limit
                },
                'search_type': 'popular_with_details'
            }
        except Exception as e:
            print(f"Erro ao buscar detalhes dos produtos: {str(e)}")
            return None
    
    def get_item_details(self, item_ids):
        """Get detailed information about specific items
        item_ids can be a single ID or a list of up to 20 IDs
        Note: Item details now requires authentication
        """
        if not item_ids:
            return None
            
        # Verificar se é uma lista ou um único ID
        if isinstance(item_ids, list):
            if len(item_ids) > 20:
                print("Aviso: Máximo de 20 IDs permitidos por requisição. Truncando lista.")
                item_ids = item_ids[:20]
                
            # Log para debug
            print(f"Buscando detalhes para {len(item_ids)} produtos...")
            print(f"Primeiro ID da lista: {item_ids[0] if item_ids else 'N/A'}")
            
            ids_param = ",".join(item_ids)
            endpoint = f"/items?ids={ids_param}"
            
            # Para o multiget, é recomendável usar 'attributes' para limitar os campos retornados
            # Isso melhora a performance da API e reduz o tamanho dos dados
            params = {
                "attributes": "id,title,permalink,seller_id,price,currency_id,available_quantity,condition,thumbnail,category_id,official_store_id,seller"
            }
        else:
            endpoint = f"/items/{item_ids}"
            print(f"Buscando detalhes para o produto com ID: {item_ids}")
            params = {}
            
        # Adicionar headers específicos conforme documentação API
        custom_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Mercado Livre API now requires authentication for all endpoints
        response = self._make_request(
            "GET", 
            endpoint, 
            params=params, 
            auth_required=True,
            headers=custom_headers
        )
        
        if response.status_code == 200:
            # Log para debug
            result = response.json()
            print(f"Detalhes de produtos retornados: {len(result) if isinstance(result, list) else 1}")
            
            # Verificação extra para garantir estrutura correta
            if isinstance(result, list):
                valid_items = 0
                for item in result:
                    if isinstance(item, dict) and item.get('code') == 200 and 'body' in item:
                        # Verificando se o 'body' tem o mínimo de campos necessários
                        body = item.get('body', {})
                        if 'id' in body and 'title' in body:
                            valid_items += 1
                            
                print(f"Produtos com detalhes válidos: {valid_items} de {len(result)}")
                
                # Se nenhum item válido, pode ser um erro de API
                if valid_items == 0 and len(result) > 0:
                    print("Aviso: Resposta recebida, mas sem detalhes válidos de produtos")
                    print(f"Exemplo de resposta: {result[0]}")
                    
            return result
        else:
            print(f"Erro ao obter detalhes dos produtos: {response.status_code}")
            print(response.text)
            
            # Tentar parsing da mensagem de erro
            try:
                error = response.json()
                print(f"Erro detalhado: {error.get('message', 'Desconhecido')}")
            except:
                pass
            
            return None
    
    def get_categories(self, site_id="MLB"):
        """Get all categories for a specific site (default: Brazil)
        Note: Categories now requires authentication
        """
        response = self._make_request("GET", f"/sites/{site_id}/categories", auth_required=True)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    
    def get_user_items(self, user_id=None, limit=50, offset=0):
        """Get items for a specific user or the authenticated user"""
        if user_id is None:
            user_id = self.user_id
            
        params = {"limit": limit, "offset": offset}
        response = self._make_request("GET", f"/users/{user_id}/items/search", params=params, auth_required=True)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    
    def get_seller_reputation(self, user_id=None):
        """Get the reputation of a seller"""
        if user_id is None:
            user_id = self.user_id
            
        response = self._make_request("GET", f"/users/{user_id}", auth_required=True)
        if response.status_code == 200:
            data = response.json()
            return data.get("seller_reputation", {})
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None

    def direct_search(self, site_id, params):
        """Realiza uma busca direta no endpoint principal com parâmetros específicos.
        Esta função é usada para buscar produtos diretamente, evitando endpoints populares/tendências
        que podem retornar IDs inválidos.
        
        Args:
            site_id (str): ID do site (MLB, MLA, etc)
            params (dict): Parâmetros de busca
            
        Returns:
            dict: Resultados da busca ou None em caso de erro
        """
        print(f"Realizando busca direta no site {site_id} com parâmetros: {params}")
        
        # Garantir que estamos usando apenas parâmetros seguros
        safe_params = {
            "q": params.get("q", ""),
            "limit": min(params.get("limit", 50), 50),  # Limitamos a 50 por segurança
            "offset": params.get("offset", 0),
            "sort": params.get("sort", "relevance")
        }
        
        # Adicionar outros parâmetros seguros
        if "seller_id" in params:
            safe_params["seller_id"] = params["seller_id"]
        if "category" in params:
            safe_params["category"] = params["category"]
        
        # Headers customizados para melhorar compatibilidade
        custom_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Fazer a requisição com verificação de erros e retry
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self._make_request(
                    "GET",
                    f"/sites/{site_id}/search",
                    params=safe_params,
                    auth_required=True,
                    headers=custom_headers
                )
                
                # Verificar a resposta
                if response.status_code == 200:
                    data = response.json()
                    
                    # Verificar se temos resultados
                    if isinstance(data, dict) and 'results' in data and len(data['results']) > 0:
                        print(f"Busca direta bem-sucedida! Encontrados {len(data['results'])} produtos.")
                        
                        # Verificar se os resultados contêm dados esperados
                        sample_item = data['results'][0]
                        if 'id' in sample_item and 'title' in sample_item:
                            print(f"Exemplo: ID={sample_item['id']}, Título={sample_item['title']}")
                            return data
                        else:
                            print("Resultados encontrados, mas formato inesperado.")
                    else:
                        print("Resposta sem resultados válidos.")
                else:
                    print(f"Erro na busca direta: {response.status_code}")
                    print(response.text)
                    
                    # Se for erro de autenticação, tentar renovar token
                    if response.status_code in [401, 403] and attempt < max_retries - 1:
                        print("Tentando renovar token...")
                        try:
                            self._refresh_token()
                            continue
                        except:
                            pass
                    
                # Esperar antes de tentar novamente
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s...
                    print(f"Tentando novamente em {wait_time} segundos...")
                    time.sleep(wait_time)
                
            except Exception as e:
                print(f"Erro na busca direta: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        print("Todas as tentativas de busca direta falharam.")
        return None

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
    if site_code == "MLB":
        base_url = f"https://lista.mercadolivre.com.br/{search_url_term}"
    else:
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
                    
                    # Adicionar à lista de produtos
                    products.append({
                        'titulo': title,
                        'link': link,
                        'preco': price,
                        'vendedor': seller,
                        'site_code': site_code
                    })
                    
                    total_collected += 1
                    print(f"Produto {total_collected} coletado: {title}")
                    
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
    
    # Exportar resultados
    if products:
        csv_path = export_to_csv(products, search_term, site_code)
        print(f"\nDados exportados com sucesso para: {csv_path}")
    else:
        print("Nenhum produto encontrado para exportar.")
    
    print("\n=== WEB SCRAPING CONCLUÍDO ===") 