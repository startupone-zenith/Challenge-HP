import requests
import json
import sys
import datetime

# Configurações da aplicação
APP_ID = '6940700813779269'
SECRET_KEY = 'rN094Y2OsesaPFCJg7K9igQa7CYN4oyN'
REDIRECT_URI = 'https://www.sandron.dev.br'

def get_new_tokens(code):
    """Troca o código de autorização por um access_token e refresh_token"""
    url = 'https://api.mercadolibre.com/oauth/token'
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'client_id': APP_ID,
        'client_secret': SECRET_KEY,
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    
    response = requests.post(url, headers=headers, data=data)
    return response

if __name__ == "__main__":
    print("========= OBTENÇÃO DE NOVOS TOKENS =========")
    
    # Solicita o código de autorização
    auth_code = input("Cole o código de autorização obtido no navegador: ")
    
    if not auth_code:
        print("Código de autorização não fornecido. Encerrando.")
        sys.exit(1)
    
    # Obtém novos tokens
    print("\nTrocando código por tokens, aguarde...")
    response = get_new_tokens(auth_code)
    
    if response.status_code == 200:
        result = response.json()
        access_token = result.get('access_token')
        refresh_token = result.get('refresh_token')
        expires_in = result.get('expires_in')
        user_id = result.get('user_id')
        
        print("\n✅ Tokens obtidos com sucesso!")
        print(f"\nAccess Token: {access_token}")
        print(f"Refresh Token: {refresh_token}")
        print(f"Expira em: {expires_in} segundos ({expires_in/3600:.1f} horas)")
        print(f"User ID: {user_id}")
        
        # Salva em um arquivo para referência futura
        with open('ml_tokens.json', 'w') as f:
            json.dump(result, f, indent=4)
            
        print("\nTokens salvos no arquivo ml_tokens.json")
        print("\nIMPORTANTE: Guarde o refresh_token para uso futuro!")
        
        # Data atual para o comentário
        refreshed_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Atualiza o arquivo refresh_token.py
        with open('refresh_token.py', 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if "REFRESH_TOKEN = " in line:
                lines[i] = f"REFRESH_TOKEN = '{refresh_token}'  # Atualizado em {refreshed_date}\n"
                break
        
        with open('refresh_token.py', 'w') as f:
            f.writelines(lines)
        
        print("Arquivo refresh_token.py atualizado com o novo refresh_token!")
    else:
        print(f"\n❌ Erro ao obter tokens: {response.status_code}")
        print(response.json()) 