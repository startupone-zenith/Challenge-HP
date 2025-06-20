# -*- coding: utf-8 -*-
"""
Script Orquestrador do Pipeline de Detecção
===========================================

Este script executa a sequência completa de processos para a detecção de
anúncios de cartuchos HP falsificados:

1.  **Coleta de Links**: Executa `generate_hp_links.py` para buscar anúncios
    no Mercado Livre e salvar as URLs em um arquivo de texto.
2.  **Extração de Dados**: Executa `generativa_sprint1.py`, passando o arquivo
    de URLs gerado para extrair dados estruturados de cada anúncio.
3.  **Classificação**: Executa `sprint2_llm_classifier copy.py` para analisar os
    dados extraídos, classificar os anúncios e gerar o relatório final.

O script foi projetado para ser o ponto de entrada (ENTRYPOINT) do container Docker,
automatizando todo o fluxo com um único comando.
"""
import subprocess
import sys
import os
from pathlib import Path
import glob

def find_latest_file(directory: str, pattern: str) -> str:
    """Encontra o arquivo mais recente em um diretório com base em um padrão."""
    try:
        list_of_files = glob.glob(os.path.join(directory, pattern))
        if not list_of_files:
            return None
        latest_file = max(list_of_files, key=os.path.getctime)
        return latest_file
    except Exception as e:
        print(f"❌ Erro ao procurar o arquivo mais recente: {e}")
        return None

def run_command(command: list):
    """Executa um comando no shell e exibe a saída em tempo real."""
    print(f"\n▶️  Executando comando: {' '.join(command)}")
    print("-" * 50)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode != 0:
            print(f"❌ Erro: O comando {' '.join(command)} retornou o código de saída {process.returncode}")
            return False
        
        print("-" * 50)
        print(f"✅ Comando {' '.join(command)} concluído com sucesso.")
        return True

    except FileNotFoundError:
        print(f"❌ Erro: O comando '{command[1]}' não foi encontrado. Verifique se o script existe e tem permissão de execução.")
        return False
    except Exception as e:
        print(f"❌ Uma exceção inesperada ocorreu: {e}")
        return False

def main():
    """Executa o pipeline completo."""
    print("🚀 INICIANDO O PIPELINE DE DETECÇÃO DE FALSIFICAÇÃO 🚀")
    
    # --- Passo 1: Gerar Links de Anúncios ---
    print("\n[PASSO 1 de 3] Coletando links de anúncios do Mercado Livre...")
    if not run_command(["python", "generate_hp_links.py"]):
        sys.exit(1) # Termina o pipeline se o passo 1 falhar

    # --- Passo 2: Extrair Dados Estruturados ---
    print("\n[PASSO 2 de 3] Extraindo dados estruturados dos links coletados...")
    
    # Encontra o arquivo de URLs mais recente gerado pelo passo 1
    data_dir = "data"
    url_file_pattern = "hp_cartridge_urls_*.txt"
    latest_url_file = find_latest_file(data_dir, url_file_pattern)
    
    if not latest_url_file:
        print(f"❌ Erro fatal: Nenhum arquivo de URL ('{url_file_pattern}') encontrado no diretório '{data_dir}'.")
        print("O script 'generate_hp_links.py' deveria ter criado este arquivo.")
        sys.exit(1)
        
    print(f"ℹ️  Usando o arquivo de links mais recente: {latest_url_file}")
    
    if not run_command(["python", "generativa_sprint1.py", latest_url_file]):
        sys.exit(1) # Termina o pipeline se o passo 2 falhar
        
    # --- Passo 3: Classificar Anúncios e Gerar Relatório ---
    print("\n[PASSO 3 de 3] Classificando anúncios e gerando relatórios de análise...")
    if not run_command(["python", "sprint2_llm_classifier copy.py"]):
        sys.exit(1) # Termina o pipeline se o passo 3 falhar

    print("\n🎉 PIPELINE CONCLUÍDO COM SUCESSO! 🎉")
    print("Verifique a pasta 'output/' para os resultados e relatórios.")

if __name__ == "__main__":
    main() 