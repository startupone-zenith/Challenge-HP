import sys
import subprocess
import importlib
import json
import time
import requests

def ensure_package_installed(package_name):
    """Verifica se um pacote está instalado e o instala se necessário"""
    try:
        importlib.import_module(package_name)
        print(f"Pacote {package_name} já está instalado")
        return True
    except ImportError:
        print(f"Instalando pacote {package_name}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"Pacote {package_name} instalado com sucesso!")
            return True
        except Exception as e:
            print(f"Erro ao instalar o pacote {package_name}: {str(e)}")
            return False

def search_with_mercadolibre_python(query, site_id="MLB", limit=20, client_id=None, client_secret=None):
    """Realiza uma busca usando a biblioteca mercadolibre-python"""
    if not ensure_package_installed("mercadolibre-python"):
        print("Não foi possível instalar a biblioteca mercadolibre-python")
        return None
    
    try:
        # Importamos após garantir que está instalado
        from mercadolibre.client import Client
        
        # Inicializamos o cliente
        try:
            print(f"Inicializando cliente do Mercado Livre para o site {site_id}...")
            client = Client(client_id, client_secret, site=site_id)
            
            # Realizamos a busca
            print(f"Realizando busca por '{query}'...")
            response = client.search(query, limit=limit)
            
            # Verificamos se obtivemos uma resposta válida
            if response and 'results' in response:
                print(f"Busca bem-sucedida! Encontrados {len(response['results'])} resultados.")
                return response
            else:
                print("A busca não retornou resultados válidos.")
                return None
        except Exception as e:
            print(f"Erro ao inicializar o cliente do Mercado Livre: {str(e)}")
            return None
    except Exception as e:
        print(f"Erro ao usar a biblioteca mercadolibre-python: {str(e)}")
        return None

def search_with_requests(query, site_id="MLB", limit=20, access_token=None):
    """Realiza uma busca direta usando a biblioteca requests"""
    ensure_package_installed("requests")
    
    try:
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        # URL básica para busca de produtos
        url = f"https://api.mercadolibre.com/sites/{site_id}/search"
        
        # Parâmetros de busca
        params = {
            "q": query,
            "limit": min(limit, 50)
        }
        
        # Fazemos a requisição
        print(f"Realizando requisição direta à API do Mercado Livre...")
        response = requests.get(url, headers=headers, params=params)
        
        # Verificamos o código de status
        if response.status_code == 200:
            data = response.json()
            print(f"Requisição bem-sucedida! Encontrados {len(data.get('results', []))} resultados.")
            return data
        else:
            print(f"Erro na requisição: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Erro ao fazer requisição direta: {str(e)}")
        return None

def fallback_search(query, site_id="MLB", limit=20, credentials=None):
    """Função principal que tenta diferentes métodos para realizar a busca"""
    print(f"Iniciando busca de fallback para '{query}' no site {site_id}...")
    
    # Primeira tentativa: usar a biblioteca oficial
    if credentials and credentials.get('client_id') and credentials.get('client_secret'):
        result = search_with_mercadolibre_python(
            query, 
            site_id, 
            limit, 
            credentials.get('client_id'), 
            credentials.get('client_secret')
        )
        if result:
            return result
    
    # Segunda tentativa: fazer requisição direta
    if credentials and credentials.get('access_token'):
        result = search_with_requests(
            query, 
            site_id, 
            limit, 
            credentials.get('access_token')
        )
        if result:
            return result
    
    # Terceira tentativa: busca anônima
    result = search_with_requests(query, site_id, limit)
    if result:
        return result
    
    # Se chegamos aqui, todas as tentativas falharam
    print("Todas as tentativas de busca fallback falharam.")
    return None

class MercadoLivreAPI:
    def __init__(self, access_token=None):
        """
        Inicializa o helper da API do Mercado Livre
        
        Args:
            access_token (str, opcional): Token de acesso para a API. Se não for fornecido,
                                          tentará ler de ml_tokens.json
        """
        self.base_url = "https://api.mercadolibre.com"
        
        if access_token:
            self.access_token = access_token
        else:
            try:
                with open('ml_tokens.json', 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get('access_token')
                    if not self.access_token:
                        print("Aviso: Token de acesso não encontrado no arquivo ml_tokens.json")
            except FileNotFoundError:
                print("Aviso: Arquivo ml_tokens.json não encontrado")
                self.access_token = None
    
    def get_auth_header(self):
        """Retorna o cabeçalho de autorização para as requisições"""
        if not self.access_token:
            raise ValueError("Token de acesso não definido")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
    
    def get_user_info(self):
        """Obtém informações do usuário autenticado"""
        endpoint = f"{self.base_url}/users/me"
        response = requests.get(endpoint, headers=self.get_auth_header())
        return response.json()
    
    def search_items(self, query, site_id="MLB", limit=50):
        """
        Busca itens no Mercado Livre
        
        Args:
            query (str): Termo de busca
            site_id (str): ID do site (país). Padrão: MLB (Brasil)
            limit (int): Número máximo de resultados
            
        Returns:
            dict: Resposta da API com os resultados
        """
        endpoint = f"{self.base_url}/sites/{site_id}/search"
        params = {
            'q': query,
            'limit': limit
        }
        
        # Para busca pública, o token não é obrigatório
        headers = self.get_auth_header() if self.access_token else {'Accept': 'application/json'}
        
        response = requests.get(endpoint, params=params, headers=headers)
        return response.json()
    
    def get_item_details(self, item_id):
        """
        Obtém detalhes de um item específico
        
        Args:
            item_id (str): ID do item
            
        Returns:
            dict: Detalhes do item
        """
        endpoint = f"{self.base_url}/items/{item_id}"
        response = requests.get(endpoint, headers={'Accept': 'application/json'})
        return response.json()
    
    def get_my_items(self, limit=50, offset=0):
        """
        Obtém itens do usuário autenticado
        
        Args:
            limit (int): Número máximo de resultados por página
            offset (int): Deslocamento para paginação
            
        Returns:
            dict: Lista de itens do usuário
        """
        if not self.access_token:
            raise ValueError("Token de acesso necessário para esta operação")
        
        endpoint = f"{self.base_url}/users/me/items/search"
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = requests.get(endpoint, params=params, headers=self.get_auth_header())
        return response.json()

# Exemplo de uso
if __name__ == "__main__":
    # Você pode passar o access_token diretamente ou deixar ler do arquivo ml_tokens.json
    # Exemplo: ml_api = MercadoLivreAPI("APP_USR-123456-etc...")
    ml_api = MercadoLivreAPI()
    
    try:
        # Obtém informações do usuário
        print("Obtendo informações do usuário...")
        user_info = ml_api.get_user_info()
        print(f"Usuário: {user_info.get('nickname')} (ID: {user_info.get('id')})")
        
        # Busca itens
        query = input("\nDigite um termo para buscar produtos: ")
        if query:
            print(f"\nBuscando produtos com o termo '{query}'...")
            search_results = ml_api.search_items(query, limit=5)
            
            print(f"Total de resultados: {search_results.get('paging', {}).get('total', 0)}")
            
            for idx, item in enumerate(search_results.get('results', []), 1):
                print(f"\nItem {idx}:")
                print(f"Título: {item.get('title')}")
                print(f"Preço: {item.get('price')} {item.get('currency_id')}")
                print(f"Link: {item.get('permalink')}")
        
        # Obtém meus anúncios
        print("\nObtendo seus anúncios...")
        my_items = ml_api.get_my_items(limit=5)
        
        if my_items.get('results'):
            print(f"Total de anúncios: {my_items.get('paging', {}).get('total', 0)}")
            
            for idx, item_id in enumerate(my_items.get('results', []), 1):
                item_details = ml_api.get_item_details(item_id)
                print(f"\nAnúncio {idx}:")
                print(f"ID: {item_details.get('id')}")
                print(f"Título: {item_details.get('title')}")
                print(f"Preço: {item_details.get('price')} {item_details.get('currency_id')}")
                print(f"Status: {item_details.get('status')}")
                print(f"Link: {item_details.get('permalink')}")
                
        else:
            print("Nenhum anúncio encontrado ou acesso não autorizado.")
    
    except Exception as e:
        print(f"Erro: {e}") 