# =============================================================================
# CONFIGURAÇÕES DE PERFORMANCE OTIMIZADAS PARA SCRAPY
# =============================================================================
# Este arquivo centraliza todas as configurações de alta performance
# baseadas na documentação oficial do Scrapy

def get_optimized_spider_settings():
    """
    Retorna configurações otimizadas para o spider principal (busca de produtos)
    Focado em alta concorrência e velocidade máxima
    """
    return {
        # ============================================================================
        # CONFIGURAÇÕES BÁSICAS
        # ============================================================================
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'TELNETCONSOLE_ENABLED': False,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'WARNING',  # Reduzir logs para melhor performance
        
        # ============================================================================
        # CONFIGURAÇÕES DE CONCORRÊNCIA - ALTA PERFORMANCE
        # ============================================================================
        
        # Requisições concorrentes (aumentado significativamente)
        'CONCURRENT_REQUESTS': 32,  # Padrão: 16, Otimizado: 32
        'CONCURRENT_REQUESTS_PER_DOMAIN': 16,  # Padrão: 8, Otimizado: 16
        'CONCURRENT_REQUESTS_PER_IP': 8,  # Padrão: 0, Otimizado: 8
        
        # Processamento de itens concorrente
        'CONCURRENT_ITEMS': 200,  # Padrão: 100, Otimizado: 200
        
        # Pool de threads do reactor
        'REACTOR_THREADPOOL_MAXSIZE': 20,  # Padrão: 10, Otimizado: 20
        
        # ============================================================================
        # CONFIGURAÇÕES DE DOWNLOAD OTIMIZADAS
        # ============================================================================
        
        # Timeouts otimizados (mais agressivos)
        'DOWNLOAD_TIMEOUT': 15,  # Padrão: 180, Otimizado: 15
        'DOWNLOAD_DELAY': 0.1,  # Padrão: 0, Otimizado: 0.1s (balanceamento)
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,  # Randomização: 0.05-0.15s
        
        # Configurações de tamanho de download
        'DOWNLOAD_MAXSIZE': 1073741824,  # 1GB (padrão: 1GB)
        'DOWNLOAD_WARNSIZE': 33554432,   # 32MB (padrão: 32MB)
        'DOWNLOAD_FAIL_ON_DATALOSS': False,  # Não falhar em perda de dados menor
        
        # ============================================================================
        # CACHE HTTP PARA ALTA PERFORMANCE
        # ============================================================================
        
        # Habilitar cache HTTP para evitar requisições desnecessárias
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 3600,  # Cache por 1 hora
        'HTTPCACHE_DIR': 'httpcache_mercadolivre',
        'HTTPCACHE_IGNORE_HTTP_CODES': [503, 504, 505, 500, 408, 429],
        'HTTPCACHE_STORAGE': 'scrapy.extensions.httpcache.FilesystemCacheStorage',
        
        # ============================================================================
        # CONFIGURAÇÕES DE RETRY OTIMIZADAS
        # ============================================================================
        
        # Retry mais agressivo mas com limite
        'RETRY_TIMES': 2,  # Padrão: 2, Mantido
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'RETRY_PRIORITY_ADJUST': -1,  # Prioridade menor para retries
        
        # ============================================================================
        # CONFIGURAÇÕES DE CONEXÃO HTTP OTIMIZADAS
        # ============================================================================
        
        # Pool de conexões HTTP persistentes
        'DOWNLOAD_HANDLERS': {
            'http': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
            'https': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
        },
        
        # Headers otimizados para performance
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        
        # ============================================================================
        # CONFIGURAÇÕES DE DNS OTIMIZADAS
        # ============================================================================
        
        # Cache DNS para melhor performance
        'DNSCACHE_ENABLED': True,
        'DNSCACHE_SIZE': 10000,  # Cache maior
        'DNS_TIMEOUT': 5,  # Timeout DNS mais agressivo
        
        # ============================================================================
        # CONFIGURAÇÕES DE MEMÓRIA E RECURSOS
        # ============================================================================
        
        # Limite de memória (desabilitado para máxima performance)
        'MEMUSAGE_ENABLED': False,
        
        # Estatísticas de download otimizadas
        'DOWNLOADER_STATS': True,
        
        # ============================================================================
        # MIDDLEWARES OTIMIZADOS
        # ============================================================================
        
        # Desabilitar middlewares desnecessários para performance
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,  # Desabilitado
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 400,
            'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
            'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
        },
    }

