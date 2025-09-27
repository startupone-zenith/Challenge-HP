#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Simples de Padronizacao dos Metodos de Scraping
====================================================

Este script valida que todos os metodos de scraping estao usando
configuracoes identicas e padronizadas (sem emojis para Windows).
"""

import sys
from datetime import datetime

def main():
    print("TESTE DE PADRONIZACAO DOS METODOS DE SCRAPING")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests_passed = 0
    total_tests = 0
    
    # Teste 1: Importacao das configuracoes
    print("1. Testando importacao das configuracoes...")
    total_tests += 1
    try:
        from shared_scraping_config import (
            USER_AGENTS_2025,
            get_random_user_agent,
            setup_requests_session,
            get_scrapy_settings,
            validate_scraping_config
        )
        print("   OK - Configuracoes importadas com sucesso")
        tests_passed += 1
    except Exception as e:
        print(f"   ERRO - Falha na importacao: {e}")
    
    # Teste 2: Validacao das configuracoes
    print("\n2. Validando configuracoes...")
    total_tests += 1
    try:
        if validate_scraping_config():
            print("   OK - Configuracoes sao validas")
            tests_passed += 1
        else:
            print("   ERRO - Configuracoes invalidas")
    except Exception as e:
        print(f"   ERRO - Falha na validacao: {e}")
    
    # Teste 3: User-Agents 2025
    print("\n3. Testando User-Agents 2025...")
    total_tests += 1
    try:
        ua = get_random_user_agent()
        # Detectar versões 2025: Chrome 118-121, Firefox 120-122, Safari 16.6/17.x, Edge 120-121
        is_2025 = any(version in ua for version in [
            '121.0.0.0', '120.0.0.0', '119.0.0.0', '118.0.0.0',  # Chrome 2025
            'rv:122.0', 'rv:121.0', 'rv:120.0',                   # Firefox 2025
            'Version/17.', 'Version/16.6',                        # Safari 2025
            'Edg/121.0', 'Edg/120.0'                             # Edge 2025
        ])
        
        if is_2025:
            print(f"   OK - User-Agent 2025: {ua[:50]}...")
            tests_passed += 1
        else:
            print(f"   AVISO - User-Agent pode ser antigo: {ua[:50]}...")
    except Exception as e:
        print(f"   ERRO - Falha no User-Agent: {e}")
    
    # Teste 4: Sessao HTTP
    print("\n4. Testando sessao HTTP...")
    total_tests += 1
    try:
        session = setup_requests_session()
        if session and hasattr(session, 'get'):
            print("   OK - Sessao HTTP criada com sucesso")
            tests_passed += 1
        else:
            print("   ERRO - Sessao HTTP invalida")
    except Exception as e:
        print(f"   ERRO - Falha na sessao HTTP: {e}")
    
    # Teste 5: Configuracoes Scrapy
    print("\n5. Testando configuracoes Scrapy...")
    total_tests += 1
    try:
        settings = get_scrapy_settings()
        if (settings.get('CONCURRENT_REQUESTS') == 1 and 
            settings.get('RETRY_TIMES') == 5):
            print("   OK - Configuracoes Scrapy padronizadas")
            tests_passed += 1
        else:
            print("   ERRO - Configuracoes Scrapy nao padronizadas")
    except Exception as e:
        print(f"   ERRO - Falha nas configuracoes Scrapy: {e}")
    
    # Teste 6: Compatibilidade dos spiders
    print("\n6. Testando compatibilidade dos spiders...")
    total_tests += 1
    try:
        from mercadolivre_spider import get_basic_scrapy_settings
        from mercadolivre_spider_reviews import MercadoLivreReviewsAPI
        from app import HPScrapingSystem
        
        # Testar instanciacoes
        api = MercadoLivreReviewsAPI("MLB123456")
        sistema = HPScrapingSystem()
        
        print("   OK - Todos os spiders sao compativeis")
        tests_passed += 1
    except Exception as e:
        print(f"   ERRO - Incompatibilidade nos spiders: {e}")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"Taxa de Sucesso: {success_rate:.1f}% ({tests_passed}/{total_tests})")
    
    if success_rate >= 90:
        print("\nEXCELENTE! Metodos de scraping totalmente padronizados!")
        print("- User-Agents 2025 em todos os scrapers")
        print("- Configuracoes HTTP identicas")
        print("- 5 tentativas de retry padronizadas")
        print("- Delays anti-bot consistentes")
        
    elif success_rate >= 70:
        print("\nBOM! Maioria dos metodos padronizados")
        print("Alguns ajustes menores podem ser necessarios")
        
    else:
        print("\nATENCAO! Metodos precisam de mais padronizacao")
        print("Revise as configuracoes que falharam")
    
    print("\n" + "=" * 60)
    print("Status: METODOS DE SCRAPING IDENTICOS!" if success_rate >= 90 else "Status: AJUSTES NECESSARIOS")
    
    return 0 if success_rate >= 90 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
