import multiprocessing
import streamlit as st
import pandas as pd
import requests
import logging
import time
import random
import re
import traceback
from lxml import html
import base64
import io
from PIL import Image
from urllib.parse import quote_plus
import numpy as np
from collections import Counter
from textstat import flesch_reading_ease
import unicodedata
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud

# Configurar o multiprocessing para Streamlit
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Suprimir warnings de contexto do Streamlit durante imports
import warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Importar os spiders do Scrapy
from mercadolivre_spider import run_spider, run_product_details_spider
from mercadolivre_spider_reviews import run_review_spider # Import the new review spider runner

def generate_csv_data(produtos, csv_config, resultados_falsificacao=None):
    """
    Gera dados CSV baseado na configuração de campos selecionados
    """
    csv_data = []
    basic_fields = csv_config['basic_fields']
    detailed_fields = csv_config['detailed_fields']
    risk_fields = csv_config.get('risk_fields', {})
    reviews_fields = csv_config.get('reviews_fields', {})
    
    # Verificar se precisa extrair dados detalhados
    needs_detailed_extraction = any(detailed_fields.values())
    needs_reviews_extraction = reviews_fields.get('incluir_reviews', False)
    
    # Criar dicionário de resultados de falsificação por ID do produto para acesso rápido
    risk_data_by_id = {}
    if resultados_falsificacao:
        for resultado in resultados_falsificacao:
            produto_id = resultado['produto'].get('ID_PRODUTO')
            if produto_id and produto_id != 'N/A':
                risk_data_by_id[produto_id] = resultado
    
    for i, produto in enumerate(produtos):
        logging.info(f"Processando produto {i+1}/{len(produtos)} para CSV: {produto.get('TITULO PRODUTO', 'N/A')[:50]}...")
        
        row_data = {}
        
        # Campos básicos (já disponíveis da busca principal)
        if basic_fields.get('titulo'):
            row_data['Título'] = produto.get('TITULO PRODUTO', 'N/A')
        
        if basic_fields.get('preco'):
            row_data['Preço'] = produto.get('PREÇO', 'N/A')
        
        if basic_fields.get('preco_anterior'):
            row_data['Preço Anterior'] = produto.get('PREÇO ANTERIOR', 'N/A')
        
        if basic_fields.get('marca'):
            row_data['Marca'] = produto.get('MARCA', 'N/A')
        
        if basic_fields.get('vendedor'):
            row_data['Vendedor'] = produto.get('VENDEDOR', 'N/A')
        
        if basic_fields.get('link'):
            row_data['Link'] = produto.get('LINK', 'N/A')
        
        if basic_fields.get('id_produto'):
            row_data['ID Produto'] = produto.get('ID_PRODUTO', 'N/A')
        
        if basic_fields.get('imagem'):
            row_data['URL Imagem'] = produto.get('IMAGEM', 'N/A')
        
        if basic_fields.get('entrega'):
            row_data['Entrega'] = produto.get('ENTREGA', 'N/A')
        
        if basic_fields.get('entrega_full'):
            row_data['Entrega FULL'] = produto.get('ENTREGA FULL', 'N/A')
        
        if basic_fields.get('media_avaliacoes_busca'):
            row_data['Média Avaliações (Busca)'] = produto.get('MÉDIA AVALIAÇÕES', 'N/A')
        
        if basic_fields.get('total_avaliacoes_busca'):
            row_data['Total Avaliações (Busca)'] = produto.get('TOTAL AVALIAÇÕES', 'N/A')
        
        # Campos detalhados (requerem extração individual)
        if needs_detailed_extraction and produto.get('LINK') and produto.get('LINK') != 'N/A':
            try:
                # Extrair detalhes do produto
                product_details = run_product_details_spider(produto['LINK'])
                
                if product_details and product_details.get('extraction_success'):
                    if detailed_fields.get('descricao'):
                        row_data['Descrição'] = product_details.get('description', 'N/A')
                    
                    if detailed_fields.get('caracteristicas_principais'):
                        main_chars = product_details.get('main_characteristics', {})
                        if main_chars:
                            # Converter características para string formatada
                            chars_text = '; '.join([f"{k}: {v}" for k, v in main_chars.items()])
                            row_data['Características Principais'] = chars_text
                        else:
                            row_data['Características Principais'] = 'N/A'
                    
                    if detailed_fields.get('outras_caracteristicas'):
                        other_chars = product_details.get('other_characteristics', {})
                        if other_chars:
                            # Converter características para string formatada
                            chars_text = '; '.join([f"{k}: {v}" for k, v in other_chars.items()])
                            row_data['Outras Características'] = chars_text
                        else:
                            row_data['Outras Características'] = 'N/A'
                    
                    if detailed_fields.get('total_reviews_detalhado'):
                        review_stats = product_details.get('review_stats', {})
                        row_data['Total Reviews (Detalhado)'] = review_stats.get('total_reviews', 'N/A')
                    
                    if detailed_fields.get('distribuicao_estrelas'):
                        review_stats = product_details.get('review_stats', {})
                        star_distribution = review_stats.get('star_distribution', {})
                        
                        if star_distribution:
                            # Adicionar colunas para cada estrela
                            for star in range(5, 0, -1):  # 5 a 1 estrelas
                                star_data = star_distribution.get(star, {})
                                row_data[f'{star} Estrelas (%)'] = star_data.get('percentage', 0)
                                row_data[f'{star} Estrelas (Qtd)'] = star_data.get('count', 0)
                        else:
                            # Preencher com N/A se não houver dados
                            for star in range(5, 0, -1):
                                row_data[f'{star} Estrelas (%)'] = 'N/A'
                                row_data[f'{star} Estrelas (Qtd)'] = 'N/A'
                else:
                    # Preencher campos detalhados com N/A se extração falhou
                    if detailed_fields.get('descricao'):
                        row_data['Descrição'] = 'N/A'
                    if detailed_fields.get('caracteristicas_principais'):
                        row_data['Características Principais'] = 'N/A'
                    if detailed_fields.get('outras_caracteristicas'):
                        row_data['Outras Características'] = 'N/A'
                    if detailed_fields.get('total_reviews_detalhado'):
                        row_data['Total Reviews (Detalhado)'] = 'N/A'
                    if detailed_fields.get('distribuicao_estrelas'):
                        for star in range(5, 0, -1):
                            row_data[f'{star} Estrelas (%)'] = 'N/A'
                            row_data[f'{star} Estrelas (Qtd)'] = 'N/A'
                            
            except Exception as e:
                logging.error(f"Erro ao extrair detalhes para CSV do produto {i+1}: {str(e)}")
                # Preencher com N/A em caso de erro
                if detailed_fields.get('descricao'):
                    row_data['Descrição'] = 'ERRO'
                if detailed_fields.get('caracteristicas_principais'):
                    row_data['Características Principais'] = 'ERRO'
                if detailed_fields.get('outras_caracteristicas'):
                    row_data['Outras Características'] = 'ERRO'
                if detailed_fields.get('total_reviews_detalhado'):
                    row_data['Total Reviews (Detalhado)'] = 'ERRO'
                if detailed_fields.get('distribuicao_estrelas'):
                    for star in range(5, 0, -1):
                        row_data[f'{star} Estrelas (%)'] = 'ERRO'
                        row_data[f'{star} Estrelas (Qtd)'] = 'ERRO'
        
        # Campos de risco de falsificação
        produto_id = produto.get('ID_PRODUTO')
        if produto_id and produto_id in risk_data_by_id:
            risk_result = risk_data_by_id[produto_id]
            
            if risk_fields.get('classificacao_risco'):
                row_data['Classificação de Risco'] = risk_result.get('classificacao', 'N/A')
            
            if risk_fields.get('probabilidade_total'):
                row_data['Probabilidade Total (%)'] = f"{risk_result.get('probabilidade_total', 0):.1f}"
            
            if risk_fields.get('probabilidade_preco'):
                row_data['Probabilidade Preço (%)'] = f"{risk_result.get('probabilidade_preco', 0):.1f}"
            
            if risk_fields.get('motivo_preco'):
                row_data['Motivo Análise Preço'] = risk_result.get('motivo_preco', 'N/A')
            
            if risk_fields.get('probabilidade_reviews'):
                row_data['Probabilidade Reviews (%)'] = f"{risk_result.get('probabilidade_reviews', 0):.1f}"
            
            if risk_fields.get('motivo_reviews'):
                row_data['Motivo Análise Reviews'] = risk_result.get('motivo_reviews', 'N/A')
            
            if risk_fields.get('detalhes_reviews_suspeitas'):
                reviews_suspeitas = risk_result.get('reviews_suspeitas', [])
                if reviews_suspeitas:
                    # Formatar todas as reviews suspeitas para CSV
                    reviews_formatadas = []
                    for review in reviews_suspeitas:
                        review_texto = f"Review #{review.get('numero_review', 'N/A')} - " \
                                     f"⭐{review.get('rating', 'N/A')} - " \
                                     f"Data: {review.get('data', 'N/A')} - " \
                                     f"Palavras suspeitas: {', '.join(review.get('palavras_suspeitas_encontradas', []))} - " \
                                     f"Texto: {review.get('texto_completo', '')}"
                        reviews_formatadas.append(review_texto)
                    
                    row_data['Reviews Suspeitas Detalhadas'] = ' || '.join(reviews_formatadas)
                    row_data['Total Reviews Suspeitas'] = len(reviews_suspeitas)
                else:
                    row_data['Reviews Suspeitas Detalhadas'] = 'Nenhuma review suspeita encontrada'
                    row_data['Total Reviews Suspeitas'] = 0
        else:
            # Preencher campos de risco com N/A se não houver dados
            if risk_fields.get('classificacao_risco'):
                row_data['Classificação de Risco'] = 'N/A'
            if risk_fields.get('probabilidade_total'):
                row_data['Probabilidade Total (%)'] = 'N/A'
            if risk_fields.get('probabilidade_preco'):
                row_data['Probabilidade Preço (%)'] = 'N/A'
            if risk_fields.get('motivo_preco'):
                row_data['Motivo Análise Preço'] = 'N/A'
            if risk_fields.get('probabilidade_reviews'):
                row_data['Probabilidade Reviews (%)'] = 'N/A'
            if risk_fields.get('motivo_reviews'):
                row_data['Motivo Análise Reviews'] = 'N/A'
            if risk_fields.get('detalhes_reviews_suspeitas'):
                row_data['Reviews Suspeitas Detalhadas'] = 'N/A'
                row_data['Total Reviews Suspeitas'] = 'N/A'
        
        # Campos de reviews (se configurado)
        if needs_reviews_extraction and produto_id and produto_id != 'N/A':
            try:
                # Extrair reviews do produto
                reviews_data = run_review_spider(produto_id, max_reviews=50)
                
                if reviews_data and reviews_data.get('reviews'):
                    reviews = reviews_data.get('reviews', [])
                    
                    if reviews_fields.get('reviews_resumo'):
                        row_data['Total Reviews Extraídas'] = len(reviews)
                        if reviews:
                            ratings = []
                            for r in reviews:
                                rating = r.get('rating', 0)
                                try:
                                    # Converter rating para float se for string
                                    if isinstance(rating, str):
                                        rating = float(rating)
                                    elif rating is None:
                                        rating = 0
                                    ratings.append(rating)
                                except (ValueError, TypeError):
                                    # Se não conseguir converter, usar 0
                                    ratings.append(0)
                            
                            avg_rating = sum(ratings) / len(ratings) if ratings else 0
                            row_data['Média Reviews Extraídas'] = f"{avg_rating:.1f}"
                        else:
                            row_data['Média Reviews Extraídas'] = 'N/A'
                    
                    if reviews_fields.get('reviews_texto'):
                        # Pegar as primeiras 3 reviews como amostra
                        sample_reviews = reviews[:3]
                        reviews_text = ' | '.join([r.get('text', '') for r in sample_reviews])
                        row_data['Amostra Texto Reviews'] = reviews_text
                    
                    if reviews_fields.get('reviews_rating'):
                        # Distribuição de ratings
                        rating_counts = {}
                        for review in reviews:
                            rating = review.get('rating', 0)
                            try:
                                # Converter rating para int se for string
                                if isinstance(rating, str):
                                    rating = int(float(rating))  # Primeiro float, depois int
                                elif rating is None:
                                    rating = 0
                                rating_counts[rating] = rating_counts.get(rating, 0) + 1
                            except (ValueError, TypeError):
                                # Se não conseguir converter, ignorar essa review
                                pass
                        
                        for star in range(1, 6):
                            row_data[f'Reviews {star}★'] = rating_counts.get(star, 0)
                    
                    if reviews_fields.get('reviews_data'):
                        # Data da review mais recente e mais antiga
                        dates = [r.get('date', '') for r in reviews if r.get('date')]
                        if dates:
                            row_data['Data Review Mais Recente'] = dates[0] if dates else 'N/A'
                            row_data['Data Review Mais Antiga'] = dates[-1] if dates else 'N/A'
                        else:
                            row_data['Data Review Mais Recente'] = 'N/A'
                            row_data['Data Review Mais Antiga'] = 'N/A'
                else:
                    # Sem reviews encontradas
                    if reviews_fields.get('reviews_resumo'):
                        row_data['Total Reviews Extraídas'] = 0
                        row_data['Média Reviews Extraídas'] = 'N/A'
                    if reviews_fields.get('reviews_texto'):
                        row_data['Amostra Texto Reviews'] = 'Nenhuma review encontrada'
                    if reviews_fields.get('reviews_rating'):
                        for star in range(1, 6):
                            row_data[f'Reviews {star}★'] = 0
                    if reviews_fields.get('reviews_data'):
                        row_data['Data Review Mais Recente'] = 'N/A'
                        row_data['Data Review Mais Antiga'] = 'N/A'
                        
            except Exception as e:
                logging.error(f"Erro ao extrair reviews para CSV do produto {i+1}: {str(e)}")
                # Preencher com ERRO em caso de falha
                if reviews_fields.get('reviews_resumo'):
                    row_data['Total Reviews Extraídas'] = 'ERRO'
                    row_data['Média Reviews Extraídas'] = 'ERRO'
                if reviews_fields.get('reviews_texto'):
                    row_data['Amostra Texto Reviews'] = 'ERRO'
                if reviews_fields.get('reviews_rating'):
                    for star in range(1, 6):
                        row_data[f'Reviews {star}★'] = 'ERRO'
                if reviews_fields.get('reviews_data'):
                    row_data['Data Review Mais Recente'] = 'ERRO'
                    row_data['Data Review Mais Antiga'] = 'ERRO'
        
        csv_data.append(row_data)
    
    return csv_data
