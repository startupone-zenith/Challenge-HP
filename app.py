import multiprocessing
import streamlit as st
import pandas as pd
import requests
import logging
import time
import random
import re
import traceback
from lxml import html
import base64
import io
from PIL import Image
from urllib.parse import quote_plus

# Configurar o multiprocessing para Streamlit
if __name__ == "__main__":
    multiprocessing.freeze_support()

# Suprimir warnings de contexto do Streamlit durante imports
import warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Importar os spiders do Scrapy
from mercadolivre_spider import run_spider, run_product_details_spider
from mercadolivre_spider_reviews import run_review_spider # Import the new review spider runner

def generate_csv_data(produtos, csv_config):
    """
    Gera dados CSV baseado na configuração de campos selecionados
    """
    csv_data = []
    basic_fields = csv_config['basic_fields']
    detailed_fields = csv_config['detailed_fields']
    
    # Verificar se precisa extrair dados detalhados
    needs_detailed_extraction = any(detailed_fields.values())
    
    for i, produto in enumerate(produtos):
        logging.info(f"Processando produto {i+1}/{len(produtos)} para CSV: {produto.get('TITULO PRODUTO', 'N/A')[:50]}...")
        
        row_data = {}
        
        # Campos básicos (já disponíveis da busca principal)
        if basic_fields.get('titulo'):
            row_data['Título'] = produto.get('TITULO PRODUTO', 'N/A')
        
        if basic_fields.get('preco'):
            row_data['Preço'] = produto.get('PREÇO', 'N/A')
        
        if basic_fields.get('preco_anterior'):
            row_data['Preço Anterior'] = produto.get('PREÇO ANTERIOR', 'N/A')
        
        if basic_fields.get('marca'):
            row_data['Marca'] = produto.get('MARCA', 'N/A')
        
        if basic_fields.get('vendedor'):
            row_data['Vendedor'] = produto.get('VENDEDOR', 'N/A')
        
        if basic_fields.get('link'):
            row_data['Link'] = produto.get('LINK', 'N/A')
        
        if basic_fields.get('id_produto'):
            row_data['ID Produto'] = produto.get('ID_PRODUTO', 'N/A')
        
        if basic_fields.get('imagem'):
            row_data['URL Imagem'] = produto.get('IMAGEM', 'N/A')
        
        if basic_fields.get('entrega'):
            row_data['Entrega'] = produto.get('ENTREGA', 'N/A')
        
        if basic_fields.get('entrega_full'):
            row_data['Entrega FULL'] = produto.get('ENTREGA FULL', 'N/A')
        
        if basic_fields.get('media_avaliacoes_busca'):
            row_data['Média Avaliações (Busca)'] = produto.get('MÉDIA AVALIAÇÕES', 'N/A')
        
        if basic_fields.get('total_avaliacoes_busca'):
            row_data['Total Avaliações (Busca)'] = produto.get('TOTAL AVALIAÇÕES', 'N/A')
        
        # Campos detalhados (requerem extração individual)
        if needs_detailed_extraction and produto.get('LINK') and produto.get('LINK') != 'N/A':
            try:
                # Extrair detalhes do produto
                product_details = run_product_details_spider(produto['LINK'])
                
                if product_details and product_details.get('extraction_success'):
                    if detailed_fields.get('descricao'):
                        row_data['Descrição'] = product_details.get('description', 'N/A')
                    
                    if detailed_fields.get('caracteristicas_principais'):
                        main_chars = product_details.get('main_characteristics', {})
                        if main_chars:
                            # Converter características para string formatada
                            chars_text = '; '.join([f"{k}: {v}" for k, v in main_chars.items()])
                            row_data['Características Principais'] = chars_text
                        else:
                            row_data['Características Principais'] = 'N/A'
                    
                    if detailed_fields.get('outras_caracteristicas'):
                        other_chars = product_details.get('other_characteristics', {})
                        if other_chars:
                            # Converter características para string formatada
                            chars_text = '; '.join([f"{k}: {v}" for k, v in other_chars.items()])
                            row_data['Outras Características'] = chars_text
                        else:
                            row_data['Outras Características'] = 'N/A'
                    
                    if detailed_fields.get('total_reviews_detalhado'):
                        review_stats = product_details.get('review_stats', {})
                        row_data['Total Reviews (Detalhado)'] = review_stats.get('total_reviews', 'N/A')
                    
                    if detailed_fields.get('distribuicao_estrelas'):
                        review_stats = product_details.get('review_stats', {})
                        star_distribution = review_stats.get('star_distribution', {})
                        
                        if star_distribution:
                            # Adicionar colunas para cada estrela
                            for star in range(5, 0, -1):  # 5 a 1 estrelas
                                star_data = star_distribution.get(star, {})
                                row_data[f'{star} Estrelas (%)'] = star_data.get('percentage', 0)
                                row_data[f'{star} Estrelas (Qtd)'] = star_data.get('count', 0)
                        else:
                            # Preencher com N/A se não houver dados
                            for star in range(5, 0, -1):
                                row_data[f'{star} Estrelas (%)'] = 'N/A'
                                row_data[f'{star} Estrelas (Qtd)'] = 'N/A'
                else:
                    # Preencher campos detalhados com N/A se extração falhou
                    if detailed_fields.get('descricao'):
                        row_data['Descrição'] = 'N/A'
                    if detailed_fields.get('caracteristicas_principais'):
                        row_data['Características Principais'] = 'N/A'
                    if detailed_fields.get('outras_caracteristicas'):
                        row_data['Outras Características'] = 'N/A'
                    if detailed_fields.get('total_reviews_detalhado'):
                        row_data['Total Reviews (Detalhado)'] = 'N/A'
                    if detailed_fields.get('distribuicao_estrelas'):
                        for star in range(5, 0, -1):
                            row_data[f'{star} Estrelas (%)'] = 'N/A'
                            row_data[f'{star} Estrelas (Qtd)'] = 'N/A'
                            
            except Exception as e:
                logging.error(f"Erro ao extrair detalhes para CSV do produto {i+1}: {str(e)}")
                # Preencher com N/A em caso de erro
                if detailed_fields.get('descricao'):
                    row_data['Descrição'] = 'ERRO'
                if detailed_fields.get('caracteristicas_principais'):
                    row_data['Características Principais'] = 'ERRO'
                if detailed_fields.get('outras_caracteristicas'):
                    row_data['Outras Características'] = 'ERRO'
                if detailed_fields.get('total_reviews_detalhado'):
                    row_data['Total Reviews (Detalhado)'] = 'ERRO'
                if detailed_fields.get('distribuicao_estrelas'):
                    for star in range(5, 0, -1):
                        row_data[f'{star} Estrelas (%)'] = 'ERRO'
                        row_data[f'{star} Estrelas (Qtd)'] = 'ERRO'
        
        csv_data.append(row_data)
    
    return csv_data

