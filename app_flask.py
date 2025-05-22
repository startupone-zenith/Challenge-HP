from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session
import pandas as pd
import requests
import logging
import time
import random
import re
import traceback
import base64
import io
from PIL import Image
from urllib.parse import quote_plus
import multiprocessing
import os
import json
from datetime import datetime
import tempfile

# Importar o spider do Scrapy
from mercadolivre_spider import run_spider
# Importar o novo spider de reviews
from mercadolivre_spider_reviews import run_spider_reviews

# Configuração do logger
logging.basicConfig(filename='scraper_errors.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Lista de User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

app = Flask(__name__)
app.secret_key = 'mercadolivre_detector_falsificacoes'  # Chave para session (mantenha segura em produção)

# Necessário criar a pasta para armazenar imagens baixadas temporariamente
if not os.path.exists('static/temp_images'):
    os.makedirs('static/temp_images')

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

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para busca de produtos
@app.route('/buscar_produtos', methods=['POST'])
def buscar_produtos():
    search_query = request.form.get('search_query', '')
    sort_by_value = request.form.get('sort_by', 'relevance')
    condition_value = request.form.get('condition', 'all')
    max_items = int(request.form.get('max_items', 100))
    load_images = 'load_images' in request.form  # Checkbox

    if not search_query:
        return render_template('index.html', error="Por favor, digite um termo de busca para continuar.")

    try:
        logging.info(f"Iniciando busca com Scrapy para: {search_query}, Sort: {sort_by_value}, Condition: {condition_value}, Max items: {max_items}")
        produtos, urls_usadas = run_spider(search_query, 
                                            extract_images=load_images, 
                                            sort_by=sort_by_value, 
                                            condition=condition_value,
                                            max_items=max_items)
        logging.info(f"Busca concluída. Produtos: {len(produtos)}, URLs: {urls_usadas}")
        
        # Processar e salvar imagens localmente se necessário
        if load_images:
            for i, produto in enumerate(produtos):
                if produto.get('IMAGEM') and produto.get('IMAGEM') not in ['N/A', 'N/A (imagens desabilitadas)']:
                    try:
                        img_response = make_request(produto['IMAGEM'])
                        if img_response:
                            img = Image.open(io.BytesIO(img_response.content))
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            img_filename = f"static/temp_images/produto_{i}_{timestamp}.jpg"
                            img.save(img_filename)
                            produto['IMAGEM_LOCAL'] = img_filename
                        else:
                            produto['IMAGEM_LOCAL'] = None
                    except Exception as e:
                        produto['IMAGEM_LOCAL'] = None
                        logging.error(f"Erro ao processar imagem {produto['IMAGEM']}: {str(e)}")
                else:
                    produto['IMAGEM_LOCAL'] = None

        # Salvar resultados na sessão para poder baixar como CSV depois
        if produtos:
            # Converter para formato serializável se necessário
            session['produtos'] = produtos
            session['urls_usadas'] = urls_usadas
            
            return render_template('resultados.html', 
                                  produtos=produtos, 
                                  urls_usadas=urls_usadas, 
                                  load_images=load_images,
                                  count=len(produtos),
                                  search_query=search_query)
        else:
            return render_template('index.html', 
                                  error="Nenhum produto encontrado. Verifique os logs ou tente outra busca.",
                                  search_query=search_query)
    
    except Exception as e:
        error_msg = f"Ocorreu um erro na busca: {str(e)}"
        logging.error(f"Erro na busca de produtos (app_flask.py): {str(e)}")
        logging.error(traceback.format_exc())
        return render_template('index.html', error=error_msg, search_query=search_query)

# Rota para download de CSV
@app.route('/download_csv')
def download_csv():
    if 'produtos' in session and session['produtos']:
        df = pd.DataFrame(session['produtos'])
        # Remover colunas que não queremos no CSV (como caminhos locais de imagens)
        if 'IMAGEM_LOCAL' in df.columns:
            df = df.drop('IMAGEM_LOCAL', axis=1)
            
        csv_data = df.to_csv(index=False).encode('utf-8')
        output = io.BytesIO(csv_data)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name='produtos_mercadolivre.csv',
            mimetype='text/csv'
        )
    else:
        return redirect(url_for('index'))

def limpar_csvs_antigos():
    temp_dir = 'static/temp_csvs'
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    for f in os.listdir(temp_dir):
        if f.endswith('.csv'):
            try:
                os.remove(os.path.join(temp_dir, f))
            except Exception as e:
                logging.warning(f'Não foi possível remover {f}: {e}')

# Rota para busca de avaliações (reviews)
@app.route('/buscar_reviews', methods=['POST'])
def buscar_reviews():
    review_url = request.form.get('review_url', '')
    if not review_url or not review_url.startswith('http'):
        return render_template('index.html', error_reviews="URL inválida. Forneça uma URL válida do Mercado Livre.")
    try:
        logging.info(f"Iniciando busca de reviews para a URL: {review_url}")
        reviews_data = run_spider_reviews(review_url)
        logging.info(f"Busca de reviews concluída. Encontradas {len(reviews_data)} avaliações.")
        if reviews_data:
            limpar_csvs_antigos()
            temp_dir = 'static/temp_csvs'
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            timestamp = int(time.time())
            csv_path = os.path.join(temp_dir, f'reviews_{timestamp}.csv')
            df = pd.DataFrame(reviews_data)
            df.to_csv(csv_path, index=False)
            # Salvar apenas o caminho do arquivo na sessão
            session['reviews_csv_path'] = csv_path
            return render_template('reviews.html', 
                                  reviews=reviews_data, 
                                  count=len(reviews_data),
                                  review_url=review_url)
        else:
            return render_template('index.html', 
                                  error_reviews="Nenhuma avaliação encontrada para esta URL.",
                                  review_url=review_url)
    except Exception as e:
        error_msg = f"Ocorreu um erro ao buscar as avaliações: {str(e)}"
        logging.error(f"Erro na busca de reviews (app_flask.py): {str(e)}")
        logging.error(traceback.format_exc())
        return render_template('index.html', error_reviews=error_msg, review_url=review_url)

# Rota para download de CSV de reviews
@app.route('/download_reviews_csv')
def download_reviews_csv():
    csv_path = session.get('reviews_csv_path')
    if csv_path and os.path.exists(csv_path):
        return send_file(
            csv_path,
            as_attachment=True,
            download_name='reviews_mercadolivre.csv',
            mimetype='text/csv'
        )
    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Necessário para multiprocessing no Windows
    multiprocessing.freeze_support()
    # Iniciar o servidor Flask
    app.run(debug=True) 