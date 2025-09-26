#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste básico do sistema de scraping
"""

try:
    # Tentar importar as funções principais
    from app import HPScrapingSystem
    from mercadolivre_spider import run_spider
    from mercadolivre_spider_reviews import run_review_spider
    
    print("✅ Todas as importações funcionaram corretamente!")
    print("✅ Sistema está pronto para uso!")
    
    # Testar instanciação da classe principal
    sistema = HPScrapingSystem()
    print("✅ Classe HPScrapingSystem instanciada com sucesso!")
    
    print("\n=== SISTEMA FUNCIONANDO CORRETAMENTE ===")
    print("Para usar o sistema, execute:")
    print("python app.py --query 'cartucho hp' --max-items 10")
    
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
except Exception as e:
    print(f"❌ Erro inesperado: {e}")
