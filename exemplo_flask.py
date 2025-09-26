#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo Prático de Uso do Sistema Flask
Sistema de Scraping HP
"""

import requests
import time
import json
from datetime import datetime

class HPScrapingClient:
    """Cliente para interagir com a API do Sistema HP"""
    
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
    
    def start_scraping(self, query, max_items=50, collect_reviews=False, **kwargs):
        """Inicia um job de scraping"""
        data = {
            "query": query,
            "max_items": max_items,
            "collect_reviews": collect_reviews,
            **kwargs
        }
        
        response = requests.post(f"{self.base_url}/scraping/start", json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['job_id']
            else:
                raise Exception(f"Erro na API: {result.get('error')}")
        else:
            raise Exception(f"Erro HTTP: {response.status_code}")
    
    def get_job_status(self, job_id):
        """Obtém status de um job"""
        response = requests.get(f"{self.base_url}/jobs/{job_id}/status")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result
            else:
                raise Exception(f"Erro na API: {result.get('error')}")
        else:
            raise Exception(f"Erro HTTP: {response.status_code}")
    
    def wait_for_completion(self, job_id, timeout=300):
        """Aguarda conclusão de um job"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            print(f"📊 Status: {status['status']} ({status['progress']}%) - "
                  f"{status['produtos_coletados']} produtos")
            
            if status['status'] == 'concluido':
                return status
            elif status['status'] == 'erro':
                raise Exception(f"Job falhou: {status.get('error_message')}")
            
            time.sleep(5)
        
        raise Exception("Timeout aguardando conclusão do job")
    
    def list_datasets(self):
        """Lista datasets disponíveis"""
        response = requests.get(f"{self.base_url}/datasets")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result['datasets']
            else:
                raise Exception(f"Erro na API: {result.get('error')}")
        else:
            raise Exception(f"Erro HTTP: {response.status_code}")
    
    def download_dataset(self, filename, save_path=None):
        """Faz download de um dataset"""
        if not save_path:
            save_path = filename
        
        response = requests.get(f"{self.base_url}/datasets/{filename}/download")
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return save_path
        else:
            raise Exception(f"Erro no download: {response.status_code}")

def exemplo_basico():
    """Exemplo básico de uso"""
    print("🔥 EXEMPLO BÁSICO - SCRAPING SIMPLES")
    print("=" * 50)
    
    client = HPScrapingClient()
    
    try:
        # Iniciar scraping
        print("1️⃣ Iniciando scraping...")
        job_id = client.start_scraping(
            query="cartucho hp 664",
            max_items=20,
            collect_reviews=False,
            sort_by="price_asc"
        )
        print(f"✅ Job iniciado: {job_id}")
        
        # Aguardar conclusão
        print("\n2️⃣ Aguardando conclusão...")
        result = client.wait_for_completion(job_id)
        print(f"✅ Job concluído! {result['produtos_coletados']} produtos coletados")
        
        # Verificar arquivos gerados
        if result.get('result_files'):
            print("\n3️⃣ Arquivos gerados:")
            for file_info in result['result_files']:
                size_mb = file_info['size'] / (1024 * 1024)
                print(f"   📄 {file_info['filename']} ({size_mb:.1f} MB)")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

def exemplo_com_reviews():
    """Exemplo com coleta de reviews"""
    print("\n🔥 EXEMPLO AVANÇADO - COM REVIEWS")
    print("=" * 50)
    
    client = HPScrapingClient()
    
    try:
        # Iniciar scraping com reviews
        print("1️⃣ Iniciando scraping com reviews...")
        job_id = client.start_scraping(
            query="toner hp laserjet",
            max_items=10,
            collect_reviews=True,
            max_reviews_per_product=50,
            generate_json=True
        )
        print(f"✅ Job iniciado: {job_id}")
        
        # Monitorar progresso
        print("\n2️⃣ Monitorando progresso...")
        result = client.wait_for_completion(job_id)
        print(f"✅ Job concluído!")
        print(f"   📦 Produtos: {result['produtos_coletados']}")
        print(f"   💬 Reviews: {result['reviews_coletadas']}")
        
        # Download dos arquivos
        print("\n3️⃣ Fazendo download dos arquivos...")
        for file_info in result.get('result_files', []):
            filename = file_info['filename']
            local_path = client.download_dataset(filename)
            print(f"   ⬇️ {local_path} baixado com sucesso")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

def exemplo_gerenciamento():
    """Exemplo de gerenciamento de datasets"""
    print("\n🔥 EXEMPLO DE GERENCIAMENTO")
    print("=" * 50)
    
    client = HPScrapingClient()
    
    try:
        # Listar datasets
        print("1️⃣ Listando datasets disponíveis...")
        datasets = client.list_datasets()
        
        if datasets:
            print(f"✅ {len(datasets)} datasets encontrados:")
            
            total_size = 0
            for dataset in datasets:
                size_mb = dataset['size'] / (1024 * 1024)
                total_size += dataset['size']
                modified = datetime.fromisoformat(dataset['modified'].replace('Z', '+00:00'))
                
                print(f"   📄 {dataset['filename']}")
                print(f"      💾 Tamanho: {size_mb:.1f} MB")
                print(f"      📅 Modificado: {modified.strftime('%d/%m/%Y %H:%M')}")
                print()
            
            total_mb = total_size / (1024 * 1024)
            print(f"📊 Total: {len(datasets)} arquivos, {total_mb:.1f} MB")
            
        else:
            print("📭 Nenhum dataset encontrado")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

def main():
    """Função principal"""
    print("🛡️ SISTEMA DE SCRAPING HP - EXEMPLOS FLASK")
    print("=" * 60)
    print()
    
    # Verificar se servidor está rodando
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        if response.status_code != 200:
            raise Exception("Servidor não respondeu corretamente")
    except:
        print("❌ Servidor Flask não está rodando!")
        print("Execute primeiro: python run_flask.py")
        print("Depois execute: python exemplo_flask.py")
        return
    
    print("✅ Servidor Flask detectado!")
    print()
    
    try:
        # Executar exemplos
        exemplo_basico()
        exemplo_com_reviews()
        exemplo_gerenciamento()
        
        print("\n" + "=" * 60)
        print("🎉 TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO!")
        print()
        print("🌐 Acesse a interface web em: http://localhost:5000")
        print("📚 Documentação da API: API_DOCUMENTATION.md")
        print("🔧 Código fonte: flask_app.py")
        
    except KeyboardInterrupt:
        print("\n⏹️ Execução interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro geral: {str(e)}")

if __name__ == "__main__":
    main()
