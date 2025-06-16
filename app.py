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
    
    # Verificar se precisa extrair dados detalhados
    needs_detailed_extraction = any(detailed_fields.values())
    
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
                detalhes = risk_result.get('detalhes_reviews', [])
                if detalhes:
                    # Criar resumo das reviews suspeitas
                    resumo_detalhes = []
                    for detalhe in detalhes[:3]:  # Máximo 3 exemplos
                        resumo_detalhes.append(f"⭐{detalhe['rating']}: {detalhe['texto_trecho'][:50]}...")
                    row_data['Exemplos Reviews Suspeitas'] = ' | '.join(resumo_detalhes)
                else:
                    row_data['Exemplos Reviews Suspeitas'] = 'Nenhuma review suspeita encontrada'
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
                row_data['Exemplos Reviews Suspeitas'] = 'N/A'
        
        csv_data.append(row_data)
    
    return csv_data

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
    'OFERTA', 'IMPERDIVEL', 'SUPER PRECO', 'MEGA OFERTA'
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
            'não imprime', 'vazou', 'vazamento', 'secou rápido', 'acabou rápido'
        ]
        
        # Contar ocorrências
        reviews_suspeitas = 0
        total_ocorrencias = 0
        detalhes_encontrados = []
        
        for review in reviews:
            texto_review = review.get('text', '').lower()
            ocorrencias_nesta_review = 0
            
            for palavra in palavras_falsificacao:
                if palavra in texto_review:
                    ocorrencias_nesta_review += texto_review.count(palavra)
                    total_ocorrencias += texto_review.count(palavra)
            
            if ocorrencias_nesta_review > 0:
                reviews_suspeitas += 1
                # Guardar exemplo (limitado)
                if len(detalhes_encontrados) < 3:
                    detalhes_encontrados.append({
                        'rating': review.get('rating', 'N/A'),
                        'texto_trecho': texto_review[:100] + '...' if len(texto_review) > 100 else texto_review,
                        'ocorrencias': ocorrencias_nesta_review
                    })
        
        # Calcular probabilidade baseada nas reviews
        percentual_reviews_suspeitas = (reviews_suspeitas / total_reviews) * 100
        
        probabilidade_reviews = 0
        motivo = ""
        
        if percentual_reviews_suspeitas >= 20:  # 20% ou mais das reviews são suspeitas
            probabilidade_reviews = 60
            motivo = f"{reviews_suspeitas}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif percentual_reviews_suspeitas >= 10:  # 10-19% suspeitas
            probabilidade_reviews = 40
            motivo = f"{reviews_suspeitas}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif percentual_reviews_suspeitas >= 5:   # 5-9% suspeitas
            probabilidade_reviews = 25
            motivo = f"{reviews_suspeitas}/{total_reviews} reviews suspeitas ({percentual_reviews_suspeitas:.1f}%)"
        elif total_ocorrencias > 0:  # Algumas ocorrências, mas baixo percentual
            probabilidade_reviews = 10
            motivo = f"{total_ocorrencias} menções suspeitas em {total_reviews} reviews"
        else:
            motivo = f"Nenhuma menção suspeita em {total_reviews} reviews analisadas"
        
        return probabilidade_reviews, motivo, detalhes_encontrados
        
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
                prob_reviews, motivo_reviews, detalhes = analisar_reviews_falsificacao(product_id, max_reviews=100)
                resultado['probabilidade_reviews'] = prob_reviews
                resultado['motivo_reviews'] = motivo_reviews
                resultado['detalhes_reviews'] = detalhes
            except Exception as e:
                resultado['motivo_reviews'] = f"Erro na análise de reviews: {str(e)}"
        else:
            resultado['motivo_reviews'] = "ID do produto não disponível para análise de reviews"
    
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

# Título da aplicação
st.title("🏆 Challenge Sprint HP - Detector de Falsificações")
st.markdown("**Entregável 1:** Sistema de Web Scraping e Análise de Dados para identificação de produtos HP suspeitos/piratas em e-commerce")

# Informações do projeto
with st.expander("📋 Sobre o Challenge Sprint HP", expanded=False):
    st.markdown("""
    **Objetivo:** Desenvolver uma solução inteligente e automatizada para identificar possíveis casos de pirataria 
    de produtos HP vendidos em sites de e-commerce.
    
    **Funcionalidades Implementadas:**
    - ✅ Web Scraping do Mercado Livre com filtros avançados
    - ✅ Coleta de dados estruturados (título, preço, vendedor, avaliações, etc.)
    - ✅ Rotulagem heurística automática ("original" vs "suspeito/pirata")
    - ✅ Análise de preços baseada em valores de referência HP
    - ✅ Verificação de vendedores oficiais/confiáveis
    - ✅ Detecção de palavras suspeitas e erros de gramática
    - ✅ Geração de dataset estruturado para Machine Learning
    - ✅ Análise de reviews para indicadores de falsificação
    
    **Critérios Heurísticos:**
    - **Original:** Vendedor oficial, preço coerente, título sem indicadores suspeitos
    - **Suspeito/Pirata:** Preço muito baixo, vendedor desconhecido, palavras suspeitas, erros de grafia
    """)

st.markdown("---")

# Interface para busca de produtos
st.write("Digite o produto que deseja buscar:")
search_query = st.text_input("Termo de busca", "cartucho hp")

# Opções de filtro
st.subheader("Opções de Filtro")

# Filtro de Ordenação
sort_options_display = {
    'Relevância': 'relevance',
    'Menor Preço': 'price_asc',
    'Maior Preço': 'price_desc'
}
selected_sort_display = st.selectbox(
    "Ordenar por:", 
    options=list(sort_options_display.keys()),
    index=0 # Padrão para Relevância
)
sort_by_value = sort_options_display[selected_sort_display]

# Filtro de Condição
condition_options_display = {
    'Todos': 'all',
    'Novo': 'new',
    'Usado': 'used'
}
selected_condition_display = st.selectbox(
    "Condição do produto:",
    options=list(condition_options_display.keys()),
    index=0 # Padrão para Todos
)
condition_value = condition_options_display[selected_condition_display]

# Campo para quantidade máxima de itens
max_items = st.number_input("Número máximo de itens a extrair:", 
                             min_value=1, 
                             max_value=500, 
                             value=10, # Reduced default for quicker testing
                             step=10,
                             help="Defina quantos produtos no máximo serão extraídos. Valores maiores podem aumentar o tempo de execução.")

# Layout em colunas para as opções adicionais
col1, col2 = st.columns(2)

# Opção para carregar imagens
with col1:
    load_images = st.checkbox("Carregar imagens dos produtos", value=True, 
                              help="Desative para busca mais rápida, sem exibir imagens dos produtos")

# Indicador de paginação
with col2:
    st.info("Com paginação automática: o sistema navegará por quantas páginas forem necessárias até atingir o limite de itens definido.")

# Seção do Gerador de CSV
st.subheader("📊 Gerador de CSV Configurável")

# Toggle para ativar o gerador de CSV
csv_enabled = st.checkbox(
    "🔧 Ativar Gerador de CSV Avançado", 
    value=st.session_state.csv_generator_enabled,
    help="Ative para configurar quais dados incluir no CSV e extrair informações detalhadas de cada produto"
)
st.session_state.csv_generator_enabled = csv_enabled

