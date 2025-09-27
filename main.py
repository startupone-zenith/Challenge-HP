#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Scraping HP - Ponto de Entrada Principal
Versão 2.0 - Estrutura Reorganizada
"""

import sys
import os

# Adicionar src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def run_flask_app():
    """Executar aplicação Flask"""
    from src.web.flask_app import app
    print(">>> Iniciando Flask App - Sistema HP...")
    print(">>> Acesse: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

def run_console_scraping():
    """Executar scraping via console"""
    from src.core import get_scraping_system
    HPScrapingSystem = get_scraping_system()
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema HP Scraping Console')
    parser.add_argument('query', help='Termo de busca')
    parser.add_argument('--max-items', type=int, default=50, help='Máximo de itens')
    parser.add_argument('--detailed', action='store_true', help='Extração detalhada')
    parser.add_argument('--reviews', action='store_true', help='Coletar reviews')
    parser.add_argument('--json', action='store_true', help='Gerar JSON')
    
    args = parser.parse_args()
    
    sistema = HPScrapingSystem()
    
    print(f"[SCRAPING] Coletando produtos para: {args.query}")
    produtos = sistema.executar_scraping_produtos(
        query=args.query,
        max_items=args.max_items,
        detailed_extraction=args.detailed
    )
    
    if produtos:
        if args.reviews:
            print("[REVIEWS] Coletando reviews...")
            sistema.coletar_reviews_para_produtos()
        
        print("[DATASET] Gerando datasets...")
        csv_file = sistema.gerar_dataset_csv()
        print(f"[SUCESSO] CSV: {csv_file}")
        
        if args.json:
            json_file = sistema.gerar_dataset_json()
            print(f"[SUCESSO] JSON: {json_file}")
        
        print(f"[CONCLUIDO] {len(produtos)} produtos coletados.")
    else:
        print("[ERRO] Nenhum produto foi coletado.")

def main():
    """Função principal"""
    if len(sys.argv) == 1:
        # Sem argumentos - executar Flask
        run_flask_app()
    else:
        # Com argumentos - executar console
        run_console_scraping()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[PARADO] Execução interrompida pelo usuário")
    except Exception as e:
        print(f"\n[ERRO] {e}")
        sys.exit(1)