def get_optimized_product_details_settings():
    """
    Retorna configurações otimizadas para o spider de detalhes de produto
    Focado em eficiência para requisições individuais
    """
    return {
        # ============================================================================
        # CONFIGURAÇÕES BÁSICAS
        # ============================================================================
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'TELNETCONSOLE_ENABLED': False,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'WARNING',  # Menos logs
        
        # ============================================================================
        # CONFIGURAÇÕES ESPECÍFICAS PARA PRODUTO INDIVIDUAL
        # ============================================================================
        
        # Configurações específicas para um produto (menos concorrência)
        'CONCURRENT_REQUESTS': 8,  # Menor para detalhes
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'CONCURRENT_ITEMS': 50,
        
        # Timeouts mais agressivos para produto individual
        'DOWNLOAD_TIMEOUT': 10,  # 10 segundos
        'DOWNLOAD_DELAY': 0.05,  # Delay mínimo
        
        # ============================================================================
        # CACHE HTTP PARA DETALHES (MAIS TEMPO DE CACHE)
        # ============================================================================
        
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 7200,  # 2 horas para detalhes
        'HTTPCACHE_DIR': 'httpcache_product_details',
        'HTTPCACHE_IGNORE_HTTP_CODES': [503, 504, 505, 500, 408, 429],
        'HTTPCACHE_STORAGE': 'scrapy.extensions.httpcache.FilesystemCacheStorage',
        
        # ============================================================================
        # DNS E CONEXÕES OTIMIZADAS
        # ============================================================================
        
        'DNSCACHE_ENABLED': True,
        'DNSCACHE_SIZE': 1000,
        'DNS_TIMEOUT': 3,
        
        # Headers otimizados
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        },
        
        # ============================================================================
        # CONFIGURAÇÕES DE RETRY PARA DETALHES
        # ============================================================================
        
        'RETRY_TIMES': 1,  # Menos retries para detalhes
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'RETRY_PRIORITY_ADJUST': -1,
        
        # ============================================================================
        # DESABILITAR RECURSOS DESNECESSÁRIOS
        # ============================================================================
        
        'MEMUSAGE_ENABLED': False,
        'DOWNLOADER_STATS': False,  # Desabilitar stats para detalhes
    }

def get_performance_recommendations():
    """
    Retorna recomendações de performance baseadas na documentação do Scrapy
    """
    return {
        'system_recommendations': [
            'Use SSD para cache HTTP (HTTPCACHE_DIR)',
            'Configure DNS cache no sistema operacional',
            'Use Python 3.8+ para melhor performance asyncio',
            'Configure limite de file descriptors (ulimit -n 65536)',
            'Use pool de conexões HTTP persistentes',
        ],
        
        'monitoring_recommendations': [
            'Monitor memory usage com MEMUSAGE_ENABLED se necessário',
            'Use DOWNLOADER_STATS para monitorar performance',
            'Configure logs específicos para debugging',
            'Monitor timeout rates e ajuste DOWNLOAD_TIMEOUT',
        ],
        
        'scaling_recommendations': [
            'Use Scrapy-Redis para distribuição',
            'Configure AutoThrottle para sites sensíveis',
            'Use proxies rotativos se necessário',
            'Implemente rate limiting personalizado',
        ],
        
        'cache_recommendations': [
            'Use cache HTTP para dados estáticos',
            'Configure TTL baseado na frequência de mudança',
            'Use cache distribuído (Redis) para múltiplos workers',
            'Implemente invalidação de cache inteligente',
        ]
    }

def apply_settings_to_process(settings_dict, scrapy_settings):
    """
    Aplica configurações otimizadas ao objeto settings do Scrapy
    
    Args:
        settings_dict (dict): Dicionário com configurações
        scrapy_settings: Objeto settings do Scrapy
    """
    for key, value in settings_dict.items():
        scrapy_settings.set(key, value)
    
    return scrapy_settings

# =============================================================================
# CONFIGURAÇÕES ESPECÍFICAS POR CENÁRIO
# =============================================================================

def get_high_volume_settings():
    """
    Configurações para cenários de alto volume (>1000 produtos)
    """
    base_settings = get_optimized_spider_settings()
    
    # Ajustes para alto volume
    base_settings.update({
        'CONCURRENT_REQUESTS': 64,  # Ainda mais concorrência
        'CONCURRENT_REQUESTS_PER_DOMAIN': 32,
        'CONCURRENT_ITEMS': 500,
        'REACTOR_THREADPOOL_MAXSIZE': 40,
        'DOWNLOAD_TIMEOUT': 10,  # Timeout mais agressivo
        'HTTPCACHE_EXPIRATION_SECS': 1800,  # Cache menor para dados mais frescos
    })
    
    return base_settings

def get_conservative_settings():
    """
    Configurações conservadoras para sites sensíveis ou conexões limitadas
    """
    return {
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'TELNETCONSOLE_ENABLED': False,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'INFO',
        
        # Configurações conservadoras
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'CONCURRENT_ITEMS': 50,
        'DOWNLOAD_TIMEOUT': 30,
        'DOWNLOAD_DELAY': 1,  # Delay maior
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,
        
        # Cache habilitado mas com TTL menor
        'HTTPCACHE_ENABLED': True,
        'HTTPCACHE_EXPIRATION_SECS': 1800,  # 30 minutos
        'HTTPCACHE_DIR': 'httpcache_conservative',
        
        # AutoThrottle habilitado
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 2.0,
        
        # Retry mais conservador
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],
    }

def get_debug_settings():
    """
    Configurações para debugging e desenvolvimento
    """
    return {
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7',
        'TELNETCONSOLE_ENABLED': True,
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'DEBUG',
        
        # Configurações de debug
        'CONCURRENT_REQUESTS': 1,  # Sequencial para debug
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_TIMEOUT': 60,
        'DOWNLOAD_DELAY': 2,  # Delay maior para debug
        
        # Cache desabilitado para debug
        'HTTPCACHE_ENABLED': False,
        
        # Stats detalhadas
        'DOWNLOADER_STATS': True,
        'MEMUSAGE_ENABLED': True,
        
        # Logs detalhados
        'LOGSTATS_INTERVAL': 5,  # Stats a cada 5 segundos
    } 