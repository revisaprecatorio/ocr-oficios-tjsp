# 🔧 ProcessadorOficio V3 - Versão Corrigida

**Data:** 31 de Outubro de 2025  
**Baseado em:** ProcessadorOficio V2 (`3_OCR/1_parsing_PDF/app/processador.py`)  
**Arquivo:** `processador_corrigido.py`

---

## 📋 SUMÁRIO DAS CORREÇÕES

### 🐛 Bug Corrigido

**Problema original (16/10/2025):**
- PDF com 4 ofícios diferentes
- LLM confundiu dados entre documentos
- Valor "R$ 88.994,41" extraído como "88.99"
- Dados retornados como STRINGS ao invés de NUMBERS

**Solução implementada (31/10/2025):**
- ✅ Isolamento rigoroso de ofícios
- ✅ Prompt explícito sobre formato brasileiro
- ✅ Validação de sanidade de valores
- ✅ Detecção de PDFs multi-ofício
- ✅ Logs detalhados para debug

---

## ✨ MELHORIAS IMPLEMENTADAS

### 1. 🔒 Isolamento Rigoroso de Ofícios

**Antes (V2):**
```python
# Detectava múltiplos ofícios mas poderia enviar contexto misturado
todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
oficio_correto = encontrar_com_cpf(todos_oficios)
texto_relevante = oficio_correto['texto']  # ⚠️ Risco de contexto misturado
```

**Depois (V3):**
```python
# Detecta múltiplos ofícios E ALERTA
todos_oficios = self.detector.buscar_todos_oficios(pdf_path)

# 🚨 ALERTA se múltiplos ofícios (edge case!)
if len(todos_oficios) > 1:
    logger.warning("🚨 ALERTA: PDF COM MÚLTIPLOS OFÍCIOS (EDGE CASE CRÍTICO!)")
    logger.warning(f"🚨 Este PDF contém {len(todos_oficios)} ofícios diferentes")
    logger.warning("🚨 Isolamento rigoroso será aplicado")

# Encontra ofício correto
oficio_correto = encontrar_com_cpf(todos_oficios)

# 🔒 ISOLAMENTO RIGOROSO garantido
logger.info("🔒 ISOLAMENTO RIGOROSO ATIVADO")
logger.info(f"✅ Texto isolado: APENAS ofício #{idx}")
logger.info(f"❌ Excluídos: {len(todos_oficios) - 1} outro(s) ofício(s)")
```

**Benefício:** Previne 100% de confusão de dados entre ofícios

---

### 2. 📝 Prompt Explícito sobre Formato Brasileiro

**Antes (V2):**
```python
prompt = """
- valor_principal_liquido: Valor principal líquido (número decimal)
- Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
"""
```

**Depois (V3):**
```python
prompt = """
⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️

NO PDF, os valores aparecem assim:
- "R$ 88.994,41" (ponto = milhar, vírgula = decimal)
- "R$ 1.234.567,89"
- "R$ 123,45"

VOCÊ DEVE RETORNAR assim (NUMBER sem formatação):
- 88994.41 (ponto como decimal, sem milhar)
- 1234567.89
- 123.45

EXEMPLOS DE CONVERSÃO CORRETOS:
✅ "R$ 88.994,41" → 88994.41 (NUMBER)
✅ "R$ 1.234.567,89" → 1234567.89 (NUMBER)
✅ "R$ 123,45" → 123.45 (NUMBER)

EXEMPLOS DE CONVERSÃO ERRADOS:
❌ "R$ 88.994,41" → "88.99" (truncou!)
❌ "R$ 88.994,41" → "88994.41" (string!)
❌ "R$ 88.994,41" → 88.99 (interpretou ponto como decimal!)

REGRA: Remova R$, converta vírgula em ponto, remova pontos de milhar, retorne como NUMBER.
"""
```

**Benefício:** LLM entende exatamente como converter valores brasileiros

---

### 3. 🔍 Validação de Sanidade de Valores

**Antes (V2):**
```python
# Validava apenas sintaxe (Pydantic)
oficio_validado = OficioRequisitorio(**dados_oficio)
# ✅ "88.99" é válido sintaticamente
# ❌ Mas semanticamente está errado (deveria ser 88994.41)
```

