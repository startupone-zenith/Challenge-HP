#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
from mercadolivre_extractor import MercadoLivreAPI
from ml_data_exporter import MercadoLivreExporter

def get_credentials():
    """Obtém as credenciais do arquivo de configuração usado pelo ml_interactive.py"""
    config_file = "ml_credentials.json"
    
    if not os.path.exists(config_file):
        print(f"Arquivo de configuração {config_file} não encontrado.")
        print("Execute primeiro o ml_interactive.py para fazer login.")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_fields = ['access_token', 'refresh_token', 'client_id', 'client_secret', 'user_id']
        if all(field in config for field in required_fields):
            return config
        else:
            print("Configuração incompleta. Execute ml_interactive.py para fazer login novamente.")
            return None
    except Exception as e:
        print(f"Erro ao ler configurações: {str(e)}")
        return None

def test_search_and_details():
    """Testa a funcionalidade corrigida de busca e obtenção de detalhes no Mercado Livre"""
    print("Inicializando conexão com a API do Mercado Livre...")
    
    # Obter credenciais do arquivo de configuração
    config = get_credentials()
    if not config:
        return
    
    ACCESS_TOKEN = config.get('access_token', '')
    REFRESH_TOKEN = config.get('refresh_token', '')
    CLIENT_ID = config.get('client_id', '')
    CLIENT_SECRET = config.get('client_secret', '')
    USER_ID = config.get('user_id', '')
    
    # Inicializar a API
    ml_api = MercadoLivreAPI(ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET, USER_ID)
    
    # Verificar autenticação
    user_info = ml_api.get_user_info()
    if user_info:
        print(f"Conectado como: {user_info.get('nickname', 'USUÁRIO')}")
    else:
        print("Falha na autenticação. Verifique suas credenciais.")
        return
    
    # Inicializar o exportador
    exporter = MercadoLivreExporter(ml_api)
    
    # Parâmetros de teste
    search_term = "notebook"
    site_id = "MLB"
    limit = 20
    
    print(f"\n=== TESTE DE BUSCA: {search_term} ===")
    print(f"Site: {site_id}, Limite: {limit}")
    
    # 1. Testar busca direta
    print("\n1. Testando busca direta...")
    search_results = ml_api.search_items(query=search_term, limit=limit, site_id=site_id)
    
    if not search_results:
        print("Nenhum resultado de busca encontrado.")
    else:
        print(f"Formato da resposta: {type(search_results).__name__}")
        
        if isinstance(search_results, dict):
            if 'results' in search_results:
                print(f"Encontrados {len(search_results.get('results', []))} resultados:")
                for i, item in enumerate(search_results.get('results', [])[:3], 1):
                    print(f"{i}. ID: {item.get('id', 'N/A')}, Título: {item.get('title', 'Sem título')}")
                print("...")
    
    # 2. Testar obtenção de detalhes com multiget
    print("\n2. Testando obtenção de detalhes via multiget...")
    
    # Extrair apenas alguns IDs para teste
    item_ids = []
    if search_results and isinstance(search_results, dict) and 'results' in search_results:
        for item in search_results.get('results', [])[:5]:  # Apenas 5 para o teste
            if isinstance(item, dict) and 'id' in item:
                item_ids.append(item.get('id'))
    
    if not item_ids:
        print("Não foram encontrados IDs para testar o multiget.")
    else:
        print(f"Testando multiget com {len(item_ids)} IDs: {', '.join(item_ids[:3])}...")
        details = ml_api.get_item_details(item_ids)
        
        if not details:
            print("Falha ao obter detalhes via multiget.")
        else:
            print(f"Obtidos detalhes para {len(details)} produtos:")
            for i, item in enumerate(details[:3], 1):
                if item.get('code') == 200 and 'body' in item:
                    body = item.get('body', {})
                    print(f"{i}. ID: {body.get('id', 'N/A')}")
                    print(f"   Título: {body.get('title', 'Sem título')}")
                    print(f"   Link: {body.get('permalink', 'N/A')}")
                    print(f"   Vendedor: {body.get('seller_id', 'N/A')}")
                    print()
    
    # 3. Testar exportação simplificada
    print("\n3. Testando exportação simplificada...")
    csv_path = exporter.export_simple_data(
        query=search_term,
        limit=limit,
        site_id=site_id
    )
    
    if csv_path:
        print(f"Exportação bem-sucedida: {csv_path}")
    else:
        print("Falha na exportação simplificada.")
    
    print("\nTeste concluído.")

if __name__ == "__main__":
    test_search_and_details() 