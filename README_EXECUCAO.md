# Como Executar o Detector de Falsificações ML

Este projeto usa Streamlit com Scrapy e multiprocessing. Para evitar os warnings de `ScriptRunContext`, siga as instruções abaixo:

## Opção 1: Usando o Launcher (Recomendado)

Execute o launcher personalizado que configura corretamente o multiprocessing:

```bash
python run_app.py
```

## Opção 2: Comando Streamlit Tradicional

```bash
streamlit run app.py
```

## Opção 3: Via PowerShell (Windows)

```powershell
python -m streamlit run app.py
```

## Resolvendo Problemas

### Warnings de ScriptRunContext

Os warnings `missing ScriptRunContext!` são normais quando:
- O aplicativo está executando em modo básico
- Há código multiprocessing sendo executado
- O contexto do Streamlit não está disponível em processos filhos

Estes warnings **podem ser ignorados** pois não afetam a funcionalidade do aplicativo.

### Configurações Aplicadas

1. **Configuração do multiprocessing**: Movida para dentro de `if __name__ == "__main__"`
2. **Filtros de warnings**: Adicionados para suprimir mensagens desnecessárias
3. **Configuração do Streamlit**: Arquivo `.streamlit/config.toml` com configurações otimizadas
4. **Logging**: Configurado para reduzir warnings de bibliotecas externas

### Dependências

Certifique-se de que todas as dependências estão instaladas:

```bash
pip install -r requirements.txt
```

### Estrutura de Arquivos

```
Challenge-HP/
├── app.py                          # Aplicativo principal
├── run_app.py                      # Launcher recomendado
├── mercadolivre_spider.py         # Spider principal
├── mercadolivre_spider_reviews.py # Spider de reviews
├── requirements.txt               # Dependências
├── .streamlit/
│   └── config.toml               # Configurações do Streamlit
└── README_EXECUCAO.md            # Este arquivo
```

## Funcionalidades

- Busca de produtos no Mercado Livre
- Extração de dados detalhados
- Análise de reviews e opiniões
- Interface web interativa
- Exportação de dados em CSV 