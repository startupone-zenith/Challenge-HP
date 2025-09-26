# 🛡️ Sistema de Scraping HP - Flask Web Application

> Sistema web completo para scraping e geração de datasets de produtos HP no Mercado Livre

## 🌟 Novidades da Versão Flask

- ✅ **Interface Web Moderna** com Bootstrap 5
- ✅ **API REST Completa** para integração
- ✅ **Jobs em Background** com monitoramento em tempo real
- ✅ **Dashboard Interativo** com estatísticas
- ✅ **Download de Datasets** direto pela web
- ✅ **Responsive Design** para mobile e desktop

## 📋 Funcionalidades

### 🌐 Interface Web
- **Página Inicial**: Dashboard com estatísticas do sistema
- **Scraping**: Configuração avançada de parâmetros
- **Jobs**: Monitoramento de jobs em tempo real
- **Datasets**: Visualização e download de arquivos gerados

### 🔌 API REST
- **POST** `/api/scraping/start` - Iniciar scraping
- **GET** `/api/jobs/{id}/status` - Status do job
- **GET** `/api/jobs` - Listar todos os jobs
- **GET** `/api/datasets` - Listar datasets
- **GET** `/api/datasets/{file}/download` - Download de arquivo

## 🚀 Como Executar

### 1. Instalação
```bash
# Instalar dependências
pip install -r requirements.txt
```

### 2. Executar Servidor
```bash
# Opção 1: Script dedicado
python run_flask.py

# Opção 2: Aplicação direta
python flask_app.py
```

### 3. Acessar Sistema
- **Interface Web**: http://localhost:5000
- **API REST**: http://localhost:5000/api/
- **Documentação**: Veja `API_DOCUMENTATION.md`

## 📱 Interface Web

### Página Inicial
![Dashboard com estatísticas em tempo real]

### Configurar Scraping
![Formulário avançado com todos os parâmetros]

### Monitorar Jobs
![Lista de jobs com progresso em tempo real]

### Gerenciar Datasets
![Visualização e download de arquivos]

## 🔌 Exemplos de Uso da API

### Iniciar Scraping
```bash
curl -X POST http://localhost:5000/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cartucho hp 664",
    "max_items": 50,
    "collect_reviews": true
  }'
```

### Verificar Status
```bash
curl http://localhost:5000/api/jobs/a1b2c3d4/status
```

### Listar Datasets
```bash
curl http://localhost:5000/api/datasets
```

## 📊 Estrutura do Projeto

```
Challenge-HP/
├── flask_app.py              # Aplicação Flask principal
├── run_flask.py              # Script de inicialização
├── app.py                    # Sistema de scraping (backend)
├── mercadolivre_spider.py    # Spider para produtos
├── mercadolivre_spider_reviews.py # Spider para reviews
├── requirements.txt          # Dependências
├── API_DOCUMENTATION.md      # Documentação da API
├── templates/                # Templates HTML
│   ├── base.html            # Template base
│   ├── index.html           # Página inicial
│   ├── scraping.html        # Configurar scraping
│   ├── jobs.html            # Monitorar jobs
│   └── datasets.html        # Gerenciar datasets
├── static/                   # Arquivos estáticos
│   └── style.css            # CSS personalizado
└── datasets_gerados/        # Datasets gerados (criado automaticamente)
```

## ⚙️ Configurações Avançadas

### Parâmetros de Scraping
- **Query**: Termo de busca no Mercado Livre
- **Max Items**: Limite de produtos (10-200)
- **Sort By**: Ordenação (relevância, preço)
- **Condition**: Condição (todos, novos, usados)
- **Extract Images**: Extrair URLs de imagens
- **Collect Reviews**: Coletar avaliações
- **Max Reviews**: Limite de reviews por produto
- **Generate JSON**: Gerar arquivo JSON além do CSV

### Jobs em Background
- **Status em Tempo Real**: Progresso atualizado automaticamente
- **Múltiplos Jobs**: Execução paralela de jobs
- **Histórico Completo**: Todos os jobs ficam salvos
- **Download Direto**: Arquivos disponíveis imediatamente

## 📈 Monitoramento

### Dashboard
- Jobs ativos e concluídos
- Total de produtos coletados
- Datasets gerados
- Estatísticas em tempo real

### Logs
- `flask_scraper.log`: Logs da aplicação Flask
- `scraper.log`: Logs do sistema de scraping

## 🔧 Personalização

### CSS Personalizado
Edite `static/style.css` para personalizar a aparência:
```css
:root {
    --hp-blue: #0096d6;
    --hp-dark-blue: #006ba6;
    /* Outras variáveis CSS */
}
```

### Templates
Modifique os templates em `templates/` para personalizar a interface.

## 🚨 Limitações e Considerações

1. **Ambiente de Desenvolvimento**: Configurado para desenvolvimento
2. **Autenticação**: Não implementada (adicionar para produção)
3. **Rate Limiting**: Não implementado
4. **Armazenamento**: Arquivos locais (considerar cloud storage)
5. **Escalabilidade**: Single-threaded (considerar Celery para produção)

## 🔒 Segurança

Para produção, considere:
- Implementar autenticação (JWT, API Keys)
- Adicionar rate limiting
- Validação rigorosa de inputs
- HTTPS obrigatório
- Logs de auditoria

## 📚 Documentação Adicional

- **API REST**: Veja `API_DOCUMENTATION.md`
- **Sistema Original**: Veja `README.md`
- **Exemplos**: Execute `exemplo_uso.py`

## 🛠️ Desenvolvimento

### Estrutura da Aplicação Flask
```python
# Principais componentes
- Flask app com blueprints
- Sistema de jobs em background
- API REST com JSON responses
- Templates Jinja2 com Bootstrap
- Arquivos estáticos organizados
```

### Adicionando Novas Funcionalidades
1. **Nova Rota**: Adicione em `flask_app.py`
2. **Novo Template**: Crie em `templates/`
3. **Novo CSS**: Adicione em `static/style.css`
4. **Nova API**: Documente em `API_DOCUMENTATION.md`

## 🎯 Próximos Passos

1. **Deploy em Produção**: Gunicorn + Nginx
2. **Banco de Dados**: SQLite ou PostgreSQL
3. **Cache**: Redis para performance
4. **Filas**: Celery para jobs pesados
5. **Monitoramento**: Prometheus + Grafana
6. **Testes**: Pytest para cobertura completa

---

**Sistema Migrado com Sucesso para Flask!** 🚀

Agora você tem uma aplicação web completa com interface moderna e API REST robusta.
