# 🚀 Projeto de Detecção de Anúncios Falsificados de Cartuchos HP

Este projeto implementa um pipeline de ponta a ponta para identificar anúncios potencialmente falsificados de cartuchos e suprimentos HP no Mercado Livre, utilizando raspagem de dados (web scraping) e classificação com Grandes Modelos de Linguagem (LLMs).

## 🏛️ Arquitetura do Pipeline

O fluxo de trabalho é orquestrado em três etapas principais, automatizadas para uma execução simples e sequencial:

1.  **Coleta de Links**: Busca ativa no Mercado Livre por anúncios relevantes de cartuchos HP com base em uma lista de modelos (ex: "cartucho hp 667").
2.  **Extração Estruturada**: Visita cada link coletado, extrai o conteúdo textual da página e utiliza um LLM (GPT-4o) para converter os dados brutos em um formato estruturado (JSON), com campos como `titulo`, `preco`, `seller_name`, etc.
3.  **Classificação Inteligente**: Alimenta os dados estruturados em um segundo LLM, que atua como um classificador. Este modelo avalia múltiplos fatores de risco (preço, reputação do vendedor, descrição) para determinar se o anúncio é `autêntico` ou `falsificado`, gerando relatórios detalhados.

### 📜 Scripts Principais

| Arquivo | Funcionalidade |
| :--- | :--- |
| **`run_pipeline.py`** |  orchestrador principal. **É o único script que você precisa executar** para rodar o pipeline completo. |
| `generate_hp_links.py`| (Passo 1) Responsável por realizar buscas no Mercado Livre e coletar as URLs dos anúncios. |
| `generativa_sprint1.py`| (Passo 2) Recebe uma lista de URLs, extrai e estrutura os dados de cada anúncio usando um LLM. |
| `sprint2_llm_classifier copy.py`| (Passo 3) Recebe os dados estruturados, classifica os anúncios e gera os relatórios de análise. |

---

## ⚙️ Configuração do Ambiente

Siga os passos abaixo para preparar seu ambiente de execução.

### 1. Pré-requisitos

*   [Python 3.9+](https://www.python.org/downloads/)
*   [Docker](https://www.docker.com/products/docker-desktop/) (para execução em contêiner)

### 2. Instalação de Dependências

Clone o repositório e, no diretório `Sprint_GENAI`, instale as bibliotecas Python necessárias:

```bash
pip install -r requirements.txt
```

### 3. Chave da API OpenAI

O projeto utiliza a API da OpenAI para as tarefas de extração e classificação. Você precisa configurar sua chave de API como uma variável de ambiente.

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sua_chave_aqui"
```

**Linux/macOS:**
```bash
export OPENAI_API_KEY="sua_chave_aqui"
```

> **Nota**: Para que a chave persista, adicione o comando ao seu perfil de shell (ex: `.bashrc`, `.zshrc`, ou `profile.ps1`).

---

## ▶️ Executando o Pipeline

Existem duas maneiras de executar o projeto: localmente ou via Docker.

### 🐳 Opção 1: Execução com Docker (Recomendado)

A forma mais simples e recomendada é utilizar Docker, que abstrai toda a configuração do ambiente.

1.  **Construa a Imagem Docker:**
    No diretório raiz do projeto (`Sprints`), execute o comando abaixo. Isso irá construir a imagem com todas as dependências e scripts.

    ```bash
    docker build -t hp-fraud-detector -f Sprint_GENAI/Dockerfile .
    ```

2.  **Execute o Contêiner:**
    Após a construção, execute o contêiner. Lembre-se de passar sua chave da API OpenAI para dentro dele.

    ```bash
    docker run --rm -e OPENAI_API_KEY=$env:OPENAI_API_KEY -v ./Sprint_GENAI/data:/app/data -v ./Sprint_GENAI/output:/app/output hp-fraud-detector
    ```
    *   `--rm`: Remove o contêiner após a execução.
    *   `-e OPENAI_API_KEY=...`: Passa a variável de ambiente para o contêiner.
    *   `-v`: Mapeia as pastas `data` e `output` locais para que os resultados sejam salvos na sua máquina.

O pipeline completo será executado dentro do contêiner.

### 💻 Opção 2: Execução Local

Se preferir não usar Docker, você pode executar o pipeline diretamente na sua máquina.

1.  **Navegue até o Diretório:**
    ```bash
    cd Sprint_GENAI
    ```

2.  **Execute o Script Orquestrador:**
    Basta executar o script `run_pipeline.py`. Ele cuidará de chamar os outros scripts na ordem correta.

    ```bash
    python run_pipeline.py
    ```

    Opcionalmente, você pode executar cada passo manualmente se quiser depurar ou analisar uma etapa específica. O orquestrador automatiza exatamente o fluxo abaixo:
    
    ```bash
    # 1. Coletar links
    python generate_hp_links.py

    # 2. Extrair dados (usando o arquivo de links gerado)
    #    (O nome do arquivo .txt muda a cada execução)
    python generativa_sprint1.py data/hp_cartridge_urls_20240618_163000.txt

    # 3. Classificar os anúncios
    python "sprint2_llm_classifier copy.py"
    ```

---

## 📊 Análise dos Resultados

Após a execução do pipeline, os resultados são salvos em duas pastas principais dentro de `Sprint_GENAI/`:

### 📁 `data/`
Contém os dados brutos e intermediários do processo.

*   `hp_cartridge_urls_*.txt`: A lista de URLs coletadas do Mercado Livre.
*   `hp_cartridge_links_*.json`: As mesmas URLs com metadados adicionais.
*   **`extracted_ads.json`**: **Arquivo chave.** Contém os dados estruturados de todos os anúncios, extraídos pelo Sprint 1. É o input principal para o classificador.
*   `extracted_ads.csv`: O mesmo que o JSON, mas em formato CSV.

### 📁 `output/`
Contém os relatórios finais e a análise de classificação.

*   `classification_results.csv`: O resultado detalhado da classificação para cada anúncio, incluindo a classe (`authentic`/`counterfeit`), a confiança do modelo e os fatores de risco identificados.
*   `evaluation_metrics.json`: Métricas de performance do classificador (Acurácia, Precisão, etc.).
*   `high_risk_products.csv`: Uma lista filtrada apenas com os anúncios classificados como falsificados com alta confiança, prontos para ação.
*   `executive_summary.md`: Um resumo executivo em Markdown com os principais KPIs de negócio, como a quantidade de anúncios suspeitos encontrados e a potencial receita protegida.
*   `confusion_matrix.png`: Gráfico visual da matriz de confusão.
*   `roc_curves.png`: Gráfico da curva ROC para avaliar a performance do classificador.
*   `confidence_distribution.png`: Histograma mostrando a distribuição das confianças das previsões.
*   `prompt_templates.txt`: Cópia exata dos prompts usados, para fins de auditoria e depuração. 