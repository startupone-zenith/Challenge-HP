#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste da API Flask - Sistema de Scraping HP
"""

import requests
import time
import json

# Configuração
BASE_URL = "http://localhost:5000/api"

def test_api():
    """Testa a API do sistema Flask"""
    
    print("🧪 TESTANDO API FLASK - SISTEMA HP")
    print("=" * 50)
    
    # 1. Teste simples primeiro
    print("\n1️⃣ Testando scraping simples...")
    try:
        response = requests.post(f"{BASE_URL}/scraping/simple", json={
            "query": "cartucho hp",
            "max_items": 3
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Sucesso! {data['total_produtos']} produtos encontrados")
                if data.get('produtos'):
                    for i, produto in enumerate(data['produtos'][:2], 1):
                        print(f"   {i}. {produto.get('title', 'N/A')} - {produto.get('price', 'N/A')}")
            else:
                print(f"❌ Erro na API: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {str(e)}")
        return False
    
    # 2. Teste de job completo
    print("\n2️⃣ Testando job de scraping...")
    try:
        response = requests.post(f"{BASE_URL}/scraping/start", json={
            "query": "toner hp",
            "max_items": 5,
            "collect_reviews": False,
            "generate_json": True
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                job_id = data['job_id']
                print(f"✅ Job iniciado: {job_id}")
                
                # Monitorar job
                print("   Monitorando progresso...")
                for i in range(10):  # Máximo 10 tentativas
                    time.sleep(2)
                    status_response = requests.get(f"{BASE_URL}/jobs/{job_id}/status")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if status_data.get('success'):
                            status = status_data['status']
                            progress = status_data['progress']
                            produtos = status_data['produtos_coletados']
                            
                            print(f"   📊 Status: {status} ({progress}%) - {produtos} produtos")
                            
                            if status in ['concluido', 'erro']:
                                break
                    else:
                        print(f"   ❌ Erro ao verificar status: {status_response.status_code}")
                        break
                
                if status == 'concluido':
                    print("   ✅ Job concluído com sucesso!")
                elif status == 'erro':
                    print(f"   ❌ Job falhou: {status_data.get('error_message')}")
                else:
                    print("   ⏳ Job ainda em andamento...")
                    
            else:
                print(f"❌ Erro ao iniciar job: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {str(e)}")
    
    # 3. Listar jobs
    print("\n3️⃣ Listando jobs...")
    try:
        response = requests.get(f"{BASE_URL}/jobs")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                jobs = data['jobs']
                print(f"✅ Total de jobs: {len(jobs)}")
                for job in jobs[-3:]:  # Últimos 3 jobs
                    print(f"   • {job['job_id']}: {job['status']} - {job['query']}")
            else:
                print(f"❌ Erro: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {str(e)}")
    
    # 4. Listar datasets
    print("\n4️⃣ Listando datasets...")
    try:
        response = requests.get(f"{BASE_URL}/datasets")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                datasets = data['datasets']
                print(f"✅ Total de datasets: {len(datasets)}")
                for dataset in datasets[-3:]:  # Últimos 3 datasets
                    size_mb = dataset['size'] / (1024 * 1024)
                    print(f"   • {dataset['filename']} ({size_mb:.1f} MB)")
            else:
                print(f"❌ Erro: {data.get('error')}")
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 TESTE CONCLUÍDO!")
    print("\n📋 Para usar a interface web, acesse:")
    print("   http://localhost:5000")
    print("\n📚 Para ver a documentação completa:")
    print("   Abra o arquivo API_DOCUMENTATION.md")
    
    return True

def check_server():
    """Verifica se o servidor Flask está rodando"""
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    if not check_server():
        print("❌ Servidor Flask não está rodando!")
        print("Execute primeiro: python run_flask.py")
        exit(1)
    
    test_api()

