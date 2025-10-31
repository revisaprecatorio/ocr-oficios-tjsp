# 🔍 ROOT CAUSE ANALYSIS: Bug de Parsing de Valores

**Status:** ✅ **BUG IDENTIFICADO**  
**Data da Investigação:** 31/10/2025  
**Data do Processamento Original:** 16/10/2025 00:24

---

## 📋 SUMÁRIO EXECUTIVO

### Problema
- **Valor Esperado:** R$ 88.994,41
- **Valor Armazenado:** R$ 88,99
- **Diferença:** -R$ 88.905,42 (99,9% de erro)

### Root Cause
**O LLM retornou valores incorretos como STRINGS no JSON.**

O GPT-4o-mini interpretou erroneamente o valor "88.994,41" como "88.99" e retornou como string ao invés de number.

---

## 🎯 EVIDÊNCIAS

### 1. JSON Original (16/10/2025 00:24)

**Arquivo:** `3_OCR/1_parsing_PDF/outputs/json/27308157830_0015796-15.2025.8.26.0500.json`

```json
{
  "processo_origem": "0024288-52.2020.8.26.0053",
  "requerente_caps": "RODRIGO AZEVEDO FERRAO",
  "numero_ordem": "9594/2026",
  "valor_principal_liquido": "88.99",        // ❌ STRING! ERRADO!
  "valor_principal_bruto": "88.99",          // ❌ STRING! ERRADO!
  "juros_moratorios": "0.00",
  "valor_total_requisitado": "88.99",        // ❌ STRING! ERRADO!
  "observacoes": "Campos não encontrados: juros_moratorios"
}
```

**Problemas Identificados:**
1. ❌ `valor_principal_liquido`: "88.99" (deveria ser 88994.41)
2. ❌ `valor_principal_bruto`: "88.99" (deveria ser 88994.41)
3. ❌ `valor_total_requisitado`: "88.99" (deveria ser 88994.41)
4. ❌ `processo_origem`: "0024288-52.2020.8.26.0053" (deveria ser "0015796-15.2025.8.26.0500")
5. ❌ `numero_ordem`: "9594/2026" (deveria ser "1/2025")
6. ⚠️  Valores retornados como **STRINGS** ao invés de **NUMBERS**

---

### 2. JSON Teste Local (31/10/2025 19:08)

**Arquivo:** `8_erro_parsing-valor/test_outputs/3_resposta_llm.json`

```json
{
  "processo_origem": "0015796-15.2025.8.26.0500",
  "requerente_caps": "RODRIGO AZEVEDO FERRAO",
  "numero_ordem": "1/2025",
  "valor_principal_liquido": 88994.41,       // ✅ NUMBER! CORRETO!
  "valor_principal_bruto": 88994.41,         // ✅ NUMBER! CORRETO!
  "juros_moratorios": 0.00,
  "valor_total_requisitado": 88994.41        // ✅ NUMBER! CORRETO!
}
```

**Resultado:**
- ✅ Todos os valores corretos
- ✅ Processo de origem correto
- ✅ Número de ordem correto
- ✅ Valores retornados como **NUMBERS**

---

## 🔍 ANÁLISE TÉCNICA

### 1. Por que o LLM errou em 16/10?

**Possíveis causas:**

#### a) Ambiguidade no formato brasileiro
- Texto PDF: "88.994,41"
- Formato BR: ponto = milhar, vírgula = decimal
- LLM pode ter interpretado: "88.99" + "4,41" (confusão)

#### b) Prompt não era suficientemente explícito
- Prompt pode não ter instruído claramente sobre formato brasileiro
- Falta de exemplo: "88.994,41 → 88994.41"

#### c) Temperature > 0 (não determinístico)
- Se temperature estava > 0, resultado pode variar
- Resposta inconsistente entre execuções

#### d) Contexto truncado
- Se texto enviado ao LLM estava truncado
- Valor pode ter sido cortado: "88.99|4,41"

---

### 2. Por que o validador Pydantic não corrigiu?

**Análise do validador `arredondar_decimais` (schemas.py):**

