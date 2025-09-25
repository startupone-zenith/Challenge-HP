#!/usr/bin/env python3
"""
Script para configuração automática do NLTK
HP Challenge Sprint - Sistema de Detecção de Falsificações
"""

import nltk
import ssl
import os

def setup_nltk():
    """
    Configura o NLTK baixando todos os recursos necessários
    para análise de texto em português e inglês
    """
    print("🔧 Configurando NLTK...")
    
    # Configurar SSL se necessário (alguns ambientes têm problemas)
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    
    # Lista de recursos necessários
    resources = [
        'punkt',           # Tokenização de sentenças
        'punkt_tab',       # Tokenização moderna
        'stopwords',       # Palavras de parada
        'wordnet',         # WordNet para análise semântica
        'omw-1.4',         # Open Multilingual Wordnet
        'vader_lexicon',   # Análise de sentimentos
        'averaged_perceptron_tagger',  # POS tagging
        'maxent_ne_chunker',  # Named Entity Recognition
        'words',           # Corpus de palavras
        'brown',           # Brown corpus
        'reuters',         # Reuters corpus
        'gutenberg',       # Gutenberg corpus
    ]
    
    print(f"📦 Baixando {len(resources)} recursos do NLTK...")
    
    success_count = 0
    for resource in resources:
        try:
            print(f"   📥 Baixando {resource}...")
            nltk.download(resource, quiet=True)
            success_count += 1
            print(f"   ✅ {resource} baixado com sucesso")
        except Exception as e:
            print(f"   ⚠️ Erro ao baixar {resource}: {str(e)}")
    
    print(f"\n🎉 Configuração concluída! {success_count}/{len(resources)} recursos baixados")
    
    # Testar funcionalidades básicas
    print("\n🧪 Testando funcionalidades...")
    
    try:
        # Teste de tokenização
        from nltk.tokenize import word_tokenize, sent_tokenize
        texto_teste = "Cartucho HP 664 original. Preço promocional!"
        tokens = word_tokenize(texto_teste, language='portuguese')
        print(f"   ✅ Tokenização: {len(tokens)} tokens extraídos")
        
        # Teste de stopwords
        from nltk.corpus import stopwords
        stop_words_pt = stopwords.words('portuguese')
        stop_words_en = stopwords.words('english')
        print(f"   ✅ Stopwords: {len(stop_words_pt)} em português, {len(stop_words_en)} em inglês")
        
        # Teste de análise de sentimentos
        from nltk.sentiment import SentimentIntensityAnalyzer
        sia = SentimentIntensityAnalyzer()
        sentiment = sia.polarity_scores("This product is amazing!")
        print(f"   ✅ Análise de sentimentos: {sentiment}")
        
        print("\n🎯 NLTK configurado e testado com sucesso!")
        print("   Recursos disponíveis para:")
        print("   • Tokenização de texto em português/inglês")
        print("   • Remoção de stopwords")
        print("   • Análise de sentimentos")
        print("   • Extração de N-grams")
        print("   • Análise semântica")
        
    except Exception as e:
        print(f"   ❌ Erro nos testes: {str(e)}")
        print("   Alguns recursos podem não estar disponíveis")
    
    return success_count == len(resources)

def show_nltk_info():
    """
    Mostra informações sobre a instalação do NLTK
    """
    print("\n📊 Informações do NLTK:")
    print(f"   Versão: {nltk.__version__}")
    
    # Verificar diretório de dados
    data_path = nltk.data.find('')
    print(f"   Diretório de dados: {data_path}")
    
    # Listar recursos baixados
    try:
        from nltk.data import find
        resources_found = []
        test_resources = ['corpora/stopwords', 'tokenizers/punkt', 'vader_lexicon']
        
        for resource in test_resources:
            try:
                find(resource)
                resources_found.append(resource)
            except:
                pass
        
        print(f"   Recursos encontrados: {len(resources_found)}")
        for resource in resources_found:
            print(f"     • {resource}")
            
    except Exception as e:
        print(f"   Erro ao verificar recursos: {str(e)}")

if __name__ == "__main__":
    print("🚀 HP Challenge Sprint - Configuração do NLTK")
    print("=" * 50)
    
    # Configurar NLTK
    success = setup_nltk()
    
    # Mostrar informações
    show_nltk_info()
    
    if success:
        print("\n✅ Configuração completa! O NLTK está pronto para uso.")
    else:
        print("\n⚠️ Configuração parcial. Alguns recursos podem não estar disponíveis.")
    
    print("\n💡 Para usar no código:")
    print("   import nltk")
    print("   from nltk.corpus import stopwords")
    print("   from nltk.tokenize import word_tokenize")
    print("\n🔗 Documentação: https://www.nltk.org/") 