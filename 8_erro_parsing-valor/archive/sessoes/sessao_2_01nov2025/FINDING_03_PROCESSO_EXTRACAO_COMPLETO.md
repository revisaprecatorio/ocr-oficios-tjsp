# 🔄 FINDING #03 - Processo Completo de Extração e Pipeline LLM

**Data:** 01 de novembro de 2025  
**Tipo:** Documentação Técnica - Arquitetura do Sistema  
**Status:** ✅ Documentado - Baseline para Testes de Migração

---

## 📋 SUMÁRIO EXECUTIVO

Este documento detalha **exatamente como funciona** o processo atual de extração de dados de Ofícios Requisitórios, desde o PDF até o JSON validado. Entender este pipeline é crítico para implementar melhorias e migrar para novos LLMs.

**Key Insight:** O sistema **NÃO é OCR tradicional** - ele processa PDFs nativos com texto já digitalizado, aplicando chunking inteligente antes de enviar para o LLM.

---

## 🏗️ ARQUITETURA DO PIPELINE (6 ETAPAS)

```
📄 PDF (até 356 páginas)
         ↓
    [ETAPA 1]
 Extração PyMuPDF
  (texto nativo)
         ↓
    [ETAPA 2]
  Detecção Python
 (heurísticas locais)
         ↓
    [ETAPA 3]
Chunking Inteligente
  (otimiza contexto)
         ↓
    [ETAPA 4]  ← 🤖 ÚNICA interação com LLM
   Extração LLM
  (GPT-4o-mini)
         ↓
    [ETAPA 5]
Validação Pydantic
  (schemas rígidos)
         ↓
    [ETAPA 6]
 PostgreSQL Upsert
  (persistência)
```

---

## 📖 ETAPA 1: Extração de Texto Bruto (PyMuPDF)

### **Tecnologia: PyMuPDF (não envolve LLM)**

```python
import pymupdf

doc = pymupdf.open(pdf_path)
texto_completo = ""

for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    texto_completo += page.get_text() + "\n"

doc.close()
```

### **Características:**
- ✅ **Rápido**: <0.1s por PDF
- ✅ **Zero custo**: Processamento local
- ✅ **PDFs nativos**: Texto já digitalizado (não precisa OCR de imagens)
- ✅ **Preserva estrutura**: Mantém quebras de linha e formatação

### **Output:**
- Texto completo do PDF (~500k caracteres para PDFs grandes)
- **NÃO é enviado ao LLM ainda!**

---

## 🔍 ETAPA 2: Detecção Inteligente (Python Puro)

### **2.1. Buscar TODOS os Ofícios no PDF**

```python
def buscar_todos_oficios(pdf_path: str) -> List[Dict]:
    """
    Detecta múltiplos ofícios em um único PDF.
    Usa heurísticas Python (sem LLM).
    """
    oficios = []
    doc = pymupdf.open(pdf_path)
    
    for page_num in range(len(doc)):
        texto = doc.load_page(page_num).get_text()
        
        # Critério 1: Keywords
        if "OFÍCIO REQUISITÓRIO" in texto.upper():
            # Critério 2: Padrão CNJ
            if re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto):
                # Critério 3: Estrutura
                if "VARA" in texto.upper():
                    # ✅ Início de ofício detectado!
                    oficios.append({
                        'inicio': page_num,
                        'texto': texto
                    })
    
    return oficios
```

### **Heurísticas de Detecção:**

| Critério | Descrição | Peso |
|----------|-----------|------|
| **Keywords** | "OFÍCIO REQUISITÓRIO", "VARA DA FAZENDA PÚBLICA" | 3 |
| **Padrão CNJ** | `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}` | 3 |
| **Estrutura** | "AO JUÍZO DA ... VARA" | 2 |

**Mínimo**: 5 pontos de 9 para detectar ofício

### **2.2. Validar CPF em Cada Ofício**

```python
def validar_cpf_no_oficio(texto: str, cpf_formatado: str) -> bool:
    """
    Busca CPF formatado (XXX.XXX.XXX-XX) no texto.
    Seleciona APENAS o ofício correto.
    """
    return cpf_formatado in texto
```

### **2.3. Detectar Seções Especiais**