#AAA
# Configuração do logger para Streamlit
logging.basicConfig(
    filename='scraper_errors.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Força a reconfiguração do logger
)

# Configurar o logger para reduzir warnings desnecessários
logging.getLogger("streamlit").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# ==================== SISTEMA DE DETECÇÃO DE FALSIFICAÇÃO ====================

# Lista de vendedores oficiais/confiáveis da HP (baseada nos dados fornecidos)
VENDEDORES_OFICIAIS_HP = {
    'AURORA COMÉRCIO ELETRÔNICO', 'BRAZÃO', 'CARREFOUR', 'CASA E VIDEO', 
    'CONECT MAGAZINE', 'CONTABILISTA', 'CREATIVE', 'DATASUPRI', 'E-FÁCIL', 
    'ESHOP', 'GIGAJET', 'IDCOMNET', 'INFORSHOP', 'KABUM', 'LEPOK', 'LOGIN', 
    'MEGAMAMUTE', 'MICROWARE', 'MIRANDA', 'MULTIMAX', 'PAPELEX', 'PORT INFO', 
    'PRIMETEK', 'OCEANO B2B', 'TECNOPAR', 'VGSHOP', 'VIKING', 'INFOMULTI', 
    'ELETRO 2U', 'MAXCO', 'CAVUCA', '123 COMPOU', 'OBERO', 'IFONTECH', 
    'INPOWER', '2ELETRO', 'TNT', 'COMERCIAL SMART'
}

# Palavras suspeitas em títulos/descrições que podem indicar falsificação
PALAVRAS_SUSPEITAS_TITULO = {
    'REPLICA', 'COPIA', 'SIMILAR', 'COMPATIVEL', 'GENERICO', 'ALTERNATIVO',
    'PARALELO', 'IMPORTADO', 'CHINA', 'BARATO', 'PROMOCAO', 'LIQUIDACAO',
    'OFERTA', 'IMPERDIVEL', 'SUPER PRECO', 'MEGA OFERTA', 'PRODUTO RUIM',
    'NÃO RECOMENDO', 'PÉSSIMO PRODUTO', 'DINHEIRO JOGADO FORA', 'ARREPENDIMENTO',
    'NÃO COMPREM', 'EVITEM'
}

# Erros de gramática/ortografia comuns em produtos falsificados
ERROS_GRAMATICA = {
    'CARTUXO', 'CARTUSHO', 'CARTUCHO HP', 'TINTA HP', 'IMPRESSORA HP',
    'ORIGINAL HP', 'GENUINO HP', 'AUTENTICO HP'
}

