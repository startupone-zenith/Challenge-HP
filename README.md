# 🛡️ Sistema Simplificado de Scraping - Mercado Livre HP

> Sistema focado em **scraping** e **geração de datasets** de produtos HP no Mercado Livre

## 📋 Sobre o Sistema

Este sistema foi simplificado para manter apenas as funcionalidades essenciais:
- ✅ **Web Scraping** automatizado do Mercado Livre
- ✅ **Coleta de Reviews** dos produtos
- ✅ **Geração de Datasets** em CSV e JSON
- ✅ **Interface de linha de comando** simples

## 🔧 Pré-requisitos

- Python 3.7 ou superior
- pip (gerenciador de pacotes Python)

## 📦 Instalação

1. **Clone o repositório:**
```bash
git clone <url-do-repositorio>
cd Challenge-HP
```

2. **Crie um ambiente virtual (recomendado):**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # Linux/Mac
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

## 🚀 Como Usar

### Uso Básico - Scraping de Produtos

```bash
# Buscar produtos HP (básico)
python app.py --query "cartucho hp"

# Buscar com limite de itens
python app.py --query "toner hp" --max-items 50

# Buscar e coletar reviews
python app.py --query "cartucho hp 664" --reviews --max-reviews 200
```

### Parâmetros Disponíveis

```bash
python app.py [OPÇÕES]

Opções obrigatórias:
  --query, -q          Termo de busca (obrigatório)

Opções de filtragem:
  --max-items, -m      Máximo de itens para coletar
  --sort              Ordenação: relevance, price_asc, price_desc
  --condition         Condição: all, new, used
  --no-images         Não extrair URLs de imagens

Opções de reviews:
  --reviews           Coletar reviews dos produtos
  --max-reviews       Máximo de reviews por produto (padrão: 100)

Opções de saída:
  --output-csv        Nome do arquivo CSV de saída
  --output-json       Nome do arquivo JSON de saída
```

### Exemplos Práticos

```bash
# Exemplo 1: Busca simples com 30 produtos
python app.py --query "cartucho hp 664" --max-items 30

# Exemplo 2: Busca com reviews e ordenação por preço
python app.py --query "toner hp laserjet" --reviews --sort price_asc --max-items 20

# Exemplo 3: Busca apenas produtos novos com arquivo de saída específico
python app.py --query "impressora hp" --condition new --output-csv "impressoras_hp.csv"

# Exemplo 4: Busca completa com reviews e saída em JSON
python app.py --query "cartucho hp original" --reviews --max-reviews 50 --output-json "dataset_cartuchos.json"
```

## 📁 Estrutura dos Arquivos

```
Challenge-HP/
├── app.py                              # Sistema principal simplificado
├── mercadolivre_spider.py             # Spider para produtos
├── mercadolivre_spider_reviews.py     # Spider para reviews
├── requirements.txt                   # Dependências mínimas
├── README.md                          # Documentação
└── scraper.log                        # Log de execução
```

## 📊 Formato dos Datasets

### CSV (Padrão)
Os datasets CSV incluem as seguintes colunas:
- `id` - ID único do produto
- `titulo` - Título do produto
- `preco` - Preço atual
- `preco_original` - Preço original (se houver desconto)
- `desconto` - Percentual de desconto
- `vendedor` - Nome do vendedor
- `reputacao_vendedor` - Reputação do vendedor
- `condicao` - Condição do produto (novo/usado)
- `frete_gratis` - Se tem frete grátis
- `link` - URL do produto
- `imagem_url` - URL da imagem principal
- `localizacao` - Localização do vendedor
- `vendas` - Número de vendas
- `data_coleta` - Data/hora da coleta

**Se reviews foram coletadas, inclui também:**
- `total_reviews` - Total de reviews
- `rating_medio` - Rating médio
- `rating_5_estrelas` - Quantidade de reviews 5 estrelas
- `rating_4_estrelas` - Quantidade de reviews 4 estrelas
- `rating_3_estrelas` - Quantidade de reviews 3 estrelas
- `rating_2_estrelas` - Quantidade de reviews 2 estrelas
- `rating_1_estrela` - Quantidade de reviews 1 estrela
- `tem_reviews` - Se o produto tem reviews

### JSON
Os datasets JSON incluem:
- `metadata` - Informações sobre o dataset
- `produtos` - Array com todos os produtos e suas reviews completas

## 🔍 Logs e Monitoramento

O sistema gera logs em:
- **Console**: Informações em tempo real
- **Arquivo**: `scraper.log` com histórico completo

## ⚠️ Considerações Importantes

1. **Rate Limiting**: O sistema inclui delays automáticos entre requisições
2. **Respeito aos Termos**: Use com responsabilidade e respeite os termos do Mercado Livre
3. **Dados Dinâmicos**: Os preços e disponibilidade podem mudar rapidamente
4. **Recursos**: Para grandes volumes, monitore uso de CPU e memória

## 🛠️ Desenvolvimento

### Estrutura do Código

- **`HPScrapingSystem`**: Classe principal que coordena o scraping
- **`mercadolivre_spider.py`**: Spider Scrapy para produtos
- **`mercadolivre_spider_reviews.py`**: Spider otimizado para reviews

### Extensões Possíveis

Para adicionar novas funcionalidades, você pode:
1. Estender a classe `HPScrapingSystem`
2. Criar novos métodos de exportação
3. Adicionar filtros personalizados

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique os logs em `scraper.log`
2. Teste com queries mais simples
3. Verifique sua conexão com a internet

---

**Versão Simplificada** - Focada em scraping e geração de datasets