# Configuração do logger para Streamlit
logging.basicConfig(
    filename='scraper_errors.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True  # Força a reconfiguração do logger
)

# Configurar o logger para reduzir warnings desnecessários
logging.getLogger("streamlit").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Lista de User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# Função para realizar uma requisição HTTP para imagens
def make_request(url, max_retries=3, initial_wait=1):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
    }
    wait_time = initial_wait
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response
            else:
                logging.warning(f"Imagem - Tentativa {attempt+1}/{max_retries} - Status: {response.status_code} para URL: {url}")
        except Exception as e:
            logging.error(f"Imagem - Erro na tentativa {attempt+1}/{max_retries}: {str(e)} para URL: {url}")
        time.sleep(wait_time)
        wait_time *= 2
    return None

# Initialize session state variables if they don't exist
if 'reviews_data' not in st.session_state:
    st.session_state.reviews_data = None
if 'fetching_reviews_for_id' not in st.session_state:
    st.session_state.fetching_reviews_for_id = None
if 'last_fetched_product_id_reviews' not in st.session_state:
    st.session_state.last_fetched_product_id_reviews = None
if 'max_reviews_to_fetch' not in st.session_state:
    st.session_state.max_reviews_to_fetch = 50
if 'use_rating_percentages' not in st.session_state:
    st.session_state.use_rating_percentages = False
if 'rating_percentages' not in st.session_state:
    st.session_state.rating_percentages = {5: 35, 4: 28, 3: 7, 2: 15, 1: 15}  # Default percentages that sum to 100%
if 'product_details_data' not in st.session_state:
    st.session_state.product_details_data = {}
if 'fetching_details_for_url' not in st.session_state:
    st.session_state.fetching_details_for_url = None
if 'csv_generator_enabled' not in st.session_state:
    st.session_state.csv_generator_enabled = False
if 'csv_fields_config' not in st.session_state:
    st.session_state.csv_fields_config = {
        'basic_fields': {
            'titulo': True,
            'preco': True,
            'preco_anterior': True,
            'marca': True,
            'vendedor': True,
            'link': True,
            'id_produto': True,
            'imagem': False,
            'entrega': True,
            'entrega_full': True,
            'media_avaliacoes_busca': True,
            'total_avaliacoes_busca': True
        },
        'detailed_fields': {
            'descricao': False,
            'caracteristicas_principais': False,
            'outras_caracteristicas': False,
            'total_reviews_detalhado': True,
            'distribuicao_estrelas': True
        }
    }

# Título da aplicação
st.title("Detector de Falsificações ML")

# Interface para busca de produtos
st.write("Digite o produto que deseja buscar:")
search_query = st.text_input("Termo de busca", "cartucho hp")

# Opções de filtro
st.subheader("Opções de Filtro")

# Filtro de Ordenação
sort_options_display = {
    'Relevância': 'relevance',
    'Menor Preço': 'price_asc',
    'Maior Preço': 'price_desc'
}
selected_sort_display = st.selectbox(
    "Ordenar por:", 
    options=list(sort_options_display.keys()),
    index=0 # Padrão para Relevância
)
sort_by_value = sort_options_display[selected_sort_display]

