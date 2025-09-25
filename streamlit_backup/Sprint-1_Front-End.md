# Challenge Sprint - HP
## Sprint 1 - Front-End

### Entregável 1: Coleta e Construção da Base de Dados

---

#### 1. Visão Geral do Processo

Para atender aos requisitos do Entregável 1, foi desenvolvida uma solução robusta de Web Scraping utilizando a framework **Scrapy** em Python. A escolha pelo Scrapy, em vez de bibliotecas mais simples como BeautifulSoup ou Selenium, foi estratégica, visando **alta performance, escalabilidade e manutenibilidade** do código.

O sistema foi projetado para extrair dados da plataforma **Mercado Livre**, o maior marketplace do Brasil, focando em anúncios de cartuchos de tinta e outros suprimentos da marca HP.

---

#### 2. Processo de Web Scraping e Coleta de Dados

A coleta foi dividida em dois spiders principais para modularizar e otimizar o processo:

1.  **`MercadoLivreSpider`**: Responsável pela busca de produtos e extração de dados da página de resultados.
2.  **`MercadoLivreProductDetailsSpider`**: Responsável por visitar a página individual de cada produto para coletar informações detalhadas.

O fluxo de execução é orquestrado de forma a garantir a coleta dos seguintes campos essenciais:

-   **Título do Anúncio**: Nome completo do produto.
-   **Preço**: Valor principal do anúncio.
-   **Preço Anterior**: Valor antigo, quando há promoção.
-   **Descrição**: Descrição textual completa fornecida pelo vendedor.
-   **Nome do Vendedor**: Identificação da loja ou vendedor.
-   **Avaliações (Média e Total)**: Média de estrelas e quantidade total de avaliações.
-   **Link do Anúncio**: URL única para cada produto.
-   **Características Principais e Outras**: Tabelas de especificações técnicas (Marca, Modelo, Cor, etc.).
-   **ID do Produto**: Identificador único do Mercado Livre (ex: `MLB22658653`).
-   **URL da Imagem**: Link direto da imagem principal do produto.
-   **Informações de Entrega**: Detalhes sobre o frete e se é "FULL".

---

#### 3. Critérios Heurísticos para Rotulagem

Para criar um dataset pronto para modelagem, foi implementado um sistema de rotulagem heurística diretamente no código (`app.py`), que classifica cada produto como **"original"** ou **"suspeito/pirata"**. A lógica se baseia em um sistema de pontuação que analisa múltiplos fatores:

-   **Análise do Vendedor (Peso Alto)**:
    -   **Pontuação Negativa (-30)**: Se o vendedor está na lista `VENDEDORES_OFICIAIS_HP`, a suspeita diminui drasticamente.
    -   **Pontuação Positiva (+20)**: Se o vendedor não é reconhecido como oficial, a suspeita aumenta.

-   **Análise do Título (Peso Médio)**:
    -   **Palavras Suspeitas (+15 pontos/palavra)**: Termos como `compativel`, `generico`, `alternativo`, `similar` aumentam o score de suspeita.
    -   **Erros de Gramática (+10 pontos/erro)**: Grafias incorretas como `cartuxo`, `inpressora` são penalizadas.
    -   **Ênfase Excessiva (+5 pontos)**: Frases como `100% ORIGINAL` podem, paradoxalmente, indicar uma tentativa de mascarar um produto falso.

-   **Análise de Preço (Peso Alto)**:
    -   O preço do anúncio é comparado com uma tabela de referência (`PRECOS_REFERENCIA_HP`) para o modelo específico do cartucho.
    -   Descontos agressivos aumentam o score de suspeita:
        -   **+90 pontos**: Se o preço for >= 60% abaixo da referência.
        -   **+70 pontos**: Se o preço for >= 40% abaixo da referência.
        -   **+50 pontos**: Se o preço for >= 25% abaixo da referência.

-   **Classificação Final**:
    -   **`suspeito`**: Se o `score_total` for >= 50.
    -   **`original`**: Se o `score_total` for < 50.

Este sistema gera a feature target (`rotulo_heuristico`) e uma série de features auxiliares (`score_total`, `score_titulo`, `score_preco`) que serão úteis para a modelagem.

---

