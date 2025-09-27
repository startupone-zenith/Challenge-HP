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
                                 detailed_extraction=False):
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
                custom_url=custom_url
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
    
    def executar_scraping_reviews(self, product_id, max_reviews=200):
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
            
            reviews_data = run_review_spider(product_id, max_reviews=max_reviews)
            
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
    
    def coletar_reviews_para_produtos(self, max_reviews_per_product=100):
        """
        Coleta reviews para todos os produtos já coletados
        
        Args:
            max_reviews_per_product (int): Máximo de reviews por produto
        """
        if not self.produtos:
            logger.warning("Nenhum produto disponível para coletar reviews")
            return
        
        logger.info(f"Coletando reviews para {len(self.produtos)} produtos")
        
        for i, produto in enumerate(self.produtos, 1):
            product_id = produto.get('id')
            if product_id:
                logger.info(f"Coletando reviews {i}/{len(self.produtos)} - ID: {product_id}")
                reviews_data = self.executar_scraping_reviews(product_id, max_reviews_per_product)
                
                # Adicionar dados de reviews ao produto
                if reviews_data:
                    produto['reviews_data'] = reviews_data
                
                # Delay entre requisições
                time.sleep(1)
    
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
    
    def gerar_dataset_csv(self, filename=None, include_reviews=True):
        """
        Gera dataset em formato CSV
        
        Args:
            filename (str): Nome do arquivo (opcional)
            include_reviews (bool): Se deve incluir dados de reviews
        
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
                # CAMPOS BÁSICOS (sempre presentes) - Mapeamento correto dos nomes dos campos do scraper
                row = {
                    'id': produto.get('ID_PRODUTO', ''),
                    'titulo': produto.get('TITULO PRODUTO', ''),
                    'preco': produto.get('PREÇO', ''),
                    'preco_original': produto.get('PREÇO ANTERIOR', ''),
                    'desconto': produto.get('DESCONTO', ''),
                    'vendedor': produto.get('VENDEDOR', ''),
                    'reputacao_vendedor': produto.get('REPUTACAO_VENDEDOR', ''),
                    'condicao': produto.get('CONDICAO', ''),
                    'frete_gratis': produto.get('ENTREGA FULL', '') == 'Sim',
                    'link': produto.get('LINK', ''),
                    'imagem_url': produto.get('IMAGEM', ''),
                    'localizacao': produto.get('LOCALIZACAO', ''),
                    'vendas': produto.get('VENDAS', ''),
                    'media_avaliacoes': produto.get('MÉDIA AVALIAÇÕES', ''),
                    'total_avaliacoes': produto.get('TOTAL AVALIAÇÕES', ''),
                    'entrega': produto.get('ENTREGA', ''),
                    'marca': produto.get('MARCA', ''),
                    'data_coleta': produto.get('scraped_at', datetime.now().isoformat())
                }
                
                # CAMPOS DETALHADOS (se extração detalhada foi usada)
                if produto.get('extracao_detalhada', False):
                    # Os 16 campos da extração detalhada
                    row.update({
                        # Informações do produto
                        'nome_produto_detalhado': produto.get('nome_produto', ''),
                        'condicao_produto_detalhada': produto.get('condicao_produto', ''),
                        'descricao_produto': produto.get('descricao_produto', ''),
                        
                        # Preços e ofertas
                        'preco_detalhado': produto.get('preco', ''),
                        'desconto_detalhado': produto.get('desconto', ''),
                        
                        # Entrega e frete
                        'frete_gratis_detalhado': produto.get('frete_gratis', ''),
                        'tempo_entrega': produto.get('tempo_entrega', ''),
                        
                        # Informações do vendedor
                        'nome_loja': produto.get('nome_loja', ''),
                        'vendas_loja': produto.get('vendas_loja', ''),
                        'vendas_produto': produto.get('vendas_produto', ''),
                        
                        # Garantias e políticas
                        'devolucao_gratis': produto.get('devolucao_gratis', ''),
                        'compra_garantida': produto.get('compra_garantida', ''),
                        'tempo_garantia': produto.get('tempo_garantia', ''),
                        
                        # Características (converter lista para string)
                        'caracteristicas_principais': self._format_list_for_csv(produto.get('caracteristicas_principais', [])),
                        
                        # Fotos (converter lista para string)
                        'fotos_produto': self._format_list_for_csv(produto.get('fotos_produto', [])),
                        
                        # Avaliações
                        'avaliacao': self._format_rating_for_csv(produto.get('avaliacao', {})),
                        
                        # Outros dados (converter dict para string)
                        'outros_dados': self._format_dict_for_csv(produto.get('outros', {})),
                        
                        # Timestamp da extração detalhada
                        'timestamp_extracao_detalhada': produto.get('timestamp', ''),
                        
                        # Flag indicando que tem dados detalhados
                        'tem_dados_detalhados': True
                    })
                else:
                    # Campos vazios para produtos sem extração detalhada
                    row.update({
                        'nome_produto_detalhado': '',
                        'condicao_produto_detalhada': '',
                        'descricao_produto': '',
                        'preco_detalhado': '',
                        'desconto_detalhado': '',
                        'frete_gratis_detalhado': '',
                        'tempo_entrega': '',
                        'nome_loja': '',
                        'vendas_loja': '',
                        'vendas_produto': '',
                        'devolucao_gratis': '',
                        'compra_garantida': '',
                        'tempo_garantia': '',
                        'caracteristicas_principais': '',
                        'fotos_produto': '',
                        'avaliacao': '',
                        'outros_dados': '',
                        'timestamp_extracao_detalhada': '',
                        'tem_dados_detalhados': False
                    })
                
                # Adicionar dados de reviews (melhorado para usar dados detalhados)
                # Prioridade: 1) reviews_data específicos, 2) dados de avaliacao da extração detalhada
                reviews_added = False
                
                if include_reviews and 'reviews_data' in produto:
                    reviews_data = produto['reviews_data']
                    statistics = reviews_data.get('statistics', {})
                    quality = reviews_data.get('quality_indicators', {})
                    
                    row.update({
                        'total_reviews': statistics.get('total_reviews', 0),
                        'rating_medio': statistics.get('average_rating', 0),
                        'rating_5_estrelas': statistics.get('rating_distribution', {}).get(5, 0),
                        'rating_4_estrelas': statistics.get('rating_distribution', {}).get(4, 0),
                        'rating_3_estrelas': statistics.get('rating_distribution', {}).get(3, 0),
                        'rating_2_estrelas': statistics.get('rating_distribution', {}).get(2, 0),
                        'rating_1_estrela': statistics.get('rating_distribution', {}).get(1, 0),
                        'tem_reviews': len(reviews_data.get('reviews', [])) > 0,
                        
                        # Campos adicionais de análise de reviews
                        'reviews_com_texto': statistics.get('reviews_with_text', 0),
                        'reviews_com_imagens': statistics.get('reviews_with_images', 0),
                        'cobertura_texto_reviews': round(statistics.get('text_coverage', 0), 1),
                        'tamanho_medio_review': round(statistics.get('avg_text_length', 0), 1),
                        'avaliacoes_positivas': quality.get('high_ratings', 0),
                        'avaliacoes_negativas': quality.get('low_ratings', 0),
                        'avaliacoes_neutras': quality.get('neutral_ratings', 0),
                        'metodo_coleta_reviews': reviews_data.get('collection_method', 'standard')
                    })
                    reviews_added = True
                
                # Se não há reviews específicos, tentar usar dados de avaliacao da extração detalhada
                elif include_reviews and 'avaliacao' in produto and produto['avaliacao'] != 'N/A':
                    avaliacao = produto['avaliacao']
                    if isinstance(avaliacao, dict):
                        rating = avaliacao.get('rating', 0)
                        count = avaliacao.get('count', 0) or avaliacao.get('review_count', 0)
                        reviews_with_comment = avaliacao.get('reviews_with_comment', 0)
                        pictures_quantity = avaliacao.get('pictures_quantity', 0)
                        
                        # Converter rating para float se necessário
                        try:
                            rating = float(rating) if rating else 0
                            count = int(count) if count else 0
                            reviews_with_comment = int(reviews_with_comment) if reviews_with_comment else 0
                            pictures_quantity = int(pictures_quantity) if pictures_quantity else 0
                        except (ValueError, TypeError):
                            rating = count = reviews_with_comment = pictures_quantity = 0
                        
                        row.update({
                            'total_reviews': count,
                            'rating_medio': rating,
                            'rating_5_estrelas': 0,  # Dados detalhados não disponíveis
                            'rating_4_estrelas': 0,
                            'rating_3_estrelas': 0,
                            'rating_2_estrelas': 0,
                            'rating_1_estrela': 0,
                            'tem_reviews': count > 0,
                            'reviews_com_texto': reviews_with_comment,
                            'reviews_com_imagens': pictures_quantity,
                            'cobertura_texto_reviews': 0,
                            'tamanho_medio_review': 0,
                            'avaliacoes_positivas': 0,
                            'avaliacoes_negativas': 0,
                            'avaliacoes_neutras': 0,
                            'metodo_coleta_reviews': 'extracao_detalhada'
                        })
                        reviews_added = True
                
                # Se não há dados de reviews de nenhuma fonte
                if not reviews_added:
                    row.update({
                        'total_reviews': 0,
                        'rating_medio': 0,
                        'rating_5_estrelas': 0,
                        'rating_4_estrelas': 0,
                        'rating_3_estrelas': 0,
                        'rating_2_estrelas': 0,
                        'rating_1_estrela': 0,
                        'tem_reviews': False,
                        'reviews_com_texto': 0,
                        'reviews_com_imagens': 0,
                        'cobertura_texto_reviews': 0,
                        'tamanho_medio_review': 0,
                        'avaliacoes_positivas': 0,
                        'avaliacoes_negativas': 0,
                        'avaliacoes_neutras': 0,
                        'metodo_coleta_reviews': 'nao_coletado'
                    })
                
                # Adicionar campos de qualidade da extração
                row.update({
                    'qualidade_extracao_detalhada': produto.get('detalhes_qualidade', 'nao_realizada'),
                    'metodo_extracao_detalhada': produto.get('extraction_method', 'nao_realizada'),
                    'score_qualidade_detalhes': produto.get('quality_score', 0),
                    'tamanho_resposta_bytes': produto.get('response_size', 0),
                    'status_resposta_http': produto.get('response_status', 0)
                })
                
                dataset_rows.append(row)
            
            # Criar DataFrame e salvar
            df = pd.DataFrame(dataset_rows)
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"Dataset gerado com sucesso: {filename}")
            logger.info(f"Total de produtos: {len(df)}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao gerar dataset CSV: {str(e)}")
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
            
            logger.info(f"Análise de reviews concluída: {average_rating:.1f}⭐ média, {reviews_with_text} com texto")
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