if csv_enabled:
    st.markdown("##### 📋 Configuração dos Campos do CSV")
    
    # Abas para organizar as configurações
    tab_basic, tab_detailed, tab_risk = st.tabs(["📦 Dados Básicos", "🔍 Dados Detalhados", "⚠️ Análise de Risco"])
    
    with tab_basic:
        st.markdown("**Campos extraídos da busca principal:**")
        
        basic_cols = st.columns(3)
        basic_fields = st.session_state.csv_fields_config['basic_fields']
        
        with basic_cols[0]:
            basic_fields['titulo'] = st.checkbox("Título do Produto", value=basic_fields['titulo'])
            basic_fields['preco'] = st.checkbox("Preço Atual", value=basic_fields['preco'])
            basic_fields['preco_anterior'] = st.checkbox("Preço Anterior", value=basic_fields['preco_anterior'])
            basic_fields['marca'] = st.checkbox("Marca", value=basic_fields['marca'])
        
        with basic_cols[1]:
            basic_fields['vendedor'] = st.checkbox("Vendedor", value=basic_fields['vendedor'])
            basic_fields['link'] = st.checkbox("Link do Produto", value=basic_fields['link'])
            basic_fields['id_produto'] = st.checkbox("ID do Produto", value=basic_fields['id_produto'])
            basic_fields['imagem'] = st.checkbox("URL da Imagem", value=basic_fields['imagem'])
        
        with basic_cols[2]:
            basic_fields['entrega'] = st.checkbox("Informações de Entrega", value=basic_fields['entrega'])
            basic_fields['entrega_full'] = st.checkbox("Entrega FULL", value=basic_fields['entrega_full'])
            basic_fields['media_avaliacoes_busca'] = st.checkbox("Média de Avaliações (Busca)", value=basic_fields['media_avaliacoes_busca'])
            basic_fields['total_avaliacoes_busca'] = st.checkbox("Total de Avaliações (Busca)", value=basic_fields['total_avaliacoes_busca'])
    
    with tab_detailed:
        st.markdown("**Campos extraídos das páginas individuais dos produtos:**")
        st.info("⚠️ **Atenção:** Estes campos requerem acesso individual a cada produto, aumentando significativamente o tempo de processamento.")
        
        detailed_cols = st.columns(2)
        detailed_fields = st.session_state.csv_fields_config['detailed_fields']
        
        with detailed_cols[0]:
            detailed_fields['descricao'] = st.checkbox("Descrição Completa", value=detailed_fields['descricao'])
            detailed_fields['caracteristicas_principais'] = st.checkbox("Características Principais", value=detailed_fields['caracteristicas_principais'])
            detailed_fields['outras_caracteristicas'] = st.checkbox("Outras Características", value=detailed_fields['outras_caracteristicas'])
        
        with detailed_cols[1]:
            detailed_fields['total_reviews_detalhado'] = st.checkbox("Total de Reviews (Detalhado)", value=detailed_fields['total_reviews_detalhado'])
            detailed_fields['distribuicao_estrelas'] = st.checkbox("Distribuição por Estrelas", value=detailed_fields['distribuicao_estrelas'])
    
    with tab_risk:
        st.markdown("**Campos da análise de risco de falsificação:**")
        st.info("🔍 **Nota:** Estes campos são gerados pela análise de detecção de falsificação baseada em preços e reviews.")
        
        # Inicializar campos de risco se não existirem
        if 'risk_fields' not in st.session_state.csv_fields_config:
            st.session_state.csv_fields_config['risk_fields'] = {
                'classificacao_risco': True,
                'probabilidade_total': True,
                'probabilidade_preco': False,
                'motivo_preco': False,
                'probabilidade_reviews': False,
                'motivo_reviews': False,
                'detalhes_reviews_suspeitas': False
            }
        
        risk_cols = st.columns(2)
        risk_fields = st.session_state.csv_fields_config['risk_fields']
        
        with risk_cols[0]:
            risk_fields['classificacao_risco'] = st.checkbox("Classificação de Risco", value=risk_fields['classificacao_risco'], help="Alto/Médio/Baixo Risco")
            risk_fields['probabilidade_total'] = st.checkbox("Probabilidade Total (%)", value=risk_fields['probabilidade_total'], help="Probabilidade geral de falsificação")
            risk_fields['probabilidade_preco'] = st.checkbox("Probabilidade Preço (%)", value=risk_fields['probabilidade_preco'], help="Probabilidade baseada na análise de preço")
            risk_fields['motivo_preco'] = st.checkbox("Motivo Análise Preço", value=risk_fields['motivo_preco'], help="Explicação da análise de preço")
        
        with risk_cols[1]:
            risk_fields['probabilidade_reviews'] = st.checkbox("Probabilidade Reviews (%)", value=risk_fields['probabilidade_reviews'], help="Probabilidade baseada na análise de reviews")
            risk_fields['motivo_reviews'] = st.checkbox("Motivo Análise Reviews", value=risk_fields['motivo_reviews'], help="Explicação da análise de reviews")
            risk_fields['detalhes_reviews_suspeitas'] = st.checkbox("Exemplos Reviews Suspeitas", value=risk_fields['detalhes_reviews_suspeitas'], help="Exemplos de reviews que indicam possível falsificação")
    
    # Mostrar resumo da configuração
    basic_selected = sum(1 for v in basic_fields.values() if v)
    detailed_selected = sum(1 for v in detailed_fields.values() if v)
    risk_selected = sum(1 for v in risk_fields.values() if v)
    
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    with summary_col1:
        st.metric("Campos Básicos", basic_selected, delta=f"de {len(basic_fields)}")
    
    with summary_col2:
        st.metric("Campos Detalhados", detailed_selected, delta=f"de {len(detailed_fields)}")
    
    with summary_col3:
        st.metric("Campos de Risco", risk_selected, delta=f"de {len(risk_fields)}")
    
    with summary_col4:
        total_fields = basic_selected + detailed_selected + risk_selected
        st.metric("Total de Campos", total_fields)
    
    # Aviso sobre tempo de processamento
    if detailed_selected > 0:
        estimated_time = max_items * detailed_selected * 2  # Estimativa: 2 segundos por campo detalhado por produto
        st.warning(f"⏱️ **Tempo estimado:** ~{estimated_time//60}min {estimated_time%60}s para {max_items} produtos com {detailed_selected} campos detalhados")
    
    st.markdown("---")

# Configurações de Reviews
st.subheader("⭐ Configurações de Reviews")

# Toggle para escolher entre modo geral ou por rating
use_rating_percentages = st.checkbox(
    "🎯 Configurar limites específicos por estrela", 
    value=st.session_state.use_rating_percentages,
    help="Ative para definir quantas reviews coletar para cada nota (1-5 estrelas)"
)
st.session_state.use_rating_percentages = use_rating_percentages

if use_rating_percentages:
    # Primeiro, configurar o total de reviews desejado
    col_total, col_info = st.columns([2, 1])
    
    with col_total:
        total_reviews_desired = st.number_input(
            "Total de reviews a coletar:",
            min_value=10,
            max_value=230,  # Limite técnico da API
            value=100,
            step=10,
            help="Número total de reviews que serão distribuídas pelas categorias de estrelas"
        )
    
    with col_info:
        st.info("💡 **Dica:** Configure as porcentagens abaixo para cada tipo de avaliação")
    
    st.markdown("##### 🌟 Distribuição percentual por estrela:")
    
    # Layout em colunas para os sliders de rating
    rating_cols = st.columns(5)
    
    for i, (rating, col) in enumerate(zip([5, 4, 3, 2, 1], rating_cols)):
        with col:
            new_percentage = st.number_input(
                f"{rating}⭐",
                min_value=0,
                max_value=100,
                value=st.session_state.rating_percentages[rating],
                step=5,
                key=f"rating_{rating}_percentage",
                help=f"Porcentagem de reviews com {rating} estrelas"
            )
            st.session_state.rating_percentages[rating] = new_percentage
    
    # Validar e mostrar resumo
    total_percentage = sum(st.session_state.rating_percentages.values())
    
    if total_percentage != 100:
        st.warning(f"⚠️ **Atenção:** As porcentagens somam {total_percentage}% (deve somar 100%)")
    else:
        st.success(f"✅ **Distribuição válida:** {total_percentage}% configurado")
    
    # Mostrar distribuição calculada
    st.markdown("##### 📊 Distribuição calculada:")
    
    calc_cols = st.columns(5)
    calculated_totals = {}
    
    for i, rating in enumerate([5, 4, 3, 2, 1]):
        with calc_cols[i]:
            if total_percentage > 0:
                # Calcular proporcionalmente mesmo se não somar exatamente 100%
                normalized_percentage = st.session_state.rating_percentages[rating] / total_percentage * 100
                calculated_amount = int((normalized_percentage / 100) * total_reviews_desired)
                calculated_totals[rating] = calculated_amount
                st.metric(f"{rating}⭐", f"{calculated_amount}", delta=f"{st.session_state.rating_percentages[rating]}%")
            else:
                calculated_totals[rating] = 0
                st.metric(f"{rating}⭐", "0", delta="0%")
    
    # Armazenar valores calculados para uso posterior
    st.session_state.calculated_rating_limits = calculated_totals
    st.session_state.total_reviews_configured = total_reviews_desired
    
