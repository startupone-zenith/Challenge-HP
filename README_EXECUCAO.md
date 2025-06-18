# Sistema Avançado de Detecção de Falsificações - Mercado Livre

## 🎯 Objetivos do Sistema

Este sistema foi desenvolvido para atender aos requisitos do **Challenge Sprint da HP**, implementando um sistema completo de análise de produtos do Mercado Livre com foco na detecção de falsificações. O sistema cumpre os seguintes objetivos:

### 1. 🧹 Limpeza e Padronização dos Dados
- ✅ **Correção de símbolos especiais** e quebras de linha
- ✅ **Normalização de formatos** de preços, nomes e descrições  
- ✅ **Tratamento de dados faltantes** e registros duplicados
- ✅ **Padronização de marcas e vendedores**

### 2. 🔧 Enriquecimento com Colunas Derivadas
- ✅ **Classificação automatizada** (Original/Compatível/Suspeito)
- ✅ **Extração de atributos técnicos** com expressões regulares
- ✅ **Indicadores binários de confiabilidade** (lacrado, nota fiscal, garantia)
- ✅ **Métricas de qualidade do anúncio**
- ✅ **Score de risco consolidado**

### 3. 📊 Análise Exploratória
- ✅ **Estatísticas descritivas** sobre preços, vendedores e tipos de produto
- ✅ **Identificação de outliers** e comportamentos fora do padrão
- ✅ **Exploração lexical** de descrições por meio de frequência de termos
- ✅ **Visualizações interativas** com gráficos e dashboards

## 🚀 Como Executar

### Instalação das Dependências
```bash
pip install -r requirements.txt
```

### Execução da Aplicação
```bash
streamlit run run_app.py
```

## 📋 Funcionalidades Principais

### 🔍 Sistema de Detecção de Falsificações

O sistema oferece **duas modalidades de análise**:

#### 📊 Análise Básica
- Análise rápida baseada em preços e reviews
- Comparação com valores de referência HP
- Busca por palavras-chave suspeitas em reviews
- Classificação: BAIXO/MÉDIO/ALTO RISCO

#### 🔬 Análise Avançada
Sistema completo com 4 etapas de processamento:

1. **🧹 Limpeza e Padronização**
   - Remove símbolos especiais e espaços excedentes
   - Normaliza formatos de preços (R$ X,XX)
   - Padroniza nomes de marcas (HP, CANON, EPSON, etc.)
   - Limpa nomes de vendedores

2. **🔧 Enriquecimento de Dados**
   - **Classificação Automática**: Identifica se produto é Original, Compatível ou Suspeito
   - **Atributos Técnicos**: Extrai modelo, cor, tipo de tinta, capacidade
   - **Indicadores de Confiabilidade**: Verifica presença de garantia, lacrado, nota fiscal
   - **Métricas de Qualidade**: Analisa qualidade da escrita e densidade de informação

3. **📈 Análise Exploratória**
   - Estatísticas descritivas completas
   - Identificação de outliers (métodos IQR e Z-Score)
   - Análise lexical do corpus de títulos
   - Identificação de padrões anômalos

4. **📊 Geração de Relatório**
   - Resumo executivo com insights principais
   - Visualizações interativas
   - Relatórios exportáveis

### 📈 Exploração e Visualização de Dados

#### 📊 Distribuições
- Gráfico de pizza: Distribuição por classificação
- Gráfico de barras: Níveis de risco
- Histograma: Distribuição de preços
- Box plot: Análise de dispersão de preços

#### ⚖️ Comparações
- Violin plot: Preços por classificação
- Estatísticas por grupo
- Comparação vendedores oficiais vs não oficiais
- Score de risco por tipo de vendedor

#### 🔗 Correlações
- Matriz de correlações (heatmap)
- Identificação de correlações fortes (>0.5)
- Análise de dependências entre variáveis

#### ⚠️ Outliers
- Identificação por método IQR e Z-Score
- Exemplos detalhados de produtos outliers
- Análise de títulos muito curtos/longos

#### 📝 Análise Lexical
- Estatísticas do corpus (total palavras, diversidade)
- Top palavras mais frequentes
- Nuvem de palavras
- Análise de bigramas (pares de palavras)

## 🏗️ Arquitetura do Sistema

### Módulos Principais

1. **`mercadolivre_spider.py`**
   - Spider para coleta de dados do Mercado Livre
   - Suporte a filtros (preço, condição, ordenação)
   - Extração de detalhes de produtos
   - Coleta de reviews via API

2. **`mercadolivre_spider_reviews.py`**
   - API especializada para coleta de reviews
   - Análise de sentimentos em comentários
   - Detecção de palavras-chave suspeitas

3. **`app.py`**
   - Interface Streamlit
   - Sistema avançado de detecção de falsificação
   - Funções de limpeza e enriquecimento de dados
   - Análise exploratória e visualizações

4. **`run_app.py`**
   - Script de execução da aplicação

### 🔧 Funcionalidades Técnicas Avançadas

#### Limpeza de Dados
```python
def limpar_e_padronizar_dados(produtos):
    """
    - Remove símbolos especiais e quebras de linha
    - Normaliza unicode (NFKD)
    - Padroniza formatos de preço
    - Limpa nomes de vendedores e marcas
    """
```

