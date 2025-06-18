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
from plotly.subplots import make_subplots
from wordcloud import WordCloud
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import nltk
from collections import Counter
import string
from scipy import stats
from scipy.stats import chi2_contingency
import warnings
warnings.filterwarnings('ignore')

# Configurar o multiprocessing para Streamlit
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Suprimir warnings de contexto do Streamlit durante imports
import warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Importar os spiders do Scrapy
from mercadolivre_spider import run_spider, run_product_details_spider
from mercadolivre_spider_reviews import run_review_spider # Import the new review spider runner

# =============================================================================
# SISTEMA DE CACHE TEMPORÁRIO
# =============================================================================

import hashlib
import json

def get_cache_key(func_name, **kwargs):
    """
    Gera uma chave única para o cache baseada no nome da função e parâmetros
    """
    # Criar string única baseada nos parâmetros
    params_str = json.dumps(kwargs, sort_keys=True, default=str)
    cache_key = f"{func_name}_{hashlib.md5(params_str.encode()).hexdigest()}"
    return cache_key

def get_from_cache(cache_key):
    """
    Recupera dados do cache (session state)
    """
    if 'scrapy_cache' not in st.session_state:
        st.session_state.scrapy_cache = {}
    
    return st.session_state.scrapy_cache.get(cache_key)

def save_to_cache(cache_key, data):
    """
    Salva dados no cache (session state)
    """
    if 'scrapy_cache' not in st.session_state:
        st.session_state.scrapy_cache = {}
    
    st.session_state.scrapy_cache[cache_key] = data
    
    # Limitar o tamanho do cache (manter apenas os 50 itens mais recentes)
    if len(st.session_state.scrapy_cache) > 50:
        # Remover os itens mais antigos
        keys_to_remove = list(st.session_state.scrapy_cache.keys())[:-50]
        for key in keys_to_remove:
            del st.session_state.scrapy_cache[key]

def clear_cache():
    """
    Limpa todo o cache
    """
    if 'scrapy_cache' in st.session_state:
        st.session_state.scrapy_cache = {}

# =============================================================================
# FUNÇÕES WRAPPER COM CACHE
# =============================================================================

def cached_run_spider(query, extract_images=True, sort_by='relevance', condition='all', max_items=None):
    """
    Wrapper com cache para run_spider
    """
    cache_key = get_cache_key(
        'run_spider',
        query=query,
        extract_images=extract_images,
        sort_by=sort_by,
        condition=condition,
        max_items=max_items
    )
    
    # Verificar se existe no cache
    cached_data = get_from_cache(cache_key)
    if cached_data:
        logging.info(f"🔄 Usando dados do cache para busca: {query}")
        return cached_data['results'], cached_data['urls_used']
    
    # Se não existe no cache, executar scraping
    logging.info(f"🔍 Executando scraping para busca: {query}")
    results, urls_used = run_spider(query, extract_images, sort_by, condition, max_items)
    
    # Salvar no cache
    save_to_cache(cache_key, {
        'results': results,
        'urls_used': urls_used,
        'timestamp': datetime.now().isoformat()
    })
    
    return results, urls_used

def cached_run_product_details_spider(product_url):
    """
    Wrapper com cache para run_product_details_spider
    """
    if not product_url or product_url == 'N/A':
        return None
    
    cache_key = get_cache_key('run_product_details_spider', product_url=product_url)
    
    # Verificar se existe no cache
    cached_data = get_from_cache(cache_key)
    if cached_data:
        logging.info(f"🔄 Usando detalhes do produto do cache: {product_url}")
        return cached_data['details']
    
    # Se não existe no cache, executar scraping
    logging.info(f"🔍 Executando scraping de detalhes para: {product_url}")
    details = run_product_details_spider(product_url)
    
    # Salvar no cache
    save_to_cache(cache_key, {
        'details': details,
        'timestamp': datetime.now().isoformat()
    })
    
    return details

