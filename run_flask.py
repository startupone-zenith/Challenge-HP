#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialização para a aplicação Flask
Sistema de Scraping HP
"""

import os
import sys
from flask_app import app

def main():
    """Função principal para executar a aplicação Flask"""
    
    print("=" * 60)
    print("🛡️  SISTEMA DE SCRAPING HP - FLASK WEB APPLICATION")
    print("=" * 60)
    print()
    print("🚀 Iniciando servidor Flask...")
    print("📍 URL: http://localhost:5000")
    print("📱 Interface Web: http://localhost:5000")
    print("🔌 API REST: http://localhost:5000/api/")
    print()
    print("📋 Endpoints Principais:")
    print("   • GET  /                     - Página inicial")
    print("   • GET  /scraping             - Configurar scraping")
    print("   • GET  /jobs                 - Ver jobs em andamento")
    print("   • GET  /datasets             - Datasets gerados")
    print("   • POST /api/scraping/start   - Iniciar scraping (API)")
    print("   • GET  /api/jobs             - Listar jobs (API)")
    print("   • GET  /api/datasets         - Listar datasets (API)")
    print()
    print("⚠️  Para parar o servidor, pressione Ctrl+C")
    print("=" * 60)
    print()
    
    try:
        # Configurar ambiente de desenvolvimento
        os.environ['FLASK_ENV'] = 'development'
        
        # Executar aplicação
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=True,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
