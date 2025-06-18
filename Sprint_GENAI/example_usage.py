#!/usr/bin/env python3
"""
Example usage of the HP Cartridge Counterfeit Detection System
==============================================================

This script demonstrates how to use the classifier for individual products
without running the full evaluation pipeline.
"""

from sprint2_llm_classifier import (
    HPCartridgeClassifier, 
    LLMClassifierEngine, 
    CartuchoAnuncio
)
import json

def classify_single_product():
    """Example: Classify a single product"""
    print("=== Single Product Classification Example ===\n")
    
    # Initialize classifier
    classifier = HPCartridgeClassifier()
    
    # Load API keys from config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    api_keys = {
        "openai": config.get("openai_api_key"),
        "anthropic": config.get("anthropic_api_key"),
        "google": config.get("google_api_key")
    }
    
    # Initialize LLM engine
    engine = LLMClassifierEngine(api_keys)
    
    # Example product data (suspicious)
    suspicious_product = {
        "titulo": "Cartucho Compatível HP 667 Preto Barato",
        "marca": "Compatível",
        "modelo": "667",
        "preco": 35.00,  # Very low price
        "cor": "preto",
        "qualidade_descricao": "Cartucho compatível com HP 667. Produto similar de ótima qualidade. Envio imediato!",
        "quantidade_reviews": 5,
        "avaliacao": 3.2,
        "quantidade_fotos": 2,
        "seller_name": "Vendedor_12345",
        "seller_reputation": "novo",
        "listing_age_days": 3
    }
    
    # Classify using structured approach
    result = engine.classify_structured(suspicious_product, classifier)
    
    print(f"Product: {suspicious_product['titulo']}")
    print(f"Price: R$ {suspicious_product['preco']}")
    print(f"Seller: {suspicious_product['seller_name']}")
    print("-" * 50)
    print(f"Classification: {result.classification.upper()}")
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Risk Factors:")
    for factor in result.risk_factors:
        print(f"  - {factor}")
    print("\n")

def classify_batch_products():
    """Example: Classify multiple products in batch"""
    print("=== Batch Classification Example ===\n")
    
    # Initialize components
    classifier = HPCartridgeClassifier()
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    api_keys = {
        "openai": config.get("openai_api_key"),
        "anthropic": config.get("anthropic_api_key"),
        "google": config.get("google_api_key")
    }
    
    engine = LLMClassifierEngine(api_keys)
    
    # Example batch of products
    products = [
        {
            "titulo": "Cartucho HP 667 Original Lacrado",
            "marca": "HP",
            "modelo": "667",
            "preco": 85.00,
            "cor": "preto",
            "qualidade_descricao": "Cartucho HP original, lacrado com nota fiscal.",
            "quantidade_reviews": 150,
            "avaliacao": 4.8,
            "quantidade_fotos": 6,
            "seller_name": "HP Store Oficial",
            "seller_reputation": "platinum",
            "listing_age_days": 90
        },
        {
            "titulo": "Kit Cartucho Genérico 667",
            "marca": "Genérico",
            "modelo": "667",
            "preco": 25.00,
            "cor": "preto",
            "qualidade_descricao": "Kit com 3 cartuchos genéricos compatíveis.",
            "quantidade_reviews": 2,
            "avaliacao": 2.5,
            "quantidade_fotos": 1,
            "seller_name": "ImportadoraXYZ",
            "seller_reputation": "bronze",
            "listing_age_days": 5
        }
    ]
    
    # Classify each product
    results = []
    for product in products:
        result = engine.classify_structured(product, classifier)
        results.append({
            "title": product["titulo"],
            "classification": result.classification,
            "confidence": result.confidence,
            "risk_level": "HIGH" if result.confidence > 0.9 and result.classification == "counterfeit" else "MEDIUM"
        })
    
    # Display results
    print("Batch Classification Results:")
    print("-" * 80)
    for r in results:
        status = "⚠️ " if r["classification"] == "counterfeit" else "✅"
        print(f"{status} {r['title']}")
        print(f"   Classification: {r['classification'].upper()}")
        print(f"   Confidence: {r['confidence']:.1%}")
        print(f"   Risk Level: {r['risk_level']}")
        print()

def demonstrate_risk_factors():
    """Example: Extract and analyze risk factors"""
    print("=== Risk Factor Analysis Example ===\n")
    
    classifier = HPCartridgeClassifier()
    
    # Product with multiple risk factors
    risky_product = CartuchoAnuncio(
        titulo="Cartucho HP 667 Super Barato",
        marca="HP",
        modelo="667",
        preco=30.00,  # 67% below MSRP
        cor="preto",
        qualidade_descricao="Cartucho barato compatível com impressoras HP.",
        quantidade_reviews=1,
        avaliacao=3.0,
        quantidade_fotos=1,
        seller_name="NovoVendedor123",
        seller_reputation="novo",
        listing_age_days=1
    )
    
    # Extract risk factors
    risk_factors = classifier.extract_risk_factors(risky_product)
    
    print(f"Product: {risky_product.titulo}")
    print(f"Identified Risk Factors: {len(risk_factors)}")
    print("-" * 50)
    
    for i, factor in enumerate(risk_factors, 1):
        print(f"{i}. {factor}")
    
    # Calculate risk score
    risk_score = len(risk_factors) / 5.0  # Normalize to 0-1
    risk_level = "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.3 else "LOW"
    
    print(f"\nOverall Risk Score: {risk_score:.2f}")
    print(f"Risk Level: {risk_level}")

def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("HP CARTRIDGE COUNTERFEIT DETECTION - USAGE EXAMPLES")
    print("="*80 + "\n")
    
    try:
        # Example 1: Single product classification
        classify_single_product()
        
        # Example 2: Batch classification
        classify_batch_products()
        
        # Example 3: Risk factor analysis
        demonstrate_risk_factors()
        
    except FileNotFoundError:
        print("ERROR: config.json not found. Please create it with your API keys.")
        print("See config.json.example for the required format.")
    except Exception as e:
        print(f"ERROR: {e}")
        print("Make sure you have configured your API keys in config.json")

if __name__ == "__main__":
    main() 