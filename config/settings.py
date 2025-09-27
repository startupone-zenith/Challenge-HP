"""
Configurações centralizadas do sistema
"""

import os

# Caminhos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, 'src')
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Flask
FLASK_CONFIG = {
    'DEBUG': True,
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'SECRET_KEY': 'hp_challenge_scraping_system_2024'
}

# Scraping
SCRAPING_CONFIG = {
    'DEFAULT_MAX_ITEMS': 50,
    'DEFAULT_DELAY': 2,
    'DEFAULT_TIMEOUT': 15,
    'MAX_RETRIES': 3
}

# Datasets
DATASET_CONFIG = {
    'OUTPUT_DIR': os.path.join(DATA_DIR, 'datasets'),
    'CSV_ENCODING': 'utf-8',
    'JSON_INDENT': 2
}

# Logging
LOGGING_CONFIG = {
    'LOG_DIR': LOGS_DIR,
    'LOG_LEVEL': 'INFO',
    'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(message)s'
}