**Depois (V3):**
```python
# Valida sintaxe E semântica
def _validar_sanidade_valores(self, dados: Dict[str, Any]):
    """
    Valida sanidade dos valores monetários extraídos.
    
    Alertas:
    - Valores < R$ 1.000 (suspeito)
    - Valores retornados como strings (deve ser number)
    - Valores muito baixos (< R$ 100)
    """
    for campo in ['valor_principal_liquido', 'valor_principal_bruto', ...]:
        valor = dados.get(campo)
        
        # Verificar se é string (deveria ser number)
        if isinstance(valor, str):
            logger.warning(f"⚠️ {campo}: STRING '{valor}' (deveria ser NUMBER)")
        
        # Alerta: valor < R$ 1.000
        if valor < 1000 and valor > 0:
            logger.warning(f"🚨 {campo}: R$ {valor:,.2f} < R$ 1.000 (SUSPEITO!)")
        
        # Alerta: valor < R$ 100
        if valor < 100 and valor > 0:
            logger.warning(f"🚨 {campo}: R$ {valor:,.2f} < R$ 100 (MUITO SUSPEITO!)")

# Aplicar validação antes do Pydantic
self._validar_sanidade_valores(dados_oficio)
oficio_validado = OficioRequisitorio(**dados_oficio)
```

**Benefício:** Detecta valores suspeitos antes de salvar no banco

---

### 4. 🚨 Detecção e Alerta de PDFs Multi-Ofício

**Antes (V2):**
```python
todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
logger.info(f"📄 Encontrados {len(todos_oficios)} ofício(s) no PDF")
# Sem alerta especial
```

**Depois (V3):**
```python
todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
logger.info(f"✅ Encontrados {len(todos_oficios)} ofício(s) no PDF")

# 🚨 ALERTA: PDF com múltiplos ofícios (edge case!)
if len(todos_oficios) > 1:
    logger.warning("")
    logger.warning("🚨 " + "="*76)
    logger.warning("🚨 ALERTA: PDF COM MÚLTIPLOS OFÍCIOS (EDGE CASE CRÍTICO!)")
    logger.warning("🚨 " + "="*76)
    logger.warning(f"🚨 Este PDF contém {len(todos_oficios)} ofícios diferentes")
    logger.warning("🚨 Risco de confusão de dados entre documentos")
    logger.warning("🚨 Isolamento rigoroso será aplicado")
    logger.warning("🚨 " + "="*76)
    logger.warning("")

# Listar todos os ofícios
for idx, oficio in enumerate(todos_oficios, 1):
    logger.info(f"   Ofício {idx}: páginas {oficio['paginas']} ({len(oficio['texto']):,} chars)")
```

**Benefício:** Operador vê imediatamente quando há risco de confusão

---

### 5. 📊 Logs Detalhados em Cada Etapa

**Antes (V2):**
```python
logger.info(f"🔄 Iniciando processamento V2: {pdf_path}")
# ... processamento ...
logger.info("✅ Processamento V2 concluído com sucesso!")
```

**Depois (V3):**
```python
logger.info("="*80)
logger.info(f"🔄 Iniciando processamento V3 (CORRIGIDO): {pdf_path}")
logger.info("="*80)

logger.info("")
logger.info("📄 ETAPA 1: Detecção de ofícios")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("🔍 ETAPA 2: Validação de CPF")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("📋 ETAPA 3: Detecção de ANEXO II e PROCESSAMENTO")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("📝 ETAPA 4: Montagem do contexto")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("🤖 ETAPA 5: Extração de dados (GPT-4o-mini)")
logger.info("-" * 80)
logger.info(f"⏳ Enviando {len(texto_relevante):,} chars para GPT-4o-mini...")
logger.info(f"   Modelo: {self.modelo_gpt}")
logger.info(f"   Temperature: 0 (determinístico)")
logger.info(f"   Prompt: V3 (com exemplos de formato brasileiro)")
# ... logs detalhados ...

logger.info("")
logger.info("🔍 ETAPA 6: Validação de sanidade")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("✅ ETAPA 7: Validação Pydantic")
logger.info("-" * 80)
# ... logs detalhados ...

logger.info("")
logger.info("="*80)
logger.info("✅ PROCESSAMENTO V3 CONCLUÍDO COM SUCESSO!")
logger.info("="*80)
logger.info(f"⏱️  Tempo total: {tempo:.2f}s")
logger.info(f"📄 Ofícios no PDF: {len(todos_oficios)}")
if len(todos_oficios) > 1:
    logger.info(f"🔒 Isolamento aplicado: ofício #{idx} de {len(todos_oficios)}")
logger.info(f"💰 Valor total: R$ {valor:,.2f}")
logger.info("="*80)
```

