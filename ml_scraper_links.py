import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
import sys
import re

def install_required_packages():
    """Instala os pacotes necessários se não estiverem presentes"""
    packages = ['requests', 'beautifulsoup4', 'pandas', 'lxml']
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Instalando {package}...")
            import subprocess
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"{package} instalado com sucesso!")
            except Exception as e:
                print(f"Erro ao instalar {package}: {e}")
                return False
    return True

def extract_title_from_url(url):
    """Extrai um título aproximado da URL, caso não consiga encontrar no HTML"""
    # Remove parâmetros de tracking, etc.
    base_url = url.split('#')[0].split('?')[0]
    
    # Tenta extrair o nome do produto da URL
    parts = base_url.split('/')
    if len(parts) > 4:
        # Para URLs do tipo produto.mercadolivre.com.br/MLB-XXXXXXX-nome-do-produto
        if 'MLB-' in base_url:
            product_part = [p for p in parts if 'MLB-' in p]
            if product_part:
                title = product_part[0].split('-', 1)[1] if '-' in product_part[0] else ''
                title = title.replace('-', ' ').title()
                return title if title else "Produto Mercado Livre"
        
        # Para URLs do tipo www.mercadolivre.com.br/nome-do-produto/p/MLBXXXXX
        if '/p/' in base_url:
            product_index = parts.index('p') - 1 if 'p' in parts else -1
            if product_index >= 0 and product_index < len(parts):
                title = parts[product_index].replace('-', ' ').title()
                return title if title else "Produto Mercado Livre"
    
    return "Produto Mercado Livre"

def scrape_mercadolibre(search_term, site_code="MLB", max_results=10):
    """
    Extrai dados de produtos do Mercado Livre usando web scraping
    
    Args:
        search_term: Termo de busca
        site_code: Código do país (MLB - Brasil, MLA - Argentina, etc.)
        max_results: Número máximo de resultados
        
    Returns:
        Lista de dicionários com informações dos produtos
    """
    # Formatar o termo de busca para URL
    formatted_term = search_term.replace(" ", "-")
    
    # Construir URL conforme o país
    if site_code == "MLB":
        # Brasil
        base_url = f"https://lista.mercadolivre.com.br/{formatted_term}"
    else:
        # Outros países
        domain = site_code.replace("ML", "").lower()
        base_url = f"https://listado.mercadolibre.com.{domain}/{formatted_term}"
    
    print(f"URL de busca: {base_url}")
    
    # Configurar headers para simular um navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Lista para armazenar resultados
    products = []
    
    # Controle da paginação
    page = 1
    products_found = 0
    
    try:
        while products_found < max_results:
            # URL da página atual
            if page == 1:
                url = base_url
            else:
                # Formato de URL para páginas adicionais
                url = f"{base_url}_Desde_{(page-1)*50+1}"
            
            print(f"Acessando página {page}: {url}")
            
            # Fazer a requisição
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"Erro ao acessar a página. Status code: {response.status_code}")
                break
            
            # Parsear o HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Abordagem simplificada: extrair todos os links da página
            all_links = []
            product_regex = re.compile(r'(/MLB-\d+|/p/MLB\d+|produto\.mercadolivre\.com\.br/MLB-\d+)')
            
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if ('mercadolivre.com.br' in href and 
                    not 'publicidade.mercadolivre' in href and 
                    (product_regex.search(href) or '/p/' in href)):
                    all_links.append(href)
            
            # Remover links duplicados e manter a ordem
            product_links = []
            for link in all_links:
                if link not in product_links:
                    product_links.append(link)
            
            print(f"Encontrados {len(product_links)} links de produtos na página {page}")
            
            if not product_links:
                print("Não foram encontrados links de produtos nesta página")
                break
            
            # Processar cada link
            for link in product_links:
                if products_found >= max_results:
                    break
                
                try:
                    # Extrair título da URL
                    title = extract_title_from_url(link)
                    
                    # Adicionar à lista de produtos
                    products.append({
                        'titulo': title,
                        'link': link,
                        'preco': "Verificar no site",
                        'vendedor': "Verificar no site",
                        'site': site_code
                    })
                    
                    products_found += 1
                    print(f"[{products_found}/{max_results}] Produto coletado: {title[:50]}..." + 
                          f"\n   Link: {link}")
                    
                except Exception as e:
                    print(f"Erro ao processar link: {link} - {str(e)}")
            
            # Se já coletamos produtos suficientes ou não encontramos mais produtos, sair do loop
            if products_found >= max_results:
                print("Atingido o número máximo de produtos solicitados.")
                break
                
            # Verificar se há mais páginas
            next_button = soup.find('a', {'title': 'Seguinte'}) or soup.find('a', {'class': 'andes-pagination__link'})
            if not next_button:
                print("Não há mais páginas disponíveis.")
                break
            
            # Ir para a próxima página
            page += 1
            
            # Pausa para evitar bloqueio
            time.sleep(1.5)
    
    except Exception as e:
        print(f"Erro durante a coleta: {str(e)}")
    
    print(f"Total de produtos coletados: {len(products)}")
    return products