def cached_run_review_spider(product_id, max_reviews=200, rating_limits=None):
    """
    Wrapper com cache para run_review_spider
    """
    if not product_id or product_id == 'N/A':
        return None
    
    cache_key = get_cache_key(
        'run_review_spider',
        product_id=product_id,
        max_reviews=max_reviews,
        rating_limits=rating_limits
    )
    
    # Verificar se existe no cache
    cached_data = get_from_cache(cache_key)
    if cached_data:
        logging.info(f"🔄 Usando reviews do cache para produto: {product_id}")
        return cached_data['reviews_data']
    
    # Se não existe no cache, executar scraping
    logging.info(f"🔍 Executando scraping de reviews para produto: {product_id}")
    reviews_data = run_review_spider(product_id, max_reviews, rating_limits)
    
    # Salvar no cache
    save_to_cache(cache_key, {
        'reviews_data': reviews_data,
        'timestamp': datetime.now().isoformat()
    })
    
    return reviews_data

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
                product_details = cached_run_product_details_spider(produto['LINK'])
                
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
                # Determinar quantas reviews extrair baseado na configuração
                max_reviews_to_extract = 300 if reviews_fields.get('incluir_todas_reviews', False) else 50
                
                # Extrair reviews do produto
                reviews_data = cached_run_review_spider(produto_id, max_reviews=max_reviews_to_extract)
                
                if reviews_data and reviews_data.get('reviews'):
                    reviews = reviews_data.get('reviews', [])
                    
                    # Se incluir todas as reviews, criar colunas individuais
                    if reviews_fields.get('incluir_todas_reviews', False):
                        row_data['Total Reviews Extraídas'] = len(reviews)
                        
                        # Adicionar cada review como uma coluna separada (limitado a 20 para não sobrecarregar)
                        for i, review in enumerate(reviews[:20]):
                            review_num = i + 1
                            row_data[f'Review {review_num} - Rating'] = review.get('rating', 'N/A')
                            row_data[f'Review {review_num} - Data'] = review.get('date', 'N/A')
                            row_data[f'Review {review_num} - Texto'] = review.get('text', 'N/A')
                            row_data[f'Review {review_num} - Útil'] = review.get('helpful_count', '0')
                        
                        # Calcular estatísticas gerais
                        if reviews:
                            ratings = []
                            for r in reviews:
                                rating = r.get('rating', 0)
                                try:
                                    if isinstance(rating, str):
                                        rating = float(rating)
                                    elif rating is None:
                                        rating = 0
                                    ratings.append(rating)
                                except (ValueError, TypeError):
                                    ratings.append(0)
                            
                            avg_rating = sum(ratings) / len(ratings) if ratings else 0
                            row_data['Média Geral Reviews'] = f"{avg_rating:.1f}"
                            
                            # Distribuição de ratings
                            rating_counts = {}
                            for rating in ratings:
                                try:
                                    rating_int = int(rating)
                                    rating_counts[rating_int] = rating_counts.get(rating_int, 0) + 1
                                except (ValueError, TypeError):
                                    pass
                            
                            for star in range(1, 6):
                                row_data[f'Total {star}★'] = rating_counts.get(star, 0)
                    
                    else:
                        # Modo resumo/amostra (comportamento original)
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
                    if reviews_fields.get('incluir_todas_reviews', False):
                        row_data['Total Reviews Extraídas'] = 0
                        row_data['Média Geral Reviews'] = 'N/A'
                        # Preencher colunas de reviews individuais com N/A
                        for i in range(1, 21):  # Até 20 reviews
                            row_data[f'Review {i} - Rating'] = 'N/A'
                            row_data[f'Review {i} - Data'] = 'N/A'
                            row_data[f'Review {i} - Texto'] = 'N/A'
                            row_data[f'Review {i} - Útil'] = 'N/A'
                        for star in range(1, 6):
                            row_data[f'Total {star}★'] = 0
                    else:
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
                if reviews_fields.get('incluir_todas_reviews', False):
                    row_data['Total Reviews Extraídas'] = 'ERRO'
                    row_data['Média Geral Reviews'] = 'ERRO'
                    # Preencher colunas de reviews individuais com ERRO
                    for i_rev in range(1, 21):  # Até 20 reviews
                        row_data[f'Review {i_rev} - Rating'] = 'ERRO'
                        row_data[f'Review {i_rev} - Data'] = 'ERRO'
                        row_data[f'Review {i_rev} - Texto'] = 'ERRO'
                        row_data[f'Review {i_rev} - Útil'] = 'ERRO'
                    for star in range(1, 6):
                        row_data[f'Total {star}★'] = 'ERRO'
                else:
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
ERROS_GRAMATICA_FALSIFICACAO = {
    'CARTUXO', 'CARTUSHO', 'CARTTUCHO', 'KCARTUCHO',
    'TINT', 'TINTTA', 'TINTAH',
    'INPRESSORA', 'IMPRESORA', 'INPRESORA', 'IMPRESSOIRA'
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
        reviews_data = cached_run_review_spider(product_id, max_reviews=max_reviews)
        
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

# Erros de gramática comuns (apenas as grafias incorretas)
ERROS_GRAMATICA = {
    'CARTUXO', 'CARTUSHO', 'CARTTUCHO', 'KCARTUCHO',
    'TINT', 'TINTTA', 'TINTAH',
    'INPRESSORA', 'IMPRESORA', 'INPRESORA', 'IMPRESSOIRA'
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
        },
        'risk_fields': {
            'classificacao_risco': False,
            'probabilidade_total': False,
            'probabilidade_preco': False,
            'motivo_preco': False,
            'probabilidade_reviews': False,
            'motivo_reviews': False,
            'detalhes_reviews_suspeitas': False
        },
        'reviews_fields': {
            'incluir_reviews': False,
            'reviews_resumo': True,
            'reviews_texto': False,
            'reviews_rating': False,
            'reviews_data': False,
            'incluir_todas_reviews': False
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
    
    st.markdown("### 📋 Dados Detalhados")
    load_detailed_data = st.checkbox("🔍 Extrair dados detalhados dos produtos", 
                                    value=st.session_state.get('load_detailed_data', False),
                                    help="Extrai descrição e características de cada produto (mais lento)")
    st.session_state.load_detailed_data = load_detailed_data
    
    if load_detailed_data:
        col_det1, col_det2 = st.columns(2)
        with col_det1:
            include_description = st.checkbox("📝 Descrição", 
                                            value=st.session_state.get('include_description', True))
            st.session_state.include_description = include_description
            
            include_main_chars = st.checkbox("⭐ Características Principais", 
                                           value=st.session_state.get('include_main_chars', True))
            st.session_state.include_main_chars = include_main_chars
        
        with col_det2:
            include_other_chars = st.checkbox("📋 Outras Características", 
                                            value=st.session_state.get('include_other_chars', False))
            st.session_state.include_other_chars = include_other_chars
            
            include_review_stats = st.checkbox("📊 Estatísticas de Reviews", 
                                             value=st.session_state.get('include_review_stats', True))
            st.session_state.include_review_stats = include_review_stats
    
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

    # Controle de Cache
    st.markdown("## 💾 Cache de Dados")
    
    # Mostrar estatísticas do cache
    cache_size = len(st.session_state.get('scrapy_cache', {}))
    st.metric("Itens no Cache", cache_size)
    
    col_cache1, col_cache2 = st.columns(2)
    
    with col_cache1:
        if st.button("🗑️ Limpar Cache", help="Remove todos os dados em cache"):
            clear_cache()
            st.success("Cache limpo!")
            st.rerun()
    
    with col_cache2:
        if st.button("📊 Ver Cache", help="Mostra informações detalhadas do cache"):
            if cache_size > 0:
                with st.expander("📋 Detalhes do Cache", expanded=True):
                    for i, (key, data) in enumerate(st.session_state.scrapy_cache.items()):
                        timestamp = data.get('timestamp', 'N/A')
                        st.write(f"**{i+1}.** {key[:30]}...")
                        st.write(f"   📅 {timestamp}")
                        if i >= 5:  # Mostrar apenas os primeiros 5
                            st.write(f"   ... e mais {cache_size - 5} itens")
                            break
            else:
                st.info("Cache vazio")
    
    st.markdown("---")
    
    # Informações de Performance
    st.markdown("## ⚡ Performance Otimizada")
    
    with st.expander("🚀 Otimizações Implementadas", expanded=False):
        st.markdown("""
        ### 📈 Melhorias de Performance Implementadas:
        
        **🔥 Scrapy Otimizado:**
        - ✅ **Concorrência 2x maior**: 32 requisições simultâneas (vs 16 padrão)
        - ✅ **Timeouts agressivos**: 15s vs 180s padrão
        - ✅ **Cache HTTP**: 1h de cache para evitar requisições desnecessárias
        - ✅ **Pool de conexões**: Conexões HTTP persistentes
        - ✅ **DNS cache**: 10.000 entradas em cache DNS
        
        **⚡ API de Reviews Concorrente:**
        - ✅ **8 threads simultâneas**: Requisições paralelas de reviews
        - ✅ **Pool de conexões HTTP**: Reutilização de conexões
        - ✅ **Cache local**: 5 minutos de cache por requisição
        - ✅ **Retry inteligente**: 3 tentativas com backoff exponencial
        - ✅ **Filtro de duplicatas otimizado**: Usando sets para O(1)
        
        **💾 Sistema de Cache Avançado:**
        - ✅ **Cache em memória**: Session state do Streamlit
        - ✅ **Chaves MD5**: Identificação única de requisições
        - ✅ **Limite inteligente**: Máximo 50 itens com rotação automática
        - ✅ **Cache por tipo**: Separado para busca, detalhes e reviews
        
        **🎯 Configurações Adaptativas:**
        - ✅ **Alto volume**: 64 requisições para >100 produtos
        - ✅ **Volume normal**: 32 requisições padrão
        - ✅ **Timeouts dinâmicos**: Baseados no número de itens
        """)
    
    with st.expander("📊 Estimativas de Performance", expanded=False):
        st.markdown("""
        ### ⏱️ Tempos Estimados (com otimizações):
        
        **🔍 Busca de Produtos:**
        - 20 produtos: ~10-15 segundos (vs 30-45s anterior)
        - 50 produtos: ~20-30 segundos (vs 60-90s anterior)
        - 100 produtos: ~40-60 segundos (vs 2-3min anterior)
        
        **📋 Detalhes de Produtos:**
        - Por produto: ~2-3 segundos (vs 5-8s anterior)
        - Cache hit: ~0.1 segundos (instantâneo)
        
        **⭐ Reviews:**
        - 50 reviews: ~3-5 segundos (vs 10-15s anterior)
        - 200 reviews: ~8-12 segundos (vs 30-45s anterior)
        - Cache hit: ~0.1 segundos (instantâneo)
        
        **🚨 Análise de Falsificação:**
        - 20 produtos: ~15-25 segundos (vs 45-60s anterior)
        - 50 produtos: ~30-45 segundos (vs 2-3min anterior)
        
        ### 📈 Melhorias Alcançadas:
        - 🚀 **2-3x mais rápido** na maioria das operações
        - 💾 **Cache inteligente** reduz tempo para operações repetidas
        - 🔄 **Requisições concorrentes** maximizam uso da banda
        - ⚡ **Timeouts otimizados** evitam esperas desnecessárias
        """)
    
    st.markdown("---")

# =============================================================================
# ÁREA PRINCIPAL - ABAS ORGANIZADAS
# =============================================================================

# Criar abas principais para organizar funcionalidades
tab_busca, tab_falsificacao, tab_dataset, tab_data_analysis = st.tabs([
    "🔍 Busca & Coleta", 
    "🚨 Detecção de Falsificação", 
    "📊 Dataset Generator",
    "🔬 Análise Exploratória (EDA)"
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
        # Verificar se existe no cache
        cache_key = get_cache_key(
            'run_spider',
            query=search_query,
            extract_images=load_images,
            sort_by=sort_value,
            condition=condition_value,
            max_items=max_items
        )
        
        cached_data = get_from_cache(cache_key)
        if cached_data:
            st.info("🔄 Dados encontrados no cache! Carregando instantaneamente...")
            search_results, urls_used = cached_data['results'], cached_data['urls_used']
        else:
            with st.spinner(f"🔍 Buscando '{search_query}' no Mercado Livre..."):
                search_results, urls_used = cached_run_spider(
                    query=search_query,
                    max_items=max_items, 
                    sort_by=sort_value,
                    condition=condition_value,
                    extract_images=load_images
                )
        
        if search_results:
            # Enriquecer com dados detalhados se solicitado
            if st.session_state.get('load_detailed_data', False):
                with st.spinner("🔍 Extraindo dados detalhados dos produtos..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, produto in enumerate(search_results):
                        progress = (i + 1) / len(search_results)
                        progress_bar.progress(progress)
                        status_text.text(f"Extraindo detalhes {i+1}/{len(search_results)}: {produto.get('TITULO PRODUTO', 'N/A')[:50]}...")
                        
                        if produto.get('LINK') and produto.get('LINK') != 'N/A':
                            try:
                                product_details = cached_run_product_details_spider(produto['LINK'])
                                
                                if product_details and product_details.get('extraction_success'):
                                    # Adicionar dados detalhados baseado nas configurações
                                    if st.session_state.get('include_description', True):
                                        produto['DESCRICAO'] = product_details.get('description', 'N/A')
                                    
                                    if st.session_state.get('include_main_chars', True):
                                        main_chars = product_details.get('main_characteristics', {})
                                        produto['CARACTERISTICAS_PRINCIPAIS'] = main_chars if main_chars else 'N/A'
                                    
                                    if st.session_state.get('include_other_chars', False):
                                        other_chars = product_details.get('other_characteristics', {})
                                        produto['OUTRAS_CARACTERISTICAS'] = other_chars if other_chars else 'N/A'
                                    
                                    if st.session_state.get('include_review_stats', True):
                                        review_stats = product_details.get('review_stats', {})
                                        produto['REVIEW_STATS'] = review_stats if review_stats else 'N/A'
                                else:
                                    # Preencher com N/A se extração falhou
                                    if st.session_state.get('include_description', True):
                                        produto['DESCRICAO'] = 'N/A'
                                    if st.session_state.get('include_main_chars', True):
                                        produto['CARACTERISTICAS_PRINCIPAIS'] = 'N/A'
                                    if st.session_state.get('include_other_chars', False):
                                        produto['OUTRAS_CARACTERISTICAS'] = 'N/A'
                                    if st.session_state.get('include_review_stats', True):
                                        produto['REVIEW_STATS'] = 'N/A'
                                        
                            except Exception as e:
                                logging.error(f"Erro ao extrair detalhes do produto {i+1}: {str(e)}")
                                # Preencher com ERRO em caso de falha
                                if st.session_state.get('include_description', True):
                                    produto['DESCRICAO'] = 'ERRO'
                                if st.session_state.get('include_main_chars', True):
                                    produto['CARACTERISTICAS_PRINCIPAIS'] = 'ERRO'
                                if st.session_state.get('include_other_chars', False):
                                    produto['OUTRAS_CARACTERISTICAS'] = 'ERRO'
                                if st.session_state.get('include_review_stats', True):
                                    produto['REVIEW_STATS'] = 'ERRO'
                    
                    progress_bar.empty()
                    status_text.empty()
                    st.success("✅ Dados detalhados extraídos com sucesso!")
            
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
                    
                    # Exibir dados detalhados se disponíveis
                    if st.session_state.get('load_detailed_data', False):
                        st.markdown("### 📋 Dados Detalhados")
                        
                        if produto.get('DESCRICAO') and produto['DESCRICAO'] not in ['N/A', 'ERRO']:
                            st.markdown("**📝 Descrição:**")
                            st.write(produto['DESCRICAO'])
                            st.markdown("---")
                        
                        if produto.get('CARACTERISTICAS_PRINCIPAIS') and produto['CARACTERISTICAS_PRINCIPAIS'] not in ['N/A', 'ERRO']:
                            st.markdown("**⭐ Características Principais:**")
                            chars = produto['CARACTERISTICAS_PRINCIPAIS']
                            if isinstance(chars, dict):
                                for key, value in chars.items():
                                    st.write(f"• **{key}:** {value}")
                            else:
                                st.write(chars)
                            st.markdown("---")
                        
                        if produto.get('OUTRAS_CARACTERISTICAS') and produto['OUTRAS_CARACTERISTICAS'] not in ['N/A', 'ERRO']:
                            st.markdown("**📋 Outras Características:**")
                            chars = produto['OUTRAS_CARACTERISTICAS']
                            if isinstance(chars, dict):
                                for key, value in chars.items():
                                    st.write(f"• **{key}:** {value}")
                            else:
                                st.write(chars)
                            st.markdown("---")
                        
                        if produto.get('REVIEW_STATS') and produto['REVIEW_STATS'] not in ['N/A', 'ERRO']:
                            st.markdown("**📊 Estatísticas de Reviews Detalhadas:**")
                            stats = produto['REVIEW_STATS']
                            if isinstance(stats, dict):
                                if stats.get('total_reviews'):
                                    st.write(f"• **Total de Reviews:** {stats['total_reviews']}")
                                if stats.get('star_distribution'):
                                    st.write("• **Distribuição por Estrelas:**")
                                    for star, data in stats['star_distribution'].items():
                                        if isinstance(data, dict):
                                            percentage = data.get('percentage', 0)
                                            count = data.get('count', 0)
                                            st.write(f"  ⭐ {star} estrelas: {count} ({percentage}%)")
                            else:
                                st.write(stats)
                            st.markdown("---")
                    
                    # Seção de Reviews
                    produto_id = produto.get('ID_PRODUTO')
                    if produto_id and produto_id != 'N/A':
                        # Exibir reviews resumidas se configurado
                        if st.session_state.get('extract_reviews', False):
                            # Verificar se reviews estão no cache
                            reviews_cache_key = get_cache_key(
                                'run_review_spider',
                                product_id=produto_id,
                                max_reviews=st.session_state.get('max_reviews_to_fetch', 50),
                                rating_limits=None
                            )
                            
                            cached_reviews = get_from_cache(reviews_cache_key)
                            if cached_reviews:
                                st.info("🔄 Reviews do cache")
                                reviews_data = cached_reviews['reviews_data']
                                
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
                                        
                                        # Mostrar algumas reviews diretamente (sem expander aninhado)
                                        st.markdown("**📝 Primeiras 3 Reviews:**")
                                        for j, review in enumerate(reviews[:3]):
                                            st.markdown(f"**Review {j+1}:** ⭐ {review.get('rating', 'N/A')}/5")
                                            st.write(f"📅 {review.get('date', 'N/A')}")
                                            st.write(f"💬 {review.get('text', 'N/A')[:150]}...")
                                            if j < 2:  # Adicionar separador entre reviews (exceto na última)
                                                st.markdown("---")
                                else:
                                    st.write("💬 **Reviews:** Nenhuma review encontrada")
                            else:
                                st.write("💬 **Reviews:** Não carregadas (use o botão abaixo)")
                        
                        # Botão para mostrar todas as reviews
                        if st.button(f"📋 Ver Todas as Reviews", key=f"all_reviews_{i}", use_container_width=True):
                                with st.spinner("🔍 Carregando todas as reviews..."):
                                    try:
                                        # Carregar mais reviews (até 200)
                                        all_reviews_data = cached_run_review_spider(produto_id, max_reviews=200)
                                        
                                        if all_reviews_data and all_reviews_data.get('reviews'):
                                            all_reviews = all_reviews_data.get('reviews', [])
                                            
                                            # Mostrar todas as reviews em uma nova seção
                                            st.markdown(f"### 📋 Todas as {len(all_reviews)} Reviews")
                                            
                                            # Calcular estatísticas
                                            if all_reviews:
                                                ratings = []
                                                for r in all_reviews:
                                                    rating = r.get('rating', 0)
                                                    try:
                                                        if isinstance(rating, str):
                                                            rating = float(rating)
                                                        elif rating is None:
                                                            rating = 0
                                                        ratings.append(rating)
                                                    except (ValueError, TypeError):
                                                        ratings.append(0)
                                                
                                                if ratings:
                                                    # Métricas principais
                                                    avg_rating = sum(ratings) / len(ratings)
                                                    max_rating = max(ratings) if ratings else 0
                                                    
                                                    st.write(f"📊 **Estatísticas Gerais:**")
                                                    st.write(f"• Média Geral: **{avg_rating:.1f}/5**")
                                                    st.write(f"• Total de Reviews: **{len(all_reviews)}**")
                                                    st.write(f"• Rating Máximo: **{max_rating:.0f}/5**")
                                                    
                                                    # Distribuição por estrelas
                                                    star_counts = {}
                                                    for rating in ratings:
                                                        star = int(rating) if rating > 0 else 0
                                                        star_counts[star] = star_counts.get(star, 0) + 1
                                                    
                                                    st.markdown("**📊 Distribuição por Estrelas:**")
                                                    for star in range(5, 0, -1):
                                                        count = star_counts.get(star, 0)
                                                        percentage = (count / len(ratings)) * 100
                                                        st.write(f"⭐ {star} estrelas: {count} reviews ({percentage:.1f}%)")
                                                    
                                                    st.markdown("---")
                                            
                                            # Lista completa de reviews
                                            st.markdown("**💬 Lista Completa de Reviews:**")
                                            
                                            # Mostrar todas as reviews
                                            for j, review in enumerate(all_reviews):
                                                st.markdown(f"**Review #{j+1}**")
                                                st.write(f"⭐ **Rating:** {review.get('rating', 'N/A')}/5 | 📅 **Data:** {review.get('date', 'N/A')} | 👍 **Útil:** {review.get('helpful_count', '0')}")
                                                st.write(f"💬 **Comentário:** {review.get('text', 'N/A')}")
                                                
                                                if j < len(all_reviews) - 1:
                                                    st.markdown("---")
                                        else:
                                            st.error("❌ Não foi possível carregar as reviews")
                                    except Exception as e:
                                        st.error(f"❌ Erro ao carregar reviews: {str(e)}")
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
            if st.button("📊 Ir para Gerador CSV", use_container_width=True):
                st.session_state.active_tab = "📊 Dataset Generator"
                st.rerun()
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
    st.markdown("## 📊 Dataset Generator & CSV Export")
    
    if 'current_products' not in st.session_state:
        st.info("🔍 **Primeiro faça uma busca** na aba 'Busca & Coleta' para carregar produtos.")
    else:
        produtos = st.session_state.current_products
        
        # Criar duas colunas principais
        col_main, col_config = st.columns([2, 1])
        
        with col_config:
            st.markdown("### ⚙️ Configurações de Export")
            
            # As configurações já foram inicializadas no topo do arquivo
            
            # Configurações de campos básicos
            with st.expander("📋 Dados Básicos", expanded=True):
                basic_fields = st.session_state.csv_fields_config.get('basic_fields', {})
                
                basic_all = st.checkbox("✅ Todos os campos básicos", value=all(basic_fields.values()))
                if basic_all != all(basic_fields.values()):
                    for field in basic_fields:
                        basic_fields[field] = basic_all
                
                if not basic_all:
                    basic_fields['titulo'] = st.checkbox("Título", value=basic_fields.get('titulo', True))
                    basic_fields['preco'] = st.checkbox("Preço", value=basic_fields.get('preco', True))
                    basic_fields['preco_anterior'] = st.checkbox("Preço Anterior", value=basic_fields.get('preco_anterior', True))
                    basic_fields['marca'] = st.checkbox("Marca", value=basic_fields.get('marca', True))
                    basic_fields['vendedor'] = st.checkbox("Vendedor", value=basic_fields.get('vendedor', True))
                    basic_fields['link'] = st.checkbox("Link", value=basic_fields.get('link', True))
                    basic_fields['id_produto'] = st.checkbox("ID Produto", value=basic_fields.get('id_produto', True))
                    basic_fields['imagem'] = st.checkbox("URL Imagem", value=basic_fields.get('imagem', False))
                    basic_fields['entrega'] = st.checkbox("Entrega", value=basic_fields.get('entrega', True))
                    basic_fields['entrega_full'] = st.checkbox("Entrega FULL", value=basic_fields.get('entrega_full', True))
                    basic_fields['media_avaliacoes_busca'] = st.checkbox("Média Avaliações", value=basic_fields.get('media_avaliacoes_busca', True))
                    basic_fields['total_avaliacoes_busca'] = st.checkbox("Total Avaliações", value=basic_fields.get('total_avaliacoes_busca', True))
            
            # Configurações de campos detalhados
            with st.expander("🔍 Dados Detalhados", expanded=False):
                detailed_fields = st.session_state.csv_fields_config.get('detailed_fields', {})
                
                detailed_all = st.checkbox("✅ Todos os campos detalhados", value=all(detailed_fields.values()))
                if detailed_all != all(detailed_fields.values()):
                    for field in detailed_fields:
                        detailed_fields[field] = detailed_all
                
                if not detailed_all:
                    detailed_fields['descricao'] = st.checkbox("Descrição", value=detailed_fields.get('descricao', False))
                    detailed_fields['caracteristicas_principais'] = st.checkbox("Características Principais", value=detailed_fields.get('caracteristicas_principais', False))
                    detailed_fields['outras_caracteristicas'] = st.checkbox("Outras Características", value=detailed_fields.get('outras_caracteristicas', False))
                    detailed_fields['total_reviews_detalhado'] = st.checkbox("Total Reviews Detalhado", value=detailed_fields.get('total_reviews_detalhado', True))
                    detailed_fields['distribuicao_estrelas'] = st.checkbox("Distribuição por Estrelas", value=detailed_fields.get('distribuicao_estrelas', True))
            
            # Configurações de análise de risco
            with st.expander("🚨 Análise de Risco", expanded=False):
                risk_fields = st.session_state.csv_fields_config.get('risk_fields', {})
                
                # Inicializar risk_fields se estiver vazio
                if not risk_fields:
                    risk_fields = {
                        'classificacao_risco': False,
                        'probabilidade_total': False,
                        'probabilidade_preco': False,
                        'motivo_preco': False,
                        'probabilidade_reviews': False,
                        'motivo_reviews': False,
                        'detalhes_reviews_suspeitas': False
                    }
                    st.session_state.csv_fields_config['risk_fields'] = risk_fields
                
                risk_all = st.checkbox("✅ Todos os campos de risco", value=all(risk_fields.values()))
                if risk_all != all(risk_fields.values()):
                    for field in risk_fields:
                        risk_fields[field] = risk_all
                
                if not risk_all:
                    risk_fields['classificacao_risco'] = st.checkbox("Classificação de Risco", value=risk_fields.get('classificacao_risco', False))
                    risk_fields['probabilidade_total'] = st.checkbox("Probabilidade Total", value=risk_fields.get('probabilidade_total', False))
                    risk_fields['probabilidade_preco'] = st.checkbox("Probabilidade Preço", value=risk_fields.get('probabilidade_preco', False))
                    risk_fields['motivo_preco'] = st.checkbox("Motivo Análise Preço", value=risk_fields.get('motivo_preco', False))
                    risk_fields['probabilidade_reviews'] = st.checkbox("Probabilidade Reviews", value=risk_fields.get('probabilidade_reviews', False))
                    risk_fields['motivo_reviews'] = st.checkbox("Motivo Análise Reviews", value=risk_fields.get('motivo_reviews', False))
                    risk_fields['detalhes_reviews_suspeitas'] = st.checkbox("Detalhes Reviews Suspeitas", value=risk_fields.get('detalhes_reviews_suspeitas', False))
            
            # Configurações de reviews
            with st.expander("⭐ Reviews", expanded=True):
                reviews_fields = st.session_state.csv_fields_config.get('reviews_fields', {})
                
                reviews_fields['incluir_reviews'] = st.checkbox("📝 Incluir Reviews no CSV", value=reviews_fields.get('incluir_reviews', False))
                
                if reviews_fields['incluir_reviews']:
                    reviews_fields['incluir_todas_reviews'] = st.checkbox("📚 Incluir TODAS as Reviews", 
                                                                         value=reviews_fields.get('incluir_todas_reviews', False),
                                                                         help="Inclui o texto completo de todas as reviews (pode gerar arquivos grandes)")
                    
                    if not reviews_fields['incluir_todas_reviews']:
                        reviews_fields['reviews_resumo'] = st.checkbox("📊 Resumo de Reviews", value=reviews_fields.get('reviews_resumo', True))
                        reviews_fields['reviews_texto'] = st.checkbox("📝 Texto das Reviews (amostra)", value=reviews_fields.get('reviews_texto', False))
                        reviews_fields['reviews_rating'] = st.checkbox("⭐ Rating das Reviews", value=reviews_fields.get('reviews_rating', False))
                        reviews_fields['reviews_data'] = st.checkbox("📅 Data das Reviews", value=reviews_fields.get('reviews_data', False))
        
        with col_main:
            st.markdown(f"### 📋 Dados carregados: {len(produtos)} produtos")
            
            # Seção de Dataset Heurístico
            st.markdown("#### 🏷️ Dataset com Rotulagem Heurística")
            
            # Informações sobre a rotulagem
            with st.expander("📋 Critérios de Rotulagem Heurística", expanded=False):
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
            
            # Seção de Export CSV
            st.markdown("#### 📥 Export CSV Personalizado")
            
            col_csv1, col_csv2 = st.columns(2)
            
            with col_csv1:
                if st.button("📊 Gerar CSV dos Produtos", use_container_width=True):
                    with st.spinner("📊 Gerando CSV personalizado..."):
                        csv_data_gerado = generate_csv_data(produtos, st.session_state.csv_fields_config)
                        df_export = pd.DataFrame(csv_data_gerado)
                        csv_string = df_export.to_csv(index=False).encode('utf-8')
                        
                        st.download_button(
                            label="⬇️ Download CSV dos Produtos",
                            data=csv_string,
                            file_name=f"produtos_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        st.success(f"✅ CSV gerado com {len(csv_data_gerado)} produtos!")
            
            with col_csv2:
                if hasattr(st.session_state, 'falsification_results'):
                    if st.button("🚨 Gerar CSV com Análise de Risco", use_container_width=True):
                        with st.spinner("🚨 Gerando CSV com análise de falsificação..."):
                            csv_data_risco = generate_csv_data(produtos, st.session_state.csv_fields_config, st.session_state.falsification_results)
                            df_risco = pd.DataFrame(csv_data_risco)
                            csv_risco_string = df_risco.to_csv(index=False).encode('utf-8')
                            
                            st.download_button(
                                label="⬇️ Download CSV com Análise de Risco",
                                data=csv_risco_string,
                                file_name=f"produtos_analise_risco_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                            
                            st.success(f"✅ CSV com análise de risco gerado!")
                else:
                    st.info("🚨 Execute a análise de falsificação primeiro para gerar CSV com dados de risco")
        
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
# FUNÇÕES AUXILIARES PARA EDA (ANÁLISE EXPLORATÓRIA DE DADOS)
# =============================================================================

def clean_text_for_analysis(text):
    """
    Limpa texto para análise, removendo caracteres especiais e normalizando
    """
    if pd.isna(text) or text == 'N/A':
        return ""
    
    # Converter para string
    text = str(text)
    
    # Verificar se é uma URL e retornar vazio se for
    if text.startswith(('http://', 'https://', 'www.', 'ftp://')) or '.com' in text or '.br' in text:
        return ""
    
    # Converter para minúsculas
    text = text.lower()
    
    # Remover apenas alguns caracteres especiais, mantendo letras e números
    # Manter números porque são importantes para produtos HP (664, 662, etc.)
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove pontuação mas mantém letras, números e espaços
    
    # Remover palavras muito comuns que não agregam valor e URLs
    stopwords_custom = ['de', 'da', 'do', 'para', 'com', 'em', 'a', 'o', 'e', 'que', 'ml', 'mlb', 
                       'mercadolivre', 'mercado', 'livre', 'www', 'http', 'https', 'com', 'br']
    words = text.split()
    words = [word for word in words if word not in stopwords_custom and len(word) > 1 
             and not word.startswith('http') and not word.endswith('.com') and not word.endswith('.br')]
    
    # Juntar palavras novamente
    text = ' '.join(words)
    
    # Remover espaços extras
    text = ' '.join(text.split())
    
    return text

def extract_ngrams(texts, n=2, max_features=20):
    """
    Extrai n-gramas mais frequentes dos textos
    """
    # Limpar textos e filtrar vazios
    cleaned_texts = []
    for text in texts:
        if text and text != 'N/A' and str(text).strip():
            cleaned = clean_text_for_analysis(text)
            if cleaned and len(cleaned.split()) >= n:  # Garantir que há palavras suficientes para n-gramas
                cleaned_texts.append(cleaned)
    
    if not cleaned_texts:
        return []
    
    # Verificar se há conteúdo suficiente
    total_words = sum(len(text.split()) for text in cleaned_texts)
    if total_words < n:
        return []
    
    # Usar CountVectorizer para extrair n-gramas
    vectorizer = CountVectorizer(
        ngram_range=(n, n),
        max_features=max_features,
        stop_words=None,  # Não usar stopwords automáticas para manter controle
        min_df=1,  # Mínimo de documentos para uma palavra aparecer
        token_pattern=r'\b\w+\b'  # Padrão para tokens
    )
    
    try:
        ngram_matrix = vectorizer.fit_transform(cleaned_texts)
        
        # Verificar se há features
        if ngram_matrix.shape[1] == 0:
            return []
            
        feature_names = vectorizer.get_feature_names_out()
        ngram_counts = ngram_matrix.sum(axis=0).A1
        
        # Criar lista de n-gramas ordenados por frequência
        ngrams = [(feature_names[i], ngram_counts[i]) for i in range(len(feature_names))]
        ngrams.sort(key=lambda x: x[1], reverse=True)
        
        return ngrams
    except ValueError as e:
        if "empty vocabulary" in str(e).lower():
            return []  # Retornar lista vazia silenciosamente para vocabulário vazio
        else:
            st.warning(f"⚠️ Erro ao extrair {n}-gramas: {str(e)}")
            return []
    except Exception as e:
        st.warning(f"⚠️ Erro inesperado ao extrair {n}-gramas: {str(e)}")
        return []

def generate_wordcloud_data(texts, max_words=100):
    """
    Gera dados para wordcloud a partir de textos
    """
    # Filtrar e limpar textos
    valid_texts = []
    for text in texts:
        if text and text != 'N/A' and str(text).strip():
            cleaned = clean_text_for_analysis(text)
            if cleaned and len(cleaned.strip()) > 0:
                valid_texts.append(cleaned)
    
    if not valid_texts:
        return None
    
    # Combinar todos os textos
    all_text = ' '.join(valid_texts)
    
    if not all_text.strip():
        return None
    
    try:
        # Stopwords customizadas para produtos HP
        custom_stopwords = set([
            'mercado', 'livre', 'ml', 'mlb', 'produto', 'item', 'novo', 'usado',
            'vendido', 'por', 'em', 'de', 'da', 'do', 'para', 'com', 'na', 'no',
            'a', 'o', 'e', 'que', 'se', 'mais', 'muito', 'bem', 'como', 'sua',
            'seu', 'uma', 'um', 'esta', 'este', 'isso', 'aqui', 'ali', 'onde'
        ])
        
        # Gerar wordcloud
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=max_words,
            colormap='viridis',
            stopwords=custom_stopwords,
            min_font_size=10,
            max_font_size=80,
            relative_scaling=0.5,
            collocations=False  # Evitar repetições de palavras próximas
        ).generate(all_text)
        
        return wordcloud
    except Exception as e:
        st.warning(f"⚠️ Erro ao gerar wordcloud: {str(e)}")
        return None

def calculate_price_segments(prices, num_segments=5):
    """
    Calcula segmentos de preço baseado em quantis
    """
    if not prices or len(prices) == 0:
        return [], []
    
    # Remover valores nulos
    valid_prices = [p for p in prices if pd.notna(p) and p > 0]
    
    if len(valid_prices) == 0:
        return [], []
    
    # Calcular quantis
    quantiles = np.linspace(0, 1, num_segments + 1)
    price_quantiles = np.quantile(valid_prices, quantiles)
    
    # Criar labels dos segmentos
    segment_labels = []
    for i in range(len(price_quantiles) - 1):
        label = f"R$ {price_quantiles[i]:.2f} - R$ {price_quantiles[i+1]:.2f}"
        segment_labels.append(label)
    
    return price_quantiles, segment_labels

def perform_correlation_analysis(df, numeric_columns):
    """
    Realiza análise de correlação entre variáveis numéricas
    """
    if len(numeric_columns) < 2:
        return None
    
    # Calcular matriz de correlação
    correlation_matrix = df[numeric_columns].corr()
    
    return correlation_matrix

def detect_outliers_iqr(data, column):
    """
    Detecta outliers usando método IQR
    """
    if column not in data.columns or data[column].dtype not in ['int64', 'float64']:
        return []
    
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = data[(data[column] < lower_bound) | (data[column] > upper_bound)]
    return outliers

def analyze_categorical_distribution(df, column):
    """
    Analisa distribuição de variável categórica
    """
    if column not in df.columns:
        return None
    
    # Contar frequências
    value_counts = df[column].value_counts()
    
    # Calcular percentuais
    percentages = (value_counts / len(df)) * 100
    
    # Combinar contagens e percentuais
    distribution = pd.DataFrame({
        'Contagem': value_counts,
        'Percentual': percentages.round(2)
    })
    
    return distribution

def create_price_rating_segments(df, price_col, rating_col):
    """
    Cria segmentos combinados de preço e rating para análise
    """
    if price_col not in df.columns or rating_col not in df.columns:
        return None
    
    # Criar cópias das colunas para análise
    df_analysis = df[[price_col, rating_col]].copy()
    df_analysis = df_analysis.dropna()
    
    if len(df_analysis) == 0:
        return None
    
    # Criar segmentos de preço (baixo, médio, alto)
    price_quantiles = df_analysis[price_col].quantile([0.33, 0.67])
    df_analysis['price_segment'] = pd.cut(
        df_analysis[price_col], 
        bins=[-np.inf, price_quantiles.iloc[0], price_quantiles.iloc[1], np.inf],
        labels=['Baixo', 'Médio', 'Alto']
    )
    
    # Criar segmentos de rating (baixo, médio, alto)
    rating_quantiles = df_analysis[rating_col].quantile([0.33, 0.67])
    df_analysis['rating_segment'] = pd.cut(
        df_analysis[rating_col], 
        bins=[-np.inf, rating_quantiles.iloc[0], rating_quantiles.iloc[1], np.inf],
        labels=['Baixo', 'Médio', 'Alto']
    )
    
    # Criar tabela de contingência
    contingency_table = pd.crosstab(df_analysis['price_segment'], df_analysis['rating_segment'])
    
    return contingency_table, df_analysis

# =============================================================================
# ABA 4: ANÁLISE DE DATASET (EDA)
# =============================================================================

def detect_column_mappings(df):
    """
    Detecta automaticamente as colunas relevantes do dataset baseado em padrões comuns
    """
    column_mappings = {
        'title': None,
        'price': None,
        'seller': None,
        'rating': None,
        'review_count': None,
        'brand': None,
        'link': None
    }
    
    # Converter nomes de colunas para minúsculas para comparação
    df_columns_lower = {col.lower(): col for col in df.columns}
    
    # Detectar coluna de título (excluindo colunas de URL/link)
    title_patterns = ['titulo', 'title', 'nome', 'produto', 'name', 'item']
    url_patterns = ['link', 'url', 'endereco', 'address', 'imagem', 'image', 'foto', 'picture']
    
    for pattern in title_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() 
                  if pattern in col_lower and not any(url_pattern in col_lower for url_pattern in url_patterns)]
        if matches:
            column_mappings['title'] = matches[0]
            break
    
    # Detectar coluna de preço
    price_patterns = ['preço', 'preco', 'price', 'valor', 'custo', 'cost']
    for pattern in price_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower and 'anterior' not in col_lower]
        if matches:
            column_mappings['price'] = matches[0]
            break
    
    # Detectar coluna de vendedor
    seller_patterns = ['vendedor', 'seller', 'loja', 'store', 'merchant']
    for pattern in seller_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower]
        if matches:
            column_mappings['seller'] = matches[0]
            break
    
    # Detectar coluna de avaliação média
    rating_patterns = ['media', 'rating', 'avaliacao', 'estrela', 'star', 'nota']
    for pattern in rating_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower and 'total' not in col_lower]
        if matches:
            column_mappings['rating'] = matches[0]
            break
    
    # Detectar coluna de total de avaliações
    review_count_patterns = ['total', 'count', 'quantidade', 'qtd', 'num']
    for pattern in review_count_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower and ('avaliacao' in col_lower or 'review' in col_lower)]
        if matches:
            column_mappings['review_count'] = matches[0]
            break
    
    # Detectar coluna de marca
    brand_patterns = ['marca', 'brand', 'fabricante', 'manufacturer']
    for pattern in brand_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower]
        if matches:
            column_mappings['brand'] = matches[0]
            break
    
    # Detectar coluna de link
    link_patterns = ['link', 'url', 'endereco', 'address']
    for pattern in link_patterns:
        matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower]
        if matches:
            column_mappings['link'] = matches[0]
            break
    
    return column_mappings

