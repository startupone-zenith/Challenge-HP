#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do Extrator de Comentários de Reviews - MercadoLivre
"""

import sys
import os
import json
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.spiders.mercadolivre_spider_reviews import extract_reviews, run_review_spider

def test_reviews_extractor():
    """Testar o extrator de reviews com o exemplo fornecido"""
    
    print("=" * 60)
    print("TESTE DO EXTRATOR DE COMENTARIOS DE REVIEWS")
    print("=" * 60)
    
    # ID do produto do exemplo fornecido
    product_id = "MLB6125886"
    max_reviews = 50  # Limite menor para teste rápido
    
    print(f"Produto: {product_id}")
    print(f"Limite: {max_reviews} reviews")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    try:
        # Executar extração
        print("Iniciando extracao...")
        result = extract_reviews(product_id, max_reviews)
        
        if result and result.get('reviews'):
            # Exibir estatísticas
            metadata = result['extraction_metadata']
            statistics = result['statistics']
            
            print("\n" + "=" * 40)
            print("RESULTADOS DA EXTRACAO")
            print("=" * 40)
            print(f"Total de reviews: {metadata['total_reviews']}")
            print(f"Reviews com comentários: {metadata['reviews_with_comments']}")
            print(f"Reviews com imagens: {metadata['reviews_with_images']}")
            print(f"Cobertura de comentários: {metadata['comment_coverage']:.1f}%")
            print(f"Cobertura de imagens: {metadata['image_coverage']:.1f}%")
            print(f"Rating medio: {statistics['average_rating']}")
            print(f"Avaliacoes positivas: {statistics['positive_reviews']}")
            print(f"Avaliacoes negativas: {statistics['negative_reviews']}")
            print(f"Avaliacoes neutras: {statistics['neutral_reviews']}")
            
            # Exibir distribuição de estrelas
            print("\n" + "=" * 40)
            print("DISTRIBUICAO DE ESTRELAS")
            print("=" * 40)
            rating_dist = statistics['rating_distribution']
            for stars in range(5, 0, -1):
                count = rating_dist[stars]
                percentage = (count / metadata['total_reviews'] * 100) if metadata['total_reviews'] > 0 else 0
                bar = "*" * int(percentage / 2)  # Barra visual
                print(f"{stars} estrelas: {count:3d} ({percentage:5.1f}%) {bar}")
            
            # Exibir alguns exemplos de reviews com comentários
            print("\n" + "=" * 40)
            print("EXEMPLOS DE COMENTARIOS")
            print("=" * 40)
            
            reviews_with_comments = [r for r in result['reviews'] if r.get('has_comment', False)]
            
            if reviews_with_comments:
                print(f"Mostrando {min(3, len(reviews_with_comments))} exemplos:")
                print()
                
                for i, review in enumerate(reviews_with_comments[:3], 1):
                    print(f"--- Exemplo {i} ---")
                    print(f"Rating: {review['rating']}")
                    print(f"Titulo: {review['title']}")
                    print(f"Comentario: {review['comment'][:200]}{'...' if len(review['comment']) > 200 else ''}")
                    print(f"Data: {review['date']}")
                    print(f"Likes: {review['likes']}")
                    print(f"Tem imagens: {'Sim' if review['has_images'] else 'Nao'}")
                    print()
            else:
                print("Nenhuma review com comentario encontrada")
            
            # Salvar resultado em arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"teste_reviews_{product_id}_{timestamp}.json"
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"Resultado salvo em: {filename}")
            except Exception as e:
                print(f"Erro ao salvar arquivo: {e}")
            
            print("\n" + "=" * 40)
            print("TESTE CONCLUIDO COM SUCESSO!")
            print("=" * 40)
            
        else:
            print("Nenhuma review foi extraida")
            print("Verifique se o ID do produto esta correto e se ha reviews disponiveis")
    
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

def test_with_different_limits():
    """Testar com diferentes limites de reviews"""
    
    print("\n" + "=" * 60)
    print("TESTE COM DIFERENTES LIMITES")
    print("=" * 60)
    
    product_id = "MLB6125886"
    limits = [10, 30, 60, 100]
    
    for limit in limits:
        print(f"\nTestando com limite: {limit} reviews")
        try:
            result = extract_reviews(product_id, limit)
            if result and result.get('reviews'):
                total = result['extraction_metadata']['total_reviews']
                with_comments = result['extraction_metadata']['reviews_with_comments']
                print(f"   Coletadas: {total} reviews ({with_comments} com comentarios)")
            else:
                print(f"   Falha na coleta")
        except Exception as e:
            print(f"   Erro: {e}")

if __name__ == "__main__":
    # Teste principal
    test_reviews_extractor()
    
    # Teste com diferentes limites
    test_with_different_limits()
    
    print(f"\nFim: {datetime.now().strftime('%H:%M:%S')}")
    print("Todos os testes concluidos!")
