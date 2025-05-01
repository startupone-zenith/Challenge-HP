# Extrator de Dados do Mercado Livre

Esta ferramenta permite extrair dados da API oficial do Mercado Livre de forma simples e eficiente. Com ela, você pode:

- Buscar e exportar produtos por palavra-chave, categoria ou vendedor
- Obter detalhes completos de produtos específicos
- Exportar seus próprios produtos (quando autenticado)
- Consultar categorias do Mercado Livre
- Ver informações da sua conta

## Requisitos

- Python 3.6 ou superior
- Pacotes Python: `requests`

## Instalação

1. Clone este repositório ou baixe os arquivos:
   ```
   git clone https://github.com/seu-usuario/mercadolivre-extractor.git
   ```

2. Instale as dependências:
   ```
   pip install requests
   ```

## Configuração

Você precisa de credenciais do Mercado Livre para usar esta ferramenta:

1. Acesse o [portal de desenvolvedores do Mercado Livre](https://developers.mercadolivre.com.br/)
2. Crie uma aplicação para obter suas credenciais (APP_ID e SECRET_KEY)
3. Obtenha um Access Token e Refresh Token seguindo a [documentação oficial](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
4. Atualize as credenciais nos arquivos `ml_interactive.py`, `mercadolivre_extractor.py` ou `ml_data_exporter.py`

## Uso

### Interface Interativa

Execute o script interativo para uma experiência guiada:

```
python ml_interactive.py
```

Siga as instruções na tela para escolher qual tipo de dados deseja extrair.

### API Python

Você também pode usar a API diretamente em seus próprios scripts:

```python
from mercadolivre_extractor import MercadoLivreAPI

# Inicializar a API
ml_api = MercadoLivreAPI(
    access_token="SEU_ACCESS_TOKEN",
    refresh_token="SEU_REFRESH_TOKEN",
    client_id="SEU_APP_ID",
    client_secret="SUA_SECRET_KEY",
    user_id="SEU_USER_ID"
)

# Buscar produtos
results = ml_api.search_items(query="smartphone", limit=10)

# Obter detalhes de um produto específico
item = ml_api.get_item_details("MLB123456789")

# Buscar categorias
categories = ml_api.get_categories()
```

### Exportador de Dados

O exportador permite salvar os dados em formato CSV e JSON:

```python
from mercadolivre_extractor import MercadoLivreAPI
from ml_data_exporter import MercadoLivreExporter

# Inicializar a API
ml_api = MercadoLivreAPI(
    access_token="SEU_ACCESS_TOKEN",
    refresh_token="SEU_REFRESH_TOKEN",
    client_id="SEU_APP_ID",
    client_secret="SUA_SECRET_KEY",
    user_id="SEU_USER_ID"
)

# Inicializar o exportador
exporter = MercadoLivreExporter(ml_api)

# Exportar resultados de busca
exporter.export_search_results(query="smartphone", limit=50)

# Exportar detalhes de produtos específicos
exporter.export_item_details(["MLB123456789", "MLB987654321"])

# Exportar categorias
exporter.export_categories()
```

## Estrutura do Projeto

- `mercadolivre_extractor.py`: Classe principal para interagir com a API
- `ml_data_exporter.py`: Exportador de dados para CSV e JSON
- `ml_interactive.py`: Interface interativa para usuários finais
- `README.md`: Este arquivo de documentação

## Limitações

- Respeita os limites de requisição da API do Mercado Livre (1500/min para operações gerais)
- O token de acesso expira após 6 horas, mas o script lidará com isso automaticamente usando o refresh token
- Utiliza exponential backoff para lidar com limitações de taxa

## Referências

- [Documentação oficial da API do Mercado Livre](https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br)
- [Autenticação e Autorização](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
- [Boas práticas para usar a plataforma](https://developers.mercadolivre.com.br/pt_br/boas-praticas-para-usar-a-plataforma)

## Contribuição

Contribuições são bem-vindas! Abra um issue ou pull request para melhorar esta ferramenta.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para detalhes. 