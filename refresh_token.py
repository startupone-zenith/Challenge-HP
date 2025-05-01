import requests
import datetime

# Configurações da aplicação
APP_ID = '6940700813779269'
SECRET_KEY = 'rN094Y2OsesaPFCJg7K9igQa7CYN4oyN'
REFRESH_TOKEN = 'TG-681384968c1fbf0001ab6392-340557736'  # Atualizado em 05/05/2024

url = 'https://api.mercadolibre.com/oauth/token'
headers = {
    'accept': 'application/json',
    'content-type': 'application/x-www-form-urlencoded'
}
data = {
    'grant_type': 'refresh_token',
    'client_id': APP_ID,
    'client_secret': SECRET_KEY,
    'refresh_token': REFRESH_TOKEN
}

response = requests.post(url, headers=headers, data=data)
print(f"Status Code: {response.status_code}")
print("Resposta:")
print(response.json())

# Se a resposta for bem-sucedida, salva o novo token
if response.status_code == 200:
    result = response.json()
    print("\nToken atualizado com sucesso!")
    print(f"Novo access_token: {result['access_token']}")
    print(f"Expira em: {result['expires_in']} segundos ({result['expires_in']/3600:.1f} horas)")
    print(f"Novo refresh_token: {result['refresh_token']}")
    print("\nIMPORTANTE: Guarde o novo refresh_token para uso futuro!")
    
    # Data atual para o comentário
    refreshed_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Atualiza o arquivo refresh_token.py
    with open('refresh_token.py', 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if "REFRESH_TOKEN = " in line:
            lines[i] = f"REFRESH_TOKEN = '{result['refresh_token']}'  # Atualizado em {refreshed_date}\n"
            break
    
    with open('refresh_token.py', 'w') as f:
        f.writelines(lines)
    
    print("Arquivo refresh_token.py atualizado com o novo refresh_token!")
else:
    print("\nERRO ao atualizar o token. Verifique as credenciais e o refresh_token.") 