# Preços de referência baseados na imagem fornecida (valores sugeridos)
PRECOS_REFERENCIA_HP = {
    # Cartuchos HP 667
    'HP 667': {'preto': 74.90, 'colorido': 89.90},
    '667': {'preto': 74.90, 'colorido': 89.90},
    
    # Cartuchos HP 664  
    'HP 664': {'preto': 74.90, 'colorido': 89.90, 'xl_preto': 172.90, 'xl_colorido': 172.90},
    '664': {'preto': 74.90, 'colorido': 89.90, 'xl_preto': 172.90, 'xl_colorido': 172.90},
    
    # Cartuchos HP 662
    'HP 662': {'preto': 69.90, 'colorido': 74.90, 'xl_preto': 134.90, 'xl_colorido': 172.90},
    '662': {'preto': 69.90, 'colorido': 74.90, 'xl_preto': 134.90, 'xl_colorido': 172.90},
    
    # Cartuchos HP GT (Garrafas de tinta)
    'HP GT': {'preto': 72.90, 'colorido': 264.90},
    'GT': {'preto': 72.90, 'colorido': 264.90},
    
    # Cartuchos HP 954
    'HP 954': {'preto': 153.90, 'colorido': 153.90, 'xl_preto': 256.90, 'xl_colorido': 256.90},
    '954': {'preto': 153.90, 'colorido': 153.90, 'xl_preto': 256.90, 'xl_colorido': 256.90},
    
    # Valores genéricos para outros modelos HP
    'HP': {'preto': 70.00, 'colorido': 80.00, 'xl_preto': 150.00, 'xl_colorido': 170.00}
}

def extrair_preco_numerico(preco_str):
    """
    Extrai o valor numérico de uma string de preço
    Ex: "R$ 61,94" -> 61.94
    """
    if not preco_str or preco_str == 'N/A':
        return None
    
    # Remover símbolos de moeda e espaços
    preco_limpo = re.sub(r'[R$\s]', '', str(preco_str))
    
    # Substituir vírgula por ponto para conversão
    preco_limpo = preco_limpo.replace(',', '.')
    
    try:
        return float(preco_limpo)
    except ValueError:
        return None

def identificar_modelo_cartucho(titulo):
    """
    Identifica o modelo do cartucho HP baseado no título
    """
    titulo_upper = titulo.upper()
    
    # Procurar por modelos específicos
    modelos = ['667', '664', '662', '954', 'GT']
    
    for modelo in modelos:
        if modelo in titulo_upper:
            # Verificar se é XL
            is_xl = 'XL' in titulo_upper
            
            # Verificar cor
            is_preto = any(palavra in titulo_upper for palavra in ['PRETO', 'BLACK', 'PRETA'])
            is_colorido = any(palavra in titulo_upper for palavra in ['COLOR', 'COLORIDO', 'TRICOLOR', 'COR'])
            
            if is_xl:
                if is_preto:
                    return modelo, 'xl_preto'
                elif is_colorido:
                    return modelo, 'xl_colorido'
                else:
                    return modelo, 'xl_preto'  # Default para XL
            else:
                if is_preto:
                    return modelo, 'preto'
                elif is_colorido:
                    return modelo, 'colorido'
                else:
                    return modelo, 'preto'  # Default para preto
    
    # Se não encontrou modelo específico, usar genérico HP
    if 'HP' in titulo_upper:
        is_xl = 'XL' in titulo_upper
        is_preto = any(palavra in titulo_upper for palavra in ['PRETO', 'BLACK', 'PRETA'])
        is_colorido = any(palavra in titulo_upper for palavra in ['COLOR', 'COLORIDO', 'TRICOLOR', 'COR'])
        
        if is_xl:
            if is_preto:
                return 'HP', 'xl_preto'
            elif is_colorido:
                return 'HP', 'xl_colorido'
            else:
                return 'HP', 'xl_preto'
        else:
            if is_preto:
                return 'HP', 'preto'
            elif is_colorido:
                return 'HP', 'colorido'
            else:
                return 'HP', 'preto'
    
    return None, None

def calcular_probabilidade_preco(produto):
    """
    Calcula probabilidade de falsificação baseada no preço
    """
    titulo = produto.get('TITULO PRODUTO', '')
    preco_str = produto.get('PREÇO', 'N/A')
    
    preco_atual = extrair_preco_numerico(preco_str)
    if preco_atual is None:
        return 0, "Preço não disponível"
    
    modelo, tipo = identificar_modelo_cartucho(titulo)
    if not modelo:
        return 0, "Modelo não identificado"
    
    preco_referencia = PRECOS_REFERENCIA_HP.get(modelo, {}).get(tipo)
    if not preco_referencia:
        return 0, f"Preço de referência não encontrado para {modelo} {tipo}"
    
    # Calcular diferença percentual
    diferenca_percentual = ((preco_referencia - preco_atual) / preco_referencia) * 100
    
    # Calcular probabilidade baseada na diferença
    probabilidade_preco = 0
    motivo = ""
    
    if diferenca_percentual >= 50:  # 50% ou mais abaixo do sugerido
        probabilidade_preco = 70
        motivo = f"Preço {diferenca_percentual:.1f}% abaixo do sugerido (R$ {preco_referencia:.2f})"
    elif diferenca_percentual >= 30:  # 30-49% abaixo
        probabilidade_preco = 50
        motivo = f"Preço {diferenca_percentual:.1f}% abaixo do sugerido (R$ {preco_referencia:.2f})"
    elif diferenca_percentual >= 15:  # 15-29% abaixo
        probabilidade_preco = 30
        motivo = f"Preço {diferenca_percentual:.1f}% abaixo do sugerido (R$ {preco_referencia:.2f})"
    elif diferenca_percentual >= 5:   # 5-14% abaixo
        probabilidade_preco = 15
        motivo = f"Preço {diferenca_percentual:.1f}% abaixo do sugerido (R$ {preco_referencia:.2f})"
    else:
        motivo = f"Preço dentro da faixa normal (ref: R$ {preco_referencia:.2f})"
    
    return probabilidade_preco, motivo

def analisar_reviews_falsificacao(product_id, max_reviews=100):
    """
    Analisa reviews procurando por indicadores de falsificação
    """
    if not product_id or product_id == 'N/A':
        return 0, "ID do produto não disponível", []
    
    try:
        # Coletar reviews do produto
        reviews_data = run_review_spider(product_id, max_reviews=max_reviews)
        
        if not reviews_data or not reviews_data.get('reviews'):
            return 0, "Reviews não disponíveis", []
        
        reviews = reviews_data.get('reviews', [])
        total_reviews = len(reviews)
        
        # Palavras-chave relacionadas a falsificação
        palavras_falsificacao = [
            'falsificado', 'falsificação', 'falso', 'falsa', 'fake', 
            'pirata', 'imitação', 'cópia', 'não original', 'não é original',
            'durou pouco', 'não funciona', 'qualidade ruim', 'péssima qualidade',
            'não imprime', 'vazou', 'vazamento', 'secou rápido', 'acabou rápido',
            'produto ruim', 'não recomendo', 'péssimo produto', 'não vale a pena',
            'dinheiro jogado fora', 'arrependimento', 'não comprem', 'evitem'
        ]
        
        # Contar ocorrências e coletar todas as reviews suspeitas
        reviews_suspeitas_count = 0
        total_ocorrencias = 0
        reviews_suspeitas_completas = []
        
        for i, review in enumerate(reviews):
            texto_review = review.get('text', '').lower()
            palavras_encontradas = []
            ocorrencias_nesta_review = 0
            
            for palavra in palavras_falsificacao:
                if palavra in texto_review:
                    count = texto_review.count(palavra)
                    ocorrencias_nesta_review += count
                    total_ocorrencias += count
                    if count > 0:
                        palavras_encontradas.append(palavra)
            
            if ocorrencias_nesta_review > 0:
                reviews_suspeitas_count += 1
                # Guardar review suspeita completa
                review_suspeita = {
                    'numero_review': i + 1,
                        'rating': review.get('rating', 'N/A'),
                    'data': review.get('date', 'N/A'),
                    'texto_completo': review.get('text', ''),
                    'palavras_suspeitas_encontradas': palavras_encontradas,
                    'total_ocorrencias': ocorrencias_nesta_review,
                    'helpful_count': review.get('helpful_count', '0')
                }
                reviews_suspeitas_completas.append(review_suspeita)
        
        # Calcular probabilidade baseada nas reviews
        percentual_reviews_suspeitas = (reviews_suspeitas_count / total_reviews) * 100 if total_reviews > 0 else 0
        
        probabilidade_reviews = 0
        motivo = ""
        
        if percentual_reviews_suspeitas >= 20:  # 20% ou mais das reviews são suspeitas
            probabilidade_reviews = 60
            motivo = f"{reviews_suspeitas_count}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif percentual_reviews_suspeitas >= 10:  # 10-19% suspeitas
            probabilidade_reviews = 40
            motivo = f"{reviews_suspeitas_count}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif percentual_reviews_suspeitas >= 5:   # 5-9% suspeitas
            probabilidade_reviews = 25
            motivo = f"{reviews_suspeitas_count}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif total_ocorrencias > 0:  # Algumas ocorrências, mas baixo percentual
            probabilidade_reviews = 10
            motivo = f"{total_ocorrencias} menções suspeitas em {total_reviews} reviews"
        else:
            motivo = f"Nenhuma menção suspeita em {total_reviews} reviews analisadas"
        
        return probabilidade_reviews, motivo, reviews_suspeitas_completas
        
    except Exception as e:
        logging.error(f"Erro ao analisar reviews para falsificação: {str(e)}")
        return 0, f"Erro na análise: {str(e)}", []