# Filtro de Condição
condition_options_display = {
    'Todos': 'all',
    'Novo': 'new',
    'Usado': 'used'
}
selected_condition_display = st.selectbox(
    "Condição do produto:",
    options=list(condition_options_display.keys()),
    index=0 # Padrão para Todos
)
condition_value = condition_options_display[selected_condition_display]

# Campo para quantidade máxima de itens
max_items = st.number_input("Número máximo de itens a extrair:", 
                             min_value=1, 
                             max_value=500, 
                             value=10, # Reduced default for quicker testing
                             step=10,
                             help="Defina quantos produtos no máximo serão extraídos. Valores maiores podem aumentar o tempo de execução.")

# Layout em colunas para as opções adicionais
col1, col2 = st.columns(2)

# Opção para carregar imagens
with col1:
    load_images = st.checkbox("Carregar imagens dos produtos", value=True, 
                              help="Desative para busca mais rápida, sem exibir imagens dos produtos")

# Indicador de paginação
with col2:
    st.info("Com paginação automática: o sistema navegará por quantas páginas forem necessárias até atingir o limite de itens definido.")

# Seção do Gerador de CSV
st.subheader("📊 Gerador de CSV Configurável")

# Toggle para ativar o gerador de CSV
csv_enabled = st.checkbox(
    "🔧 Ativar Gerador de CSV Avançado", 
    value=st.session_state.csv_generator_enabled,
    help="Ative para configurar quais dados incluir no CSV e extrair informações detalhadas de cada produto"
)
st.session_state.csv_generator_enabled = csv_enabled

if csv_enabled:
    st.markdown("##### 📋 Configuração dos Campos do CSV")
    
    # Abas para organizar as configurações
    tab_basic, tab_detailed = st.tabs(["📦 Dados Básicos", "🔍 Dados Detalhados"])
    
    with tab_basic:
        st.markdown("**Campos extraídos da busca principal:**")
        
        basic_cols = st.columns(3)
        basic_fields = st.session_state.csv_fields_config['basic_fields']
        
        with basic_cols[0]:
            basic_fields['titulo'] = st.checkbox("Título do Produto", value=basic_fields['titulo'])
            basic_fields['preco'] = st.checkbox("Preço Atual", value=basic_fields['preco'])
            basic_fields['preco_anterior'] = st.checkbox("Preço Anterior", value=basic_fields['preco_anterior'])
            basic_fields['marca'] = st.checkbox("Marca", value=basic_fields['marca'])
        
        with basic_cols[1]:
            basic_fields['vendedor'] = st.checkbox("Vendedor", value=basic_fields['vendedor'])
            basic_fields['link'] = st.checkbox("Link do Produto", value=basic_fields['link'])
            basic_fields['id_produto'] = st.checkbox("ID do Produto", value=basic_fields['id_produto'])
            basic_fields['imagem'] = st.checkbox("URL da Imagem", value=basic_fields['imagem'])
        
        with basic_cols[2]:
            basic_fields['entrega'] = st.checkbox("Informações de Entrega", value=basic_fields['entrega'])
            basic_fields['entrega_full'] = st.checkbox("Entrega FULL", value=basic_fields['entrega_full'])
            basic_fields['media_avaliacoes_busca'] = st.checkbox("Média de Avaliações (Busca)", value=basic_fields['media_avaliacoes_busca'])
            basic_fields['total_avaliacoes_busca'] = st.checkbox("Total de Avaliações (Busca)", value=basic_fields['total_avaliacoes_busca'])
    
    with tab_detailed:
        st.markdown("**Campos extraídos das páginas individuais dos produtos:**")
        st.info("⚠️ **Atenção:** Estes campos requerem acesso individual a cada produto, aumentando significativamente o tempo de processamento.")
        
        detailed_cols = st.columns(2)
        detailed_fields = st.session_state.csv_fields_config['detailed_fields']
        
        with detailed_cols[0]:
            detailed_fields['descricao'] = st.checkbox("Descrição Completa", value=detailed_fields['descricao'])
            detailed_fields['caracteristicas_principais'] = st.checkbox("Características Principais", value=detailed_fields['caracteristicas_principais'])
            detailed_fields['outras_caracteristicas'] = st.checkbox("Outras Características", value=detailed_fields['outras_caracteristicas'])
        
        with detailed_cols[1]:
            detailed_fields['total_reviews_detalhado'] = st.checkbox("Total de Reviews (Detalhado)", value=detailed_fields['total_reviews_detalhado'])
            detailed_fields['distribuicao_estrelas'] = st.checkbox("Distribuição por Estrelas", value=detailed_fields['distribuicao_estrelas'])
    
    # Mostrar resumo da configuração
    basic_selected = sum(1 for v in basic_fields.values() if v)
    detailed_selected = sum(1 for v in detailed_fields.values() if v)
    
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    
    with summary_col1:
        st.metric("Campos Básicos", basic_selected, delta=f"de {len(basic_fields)}")
    
    with summary_col2:
        st.metric("Campos Detalhados", detailed_selected, delta=f"de {len(detailed_fields)}")
    
    with summary_col3:
        total_fields = basic_selected + detailed_selected
        st.metric("Total de Campos", total_fields)
    
    # Aviso sobre tempo de processamento
    if detailed_selected > 0:
        estimated_time = max_items * detailed_selected * 2  # Estimativa: 2 segundos por campo detalhado por produto
        st.warning(f"⏱️ **Tempo estimado:** ~{estimated_time//60}min {estimated_time%60}s para {max_items} produtos com {detailed_selected} campos detalhados")
    
    st.markdown("---")

