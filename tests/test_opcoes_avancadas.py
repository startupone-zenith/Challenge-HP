#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das Novas Funcionalidades Avancadas de Scraping
Sistema HP - Interface Expandida (Versao Windows)
"""

import requests
import json
import time
from datetime import datetime

def test_basic_api():
    """Testa a API basica com novos parametros"""
    
    print("TESTE 1: API com Configuracoes Basicas")
    print("=" * 50)
    
    url = "http://localhost:5000/api/scraping/start"
    
    data = {
        "query": "cartucho hp 664",
        "max_items": 10,
        "collect_reviews": True,
        "max_reviews_per_product": 25,
        "detailed_extraction": True,
        "generate_json": True,
        
        # Novos parametros
        "site": "mercadolivre",
        "category": "cartuchos", 
        "sort_by": "price_asc",
        "condition": "new",
        "shipping": "free",
        "seller_type": "official",
        
        # Performance
        "delay_between_requests": 1.5,
        "timeout_seconds": 20,
        "max_retries": 2,
        "concurrent_requests": 1,
        
        # Opcoes avancadas
        "save_debug_html": False,
        "verbose_logging": True,
        "skip_duplicates": True
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('success'):
            print("[OK] Sucesso!")
            print(f"   Job ID: {result['job_id']}")
            print(f"   Configuracao: {result.get('configuration', {})}")
            return result['job_id']
        else:
            print(f"[ERRO] Erro: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"[ERRO] Excecao: {e}")
        return None

def test_custom_quantities():
    """Testa quantidades personalizadas"""
    
    print("\nTESTE 2: Quantidades Personalizadas")
    print("=" * 50)
    
    url = "http://localhost:5000/api/scraping/start"
    
    data = {
        "query": "impressora hp deskjet",
        "max_items": 5,  # Quantidade pequena para teste
        "collect_reviews": True,
        "max_reviews_per_product": 10,  # Poucos reviews para teste
        "detailed_extraction": True,
        
        # Configuracoes rapidas
        "delay_between_requests": 1.0,
        "timeout_seconds": 15,
        "max_retries": 2,
        "concurrent_requests": 1
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('success'):
            print("[OK] Quantidades personalizadas aplicadas!")
            print(f"   Job ID: {result['job_id']}")
            print(f"   Produtos: {result.get('configuration', {}).get('max_items', 'N/A')}")
            print(f"   Reviews: {data['max_reviews_per_product']}")
            return result['job_id']
        else:
            print(f"[ERRO] Erro: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"[ERRO] Excecao: {e}")
        return None

def monitor_job(job_id, max_wait=120):
    """Monitora execucao do job"""
    
    if not job_id:
        return False
    
    print(f"\nMONITORAMENTO: Job {job_id}")
    print("-" * 30)
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"http://localhost:5000/api/jobs/{job_id}/status", timeout=5)
            
            if response.status_code == 200:
                status = response.json()
                
                print(f"Status: {status.get('status', 'N/A')} | "
                      f"Progresso: {status.get('progress', 0)}% | "
                      f"Produtos: {status.get('produtos_coletados', 0)}")
                
                if status.get('status') in ['concluido', 'erro']:
                    if status.get('status') == 'concluido':
                        print("[OK] Job concluido com sucesso!")
                        if status.get('result_files'):
                            print(f"   Arquivos gerados: {len(status['result_files'])}")
                            for file in status['result_files'][:3]:  # Mostrar apenas os primeiros 3
                                print(f"     - {file}")
                    else:
                        print(f"[ERRO] Job falhou: {status.get('error_message', 'Erro desconhecido')}")
                    
                    return status.get('status') == 'concluido'
                
            time.sleep(3)  # Aguardar 3 segundos
            
        except Exception as e:
            print(f"   Erro ao verificar status: {e}")
            time.sleep(3)
    
    print("Timeout do monitoramento")
    return False

def main():
    """Executa todos os testes"""
    
    print("TESTES DAS NOVAS FUNCIONALIDADES DE SCRAPING")
    print("Iniciado em:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # Verificar se Flask esta rodando
    try:
        response = requests.get("http://localhost:5000/api/jobs", timeout=5)
        if response.status_code != 200:
            print("[ERRO] Flask nao esta rodando!")
            print("   Inicie com: cd src/web && python run_flask.py")
            return
    except:
        print("[ERRO] Flask nao esta acessivel!")
        print("   Inicie com: cd src/web && python run_flask.py")
        return
    
    print("[OK] Flask ativo, iniciando testes...")
    
    # Executar testes
    jobs = []
    
    # Teste 1: Configuracao basica
    job1 = test_basic_api()
    if job1:
        jobs.append(job1)
    
    # Aguardar um pouco antes do proximo teste
    time.sleep(2)
    
    # Teste 2: Quantidades personalizadas
    job2 = test_custom_quantities()
    if job2:
        jobs.append(job2)
    
    # Monitorar primeiro job
    if jobs:
        print(f"\nMONITORANDO JOB: {jobs[0]}")
        if len(jobs) > 1:
            print(f"Outros jobs: {jobs[1:]}")
        
        success = monitor_job(jobs[0], max_wait=120)  # 2 minutos
        
        if success:
            print("\nTESTE CONCLUIDO COM SUCESSO!")
        else:
            print("\nTESTE PARCIALMENTE CONCLUIDO")
    else:
        print("\nNENHUM JOB FOI INICIADO")
    
    print(f"\nTestes finalizados em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Verifique os datasets gerados em: /datasets_gerados/")
    print("Logs detalhados em: /logs/flask_scraper.log")

if __name__ == "__main__":
    main()