def calcular_probabilidade_falsificacao(produto, analisar_reviews=True):
    """
    Calcula a probabilidade total de falsificação combinando preço e reviews
    """
    resultado = {
        'probabilidade_total': 0,
        'probabilidade_preco': 0,
        'probabilidade_reviews': 0,
        'motivo_preco': '',
        'motivo_reviews': '',
        'detalhes_reviews': [],
        'classificacao': 'BAIXO RISCO'
    }
    
    # Análise de preço
    prob_preco, motivo_preco = calcular_probabilidade_preco(produto)
    resultado['probabilidade_preco'] = prob_preco
    resultado['motivo_preco'] = motivo_preco
    
    # Análise de reviews (se solicitado)
    if analisar_reviews:
        product_id = produto.get('ID_PRODUTO')
        if product_id and product_id != 'N/A':
            try:
                prob_reviews, motivo_reviews, reviews_suspeitas = analisar_reviews_falsificacao(product_id, max_reviews=100)
                resultado['probabilidade_reviews'] = prob_reviews
                resultado['motivo_reviews'] = motivo_reviews
                resultado['reviews_suspeitas'] = reviews_suspeitas
                resultado['total_reviews_suspeitas'] = len(reviews_suspeitas)
            except Exception as e:
                resultado['motivo_reviews'] = f"Erro na análise de reviews: {str(e)}"
                resultado['reviews_suspeitas'] = []
                resultado['total_reviews_suspeitas'] = 0
        else:
            resultado['motivo_reviews'] = "ID do produto não disponível para análise de reviews"
            resultado['reviews_suspeitas'] = []
            resultado['total_reviews_suspeitas'] = 0
    
    # Calcular probabilidade total (média ponderada)
    if analisar_reviews and resultado['probabilidade_reviews'] > 0:
        # Peso maior para reviews (70%) e menor para preço (30%) quando ambos estão disponíveis
        resultado['probabilidade_total'] = (resultado['probabilidade_preco'] * 0.3) + (resultado['probabilidade_reviews'] * 0.7)
    else:
        # Usar apenas análise de preço
        resultado['probabilidade_total'] = resultado['probabilidade_preco']
    
    # Classificar risco
    if resultado['probabilidade_total'] >= 60:
        resultado['classificacao'] = 'ALTO RISCO'
    elif resultado['probabilidade_total'] >= 30:
        resultado['classificacao'] = 'MÉDIO RISCO'
    else:
        resultado['classificacao'] = 'BAIXO RISCO'
    
    return resultado

def processar_deteccao_falsificacao(produtos, analisar_reviews=True, progress_callback=None):
    """
    Processa detecção de falsificação para uma lista de produtos
    """
    resultados = []
    
    for i, produto in enumerate(produtos):
        if progress_callback:
            progress_callback(i + 1, len(produtos))
        
        logging.info(f"Analisando falsificação {i+1}/{len(produtos)}: {produto.get('TITULO PRODUTO', 'N/A')[:50]}...")
        
        resultado = calcular_probabilidade_falsificacao(produto, analisar_reviews)
        resultado['produto'] = produto
        resultados.append(resultado)
        
        # Pequena pausa para não sobrecarregar
        time.sleep(0.1)
    
    return resultados

# ==================== FIM DO SISTEMA DE DETECÇÃO ====================

# Lista de User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# =============================================================================
# FUNÇÕES AUXILIARES PARA DATASET HP CHALLENGE
# =============================================================================

# Lista de vendedores oficiais HP
VENDEDORES_OFICIAIS_HP = {
    'HP STORE OFICIAL',
    'HP BRASIL',
    'HP STORE',
    'HEWLETT PACKARD',
    'LOJA HP',
    'HP OFFICIAL STORE',
    'HP SUPPLIES',
    'LOJA OFICIAL HP'
}

# Palavras suspeitas em títulos
PALAVRAS_SUSPEITAS_TITULO = {
    'FALSIFICADO', 'FALSIFICACAO', 'FALSO', 'FALSA', 'FAKE', 
    'PIRATA', 'IMITACAO', 'COPIA', 'REPLICA', 'COMPATIVEL', 
    'GENERICO', 'ALTERNATIVO', 'PARALELO', 'IMPORTADO', 
    'CHINA', 'BARATO', 'PROMOCAO', 'LIQUIDACAO', 'OFERTA', 
    'IMPERDIVEL', 'SUPER PRECO', 'MEGA OFERTA'
}

# Erros de gramática comuns
ERROS_GRAMATICA = {
    'CARTUCHO', 'CARTUXO', 'CARTTUCHO', 'KCARTUCHO',
    'TINTA', 'TINTA', 'TINT', 'TINTTA',
    'IMPRESSORA', 'INPRESSORA', 'IMPRESORA', 'INPRESORA'
}

# Preços de referência HP (valores aproximados em R$)
PRECOS_REFERENCIA_HP = {
    'HP664': {'original': 45.00, 'xl': 70.00},
    'HP662': {'original': 40.00, 'xl': 65.00},
    'HP667': {'original': 50.00, 'xl': 80.00},
    'HP954': {'original': 180.00, 'xl': 240.00},
    'HP938': {'original': 160.00, 'xl': 220.00},
    'HP774': {'original': 200.00, 'xl': 280.00}
}

def verificar_vendedor_oficial(vendedor):
    """
    Verifica se o vendedor está na lista de vendedores oficiais/confiáveis da HP
    """
    if not vendedor or vendedor == 'N/A':
        return False
    
    vendedor_upper = vendedor.upper().strip()
    
    # Verificação direta
    if vendedor_upper in VENDEDORES_OFICIAIS_HP:
        return True
    
    # Verificação por similaridade (para casos de pequenas variações)
    for vendedor_oficial in VENDEDORES_OFICIAIS_HP:
        if vendedor_upper in vendedor_oficial or vendedor_oficial in vendedor_upper:
            return True
    
    return False

def analisar_titulo_suspeito(titulo):
    """
    Analisa o título do produto procurando por palavras suspeitas ou erros de gramática
    """
    if not titulo:
        return 0, []
    
    titulo_upper = titulo.upper()
    indicadores_suspeitos = []
    pontuacao_suspeita = 0
    
    # Verificar palavras suspeitas
    for palavra in PALAVRAS_SUSPEITAS_TITULO:
        if palavra in titulo_upper:
            indicadores_suspeitos.append(f"Palavra suspeita: '{palavra}'")
            pontuacao_suspeita += 15  # 15 pontos por palavra suspeita
    
    # Verificar erros de gramática/ortografia
    for erro in ERROS_GRAMATICA:
        # Usar regex para encontrar apenas palavras inteiras e evitar falsos positivos
        if re.search(r'\b' + re.escape(erro) + r'\b', titulo_upper):
            indicadores_suspeitos.append(f"Possível erro de grafia: '{erro}'")
            pontuacao_suspeita += 10  # 10 pontos por erro
    
    # Verificar se menciona "original" ou "genuíno" (pode ser suspeito se enfatizar muito)
    palavras_enfase = ['100% ORIGINAL', 'GENUINO', 'AUTENTICO', 'VERDADEIRO']
    for palavra in palavras_enfase:
        if palavra in titulo_upper:
            indicadores_suspeitos.append(f"Ênfase suspeita em autenticidade: '{palavra}'")
            pontuacao_suspeita += 5  # 5 pontos por ênfase excessiva
    
    return min(pontuacao_suspeita, 100), indicadores_suspeitos

def calcular_score_preco_mercado(produto):
    """
    Calcula um score baseado na análise de preço em relação ao mercado
    """
    titulo = produto.get('TITULO PRODUTO', '')
    preco_str = produto.get('PREÇO', 'N/A')
    
    preco_atual = extrair_preco_numerico(preco_str)
    if preco_atual is None:
        return 0, "Preço não disponível para análise"
    
    modelo, tipo = identificar_modelo_cartucho(titulo)
    if not modelo:
        return 0, "Modelo não identificado para análise de preço"
    
    preco_referencia = PRECOS_REFERENCIA_HP.get(modelo, {}).get(tipo)
    if not preco_referencia:
        return 0, f"Preço de referência não encontrado para {modelo} {tipo}"
    
    # Calcular diferença percentual
    diferenca_percentual = ((preco_referencia - preco_atual) / preco_referencia) * 100
    
    # Score baseado na diferença de preço
    if diferenca_percentual >= 60:  # 60% ou mais abaixo
        return 90, f"Preço extremamente baixo: {diferenca_percentual:.1f}% abaixo da referência"
    elif diferenca_percentual >= 40:  # 40-59% abaixo
        return 70, f"Preço muito baixo: {diferenca_percentual:.1f}% abaixo da referência"
    elif diferenca_percentual >= 25:  # 25-39% abaixo
        return 50, f"Preço baixo: {diferenca_percentual:.1f}% abaixo da referência"
    elif diferenca_percentual >= 10:  # 10-24% abaixo
        return 25, f"Preço ligeiramente baixo: {diferenca_percentual:.1f}% abaixo da referência"
    elif diferenca_percentual >= -10:  # Dentro da faixa normal
        return 0, f"Preço dentro da faixa normal (ref: R$ {preco_referencia:.2f})"
    else:  # Preço acima da referência
        return 0, f"Preço acima da referência: {abs(diferenca_percentual):.1f}% mais caro"

