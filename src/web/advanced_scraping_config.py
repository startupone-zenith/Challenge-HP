#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurações Avançadas de Scraping
Sistema de opções expandidas e variáveis configuráveis
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum

class ScrapingMode(Enum):
    """Modos de scraping disponíveis"""
    QUICK = "quick"           # Rápido - dados básicos
    STANDARD = "standard"     # Padrão - dados completos
    DETAILED = "detailed"     # Detalhado - todos os campos
    COMPREHENSIVE = "comprehensive"  # Abrangente - máximo de dados

class DataQuality(Enum):
    """Níveis de qualidade de dados"""
    BASIC = "basic"           # Básico - apenas campos essenciais
    GOOD = "good"            # Bom - campos importantes
    EXCELLENT = "excellent"   # Excelente - todos os campos disponíveis

class ScrapingPriority(Enum):
    """Prioridades de scraping"""
    SPEED = "speed"           # Velocidade - menos dados, mais rápido
    BALANCED = "balanced"     # Equilibrado - velocidade e qualidade
    QUALITY = "quality"       # Qualidade - máximo de dados, mais lento

@dataclass
class ScrapingOptions:
    """Configurações avançadas de scraping"""
    
    # === CONFIGURAÇÕES BÁSICAS ===
    query: str = ""
    max_items: int = 50
    
    # === MODOS DE SCRAPING ===
    mode: ScrapingMode = ScrapingMode.STANDARD
    data_quality: DataQuality = DataQuality.GOOD
    priority: ScrapingPriority = ScrapingPriority.BALANCED
    
    # === CONFIGURAÇÕES DE QUANTIDADE ===
    # Produtos
    min_products: int = 1
    max_products: int = 1000
    products_step: int = 10
    
    # Reviews
    min_reviews: int = 10
    max_reviews: int = 500
    reviews_step: int = 10
    
    # Imagens
    min_images: int = 1
    max_images: int = 20
    images_step: int = 1
    
    # === CONFIGURAÇÕES DE FILTROS ===
    # Preço
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_currency: str = "BRL"
    
    # Vendedor
    min_seller_rating: Optional[float] = None
    min_seller_sales: Optional[int] = None
    power_seller_only: bool = False
    
    # Produto
    min_product_rating: Optional[float] = None
    min_reviews_count: Optional[int] = None
    free_shipping_only: bool = False
    
    # === CONFIGURAÇÕES DE EXTRAÇÃO ===
    # Campos básicos
    extract_basic_info: bool = True
    extract_prices: bool = True
    extract_seller_info: bool = True
    extract_shipping_info: bool = True
    
    # Campos detalhados
    extract_detailed_description: bool = False
    extract_technical_specs: bool = False
    extract_compatibility: bool = False
    extract_warranty_info: bool = False
    
    # Reviews e avaliações
    extract_reviews: bool = False
    extract_rating_distribution: bool = False
    extract_review_texts: bool = False
    extract_review_images: bool = False
    
    # Imagens
    extract_images: bool = False
    extract_image_metadata: bool = False
    max_images_per_product: int = 5
    
    # === CONFIGURAÇÕES DE PERFORMANCE ===
    # Delays
    min_delay: float = 1.0
    max_delay: float = 3.0
    adaptive_delay: bool = True
    
    # Timeouts
    page_timeout: int = 30
    request_timeout: int = 20
    retry_attempts: int = 3
    
    # Paralelização
    max_concurrent_requests: int = 3
    use_multiprocessing: bool = False
    
    # === CONFIGURAÇÕES DE DADOS ===
    # Formato de saída
    generate_csv: bool = True
    generate_json: bool = False
    generate_excel: bool = False
    
    # Campos personalizados
    custom_fields: List[str] = None
    
    # Filtros de dados
    remove_duplicates: bool = True
    validate_data: bool = True
    clean_data: bool = True
    
    def __post_init__(self):
        """Inicialização pós-criação"""
        if self.custom_fields is None:
            self.custom_fields = []

# === CONFIGURAÇÕES PREDEFINIDAS ===

def get_quick_scraping_config() -> ScrapingOptions:
    """Configuração para scraping rápido"""
    return ScrapingOptions(
        mode=ScrapingMode.QUICK,
        data_quality=DataQuality.BASIC,
        priority=ScrapingPriority.SPEED,
        max_items=25,
        extract_basic_info=True,
        extract_prices=True,
        extract_seller_info=False,
        extract_shipping_info=False,
        extract_reviews=False,
        extract_images=False,
        min_delay=0.5,
        max_delay=1.5,
        max_concurrent_requests=5
    )

def get_standard_scraping_config() -> ScrapingOptions:
    """Configuração para scraping padrão"""
    return ScrapingOptions(
        mode=ScrapingMode.STANDARD,
        data_quality=DataQuality.GOOD,
        priority=ScrapingPriority.BALANCED,
        max_items=50,
        extract_basic_info=True,
        extract_prices=True,
        extract_seller_info=True,
        extract_shipping_info=True,
        extract_reviews=False,
        extract_images=True,
        max_images_per_product=3,
        min_delay=1.0,
        max_delay=2.5,
        max_concurrent_requests=3
    )

