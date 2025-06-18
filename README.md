# 🛡️ Sistema de Detecção de Falsificações - Mercado Livre HP

> Sistema avançado para identificação de produtos falsificados da HP no Mercado Livre, desenvolvido para o **Challenge HP**

## 📋 Índice

- [Sobre o Sistema](#-sobre-o-sistema)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Como Executar](#-como-executar)
- [Como Usar](#-como-usar)
- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Solução de Problemas](#-solução-de-problemas)
- [Tecnologias](#-tecnologias)

## 🎯 Sobre o Sistema

Este sistema foi desenvolvido para detectar produtos falsificados da HP no Mercado Livre através de análise automatizada de dados. O sistema combina web scraping, análise de texto, machine learning e visualizações interativas para identificar produtos suspeitos.

### Principais Recursos:
- ✅ **Web Scraping** automatizado do Mercado Livre
- ✅ **Análise de Reviews** com detecção de sentimentos
- ✅ **Detecção de Falsificações** baseada em múltiplos critérios
- ✅ **Interface Web** intuitiva com Streamlit
- ✅ **Visualizações Interativas** com gráficos e dashboards
- ✅ **Exportação de Dados** em múltiplos formatos

## 🔧 Pré-requisitos

### Sistema Operacional
- Windows 10/11
- macOS 10.14+
- Linux (Ubuntu 18.04+)

### Software Necessário
- **Python 3.8+** (recomendado: Python 3.9 ou 3.10)
- **pip** (gerenciador de pacotes Python)
- **Git** (opcional, para clonar o repositório)

### Verificar Instalação do Python
```bash
python --version
# ou
python3 --version
```

Se não tiver Python instalado, baixe em: https://python.org/downloads/

## 📦 Instalação

### 1. Baixar o Projeto

**Opção A: Download direto**
- Baixe o arquivo ZIP do projeto
- Extraia em uma pasta de sua escolha

**Opção B: Git Clone**
```bash
git clone [URL_DO_REPOSITORIO]
cd Challenge-HP
```

### 2. Criar Ambiente Virtual (Recomendado)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar NLTK (Necessário para análise de texto)

```bash
python setup_nltk.py
```

## 🚀 Como Executar

### 1. Ativar Ambiente Virtual (se criado)

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 2. Executar a Aplicação

```bash
streamlit run run_app.py
```

### 3. Acessar a Interface

Após executar o comando, a aplicação abrirá automaticamente no navegador em:
```
http://localhost:8501
```

Se não abrir automaticamente, copie e cole o link no seu navegador.

## 📖 Como Usar

### 1. 🔍 Buscar Produtos

1. **Acesse a aba "🔍 Buscar Produtos"**
2. **Digite o termo de busca** (ex: "cartucho hp", "toner hp")
3. **Configure os filtros:**
   - **Máximo de itens**: 50-500 produtos
   - **Preço mínimo/máximo**: Faixa de preço desejada
   - **Condição**: Novo, Usado, ou Ambos
   - **Ordenação**: Relevância, Preço, Mais vendidos

4. **Clique em "🔍 Buscar Produtos"**
5. **Aguarde a coleta** (pode levar alguns minutos)

### 2. 📊 Análise Básica de Falsificação

1. **Acesse a aba "📊 Análise Básica de Falsificação"**
2. **Configure a análise:**
   - **Máximo de reviews**: 50-200 por produto
   - **Ativar coleta de reviews**: Para análise mais detalhada
3. **Clique em "🔍 Analisar Falsificação"**
4. **Visualize os resultados:**
   - Lista de produtos com score de risco
   - Classificação: BAIXO/MÉDIO/ALTO RISCO
   - Detalhes de cada produto

### 3. 🔬 Análise Avançada

1. **Acesse a aba "🔬 Análise Avançada"**
2. **Clique em "🔬 Executar Análise Avançada"**
3. **Acompanhe as 4 etapas:**
   - **Limpeza**: Padronização dos dados
   - **Enriquecimento**: Extração de atributos
   - **Análise**: Estatísticas e padrões
   - **Relatório**: Insights e visualizações

### 4. 📈 Exploração de Dados

1. **Acesse a aba "📈 Exploração de Dados"**
2. **Explore as seções:**
   - **Distribuições**: Gráficos de pizza e histogramas
   - **Comparações**: Análise por categorias
   - **Correlações**: Matriz de correlações
   - **Outliers**: Produtos fora do padrão
   - **Análise Lexical**: Frequência de palavras

### 5. 📤 Exportar Dados

1. **Na aba de análise desejada**
2. **Clique no botão "📥 Download"**
3. **Escolha o formato:**
   - CSV Básico
   - CSV Avançado
   - Relatório de Falsificação

## 🛠️ Funcionalidades Detalhadas

### 🕷️ Web Scraping
- **Coleta automatizada** de produtos do Mercado Livre
- **Extração de dados** completos (preço, vendedor, descrição)
- **Coleta de reviews** via API oficial
- **Rate limiting** para evitar bloqueios

### 🤖 Detecção de Falsificação

#### Critérios de Análise:
- **Preços suspeitos** (muito abaixo da média)
- **Vendedores não autorizados**
- **Palavras-chave suspeitas** em títulos e reviews
- **Qualidade da descrição** do produto
- **Indicadores de confiabilidade** (garantia, lacrado, nota fiscal)

#### Classificação de Risco:
- 🔴 **ALTO RISCO** (60-100): Muito provável falsificação
- 🟡 **MÉDIO RISCO** (30-59): Suspeito, requer análise
- 🟢 **BAIXO RISCO** (0-29): Provavelmente original

### 📊 Análises Disponíveis

#### Análise Básica:
- Score de risco por produto
- Comparação de preços
- Análise de reviews suspeitas
- Lista de produtos por risco

#### Análise Avançada:
- Limpeza e padronização de dados
- Extração de atributos técnicos
- Classificação automática (Original/Compatível/Suspeito)
- Estatísticas descritivas completas
- Identificação de outliers
- Análise lexical do corpus

#### Visualizações:
- Gráficos de distribuição
- Box plots de preços
- Matriz de correlações
- Nuvem de palavras
- Análise de bigramas

## 🏗️ Arquitetura do Sistema

```
Challenge-HP/
├── app.py                          # Interface principal Streamlit
├── run_app.py                      # Script de execução
├── mercadolivre_spider.py          # Web scraper principal
├── mercadolivre_spider_reviews.py  # Coletor de reviews
├── setup_nltk.py                   # Configuração NLTK
├── requirements.txt                # Dependências Python
├── scrapy_performance_config.py    # Configurações Scrapy
└── README.md                       # Este arquivo
```

### Módulos Principais:

#### 1. `app.py` - Interface Principal
- Interface Streamlit com múltiplas abas
- Sistema de detecção de falsificação
- Funções de análise e visualização
- Gerenciamento de estado da aplicação

#### 2. `mercadolivre_spider.py` - Web Scraper
- Coleta dados de produtos do Mercado Livre
- Suporte a filtros avançados
- Extração de metadados completos
- Sistema de cache para otimização

#### 3. `mercadolivre_spider_reviews.py` - Coletor de Reviews
- API para coleta de reviews
- Análise de sentimentos
- Detecção de palavras-chave suspeitas
- Tratamento de erros e timeouts

## 🔧 Solução de Problemas

### Problemas Comuns:

#### ❌ Erro: "ModuleNotFoundError"
**Solução:**
```bash
pip install -r requirements.txt
python setup_nltk.py
```

#### ❌ Erro: "missing ScriptRunContext"
**Solução:**
- Este é um aviso normal do Streamlit
- Pode ser ignorado, não afeta o funcionamento

#### ❌ Erro: "Não foi possível carregar as reviews"
**Possíveis causas:**
- Limite de rate do Mercado Livre atingido
- Produto sem reviews disponíveis
- Problema de conectividade

**Solução:**
- Aguarde alguns minutos e tente novamente
- Reduza o número de reviews solicitadas
- Verifique sua conexão com a internet

#### ❌ Aplicação não abre no navegador
**Solução:**
```bash
# Tente especificar a porta
streamlit run run_app.py --server.port 8501

# Ou acesse manualmente
# http://localhost:8501
```

#### ❌ Erro de memória com muitos produtos
**Solução:**
- Reduza o número máximo de itens para 100-200
- Feche outras aplicações que consomem memória
- Use análise básica em vez de avançada

### Logs e Debug:

#### Ver logs detalhados:
```bash
streamlit run run_app.py --logger.level debug
```

#### Arquivo de log de erros:
```
scraper_errors.log
```

### Performance:

#### Para melhorar a performance:
- Use menos produtos por busca (50-100)
- Desative coleta de reviews se não necessário
- Use análise básica para buscas rápidas

## 🛡️ Limitações e Considerações

### Limitações Técnicas:
- **Rate Limiting**: Mercado Livre limita requisições
- **Dados Dinâmicos**: Preços mudam constantemente
- **Detecção Heurística**: Baseada em padrões, não 100% precisa
- **Dependência de Conectividade**: Requer internet estável

### Considerações Éticas:
- **Uso Responsável**: Respeite os termos de uso do Mercado Livre
- **Rate Limiting**: Sistema implementa pausas entre requisições
- **Dados Públicos**: Coleta apenas informações públicas
- **Finalidade Educacional**: Desenvolvido para fins acadêmicos

### Recomendações:
- Use o sistema durante horários de menor tráfego
- Faça buscas específicas em vez de muito amplas
- Combine análise automática com revisão manual
- Mantenha backups dos dados coletados

## 💻 Tecnologias Utilizadas

### Backend:
- **Python 3.8+**: Linguagem principal
- **Streamlit**: Framework web para interface
- **Scrapy**: Framework de web scraping
- **Pandas**: Manipulação de dados
- **NumPy**: Computação científica

### Análise de Dados:
- **Scikit-learn**: Machine learning
- **NLTK**: Processamento de linguagem natural
- **TextStat**: Análise de legibilidade
- **WordCloud**: Nuvem de palavras

### Visualização:
- **Plotly**: Gráficos interativos
- **Matplotlib**: Visualizações estáticas
- **Seaborn**: Gráficos estatísticos

### Web Scraping:
- **Requests**: Requisições HTTP
- **BeautifulSoup**: Parser HTML
- **lxml**: Parser XML/HTML
- **Scrapy**: Framework completo

## 📞 Suporte

### Para problemas ou dúvidas:

1. **Verifique a seção [Solução de Problemas](#-solução-de-problemas)**
2. **Consulte os logs de erro** em `scraper_errors.log`
3. **Teste com dados menores** para isolar o problema
4. **Verifique se todas as dependências estão instaladas**

### Informações Úteis para Debug:
- Versão do Python: `python --version`
- Versão do Streamlit: `streamlit version`
- Sistema operacional
- Mensagem de erro completa
- Passos para reproduzir o problema

---

**Desenvolvido para o Challenge HP - Sistema de Detecção de Falsificações**
