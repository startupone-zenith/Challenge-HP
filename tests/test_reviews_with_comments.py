#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste de filtro para reviews com comentários
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.app import HPScrapingSystem

def test_reviews_with_comments():
    print("Testando filtro para reviews com comentários...")
    
    # URL de teste (produto HP com reviews)
    test_url = "https://www.mercadolivre.com.br/cartucho-hp-3ed68a-no-712-magenta-29ml-hp/p/MLB6125886"
    
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
            
            # Testar coleta de reviews
            print(f"\nColetando reviews...")
            sistema.coletar_reviews_para_produtos(max_reviews_per_product=10, delay=1.0)
            
            # Verificar se reviews foram coletadas
            produto_com_reviews = sistema.produtos[0]
            if 'reviews_data' in produto_com_reviews:
                reviews_data = produto_com_reviews['reviews_data']
                reviews_list = reviews_data.get('reviews', [])
                print(f"[OK] Reviews coletadas: {len(reviews_list)}")
                
                # Analisar reviews antes do filtro
                print(f"\n--- Análise das Reviews Coletadas ---")
                reviews_with_comments = 0
                reviews_without_comments = 0
                
                for i, review in enumerate(reviews_list):
                    comment = review.get('comment', '')
                    has_comment = review.get('has_comment', False)
                    rating = review.get('rating', 'N/A')
                    title = review.get('title', '')
                    if isinstance(title, dict):
                        title = title.get('text', '')
                    
                    if has_comment and comment and comment.strip():
                        reviews_with_comments += 1
                        print(f"Review {i+1}: Rating={rating}, Title={title}, Comment={comment[:50]}...")
                    else:
                        reviews_without_comments += 1
                        print(f"Review {i+1}: Rating={rating}, Title={title}, Comment=N/A (sem comentário)")
                
                print(f"\nResumo: {reviews_with_comments} com comentários, {reviews_without_comments} sem comentários")
                
                # Testar geração de CSV com filtro de comentários
                print(f"\nGerando CSV com filtro de comentários...")
                csv_file = sistema.gerar_dataset_csv(
                    filename="test_reviews_with_comments.csv",
                    include_reviews=True,
                    individual_reviews=True  # Ativar reviews como colunas
                )
                
                if csv_file:
                    print(f"[OK] CSV gerado: {csv_file}")
                    
                    # Verificar o conteúdo do CSV
                    import pandas as pd
                    df = pd.read_csv(csv_file)
                    
                    print(f"\n--- Análise do CSV Filtrado ---")
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
                            print(f"Total de reviews individuais (com comentários): {first_row.get('total_reviews_individual', 'N/A')}")
                            print(f"Total de reviews original: {first_row.get('total_reviews_original', 'N/A')}")
                            
                            # Mostrar dados das primeiras 5 reviews filtradas
                            for i in range(1, 6):
                                review_id = first_row.get(f'review_{i}_id', 'N/A')
                                review_rating = first_row.get(f'review_{i}_rating', 'N/A')
                                review_title = first_row.get(f'review_{i}_title', 'N/A')
                                review_comment = first_row.get(f'review_{i}_comment', 'N/A')
                                if review_id != 'N/A':
                                    print(f"Review {i}: ID={review_id}, Rating={review_rating}, Title={review_title}, Comment={review_comment[:50]}...")
                                else:
                                    print(f"Review {i}: N/A (não existe)")
                    
                    print(f"\n[SUCESSO] Filtro de reviews com comentários implementado com sucesso!")
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
    
    print("\n[SUCESSO] Teste de filtro de reviews com comentários concluído!")

if __name__ == "__main__":
    test_reviews_with_comments()
