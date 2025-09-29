#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Scraping HP - Flask Web Application
Funcionalidades: API REST + Interface Web para Scraping e Geração de Dataset
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import pandas as pd
import logging
import time
import json
import os
import io
from datetime import datetime
import threading
from werkzeug.utils import secure_filename
import uuid

# Importar o sistema de scraping existente
from ..core import get_scraping_system

# Diretório para logs - caminho absoluto baseado na raiz do projeto
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_FOLDER = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOGS_FOLDER, exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_FOLDER, 'flask_scraper.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)
app.secret_key = 'hp_challenge_scraping_system_2024'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Diretório para arquivos gerados
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'datasets_gerados')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Criar diretório se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Log do caminho para debug
logger.info(f"Diretório de datasets configurado: {UPLOAD_FOLDER}")

# Sistema de scraping global
HPScrapingSystem = get_scraping_system()
scraping_system = HPScrapingSystem()

# Armazenar jobs de scraping em andamento
active_jobs = {}

class ScrapingJob:
    """Classe para gerenciar jobs de scraping em background"""
    
    def __init__(self, job_id, query, parameters):
        self.job_id = job_id
        self.query = query
        self.parameters = parameters
        self.status = 'iniciado'
        self.progress = 0
        self.produtos_coletados = 0
        self.reviews_coletadas = 0
        self.start_time = datetime.now()
        self.end_time = None
        self.error_message = None
        self.result_files = []
        HPScrapingSystem = get_scraping_system()
        self.sistema = HPScrapingSystem()
    
    def run(self):
        """Executa o job de scraping"""
        try:
            self.status = 'coletando_produtos'
            logger.info(f"Job {self.job_id}: Iniciando coleta de produtos")
            
            # Executar scraping de produtos
            produtos = self.sistema.executar_scraping_produtos(
                query=self.parameters.get('query'),
                max_items=self.parameters.get('max_items'),
                extract_images=self.parameters.get('extract_images', False),
                sort_by=self.parameters.get('sort_by', 'relevance'),
                condition=self.parameters.get('condition', 'all'),
                custom_url=self.parameters.get('custom_url'),
                detailed_extraction=self.parameters.get('detailed_extraction', False),
                request_delay=self.parameters.get('request_delay', 2.0)
            )
            
            if not produtos:
                self.status = 'erro'
                self.error_message = 'Nenhum produto foi coletado'
                return
            
            self.produtos_coletados = len(produtos)
            self.progress = 50
            
            # Coletar reviews se solicitado
            if self.parameters.get('collect_reviews', False):
                self.status = 'coletando_reviews'
                logger.info(f"Job {self.job_id}: Coletando reviews")
                
                self.sistema.coletar_reviews_para_produtos(
                    self.parameters.get('max_reviews_per_product', 100),
                    self.parameters.get('request_delay', 2.0)
                )
                
                # Contar reviews coletadas
                self.reviews_coletadas = sum(
                    len(p.get('reviews_data', {}).get('reviews', [])) 
                    for p in self.sistema.produtos
                )
            
            self.progress = 80
            self.status = 'gerando_datasets'
            logger.info(f"Job {self.job_id}: Gerando datasets")
            
            # Gerar datasets
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # CSV
            csv_filename = f"dataset_{self.job_id}_{timestamp}.csv"
            csv_path = os.path.join(UPLOAD_FOLDER, csv_filename)
            csv_file = self.sistema.gerar_dataset_csv(
                csv_path, 
                include_reviews=self.parameters.get('collect_reviews', False),
                individual_reviews=self.parameters.get('individual_reviews', False)
            )
            
            if csv_file:
                self.result_files.append({
                    'type': 'csv',
                    'filename': csv_filename,
                    'path': csv_file,
                    'size': os.path.getsize(csv_file)
                })
                logger.info(f"Job {self.job_id}: Arquivo CSV gerado - {csv_filename}")
            else:
                logger.warning(f"Job {self.job_id}: Falha ao gerar arquivo CSV")
            
            # JSON - SEMPRE gerar
            json_filename = f"dataset_{self.job_id}_{timestamp}.json"
            json_path = os.path.join(UPLOAD_FOLDER, json_filename)
            json_file = self.sistema.gerar_dataset_json(json_path)
            
            if json_file:
                self.result_files.append({
                    'type': 'json',
                    'filename': json_filename,
                    'path': json_file,
                    'size': os.path.getsize(json_file)
                })
                logger.info(f"Job {self.job_id}: Arquivo JSON gerado - {json_filename}")
            else:
                logger.warning(f"Job {self.job_id}: Falha ao gerar arquivo JSON")
            
            # Excel - se solicitado
            if self.parameters.get('generate_excel', False):
                excel_filename = f"dataset_{self.job_id}_{timestamp}.xlsx"
                excel_path = os.path.join(UPLOAD_FOLDER, excel_filename)
                
                try:
                    # Gerar Excel usando o método do sistema
                    excel_file = self.sistema.gerar_dataset_excel(
                        excel_path,
                        include_reviews=self.parameters.get('collect_reviews', False),
                        individual_reviews=self.parameters.get('individual_reviews', False)
                    )
                    
                    if excel_file:
                        self.result_files.append({
                            'type': 'excel',
                            'filename': excel_filename,
                            'path': excel_file,
                            'size': os.path.getsize(excel_file)
                        })
                        logger.info(f"Job {self.job_id}: Arquivo Excel gerado - {excel_filename}")
                    else:
                        logger.warning(f"Job {self.job_id}: Falha ao gerar arquivo Excel")
                except Exception as e:
                    logger.warning(f"Job {self.job_id}: Erro ao gerar Excel: {e}")
            
            self.progress = 100
            self.status = 'concluido'
            self.end_time = datetime.now()
            
            # Log resumo completo
            logger.info(f"Job {self.job_id}: Concluído com sucesso")
            logger.info(f"   - Produtos coletados: {self.produtos_coletados}")
            logger.info(f"   - Reviews coletadas: {self.reviews_coletadas}")
            logger.info(f"   - Arquivos gerados: {len(self.result_files)}")
            for file_info in self.result_files:
                size_kb = file_info['size'] / 1024
                logger.info(f"     * {file_info['type'].upper()}: {file_info['filename']} ({size_kb:.1f} KB)")
            
        except Exception as e:
            self.status = 'erro'
            self.error_message = str(e)
            self.end_time = datetime.now()
            logger.error(f"Job {self.job_id}: Erro - {str(e)}")

