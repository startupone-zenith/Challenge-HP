#!/usr/bin/env python3
"""
Teste da Nova Funcionalidade de Extração Detalhada do MercadoLivre

Este script demonstra como usar a nova função extract_detailed_product_info()
que extrai todos os campos solicitados:
- Nome do produto
- Condição do Produto  
- Preço
- Desconto
- Frete Grátis ou Não
- Tempo de entrega
- Nome da loja
- Quantidade de vendas da loja
- Quantidade de vendas do produto
- Devolução grátis, Sim ou não
- Compra Garantida Sim ou Não
- Tempo de garantia
- Descrição do produto
- Características Principais
- Outros
- Fotos do produto
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
import json
from datetime import datetime
import logging
import sys
import os

# Adicionar o diretório atual ao path para importar o spider
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mercadolivre_spider import MercadoLivreSpider

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teste_extracao_detalhada.log'),
        logging.StreamHandler()
    ]
)

class TestDetailedExtractionSpider(MercadoLivreSpider):
    """Spider de teste para a nova funcionalidade de extração detalhada"""
    name = 'test_detailed_extraction'
    
    def __init__(self, test_url=None, *args, **kwargs):
        super(TestDetailedExtractionSpider, self).__init__(*args, **kwargs)
        self.test_url = test_url or "https://www.mercadolivre.com.br/cartucho-hp-3ed68a-n-712-magenta-29ml-hp/p/MLB22536185"
        self.start_urls = [self.test_url]
        self.detailed_results = []
        
    def start_requests(self):
        """Fazer request para a URL de teste"""
        logging.info(f"Testando extração detalhada da URL: {self.test_url}")
        yield scrapy.Request(
            url=self.test_url,
            callback=self.test_detailed_extraction,
            headers=self.get_random_headers(),
            meta={'dont_cache': True}
        )
    
    def test_detailed_extraction(self, response):
        """Testar a nova função de extração detalhada"""
        logging.info(f"Iniciando teste de extração detalhada para: {response.url}")
        
        # Chamar a nova função de extração detalhada
        detailed_info = self.extract_detailed_product_info(response)
        
        if detailed_info:
            logging.info("=== EXTRAÇÃO DETALHADA REALIZADA COM SUCESSO ===")
            
            # Exibir todos os campos extraídos
            print("\n" + "="*60)
            print("RESULTADO DA EXTRAÇÃO DETALHADA")
            print("="*60)
            
            print(f"\n📦 PRODUTO:")
            print(f"  • Nome: {detailed_info.get('nome_produto', 'N/A')}")
            print(f"  • Condição: {detailed_info.get('condicao_produto', 'N/A')}")
            print(f"  • URL: {detailed_info.get('url', 'N/A')}")
            
            print(f"\n💰 PREÇOS E DESCONTOS:")
            print(f"  • Preço: {detailed_info.get('preco', 'N/A')}")
            print(f"  • Desconto: {detailed_info.get('desconto', 'N/A')}")
            
            print(f"\n🚚 ENTREGA:")
            print(f"  • Frete Grátis: {detailed_info.get('frete_gratis', 'N/A')}")
            print(f"  • Tempo de Entrega: {detailed_info.get('tempo_entrega', 'N/A')}")
            
            print(f"\n🏪 LOJA:")
            print(f"  • Nome da Loja: {detailed_info.get('nome_loja', 'N/A')}")
            print(f"  • Vendas da Loja: {detailed_info.get('vendas_loja', 'N/A')}")
            print(f"  • Vendas do Produto: {detailed_info.get('vendas_produto', 'N/A')}")
            
            print(f"\n🛡️ GARANTIAS:")
            print(f"  • Devolução Grátis: {detailed_info.get('devolucao_gratis', 'N/A')}")
            print(f"  • Compra Garantida: {detailed_info.get('compra_garantida', 'N/A')}")
            print(f"  • Tempo de Garantia: {detailed_info.get('tempo_garantia', 'N/A')}")
            
            print(f"\n📝 DESCRIÇÃO:")
            desc = detailed_info.get('descricao_produto', 'N/A')
            print(f"  • {desc[:200]}{'...' if len(desc) > 200 else ''}")
            
            print(f"\n⚙️ CARACTERÍSTICAS PRINCIPAIS:")
            specs = detailed_info.get('caracteristicas_principais', ['N/A'])
            for i, spec in enumerate(specs[:5], 1):  # Mostrar apenas as primeiras 5
                print(f"  {i}. {spec}")
            if len(specs) > 5:
                print(f"  ... e mais {len(specs)-5} características")
            
            print(f"\n📸 FOTOS ({len(detailed_info.get('fotos_produto', []))}):")
            photos = detailed_info.get('fotos_produto', ['N/A'])
            for i, photo in enumerate(photos[:3], 1):  # Mostrar apenas as primeiras 3
                print(f"  {i}. {photo[:80]}{'...' if len(photo) > 80 else ''}")
            if len(photos) > 3:
                print(f"  ... e mais {len(photos)-3} fotos")
            
            print(f"\n⭐ AVALIAÇÕES:")
            rating = detailed_info.get('avaliacao', 'N/A')
            if isinstance(rating, dict):
                print(f"  • Rating: {rating.get('rating', 'N/A')}/5")
                print(f"  • Total de Ratings: {rating.get('count', 'N/A')}")
                print(f"  • Reviews: {rating.get('review_count', 'N/A')}")
            else:
                print(f"  • Rating: {rating}")
            
            print(f"\n📊 INFORMAÇÕES ADICIONAIS:")
            others = detailed_info.get('outros', {})
            for key, value in others.items():
                print(f"  • {key}: {value}")
            
            print("\n" + "="*60)
            
            # Salvar resultado completo em JSON
            self.detailed_results.append(detailed_info)
            
            # Salvar em arquivo JSON
            output_filename = f"resultado_extracao_detalhada_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(detailed_info, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Resultado detalhado salvo em: {output_filename}")
            print(f"\n✅ Resultado completo salvo em: {output_filename}")
            
            return detailed_info
            
        else:
            logging.error("FALHA na extração detalhada!")
            print("\n❌ FALHA na extração detalhada!")
            return None

def run_detailed_extraction_test(test_url=None):
    """
    Executa o teste de extração detalhada
    
    Args:
        test_url (str): URL do produto para testar (opcional)
    """
    
    # URLs de teste padrão
    if not test_url:
        test_urls = [
            "https://www.mercadolivre.com.br/cartucho-hp-3ed68a-n-712-magenta-29ml-hp/p/MLB22536185",
            "https://produto.mercadolivre.com.br/MLB-5691756754-cartucho-hp-3ed68a-n-712-magenta-29ml-hp-_JM"
        ]
        test_url = test_urls[0]  # Usar a primeira URL como padrão
    
    logging.info("=== INICIANDO TESTE DE EXTRAÇÃO DETALHADA ===")
    print("🚀 Iniciando teste de extração detalhada do MercadoLivre...")
    print(f"URL de teste: {test_url}")
    
    # Configurar Scrapy
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'COOKIES_ENABLED': False,
        'TELNETCONSOLE_ENABLED': False,
        'LOG_LEVEL': 'INFO'
    })
    
    # Executar spider de teste
    process.crawl(TestDetailedExtractionSpider, test_url=test_url)
    process.start()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Teste da Extração Detalhada do MercadoLivre")
    parser.add_argument('--url', type=str, help='URL do produto para testar')
    
    args = parser.parse_args()
    
    try:
        run_detailed_extraction_test(args.url)
    except KeyboardInterrupt:
        print("\n⏹️  Teste interrompido pelo usuário")
    except Exception as e:
        logging.error(f"Erro durante o teste: {e}")
        print(f"\n❌ Erro durante o teste: {e}")