def prepare_dataframe(df, column_mappings):
    """
    Prepara o dataframe padronizando as colunas e convertendo tipos de dados
    """
    prepared_df = df.copy()
    
    # Criar colunas padronizadas
    if column_mappings['price']:
        # Tentar extrair valores numéricos de preços
        price_col = column_mappings['price']
        # Limpar dados de preço removendo caracteres não numéricos exceto vírgulas e pontos
        prepared_df['PRICE_NUMERIC'] = prepared_df[price_col].astype(str).str.replace(r'[^\d,.]', '', regex=True)
        # Substituir vírgulas por pontos para conversão
        prepared_df['PRICE_NUMERIC'] = prepared_df['PRICE_NUMERIC'].str.replace(',', '.')
        # Converter para numérico usando pd.to_numeric que é mais robusto
        prepared_df['PRICE_NUMERIC'] = pd.to_numeric(prepared_df['PRICE_NUMERIC'], errors='coerce')
    
    if column_mappings['rating']:
        # Converter avaliações para numérico
        rating_col = column_mappings['rating']
        prepared_df['RATING_NUMERIC'] = pd.to_numeric(prepared_df[rating_col], errors='coerce')
    
    if column_mappings['review_count']:
        # Converter contagem de reviews para numérico
        review_col = column_mappings['review_count']
        prepared_df['REVIEW_COUNT_NUMERIC'] = pd.to_numeric(prepared_df[review_col], errors='coerce')
    
    return prepared_df

