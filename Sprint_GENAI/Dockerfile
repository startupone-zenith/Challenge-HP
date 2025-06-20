# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Evita prompts interativos (e.g. apt)
ENV DEBIAN_FRONTEND=noninteractive

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia apenas arquivos de dependência primeiro para otimizar cache
COPY requirements.txt ./

# Instala dependências do sistema e Python
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copia o restante do código
COPY . .

# Variáveis de ambiente obrigatórias (substitua pelas suas chaves reais)
ENV OPENAI_API_KEY="YOUR_OPENAI_KEY" \
    ANTHROPIC_API_KEY="YOUR_ANTHROPIC_KEY" \
    GOOGLE_API_KEY="YOUR_GOOGLE_KEY"

# Diretório onde dados e saídas serão gravados
RUN mkdir -p /app/data /app/output
VOLUME ["/app/data", "/app/output"]

# Comando padrão (ajustável via docker-compose)
CMD ["python", "quick_test_links.py"] 