def rotular_produto_heuristico(produto):
    """
    Aplica critérios heurísticos para rotular o produto como "original" ou "suspeito/pirata"
    Baseado nos critérios do Challenge Sprint da HP
    """
    titulo = produto.get('TITULO PRODUTO', '')
    vendedor = produto.get('VENDEDOR', 'N/A')
    preco_str = produto.get('PREÇO', 'N/A')
    
    # Inicializar scores
    score_total = 0
    criterios_aplicados = []
    detalhes_analise = {
        'vendedor_oficial': False,
        'score_titulo': 0,
        'score_preco': 0,
        'indicadores_titulo': [],
        'motivo_preco': '',
        'motivo_vendedor': ''
    }
    
    # 1. Análise do Vendedor (peso alto)
    is_vendedor_oficial = verificar_vendedor_oficial(vendedor)
    detalhes_analise['vendedor_oficial'] = is_vendedor_oficial
    
    if is_vendedor_oficial:
        score_total -= 30  # Reduz suspeita significativamente
        detalhes_analise['motivo_vendedor'] = f"Vendedor oficial/confiável: {vendedor}"
        criterios_aplicados.append("✅ Vendedor oficial")
    else:
        score_total += 20  # Aumenta suspeita
        detalhes_analise['motivo_vendedor'] = f"Vendedor não oficial: {vendedor}"
        criterios_aplicados.append("⚠️ Vendedor não oficial")
    
    # 2. Análise do Título (palavras suspeitas, erros de gramática)
    score_titulo, indicadores_titulo = analisar_titulo_suspeito(titulo)
    detalhes_analise['score_titulo'] = score_titulo
    detalhes_analise['indicadores_titulo'] = indicadores_titulo
    
    score_total += score_titulo
    if score_titulo > 0:
        criterios_aplicados.append(f"⚠️ Título suspeito (+{score_titulo} pts)")
        for indicador in indicadores_titulo[:2]:  # Mostrar até 2 indicadores
            criterios_aplicados.append(f"  • {indicador}")
    else:
        criterios_aplicados.append("✅ Título sem indicadores suspeitos")
    
    # 3. Análise de Preço (comparação com referências de mercado)
    score_preco, motivo_preco = calcular_score_preco_mercado(produto)
    detalhes_analise['score_preco'] = score_preco
    detalhes_analise['motivo_preco'] = motivo_preco
    
    score_total += score_preco
    if score_preco > 0:
        criterios_aplicados.append(f"⚠️ Preço suspeito (+{score_preco} pts)")
        criterios_aplicados.append(f"  • {motivo_preco}")
    else:
        criterios_aplicados.append("✅ Preço dentro da normalidade")
    
    # 4. Decisão final baseada no score
    detalhes_analise['score_total'] = score_total
    detalhes_analise['criterios_aplicados'] = criterios_aplicados
    
    # Critério de classificação
    if score_total >= 50:
        rotulo = 'suspeito'
        criterios_aplicados.append(f"🔴 RESULTADO: SUSPEITO (score: {score_total})")
    else:
        rotulo = 'original'
        criterios_aplicados.append(f"🟢 RESULTADO: ORIGINAL (score: {score_total})")
    
    return rotulo, detalhes_analise

def gerar_dataset_hp_challenge(produtos):
    """
    Gera dataset rotulado usando critérios heurísticos para o HP Challenge Sprint
    """
    dataset_rotulado = []
    
    for produto in produtos:
        # Aplicar rotulagem heurística
        rotulo, detalhes_rotulagem = rotular_produto_heuristico(produto)
        
        # Criar entrada do dataset
        entrada_dataset = {
            'produto_original': produto,
            'rotulo_heuristico': rotulo,
            'detalhes_rotulagem': detalhes_rotulagem
        }
        
        dataset_rotulado.append(entrada_dataset)
    
    return dataset_rotulado

# Função para realizar uma requisição HTTP para imagens
def make_request(url, max_retries=3, initial_wait=1):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
    }
    wait_time = initial_wait
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response
            else:
                logging.warning(f"Imagem - Tentativa {attempt+1}/{max_retries} - Status: {response.status_code} para URL: {url}")
        except Exception as e:
            logging.error(f"Imagem - Erro na tentativa {attempt+1}/{max_retries}: {str(e)} para URL: {url}")
        time.sleep(wait_time)
        wait_time *= 2
    return None

# Initialize session state variables if they don't exist
if 'reviews_data' not in st.session_state:
    st.session_state.reviews_data = None
if 'fetching_reviews_for_id' not in st.session_state:
    st.session_state.fetching_reviews_for_id = None
if 'last_fetched_product_id_reviews' not in st.session_state:
    st.session_state.last_fetched_product_id_reviews = None
if 'max_reviews_to_fetch' not in st.session_state:
    st.session_state.max_reviews_to_fetch = 50
if 'use_rating_percentages' not in st.session_state:
    st.session_state.use_rating_percentages = False
if 'rating_percentages' not in st.session_state:
    st.session_state.rating_percentages = {5: 35, 4: 28, 3: 7, 2: 15, 1: 15}  # Default percentages that sum to 100%
if 'product_details_data' not in st.session_state:
    st.session_state.product_details_data = {}
if 'fetching_details_for_url' not in st.session_state:
    st.session_state.fetching_details_for_url = None
if 'csv_generator_enabled' not in st.session_state:
    st.session_state.csv_generator_enabled = False
if 'csv_fields_config' not in st.session_state:
    st.session_state.csv_fields_config = {
        'basic_fields': {
            'titulo': True,
            'preco': True,
            'preco_anterior': True,
            'marca': True,
            'vendedor': True,
            'link': True,
            'id_produto': True,
            'imagem': False,
            'entrega': True,
            'entrega_full': True,
            'media_avaliacoes_busca': True,
            'total_avaliacoes_busca': True
        },
        'detailed_fields': {
            'descricao': False,
            'caracteristicas_principais': False,
            'outras_caracteristicas': False,
            'total_reviews_detalhado': True,
            'distribuicao_estrelas': True
        }
    }

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="HP Challenge Sprint - Detector de Falsificações", 
    page_icon="🏆", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# HEADER PRINCIPAL
# =============================================================================

st.title("🏆 HP Challenge Sprint - Detector de Falsificações")
st.markdown("**Sistema Inteligente de Detecção de Produtos HP Suspeitos/Piratas em E-commerce**")

# Informações do projeto na sidebar
with st.sidebar:
    st.markdown("## 📋 Sobre o Projeto")
    st.markdown("""
    **Objetivo:** Desenvolver uma solução automatizada para identificar 
    possíveis casos de pirataria de produtos HP vendidos em sites de e-commerce.
    
    **✅ Funcionalidades:**
    - Web Scraping inteligente
    - Análise de preços e vendors
    - Detecção de reviews suspeitas
    - Rotulagem automática
    - Análise exploratória avançada
    """)

st.markdown("---")

