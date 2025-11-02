# 📋 PLANO DE INVESTIGAÇÃO: Bug de Parsing de Valores

**Processo:** 0015796-15.2025.8.26.0500  
**PDF:** Precatório-RAF.pdf  
**Data:** 31/10/2025

---

## 🎯 OBJETIVO

Reproduzir e corrigir o bug de extração de valores onde:
- **Valor Correto:** R$ 88.994,41
- **Valor Extraído:** R$ 88,99
- **Diferença:** -R$ 88.905,42

---

## 📊 ESTRUTURA CRIADA

```
8_erro_parsing-valor/
├── README.md                      ✅ Documentação principal
├── PLANO_INVESTIGACAO.md          ✅ Este arquivo
├── test_data/
│   └── Precatório-RAF.pdf        ✅ PDF problem

ático
├── test_outputs/                  📝 Outputs do teste
│   ├── 1_texto_extraido.txt      # Texto bruto do PDF
│   ├── 2_prompt_llm.txt          # Prompt enviado ao LLM
│   ├── 3_resposta_llm.json       # Resposta do GPT-4o-mini
│   ├── 4_dados_validados.json    # Após validação Pydantic
│   ├── 5_sql_statement.sql       # SQL que seria executado
│   └── 6_tabela_comparacao.txt   # Tabela comparativa
├── test_scripts/
│   ├── test_parse_local.py       📝 Script principal de teste
│   ├── compare_values.py         📝 Comparação valores
│   └── fix_validator.py          📝 Teste da correção
└── docs/
    ├── ANALISE_BUG.md            📝 Análise detalhada
    └── SOLUCAO_PROPOSTA.md       📝 Correção proposta
```

---

## 🔍 ETAPAS DE INVESTIGAÇÃO

### FASE 1: Reprodução do Bug ✅

**Objetivo:** Processar o PDF localmente e capturar todos os dados intermediários

**Script:** `test_parse_local.py`

**Ações:**
1. ✅ Copiar PDF para `test_data/`
2. ✅ Configurar ambiente de teste
3. 📝 Processar PDF com pipeline completo
4. 📝 Salvar outputs em cada etapa:
   - Texto extraído do PDF
   - Prompt enviado ao LLM
   - Resposta JSON do LLM
   - Dados após validação Pydantic
   - SQL statement

**Outputs Esperados:**
- `1_texto_extraido.txt` - Ver se `88.994,41` está no texto
- `2_prompt_llm.txt` - Ver se prompt está correto
- `3_resposta_llm.json` - Ver o que o LLM retornou
- `4_dados_validados.json` - Ver se validação alterou valores
- `5_sql_statement.sql` - Ver SQL final

### FASE 2: Identificação do Root Cause 🔍

**Objetivo:** Identificar onde o valor é alterado

**Pontos de Verificação:**

1. **Extração do PDF (PyMuPDF)**
   - ✅ Verificar se `88.994,41` está no texto bruto
   - ✅ Verificar encoding/formatação

2. **Prompt para LLM**
   - ✅ Verificar se instruções de parsing estão claras
   - ✅ Verificar se exemplo mostra formato brasileiro

3. **Resposta do LLM (GPT-4o-mini)**
   - ✅ Verificar JSON retornado
   - ✅ Ver se LLM já retorna valor errado

4. **Validação Pydantic (`schemas.py`)**
   - 🔴 **SUSPEITO PRINCIPAL:** Método `arredondar_decimais`
   - ✅ Ver lógica de conversão String → Decimal
   - ✅ Ver tratamento de separadores

**Localização do Código Suspeito:**

```python
# Arquivo: 3_OCR/1_parsing_PDF/app/schemas.py
# Linha: ~314-370

@field_validator(...)
@classmethod
def arredondar_decimais(cls, v):
    """
    Limpa e normaliza valores monetários antes da validação.
    
    Remove: R$, espaços, pontos de milhar
    Converte: vírgula em ponto decimal
    """
    # ... código aqui ...
```

**Lógica Atual:**
```python
# Se tem vírgula, é separador decimal brasileiro
if ',' in v:
    # Formato brasileiro: 1.234.567,89
    v = v.replace('.', '')  # Remove pontos de milhar
    v = v.replace(',', '.')  # Converte vírgula em ponto
elif v.count('.') > 1:
    # Múltiplos pontos = pontos de milhar
    partes = v.split('.')
    v = ''.join(partes[:-1]) + '.' + partes[-1]
```

**Problema Identificado:**
- Se LLM retornar `88.994,41` → funciona ✅
- Se LLM retornar `88.994` (sem vírgula) → vai para `elif`
- `elif` assume que `.994` é decimal → **BUG!**

### FASE 3: Implementação da Correção 🛠️

**Arquivo a Corrigir:** `3_OCR/1_parsing_PDF/app/schemas.py`

**Correção Proposta:**