#### Classificação Automática
```python
def classificar_produto_automaticamente(titulo):
    """
    Analisa palavras-chave para classificar:
    - ORIGINAL: "original", "genuíno", "lacrado"
    - COMPATÍVEL: "compatível", "genérico", "similar"  
    - SUSPEITO: "réplica", "cópia", "paralelo"
    """
```

#### Extração de Atributos Técnicos
```python
def extrair_atributos_tecnicos(titulo):
    """
    Usa regex para extrair:
    - Modelo do cartucho (ex: 664, 122, 61)
    - Cor da tinta (preto, colorido, ciano)
    - Tipo (pigmentada, corante)
    - Capacidade em ML
    - Rendimento em páginas
    """
```

#### Score de Risco Consolidado
```python
def calcular_score_risco_consolidado(produto):
    """
    Combina múltiplos fatores:
    - Classificação automática (peso 30%)
    - Vendedor oficial/não oficial (peso 25%)
    - Qualidade do anúncio (peso 20%)
    - Fatores positivos reduzem score
    """
```

## 📊 Critérios de Detecção de Falsificação

### 🔴 Indicadores de Alto Risco (Score 60-100)
- Produtos classificados como "SUSPEITO"
- Vendedores não oficiais
- Preços 50%+ abaixo da referência
- Reviews com 20%+ de menções suspeitas
- Qualidade de escrita muito baixa

### 🟡 Indicadores de Médio Risco (Score 30-59)
- Produtos "COMPATÍVEIS" sem indicação clara
- Preços 30-49% abaixo da referência
- 10-19% de reviews suspeitas
- Títulos com termos promocionais excessivos

### 🟢 Indicadores de Baixo Risco (Score 0-29)
- Produtos "ORIGINAIS" de vendedores oficiais
- Preços dentro da faixa normal
- Presença de garantia/lacrado/nota fiscal
- Reviews positivas sem indicadores suspeitos

## 📈 Análises Implementadas

### 1. Estatísticas Descritivas
- **Preços**: média, mediana, desvio padrão, quartis
- **Vendedores**: concentração de mercado, top vendedores
- **Classificações**: distribuição por categoria
- **Riscos**: percentual por nível de risco

### 2. Identificação de Outliers
- **Método IQR**: Q1 - 1.5*IQR < valor < Q3 + 1.5*IQR
- **Método Z-Score**: |z| > 3 (3 desvios padrão)
- **Análise de títulos**: muito curtos (<20 chars) ou longos (>150 chars)

### 3. Análise Lexical
- **Frequência de termos**: palavras mais comuns
- **Bigramas**: pares de palavras frequentes
- **Diversidade lexical**: type-token ratio
- **Densidade de informação**: proporção de termos técnicos

### 4. Padrões Anômalos
- Produtos "originais" com preços muito baixos
- Vendedores não oficiais com muitos "originais"
- Títulos longos com pouca informação técnica

## 🎯 Casos de Uso

### Para Analistas de E-commerce
- Identificação rápida de produtos suspeitos
- Monitoramento de vendedores não autorizados
- Análise de competitividade de preços

### Para Equipes de Compliance
- Detecção automatizada de falsificações
- Relatórios detalhados para ações legais
- Monitoramento contínuo do marketplace

### Para Pesquisadores
- Dataset enriquecido para machine learning
- Análises estatísticas aprofundadas
- Visualizações para apresentações

## 📤 Exportação de Dados

O sistema permite exportar:
- **CSV Básico**: Dados originais + análise básica
- **CSV Avançado**: Dados enriquecidos + todas as métricas
- **Relatório de Falsificação**: Foco em produtos suspeitos
- **Dataset HP Challenge**: Formato específico para ML

## 🔍 Exemplo de Workflow

1. **Busca de Produtos**: Digite "cartucho hp" na interface
2. **Configuração**: Escolha filtros (preço, condição, máximo de itens)
3. **Coleta**: Sistema coleta dados via web scraping
4. **Análise Básica**: Análise rápida de preços e reviews
5. **Análise Avançada**: Limpeza, enriquecimento e classificação
6. **Exploração**: Visualizações interativas e insights
7. **Exportação**: Download dos resultados em CSV

## 📚 Tecnologias Utilizadas

- **Frontend**: Streamlit
- **Web Scraping**: Scrapy
- **Análise de Dados**: Pandas, NumPy
- **Visualizações**: Plotly, Matplotlib, Seaborn
- **Processamento de Texto**: Regex, TextStat
- **APIs**: Requests para coleta de reviews

## 🚨 Limitações e Considerações

- **Rate Limiting**: Pausas entre requisições para evitar bloqueios
- **Dados Dinâmicos**: Preços e disponibilidade mudam constantemente
- **Detecção Heurística**: Baseada em padrões, não 100% precisa
- **Dependência de Dados**: Qualidade depende da informação disponível

## 🔄 Atualizações Futuras

- [ ] Machine Learning para classificação automática
- [ ] Integração com APIs oficiais de marcas
- [ ] Monitoramento em tempo real
- [ ] Análise de imagens de produtos
- [ ] Sistema de alertas automatizado

---

**Desenvolvido para o Challenge Sprint da HP - Sistema de Detecção de Falsificações** 