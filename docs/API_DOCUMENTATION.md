# 🔌 API REST - Sistema de Scraping HP

Esta documentação descreve a API REST do Sistema de Scraping HP desenvolvido com Flask.

## 📋 Base URL
```
http://localhost:5000/api
```

## 🔐 Autenticação
A API atual não requer autenticação, mas em produção é recomendado implementar autenticação via API Key ou JWT.

## 📊 Endpoints Principais

### 1. Iniciar Scraping

**POST** `/scraping/start`

Inicia um novo job de scraping em background.

#### Request Body
```json
{
  "query": "cartucho hp 664",
  "max_items": 50,
  "extract_images": false,
  "sort_by": "relevance",
  "condition": "all",
  "collect_reviews": true,
  "max_reviews_per_product": 100,
  "generate_json": false
}
```

#### Parâmetros
- `query` (string, obrigatório): Termo de busca
- `max_items` (int, opcional): Máximo de produtos (padrão: 50)
- `extract_images` (bool, opcional): Extrair URLs de imagens (padrão: false)
- `sort_by` (string, opcional): Ordenação - "relevance", "price_asc", "price_desc" (padrão: "relevance")
- `condition` (string, opcional): Condição - "all", "new", "used" (padrão: "all")
- `collect_reviews` (bool, opcional): Coletar reviews (padrão: false)
- `max_reviews_per_product` (int, opcional): Máximo de reviews por produto (padrão: 100)
- `generate_json` (bool, opcional): Gerar arquivo JSON além do CSV (padrão: false)

#### Response
```json
{
  "success": true,
  "job_id": "a1b2c3d4",
  "message": "Job de scraping iniciado com sucesso"
}
```

### 2. Status do Job

**GET** `/jobs/{job_id}/status`

Obtém o status atual de um job específico.

#### Response
```json
{
  "success": true,
  "job_id": "a1b2c3d4",
  "status": "concluido",
  "progress": 100,
  "query": "cartucho hp 664",
  "produtos_coletados": 45,
  "reviews_coletadas": 230,
  "start_time": "2024-09-25T20:30:00",
  "end_time": "2024-09-25T20:35:00",
  "error_message": null,
  "result_files": [
    {
      "type": "csv",
      "filename": "dataset_a1b2c3d4_20240925_203500.csv",
      "path": "datasets_gerados/dataset_a1b2c3d4_20240925_203500.csv",
      "size": 1024000
    }
  ]
}
```

#### Status Possíveis
- `iniciado`: Job foi criado
- `coletando_produtos`: Coletando dados dos produtos
- `coletando_reviews`: Coletando reviews dos produtos
- `gerando_datasets`: Gerando arquivos de saída
- `concluido`: Job finalizado com sucesso
- `erro`: Job falhou

### 3. Listar Jobs

**GET** `/jobs`

Lista todos os jobs de scraping.

#### Response
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "a1b2c3d4",
      "status": "concluido",
      "progress": 100,
      "query": "cartucho hp 664",
      "produtos_coletados": 45,
      "reviews_coletadas": 230,
      "start_time": "2024-09-25T20:30:00",
      "end_time": "2024-09-25T20:35:00"
    }
  ]
}
```

### 4. Listar Datasets

**GET** `/datasets`

Lista todos os datasets disponíveis para download.

#### Response
```json
{
  "success": true,
  "datasets": [
    {
      "filename": "dataset_a1b2c3d4_20240925_203500.csv",
      "size": 1024000,
      "modified": "2024-09-25T20:35:00",
      "type": "CSV"
    }
  ]
}
```

### 5. Download de Dataset

**GET** `/datasets/{filename}/download`

Faz download de um dataset específico.

#### Response
Arquivo binário com headers apropriados para download.

### 6. Scraping Simples

**POST** `/scraping/simple`

Executa scraping síncrono simples para testes (limitado a 10 produtos).

#### Request Body
```json
{
  "query": "cartucho hp",
  "max_items": 5,
  "sort_by": "relevance",
  "condition": "all"
}
```

#### Response
```json
{
  "success": true,
  "total_produtos": 5,
  "produtos": [
    {
      "id": "MLB123456",
      "title": "Cartucho HP 664 Original",
      "price": "R$ 89,90",
      "seller": "Loja HP Oficial",
      "condition": "new",
      "free_shipping": true,
      "link": "https://produto.mercadolivre.com.br/...",
      "image_url": "https://...",
      "location": "São Paulo",
      "sales": "100+ vendidos"
    }
  ]
}
```

## 🚨 Códigos de Erro

### 400 - Bad Request
```json
{
  "success": false,
  "error": "Parâmetro 'query' é obrigatório"
}
```

### 404 - Not Found
```json
{
  "success": false,
  "error": "Job não encontrado"
}
```

### 500 - Internal Server Error
```json
{
  "success": false,
  "error": "Erro interno do servidor"
}
```

## 📝 Exemplos de Uso

### cURL

#### Iniciar Scraping
```bash
curl -X POST http://localhost:5000/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cartucho hp 664",
    "max_items": 20,
    "collect_reviews": true
  }'
```

#### Verificar Status
```bash
curl http://localhost:5000/api/jobs/a1b2c3d4/status
```

#### Listar Datasets
```bash
curl http://localhost:5000/api/datasets
```

#### Download Dataset
```bash
curl -O http://localhost:5000/api/datasets/dataset_a1b2c3d4_20240925_203500.csv/download
```

### Python

```python
import requests

# Iniciar scraping
response = requests.post('http://localhost:5000/api/scraping/start', json={
    'query': 'cartucho hp 664',
    'max_items': 20,
    'collect_reviews': True
})

job_data = response.json()
job_id = job_data['job_id']

# Verificar status
status_response = requests.get(f'http://localhost:5000/api/jobs/{job_id}/status')
status_data = status_response.json()

print(f"Status: {status_data['status']}")
print(f"Progresso: {status_data['progress']}%")
```

### JavaScript

```javascript
// Iniciar scraping
fetch('http://localhost:5000/api/scraping/start', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'cartucho hp 664',
    max_items: 20,
    collect_reviews: true
  })
})
.then(response => response.json())
.then(data => {
  console.log('Job iniciado:', data.job_id);
  
  // Verificar status periodicamente
  const checkStatus = () => {
    fetch(`http://localhost:5000/api/jobs/${data.job_id}/status`)
      .then(response => response.json())
      .then(status => {
        console.log(`Status: ${status.status} (${status.progress}%)`);
        
        if (status.status !== 'concluido' && status.status !== 'erro') {
          setTimeout(checkStatus, 5000); // Verificar novamente em 5s
        }
      });
  };
  
  checkStatus();
});
```

## 🔧 Limitações

1. **Rate Limiting**: Não implementado (recomendado para produção)
2. **Autenticação**: Não implementada (necessária para produção)
3. **Paginação**: Não implementada para listas grandes
4. **Cache**: Não implementado
5. **Logs de API**: Logs básicos apenas

## 🚀 Melhorias Futuras

1. Implementar autenticação via API Key
2. Adicionar rate limiting
3. Implementar paginação
4. Adicionar cache Redis
5. Melhorar logs e monitoramento
6. Adicionar webhooks para notificações
7. Implementar filtros avançados
8. Adicionar compressão de responses

