# 🔧 Sistema de Scraping HP - MercadoLivre

Sistema completo de coleta de dados do MercadoLivre para produtos HP com **extração detalhada de 16 campos**.

## 📁 Estrutura do Projeto (Nova Versão 2.0)

```
Challenge-HP/
├── 📂 src/                          # Código fonte
│   ├── 📂 core/                     # Funcionalidades principais
│   │   ├── app.py                   # Sistema principal HPScrapingSystem
│   │   └── shared_scraping_config.py # Configurações compartilhadas
│   ├── 📂 spiders/                  # Spiders do Scrapy
│   │   ├── mercadolivre_spider.py   # Spider principal com extração detalhada
│   │   └── mercadolivre_spider_reviews.py # Spider de reviews
│   ├── 📂 web/                      # Interface Flask
│   │   ├── flask_app.py             # Aplicação Flask
│   │   ├── run_flask.py             # Executor Flask
│   │   ├── 📂 templates/            # Templates HTML
│   │   └── 📂 static/               # CSS/JS
│   └── 📂 utils/                    # Utilitários
├── 📂 tests/                        # Testes organizados
│   ├── 📂 unit/                     # Testes unitários
│   ├── 📂 integration/              # Testes de integração
│   └── 📂 examples/                 # Exemplos de teste
├── 📂 docs/                         # Documentação
├── 📂 data/                         # Dados
│   ├── 📂 datasets/                 # Datasets gerados
│   ├── 📂 samples/                  # Amostras de páginas
│   └── 📂 cache/                    # Cache temporário
├── 📂 examples/                     # Exemplos de uso
├── 📂 logs/                         # Arquivos de log
├── 📂 config/                       # Configurações
├── 📂 scripts/                      # Scripts auxiliares
├── main.py                          # 🚀 PONTO DE ENTRADA PRINCIPAL
├── requirements.txt                 # Dependências
└── README.md                        # Este arquivo
```

## 🚀 Como Usar

### 1. **Interface Web (Recomendado)**
```bash
# Executar aplicação Flask
python main.py

# Ou diretamente:
python src/web/flask_app.py
```
**Acesse:** `http://localhost:5000`

### 2. **Linha de Comando**
```bash
# Scraping básico
python main.py "cartucho hp 664" --max-items 50

# Scraping detalhado (16 campos)
python main.py "cartucho hp 664" --max-items 50 --detailed

# Com reviews e JSON
python main.py "cartucho hp 664" --max-items 50 --detailed --reviews --json
```

## ✨ Funcionalidades

### 🔍 **Extração Detalhada (16 Campos)**
- ✅ Nome do produto
- ✅ Condição do produto
- ✅ Preço e desconto
- ✅ Informações de frete
- ✅ Dados do vendedor
- ✅ Garantias e políticas
- ✅ Descrição completa
- ✅ Características técnicas
- ✅ Fotos do produto
- ✅ Avaliações detalhadas

### 🌐 **Interface Web**
- ✅ Formulário intuitivo
- ✅ Monitoramento de jobs
- ✅ Preview dos datasets
- ✅ Download CSV/JSON
- ✅ Dashboard de resultados

### 🤖 **Anti-Bot & Robustez**
- ✅ User-agents rotativos
- ✅ Headers realistas
- ✅ Delays adaptativos
- ✅ Contorno de verificações
- ✅ Múltiplas estratégias

## 🔧 Configuração

### Instalar Dependências
```bash
pip install -r requirements.txt
```

### Estrutura de Imports
```python
# Sistema principal
from src.core import HPScrapingSystem

# Spiders
from src.spiders import MercadoLivreSpider, run_spider

# Interface web
from src.web import app
```

## 📊 Exemplo de Uso Programático

```python
from src.core import HPScrapingSystem

# Criar instância
sistema = HPScrapingSystem()

# Scraping com extração detalhada
produtos = sistema.executar_scraping_produtos(
    query="cartucho hp 664",
    max_items=50,
    detailed_extraction=True  # ✨ NOVA FUNCIONALIDADE!
)

# Gerar datasets
csv_file = sistema.gerar_dataset_csv()
json_file = sistema.gerar_dataset_json()

print(f"Coletados {len(produtos)} produtos")
print(f"CSV: {csv_file}")
print(f"JSON: {json_file}")
```

## 🧪 Testes

```bash
# Testes unitários
python -m pytest tests/unit/

# Testes de integração
python -m pytest tests/integration/

# Teste rápido
python tests/integration/teste_integracao_final.py
```

## 📋 Logs e Monitoramento

- **Logs:** `logs/` - Arquivos de log organizados
- **Flask:** Interface web com monitoramento em tempo real
- **Jobs:** Processamento em background com status

## 🎯 Diferencial da Nova Versão

### **Antes (v1.0)**
- Estrutura desorganizada
- 8 campos básicos
- Apenas HTML parsing

### **Agora (v2.0)** ✨
- **Estrutura profissional** organizada em módulos
- **16+ campos detalhados**
- **Dados estruturados JSON-LD**
- **Interface web melhorada**
- **Testes organizados**
- **Documentação completa**

## 🌟 Campos Detalhados Extraídos

| Campo | Descrição | Origem |
|-------|-----------|--------|
| `nome_produto` | Nome completo | JSON-LD |
| `condicao_produto` | Novo/Usado | Schema.org |
| `preco` | Preço atual | Event data |
| `desconto` | % desconto | Cálculo |
| `frete_gratis` | Frete gratuito | JSON-LD |
| `tempo_entrega` | Prazo estimado | Shipping details |
| `nome_loja` | Nome do vendedor | Event data |
| `vendas_produto` | Vendas específicas | HTML |
| `devolucao_gratis` | Política devolução | Schema.org |
| `compra_garantida` | Garantia ML | Padrão |
| `tempo_garantia` | Prazo garantia | Return policy |
| `descricao_produto` | Descrição completa | JSON-LD |
| `caracteristicas_principais` | Specs técnicas | HTML table |
| `fotos_produto` | URLs imagens | JSON-LD + HTML |
| `avaliacao` | Ratings/reviews | Aggregate data |
| `outros` | Dados extras | Mixed sources |

## 🎉 Resultado

Sistema **100% funcional** com:
- ⚡ **Extração básica** (rápida)
- 🔍 **Extração detalhada** (completa)
- 🌐 **Interface web** profissional
- 📊 **Dados ricos** em CSV/JSON
- 🧪 **Totalmente testado**

---

**Versão 2.0** - Sistema reorganizado e otimizado! 🚀