def get_detailed_scraping_config() -> ScrapingOptions:
    """Configuração para scraping detalhado"""
    return ScrapingOptions(
        mode=ScrapingMode.DETAILED,
        data_quality=DataQuality.EXCELLENT,
        priority=ScrapingPriority.QUALITY,
        max_items=100,
        extract_basic_info=True,
        extract_prices=True,
        extract_seller_info=True,
        extract_shipping_info=True,
        extract_detailed_description=True,
        extract_technical_specs=True,
        extract_compatibility=True,
        extract_warranty_info=True,
        extract_reviews=True,
        extract_rating_distribution=True,
        extract_review_texts=True,
        extract_images=True,
        max_images_per_product=10,
        min_delay=1.5,
        max_delay=3.0,
        max_concurrent_requests=2
    )

def get_comprehensive_scraping_config() -> ScrapingOptions:
    """Configuração para scraping abrangente"""
    return ScrapingOptions(
        mode=ScrapingMode.COMPREHENSIVE,
        data_quality=DataQuality.EXCELLENT,
        priority=ScrapingPriority.QUALITY,
        max_items=200,
        extract_basic_info=True,
        extract_prices=True,
        extract_seller_info=True,
        extract_shipping_info=True,
        extract_detailed_description=True,
        extract_technical_specs=True,
        extract_compatibility=True,
        extract_warranty_info=True,
        extract_reviews=True,
        extract_rating_distribution=True,
        extract_review_texts=True,
        extract_review_images=True,
        extract_images=True,
        extract_image_metadata=True,
        max_images_per_product=20,
        min_delay=2.0,
        max_delay=4.0,
        max_concurrent_requests=1,
        generate_csv=True,
        generate_json=True,
        generate_excel=True
    )

# === CONFIGURAÇÕES DE QUANTIDADE ===

QUANTITY_PRESETS = {
    "micro": {
        "products": (5, 10, 5),
        "reviews": (10, 25, 5),
        "images": (1, 3, 1)
    },
    "small": {
        "products": (10, 50, 10),
        "reviews": (25, 100, 25),
        "images": (1, 5, 1)
    },
    "medium": {
        "products": (25, 100, 25),
        "reviews": (50, 200, 50),
        "images": (2, 10, 2)
    },
    "large": {
        "products": (50, 250, 50),
        "reviews": (100, 400, 100),
        "images": (3, 15, 3)
    },
    "xlarge": {
        "products": (100, 500, 100),
        "reviews": (200, 500, 100),
        "images": (5, 20, 5)
    }
}

# === CONFIGURAÇÕES DE FILTROS ===

FILTER_PRESETS = {
    "budget": {
        "max_price": 100.0,
        "free_shipping_only": True,
        "min_seller_rating": 4.0
    },
    "premium": {
        "min_price": 50.0,
        "power_seller_only": True,
        "min_product_rating": 4.5,
        "min_reviews_count": 10
    },
    "new_products": {
        "min_seller_rating": 4.0,
        "min_seller_sales": 100,
        "min_product_rating": 4.0
    },
    "high_volume": {
        "min_seller_sales": 1000,
        "power_seller_only": True,
        "min_reviews_count": 50
    }
}

# === CONFIGURAÇÕES DE PERFORMANCE ===

PERFORMANCE_PRESETS = {
    "fast": {
        "min_delay": 0.5,
        "max_delay": 1.0,
        "max_concurrent_requests": 5,
        "page_timeout": 15,
        "retry_attempts": 2
    },
    "balanced": {
        "min_delay": 1.0,
        "max_delay": 2.5,
        "max_concurrent_requests": 3,
        "page_timeout": 30,
        "retry_attempts": 3
    },
    "thorough": {
        "min_delay": 2.0,
        "max_delay": 4.0,
        "max_concurrent_requests": 1,
        "page_timeout": 45,
        "retry_attempts": 5
    }
}

def get_config_by_name(config_name: str) -> ScrapingOptions:
    """Obter configuração por nome"""
    configs = {
        "quick": get_quick_scraping_config,
        "standard": get_standard_scraping_config,
        "detailed": get_detailed_scraping_config,
        "comprehensive": get_comprehensive_scraping_config
    }
    
    if config_name in configs:
        return configs[config_name]()
    else:
        return get_standard_scraping_config()

def apply_quantity_preset(options: ScrapingOptions, preset_name: str) -> ScrapingOptions:
    """Aplicar preset de quantidade"""
    if preset_name in QUANTITY_PRESETS:
        preset = QUANTITY_PRESETS[preset_name]
        options.min_products, options.max_products, options.products_step = preset["products"]
        options.min_reviews, options.max_reviews, options.reviews_step = preset["reviews"]
        options.min_images, options.max_images, options.images_step = preset["images"]
    return options

def apply_filter_preset(options: ScrapingOptions, preset_name: str) -> ScrapingOptions:
    """Aplicar preset de filtros"""
    if preset_name in FILTER_PRESETS:
        preset = FILTER_PRESETS[preset_name]
        for key, value in preset.items():
            setattr(options, key, value)
    return options

def apply_performance_preset(options: ScrapingOptions, preset_name: str) -> ScrapingOptions:
    """Aplicar preset de performance"""
    if preset_name in PERFORMANCE_PRESETS:
        preset = PERFORMANCE_PRESETS[preset_name]
        for key, value in preset.items():
            setattr(options, key, value)
    return options
