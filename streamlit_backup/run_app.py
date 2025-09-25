#!/usr/bin/env python
"""
Launcher para executar o app Streamlit com configuração adequada de multiprocessing
"""
import os
import sys
import multiprocessing

def run_streamlit_app():
    """Executa o app Streamlit com as configurações adequadas"""
    # Configurar multiprocessing para Windows
    if os.name == 'nt':  # Windows
        multiprocessing.freeze_support()
    
    # Importar e executar streamlit
    import streamlit.web.cli as stcli
    
    # Configurar argumentos para o streamlit
    sys.argv = ["streamlit", "run", "app.py"]
    
    # Executar o app
    stcli.main()

if __name__ == "__main__":
    run_streamlit_app() 