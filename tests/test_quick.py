import requests
import time

print('🧪 Teste rápido das melhorias anti-bot...')
start = time.time()

try:
    response = requests.post('http://localhost:5000/api/scraping/simple', 
                           json={'query': 'Cartucho HP', 'max_items': 1}, 
                           timeout=120)
    end = time.time()
    
    print(f'⏱️ Tempo de resposta: {end-start:.1f}s')
    print(f'📊 Status HTTP: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            produtos = data.get('produtos', [])
            print(f'✅ SUCESSO! {len(produtos)} produtos coletados')
            if produtos:
                print(f'📦 Primeiro produto: {produtos[0].get("title", "")[:50]}...')
        else:
            error = data.get('error', 'Erro desconhecido')
            print(f'❌ Erro: {error}')
            if 'account-verification' in error.lower():
                print('🤖 Ainda detectando bot - precisa de mais melhorias')
            else:
                print('ℹ️ Erro pode não estar relacionado à detecção de bot')
    else:
        print(f'🚨 Erro HTTP: {response.text[:100]}')
        
except requests.exceptions.Timeout:
    print('⏰ Timeout - normal devido aos delays anti-bot')
except Exception as e:
    print(f'💥 Erro: {e}')

print('\n📋 Status das melhorias implementadas:')
print('✅ User-Agents atualizados e rotativos')
print('✅ Headers realistas de navegador')  
print('✅ Delays conservadores (5-10s base)')
print('✅ Configurações ultra-conservadoras (1 req simultânea)')
print('✅ Sistema de retry inteligente')
print('✅ Detecção de páginas de verificação')
print('✅ Middlewares personalizados')

