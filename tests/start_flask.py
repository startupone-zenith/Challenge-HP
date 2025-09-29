#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de inicialização para Flask - SEM RELOADER AUTOMÁTICO
Sistema de Scraping HP
"""

import os
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Inicializar Flask sem reloader automático"""
    
    print("🚀 INICIANDO SISTEMA DE SCRAPING HP")
    print("=" * 50)
    print("📍 URL: http://localhost:5000")
    print("🔧 Modo: Desenvolvimento (SEM reloader automático)")
    print("⚠️  Para parar: Ctrl+C")
    print("=" * 50)
    print()
    
    try:
        from src.web.flask_app import app
        
        # Configurar ambiente
        os.environ['FLASK_ENV'] = 'development'
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        
        print("✅ Flask carregado com sucesso")
        print("✅ Reloader automático DESATIVADO")
        print("✅ Debug mode ATIVADO")
        print()
        print("🌐 Servidor iniciando...")
        print()
        
        # Executar Flask SEM reloader
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=False,  # CRUCIAL: Desativar reloader
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
