#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo de Uso do Extrator de Comentários de Reviews
Integração com o Sistema HP Challenge
"""

import sys
import os
import json
from datetime import datetime

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.spiders.mercadolivre_spider_reviews import extract_reviews, run_review_spider

def exemplo_basico():
    """Exemplo básico de uso do extrator"""
    
    print("=" * 60)
    print("📝 EXEMPLO BÁSICO - EXTRATOR DE REVIEWS")
    print("=" * 60)
    
    # ID do produto do exemplo fornecido
    product_id = "MLB6125886"
    
    print(f"🔍 Extraindo reviews do produto: {product_id}")
    print("⏳ Aguarde...")
    
    # Extrair reviews (limite de 30 para exemplo rápido)
    result = extract_reviews(product_id, max_reviews=30)
    
    if result and result.get('reviews'):
        print(f"\n✅ Sucesso! {len(result['reviews'])} reviews coletadas")
        
        # Mostrar algumas estatísticas
        metadata = result['extraction_metadata']
        print(f"💬 Reviews com comentários: {metadata['reviews_with_comments']}")
        print(f"📸 Reviews com imagens: {metadata['reviews_with_images']}")
        print(f"⭐ Rating médio: {result['statistics']['average_rating']}")
        
        # Mostrar primeiro comentário como exemplo
        reviews_with_comments = [r for r in result['reviews'] if r.get('has_comment', False)]
        if reviews_with_comments:
            first_review = reviews_with_comments[0]
            print(f"\n📖 Primeiro comentário encontrado:")
            print(f"   Rating: {first_review['rating']} ⭐")
            print(f"   Título: {first_review['title']}")
            print(f"   Comentário: {first_review['comment'][:100]}...")
    else:
        print("❌ Nenhuma review foi extraída")

def exemplo_integracao_sistema():
    """Exemplo de integração com o sistema existente"""
    
    print("\n" + "=" * 60)
    print("🔗 EXEMPLO DE INTEGRAÇÃO COM SISTEMA EXISTENTE")
    print("=" * 60)
    
    # Simular dados de produtos coletados pelo sistema principal
    produtos_coletados = [
        {
            'ID_PRODUTO': 'MLB6125886',
            'TITULO PRODUTO': 'Cartucho HP 3ed68a Nº 712 Magenta 29ml',
            'LINK': 'https://produto.mercadolivre.com.br/MLB-6125886-...',
            'PREÇO': 'R$ 89,90'
        },
        {
            'ID_PRODUTO': 'MLB1234567',
            'TITULO PRODUTO': 'Cartucho HP Preto 29ml',
            'LINK': 'https://produto.mercadolivre.com.br/MLB-1234567-...',
            'PREÇO': 'R$ 75,50'
        }
    ]
    
    print(f"📦 Processando {len(produtos_coletados)} produtos...")
    
    for i, produto in enumerate(produtos_coletados, 1):
        product_id = produto['ID_PRODUTO']
        titulo = produto['TITULO PRODUTO']
        
        print(f"\n{i}. {titulo}")
        print(f"   ID: {product_id}")
        
        try:
            # Usar função de compatibilidade do sistema
            reviews_data = run_review_spider(product_id, max_reviews=20)
            
            if reviews_data and reviews_data.get('reviews'):
                metadata = reviews_data['extraction_metadata']
                statistics = reviews_data['statistics']
                
                print(f"   ✅ {metadata['total_reviews']} reviews coletadas")
                print(f"   💬 {metadata['reviews_with_comments']} com comentários")
                print(f"   ⭐ Rating: {statistics['average_rating']}")
                
                # Adicionar dados de reviews ao produto
                produto['reviews_data'] = reviews_data
                produto['tem_reviews'] = True
                
            else:
                print(f"   ❌ Nenhuma review encontrada")
                produto['tem_reviews'] = False
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            produto['tem_reviews'] = False
    
    # Mostrar resumo final
    produtos_com_reviews = sum(1 for p in produtos_coletados if p.get('tem_reviews', False))
    print(f"\n📊 Resumo: {produtos_com_reviews}/{len(produtos_coletados)} produtos com reviews")

def exemplo_analise_comentarios():
    """Exemplo de análise dos comentários extraídos"""
    
    print("\n" + "=" * 60)
    print("🔍 EXEMPLO DE ANÁLISE DE COMENTÁRIOS")
    print("=" * 60)
    
    product_id = "MLB6125886"
    
    print(f"🔍 Analisando comentários do produto: {product_id}")
    
    # Extrair reviews
    result = extract_reviews(product_id, max_reviews=50)
    
    if not result or not result.get('reviews'):
        print("❌ Nenhuma review encontrada para análise")
        return
    
    reviews = result['reviews']
    reviews_with_comments = [r for r in reviews if r.get('has_comment', False)]
    
    print(f"📊 Total de reviews: {len(reviews)}")
    print(f"💬 Reviews com comentários: {len(reviews_with_comments)}")
    
    if not reviews_with_comments:
        print("❌ Nenhum comentário encontrado para análise")
        return
    
    # Análise de sentimento simples (baseada em palavras-chave)
    palavras_positivas = ['excelente', 'bom', 'ótimo', 'qualidade', 'recomendo', 'satisfeito', 'perfeito']
    palavras_negativas = ['ruim', 'péssimo', 'problema', 'defeito', 'não recomendo', 'decepcionado']
    
    comentarios_positivos = 0
    comentarios_negativos = 0
    comentarios_neutros = 0
    
    print(f"\n🔍 Analisando sentimento dos comentários...")
    
    for review in reviews_with_comments:
        comentario = review['comment'].lower()
        
        # Contar palavras positivas e negativas
        pos_count = sum(1 for palavra in palavras_positivas if palavra in comentario)
        neg_count = sum(1 for palavra in palavras_negativas if palavra in comentario)
        
        if pos_count > neg_count:
            comentarios_positivos += 1
        elif neg_count > pos_count:
            comentarios_negativos += 1
        else:
            comentarios_neutros += 1
    
    total_comentarios = len(reviews_with_comments)
    
    print(f"\n📈 Resultados da análise de sentimento:")
    print(f"   😊 Positivos: {comentarios_positivos} ({comentarios_positivos/total_comentarios*100:.1f}%)")
    print(f"   😞 Negativos: {comentarios_negativos} ({comentarios_negativos/total_comentarios*100:.1f}%)")
    print(f"   😐 Neutros: {comentarios_neutros} ({comentarios_neutros/total_comentarios*100:.1f}%)")
    
    # Mostrar alguns comentários por categoria
    print(f"\n📝 Exemplos de comentários por categoria:")
    
    # Positivos
    positivos = [r for r in reviews_with_comments if any(palavra in r['comment'].lower() for palavra in palavras_positivas)]
    if positivos:
        print(f"\n😊 Comentário positivo:")
        exemplo_pos = positivos[0]
        print(f"   Rating: {exemplo_pos['rating']} ⭐")
        print(f"   Comentário: {exemplo_pos['comment'][:150]}...")
    
    # Negativos
    negativos = [r for r in reviews_with_comments if any(palavra in r['comment'].lower() for palavra in palavras_negativas)]
    if negativos:
        print(f"\n😞 Comentário negativo:")
        exemplo_neg = negativos[0]
        print(f"   Rating: {exemplo_neg['rating']} ⭐")
        print(f"   Comentário: {exemplo_neg['comment'][:150]}...")

def exemplo_salvar_dados():
    """Exemplo de como salvar os dados extraídos"""
    
    print("\n" + "=" * 60)
    print("💾 EXEMPLO DE SALVAMENTO DE DADOS")
    print("=" * 60)
    
    product_id = "MLB6125886"
    
    print(f"💾 Extraindo e salvando dados do produto: {product_id}")
    
    # Extrair reviews
    result = extract_reviews(product_id, max_reviews=30)
    
    if not result or not result.get('reviews'):
        print("❌ Nenhuma review encontrada para salvar")
        return
    
    # Salvar em diferentes formatos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. JSON completo
    json_filename = f"reviews_completo_{product_id}_{timestamp}.json"
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON completo salvo: {json_filename}")
    except Exception as e:
        print(f"❌ Erro ao salvar JSON: {e}")
    
    # 2. Apenas comentários (CSV simples)
    csv_filename = f"comentarios_{product_id}_{timestamp}.csv"
    try:
        with open(csv_filename, 'w', encoding='utf-8') as f:
            f.write("review_id,rating,title,comment,date,likes\n")
            
            for review in result['reviews']:
                if review.get('has_comment', False):
                    # Escapar aspas e quebras de linha para CSV
                    comment_escaped = review['comment'].replace('"', '""').replace('\n', ' ').replace('\r', ' ')
                    title_escaped = review['title'].replace('"', '""').replace('\n', ' ').replace('\r', ' ')
                    
                    f.write(f'"{review["review_id"]}",{review["rating"]},"{title_escaped}","{comment_escaped}","{review["date"]}",{review["likes"]}\n')
        
        print(f"✅ Comentários CSV salvo: {csv_filename}")
    except Exception as e:
        print(f"❌ Erro ao salvar CSV: {e}")
    
    # 3. Estatísticas resumidas
    stats_filename = f"estatisticas_{product_id}_{timestamp}.txt"
    try:
        with open(stats_filename, 'w', encoding='utf-8') as f:
            metadata = result['extraction_metadata']
            statistics = result['statistics']
            
            f.write(f"ESTATÍSTICAS DE REVIEWS - {product_id}\n")
            f.write(f"Data de extração: {metadata['extraction_date']}\n")
            f.write(f"Total de reviews: {metadata['total_reviews']}\n")
            f.write(f"Reviews com comentários: {metadata['reviews_with_comments']}\n")
            f.write(f"Reviews com imagens: {metadata['reviews_with_images']}\n")
            f.write(f"Rating médio: {statistics['average_rating']}\n")
            f.write(f"Avaliações positivas: {statistics['positive_reviews']}\n")
            f.write(f"Avaliações negativas: {statistics['negative_reviews']}\n")
            f.write(f"Avaliações neutras: {statistics['neutral_reviews']}\n")
        
        print(f"✅ Estatísticas salvas: {stats_filename}")
    except Exception as e:
        print(f"❌ Erro ao salvar estatísticas: {e}")

def main():
    """Função principal com todos os exemplos"""
    
    print("🚀 EXEMPLOS DE USO DO EXTRATOR DE REVIEWS")
    print("Sistema HP Challenge - MercadoLivre")
    print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # Executar todos os exemplos
        exemplo_basico()
        exemplo_integracao_sistema()
        exemplo_analise_comentarios()
        exemplo_salvar_dados()
        
        print(f"\n🎉 Todos os exemplos executados com sucesso!")
        print(f"⏰ Fim: {datetime.now().strftime('%H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Execução interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