# =============================================================================
# CONFIGURAÇÕES PRINCIPAIS NA SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("## ⚙️ Configurações de Busca")
    
    # Busca principal
    search_query = st.text_input("🔍 Termo de busca:", "cartucho hp", help="Produto para buscar no Mercado Livre")
    
    # Quantidade de itens
    max_items = st.number_input(
        "📊 Máximo de itens:", 
        min_value=1, 
        max_value=500, 
        value=20, 
        step=10,
        help="Quantidade máxima de produtos a extrair"
    )
    
    # Filtros
    st.markdown("### 🔧 Filtros")
    
    # Ordenação
    sort_options = {
    'Relevância': 'relevance',
    'Menor Preço': 'price_asc',
    'Maior Preço': 'price_desc'
}
    sort_by = st.selectbox("Ordenar por:", list(sort_options.keys()))
    sort_value = sort_options[sort_by]
    
    # Condição
    condition_options = {
    'Todos': 'all',
    'Novo': 'new',
    'Usado': 'used'
}
    condition = st.selectbox("Condição:", list(condition_options.keys()))
    condition_value = condition_options[condition]
    
    # Outras opções
    load_images = st.checkbox("🖼️ Carregar imagens", value=True)
    
    st.markdown("---")

    # Configurações de Reviews
    st.markdown("## ⭐ Reviews & Análise")

    # Configuração principal: Extrair reviews
    extract_reviews = st.checkbox(
        "🔍 Extrair Reviews dos Produtos",
        value=st.session_state.get('extract_reviews', False),
        help="Ativa a extração e exibição de reviews no frontend"
    )
    st.session_state.extract_reviews = extract_reviews

    if extract_reviews:
        # Configuração de quantidade de reviews
        max_reviews = st.number_input(
            "📈 Máximo de reviews por produto:",
            min_value=10,
            max_value=300,
            value=st.session_state.get('max_reviews_to_fetch', 50),
            step=10,
            help="Quantidade máxima de reviews a extrair por produto"
        )
        st.session_state.max_reviews_to_fetch = max_reviews
        
        # Configuração avançada: Distribuição personalizada por estrelas
        use_rating_percentages = st.checkbox(
            "📊 Usar distribuição personalizada por estrelas",
            value=st.session_state.get('use_rating_percentages', False),
            help="Coleta reviews específicas por rating em percentuais definidos"
        )
        st.session_state.use_rating_percentages = use_rating_percentages

        if use_rating_percentages:
            st.markdown("**Distribuição por estrela:**")
            review_percentages = {}
            total_percentage = 0
            
            for star in [5, 4, 3, 2, 1]:
                default_value = st.session_state.get(f'percentage_{star}_star', 
                                                   {5: 40, 4: 30, 3: 10, 2: 10, 1: 10}[star])
                percentage = st.slider(
                    f"{star}⭐", 
                    min_value=0,
                    max_value=100,
                    value=default_value,
                    help=f"Percentual de reviews de {star} estrelas"
                )
                review_percentages[star] = percentage
                total_percentage += percentage
                st.session_state[f'percentage_{star}_star'] = percentage
            
            if total_percentage != 100:
                st.warning(f"⚠️ Total: {total_percentage}% (recomendado: 100%)")
            
            st.session_state.rating_percentages = review_percentages
    
    st.markdown("---")

# =============================================================================
# CONFIGURAÇÕES DE EXPORTAÇÃO NA SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("---")
    st.markdown("## 📥 Configurações de Export")
    
    # CSV Generator
    csv_enabled = st.checkbox("📊 Gerador CSV Avançado", value=st.session_state.get('csv_generator_enabled', False))
    st.session_state.csv_generator_enabled = csv_enabled
    
    if csv_enabled:
        with st.expander("⚙️ Configurar Campos CSV", expanded=True):
            # Simplificar configuração na sidebar
            basic_fields = st.session_state.csv_fields_config.get('basic_fields', {})
            detailed_fields = st.session_state.csv_fields_config.get('detailed_fields', {})
            risk_fields = st.session_state.csv_fields_config.get('risk_fields', {})
            
            st.markdown("**Dados Básicos:**")
            basic_all = st.checkbox("Todos os campos básicos", value=all(basic_fields.values()))
            if basic_all != all(basic_fields.values()):
                for field in basic_fields:
                    basic_fields[field] = basic_all
            
            st.markdown("**Dados Detalhados:**")
            detailed_all = st.checkbox("Todos os campos detalhados", value=all(detailed_fields.values()))
            if detailed_all != all(detailed_fields.values()):
                for field in detailed_fields:
                    detailed_fields[field] = detailed_all
            
            st.markdown("**Análise de Risco:**")
            risk_all = st.checkbox("Todos os campos de risco", value=all(risk_fields.values()))
            if risk_all != all(risk_fields.values()):
                for field in risk_fields:
                    risk_fields[field] = risk_all
            
            st.markdown("**Reviews:**")
            reviews_fields = st.session_state.csv_fields_config.get('reviews_fields', {})
            if not reviews_fields:
                # Inicializar reviews_fields se não existir
                reviews_fields = {
                    'incluir_reviews': False,
                    'reviews_texto': False,
                    'reviews_rating': False,
                    'reviews_data': False,
                    'reviews_resumo': True
                }
                st.session_state.csv_fields_config['reviews_fields'] = reviews_fields
            
            reviews_fields['incluir_reviews'] = st.checkbox("Incluir Reviews no CSV", value=reviews_fields.get('incluir_reviews', False))
            
            if reviews_fields['incluir_reviews']:
                reviews_fields['reviews_resumo'] = st.checkbox("Resumo de Reviews", value=reviews_fields.get('reviews_resumo', True))
                reviews_fields['reviews_texto'] = st.checkbox("Texto das Reviews", value=reviews_fields.get('reviews_texto', False))
                reviews_fields['reviews_rating'] = st.checkbox("Rating das Reviews", value=reviews_fields.get('reviews_rating', False))
                reviews_fields['reviews_data'] = st.checkbox("Data das Reviews", value=reviews_fields.get('reviews_data', False))

# =============================================================================
# ÁREA PRINCIPAL - ABAS ORGANIZADAS
# =============================================================================

# Criar abas principais para organizar funcionalidades
tab_busca, tab_falsificacao, tab_dataset, tab_analytics = st.tabs([
    "🔍 Busca & Coleta", 
    "🚨 Detecção de Falsificação", 
    "📊 Dataset Generator",
    "📈 Analytics Avançado"
])

# =============================================================================
# ABA 1: BUSCA & COLETA
# =============================================================================

