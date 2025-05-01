import sys
from mercadolivre_extractor import MercadoLivreAPI
from ml_data_exporter import MercadoLivreExporter

def display_menu():
    """Display the main menu options"""
    print("\n" + "=" * 50)
    print("MERCADO LIVRE DATA EXTRACTOR")
    print("=" * 50)
    print("1. Buscar e exportar produtos")
    print("2. Exportar detalhes de um produto específico")
    print("3. Exportar meus produtos")
    print("4. Exportar categorias")
    print("5. Exportar informações da minha conta")
    print("6. Exportar dados simplificados (link, nome e vendedor)")
    print("7. Sair")
    print("=" * 50)

def search_products(exporter):
    """Search and export products based on user criteria"""
    print("\n--- BUSCA DE PRODUTOS ---")
    query = input("Digite o termo de busca (deixe vazio para pular): ")
    seller_id = input("ID do vendedor (deixe vazio para pular): ")
    category = input("ID da categoria (deixe vazio para pular): ")
    
    # Display available sites
    print("\nSites disponíveis:")
    print("MLB - Brasil")
    print("MLA - Argentina")
    print("MLM - México")
    print("MCO - Colômbia")
    print("MLU - Uruguai")
    print("MLC - Chile")
    print("MPE - Peru")
    print("MLV - Venezuela")
    site_id = input("\nCódigo do site (padrão: MLB para Brasil): ") or "MLB"
    
    try:
        limit = int(input("Número máximo de resultados (padrão: 50): ") or "50")
    except ValueError:
        limit = 50
        print("Valor inválido, usando padrão: 50")
    
    # Validate input - at least one search criteria
    if not any([query, seller_id, category]):
        print("Erro: Forneça pelo menos um critério de busca (termo, vendedor ou categoria)")
        return
    
    # Execute search
    print(f"\nBuscando produtos no site {site_id}, aguarde...")
    csv_path, json_path = exporter.export_search_results(
        query=query if query else None,
        seller_id=seller_id if seller_id else None,
        category=category if category else None,
        limit=limit,
        site_id=site_id
    )
    
    if csv_path and json_path:
        print(f"\nDados exportados com sucesso!")
        print(f"CSV: {csv_path}")
        print(f"JSON (dados completos): {json_path}")
    else:
        print("\nNenhum resultado encontrado para os critérios fornecidos.")

def get_item_details(exporter):
    """Get and export details for specific items"""
    print("\n--- DETALHES DO PRODUTO ---")
    items_input = input("Digite o ID do produto ou múltiplos IDs separados por vírgula: ")
    
    if not items_input.strip():
        print("Erro: Forneça pelo menos um ID de produto")
        return
    
    # Parse input and clean whitespace
    item_ids = [item_id.strip() for item_id in items_input.split(",")]
    
    print(f"\nBuscando detalhes para {len(item_ids)} produto(s), aguarde...")
    csv_path, json_path = exporter.export_item_details(item_ids)
    
    if csv_path and json_path:
        print(f"\nDados exportados com sucesso!")
        print(f"CSV: {csv_path}")
        print(f"JSON (dados completos): {json_path}")
    else:
        print("\nNenhum detalhe encontrado para os IDs fornecidos.")

def export_user_items(exporter):
    """Export the user's items"""
    print("\n--- MEUS PRODUTOS ---")
    try:
        limit = int(input("Número máximo de produtos (padrão: 50): ") or "50")
    except ValueError:
        limit = 50
        print("Valor inválido, usando padrão: 50")
    
    print(f"\nBuscando seus produtos, aguarde...")
    csv_path, json_path = exporter.export_user_items(limit=limit)
    
    if csv_path and json_path:
        print(f"\nDados exportados com sucesso!")
        print(f"CSV: {csv_path}")
        print(f"JSON (dados completos): {json_path}")
    else:
        print("\nNenhum produto encontrado em sua conta.")

