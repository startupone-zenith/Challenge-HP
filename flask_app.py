#!/usr/bin/env python
"""
HP Challenge Sprint - Detector de Falsificações
Flask Application - Migrated from Streamlit

Sistema Inteligente de Detecção de Produtos HP Suspeitos/Piratas em E-commerce
"""

import multiprocessing
import os
import sys
from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, flash
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
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Flask
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
import hashlib
import json
warnings.filterwarnings('ignore')

# Configurar o multiprocessing
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Suprimir warnings
import warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Importar os spiders do Scrapy
from mercadolivre_spider import run_spider, run_product_details_spider
from mercadolivre_spider_reviews import run_review_spider

# =============================================================================
# FLASK APP CONFIGURATION
# =============================================================================

app = Flask(__name__)
app.secret_key = 'hp-challenge-sprint-2024-secret-key'  # Change this in production
app.config['PERMANENT_SESSION_LIFETIME'] = 7200  # 2 hours

# =============================================================================
# SISTEMA DE CACHE TEMPORÁRIO ADAPTADO PARA FLASK
# =============================================================================

def get_cache_key(func_name, **kwargs):
    """
    Gera uma chave única para o cache baseada no nome da função e parâmetros
    """
    params_str = json.dumps(kwargs, sort_keys=True, default=str)
    cache_key = f"{func_name}_{hashlib.md5(params_str.encode()).hexdigest()}"
    return cache_key

def get_from_cache(cache_key):
    """
    Recupera dados do cache (session)
    """
    if 'scrapy_cache' not in session:
        session['scrapy_cache'] = {}
    
    return session['scrapy_cache'].get(cache_key)

def save_to_cache(cache_key, data):
    """
    Salva dados no cache (session)
    """
    if 'scrapy_cache' not in session:
        session['scrapy_cache'] = {}
    
    session['scrapy_cache'][cache_key] = data
    
    # Limitar o tamanho do cache (manter apenas os 50 itens mais recentes)
    if len(session['scrapy_cache']) > 50:
        keys_to_remove = list(session['scrapy_cache'].keys())[:-50]
        for key in keys_to_remove:
            del session['scrapy_cache'][key]

def clear_cache():
    """
    Limpa todo o cache
    """
    if 'scrapy_cache' in session:
        session['scrapy_cache'] = {}

