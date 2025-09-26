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
from datetime import datetime
import argparse

# Importar os spiders
from mercadolivre_spider import run_spider, run_product_details_spider
from mercadolivre_spider_reviews import run_review_spider

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class HPScrapingSystem:
    """Sistema simplificado para scraping e geração de datasets"""
    
    def __init__(self):
        self.produtos = []
        self.reviews_data = {}
        
    def executar_scraping_produtos(self, query, max_items=None, extract_images=False, 
                                 sort_by='relevance', condition='all'):
        """
        Executa scraping de produtos no Mercado Livre
        
        Args:
            query (str): Termo de busca
            max_items (int): Máximo de itens para coletar
            extract_images (bool): Se deve extrair imagens
            sort_by (str): Ordenação ('relevance', 'price_asc', 'price_desc')
            condition (str): Condição ('all', 'new', 'used')
        
        Returns:
            list: Lista de produtos coletados
        """
        logger.info(f"Iniciando scraping para: {query}")
        logger.info(f"Parâmetros: max_items={max_items}, images={extract_images}, sort={sort_by}")
        
        try:
            # Executar spider principal
            produtos, urls_used = run_spider(
                query=query,
                extract_images=extract_images,
                sort_by=sort_by,
                condition=condition,
                max_items=max_items
            )
            
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
        
        Args:
            product_id (str): ID do produto no Mercado Livre
            max_reviews (int): Máximo de reviews para coletar
        
        Returns:
            dict: Dados das reviews coletadas
        """
        logger.info(f"Coletando reviews para produto: {product_id}")
        
        try:
            reviews_data = run_review_spider(product_id, max_reviews=max_reviews)
            
            if reviews_data and 'reviews' in reviews_data:
                logger.info(f"Coletadas {len(reviews_data['reviews'])} reviews")
                self.reviews_data[product_id] = reviews_data
                return reviews_data
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
                row = {
                    'id': produto.get('id', ''),
                    'titulo': produto.get('title', ''),
                    'preco': produto.get('price', ''),
                    'preco_original': produto.get('original_price', ''),
                    'desconto': produto.get('discount', ''),
                    'vendedor': produto.get('seller', ''),
                    'reputacao_vendedor': produto.get('seller_reputation', ''),
                    'condicao': produto.get('condition', ''),
                    'frete_gratis': produto.get('free_shipping', False),
                    'link': produto.get('link', ''),
                    'imagem_url': produto.get('image_url', ''),
                    'localizacao': produto.get('location', ''),
                    'vendas': produto.get('sales', ''),
                    'data_coleta': produto.get('scraped_at', datetime.now().isoformat())
                }
                
                # Adicionar dados de reviews se disponível
                if include_reviews and 'reviews_data' in produto:
                    reviews_data = produto['reviews_data']
                    row.update({
                        'total_reviews': reviews_data.get('total_reviews', 0),
                        'rating_medio': reviews_data.get('average_rating', 0),
                        'rating_5_estrelas': reviews_data.get('rating_distribution', {}).get('5', 0),
                        'rating_4_estrelas': reviews_data.get('rating_distribution', {}).get('4', 0),
                        'rating_3_estrelas': reviews_data.get('rating_distribution', {}).get('3', 0),
                        'rating_2_estrelas': reviews_data.get('rating_distribution', {}).get('2', 0),
                        'rating_1_estrela': reviews_data.get('rating_distribution', {}).get('1', 0),
                        'tem_reviews': len(reviews_data.get('reviews', [])) > 0
                    })
                else:
                    row.update({
                        'total_reviews': 0,
                        'rating_medio': 0,
                        'rating_5_estrelas': 0,
                        'rating_4_estrelas': 0,
                        'rating_3_estrelas': 0,
                        'rating_2_estrelas': 0,
                        'rating_1_estrela': 0,
                        'tem_reviews': False
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
