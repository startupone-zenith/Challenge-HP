#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Spider para extração de reviews do MercadoLivre
Implementa extração dinâmica com paginação automática e cancelamento imediato
"""

import requests
import time
import random
import json
from typing import Dict, List, Optional
import logging

def extract_reviews(product_id: str, max_reviews: int = 300, delay: float = 2.0):
    """
    Extrai reviews de um produto do MercadoLivre com paginação dinâmica
    
    Args:
        product_id (str): ID do produto (ex: MLB6125886)
        max_reviews (int): Número máximo de reviews para coletar
        delay (float): Delay entre requisições em segundos
    
    Returns:
        dict: Dados das reviews extraídas
    """
    if not product_id or product_id == 'N/A':
        print("ID do produto inválido ou não fornecido")
        return None
    
    base_url = "https://www.mercadolivre.com.br/noindex/catalog/reviews"
    limit = 30  # Limite da API
    all_reviews = []
    offset = 0
    page = 1
    consecutive_empty_pages = 0  # Contador de páginas vazias consecutivas
    max_empty_pages = 3  # Máximo de páginas vazias antes de parar
    max_pages = 20  # Máximo de páginas para evitar loop infinito
    
    # Headers para simular navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': f'https://www.mercadolivre.com.br/produto/{product_id}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }
    
    print(f"Iniciando extração dinâmica de reviews para {product_id}")
    print(f"Meta: {max_reviews} reviews, Delay: {delay}s")
    
    while len(all_reviews) < max_reviews and page <= max_pages:
        # Calcular quantas reviews ainda precisamos
        remaining_reviews = max_reviews - len(all_reviews)
        current_limit = min(limit, remaining_reviews)
        
        url = f"{base_url}/{product_id}/search"
        params = {
            'objectId': product_id,
            'offset': offset,
            'limit': current_limit
        }
        
        try:
            print(f"Página {page}: offset={offset}, limit={current_limit}, coletadas={len(all_reviews)}/{max_reviews}")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            
            # Se erro 404 ou 400, produto não existe ou ID inválido - parar imediatamente
            if response.status_code in [404, 400]:
                print(f"Produto não encontrado ou ID inválido ({response.status_code}). Parando imediatamente.")
                break
            
            response.raise_for_status()
            
            # Verificar se a resposta é um JSON válido
            try:
                data = response.json()
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Resposta não é um JSON válido: {e}. Produto sem reviews. Parando imediatamente.")
                break
            
            # Verificar se a resposta contém dados válidos
            if not isinstance(data, dict):
                print(f"Resposta não é um dicionário válido. Produto sem reviews. Parando imediatamente.")
                break
            
            # Verificar se a resposta contém o campo 'reviews'
            if 'reviews' not in data:
                print("Resposta não contém campo 'reviews'. Produto sem reviews. Parando imediatamente.")
                break
            
            reviews = data.get('reviews', [])
            if not reviews:
                # Se é a primeira página e está vazia, parar imediatamente (otimização)
                if page == 1:
                    print("Primeira página vazia - produto não possui reviews. Parando imediatamente.")
                    break
                
                # Para outras páginas, contar páginas vazias consecutivas
                consecutive_empty_pages += 1
                print(f"Nenhuma review encontrada na página {page}. Páginas vazias consecutivas: {consecutive_empty_pages}")
                
                # Se atingiu o limite de páginas vazias consecutivas, parar
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"Limite de {max_empty_pages} páginas vazias consecutivas atingido. Parando.")
                    break
                
                # Continuar para próxima página se não é a primeira
                offset += limit
                page += 1
                continue
            else:
                # Reset contador se encontrou reviews
                consecutive_empty_pages = 0
            
            # Processar reviews
            reviews_added = 0
            for review in reviews:
                if len(all_reviews) >= max_reviews:
                    break
                    
                processed_review = process_single_review(review, product_id)
                if processed_review:
                    all_reviews.append(processed_review)
                    reviews_added += 1
            
            print(f"  -> {reviews_added} reviews processadas (total: {len(all_reviews)})")
            
            # Se não conseguimos mais reviews ou atingimos o limite, parar
            if len(reviews) < current_limit or len(all_reviews) >= max_reviews:
                print(f"Limite atingido ou fim das reviews. Parando.")
                break
                
            # Atualizar offset para próxima página
            offset += limit
            page += 1
            
            # Delay mínimo apenas para evitar sobrecarga (sem delay configurado pelo usuário)
            if len(all_reviews) < max_reviews:  # Só fazer delay se ainda precisamos de mais reviews
                # Delay mínimo de 0.1s para evitar sobrecarga, sem usar o delay configurado
                minimal_delay = random.uniform(0.1, 0.3)  # Entre 0.1s e 0.3s
                print(f"  -> Aguardando {minimal_delay:.1f}s antes da proxima requisicao...")
                time.sleep(minimal_delay)
                    
        except Exception as e:
            print(f"Erro na página {page}: {e}")
            print("Tentando continuar com delay maior...")
            time.sleep(delay * 2)  # Delay maior em caso de erro
            offset += limit
            page += 1
    
    # Verificações finais para evitar loops infinitos
    if page > max_pages:
        print(f"Limite máximo de {max_pages} páginas atingido. Parando.")
    
    if consecutive_empty_pages >= max_empty_pages:
        print(f"Limite de {max_empty_pages} páginas vazias consecutivas atingido. Parando.")
    
    print(f"Extracao finalizada. Total de reviews coletadas: {len(all_reviews)}")
    
    return structure_result(all_reviews, product_id)

def process_single_review(review: dict, product_id: str) -> Optional[dict]:
    """
    Processa uma única review extraída da API
    
    Args:
        review (dict): Dados da review da API
        product_id (str): ID do produto
    
    Returns:
        dict: Review processada ou None se inválida
    """
    try:
        # Extrair dados básicos
        review_id = review.get('id', '')
        rating = review.get('rating', 0)
        title = review.get('title', '')
        comment = review.get('content', '')
        date = review.get('date_created', '')
        likes = review.get('likes', 0)
        
        # Verificar se tem imagens
        has_images = bool(review.get('pictures', []))
        
        # Verificar se tem comentário
        has_comment = bool(comment and comment.strip())
        
        return {
            'id': review_id,
            'rating': rating,
            'title': title,
            'comment': comment,
            'date': date,
            'likes': likes,
            'has_images': has_images,
            'has_comment': has_comment,
            'product_id': product_id
        }
        
    except Exception as e:
        print(f"Erro ao processar review: {e}")
        return None

def structure_result(reviews: List[dict], product_id: str) -> dict:
    """
    Estrutura o resultado final das reviews
    
    Args:
        reviews (List[dict]): Lista de reviews processadas
        product_id (str): ID do produto
    
    Returns:
        dict: Resultado estruturado
    """
    return {
        'product_id': product_id,
        'reviews': reviews,
        'total_reviews': len(reviews),
        'extraction_metadata': {
            'total_reviews': len(reviews),
            'pages_processed': len(reviews) // 30 + 1,
            'extraction_timestamp': time.time(),
            'success': True
        }
    }

def run_review_spider(product_id: str, max_reviews: int = 300, delay: float = 2.0):
    """Função de compatibilidade com o sistema existente"""
    return extract_reviews(product_id, max_reviews, delay)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python mercadolivre_spider_reviews.py <product_id> [max_reviews] [delay]")
        sys.exit(1)
    
    product_id = sys.argv[1]
    max_reviews = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    
    print(f"Testando extração de reviews para {product_id}")
    result = extract_reviews(product_id, max_reviews, delay)
    
    if result:
        print(f"Sucesso! {result['total_reviews']} reviews extraídas")
    else:
        print("Falha na extração")