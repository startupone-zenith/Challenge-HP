# Challenge Sprint - HP
## Sprint 2 - RPA

### Entregável 2: Enriquecimento, Análise Exploratória e Integração de Múltiplas Fontes da Base de Dados

---

#### 1. Introdução

Este relatório descreve o processo de transformação e enriquecimento dos dados brutos coletados, conforme os requisitos do Entregável 2 da disciplina de RPA. O foco desta fase foi converter o dataset inicial em um ativo analítico de alto valor, através de limpeza, padronização, criação de novas features e, crucialmente, a integração de uma fonte de dados externa para enriquecer as informações dos produtos.

---

#### 2. Limpeza e Padronização dos Dados

A qualidade dos dados é fundamental para qualquer análise subsequente. O sistema implementado no `app.py` possui um módulo completo de limpeza e padronização, que inclui:

-   **Correção de Tipos de Dados**: Funções como `extrair_preco_numerico` e `prepare_dataframe` garantem que colunas como preço e avaliações sejam convertidas para formato numérico, removendo símbolos (R$), espaços e tratando vírgulas como separadores decimais.
-   **Tratamento de Strings**: Aplicação de `strip()` e normalização para minúsculas para garantir consistência.
-   **Limpeza de Texto para Análise**: A função `clean_text_for_analysis` foi aprimorada para remover não apenas stopwords e pontuação, mas também para detectar e eliminar URLs completas, que poderiam poluir análises textuais como o WordCloud.
-   **Módulo de Limpeza de Reviews**: Uma seção dedicada na interface permite ao usuário final aplicar filtros avançados, como remover reviews vazias, duplicadas e normalizar ratings e datas, gerando um dataset limpo para download.

---

#### 3. Enriquecimento com Colunas Derivadas

Uma das etapas mais importantes foi a engenharia de novas features para enriquecer o dataset. Isso foi feito através do sistema de **rotulagem heurística** implementado na função `rotular_produto_heuristico`:

-   **`rotulo_heuristico`**: Criação da feature target binária ("original" ou "suspeito").
-   **`score_total`**: Uma feature numérica que quantifica o nível de suspeita, agregando os scores de diferentes análises. É uma variável poderosa para modelagem.
-   **`score_titulo`, `score_preco`**: Features intermediárias que detalham a origem da suspeita (se vem do título ou do preço).
-   **`vendedor_oficial`**: Uma feature binária (True/False) que classifica o vendedor com base em uma lista pré-definida de parceiros oficiais da HP.
-   **Indicadores de Palavras-Chave**: A análise textual na interface também serve como uma forma de enriquecimento, identificando a presença de palavras suspeitas (`compativel`, `generico`) ou positivas (`original`, `qualidade`).

---

#### 4. Análise Exploratória

A análise exploratória foi totalmente automatizada e integrada à interface do Streamlit, na aba **"🔬 Análise Exploratória (EDA)"**. Esta seção funciona como um dashboard de BI, permitindo ao usuário interagir com os dados de forma visual e intuitiva, explorando:

-   **Estatísticas Descritivas**: Visão geral completa da qualidade e distribuição dos dados.
-   **Análise de Preços**: Histogramas e box plots para entender a dispersão dos preços.
-   **Análise Textual de Reviews**: Ferramenta focada em produto, com WordCloud e Análise de Sentimento para extrair insights qualitativos.
-   **Correlações e Segmentação**: Heatmaps e scatter plots para descobrir relações entre as variáveis.

---

#### 5. Coleta e Integração de Dados de Novas Fontes

Para cumprir o requisito de integração de múltiplas fontes, a solução foi projetada para combinar dados de duas origens distintas, embora ambas sejam do ecossistema do Mercado Livre:

1.  **Fonte Primária: Web Scraping de Páginas de Produto (`mercadolivre_spider.py`)**
    -   **Estratégia**: Coleta de dados estruturados diretamente do HTML das páginas de busca e de produto.
    -   **Dados Obtidos**: Título, preço, vendedor, descrição, características técnicas.

2.  **Fonte Secundária (Externa): API de Reviews do Mercado Livre (`mercadolivre_spider_reviews.py`)**
    -   **Estratégia**: Utilização de um cliente de API para acessar um endpoint JSON não documentado publicamente (`api.mercadolibre.com/reviews/item/{PRODUCT_ID}`). Esta abordagem é significativamente mais rápida e confiável do que tentar extrair reviews do HTML.
    -   **Dados Obtidos**: Texto completo das reviews, rating individual, data, contagem de votos úteis.

**Processo de Integração e Fusão:**

-   O **`ID do Produto`**, extraído da URL na fonte primária, serve como a **chave de junção** (primary key) para conectar os dois datasets.
-   Durante a geração do CSV final (`generate_csv_data`), a aplicação itera sobre os produtos da fonte primária e, para cada um, dispara uma chamada à fonte secundária (API de reviews) usando o `ID do Produto`.
-   Os dados de reviews são então **anexados como novas colunas** ao registro do produto correspondente, criando uma base de dados consolidada e enriquecida.

Esta estratégia de duas fontes (scraping de HTML + consumo de API) permitiu a criação de um dataset muito mais rico do que seria possível com apenas uma abordagem, combinando dados de anúncio com o feedback qualitativo e quantitativo dos consumidores.

---
