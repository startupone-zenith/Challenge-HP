#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de uso do sistema com URL customizada do Mercado Livre
Demonstra como usar URLs específicas como base para scraping
"""

from app import HPScrapingSystem
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def exemplo_url_customizada():
    """
    Exemplo usando a URL específica fornecida para cartuchos HP originais
    """
    print("=== EXEMPLO: SCRAPING COM URL CUSTOMIZADA ===")
    print()
    
    # URL específica do Mercado Livre para cartuchos HP originais
    url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True#applied_filter_id%3DINK_CARTRIDGE_TYPE%26applied_filter_name%3DTipo+de+cartucho%26applied_filter_order%3D3%26applied_value_id%3D281072%26applied_value_name%3DOriginal%26applied_value_order%3D1%26applied_value_results%3D131%26is_custom%3Dfalse"
    
    print(f"URL customizada: {url_customizada}")
    print()
    
    # Criar sistema
    sistema = HPScrapingSystem()
    
    try:
        print("1. Executando scraping com URL customizada...")
        
        # Usar a URL customizada - note que ainda precisamos fornecer um query para compatibilidade
        produtos = sistema.executar_scraping_produtos(
            query="Cartucho HP Original",  # Query para logs e compatibilidade
            max_items=10,
            extract_images=True,
            custom_url=url_customizada  # Nova funcionalidade!
        )
        
        if produtos:
            print(f"✓ Coletados {len(produtos)} produtos usando URL customizada")
            print()
            
            # Mostrar alguns exemplos
            print("Exemplos de produtos encontrados:")
            for i, produto in enumerate(produtos[:3], 1):
                print(f"{i}. {produto.get('title', 'N/A')}")
                print(f"   Preço: {produto.get('price', 'N/A')}")
                print(f"   Link: {produto.get('link', 'N/A')}")
                print()
            
            # Gerar dataset
            print("2. Gerando datasets...")
            csv_file = sistema.gerar_dataset_csv(include_reviews=False)
            json_file = sistema.gerar_dataset_json()
            
            if csv_file:
                print(f"✓ Dataset CSV gerado: {csv_file}")
            if json_file:
                print(f"✓ Dataset JSON gerado: {json_file}")
                
            # Estatísticas
            print("\n3. Estatísticas:")
            sistema.estatisticas_coleta()
            
        else:
            print("✗ Nenhum produto foi coletado")
            
    except Exception as e:
        print(f"✗ Erro durante execução: {str(e)}")

def exemplo_comparacao():
    """
    Exemplo comparando busca normal vs URL customizada
    """
    print("\n" + "=" * 60)
    print("=== COMPARAÇÃO: BUSCA NORMAL vs URL CUSTOMIZADA ===")
    print()
    
    sistema1 = HPScrapingSystem()
    sistema2 = HPScrapingSystem()
    
    try:
        print("1. Busca normal...")
        produtos_normal = sistema1.executar_scraping_produtos(
            query="Cartucho HP",
            max_items=5,
            extract_images=False
        )
        
        print("2. Busca com URL customizada...")
        url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"
        
        produtos_customizada = sistema2.executar_scraping_produtos(
            query="Cartucho HP Original",
            max_items=5,
            extract_images=False,
            custom_url=url_customizada
        )
        
        print(f"\nResultados:")
        print(f"- Busca normal: {len(produtos_normal) if produtos_normal else 0} produtos")
        print(f"- URL customizada: {len(produtos_customizada) if produtos_customizada else 0} produtos")
        
        if produtos_normal and produtos_customizada:
            print("\nPrimeiros resultados de cada método:")
            print(f"Normal: {produtos_normal[0].get('title', 'N/A')[:50]}...")
            print(f"Customizada: {produtos_customizada[0].get('title', 'N/A')[:50]}...")
        
    except Exception as e:
        print(f"✗ Erro durante comparação: {str(e)}")

if __name__ == "__main__":
    print("🛡️ SISTEMA DE SCRAPING HP - EXEMPLO URL CUSTOMIZADA")
    print("=" * 60)
    
    # Exemplo principal
    exemplo_url_customizada()
    
    # Exemplo de comparação
    exemplo_comparacao()
    
    print("\n" + "=" * 60)
    print("✓ Exemplos concluídos!")
    print("\nVantagens da URL customizada:")
    print("- Usa filtros específicos já aplicados no Mercado Livre")
    print("- Pode incluir filtros complexos não disponíveis via parâmetros")
    print("- Mantém a estrutura de navegação do site")
    print("- Permite usar URLs de categorias específicas")
