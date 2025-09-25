# HP Challenge Sprint - Flask Migration

## 🏆 Detector de Falsificações - Versão Flask

Sistema Inteligente de Detecção de Produtos HP Suspeitos/Piratas em E-commerce, migrado do Streamlit para Flask.

## 📁 Estrutura do Projeto

```
Challenge-HP/
├── streamlit_backup/          # Backup da aplicação Streamlit original
├── templates/                 # Templates HTML do Flask
│   ├── base.html             # Template base
│   ├── index.html            # Página inicial
│   ├── busca.html            # Busca & Coleta
│   ├── falsificacao.html     # Detecção de Falsificação
│   ├── dataset.html          # Gerador de Dataset
│   ├── analise.html          # Análise Exploratória
│   ├── 404.html              # Página de erro 404
│   └── 500.html              # Página de erro 500
├── static/                   # Arquivos estáticos (CSS, JS, imagens)
├── flask_app.py              # Aplicação Flask principal
├── run_flask_app.py          # Script para executar a aplicação
├── requirements_flask.txt    # Dependências do Flask
└── README_FLASK.md          # Este arquivo
```

## 🚀 Como Executar

### 1. Instalar Dependências

```bash
pip install -r requirements_flask.txt
```

### 2. Executar a Aplicação

```bash
python run_flask_app.py
```

Ou diretamente:

```bash
python flask_app.py
```

### 3. Acessar a Aplicação

Abra seu navegador e acesse: `http://localhost:5000`

## ✨ Funcionalidades Migradas

### 🔍 Busca & Coleta
- ✅ Interface de configuração de busca
- ✅ Integração com spiders do Scrapy
- ✅ Sistema de cache inteligente
- ✅ Extração de dados detalhados
- ✅ Carregamento de imagens
- ✅ Filtros e ordenação

### 🚨 Detecção de Falsificação
- ✅ Análise probabilística multi-critério
- ✅ Análise de preços suspeitos
- ✅ Verificação de vendedores
- ✅ Análise de títulos e descrições
- ✅ Padrões em reviews
- ✅ Classificação automática (Suspeito/Original/Incerto)
- ✅ Relatórios exportáveis

### 📊 Dataset Generator
- ✅ Múltiplos formatos de saída (CSV, JSON, XLSX)
- ✅ Configuração flexível de campos
- ✅ Templates pré-configurados
- ✅ Limpeza de dados
- ✅ Inclusão de metadados

### 🔬 Análise Exploratória (EDA)
- ✅ Visualizações interativas com Plotly
- ✅ Estatísticas descritivas
- ✅ Análise de preços e outliers
- ✅ Análise de vendedores
- ✅ Distribuição de ratings
- ✅ Análise de texto e nuvem de palavras
- ✅ Exportação de relatórios

## 🔧 Principais Melhorias na Migração

### Interface de Usuário
- **Bootstrap 5**: Interface moderna e responsiva
- **Navegação intuitiva**: Menu de navegação claro
- **Feedback visual**: Alertas e indicadores de progresso
- **Responsividade**: Funciona em desktop e mobile

### Arquitetura
- **Separação de responsabilidades**: Templates, rotas e lógica separados
- **API RESTful**: Endpoints JSON para comunicação assíncrona
- **Sistema de sessões**: Cache persistente durante a sessão
- **Tratamento de erros**: Páginas de erro personalizadas

### Performance
- **Carregamento assíncrono**: Interface não trava durante processamento
- **Cache otimizado**: Sistema de cache adaptado para Flask sessions
- **Processamento paralelo**: Mantém capacidades de multiprocessing

## 📝 Diferenças do Streamlit

| Aspecto | Streamlit | Flask |
|---------|-----------|--------|
| **Interface** | Widgets automáticos | HTML/CSS personalizado |
| **Navegação** | Sidebar e tabs | Menu de navegação |
| **Estado** | Session state | Flask sessions |
| **Atualizações** | Rerun automático | AJAX requests |
| **Customização** | Limitada | Total controle |
| **Deploy** | Streamlit Cloud | Qualquer servidor web |

## 🛠️ Configuração Avançada

### Variáveis de Ambiente
Crie um arquivo `.env` para configurações:

```env
FLASK_ENV=development
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
```

### Configuração de Produção
Para produção, modifique `flask_app.py`:

```python
app.config.update(
    DEBUG=False,
    SECRET_KEY=os.environ.get('SECRET_KEY'),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True
)
```

## 📊 API Endpoints

### Busca de Produtos
```
POST /api/buscar
Content-Type: application/json

{
    "query": "cartucho hp",
    "max_items": 20,
    "sort_by": "relevance",
    "condition": "all",
    "load_images": true
}
```

### Análise de Falsificação
```
POST /api/analisar_falsificacao
Content-Type: application/json

{
    "analisar_reviews": false,
    "analise_detalhada": true
}
```

### Gerenciamento de Cache
```
POST /api/clear_cache
GET /api/cache_info
```

## 🐛 Troubleshooting

### Problema: Erro ao importar módulos
**Solução**: Certifique-se de que está no diretório correto e instalou as dependências:
```bash
cd Challenge-HP
pip install -r requirements_flask.txt
```

### Problema: Porta 5000 ocupada
**Solução**: Modifique a porta em `flask_app.py`:
```python
app.run(host='127.0.0.1', port=5001, debug=True)
```

### Problema: Cache não funcionando
**Solução**: Verifique se as sessões estão habilitadas e configure uma SECRET_KEY.

## 🔄 Migração de Dados

Os dados do Streamlit (session_state) não são automaticamente migrados. Para preservar dados:

1. Execute uma nova busca na aplicação Flask
2. Os resultados serão armazenados nas sessões Flask
3. Use as funcionalidades normalmente

## 🚀 Deploy

### Desenvolvimento
```bash
python run_flask_app.py
```

### Produção (exemplo com Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 flask_app:app
```

### Docker (opcional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements_flask.txt .
RUN pip install -r requirements_flask.txt
COPY . .
EXPOSE 5000
CMD ["python", "flask_app.py"]
```

## 📞 Suporte

Para dúvidas sobre a migração ou problemas técnicos, verifique:

1. **Logs da aplicação**: Console onde executou o Flask
2. **Logs do navegador**: F12 > Console para erros JavaScript
3. **Backup Streamlit**: Pasta `streamlit_backup/` com versão original

## 🎯 Próximos Passos

- [ ] Implementar autenticação de usuários
- [ ] Adicionar testes automatizados
- [ ] Otimizar performance para datasets grandes
- [ ] Integrar com banco de dados
- [ ] Implementar API de machine learning
- [ ] Adicionar monitoramento e métricas

---

**HP Challenge Sprint** - Sistema Inteligente de Detecção de Falsificações
Migrado para Flask com sucesso! 🎉

