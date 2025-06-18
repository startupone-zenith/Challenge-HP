# Challenge Sprint - HP
## Sprint 2 - Front-End

### Entregável 2: Análise Exploratória e Descritiva dos Dados

---

#### 1. Visão Geral e Escopo do Projeto

Este documento apresenta os resultados da **Análise Exploratória de Dados (EDA)**, realizada sobre o dataset coletado na primeira fase do projeto. O objetivo desta etapa, correspondente ao Entregável 2 de Front-End & Mobile Development, foi investigar os dados, extrair insights, identificar padrões e preparar o terreno para a modelagem de Machine Learning.

O escopo da análise abrange:

-   **Segmento de Produtos**: Cartuchos de tinta e suprimentos HP.
-   **Fonte de Dados**: Anúncios coletados do Mercado Livre.
-   **Metodologia**: Análise interativa e visual implementada diretamente no WebApp com Streamlit, cobrindo limpeza, análise descritiva, análise textual e de correlações.

---

#### 2. Limpeza e Preparação dos Dados

A análise inicia com uma etapa robusta de preparação dos dados, implementada na aba **"🔬 Análise Exploratória (EDA)"** da aplicação.

-   **Detecção Automática de Colunas**: A função `detect_column_mappings` inspeciona o dataset carregado e identifica automaticamente as colunas mais importantes (`título`, `preço`, `vendedor`, `avaliação`, etc.), mesmo que os nomes variem.
-   **Padronização de Tipos**: A função `prepare_dataframe` converte colunas como preço e avaliações para formato numérico, tratando erros de conversão e garantindo que os dados estejam prontos para análise matemática.
-   **Limpeza de Reviews**: Uma aba dedicada, **"🛠️ Limpeza de Reviews"**, foi criada para realizar o tratamento específico de dados de review, incluindo:
    -   Remoção de reviews vazias ou duplicadas.
    -   Normalização de ratings para a escala 1-5.
    -   Padronização de formatos de data.
    -   Limpeza de texto (remoção de caracteres especiais).

---

#### 3. Análise Exploratória de Dados (EDA)

A EDA foi implementada como um sistema de abas interativas no Streamlit, permitindo uma análise profunda e segmentada.

##### Aba 1: 🧹 Limpeza & Descritiva
-   **Resumo do Dataset**: Métricas gerais como total de registros, colunas, valores ausentes e linhas duplicadas.
-   **Análise de Valores Ausentes**: Gráfico de barras mostrando o percentual de dados faltantes por coluna.
-   **Tipos de Dados**: Tabela detalhando o tipo de cada coluna, valores únicos e um exemplo.
-   **Estatísticas Descritivas**: `describe()` do Pandas para todas as colunas numéricas.
-   **Top Valores Categóricos**: Gráficos de barra para as categorias mais frequentes.
-   **Recomendações de Limpeza**: Sugestões automáticas baseadas nos problemas de qualidade encontrados.

##### Aba 2: 💰 Distribuição de Preços
-   **Métricas de Preço**: Mínimo, máximo, média e mediana.
-   **Histograma de Preços**: Visualização da distribuição dos valores dos produtos.
-   **Box Plot por Vendedor**: Comparativo da faixa de preços entre os top 10 vendedores.
-   **Listas de Extremos**: Tabelas com os 5 produtos mais caros e os 5 mais baratos.

##### Aba 3: 📝 Análise Textual (WordCloud & N-grams)
-   **WordCloud por Review de Produto**: O usuário pode selecionar um produto específico no dataset para gerar um WordCloud exclusivo das suas reviews. Isso permite uma análise focada no feedback de um único item.
-   **Análise de Sentimento**: Junto ao WordCloud, um gráfico de pizza mostra a distribuição de sentimentos (Positivo, Negativo, Neutro) com base em palavras-chave presentes nas reviews.
-   **Métricas do Produto**: Ao selecionar um produto, são exibidas informações detalhadas como ID, preço, vendedor e título completo.

##### Aba 4: 📊 Correlações & Segmentação
-   **Matriz de Correlação**: Heatmap mostrando a correlação de Pearson entre todas as variáveis numéricas.
-   **Segmentação Preço vs. Rating**: Análise de como a avaliação média se comporta em diferentes faixas de preço (Baixo, Médio, Alto).
-   **Detecção de Outliers**: Utilização do método IQR para identificar e quantificar outliers em colunas numéricas.
-   **Análise de Vendedores**: Análise de concentração de mercado (HHI) e distribuição de produtos entre os principais vendedores.

##### Aba 5: 🏷️ Distribuição por Rótulos
-   Análise da distribuição da feature target (`rotulo_heuristico`).
-   Gráfico de pizza mostrando a proporção de produtos classificados como "original" vs. "suspeito".
-   Box plots comparando a distribuição de scores e preços entre as duas classes.

---

#### 4. Features para Modelagem e Metodologia CRISP-DM

##### Aba 6: 🔧 Features para Modelagem
-   **Identificação de Features**: Separação e análise de features numéricas, categóricas e textuais.
-   **Engenharia de Features Sugerida**: Apresentação de possíveis features a serem criadas, como `price_zscore`, `vendor_reputation_score` e interações (`preço × rating`).
-   **Algoritmos Recomendados**: Sugestão de algoritmos de Machine Learning adequados para o problema de classificação (Random Forest, XGBoost, etc.).

##### Cronograma Macro (CRISP-DM)
Embora a seção detalhada tenha sido simplificada na interface para clareza, a metodologia **CRISP-DM** guiou todo o projeto:

1.  **Business Understanding**: Identificar produtos HP falsificados (Concluído).
2.  **Data Understanding**: Coleta e EDA (Esta entrega).
3.  **Data Preparation**: Limpeza e feature engineering (Concluído).
4.  **Modeling**: Treinamento de modelos de classificação (Próxima etapa).
5.  **Evaluation**: Validação e medição de performance (Próxima etapa).
6.  **Deployment**: WebApp funcional (Concluído).

---
**Link do Repositório GitHub:** `https://github.com/seu-usuario/seu-repositorio`

(Substituir pelo link real do repositório)
    