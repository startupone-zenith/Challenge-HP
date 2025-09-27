"""
Módulo core - Funcionalidades principais do sistema
"""

# Importações diferidas para evitar importação circular
from .shared_scraping_config import (
    USER_AGENTS_2025,
    STANDARD_BROWSER_HEADERS,
    MERCADOLIVRE_SELECTORS,
    get_random_user_agent,
    get_browser_specific_headers,
    setup_standard_logging
)

def get_scraping_system():
    """Retorna uma instância do HPScrapingSystem, carregando apenas quando necessário"""
    from .app import HPScrapingSystem
    return HPScrapingSystem

__all__ = [
    'get_scraping_system',
    'USER_AGENTS_2025',
    'STANDARD_BROWSER_HEADERS', 
    'MERCADOLIVRE_SELECTORS',
    'get_random_user_agent',
    'get_browser_specific_headers',
    'setup_standard_logging'
]
