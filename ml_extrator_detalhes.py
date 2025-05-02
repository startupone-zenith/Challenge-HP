#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import pandas as pd
from datetime import datetime
import time

# Importar funções do web scraper
from ml_web_scraper import scrape_mercado_livre, extract_product_details, scrape_mercado_livre_lotes

def print_product_details(product):
    """Imprime detalhes formatados de um produto"""
    print(f"\n--- Produto {product.get('index', '')} ---")
    
    # Imprimir título, preço e condição
    print(f"Título: {product.get('title', 'Não disponível')}")
    print(f"Preço: {product.get('preco', 'Não disponível')}")
    print(f"Condição: {product.get('condicao', 'Não disponível')}")
    
    # Imprimir informações do vendedor
    if 'vendedor_nome' in product or 'vendedor_id' in product:
        print("\nVendedor:")
        print(f"  Nome: {product.get('vendedor_nome', 'Não disponível')}")
        print(f"  ID: {product.get('vendedor_id', 'Não disponível')}")
        print(f"  Avaliação: {product.get('vendedor_avaliacao', 'Não disponível')}")
        
        # Imprimir métricas de reputação se disponíveis
        if 'vendedor_vendas_concluidas' in product:
            print(f"  Vendas concluídas: {product.get('vendedor_vendas_concluidas')}")
        if 'vendedor_qualidade_atendimento' in product:
            print(f"  Qualidade do atendimento: {product.get('vendedor_qualidade_atendimento')}")
        if 'vendedor_entrega_nos_prazos' in product:
            print(f"  Entrega nos prazos: {product.get('vendedor_entrega_nos_prazos')}")
    
    # Imprimir avaliação média e total de avaliações
    avaliacao_media = product.get('avaliacao_media', 0)
    total_avaliacoes = product.get('total_avaliacoes', 0)
    
    print()
    if avaliacao_media > 0:
        # Formatação visual em estrelas
        estrelas_cheias = int(avaliacao_media)
        decimal = avaliacao_media - estrelas_cheias
        meia_estrela = '½' if decimal >= 0.25 and decimal < 0.75 else ''
        estrela_adicional = '★' if decimal >= 0.75 else ''
        
        print(f"Avaliação média: {avaliacao_media:.1f}/5.0 {'★' * estrelas_cheias}{meia_estrela}{estrela_adicional}")
    elif total_avaliacoes > 0:
        print("Avaliação média: Não disponível")
    else:
        print("Avaliação média: Sem avaliações")
    
    print(f"Total de avaliações: {total_avaliacoes}")
    
    # Imprimir distribuição de avaliações
    if total_avaliacoes > 0:
        print("\nDistribuição de avaliações:")
        
        # Mostrar barras para cada nível de estrela
        for star in range(5, 0, -1):
            count = product.get(f'estrelas_{star}', 0)
            percentage = product.get(f'porcentagem_{star}_estrela{"s" if star > 1 else ""}', 0)
            bar_length = int(percentage * 0.4)  # Ajustar tamanho da barra
            bar = '█' * bar_length
            print(f"{star} ★ {bar} {count} avaliações ({percentage:.1f}%)")
        
        # Mostrar ratio 5★/1★
        ratio = product.get('ratio_5_to_1', 0)
        if ratio == float('inf'):
            print("\nRatio 5★/1★: ∞ (infinito)")
        elif ratio > 0:
            print(f"\nRatio 5★/1★: {ratio:.1f}")
        else:
            print("\nRatio 5★/1★: Não disponível")
    else:
        print("\nDistribuição de avaliações:")
        print("Não há avaliações disponíveis")
    
    print(f"Link: {product.get('link', '')}")
    print("--------------------------------------------------")

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
            os.makedirs(export_dir)
        
        csv_files = [f for f in os.listdir(export_dir) if f.endswith('.csv')]
        
        if not csv_files:
            print("Nenhum arquivo CSV encontrado na pasta ml_data_exports.")
            print("Será realizada uma nova busca.")
            modo = 'n'
        else:
            # Mostrar arquivos disponíveis
            print("\nArquivos CSV disponíveis:")
            for i, csv_file in enumerate(csv_files, 1):
                print(f"{i}. {csv_file}")
            
            # Selecionar arquivo
            while True:
                try:
                    file_index = int(input("\nSelecione o número do arquivo que deseja usar: "))
                    if 1 <= file_index <= len(csv_files):
                        break
                    print(f"Por favor, digite um número entre 1 e {len(csv_files)}.")
                except ValueError:
                    print("Por favor, digite um número válido.")
            
            file_path = os.path.join(export_dir, csv_files[file_index - 1])
            print(f"Carregando arquivo {file_path}...")
            
            # Carregar dados do CSV
            try:
                df = pd.read_csv(file_path)
                products = df.to_dict('records')
                print(f"Foram carregados {len(products)} produtos.")
            except Exception as e:
                print(f"Erro ao carregar o arquivo CSV: {str(e)}")
                print("Será realizada uma nova busca.")
                modo = 'n'
    
    if modo == 'n':
        # Fazer nova busca
        termo = input("\nDigite o termo de busca: ")
        
        # Mostrar opções de sites
        print("\nSites disponíveis:")
        print("MLB - Brasil")
        print("MLA - Argentina")
        print("MLM - México")
        print("MCO - Colômbia")
        print("MLU - Uruguai")
        print("MLC - Chile")
        
        site_code = input("Código do site (padrão: MLB para Brasil): ").upper() or "MLB"
        
        # Perguntar se deseja extrair um grande volume de dados
        while True:
            modo_extracao = input("\nDeseja usar o modo de extração para grandes volumes (1000+ produtos)? (s/n): ").lower()
            if modo_extracao in ['s', 'n']:
                break
            print("Opção inválida. Digite 's' para sim ou 'n' para não.")
        
        if modo_extracao == 's':
            # Modo de extração para grandes volumes
            try:
                max_produtos = int(input("Número de produtos a extrair (padrão: 500, recomendado: até 2000): ") or "500")
                if max_produtos <= 0:
                    max_produtos = 500
                    print("Valor inválido, usando padrão: 500")
                    
                # Confirmar se o usuário realmente quer extrair muitos produtos
                if max_produtos > 2000:
                    confirmar = input(f"Atenção: Extrair {max_produtos} produtos pode demorar muito tempo e aumentar o risco de bloqueio. Confirma? (s/n): ").lower()
                    if confirmar != 's':
                        max_produtos = 2000
                        print(f"Limitando para {max_produtos} produtos.")
                
                # Definir tamanho do lote
                tamanho_lote = 50
                try:
                    tamanho_lote = int(input(f"Tamanho do lote (padrão: 50, recomendado: 30-100): ") or "50")
                    if tamanho_lote <= 0 or tamanho_lote > 200:
                        tamanho_lote = 50
                        print("Valor inválido, usando padrão: 50")
                except ValueError:
                    tamanho_lote = 50
                    print("Valor inválido, usando padrão: 50")
                
                print(f"\nIniciando extração de {max_produtos} produtos em lotes de {tamanho_lote}...")
                print("Isso pode levar alguns minutos. Os resultados serão salvos automaticamente por lote.")
                
                # Usar a função especializada para grandes volumes
                products = scrape_mercado_livre_lotes(
                    termo, 
                    site_code, 
                    max_results=max_produtos, 
                    lote_size=tamanho_lote, 
                    delay_entre_lotes=20
                )
                
            except ValueError:
                print("Valor inválido, usando extração normal com 100 produtos")
                products = scrape_mercado_livre(termo, site_code, 100)
                
        else:
            # Modo de extração normal
            try:
                max_produtos = int(input("Número máximo de produtos para buscar (padrão: 100): ") or "100")
                if max_produtos <= 0:
                    max_produtos = 100
                    print("Valor inválido, usando padrão: 100")
            except ValueError:
                max_produtos = 100
                print("Valor inválido, usando padrão: 100")
        
            print(f"\nBuscando {max_produtos} produtos para: {termo}")
            
            # Fazer web scraping normal
            products = scrape_mercado_livre(termo, site_code, max_produtos)
    
    # Perguntar quantos produtos o usuário deseja analisar
    if products:
        max_products = len(products)
        try:
            num_products = int(input(f"\nQuantos produtos deseja analisar detalhadamente (máx: {max_products}, recomendado: 50 para evitar sobrecarga)? ") or "50")
            num_products = min(num_products, max_products)
            
            # Aviso adicional para grandes volumes
            if num_products > 100:
                confirmar = input(f"Atenção: Analisar {num_products} produtos detalhadamente pode levar muito tempo. Confirma? (s/n): ").lower()
                if confirmar != 's':
                    num_products = 100
                    print(f"Limitando para {num_products} produtos.")
        except ValueError:
            num_products = min(50, max_products)
            print(f"Valor inválido, usando: {num_products}")
        
        # Selecionar apenas os produtos a serem analisados
        products = products[:num_products]
        
        # Adicionar índice para referência
        for i, product in enumerate(products, 1):
            product['index'] = i
        
        print(f"\nExtraindo detalhes de {len(products)} produtos...")
        
        # Pergunta se o usuário deseja processar em lotes
        processar_lotes = False
        tamanho_lote = num_products
        
        if num_products > 20:
            opcao_lotes = input("Deseja processar os produtos em lotes para evitar bloqueios? (s/n): ").lower()
            if opcao_lotes == 's':
                processar_lotes = True
                try:
                    tamanho_lote = int(input(f"Tamanho do lote (recomendado: 10-20, máx: {num_products}): ") or "20")
                    if tamanho_lote <= 0 or tamanho_lote > num_products:
                        tamanho_lote = min(20, num_products)
                        print(f"Valor inválido, usando: {tamanho_lote}")
                except ValueError:
                    tamanho_lote = min(20, num_products)
                    print(f"Valor inválido, usando: {tamanho_lote}")
        
        # Extrair detalhes em lotes se necessário
        detailed_products = []
        
        if processar_lotes:
            # Dividir em lotes
            lotes = [products[i:i+tamanho_lote] for i in range(0, len(products), tamanho_lote)]
            
            for i, lote in enumerate(lotes, 1):
                print(f"\n--- Processando lote {i}/{len(lotes)} ({len(lote)} produtos) ---")
                detailed_lote = extract_product_details(lote, site_code)
                detailed_products.extend(detailed_lote)
                
                # Salvar resultados parciais para evitar perda de dados
                if i < len(lotes):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    partial_path = os.path.join("ml_data_exports", f"ml_detalhes_parcial_lote{i}_{timestamp}.csv")
                    
                    # Converter para DataFrame e exportar
                    partial_df = pd.DataFrame(detailed_products)
                    partial_df.to_csv(partial_path, index=False, encoding='utf-8-sig')
                    
                    print(f"Resultados parciais salvos em: {partial_path}")
                    
                    # Perguntar se deseja continuar ou pausar
                    if i < len(lotes):
                        continuar = input(f"\nProcessados {len(detailed_products)}/{len(products)} produtos. Continuar para o próximo lote? (s/n): ").lower()
                        if continuar != 's':
                            print("Interrompendo o processamento. Dados parciais foram salvos.")
                            break
                        
                        # Aguardar entre lotes para evitar bloqueio
                        print("Aguardando 30 segundos antes do próximo lote para evitar bloqueio...")
                        time.sleep(30)
        else:
            # Extrair todos de uma vez
            detailed_products = extract_product_details(products, site_code)
        
        # Exibir resultados detalhados
        print("\n=== RESULTADOS DETALHADOS ===")
        for product in detailed_products:
            print_product_details(product)
        
        # Exportar dados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = "ml_data_exports"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        export_path = os.path.join(export_dir, f"ml_detalhes_{timestamp}.csv")
        
        # Converter para DataFrame e exportar
        df = pd.DataFrame(detailed_products)
        
        # Remover colunas irrelevantes ou duplicadas
        colunas_para_remover = ['price', 'seller', 'condition']
        for coluna in colunas_para_remover:
            if coluna in df.columns:
                df = df.drop(columns=[coluna])
        
        # Reorganizar as colunas em uma ordem mais lógica
        colunas_ordenadas = []
        colunas_prioritarias = ['index', 'title', 'preco', 'condicao', 
                              'vendedor_nome', 'vendedor_id', 'vendedor_avaliacao', 
                              'vendedor_vendas_concluidas', 'vendedor_qualidade_atendimento', 'vendedor_entrega_nos_prazos',
                              'avaliacao_media', 'total_avaliacoes', 'pagina', 'lote']
        
        # Adicionar colunas prioritárias que existem no dataframe
        for col in colunas_prioritarias:
            if col in df.columns:
                colunas_ordenadas.append(col)
        
        # Adicionar o restante das colunas
        for col in df.columns:
            if col not in colunas_ordenadas and col != 'link':
                colunas_ordenadas.append(col)
        
        # Adicionar link no final
        if 'link' in df.columns:
            colunas_ordenadas.append('link')
        
        # Reordenar se temos todas as colunas necessárias
        if all(col in df.columns for col in colunas_ordenadas):
            df = df[colunas_ordenadas]
            
        # Converter valores float para formato brasileiro
        for coluna in df.columns:
            if df[coluna].dtype == 'float64':
                df[coluna] = df[coluna].apply(lambda x: f"{x:.1f}".replace('.', ',') if pd.notnull(x) else '')
        
        df.to_csv(export_path, index=False, encoding='utf-8-sig')
        
        print(f"\nDados detalhados exportados para: {export_path}")
        print(f"Total de {len(detailed_products)} produtos analisados e exportados.")
    else:
        print("Nenhum produto encontrado. Tente com outro termo de busca.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        import traceback
        traceback.print_exc() 