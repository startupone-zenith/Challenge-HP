#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da funcionalidade de URL customizada
"""

import requests
import json

def test_url_customizada_via_api():
    """Testa a nova funcionalidade via API Flask"""
    
    print("🧪 TESTE: URL CUSTOMIZADA VIA API")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # URL fornecida pelo usuário
    url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True#applied_filter_id%3DINK_CARTRIDGE_TYPE%26applied_filter_name%3DTipo+de+cartucho%26applied_filter_order%3D3%26applied_value_id%3D281072%26applied_value_name%3DOriginal%26applied_value_order%3D1%26applied_value_results%3D131%26is_custom%3Dfalse"
    
    try:
        print("1. Testando scraping simples com URL customizada...")
        
        payload = {
            "query": "Cartucho HP Original",
            "max_items": 3,
            "custom_url": url_customizada
        }
        
        response = requests.post(f"{base_url}/api/scraping/simple", 
                               json=payload, 
                               timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                produtos = data.get('produtos', [])
                print(f"✓ Sucesso! {len(produtos)} produtos encontrados usando URL customizada")
                
                if produtos:
                    print("\nPrimeiros produtos:")
                    for i, produto in enumerate(produtos[:2], 1):
                        print(f"{i}. {produto.get('title', 'N/A')[:60]}...")
                        print(f"   Preço: {produto.get('price', 'N/A')}")
                
                return True
            else:
                print(f"✗ Erro na API: {data.get('error')}")
                return False
        else:
            print(f"✗ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        return False

def test_job_com_url_customizada():
    """Testa job completo com URL customizada"""
    
    print("\n2. Testando job completo com URL customizada...")
    
    base_url = "http://localhost:5000"
    url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"
    
    try:
        payload = {
            "query": "Cartucho HP Original",
            "max_items": 5,
            "collect_reviews": False,
            "extract_images": True,
            "custom_url": url_customizada
        }
        
        response = requests.post(f"{base_url}/api/scraping/start", 
                               json=payload, 
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('job_id')
            print(f"✓ Job iniciado: {job_id}")
            
            # Verificar status após alguns segundos
            import time
            time.sleep(3)
            
            status_response = requests.get(f"{base_url}/api/jobs/{job_id}/status", timeout=5)
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"✓ Status: {status_data.get('status')} ({status_data.get('progress')}%)")
                
                if status_data.get('status') == 'erro':
                    print(f"✗ Erro no job: {status_data.get('error_message')}")
                    return False
                else:
                    print("✓ Job executando corretamente com URL customizada")
                    return True
            
        else:
            print(f"✗ Erro ao iniciar job: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Erro no teste de job: {e}")
        return False

if __name__ == "__main__":
    print("🛡️ TESTE DA FUNCIONALIDADE URL CUSTOMIZADA")
    print()
    
    # Verificar se o servidor está rodando
    try:
        response = requests.get("http://localhost:5000/api/jobs", timeout=5)
        if response.status_code != 200:
            print("✗ Servidor Flask não está respondendo corretamente")
            exit(1)
    except:
        print("✗ Servidor Flask não está rodando!")
        print("Execute: python run_flask.py")
        exit(1)
    
    print("✓ Servidor Flask detectado!")
    print()
    
    # Executar testes
    test1 = test_url_customizada_via_api()
    test2 = test_job_com_url_customizada()
    
    print("\n" + "=" * 50)
    print("RESULTADOS DOS TESTES:")
    print(f"- Scraping simples com URL: {'✓ PASSOU' if test1 else '✗ FALHOU'}")
    print(f"- Job completo com URL: {'✓ PASSOU' if test2 else '✗ FALHOU'}")
    
    if test1 and test2:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("\nA funcionalidade de URL customizada está funcionando!")
        print("\nComo usar:")
        print("- Inclua 'custom_url' no payload da API")
        print("- A URL será usada diretamente para scraping")
        print("- Mantém todos os filtros da URL original")
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")
        print("Verifique os logs para mais detalhes.")