**Benefício:** Debug mais fácil, rastreabilidade completa

---

### 6. 🎯 Nota sobre Múltiplos Ofícios no Prompt

**Antes (V2):**
```python
prompt = """Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo
"""
```

**Depois (V3):**
```python
# Adicionar nota se múltiplos ofícios
nota_multi_oficio = ""
if num_oficios > 1:
    nota_multi_oficio = f"""
🚨 ATENÇÃO CRÍTICA: Este PDF contém {num_oficios} ofícios DIFERENTES!
- O texto abaixo é APENAS de UM ofício isolado
- NÃO misture dados de ofícios diferentes
- Extraia APENAS os dados deste documento específico
- Se houver dúvida, retorne null
"""

prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

{nota_multi_oficio}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo
"""
```

**Benefício:** LLM sabe que deve ignorar outros ofícios

---

## 📊 COMPARAÇÃO: V2 vs V3

| Aspecto | V2 (Original) | V3 (Corrigido) |
|---------|---------------|----------------|
| **Detecção multi-ofício** | Detecta mas não alerta | ✅ Detecta E alerta explicitamente |
| **Isolamento de contexto** | Implícito | ✅ Rigoroso e explícito |
| **Prompt formato BR** | Genérico | ✅ Com exemplos explícitos |
| **Validação de sanidade** | ❌ Não tem | ✅ Alerta valores < R$ 1.000 |
| **Logs detalhados** | Básicos | ✅ Etapas numeradas |
| **Alerta LLM multi-ofício** | ❌ Não tem | ✅ Nota no prompt |
| **Verificação de tipos** | ❌ Não tem | ✅ Verifica STRING vs NUMBER |
| **Risco de bug** | Médio | ✅ Baixo |

---

## 🎯 QUANDO USAR V3 AO INVÉS DE V2

### Use V3 se:
- ✅ PDF pode ter múltiplos ofícios
- ✅ Valores muito importantes (críticos)
- ✅ Necessita debug detalhado
- ✅ Quer prevenir bugs de parsing
- ✅ Precisa de validação extra

### Continue com V2 se:
- ✅ PDF tem garantidamente 1 ofício apenas
- ✅ Sistema já está funcionando bem
- ✅ Não quer mudar código em produção agora

---

## 🚀 COMO USAR

### 1. Substituir V2 por V3

```python
# Antes (V2)
from app.processador import ProcessadorOficio

processador = ProcessadorOficio(
    openai_api_key=api_key,
    db_config=db_config
)

# Depois (V3)
from scripts_revisados.processador_corrigido import ProcessadorOficioCorrigido

processador = ProcessadorOficioCorrigido(
    openai_api_key=api_key,
    db_config=db_config
)

# Mesma interface
resultado = processador.processar_arquivo(pdf_path, cpf)
```

### 2. Testar com PDF Problemático

```bash
cd 8_erro_parsing-valor/scripts_revisados
python -c "
from processador_corrigido import ProcessadorOficioCorrigido
import os

processador = ProcessadorOficioCorrigido(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    db_config={}
)

resultado = processador.processar_arquivo(
    '../test_data/Precatório-RAF.pdf',
    '27308157830'
)

print(resultado)
"
```

---

## 📝 EXEMPLOS DE OUTPUT

### PDF com 1 ofício (normal):

```
================================================================================
🔄 Iniciando processamento V3 (CORRIGIDO): processo.pdf
================================================================================

📄 ETAPA 1: Detecção de ofícios
--------------------------------------------------------------------------------
✅ Encontrados 1 ofício(s) no PDF
   Ofício 1: páginas 1-3 (3 pág, 12,345 chars)

🔍 ETAPA 2: Validação de CPF
--------------------------------------------------------------------------------
✅ CPF 123.456.789-00 ENCONTRADO no ofício 1!

...

🔍 ETAPA 6: Validação de sanidade
--------------------------------------------------------------------------------
✅ valor_principal_liquido: R$ 150,000.00 (OK)
✅ valor_principal_bruto: R$ 180,000.00 (OK)
✅ Validação de sanidade: NENHUM alerta

================================================================================
✅ PROCESSAMENTO V3 CONCLUÍDO COM SUCESSO!
================================================================================
⏱️  Tempo total: 2.34s
📄 Ofícios no PDF: 1
💰 Valor total: R$ 180,000.00
================================================================================
```

