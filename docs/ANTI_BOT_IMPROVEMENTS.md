# 🤖 Melhorias Anti-Detecção de Bot

Este documento descreve as melhorias implementadas para contornar a detecção de bot do Mercado Livre.

## 🚨 Problema Identificado

O Mercado Livre estava redirecionando para páginas de verificação de conta (`account-verification`), indicando detecção de comportamento automatizado.

## 🛡️ Estratégias Implementadas

### 1. **User-Agents Avançados**
- Lista expandida com 13+ User-Agents atualizados
- Rotação automática para cada requisição
- Simulação de Chrome, Firefox, Safari e Edge
- Versões mais recentes dos navegadores

```python
USER_AGENTS = [
    # Chrome Windows/macOS
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    # Firefox, Safari, Edge...
]
```

### 2. **Headers Realistas de Navegador**
- Headers completos que simulam navegadores reais
- Headers específicos por tipo de navegador
- Simulação de viewport e características do dispositivo

```python
BROWSER_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    # ... mais headers
}
```

### 3. **Sistema de Delays Inteligentes**
- **Delay base**: 5-10 segundos (muito conservador)
- **Randomização**: 100% de variação
- **Delay inicial**: 2-5 segundos antes da primeira requisição
- **Delays progressivos**: Aumentam com tentativas de retry

### 4. **Configurações Ultra-Conservadoras**
```python
{
    'CONCURRENT_REQUESTS': 1,  # Apenas 1 requisição simultânea
    'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    'DOWNLOAD_DELAY': 5-10 segundos,
    'AUTOTHROTTLE_MAX_DELAY': 30 segundos,
    'RETRY_TIMES': 5,  # Mais tentativas
}
```

### 5. **Detecção e Contorno de Verificação**
- Detecção automática de páginas `account-verification`
- Sistema de retry com 5 tentativas
- Estratégias diferentes por tentativa:
  1. **Tentativa 1**: URL original com headers diferentes
  2. **Tentativa 2**: URL simplificada sem parâmetros
  3. **Tentativa 3**: URL base do ML
  4. **Tentativas 4-5**: Volta à URL original
- Delays progressivos: 20s, 40s, 60s, 80s, 100s

### 6. **Middlewares Personalizados**

#### RotatingUserAgentMiddleware
- Rotação automática de User-Agents
- Headers específicos por navegador
- Simulação de sessão realista

#### DelayMiddleware  
- Monitoramento de frequência de requisições
- Delays adaptativos baseados no histórico
- Proteção contra rajadas de requisições

### 7. **Simulação de Comportamento Humano**
- **Referrers ocasionais**: 30% chance de incluir referrer do Google/Bing
- **Viewports aleatórios**: Simulação de diferentes resoluções
- **Sessões realistas**: Renovação de sessão a cada 30 minutos
- **Cookies habilitados**: Manutenção de estado como navegador real

## 📊 Configurações Técnicas

### Headers por Navegador
```python
# Chrome
'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"'
'sec-ch-ua-mobile': '?0'
'sec-ch-ua-platform': '"Windows"'

# Firefox
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3'

# Safari
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
'Accept-Language': 'pt-br'
```

### Timeline de Delays
```
Requisição inicial: 2-5s
Entre requisições: 5-10s + 0-10s (randomização)
Retry 1: 20-30s
Retry 2: 40-50s  
Retry 3: 60-70s
Retry 4: 80-90s
Retry 5: 100-110s
```

## 🧪 Como Testar

### Via API
```bash
curl -X POST http://localhost:5000/api/scraping/simple \
  -H "Content-Type: application/json" \
  -d '{"query": "Cartucho HP", "max_items": 3}'
```

### Via Código Python
```python
from app import HPScrapingSystem

sistema = HPScrapingSystem()
produtos = sistema.executar_scraping_produtos(
    query="Cartucho HP",
    max_items=5
)
```

## 📈 Indicadores de Sucesso

### ✅ Sinais Positivos
- Produtos coletados com sucesso
- Logs sem menção a `account-verification`
- HTML contém estrutura válida do ML
- Tempo de resposta dentro do esperado (considerando delays)

### ⚠️ Sinais de Detecção
- Redirecionamento para `/gz/account-verification`
- HTML muito pequeno ou suspeito
- Erro "Nenhum container de produto encontrado"
- Bloqueios HTTP 403/429

## 🔄 Próximas Melhorias (Se Necessário)

### 1. **Sistema de Proxies**
```python
ROTATING_PROXIES = [
    'http://proxy1:port',
    'http://proxy2:port',
    # Proxies residenciais recomendados
]
```

### 2. **Simulação de JavaScript**
- Usar Selenium ou Playwright
- Executar JavaScript real
- Simular eventos de mouse/teclado

### 3. **Cookies Persistentes**
- Salvar cookies entre sessões
- Simular histórico de navegação
- Manter estado de sessão

### 4. **Geolocalização**
- Headers de localização
- Proxies por região
- Timezone apropriado

## 📋 Logs e Debugging

### Verificar Detecção
```bash
# Verificar logs
grep -i "account-verification" scraper.log

# Analisar HTML salvo
grep -i "verification" scraped_page_content_debug.html
```

### Monitorar Performance
```bash
# Tempo médio de resposta
grep -i "aguardando" scraper.log | tail -5

# Taxa de sucesso
grep -i "produtos coletados" scraper.log | wc -l
```

## 🎯 Resultados Esperados

Com essas melhorias, o sistema deve:
- ✅ Contornar detecção básica de bot
- ✅ Coletar produtos com sucesso
- ✅ Manter baixo perfil de requisições  
- ✅ Simular comportamento humano realista
- ✅ Lidar graciosamente com bloqueios temporários

---

**⚠️ Aviso Legal**: Use estas técnicas de forma ética e respeitando os termos de uso dos sites. O web scraping deve ser feito de forma responsável e com moderação.

