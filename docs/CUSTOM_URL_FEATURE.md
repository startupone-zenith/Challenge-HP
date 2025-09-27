# 🔗 Funcionalidade URL Customizada

Esta nova funcionalidade permite usar URLs específicas do Mercado Livre como base para scraping, mantendo todos os filtros e configurações da URL original.

## 📋 Visão Geral

A funcionalidade de URL customizada foi implementada para permitir:
- Usar URLs específicas do Mercado Livre com filtros complexos já aplicados
- Manter a estrutura de navegação e filtros do site original
- Aproveitar URLs de categorias específicas ou buscas refinadas
- Contornar limitações dos filtros via parâmetros

## 🚀 Como Usar

### Via Código Python

```python
from app import HPScrapingSystem

sistema = HPScrapingSystem()

# URL específica com filtros aplicados
url_customizada = "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"

produtos = sistema.executar_scraping_produtos(
    query="Cartucho HP Original",  # Query para logs
    max_items=10,
    extract_images=True,
    custom_url=url_customizada  # Nova funcionalidade!
)
```

### Via API REST

#### Scraping Simples

```bash
curl -X POST http://localhost:5000/api/scraping/simple \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Cartucho HP Original",
    "max_items": 5,
    "custom_url": "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"
  }'
```

#### Job Completo

```bash
curl -X POST http://localhost:5000/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Cartucho HP Original",
    "max_items": 20,
    "collect_reviews": true,
    "extract_images": true,
    "custom_url": "https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True"
  }'
```

### Via Interface Web

1. Acesse `http://localhost:5000/scraping`
2. No campo "Query", insira o termo de busca
3. No campo "URL Customizada" (se disponível), cole a URL específica
4. Configure os demais parâmetros
5. Inicie o scraping

## 🔍 Exemplo de URL

A URL fornecida como exemplo:
```
https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/cartucho-hp_TempoFrete_DiaSeguinte_Frete_Full_NoIndex_True#applied_filter_id%3DINK_CARTRIDGE_TYPE%26applied_filter_name%3DTipo+de+cartucho%26applied_filter_order%3D3%26applied_value_id%3D281072%26applied_value_name%3DOriginal%26applied_value_order%3D1%26applied_value_results%3D131%26is_custom%3Dfalse
```

Esta URL contém:
- **Categoria específica**: `informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/`
- **Filtros de frete**: `TempoFrete_DiaSeguinte_Frete_Full`
- **Filtros aplicados**: Tipo de cartucho = Original
- **Fragmento com parâmetros**: Filtros específicos codificados na URL

## ⚙️ Funcionamento Técnico

1. **Detecção**: O sistema verifica se `custom_url` foi fornecida
2. **Prioridade**: Se fornecida, a URL customizada substitui a construção automática
3. **Preservação**: Todos os filtros e parâmetros da URL são mantidos
4. **Compatibilidade**: O sistema ainda aceita outros parâmetros (max_items, extract_images, etc.)

## 📊 Vantagens

### ✅ Benefícios
- **Filtros Complexos**: Usa filtros que não estão disponíveis via parâmetros
- **Precisão**: Mantém exatamente os mesmos filtros da navegação manual
- **Flexibilidade**: Permite usar qualquer URL válida do Mercado Livre
- **Performance**: Evita múltiplas requisições para aplicar filtros

### 🔄 Compatibilidade
- **Retrocompatível**: Funciona com o método tradicional quando `custom_url` não é fornecida
- **Parâmetros**: Outros parâmetros (max_items, extract_images) continuam funcionando
- **API**: Totalmente integrada com a API REST e interface web

## 🧪 Testes

Execute os testes para verificar o funcionamento:

```bash
# Teste básico
python test_url_customizada.py

# Exemplo completo
python exemplo_url_customizada.py
```

## 📝 Parâmetros da API

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `query` | string | Sim* | Termo de busca (usado para logs) |
| `custom_url` | string | Não | URL específica do Mercado Livre |
| `max_items` | integer | Não | Máximo de itens (padrão: 50) |
| `extract_images` | boolean | Não | Extrair URLs de imagens |
| `collect_reviews` | boolean | Não | Coletar reviews dos produtos |
| `sort_by` | string | Não | Ignorado se custom_url fornecida |
| `condition` | string | Não | Ignorado se custom_url fornecida |

*Nota: `query` ou `custom_url` deve ser fornecida

## 🔧 Implementação

A funcionalidade foi implementada nos seguintes arquivos:
- `mercadolivre_spider.py`: Spider principal com suporte a URL customizada
- `app.py`: Sistema principal com novo parâmetro
- `flask_app.py`: API Flask com suporte ao parâmetro
- Arquivos de exemplo e teste

## 🚨 Limitações

- A URL deve ser válida e acessível
- Filtros específicos da URL são mantidos (sort_by e condition são ignorados)
- A query ainda é necessária para compatibilidade e logs
- URLs muito longas podem ter limitações de URL encoding

## 📚 Exemplos de URLs Úteis

### Cartuchos HP Originais
```
https://lista.mercadolivre.com.br/informatica/impressao/suprimentos-impressao/cartuchos-tinta/original/hp/
```

### Com Frete Grátis
```
https://lista.mercadolivre.com.br/cartucho-hp_Frete_Full
```

### Produtos Novos com Melhor Preço
```
https://lista.mercadolivre.com.br/cartucho-hp_OrderId_PRICE_ITEM*CONDITION_2230284
```

---

**Desenvolvido para o Sistema de Scraping HP** 🛡️
