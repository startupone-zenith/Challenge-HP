#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para verificar se o Flask não reinicia mais quando jobs terminam
"""

import time
import requests
import json

def test_job_completion_no_restart():
    """Testa se um job completa sem causar restart no Flask"""
    
    print("🧪 TESTE: Job completion sem restart do Flask")
    print("=" * 50)
    
    # Configuração do teste
    base_url = "http://localhost:5000"
    
    try:
        # Verificar se Flask está rodando
        print("1. Verificando se Flask está ativo...")
        response = requests.get(f"{base_url}/api/jobs", timeout=5)
        if response.status_code != 200:
            print("❌ Flask não está rodando. Inicie com: python src/web/run_flask.py")
            return False
        print("✅ Flask ativo")
        
        # Iniciar um job pequeno de teste
        print("\n2. Iniciando job de teste...")
        job_data = {
            "query": "cartucho hp",
            "max_items": 5,  # Poucos itens para teste rápido
            "extract_images": False,
            "collect_reviews": False,
            "detailed_extraction": False
        }
        
        response = requests.post(f"{base_url}/api/scraping/start", json=job_data, timeout=10)
        if response.status_code != 200:
            print("❌ Falha ao iniciar job")
            return False
            
        result = response.json()
        job_id = result.get('job_id')
        print(f"✅ Job iniciado: {job_id}")
        
        # Monitorar o job até conclusão
        print("\n3. Monitorando job...")
        max_attempts = 60  # 5 minutos máximo
        attempt = 0
        
        while attempt < max_attempts:
            try:
                response = requests.get(f"{base_url}/api/jobs/{job_id}/status", timeout=5)
                
                if response.status_code != 200:
                    print("❌ FLASK REINICIOU! (erro ao acessar status)")
                    return False
                
                status = response.json()
                job_status = status.get('status', 'unknown')
                progress = status.get('progress', 0)
                
                print(f"   Status: {job_status} ({progress}%)")
                
                if job_status == 'concluido':
                    print("✅ Job concluído!")
                    break
                elif job_status == 'erro':
                    print("⚠️ Job terminou com erro")
                    break
                    
                time.sleep(5)
                attempt += 1
                
            except requests.exceptions.RequestException as e:
                print(f"❌ FLASK REINICIOU! (conexão perdida: {e})")
                return False
        
        # Aguardar um pouco mais após conclusão
        print("\n4. Aguardando após conclusão...")
        time.sleep(10)
        
        # Verificar se Flask ainda está responsivo
        try:
            response = requests.get(f"{base_url}/api/jobs", timeout=5)
            if response.status_code == 200:
                print("✅ Flask ainda ativo após job!")
                print("🎉 TESTE PASSOU: Sem restart automático!")
                return True
            else:
                print("❌ Flask não responsivo")
                return False
                
        except requests.exceptions.RequestException:
            print("❌ FLASK REINICIOU após job!")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        return False

def main():
    """Executar teste"""
    success = test_job_completion_no_restart()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ RESULTADO: PROBLEMA RESOLVIDO!")
        print("   Flask não reinicia mais quando jobs terminam")
    else:
        print("❌ RESULTADO: PROBLEMA PERSISTE")
        print("   Flask ainda está reiniciando")
    print("=" * 50)
    
    return success

if __name__ == '__main__':
    main()