# Configurações de Reviews
st.subheader("⭐ Configurações de Reviews")

# Toggle para escolher entre modo geral ou por rating
use_rating_percentages = st.checkbox(
    "🎯 Configurar limites específicos por estrela", 
    value=st.session_state.use_rating_percentages,
    help="Ative para definir quantas reviews coletar para cada nota (1-5 estrelas)"
)
st.session_state.use_rating_percentages = use_rating_percentages

if use_rating_percentages:
    # Primeiro, configurar o total de reviews desejado
    col_total, col_info = st.columns([2, 1])
    
    with col_total:
        total_reviews_desired = st.number_input(
            "Total de reviews a coletar:",
            min_value=10,
            max_value=230,  # Limite técnico da API
            value=100,
            step=10,
            help="Número total de reviews que serão distribuídas pelas categorias de estrelas"
        )
    
    with col_info:
        st.info("💡 **Dica:** Configure as porcentagens abaixo para cada tipo de avaliação")
    
    st.markdown("##### 🌟 Distribuição percentual por estrela:")
    
    # Layout em colunas para os sliders de rating
    rating_cols = st.columns(5)
    
    for i, (rating, col) in enumerate(zip([5, 4, 3, 2, 1], rating_cols)):
        with col:
            new_percentage = st.number_input(
                f"{rating}⭐",
                min_value=0,
                max_value=100,
                value=st.session_state.rating_percentages[rating],
                step=5,
                key=f"rating_{rating}_percentage",
                help=f"Porcentagem de reviews com {rating} estrelas"
            )
            st.session_state.rating_percentages[rating] = new_percentage
    
    # Validar e mostrar resumo
    total_percentage = sum(st.session_state.rating_percentages.values())
    
    if total_percentage != 100:
        st.warning(f"⚠️ **Atenção:** As porcentagens somam {total_percentage}% (deve somar 100%)")
    else:
        st.success(f"✅ **Distribuição válida:** {total_percentage}% configurado")
    
    # Mostrar distribuição calculada
    st.markdown("##### 📊 Distribuição calculada:")
    
    calc_cols = st.columns(5)
    calculated_totals = {}
    
    for i, rating in enumerate([5, 4, 3, 2, 1]):
        with calc_cols[i]:
            if total_percentage > 0:
                # Calcular proporcionalmente mesmo se não somar exatamente 100%
                normalized_percentage = st.session_state.rating_percentages[rating] / total_percentage * 100
                calculated_amount = int((normalized_percentage / 100) * total_reviews_desired)
                calculated_totals[rating] = calculated_amount
                st.metric(f"{rating}⭐", f"{calculated_amount}", delta=f"{st.session_state.rating_percentages[rating]}%")
            else:
                calculated_totals[rating] = 0
                st.metric(f"{rating}⭐", "0", delta="0%")
    
    # Armazenar valores calculados para uso posterior
    st.session_state.calculated_rating_limits = calculated_totals
    st.session_state.total_reviews_configured = total_reviews_desired
    
else:
    # Modo geral (original)
    col_reviews1, col_reviews2 = st.columns(2)
    
    with col_reviews1:
        # Definir o valor atual, limitando ao máximo permitido se necessário
        current_value = min(st.session_state.max_reviews_to_fetch, 230)
        
        max_reviews = st.number_input(
            "Máximo de reviews por produto:",
            min_value=10,
            max_value=230,  # Limite técnico da API (200 offset + 30 limit)
            value=current_value,
            step=10,
            help="Quantas opiniões coletar quando clicar em 'Ver Opiniões Detalhadas'. Máximo: 230 reviews."
        )
        st.session_state.max_reviews_to_fetch = max_reviews
    
    with col_reviews2:
        st.info(f"📊 **Configuração atual:** {max_reviews} reviews por produto\n\n💡 **Dica:** Valores maiores podem demorar mais para carregar, mas oferecem análise mais completa.")

# Botões para busca
button_col1, button_col2 = st.columns(2)

