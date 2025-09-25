#!/usr/bin/env python
"""
Launcher para executar o app Flask com configuração adequada
HP Challenge Sprint - Detector de Falsificações
"""
import os
import sys
import multiprocessing

def run_flask_app():
    """Executa o app Flask com as configurações adequadas"""
    # Configurar multiprocessing para Windows
    if os.name == 'nt':  # Windows
        multiprocessing.freeze_support()
    
    # Importar e executar Flask app
    from flask_app import app
    
    # Configurações de desenvolvimento
    app.config.update(
        DEBUG=True,
        SECRET_KEY='hp-challenge-sprint-dev-key-change-in-production',
        SESSION_PERMANENT=False,
        PERMANENT_SESSION_LIFETIME=7200  # 2 hours
    )
    
    print("=" * 60)
    print("🏆 HP Challenge Sprint - Detector de Falsificações")
    print("Flask Application Starting...")
    print("=" * 60)
    print()
    print("📋 Funcionalidades disponíveis:")
    print("  🔍 Busca & Coleta de dados no Mercado Livre")
    print("  🚨 Detecção de falsificação com IA")
    print("  📊 Gerador de datasets estruturados")
    print("  🔬 Análise exploratória avançada")
    print()
    print("🌐 Acesse: http://localhost:5000")
    print("⏹️  Para parar: Ctrl+C")
    print("=" * 60)
    
    # Executar o app
    try:
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Aplicação finalizada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao executar aplicação: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = run_flask_app()
    sys.exit(exit_code)

