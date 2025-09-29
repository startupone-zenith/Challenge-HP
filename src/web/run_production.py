#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar o Flask em MODO PRODUÇÃO
Sistema de Scraping HP - Sem watchdog/reloader
"""

import os
import sys

def main():
    """Executar Flask em modo produção"""
    # Forçar modo produção
    os.environ['FLASK_ENV'] = 'production'
    
    # Importar e executar
    from run_flask import main as run_main
    run_main()

if __name__ == '__main__':
    main()