# =============================================================================
# ROTAS DA INTERFACE WEB
# =============================================================================

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/scraping')
def scraping_page():
    """Página de scraping"""
    return render_template('scraping.html')

@app.route('/jobs')
def jobs_page():
    """Página de jobs"""
    return render_template('jobs.html', jobs=active_jobs)

@app.route('/datasets')
def datasets_page():
    """Página de datasets"""
    # Listar arquivos na pasta de datasets
    datasets = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                datasets.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath))
                })
    
    return render_template('datasets.html', datasets=datasets)

# =============================================================================
# API REST ENDPOINTS
# =============================================================================

@app.route('/api/scraping/start', methods=['POST'])
def api_start_scraping():
    """Inicia um job de scraping"""
    try:
        data = request.get_json()
        
        # Validar parâmetros obrigatórios
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Parâmetro "query" é obrigatório'
            }), 400
        
        # Gerar ID único para o job
        job_id = str(uuid.uuid4())[:8]
        
        # Parâmetros do job - expandidos com novas opções
        parameters = {
            'query': data['query'],
            'max_items': data.get('max_items', 50),
            'extract_images': data.get('extract_images', False),
            'sort_by': data.get('sort_by', 'relevance'),
            'condition': data.get('condition', 'all'),
            'collect_reviews': data.get('collect_reviews', False),
            'max_reviews_per_product': data.get('max_reviews_per_product', 100),
            'generate_json': data.get('generate_json', False),
            'generate_csv': data.get('generate_csv', True),
            'generate_excel': data.get('generate_excel', False),
            'detailed_extraction': data.get('detailed_extraction', False),
            
            # Novos parâmetros de filtros
            'min_price': data.get('min_price'),
            'max_price': data.get('max_price'),
            'min_seller_rating': data.get('min_seller_rating'),
            'min_seller_sales': data.get('min_seller_sales'),
            'power_seller_only': data.get('power_seller_only', False),
            'min_product_rating': data.get('min_product_rating'),
            'min_reviews_count': data.get('min_reviews_count'),
            'free_shipping_only': data.get('free_shipping_only', False),
            
            # Parâmetros de modo
            'scraping_mode': data.get('scraping_mode', 'standard')
        }
        
        # Criar job
        job = ScrapingJob(job_id, data['query'], parameters)
        active_jobs[job_id] = job
        
        # Executar job em background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()
        
        logger.info(f"Job {job_id} iniciado para query: {data['query']}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job de scraping iniciado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao iniciar scraping: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/jobs/<job_id>/status', methods=['GET'])
def api_job_status(job_id):
    """Obtém status de um job"""
    if job_id not in active_jobs:
        return jsonify({
            'success': False,
            'error': 'Job não encontrado'
        }), 404
    
    job = active_jobs[job_id]
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'query': job.query,
        'produtos_coletados': job.produtos_coletados,
        'reviews_coletadas': job.reviews_coletadas,
        'start_time': job.start_time.isoformat() if job.start_time else None,
        'end_time': job.end_time.isoformat() if job.end_time else None,
        'error_message': job.error_message,
        'result_files': job.result_files
    })

