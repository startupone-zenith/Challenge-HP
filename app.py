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
import multiprocessing

# Importar o spider do Scrapy
from mercadolivre_spider import run_spider
# Importar o novo spider de reviews
from mercadolivre_spider_reviews import run_spider_reviews

# Configuração do logger
logging.basicConfig(filename='scraper_errors.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Lista de User Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
]

# Função para realizar uma requisição HTTP para imagens (pode ser simplificada se o spider retornar dados de imagem)
def make_request(url, max_retries=3, initial_wait=1): # Reduzido initial_wait para imagens
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
    }
    wait_time = initial_wait
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=5) # Timeout menor para imagens
            if response.status_code == 200:
                return response
            else:
                logging.warning(f"Imagem - Tentativa {attempt+1}/{max_retries} - Status: {response.status_code} para URL: {url}")
        except Exception as e:
            logging.error(f"Imagem - Erro na tentativa {attempt+1}/{max_retries}: {str(e)} para URL: {url}")
        time.sleep(wait_time)
        wait_time *= 2
    return None

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
                             value=100,
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

# Botão para iniciar a busca
if st.button("Buscar"):
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
                
                if not urls_usadas:
                    st.warning("O spider não retornou nenhuma URL de busca. Verifique os logs do spider.")
                else:
                    st.subheader("URLs de busca usadas pelo Scraper:")
                    for i, url in enumerate(urls_usadas):
                        st.write(f"{i+1}. [{url}]({url})")
                    st.markdown("---")
                
                if produtos:
                    # Converter para DataFrame
                    df = pd.DataFrame(produtos)
                    
                    st.success(f"Encontrados {len(produtos)} produtos!")
                    
                    # Exibir produtos com imagens (ou sem, conforme a opção)
                    for i, produto in enumerate(produtos):
                        with st.container():
                            cols = st.columns([1, 3]) # Ajuste na proporção das colunas
                            
                            # Imagem do produto
                            with cols[0]:
                                if load_images and produto.get('IMAGEM') and produto.get('IMAGEM') not in ['N/A', 'N/A (imagens desabilitadas)']:
                                    try:
                                        img_response = make_request(produto['IMAGEM'])
                                        if img_response:
                                            img = Image.open(io.BytesIO(img_response.content))
                                            st.image(img, width=120) # Ajuste no tamanho da imagem
                                        else:
                                            st.caption("Imagem não baixada")
                                    except Exception as e:
                                        st.caption("Erro imagem")
                                        logging.error(f"Erro ao carregar imagem {produto['IMAGEM']}: {str(e)}")
                                elif not load_images:
                                    st.caption("(Imagens desabilitadas)")
                                else:
                                    st.caption("Sem imagem") # Se 'IMAGEM' for N/A
                            
                            # Informações do produto
                            with cols[1]:
                                if produto.get('LINK'):
                                    st.markdown(f"**<a href='{produto['LINK']}' target='_blank'>{produto.get('TITULO PRODUTO', 'Título não disponível')}</a>**", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**{produto.get('TITULO PRODUTO', 'Título não disponível')}**")
                                
                                st.write(f"**Preço:** {produto.get('PREÇO', 'N/A')}")
                                if produto.get('PREÇO ANTERIOR', 'N/A') != 'N/A':
                                    st.write(f"**Preço anterior:** <s style='color: grey;'>{produto.get('PREÇO ANTERIOR', 'N/A')}</s>", unsafe_allow_html=True)
                                
                                st.write(f"**Marca:** {produto.get('MARCA', 'N/A')}")
                                st.write(f"**Vendedor:** {produto.get('VENDEDOR', 'N/A')}")
                                
                                avg_rating = produto.get('MÉDIA AVALIAÇÕES', 'N/A')
                                total_ratings = produto.get('TOTAL AVALIAÇÕES', 'N/A')
                                if avg_rating != 'N/A':
                                    st.write(f"**Avaliação:** {avg_rating}⭐ ({total_ratings} avaliações)")
                                else:
                                    st.write("**Avaliação:** N/A")

                                st.write(f"**Entrega:** {produto.get('ENTREGA', 'N/A')}")
                                if produto.get('ENTREGA FULL', 'Não') == 'Sim':
                                    st.markdown("**Entrega FULL:** <span style='color:green;font-weight:bold;'>Sim</span>", unsafe_allow_html=True)
                                else:
                                    st.write(f"**Entrega FULL:** Não")
                        
                        st.markdown("---") # Divisor entre produtos
                    
                    # Opção para baixar os resultados como CSV
                    csv = df.to_csv(index=False).encode('utf-8') # Garantir encoding utf-8
                    b64 = base64.b64encode(csv).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="produtos_mercadolivre.csv">Baixar resultados como CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("Nenhum produto encontrado. Verifique os logs ou tente outra busca.")
            except Exception as e:
                st.error(f"Ocorreu um erro geral na aplicação: {str(e)}")
                logging.error(f"Erro na busca de produtos (app.py): {str(e)}")
                logging.error(traceback.format_exc())
    else:
        st.warning("Por favor, digite um termo de busca para continuar.")

# Seção para busca de reviews
st.markdown("---") # Divisor visual
st.header("Buscar Avaliações de um Produto Específico")
review_url_input = st.text_input("Cole a URL da página de reviews do Mercado Livre:", \
                                 placeholder="Ex: https://www.mercadolivre.com.br/noindex/catalog/reviews/MLB24113448?noIndex=true&access=view_all...")

if st.button("Buscar Avaliações"):
    if review_url_input and review_url_input.startswith("http"):
        with st.spinner("Buscando avaliações... Este processo pode levar alguns minutos."):
            try:
                logging.info(f"Iniciando busca de reviews para a URL: {review_url_input}")
                reviews_data = run_spider_reviews(review_url_input)
                logging.info(f"Busca de reviews concluída. Encontradas {len(reviews_data)} avaliações.")

                if reviews_data:
                    st.success(f"Encontradas {len(reviews_data)} avaliações!")
                    
                    # Opcional: Converter para DataFrame se quiser baixar CSV das reviews também
                    # df_reviews = pd.DataFrame(reviews_data)
                    # csv_reviews = df_reviews.to_csv(index=False).encode('utf-8')
                    # b64_reviews = base64.b64encode(csv_reviews).decode()
                    # href_reviews = f'<a href="data:file/csv;base64,{b64_reviews}" download="reviews_mercadolivre.csv">Baixar avaliações como CSV</a>'
                    # st.markdown(href_reviews, unsafe_allow_html=True)
                    # st.markdown("---")

                    for i, review in enumerate(reviews_data):
                        with st.container():
                            st.markdown(f"**Avaliação {i+1}**")
                            
                            # Estrelas: Exibir como texto "X estrelas" ou visualmente se preferir
                            stars_display = "⭐" * review.get('ESTRELAS', 0)
                            st.markdown(f"**Estrelas:** {stars_display} ({review.get('ESTRELAS', 'N/A')}/5)")
                            
                            st.write(f"**Data:** {review.get('DATA', 'N/A')}")
                            st.markdown(f"**Comentário:**")
                            st.info(f"{review.get('COMENTARIO', 'N/A')}") # Usar st.info ou st.markdown para o texto
                            
                            curtidas = review.get('CURTIDAS', '0')
                            st.write(f"**Útil para:** {curtidas} pessoas")
                        st.markdown("---") # Divisor entre avaliações
                else:
                    st.warning("Nenhuma avaliação encontrada para esta URL ou ocorreu um erro durante a extração. Verifique os logs.")
            
            except Exception as e:
                st.error(f"Ocorreu um erro ao buscar as avaliações: {str(e)}")
                logging.error(f"Erro na busca de reviews (app.py): {str(e)}")
                logging.error(traceback.format_exc())
    elif not review_url_input:
        st.warning("Por favor, insira uma URL de reviews para continuar.")
    else:
        st.error("URL inválida. Por favor, insira uma URL válida do Mercado Livre (começando com http ou https).")

# Rodapé
st.markdown("---")
st.write("Criado para detecção de falsificações no Mercado Livre")

# Adicionar freeze_support() para o caso de execução direta do script app.py 
# ou se for empacotado em um executável.
if __name__ == '__main__':
    multiprocessing.freeze_support()
    # O restante do código do Streamlit já é executado quando o script é chamado com `streamlit run app.py`
    # por isso, não é necessário chamar st.run() ou similar aqui.
    # O freeze_support() é a principal adição para este bloco em um contexto de Streamlit + multiprocessing. 