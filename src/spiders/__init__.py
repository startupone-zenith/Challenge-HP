"""
Módulo spiders - Spiders do Scrapy para coleta de dados
"""

from .mercadolivre_spider import MercadoLivreSpider, run_spider, run_product_details_spider
from .mercadolivre_spider_reviews import run_review_spider

__all__ = [
    'MercadoLivreSpider',
    'run_spider', 
    'run_product_details_spider',
    'run_review_spider'
]
