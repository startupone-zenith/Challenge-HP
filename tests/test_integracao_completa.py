#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Integração Completa - Sistema HP Challenge
Testa: Scraping + Reviews + CSV + Excel
"""

import sys
import os
import json
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.app import HPScrapingSystem
from src.spiders.mercadolivre_spider_reviews import run_review_spider

def test_integracao_completa():
    """Teste completo de integração"""
    
    print("=" * 70)
    print("TESTE DE INTEGRACAO COMPLETA - SISTEMA HP CHALLENGE")
    print("=" * 70)
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    try:
        # 1. Criar instância do sistema
        print("1. Inicializando sistema...")
        sistema = HPScrapingSystem()
        
        # 2. Executar scraping de produtos
        print("2. Executando scraping de produtos...")
        query = "cartucho hp 664"
        max_items = 5  # Pequeno para teste rápido
        
        print(f"   Query: {query}")
        print(f"   Max items: {max_items}")
        
        produtos = sistema.executar_scraping_produtos(
            query=query,
            max_items=max_items,
            extract_images=True,
            sort_by='relevance',
            condition='all'
        )
        
        if not produtos:
            print("   [ERRO] Nenhum produto coletado")
            return
        
        print(f"   [OK] {len(produtos)} produtos coletados")
        
        # 3. Coletar reviews para cada produto
        print("\n3. Coletando reviews dos produtos...")
        for i, produto in enumerate(produtos, 1):
            product_id = produto.get('ID_PRODUTO')
            titulo = produto.get('TITULO PRODUTO', 'N/A')
            
            print(f"   {i}. {titulo[:50]}...")
            print(f"      ID: {product_id}")
            
            if product_id:
                try:
                    # Coletar reviews
                    reviews_data = run_review_spider(product_id, max_reviews=20)
                    
                    if reviews_data and reviews_data.get('reviews'):
                        # Adicionar dados de reviews ao produto
                        produto['reviews_data'] = reviews_data
                        produto['tem_reviews'] = True
                        
                        metadata = reviews_data['extraction_metadata']
                        statistics = reviews_data['statistics']
                        
                        print(f"      [OK] {metadata['total_reviews']} reviews coletadas")
                        print(f"      [COM] {metadata['reviews_with_comments']} com comentarios")
                        print(f"      [RATING] Rating medio: {statistics['average_rating']}")
                    else:
                        print(f"      [ERRO] Nenhuma review encontrada")
                        produto['tem_reviews'] = False
                        
                except Exception as e:
                    print(f"      [ERRO] Erro: {e}")
                    produto['tem_reviews'] = False
            else:
                print(f"      [ERRO] ID do produto nao encontrado")
                produto['tem_reviews'] = False
        
        # 4. Gerar datasets
        print("\n4. Gerando datasets...")
        
        # CSV com reviews
        print("   Gerando CSV com reviews...")
        csv_file = sistema.gerar_dataset_csv(include_reviews=True)
        
        if csv_file:
            print(f"   [OK] CSV gerado: {csv_file}")
            
            # Verificar se o arquivo foi criado e tem conteúdo
            if os.path.exists(csv_file):
                with open(csv_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    print(f"   [INFO] Linhas no CSV: {len(lines)} (incluindo cabecalho)")
                    
                    # Verificar se tem colunas de comentários
                    if len(lines) > 0:
                        header = lines[0]
                        if 'comentarios_reviews' in header:
                            print(f"   [OK] Coluna de comentarios encontrada no CSV")
                        else:
                            print(f"   [ERRO] Coluna de comentarios NAO encontrada no CSV")
        else:
            print(f"   [ERRO] Falha ao gerar CSV")
        
        # Verificar se Excel foi gerado
        excel_file = csv_file.replace('.csv', '.xlsx') if csv_file else None
        if excel_file and os.path.exists(excel_file):
            print(f"   [OK] Excel gerado: {excel_file}")
        else:
            print(f"   [ERRO] Excel nao foi gerado")
        
        # 5. Análise dos dados
        print("\n5. Analise dos dados coletados...")
        
        produtos_com_reviews = sum(1 for p in produtos if p.get('tem_reviews', False))
        total_comentarios = 0
        
        for produto in produtos:
            if produto.get('tem_reviews', False):
                reviews_data = produto.get('reviews_data', {})
                reviews = reviews_data.get('reviews', [])
                comentarios = [r for r in reviews if r.get('has_comment', False)]
                total_comentarios += len(comentarios)
        
        print(f"   [INFO] Produtos com reviews: {produtos_com_reviews}/{len(produtos)}")
        print(f"   [COM] Total de comentarios coletados: {total_comentarios}")
        
        # Mostrar alguns exemplos de comentários
        print(f"\n6. Exemplos de comentarios coletados:")
        comentarios_exibidos = 0
        for produto in produtos:
            if produto.get('tem_reviews', False) and comentarios_exibidos < 3:
                reviews_data = produto.get('reviews_data', {})
                reviews = reviews_data.get('reviews', [])
                comentarios = [r for r in reviews if r.get('has_comment', False)]
                
                if comentarios:
                    comentario = comentarios[0]  # Primeiro comentário
                    print(f"\n   Produto: {produto.get('TITULO PRODUTO', 'N/A')[:50]}...")
                    print(f"   Rating: {comentario.get('rating', 0)} estrelas")
                    print(f"   Comentario: {comentario.get('comment', '')[:100]}...")
                    print(f"   Likes: {comentario.get('likes', 0)}")
                    comentarios_exibidos += 1
        
        print(f"\n" + "=" * 70)
        print("TESTE CONCLUIDO COM SUCESSO!")
        print("=" * 70)
        print(f"Fim: {datetime.now().strftime('%H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"\n[ERRO] Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_slider_html():
    """Teste do slider HTML (verificação manual)"""
    
    print("\n" + "=" * 70)
    print("TESTE DO SLIDER HTML")
    print("=" * 70)
    print("Para testar o slider:")
    print("1. Execute: python main.py")
    print("2. Acesse: http://localhost:5000")
    print("3. Vá para a página de Scraping")
    print("4. Teste o slider 'Quantidade de Produtos'")
    print("5. Verifique se vai de 1 em 1 (não de 10 em 10)")
    print("6. Teste tanto o slider quanto o input numérico")
    print("=" * 70)

if __name__ == "__main__":
    print("INICIANDO TESTES DE INTEGRACAO")
    print()
    
    # Teste principal
    sucesso = test_integracao_completa()
    
    # Instruções para teste do slider
    test_slider_html()
    
    if sucesso:
        print("\nTODOS OS TESTES CONCLUIDOS COM SUCESSO!")
    else:
        print("\nALGUNS TESTES FALHARAM!")
        sys.exit(1)
