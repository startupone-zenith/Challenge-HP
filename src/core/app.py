#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Simplificado de Scraping - Mercado Livre HP
Funcionalidades: Scraping e Geração de Dataset
"""

import pandas as pd
import logging
import time
import json
import sys
import requests
import random
from datetime import datetime
import argparse

# Importar configurações padronizadas
from .shared_scraping_config import setup_standard_logging

# Configurar logging padronizado
logger = setup_standard_logging(__name__, 'scraper.log')

class HPScrapingSystem:
    """Sistema simplificado para scraping e geração de datasets"""
    
    def __init__(self):
        self.produtos = []
        self.reviews_data = {}
        
    def executar_scraping_produtos(self, query, max_items=None, extract_images=False, 
                                 sort_by='relevance', condition='all', custom_url=None, 
                                 detailed_extraction=False, request_delay=2.0):
        """
        Executa scraping de produtos no Mercado Livre
        
        Args:
            query (str): Termo de busca
            max_items (int): Máximo de itens para coletar
            extract_images (bool): Se deve extrair imagens
            sort_by (str): Ordenação ('relevance', 'price_asc', 'price_desc')
            condition (str): Condição ('all', 'new', 'used')
            custom_url (str): URL específica do Mercado Livre para usar como base
            detailed_extraction (bool): Se deve usar extração detalhada (16 campos)
            request_delay (float): Delay entre requisições em segundos
        
        Returns:
            list: Lista de produtos coletados
        """
        logger.info(f"Iniciando scraping para: {query}")
        logger.info(f"Parâmetros: max_items={max_items}, images={extract_images}, sort={sort_by}")
        logger.info(f"Extração detalhada: {'ATIVADA' if detailed_extraction else 'DESATIVADA'}")
        
        try:
            # Importar spider dinamicamente para evitar importação circular
            from ..spiders.mercadolivre_spider import run_spider
            
            # Executar spider principal
            produtos, urls_used = run_spider(
                query=query,
                extract_images=extract_images,
                sort_by=sort_by,
                condition=condition,
                max_items=max_items,
                custom_url=custom_url,
                request_delay=request_delay
            )
            
            # Se extração detalhada foi solicitada, executar para cada produto
            if detailed_extraction and produtos:
                logger.info("Executando extração detalhada para todos os produtos...")
                produtos = self._executar_extracao_detalhada_produtos(produtos)
            
            if produtos:
                logger.info(f"Coletados {len(produtos)} produtos")
                self.produtos = produtos
                return produtos
            else:
                logger.warning("Nenhum produto foi coletado")
                return []
                
        except Exception as e:
            logger.error(f"Erro durante scraping de produtos: {str(e)}")
            return []
    
    def executar_scraping_reviews(self, product_id, max_reviews=200, delay=2.0):
        """
        Executa scraping de reviews para um produto específico
        Versão melhorada com análise de sentimento e distribuição detalhada
        
        Args:
            product_id (str): ID do produto no Mercado Livre
            max_reviews (int): Máximo de reviews para coletar
        
        Returns:
            dict: Dados das reviews coletadas com análise completa
        """
        logger.info(f"Coletando reviews para produto: {product_id}")
        
        try:
            # Importar spider dinamicamente para evitar importação circular
            from ..spiders.mercadolivre_spider_reviews import run_review_spider
            
            reviews_data = run_review_spider(product_id, max_reviews=max_reviews, delay=delay)
            
            if reviews_data and 'reviews' in reviews_data:
                logger.info(f"Coletadas {len(reviews_data['reviews'])} reviews")
                
                # Adicionar análise estatística avançada das reviews
                processed_data = self._analisar_reviews_estatisticas(reviews_data)
                
                self.reviews_data[product_id] = processed_data
                return processed_data
            else:
                logger.warning(f"Nenhuma review coletada para produto {product_id}")
                return {}
                
        except Exception as e:
            logger.error(f"Erro durante scraping de reviews: {str(e)}")
            return {}
    
    def coletar_reviews_para_produtos(self, max_reviews_per_product=100, delay=2.0):
        """
        Coleta reviews para todos os produtos já coletados
        
        Args:
            max_reviews_per_product (int): Máximo de reviews por produto
            delay (float): Delay entre requisições em segundos
        """
        if not self.produtos:
            logger.warning("Nenhum produto disponível para coletar reviews")
            return
        
        logger.info(f"Coletando reviews para {len(self.produtos)} produtos")
        
        for i, produto in enumerate(self.produtos, 1):
            product_id = produto.get('product_id') or produto.get('ID_PRODUTO')
            if product_id:
                logger.info(f"Coletando reviews {i}/{len(self.produtos)} - ID: {product_id}")
                reviews_data = self.executar_scraping_reviews(product_id, max_reviews_per_product, delay)
                
                # Adicionar dados de reviews ao produto
                if reviews_data:
                    produto['reviews_data'] = reviews_data
                
                # Delay entre requisições
                time.sleep(delay)
    
    def _executar_extracao_detalhada_produtos(self, produtos):
        """
        Executa extração detalhada melhorada para uma lista de produtos
        Versão otimizada com múltiplas estratégias de extração
        
        Args:
            produtos (list): Lista de produtos básicos
            
        Returns:
            list: Lista de produtos com dados detalhados
        """
        produtos_detalhados = []
        
        logger.info(f"Executando extração detalhada aprimorada para {len(produtos)} produtos...")
        
        for i, produto in enumerate(produtos, 1):
            produto_url = produto.get('LINK') or produto.get('LINK PRODUTO') or produto.get('link')
            
            if produto_url:
                logger.info(f"Extração detalhada {i}/{len(produtos)}: {produto_url[:100]}...")
                
                try:
                    detalhes = self._extrair_dados_detalhados_produto(produto_url)
                    
                    if detalhes and detalhes.get('extraction_success', False):
                        # Mesclar dados básicos com detalhados
                        produto_completo = produto.copy()  # Dados básicos
                        produto_completo.update(detalhes)  # Adicionar dados detalhados
                        produto_completo['extracao_detalhada'] = True
                        produto_completo['detalhes_qualidade'] = self._avaliar_qualidade_extracao(detalhes)
                        produtos_detalhados.append(produto_completo)
                        logger.info(f"  [OK] Extração detalhada concluída: {detalhes.get('nome_produto', 'N/A')}")
                    else:
                        # Se falhar, manter dados básicos
                        produto['extracao_detalhada'] = False
                        produto['detalhes_qualidade'] = 'basico_apenas'
                        produtos_detalhados.append(produto)
                        logger.warning(f"  [FALHA] Falha na extração detalhada, mantendo dados básicos")
                
                except Exception as e:
                    logger.error(f"  [ERRO] Erro na extração detalhada: {str(e)}")
                    # Se falhar, manter dados básicos
                    produto['extracao_detalhada'] = False
                    produto['detalhes_qualidade'] = 'erro'
                    produtos_detalhados.append(produto)
                
                # Delay inteligente baseado no sucesso
                delay = random.uniform(1.5, 3.0) if detalhes else random.uniform(0.5, 1.5)
                time.sleep(delay)
            else:
                logger.warning(f"Produto {i} sem URL válida")
                produto['extracao_detalhada'] = False
                produto['detalhes_qualidade'] = 'sem_url'
                produtos_detalhados.append(produto)
        
        logger.info(f"Extração detalhada concluída: {len(produtos_detalhados)} produtos processados")
        return produtos_detalhados
    
    def _extrair_dados_detalhados_produto(self, produto_url):
        """
        Extrai dados detalhados de um produto usando múltiplas estratégias
        
        Args:
            produto_url (str): URL do produto
            
        Returns:
            dict: Dados detalhados extraídos ou None se falhar
        """
        try:
            # Estratégia 1: Usar spider existente
            from ..spiders.mercadolivre_spider import MercadoLivreSpider
            import requests
            from scrapy.http import HtmlResponse
            
            # Headers mais realistas
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            # Fazer requisição com timeout maior
            response = requests.get(produto_url, headers=headers, timeout=20)
            response.raise_for_status()
            
            # Criar response do Scrapy
            scrapy_response = HtmlResponse(
                url=produto_url, 
                body=response.content,
                encoding='utf-8'
            )
            
            # Criar instância do spider com parâmetros dummy
            spider_instance = MercadoLivreSpider(query='dummy')
            
            # Executar extração detalhada
            detalhes = spider_instance.extract_detailed_product_info(scrapy_response)
            
            if detalhes:
                # Adicionar campos extras de análise
                detalhes['extraction_success'] = True
                detalhes['extraction_method'] = 'spider_scrapy'
                detalhes['response_size'] = len(response.content)
                detalhes['response_status'] = response.status_code
                
                # Validar qualidade da extração
                quality_score = self._calcular_score_qualidade(detalhes)
                detalhes['quality_score'] = quality_score
                
                logger.debug(f"Extração via spider concluída com score {quality_score}")
                return detalhes
            else:
                logger.warning("Spider não retornou dados detalhados")
                
        except Exception as e:
            logger.error(f"Erro na extração via spider: {str(e)}")
        
        # Estratégia 2: Extração simples por seletores
        try:
            detalhes_simples = self._extrair_dados_simples(produto_url)
            if detalhes_simples:
                detalhes_simples['extraction_method'] = 'seletores_simples'
                return detalhes_simples
        except Exception as e:
            logger.error(f"Erro na extração simples: {str(e)}")
        
        return None
    
    def _extrair_dados_simples(self, produto_url):
        """
        Extração simples usando requests + BeautifulSoup como fallback
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(produto_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            detalhes = {
                'nome_produto': '',
                'preco': '',
                'descricao_produto': '',
                'caracteristicas_principais': [],
                'extraction_success': False,
                'timestamp': datetime.now().isoformat()
            }
            
            # Extrair nome do produto
            nome_elem = soup.find('h1', class_='ui-pdp-title')
            if nome_elem:
                detalhes['nome_produto'] = nome_elem.get_text(strip=True)
            
            # Extrair preço
            preco_elem = soup.find('span', class_='andes-money-amount__fraction')
            if preco_elem:
                detalhes['preco'] = f"R$ {preco_elem.get_text(strip=True)}"
            
            # Extrair descrição
            desc_container = soup.find('div', class_='ui-pdp-description__content')
            if desc_container:
                paragrafos = desc_container.find_all('p')
                descricao = ' '.join([p.get_text(strip=True) for p in paragrafos])
                detalhes['descricao_produto'] = descricao[:1000]  # Limitar tamanho
            
            # Extrair algumas características
            specs_table = soup.find('table', class_='andes-table')
            if specs_table:
                specs = []
                rows = specs_table.find_all('tr')
                for row in rows[:5]:  # Máximo 5 características
                    cells = row.find_all(['th', 'td'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            specs.append(f"{key}: {value}")
                detalhes['caracteristicas_principais'] = specs
            
            # Marcar como sucesso se conseguiu pelo menos nome ou preço
            if detalhes['nome_produto'] or detalhes['preco']:
                detalhes['extraction_success'] = True
                logger.debug("Extração simples concluída com sucesso")
                return detalhes
            
        except ImportError:
            logger.warning("BeautifulSoup não disponível para extração simples")
        except Exception as e:
            logger.error(f"Erro na extração simples: {str(e)}")
        
        return None
    
    def _calcular_score_qualidade(self, detalhes):
        """
        Calcula score de qualidade da extração baseado nos campos preenchidos
        """
        score = 0
        campos_importantes = [
            'nome_produto', 'preco', 'descricao_produto', 
            'caracteristicas_principais', 'fotos_produto', 'avaliacao'
        ]
        
        for campo in campos_importantes:
            valor = detalhes.get(campo, '')
            if valor and valor != 'N/A':
                if isinstance(valor, list) and len(valor) > 0:
                    score += 1
                elif isinstance(valor, str) and valor.strip():
                    score += 1
                elif isinstance(valor, dict) and valor:
                    score += 1
        
        return round(score / len(campos_importantes) * 100, 1)
    
    def _avaliar_qualidade_extracao(self, detalhes):
        """
        Avalia a qualidade da extração e retorna categoria
        """
        score = detalhes.get('quality_score', 0)
        
        if score >= 80:
            return 'excelente'
        elif score >= 60:
            return 'boa'
        elif score >= 40:
            return 'regular'
        else:
            return 'limitada'
    
    def gerar_dataset_csv(self, filename=None, include_reviews=True, individual_reviews=False):
        """
        Gera dataset em formato CSV
        
        Args:
            filename (str): Nome do arquivo (opcional)
            include_reviews (bool): Se deve incluir dados de reviews
            individual_reviews (bool): Se deve incluir cada review como linha separada
        
        Returns:
            str: Caminho do arquivo gerado
        """
        if not self.produtos:
            logger.error("Nenhum produto disponível para gerar dataset")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dataset_hp_produtos_{timestamp}.csv"
        
        logger.info(f"Gerando dataset CSV: {filename}")
        
        try:
            # Preparar dados para DataFrame
            dataset_rows = []
            
            for produto in self.produtos:
                # =============================================================================
                # CONSOLIDAÇÃO DE DADOS - Usar detalhados quando disponível, senão básicos
                # =============================================================================
                
                # Consolidar título
                titulo_final = produto.get('nome_produto', '') or produto.get('TITULO PRODUTO', '')
                
                # Consolidar preço
                preco_final = produto.get('preco', '') or produto.get('PREÇO', '')
                
                # Consolidar vendedor
                vendedor_final = produto.get('nome_loja', '') or produto.get('VENDEDOR', '')
                
                # Consolidar marca
                marca_final = produto.get('brand', '') or produto.get('MARCA', '')
                
                # Consolidar condição
                condicao_final = produto.get('condicao_produto', '') or produto.get('CONDICAO', '') or 'Novo'
                
                # Consolidar frete grátis
                frete_gratis_final = produto.get('frete_gratis', False) or (produto.get('ENTREGA FULL', '') == 'Sim')
                
                # Consolidar dados de avaliações (CORRIGIR PROBLEMA DE REVIEWS ZERADAS)
                total_reviews_final = 0
                rating_medio_final = 0
                star_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
                reviews_com_texto_final = 0
                reviews_com_imagens_final = 0
                
                # 1. Prioridade: dados específicos de reviews_data
                comentarios_reviews = []
                if include_reviews and 'reviews_data' in produto:
                    reviews_data = produto['reviews_data']
                    statistics = reviews_data.get('statistics', {})
                    total_reviews_final = statistics.get('total_reviews', 0)
                    rating_medio_final = statistics.get('average_rating', 0)
                    rating_dist = statistics.get('rating_distribution', {})
                    star_distribution.update(rating_dist)
                    reviews_com_texto_final = statistics.get('reviews_with_text', 0)
                    reviews_com_imagens_final = statistics.get('reviews_with_images', 0)
                    
                    # Extrair comentários das reviews
                    reviews_list = reviews_data.get('reviews', [])
                    for review in reviews_list:
                        if review.get('has_comment', False) and review.get('comment', '').strip():
                            comentario = {
                                'rating': review.get('rating', 0),
                                'titulo': review.get('title', ''),
                                'comentario': review.get('comment', ''),
                                'data': review.get('date', ''),
                                'likes': review.get('likes', 0),
                                'tem_imagens': review.get('has_images', False)
                            }
                            comentarios_reviews.append(comentario)
                
                # 2. Fallback: dados de avaliacao da extração detalhada
                elif include_reviews and 'avaliacao' in produto and produto['avaliacao'] != 'N/A':
                    avaliacao = produto['avaliacao']
                    if isinstance(avaliacao, dict):
                        total_reviews_final = avaliacao.get('count', 0) or avaliacao.get('review_count', 0)
                        rating_medio_final = avaliacao.get('rating', 0)
                        reviews_com_texto_final = avaliacao.get('reviews_with_comment', 0)
                        reviews_com_imagens_final = avaliacao.get('pictures_quantity', 0)
                        # Calcular distribuição de estrelas
                        star_distribution = self._estimate_star_distribution(avaliacao, rating_medio_final, total_reviews_final)
                
                # 3. Último fallback: dados básicos da busca
                elif include_reviews:
                    try:
                        if produto.get('TOTAL AVALIAÇÕES'):
                            total_reviews_final = int(str(produto.get('TOTAL AVALIAÇÕES', '')).replace('.', '').replace(',', ''))
                        if produto.get('MÉDIA AVALIAÇÕES'):
                            rating_medio_final = float(produto.get('MÉDIA AVALIAÇÕES', ''))
                        # Se há dados básicos, estimar distribuição
                        if total_reviews_final > 0 and rating_medio_final > 0:
                            star_distribution = self._estimate_star_distribution({}, rating_medio_final, total_reviews_final)
                    except (ValueError, TypeError):
                        pass
                
                # =============================================================================
                # ESTRUTURA REORGANIZADA DO CSV - DADOS MAIS IMPORTANTES PRIMEIRO
                # =============================================================================
                row = {
                    # === IDENTIFICAÇÃO DO PRODUTO ===
                    'id': produto.get('ID_PRODUTO', ''),
                    'titulo': titulo_final,
                    'link': produto.get('LINK', ''),
                    
                    # === PREÇO E OFERTAS ===
                    'preco': preco_final,
                    'preco_original': produto.get('PREÇO ANTERIOR', ''),
                    'desconto': produto.get('DESCONTO', '') or produto.get('desconto', ''),
                    
                    # === VENDEDOR ===
                    'vendedor': vendedor_final,
                    'seller_id': produto.get('seller_id', ''),
                    'reputation_level': produto.get('reputation_level', ''),
                    'power_seller_status': produto.get('power_seller_status', ''),
                    
                    # === AVALIAÇÕES (CONSOLIDADAS) ===
                    'rating_medio': rating_medio_final,
                    'total_reviews': total_reviews_final,
                    'rating_5_estrelas': star_distribution.get(5, 0),
                    'rating_4_estrelas': star_distribution.get(4, 0),
                    'rating_3_estrelas': star_distribution.get(3, 0),
                    'rating_2_estrelas': star_distribution.get(2, 0),
                    'rating_1_estrela': star_distribution.get(1, 0),
                    'tem_reviews': total_reviews_final > 0,
                    'reviews_com_texto': reviews_com_texto_final,
                    'reviews_com_imagens': reviews_com_imagens_final,
                    'avaliacoes_positivas': star_distribution.get(5, 0) + star_distribution.get(4, 0),
                    'avaliacoes_negativas': star_distribution.get(1, 0) + star_distribution.get(2, 0),
                    'avaliacoes_neutras': star_distribution.get(3, 0),
                    
                    # === PRODUTO ===
                    'marca': marca_final,
                    'condicao': condicao_final,
                    'descricao_produto': produto.get('descricao_produto', ''),
                    'caracteristicas_principais': self._format_list_for_csv(produto.get('caracteristicas_principais', [])),
                    
                    # === CARACTERÍSTICAS DETALHADAS ===
                    'main_characteristics': self._format_dict_for_csv(produto.get('main_characteristics', {})),
                    'other_characteristics': self._format_dict_for_csv(produto.get('other_characteristics', {})),
                    
                    # === ENTREGA ===
                    'frete_gratis': frete_gratis_final,
                    'shipping_mode': produto.get('shipping_mode', ''),
                    'tempo_entrega': produto.get('tempo_entrega', ''),
                    
                    # === DADOS TÉCNICOS ===
                    'imagem_url': produto.get('IMAGEM', ''),
                    'fotos_produto': self._format_list_for_csv(produto.get('fotos_produto', [])),
                    'product_id': produto.get('product_id', '') or produto.get('ID_PRODUTO', ''),
                    'sku': produto.get('sku', ''),
                    'brand': produto.get('brand', ''),  # Manter separado para compatibilidade
                    
                    # === METADADOS ===
                    'data_coleta': produto.get('scraped_at', datetime.now().isoformat()),
                    'tem_dados_detalhados': produto.get('extracao_detalhada', False),
                    'qualidade_extracao_detalhada': produto.get('detalhes_qualidade', 'nao_realizada'),
                    'score_qualidade_detalhes': produto.get('quality_score', 0),
                    
                    # === COMENTÁRIOS DE REVIEWS ===
                    'comentarios_reviews': self._format_comentarios_for_csv(comentarios_reviews),
                    'total_comentarios': len(comentarios_reviews),
                    'comentarios_positivos': len([c for c in comentarios_reviews if c.get('rating', 0) >= 4]),
                    'comentarios_negativos': len([c for c in comentarios_reviews if c.get('rating', 0) <= 2]),
                    'comentarios_com_imagens': len([c for c in comentarios_reviews if c.get('tem_imagens', False)]),
                    'comentario_mais_curtido': self._get_most_liked_comment(comentarios_reviews),
                    'comentario_mais_recente': self._get_most_recent_comment(comentarios_reviews)
                }
                
                # Adicionar campos extraídos de outros_dados
                row.update(self._extract_outros_dados_fields(produto.get('outros', {})))
                
                # Adicionar alguns campos adicionais que podem ser úteis (apenas se disponíveis)
                if produto.get('extracao_detalhada', False):
                    row.update({
                        'vendas_loja': produto.get('vendas_loja', ''),
                        'vendas_produto': produto.get('vendas_produto', ''),
                        'devolucao_gratis': produto.get('devolucao_gratis', ''),
                        'compra_garantida': produto.get('compra_garantida', ''),
                        'tempo_garantia': produto.get('tempo_garantia', ''),
                        'timestamp_extracao_detalhada': produto.get('timestamp', ''),
                        'metodo_extracao_detalhada': produto.get('extraction_method', 'spider_scrapy'),
                        'tamanho_resposta_bytes': produto.get('response_size', 0),
                        'status_resposta_http': produto.get('response_status', 0)
                    })
                else:
                    row.update({
                        'vendas_loja': '',
                        'vendas_produto': '',
                        'devolucao_gratis': '',
                        'compra_garantida': '',
                        'tempo_garantia': '',
                        'timestamp_extracao_detalhada': '',
                        'metodo_extracao_detalhada': 'nao_realizada',
                        'tamanho_resposta_bytes': 0,
                        'status_resposta_http': 0
                    })
                
                dataset_rows.append(row)
                
                # Se individual_reviews=True, adicionar reviews como colunas
                if individual_reviews and include_reviews and 'reviews_data' in produto:
                    reviews_list = produto['reviews_data'].get('reviews', [])
                    
                    # Filtrar apenas reviews que possuam comentários
                    reviews_with_comments = []
                    for review in reviews_list:
                        comment = review.get('comment', '')
                        has_comment = review.get('has_comment', False)
                        
                        # Verificar se a review tem comentário válido
                        if has_comment and comment and comment.strip():
                            reviews_with_comments.append(review)
                    
                    # Adicionar colunas para cada review com comentário (sem limite máximo)
                    for i, review in enumerate(reviews_with_comments):
                        row[f'review_{i+1}_id'] = review.get('id', 'N/A')
                        row[f'review_{i+1}_rating'] = review.get('rating', 'N/A')
                        # Extrair texto do título se for dicionário
                        title = review.get('title', '')
                        if isinstance(title, dict):
                            title = title.get('text', '')
                        row[f'review_{i+1}_title'] = title if title else 'N/A'
                        row[f'review_{i+1}_comment'] = review.get('comment', 'N/A')
                        row[f'review_{i+1}_date'] = review.get('date', 'N/A')
                        row[f'review_{i+1}_likes'] = review.get('likes', 'N/A')
                        row[f'review_{i+1}_has_images'] = review.get('has_images', 'N/A')
                        row[f'review_{i+1}_has_comment'] = review.get('has_comment', 'N/A')
                    
                    # Adicionar informações sobre total de reviews com comentários
                    row['total_reviews_individual'] = len(reviews_with_comments)
                    row['total_reviews_original'] = len(reviews_list)  # Total original de reviews
                    row['tipo_linha'] = 'produto_com_reviews'
                else:
                    row['tipo_linha'] = 'produto'
            
            # Criar DataFrame e salvar
            df = pd.DataFrame(dataset_rows)
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Dataset gerado com sucesso: {filename}")
            logger.info(f"Total de produtos: {len(df)}")
            
            # Gerar também arquivo Excel
            excel_filename = filename.replace('.csv', '.xlsx')
            try:
                self._gerar_dataset_excel(df, excel_filename)
                logger.info(f"Dataset Excel gerado: {excel_filename}")
            except Exception as e:
                logger.warning(f"Erro ao gerar Excel: {e}")
            
            # Gerar também arquivo JSON
            json_filename = filename.replace('.csv', '.json')
            try:
                df.to_json(json_filename, orient='records', indent=2, force_ascii=False)
                logger.info(f"Dataset JSON gerado: {json_filename}")
            except Exception as e:
                logger.warning(f"Erro ao gerar JSON: {e}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar dataset CSV: {str(e)}")
            return None
    
    def gerar_dataset_excel(self, filename=None, include_reviews=True, individual_reviews=False):
        """
        Gera dataset em formato Excel
        
        Args:
            filename (str): Nome do arquivo (opcional)
            include_reviews (bool): Se deve incluir dados de reviews
            individual_reviews (bool): Se deve incluir cada review como linha separada
        
        Returns:
            str: Caminho do arquivo gerado
        """
        if not self.produtos:
            logger.error("Nenhum produto disponível para gerar dataset")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dataset_hp_produtos_{timestamp}.xlsx"
        
        logger.info(f"Gerando dataset Excel: {filename}")
        
        try:
            # Usar o mesmo método do CSV para gerar dados
            csv_file = self.gerar_dataset_csv(
                filename.replace('.xlsx', '.csv'), 
                include_reviews=include_reviews, 
                individual_reviews=individual_reviews
            )
            
            if not csv_file:
                logger.error("Falha ao gerar CSV para conversão Excel")
                return None
            
            # Ler CSV e converter para Excel
            df = pd.read_csv(csv_file)
            
            # Gerar Excel usando o método existente
            self._gerar_dataset_excel(df, filename)
            
            logger.info(f"Dataset Excel gerado: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar dataset Excel: {str(e)}")
            return None
    
    def _format_list_for_csv(self, data_list):
        """Formatar lista para CSV (separado por ponto e vírgula)"""
        if isinstance(data_list, list):
            return '; '.join([str(item) for item in data_list if item != 'N/A'])
        return str(data_list) if data_list else ''
    
    def _format_dict_for_csv(self, data_dict):
        """Formatar dicionário para CSV"""
        if isinstance(data_dict, dict):
            items = []
            for key, value in data_dict.items():
                if value is not None:
                    items.append(f"{key}: {value}")
            return '; '.join(items)
        return str(data_dict) if data_dict else ''
    
    def _format_rating_for_csv(self, rating_data):
        """Formatar dados de avaliação para CSV"""
        if isinstance(rating_data, dict):
            rating = rating_data.get('rating', '')
            count = rating_data.get('count', '')
            review_count = rating_data.get('review_count', '')
            return f"Rating: {rating}, Count: {count}, Reviews: {review_count}"
        return str(rating_data) if rating_data else ''
    
    def _format_comentarios_for_csv(self, comentarios):
        """Formatar comentários de reviews para CSV"""
        if not comentarios:
            return ''
        
        comentarios_formatados = []
        for i, comentario in enumerate(comentarios[:10], 1):  # Limitar a 10 comentários
            rating = comentario.get('rating', 0)
            titulo = comentario.get('titulo', '')
            texto = comentario.get('comentario', '')
            data = comentario.get('data', '')
            likes = comentario.get('likes', 0)
            
            # Truncar texto se muito longo
            if len(texto) > 200:
                texto = texto[:200] + '...'
            
            comentario_formatado = f"[{i}] {rating} estrelas - {titulo}: {texto} (Data: {data}, Likes: {likes})"
            comentarios_formatados.append(comentario_formatado)
        
        return ' | '.join(comentarios_formatados)
    
    def _get_most_liked_comment(self, comentarios):
        """Obter o comentário mais curtido"""
        if not comentarios:
            return ''
        
        most_liked = max(comentarios, key=lambda c: c.get('likes', 0))
        return f"{most_liked.get('rating', 0)} estrelas - {most_liked.get('comentario', '')[:100]}... (Likes: {most_liked.get('likes', 0)})"
    
    def _get_most_recent_comment(self, comentarios):
        """Obter o comentário mais recente"""
        if not comentarios:
            return ''
        
        # Para simplificar, pegar o primeiro comentário (assumindo que estão ordenados por data)
        recent = comentarios[0]
        return f"{recent.get('rating', 0)} estrelas - {recent.get('comentario', '')[:100]}... (Data: {recent.get('data', '')})"
    
    def _extract_outros_dados_fields(self, outros_dados):
        """
        Extrai campos específicos do dicionário outros_dados como colunas separadas
        
        Args:
            outros_dados (dict): Dicionário com dados extras do produto
            
        Returns:
            dict: Campos extraídos como colunas separadas
        """
        fields = {
            'seller_id': '',
            'reputation_level': '',
            'power_seller_status': '',
            'shipping_mode': '',
            'brand': '',
            'sku': '',
            'product_id': ''
        }
        
        if isinstance(outros_dados, dict):
            # Mapear campos do outros_dados para as novas colunas
            fields.update({
                'seller_id': outros_dados.get('seller_id', ''),
                'reputation_level': outros_dados.get('reputation_level', ''),
                'power_seller_status': outros_dados.get('power_seller_status', ''),
                'shipping_mode': outros_dados.get('shipping_mode', ''),
                'brand': outros_dados.get('brand', ''),
                'sku': outros_dados.get('sku', ''),
                'product_id': outros_dados.get('product_id', '')
            })
        
        return fields
    
    def _gerar_dataset_excel(self, df, filename):
        """Gerar dataset em formato Excel com formatação"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils.dataframe import dataframe_to_rows
            from openpyxl.worksheet.table import Table, TableStyleInfo
            
            # Criar workbook
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Produtos HP"
            
            # Adicionar dados do DataFrame
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)
            
            # Formatação do cabeçalho
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            
            # Aplicar formatação ao cabeçalho
            for cell in ws[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Ajustar largura das colunas
            column_widths = {
                'A': 15,  # id
                'B': 50,  # titulo
                'C': 30,  # link
                'D': 15,  # preco
                'E': 15,  # preco_original
                'F': 15,  # desconto
                'G': 25,  # vendedor
                'H': 15,  # rating_medio
                'I': 15,  # total_reviews
                'J': 20,  # marca
                'K': 15,  # condicao
                'L': 100, # comentarios_reviews
            }
            
            for col, width in column_widths.items():
                ws.column_dimensions[col].width = width
            
            # Adicionar bordas
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in ws.iter_rows():
                for cell in row:
                    cell.border = thin_border
            
            # Salvar arquivo
            wb.save(filename)
            logger.info(f"Arquivo Excel salvo: {filename}")
            
        except ImportError:
            logger.error("openpyxl não instalado. Instale com: pip install openpyxl")
            raise
        except Exception as e:
            logger.error(f"Erro ao gerar Excel: {e}")
            raise
    
    def _estimate_star_distribution(self, avaliacao_data, rating, count):
        """
        Estima a distribuição de estrelas baseada no rating médio e dados disponíveis
        
        Args:
            avaliacao_data (dict): Dados de avaliação extraídos
            rating (float): Rating médio
            count (int): Total de reviews
            
        Returns:
            dict: Distribuição estimada por estrelas {1: x, 2: y, 3: z, 4: w, 5: v}
        """
        
        # Se há dados específicos de distribuição, usar (apenas se não estão vazios)
        if isinstance(avaliacao_data, dict) and 'star_distribution' in avaliacao_data:
            star_dist = avaliacao_data['star_distribution']
            if star_dist and isinstance(star_dist, dict) and any(v > 0 for v in star_dist.values()):
                return star_dist
        
        if isinstance(avaliacao_data, dict) and 'rating_breakdown' in avaliacao_data:
            rating_breakdown = avaliacao_data['rating_breakdown'] 
            if rating_breakdown and isinstance(rating_breakdown, dict) and any(v > 0 for v in rating_breakdown.values()):
                return rating_breakdown
            
        # Se não há dados específicos, fazer estimativa baseada no rating
        if rating <= 0 or count <= 0:
            return {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # Algoritmo de estimativa baseado em padrões comuns do MercadoLivre
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        if rating >= 4.5:
            # Rating alto - maioria 5 e 4 estrelas
            distribution[5] = int(count * 0.7)  # 70%
            distribution[4] = int(count * 0.25) # 25%
            distribution[3] = int(count * 0.03) # 3%
            distribution[2] = int(count * 0.01) # 1%
            distribution[1] = int(count * 0.01) # 1%
        elif rating >= 4.0:
            # Rating bom - equilibrio entre 5, 4 e 3
            distribution[5] = int(count * 0.5)  # 50%
            distribution[4] = int(count * 0.35) # 35%
            distribution[3] = int(count * 0.1)  # 10%
            distribution[2] = int(count * 0.03) # 3%
            distribution[1] = int(count * 0.02) # 2%
        elif rating >= 3.5:
            # Rating médio 
            distribution[5] = int(count * 0.3)  # 30%
            distribution[4] = int(count * 0.35) # 35%
            distribution[3] = int(count * 0.25) # 25%
            distribution[2] = int(count * 0.07) # 7%
            distribution[1] = int(count * 0.03) # 3%
        elif rating >= 3.0:
            # Rating baixo-médio
            distribution[5] = int(count * 0.2)  # 20%
            distribution[4] = int(count * 0.25) # 25%
            distribution[3] = int(count * 0.35) # 35%
            distribution[2] = int(count * 0.15) # 15%
            distribution[1] = int(count * 0.05) # 5%
        else:
            # Rating baixo
            distribution[5] = int(count * 0.1)  # 10%
            distribution[4] = int(count * 0.15) # 15%
            distribution[3] = int(count * 0.25) # 25%
            distribution[2] = int(count * 0.3)  # 30%
            distribution[1] = int(count * 0.2)  # 20%
        
        # Ajustar para somar exatamente o total de reviews
        total_estimated = sum(distribution.values())
        if total_estimated != count and count > 0:
            # Ajustar a categoria com mais reviews
            max_category = max(distribution.keys(), key=lambda k: distribution[k])
            distribution[max_category] += count - total_estimated
        
        return distribution
    
    def _analisar_reviews_estatisticas(self, reviews_data):
        """
        Análise estatística avançada das reviews coletadas
        
        Args:
            reviews_data (dict): Dados brutos das reviews
            
        Returns:
            dict: Dados processados com análise estatística
        """
        try:
            if not reviews_data or 'reviews' not in reviews_data:
                return reviews_data
            
            reviews = reviews_data['reviews']
            
            # Distribuição por rating
            rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            total_ratings = 0
            sum_ratings = 0
            
            # Análise de conteúdo
            reviews_with_text = 0
            reviews_with_images = 0
            avg_text_length = 0
            total_text_length = 0
            
            # Análise temporal
            reviews_by_month = {}
            
            for review in reviews:
                # Análise de rating
                rating = int(review.get('rating', 0)) if review.get('rating', '0').isdigit() else 0
                if 1 <= rating <= 5:
                    rating_distribution[rating] += 1
                    total_ratings += 1
                    sum_ratings += rating
                
                # Análise de conteúdo
                text = review.get('text', '').strip()
                if text:
                    reviews_with_text += 1
                    total_text_length += len(text)
                
                # Verificar se tem imagens (se disponível)
                if review.get('images') or review.get('photos'):
                    reviews_with_images += 1
                
                # Análise temporal
                date_str = review.get('date', '')
                if date_str and date_str != 'N/A':
                    try:
                        # Extrair mês/ano da data
                        if '-' in date_str:
                            year_month = date_str[:7]  # YYYY-MM
                            reviews_by_month[year_month] = reviews_by_month.get(year_month, 0) + 1
                    except:
                        pass
            
            # Calcular estatísticas
            average_rating = sum_ratings / total_ratings if total_ratings > 0 else 0
            avg_text_length = total_text_length / reviews_with_text if reviews_with_text > 0 else 0
            
            # Percentuais por rating
            rating_percentages = {}
            for rating, count in rating_distribution.items():
                rating_percentages[rating] = (count / total_ratings * 100) if total_ratings > 0 else 0
            
            # Adicionar estatísticas aos dados originais
            reviews_data.update({
                'statistics': {
                    'total_reviews': len(reviews),
                    'rating_distribution': rating_distribution,
                    'rating_percentages': rating_percentages,
                    'average_rating': round(average_rating, 2),
                    'total_ratings': total_ratings,
                    'reviews_with_text': reviews_with_text,
                    'reviews_with_images': reviews_with_images,
                    'avg_text_length': round(avg_text_length, 1),
                    'text_coverage': (reviews_with_text / len(reviews) * 100) if reviews else 0,
                    'reviews_by_month': reviews_by_month
                },
                'quality_indicators': {
                    'high_ratings': rating_distribution.get(5, 0) + rating_distribution.get(4, 0),
                    'low_ratings': rating_distribution.get(1, 0) + rating_distribution.get(2, 0),
                    'neutral_ratings': rating_distribution.get(3, 0),
                    'detailed_reviews': reviews_with_text,
                    'visual_reviews': reviews_with_images
                }
            })
            
            logger.info(f"Análise de reviews concluída: {average_rating:.1f} estrelas média, {reviews_with_text} com texto")
            return reviews_data
            
        except Exception as e:
            logger.error(f"Erro na análise de estatísticas de reviews: {str(e)}")
            return reviews_data
    
    def gerar_dataset_json(self, filename=None):
        """
        Gera dataset em formato JSON
        
        Args:
            filename (str): Nome do arquivo (opcional)
        
        Returns:
            str: Caminho do arquivo gerado
        """
        if not self.produtos:
            logger.error("Nenhum produto disponível para gerar dataset")
            return None
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dataset_hp_produtos_{timestamp}.json"
        
        logger.info(f"Gerando dataset JSON: {filename}")
        
        try:
            dataset = {
                'metadata': {
                    'total_produtos': len(self.produtos),
                    'data_geracao': datetime.now().isoformat(),
                    'versao': '1.0'
                },
                'produtos': self.produtos
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Dataset JSON gerado com sucesso: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar dataset JSON: {str(e)}")
            return None
    
    def estatisticas_coleta(self):
        """Exibe estatísticas da coleta realizada"""
        if not self.produtos:
            print("Nenhum produto coletado")
            return
        
        total_produtos = len(self.produtos)
        produtos_com_reviews = sum(1 for p in self.produtos if 'reviews_data' in p)
        
        print(f"\n=== ESTATÍSTICAS DA COLETA ===")
        print(f"Total de produtos: {total_produtos}")
        print(f"Produtos com reviews: {produtos_com_reviews}")
        print(f"Produtos sem reviews: {total_produtos - produtos_com_reviews}")
        
        # Estatísticas de preços
        precos = []
        for produto in self.produtos:
            preco_str = produto.get('price', '')
            if preco_str and 'R$' in preco_str:
                try:
                    preco_num = float(preco_str.replace('R$', '').replace('.', '').replace(',', '.').strip())
                    precos.append(preco_num)
                except:
                    pass
        
        if precos:
            print(f"Preço médio: R$ {sum(precos)/len(precos):.2f}")
            print(f"Preço mínimo: R$ {min(precos):.2f}")
            print(f"Preço máximo: R$ {max(precos):.2f}")


def main():
    """Função principal para execução via linha de comando"""
    parser = argparse.ArgumentParser(description='Sistema de Scraping HP - Mercado Livre')
    parser.add_argument('--query', '-q', required=True, help='Termo de busca')
    parser.add_argument('--max-items', '-m', type=int, help='Máximo de itens para coletar')
    parser.add_argument('--no-images', action='store_true', help='Não extrair imagens')
    parser.add_argument('--sort', choices=['relevance', 'price_asc', 'price_desc'], 
                       default='relevance', help='Ordenação dos resultados')
    parser.add_argument('--condition', choices=['all', 'new', 'used'], 
                       default='all', help='Condição dos produtos')
    parser.add_argument('--reviews', action='store_true', help='Coletar reviews dos produtos')
    parser.add_argument('--max-reviews', type=int, default=100, 
                       help='Máximo de reviews por produto')
    parser.add_argument('--output-csv', help='Nome do arquivo CSV de saída')
    parser.add_argument('--output-json', help='Nome do arquivo JSON de saída')
    
    args = parser.parse_args()
    
    # Criar instância do sistema
    sistema = HPScrapingSystem()
    
    # Executar scraping de produtos
    produtos = sistema.executar_scraping_produtos(
        query=args.query,
        max_items=args.max_items,
        extract_images=not args.no_images,
        sort_by=args.sort,
        condition=args.condition
    )
    
    if not produtos:
        print("Nenhum produto foi coletado. Encerrando.")
        return
    
    # Coletar reviews se solicitado
    if args.reviews:
        sistema.coletar_reviews_para_produtos(args.max_reviews)
    
    # Gerar datasets
    if args.output_csv or not args.output_json:
        csv_file = sistema.gerar_dataset_csv(args.output_csv, include_reviews=args.reviews)
        if csv_file:
            print(f"Dataset CSV gerado: {csv_file}")
    
    if args.output_json:
        json_file = sistema.gerar_dataset_json(args.output_json)
        if json_file:
            print(f"Dataset JSON gerado: {json_file}")
    
    # Exibir estatísticas
    sistema.estatisticas_coleta()


if __name__ == "__main__":
    main()