def export_categories(exporter):
    """Export categories"""
    print("\n--- CATEGORIAS ---")
    
    # Display available sites
    print("\nSites disponíveis:")
    print("MLB - Brasil")
    print("MLA - Argentina")
    print("MLM - México")
    print("MCO - Colômbia")
    print("MLU - Uruguai")
    print("MLC - Chile")
    print("MPE - Peru")
    print("MLV - Venezuela")
    site_id = input("\nCódigo do site (padrão: MLB para Brasil): ") or "MLB"
    
    print(f"\nBuscando categorias para o site {site_id}, aguarde...")
    csv_path, json_path = exporter.export_categories(site_id)
    
    if csv_path and json_path:
        print(f"\nDados exportados com sucesso!")
        print(f"CSV: {csv_path}")
        print(f"JSON (dados completos): {json_path}")
    else:
        print(f"\nNenhuma categoria encontrada para o site {site_id}.")

def export_user_info(ml_api):
    """Export user information"""
    print("\n--- MINHAS INFORMAÇÕES ---")
    print("Buscando suas informações, aguarde...")
    
    user_info = ml_api.get_user_info()
    if user_info:
        print("\nInformações da Conta:")
        print(f"ID: {user_info.get('id')}")
        print(f"Apelido: {user_info.get('nickname')}")
        print(f"Nome: {user_info.get('first_name', '')} {user_info.get('last_name', '')}")
        print(f"E-mail: {user_info.get('email', 'Não disponível')}")
        print(f"País: {user_info.get('country_id', '')}")
        print(f"Data de registro: {user_info.get('registration_date', '')}")
        
        # Get reputation
        reputation = user_info.get('seller_reputation', {})
        if reputation:
            print("\nReputação como Vendedor:")
            print(f"Nível: {reputation.get('level_id', 'N/A')}")
            print(f"Status Power Seller: {reputation.get('power_seller_status', 'N/A')}")
            
            transactions = reputation.get('transactions', {})
            if transactions:
                print(f"Total de vendas: {transactions.get('total', 0)}")
                print(f"Vendas completadas: {transactions.get('completed', 0)}")
                print(f"Avaliações positivas: {transactions.get('ratings', {}).get('positive', 0)}")
                print(f"Avaliações neutras: {transactions.get('ratings', {}).get('neutral', 0)}")
                print(f"Avaliações negativas: {transactions.get('ratings', {}).get('negative', 0)}")
    else:
        print("\nNão foi possível obter informações da conta.")

def export_simplified_data(ml_api):
    """Exporta dados simplificados (link, nome e vendedor)"""
    print("\n--- DADOS SIMPLIFICADOS ---")
    query = input("Digite o termo de busca (deixe vazio para pular): ")
    seller_id = input("ID do vendedor (deixe vazio para pular): ")
    category = input("ID da categoria (deixe vazio para pular): ")
    
    display_available_sites()
    site_id = input("Código do site (padrão: MLB para Brasil): ") or "MLB"
    
    try:
        limit = int(input("Número máximo de resultados (padrão: 50): ") or "50")
    except ValueError:
        limit = 50
        
    # Valida entradas
    if not any([query, seller_id, category]):
        print("Erro: Você deve fornecer pelo menos um termo de busca, ID de vendedor ou categoria.")
        return
        
    print(f"\nBuscando produtos simplificados no site {site_id}, aguarde...")
    
    # Tenta exportar
    try:
        exporter = MercadoLivreExporter(ml_api)
        csv_file = exporter.export_simple_data(query, seller_id, category, limit, site_id)
        
        if csv_file:
            print("\nDados exportados com sucesso!")
            print(f"CSV: {csv_file}")
        else:
            print("\nErro: Não foi possível exportar os dados.")
            print("Verificando detalhes para diagnóstico...")
            
            # Tenta obter os dados diretamente da API para diagnóstico
            results = ml_api.search_items(query, seller_id, category, limit, site_id=site_id)
            if results:
                print("\nDados recebidos da API para diagnóstico:")
                
                if isinstance(results, dict):
                    print(f"Tipo de resposta: Dicionário com {len(results)} chaves")
                    print(f"Chaves disponíveis: {', '.join(results.keys())}")
                    
                    # Verificar o conteúdo do 'results' ou 'content'
                    if 'results' in results:
                        items = results.get('results', [])
                        print(f"Total de itens em 'results': {len(items)}")
                        if items and len(items) > 0:
                            first_item = items[0]
                            if isinstance(first_item, dict):
                                print(f"Campos do primeiro item: {', '.join(first_item.keys())}")
                                print(f"Título: {first_item.get('title', 'N/A')}")
                                print(f"Link: {first_item.get('permalink', 'N/A')}")
                                print(f"Vendedor: {first_item.get('seller_id', 'N/A') if 'seller_id' in first_item else 'N/A'}")
                    
                    elif 'content' in results:
                        items = results.get('content', [])
                        print(f"Total de itens em 'content': {len(items)}")
                        if items and len(items) > 0:
                            first_item = items[0]
                            if isinstance(first_item, dict):
                                print(f"Campos do primeiro item: {', '.join(first_item.keys())}")
                                
                elif isinstance(results, list):
                    print(f"Tipo de resposta: Lista com {len(results)} itens")
                    if results and len(results) > 0:
                        first_item = results[0]
                        if isinstance(first_item, dict):
                            print(f"Campos do primeiro item: {', '.join(first_item.keys())}")
            else:
                print("Não foi possível obter dados da API para diagnóstico.")
    except Exception as e:
        print(f"\nErro durante a exportação: {str(e)}")
        import traceback
        traceback.print_exc()
        
    input("\nPressione Enter para continuar...")

def display_available_sites():
    """Exibe os sites disponíveis do Mercado Livre"""
    print("\nSites disponíveis:")
    print("MLB - Brasil")
    print("MLA - Argentina")
    print("MLM - México")
    print("MCO - Colômbia")
    print("MLU - Uruguai")
    print("MLC - Chile")
    print("MPE - Peru")
    print("MLV - Venezuela")

def main():
    # Your credentials
    ACCESS_TOKEN = "APP_USR-6940700813779269-043021-e53bceb91d8b8160f740cd24326f2e21-340557736"
    REFRESH_TOKEN = "TG-6812caf93f6ca20001c4cefc-340557736"
    CLIENT_ID = "6940700813779269"  # Your APP_ID
    CLIENT_SECRET = "rN094Y2OsesaPFCJg7K9igQa7CYN4oyN"  # Your API KEY
    USER_ID = "340557736"
    
    # Initialize API client
    print("Inicializando conexão com a API do Mercado Livre...")
    ml_api = MercadoLivreAPI(ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET, USER_ID)
    
    # Test API connection by getting user info
    user_info = ml_api.get_user_info()
    if not user_info:
        print("Erro ao conectar com a API do Mercado Livre. Verifique suas credenciais.")
        return
    
    print(f"Conexão estabelecida! Bem-vindo, {user_info.get('nickname')}!")
    
    # Initialize exporter
    exporter = MercadoLivreExporter(ml_api)
    
    while True:
        display_menu()
        choice = input("\nEscolha uma opção (1-7): ")
        
        if choice == '1':
            search_products(exporter)
        elif choice == '2':
            get_item_details(exporter)
        elif choice == '3':
            export_user_items(exporter)
        elif choice == '4':
            export_categories(exporter)
        elif choice == '5':
            export_user_info(ml_api)
        elif choice == '6':
            export_simplified_data(ml_api)
        elif choice == '7':
            print("\nSaindo do programa. Obrigado por usar o Extrator de Dados do Mercado Livre!")
            sys.exit(0)
        else:
            print("\nOpção inválida. Por favor, escolha uma opção entre 1 e 7.")
        
        input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperação interrompida pelo usuário. Saindo...")
        sys.exit(0)
    except Exception as e:
        print(f"\nErro inesperado: {str(e)}")
        sys.exit(1) 