else:
    # Modo geral (original)
    col_reviews1, col_reviews2 = st.columns(2)
    
    with col_reviews1:
        # Definir o valor atual, limitando ao máximo permitido se necessário
        current_value = min(st.session_state.max_reviews_to_fetch, 230)
        
        max_reviews = st.number_input(
            "Máximo de reviews por produto:",
            min_value=10,
            max_value=230,  # Limite técnico da API (200 offset + 30 limit)
            value=current_value,
            step=10,
            help="Quantas opiniões coletar quando clicar em 'Ver Opiniões Detalhadas'. Máximo: 230 reviews."
        )
        st.session_state.max_reviews_to_fetch = max_reviews
    
    with col_reviews2:
        st.info(f"📊 **Configuração atual:** {max_reviews} reviews por produto\n\n💡 **Dica:** Valores maiores podem demorar mais para carregar, mas oferecem análise mais completa.")

# Botões para busca
button_col1, button_col2 = st.columns(2)

with button_col1:
    # Botão para busca normal
    if st.button("🔍 Buscar Produtos", type="primary"):
        st.session_state.reviews_data = None # Clear previous reviews
        st.session_state.fetching_reviews_for_id = None
        st.session_state.last_fetched_product_id_reviews = None
        if search_query:
            with st.spinner(f'Buscando até {max_items} produtos...'):
                try:
                    logging.info(f"Iniciando busca com Scrapy para: {search_query}, Sort: {sort_by_value}, Condition: {condition_value}, Max items: {max_items}")
                    produtos, urls_usadas = run_spider(search_query, 
                                                       extract_images=load_images, 
                                                       sort_by=sort_by_value, 
                                                       condition=condition_value,
                                                       max_items=max_items)
                    logging.info(f"Busca concluída. Produtos: {len(produtos)}, URLs: {urls_usadas}")
                    
                    st.session_state.search_results = produtos # Store results in session state
                    st.session_state.search_urls_used = urls_usadas

                except Exception as e:
                    st.error(f"Ocorreu um erro geral na aplicação durante a busca de produtos: {str(e)}")
                    logging.error(f"Erro na busca de produtos (app.py): {str(e)}")
                    logging.error(traceback.format_exc())
                    st.session_state.search_results = []
                    st.session_state.search_urls_used = []
        else:
            st.warning("Por favor, digite um termo de busca para continuar.")

with button_col2:
    # Botão para gerar CSV
    csv_button_disabled = not st.session_state.csv_generator_enabled
    if st.button("📊 Buscar e Gerar CSV", disabled=csv_button_disabled):
        if not st.session_state.csv_generator_enabled:
            st.warning("Ative o Gerador de CSV primeiro!")
        elif search_query:
            # Verificar se há campos selecionados
            basic_selected = sum(1 for v in st.session_state.csv_fields_config['basic_fields'].values() if v)
            detailed_selected = sum(1 for v in st.session_state.csv_fields_config['detailed_fields'].values() if v)
            risk_selected = sum(1 for v in st.session_state.csv_fields_config.get('risk_fields', {}).values() if v)
            
            if basic_selected == 0 and detailed_selected == 0 and risk_selected == 0:
                st.error("Selecione pelo menos um campo para incluir no CSV!")
            else:
                st.session_state.reviews_data = None # Clear previous reviews
                st.session_state.fetching_reviews_for_id = None
                st.session_state.last_fetched_product_id_reviews = None
                
                # Determinar texto do spinner baseado nos campos selecionados
                spinner_parts = []
                if detailed_selected > 0:
                    spinner_parts.append(f"{detailed_selected} campos detalhados")
                if risk_selected > 0:
                    spinner_parts.append("análise de risco")
                
                if spinner_parts:
                    spinner_text = f'Buscando {max_items} produtos e processando {", ".join(spinner_parts)}...'
                else:
                    spinner_text = f'Buscando {max_items} produtos para CSV...'
                
                with st.spinner(spinner_text):
                    try:
                        # Primeira etapa: busca básica
                        st.info("🔍 Etapa 1/3: Buscando produtos...")
                        logging.info(f"Iniciando busca para CSV: {search_query}, Sort: {sort_by_value}, Condition: {condition_value}, Max items: {max_items}")
                        produtos, urls_usadas = run_spider(search_query, 
                                                           extract_images=load_images, 
                                                           sort_by=sort_by_value, 
                                                           condition=condition_value,
                                                           max_items=max_items)
                        logging.info(f"Busca concluída. Produtos: {len(produtos)}, URLs: {urls_usadas}")
                        
                        if produtos:
                            resultados_falsificacao = None
                            
                            # Segunda etapa: análise de risco (se campos de risco estão selecionados)
                            if risk_selected > 0:
                                st.info("⚠️ Etapa 2/3: Executando análise de risco de falsificação...")
                                
                                def update_progress_csv(current, total):
                                    progress_percent = (current / total) * 100
                                    st.progress(progress_percent / 100, text=f"Analisando produto {current}/{total} ({progress_percent:.1f}%)")
                                
                                resultados_falsificacao = processar_deteccao_falsificacao(
                                    produtos, 
                                    analisar_reviews=True,  # Sempre analisar reviews para CSV
                                    progress_callback=update_progress_csv
                                )
                            
                            # Terceira etapa: gerar CSV
                            etapa_final = "3/3" if risk_selected > 0 else "2/2"
                            st.info(f"📊 Etapa {etapa_final}: Gerando CSV com dados configurados...")
                            csv_data = generate_csv_data(produtos, st.session_state.csv_fields_config, resultados_falsificacao)
                            
                            # Criar DataFrame e CSV
                            df_csv = pd.DataFrame(csv_data)
                            csv_content = df_csv.to_csv(index=False).encode('utf-8')
                            
                            # Armazenar resultados
                            st.session_state.search_results = produtos
                            st.session_state.search_urls_used = urls_usadas
                            st.session_state.csv_data = csv_data
                            st.session_state.csv_content = csv_content
                            if resultados_falsificacao:
                                st.session_state.resultados_falsificacao = resultados_falsificacao
                            
                            success_msg = f"✅ CSV gerado com sucesso! {len(csv_data)} produtos processados com {len(df_csv.columns)} campos."
                            if risk_selected > 0:
                                success_msg += f" Incluindo {risk_selected} campos de análise de risco."
                            st.success(success_msg)
                        else:
                            st.error("Nenhum produto encontrado para gerar o CSV.")
                            
                    except Exception as e:
                        st.error(f"Erro durante a geração do CSV: {str(e)}")
                        logging.error(f"Erro na geração do CSV: {str(e)}")
                        logging.error(traceback.format_exc())
        else:
            st.warning("Por favor, digite um termo de busca para continuar.")

