# 🔧 Modos de Execução do Flask

## 🚫 **PROBLEMA RESOLVIDO**

O Flask estava reiniciando automaticamente quando os jobs terminavam porque:
- **Debug mode** estava ativo (`debug=True`)
- **Watchdog** monitorava todos os arquivos do projeto
- Quando jobs salvavam dados (CSV/JSON/logs), o watchdog detectava e reiniciava o Flask

## ✅ **SOLUÇÃO IMPLEMENTADA**

### 1. **Modo Desenvolvimento (Padrão)**
```bash
cd src/web
python run_flask.py
```

**Características:**
- ✅ Debug ativado (mensagens detalhadas de erro)  
- ❌ Watchdog/Reloader **DESATIVADO** (não reinicia mais)
- ✅ Perfeito para testar jobs sem interrupções

### 2. **Modo Produção**
```bash
cd src/web
python run_production.py
```

**Características:**
- ❌ Debug desativado (otimizado)
- ❌ Watchdog/Reloader desativado
- ✅ Máxima performance

## 🎯 **Recomendação**

**Para testar o sistema:** Use `python run_flask.py` (modo padrão)
- Jobs vão funcionar normalmente 
- Flask **NÃO** vai mais reiniciar
- Você ainda terá mensagens de debug úteis

## 📝 **Mudanças Realizadas**

1. **`src/web/run_flask.py`** - Reloader desativado por padrão
2. **`src/web/flask_app.py`** - Logs movidos para diretório `/logs`
3. **`src/web/run_production.py`** - Modo produção dedicado

## 🧪 **Teste**

Execute um job de scraping e observe que o Flask **NÃO** reiniciará mais quando o job terminar.
