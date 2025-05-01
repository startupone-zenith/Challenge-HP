import sys
import subprocess
import importlib
import json
import time

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
    import requests
    
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

# Exemplo de uso
if __name__ == "__main__":
    # Credenciais de exemplo
    credentials = {
        "client_id": "SEU_CLIENT_ID",
        "client_secret": "SEU_CLIENT_SECRET",
        "access_token": "SEU_ACCESS_TOKEN"
    }
    
    # Realizamos uma busca
    result = fallback_search("smartphone", "MLB", 10, credentials)
    
    # Salvamos o resultado em um arquivo JSON para análise
    if result:
        with open("fallback_search_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("Resultado salvo em 'fallback_search_result.json'") 