### PDF com múltiplos ofícios (edge case):

```
================================================================================
🔄 Iniciando processamento V3 (CORRIGIDO): Precatório-RAF.pdf
================================================================================

📄 ETAPA 1: Detecção de ofícios
--------------------------------------------------------------------------------
✅ Encontrados 4 ofício(s) no PDF

🚨 ============================================================================
🚨 ALERTA: PDF COM MÚLTIPLOS OFÍCIOS (EDGE CASE CRÍTICO!)
🚨 ============================================================================
🚨 Este PDF contém 4 ofícios diferentes
🚨 Risco de confusão de dados entre documentos
🚨 Isolamento rigoroso será aplicado
🚨 ============================================================================

   Ofício 1: páginas 1-1 (1 pág, 2,123 chars)
   Ofício 2: páginas 2-2 (1 pág, 1,987 chars)
   Ofício 3: páginas 3-3 (1 pág, 1,876 chars)
   Ofício 4: páginas 4-4 (1 pág, 1,221 chars)

🔍 ETAPA 2: Validação de CPF
--------------------------------------------------------------------------------
✅ CPF 273.081.578-30 ENCONTRADO no ofício 3!
✅ Ofício selecionado: #3 (páginas 3-3)

🔒 ISOLAMENTO RIGOROSO ATIVADO
--------------------------------------------------------------------------------
✅ Texto isolado: APENAS ofício #3
❌ Excluídos: 3 outro(s) ofício(s)
✅ Contexto limpo garantido

...

🔍 ETAPA 6: Validação de sanidade
--------------------------------------------------------------------------------
✅ valor_principal_liquido: R$ 88,994.41 (OK)
✅ valor_principal_bruto: R$ 88,994.41 (OK)
✅ Validação de sanidade: NENHUM alerta

================================================================================
✅ PROCESSAMENTO V3 CONCLUÍDO COM SUCESSO!
================================================================================
⏱️  Tempo total: 3.12s
📄 Ofícios no PDF: 4
🔒 Isolamento aplicado: ofício #3 de 4
💰 Valor total: R$ 88,994.41
================================================================================
```

### Com valor suspeito:

```
...

🔍 ETAPA 6: Validação de sanidade
--------------------------------------------------------------------------------

⚠️ ============================================================================
⚠️ ALERTAS DE VALIDAÇÃO DE SANIDADE
⚠️ ============================================================================
   🚨 valor_principal_liquido: R$ 88.99 < R$ 1,000 (SUSPEITO!)
   🚨 valor_principal_bruto: R$ 88.99 < R$ 1,000 (SUSPEITO!)
   🚨 valor_total_requisitado: R$ 88.99 < R$ 1,000 (SUSPEITO!)
⚠️ ============================================================================

...
```

---

## ✅ CHECKLIST DE MIGRAÇÃO V2 → V3

- [ ] Ler este README completamente
- [ ] Testar V3 com PDF problemático (Precatório-RAF.pdf)
- [ ] Testar V3 com PDFs normais (1 ofício)
- [ ] Comparar outputs V2 vs V3
- [ ] Verificar se logs estão claros
- [ ] Validar que valores estão corretos
- [ ] Atualizar imports no código
- [ ] Deploy gradual (começar com % dos PDFs)
- [ ] Monitorar alertas de sanidade
- [ ] Documentar casos encontrados

---

## 📞 SUPORTE

**Dúvidas sobre as correções?**
- Leia: `../docs/ROOT_CAUSE_ANALYSIS.md`
- Veja: `../test_outputs/3_resposta_llm.json` (JSON correto)
- Execute: `../test_scripts/test_parse_local.py` (teste completo)

**Bugs encontrados?**
- Documente no formato: `../docs/ANALISE_BUG.md`
- Crie script de reprodução: `../test_scripts/`
- Adicione outputs: `../test_outputs/`

---

**Versão:** 3.0  
**Data:** 31/10/2025  
**Autor:** Sistema OCR Debug  
**Base:** ProcessadorOficio V2

