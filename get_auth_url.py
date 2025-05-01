import random
import string

# Substitua pelo ID da sua aplicação
APP_ID = '6940700813779269'
# URI de redirecionamento correta com protocolo
REDIRECT_URI = 'http://www.sandron.dev.br'

# Gera um state aleatório para segurança
def generate_random_state(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

state = generate_random_state()

# URL para o Brasil
auth_url = f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={APP_ID}&state={state}&redirect_uri={REDIRECT_URI}"

print("========= INSTRUÇÕES PARA OBTER UM NOVO TOKEN =========")
print("1. Acesse a URL abaixo no seu navegador:")
print(auth_url)
print("\n2. Faça login na sua conta do Mercado Livre quando solicitado")
print("3. Autorize a aplicação quando solicitado")
print("4. Você será redirecionado para a URL de redirecionamento")
print("5. Procure por 'code=' na URL redirecionada e copie o valor")
print("\nEm seguida, use esse código no script exchange_code.py para obter um novo access_token e refresh_token") 