def show_column_detection_summary(column_mappings, df):
    """
    Mostra um resumo das colunas detectadas automaticamente
    """
    st.markdown("### 🔍 Detecção Automática de Colunas")
    
    detection_results = []
    for key, value in column_mappings.items():
        status = "✅ Detectada" if value else "❌ Não encontrada"
        detection_results.append({
            'Campo': key.replace('_', ' ').title(),
            'Coluna Detectada': value if value else 'N/A',
            'Status': status
        })
    
    detection_df = pd.DataFrame(detection_results)
    st.dataframe(detection_df, use_container_width=True)
    
    # Permitir override manual das detecções
    with st.expander("🔧 Ajustar Detecção de Colunas", expanded=False):
        st.markdown("**Selecione manualmente as colunas se a detecção automática estiver incorreta:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            title_override = st.selectbox("Coluna de Título:", ["Auto"] + list(df.columns), 
                                        index=0 if not column_mappings['title'] else list(df.columns).index(column_mappings['title']) + 1)
            price_override = st.selectbox("Coluna de Preço:", ["Auto"] + list(df.columns),
                                        index=0 if not column_mappings['price'] else list(df.columns).index(column_mappings['price']) + 1)
            seller_override = st.selectbox("Coluna de Vendedor:", ["Auto"] + list(df.columns),
                                         index=0 if not column_mappings['seller'] else list(df.columns).index(column_mappings['seller']) + 1)
        
        with col2:
            rating_override = st.selectbox("Coluna de Avaliação:", ["Auto"] + list(df.columns),
                                         index=0 if not column_mappings['rating'] else list(df.columns).index(column_mappings['rating']) + 1)
            review_count_override = st.selectbox("Coluna de Total Reviews:", ["Auto"] + list(df.columns),
                                                index=0 if not column_mappings['review_count'] else list(df.columns).index(column_mappings['review_count']) + 1)
            brand_override = st.selectbox("Coluna de Marca:", ["Auto"] + list(df.columns),
                                        index=0 if not column_mappings['brand'] else list(df.columns).index(column_mappings['brand']) + 1)
        
        # Aplicar overrides se selecionados
        if title_override != "Auto":
            column_mappings['title'] = title_override
        if price_override != "Auto":
            column_mappings['price'] = price_override
        if seller_override != "Auto":
            column_mappings['seller'] = seller_override
        if rating_override != "Auto":
            column_mappings['rating'] = rating_override
        if review_count_override != "Auto":
            column_mappings['review_count'] = review_count_override
        if brand_override != "Auto":
            column_mappings['brand'] = brand_override
    
    return column_mappings

# =============================================================================
# FUNÇÕES AUXILIARES PARA LIMPEZA DE REVIEWS
# =============================================================================

def detect_review_columns(df):
    """
    Detecta automaticamente colunas relacionadas a reviews no dataset
    """
    review_columns = {
        'individual_reviews': [],  # Reviews individuais (Review 1 - Texto, etc.)
        'review_text_columns': [],  # Colunas com texto de reviews
        'review_rating_columns': [],  # Colunas com ratings de reviews
        'review_date_columns': [],  # Colunas com datas de reviews
        'review_summary_columns': [],  # Colunas com resumos de reviews
        'suspicious_review_columns': []  # Colunas com reviews suspeitas
    }
    
    # Converter nomes de colunas para minúsculas para comparação
    df_columns_lower = {col.lower(): col for col in df.columns}
    
    # Detectar reviews individuais (padrão Review X - Texto, Review X - Rating, etc.)
    for col_lower, col_original in df_columns_lower.items():
        if 'review' in col_lower and ('texto' in col_lower or 'text' in col_lower):
            review_columns['individual_reviews'].append(col_original)
            review_columns['review_text_columns'].append(col_original)
        elif 'review' in col_lower and ('rating' in col_lower or 'nota' in col_lower):
            review_columns['individual_reviews'].append(col_original)
            review_columns['review_rating_columns'].append(col_original)
        elif 'review' in col_lower and ('data' in col_lower or 'date' in col_lower):
            review_columns['individual_reviews'].append(col_original)
            review_columns['review_date_columns'].append(col_original)
        elif 'review' in col_lower and ('suspeita' in col_lower or 'suspicious' in col_lower):
            review_columns['suspicious_review_columns'].append(col_original)
        elif 'review' in col_lower and ('amostra' in col_lower or 'sample' in col_lower or 'resumo' in col_lower):
            review_columns['review_summary_columns'].append(col_original)
    
    # Remover duplicatas
    for key in review_columns:
        review_columns[key] = list(set(review_columns[key]))
    
    return review_columns

def clean_review_text(text):
    """
    Limpa texto de reviews removendo caracteres especiais e normalizando
    """
    if pd.isna(text) or text == 'N/A' or text == '':
        return ""
    
    # Converter para string
    text = str(text)
    
    # Remover quebras de linha e espaços extras
    text = ' '.join(text.split())
    
    # Remover caracteres especiais mantendo pontuação básica
    text = re.sub(r'[^\w\s\.\,\!\?\-\(\)]', ' ', text)
    
    # Remover espaços extras
    text = ' '.join(text.split())
    
    return text.strip()

def validate_review_rating(rating):
    """
    Valida e normaliza ratings de reviews (1-5 estrelas)
    """
    if pd.isna(rating) or rating == 'N/A' or rating == '':
        return None
    
    try:
        # Converter para float
        rating_float = float(str(rating).replace(',', '.'))
        
        # Verificar se está no range válido (1-5)
        if 1 <= rating_float <= 5:
            return rating_float
        else:
            return None
    except (ValueError, TypeError):
        return None

def parse_review_date(date_str):
    """
    Tenta converter string de data em formato padronizado
    """
    if pd.isna(date_str) or date_str == 'N/A' or date_str == '':
        return None
    
    # Formatos comuns de data
    date_formats = [
        '%d %b. %Y',  # 04 jun. 2024
        '%d %b %Y',   # 04 jun 2024
        '%d/%m/%Y',   # 04/06/2024
        '%Y-%m-%d',   # 2024-06-04
        '%d-%m-%Y',   # 04-06-2024
        '%m/%d/%Y',   # 06/04/2024
    ]
    
    # Mapeamento de meses em português
    month_mapping = {
        'jan': 'Jan', 'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr',
        'mai': 'May', 'jun': 'Jun', 'jul': 'Jul', 'ago': 'Aug',
        'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'
    }
    
    date_str = str(date_str).strip()
    
    # Substituir meses em português
    for pt_month, en_month in month_mapping.items():
        date_str = date_str.replace(pt_month, en_month)
    
    # Tentar converter com diferentes formatos
    for fmt in date_formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    # Se não conseguir converter, tentar parse automático
    try:
        return pd.to_datetime(date_str)
    except:
        return None

def identify_duplicate_reviews(df, text_columns):
    """
    Identifica reviews duplicadas baseado no texto
    """
    if not text_columns:
        return pd.DataFrame()
    
    duplicates_info = []
    
    for col in text_columns:
        if col in df.columns:
            # Limpar textos para comparação
            df_temp = df.copy()
            df_temp[f'{col}_clean'] = df_temp[col].apply(clean_review_text)
            
            # Encontrar duplicatas (excluindo textos vazios)
            non_empty = df_temp[df_temp[f'{col}_clean'] != '']
            duplicated_mask = non_empty.duplicated(subset=[f'{col}_clean'], keep=False)
            
            if duplicated_mask.any():
                duplicates = non_empty[duplicated_mask]
                
                for idx, row in duplicates.iterrows():
                    duplicates_info.append({
                        'Linha': idx + 1,
                        'Coluna': col,
                        'Texto': row[col][:100] + '...' if len(str(row[col])) > 100 else str(row[col]),
                        'Texto_Limpo': row[f'{col}_clean']
                    })
    
    return pd.DataFrame(duplicates_info)

def clean_reviews_dataset(df, review_columns, cleaning_options):
    """
    Aplica limpeza nas colunas de reviews baseado nas opções selecionadas
    """
    df_cleaned = df.copy()
    cleaning_report = {
        'original_rows': len(df),
        'cleaned_rows': 0,
        'removed_empty': 0,
        'removed_duplicates': 0,
        'normalized_ratings': 0,
        'parsed_dates': 0,
        'cleaned_text': 0
    }
    
    # 1. Remover reviews vazias
    if cleaning_options.get('remove_empty_reviews', False):
        text_cols = review_columns.get('review_text_columns', [])
        for col in text_cols:
            if col in df_cleaned.columns:
                before_count = len(df_cleaned)
                df_cleaned = df_cleaned[
                    (df_cleaned[col].notna()) & 
                    (df_cleaned[col] != 'N/A') & 
                    (df_cleaned[col] != '') &
                    (df_cleaned[col].astype(str).str.strip() != '')
                ]
                cleaning_report['removed_empty'] += before_count - len(df_cleaned)
    
    # 2. Normalizar ratings
    if cleaning_options.get('normalize_ratings', False):
        rating_cols = review_columns.get('review_rating_columns', [])
        for col in rating_cols:
            if col in df_cleaned.columns:
                original_values = df_cleaned[col].notna().sum()
                df_cleaned[col] = df_cleaned[col].apply(validate_review_rating)
                cleaned_values = df_cleaned[col].notna().sum()
                cleaning_report['normalized_ratings'] += original_values - cleaned_values
    
    # 3. Limpar texto das reviews
    if cleaning_options.get('clean_text', False):
        text_cols = review_columns.get('review_text_columns', [])
        for col in text_cols:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].apply(clean_review_text)
                cleaning_report['cleaned_text'] += 1
    
    # 4. Converter datas
    if cleaning_options.get('parse_dates', False):
        date_cols = review_columns.get('review_date_columns', [])
        for col in date_cols:
            if col in df_cleaned.columns:
                df_cleaned[f'{col}_parsed'] = df_cleaned[col].apply(parse_review_date)
                cleaning_report['parsed_dates'] += df_cleaned[f'{col}_parsed'].notna().sum()
    
    # 5. Remover duplicatas (sempre por último)
    if cleaning_options.get('remove_duplicates', False):
        text_cols = review_columns.get('review_text_columns', [])
        if text_cols:
            before_count = len(df_cleaned)
            # Criar coluna temporária com texto limpo para identificar duplicatas
            for col in text_cols:
                if col in df_cleaned.columns:
                    df_cleaned[f'{col}_temp_clean'] = df_cleaned[col].apply(clean_review_text)
            
            # Remover duplicatas baseado em todas as colunas de texto
            temp_cols = [f'{col}_temp_clean' for col in text_cols if col in df_cleaned.columns]
            if temp_cols:
                df_cleaned = df_cleaned.drop_duplicates(subset=temp_cols, keep='first')
                # Remover colunas temporárias
                df_cleaned = df_cleaned.drop(columns=temp_cols)
                cleaning_report['removed_duplicates'] = before_count - len(df_cleaned)
    
    cleaning_report['cleaned_rows'] = len(df_cleaned)
    
    return df_cleaned, cleaning_report

