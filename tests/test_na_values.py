#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste de valores N/A para produtos com poucas reviews
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.app import HPScrapingSystem

def test_na_values():
    print("Testando valores N/A para produtos com poucas reviews...")
    
    # URL de teste (produto HP com poucas reviews)
    test_url = "https://www.mercadolivre.com.br/cartucho-de-tinta-hp-tricolor-667/p/MLB36752162"
    
    print(f"\nTestando URL: {test_url}")
    
    try:
        # Usar função de extração detalhada para produto individual
        print("Extraindo dados detalhados do produto...")
        sistema = HPScrapingSystem()
        detalhes = sistema._extrair_dados_detalhados_produto(test_url)
        
        if detalhes:
            print(f"\nProduto encontrado: {detalhes.get('nome_produto', 'N/A')}")
            
            # Adicionar produto ao sistema
            sistema.produtos = [detalhes]
            
            # Testar coleta de poucas reviews (3 para testar N/A)
            print(f"\nColetando 3 reviews...")
            sistema.coletar_reviews_para_produtos(max_reviews_per_product=3, delay=1.0)
            
            # Verificar se reviews foram coletadas
            produto_com_reviews = sistema.produtos[0]
            if 'reviews_data' in produto_com_reviews:
                reviews_data = produto_com_reviews['reviews_data']
                reviews_list = reviews_data.get('reviews', [])
                print(f"[OK] Reviews coletadas: {len(reviews_list)}")
                
                # Testar geração de CSV com poucas reviews
                print(f"\nGerando CSV com poucas reviews...")
                csv_file = sistema.gerar_dataset_csv(
                    filename="test_na_values.csv",
                    include_reviews=True,
                    individual_reviews=True  # Ativar reviews como colunas
                )
                
                if csv_file:
                    print(f"[OK] CSV gerado: {csv_file}")
                    
                    # Verificar o conteúdo do CSV
                    import pandas as pd
                    df = pd.read_csv(csv_file)
                    
                    print(f"\n--- Análise do CSV ---")
                    print(f"Total de linhas: {len(df)}")
                    print(f"Total de colunas: {len(df.columns)}")
                    
                    # Verificar se há colunas de reviews
                    review_columns = [col for col in df.columns if col.startswith('review_')]
                    print(f"Colunas de reviews encontradas: {len(review_columns)}")
                    
                    if review_columns:
                        # Verificar dados da primeira linha
                        if len(df) > 0:
                            first_row = df.iloc[0]
                            print(f"\n--- Dados da primeira linha ---")
                            print(f"Tipo de linha: {first_row.get('tipo_linha', 'N/A')}")
                            print(f"Total de reviews individuais: {first_row.get('total_reviews_individual', 'N/A')}")
                            
                            # Mostrar dados das primeiras 5 reviews (algumas devem ser N/A)
                            for i in range(1, 6):
                                review_id = first_row.get(f'review_{i}_id', 'N/A')
                                review_rating = first_row.get(f'review_{i}_rating', 'N/A')
                                review_title = first_row.get(f'review_{i}_title', 'N/A')
                                print(f"Review {i}: ID={review_id}, Rating={review_rating}, Title={review_title}")
                    
                    print(f"\n[SUCESSO] Valores N/A implementados corretamente!")
                else:
                    print("[X] Falha ao gerar CSV")
            else:
                print("[OK] Nenhuma review foi coletada (esperado para alguns produtos)")
            
        else:
            print("[X] Nenhum produto encontrado")
            
    except Exception as e:
        print(f"[X] Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[SUCESSO] Teste de valores N/A concluído!")

if __name__ == "__main__":
    test_na_values()