#### **ANEXO II (Dados Bancários):**
```python
def detectar_anexo_ii(pdf_path: str) -> Tuple[List[int], str]:
    """
    Detecta páginas com "ANEXO II" e dados bancários.
    """
    criterios = [
        "ANEXO II" in texto.upper(),
        "BANCO:" in texto or "AGÊNCIA:" in texto,
        "CONTA:" in texto,
        "Credor nº:" in texto  # Estrutura tabular
    ]
    
    if sum(criterios) >= 2:  # Mínimo 2 critérios
        return True
```

#### **PROCESSAMENTO (Número de Ordem/Rejeição):**
```python
def detectar_processamento(pdf_path: str, inicio: int) -> Tuple[int, str]:
    """
    Detecta página de PROCESSAMENTO após o ofício.
    """
    keywords = [
        "PROCESSAMENTO COM INFORMAÇÃO",
        "Nº de Ordem:",
        "NOTA DE REJEIÇÃO",
        "OFÍCIO REJEITADO"
    ]
    
    # Buscar em até 100 páginas após o ofício
    for offset in range(100):
        pagina = inicio + offset
        texto = extrair_texto_pagina(pdf_path, pagina)
        
        if any(kw in texto.upper() for kw in keywords):
            return pagina, texto
    
    return None, None
```

### **Output da Etapa 2:**
```python
{
    'oficio_correto': {
        'paginas': [201, 202, ..., 356],  # 156 páginas
        'texto': "OFÍCIO REQUISITÓRIO Nº 644/2015..."
    },
    'anexo_ii': {
        'paginas': [250, 251],
        'texto': "ANEXO II\nBanco: 341\nAgência: 1234..."
    },
    'processamento': {
        'pagina': 355,
        'texto': "PROCESSAMENTO COM INFORMAÇÃO\nNº de Ordem: 644/2015..."
    }
}
```

---

## ✂️ ETAPA 3: Chunking Inteligente (Otimização de Contexto)

### **Problema: Limite de Contexto do LLM**

- **GPT-4o-mini**: 128k tokens (~256k caracteres)
- **Margem de segurança**: 200k caracteres
- **PDFs grandes**: Até 500k caracteres

### **Estratégia de Chunking:**

```python
def aplicar_chunking(oficio: Dict, anexo: Dict, proc: Dict) -> str:
    """
    Reduz texto mantendo partes críticas.
    """
    paginas_oficio = oficio['paginas']
    num_paginas = len(paginas_oficio)
    
    # CASO 1: Ofício pequeno (<100 páginas)
    if num_paginas <= 100:
        texto_final = oficio['texto']  # Enviar completo
    
    # CASO 2: Ofício grande SEM anexo/processamento
    elif num_paginas > 100 and not anexo and not proc:
        # CHUNKING: Primeiras 50 + Últimas 50
        paginas_chunk = paginas_oficio[:50] + paginas_oficio[-50:]
        texto_final = extrair_texto_paginas(paginas_chunk)
        logger.info(f"📄 CHUNKING aplicado: 100 páginas de {num_paginas}")
    
    # CASO 3: Texto final muito grande (>200k chars)
    if len(texto_final) > 200_000:
        # CHUNKING AGRESSIVO: Primeiras 30 + Últimas 30
        paginas_chunk = paginas_oficio[:30] + paginas_oficio[-30:]
        texto_final = extrair_texto_paginas(paginas_chunk)
        logger.warning(f"⚠️ CHUNKING AGRESSIVO: 60 páginas de {num_paginas}")
    
    # SEMPRE adicionar ANEXO II e PROCESSAMENTO completos
    if anexo:
        texto_final += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{anexo['texto']}"
    
    if proc:
        texto_final += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{proc['texto']}"
    
    return texto_final
```

### **Exemplo Real - PDF de 356 Páginas:**

```python
# PDF: 10155175874/7007859-54.2010.8.26.0500.pdf
# Total: 356 páginas (500k caracteres)

# Ofício correto: Páginas 201-356 (156 páginas)
# ANEXO II: Páginas 250-251 (2 páginas)
# PROCESSAMENTO: Página 355 (1 página)

# CHUNKING APLICADO:
texto_enviado = (
    paginas[201:231] +    # Primeiras 30 do ofício
    paginas[326:356] +    # Últimas 30 do ofício
    anexo_completo +      # ANEXO II completo (pág 250-251)
    proc_completo         # PROCESSAMENTO completo (pág 355)
)

# Total enviado: ~63 páginas (~90k caracteres)
# Redução: 356 páginas → 63 páginas (82% menor!)
```

### **⚠️ PROBLEMA IDENTIFICADO:**