@app.route('/api/jobs', methods=['GET'])
def api_list_jobs():
    """Lista todos os jobs"""
    jobs_list = []
    for job_id, job in active_jobs.items():
        jobs_list.append({
            'job_id': job_id,
            'status': job.status,
            'progress': job.progress,
            'query': job.query,
            'produtos_coletados': job.produtos_coletados,
            'reviews_coletadas': job.reviews_coletadas,
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'end_time': job.end_time.isoformat() if job.end_time else None
        })
    
    return jsonify({
        'success': True,
        'jobs': jobs_list
    })

@app.route('/api/datasets', methods=['GET'])
def api_list_datasets():
    """Lista datasets disponíveis"""
    datasets = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                datasets.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    'type': filename.split('.')[-1].upper()
                })
    
    return jsonify({
        'success': True,
        'datasets': datasets
    })

@app.route('/api/datasets/<filename>/download', methods=['GET'])
def api_download_dataset(filename):
    """Download de dataset"""
    # Validar nome do arquivo
    safe_filename = secure_filename(filename)
    filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
    
    logger.info(f"Tentando download de: {safe_filename}")
    logger.info(f"Caminho completo: {filepath}")
    logger.info(f"Arquivo existe: {os.path.exists(filepath)}")
    
    if not os.path.exists(filepath):
        # Listar arquivos disponíveis para debug
        available_files = []
        if os.path.exists(UPLOAD_FOLDER):
            available_files = os.listdir(UPLOAD_FOLDER)
        
        logger.warning(f"Arquivo não encontrado: {filepath}")
        logger.warning(f"Arquivos disponíveis: {available_files}")
        
        return jsonify({
            'success': False,
            'error': 'Arquivo não encontrado',
            'filepath': filepath,
            'available_files': available_files
        }), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=safe_filename
    )

