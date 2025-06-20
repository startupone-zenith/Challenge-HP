
# Diretrizes de Anotação para Classificação de Cartuchos HP

## Visão Geral
Classifique cada anúncio de cartucho HP como **AUTÊNTICO** ou **FALSIFICADO/SUSPEITO**.

## Critérios de Classificação

### AUTÊNTICO (Rótulo: 1)
- Preço dentro de 40% do MSRP
- Vendido por revendedores autorizados (HP Store, Kalunga, etc.)
- Contém palavras-chave "original", "genuíno"
- Possui 3+ fotos de alta qualidade
- Vendedor com reputação platina/ouro
- 50+ avaliações positivas

### FALSIFICADO/SUSPEITO (Rótulo: 0)
- Preço >40% abaixo do MSRP
- Contém "compatível", "similar", "genérico"
- Vendedor novo/desconhecido
- Poucas fotos (<3) ou de baixa qualidade
- Nenhuma menção de garantia
- Descrições suspeitas

## Casos de Borda
- Revendedores autorizados com grandes descontos: Geralmente AUTÊNTICO
- Remanufaturados de vendedores autorizados: AUTÊNTICO
- "Original" no título, mas preço suspeito: Requer análise cuidadosa

## Processo de Anotação
1. Revise todos os atributos do produto
2. Verifique o preço em relação ao MSRP
3. Verifique a reputação do vendedor
4. Analise a qualidade da descrição
5. Atribua um score de confiança (0.0-1.0)