def save_to_csv(products, search_term, site_code):
    """Salva os produtos em um arquivo CSV"""
    if not products:
        print("Não há produtos para salvar")
        return None
    
    # Criar diretório se não existir
    export_dir = "ml_data_exports"
    os.makedirs(export_dir, exist_ok=True)
    
    # Nome do arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    search_clean = search_term.replace(" ", "_").lower()
    filename = f"{export_dir}/ml_links_{search_clean}_{site_code}_{timestamp}.csv"
    
    # Criar DataFrame e salvar
    df = pd.DataFrame(products)
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"Dados salvos em: {filename}")
    return filename

def display_sample_data(products, num_samples=3):
    """Mostra uma amostra dos dados coletados"""
    print("\n=== AMOSTRA DOS DADOS COLETADOS ===")
    for i, product in enumerate(products[:num_samples], 1):
        print(f"\nProduto {i}:")
        print(f"Título: {product['titulo']}")
        print(f"Link: {product['link']}")
        print(f"Preço: {product['preco']}")
        print(f"Vendedor: {product['vendedor']}")
    print("\n" + "="*40)

if __name__ == "__main__":
    print("===== COLETOR DE LINKS DO MERCADO LIVRE =====")
    
    # Verificar e instalar dependências
    if not install_required_packages():
        print("Não foi possível instalar os pacotes necessários. Saindo...")
        sys.exit(1)
    
    # Obter parâmetros do usuário
    search_term = input("Digite o termo de busca: ")
    if not search_term:
        print("Termo de busca é obrigatório!")
        sys.exit(1)
    
    # Obter código do site
    print("\nSites disponíveis:")
    print("MLB - Brasil")
    print("MLA - Argentina")
    print("MLM - México")
    print("MCO - Colômbia")
    print("MLU - Uruguai")
    print("MLC - Chile")
    site_code = input("Código do site (padrão: MLB): ").upper() or "MLB"
    
    # Obter número máximo de resultados
    try:
        max_results = int(input("Número máximo de resultados (padrão: 10): ") or "10")
    except ValueError:
        print("Valor inválido. Usando o padrão: 10")
        max_results = 10
    
    print(f"\nIniciando coleta de até {max_results} produtos...\n")
    
    # Executar o scraping
    products = scrape_mercadolibre(search_term, site_code, max_results)
    
    # Mostrar amostra dos dados
    if products:
        display_sample_data(products)
        
        # Salvar resultados
        csv_path = save_to_csv(products, search_term, site_code)
        print(f"\nDados completos salvos em: {csv_path}")
    else:
        print("Nenhum produto encontrado para exportar.")
    
    print("\n===== COLETA FINALIZADA =====") 