with button_col1:
    # Botão para busca normal
    if st.button("🔍 Buscar Produtos", type="primary"):
        st.session_state.reviews_data = None # Clear previous reviews
        st.session_state.fetching_reviews_for_id = None
        st.session_state.last_fetched_product_id_reviews = None
        if search_query:
            with st.spinner(f'Buscando até {max_items} produtos...'):
                try:
                    logging.info(f"Iniciando busca com Scrapy para: {search_query}, Sort: {sort_by_value}, Condition: {condition_value}, Max items: {max_items}")
                    produtos, urls_usadas = run_spider(search_query, 
                                                       extract_images=load_images, 
                                                       sort_by=sort_by_value, 
                                                       condition=condition_value,
                                                       max_items=max_items)
                    logging.info(f"Busca concluída. Produtos: {len(produtos)}, URLs: {urls_usadas}")
                    
                    st.session_state.search_results = produtos # Store results in session state
                    st.session_state.search_urls_used = urls_usadas

                except Exception as e:
                    st.error(f"Ocorreu um erro geral na aplicação durante a busca de produtos: {str(e)}")
                    logging.error(f"Erro na busca de produtos (app.py): {str(e)}")
                    logging.error(traceback.format_exc())
                    st.session_state.search_results = []
                    st.session_state.search_urls_used = []
        else:
            st.warning("Por favor, digite um termo de busca para continuar.")

with button_col2:
    # Botão para gerar CSV
    csv_button_disabled = not st.session_state.csv_generator_enabled
    if st.button("📊 Buscar e Gerar CSV", disabled=csv_button_disabled):
        if not st.session_state.csv_generator_enabled:
            st.warning("Ative o Gerador de CSV primeiro!")
        elif search_query:
            # Verificar se há campos selecionados
            basic_selected = sum(1 for v in st.session_state.csv_fields_config['basic_fields'].values() if v)
            detailed_selected = sum(1 for v in st.session_state.csv_fields_config['detailed_fields'].values() if v)
            
            if basic_selected == 0 and detailed_selected == 0:
                st.error("Selecione pelo menos um campo para incluir no CSV!")
            else:
                st.session_state.reviews_data = None # Clear previous reviews
                st.session_state.fetching_reviews_for_id = None
                st.session_state.last_fetched_product_id_reviews = None
                
                # Determinar texto do spinner baseado nos campos selecionados
                if detailed_selected > 0:
                    spinner_text = f'Buscando {max_items} produtos e extraindo {detailed_selected} campos detalhados...'
                else:
                    spinner_text = f'Buscando {max_items} produtos para CSV...'
                
                with st.spinner(spinner_text):
                    try:
                        # Primeira etapa: busca básica
                        st.info("🔍 Etapa 1/2: Buscando produtos...")
                        logging.info(f"Iniciando busca para CSV: {search_query}, Sort: {sort_by_value}, Condition: {condition_value}, Max items: {max_items}")
                        produtos, urls_usadas = run_spider(search_query, 
                                                           extract_images=load_images, 
                                                           sort_by=sort_by_value, 
                                                           condition=condition_value,
                                                           max_items=max_items)
                        logging.info(f"Busca concluída. Produtos: {len(produtos)}, URLs: {urls_usadas}")
                        
                        if produtos:
                            # Segunda etapa: gerar CSV
                            st.info("📊 Etapa 2/2: Gerando CSV com dados configurados...")
                            csv_data = generate_csv_data(produtos, st.session_state.csv_fields_config)
                            
                            # Criar DataFrame e CSV
                            df_csv = pd.DataFrame(csv_data)
                            csv_content = df_csv.to_csv(index=False).encode('utf-8')
                            
                            # Armazenar resultados
                            st.session_state.search_results = produtos
                            st.session_state.search_urls_used = urls_usadas
                            st.session_state.csv_data = csv_data
                            st.session_state.csv_content = csv_content
                            
                            st.success(f"✅ CSV gerado com sucesso! {len(csv_data)} produtos processados com {len(df_csv.columns)} campos.")
                        else:
                            st.error("Nenhum produto encontrado para gerar o CSV.")
                            
                    except Exception as e:
                        st.error(f"Erro durante a geração do CSV: {str(e)}")
                        logging.error(f"Erro na geração do CSV: {str(e)}")
                        logging.error(traceback.format_exc())
        else:
            st.warning("Por favor, digite um termo de busca para continuar.")

