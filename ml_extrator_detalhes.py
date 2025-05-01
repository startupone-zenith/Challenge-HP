#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import pandas as pd
from datetime import datetime

# Importar funções do web scraper
from ml_web_scraper import scrape_mercado_livre, extract_product_details

def main():
    """Função principal para extrair detalhes de produtos do Mercado Livre"""
    print("=== EXTRATOR DE DETALHES DE PRODUTOS DO MERCADO LIVRE ===")
    
    # Inicializar products como vazio para evitar erro
    products = []
    
    # Verificar se deseja extrair de um arquivo CSV existente ou fazer nova busca
    while True:
        modo = input("Deseja usar um arquivo CSV existente (e) ou fazer uma nova busca (n)? [e/n]: ").lower()
        if modo in ['e', 'n']:
            break
        print("Opção inválida. Digite 'e' para arquivo existente ou 'n' para nova busca.")
    
    if modo == 'e':
        # Listar arquivos CSV na pasta de exportações
        export_dir = "ml_data_exports"
        if not os.path.exists(export_dir):
            print(f"Pasta {export_dir} não encontrada. Criando pasta...")
            os.makedirs(export_dir)
            print("Não há arquivos CSV disponíveis. Fazendo nova busca.")
            modo = 'n'
        else:
            csv_files = [f for f in os.listdir(export_dir) if f.endswith('.csv')]
            
            if not csv_files:
                print("Não há arquivos CSV disponíveis. Fazendo nova busca.")
                modo = 'n'
            else:
                print("\nArquivos CSV disponíveis:")
                for i, file in enumerate(csv_files):
                    print(f"{i+1}. {file}")
                
                # Selecionar arquivo
                file_selected = False
                while not file_selected and modo == 'e':
                    try:
                        file_input = input("\nSelecione o número do arquivo (ou digite 'n' para nova busca): ")
                        if file_input.lower() == 'n':
                            modo = 'n'
                            break
                        
                        file_idx = int(file_input) - 1
                        if 0 <= file_idx < len(csv_files):
                            selected_file = os.path.join(export_dir, csv_files[file_idx])
                            
                            # Carregar produtos do CSV
                            try:
                                df = pd.read_csv(selected_file)
                                products = df.to_dict('records')
                                print(f"Carregados {len(products)} produtos do arquivo.")
                                file_selected = True
                            except Exception as e:
                                print(f"Erro ao carregar o arquivo: {str(e)}")
                                retry = input("Deseja tentar outro arquivo? (s/n): ").lower()
                                if retry != 's':
                                    modo = 'n'
                        else:
                            print(f"Seleção inválida. Digite um número entre 1 e {len(csv_files)}.")
                    except ValueError:
                        print("Entrada inválida. Digite um número.")
    
    if modo == 'n':
        # Nova busca
        while True:
            search_term = input("\nDigite o termo de busca: ")
            if search_term:
                break
            print("Termo de busca é obrigatório.")
        
        # Obter código do site
        print("\nSites disponíveis:")
        print("MLB - Brasil")
        print("MLA - Argentina")
        print("MLM - México")
        print("MCO - Colômbia")
        print("MLU - Uruguai")
        print("MLC - Chile")
        site_code = input("Código do site (padrão: MLB para Brasil): ").upper() or "MLB"
        
        # Obter número máximo de resultados
        while True:
            try:
                max_input = input("Número máximo de produtos para buscar (padrão: 10): ") or "10"
                max_results = int(max_input)
                if max_results > 0:
                    break
                print("Digite um número maior que zero.")
            except ValueError:
                print("Valor inválido, digite um número.")
        
        # Fazer scraping
        try:
            print(f"\nBuscando produtos para: {search_term}")
            products = scrape_mercado_livre(search_term, site_code, max_results)
            
            if not products:
                print("Nenhum produto encontrado. Saindo...")
                return
        except Exception as e:
            print(f"Erro durante a busca: {str(e)}")
            import traceback
            traceback.print_exc()
            return
    
    # Limitar o número de produtos para extrair detalhes
    if len(products) > 0:
        max_details = min(len(products), 10)
        while True:
            try:
                details_input = input(f"\nQuantos produtos deseja analisar detalhadamente (máx: {len(products)}, recomendado: 10)? ") or "10"
                max_details = int(details_input)
                if 0 < max_details <= len(products):
                    break
                print(f"Digite um número entre 1 e {len(products)}.")
            except ValueError:
                print("Valor inválido, digite um número.")
        
        # Extrair detalhes
        try:
            site_code = products[0].get('site_code', "MLB") if 'site_code' in products[0] else "MLB"
            print(f"\nExtraindo detalhes de {max_details} produtos...")
            detailed_products = extract_product_details(products[:max_details], site_code)
            
            # Exibir resultados
            print("\n=== RESULTADOS DETALHADOS ===")
            for i, product in enumerate(detailed_products):
                titulo = product.get('nome_produto', product.get('title', 'N/A'))
                preco = product.get('preco', 'N/A')
                avaliacao_media = product.get('avaliacao_media', 'N/A')
                total_avaliacoes = product.get('total_avaliacoes', 0)
                
                ratio_5_to_1 = product.get('ratio_5_to_1', 'N/A')
                if ratio_5_to_1 == float('inf'):
                    ratio_5_to_1 = "∞ (infinito)"
                
                print(f"\n--- Produto {i+1} ---")
                print(f"Título: {titulo}")
                print(f"Preço: R$ {preco}")
                print(f"Avaliação média: {avaliacao_media}")
                print(f"Total de avaliações: {total_avaliacoes}")
                
                # Mostrar distribuição de avaliações
                print("\nDistribuição de avaliações:")
                if total_avaliacoes > 0:
                    for star in range(5, 0, -1):
                        count = product.get(f'estrelas_{star}', 0)
                        percentage = product.get(f'porcentagem_{star}_estrelas' if star > 1 else f'porcentagem_{star}_estrela', 0)
                        bar_length = int(percentage / 2)  # Reduzir para caber na tela
                        bar = "█" * bar_length
                        print(f"{star} ★ {bar} {count} avaliações ({percentage:.1f}%)")
                else:
                    print("Não há avaliações disponíveis")
                
                print(f"\nRatio 5★/1★: {ratio_5_to_1}")
                print(f"Link: {product.get('link', 'N/A')}")
                print("-" * 50)
            
            # Exportar resultados detalhados
            export_dir = "ml_data_exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"{export_dir}/ml_detalhes_{timestamp}.csv"
            
            # Criar DataFrame e exportar
            df = pd.DataFrame(detailed_products)
            df.to_csv(export_file, index=False, encoding='utf-8-sig')
            
            print(f"\nDados detalhados exportados para: {export_file}")
        except Exception as e:
            print(f"Erro ao processar os detalhes: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("Nenhum produto disponível para análise.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        import traceback
        traceback.print_exc() 