@app.route('/api/scraping/simple', methods=['POST'])
def api_simple_scraping():
    """Scraping simples síncrono (para testes rápidos)"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Parâmetro "query" é obrigatório'
            }), 400
        
        # Limitar a 10 itens para scraping simples
        max_items = min(data.get('max_items', 5), 10)
        
        HPScrapingSystem = get_scraping_system()
        sistema = HPScrapingSystem()
        produtos = sistema.executar_scraping_produtos(
            query=data['query'],
            max_items=max_items,
            extract_images=False,
            sort_by=data.get('sort_by', 'relevance'),
            condition=data.get('condition', 'all'),
            custom_url=data.get('custom_url')
        )
        
        if not produtos:
            return jsonify({
                'success': False,
                'error': 'Nenhum produto encontrado'
            })
        
        return jsonify({
            'success': True,
            'total_produtos': len(produtos),
            'produtos': produtos[:5]  # Retornar apenas os primeiros 5
        })
        
    except Exception as e:
        logger.error(f"Erro no scraping simples: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# ROTAS DE FORMULÁRIO WEB
# =============================================================================

@app.route('/web/scraping/start', methods=['POST'])
def web_start_scraping():
    """Inicia scraping via formulário web"""
    try:
        query = request.form.get('query')
        if not query:
            flash('Query é obrigatória', 'error')
            return redirect(url_for('scraping_page'))
        
        # Gerar ID único para o job
        job_id = str(uuid.uuid4())[:8]
        
        # Parâmetros do job - expandidos com novas opções
        parameters = {
            'query': query,
            'max_items': int(request.form.get('max_items', 50)),
            'extract_images': 'extract_images' in request.form,
            'sort_by': request.form.get('sort_by', 'relevance'),
            'condition': request.form.get('condition', 'all'),
            'collect_reviews': 'collect_reviews' in request.form,
            'max_reviews_per_product': int(request.form.get('max_reviews_per_product', 100)),
            'individual_reviews': 'individual_reviews' in request.form,
            'request_delay': float(request.form.get('request_delay', 2.0)),
            'generate_json': 'generate_json' in request.form,
            'generate_csv': 'generate_csv' in request.form,
            'generate_excel': 'generate_excel' in request.form,
            'detailed_extraction': 'detailed_extraction' in request.form,
            
            # Novos parâmetros de filtros
            'min_price': request.form.get('min_price'),
            'max_price': request.form.get('max_price'),
            'min_seller_rating': request.form.get('min_seller_rating'),
            'min_seller_sales': request.form.get('min_seller_sales'),
            'power_seller_only': 'power_seller_only' in request.form,
            'min_product_rating': request.form.get('min_product_rating'),
            'min_reviews_count': request.form.get('min_reviews_count'),
            'free_shipping_only': 'free_shipping_only' in request.form,
            
            # Parâmetros de modo
            'scraping_mode': request.form.get('scraping_mode', 'standard')
        }
        
        # Converter valores numéricos
        if parameters['min_price']:
            parameters['min_price'] = float(parameters['min_price'])
        if parameters['max_price']:
            parameters['max_price'] = float(parameters['max_price'])
        if parameters['min_seller_rating']:
            parameters['min_seller_rating'] = float(parameters['min_seller_rating'])
        if parameters['min_seller_sales']:
            parameters['min_seller_sales'] = int(parameters['min_seller_sales'])
        if parameters['min_product_rating']:
            parameters['min_product_rating'] = float(parameters['min_product_rating'])
        if parameters['min_reviews_count']:
            parameters['min_reviews_count'] = int(parameters['min_reviews_count'])
        
        # Criar job
        job = ScrapingJob(job_id, query, parameters)
        active_jobs[job_id] = job
        
        # Executar job em background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()
        
        flash(f'Job {job_id} iniciado com sucesso!', 'success')
        return redirect(url_for('jobs_page'))
        
    except Exception as e:
        flash(f'Erro ao iniciar scraping: {str(e)}', 'error')
        return redirect(url_for('scraping_page'))

# =============================================================================
# FILTROS DE TEMPLATE
# =============================================================================

@app.template_filter('filesizeformat')
def filesizeformat(bytes_size):
    """Formatar tamanho de arquivo"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

@app.template_filter('timeago')
def timeago(dt):
    """Formatar tempo relativo"""
    if not dt:
        return 'N/A'
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} dias atrás"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} horas atrás"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutos atrás"
    else:
        return "Agora mesmo"

# =============================================================================
# EXECUTAR APLICAÇÃO
# =============================================================================

if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask - Sistema de Scraping HP")
    app.run(debug=True, host='0.0.0.0', port=5000)