# Display search results if available in session state
if 'search_results' in st.session_state and st.session_state.search_results is not None:
    produtos = st.session_state.search_results
    urls_usadas = st.session_state.search_urls_used

    if not urls_usadas:
        st.warning("O spider não retornou nenhuma URL de busca. Verifique os logs do spider.")
    else:
        st.subheader("URLs de busca usadas pelo Scraper Principal:")
        for i, url in enumerate(urls_usadas):
            st.write(f"{i+1}. [{url}]({url})")
        st.markdown("---")
    
    if produtos:
        st.success(f"Encontrados {len(produtos)} produtos!")
        
        for i, produto in enumerate(produtos):
            product_id_field = produto.get('ID_PRODUTO', 'N/A')
            with st.container():
                st.markdown(f"### {produto.get('TITULO PRODUTO', 'Título não disponível')}")
                cols_main = st.columns([1, 3])
                
                with cols_main[0]: # Image
                    if load_images and produto.get('IMAGEM') and produto.get('IMAGEM') not in ['N/A', 'N/A (imagens desabilitadas)']:
                        try:
                            img_response = make_request(produto['IMAGEM'])
                            if img_response:
                                img = Image.open(io.BytesIO(img_response.content))
                                st.image(img, width=120)
                            else:
                                st.caption("Imagem não baixada")
                        except Exception as e:
                            st.caption("Erro imagem")
                            logging.error(f"Erro ao carregar imagem {produto['IMAGEM']}: {str(e)}")
                    elif not load_images:
                        st.caption("(Imagens desabilitadas)")
                    else:
                        st.caption("Sem imagem")
                
                with cols_main[1]: # Product Info
                    if produto.get('LINK'):
                        st.markdown(f"**Link:** <a href='{produto['LINK']}' target='_blank'>Ver no Mercado Livre</a>", unsafe_allow_html=True)
                    
                    st.write(f"**Preço:** {produto.get('PREÇO', 'N/A')}")
                    if produto.get('PREÇO ANTERIOR', 'N/A') != 'N/A':
                        st.write(f"**Preço anterior:** <s style='color: grey;'>{produto.get('PREÇO ANTERIOR', 'N/A')}</s>", unsafe_allow_html=True)
                    
                    st.write(f"**Marca:** {produto.get('MARCA', 'N/A')}")
                    st.write(f"**ID Produto:** {product_id_field}")
                    st.write(f"**Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                    
                    avg_rating = produto.get('MÉDIA AVALIAÇÕES', 'N/A')
                    total_ratings = produto.get('TOTAL AVALIAÇÕES', 'N/A')
                    if avg_rating != 'N/A':
                        st.write(f"**Avaliação (na busca):** {avg_rating}⭐ ({total_ratings} avaliações)")
                    else:
                        st.write("**Avaliação (na busca):** N/A")

                    st.write(f"**Entrega:** {produto.get('ENTREGA', 'N/A')}")
                    if produto.get('ENTREGA FULL', 'Não') == 'Sim':
                        st.markdown("**Entrega FULL:** <span style='color:green;font-weight:bold;'>Sim</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"**Entrega FULL:** Não")

                # --- Product Details Section ---
                if produto.get('LINK') and produto.get('LINK') != 'N/A':
                    st.markdown("##### 🔍 Análise Detalhada do Produto")
                    
                    details_col1, details_col2 = st.columns([2, 1])
                    
                    with details_col1:
                        details_button_key = f"details_button_{produto.get('LINK', '')}_{i}"
                        if st.button("📋 Analisar Descrição e Características", key=details_button_key):
                            st.session_state.fetching_details_for_url = produto['LINK']
                            
                            with st.spinner(f"Analisando detalhes do produto..."):
                                product_details = run_product_details_spider(produto['LINK'])
                                st.session_state.product_details_data[produto['LINK']] = product_details
                                st.rerun()
                    
                    with details_col2:
                        if produto['LINK'] in st.session_state.product_details_data:
                            details = st.session_state.product_details_data[produto['LINK']]
                            if details and details.get('extraction_success'):
                                st.success("✅ Detalhes extraídos")
                            else:
                                st.error("❌ Falha na extração")
                        else:
                            st.caption("🔍 Clique para analisar")
                    
                    # Display product details if available
                    if produto['LINK'] in st.session_state.product_details_data:
                        details = st.session_state.product_details_data[produto['LINK']]
                        if details and details.get('extraction_success'):
                            with st.expander("📋 Detalhes do Produto", expanded=True):
                                # Descrição
                                st.markdown("**📝 Descrição do Produto:**")
                                if details.get('description') and details['description'] != 'N/A':
                                    st.write(details['description'])
                                else:
                                    st.write("Descrição não disponível")
                                
                                st.markdown("---")
                                
                                # Características Principais
                                main_chars = details.get('main_characteristics', {})
                                if main_chars:
                                    st.markdown("**🔧 Características Principais:**")
                                    
                                    # Organizar em colunas para melhor visualização
                                    char_cols = st.columns(2)
                                    char_items = list(main_chars.items())
                                    
                                    for idx, (char_name, char_value) in enumerate(char_items):
                                        with char_cols[idx % 2]:
                                            st.write(f"**{char_name}:** {char_value}")
                                else:
                                    st.markdown("**🔧 Características Principais:** Não disponíveis")
                                
                                # Outras Características
                                other_chars = details.get('other_characteristics', {})
                                if other_chars:
                                    st.markdown("---")
                                    st.markdown("**📋 Outras Características:**")
                                    
                                    # Organizar em colunas para melhor visualização
                                    other_cols = st.columns(2)
                                    other_items = list(other_chars.items())
                                    
                                    for idx, (char_name, char_value) in enumerate(other_items):
                                        with other_cols[idx % 2]:
                                            st.write(f"**{char_name}:** {char_value}")
                        elif details and not details.get('extraction_success'):
                            with st.expander("📋 Detalhes do Produto", expanded=True):
                                st.warning("⚠️ Não foi possível extrair os detalhes deste produto. O layout da página pode ter mudado ou as informações podem não estar disponíveis.")

                # --- Reviews Section ---
                if product_id_field != 'N/A':
                    st.markdown("##### ⭐ Análise de Opiniões")
                    # Layout para o botão de reviews e informações
                    reviews_col1, reviews_col2 = st.columns([2, 1])
                    
                    with reviews_col1:
                        button_key = f"reviews_button_{product_id_field}_{i}" # Unique key for button
                        if st.button("Ver Opiniões Detalhadas", key=button_key):
                            st.session_state.fetching_reviews_for_id = product_id_field
                            st.session_state.reviews_data = None # Clear previous reviews data or set to loading
                            st.session_state.last_fetched_product_id_reviews = None
                            
                            # Preparar parâmetros baseados na configuração
                            if st.session_state.use_rating_percentages:
                                if hasattr(st.session_state, 'calculated_rating_limits') and sum(st.session_state.rating_percentages.values()) == 100:
                                    rating_limits = st.session_state.calculated_rating_limits
                                    active_ratings = [f"{r}⭐:{l}" for r, l in sorted(rating_limits.items(), reverse=True) if l > 0]
                                    total_configured = st.session_state.total_reviews_configured
                                    spinner_text = f"Buscando {total_configured} reviews por rating ({', '.join(active_ratings)}) para o produto ID: {product_id_field}..."
                                    
                                    with st.spinner(spinner_text):
                                        reviews_result = run_review_spider(product_id_field, rating_limits=rating_limits)
                                else:
                                    st.error("⚠️ Configure as porcentagens corretamente (devem somar 100%) antes de buscar reviews.")
                                    continue
                            else:
                                spinner_text = f"Buscando até {st.session_state.max_reviews_to_fetch} opiniões para o produto ID: {product_id_field}..."
                                
                                with st.spinner(spinner_text):
                                    reviews_result = run_review_spider(product_id_field, max_reviews=st.session_state.max_reviews_to_fetch)
                            
                            st.session_state.reviews_data = reviews_result
                            st.session_state.last_fetched_product_id_reviews = product_id_field
                            st.rerun() # Replace experimental_rerun with rerun
                    
                    with reviews_col2:
                        if st.session_state.use_rating_percentages:
                            if hasattr(st.session_state, 'total_reviews_configured'):
                                st.caption(f"🎯 Coleta por percentual: {st.session_state.total_reviews_configured} reviews")
                            else:
                                st.caption(f"🎯 Configure percentuais primeiro")
                        else:
                            st.caption(f"🔍 Coletará até {st.session_state.max_reviews_to_fetch} reviews")
                
                # Display reviews if they are for the current product and data exists
                if st.session_state.last_fetched_product_id_reviews == product_id_field and st.session_state.reviews_data:
                    reviews = st.session_state.reviews_data
                    reviews_count = len(reviews.get('reviews', []))
                    with st.expander(f"Opiniões Detalhadas do Produto ({reviews_count} reviews coletadas)", expanded=True):
                        # Cabeçalho com estatísticas
                        if st.session_state.use_rating_percentages:
                            # Mostrar estatísticas por rating
                            st.markdown("**📊 Coleta por Rating Configurada**")
                            
                            # Calcular estatísticas reais vs configuradas
                            actual_by_rating = {}
                            for review in reviews.get('reviews', []):
                                rating = int(review.get('rating', 0)) if review.get('rating', '0').isdigit() else 0
                                actual_by_rating[rating] = actual_by_rating.get(rating, 0) + 1
                            
                            # Mostrar comparação
                            comparison_cols = st.columns(5)
                            for i, rating in enumerate([5, 4, 3, 2, 1]):
                                with comparison_cols[i]:
                                    if hasattr(st.session_state, 'calculated_rating_limits'):
                                        configured = st.session_state.calculated_rating_limits.get(rating, 0)
                                        actual = actual_by_rating.get(rating, 0)
                                        percentage = st.session_state.rating_percentages.get(rating, 0)
                                        if configured > 0:
                                            efficiency = f"{(actual/configured*100):.0f}%" if configured > 0 else "0%"
                                            st.metric(f"{rating}⭐", f"{actual}/{configured}", delta=f"{percentage}%")
                                        else:
                                            st.metric(f"{rating}⭐", "0/0", delta=f"{percentage}%")
                                    else:
                                        st.metric(f"{rating}⭐", "N/A", delta="N/A")
                        else:
                            # Estatísticas gerais
                            stats_col1, stats_col2, stats_col3 = st.columns(3)
                            with stats_col1:
                                st.metric("Reviews Coletadas", reviews_count)
                            with stats_col2:
                                configured_limit = st.session_state.max_reviews_to_fetch
                                st.metric("Limite Configurado", configured_limit)
                            with stats_col3:
                                collection_rate = f"{(reviews_count / configured_limit * 100):.1f}%" if configured_limit > 0 else "0%"
                                st.metric("Taxa de Coleta", collection_rate)
                        
                        st.markdown("---")
                        st.write(f"**ID do Produto (Reviews):** {reviews.get('product_id')}")
                        st.write(f"**Avaliação Geral (Detalhada):** {reviews.get('overall_rating', 'N/A')} ⭐")
                        st.write(f"**Total de Avaliações (Detalhada):** {reviews.get('total_reviews_count', 'N/A')}")
                        
                        st.markdown("##### Avaliação por Características:")
                        if reviews.get('characteristics_ratings'):
                            for char_rating in reviews['characteristics_ratings']:
                                st.write(f"- {char_rating['characteristic_name']}: {char_rating['characteristic_rating']} / 5")
                        else:
                            st.write("Nenhuma avaliação por característica encontrada.")
                        
                        st.markdown("##### Comentários:")
                        if reviews.get('reviews'):
                            # Calcular estatísticas das reviews
                            ratings = [int(rev.get('rating', 0)) for rev in reviews['reviews'] if rev.get('rating', '0').isdigit()]
                            if ratings:
                                avg_rating = sum(ratings) / len(ratings)
                                rating_distribution = {i: ratings.count(i) for i in range(1, 6)}
                                
                                # Mostrar resumo estatístico
                                with st.container():
                                    st.markdown("**📊 Resumo das Avaliações Coletadas:**")
                                    summary_col1, summary_col2 = st.columns(2)
                                    
                                    with summary_col1:
                                        st.write(f"**Média das reviews:** {avg_rating:.1f} ⭐")
                                        st.write(f"**Total de comentários:** {len(reviews['reviews'])}")
                                    
                                    with summary_col2:
                                        st.write("**Distribuição de notas:**")
                                        for rating, count in sorted(rating_distribution.items(), reverse=True):
                                            percentage = (count / len(ratings)) * 100
                                            st.write(f"{rating}⭐: {count} ({percentage:.1f}%)")
                                    
                                    st.markdown("---")
                            
                            # Mostrar comentários individuais
                            for i, rev_item in enumerate(reviews['reviews']):
                                with st.container():
                                    comment_header_col1, comment_header_col2 = st.columns([3, 1])
                                    with comment_header_col1:
                                        st.markdown(f"**Review #{i+1} - Nota:** {rev_item.get('rating','N/A')} ⭐")
                                    with comment_header_col2:
                                        st.markdown(f"*{rev_item.get('date','N/A')}*")
                                    
                                    st.markdown(f"**Comentário:** {rev_item.get('text','N/A')}")
                                    st.markdown(f"**Útil:** {rev_item.get('helpful_count','0')} pessoas acharam útil")
                                    st.markdown("---")
                        else:
                            st.write("Nenhum comentário encontrado.")
                elif st.session_state.last_fetched_product_id_reviews == product_id_field and not st.session_state.reviews_data:
                     with st.expander("Opiniões Detalhadas do Produto", expanded=True):
                        st.warning("Não foi possível carregar as opiniões para este produto.")

            st.markdown("***") # Main Divisor between products
        
        # Opções para baixar os resultados como CSV
        if produtos:
            download_col1, download_col2 = st.columns(2)
            
            with download_col1:
                # CSV básico (dados da busca)
                df = pd.DataFrame(produtos)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Baixar CSV Básico",
                    data=csv,
                    file_name=f"produtos_mercadolivre_basico_{search_query.replace(' ', '_')}.csv",
                    mime="text/csv",
                    help="Download dos dados básicos extraídos da busca"
                )
            
            with download_col2:
                # CSV configurável (se foi gerado)
                if 'csv_content' in st.session_state and st.session_state.csv_content:
                    st.download_button(
                        label="📊 Baixar CSV Configurado",
                        data=st.session_state.csv_content,
                        file_name=f"produtos_mercadolivre_detalhado_{search_query.replace(' ', '_')}.csv",
                        mime="text/csv",
                        help="Download do CSV com campos configurados e dados detalhados"
                    )
                else:
                    st.caption("Use 'Buscar e Gerar CSV' para criar um CSV configurável")

    elif 'search_results' in st.session_state: # Searched but no products found
        st.error("Nenhum produto encontrado para a busca realizada. Verifique os logs ou tente outros termos/filtros.")

# Rodapé
st.markdown("---")
st.write("Criado para detecção de falsificações no Mercado Livre")

# Configuração para execução adequada do multiprocessing com Streamlit
if __name__ == "__main__":
    # Esta seção garante que o multiprocessing funcione corretamente
    # quando o arquivo for executado diretamente
    pass
 