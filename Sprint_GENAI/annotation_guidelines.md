
# HP Cartridge Classification Annotation Guidelines

## Overview
Classify each HP cartridge listing as either **AUTHENTIC** or **COUNTERFEIT/SUSPICIOUS**.

## Classification Criteria

### AUTHENTIC (Label: 1)
- Price within 40% of MSRP
- Sold by authorized resellers (HP Store, Kalunga, etc.)
- Contains "original", "genuíno" keywords
- Has 3+ high-quality photos
- Seller has platinum/gold reputation
- 50+ positive reviews

### COUNTERFEIT/SUSPICIOUS (Label: 0)
- Price >40% below MSRP
- Contains "compatível", "similar", "genérico"
- New/unknown seller
- Few photos (<3) or low quality
- No mention of warranty/guarantee
- Suspicious descriptions

## Edge Cases
- Authorized sellers with deep discounts: Usually AUTHENTIC
- Refurbished from authorized sellers: AUTHENTIC
- "Original" in title but suspicious price: Requires careful review

## Annotation Process
1. Review all product attributes
2. Check price against MSRP
3. Verify seller reputation
4. Analyze description quality
5. Assign confidence score (0.0-1.0)