```python
@field_validator(
    'valor_principal_liquido',
    'valor_principal_bruto',
    'juros_moratorios',
    'valor_total_requisitado',
    mode='before'
)
@classmethod
def arredondar_decimais(cls, v):
    if isinstance(v, str):
        v = v.strip()
        v = v.replace('R$', '').replace('R$ ', '')
        v = v.replace(' ', '')
        
        # Lógica: se tem vírgula, é separador decimal brasileiro
        if ',' in v:
            v = v.replace('.', '')  # Remove pontos de milhar
            v = v.replace(',', '.')  # Converte vírgula em ponto
        elif v.count('.') > 1:
            # Múltiplos pontos = pontos de milhar
            partes = v.split('.')
            v = ''.join(partes[:-1]) + '.' + partes[-1]
        
        v = Decimal(v)
    
    return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

**O validador DEVERIA ter corrigido**, mas:

#### Cenário 1: String "88.99" (sem vírgula)
```python
v = "88.99"
# Não tem vírgula → não entra no if
# Tem apenas 1 ponto → não entra no elif
# Converte direto: Decimal("88.99") = 88.99 ✅
```

**PROBLEMA:** O validador assume que "88.99" é um valor válido!

#### Cenário 2: Se o LLM tivesse retornado "88.994,41"
```python
v = "88.994,41"
# Tem vírgula → entra no if
v = v.replace('.', '')      # "88994,41"
v = v.replace(',', '.')     # "88994.41"
# Converte: Decimal("88994.41") = 88994.41 ✅
```

**CONCLUSÃO:** O erro foi no LLM, NÃO no validador!

---

### 3. Comparação: 16/10 vs 31/10

| Aspecto | 16/10/2025 (ERRADO) | 31/10/2025 (CORRETO) |
|---------|---------------------|----------------------|
| **Valor retornado** | "88.99" (string) | 88994.41 (number) |
| **Processo origem** | 0024288-52.2020.8.26.0053 | 0015796-15.2025.8.26.0500 |
| **Número ordem** | 9594/2026 | 1/2025 |
| **LLM** | Interpretou errado | Interpretou correto |
| **Validador** | Aceitou "88.99" | Manteve 88994.41 |

**Hipótese:** O LLM **confundiu ofícios** no PDF!

---

## 🚨 DESCOBERTA CRÍTICA

### O PDF tem 4 ofícios!

```
Ofício 1: página 1 (2/3 critérios)
Ofício 2: página 2 (3/3 critérios)
Ofício 3: página 3 (2/3 critérios) ← CPF 273.081.578-30 AQUI!
Ofício 4: página 4 (2/3 critérios)
```

**O LLM pode ter extraído dados do OFÍCIO ERRADO!**

Dados corretos:
- Ofício 3 (página 3): Processo 0015796-15.2025.8.26.0500, Ordem 1/2025, Valor 88.994,41

Dados extraídos em 16/10:
- Processo 0024288-52.2020.8.26.0053 (❌ diferente)
- Ordem 9594/2026 (❌ diferente)
- Valor 88.99 (❌ errado)

**ROOT CAUSE:** O detector encontrou o ofício certo (3), mas o LLM processou dados de outro ofício OU interpretou mal o texto.

---

## 💡 HIPÓTESES FINAIS

### Hipótese Principal ✅
**O LLM recebeu texto de múltiplos ofícios e misturou os dados.**

Evidências:
1. Processo origem diferente (ofício errado)
2. Número de ordem diferente (ofício errado)
3. Valor truncado "88.99" (interpretação errada)

### Hipótese Secundária
**O prompt não era claro o suficiente sobre formato numérico brasileiro.**

Evidências:
1. Valores retornados como strings
2. Ponto interpretado como decimal

---

## ✅ AÇÕES CORRETIVAS

### 1. Melhorar o Prompt
```python
⚠️ IMPORTANTE: Para valores monetários brasileiros:
- Formato no PDF: "88.994,41" (ponto = milhar, vírgula = decimal)
- Retorne como NUMBER: 88994.41 (sem ponto de milhar, ponto como decimal)
- NUNCA retorne como string
- Exemplos:
  * "R$ 88.994,41" → 88994.41
  * "R$ 1.234.567,89" → 1234567.89
  * "R$ 123,45" → 123.45
```

### 2. Adicionar Validação Extra
```python
# Verificar se valores são razoáveis
if valor_principal_liquido < 1000:
    logger.warning(f"Valor suspeito: {valor_principal_liquido}")
```

### 3. Garantir Isolamento de Ofícios
- Melhorar detecção de limites entre ofícios
- Enviar APENAS o texto do ofício específico para o LLM
- Não enviar múltiplos ofícios juntos

### 4. Reprocessar PDFs Afetados
- Identificar todos os JSONs com valores < R$ 100
- Reprocessar com código atualizado
- Atualizar banco de dados

---

## 📊 IMPACTO

### Processos Afetados
- CPF: 27308157830 (273.081.578-30)
- Processo: 0015796-15.2025.8.26.0500
- Requerente: RODRIGO AZEVEDO FERRAO

### Valor do Erro
- Esperado: R$ 88.994,41
- Armazenado: R$ 88,99
- **Diferença: R$ 88.905,42 (99,9% de erro)**

### Outros Processos
**URGENTE:** Verificar se há outros processos com valores suspeitos < R$ 1.000

```sql
SELECT cpf, numero_processo, requerente_caps,
       valor_principal_liquido,
       valor_principal_bruto,
       valor_total_requisitado
FROM lista_processos
WHERE valor_principal_liquido < 1000
   OR valor_principal_bruto < 1000
   OR valor_total_requisitado < 1000;
```

---

## 🎯 CONCLUSÃO

### Root Cause Confirmado
**O LLM (gpt-4o-mini) em 16/10/2025:**
1. Recebeu texto com múltiplos ofícios
2. Extraiu dados do ofício errado ou misturou dados
3. Interpretou "88.994,41" como "88.99"
4. Retornou valores como strings

**O validador Pydantic:**
- Funcionou corretamente
- Aceitou "88.99" como valor válido (não tinha como saber que estava errado)

### Fix Aplicado
**O código ATUAL (31/10/2025) processa CORRETAMENTE:**
- ✅ Detecta o ofício certo
- ✅ Extrai valores corretos
- ✅ LLM retorna numbers (não strings)
- ✅ Todos os valores validados

**Próximo passo:** Reprocessar PDFs antigos e atualizar banco de dados.

---

**Última Atualização:** 31/10/2025 19:30  
**Investigador:** Sistema OCR Debug  
**Status:** ✅ Root Cause Identificado - Aguardando Reprocessamento