# Display search results if available in session state
if 'search_results' in st.session_state and st.session_state.search_results is not None:
    produtos = st.session_state.search_results
    urls_usadas = st.session_state.search_urls_used

    if not urls_usadas:
        st.warning("O spider não retornou nenhuma URL de busca. Verifique os logs do spider.")
    else:
        st.subheader("URLs de busca usadas pelo Scraper Principal:")
        for i, url in enumerate(urls_usadas):
            st.write(f"{i+1}. [{url}]({url})")
        st.markdown("---")
    
    if produtos:
        st.success(f"Encontrados {len(produtos)} produtos!")
        
        for i, produto in enumerate(produtos):
            product_id_field = produto.get('ID_PRODUTO', 'N/A')
            with st.container():
                st.markdown(f"### {produto.get('TITULO PRODUTO', 'Título não disponível')}")
                cols_main = st.columns([1, 3])
                
                with cols_main[0]: # Image
                    if load_images and produto.get('IMAGEM') and produto.get('IMAGEM') not in ['N/A', 'N/A (imagens desabilitadas)']:
                        try:
                            img_response = make_request(produto['IMAGEM'])
                            if img_response:
                                img = Image.open(io.BytesIO(img_response.content))
                                st.image(img, width=120)
                            else:
                                st.caption("Imagem não baixada")
                        except Exception as e:
                            st.caption("Erro imagem")
                            logging.error(f"Erro ao carregar imagem {produto['IMAGEM']}: {str(e)}")
                    elif not load_images:
                        st.caption("(Imagens desabilitadas)")
                    else:
                        st.caption("Sem imagem")
                
                with cols_main[1]: # Product Info
                    if produto.get('LINK'):
                        st.markdown(f"**Link:** <a href='{produto['LINK']}' target='_blank'>Ver no Mercado Livre</a>", unsafe_allow_html=True)
                    
                    st.write(f"**Preço:** {produto.get('PREÇO', 'N/A')}")
                    if produto.get('PREÇO ANTERIOR', 'N/A') != 'N/A':
                        st.write(f"**Preço anterior:** <s style='color: grey;'>{produto.get('PREÇO ANTERIOR', 'N/A')}</s>", unsafe_allow_html=True)
                    
                    st.write(f"**Marca:** {produto.get('MARCA', 'N/A')}")
                    st.write(f"**ID Produto:** {product_id_field}")
                    st.write(f"**Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                    
                    avg_rating = produto.get('MÉDIA AVALIAÇÕES', 'N/A')
                    total_ratings = produto.get('TOTAL AVALIAÇÕES', 'N/A')
                    if avg_rating != 'N/A':
                        st.write(f"**Avaliação (na busca):** {avg_rating}⭐ ({total_ratings} avaliações)")
                    else:
                        st.write("**Avaliação (na busca):** N/A")

                    st.write(f"**Entrega:** {produto.get('ENTREGA', 'N/A')}")
                    if produto.get('ENTREGA FULL', 'Não') == 'Sim':
                        st.markdown("**Entrega FULL:** <span style='color:green;font-weight:bold;'>Sim</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"**Entrega FULL:** Não")

                # --- Product Details Section ---
                if produto.get('LINK') and produto.get('LINK') != 'N/A':
                    st.markdown("##### 🔍 Análise Detalhada do Produto")
                    
                    details_col1, details_col2 = st.columns([2, 1])
                    
                    with details_col1:
                        details_button_key = f"details_button_{produto.get('LINK', '')}_{i}"
                        if st.button("📋 Analisar Descrição e Características", key=details_button_key):
                            st.session_state.fetching_details_for_url = produto['LINK']
                            
                            with st.spinner(f"Analisando detalhes do produto..."):
                                product_details = run_product_details_spider(produto['LINK'])
                                st.session_state.product_details_data[produto['LINK']] = product_details
                                st.rerun()
                    
                    with details_col2:
                        if produto['LINK'] in st.session_state.product_details_data:
                            details = st.session_state.product_details_data[produto['LINK']]
                            if details and details.get('extraction_success'):
                                st.success("✅ Detalhes extraídos")
                            else:
                                st.error("❌ Falha na extração")
                        else:
                            st.caption("🔍 Clique para analisar")
                    
                    # Display product details if available
                    if produto['LINK'] in st.session_state.product_details_data:
                        details = st.session_state.product_details_data[produto['LINK']]
                        if details and details.get('extraction_success'):
                            with st.expander("📋 Detalhes do Produto", expanded=True):
                                # Descrição
                                st.markdown("**📝 Descrição do Produto:**")
                                if details.get('description') and details['description'] != 'N/A':
                                    st.write(details['description'])
                                else:
                                    st.write("Descrição não disponível")
                                
                                st.markdown("---")
                                
                                # Características Principais
                                main_chars = details.get('main_characteristics', {})
                                if main_chars:
                                    st.markdown("**🔧 Características Principais:**")
                                    
                                    # Organizar em colunas para melhor visualização
                                    char_cols = st.columns(2)
                                    char_items = list(main_chars.items())
                                    
                                    for idx, (char_name, char_value) in enumerate(char_items):
                                        with char_cols[idx % 2]:
                                            st.write(f"**{char_name}:** {char_value}")
                                else:
                                    st.markdown("**🔧 Características Principais:** Não disponíveis")
                                
                                # Outras Características
                                other_chars = details.get('other_characteristics', {})
                                if other_chars:
                                    st.markdown("---")
                                    st.markdown("**📋 Outras Características:**")
                                    
                                    # Organizar em colunas para melhor visualização
                                    other_cols = st.columns(2)
                                    other_items = list(other_chars.items())
                                    
                                    for idx, (char_name, char_value) in enumerate(other_items):
                                        with other_cols[idx % 2]:
                                            st.write(f"**{char_name}:** {char_value}")
                        elif details and not details.get('extraction_success'):
                            with st.expander("📋 Detalhes do Produto", expanded=True):
                                st.warning("⚠️ Não foi possível extrair os detalhes deste produto. O layout da página pode ter mudado ou as informações podem não estar disponíveis.")

                # --- Reviews Section ---
                if product_id_field != 'N/A':
                    st.markdown("##### ⭐ Análise de Opiniões")
                    # Layout para o botão de reviews e informações
                    reviews_col1, reviews_col2 = st.columns([2, 1])
                    
                    with reviews_col1:
                        button_key = f"reviews_button_{product_id_field}_{i}" # Unique key for button
                        if st.button("Ver Opiniões Detalhadas", key=button_key):
                            st.session_state.fetching_reviews_for_id = product_id_field
                            st.session_state.reviews_data = None # Clear previous reviews data or set to loading
                            st.session_state.last_fetched_product_id_reviews = None
                            
                            # Preparar parâmetros baseados na configuração
                            if st.session_state.use_rating_percentages:
                                if hasattr(st.session_state, 'calculated_rating_limits') and sum(st.session_state.rating_percentages.values()) == 100:
                                    rating_limits = st.session_state.calculated_rating_limits
                                    active_ratings = [f"{r}⭐:{l}" for r, l in sorted(rating_limits.items(), reverse=True) if l > 0]
                                    total_configured = st.session_state.total_reviews_configured
                                    spinner_text = f"Buscando {total_configured} reviews por rating ({', '.join(active_ratings)}) para o produto ID: {product_id_field}..."
                                    
                                    with st.spinner(spinner_text):
                                        reviews_result = run_review_spider(product_id_field, rating_limits=rating_limits)
                                else:
                                    st.error("⚠️ Configure as porcentagens corretamente (devem somar 100%) antes de buscar reviews.")
                                    continue
                            else:
                                spinner_text = f"Buscando até {st.session_state.max_reviews_to_fetch} opiniões para o produto ID: {product_id_field}..."
                                
                                with st.spinner(spinner_text):
                                    reviews_result = run_review_spider(product_id_field, max_reviews=st.session_state.max_reviews_to_fetch)
                            
                            st.session_state.reviews_data = reviews_result
                            st.session_state.last_fetched_product_id_reviews = product_id_field
                            st.rerun() # Replace experimental_rerun with rerun
                    
                    with reviews_col2:
                        if st.session_state.use_rating_percentages:
                            if hasattr(st.session_state, 'total_reviews_configured'):
                                st.caption(f"🎯 Coleta por percentual: {st.session_state.total_reviews_configured} reviews")
                            else:
                                st.caption(f"🎯 Configure percentuais primeiro")
                        else:
                            st.caption(f"🔍 Coletará até {st.session_state.max_reviews_to_fetch} reviews")
                
                # Display reviews if they are for the current product and data exists
                if st.session_state.last_fetched_product_id_reviews == product_id_field and st.session_state.reviews_data:
                    reviews = st.session_state.reviews_data
                    reviews_count = len(reviews.get('reviews', []))
                    with st.expander(f"Opiniões Detalhadas do Produto ({reviews_count} reviews coletadas)", expanded=True):
                        # Cabeçalho com estatísticas
                        if st.session_state.use_rating_percentages:
                            # Mostrar estatísticas por rating
                            st.markdown("**📊 Coleta por Rating Configurada**")
                            
                            # Calcular estatísticas reais vs configuradas
                            actual_by_rating = {}
                            for review in reviews.get('reviews', []):
                                rating = int(review.get('rating', 0)) if review.get('rating', '0').isdigit() else 0
                                actual_by_rating[rating] = actual_by_rating.get(rating, 0) + 1
                            
                            # Mostrar comparação
                            comparison_cols = st.columns(5)
                            for i, rating in enumerate([5, 4, 3, 2, 1]):
                                with comparison_cols[i]:
                                    if hasattr(st.session_state, 'calculated_rating_limits'):
                                        configured = st.session_state.calculated_rating_limits.get(rating, 0)
                                        actual = actual_by_rating.get(rating, 0)
                                        percentage = st.session_state.rating_percentages.get(rating, 0)
                                        if configured > 0:
                                            efficiency = f"{(actual/configured*100):.0f}%" if configured > 0 else "0%"
                                            st.metric(f"{rating}⭐", f"{actual}/{configured}", delta=f"{percentage}%")
                                        else:
                                            st.metric(f"{rating}⭐", "0/0", delta=f"{percentage}%")
                                    else:
                                        st.metric(f"{rating}⭐", "N/A", delta="N/A")
                        else:
                            # Estatísticas gerais
                            stats_col1, stats_col2, stats_col3 = st.columns(3)
                            with stats_col1:
                                st.metric("Reviews Coletadas", reviews_count)
                            with stats_col2:
                                configured_limit = st.session_state.max_reviews_to_fetch
                                st.metric("Limite Configurado", configured_limit)
                            with stats_col3:
                                collection_rate = f"{(reviews_count / configured_limit * 100):.1f}%" if configured_limit > 0 else "0%"
                                st.metric("Taxa de Coleta", collection_rate)
                        
                        st.markdown("---")
                        st.write(f"**ID do Produto (Reviews):** {reviews.get('product_id')}")
                        st.write(f"**Avaliação Geral (Detalhada):** {reviews.get('overall_rating', 'N/A')} ⭐")
                        st.write(f"**Total de Avaliações (Detalhada):** {reviews.get('total_reviews_count', 'N/A')}")
                        
                        st.markdown("##### Avaliação por Características:")
                        if reviews.get('characteristics_ratings'):
                            for char_rating in reviews['characteristics_ratings']:
                                st.write(f"- {char_rating['characteristic_name']}: {char_rating['characteristic_rating']} / 5")
                        else:
                            st.write("Nenhuma avaliação por característica encontrada.")
                        
                        st.markdown("##### Comentários:")
                        if reviews.get('reviews'):
                            # Calcular estatísticas das reviews
                            ratings = [int(rev.get('rating', 0)) for rev in reviews['reviews'] if rev.get('rating', '0').isdigit()]
                            if ratings:
                                avg_rating = sum(ratings) / len(ratings)
                                rating_distribution = {i: ratings.count(i) for i in range(1, 6)}
                                
                                # Mostrar resumo estatístico
                                with st.container():
                                    st.markdown("**📊 Resumo das Avaliações Coletadas:**")
                                    summary_col1, summary_col2 = st.columns(2)
                                    
                                    with summary_col1:
                                        st.write(f"**Média das reviews:** {avg_rating:.1f} ⭐")
                                        st.write(f"**Total de comentários:** {len(reviews['reviews'])}")
                                    
                                    with summary_col2:
                                        st.write("**Distribuição de notas:**")
                                        for rating, count in sorted(rating_distribution.items(), reverse=True):
                                            percentage = (count / len(ratings)) * 100
                                            st.write(f"{rating}⭐: {count} ({percentage:.1f}%)")
                                    
                                    st.markdown("---")
                            
                            # Mostrar comentários individuais
                            for i, rev_item in enumerate(reviews['reviews']):
                                with st.container():
                                    comment_header_col1, comment_header_col2 = st.columns([3, 1])
                                    with comment_header_col1:
                                        st.markdown(f"**Review #{i+1} - Nota:** {rev_item.get('rating','N/A')} ⭐")
                                    with comment_header_col2:
                                        st.markdown(f"*{rev_item.get('date','N/A')}*")
                                    
                                    st.markdown(f"**Comentário:** {rev_item.get('text','N/A')}")
                                    st.markdown(f"**Útil:** {rev_item.get('helpful_count','0')} pessoas acharam útil")
                                    st.markdown("---")
                        else:
                            st.write("Nenhum comentário encontrado.")
                elif st.session_state.last_fetched_product_id_reviews == product_id_field and not st.session_state.reviews_data:
                     with st.expander("Opiniões Detalhadas do Produto", expanded=True):
                        st.warning("Não foi possível carregar as opiniões para este produto.")

            st.markdown("***") # Main Divisor between products
        
        # Opções para baixar os resultados como CSV
        if produtos:
            download_col1, download_col2 = st.columns(2)
            
            with download_col1:
                # CSV básico (dados da busca)
                df = pd.DataFrame(produtos)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV Básico",
                    data=csv,
                    file_name=f"produtos_mercadolivre_basico_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv",
                    help="Download dos dados básicos extraídos da busca"
                )
            
            with download_col2:
                # CSV configurável (se foi gerado)
                if 'csv_content' in st.session_state and st.session_state.csv_content:
                    st.download_button(
                        label="📊 Baixar CSV Configurado",
                        data=st.session_state.csv_content,
                        file_name=f"produtos_mercadolivre_detalhado_{search_query.replace(' ', '_')}.csv",
                        mime="text/csv",
                        help="Download do CSV com campos configurados e dados detalhados"
                    )
                else:
                    st.caption("Use 'Buscar e Gerar CSV' para criar um CSV configurável")

    elif 'search_results' in st.session_state: # Searched but no products found
        st.error("Nenhum produto encontrado para a busca realizada. Verifique os logs ou tente outros termos/filtros.")

# ==================== SEÇÃO DE DETECÇÃO DE FALSIFICAÇÃO ====================
if 'search_results' in st.session_state and st.session_state.search_results:
    st.markdown("---")
    st.header("🔍 Detector de Falsificações")
    st.markdown("Analise a probabilidade de falsificação dos produtos encontrados baseado em preços e reviews.")
    
    # Configurações da análise
    with st.expander("⚙️ Configurações da Análise", expanded=False):
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            analisar_reviews_checkbox = st.checkbox(
                "🔍 Analisar Reviews para Falsificação",
                value=True,
                help="Analisa os comentários dos produtos procurando por indicadores de falsificação"
            )
            
            if analisar_reviews_checkbox:
                max_reviews_falsificacao = st.slider(
                    "Máximo de reviews por produto",
                    min_value=20,
                    max_value=200,
                    value=50,
                    step=10,
                    help="Número máximo de reviews a analisar por produto"
                )
        
        with col_config2:
            st.markdown("**📊 Critérios de Análise:**")
            st.markdown("• **Preço:** Comparação com valores de referência HP")
            st.markdown("• **Reviews:** Busca por palavras-chave suspeitas")
            st.markdown("• **Classificação:** BAIXO/MÉDIO/ALTO RISCO")
            
            if analisar_reviews_checkbox:
                st.markdown("**🔍 Palavras-chave analisadas:**")
                st.caption("falsificado, fake, não original, durou pouco, não funciona, vazou, etc.")
    
    # Botão para iniciar análise
    if st.button("🚀 Analisar Probabilidade de Falsificação", type="primary"):
        produtos = st.session_state.search_results
        
        # Inicializar progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"Analisando produto {current}/{total}...")
        
        try:
            with st.spinner("Iniciando análise de falsificação..."):
                resultados_falsificacao = processar_deteccao_falsificacao(
                    produtos, 
                    analisar_reviews=analisar_reviews_checkbox,
                    progress_callback=update_progress
                )
                
                # Armazenar resultados
                st.session_state.resultados_falsificacao = resultados_falsificacao
                
                # Limpar progress
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"✅ Análise concluída! {len(resultados_falsificacao)} produtos analisados.")
                st.rerun()
                
        except Exception as e:
            st.error(f"Erro durante a análise: {str(e)}")
            logging.error(f"Erro na análise de falsificação: {str(e)}")
            progress_bar.empty()
            status_text.empty()