```python
@field_validator(...)
@classmethod
def arredondar_decimais(cls, v):
    if v is None:
        return v
    
    from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
    
    try:
        if isinstance(v, (int, float)):
            v = Decimal(str(v))
        elif isinstance(v, str):
            v = v.strip()
            v = v.replace('R$', '').replace('R$ ', '').replace(' ', '')
            
            if not v or v.lower() in ('null', 'none', 'n/a', '-'):
                return None
            
            # 🔴 NOVA LÓGICA: Sempre assumir formato brasileiro
            # Se tem vírgula E ponto, é formato BR: X.XXX.XXX,XX
            if ',' in v and '.' in v:
                v = v.replace('.', '')  # Remove pontos de milhar
                v = v.replace(',', '.')  # Converte vírgula em ponto decimal
            # Se tem apenas vírgula, é decimal BR: XXX,XX
            elif ',' in v:
                v = v.replace(',', '.')  # Converte vírgula em ponto
            # Se tem apenas ponto e tem mais de 2 dígitos após o ponto
            # pode ser milhar sem vírgula: X.XXX → XXXX
            elif '.' in v:
                partes = v.split('.')
                # Se última parte tem 2 dígitos, assumir que é decimal
                if len(partes[-1]) == 2:
                    # É decimal: 88.99
                    pass
                # Se última parte tem 3 dígitos, é milhar: 88.994 → 88994
                elif len(partes[-1]) == 3:
                    v = ''.join(partes)
                # Múltiplos pontos, todos são milhares exceto último
                elif len(partes) > 2:
                    v = ''.join(partes[:-1]) + '.' + partes[-1]
            
            v = Decimal(v)
        
        if v < 0:
            return None
        
        return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
    except (ValueError, InvalidOperation, AttributeError):
        return None
```

**Teste da Correção:**
- `88.994,41` → `88994.41` ✅
- `88.994` → `88994.00` ✅ (assume milhar, não decimal)
- `88,99` → `88.99` ✅
- `88.99` (2 dígitos após ponto) → `88.99` ✅

### FASE 4: Validação 🧪

**Script:** `fix_validator.py`

**Testes:**
```python
test_cases = [
    ("88.994,41", 88994.41, "Formato BR completo"),
    ("88.994", 88994.00, "Formato BR sem centavos"),
    ("88,99", 88.99, "Formato BR somente centavos"),
    ("88.99", 88.99, "Formato US decimal"),
    ("1.234.567,89", 1234567.89, "Formato BR grande"),
    ("R$ 88.994,41", 88994.41, "Com prefixo R$"),
]

for input_val, expected, description in test_cases:
    result = arredondar_decimais(input_val)
    assert result == Decimal(str(expected)), f"Falhou: {description}"
    print(f"✅ {description}: {input_val} → {result}")
```

### FASE 5: Reprocessamento 🔄

**Ações:**
1. Aplicar correção em `3_OCR/1_parsing_PDF/app/schemas.py`
2. Reprocessar `Precatório-RAF.pdf`
3. Verificar valores corretos
4. Atualizar banco de dados (se necessário)

---

## ❓ PERGUNTAS PARA O USUÁRIO

Antes de prosseguir, preciso confirmar:

### 1. Variáveis de Ambiente

O ambiente de teste precisa acessar:
- ✅ **OpenAI API Key** - Para chamar GPT-4o-mini
- ⚠️ **PostgreSQL** - Para ler dados (opcional)

**Pergunta:** Posso usar as mesmas credenciais do `.env` da pasta `3_OCR`?

### 2. Escopo do Teste

**Opções:**

**A) Teste Completo (Recomendado)**
- Processa PDF inteiro
- Extrai texto com PyMuPDF
- Chama GPT-4o-mini
- Valida com Pydantic
- **NÃO grava** no banco
- Gera SQL statement para análise
- **Custo:** ~$0.01 (1 chamada OpenAI)

**B) Teste Parcial (Mais Rápido)**
- Usa JSON já existente (se houver)
- Pula extração e LLM
- Testa apenas validação Pydantic
- **Custo:** $0.00

**Pergunta:** Qual opção prefere? (Recomendo A para diagnóstico completo)

### 3. Formato dos Outputs

**Pergunta:** Os formatos dos outputs estão OK?
- `1_texto_extraido.txt` - Texto bruto do PDF
- `2_prompt_llm.txt` - Prompt enviado
- `3_resposta_llm.json` - Resposta do LLM
- `4_dados_validados.json` - Após Pydantic
- `5_sql_statement.sql` - SQL formatado
- `6_tabela_comparacao.txt` - Tabela com comparação

### 4. Dados do Processo

**Pergunta:** Preciso do CPF do processo para estruturar corretamente. 
Qual é o CPF associado ao processo `0015796-15.2025.8.26.0500`?

(Ou posso usar um CPF fictício para teste: `27308157830`)

---

## 🚀 PRÓXIMOS PASSOS IMEDIATOS

1. ✅ Confirmar perguntas acima
2. 📝 Criar `test_parse_local.py` com suas respostas
3. 🔄 Executar teste e gerar outputs
4. 🔍 Analisar resultados
5. 🛠️ Implementar correção
6. ✅ Validar solução

---

**Aguardando suas respostas para prosseguir!** 🎯

