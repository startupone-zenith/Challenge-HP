#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações Compartilhadas de Scraping - Sistema HP
====================================================

Este módulo centraliza todas as configurações de scraping para garantir
consistência entre mercadolivre_spider.py e mercadolivre_spider_reviews.py

Versão: 3.0 (Sprint 3)
Data: Setembro 2025
"""

import random
import time
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# USER-AGENTS PADRONIZADOS - ATUALIZADOS PARA 2025
# =============================================================================

USER_AGENTS_2025 = [
    # Chrome Windows (versões mais recentes)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    
    # Chrome macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    
    # Firefox Windows (versões mais recentes)
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    
    # Safari macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    
    # Edge Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    
    # Mobile User Agents para variação
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36',
]

# =============================================================================
# HEADERS PADRONIZADOS - SIMULAÇÃO REALISTA DE NAVEGADOR
# =============================================================================

STANDARD_BROWSER_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
}

# Headers específicos para API requests
API_HEADERS_BASE = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

# =============================================================================
# CONFIGURAÇÕES DE RETRY PADRONIZADAS
# =============================================================================

STANDARD_RETRY_CONFIG = {
    'total': 5,                    # Máximo 5 tentativas (padronizado)
    'backoff_factor': 0.5,         # Backoff exponencial
    'status_forcelist': [429, 500, 502, 503, 504, 408, 403],  # Códigos para retry
    'allowed_methods': ["GET", "POST"]  # Métodos permitidos
}

# =============================================================================
# CONFIGURAÇÕES HTTP PADRONIZADAS
# =============================================================================

STANDARD_HTTP_CONFIG = {
    'pool_connections': 20,        # Pool de conexões
    'pool_maxsize': 50,           # Máximo de conexões por pool
    'pool_block': False,          # Não bloquear quando pool estiver cheio
    'timeout': (5, 15),           # (connect_timeout, read_timeout)
    'cache_ttl': 300              # 5 minutos de cache
}

# =============================================================================
# DELAYS PADRONIZADOS - CONFIGURAÇÕES ANTI-BOT
# =============================================================================

ANTI_BOT_DELAYS = {
    'base_delay_min': 5.0,        # Delay mínimo base
    'base_delay_max': 10.0,       # Delay máximo base
    'initial_delay_min': 2.0,     # Delay inicial mínimo
    'initial_delay_max': 5.0,     # Delay inicial máximo
    'retry_delay_base': 15.0,     # Base para delays de retry
    'retry_delay_increment': 10.0, # Incremento por tentativa
    'session_renewal': 1800       # 30 minutos para renovar sessão
}

# =============================================================================
# SELETORES CSS PADRONIZADOS
# =============================================================================

MERCADOLIVRE_SELECTORS = {
    'product_containers': [
        'ol.ui-search-results li',
        '.ui-search-results .ui-search-result',
        'li.ui-search-layout__item',
        '.ui-search-layout__item',
        'div.andes-card.poly-card',
        '.ui-search-result',
        '[data-testid="search-result"]',
        'article[data-testid="results-item"]',
    ],
    'titles': [
        'h2.poly-box a::text',
        'h2.ui-search-item__title a::text',
        '.ui-search-item__title-label::text',
        '.ui-search-item__title::text',
        '.poly-component__title::text',
    ],
    'prices': [
        '.andes-money-amount__fraction',
        '.poly-price__current .andes-money-amount__fraction',
        '.ui-search-price .andes-money-amount__fraction',
        '.price-tag-fraction',
    ],
    'links': [
        'h2.poly-box a::attr(href)',
        'a.ui-search-item__group__element::attr(href)',
        'h2.ui-search-item__title a::attr(href)',
        '.ui-search-item__title a::attr(href)',
    ]
}

# =============================================================================
# FUNÇÕES UTILITÁRIAS PADRONIZADAS
# =============================================================================

def get_random_user_agent():
    """Retorna um User-Agent aleatório da lista padronizada"""
    return random.choice(USER_AGENTS_2025)

def get_browser_specific_headers(user_agent):
    """Retorna headers específicos baseados no navegador"""
    headers = STANDARD_BROWSER_HEADERS.copy()
    headers['User-Agent'] = user_agent
    
    if 'Chrome' in user_agent:
        headers.update({
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="121", "Google Chrome";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
    elif 'Firefox' in user_agent:
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        })
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-br',
        })
    
    return headers

def get_api_headers():
    """Retorna headers padronizados para requisições de API"""
    headers = API_HEADERS_BASE.copy()
    headers['User-Agent'] = get_random_user_agent()
    return headers

def setup_requests_session():
    """Configura uma sessão HTTP padronizada com retry"""
    import requests
    
    session = requests.Session()
    
    # Configurar retry strategy padronizada
    retry_strategy = Retry(**STANDARD_RETRY_CONFIG)
    
    # Configurar adaptador HTTP
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=STANDARD_HTTP_CONFIG['pool_connections'],
        pool_maxsize=STANDARD_HTTP_CONFIG['pool_maxsize'],
        pool_block=STANDARD_HTTP_CONFIG['pool_block']
    )
    
    # Montar adaptadores
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers padrão
    session.headers.update(get_api_headers())
    
    return session

def get_scrapy_settings():
    """Retorna configurações padronizadas do Scrapy"""
    return {
        'USER_AGENT': get_random_user_agent(),
        'ROBOTSTXT_OBEY': False,
        
        # Configurações anti-detecção padronizadas
        'CONCURRENT_REQUESTS': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        
        # Delays padronizados
        'DOWNLOAD_DELAY': random.uniform(
            ANTI_BOT_DELAYS['base_delay_min'], 
            ANTI_BOT_DELAYS['base_delay_max']
        ),
        'RANDOMIZE_DOWNLOAD_DELAY': 1.0,
        
        # AutoThrottle padronizado
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': random.uniform(
            ANTI_BOT_DELAYS['initial_delay_min'], 
            ANTI_BOT_DELAYS['initial_delay_max']
        ),
        'AUTOTHROTTLE_MAX_DELAY': 30,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
        'AUTOTHROTTLE_DEBUG': False,
        
        # Headers e cookies
        'COOKIES_ENABLED': True,
        'COOKIES_DEBUG': False,
        
        # Retry policy padronizada
        'RETRY_ENABLED': True,
        'RETRY_TIMES': STANDARD_RETRY_CONFIG['total'],
        'RETRY_HTTP_CODES': STANDARD_RETRY_CONFIG['status_forcelist'],
        
        # Timeouts padronizados
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_WARNSIZE': 0,
        
        # Logging
        'LOG_LEVEL': 'INFO',
        
        # Middlewares padronizados
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
        },
        
        # Cache e outras configurações
        'HTTPCACHE_ENABLED': False,
        'DUPEFILTER_DEBUG': False,
        'DEFAULT_REQUEST_HEADERS': STANDARD_BROWSER_HEADERS,
    }

def calculate_adaptive_delay(attempt_number=1):
    """Calcula delay adaptativo baseado no número de tentativas"""
    if attempt_number <= 1:
        return random.uniform(
            ANTI_BOT_DELAYS['initial_delay_min'],
            ANTI_BOT_DELAYS['initial_delay_max']
        )
    
    base_delay = ANTI_BOT_DELAYS['retry_delay_base']
    increment = ANTI_BOT_DELAYS['retry_delay_increment']
    calculated_delay = base_delay + (increment * (attempt_number - 1))
    
    # Adicionar randomização (±25%)
    variation = calculated_delay * 0.25
    return random.uniform(calculated_delay - variation, calculated_delay + variation)

# =============================================================================
# LOGGING PADRONIZADO
# =============================================================================

def setup_standard_logging(name, log_file='scraper.log'):
    """Configura logging padronizado para todos os scrapers"""
    import sys
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Formato padronizado
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# =============================================================================
# VALIDAÇÃO DE CONFIGURAÇÕES
# =============================================================================

def validate_scraping_config():
    """Valida se todas as configurações estão corretas"""
    try:
        # Validar User-Agents
        assert len(USER_AGENTS_2025) >= 15, "Lista de User-Agents muito pequena"
        
        # Validar Headers
        assert 'User-Agent' in STANDARD_BROWSER_HEADERS or 'Accept' in STANDARD_BROWSER_HEADERS
        
        # Validar configurações de delay
        assert ANTI_BOT_DELAYS['base_delay_min'] < ANTI_BOT_DELAYS['base_delay_max']
        
        # Validar seletores
        assert len(MERCADOLIVRE_SELECTORS['product_containers']) >= 5
        
        return True
    except Exception as e:
        logging.error(f"Erro na validação das configurações: {e}")
        return False

# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

# Validar configurações ao importar o módulo
if __name__ == "__main__":
    if validate_scraping_config():
        print("✅ Configurações de scraping validadas com sucesso!")
    else:
        print("❌ Erro na validação das configurações de scraping!")
else:
    validate_scraping_config()

