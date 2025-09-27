#!/usr/bin/env python3
"""
Exemplo de Uso da Nova Funcionalidade de Extração Detalhada

Este exemplo mostra como integrar a nova funcionalidade no seu código.
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mercadolivre_spider import MercadoLivreSpider
from scrapy.crawler import CrawlerProcess
import json
import logging

def exemplo_uso_simples():
    """Exemplo simples de como usar a extração detalhada"""
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # URL do produto para teste
    produto_url = "https://www.mercadolivre.com.br/cartucho-hp-3ed68a-n-712-magenta-29ml-hp/p/MLB22536185"
    
    class ExemploSpider(MercadoLivreSpider):
        name = 'exemplo_detalhado'
        
        def start_requests(self):
            yield scrapy.Request(
                url=produto_url,
                callback=self.processar_produto_detalhado
            )
        
        def processar_produto_detalhado(self, response):
            # Usar a nova função de extração detalhada
            detalhes = self.extract_detailed_product_info(response)
            
            if detalhes:
                print("✅ Extração realizada com sucesso!")
                print(f"Produto: {detalhes.get('nome_produto')}")
                print(f"Preço: {detalhes.get('preco')}")
                print(f"Loja: {detalhes.get('nome_loja')}")
                
                # Salvar em arquivo
                with open('produto_detalhado.json', 'w', encoding='utf-8') as f:
                    json.dump(detalhes, f, ensure_ascii=False, indent=2)
                
                return detalhes
            else:
                print("❌ Falha na extração")
    
    # Executar
    process = CrawlerProcess()
    process.crawl(ExemploSpider)
    process.start()

if __name__ == "__main__":
    exemplo_uso_simples()
