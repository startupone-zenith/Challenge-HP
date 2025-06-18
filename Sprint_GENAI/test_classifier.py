#!/usr/bin/env python3
"""
Test script for HP Cartridge Classifier
======================================

This script tests the classifier functionality without requiring actual API keys.
It uses the rule-based fallback classification.
"""

from sprint2_llm_classifier import (
    HPCartridgeClassifier,
    LLMClassifierEngine,
    CartuchoAnuncio,
    create_synthetic_dataset,
    save_annotation_guidelines
)
import json

def test_basic_functionality():
    """Test basic classifier functionality"""
    print("Testing HP Cartridge Classifier...\n")
    
    # Test 1: Initialize classifier
    print("1. Testing classifier initialization...")
    try:
        classifier = HPCartridgeClassifier()
        print("   ✓ Classifier initialized successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Test 2: Test risk factor extraction
    print("\n2. Testing risk factor extraction...")
    test_product = CartuchoAnuncio(
        titulo="Cartucho Compatível HP 667",
        marca="Compatível",
        modelo="667",
        preco=35.00,
        cor="preto",
        qualidade_descricao="Cartucho compatível com HP, produto similar de qualidade.",
        quantidade_reviews=5,
        avaliacao=3.0,
        quantidade_fotos=2,
        seller_name="Vendedor_Novo",
        seller_reputation="novo",
        listing_age_days=2
    )
    
    risk_factors = classifier.extract_risk_factors(test_product)
    print(f"   ✓ Found {len(risk_factors)} risk factors:")
    for factor in risk_factors:
        print(f"     - {factor}")
    
    # Test 3: Test LLM engine with fallback
    print("\n3. Testing LLM engine with rule-based fallback...")
    dummy_api_keys = {
        "openai": "dummy-key",
        "anthropic": "dummy-key",
        "google": "dummy-key"
    }
    
    engine = LLMClassifierEngine(dummy_api_keys)
    
    test_dict = test_product.model_dump()
    result = engine.classify_zero_shot(test_dict)
    
    print(f"   ✓ Classification: {result.classification}")
    print(f"   ✓ Confidence: {result.confidence:.2%}")
    print(f"   ✓ Reasoning: {result.reasoning}")
    
    # Test 4: Test synthetic dataset generation
    print("\n4. Testing synthetic dataset generation...")
    dataset = create_synthetic_dataset(n_samples=10)
    print(f"   ✓ Generated {len(dataset)} samples")
    
    authentic_count = sum(1 for d in dataset if d["ground_truth"] == "authentic")
    counterfeit_count = sum(1 for d in dataset if d["ground_truth"] == "counterfeit")
    
    print(f"   ✓ Authentic products: {authentic_count}")
    print(f"   ✓ Counterfeit products: {counterfeit_count}")
    
    # Test 5: Save annotation guidelines
    print("\n5. Testing annotation guidelines generation...")
    try:
        save_annotation_guidelines("test_guidelines.md")
        print("   ✓ Guidelines saved successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print("\n\nTesting Edge Cases...\n")
    
    classifier = HPCartridgeClassifier()
    engine = LLMClassifierEngine({"openai": "dummy", "anthropic": "dummy", "google": "dummy"})
    
    # Edge case 1: Authorized seller with low price
    edge_case_1 = {
        "titulo": "Cartucho HP 667 - Black Friday",
        "marca": "HP",
        "modelo": "667",
        "preco": 50.00,  # 44% discount
        "cor": "preto",
        "qualidade_descricao": "Promoção Black Friday! Cartucho HP original.",
        "quantidade_reviews": 200,
        "avaliacao": 4.5,
        "quantidade_fotos": 5,
        "seller_name": "Americanas",
        "seller_reputation": "platinum",
        "listing_age_days": 5
    }
    
    result1 = engine.classify_structured(edge_case_1, classifier)
    print("Edge Case 1: Authorized seller with deep discount")
    print(f"   Classification: {result1.classification}")
    print(f"   Confidence: {result1.confidence:.2%}")
    
    # Edge case 2: Unknown seller with normal price
    edge_case_2 = {
        "titulo": "Cartucho HP 667 Original",
        "marca": "HP",
        "modelo": "667",
        "preco": 85.00,
        "cor": "preto",
        "qualidade_descricao": "Cartucho HP original, genuíno, lacrado.",
        "quantidade_reviews": 15,
        "avaliacao": 4.0,
        "quantidade_fotos": 4,
        "seller_name": "LojaNova123",
        "seller_reputation": "silver",
        "listing_age_days": 30
    }
    
    result2 = engine.classify_structured(edge_case_2, classifier)
    print("\nEdge Case 2: Unknown seller with normal price")
    print(f"   Classification: {result2.classification}")
    print(f"   Confidence: {result2.confidence:.2%}")

def main():
    """Run all tests"""
    print("="*60)
    print("HP CARTRIDGE CLASSIFIER - TEST SUITE")
    print("="*60)
    
    # Run basic functionality tests
    test_basic_functionality()
    
    # Run edge case tests
    test_edge_cases()
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)

if __name__ == "__main__":
    main() 