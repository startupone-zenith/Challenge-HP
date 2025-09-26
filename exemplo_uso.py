#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do Sistema de Scraping HP
"""

from app import HPScrapingSystem

def exemplo_basico():
    """Exemplo básico de uso do sistema"""
    print("=== EXEMPLO BÁSICO - SCRAPING DE PRODUTOS ===")
    
    # Criar instância do sistema
    sistema = HPScrapingSystem()
    
    # Executar scraping de produtos
    produtos = sistema.executar_scraping_produtos(
        query="cartucho hp 664",
        max_items=10,
        extract_images=False
    )
    
    if produtos:
        print(f"✅ Coletados {len(produtos)} produtos")
        
        # Gerar dataset CSV
        csv_file = sistema.gerar_dataset_csv("exemplo_produtos.csv", include_reviews=False)
        print(f"✅ Dataset CSV gerado: {csv_file}")
        
        # Exibir estatísticas
        sistema.estatisticas_coleta()
    else:
        print("❌ Nenhum produto foi coletado")

def exemplo_com_reviews():
    """Exemplo com coleta de reviews"""
    print("\n=== EXEMPLO COM REVIEWS ===")
    
    # Criar instância do sistema
    sistema = HPScrapingSystem()
    
    # Executar scraping de produtos
    produtos = sistema.executar_scraping_produtos(
        query="toner hp laserjet",
        max_items=5,
        sort_by='price_asc'
    )
    
    if produtos:
        print(f"✅ Coletados {len(produtos)} produtos")
        
        # Coletar reviews para os produtos
        sistema.coletar_reviews_para_produtos(max_reviews_per_product=50)
        
        # Gerar dataset com reviews
        csv_file = sistema.gerar_dataset_csv("exemplo_com_reviews.csv", include_reviews=True)
        json_file = sistema.gerar_dataset_json("exemplo_com_reviews.json")
        
        print(f"✅ Dataset CSV gerado: {csv_file}")
        print(f"✅ Dataset JSON gerado: {json_file}")
        
        # Exibir estatísticas
        sistema.estatisticas_coleta()
    else:
        print("❌ Nenhum produto foi coletado")

if __name__ == "__main__":
    # Executar exemplos
    exemplo_basico()
    exemplo_com_reviews()
    
    print("\n=== EXEMPLOS CONCLUÍDOS ===")
    print("Verifique os arquivos gerados no diretório atual.")