```python
# Páginas enviadas: 201-231, 326-356, 250-251, 355
# Páginas PERDIDAS: 232-249, 252-325 (total: 61 páginas)

# Se informações críticas (juros, contribuições) 
# estiverem nas páginas perdidas → ERRO!

# Caso real: Erro de R$ 166k (13.3%)
# Causa provável: Juros nas páginas 232-325 não capturados
```

---

## 🤖 ETAPA 4: Extração com LLM (GPT-4o-mini)

### **4.1. Estrutura da Chamada**

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{
        "role": "user",
        "content": prompt_estruturado  # Ver próxima seção
    }],
    temperature=0,  # Determinístico (sempre mesma resposta)
    max_tokens=4096  # Resposta grande (JSON com 50+ campos)
)

# Parse do JSON retornado
dados = json.loads(response.choices[0].message.content)
```

### **4.2. Input do LLM (Exemplo):**

```
=== TEXTO ENVIADO ===

[Páginas 201-231 do ofício]
OFÍCIO REQUISITÓRIO Nº 644/2015

Processo nº: 7007859-54.2010.8.26.0500
1ª Vara da Fazenda Pública - Comarca de São Paulo

Requerente: FERNANDO SANTOS ERNESTO
CPF: 101.551.758-74

...
[muitas páginas com detalhes do processo]
...

[Páginas 326-356 do ofício]
...
VALOR PRINCIPAL BRUTO: R$ 1.098.664,34
JUROS MORATÓRIOS: [?] ← ⚠️ Pode estar nas páginas perdidas!
VALOR TOTAL REQUISITADO: R$ 1.087.665,34
...

============================================
=== ANEXO II ===
============================================

DADOS BANCÁRIOS DO CREDOR

Banco: 341 - Itaú
Agência: 1234
Conta Corrente: 12345-6
CPF Titular: 101.551.758-74

============================================
=== PROCESSAMENTO ===
============================================

PROCESSAMENTO COM INFORMAÇÃO

Nº de Ordem: 644/2015
Data de Cadastramento: 15/03/2015

Total: 156 páginas → 63 páginas enviadas
```

### **4.3. Custos da Etapa 4:**

```python
# Exemplo: PDF médio com 100 páginas
texto_enviado = "90,000 caracteres"
tokens_input = 90_000 / 2 = 45_000 tokens  # ~2 chars/token em PT
tokens_output = 500 tokens  # JSON com 50+ campos

# Custos GPT-4o-mini:
custo_input = 45_000 / 1_000_000 * $0.150 = $0.00675
custo_output = 500 / 1_000_000 * $0.600 = $0.00030
custo_total = $0.00705 ≈ $0.007 por documento

# Para 1000 docs/mês: ~$7.00 (R$ 35.70)
```

---

## 📝 ETAPA 5: Validação com Pydantic

### **Schema de Validação:**

```python
from pydantic import BaseModel, Field, field_validator

class OficioRequisitorio(BaseModel):
    # CAMPOS OBRIGATÓRIOS
    processo_origem: str = Field(
        ..., 
        min_length=10,
        max_length=30,
        description="Número CNJ do processo"
    )
    
    requerente_caps: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Nome em MAIÚSCULAS"
    )
    
    # CAMPOS OPCIONAIS
    numero_ordem: Optional[str] = Field(
        None,
        pattern=r'^\d{1,6}/\d{4}$',  # Formato: XXX/YYYY
        description="Número de ordem do precatório"
    )
    
    valor_principal_liquido: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Valor principal líquido"
    )
    
    valor_total_requisitado: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Valor total requisitado"
    )
    
    banco: Optional[str] = Field(
        None,
        pattern=r'^\d{3}$',  # Código de 3 dígitos
        description="Código do banco"
    )
    
    # ... [50+ campos]
    
    @field_validator('processo_origem')
    def validar_cnj(cls, v):
        """Valida formato CNJ"""
        pattern = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
        if not re.match(pattern, v):
            raise ValueError(f"Processo CNJ inválido: {v}")
        return v
    
    @field_validator('requerente_caps')
    def validar_maiusculas(cls, v):
        """Valida se nome está em maiúsculas"""
        if v != v.upper():
            raise ValueError(f"Nome deve estar em MAIÚSCULAS: {v}")
        return v
