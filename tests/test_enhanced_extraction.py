#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste das melhorias na extração detalhada:
- Especificações técnicas detalhadas
- Reviews estruturados completos
"""

import requests
import json
import time
from datetime import datetime

def test_enhanced_extraction():
    """Testa as novas funcionalidades de extração"""
    
    print("🧪 TESTE: Extração Melhorada de Especificações e Reviews")
    print("=" * 60)
    
    # URL base do Flask
    base_url = "http://localhost:5000"
    
    try:
        # Verificar se Flask está rodando
        print("1. Verificando se Flask está ativo...")
        response = requests.get(f"{base_url}/api/jobs", timeout=5)
        if response.status_code != 200:
            print("❌ Flask não está rodando. Inicie com: cd src/web && python run_flask.py")
            return False
        print("✅ Flask ativo")
        
        # Iniciar job com extração detalhada
        print("\n2. Iniciando job com extração DETALHADA...")
        job_data = {
            "query": "cartucho hp 664",
            "max_items": 3,  # Poucos itens para teste rápido mas completo
            "extract_images": True,
            "collect_reviews": False,  # Não coletar reviews separadamente
            "detailed_extraction": True  # ATIVAR extração detalhada
        }
        
        response = requests.post(f"{base_url}/api/scraping/start", json=job_data, timeout=10)
        if response.status_code != 200:
            print(f"❌ Falha ao iniciar job: {response.status_code}")
            return False
            
        result = response.json()
        job_id = result.get('job_id')
        print(f"✅ Job iniciado: {job_id}")
        
        # Monitorar job até conclusão
        print("\n3. Aguardando conclusão...")
        max_wait = 300  # 5 minutos
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{base_url}/api/jobs/{job_id}/status", timeout=5)
                if response.status_code != 200:
                    print("❌ Erro ao verificar status do job")
                    return False
                
                status = response.json()
                job_status = status.get('status', 'unknown')
                progress = status.get('progress', 0)
                
                print(f"   Status: {job_status} ({progress}%)")
                
                if job_status == 'concluido':
                    print("✅ Job concluído!")
                    break
                elif job_status == 'erro':
                    print("❌ Job terminou com erro")
                    print(f"   Erro: {status.get('error_message', 'N/A')}")
                    return False
                    
                time.sleep(10)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Erro de comunicação: {e}")
                return False
        else:
            print("❌ Timeout aguardando job")
            return False
        
        # Verificar arquivos gerados
        print("\n4. Verificando arquivos gerados...")
        response = requests.get(f"{base_url}/api/jobs/{job_id}/status", timeout=5)
        
        if response.status_code != 200:
            print("❌ Erro ao obter detalhes do job")
            return False
        
        job_details = response.json()
        result_files = job_details.get('result_files', [])
        
        if not result_files:
            print("❌ Nenhum arquivo foi gerado")
            return False
        
        print(f"✅ {len(result_files)} arquivo(s) gerado(s):")
        for file_info in result_files:
            print(f"   • {file_info['type'].upper()}: {file_info['filename']}")
        
        # Analisar arquivo JSON para validar novas funcionalidades
        json_file = next((f for f in result_files if f['type'] == 'json'), None)
        if json_file:
            print(f"\n5. Analisando {json_file['filename']}...")
            
            # Baixar arquivo JSON
            download_url = f"{base_url}/api/datasets/{json_file['filename']}/download"
            response = requests.get(download_url, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Dataset carregado: {len(data)} produtos")
                    
                    # Validar novas funcionalidades
                    validated_features = validate_enhanced_features(data)
                    return validated_features
                    
                except json.JSONDecodeError:
                    print("❌ Erro ao decodificar JSON")
                    return False
            else:
                print(f"❌ Erro ao baixar arquivo: {response.status_code}")
                return False
        else:
            print("❌ Arquivo JSON não encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        return False

def validate_enhanced_features(data):
    """Valida se as novas funcionalidades estão funcionando"""
    
    print("\n🔍 VALIDANDO NOVAS FUNCIONALIDADES:")
    print("-" * 40)
    
    success_count = 0
    total_validations = 0
    
    # Validar especificações técnicas
    print("\n📋 Especificações Técnicas Detalhadas:")
    
    specs_found = 0
    for produto in data[:5]:  # Testar primeiros 5 produtos
        if 'especificacoes_tecnicas' in produto and produto['especificacoes_tecnicas'] != 'N/A':
            specs = produto['especificacoes_tecnicas']
            produto_nome = produto.get('titulo', produto.get('nome_produto', 'N/A'))[:50]
            
            print(f"   📦 {produto_nome}...")
            
            # Verificar campos específicos
            campos_verificados = []
            if 'tipo_tinta' in specs:
                print(f"      ✅ Tipo de tinta: {specs['tipo_tinta']}")
                campos_verificados.append('tipo_tinta')
            
            if 'rendimento_paginas' in specs:
                print(f"      ✅ Rendimento: {specs['rendimento_paginas']}")
                campos_verificados.append('rendimento')
            
            if 'volume_ml' in specs:
                print(f"      ✅ Volume: {specs['volume_ml']}")
                campos_verificados.append('volume')
            
            if 'impressoras_compativeis' in specs:
                print(f"      ✅ Compatibilidade: {specs['impressoras_compativeis'][:100]}...")
                campos_verificados.append('compatibilidade')
            
            if 'temperatura_operacional' in specs or 'temperatura' in specs:
                temp_info = specs.get('temperatura_operacional', specs.get('temperatura'))
                print(f"      ✅ Temperatura: {temp_info}")
                campos_verificados.append('temperatura')
            
            if campos_verificados:
                specs_found += 1
                print(f"      ✅ {len(campos_verificados)} especificação(ões) extraída(s)")
            else:
                print("      ⚠️  Nenhuma especificação técnica encontrada")
    
    total_validations += 1
    if specs_found > 0:
        success_count += 1
        print(f"✅ Especificações técnicas: {specs_found} produtos com dados detalhados")
    else:
        print("❌ Especificações técnicas: Nenhum produto com dados detalhados")
    
    # Validar reviews estruturados
    print("\n⭐ Reviews Estruturados Completos:")
    
    reviews_found = 0
    for produto in data[:5]:  # Testar primeiros 5 produtos
        if 'reviews_detalhados' in produto:
            reviews = produto['reviews_detalhados']
            produto_nome = produto.get('titulo', produto.get('nome_produto', 'N/A'))[:50]
            
            print(f"   📦 {produto_nome}...")
            
            # Verificar estrutura completa
            if reviews.get('tem_reviews') and reviews.get('rating_medio') != 'N/A':
                rating = reviews.get('rating_medio')
                total = reviews.get('total_reviews')
                
                print(f"      ✅ Rating médio: {rating}")
                print(f"      ✅ Total reviews: {total}")
                
                # Verificar distribuição de estrelas
                distribuicao = reviews.get('distribuicao_estrelas', {})
                if any(v['quantidade'] > 0 for v in distribuicao.values()):
                    print("      ✅ Distribuição de estrelas:")
                    for estrela, dados in distribuicao.items():
                        if dados['quantidade'] > 0:
                            print(f"         • {estrela}: {dados['quantidade']} ({dados['percentual']})")
                    
                    # Verificar avaliações categorizadas
                    positivas = reviews.get('avaliacoes_positivas', 0)
                    neutras = reviews.get('avaliacoes_neutras', 0)
                    negativas = reviews.get('avaliacoes_negativas', 0)
                    
                    print(f"      ✅ Positivas: {positivas}, Neutras: {neutras}, Negativas: {negativas}")
                    reviews_found += 1
                    
                else:
                    print("      ⚠️  Distribuição de estrelas não encontrada")
            else:
                print("      ⚠️  Sem reviews ou rating médio")
    
    total_validations += 1
    if reviews_found > 0:
        success_count += 1
        print(f"✅ Reviews estruturados: {reviews_found} produtos com dados completos")
    else:
        print("❌ Reviews estruturados: Nenhum produto com dados completos")
    
    # Resultado final
    print("\n" + "=" * 60)
    success_rate = (success_count / total_validations * 100) if total_validations > 0 else 0
    
    if success_rate >= 100:
        print("🎉 SUCESSO COMPLETO: Todas as novas funcionalidades estão funcionando!")
        print(f"   ✅ Especificações técnicas extraídas")
        print(f"   ✅ Reviews estruturados completos")
        return True
    elif success_rate >= 50:
        print(f"⚠️  SUCESSO PARCIAL: {success_rate:.0f}% das funcionalidades funcionando")
        return True
    else:
        print(f"❌ FALHA: Apenas {success_rate:.0f}% das funcionalidades funcionando")
        return False

def main():
    """Executar teste principal"""
    success = test_enhanced_extraction()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TESTE PASSOU: Melhorias implementadas com sucesso!")
    else:
        print("❌ TESTE FALHOU: Melhorias precisam de ajustes")
    print("=" * 60)
    
    return success

if __name__ == '__main__':
    main()