#### 4. Dataset Estruturado

O resultado final é um dataset estruturado em formato CSV, contendo todas as features coletadas e as colunas geradas pela rotulagem heurística.

**Features Coletadas e Geradas:**

| Nome da Feature        | Descrição                                         | Origem      |
| ---------------------- | ------------------------------------------------- | ----------- |
| `Título`               | Título completo do anúncio.                       | Scraping    |
| `Preço`                | Valor do produto.                                 | Scraping    |
| `Vendedor`             | Nome da loja ou vendedor.                         | Scraping    |
| `Link`                 | URL do anúncio.                                   | Scraping    |
| `ID Produto`           | Identificador único do Mercado Livre.             | Scraping    |
| `Descrição`            | Descrição detalhada do produto.                   | Scraping    |
| `Média Avaliações`     | Nota média das avaliações (1-5).                  | Scraping    |
| `Total Avaliações`     | Número total de avaliações recebidas.             | Scraping    |
| `rotulo_heuristico`    | **Feature Target**: "original" ou "suspeito".     | Heurística  |
| `score_total`          | Pontuação final de suspeita.                      | Heurística  |
| `vendedor_oficial`     | Flag booleana se o vendedor é oficial.            | Heurística  |
| `score_titulo`         | Pontuação de suspeita baseada no título.          | Heurística  |
| `score_preco`          | Pontuação de suspeita baseada no preço.           | Heurística  |

---

### Amostra de Dados Coletados e Rotulados

| Título do Anúncio                                                          | Preço     | Vendedor   | Rótulo Heurístico   | Link do Anúncio                                                                                                                                                                                            |
|:---------------------------------------------------------------------------|:----------|:-----------|:--------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Cartucho Hp 667 Colorido 3ym78ab                                           | R$ 66,49  | Eshop      | nan                 | https://www.mercadolivre.com.br/cartucho-hp-667-colorido-3ym78ab/p/MLB22658653#polycard_client=search-nordic&searchVariation=MLB22658653&wid=MLB4030705941&position=3&search_layout=grid&type=product&tracking_id=55a851a6-af80-4409-841f-c2b3b5ecdad3&sid=search |
| Cartucho De Tinta Hp 904xl T6m16ab Preto 24130                             | R$ 295    | nan        | nan                 | https://www.mercadolivre.com.br/cartucho-de-tinta-hp-904xl-t6m16ab-preto-24130/up/MLBU3204774123#polycard_client=search-nordic&searchVariation=MLBU3204774123&wid=MLB4078793315&position=5&search_layout=grid&type=product&tracking_id=55a851a6-af80-4409-841f-c2b3b5ecdad3&sid=search                |
| Hp Ink Cartridges 2x 662xl Preto / Black Cz105ab                           | R$ 187,20 | Park Ecom  | nan                 | https://www.mercadolivre.com.br/hp-ink-cartridges-2x-662xl-preto-black-cz105ab/p/MLB48643172#polycard_client=search-nordic&searchVariation=MLB48643172&wid=MLB5356295280&position=6&search_layout=grid&type=product&tracking_id=55a851a6-af80-4409-841f-c2b3b5ecdad3&sid=search                       |
| Cartucho HP 667 Preto 2376 2776 6476                                       | R$ 66,90  | nan        | nan                 | https://www.mercadolivre.com.br/cartucho-hp-667-preto-2376-2776-6476/p/MLB22022306#polycard_client=search-nordic&searchVariation=MLB22022306&wid=MLB3966990865&position=7&search_layout=grid&type=product&tracking_id=55a851a6-af80-4409-841f-c2b3b5ecdad3&sid=search                                 |
| Cartucho HP 664 preto(F6V29AB) Para Deskjet 4535, 4675, 1115, 2135, 3775   | R$ 64,61  | Eshop      | nan                 | https://www.mercadolivre.com.br/cartucho-hp-664-pretof6v29ab-para-deskjet-4535-4675-1115-2135-3775/p/MLB22534728#polycard_client=search-nordic&searchVariation=MLB22534728&wid=MLB3927113057&position=8&search_layout=grid&type=product&tracking_id=55a851a6-af80-4409-841f-c2b3b5ecdad3&sid=search |

---
