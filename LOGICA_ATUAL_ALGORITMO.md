# 🔍 Lógica Atual do Algoritmo de Extração

**Data:** 11 de Novembro de 2025  
**Versão:** v2.4.2 (com fix ANEXO II multi-creditor)

---

## 📊 Fluxo Completo do Algoritmo

```
┌─────────────────────────────────────────────────────────────┐
│                    INÍCIO DO PROCESSAMENTO                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 1: EXTRAIR CPF DA PASTA                               │
│ • Pega nome da pasta: "03730461893"                         │
│ • Formata: "037.304.618-93"                                 │
│ • Se inválido → ERRO e para                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 2: BUSCAR TODOS OS OFÍCIOS NO PDF                    │
│ • Detector varre TODO o PDF                                 │
│ • Identifica início de cada ofício (keywords + CNJ)         │
│ • Retorna lista: [{paginas: [11,12], texto: "..."}, ...]   │
│ • Se nenhum ofício → ERRO e para                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 3: ENCONTRAR OFÍCIO COM CPF CORRETO                  │
│ • Loop por cada ofício encontrado                           │
│ • Verifica se texto contém CPF da pasta                     │
│ • Primeiro ofício com CPF → SELECIONADO                     │
│ • Se nenhum match → ERRO e para                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 3.1: DETECTAR TERMOS JURÍDICOS (V2.4.0)             │
│ • Extrai texto COMPLETO do PDF                              │
│ • Busca: "CESSÃO DE CRÉDITO", "HABILITAÇÃO", etc.          │
│ • Armazena flags para uso posterior                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 4: DETECTAR ANEXO II                                 │
│ • 🆕 FIX v2.4.2: Busca A PARTIR da última página do ofício │
│ • Antes: buscava desde o início (pegava ANEXO II errado)   │
│ • Agora: inicio = ultima_pag_oficio                         │
│ • Procura: "ANEXO II" + dados bancários (CPF + Banco)      │
│ • Se encontrado → armazena texto                            │
│ • Se NÃO encontrado → continua (pode ter dados inline)     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 5: EXTRAIR NÚMERO DE ORDEM DO TÍTULO                 │
│ • Busca no texto do ofício: "OFÍCIO REQUISITÓRIO Nº XXX/YY"│
│ • Padrão: "644/2015", "2913/2023"                          │
│ • Se encontrado → armazena                                  │
│ • Se NÃO encontrado → continua (pode estar no PROCESSAMENTO)│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 6: DETECTAR PROCESSAMENTO                            │
│ • Busca A PARTIR de: última página ANEXO II OU ofício      │
│ • Limite: 100 páginas após o início                         │
│ • Procura: "PROCESSAMENTO", "Nº de Ordem:", "DEPRE"        │
│ • Se encontrado → armazena texto                            │
│ • Se NÃO encontrado → continua                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 6.1: VERIFICAR SE OFÍCIO FOI REJEITADO              │
│ 🔴 REGRA CRÍTICA: Verificar ACEITAÇÃO primeiro!            │
│                                                              │
│ A) TEM "PROCESSAMENTO COM INFORMAÇÃO"? → ACEITO ✅         │
│ B) TEM número de ordem? → ACEITO ✅                         │
│ C) Se NÃO tem A nem B:                                      │
│    → Busca "NOTA DE REJEIÇÃO" no PROCESSAMENTO             │
│    → Busca em 50 páginas após o ofício                     │
│    → Se encontrar → REJEITADO ❌                            │
│                                                              │
│ Se REJEITADO:                                               │
│ • Extrai motivo da rejeição                                 │
│ • Marca flag rejeitado=true                                 │
│ • Continua processamento (extrai o que for possível)        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 7: MONTAR TEXTO RELEVANTE                            │
│ • Base: texto do ofício selecionado                         │
│ • + ANEXO II (se encontrado)                                │
│ • + PROCESSAMENTO ou NOTA DE REJEIÇÃO (se encontrado)      │
│                                                              │
│ CHUNKING (se necessário):                                   │
│ • Se ofício > 100 páginas SEM ANEXO II/PROC → chunk        │
│ • Pega: primeiras 50 + últimas 50 páginas                  │
│ • Se Gemini disponível → NÃO faz chunking (1M tokens)      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 8: NORMALIZAR VALORES MONETÁRIOS                     │
│ • Busca padrões: R$ XX.XXX,XX                              │
│ • Converte: R$ 52.228,43 → R$ 52228.43                     │
│ • Remove pontos de milhar, mantém vírgula como ponto       │
│ • Evita LLM interpretar ponto como decimal                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 9: ENVIAR PARA LLM (Modo Híbrido)                   │
│ • Tenta Gemini 2.5 Flash primeiro (se disponível)          │
│ • Fallback: GPT-4o-mini                                     │
│ • Prompt com instruções detalhadas                          │
│ • Inclui: formato brasileiro, dados inline, etc.           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 10: VALIDAR DADOS EXTRAÍDOS (Pydantic)              │
│ • Valida formato CNJ do processo                            │
│ • Valida CPF/CNPJ                                           │
│ • Valida datas (ISO format)                                 │
│ • Arredonda valores decimais                                │
│ • Se validação falha → tenta OpenAI como fallback          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASSO 11: RETORNAR RESULTADO                               │
│ • sucesso: true/false                                       │
│ • dados: {...} (validados)                                  │
│ • observacoes: campos faltantes, avisos                     │
│ • tempo_processamento: segundos                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Decisões Críticas do Algoritmo

### **1. Busca de Ofícios (Passo 2)**

**O que busca:**
- Keywords: "OFÍCIO REQUISITÓRIO", "VARA DA FAZENDA PÚBLICA"
- Padrão CNJ: `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
- Estrutura: "AO JUÍZO DA ... VARA"

