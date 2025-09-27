#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste do scraper corrigido - Mercado Livre HP
"""

import sys
import os
import logging
from datetime import datetime

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_spider_corrected():
    """Testa o spider corrigido"""
    try:
        logger.info("=== TESTE DO SPIDER CORRIGIDO ===")
        logger.info(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Importar o spider
        from mercadolivre_spider import run_spider
        
        logger.info("Spider importado com sucesso!")
        
        # Parâmetros de teste
        query = "cartucho hp"
        max_items = 10
        extract_images = True
        
        logger.info(f"Iniciando teste com query='{query}', max_items={max_items}")
        
        # Executar spider
        results, urls_used = run_spider(
            query=query,
            extract_images=extract_images,
            sort_by='relevance',
            condition='all',
            max_items=max_items
        )
        
        logger.info(f"Teste concluído!")
        logger.info(f"Resultados obtidos: {len(results) if results else 0}")
        logger.info(f"URLs utilizadas: {len(urls_used) if urls_used else 0}")
        
        if urls_used:
            logger.info(f"Primeira URL usada: {urls_used[0]}")
        
        if results:
            logger.info("=== AMOSTRA DOS RESULTADOS ===")
            for i, product in enumerate(results[:3], 1):
                logger.info(f"Produto {i}:")
                logger.info(f"  Título: {product.get('TITULO PRODUTO', 'N/A')}")
                logger.info(f"  Preço: {product.get('PREÇO', 'N/A')}")
                logger.info(f"  Link: {product.get('LINK', 'N/A')}")
                logger.info(f"  Vendedor: {product.get('VENDEDOR', 'N/A')}")
                logger.info("  ---")
        
        # Resultados do teste
        success = len(results) > 0 if results else False
        logger.info("=== RESULTADO DO TESTE ===")
        logger.info(f"Status: {'SUCESSO' if success else 'FALHA'}")
        logger.info(f"Produtos coletados: {len(results) if results else 0}")
        logger.info(f"Taxa de sucesso: {len(results)/max_items*100 if results and max_items > 0 else 0:.1f}%")
        
        return success, results, urls_used
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {str(e)}")
        logger.exception("Detalhes do erro:")
        return False, None, None

if __name__ == "__main__":
    success, results, urls = test_spider_corrected()
    sys.exit(0 if success else 1)