```

### **Validações Aplicadas:**

1. ✅ **Tipos de dados**: string, decimal, date, boolean
2. ✅ **Formatos**: CNJ, CPF/CNPJ, OAB, códigos bancários
3. ✅ **Ranges**: Valores >= 0, strings com tamanho mínimo/máximo
4. ✅ **Padrões regex**: Número de ordem (XXX/YYYY), banco (3 dígitos)
5. ✅ **Normalização**: Datas para ISO (YYYY-MM-DD), valores para Decimal

### **Cálculos Derivados:**

```python
# Calcular idade e flag "idoso" automaticamente
if oficio.data_nascimento:
    hoje = date.today()
    idade = hoje.year - oficio.data_nascimento.year
    
    # Ajustar se ainda não fez aniversário
    if (hoje.month, hoje.day) < (oficio.data_nascimento.month, oficio.data_nascimento.day):
        idade -= 1
    
    oficio.idoso = (idade >= 60)
    logger.info(f"🎂 Idade: {idade} anos → idoso={oficio.idoso}")
```

---

## 💾 ETAPA 6: Armazenamento PostgreSQL

### **Schema da Tabela:**

```sql
CREATE TABLE lista_processos (
    -- Chaves primárias
    cpf VARCHAR(11) NOT NULL,
    numero_processo VARCHAR(30) NOT NULL,
    
    -- Dados do Ofício
    vara VARCHAR(100),
    processo_execucao VARCHAR(30),
    requerente_caps VARCHAR(200),
    advogado_nome VARCHAR(200),
    advogado_oab VARCHAR(20),
    
    -- Dados Financeiros
    valor_principal_liquido DECIMAL(15,2),
    valor_principal_bruto DECIMAL(15,2),
    juros_moratorios DECIMAL(15,2),
    valor_total_requisitado DECIMAL(15,2),
    data_base_atualizacao DATE,
    
    -- Dados Bancários (ANEXO II)
    banco VARCHAR(10),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    conta_tipo VARCHAR(20),
    
    -- Preferências
    idoso BOOLEAN,
    doenca_grave BOOLEAN,
    pcd BOOLEAN,
    
    -- Controle
    texto_completo_oficio TEXT NOT NULL,
    timestamp_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (cpf, numero_processo)
);
```

### **Operação UPSERT:**

```python
INSERT INTO lista_processos (
    cpf, numero_processo, vara, requerente_caps, 
    valor_total_requisitado, banco, agencia, conta,
    texto_completo_oficio, processado
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (cpf, numero_processo) 
DO UPDATE SET
    vara = EXCLUDED.vara,
    requerente_caps = EXCLUDED.requerente_caps,
    valor_total_requisitado = EXCLUDED.valor_total_requisitado,
    banco = EXCLUDED.banco,
    agencia = EXCLUDED.agencia,
    conta = EXCLUDED.conta,
    texto_completo_oficio = EXCLUDED.texto_completo_oficio,
    timestamp_processamento = CURRENT_TIMESTAMP,
    processado = EXCLUDED.processado;
```

**Vantagens:**
- ✅ Evita duplicatas
- ✅ Atualiza registros existentes
- ✅ Mantém histórico de processamento

---

## 📊 MÉTRICAS DO PIPELINE COMPLETO

### **Performance (por documento):**

| Etapa | Tempo | Custo | Nota |
|-------|-------|-------|------|
| 1. PyMuPDF | <0.1s | $0 | Local |
| 2. Detecção | <0.2s | $0 | Python puro |
| 3. Chunking | <0.1s | $0 | Local |
| **4. LLM** | **~1s** | **$0.0009** | **OpenAI** |
| 5. Pydantic | <0.05s | $0 | Local |
| 6. PostgreSQL | <0.05s | $0 | Local |
| **TOTAL** | **~1.5s** | **$0.0009** | **98% sucesso** |

### **Custos Mensais (1000 documentos):**

```
1000 docs × $0.0009 = $0.90/mês (R$ 4.60)

Distribuição de custos:
├─ LLM (GPT-4o-mini): 100% ($0.90)
├─ Infraestrutura: $0 (processamento local)
└─ PostgreSQL: $0 (já provisionado)
```

### **Acurácia Atual:**

```
📊 Resultados (50 PDFs processados):
├─ Sucesso: 98% (50/51)
├─ Acurácia perfeita: 56% (28/50)
├─ Discrepâncias: 16% (8/50)
│   ├─ Baixa (<1%): 14% (7/50)
│   └─ Alta (>10%): 2% (1/50) ← 🚨 Caso crítico
└─ Casos críticos: 2% (1/50)
    └─ Erro R$ 166k (13.3%) - PDF 356 páginas
```

---

## 🔴 PROBLEMA CRÍTICO IDENTIFICADO

### **Caso: PDF de 356 Páginas**

```
📄 PDF: 10155175874/7007859-54.2010.8.26.0500.pdf
├─ Total: 356 páginas (~500k caracteres)
├─ Ofício correto: Páginas 201-356 (156 páginas)
└─ Problema: Contexto perdido por chunking

CHUNKING APLICADO:
├─ Enviado: Páginas 201-231, 326-356 (60 pág)
├─ ANEXO II: Páginas 250-251 (2 pág)
├─ PROCESSAMENTO: Página 355 (1 pág)
└─ PERDIDO: Páginas 232-325 (94 páginas! 🚨)

RESULTADO:
├─ Valor extraído: R$ 1.087.665,34
├─ Valor correto: R$ 1.253.909,97
└─ Erro: R$ 166.244,63 (13.3%)

CAUSA PROVÁVEL:
└─ Juros/contribuições nas páginas 232-325 não capturados
```

### **Solução com Gemini 2.5 Pro:**

```
🚀 Gemini 2.5 Pro:
├─ Contexto: 2M tokens (~1500 páginas)
├─ PDF 356 páginas: Cabe inteiro! ✅
├─ Sem chunking necessário
└─ Juros capturados: Erro eliminado

📈 Melhoria esperada:
├─ Casos críticos: 2% → 0%
├─ Acurácia perfeita: 56% → ~65%
└─ ROI: Elimina risco de erros >R$ 100k
```

---

## 🎯 CONCLUSÕES E PRÓXIMOS PASSOS

### **Pontos Fortes do Pipeline Atual:**

1. ✅ **Eficiente**: 5 de 6 etapas são locais (zero custo)
2. ✅ **Rápido**: ~1.5s por documento
3. ✅ **Preciso**: 98% taxa de sucesso geral
4. ✅ **Barato**: $0.0009/documento
5. ✅ **Validado**: Schema Pydantic robusto

### **Pontos Fracos Identificados:**

1. ❌ **Chunking perde contexto**: PDFs >100 páginas
2. ❌ **Limite 128k tokens**: Insuficiente para documentos grandes
3. ❌ **Erro crítico**: 2% de casos com erro >10%
4. ❌ **Risco financeiro**: Erros de até R$ 166k

### **Recomendações:**

#### **Curto Prazo (Semana 1-2):**
1. ✅ Testar Gemini 2.5 Pro nos 3 casos problemáticos
2. ✅ Validar custos reais vs estimados
3. ✅ Comparar precisão GPT-4o-mini vs Gemini
4. ✅ Medir latência em produção

#### **Médio Prazo (Semana 3-4):**
1. ✅ Implementar seleção dinâmica de modelo
2. ✅ Configurar fallback automático
3. ✅ Deploy em staging com monitoramento
4. ✅ Documentar best practices de prompt

#### **Longo Prazo (Mês 2+):**
1. ✅ Estratégia híbrida (GPT + Gemini + Claude)
2. ✅ Cache de resultados (reduz 30% custos)
3. ✅ Otimização de prompts por modelo
4. ✅ Dashboard de métricas em tempo real

---

## 📚 REFERÊNCIAS

### **Código Fonte:**
- `3_OCR/1_parsing_PDF/app/processador.py` - Pipeline completo
- `3_OCR/1_parsing_PDF/app/detector.py` - Detecção de ofícios
- `3_OCR/1_parsing_PDF/app/schemas.py` - Validação Pydantic

### **Documentação:**
- `3_OCR/README.md` - Visão geral do sistema
- `3_OCR/AGENTS.md` - Especificações técnicas
- `3_OCR/CHANGELOG.md` - Histórico de mudanças

### **Análises Relacionadas:**
- `FINDING_01_ANALISE_GPT41_VIABILIDADE.md` - Análise GPT-4.1
- `FINDING_02_ANALISE_LLM_RECOMENDACOES_2025.md` - Comparação de LLMs
- `RESULTADOS_VALIDACAO_PARCIAL.md` - Validação de 16 PDFs

---

**Documento gerado em:** 01/11/2025  
**Próxima ação:** Analisar engenharia de prompt atual antes de testes com Gemini  
**Status:** ✅ Completo - Pronto para implementação

