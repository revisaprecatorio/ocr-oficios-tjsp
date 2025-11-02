# 📚 Documentação Técnica Completa: Pipeline OCR V3.0

**Data:** 01/11/2025 23:55  
**Versão:** V3.0  
**Objetivo:** Explicar lógica de execução, filtros, prompt LLM e cálculo de acurácia

---

## 📋 ÍNDICE

1. [Lógica de Execução Completa](#1-lógica-de-execução-completa)
2. [Filtros e Regras PRÉ-LLM](#2-filtros-e-regras-pré-llm)
3. [Prompt do LLM e Output Esperado](#3-prompt-do-llm-e-output-esperado)
4. [Lógica de Ofício Rejeitado](#4-lógica-de-ofício-rejeitado)
5. [Cálculo de Acurácia](#5-cálculo-de-acurácia)
6. [Racional e Balizadores](#6-racional-e-balizadores)

---

## 1. LÓGICA DE EXECUÇÃO COMPLETA

### 📊 Pipeline de Processamento (10 Etapas)

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRADA: PDF + CPF                                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 1: DETECÇÃO DE OFÍCIOS                                │
│ • Busca por "OFÍCIO REQUISITÓRIO" em TODAS as páginas       │
│ • Identifica início/fim de cada ofício                      │
│ • Resultado: Lista de N ofícios encontrados                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 2: VALIDAÇÃO DE CPF                                   │
│ • Verifica se CPF informado está em cada ofício             │
│ • Busca o CPF completo ou parcial no texto                  │
│ • Resultado: Ofício CORRETO identificado                    │
│ • ⚠️ FILTRO: Se CPF não encontrado → REJEITA                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 3: DETECÇÃO DE ANEXO II                               │
│ • Busca por "ANEXO II" nas páginas do ofício                │
│ • Valida presença de: CPF, Nome Credor, Valor              │
│ • Resultado: Página(s) do ANEXO II ou null                  │
│ • ⚠️ AVISO: ANEXO II ausente indica possível rejeição       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 4: DETECÇÃO DE PROCESSAMENTO                          │
│ • Busca por "PROCESSAMENTO" após ANEXO II                   │
│ • Extrai "Número de Ordem" (formato: XXX/YYYY)              │
│ • Resultado: Página PROCESSAMENTO + Número de Ordem         │
│ • ⚠️ REGRA: Sem número de ordem → pode ser rejeitado        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 5: DETECÇÃO DE REJEIÇÃO (CRÍTICO!)                    │
│ ⚠️ REGRAS DE ACEITAÇÃO (executadas ANTES de verificar       │
│    rejeição):                                               │
│                                                             │
│ ✅ SE TEM "PROCESSAMENTO COM INFORMAÇÃO" → ACEITO          │
│ ✅ SE TEM NÚMERO DE ORDEM → ACEITO                         │
│                                                             │
│ ⚠️ REGRAS DE REJEIÇÃO (só verificadas se NÃO aceito):      │
│                                                             │
│ ❌ SE TEM "NOTA DE REJEIÇÃO" → REJEITADO                   │
│ ❌ SE TEM "REJEIÇÃO" + motivo → REJEITADO                  │
│                                                             │
│ Resultado: oficio_rejeitado=true/false                      │
│           motivo_rejeicao=string ou null                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 6: MONTAGEM DO CONTEXTO (Páginas Relevantes)          │
│ • Texto do Ofício (páginas detectadas)                      │
│ • + Texto do ANEXO II (se encontrado)                       │
│ • + Texto do PROCESSAMENTO (se encontrado)                  │
│ • ⚠️ CHUNKING: Se >100 páginas → primeiras 50 + últimas 50 │
│ • ⚠️ CHUNKING AGRESSIVO: Se >200k chars → 30 + 30 páginas  │
│ Resultado: texto_relevante (string pronta para LLM)         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 7: EXTRAÇÃO LLM (Modo Híbrido)                        │
│ 1️⃣ TENTATIVA 1: Gemini 2.5 Flash (grátis, 1M context)      │
│    • Se sucesso → retorna dados                             │
│    • Se falha (quota/safety) → fallback OpenAI              │
│                                                             │
│ 2️⃣ FALLBACK: OpenAI GPT-4o-mini (pago, 128k context)       │
│    • Usa mesmo prompt                                       │
│    • Retorna dados estruturados (JSON)                      │
│                                                             │
│ ⚠️ PROMPT INCLUI (V3.0):                                    │
│    • Exemplos explícitos de valores brasileiros             │
│    • Regras de verificação obrigatória                      │
│    • Nota sobre rejeição (se aplicável)                     │
│                                                             │
│ Resultado: Dict[str, Any] com ~40 campos                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 8: VALIDAÇÃO PYDANTIC                                 │
│ • Valida tipos de dados (int, float, str, date)            │
│ • Valida formatos (CNJ, CPF, CNPJ, OAB)                    │
│ • Normaliza valores monetários (arredonda 2 decimais)       │
│ • Calcula tag IDOSO (se data_nascimento disponível)         │
│                                                             │
│ ⚠️ SE VALIDAÇÃO FALHAR:                                     │
│    • Tenta fallback OpenAI (se veio do Gemini)             │
│    • Se ambos falharem → retorna erro                       │
│                                                             │
│ Resultado: OficioRequisitorio (objeto validado)             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 9: SERIALIZAÇÃO E METADADOS                           │
│ • Converte Pydantic → Dict                                  │
│ • Adiciona metadados:                                       │
│   - cpf_fornecido                                           │
│   - caminho_pdf                                             │
│   - timestamp_ingestao                                      │
│   - process_diagnostico (tempo, modelo LLM usado)           │
│                                                             │
│ Resultado: Dict completo pronto para salvar                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ ETAPA 10: PERSISTÊNCIA (PostgreSQL)                         │
│ • UPSERT na tabela lista_processos                          │
│ • Chave: cpf + processo_origem                              │
│ • Atualiza se já existe, insere se novo                     │
│                                                             │
│ ⚠️ MODO TESTE: Se db_config não fornecido → não salva      │
│                                                             │
│ Resultado: Dados salvos no banco                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ SAÍDA: Dict com sucesso=true/false + dados ou erro          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. FILTROS E REGRAS PRÉ-LLM

### 🔍 Filtros de Validação (Ordem de Execução)

#### FILTRO 1: Validação de CPF no Ofício

```python
# Localização: detector.py → validar_cpf()
# Execução: ETAPA 2

REGRA:
- CPF informado DEVE estar presente no texto do ofício
- Busca CPF formatado: "123.456.789-00"
- OU CPF sem formatação: "12345678900"
- OU CPF parcial: "***456.789-**"

SE CPF NÃO ENCONTRADO:
    → Marca ofício como "CPF não encontrado"
    → Busca próximo ofício no PDF
    → Se nenhum ofício tem o CPF → ERRO

RESULTADO:
- oficio_correto: Dict com páginas e texto do ofício
- cpf_validado: True
```

#### FILTRO 2: Detecção de ANEXO II

```python
# Localização: detector_anexo.py → detectar_anexo_ii()
# Execução: ETAPA 3

REGRA:
- Busca palavra-chave "ANEXO II" nas páginas
- Valida presença de 3 elementos:
  1. CPF do credor
  2. Nome do credor
  3. Valor monetário (padrão R$ X.XXX,XX)

VALIDAÇÃO TRIPLA:
✅ tem_cpf: bool
✅ tem_credor: bool
✅ tem_valor: bool

SE TODOS = True:
    → ANEXO II confirmado
    → Retorna páginas do ANEXO II
SENÃO:
    → ANEXO II não encontrado
    → Retorna None (não é erro fatal)

RESULTADO:
- paginas_anexo: List[int] ou []
- texto_anexo: str ou None
```

#### FILTRO 3: Detecção de PROCESSAMENTO

```python
# Localização: detector_processamento.py → detectar_processamento()
# Execução: ETAPA 4

REGRA:
- Busca por "PROCESSAMENTO" após página do ANEXO II
- Valida presença de:
  • "DEPRE" ou "DIRETORIA DE EXECUÇÕES"
  • "Nº de Ordem" ou "Número do Precatório"

EXTRAÇÃO DE NÚMERO DE ORDEM:
- Padrão regex: (\d{1,5}/\d{4})
- Exemplo: "822/2026", "6475/2022", "2913/2023"

SE ENCONTRADO:
    → Extrai número de ordem
    → Retorna página do PROCESSAMENTO
SENÃO:
    → Busca no TÍTULO do ofício: "OFÍCIO REQUISITÓRIO Nº XXX/YYYY"
    → Se não encontrar em nenhum lugar → numero_ordem = None

RESULTADO:
- pagina_proc: int ou None
- numero_ordem_titulo: str ou None
- texto_proc: str ou None
```

#### FILTRO 4: Detecção de REJEIÇÃO (CRÍTICO!)

```python
# Localização: detector_processamento.py → eh_oficio_rejeitado()
# Execução: ETAPA 5

⚠️ ORDEM DE VERIFICAÇÃO IMPORTANTÍSSIMA:

PASSO 1: VERIFICAR ACEITAÇÃO (TEM PRIORIDADE!)
─────────────────────────────────────────────────
✅ SE texto contém "PROCESSAMENTO COM INFORMAÇÃO":
    → oficio_rejeitado = False
    → RETORNA IMEDIATAMENTE (não verifica rejeição)
    → LOG: "✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO"

✅ SE numero_ordem foi extraído (não é None):
    → oficio_rejeitado = False
    → RETORNA IMEDIATAMENTE
    → LOG: "✅ Número de ordem detectado → Ofício ACEITO"

PASSO 2: VERIFICAR REJEIÇÃO (SÓ SE NÃO PASSOU NO PASSO 1)
───────────────────────────────────────────────────────────
❌ SE texto contém "NOTA DE REJEIÇÃO":
    → oficio_rejeitado = True
    → Extrai motivo_rejeicao (próximos 200 chars após "NOTA DE REJEIÇÃO")
    → LOG: "⚠️ OFÍCIO REJEITADO detectado!"

❌ SE texto contém "irregularidade(s) passível(eis) de REJEIÇÃO":
    → oficio_rejeitado = True
    → Extrai motivo

SE NENHUMA REGRA ACIMA:
    → oficio_rejeitado = False (benefício da dúvida)

RESULTADO:
- oficio_rejeitado: bool
- motivo_rejeicao: str ou None
```

#### FILTRO 5: Chunking (Controle de Tamanho)

```python
# Localização: processador.py → processar_arquivo()
# Execução: ETAPA 6

REGRA 1: Chunking por Número de Páginas
────────────────────────────────────────
SE num_paginas > 100 AND sem_anexo_ii AND sem_processamento:
    → Aplica chunking: primeiras 50 + últimas 50 páginas
    → LOG: "🔧 Aplicando CHUNKING: primeiras 50 + últimas 50"

REGRA 2: Chunking por Tamanho de Caracteres
─────────────────────────────────────────────
MAX_CHARS = 200.000 (limite conservador para 128k tokens)

SE len(texto_relevante) > MAX_CHARS:
    → Aplica chunking agressivo: primeiras 30 + últimas 30 páginas
    → Re-adiciona ANEXO II e PROCESSAMENTO
    → LOG: "🔧 Aplicando CHUNKING AGRESSIVO"

EXCEÇÃO: Se GEMINI disponível (1M tokens de contexto)
    → NÃO aplica chunking
    → Envia texto completo

RESULTADO:
- texto_relevante: str (otimizado para LLM)
```

### 📊 Resumo dos Filtros PRÉ-LLM

| Filtro | Executado | Critério | Se Falhar |
|--------|-----------|----------|-----------|
| **CPF** | Sempre | CPF encontrado no ofício | Busca próximo ofício ou ERRO |
| **ANEXO II** | Sempre | 3 validações (CPF+Nome+Valor) | Aviso (não é erro fatal) |
| **PROCESSAMENTO** | Sempre | Título "PROCESSAMENTO" + indicadores | Busca no título do ofício |
| **NÚMERO DE ORDEM** | Sempre | Padrão XXX/YYYY | Marca como null (pode indicar rejeição) |
| **REJEIÇÃO** | Sempre | Prioridade: ACEITO antes de REJEITADO | Define flag rejeitado=true/false |
| **CHUNKING** | Condicional | >100 pág OU >200k chars | Reduz texto para LLM |

---

## 3. PROMPT DO LLM E OUTPUT ESPERADO

### 📝 Prompt LLM (V3.0)

O prompt é construído dinamicamente e contém:

#### PARTE 1: Instruções Gerais

```
Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!
```

#### PARTE 2: Nota de Rejeição (Se Aplicável)

```
⚠️ ATENÇÃO: Este ofício foi REJEITADO pelo DEPRE!
- Extraia apenas os dados disponíveis no documento
- Campos que não estiverem disponíveis devem ser null
- Não invente valores
- Marque rejeitado=true
```

#### PARTE 3: Nota de Anomalia (Se Texto Curto)

```
⚠️ ATENÇÃO: Documento muito curto ou com formato anômalo!
- Se o documento não seguir o padrão esperado, marque anomalia=true
- Descreva o problema encontrado em descricao_anomalia
- Extraia o que for possível
```

#### PARTE 4: Campos Obrigatórios

```
=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ (0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Formato XXXXX/YYYY (ex: "644/2015")
- valor_principal_liquido: Número decimal
- valor_principal_bruto: Número decimal
- juros_moratorios: Número decimal
- valor_total_requisitado: Número decimal
```

#### PARTE 5: Exemplos Explícitos (V3.0 - NOVO!)

```
⚠️⚠️⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Em português brasileiro, o PONTO (.) é separador de MILHARES 
e a VÍRGULA (,) é separador de DECIMAIS!

EXEMPLOS CORRETOS - SIGA EXATAMENTE ESTE PADRÃO:

NO PDF:              RETORNE COMO:
"R$ 73.431,66"    →  73431.66  (NUMBER, não string!)
"R$ 88.994,41"    →  88994.41  (NUMBER, não string!)
"R$ 1.234.567,89" →  1234567.89 (NUMBER, não string!)
"R$ 190.221,42"   →  190221.42  (NUMBER, não string!)
"R$ 177.969,22"   →  177969.22  (NUMBER, não string!)

❌❌❌ EXEMPLOS ERRADOS (NÃO FAÇA ISTO): ❌❌❌

"R$ 73.431,66"    →  73.43     ❌ ERRADO! (truncou)
"R$ 88.994,41"    →  88.99     ❌ ERRADO! (truncou)
"R$ 73.431,66"    →  "73431.66" ❌ ERRADO! (é string, deve ser NUMBER)

VERIFICAÇÃO OBRIGATÓRIA:
1. Todos valores monetários são NÚMEROS (type: number), NÃO strings
2. Valores realistas: R$ 1.000 a R$ 10.000.000 (se < R$ 100, REVISE!)
3. Líquido ≤ Bruto (se líquido > bruto, INVERTEU OS CAMPOS!)

ATENÇÃO - LÍQUIDO vs BRUTO:
- Valor Principal LÍQUIDO = APÓS descontos (sempre ≤ bruto)
- Valor Principal BRUTO = ANTES de descontos (sempre ≥ líquido)
```

#### PARTE 6: Campos Opcionais (40+ campos)

```
=== CAMPOS OPCIONAIS ===

DADOS BANCÁRIOS:
- banco, agencia, conta, conta_tipo
- dados_bancarios_advogado, cpf_titular_conta

CONTRIBUIÇÕES:
- contrib_previdenciaria_iprem
- contrib_previdenciaria_hspm

DATAS (YYYY-MM-DD):
- data_nascimento, data_base_atualizacao
- data_ajuizamento, data_transito_julgado

PREFERÊNCIAS (true/false):
- idoso, doenca_grave, pcd

... (continua com ~30 campos adicionais)
```

#### PARTE 7: Documento

```
[DOCUMENTO]
{texto_relevante}
[FIM DO DOCUMENTO]
```

### 📤 Output Esperado do LLM

#### Formato: JSON Flat (NÃO aninhado)

```json
{
  // OBRIGATÓRIOS
  "processo_origem": "0221126-48.2021.8.26.0500",
  "requerente_caps": "IZAURA BATISTA DA SILVA",
  "numero_ordem": "6475/2022",
  "valor_principal_liquido": 78384.27,
  "valor_principal_bruto": 78384.27,
  "juros_moratorios": 0.0,
  "valor_total_requisitado": 78384.27,
  
  // OPCIONAIS - Dados Bancários
  "banco": "341",
  "agencia": "3740",
  "conta": "00000001341-6",
  "conta_tipo": "corrente",
  "dados_bancarios_advogado": false,
  "cpf_titular_conta": "95653511820",
  
  // OPCIONAIS - Contribuições
  "contrib_previdenciaria_iprem": 648.14,
  "contrib_previdenciaria_hspm": 129.03,
  
  // OPCIONAIS - Datas
  "data_nascimento": "1957-10-16",
  "data_base_atualizacao": "2020-02-29",
  
  // OPCIONAIS - Preferências
  "idoso": true,
  "doenca_grave": false,
  "pcd": false,
  
  // OPCIONAIS - Controle
  "rejeitado": false,
  "motivo_rejeicao": null,
  "anomalia": false,
  "descricao_anomalia": null,
  
  // ... (outros campos opcionais)
}
```

#### Validação Pydantic (Pós-LLM)

Após receber o JSON do LLM, o `OficioRequisitorio` (Pydantic) aplica:

1. **Validação de Tipos:**
   - `valor_*`: float (obrigatório)
   - `processo_origem`: str com regex CNJ
   - `data_*`: date (formato YYYY-MM-DD)
   - `idoso`, `pcd`: bool

2. **Normalização de Valores:**
   - Arredondamento para 2 decimais (`arredondar_decimais`)
   - Remoção de espaços (`strip_strings`)
   - Conversão de CPF/CNPJ (`normalizar_cpf_cnpj`)

3. **Cálculo Automático:**
   - `idoso`: Se `data_nascimento` existe → calcula idade
   - Se idade ≥ 60 → `idoso = True`

---

## 4. LÓGICA DE OFÍCIO REJEITADO

### 🔴 Quando um Ofício é Marcado como Rejeitado?

#### REGRAS DE DECISÃO (Ordem CRÍTICA)

```
┌────────────────────────────────────────────────────────┐
│ VERIFICAÇÃO 1: TEM PROCESSAMENTO COM INFORMAÇÃO?       │
└────────────────────────────────────────────────────────┘
                      ↓ SIM
           ✅ OFÍCIO ACEITO (rejeitado=False)
           PARA POR AQUI (não verifica rejeição)
                      ↓ NÃO
┌────────────────────────────────────────────────────────┐
│ VERIFICAÇÃO 2: TEM NÚMERO DE ORDEM?                    │
└────────────────────────────────────────────────────────┘
                      ↓ SIM
           ✅ OFÍCIO ACEITO (rejeitado=False)
           PARA POR AQUI
                      ↓ NÃO
┌────────────────────────────────────────────────────────┐
│ VERIFICAÇÃO 3: TEM "NOTA DE REJEIÇÃO"?                 │
└────────────────────────────────────────────────────────┘
                      ↓ SIM
           ❌ OFÍCIO REJEITADO (rejeitado=True)
           Extrai motivo_rejeicao
                      ↓ NÃO
┌────────────────────────────────────────────────────────┐
│ VERIFICAÇÃO 4: TEM KEYWORDS DE REJEIÇÃO?               │
│ • "irregularidade(s) passível(eis) de REJEIÇÃO"        │
└────────────────────────────────────────────────────────┘
                      ↓ SIM
           ❌ OFÍCIO REJEITADO (rejeitado=True)
                      ↓ NÃO
           ✅ BENEFÍCIO DA DÚVIDA (rejeitado=False)
```

### 📋 Dados Disponíveis vs. Rejeitado

#### ✅ Ofício ACEITO (rejeitado=False)

**Dados SEMPRE Disponíveis:**
- ✅ `processo_origem` (do cabeçalho)
- ✅ `requerente_caps` (do cabeçalho)
- ✅ `numero_ordem` (da página PROCESSAMENTO)
- ✅ Todos os valores monetários (ANEXO II)
- ✅ Dados bancários (ANEXO II)
- ✅ Datas, advogado, credor (corpo do ofício)

**Exemplo Real (Aceito):**
```json
{
  "processo_origem": "0221126-48.2021.8.26.0500",
  "requerente_caps": "IZAURA BATISTA DA SILVA",
  "numero_ordem": "6475/2022",  ← PRESENTE!
  "valor_principal_liquido": 78384.27,
  "rejeitado": false
}
```

#### ❌ Ofício REJEITADO (rejeitado=True)

**Dados que NÃO Existem:**
- ❌ `numero_ordem` → **SEMPRE null** (nunca foi atribuído!)
- ❌ Página "PROCESSAMENTO" não tem número
- ❌ Tem apenas "NOTA DE REJEIÇÃO" em seu lugar

**Dados que AINDA Existem:**
- ✅ `processo_origem` (do cabeçalho)
- ✅ `requerente_caps` (do cabeçalho)
- ✅ Alguns valores (podem estar no corpo)
- ✅ `motivo_rejeicao` (texto explicando por que foi rejeitado)

**Exemplo Real (Rejeitado):**
```json
{
  "processo_origem": "0123456-78.2021.8.26.0500",
  "requerente_caps": "FULANO DE TAL",
  "numero_ordem": null,  ← SEMPRE NULL!
  "valor_principal_liquido": null,  ← Pode ser null
  "rejeitado": true,
  "motivo_rejeicao": "Falta de documentação bancária"
}
```

### 🔍 Por Que Número de Ordem NÃO Existe em Rejeitados?

**Fluxo do DEPRE (Diretoria de Execuções de Precatórios):**

1. **Ofício chega ao DEPRE**
   - DEPRE analisa documentação
   - Verifica se está tudo correto

2. **SE APROVADO:**
   - ✅ DEPRE atribui **Número de Ordem** (ex: 6475/2022)
   - ✅ Cria página "PROCESSAMENTO COM INFORMAÇÃO"
   - ✅ Ofício entra na fila de pagamento

3. **SE REJEITADO:**
   - ❌ DEPRE **NÃO atribui número**
   - ❌ Cria página "NOTA DE REJEIÇÃO"
   - ❌ Explica motivo da rejeição
   - ❌ Ofício volta para correção

**Conclusão:**
- `numero_ordem` é a **prova de aceitação**
- Sem `numero_ordem` → ofício não foi aceito pelo DEPRE
- Com `numero_ordem` → ofício aprovado e na fila

---

## 5. CÁLCULO DE ACURÁCIA

### 📊 Definição de Acurácia

**Acurácia = Percentual de processos onde TODOS os valores monetários extraídos estão corretos (ou quase corretos) quando comparados com um valor de referência.**

### 🎯 Balizador Utilizado

**Balizador:** CSV de exportação anterior (`2025-10-31T23-26_export.csv`)

- **O que é:** Arquivo CSV com 49 registros de processos já processados anteriormente
- **Origem:** Exportação do banco de dados PostgreSQL de produção
- **Data:** 31/10/2025
- **Campos usados para comparação:**
  - `cpf`
  - `numero_processo_cnj`
  - `valor_principal_liquido`
  - `valor_principal_bruto`
  - `juros_moratorios`
  - `valor_total_requisitado`

### 📐 Método de Cálculo

#### PASSO 1: Processar PDF com V3.0

```python
resultado = processador.processar_arquivo(
    pdf_path=caminho_pdf,
    cpf_numerico=cpf
)

valores_processados = {
    'liquido': resultado['dados']['valor_principal_liquido'],
    'bruto': resultado['dados']['valor_principal_bruto'],
    'juros': resultado['dados']['juros_moratorios'],
    'total': resultado['dados']['valor_total_requisitado']
}
```

#### PASSO 2: Buscar Valores de Referência no CSV

```python
ref_row = df_csv[
    (df_csv['cpf'] == cpf) & 
    (df_csv['numero_processo_cnj'] == processo)
]

valores_referencia = {
    'liquido': parse_valor(ref_row['valor_principal_liquido']),
    'bruto': parse_valor(ref_row['valor_principal_bruto']),
    'juros': parse_valor(ref_row['juros_moratorios']),
    'total': parse_valor(ref_row['valor_total_requisitado'])
}
```

#### PASSO 3: Comparar Valores (Campo por Campo)

```python
for campo in ['liquido', 'bruto', 'juros', 'total']:
    valor_processado = valores_processados[campo]
    valor_referencia = valores_referencia[campo]
    
    # Calcular diferença absoluta
    diferenca_abs = abs(valor_processado - valor_referencia)
    
    # Calcular diferença percentual
    if valor_referencia > 0:
        diferenca_pct = (diferenca_abs / valor_referencia) * 100
    else:
        diferenca_pct = 0
    
    # Classificar discrepância
    if diferenca_abs < 1.00:  # Tolerância de R$ 1,00
        status = "✅ PERFEITO"
    elif diferenca_pct < 1:
        status = "✅ ACEITÁVEL"
    elif diferenca_pct < 10:
        status = "⚠️ BAIXO"
    else:
        status = "❌ CRÍTICO"
```

#### PASSO 4: Determinar Status Geral do Processo

```python
if TODOS os campos são "✅ PERFEITO":
    status_geral = "✅ PERFEITO"
    
elif TODOS os campos são "✅ PERFEITO" ou "✅ ACEITÁVEL":
    status_geral = "✅ ACEITÁVEL"
    
elif ALGUM campo é "❌ CRÍTICO":
    status_geral = "❌ CRÍTICO"
    
else:
    status_geral = "⚠️ BAIXO"
```

#### PASSO 5: Calcular Estatísticas Globais

```python
total_processos = 51
processos_perfeitos = contagem de status_geral "✅ PERFEITO"
processos_aceitaveis = contagem de status_geral "✅ ACEITÁVEL"
processos_baixos = contagem de status_geral "⚠️ BAIXO"
processos_criticos = contagem de status_geral "❌ CRÍTICO"

# ACURÁCIA PERFEITA
acuracia_perfeita = (processos_perfeitos / total_processos) * 100

# TAXA DE SUCESSO
taxa_sucesso = ((processos_perfeitos + processos_aceitaveis) / total_processos) * 100
```

### 📊 Categorias de Status

| Categoria | Critério | Considerado para Taxa de Sucesso? |
|-----------|----------|-----------------------------------|
| ✅ **PERFEITO** | Diferença < R$ 1,00 em TODOS os campos | ✅ SIM |
| ✅ **ACEITÁVEL** | Diferença < 1% em TODOS os campos | ✅ SIM |
| ⚠️ **BAIXO** | Diferença entre 1% e 10% | ❌ NÃO |
| ❌ **CRÍTICO** | Diferença > 10% em ALGUM campo | ❌ NÃO |

### 🎯 Métricas Reportadas

#### 1. Taxa de Sucesso
```
Taxa de Sucesso = (PERFEITOS + ACEITÁVEIS) / TOTAL * 100

Exemplo V3.0:
(39 + 6) / 51 * 100 = 88.2%
```

#### 2. Acurácia Perfeita
```
Acurácia Perfeita = PERFEITOS / TOTAL * 100

Exemplo V3.0:
39 / 51 * 100 = 76.5%
```

#### 3. Casos Críticos
```
Casos Críticos = CRÍTICOS / TOTAL * 100

Exemplo V3.0:
6 / 51 * 100 = 11.8%
```

---

## 6. RACIONAL E BALIZADORES

### 🤔 Por Que Usar CSV como Balizador?

#### Vantagens:
1. ✅ **Dados Reais de Produção:** CSV veio do banco PostgreSQL em produção
2. ✅ **Contexto Histórico:** Mostra como sistema processava antes das melhorias
3. ✅ **Comparabilidade:** Permite medir evolução entre versões (V2 → V3)
4. ✅ **Reprodutibilidade:** Mesmos PDFs, mesmas referências

#### Desvantagens Descobertas:
1. ⚠️ **CSV Tem Erros:** Descobrimos 2 processos com valores truncados no CSV
2. ⚠️ **Versão Antiga:** CSV foi gerado com V2.3, não V2.5.1
3. ⚠️ **Incompleto:** CSV tem 49 processos, mas temos 51 PDFs

### 📏 Critérios de Tolerância

#### Por Que R$ 1,00 de Tolerância?

```
RAZÃO: Arredondamento do Pydantic

Exemplo:
- Valor no PDF: R$ 78.384,271
- LLM extrai: 78384.271
- Pydantic arredonda: 78384.27
- CSV (gerado antes): 78384.27
- Diferença: R$ 0,00 ✅

MAS se houve diferença de arredondamento entre versões:
- V2: 78384.27
- V3: 78384.28
- Diferença: R$ 0,01 ✅ (aceita com tolerância)
```

#### Por Que 1% de Diferença é "Aceitável"?

```
RAZÃO: Pequenas variações em descontos/taxas

Exemplo:
- Valor no PDF: R$ 100.000,00
- CSV: R$ 100.000,00
- V3 extraiu: R$ 100.500,00 (incluiu uma taxa extra)
- Diferença: R$ 500,00 (0,5%)
- Status: ✅ ACEITÁVEL

Isso pode acontecer se:
- LLM anterior não viu uma taxa
- LLM atual viu e incluiu corretamente
```

#### Por Que >10% é "Crítico"?

```
RAZÃO: Indica erro grave de parsing ou lógica

Exemplo:
- Valor real: R$ 73.431,66
- V2 extraiu: R$ 73,43 (truncou!)
- Diferença: R$ 73.358,23 (99.9%)
- Status: ❌ CRÍTICO

Valores com >10% de diferença indicam:
- Bug no parsing (caso do ponto decimal)
- Confusão de contexto (multi-ofício)
- Inversão de campos (líquido/bruto)
```

### 🔍 Limitações do Método Atual

1. **CSV não é "verdade absoluta":**
   - CSV tem erros (2 processos identificados)
   - CSV foi gerado com versão anterior (V2.3)

2. **Não valida TODOS os campos:**
   - Apenas 4 campos monetários são comparados
   - Campos como `banco`, `agencia`, `conta` não são validados

3. **Tolerância pode mascarar problemas:**
   - R$ 1,00 de diferença em R$ 1.000 = OK
   - R$ 1,00 de diferença em R$ 50 = 2% (deveria ser crítico?)

### ✅ Proposta de Melhoria Futura

#### Validação Tier 1: Valores Monetários
- Comparar com CSV (atual)
- Tolerância: R$ 1,00 ou 1%

#### Validação Tier 2: Dados Estruturados
- Validar CPF, banco, agência, conta
- Comparar com CSV
- Sem tolerância (exato ou erro)

#### Validação Tier 3: Campos Textuais
- Validar nomes, endereços
- Comparar similaridade de strings (fuzzy match)
- Tolerância: 90% similaridade

#### Validação Tier 4: Manual (Amostragem)
- Revisar manualmente 10% dos processos
- Comparar com PDF original
- Validação humana de campos críticos

---

## 📚 Resumo Executivo

### Pipeline em 3 Fases

1. **PRÉ-LLM (Filtros):**
   - Validação de CPF
   - Detecção de ANEXO II, PROCESSAMENTO
   - Detecção de REJEIÇÃO
   - Chunking de contexto

2. **LLM (Extração):**
   - Gemini 2.5 Flash (tentativa 1)
   - OpenAI GPT-4o-mini (fallback)
   - Prompt com exemplos explícitos (V3.0)
   - Retorna JSON flat (~40 campos)

3. **PÓS-LLM (Validação):**
   - Pydantic valida tipos e formatos
   - Normaliza valores (arredondamento)
   - Calcula flags (idoso)
   - Salva no PostgreSQL

### Lógica de Rejeição

```
TEM "PROCESSAMENTO COM INFORMAÇÃO"? → ACEITO ✅
TEM NÚMERO DE ORDEM? → ACEITO ✅
TEM "NOTA DE REJEIÇÃO"? → REJEITADO ❌
NENHUM DOS ACIMA? → ACEITO (benefício da dúvida) ✅
```

**Dados ausentes em rejeitados:**
- ❌ `numero_ordem` (SEMPRE null)
- ⚠️ Valores podem estar parcialmente disponíveis

### Cálculo de Acurácia

```
Acurácia Perfeita = Processos com diferença < R$ 1,00 / Total
Taxa de Sucesso = (Perfeitos + Aceitáveis <1%) / Total

V3.0 Resultados:
- Acurácia Perfeita: 76.5% (39/51)
- Taxa de Sucesso: 88.2% (45/51)
- Casos Críticos: 11.8% (6/51)
```

**Balizador:** CSV de exportação anterior (31/10/2025)  
**Tolerância:** R$ 1,00 absoluto ou 1% relativo  
**Limitação:** CSV tem erros conhecidos (2 processos)

---

**Criado por:** Claude Sonnet 4.5  
**Data:** 01/11/2025 23:55  
**Versão:** V3.0  
**Status:** ✅ DOCUMENTAÇÃO COMPLETA