with tab_data_analysis:
    st.markdown("## 🔬 Análise Exploratória de Dados (EDA)")
    st.markdown("**Entregável 2:** EDA completa com limpeza, análise descritiva, wordclouds, n-grams, correlações e identificação de features para modelagem.")
    
    # Definir escopo do projeto
    with st.expander("🎯 Escopo do Projeto HP Challenge", expanded=False):
        st.markdown("""
        ### 📋 Definição do Escopo do Projeto
        
        **🛍️ Segmento de Produtos:**
        - Cartuchos de tinta HP (modelos 664, 662, 667, 954, GT, etc.)
        - Produtos HP originais vs. suspeitos/piratas
        - Foco em consumíveis de impressão
        
        **🌐 Abrangência de Sites:**
        - Mercado Livre (principal marketplace brasileiro)
        - Vendedores oficiais vs. não-oficiais
        - Análise de múltiplos vendedores por produto
        
        **🎯 Objetivos da EDA:**
        1. **Limpeza e Padronização** dos dados coletados
        2. **Análise Descritiva** de preços, vendedores e avaliações
        3. **Análise Textual** com wordclouds e n-grams dos títulos
        4. **Correlações** entre variáveis numéricas
        5. **Distribuição por Rótulos** (original vs. suspeito)
        6. **Identificação de Features** para modelagem ML
        
        **📊 Metodologia CRISP-DM:**
        - **Business Understanding:** Detectar produtos HP falsificados
        - **Data Understanding:** EDA dos dados coletados (esta etapa)
        - **Data Preparation:** Limpeza e feature engineering
        - **Modeling:** Algoritmos de classificação
        - **Evaluation:** Métricas de performance
        - **Deployment:** Sistema web funcional
        """)
    
    st.markdown("---")
    
    # Upload de arquivo CSV
    uploaded_file = st.file_uploader(
        "📂 Carregar Dataset CSV", 
        type=['csv'],
        help="Carregue qualquer arquivo CSV para análise automática"
    )
    
    # Ou selecionar arquivo existente
    if not uploaded_file:
        st.markdown("**Ou selecione um dataset existente:**")
        
        # Listar arquivos CSV existentes
        import glob
        csv_files = glob.glob("*.csv")
        
        if csv_files:
            selected_file = st.selectbox("📁 Arquivos CSV Disponíveis:", ["Selecione..."] + csv_files)
            if selected_file != "Selecione...":
                uploaded_file = selected_file
    
    # Verificar se foi selecionado um arquivo via botão
    if 'selected_csv' in st.session_state:
        uploaded_file = st.session_state.selected_csv
        del st.session_state.selected_csv  # Limpar após usar
    
    if uploaded_file:
        try:
            import pandas as pd
            import numpy as np
            import plotly.express as px
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            # Carregar dados com diferentes encodings
            df = None
            encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    if isinstance(uploaded_file, str):
                        # Arquivo local
                        df = pd.read_csv(uploaded_file, encoding=encoding)
                        st.success(f"✅ Dataset carregado: {uploaded_file} (encoding: {encoding})")
                    else:
                        # Arquivo enviado
                        df = pd.read_csv(uploaded_file, encoding=encoding)
                        st.success(f"✅ Dataset carregado: {uploaded_file.name} (encoding: {encoding})")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                st.error("❌ Não foi possível carregar o arquivo. Verifique o formato e encoding.")
                st.stop()
            
            # Detectar automaticamente as colunas relevantes
            column_mappings = detect_column_mappings(df)
            
            # Mostrar resumo da detecção
            column_mappings = show_column_detection_summary(column_mappings, df)
            
            # Preparar dataframe com colunas padronizadas
            df_prepared = prepare_dataframe(df, column_mappings)
            
            # Informações básicas do dataset
            st.markdown("### 📊 Informações Gerais")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Registros", len(df))
            with col2:
                st.metric("Total de Colunas", len(df.columns))
            with col3:
                # Contar registros com reviews se disponível
                if column_mappings['review_count'] and 'REVIEW_COUNT_NUMERIC' in df_prepared.columns:
                    reviews_count = len(df_prepared[df_prepared['REVIEW_COUNT_NUMERIC'].notna() & (df_prepared['REVIEW_COUNT_NUMERIC'] > 0)])
                    st.metric("Com Reviews", reviews_count)
                else:
                    st.metric("Com Reviews", "N/A")
            with col4:
                # Contar vendedores únicos se disponível
                if column_mappings['seller']:
                    unique_sellers = df_prepared[column_mappings['seller']].nunique()
                    st.metric("Vendedores Únicos", unique_sellers)
                else:
                    st.metric("Vendedores Únicos", "N/A")
            
            # Mostrar preview dos dados
            st.markdown("### 👀 Preview dos Dados")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Análises EDA em abas
            eda_tab1, eda_tab2, eda_tab3, eda_tab4, eda_tab5, eda_tab6, eda_tab7 = st.tabs([
                "🧹 Limpeza & Descritiva",
                "💰 Distribuição de Preços",
                "📝 Análise Textual (WordCloud/N-grams)", 
                "📊 Correlações & Segmentação",
                "🏷️ Distribuição por Rótulos",
                "🔧 Features para Modelagem",
                "🛠️ Limpeza de Reviews"
            ])
            
            # EDA TAB 1: Limpeza & Análise Descritiva
            with eda_tab1:
                st.markdown("#### 🧹 Limpeza da Base e Estatísticas Descritivas")
                
                # 1. Informações gerais do dataset
                st.markdown("##### 📊 Informações Gerais")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total de Registros", len(df))
                with col2:
                    st.metric("Total de Colunas", len(df.columns))
                with col3:
                    missing_data = df.isnull().sum().sum()
                    st.metric("Valores Ausentes", missing_data)
                with col4:
                    duplicate_rows = df.duplicated().sum()
                    st.metric("Linhas Duplicadas", duplicate_rows)
                
                # 2. Análise de valores ausentes
                st.markdown("##### 🔍 Análise de Valores Ausentes")
                missing_analysis = df.isnull().sum()
                missing_percent = (missing_analysis / len(df)) * 100
                
                missing_df = pd.DataFrame({
                    'Coluna': missing_analysis.index,
                    'Valores Ausentes': missing_analysis.values,
                    'Percentual (%)': missing_percent.values.round(2)
                })
                missing_df = missing_df[missing_df['Valores Ausentes'] > 0].sort_values('Valores Ausentes', ascending=False)
                
                if len(missing_df) > 0:
                    st.dataframe(missing_df, use_container_width=True)
                    
                    # Visualização de valores ausentes
                    fig_missing = px.bar(
                        missing_df, 
                        x='Coluna', 
                        y='Percentual (%)',
                        title='Percentual de Valores Ausentes por Coluna'
                    )
                    fig_missing.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_missing, use_container_width=True)
                else:
                    st.success("✅ Nenhum valor ausente encontrado no dataset!")
                
                # 3. Tipos de dados
                st.markdown("##### 🔢 Tipos de Dados")
                dtypes_df = pd.DataFrame({
                    'Coluna': df.dtypes.index,
                    'Tipo': df.dtypes.values.astype(str),
                    'Valores Únicos': [df[col].nunique() for col in df.columns],
                    'Exemplo': [str(df[col].iloc[0]) if len(df) > 0 else 'N/A' for col in df.columns]
                })
                st.dataframe(dtypes_df, use_container_width=True)
                
                # 4. Estatísticas descritivas para colunas numéricas
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                if numeric_columns:
                    st.markdown("##### 📈 Estatísticas Descritivas (Variáveis Numéricas)")
                    st.dataframe(df[numeric_columns].describe().round(2), use_container_width=True)
                
                # 5. Top valores para colunas categóricas
                categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
                if categorical_columns:
                    st.markdown("##### 📋 Top Valores (Variáveis Categóricas)")
                    
                    for col in categorical_columns[:3]:  # Mostrar apenas as 3 primeiras
                        with st.expander(f"Top valores em '{col}'", expanded=False):
                            top_values = df[col].value_counts().head(10)
                            if len(top_values) > 0:
                                fig_top = px.bar(
                                    x=top_values.values,
                                    y=top_values.index,
                                    orientation='h',
                                    title=f'Top 10 valores em {col}'
                                )
                                st.plotly_chart(fig_top, use_container_width=True)
                
                # 6. Recomendações de limpeza
                st.markdown("##### 💡 Recomendações de Limpeza")
                
                recommendations = []
                
                if duplicate_rows > 0:
                    recommendations.append(f"🔄 **Duplicatas:** {duplicate_rows} linhas duplicadas encontradas - considere remover")
                
                if missing_data > 0:
                    recommendations.append(f"❌ **Valores Ausentes:** {missing_data} valores ausentes - estratégias: imputação, remoção ou flag")
                
                # Verificar colunas com alta cardinalidade
                high_cardinality = [col for col in categorical_columns if df[col].nunique() > len(df) * 0.8]
                if high_cardinality:
                    recommendations.append(f"🔢 **Alta Cardinalidade:** Colunas {high_cardinality} podem precisar de encoding especial")
                
                # Verificar colunas numéricas que podem ser categóricas
                potential_categorical = [col for col in numeric_columns if df[col].nunique() < 10 and df[col].dtype in ['int64']]
                if potential_categorical:
                    recommendations.append(f"🏷️ **Possíveis Categóricas:** {potential_categorical} podem ser tratadas como categóricas")
                
                if not recommendations:
                    recommendations.append("✅ **Dataset Limpo:** Nenhum problema crítico de qualidade detectado")
                
                for rec in recommendations:
                    st.info(rec)
            
            # EDA TAB 2: Distribuição de Preços
            with eda_tab2:
                st.markdown("#### 💰 Distribuição de Preços")
                
                if column_mappings['price'] and 'PRICE_NUMERIC' in df_prepared.columns and df_prepared['PRICE_NUMERIC'].notna().any():
                    valid_prices = df_prepared['PRICE_NUMERIC'].dropna()
                    price_col_name = column_mappings['price']
                    
                    # Estatísticas básicas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Preço Mínimo", f"R$ {valid_prices.min():.2f}")
                    with col2:
                        st.metric("Preço Máximo", f"R$ {valid_prices.max():.2f}")
                    with col3:
                        st.metric("Preço Médio", f"R$ {valid_prices.mean():.2f}")
                    with col4:
                        st.metric("Mediana", f"R$ {valid_prices.median():.2f}")
                    
                    # Histograma de preços
                    fig_hist = px.histogram(
                        df_prepared, x='PRICE_NUMERIC', nbins=30,
                        title='Distribuição de Preços dos Produtos',
                        labels={'PRICE_NUMERIC': 'Preço (R$)', 'count': 'Quantidade'}
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
                    
                    # Box plot de preços por vendedor (top 10) se vendedor disponível
                    if column_mappings['seller']:
                        seller_col = column_mappings['seller']
                        top_sellers = df_prepared[seller_col].value_counts().head(10).index
                        df_top_sellers = df_prepared[df_prepared[seller_col].isin(top_sellers)]
                        
                        if len(df_top_sellers) > 0:
                            fig_box = px.box(
                                df_top_sellers, x=seller_col, y='PRICE_NUMERIC',
                                title='Distribuição de Preços por Vendedor (Top 10)'
                            )
                            fig_box.update_xaxes(tickangle=45)
                            st.plotly_chart(fig_box, use_container_width=True)
                    
                    # Produtos mais caros e mais baratos
                    col1, col2 = st.columns(2)
                    
                    # Preparar colunas para exibição
                    display_cols = []
                    if column_mappings['title']:
                        display_cols.append(column_mappings['title'])
                    if column_mappings['price']:
                        display_cols.append(column_mappings['price'])
                    if column_mappings['seller']:
                        display_cols.append(column_mappings['seller'])
                    
                    if display_cols:
                        with col1:
                            st.markdown("**🔝 Produtos Mais Caros**")
                            expensive = df_prepared.nlargest(5, 'PRICE_NUMERIC')[display_cols]
                            st.dataframe(expensive, use_container_width=True)
                        
                        with col2:
                            st.markdown("**💸 Produtos Mais Baratos**")
                            cheap = df_prepared.nsmallest(5, 'PRICE_NUMERIC')[display_cols]
                            st.dataframe(cheap, use_container_width=True)
                
                else:
                    st.warning("⚠️ Dados de preço não disponíveis para análise")
                    if not column_mappings['price']:
                        st.info("💡 **Dica:** Verifique se o dataset possui uma coluna de preços ou ajuste a detecção manual acima.")
            
            # EDA TAB 3: Análise Textual (WordCloud/N-grams)
            with eda_tab3:
                st.markdown("#### 📝 Análise Textual: WordClouds e N-grams")
                
                # Detectar colunas de reviews
                review_columns = detect_review_columns(df)
                text_review_cols = review_columns.get('review_text_columns', [])
                
                # Verificar se existem colunas de reviews
                if text_review_cols:
                    st.markdown("##### ☁️ WordCloud das Reviews por Produto")
                    
                    # Permitir seleção de produto
                    title_col = column_mappings.get('title')
                    if title_col and title_col in df.columns:
                        st.markdown("**Selecione um produto para análise das reviews:**")
                        
                        # Detectar coluna de ID do produto (se disponível)
                        id_col = None
                        id_patterns = ['id', 'product_id', 'produto_id', 'mlb', 'sku', 'codigo']
                        df_columns_lower = {col.lower(): col for col in df.columns}
                        
                        for pattern in id_patterns:
                            matches = [col for col_lower, col in df_columns_lower.items() if pattern in col_lower]
                            if matches:
                                id_col = matches[0]
                                break
                        
                        # Criar DataFrame com informações dos produtos únicos
                        produtos_info = []
                        for idx, row in df.iterrows():
                            titulo = str(row[title_col]) if pd.notna(row[title_col]) else "Sem título"
                            produto_id = str(row[id_col]) if id_col and pd.notna(row[id_col]) else "N/A"
                            
                            # Truncar título se muito longo
                            titulo_truncado = titulo[:80] + "..." if len(titulo) > 80 else titulo
                            
                            # Criar label combinado
                            if produto_id != "N/A":
                                label = f"#{idx} | ID: {produto_id} | {titulo_truncado}"
                            else:
                                label = f"#{idx} | {titulo_truncado}"
                            
                            produtos_info.append({
                                'index': idx,
                                'label': label,
                                'titulo': titulo,
                                'id': produto_id
                            })
                        
                        if len(produtos_info) > 0:
                            # Selectbox para escolher o produto
                            produto_selecionado_label = st.selectbox(
                                "Produto:",
                                options=[p['label'] for p in produtos_info],
                                index=0,
                                help="Selecione um produto para ver o WordCloud das suas reviews"
                            )
                            
                            # Encontrar o produto selecionado
                            produto_selecionado_info = next(p for p in produtos_info if p['label'] == produto_selecionado_label)
                            produto_selecionado_idx = produto_selecionado_info['index']
                            
                            # Filtrar dados do produto selecionado (usar índice)
                            produto_data = df.iloc[[produto_selecionado_idx]]
                            
                            if len(produto_data) > 0:
                                # Mostrar informações do produto selecionado
                                st.markdown("##### 📋 Informações do Produto Selecionado")
                                
                                col_info_prod1, col_info_prod2, col_info_prod3, col_info_prod4 = st.columns(4)
                                
                                with col_info_prod1:
                                    st.metric("Índice no Dataset", f"#{produto_selecionado_idx}")
                                with col_info_prod2:
                                    if produto_selecionado_info['id'] != "N/A":
                                        st.metric("ID do Produto", produto_selecionado_info['id'])
                                    else:
                                        st.metric("ID do Produto", "N/A")
                                with col_info_prod3:
                                    # Mostrar preço se disponível
                                    price_col = column_mappings.get('price')
                                    if price_col and price_col in produto_data.columns:
                                        preco = produto_data[price_col].iloc[0]
                                        st.metric("Preço", str(preco))
                                    else:
                                        st.metric("Preço", "N/A")
                                with col_info_prod4:
                                    # Mostrar vendedor se disponível
                                    seller_col = column_mappings.get('seller')
                                    if seller_col and seller_col in produto_data.columns:
                                        vendedor = produto_data[seller_col].iloc[0]
                                        st.metric("Vendedor", str(vendedor)[:20] + "..." if len(str(vendedor)) > 20 else str(vendedor))
                                    else:
                                        st.metric("Vendedor", "N/A")
                                
                                # Mostrar título completo
                                st.markdown(f"**Título Completo:** {produto_selecionado_info['titulo']}")
                                
                                st.markdown("---")
                                
                                # Coletar todas as reviews do produto
                                all_reviews = []
                                for col in text_review_cols:
                                    if col in produto_data.columns:
                                        reviews = produto_data[col].dropna().astype(str).tolist()
                                        all_reviews.extend([r for r in reviews if r != 'N/A' and r.strip()])
                                
                                if all_reviews:
                                    # Informações sobre as reviews
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    with col_info1:
                                        st.metric("Total de Reviews", len(all_reviews))
                                    with col_info2:
                                        avg_length = np.mean([len(r) for r in all_reviews])
                                        st.metric("Comprimento Médio", f"{avg_length:.0f} chars")
                                    with col_info3:
                                        total_words = sum(len(r.split()) for r in all_reviews)
                                        st.metric("Total de Palavras", total_words)
                                    
                                    # Gerar WordCloud das reviews
                                    wordcloud_data = generate_wordcloud_data(all_reviews, max_words=150)
                                    
                                    if wordcloud_data:
                                        # Converter WordCloud para imagem
                                        fig_wc, ax = plt.subplots(figsize=(12, 6))
                                        ax.imshow(wordcloud_data, interpolation='bilinear')
                                        ax.axis('off')
                                        # Título mais informativo
                                        titulo_wordcloud = f'WordCloud das Reviews - #{produto_selecionado_idx}'
                                        if produto_selecionado_info['id'] != "N/A":
                                            titulo_wordcloud += f' | ID: {produto_selecionado_info["id"]}'
                                        titulo_wordcloud += f' | {produto_selecionado_info["titulo"][:50]}...'
                                        
                                        ax.set_title(titulo_wordcloud, fontsize=12, fontweight='bold')
                                        st.pyplot(fig_wc)
                                        
                                        # Mostrar palavras mais frequentes
                                        word_freq = wordcloud_data.words_
                                        if word_freq:
                                            st.markdown("##### 📊 Top 20 Palavras Mais Frequentes nas Reviews")
                                            top_words = list(word_freq.items())[:20]
                                            
                                            words_df = pd.DataFrame(top_words, columns=['Palavra', 'Frequência'])
                                            
                                            fig_words = px.bar(
                                                words_df, 
                                                x='Frequência', 
                                                y='Palavra',
                                                orientation='h',
                                                title='Palavras Mais Frequentes nas Reviews do Produto Selecionado',
                                                color='Frequência',
                                                color_continuous_scale='viridis'
                                            )
                                            st.plotly_chart(fig_words, use_container_width=True)
                                            
                                            # Análise de sentimento básica das palavras
                                            st.markdown("##### 😊 Análise de Sentimento das Palavras")
                                            
                                            palavras_positivas = ['bom', 'boa', 'excelente', 'ótimo', 'ótima', 'perfeito', 'perfeita', 
                                                                'recomendo', 'satisfeito', 'satisfeita', 'qualidade', 'rápido', 'rápida']
                                            palavras_negativas = ['ruim', 'péssimo', 'péssima', 'terrível', 'horrível', 'problema', 
                                                                'defeito', 'quebrado', 'quebrada', 'não funciona', 'demorou']
                                            
                                            sentiment_counts = {'Positivas': 0, 'Negativas': 0, 'Neutras': 0}
                                            
                                            for palavra, freq in word_freq.items():
                                                if any(pos in palavra.lower() for pos in palavras_positivas):
                                                    sentiment_counts['Positivas'] += freq
                                                elif any(neg in palavra.lower() for neg in palavras_negativas):
                                                    sentiment_counts['Negativas'] += freq
                                                else:
                                                    sentiment_counts['Neutras'] += freq
                                            
                                            # Gráfico de pizza do sentimento
                                            fig_sentiment = px.pie(
                                                values=list(sentiment_counts.values()),
                                                names=list(sentiment_counts.keys()),
                                                title='Distribuição de Sentimento nas Palavras das Reviews',
                                                color_discrete_map={
                                                    'Positivas': '#2E8B57',
                                                    'Negativas': '#DC143C', 
                                                    'Neutras': '#708090'
                                                }
                                            )
                                            st.plotly_chart(fig_sentiment, use_container_width=True)
                                        
                                    else:
                                        st.warning("⚠️ Não foi possível gerar WordCloud - reviews insuficientes")
                                else:
                                    st.info("📝 Este produto não possui reviews de texto disponíveis")
                            else:
                                st.error("❌ Produto não encontrado no dataset")
                        else:
                            st.warning("⚠️ Nenhum produto encontrado no dataset")
                    else:
                        st.warning("⚠️ Coluna de título não detectada - não é possível selecionar produtos")
                
                else:
                    st.warning("⚠️ Nenhuma coluna de review de texto detectada no dataset")
                    st.info("""
                    💡 **Para usar esta funcionalidade, o dataset precisa ter colunas de reviews como:**
                    - Review 1 - Texto
                    - Review 2 - Texto  
                    - Review Text
                    - Comentários
                    - Avaliações
                    """)
            
            # EDA TAB 4: Correlações & Segmentação
            with eda_tab4:
                st.markdown("#### 📊 Correlações entre Variáveis e Segmentação")
                
                # 1. Análise de Correlação
                numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
                
                if len(numeric_columns) >= 2:
                    st.markdown("##### 🔗 Matriz de Correlação")
                    
                    # Calcular correlações
                    correlation_matrix = perform_correlation_analysis(df, numeric_columns)
                    
                    if correlation_matrix is not None:
                        # Heatmap de correlação
                        fig_corr = px.imshow(
                            correlation_matrix,
                            text_auto=True,
                            aspect="auto",
                            title="Matriz de Correlação entre Variáveis Numéricas",
                            color_continuous_scale='RdBu_r'
                        )
                        st.plotly_chart(fig_corr, use_container_width=True)
                        
                        # Identificar correlações mais fortes
                        strong_correlations = []
                        for i in range(len(correlation_matrix.columns)):
                            for j in range(i+1, len(correlation_matrix.columns)):
                                corr_value = correlation_matrix.iloc[i, j]
                                if abs(corr_value) > 0.5:  # Correlação moderada a forte
                                    strong_correlations.append({
                                        'Variável 1': correlation_matrix.columns[i],
                                        'Variável 2': correlation_matrix.columns[j],
                                        'Correlação': round(corr_value, 3),
                                        'Interpretação': 'Forte' if abs(corr_value) > 0.7 else 'Moderada'
                                    })
                        
                        if strong_correlations:
                            st.markdown("##### 🔍 Correlações Significativas (|r| > 0.5)")
                            correlations_df = pd.DataFrame(strong_correlations)
                            st.dataframe(correlations_df, use_container_width=True)
                        else:
                            st.info("ℹ️ Nenhuma correlação forte encontrada entre as variáveis numéricas")
                
                # 2. Segmentação de Preços vs Ratings (se disponível)
                price_col = column_mappings.get('price')
                rating_col = column_mappings.get('rating')
                
                if price_col and rating_col and 'PRICE_NUMERIC' in df_prepared.columns and 'RATING_NUMERIC' in df_prepared.columns:
                    st.markdown("##### 🎯 Segmentação: Preço vs Rating")
                    
                    # Criar segmentos combinados
                    segmentation_result = create_price_rating_segments(df_prepared, 'PRICE_NUMERIC', 'RATING_NUMERIC')
                    
                    if segmentation_result:
                        contingency_table, df_segments = segmentation_result
                        
                        # Mostrar tabela de contingência
                        st.markdown("**Tabela de Contingência: Segmentos de Preço vs Rating**")
                        st.dataframe(contingency_table, use_container_width=True)
                        
                        # Heatmap da segmentação
                        fig_segments = px.imshow(
                            contingency_table,
                            text_auto=True,
                            aspect="auto",
                            title="Segmentação: Preço vs Rating",
                            labels=dict(x="Segmento de Rating", y="Segmento de Preço"),
                            color_continuous_scale='Blues'
                        )
                        st.plotly_chart(fig_segments, use_container_width=True)
                        
                        # Scatter plot com segmentos
                        fig_scatter_segments = px.scatter(
                            df_segments,
                            x='PRICE_NUMERIC',
                            y='RATING_NUMERIC',
                            color='price_segment',
                            symbol='rating_segment',
                            title='Distribuição de Produtos por Segmentos de Preço e Rating',
                            labels={'PRICE_NUMERIC': 'Preço (R$)', 'RATING_NUMERIC': 'Rating Médio'}
                        )
                        st.plotly_chart(fig_scatter_segments, use_container_width=True)
                        
                        # Análise dos segmentos
                        st.markdown("##### 📈 Análise dos Segmentos")
                        
                        segment_analysis = df_segments.groupby(['price_segment', 'rating_segment']).size().reset_index(name='count')
                        segment_analysis['percentage'] = (segment_analysis['count'] / len(df_segments) * 100).round(2)
                        
                        # Identificar segmentos interessantes
                        high_price_high_rating = segment_analysis[
                            (segment_analysis['price_segment'] == 'Alto') & 
                            (segment_analysis['rating_segment'] == 'Alto')
                        ]
                        
                        low_price_high_rating = segment_analysis[
                            (segment_analysis['price_segment'] == 'Baixo') & 
                            (segment_analysis['rating_segment'] == 'Alto')
                        ]
                        
                        insights = []
                        
                        if len(high_price_high_rating) > 0:
                            count = high_price_high_rating['count'].iloc[0]
                            pct = high_price_high_rating['percentage'].iloc[0]
                            insights.append(f"🟢 **Premium Products:** {count} produtos ({pct}%) com preço alto e rating alto")
                        
                        if len(low_price_high_rating) > 0:
                            count = low_price_high_rating['count'].iloc[0]
                            pct = low_price_high_rating['percentage'].iloc[0]
                            insights.append(f"🟡 **Value Products:** {count} produtos ({pct}%) com preço baixo e rating alto - possível oportunidade")
                        
                        for insight in insights:
                            st.info(insight)
                
                # 3. Análise de Outliers
                st.markdown("##### 🎯 Detecção de Outliers")
                
                outlier_results = {}
                for col in numeric_columns:
                    outliers = detect_outliers_iqr(df, col)
                    if len(outliers) > 0:
                        outlier_results[col] = len(outliers)
                
                if outlier_results:
                    col_out1, col_out2 = st.columns(2)
                    
                    with col_out1:
                        st.markdown("**Contagem de Outliers por Variável:**")
                        outliers_df = pd.DataFrame(list(outlier_results.items()), 
                                                 columns=['Variável', 'Outliers'])
                        st.dataframe(outliers_df, use_container_width=True)
                    
                    with col_out2:
                        # Gráfico de outliers
                        fig_outliers = px.bar(
                            outliers_df,
                            x='Variável',
                            y='Outliers',
                            title='Quantidade de Outliers por Variável'
                        )
                        st.plotly_chart(fig_outliers, use_container_width=True)
                    
                    # Box plots para visualizar outliers
                    if price_col and 'PRICE_NUMERIC' in df_prepared.columns:
                        fig_box_price = px.box(
                            df_prepared,
                            y='PRICE_NUMERIC',
                            title='Box Plot - Distribuição de Preços (com outliers)'
                        )
                        st.plotly_chart(fig_box_price, use_container_width=True)
                else:
                    st.success("✅ Nenhum outlier significativo detectado nas variáveis numéricas")
                
                # 4. Análise de Vendedores (se disponível)
                seller_col = column_mappings.get('seller')
                if seller_col and seller_col in df.columns:
                    st.markdown("##### 🏪 Segmentação por Vendedores")
                    
                    # Top vendedores
                    top_sellers = df[seller_col].value_counts().head(10)
                    
                    if len(top_sellers) > 0:
                        # Análise de concentração de vendedores
                        total_sellers = df[seller_col].nunique()
                        top_5_concentration = (top_sellers.head(5).sum() / len(df)) * 100
                        
                        col_seller1, col_seller2, col_seller3 = st.columns(3)
                        
                        with col_seller1:
                            st.metric("Total de Vendedores", total_sellers)
                        with col_seller2:
                            st.metric("Concentração Top 5", f"{top_5_concentration:.1f}%")
                        with col_seller3:
                            hhi = sum((count/len(df))**2 for count in top_sellers.head(10))
                            st.metric("Índice HHI (Top 10)", f"{hhi:.3f}")
                        
                        # Gráfico de concentração
                        fig_sellers_conc = px.bar(
                            x=top_sellers.values,
                            y=top_sellers.index,
                            orientation='h',
                            title='Top 10 Vendedores por Volume de Produtos'
                        )
                        st.plotly_chart(fig_sellers_conc, use_container_width=True)
                        
                        # Análise de preços por vendedor (se disponível)
                        if price_col and 'PRICE_NUMERIC' in df_prepared.columns:
                            seller_price_analysis = df_prepared.groupby(seller_col)['PRICE_NUMERIC'].agg(['mean', 'std', 'count']).round(2)
                            seller_price_analysis = seller_price_analysis[seller_price_analysis['count'] >= 3].sort_values('mean')
                            
                            if len(seller_price_analysis) > 0:
                                st.markdown("**Análise de Preços por Vendedor (min. 3 produtos):**")
                                seller_price_analysis.columns = ['Preço Médio', 'Desvio Padrão', 'Qtd Produtos']
                                st.dataframe(seller_price_analysis.head(10), use_container_width=True)
                
                else:
                    st.warning("⚠️ Análise de correlação limitada - poucas variáveis numéricas disponíveis")
                    st.info("💡 Para análise mais rica, inclua colunas numéricas como preço, rating, contagem de reviews, etc.")
                
                if column_mappings['rating'] and 'RATING_NUMERIC' in df_prepared.columns and df_prepared['RATING_NUMERIC'].notna().any():
                    valid_ratings = df_prepared['RATING_NUMERIC'].dropna()
                    rating_col = column_mappings['rating']
                    
                    # Estatísticas básicas
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Avaliação Média", f"{valid_ratings.mean():.2f}")
                    with col2:
                        st.metric("Mediana", f"{valid_ratings.median():.2f}")
                    with col3:
                        st.metric("Desvio Padrão", f"{valid_ratings.std():.2f}")
                    with col4:
                        produtos_bem_avaliados = len(valid_ratings[valid_ratings >= 4.5])
                        st.metric("≥ 4.5 Estrelas", produtos_bem_avaliados)
                    
                    # Distribuição de avaliações
                    fig_ratings = px.histogram(
                        df_prepared, x='RATING_NUMERIC', nbins=20,
                        title='Distribuição de Avaliações Médias',
                        labels={'RATING_NUMERIC': 'Avaliação Média', 'count': 'Quantidade'}
                    )
                    st.plotly_chart(fig_ratings, use_container_width=True)
                    
                    # Scatter plot: Preço vs Avaliação (se preço disponível)
                    if column_mappings['price'] and 'PRICE_NUMERIC' in df_prepared.columns:
                        hover_data = []
                        if column_mappings['title']:
                            hover_data.append(column_mappings['title'])
                        if column_mappings['seller']:
                            hover_data.append(column_mappings['seller'])
                        
                        fig_scatter = px.scatter(
                            df_prepared, x='PRICE_NUMERIC', y='RATING_NUMERIC',
                            hover_data=hover_data if hover_data else None,
                            title='Relação entre Preço e Avaliação',
                            labels={'PRICE_NUMERIC': 'Preço (R$)', 'RATING_NUMERIC': 'Avaliação Média'}
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Análise de reviews por vendedor (se disponível)
                    if column_mappings['seller'] and column_mappings['review_count'] and 'REVIEW_COUNT_NUMERIC' in df_prepared.columns:
                        seller_col = column_mappings['seller']
                        review_count_col = column_mappings['review_count']
                        
                        # Vendedores com mais reviews
                        seller_reviews = df_prepared.groupby(seller_col).agg({
                            'REVIEW_COUNT_NUMERIC': 'sum',
                            'RATING_NUMERIC': 'mean'
                        }).sort_values('REVIEW_COUNT_NUMERIC', ascending=False).head(10)
                        
                        fig_seller_reviews = px.bar(
                            x=seller_reviews.index,
                            y=seller_reviews['REVIEW_COUNT_NUMERIC'],
                            title='Vendedores com Mais Reviews Totais'
                        )
                        fig_seller_reviews.update_xaxes(tickangle=45)
                        st.plotly_chart(fig_seller_reviews, use_container_width=True)
                        
                        # Produtos mais bem avaliados
                        st.markdown("**🌟 Produtos Mais Bem Avaliados**")
                        display_cols_reviews = []
                        if column_mappings['title']:
                            display_cols_reviews.append(column_mappings['title'])
                        if column_mappings['rating']:
                            display_cols_reviews.append(column_mappings['rating'])
                        if column_mappings['review_count']:
                            display_cols_reviews.append(column_mappings['review_count'])
                        if column_mappings['seller']:
                            display_cols_reviews.append(column_mappings['seller'])
                        
                        if display_cols_reviews:
                            best_rated = df_prepared.nlargest(10, 'RATING_NUMERIC')[display_cols_reviews]
                            st.dataframe(best_rated, use_container_width=True)
                
                else:
                    st.warning("⚠️ Dados de avaliação não disponíveis para análise")
                    if not column_mappings['rating']:
                        st.info("💡 **Dica:** Verifique se o dataset possui uma coluna de avaliações ou ajuste a detecção manual acima.")
            
            # EDA TAB 5: Distribuição por Rótulos
            with eda_tab5:
                st.markdown("#### 🏷️ Distribuição por Rótulos e Análise de Classes")
                
                # Verificar se existe análise de rotulagem no session state
                if hasattr(st.session_state, 'labeled_dataset') and st.session_state.labeled_dataset:
                    dataset_rotulado = st.session_state.labeled_dataset
                    
                    st.markdown("##### 📊 Distribuição dos Rótulos Heurísticos")
                    
                    # Extrair rótulos
                    labels = [item['rotulo_heuristico'] for item in dataset_rotulado]
                    label_counts = pd.Series(labels).value_counts()
                    
                    # Métricas gerais
                    col_label1, col_label2, col_label3, col_label4 = st.columns(4)
                    
                    with col_label1:
                        st.metric("Total de Produtos", len(labels))
                    with col_label2:
                        original_count = label_counts.get('original', 0)
                        st.metric("Produtos Originais", original_count)
                    with col_label3:
                        suspeito_count = label_counts.get('suspeito', 0)
                        st.metric("Produtos Suspeitos", suspeito_count)
                    with col_label4:
                        if len(labels) > 0:
                            suspeito_rate = (suspeito_count / len(labels)) * 100
                            st.metric("Taxa de Suspeição", f"{suspeito_rate:.1f}%")
                    
                    # Gráfico de distribuição
                    fig_labels = px.pie(
                        values=label_counts.values,
                        names=label_counts.index,
                        title='Distribuição de Produtos por Rótulo',
                        color_discrete_map={'original': '#2E8B57', 'suspeito': '#DC143C'}
                    )
                    st.plotly_chart(fig_labels, use_container_width=True)
                    
                    # Análise detalhada por rótulo
                    st.markdown("##### 🔍 Análise Detalhada por Rótulo")
                    
                    # Preparar dados para análise
                    analysis_data = []
                    for item in dataset_rotulado:
                        produto = item['produto_original']
                        detalhes = item['detalhes_rotulagem']
                        
                        analysis_data.append({
                            'rotulo': item['rotulo_heuristico'],
                            'score_total': detalhes['score_total'],
                            'score_titulo': detalhes['score_titulo'],
                            'score_preco': detalhes['score_preco'],
                            'vendedor_oficial': detalhes['vendedor_oficial'],
                            'preco': extrair_preco_numerico(produto.get('PREÇO', 'N/A')),
                            'vendedor': produto.get('VENDEDOR', 'N/A'),
                            'titulo': produto.get('TITULO PRODUTO', 'N/A')
                        })
                    
                    analysis_df = pd.DataFrame(analysis_data)
                    
                    # Estatísticas por rótulo
                    if len(analysis_df) > 0:
                        col_stats1, col_stats2 = st.columns(2)
                        
                        with col_stats1:
                            st.markdown("**Estatísticas de Score por Rótulo:**")
                            score_stats = analysis_df.groupby('rotulo')['score_total'].agg(['mean', 'std', 'min', 'max']).round(2)
                            score_stats.columns = ['Média', 'Desvio Padrão', 'Mínimo', 'Máximo']
                            st.dataframe(score_stats, use_container_width=True)
                        
                        with col_stats2:
                            st.markdown("**Distribuição de Vendedores Oficiais:**")
                            vendor_stats = analysis_df.groupby('rotulo')['vendedor_oficial'].agg(['sum', 'count'])
                            vendor_stats['percentual'] = (vendor_stats['sum'] / vendor_stats['count'] * 100).round(2)
                            vendor_stats.columns = ['Oficiais', 'Total', 'Percentual (%)']
                            st.dataframe(vendor_stats, use_container_width=True)
                        
                        # Box plot dos scores por rótulo
                        fig_scores = px.box(
                            analysis_df,
                            x='rotulo',
                            y='score_total',
                            title='Distribuição dos Scores Totais por Rótulo',
                            color='rotulo',
                            color_discrete_map={'original': '#2E8B57', 'suspeito': '#DC143C'}
                        )
                        st.plotly_chart(fig_scores, use_container_width=True)
                        
                        # Análise de preços por rótulo (se disponível)
                        prices_available = analysis_df['preco'].notna().sum() > 0
                        if prices_available:
                            fig_prices = px.box(
                                analysis_df[analysis_df['preco'].notna()],
                                x='rotulo',
                                y='preco',
                                title='Distribuição de Preços por Rótulo',
                                color='rotulo',
                                color_discrete_map={'original': '#2E8B57', 'suspeito': '#DC143C'}
                            )
                            st.plotly_chart(fig_prices, use_container_width=True)
                            
                            # Estatísticas de preço
                            price_stats = analysis_df[analysis_df['preco'].notna()].groupby('rotulo')['preco'].agg(['mean', 'median', 'std']).round(2)
                            price_stats.columns = ['Preço Médio', 'Preço Mediano', 'Desvio Padrão']
                            st.markdown("**Estatísticas de Preço por Rótulo:**")
                            st.dataframe(price_stats, use_container_width=True)
                        
                        # Top vendedores por rótulo
                        st.markdown("##### 🏪 Top Vendedores por Rótulo")
                        
                        for rotulo in ['original', 'suspeito']:
                            if rotulo in analysis_df['rotulo'].values:
                                with st.expander(f"Top vendedores - {rotulo.title()}", expanded=False):
                                    rotulo_data = analysis_df[analysis_df['rotulo'] == rotulo]
                                    top_vendors = rotulo_data['vendedor'].value_counts().head(10)
                                    
                                    if len(top_vendors) > 0:
                                        fig_vendors = px.bar(
                                            x=top_vendors.values,
                                            y=top_vendors.index,
                                            orientation='h',
                                            title=f'Top 10 Vendedores - Produtos {rotulo.title()}'
                                        )
                                        st.plotly_chart(fig_vendors, use_container_width=True)
                        
                        # Produtos mais suspeitos
                        if 'suspeito' in analysis_df['rotulo'].values:
                            st.markdown("##### 🚨 Produtos Mais Suspeitos")
                            suspeitos = analysis_df[analysis_df['rotulo'] == 'suspeito'].nlargest(5, 'score_total')
                            
                            display_cols = ['titulo', 'score_total', 'vendedor']
                            if prices_available:
                                display_cols.append('preco')
                            
                            st.dataframe(suspeitos[display_cols], use_container_width=True)
                
                else:
                    st.info("🔍 **Execute a rotulagem heurística** na aba 'Dataset Generator' para visualizar a distribuição por rótulos.")
                    
                    # Oferecer análise básica se dados estiverem disponíveis
                    if 'current_products' in st.session_state and st.session_state.current_products:
                        st.markdown("##### 💡 Análise Básica dos Dados Atuais")
                        
                        produtos = st.session_state.current_products
                        
                        # Análise de vendedores
                        vendedores = [p.get('VENDEDOR', 'N/A') for p in produtos]
                        vendedor_counts = pd.Series(vendedores).value_counts().head(10)
                        
                        fig_basic_vendors = px.bar(
                            x=vendedor_counts.values,
                            y=vendedor_counts.index,
                            orientation='h',
                            title='Top 10 Vendedores nos Dados Atuais'
                        )
                        st.plotly_chart(fig_basic_vendors, use_container_width=True)
                        
                        # Análise de preços básica
                        precos = [extrair_preco_numerico(p.get('PREÇO', 'N/A')) for p in produtos]
                        precos_validos = [p for p in precos if p is not None]
                        
                        if precos_validos:
                            col_basic1, col_basic2, col_basic3 = st.columns(3)
                            
                            with col_basic1:
                                st.metric("Preço Médio", f"R$ {np.mean(precos_validos):.2f}")
                            with col_basic2:
                                st.metric("Preço Mínimo", f"R$ {min(precos_validos):.2f}")
                            with col_basic3:
                                st.metric("Preço Máximo", f"R$ {max(precos_validos):.2f}")
            
            # EDA TAB 6: Features para Modelagem
            with eda_tab6:
                st.markdown("#### 🔧 Identificação de Features para Modelagem ML")
                
                st.markdown("##### 🎯 Features Identificadas para Classificação")
                
                # 1. Features Numéricas
                st.markdown("##### 📊 Features Numéricas")
                
                numeric_features = []
                feature_descriptions = {}
                
                if column_mappings.get('price') and 'PRICE_NUMERIC' in df_prepared.columns:
                    numeric_features.append('PRICE_NUMERIC')
                    feature_descriptions['PRICE_NUMERIC'] = "Preço do produto (normalizado)"
                
                if column_mappings.get('rating') and 'RATING_NUMERIC' in df_prepared.columns:
                    numeric_features.append('RATING_NUMERIC')
                    feature_descriptions['RATING_NUMERIC'] = "Avaliação média do produto"
                
                if column_mappings.get('review_count') and 'REVIEW_COUNT_NUMERIC' in df_prepared.columns:
                    numeric_features.append('REVIEW_COUNT_NUMERIC')
                    feature_descriptions['REVIEW_COUNT_NUMERIC'] = "Quantidade total de reviews"
                
                if numeric_features:
                    numeric_df = pd.DataFrame({
                        'Feature': numeric_features,
                        'Descrição': [feature_descriptions[f] for f in numeric_features],
                        'Tipo': ['Numérica'] * len(numeric_features),
                        'Importância': ['Alta', 'Média', 'Média'][:len(numeric_features)]
                    })
                    st.dataframe(numeric_df, use_container_width=True)
                    
                    # Estatísticas das features numéricas
                    if len(numeric_features) > 0:
                        st.markdown("**Estatísticas das Features Numéricas:**")
                        st.dataframe(df_prepared[numeric_features].describe().round(3), use_container_width=True)
                else:
                    st.warning("⚠️ Nenhuma feature numérica detectada")
                
                # 2. Features Categóricas
                st.markdown("##### 📋 Features Categóricas")
                
                categorical_features = []
                
                if column_mappings.get('seller'):
                    categorical_features.append(column_mappings['seller'])
                    feature_descriptions[column_mappings['seller']] = "Vendedor do produto (encoding necessário)"
                
                if column_mappings.get('brand'):
                    categorical_features.append(column_mappings['brand'])
                    feature_descriptions[column_mappings['brand']] = "Marca do produto"
                
                if categorical_features:
                    categorical_df = pd.DataFrame({
                        'Feature': categorical_features,
                        'Descrição': [feature_descriptions[f] for f in categorical_features],
                        'Tipo': ['Categórica'] * len(categorical_features),
                        'Cardinalidade': [df[f].nunique() for f in categorical_features],
                        'Encoding Sugerido': ['Label/One-Hot', 'One-Hot'][:len(categorical_features)]
                    })
                    st.dataframe(categorical_df, use_container_width=True)
                else:
                    st.info("ℹ️ Nenhuma feature categórica detectada")
                
                # 3. Features Textuais (Engenharia de Features)
                st.markdown("##### 📝 Features Textuais (Feature Engineering)")
                
                title_col = column_mappings.get('title')
                if title_col:
                    st.markdown("**Features derivadas do título do produto:**")
                    
                    # Calcular features textuais de exemplo
                    sample_titles = df[title_col].head(100).tolist()  # Amostra para demonstração
                    
                    text_features = {
                        'titulo_length': 'Comprimento do título (caracteres)',
                        'titulo_word_count': 'Número de palavras no título',
                        'has_suspicious_words': 'Presença de palavras suspeitas (flag binária)',
                        'has_model_number': 'Presença de número de modelo HP (flag binária)',
                        'has_color_keywords': 'Presença de palavras relacionadas a cor',
                        'has_promotional_words': 'Presença de palavras promocionais',
                        'title_uppercase_ratio': 'Proporção de caracteres maiúsculos',
                        'title_special_chars': 'Quantidade de caracteres especiais'
                    }
                    
                    text_features_df = pd.DataFrame({
                        'Feature': list(text_features.keys()),
                        'Descrição': list(text_features.values()),
                        'Tipo': ['Numérica', 'Numérica', 'Binária', 'Binária', 'Binária', 'Binária', 'Numérica', 'Numérica'],
                        'Importância': ['Baixa', 'Baixa', 'Alta', 'Alta', 'Média', 'Alta', 'Média', 'Baixa']
                    })
                    st.dataframe(text_features_df, use_container_width=True)
                    
                    # Demonstração de algumas features textuais
                    if len(sample_titles) > 0:
                        st.markdown("**Exemplo de Features Textuais (amostra):**")
                        
                        # Calcular features de exemplo
                        sample_features = []
                        for title in sample_titles[:5]:  # Apenas 5 exemplos
                            if pd.notna(title):
                                title_str = str(title)
                                
                                # Features calculadas
                                length = len(title_str)
                                word_count = len(title_str.split())
                                has_suspicious = any(word in title_str.lower() for word in ['barato', 'promocao', 'oferta', 'liquidacao'])
                                has_hp_model = any(model in title_str.upper() for model in ['664', '662', '667', '954', 'GT'])
                                uppercase_ratio = sum(1 for c in title_str if c.isupper()) / len(title_str) if len(title_str) > 0 else 0
                                
                                sample_features.append({
                                    'Título (truncado)': title_str[:50] + '...' if len(title_str) > 50 else title_str,
                                    'Comprimento': length,
                                    'Palavras': word_count,
                                    'Suspeito': has_suspicious,
                                    'Modelo HP': has_hp_model,
                                    'Maiúsculas (%)': f"{uppercase_ratio:.2%}"
                                })
                        
                        if sample_features:
                            sample_df = pd.DataFrame(sample_features)
                            st.dataframe(sample_df, use_container_width=True)
                
                # 4. Features de Engenharia Avançada
                st.markdown("##### ⚙️ Features de Engenharia Avançada")
                
                advanced_features = {
                    'price_zscore': 'Z-score do preço (detecção de outliers)',
                    'price_percentile': 'Percentil do preço no dataset',
                    'vendor_reputation_score': 'Score de reputação do vendedor',
                    'price_vs_market_avg': 'Razão preço/média do mercado por categoria',
                    'review_density': 'Densidade de reviews (reviews/tempo no mercado)',
                    'title_similarity_cluster': 'Cluster de similaridade de títulos',
                    'price_rating_interaction': 'Interação preço × rating',
                    'vendor_price_deviation': 'Desvio do preço em relação à média do vendedor'
                }
                
                advanced_df = pd.DataFrame({
                    'Feature': list(advanced_features.keys()),
                    'Descrição': list(advanced_features.values()),
                    'Complexidade': ['Média', 'Baixa', 'Alta', 'Alta', 'Média', 'Alta', 'Baixa', 'Média'],
                    'Potencial Discriminativo': ['Alto', 'Médio', 'Alto', 'Alto', 'Médio', 'Médio', 'Médio', 'Alto']
                })
                st.dataframe(advanced_df, use_container_width=True)
                
                # 5. Resumo para Modelagem
                st.markdown("##### 💡 Resumo para Modelagem ML")
                
                col_model1, col_model2 = st.columns(2)
                
                with col_model1:
                    st.markdown("""
                    **🔧 Pré-processamento:**
                    - Normalizar features numéricas
                    - Encoding de variáveis categóricas  
                    - Tratar valores ausentes
                    - Feature engineering textual
                    """)
                
                with col_model2:
                    st.markdown("""
                    **📈 Validação:**
                    - Validação cruzada estratificada
                    - Métricas: Precision, Recall, F1-Score
                    - Análise de importância das features
                    - Teste em holdout set
                    """)
                
                # 6. Algoritmos Recomendados
                st.markdown("##### 🤖 Algoritmos Recomendados")
                
                algorithms_info = {
                    "Random Forest": "✅ Bom para features mistas, interpretável, robusto",
                    "XGBoost": "✅ Alto desempenho, handling automático de missing values",
                    "Logistic Regression": "✅ Baseline rápido, interpretável, simples",
                    "SVM": "✅ Eficaz para features textuais e high-dimensional"
                }
                
                for algo, desc in algorithms_info.items():
                    st.write(f"**{algo}:** {desc}")
                
                st.info("💡 **Recomendação:** Começar com Random Forest como baseline e comparar com XGBoost para otimização.")
            
            # EDA TAB 7: Limpeza de Reviews
            with eda_tab7:
                st.markdown("#### 🛠️ Limpeza e Processamento de Reviews")
                
                # Detectar colunas de reviews
                review_columns = detect_review_columns(df)
                
                # Verificar se há colunas de reviews
                total_review_cols = sum(len(cols) for cols in review_columns.values())
                
                if total_review_cols == 0:
                    st.warning("⚠️ Nenhuma coluna de review detectada no dataset.")
                    st.info("""
                    💡 **Dica:** O sistema procura por colunas com padrões como:
                    - Review X - Texto
                    - Review X - Rating  
                    - Review X - Data
                    - Reviews Suspeitas
                    - Amostra Reviews
                    """)
                else:
                    # Mostrar resumo das colunas detectadas
                    st.markdown("##### 🔍 Colunas de Reviews Detectadas")
                    
                    detection_summary = []
                    for category, columns in review_columns.items():
                        if columns:
                            category_name = {
                                'review_text_columns': 'Texto das Reviews',
                                'review_rating_columns': 'Ratings das Reviews', 
                                'review_date_columns': 'Datas das Reviews',
                                'review_summary_columns': 'Resumos de Reviews',
                                'suspicious_review_columns': 'Reviews Suspeitas',
                                'individual_reviews': 'Reviews Individuais'
                            }.get(category, category)
                            
                            detection_summary.append({
                                'Categoria': category_name,
                                'Quantidade': len(columns),
                                'Colunas': ', '.join(columns[:3]) + ('...' if len(columns) > 3 else '')
                            })
                    
                    if detection_summary:
                        detection_df = pd.DataFrame(detection_summary)
                        st.dataframe(detection_df, use_container_width=True)
                    
                    # Análise inicial das reviews
                    st.markdown("##### 📊 Análise Inicial das Reviews")
                    
                    text_cols = review_columns.get('review_text_columns', [])
                    rating_cols = review_columns.get('review_rating_columns', [])
                    
                    if text_cols:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        # Estatísticas das reviews de texto
                        total_text_reviews = 0
                        empty_text_reviews = 0
                        
                        for col in text_cols[:5]:  # Analisar até 5 colunas
                            if col in df.columns:
                                col_data = df[col].astype(str)
                                total_text_reviews += len(col_data)
                                empty_text_reviews += len(col_data[
                                    (col_data.isna()) | 
                                    (col_data == 'N/A') | 
                                    (col_data == '') |
                                    (col_data.str.strip() == '')
                                ])
                        
                        with col1:
                            st.metric("Total Reviews Texto", total_text_reviews)
                        with col2:
                            st.metric("Reviews Vazias", empty_text_reviews)
                        with col3:
                            valid_reviews = total_text_reviews - empty_text_reviews
                            st.metric("Reviews Válidas", valid_reviews)
                        with col4:
                            if total_text_reviews > 0:
                                completeness = (valid_reviews / total_text_reviews) * 100
                                st.metric("Completude (%)", f"{completeness:.1f}%")
                            else:
                                st.metric("Completude (%)", "N/A")
                    
                    # Identificar duplicatas
                    if text_cols:
                        st.markdown("##### 🔄 Análise de Duplicatas")
                        
                        duplicates_df = identify_duplicate_reviews(df, text_cols[:3])  # Analisar até 3 colunas
                        
                        if len(duplicates_df) > 0:
                            st.warning(f"⚠️ {len(duplicates_df)} reviews duplicadas encontradas!")
                            
                            with st.expander("👀 Ver Reviews Duplicadas", expanded=False):
                                st.dataframe(duplicates_df, use_container_width=True)
                        else:
                            st.success("✅ Nenhuma review duplicada encontrada!")
                    
                    # Análise de ratings
                    if rating_cols:
                        st.markdown("##### ⭐ Análise de Ratings")
                        
                        valid_ratings = 0
                        invalid_ratings = 0
                        
                        for col in rating_cols[:5]:  # Analisar até 5 colunas
                            if col in df.columns:
                                col_data = df[col]
                                for rating in col_data:
                                    if validate_review_rating(rating) is not None:
                                        valid_ratings += 1
                                    else:
                                        invalid_ratings += 1
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Ratings Válidos", valid_ratings)
                        with col2:
                            st.metric("Ratings Inválidos", invalid_ratings)
                        with col3:
                            total_ratings = valid_ratings + invalid_ratings
                            if total_ratings > 0:
                                validity_pct = (valid_ratings / total_ratings) * 100
                                st.metric("Validade (%)", f"{validity_pct:.1f}%")
                            else:
                                st.metric("Validade (%)", "N/A")
                    
                    # Opções de limpeza
                    st.markdown("##### 🧹 Opções de Limpeza")
                    
                    col_clean1, col_clean2 = st.columns(2)
                    
                    with col_clean1:
                        st.markdown("**🗑️ Remoção:**")
                        remove_empty = st.checkbox("Remover reviews vazias", value=True, help="Remove reviews com texto vazio ou N/A")
                        remove_duplicates = st.checkbox("Remover reviews duplicadas", value=True, help="Remove reviews com texto idêntico")
                        
                        st.markdown("**🔧 Normalização:**")
                        clean_text = st.checkbox("Limpar texto das reviews", value=True, help="Remove caracteres especiais e normaliza texto")
                        normalize_ratings = st.checkbox("Normalizar ratings (1-5)", value=True, help="Valida e converte ratings para escala 1-5")
                    
                    with col_clean2:
                        st.markdown("**📅 Processamento de Datas:**")
                        parse_dates = st.checkbox("Converter datas", value=True, help="Converte strings de data para formato datetime")
                        
                        st.markdown("**🎯 Filtros Avançados:**")
                        min_rating = st.selectbox("Rating mínimo:", [None, 1, 2, 3, 4, 5], index=0, help="Manter apenas reviews com rating >= valor")
                        max_rating = st.selectbox("Rating máximo:", [None, 1, 2, 3, 4, 5], index=0, help="Manter apenas reviews com rating <= valor")
                        
                        # Filtro por data
                        date_filter = st.checkbox("Filtrar por período", help="Manter apenas reviews de um período específico")
                        if date_filter:
                            col_date1, col_date2 = st.columns(2)
                            with col_date1:
                                start_date = st.date_input("Data inicial:")
                            with col_date2:
                                end_date = st.date_input("Data final:")
                    
                    # Botão para aplicar limpeza
                    if st.button("🚀 Aplicar Limpeza", type="primary", use_container_width=True):
                        with st.spinner("🔄 Aplicando limpeza nas reviews..."):
                            
                            cleaning_options = {
                                'remove_empty_reviews': remove_empty,
                                'remove_duplicates': remove_duplicates,
                                'clean_text': clean_text,
                                'normalize_ratings': normalize_ratings,
                                'parse_dates': parse_dates
                            }
                            
                            # Aplicar limpeza
                            df_cleaned, cleaning_report = clean_reviews_dataset(df, review_columns, cleaning_options)
                            
                            # Aplicar filtros adicionais
                            if min_rating is not None or max_rating is not None:
                                for col in rating_cols:
                                    if col in df_cleaned.columns:
                                        if min_rating is not None:
                                            df_cleaned = df_cleaned[
                                                (df_cleaned[col].isna()) | 
                                                (pd.to_numeric(df_cleaned[col], errors='coerce') >= min_rating)
                                            ]
                                        if max_rating is not None:
                                            df_cleaned = df_cleaned[
                                                (df_cleaned[col].isna()) | 
                                                (pd.to_numeric(df_cleaned[col], errors='coerce') <= max_rating)
                                            ]
                            
                            # Mostrar relatório de limpeza
                            st.success("✅ Limpeza concluída!")
                            
                            st.markdown("##### 📈 Relatório de Limpeza")
                            
                            report_col1, report_col2, report_col3, report_col4 = st.columns(4)
                            
                            with report_col1:
                                st.metric("Registros Originais", cleaning_report['original_rows'])
                            with report_col2:
                                st.metric("Registros Limpos", cleaning_report['cleaned_rows'])
                            with report_col3:
                                removed = cleaning_report['original_rows'] - cleaning_report['cleaned_rows']
                                st.metric("Registros Removidos", removed)
                            with report_col4:
                                if cleaning_report['original_rows'] > 0:
                                    retention_pct = (cleaning_report['cleaned_rows'] / cleaning_report['original_rows']) * 100
                                    st.metric("Retenção (%)", f"{retention_pct:.1f}%")
                                else:
                                    st.metric("Retenção (%)", "N/A")
                            
                            # Detalhes da limpeza
                            details_col1, details_col2 = st.columns(2)
                            
                            with details_col1:
                                st.markdown("**🔍 Detalhes da Limpeza:**")
                                if cleaning_report['removed_empty'] > 0:
                                    st.write(f"• Reviews vazias removidas: {cleaning_report['removed_empty']}")
                                if cleaning_report['removed_duplicates'] > 0:
                                    st.write(f"• Reviews duplicadas removidas: {cleaning_report['removed_duplicates']}")
                                if cleaning_report['cleaned_text'] > 0:
                                    st.write(f"• Colunas de texto limpas: {cleaning_report['cleaned_text']}")
                            
                            with details_col2:
                                st.markdown("**📊 Processamento:**")
                                if cleaning_report['normalized_ratings'] > 0:
                                    st.write(f"• Ratings normalizados: {cleaning_report['normalized_ratings']}")
                                if cleaning_report['parsed_dates'] > 0:
                                    st.write(f"• Datas convertidas: {cleaning_report['parsed_dates']}")
                            
                            # Mostrar preview do dataset limpo
                            st.markdown("##### 👀 Preview do Dataset Limpo")
                            st.dataframe(df_cleaned.head(10), use_container_width=True)
                            
                            # Opção para download
                            st.markdown("##### 💾 Download do Dataset Limpo")
                            
                            # Preparar CSV para download
                            csv_buffer = io.StringIO()
                            df_cleaned.to_csv(csv_buffer, index=False)
                            csv_data = csv_buffer.getvalue()
                            
                            # Nome do arquivo
                            original_name = uploaded_file.name if hasattr(uploaded_file, 'name') else str(uploaded_file)
                            if original_name.endswith('.csv'):
                                clean_filename = original_name.replace('.csv', '_limpo.csv')
                            else:
                                clean_filename = f"{original_name}_limpo.csv"
                            
                            st.download_button(
                                label="📥 Baixar Dataset Limpo",
                                data=csv_data,
                                file_name=clean_filename,
                                mime="text/csv",
                                use_container_width=True
                            )
                            
                            # Salvar no session state para usar em outras análises
                            st.session_state.cleaned_dataset = df_cleaned
                            st.info("💡 **Dica:** O dataset limpo foi salvo e pode ser usado nas outras abas de análise!")
        
        except Exception as e:
            st.error(f"❌ Erro ao analisar dataset: {str(e)}")
            st.exception(e)
    
    else:
        st.info("📂 Carregue um dataset CSV para começar a análise EDA.")
        
        # Mostrar formatos suportados
        st.markdown("### 📋 Formatos de Dataset Suportados")
        
        col_format1, col_format2 = st.columns(2)
        
        with col_format1:
            st.markdown("**🎯 Detecção Automática de Colunas:**")
            st.markdown("""
            O sistema detecta automaticamente colunas baseado em padrões:
            
            **Título/Nome do Produto:**
            - titulo, title, nome, produto, name, item
            
            **Preço:**
            - preço, preco, price, valor, custo, cost
            
            **Vendedor:**
            - vendedor, seller, loja, store, merchant
            
            **Avaliação:**
            - media, rating, avaliacao, estrela, star, nota
            
            **Total de Reviews:**
            - total avaliações, review count, quantidade
            
            **Marca:**
            - marca, brand, fabricante, manufacturer
            """)
        
        with col_format2:
            st.markdown("**📊 Exemplos de Datasets Compatíveis:**")
            st.markdown("""
            **Formato HP Challenge (completo):**
            ```
            TÍTULO, PREÇO, VENDEDOR, MÉDIA AVALIAÇÕES, TOTAL AVALIAÇÕES
            ```
            
            **Formato E-commerce Simples:**
            ```
            nome, valor, loja, rating
            ```
            
            **Formato Marketplace:**
            ```
            produto, price, seller, stars, reviews
            ```
            
            **Formato Mínimo:**
            ```
            title, price
            ```
            
            ✅ **Qualquer CSV com pelo menos uma coluna será analisado!**
            """)
        
        # Mostrar dataset de exemplo se existir
        import glob
        csv_files = glob.glob("*.csv")
        if csv_files:
            st.markdown("### 🔍 Datasets Disponíveis")
            
            for csv_file in csv_files[:5]:  # Mostrar até 5 arquivos
                col_file1, col_file2 = st.columns([3, 1])
                with col_file1:
                    st.write(f"📄 **{csv_file}**")
                    try:
                        # Tentar ler as primeiras linhas para mostrar preview
                        preview_df = pd.read_csv(csv_file, nrows=0)  # Só as colunas
                        st.write(f"Colunas: {', '.join(preview_df.columns[:5])}{'...' if len(preview_df.columns) > 5 else ''}")
                    except:
                        st.write("Arquivo CSV detectado")
                
                with col_file2:
                    if st.button(f"📊 Carregar", key=f"load_{csv_file}", use_container_width=True):
                        st.session_state.selected_csv = csv_file
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### 🚀 Funcionalidades da EDA")
        
        feature_col1, feature_col2, feature_col3 = st.columns(3)
        
        with feature_col1:
            st.markdown("""
            **🧹 Limpeza & Descritiva:**
            - Detecção de valores ausentes
            - Análise de tipos de dados
            - Estatísticas descritivas
            - Recomendações de limpeza
            """)
        
        with feature_col2:
            st.markdown("""
            **📝 Análise Textual:**
            - WordClouds interativas
            - N-grams (bigramas, trigramas)
            - Análise de palavras suspeitas
            - Features textuais para ML
            """)
        
        with feature_col3:
            st.markdown("""
            **📊 Correlações & Features:**
            - Matriz de correlação
            - Segmentação avançada
            - Identificação de features ML
            - Cronograma CRISP-DM
            """)

# Rodapé
st.markdown("---")
st.markdown("**🏆 HP Challenge Sprint** - Sistema Inteligente de Detecção de Falsificações | Desenvolvido com Streamlit") 