# Exibir resultados da análise de falsificação
if 'resultados_falsificacao' in st.session_state and st.session_state.resultados_falsificacao:
    st.markdown("---")
    st.subheader("📊 Resultados da Análise de Falsificação")
    
    resultados = st.session_state.resultados_falsificacao
    
    # Estatísticas gerais
    total_produtos = len(resultados)
    alto_risco = len([r for r in resultados if r['classificacao'] == 'ALTO RISCO'])
    medio_risco = len([r for r in resultados if r['classificacao'] == 'MÉDIO RISCO'])
    baixo_risco = len([r for r in resultados if r['classificacao'] == 'BAIXO RISCO'])
    
    # Métricas resumo
    col_metrics1, col_metrics2, col_metrics3, col_metrics4 = st.columns(4)
    
    with col_metrics1:
        st.metric("Total Analisados", total_produtos)
    
    with col_metrics2:
        st.metric("🔴 Alto Risco", alto_risco, delta=f"{(alto_risco/total_produtos*100):.1f}%")
    
    with col_metrics3:
        st.metric("🟡 Médio Risco", medio_risco, delta=f"{(medio_risco/total_produtos*100):.1f}%")
    
    with col_metrics4:
        st.metric("🟢 Baixo Risco", baixo_risco, delta=f"{(baixo_risco/total_produtos*100):.1f}%")
    
    # Filtros para visualização
    st.markdown("### 🔍 Filtrar Resultados")
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        filtro_risco = st.selectbox(
            "Filtrar por Classificação",
            options=["Todos", "ALTO RISCO", "MÉDIO RISCO", "BAIXO RISCO"],
            index=0
        )
    
    with col_filter2:
        ordenar_por = st.selectbox(
            "Ordenar por",
            options=["Probabilidade (Maior→Menor)", "Probabilidade (Menor→Maior)", "Preço (Menor→Maior)", "Preço (Maior→Menor)"],
            index=0
        )
    
    # Aplicar filtros
    resultados_filtrados = resultados.copy()
    
    if filtro_risco != "Todos":
        resultados_filtrados = [r for r in resultados_filtrados if r['classificacao'] == filtro_risco]
    
    # Aplicar ordenação
    if ordenar_por == "Probabilidade (Maior→Menor)":
        resultados_filtrados.sort(key=lambda x: x['probabilidade_total'], reverse=True)
    elif ordenar_por == "Probabilidade (Menor→Maior)":
        resultados_filtrados.sort(key=lambda x: x['probabilidade_total'])
    elif ordenar_por == "Preço (Menor→Maior)":
        resultados_filtrados.sort(key=lambda x: extrair_preco_numerico(x['produto'].get('PREÇO', '0')) or 0)
    elif ordenar_por == "Preço (Maior→Menor)":
        resultados_filtrados.sort(key=lambda x: extrair_preco_numerico(x['produto'].get('PREÇO', '0')) or 0, reverse=True)
    
    st.markdown(f"### 📋 Produtos Analisados ({len(resultados_filtrados)} de {total_produtos})")
    
    # Exibir resultados
    for i, resultado in enumerate(resultados_filtrados):
        produto = resultado['produto']
        
        # Determinar cor do risco
        if resultado['classificacao'] == 'ALTO RISCO':
            cor_risco = "🔴"
            cor_bg = "#ffebee"
        elif resultado['classificacao'] == 'MÉDIO RISCO':
            cor_risco = "🟡"
            cor_bg = "#fff8e1"
        else:
            cor_risco = "🟢"
            cor_bg = "#e8f5e8"
        
        with st.container():
            # Cabeçalho do produto com risco
            st.markdown(f"""
            <div style="background-color: {cor_bg}; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <h4>{cor_risco} {produto.get('TITULO PRODUTO', 'N/A')}</h4>
                <p><strong>Classificação:</strong> {resultado['classificacao']} | 
                   <strong>Probabilidade:</strong> {resultado['probabilidade_total']:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Detalhes da análise
            col_produto, col_analise = st.columns([1, 2])
            
            with col_produto:
                st.write(f"**Preço:** {produto.get('PREÇO', 'N/A')}")
                st.write(f"**Marca:** {produto.get('MARCA', 'N/A')}")
                st.write(f"**Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                
                if produto.get('LINK') and produto.get('LINK') != 'N/A':
                    st.markdown(f"[🔗 Ver no ML]({produto['LINK']})")
            
            with col_analise:
                # Análise de preço
                st.markdown("**💰 Análise de Preço:**")
                st.write(f"• Probabilidade: {resultado['probabilidade_preco']:.1f}%")
                st.write(f"• {resultado['motivo_preco']}")
                
                # Análise de reviews (se disponível)
                if resultado['probabilidade_reviews'] > 0:
                    st.markdown("**💬 Análise de Reviews:**")
                    st.write(f"• Probabilidade: {resultado['probabilidade_reviews']:.1f}%")
                    st.write(f"• {resultado['motivo_reviews']}")
                    
                    # Mostrar exemplos de reviews suspeitas
                    if resultado['detalhes_reviews']:
                        with st.expander("Ver exemplos de reviews suspeitas"):
                            for j, detalhe in enumerate(resultado['detalhes_reviews']):
                                st.write(f"**Review {j+1}** (⭐{detalhe['rating']}):")
                                st.write(f"• {detalhe['texto_trecho']}")
                                st.write(f"• {detalhe['ocorrencias']} ocorrência(s) suspeita(s)")
                                st.markdown("---")
                elif analisar_reviews_checkbox:
                    st.markdown("**💬 Análise de Reviews:**")
                    st.write(f"• {resultado['motivo_reviews']}")
            
            st.markdown("---")
    
    # Opção para baixar relatório
    if resultados_filtrados:
        st.markdown("### 📥 Download do Relatório")
        
        # Preparar dados para CSV
        dados_relatorio = []
        for resultado in resultados_filtrados:
            produto = resultado['produto']
            dados_relatorio.append({
                'Título': produto.get('TITULO PRODUTO', 'N/A'),
                'Preço': produto.get('PREÇO', 'N/A'),
                'Marca': produto.get('MARCA', 'N/A'),
                'Vendedor': produto.get('VENDEDOR', 'N/A'),
                'Link': produto.get('LINK', 'N/A'),
                'Classificação_Risco': resultado['classificacao'],
                'Probabilidade_Total': f"{resultado['probabilidade_total']:.1f}%",
                'Probabilidade_Preço': f"{resultado['probabilidade_preco']:.1f}%",
                'Motivo_Preço': resultado['motivo_preco'],
                'Probabilidade_Reviews': f"{resultado['probabilidade_reviews']:.1f}%",
                'Motivo_Reviews': resultado['motivo_reviews']
            })
        
        df_relatorio = pd.DataFrame(dados_relatorio)
        csv_relatorio = df_relatorio.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📊 Baixar Relatório de Falsificação (CSV)",
            data=csv_relatorio,
            file_name=f"relatorio_falsificacao_{search_query.replace(' ', '_')}.csv",
            mime="text/csv",
            help="Download do relatório completo de análise de falsificação"
        )

# Rodapé
st.markdown("---")
st.write("Criado para detecção de falsificações no Mercado Livre") 

# Configuração para execução adequada do multiprocessing com Streamlit
if __name__ == "__main__":
    # Esta seção garante que o multiprocessing funcione corretamente
    # quando o arquivo for executado diretamente
    pass
 
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
        if erro in titulo_upper:
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
    
    # 3. Análise de Preço
    score_preco, motivo_preco = calcular_score_preco_mercado(produto)
    detalhes_analise['score_preco'] = score_preco
    detalhes_analise['motivo_preco'] = motivo_preco
    
    score_total += score_preco
    if score_preco > 0:
        criterios_aplicados.append(f"⚠️ Preço suspeito (+{score_preco} pts)")
        criterios_aplicados.append(f"  • {motivo_preco}")
    else:
        criterios_aplicados.append("✅ Preço dentro do esperado")
    
    # 4. Determinar rótulo final
    if score_total >= 60:
        rotulo = "suspeito/pirata"
        confianca = "ALTA"
        cor_status = "🔴"
    elif score_total >= 30:
        rotulo = "suspeito/pirata"
        confianca = "MÉDIA"
        cor_status = "🟡"
    elif score_total >= 10:
        rotulo = "suspeito/pirata"
        confianca = "BAIXA"
        cor_status = "🟠"
    else:
        rotulo = "original"
        confianca = "ALTA" if score_total <= -10 else "MÉDIA"
        cor_status = "🟢"
    
    return {
        'rotulo': rotulo,
        'score_total': score_total,
        'confianca': confianca,
        'cor_status': cor_status,
        'criterios_aplicados': criterios_aplicados,
        'detalhes_analise': detalhes_analise
    }

def gerar_dataset_hp_challenge(produtos):
    """
    Gera dataset estruturado para o Challenge Sprint da HP
    com features relevantes e target de rótulo binário (original/pirata)
    """
    dataset = []
    
    for i, produto in enumerate(produtos):
        # Aplicar rotulagem heurística
        resultado_rotulagem = rotular_produto_heuristico(produto)
        
        # Extrair features relevantes
        features = {
            # Features básicas (dados coletados)
            'titulo_anuncio': produto.get('TITULO PRODUTO', 'N/A'),
            'preco': produto.get('PREÇO', 'N/A'),
            'preco_numerico': extrair_preco_numerico(produto.get('PREÇO', 'N/A')),
            'vendedor': produto.get('VENDEDOR', 'N/A'),
            'link_anuncio': produto.get('LINK', 'N/A'),
            'avaliacao_media': produto.get('MÉDIA AVALIAÇÕES', 'N/A'),
            'total_avaliacoes': produto.get('TOTAL AVALIAÇÕES', 'N/A'),
            'entrega_full': produto.get('ENTREGA FULL', 'Não'),
            'marca': produto.get('MARCA', 'N/A'),
            
            # Features derivadas (para ML)
            'vendedor_oficial': resultado_rotulagem['detalhes_analise']['vendedor_oficial'],
            'score_titulo_suspeito': resultado_rotulagem['detalhes_analise']['score_titulo'],
            'score_preco_suspeito': resultado_rotulagem['detalhes_analise']['score_preco'],
            'diferenca_preco_percentual': 0,  # Será calculado abaixo
            'tem_avaliacao': produto.get('MÉDIA AVALIAÇÕES', 'N/A') != 'N/A',
            'quantidade_avaliacoes': 0,  # Será calculado abaixo
            
            # Target (rótulo)
            'rotulo_binario': 1 if resultado_rotulagem['rotulo'] == 'suspeito/pirata' else 0,
            'rotulo_texto': resultado_rotulagem['rotulo'],
            'confianca_rotulo': resultado_rotulagem['confianca'],
            'score_total_suspeita': resultado_rotulagem['score_total']
        }
        
        # Calcular features adicionais
        modelo, tipo = identificar_modelo_cartucho(features['titulo_anuncio'])
        if modelo and features['preco_numerico']:
            preco_ref = PRECOS_REFERENCIA_HP.get(modelo, {}).get(tipo, 0)
            if preco_ref > 0:
                features['diferenca_preco_percentual'] = ((preco_ref - features['preco_numerico']) / preco_ref) * 100
        
        # Processar quantidade de avaliações
        total_aval = features['total_avaliacoes']
        if total_aval != 'N/A':
            try:
                # Remover parênteses e converter
                if isinstance(total_aval, str):
                    total_aval = total_aval.replace('(', '').replace(')', '').replace('k', '000')
                features['quantidade_avaliacoes'] = int(float(total_aval))
            except:
                features['quantidade_avaliacoes'] = 0
        
        dataset.append(features)
    
    return dataset

# ==================== SEÇÃO CHALLENGE SPRINT HP ====================
if 'search_results' in st.session_state and st.session_state.search_results:
    st.markdown("---")
    st.header("🏆 Challenge Sprint HP - Dataset Generator")
    st.markdown("**Entregável 1:** Coleta e Construção da Base de Dados com rotulagem heurística para identificação de produtos suspeitos/piratas.")
    
    produtos = st.session_state.search_results
    
    # Estatísticas do dataset
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        st.metric("Total de Produtos", len(produtos))
    
    with col_stats2:
        vendedores_oficiais = sum(1 for p in produtos if verificar_vendedor_oficial(p.get('VENDEDOR', '')))
        st.metric("Vendedores Oficiais", vendedores_oficiais, delta=f"{(vendedores_oficiais/len(produtos)*100):.1f}%")
    
    with col_stats3:
        produtos_hp = sum(1 for p in produtos if 'HP' in p.get('TITULO PRODUTO', '').upper())
        st.metric("Produtos HP", produtos_hp, delta=f"{(produtos_hp/len(produtos)*100):.1f}%")
    
    # Configurações da rotulagem
    with st.expander("⚙️ Configurações da Rotulagem Heurística", expanded=False):
        st.markdown("**Critérios aplicados automaticamente:**")
        
        col_criterios1, col_criterios2 = st.columns(2)
        
        with col_criterios1:
            st.markdown("**✅ Indicadores de Produto Original:**")
            st.markdown("• Vendedor na lista oficial HP")
            st.markdown("• Preço dentro da faixa normal")
            st.markdown("• Título sem palavras suspeitas")
            st.markdown("• Sem erros de gramática/ortografia")
        
        with col_criterios2:
            st.markdown("**⚠️ Indicadores de Produto Suspeito:**")
            st.markdown("• Vendedor não oficial/desconhecido")
            st.markdown("• Preço muito abaixo da referência")
            st.markdown("• Palavras suspeitas (réplica, cópia, etc.)")
            st.markdown("• Erros de grafia ou ênfase excessiva")
        
        st.markdown("---")
        st.markdown("**📋 Lista de Vendedores Oficiais HP:**")
        vendedores_lista = ', '.join(sorted(VENDEDORES_OFICIAIS_HP))
        st.caption(vendedores_lista)
    
    # Botão para gerar análise heurística
    if st.button("🔍 Aplicar Rotulagem Heurística", type="primary"):
        with st.spinner("Aplicando critérios heurísticos para rotulagem..."):
            # Gerar dataset com rotulagem
            dataset_hp = gerar_dataset_hp_challenge(produtos)
            st.session_state.dataset_hp_challenge = dataset_hp
            
            # Calcular estatísticas
            total_produtos = len(dataset_hp)
            produtos_originais = sum(1 for item in dataset_hp if item['rotulo_texto'] == 'original')
            produtos_suspeitos = sum(1 for item in dataset_hp if item['rotulo_texto'] == 'suspeito/pirata')
            
            st.success(f"✅ Rotulagem concluída! {total_produtos} produtos analisados.")
            st.rerun()

# Exibir resultados da rotulagem heurística
if 'dataset_hp_challenge' in st.session_state and st.session_state.dataset_hp_challenge:
    st.markdown("---")
    st.subheader("📊 Resultados da Rotulagem Heurística")
    
    dataset = st.session_state.dataset_hp_challenge
    
    # Estatísticas do dataset
    total_produtos = len(dataset)
    produtos_originais = sum(1 for item in dataset if item['rotulo_texto'] == 'original')
    produtos_suspeitos = sum(1 for item in dataset if item['rotulo_texto'] == 'suspeito/pirata')
    
    # Métricas do dataset
    col_dataset1, col_dataset2, col_dataset3, col_dataset4 = st.columns(4)
    
    with col_dataset1:
        st.metric("Total Analisados", total_produtos)
    
    with col_dataset2:
        st.metric("🟢 Originais", produtos_originais, delta=f"{(produtos_originais/total_produtos*100):.1f}%")
    
    with col_dataset3:
        st.metric("🔴 Suspeitos/Piratas", produtos_suspeitos, delta=f"{(produtos_suspeitos/total_produtos*100):.1f}%")
    
    with col_dataset4:
        score_medio = sum(item['score_total_suspeita'] for item in dataset) / total_produtos
        st.metric("Score Médio Suspeita", f"{score_medio:.1f}")
    
    # Filtros para visualização
    st.markdown("### 🔍 Visualizar Resultados")
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        filtro_rotulo = st.selectbox(
            "Filtrar por Rótulo",
            options=["Todos", "original", "suspeito/pirata"],
            index=0
        )
    
    with col_filter2:
        ordenar_dataset = st.selectbox(
            "Ordenar por",
            options=["Score Suspeita (Maior→Menor)", "Score Suspeita (Menor→Maior)", "Preço (Menor→Maior)", "Preço (Maior→Menor)"],
            index=0
        )
    
    # Aplicar filtros
    dataset_filtrado = dataset.copy()
    
    if filtro_rotulo != "Todos":
        dataset_filtrado = [item for item in dataset_filtrado if item['rotulo_texto'] == filtro_rotulo]
    
    # Aplicar ordenação
    if ordenar_dataset == "Score Suspeita (Maior→Menor)":
        dataset_filtrado.sort(key=lambda x: x['score_total_suspeita'], reverse=True)
    elif ordenar_dataset == "Score Suspeita (Menor→Maior)":
        dataset_filtrado.sort(key=lambda x: x['score_total_suspeita'])
    elif ordenar_dataset == "Preço (Menor→Maior)":
        dataset_filtrado.sort(key=lambda x: x['preco_numerico'] or 0)
    elif ordenar_dataset == "Preço (Maior→Menor)":
        dataset_filtrado.sort(key=lambda x: x['preco_numerico'] or 0, reverse=True)
    
    st.markdown(f"### 📋 Dataset Rotulado ({len(dataset_filtrado)} de {total_produtos})")
    
    # Exibir amostras do dataset
    for i, item in enumerate(dataset_filtrado[:10]):  # Mostrar até 10 itens
        # Determinar cor do rótulo
        if item['rotulo_texto'] == 'original':
            cor_rotulo = "🟢"
            cor_bg = "#e8f5e8"
        else:
            cor_rotulo = "🔴"
            cor_bg = "#ffebee"
        
        with st.container():
            # Cabeçalho do item
            st.markdown(f"""
            <div style="background-color: {cor_bg}; padding: 10px; border-radius: 5px; margin: 10px 0;">
                <h4>{cor_rotulo} {item['titulo_anuncio']}</h4>
                <p><strong>Rótulo:</strong> {item['rotulo_texto']} | 
                   <strong>Confiança:</strong> {item['confianca_rotulo']} | 
                   <strong>Score:</strong> {item['score_total_suspeita']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Detalhes do item
            col_item1, col_item2 = st.columns([1, 2])
            
            with col_item1:
                st.write(f"**Preço:** {item['preco']}")
                st.write(f"**Vendedor:** {item['vendedor']}")
                st.write(f"**Vendedor Oficial:** {'✅ Sim' if item['vendedor_oficial'] else '❌ Não'}")
                st.write(f"**Avaliação:** {item['avaliacao_media']}")
                
                if item['link_anuncio'] and item['link_anuncio'] != 'N/A':
                    st.markdown(f"[🔗 Ver Anúncio]({item['link_anuncio']})")
            
            with col_item2:
                # Aplicar rotulagem individual para mostrar critérios
                resultado_individual = rotular_produto_heuristico({
                    'TITULO PRODUTO': item['titulo_anuncio'],
                    'PREÇO': item['preco'],
                    'VENDEDOR': item['vendedor']
                })
                
                st.markdown("**🔍 Critérios Aplicados:**")
                for criterio in resultado_individual['criterios_aplicados']:
                    st.write(f"• {criterio}")
            
            st.markdown("---")
    
    if len(dataset_filtrado) > 10:
        st.info(f"Mostrando 10 de {len(dataset_filtrado)} itens. Use os filtros para refinar a visualização.")
    
    # Seção de download do dataset
    st.markdown("### 📥 Download do Dataset")
    
    col_download1, col_download2 = st.columns(2)
    
    with col_download1:
        # Dataset completo
        df_dataset = pd.DataFrame(dataset)
        csv_dataset = df_dataset.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📊 Baixar Dataset Completo (CSV)",
            data=csv_dataset,
            file_name=f"dataset_hp_challenge_{search_query.replace(' ', '_')}.csv",
            mime="text/csv",
            help="Dataset estruturado com features relevantes e rótulos binários (original/pirata)"
        )
    
    with col_download2:
        # Apenas features para ML
        features_ml = []
        for item in dataset:
            features_ml.append({
                'preco_numerico': item['preco_numerico'],
                'vendedor_oficial': int(item['vendedor_oficial']),
                'score_titulo_suspeito': item['score_titulo_suspeito'],
                'score_preco_suspeito': item['score_preco_suspeito'],
                'diferenca_preco_percentual': item['diferenca_preco_percentual'],
                'tem_avaliacao': int(item['tem_avaliacao']),
                'quantidade_avaliacoes': item['quantidade_avaliacoes'],
                'entrega_full': 1 if item['entrega_full'] == 'Sim' else 0,
                'rotulo_binario': item['rotulo_binario']  # Target
            })
        
        df_ml = pd.DataFrame(features_ml)
        csv_ml = df_ml.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="🤖 Baixar Features ML (CSV)",
            data=csv_ml,
            file_name=f"features_ml_hp_{search_query.replace(' ', '_')}.csv",
            mime="text/csv",
            help="Features numéricas preparadas para Machine Learning"
        )
    
    # Exemplos de amostras para documentação
    st.markdown("### 📋 Exemplos de Amostras (para Documentação)")
    st.markdown("**5 exemplos representativos do dataset:**")
    
    # Selecionar exemplos diversos
    exemplos = []
    
    # 2 originais com alta confiança
    originais_alta = [item for item in dataset if item['rotulo_texto'] == 'original' and item['confianca_rotulo'] == 'ALTA']
    if originais_alta:
        exemplos.extend(originais_alta[:2])
    
    # 2 suspeitos com alta confiança
    suspeitos_alta = [item for item in dataset if item['rotulo_texto'] == 'suspeito/pirata' and item['confianca_rotulo'] == 'ALTA']
    if suspeitos_alta:
        exemplos.extend(suspeitos_alta[:2])
    
    # 1 caso limítrofe
    limitrofes = [item for item in dataset if item['confianca_rotulo'] in ['MÉDIA', 'BAIXA']]
    if limitrofes:
        exemplos.append(limitrofes[0])
    
    # Preencher com outros se necessário
    while len(exemplos) < 5 and len(exemplos) < len(dataset):
        for item in dataset:
            if item not in exemplos:
                exemplos.append(item)
                break
    
    for i, exemplo in enumerate(exemplos[:5]):
        st.markdown(f"**Exemplo {i+1}:**")
        st.json({
            'titulo_anuncio': exemplo['titulo_anuncio'],
            'preco': exemplo['preco'],
            'vendedor': exemplo['vendedor'],
            'vendedor_oficial': exemplo['vendedor_oficial'],
            'rotulo_texto': exemplo['rotulo_texto'],
            'rotulo_binario': exemplo['rotulo_binario'],
            'score_total_suspeita': exemplo['score_total_suspeita'],
            'confianca_rotulo': exemplo['confianca_rotulo']
        })
        st.markdown("---")
 