# =============================================================================
# FUNÇÕES WRAPPER COM CACHE (ADAPTADAS DO STREAMLIT)
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
    
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data['results'], cached_data['urls_used']
    
    # Executar spider
    search_results, urls_used = run_spider(
        query=query,
        max_items=max_items,
        sort_by=sort_by,
        condition=condition,
        extract_images=extract_images
    )
    
    # Salvar no cache
    cache_data = {
        'results': search_results,
        'urls_used': urls_used,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_to_cache(cache_key, cache_data)
    
    return search_results, urls_used

def cached_run_product_details_spider(product_url):
    """
    Wrapper com cache para run_product_details_spider
    """
    cache_key = get_cache_key('run_product_details_spider', product_url=product_url)
    
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data['results']
    
    # Executar spider
    product_details = run_product_details_spider(product_url)
    
    # Salvar no cache
    cache_data = {
        'results': product_details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_to_cache(cache_key, cache_data)
    
    return product_details

def cached_run_review_spider(product_id, max_reviews=200, rating_limits=None):
    """
    Wrapper com cache para run_review_spider
    """
    cache_key = get_cache_key(
        'run_review_spider',
        product_id=product_id,
        max_reviews=max_reviews,
        rating_limits=rating_limits
    )
    
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data['results']
    
    # Executar spider
    reviews = run_review_spider(
        product_id=product_id,
        max_reviews=max_reviews,
        rating_limits=rating_limits
    )
    
    # Salvar no cache
    cache_data = {
        'results': reviews,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_to_cache(cache_key, cache_data)
    
    return reviews

# =============================================================================
# IMPORT ALL ANALYSIS FUNCTIONS FROM ORIGINAL APP
# =============================================================================

def extrair_preco_numerico(preco_str):
    """
    Extrai o valor numérico de uma string de preço
    """
    if pd.isna(preco_str) or preco_str == 'N/A':
        return None
    
    # Remover símbolos de moeda e espaços
    preco_clean = re.sub(r'[R$\s]', '', str(preco_str))
    
    # Substituir vírgula por ponto para decimal
    preco_clean = preco_clean.replace(',', '.')
    
    # Extrair números e ponto decimal
    match = re.search(r'\d+\.?\d*', preco_clean)
    
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    
    return None

def identificar_modelo_cartucho(titulo):
    """
    Identifica o modelo do cartucho HP baseado no título
    """
    if pd.isna(titulo):
        return 'N/A'
    
    titulo_upper = str(titulo).upper()
    
    # Padrões de modelos HP mais comuns
    modelos_hp = [
        r'HP\s*(\d{2,3}[A-Z]*)', # HP 664, HP 122A, etc.
        r'(\d{2,3}[A-Z]*)\s*HP', # 664 HP, 122A HP, etc.
        r'HP(\d{2,3}[A-Z]*)',    # HP664, HP122A, etc.
        r'(\d{2,3}[A-Z]*)',      # Apenas números como 664, 122A
    ]
    
    for padrao in modelos_hp:
        matches = re.findall(padrao, titulo_upper)
        if matches:
            # Retornar o primeiro match encontrado
            modelo = matches[0]
            # Limpar e padronizar
            modelo = re.sub(r'[^\w]', '', modelo)
            return f"HP {modelo}"
    
    return 'Modelo não identificado'

def calcular_probabilidade_preco(produto):
    """
    Calcula a probabilidade de falsificação baseada no preço
    """
    preco = extrair_preco_numerico(produto.get('PRECO', 'N/A'))
    
    if preco is None:
        return 0.5  # Probabilidade neutra se não conseguir extrair preço
    
    # Definir faixas de preço suspeitas para cartuchos HP
    # Baseado em preços típicos de mercado
    if preco < 15:  # Preços muito baixos são suspeitos
        return 0.8
    elif preco < 25:  # Preços baixos são moderadamente suspeitos
        return 0.6
    elif preco < 50:  # Preços normais
        return 0.3
    elif preco < 100:  # Preços altos mas ainda razoáveis
        return 0.2
    else:  # Preços muito altos podem ser suspeitos também
        return 0.4

def analisar_reviews_falsificacao(product_id, max_reviews=100):
    """
    Analisa reviews para detectar padrões suspeitos
    """
    try:
        reviews = cached_run_review_spider(product_id, max_reviews=max_reviews)
        
        if not reviews or len(reviews) == 0:
            return {
                'probabilidade_reviews': 0.5,
                'total_reviews': 0,
                'detalhes': 'Nenhuma review encontrada'
            }
        
        # Análise de padrões suspeitos
        suspicious_patterns = 0
        total_reviews = len(reviews)
        
        # Padrões a verificar:
        for review in reviews:
            texto = review.get('texto', '').lower()
            
            # 1. Reviews muito curtas ou genéricas
            if len(texto) < 10:
                suspicious_patterns += 1
            
            # 2. Reviews com padrões repetitivos
            if any(pattern in texto for pattern in [
                'produto original', 'recomendo', 'muito bom',
                'excelente produto', 'chegou rápido'
            ]):
                suspicious_patterns += 0.5
            
            # 3. Reviews com erros de português excessivos
            if texto.count('  ') > 2:  # Espaços duplos excessivos
                suspicious_patterns += 0.3
        
        # Calcular probabilidade baseada nos padrões
        if total_reviews > 0:
            ratio_suspeitas = suspicious_patterns / total_reviews
            probabilidade = min(ratio_suspeitas * 1.5, 1.0)  # Limitar a 1.0
        else:
            probabilidade = 0.5
        
        return {
            'probabilidade_reviews': probabilidade,
            'total_reviews': total_reviews,
            'padroes_suspeitos': suspicious_patterns,
            'detalhes': f'{suspicious_patterns:.1f} padrões suspeitos em {total_reviews} reviews'
        }
        
    except Exception as e:
        logging.error(f"Erro ao analisar reviews: {str(e)}")
        return {
            'probabilidade_reviews': 0.5,
            'total_reviews': 0,
            'detalhes': f'Erro na análise: {str(e)}'
        }

def calcular_probabilidade_falsificacao(produto, analisar_reviews=True):
    """
    Calcula a probabilidade total de falsificação
    """
    # Peso dos diferentes fatores
    peso_preco = 0.4
    peso_vendedor = 0.3
    peso_titulo = 0.2
    peso_reviews = 0.1
    
    # Calcular probabilidades individuais
    prob_preco = calcular_probabilidade_preco(produto)
    
    # Análise do vendedor (simplificada)
    vendedor = produto.get('VENDEDOR', '')
    if 'hp' in vendedor.lower() or 'oficial' in vendedor.lower():
        prob_vendedor = 0.1  # Vendedor oficial é menos provável de ser falso
    else:
        prob_vendedor = 0.6  # Vendedores não oficiais são mais suspeitos
    
    # Análise do título
    titulo = produto.get('TITULO PRODUTO', '')
    if any(palavra in titulo.lower() for palavra in ['original', 'genuíno', 'hp']):
        prob_titulo = 0.3
    else:
        prob_titulo = 0.7
    
    # Análise de reviews (se solicitada)
    prob_reviews = 0.5  # Valor padrão
    if analisar_reviews:
        product_id = produto.get('PRODUCT_ID')
        if product_id:
            review_analysis = analisar_reviews_falsificacao(product_id)
            prob_reviews = review_analysis['probabilidade_reviews']
    
    # Calcular probabilidade total
    probabilidade_total = (
        prob_preco * peso_preco +
        prob_vendedor * peso_vendedor +
        prob_titulo * peso_titulo +
        prob_reviews * peso_reviews
    )
    
    return {
        'probabilidade_total': probabilidade_total * 100,  # Converter para percentual
        'prob_preco': prob_preco * 100,
        'prob_vendedor': prob_vendedor * 100,
        'prob_titulo': prob_titulo * 100,
        'prob_reviews': prob_reviews * 100,
        'classificacao': 'SUSPEITO' if probabilidade_total > 0.6 else 'PROVÁVEL ORIGINAL' if probabilidade_total < 0.4 else 'INCERTO'
    }

def processar_deteccao_falsificacao(produtos, analisar_reviews=True):
    """
    Processa a detecção de falsificação para uma lista de produtos
    """
    resultados = []
    
    for i, produto in enumerate(produtos):
        try:
            resultado = calcular_probabilidade_falsificacao(produto, analisar_reviews)
            resultado['produto_index'] = i
            resultado['produto'] = produto
            resultados.append(resultado)
        except Exception as e:
            logging.error(f"Erro ao processar produto {i}: {str(e)}")
            # Adicionar resultado com erro
            resultados.append({
                'produto_index': i,
                'produto': produto,
                'probabilidade_total': 50,
                'classificacao': 'ERRO',
                'erro': str(e)
            })
    
    return resultados

# =============================================================================
# FLASK ROUTES
# =============================================================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/busca')
def busca():
    """Página de busca e coleta"""
    return render_template('busca.html')

@app.route('/api/buscar', methods=['POST'])
def api_buscar():
    """API endpoint para buscar produtos"""
    try:
        data = request.json
        
        # Extrair parâmetros
        search_query = data.get('query', 'cartucho hp')
        max_items = data.get('max_items', 20)
        sort_by = data.get('sort_by', 'relevance')
        condition = data.get('condition', 'all')
        load_images = data.get('load_images', True)
        
        # Executar busca
        search_results, urls_used = cached_run_spider(
            query=search_query,
            max_items=max_items,
            sort_by=sort_by,
            condition=condition,
            extract_images=load_images
        )
        
        # Salvar resultados na sessão para uso posterior
        session['last_search_results'] = search_results
        session['last_urls_used'] = urls_used
        
        return jsonify({
            'success': True,
            'results': search_results,
            'urls_used': urls_used,
            'total_found': len(search_results)
        })
        
    except Exception as e:
        logging.error(f"Erro na busca: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/falsificacao')
def falsificacao():
    """Página de detecção de falsificação"""
    return render_template('falsificacao.html')

@app.route('/api/analisar_falsificacao', methods=['POST'])
def api_analisar_falsificacao():
    """API endpoint para análise de falsificação"""
    try:
        # Obter produtos da última busca
        produtos = session.get('last_search_results', [])
        
        if not produtos:
            return jsonify({
                'success': False,
                'error': 'Nenhum produto encontrado. Execute uma busca primeiro.'
            }), 400
        
        data = request.json
        analisar_reviews = data.get('analisar_reviews', False)
        
        # Processar detecção
        resultados = processar_deteccao_falsificacao(produtos, analisar_reviews)
        
        # Calcular estatísticas
        total_produtos = len(resultados)
        suspeitos = sum(1 for r in resultados if r['classificacao'] == 'SUSPEITO')
        originais = sum(1 for r in resultados if r['classificacao'] == 'PROVÁVEL ORIGINAL')
        incertos = sum(1 for r in resultados if r['classificacao'] == 'INCERTO')
        
        stats = {
            'total_produtos': total_produtos,
            'suspeitos': suspeitos,
            'originais': originais,
            'incertos': incertos,
            'percentual_suspeitos': (suspeitos / total_produtos * 100) if total_produtos > 0 else 0
        }
        
        return jsonify({
            'success': True,
            'resultados': resultados,
            'estatisticas': stats
        })
        
    except Exception as e:
        logging.error(f"Erro na análise de falsificação: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dataset')
def dataset():
    """Página do gerador de dataset"""
    return render_template('dataset.html')

@app.route('/analise')
def analise():
    """Página de análise exploratória"""
    return render_template('analise.html')

@app.route('/api/clear_cache', methods=['POST'])
def api_clear_cache():
    """API endpoint para limpar cache"""
    try:
        clear_cache()
        return jsonify({
            'success': True,
            'message': 'Cache limpo com sucesso!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cache_info')
def api_cache_info():
    """API endpoint para informações do cache"""
    try:
        cache_size = len(session.get('scrapy_cache', {}))
        cache_items = []
        
        for key, data in session.get('scrapy_cache', {}).items():
            cache_items.append({
                'key': key[:30] + '...' if len(key) > 30 else key,
                'timestamp': data.get('timestamp', 'N/A')
            })
        
        return jsonify({
            'success': True,
            'cache_size': cache_size,
            'cache_items': cache_items[:10]  # Mostrar apenas os primeiros 10
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# =============================================================================
# MAIN APPLICATION
# =============================================================================

if __name__ == '__main__':
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Executar app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )

