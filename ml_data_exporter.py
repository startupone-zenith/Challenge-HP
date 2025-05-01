import csv
import json
import os
from datetime import datetime
from mercadolivre_extractor import MercadoLivreAPI

class MercadoLivreExporter:
    def __init__(self, ml_api):
        self.ml_api = ml_api
        self.output_dir = "ml_data_exports"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def _save_to_csv(self, data, filename, headers):
        """Save data to a CSV file"""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print(f"Data exported successfully to {filepath}")
        return filepath
    
    def _save_to_json(self, data, filename):
        """Save raw data to a JSON file for full data preservation"""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, ensure_ascii=False, indent=2)
        print(f"Raw data exported to {filepath}")
        return filepath
    
    def export_search_results(self, query=None, seller_id=None, category=None, limit=50, site_id="MLB"):
        """Export search results to CSV and JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_term = query or seller_id or category or "all"
        
        # Get search results
        results = self.ml_api.search_items(query, seller_id, category, limit, site_id=site_id)
        if not results or not results.get('results'):
            print("No results found.")
            return None, None
        
        # Save raw data to JSON
        json_filename = f"search_{search_term}_{site_id}_{timestamp}.json"
        json_path = self._save_to_json(results, json_filename)
        
        # Process data for CSV
        csv_data = []
        for item in results.get('results', []):
            csv_data.append({
                'id': item.get('id'),
                'title': item.get('title'),
                'price': item.get('price'),
                'currency': item.get('currency_id'),
                'available_quantity': item.get('available_quantity'),
                'condition': item.get('condition'),
                'listing_type': item.get('listing_type_id'),
                'permalink': item.get('permalink'),
                'seller_id': item.get('seller', {}).get('id'),
                'category_id': item.get('category_id')
            })
        
        # Save processed data to CSV
        headers = ['id', 'title', 'price', 'currency', 'available_quantity', 
                   'condition', 'listing_type', 'permalink', 'seller_id', 'category_id']
        csv_filename = f"search_{search_term}_{site_id}_{timestamp}.csv"
        csv_path = self._save_to_csv(csv_data, csv_filename, headers)
        
        return csv_path, json_path
    
    def export_item_details(self, item_ids):
        """Export detailed item information to CSV and JSON"""
        if not isinstance(item_ids, list):
            item_ids = [item_ids]
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get item details
        details = self.ml_api.get_item_details(item_ids)
        if not details:
            print("No item details found.")
            return None, None
        
        # Save raw data to JSON
        json_filename = f"items_details_{timestamp}.json"
        json_path = self._save_to_json(details, json_filename)
        
        # Process data for CSV
        csv_data = []
        for item in details:
            if item.get('code') == 200 and item.get('body'):
                body = item.get('body', {})
                
                # Extract main images
                pictures = body.get('pictures', [])
                main_picture = pictures[0].get('url') if pictures else ""
                
                # Extract main attributes
                attributes = body.get('attributes', [])
                brand = next((attr.get('value_name') for attr in attributes if attr.get('id') == 'BRAND'), "")
                model = next((attr.get('value_name') for attr in attributes if attr.get('id') == 'MODEL'), "")
                
                csv_data.append({
                    'id': body.get('id'),
                    'title': body.get('title'),
                    'subtitle': body.get('subtitle', ''),
                    'price': body.get('price'),
                    'original_price': body.get('original_price', body.get('price')),
                    'currency': body.get('currency_id'),
                    'available_quantity': body.get('available_quantity'),
                    'sold_quantity': body.get('sold_quantity'),
                    'condition': body.get('condition'),
                    'listing_type': body.get('listing_type_id'),
                    'category_id': body.get('category_id'),
                    'official_store_id': body.get('official_store_id', ''),
                    'permalink': body.get('permalink'),
                    'seller_id': body.get('seller_id'),
                    'main_picture': main_picture,
                    'brand': brand,
                    'model': model,
                    'status': body.get('status'),
                    'date_created': body.get('date_created'),
                    'last_updated': body.get('last_updated')
                })
        
        # Save processed data to CSV
        headers = ['id', 'title', 'subtitle', 'price', 'original_price', 'currency', 
                   'available_quantity', 'sold_quantity', 'condition', 'listing_type', 
                   'category_id', 'official_store_id', 'permalink', 'seller_id', 
                   'main_picture', 'brand', 'model', 'status', 'date_created', 'last_updated']
        csv_filename = f"items_details_{timestamp}.csv"
        csv_path = self._save_to_csv(csv_data, csv_filename, headers)
        
        return csv_path, json_path
    
    def export_user_items(self, user_id=None, limit=50):
        """Export items from a specific user"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user = user_id or self.ml_api.user_id
        
        # Get user's items
        user_items_data = self.ml_api.get_user_items(user, limit)
        if not user_items_data or not user_items_data.get('results'):
            print("No user items found.")
            return None, None
            
        # Save raw results to JSON
        json_filename = f"user_items_{user}_{timestamp}.json"
        json_path = self._save_to_json(user_items_data, json_filename)
        
        # For CSV we need to get details of each item
        item_ids = user_items_data.get('results', [])
        
        # Process in batches of 20 (API limit for multiget)
        all_item_details = []
        for i in range(0, len(item_ids), 20):
            batch = item_ids[i:i+20]
            details = self.ml_api.get_item_details(batch)
            if details:
                all_item_details.extend(details)
        
        # Process data for CSV
        csv_data = []
        for item in all_item_details:
            if item.get('code') == 200 and item.get('body'):
                body = item.get('body', {})
                csv_data.append({
                    'id': body.get('id'),
                    'title': body.get('title'),
                    'price': body.get('price'),
                    'currency': body.get('currency_id'),
                    'available_quantity': body.get('available_quantity'),
                    'sold_quantity': body.get('sold_quantity', 0),
                    'condition': body.get('condition'),
                    'status': body.get('status'),
                    'permalink': body.get('permalink'),
                    'date_created': body.get('date_created'),
                    'last_updated': body.get('last_updated')
                })
        
        # Save processed data to CSV
        headers = ['id', 'title', 'price', 'currency', 'available_quantity', 
                  'sold_quantity', 'condition', 'status', 'permalink', 
                  'date_created', 'last_updated']
        csv_filename = f"user_items_{user}_{timestamp}.csv"
        csv_path = self._save_to_csv(csv_data, csv_filename, headers)
        
        return csv_path, json_path
    
    def export_categories(self, site_id="MLB"):
        """Export categories to CSV"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get categories
        categories = self.ml_api.get_categories(site_id)
        if not categories:
            print("No categories found.")
            return None, None
        
        # Save raw data to JSON
        json_filename = f"categories_{site_id}_{timestamp}.json"
        json_path = self._save_to_json(categories, json_filename)
        
        # Process data for CSV
        csv_data = []
        for category in categories:
            csv_data.append({
                'id': category.get('id'),
                'name': category.get('name'),
                'total_items_in_this_category': category.get('total_items_in_this_category', 0)
            })
        
        # Save processed data to CSV
        headers = ['id', 'name', 'total_items_in_this_category']
        csv_filename = f"categories_{site_id}_{timestamp}.csv"
        csv_path = self._save_to_csv(csv_data, csv_filename, headers)
        
        return csv_path, json_path

    def export_simple_data(self, query=None, seller_id=None, category=None, limit=50, site_id="MLB"):
        """Exporta apenas as informações básicas: link da página, nome do produto e vendedor"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_term = query or seller_id or category or "all"
        
        # Criar arquivo CSV vazio inicialmente - isso nos permite retornar algo mesmo se a busca falhar
        headers = ['link', 'nome_produto', 'vendedor']
        search_term_slug = search_term.replace(" ", "_").lower()
        csv_filename = f"simple_{search_term_slug}_{site_id}_{timestamp}.csv"
        
        # Cria diretório de output se não existir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Caminho completo do arquivo
        filepath = os.path.join(self.output_dir, csv_filename)
        
        # Cria o arquivo para garantir que tenhamos pelo menos um CSV (mesmo vazio)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
        except Exception as e:
            print(f"Erro ao criar arquivo CSV inicial: {str(e)}")
        
        print(f"Buscando produtos com termo '{search_term}' no site {site_id}...")
        
        # Processo de busca em etapas, tentando diferentes abordagens
        simple_data = []
        
        # 1. Para query de busca, tenta primeiro a API direta
        if query and isinstance(query, str) and len(query) > 0:
            print("Tentando busca via API principal...")
            
            # Tenta a busca via API
            try_api = True
            attempt_count = 0
            max_attempts = 2
            
            while try_api and attempt_count < max_attempts:
                attempt_count += 1
                
                # Tenta a busca via API
                try:
                    results = self.ml_api.search_items(query, seller_id, category, limit, site_id=site_id)
                    
                    # Tenta extrair produtos diretos da resposta
                    if results and isinstance(results, dict) and 'results' in results:
                        results_list = results.get('results', [])
                        
                        # Verificar se temos produtos válidos
                        valid_count = 0
                        for item in results_list:
                            if isinstance(item, dict) and 'id' in item and 'title' in item and 'permalink' in item:
                                valid_count += 1
                        
                        if valid_count > 0:
                            print(f"API retornou {valid_count} produtos válidos.")
                            for item in results_list:
                                # Extrai dados básicos do item
                                if isinstance(item, dict) and 'id' in item and 'title' in item:
                                    simple_data.append({
                                        'link': item.get('permalink', f"https://produto.mercadolivre.com.br/{item.get('id', '')}"),
                                        'nome_produto': item.get('title', 'Sem título'),
                                        'vendedor': str(item.get('seller', {}).get('id', '')) if isinstance(item.get('seller'), dict) else str(item.get('seller_id', ''))
                                    })
                            try_api = False  # Conseguimos resultados, não precisa continuar
                        else:
                            print("API retornou resultados, mas sem produtos válidos.")
                    else:
                        print("API não retornou resultados válidos.")
                except Exception as e:
                    print(f"Erro na busca via API: {str(e)}")
                
                if try_api and attempt_count < max_attempts:
                    print(f"Tentativa {attempt_count} falhou. Tentando novamente...")
        
        # 2. Se não tiver dados da API, tenta web scraping
        if not simple_data and query and isinstance(query, str) and len(query) > 0:
            print("API falhou em retornar produtos. Tentando web scraping...")
            
            try:
                # Importação dinâmica para não depender do BeautifulSoup se não for necessário
                from ml_web_scraper import MercadoLivreWebScraper
                
                scraper = MercadoLivreWebScraper(output_dir=self.output_dir)
                products = scraper.search_items(query, site_id, limit)
                
                if products and len(products) > 0:
                    print(f"Web scraping encontrou {len(products)} produtos.")
                    
                    # Processar os produtos para garantir que só temos os campos necessários
                    web_data = []
                    for product in products:
                        # Extrai apenas os campos necessários
                        web_data.append({
                            'link': product.get('link', ''),
                            'nome_produto': product.get('nome_produto', 'Sem título'),
                            'vendedor': product.get('vendedor', 'Vendedor Mercado Livre')
                        })
                    
                    simple_data = web_data
                    
                    # Salvar os dados obtidos por web scraping
                    try:
                        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=headers)
                            writer.writeheader()
                            writer.writerows(simple_data)
                        
                        print(f"Dados de web scraping exportados com sucesso para {filepath}")
                        print(f"Total de {len(simple_data)} produtos exportados.")
                        
                        return filepath
                    except Exception as e:
                        print(f"Erro ao salvar arquivo CSV do web scraping: {str(e)}")
                else:
                    print("Web scraping não encontrou produtos.")
            except ImportError:
                print("Biblioteca BeautifulSoup não está instalada. Não é possível fazer web scraping.")
            except Exception as e:
                print(f"Erro durante web scraping: {str(e)}")
        
        # 3. Se ainda não tiver dados, tenta o método tradicional com multiget
        if not simple_data:
            print("Tentando método tradicional com multiget...")
            
            # Obter resultados brutos da API para debug
            results = self.ml_api.search_items(query, seller_id, category, limit, site_id=site_id)
            
            # Informações de debug
            print(f"Tipo de resposta recebida: {type(results).__name__}")
            
            if not results:
                print("Nenhum resultado encontrado.")
                return filepath  # Retornamos o caminho do arquivo mesmo vazio
            
            # Extrair IDs dos produtos da busca
            item_ids = []
            
            # Verificar a estrutura da resposta para extrair IDs
            if isinstance(results, dict):
                if 'results' in results:
                    for item in results.get('results', []):
                        if isinstance(item, dict) and 'id' in item:
                            item_ids.append(item.get('id'))
                elif 'content' in results:
                    for item in results.get('content', []):
                        if isinstance(item, dict) and 'id' in item:
                            item_ids.append(item.get('id'))
            elif isinstance(results, list):
                for item in results:
                    if isinstance(item, dict) and 'id' in item:
                        item_ids.append(item.get('id'))
            
            print(f"Extraídos {len(item_ids)} IDs de produtos.")
            
            if not item_ids:
                print("Não foi possível encontrar IDs de produtos nos resultados.")
                return filepath  # Retornamos o caminho do arquivo mesmo vazio
            
            # Processar IDs em lotes de 20 (limite da API para multiget)
            
            # Processar em lotes de no máximo 20 IDs (limite da API)
            for i in range(0, len(item_ids), 20):
                batch = item_ids[i:i+20]
                print(f"Buscando detalhes para o lote {i//20 + 1} com {len(batch)} produtos...")
                
                # Usar o endpoint multiget para obter detalhes de até 20 produtos ao mesmo tempo
                details = self.ml_api.get_item_details(batch)
                
                if not details:
                    print(f"Falha ao obter detalhes para o lote {i//20 + 1}.")
                    continue
                
                # Processar os detalhes retornados
                for item in details:
                    if item.get('code') == 200 and 'body' in item:
                        body = item.get('body', {})
                        
                        # Criar entry com as informações completas
                        simple_data.append({
                            'link': body.get('permalink', f"https://produto.mercadolivre.com.br/{body.get('id', '')}"),
                            'nome_produto': body.get('title', body.get('id', 'Sem título')),
                            'vendedor': str(body.get('seller_id', ''))
                        })
        
        print(f"Total de itens obtidos: {len(simple_data)}")
        
        # Mesmo se não tivermos dados válidos, retornamos o arquivo (pode estar vazio)
        if simple_data:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=headers)
                    writer.writeheader()
                    # Garantir que só escrevemos os campos necessários
                    filtered_data = []
                    for item in simple_data:
                        filtered_data.append({
                            'link': item.get('link', ''),
                            'nome_produto': item.get('nome_produto', 'Sem título'),
                            'vendedor': item.get('vendedor', 'Vendedor Mercado Livre')
                        })
                    writer.writerows(filtered_data)
                
                print(f"Dados simplificados exportados com sucesso para {filepath}")
                print(f"Total de {len(simple_data)} produtos exportados.")
            except Exception as e:
                print(f"Erro ao salvar arquivo CSV: {str(e)}")
        else:
            print("Não foi possível obter dados válidos dos produtos.")
        
        return filepath

if __name__ == "__main__":
    # Replace with your actual credentials
    ACCESS_TOKEN = "APP_USR-6940700813779269-043021-e53bceb91d8b8160f740cd24326f2e21-340557736"
    REFRESH_TOKEN = "TG-6812caf93f6ca20001c4cefc-340557736"
    CLIENT_ID = "6940700813779269"  # Your APP_ID
    CLIENT_SECRET = "rN094Y2OsesaPFCJg7K9igQa7CYN4oyN"  # Your API KEY
    USER_ID = "340557736"
    
    # Initialize the API client
    ml_api = MercadoLivreAPI(ACCESS_TOKEN, REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET, USER_ID)
    
    # Initialize the exporter
    exporter = MercadoLivreExporter(ml_api)
    
    # Example 1: Export search results for a query
    print("\nExporting search results for 'smartphone'...")
    exporter.export_search_results(query="smartphone", limit=20)
    
    # Example 2: Export items from your account
    print("\nExporting your items...")
    exporter.export_user_items(limit=50)
    
    # Example 3: Export categories
    print("\nExporting categories...")
    exporter.export_categories()
    
    # Example 4: Export simple data
    print("\nExporting simple data...")
    exporter.export_simple_data(query="smartphone", limit=20)
    
    print("\nAll exports completed!") 