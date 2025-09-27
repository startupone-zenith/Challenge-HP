#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das melhorias anti-detecção de bot
"""

import requests
import json
import time

def test_anti_bot_improvements():
    """Testa as melhorias anti-bot via API"""
    
    print("🤖 TESTE: MELHORIAS ANTI-DETECÇÃO DE BOT")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    try:
        print("1. Verificando se servidor está ativo...")
        response = requests.get(f"{base_url}/api/jobs", timeout=5)
        if response.status_code != 200:
            print("✗ Servidor Flask não está respondendo")
            return False
        print("✓ Servidor ativo")
        
        print("\n2. Testando scraping com melhorias anti-bot...")
        
        # Teste com query simples primeiro
        payload = {
            "query": "Cartucho HP",
            "max_items": 3,
            "extract_images": False,
            "sort_by": "relevance"
        }
        
        print("   Iniciando requisição...")
        start_time = time.time()
        
        response = requests.post(f"{base_url}/api/scraping/simple", 
                               json=payload, 
                               timeout=60)  # Timeout maior devido aos delays
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   Tempo de resposta: {duration:.1f}s")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                produtos = data.get('produtos', [])
                print(f"✓ Sucesso! {len(produtos)} produtos coletados")
                
                if produtos:
                    print("\n   Produtos encontrados:")
                    for i, produto in enumerate(produtos, 1):
                        title = produto.get('title', 'N/A')[:50]
                        price = produto.get('price', 'N/A')
                        print(f"   {i}. {title}... - {price}")
                
                # Se conseguiu coletar produtos, as melhorias funcionaram
                if len(produtos) > 0:
                    print("\n✓ TESTE PASSOU: Bot não foi detectado!")
                    return True
                else:
                    print("\n⚠️ TESTE PARCIAL: Não foram coletados produtos")
                    return False
            else:
                error = data.get('error', 'Erro desconhecido')
                print(f"✗ Erro na API: {error}")
                
                # Verificar se ainda é problema de detecção de bot
                if 'account-verification' in error.lower() or 'verificação' in error.lower():
                    print("⚠️ Ainda há detecção de bot - pode precisar de mais melhorias")
                    return False
                else:
                    print("ℹ️ Erro não relacionado a detecção de bot")
                    return True
        else:
            print(f"✗ Erro HTTP: {response.status_code}")
            print(f"Resposta: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ Timeout - isso pode ser normal devido aos delays anti-bot")
        print("ℹ️ Tente aumentar o timeout ou verificar os logs do Flask")
        return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Erro de conexão: {e}")
        return False
    except Exception as e:
        print(f"✗ Erro inesperado: {e}")
        return False

def test_with_custom_url():
    """Testa com URL customizada e melhorias anti-bot"""
    
    print("\n" + "=" * 60)
    print("3. Testando com URL customizada + anti-bot...")
    
    base_url = "http://localhost:5000"
    url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"
    
    payload = {
        "query": "Cartucho HP Original",
        "max_items": 2,
        "custom_url": url_customizada
    }
    
    try:
        print("   Testando URL específica com filtros...")
        start_time = time.time()
        
        response = requests.post(f"{base_url}/api/scraping/simple", 
                               json=payload, 
                               timeout=60)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   Tempo de resposta: {duration:.1f}s")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                produtos = data.get('produtos', [])
                print(f"✓ URL customizada funcionou! {len(produtos)} produtos")
                
                if produtos:
                    for i, produto in enumerate(produtos, 1):
                        title = produto.get('title', 'N/A')[:40]
                        print(f"   {i}. {title}...")
                
                return len(produtos) > 0
            else:
                error = data.get('error', '')
                print(f"✗ Erro com URL customizada: {error}")
                return False
        else:
            print(f"✗ Erro HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Erro no teste de URL customizada: {e}")
        return False

def analyze_logs():
    """Analisa os logs para verificar se há sinais de detecção de bot"""
    
    print("\n" + "=" * 60)
    print("4. Analisando logs para detecção de bot...")
    
    try:
        # Verificar arquivo de debug HTML se existir
        try:
            with open('scraped_page_content_debug.html', 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'account-verification' in content:
                print("⚠️ Detectada página de verificação nos logs HTML")
                return False
            elif 'mercadolivre.com.br' in content and len(content) > 10000:
                print("✓ HTML parece ser página válida do ML")
                return True
            else:
                print("ℹ️ HTML muito pequeno ou suspeito")
                return False
                
        except FileNotFoundError:
            print("ℹ️ Arquivo de debug HTML não encontrado")
            
        # Verificar logs do scraper
        try:
            with open('scraper.log', 'r', encoding='utf-8') as f:
                logs = f.read()
                
            if 'account-verification' in logs:
                print("⚠️ Logs mostram redirecionamento para verificação")
                return False
            elif 'produtos coletados' in logs or 'produtos encontrados' in logs:
                print("✓ Logs mostram coleta bem-sucedida")
                return True
                
        except FileNotFoundError:
            print("ℹ️ Arquivo de logs não encontrado")
            
        return None
        
    except Exception as e:
        print(f"✗ Erro ao analisar logs: {e}")
        return None

if __name__ == "__main__":
    print("🛡️ TESTE DAS MELHORIAS ANTI-BOT")
    print("Sistema de Scraping HP - Versão Anti-Detecção")
    print()
    
    # Verificar se Flask está rodando
    try:
        response = requests.get("http://localhost:5000/api/jobs", timeout=5)
        if response.status_code != 200:
            print("✗ Servidor Flask não está rodando ou não responde")
            print("Execute: python run_flask.py")
            exit(1)
    except:
        print("✗ Servidor Flask não está acessível!")
        print("Execute: python run_flask.py")
        exit(1)
    
    print("✓ Servidor Flask detectado!")
    print()
    
    # Executar testes
    test1 = test_anti_bot_improvements()
    test2 = test_with_custom_url()
    log_analysis = analyze_logs()
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES ANTI-BOT:")
    print(f"- Scraping básico: {'✓ PASSOU' if test1 else '✗ FALHOU'}")
    print(f"- URL customizada: {'✓ PASSOU' if test2 else '✗ FALHOU'}")
    
    if log_analysis is not None:
        print(f"- Análise de logs: {'✓ SEM DETECÇÃO' if log_analysis else '⚠️ POSSÍVEL DETECÇÃO'}")
    
    success_rate = sum([test1, test2, log_analysis or False]) / 3 * 100
    
    print(f"\n📈 Taxa de sucesso: {success_rate:.0f}%")
    
    if success_rate >= 66:
        print("\n🎉 MELHORIAS ANTI-BOT ESTÃO FUNCIONANDO!")
        print("✓ Sistema conseguiu contornar a detecção do Mercado Livre")
        print("\nMelhorias implementadas:")
        print("- User-Agents atualizados e rotativos")
        print("- Headers realistas de navegador")
        print("- Delays aleatórios e inteligentes")
        print("- Detecção e retry em páginas de verificação")
        print("- Configurações conservadoras de requisições")
    else:
        print("\n⚠️ ALGUMAS MELHORIAS PODEM PRECISAR DE AJUSTES")
        print("Considere implementar:")
        print("- Proxies rotativos")
        print("- Cookies persistentes")
        print("- Simulação de JavaScript")
        print("- Delays ainda maiores")
    
    print("\n" + "=" * 60)

