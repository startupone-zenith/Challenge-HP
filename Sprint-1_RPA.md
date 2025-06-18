# Challenge Sprint - HP
## Sprint 1 - RPA

### Entregável 1: Coleta Automatizada de Dados de Produtos HP em E-commerce (RPA)

---

#### 1. Introdução e Estratégia de Automação

Este documento detalha a implementação do robô de automação (RPA) para a coleta massiva e estruturada de dados de produtos HP, conforme os requisitos da disciplina de Robotic Process Automation. A solução foi desenvolvida em **Python** com o framework **Scrapy**, escolhido por sua arquitetura assíncrona, alta performance e capacidade de gerenciar projetos de scraping complexos.

A estratégia adotada se concentrou em criar um sistema de coleta **robusto, reutilizável e otimizado**, capaz de extrair informações detalhadas do **Mercado Livre** e, subsequentemente, enriquecer esses dados com uma fonte secundária (API de reviews).

---

#### 2. Ferramentas e Tecnologias

-   **Linguagem**: Python 3.12
-   **Framework de Scraping**: Scrapy
-   **Análise e Manipulação de Dados**: Pandas, NumPy
-   **Gerenciamento de Processos**: `multiprocessing` para execução paralela dos spiders.
-   **Requisições HTTP**: `requests` (na API de reviews) com `ThreadPoolExecutor` para concorrência.
-   **Interface e Demonstração**: Streamlit

#### Otimizações de Performance Implementadas:

Para garantir a eficiência da coleta, diversas otimizações de performance foram configuradas em `scrapy_performance_config.py` e aplicadas aos spiders:

-   **Alta Concorrência**: O número de requisições simultâneas (`CONCURRENT_REQUESTS`) foi aumentado para 32 (e 64 para coletas de alto volume), superando o padrão de 16.
-   **Timeouts Agressivos**: O timeout de download (`DOWNLOAD_TIMEOUT`) foi reduzido para 15 segundos (padrão é 180s), evitando longas esperas em páginas lentas.
-   **Cache HTTP**: Ativado com duração de 1 hora (`HTTPCACHE_EXPIRATION_SECS`), o que previne requisições repetidas à mesma URL em um curto período.
-   **Pool de Conexões e DNS Cache**: Otimizações para reutilizar conexões e acelerar a resolução de nomes de domínio.

---

#### 3. Escopo e Coleta de Dados

O robô foi configurado para focar em anúncios de **cartuchos de tinta e suprimentos HP** no **Mercado Livre**. O spider principal (`mercadolivre_spider.py`) é parametrizável, aceitando:

-   `query`: Termo de busca (ex: "cartucho hp 664").
-   `sort_by`: Critério de ordenação ('relevance', 'price_asc', 'price_desc').
-   `condition`: Condição do produto ('all', 'new', 'used').
-   `max_items`: Número máximo de itens a coletar.

**Dados Extraídos de Cada Anúncio:**

O spider é projetado para extrair um conjunto rico de informações, tratando diferentes layouts de página com múltiplos seletores de fallback para garantir a robustez.

-   **Dados Principais**:
    -   `Título do anúncio`: `h2.ui-search-item__title`
    -   `Preço`: `.andes-money-amount__fraction` e `.andes-money-amount__cents`
    -   `Nome do vendedor`: `.ui-search-seller__name`
    -   `Link do anúncio`: `a.ui-search-item__group__element::attr(href)`
    -   `ID do Produto`: Extraído via regex do link do anúncio.

-   **Dados Detalhados (via `MercadoLivreProductDetailsSpider`)**:
    -   `Descrição detalhada`: Coletada de múltiplos parágrafos em `.ui-pdp-description__content`.
    -   `Características Principais`: Extraídas da tabela de especificações.
    -   `Outras Características`: Extraídas da tabela secundária.
    -   `Estatísticas de Reviews`: Total de reviews e distribuição percentual por estrelas.

-   **Dados de Reviews (via `MercadoLivreReviewsAPI`)**:
    -   Coleta massiva e concorrente de até 300 reviews por produto.
    -   Extração de `rating`, `texto`, `data`, `ID do autor` e `contagem de votos úteis`.

---

#### 4. Fluxo Automatizado Reutilizável

O código foi estruturado de forma modular para ser facilmente reutilizável e agendável:

1.  **Funções Wrapper**: As funções `run_spider`, `run_product_details_spider` e `run_review_spider` encapsulam a lógica de execução dos spiders em processos separados, tornando a chamada simples e direta a partir de qualquer outro script (como o `app.py`).

2.  **Parametrização**: Como mencionado, as funções de scraping são totalmente parametrizáveis, permitindo que a coleta seja direcionada para diferentes produtos ou filtros sem alterar o código do robô.

3.  **Tratamento de Erros**: Os spiders incluem lógica de `errback` e o processo de execução tem `timeouts` para lidar com falhas de rede ou páginas que não carregam, garantindo que o robô não trave indefinidamente.

4.  **Sistema de Cache**: Um sistema de cache em memória (`st.session_state`) foi implementado para armazenar os resultados das buscas, detalhes e reviews. Isso acelera drasticamente a re-execução de análises com os mesmos parâmetros.

---

#### 5. Limpeza e Armazenamento dos Dados

O processo de coleta já inclui etapas de limpeza e estruturação:

-   **Limpeza em Tempo Real**:
    -   **Preços**: A função `extrair_preco_numerico` utiliza regex para converter strings como "R$ 66,49" para o formato numérico `66.49`.
    -   **Strings**: `strip()` é aplicado em todos os campos textuais para remover espaços em branco.
    -   **Dados Estruturados**: As características são armazenadas em dicionários Python antes de serem salvas.

-   **Armazenamento**:
    -   A aplicação Streamlit oferece uma funcionalidade de **Dataset Generator** que permite ao usuário configurar quais campos deseja exportar.
    -   Os dados coletados e processados são então salvos em um **arquivo CSV** limpo e estruturado, pronto para análise, utilizando a biblioteca `pandas`. Cada linha do CSV representa um produto único, e as colunas correspondem às features extraídas.

Este fluxo automatizado garante a geração de uma base de dados de alta qualidade, pronta para ser consumida pelas próximas etapas do projeto.

---
**Link do Repositório GitHub:** `https://github.com/seu-usuario/seu-repositorio`

(Substituir pelo link real do repositório)
    