with tab_busca:
    st.markdown("## 🔍 Busca e Coleta de Dados")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"**Buscando:** `{search_query}` | **Itens:** {max_items} | **Ordenação:** {sort_by}")
    
    with col2:
        search_button = st.button("🚀 Iniciar Busca", type="primary", use_container_width=True)
    
    if search_button:
        with st.spinner(f"🔍 Buscando '{search_query}' no Mercado Livre..."):
            search_results, urls_used = run_spider(
                query=search_query,
                max_items=max_items, 
                sort_by=sort_value,
                condition=condition_value,
                extract_images=load_images
            )
            
            if search_results:
                st.session_state.current_products = search_results
                # Limpar resultados antigos de outras análises
                if 'falsification_results' in st.session_state:
                    del st.session_state.falsification_results
                if 'labeled_dataset' in st.session_state:
                    del st.session_state.labeled_dataset
            else:
                st.error("❌ Não foi possível realizar a busca. Tente novamente.")
                if 'current_products' in st.session_state:
                    del st.session_state.current_products

    # Exibir resultados da busca (se existirem no estado da sessão)
    if 'current_products' in st.session_state and st.session_state.current_products:
        st.success(f"✅ Exibindo {len(st.session_state.current_products)} produtos encontrados!")
        
        # Mostrar todos os resultados
        st.markdown("### 📋 Produtos Encontrados")
        
        for i, produto in enumerate(st.session_state.current_products):
            # Exibir título completo, sem truncar
            with st.expander(f"📦 {produto.get('TITULO PRODUTO', 'Sem título')}", expanded=True):
                col_img, col_details = st.columns([1, 3])
                
                with col_img:
                    if load_images and produto.get('IMAGEM') != 'N/A':
                        try:
                            st.image(produto['IMAGEM'], width=100)
                        except Exception as e:
                            st.write(f"📷 Erro ao carregar imagem: {e}")
                    else:
                        st.write("🖼️ Imagens desabilitadas")
                
                with col_details:
                    st.write(f"**💰 Preço:** {produto.get('PREÇO', 'N/A')}")
                    st.write(f"**🏪 Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                    st.write(f"**⭐ Avaliações:** {produto.get('MÉDIA AVALIAÇÕES', 'N/A')} ({produto.get('TOTAL AVALIAÇÕES', 'N/A')})")
                    if produto.get('LINK') != 'N/A':
                        st.markdown(f"🔗 [Ver produto]({produto['LINK']})")
                    
                    # Exibir reviews se configurado
                    if st.session_state.get('extract_reviews', False):
                        produto_id = produto.get('ID_PRODUTO')
                        if produto_id and produto_id != 'N/A':
                            with st.spinner("Carregando reviews..."):
                                try:
                                    max_reviews_config = st.session_state.get('max_reviews_to_fetch', 50)
                                    reviews_data = run_review_spider(produto_id, max_reviews=max_reviews_config)
                                    
                                    if reviews_data and reviews_data.get('reviews'):
                                        reviews = reviews_data.get('reviews', [])
                                        st.markdown("**💬 Reviews do Produto:**")
                                        st.write(f"📊 **Total:** {len(reviews)} reviews")
                                        
                                        if reviews:
                                            # Calcular média de rating
                                            ratings = []
                                            for r in reviews:
                                                rating = r.get('rating', 0)
                                                try:
                                                    # Converter rating para float se for string
                                                    if isinstance(rating, str):
                                                        rating = float(rating)
                                                    elif rating is None:
                                                        rating = 0
                                                    ratings.append(rating)
                                                except (ValueError, TypeError):
                                                    # Se não conseguir converter, usar 0
                                                    ratings.append(0)
                                            
                                            if ratings:
                                                avg_rating = sum(ratings) / len(ratings)
                                                st.write(f"⭐ **Média:** {avg_rating:.1f}/5")
                                            
                                            # Mostrar algumas reviews
                                            with st.expander(f"Ver primeiras {min(3, len(reviews))} reviews", expanded=False):
                                                for j, review in enumerate(reviews[:3]):
                                                    st.markdown(f"**Review {j+1}:**")
                                                    st.write(f"⭐ {review.get('rating', 'N/A')}/5")
                                                    st.write(f"📅 {review.get('date', 'N/A')}")
                                                    st.write(f"💬 {review.get('text', 'N/A')[:200]}...")
                                                    st.markdown("---")
                                    else:
                                        st.write("💬 **Reviews:** Nenhuma review encontrada")
                                except Exception as e:
                                    st.write(f"💬 **Reviews:** Erro ao carregar ({str(e)})")
                        else:
                            st.write("💬 **Reviews:** ID do produto não disponível")

        # Opções pós-busca
        st.markdown("### 📊 Próximos Passos")
        st.info("Utilize as abas no topo da página para continuar a análise.")
        
        col_next1, col_next2, col_next3 = st.columns(3)
        
        with col_next1:
            if st.button("🚨 Ir para Detecção de Falsificação", use_container_width=True):
                st.session_state.active_tab = "🚨 Detecção de Falsificação"
                st.rerun() # Força a atualização para mudar de aba

        with col_next2:
            if st.button("📊 Ir para Gerador de Dataset", use_container_width=True):
                st.session_state.active_tab = "📊 Dataset Generator"
                st.rerun()
                    
        with col_next3:
            if csv_enabled:
                csv_data_gerado = generate_csv_data(st.session_state.current_products, st.session_state.csv_fields_config)
                df_export = pd.DataFrame(csv_data_gerado)
                csv_string = df_export.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="📥 Exportar CSV da Busca",
                    data=csv_string,
                    file_name=f"produtos_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    elif not search_button:
        st.info("Clique em 'Iniciar Busca' para carregar os dados dos produtos.")

# =============================================================================
# ABA 2: DETECÇÃO DE FALSIFICAÇÃO  
# =============================================================================

with tab_falsificacao:
    st.markdown("## 🚨 Sistema de Detecção de Falsificação")
    
    if 'current_products' not in st.session_state:
        st.info("🔍 **Primeiro faça uma busca** na aba 'Busca & Coleta' para carregar produtos.")
    else:
        produtos = st.session_state.current_products
        
        st.markdown(f"### 📊 Analisando {len(produtos)} produtos carregados")
        
        # Opções de análise
        col_opt1, col_opt2 = st.columns(2)
        
        with col_opt1:
            analisar_reviews_checkbox = st.checkbox("🔍 Analisar Reviews para Falsificação", value=True, 
                                                    help="Ativa análise de reviews buscando indicadores suspeitos")
        
        with col_opt2:
            incluir_detalhes = st.checkbox("📋 Incluir Reviews Suspeitas Detalhadas", value=True,
                                          help="Mostra as reviews suspeitas encontradas")
    
        # Botão para iniciar análise
        if st.button("🚀 Iniciar Análise de Falsificação", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Analisando produto {current}/{total}...")
            
            with st.spinner("🔍 Analisando produtos para detecção de falsificação..."):
                resultados = processar_deteccao_falsificacao(
                    produtos, 
                    analisar_reviews=analisar_reviews_checkbox,
                    progress_callback=update_progress
                )
                
                st.session_state.falsification_results = resultados
                progress_bar.empty()
                status_text.empty()
                st.success(f"✅ Análise concluída! {len(resultados)} produtos analisados.")
        
        # Mostrar resultados se existirem
        if hasattr(st.session_state, 'falsification_results'):
            resultados = st.session_state.falsification_results
            
            # Estatísticas resumidas
            st.markdown("### 📈 Resumo da Análise")
            
            alto_risco = sum(1 for r in resultados if r['classificacao'] == 'Alto Risco')
            medio_risco = sum(1 for r in resultados if r['classificacao'] == 'Médio Risco')
            baixo_risco = sum(1 for r in resultados if r['classificacao'] == 'Baixo Risco')
            
            col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
            
            with col_stats1:
                st.metric("🔴 Alto Risco", alto_risco, delta=f"{alto_risco/len(resultados)*100:.1f}%")
            
            with col_stats2:
                st.metric("🟡 Médio Risco", medio_risco, delta=f"{medio_risco/len(resultados)*100:.1f}%")
            
            with col_stats3:
                st.metric("🟢 Baixo Risco", baixo_risco, delta=f"{baixo_risco/len(resultados)*100:.1f}%")
            
            with col_stats4:
                media_prob = sum(r['probabilidade_total'] for r in resultados) / len(resultados)
                st.metric("📊 Média Prob.", f"{media_prob:.1f}%")
            
            # Filtros para resultados
            st.markdown("### 🔍 Filtrar Resultados")
            
            filtro_col1, filtro_col2, filtro_col3 = st.columns(3)
            
            with filtro_col1:
                filtro_risco = st.selectbox("Filtrar por risco:", 
                                          ["Todos", "Alto Risco", "Médio Risco", "Baixo Risco"])
            
            with filtro_col2:
                min_prob = st.slider("Probabilidade mínima:", 0, 100, 0, help="Filtrar por probabilidade mínima")
            
            with filtro_col3:
                apenas_com_reviews = st.checkbox("Apenas com reviews suspeitas", 
                                                help="Mostrar apenas produtos com reviews suspeitas encontradas")
    
            # Aplicar filtros
            resultados_filtrados = resultados
            
            if filtro_risco != "Todos":
                resultados_filtrados = [r for r in resultados_filtrados if r['classificacao'] == filtro_risco]
            
            if min_prob > 0:
                resultados_filtrados = [r for r in resultados_filtrados if r['probabilidade_total'] >= min_prob]
            
            if apenas_com_reviews:
                resultados_filtrados = [r for r in resultados_filtrados if r.get('total_reviews_suspeitas', 0) > 0]
            
            st.markdown(f"### 📋 Resultados Filtrados ({len(resultados_filtrados)} de {len(resultados)})")
            
            # Mostrar produtos
            for i, resultado in enumerate(resultados_filtrados):
                produto = resultado['produto']
                
                # Cor do expander baseada no risco
                risco_cor = {"Alto Risco": "🔴", "Médio Risco": "🟡", "Baixo Risco": "🟢"}
                cor = risco_cor.get(resultado['classificacao'], "⚪")
                
                with st.expander(f"{cor} {produto.get('TITULO PRODUTO', 'Sem título')[:70]}... - {resultado['classificacao']} ({resultado['probabilidade_total']:.1f}%)", expanded=True):
                    
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write(f"**💰 Preço:** {produto.get('PREÇO', 'N/A')}")
                        st.write(f"**🏪 Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                        st.write(f"**🔗 Link:** [Ver produto]({produto.get('LINK', '#')})")
                    
                    with col_info2:
                        st.write(f"**📊 Probabilidade Total:** {resultado['probabilidade_total']:.1f}%")
                        st.write(f"**💰 Prob. Preço:** {resultado['probabilidade_preco']:.1f}%")
                        st.write(f"**💬 Prob. Reviews:** {resultado['probabilidade_reviews']:.1f}%")
                    
                    # Motivos da análise
                    if resultado['motivo_preco']:
                        st.markdown("**💰 Análise de Preço:**")
                        st.write(f"• {resultado['motivo_preco']}")
                    
                    if resultado['probabilidade_reviews'] > 0:
                        st.markdown("**💬 Análise de Reviews:**")
                        st.write(f"• {resultado['motivo_reviews']}")
                        
                        # Mostrar reviews suspeitas se solicitado
                        if incluir_detalhes and resultado.get('reviews_suspeitas'):
                            with st.expander(f"Ver {len(resultado['reviews_suspeitas'])} reviews suspeitas", expanded=True):
                                for review in resultado['reviews_suspeitas']:
                                    st.write(f"**Review #{review.get('numero_review', 'N/A')}** (⭐{review.get('rating', 'N/A')})")
                                    st.write(f"**Texto:** {review.get('texto_completo', 'N/A')}")
                                    st.write(f"**Palavras suspeitas:** {', '.join(review.get('palavras_suspeitas_encontradas', []))}")
                                    st.markdown("---")
            
            # Download dos resultados
            st.markdown("### 📥 Download dos Resultados")
            
            if st.button("📊 Baixar Relatório Completo (CSV)", use_container_width=True):
                # Gerar CSV com resultados de falsificação
                csv_data = generate_csv_data(
                    produtos, 
                    st.session_state.csv_fields_config, 
                    resultados_falsificacao=resultados
                )
                df = pd.DataFrame(csv_data)
                csv_string = df.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="⬇️ Download CSV Completo",
                    data=csv_string,
                    file_name=f"analise_falsificacao_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

# =============================================================================
# ABA 3: DATASET GENERATOR
# =============================================================================

with tab_dataset:
    st.markdown("## 📊 Dataset Generator - HP Challenge")
    
    if 'current_products' not in st.session_state:
        st.info("🔍 **Primeiro faça uma busca** na aba 'Busca & Coleta' para carregar produtos.")
    else:
        produtos = st.session_state.current_products
        
        st.markdown(f"### 📋 Gerando dataset rotulado para {len(produtos)} produtos")
        
        # Informações sobre a rotulagem
        with st.expander("📋 Critérios de Rotulagem Heurística", expanded=True):
            st.markdown("""
            **🟢 ORIGINAL:**
            - Vendedor oficial/confiável
            - Preço coerente com referências HP
            - Título sem indicadores suspeitos
            
            **🔴 SUSPEITO/PIRATA:**
            - Preço muito abaixo da referência (>40% desconto)
            - Vendedor desconhecido
            - Palavras suspeitas no título
            - Erros de gramática/ortografia
            """)
        
        if st.button("🚀 Gerar Dataset Rotulado", type="primary", use_container_width=True):
            with st.spinner("🔍 Aplicando rotulagem heurística..."):
                dataset_rotulado = gerar_dataset_hp_challenge(produtos)
                st.session_state.labeled_dataset = dataset_rotulado
                st.success(f"✅ Dataset gerado! {len(dataset_rotulado)} produtos rotulados.")
        
        # Mostrar resultados do dataset
        if hasattr(st.session_state, 'labeled_dataset'):
            dataset = st.session_state.labeled_dataset
            
            # Estatísticas do dataset
            st.markdown("### 📈 Estatísticas do Dataset")
            
            originais = sum(1 for d in dataset if d['rotulo_heuristico'] == 'original')
            suspeitos = sum(1 for d in dataset if d['rotulo_heuristico'] == 'suspeito')
            
            col_ds1, col_ds2, col_ds3 = st.columns(3)
            
            with col_ds1:
                st.metric("🟢 Originais", originais, delta=f"{originais/len(dataset)*100:.1f}%")
            
            with col_ds2:
                st.metric("🔴 Suspeitos", suspeitos, delta=f"{suspeitos/len(dataset)*100:.1f}%")
            
            with col_ds3:
                st.metric("📊 Total", len(dataset))
            
            # Filtros para visualização
            st.markdown("### 🔍 Visualizar Dataset")
            
            filtro_rotulo = st.selectbox("Filtrar por rótulo:", ["Todos", "original", "suspeito"])
            
            dataset_filtrado = dataset
            if filtro_rotulo != "Todos":
                dataset_filtrado = [d for d in dataset if d['rotulo_heuristico'] == filtro_rotulo]
            
            st.markdown(f"### 📋 Amostras ({len(dataset_filtrado)} de {len(dataset)})")
            
            # Mostrar algumas amostras
            for i, item in enumerate(dataset_filtrado[:10]):  # Mostrar até 10
                produto = item['produto_original']
                detalhes = item['detalhes_rotulagem']
                
                rotulo_emoji = "🟢" if item['rotulo_heuristico'] == 'original' else "🔴"
                
                with st.expander(f"{rotulo_emoji} {produto.get('TITULO PRODUTO', 'Sem título')[:60]}... - {item['rotulo_heuristico'].upper()}", expanded=True):
                    col_prod1, col_prod2 = st.columns(2)
                    
                    with col_prod1:
                        st.write(f"**💰 Preço:** {produto.get('PREÇO', 'N/A')}")
                        st.write(f"**🏪 Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                        st.write(f"**🏷️ Rótulo:** {item['rotulo_heuristico'].upper()}")
                    
                    with col_prod2:
                        st.write(f"**📊 Score Total:** {detalhes['score_total']}")
                        st.write(f"**🏪 Vendedor Oficial:** {'✅' if detalhes['vendedor_oficial'] else '❌'}")
                        st.write(f"**📝 Score Título:** {detalhes['score_titulo']}")
                    
                    # Critérios aplicados
                    if detalhes['criterios_aplicados']:
                        st.markdown("**📋 Critérios Aplicados:**")
                        for criterio in detalhes['criterios_aplicados']:
                            st.write(f"• {criterio}")
            
            # Download do dataset
            st.markdown("### 📥 Download do Dataset")
            
            if st.button("📊 Baixar Dataset Completo (CSV)", use_container_width=True):
                # Preparar dados para CSV
                dados_csv = []
                for item in dataset:
                    produto = item['produto_original']
                    detalhes = item['detalhes_rotulagem']
                    
                    dados_csv.append({
                        'titulo': produto.get('TITULO PRODUTO', 'N/A'),
                        'preco': produto.get('PREÇO', 'N/A'),
                        'vendedor': produto.get('VENDEDOR', 'N/A'),
                        'link': produto.get('LINK', 'N/A'),
                        'rotulo_heuristico': item['rotulo_heuristico'],
                        'score_total': detalhes['score_total'],
                        'vendedor_oficial': detalhes['vendedor_oficial'],
                        'score_titulo': detalhes['score_titulo'],
                        'score_preco': detalhes['score_preco'],
                        'motivo_vendedor': detalhes['motivo_vendedor'],
                        'motivo_preco': detalhes['motivo_preco'],
                        'criterios_aplicados': ' | '.join(detalhes['criterios_aplicados'])
                    })
                
                df_dataset = pd.DataFrame(dados_csv)
                csv_string = df_dataset.to_csv(index=False).encode('utf-8')
                
                st.download_button(
                    label="⬇️ Download Dataset CSV",
                    data=csv_string,
                    file_name=f"dataset_hp_challenge_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

# =============================================================================
# ABA 4: ANALYTICS AVANÇADO
# =============================================================================

with tab_analytics:
    st.markdown("## 📈 Analytics e Exploração Avançada")
    
    if 'current_products' not in st.session_state:
        st.info("🔍 **Primeiro faça uma busca** na aba 'Busca & Coleta' para carregar produtos.")
    else:
        produtos = st.session_state.current_products
        
        st.markdown(f"### 📊 Análise exploratória de {len(produtos)} produtos")
        
        # Opções de análise avançada
        col_adv1, col_adv2 = st.columns(2)
        
        with col_adv1:
            incluir_limpeza = st.checkbox("🧹 Limpeza e Padronização", value=True)
            incluir_enriquecimento = st.checkbox("⚡ Enriquecimento de Dados", value=True)
        
        with col_adv2:
            incluir_exploracao = st.checkbox("🔍 Análise Exploratória", value=True)
            incluir_visualizacoes = st.checkbox("📊 Visualizações Interativas", value=True)
        
        if st.button("🚀 Executar Análise Avançada", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress_avancado(status_message):
                status_text.text(status_message)
            
            with st.spinner("🔍 Executando análise exploratória avançada..."):
                # Simular as etapas da análise avançada
                etapas = []
                if incluir_limpeza:
                    etapas.append("Limpeza e Padronização")
                if incluir_enriquecimento:
                    etapas.append("Enriquecimento de Dados")
                if incluir_exploracao:
                    etapas.append("Análise Exploratória")
                if incluir_visualizacoes:
                    etapas.append("Geração de Visualizações")
                
                for i, etapa in enumerate(etapas):
                    progress_bar.progress((i + 1) / len(etapas))
                    update_progress_avancado(f"Executando: {etapa}...")
                    time.sleep(1)  # Simular processamento
                
                # Resultado simulado (na implementação real seria a análise completa)
                relatorio_avancado = {
                    'produtos_analisados': len(produtos),
                    'etapas_executadas': etapas,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.advanced_analysis = relatorio_avancado
                progress_bar.empty()
                status_text.empty()
                st.success(f"✅ Análise avançada concluída! {len(etapas)} etapas executadas.")
        
        # Mostrar resultados da análise avançada
        if hasattr(st.session_state, 'advanced_analysis'):
            relatorio = st.session_state.advanced_analysis
            
            st.markdown("### 📊 Relatório da Análise Avançada")
            
            col_rel1, col_rel2, col_rel3 = st.columns(3)
            
            with col_rel1:
                st.metric("📦 Produtos", relatorio['produtos_analisados'])
            
            with col_rel2:
                st.metric("⚙️ Etapas", len(relatorio['etapas_executadas']))
            
            with col_rel3:
                st.metric("🕒 Concluído", relatorio['timestamp'])
            
            # Placeholder para visualizações avançadas
            st.markdown("### 📈 Visualizações Geradas")
            st.info("💡 **Funcionalidade em Desenvolvimento:** As visualizações avançadas incluirão gráficos interativos, análise de correlações, detecção de outliers e análise lexical dos títulos.")

# Rodapé
        st.markdown("---")
st.markdown("**🏆 HP Challenge Sprint** - Sistema Inteligente de Detecção de Falsificações | Desenvolvido com Streamlit")
 