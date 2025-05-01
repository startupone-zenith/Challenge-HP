import requests
import json

# Insira aqui seu token de acesso
ACCESS_TOKEN = 'APP_USR-6940700813779269-050110-2b2adae1508cb1c0228e551eb5a209d1-340557736'

def get_user_info(access_token):
    """Obtém informações do usuário autenticado"""
    url = "https://api.mercadolibre.com/users/me"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    return response.json()

def search_items(query, site_id="MLB", limit=10, access_token=None):
    """Busca itens no Mercado Livre"""
    url = f"https://api.mercadolibre.com/sites/{site_id}/search"
    params = {
        'q': query,
        'limit': limit
    }
    
    headers = {}
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()

def get_my_items(access_token, limit=10):
    """Obtém os itens do usuário autenticado"""
    url = "https://api.mercadolibre.com/users/me/items/search"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    params = {
        'limit': limit
    }
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()

# Executar demonstração
if __name__ == "__main__":
    print("=== DEMONSTRAÇÃO DE USO DO TOKEN DO MERCADO LIVRE ===")
    
    # Exibir informações do usuário
    print("\n1. Informações do usuário:")
    user_info = get_user_info(ACCESS_TOKEN)
    print(f"ID: {user_info.get('id')}")
    print(f"Apelido: {user_info.get('nickname')}")
    print(f"Nome: {user_info.get('first_name')} {user_info.get('last_name')}")
    print(f"E-mail: {user_info.get('email')}")
    print(f"País: {user_info.get('country_id')}")
    
    # Buscar produtos
    print("\n2. Busca de produtos:")
    termo = input("Digite um termo para busca (ou pressione Enter para pular): ")
    
    if termo:
        results = search_items(termo, limit=5)
        print(f"Total de resultados: {results.get('paging', {}).get('total', 0)}")
        
        for i, item in enumerate(results.get('results', []), 1):
            print(f"\nProduto {i}:")
            print(f"Título: {item.get('title')}")
            print(f"Preço: {item.get('price')} {item.get('currency_id')}")
            print(f"Condição: {item.get('condition')}")
            print(f"Link: {item.get('permalink')}")
    
    # Listar meus anúncios
    print("\n3. Meus anúncios:")
    my_items = get_my_items(ACCESS_TOKEN)
    
    if my_items.get('results'):
        print(f"Total de anúncios: {my_items.get('paging', {}).get('total', 0)}")
        
        # Obter detalhes de cada item
        for i, item_id in enumerate(my_items.get('results', [])[:5], 1):
            url = f"https://api.mercadolibre.com/items/{item_id}"
            response = requests.get(url)
            item = response.json()
            
            print(f"\nAnúncio {i}:")
            print(f"ID: {item.get('id')}")
            print(f"Título: {item.get('title')}")
            print(f"Preço: {item.get('price')} {item.get('currency_id')}")
            print(f"Status: {item.get('status')}")
            print(f"Link: {item.get('permalink')}")
    else:
        print("Nenhum anúncio encontrado ou você não tem permissão para ver anúncios.")
    
    print("\n=== FIM DA DEMONSTRAÇÃO ===")
    print("Seu token está funcionando corretamente!")
    print("Lembre-se que o access_token expira em 6 horas.")
    print("Use o refresh_token para renovar o access_token quando necessário.") 