**Critério de detecção:**
- Mínimo **2 de 3 critérios** para considerar início de ofício
- Fim do ofício: próximo ofício OU assinatura + página curta

**Se encontra:**
- ✅ Armazena lista de ofícios com páginas e texto

**Se NÃO encontra:**
- ❌ ERRO: "Nenhum ofício detectado"
- Para processamento

---

### **2. Seleção do Ofício Correto (Passo 3)**

**O que busca:**
- CPF formatado: "037.304.618-93"
- CPF sem formatação (backup): "03730461893"

**Lógica:**
```python
for oficio in todos_oficios:
    if CPF in oficio.texto:
        return oficio  # PRIMEIRO match
        break
```

**Se encontra:**
- ✅ Seleciona PRIMEIRO ofício com CPF
- Continua para próximos passos

**Se NÃO encontra:**
- ❌ ERRO: "CPF não encontrado (PDF tem X ofício(s))"
- Para processamento

**⚠️ PROBLEMA ATUAL:**
- Em PDFs multi-creditor, pode ter 52 ofícios
- Sistema encontra o correto (ex: ofício #28)
- MAS... próximos passos podem pegar dados de outros credores!

---

### **3. Detecção ANEXO II (Passo 4)**

**O que busca:**
- Marcador: "ANEXO II"
- Dados bancários REAIS:
  - CPF formatado: `\d{3}\.\d{3}\.\d{3}-\d{2}`
  - Nome do credor
  - Valor requisitado

**🆕 FIX v2.4.2:**
```python
# ANTES (v2.4.1):
detectar_anexo_ii(pdf_path)  # Buscava desde o início

# AGORA (v2.4.2):
detectar_anexo_ii(pdf_path, inicio=ultima_pag_oficio)  # Busca APÓS ofício
```

**Se encontra:**
- ✅ Adiciona texto do ANEXO II ao contexto
- LLM usa dados bancários do ANEXO II

**Se NÃO encontra:**
- ⚠️ Continua sem ANEXO II
- LLM deve procurar dados inline no ofício
- **PROBLEMA:** Prompt não estava instruindo isso adequadamente

---

### **4. Detecção PROCESSAMENTO (Passo 6)**

**O que busca:**
- Keywords: "PROCESSAMENTO", "DEPRE", "Nº de Ordem"
- Busca em 100 páginas após ANEXO II ou ofício

**Se encontra:**
- ✅ Adiciona ao contexto
- Extrai número de ordem (se disponível)

**Se NÃO encontra:**
- ⚠️ Continua sem PROCESSAMENTO
- Tenta usar número de ordem do título

---

### **5. Verificação de Rejeição (Passo 6.1)**

**Lógica de Prioridade:**

```
1. TEM "PROCESSAMENTO COM INFORMAÇÃO"?
   SIM → ACEITO ✅ (não verifica rejeição)
   NÃO → vai para 2

2. TEM número de ordem?
   SIM → ACEITO ✅ (não verifica rejeição)
   NÃO → vai para 3

3. Busca "NOTA DE REJEIÇÃO"
   ENCONTROU → REJEITADO ❌
   NÃO ENCONTROU → ACEITO ✅ (por padrão)
```

**Se REJEITADO:**
- ✅ Marca `rejeitado=true`
- ✅ Extrai motivo da rejeição
- ✅ **CONTINUA processamento** (extrai o que for possível)
- ⚠️ Campos podem ficar null (ex: banco, agência, conta)

**⚠️ PROBLEMA IDENTIFICADO:**
- Ofício rejeitado pode TER valores (ex: Roberto R$ 52.228,43)
- MAS sistema não extrai porque:
  1. Não tem ANEXO II separado
  2. LLM não procura dados inline adequadamente
  3. PROCESSAMENTO tem nome diferente (Maria vs Roberto)

---

## 🐛 Caso do Roberto: O Que Aconteceu?

### **Situação:**
- PDF: `0037256-10.2015.8.26.0500.pdf`
- Pasta: `03730461893` (Roberto)
- 52 credores no PDF

### **Fluxo Executado:**

```
PASSO 1: CPF extraído ✅
└─> "037.304.618-93"

PASSO 2: Ofícios encontrados ✅
└─> 52 ofícios

PASSO 3: Ofício correto selecionado ✅
└─> Ofício #28 (página 39) - Roberto

PASSO 4: ANEXO II ✅ (fix funcionou!)
└─> Busca após página 39
└─> NÃO encontrado (dados inline no ofício)

PASSO 5: Número de ordem ❌
└─> NÃO encontrado no título

PASSO 6: PROCESSAMENTO ✅
└─> Encontrado na página 63
└─> Texto: "NOTA DE REJEIÇÃO"

PASSO 6.1: Verificação rejeição ✅
└─> Encontrou "NOTA DE REJEIÇÃO"
└─> Marcou rejeitado=true
└─> Motivo: "não foram individualizadas as verbas..."

PASSO 7: Texto montado ✅
└─> Ofício (página 39) + PROCESSAMENTO (página 63)

PASSO 8: Normalização ✅
└─> 12 valores normalizados

PASSO 9: LLM extração ❌ PROBLEMA!
└─> Recebeu:
    • Ofício: "Nome: Roberto Pereira da Cruz"
    • PROCESSAMENTO: "Requerente: Maria das Dores e outros"
└─> LLM escolheu: "Maria das Dores" ❌
└─> Motivo: "Requerente" parece mais oficial que "Nome"

PASSO 10: Validação ⚠️
└─> Dados extraídos: requerente="MARIA DAS DORES..."
└─> Valores: todos null
└─> Validação passou (campos opcionais)

PASSO 11: Resultado ❌
└─> sucesso=true (tecnicamente processou)
└─> MAS dados ERRADOS (credor errado, valores faltando)
```

---

## 🔍 Problemas Identificados

### **Problema 1: Conflito de Nomes (CRÍTICO)**

**Onde:**
- Ofício tem: "Nome: Roberto Pereira da Cruz"
- PROCESSAMENTO tem: "Requerente: Maria das Dores e outros"

**Por que acontece:**
- PROCESSAMENTO lista o **requerente GERAL** do processo
- Em PDFs multi-creditor, o requerente geral é diferente do credor específico
- LLM prioriza "Requerente" (campo oficial) sobre "Nome" (campo inline)

**Impacto:**
- ❌ Extrai nome errado
- ❌ CPF fica null (não encontra CPF de Maria no ofício de Roberto)
- ❌ Valores ficam null (LLM confuso com dados conflitantes)

---

### **Problema 2: Dados Inline Não Extraídos**

**Onde:**
- Ofício tem dados inline (sem ANEXO II separado):
  ```
  Credor nº.: 26
  Nome: Roberto Pereira da Cruz
  CPF/CNPJ: 037.304.618-93
  Valor requisitado: R$ 52.228,43
  ```

**Por que acontece:**
- Prompt menciona dados inline, MAS...
- LLM está confuso com conflito de nomes
- Sem ANEXO II, LLM não sabe onde procurar valores

**Impacto:**
- ❌ Valores não extraídos (mesmo estando no ofício)
- ❌ Dados bancários null (não há ANEXO II)

---

### **Problema 3: Ofícios Rejeitados Sem Dados Completos**

**Onde:**
- Ofício rejeitado pode TER valores
- Sistema marca rejeitado=true
- MAS não extrai valores disponíveis

**Por que acontece:**
- Rejeição não significa ausência de dados
- Rejeição = problema administrativo (ex: verbas não individualizadas)
- Valores EXISTEM no ofício, mas sistema não garante extração

**Impacto:**
- ⚠️ Perda de dados válidos
- ⚠️ Relatórios incompletos

---

## 🎯 Condições Não Previstas

### **1. PDF Multi-Creditor com PROCESSAMENTO Geral**

**Cenário:**
- 52 credores em um processo
- PROCESSAMENTO lista requerente geral (Maria + outros)
- Cada ofício tem credor específico (Roberto, João, etc.)

**Não previsto:**
- Sistema assume que "Requerente" no PROCESSAMENTO = credor do ofício
- Não filtra/ignora o campo "Requerente" do PROCESSAMENTO

**Solução necessária:**
- Ignorar "Requerente" do PROCESSAMENTO
- Usar APENAS "Nome" do ofício

---

### **2. Dados Inline em Ofícios Rejeitados**

**Cenário:**
- Ofício rejeitado
- Dados inline (sem ANEXO II)
- Valores presentes no ofício

**Não previsto:**
- Prompt não enfatiza extração de dados inline
- LLM não procura valores fora do ANEXO II

**Solução necessária:**
- Prompt mais explícito sobre dados inline
- Validação: se rejeitado E sem valores → tentar re-extração

---

### **3. ANEXO II de Outro Credor (RESOLVIDO v2.4.2)**

**Cenário:**
- PDF multi-creditor
- Cada credor tem ANEXO II
- Sistema pegava ANEXO II do primeiro credor

**Solução implementada:**
- ✅ Buscar ANEXO II APÓS ofício selecionado
- ✅ Evita pegar ANEXO II de credores anteriores

---

## 📊 Estatísticas do Caso Roberto

| Métrica | Valor | Status |
|---------|-------|--------|
| **Ofícios no PDF** | 52 | ✅ Detectados |
| **Ofício correto** | #28 (pág 39) | ✅ Selecionado |
| **CPF match** | 037.304.618-93 | ✅ Encontrado |
| **ANEXO II** | Não encontrado | ⚠️ Dados inline |
| **PROCESSAMENTO** | Página 63 | ✅ Encontrado |
| **Rejeição** | Sim | ✅ Detectada |
| **Nome extraído** | Maria (errado) | ❌ ERRO |
| **CPF extraído** | null | ❌ ERRO |
| **Valor extraído** | null | ❌ ERRO |

---

## 🔧 Próximos Passos Recomendados

### **Prioridade 1: Filtrar PROCESSAMENTO**
```python
# Remover campo "Requerente" do PROCESSAMENTO antes de enviar ao LLM
texto_proc_filtered = re.sub(
    r'Requerente[:\s]+[^\n]+',
    'Requerente: [VIDE OFÍCIO PARA CREDOR ESPECÍFICO]',
    texto_proc
)
```

### **Prioridade 2: Prompt Mais Explícito**
```
⚠️ MULTI-CREDITOR: Use "Nome:" do OFÍCIO, IGNORE "Requerente:" do PROCESSAMENTO
```

### **Prioridade 3: Validação CPF Pós-Extração**
```python
if cpf_extraido != cpf_esperado:
    logger.error("CPF mismatch - dados do credor errado!")
    # Tentar re-extração ou rejeitar
```

---

**Status:** 📋 **Documentado - Aguardando decisão de implementação**
