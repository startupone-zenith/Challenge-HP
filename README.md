# Detector de Falsificações Mercado Livre

Este projeto é um scraper para o Mercado Livre que permite buscar produtos e avaliações, ajudando a detectar possíveis falsificações.

## Funcionalidades

- Busca de produtos no Mercado Livre com filtros (ordenação, condição, etc.)
- Extração de avaliações de produtos específicos
- Possibilidade de baixar os dados em formato CSV
- Interface web amigável

## Requisitos

- Python 3.8 ou superior
- Bibliotecas listadas em `requirements.txt`

## Instalação

1. Clone este repositório:
```
git clone <url-repositorio>
cd Challenge-HP
```

2. Crie e ative um ambiente virtual (opcional):
```
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. Instale as dependências:
```
pip install -r requirements.txt
```

## Execução

### Versão Streamlit (original)

```
streamlit run app.py
```

A aplicação estará disponível em `http://localhost:8501`

### Versão Flask (nova)

```
python app_flask.py
```

A aplicação estará disponível em `http://localhost:5000`

## Estrutura do Projeto

- `app.py`: Aplicação Streamlit original
- `app_flask.py`: Nova versão da aplicação usando Flask
- `mercadolivre_spider.py`: Spider para extrair dados de produtos
- `mercadolivre_spider_reviews.py`: Spider para extrair avaliações de produtos
- `templates/`: Diretório contendo templates HTML para a versão Flask
- `static/`: Diretório para arquivos estáticos (CSS, imagens temporárias)

## Uso

1. Na página inicial, digite o termo de busca desejado e selecione os filtros
2. Clique em "Buscar" para iniciar a busca por produtos
3. Visualize os resultados e baixe como CSV se desejar
4. Para buscar avaliações, cole a URL da página de avaliações do Mercado Livre e clique em "Buscar Avaliações"

## Notas

- A extração de imagens pode tornar a busca mais lenta. Desative a opção se velocidade for necessária.
- Respeite os limites e políticas do Mercado Livre ao utilizar este scraper.
- Alguns produtos podem não retornar todos os dados (preço, avaliações, etc.) dependendo da disponibilidade no site. 