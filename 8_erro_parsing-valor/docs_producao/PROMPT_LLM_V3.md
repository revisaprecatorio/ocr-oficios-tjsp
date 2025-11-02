# 📝 Prompt LLM V3.0 - Documentação Completa

**Versão:** V3.0  
**Data:** 02/11/2025  
**Modelo:** GPT-4o-mini (primary) + Gemini 2.5 Flash (fallback)

---

## 🎯 Objetivo

Este documento contém o prompt completo usado na extração estruturada de dados de Ofícios Requisitórios do TJSP.

---

## 📋 Prompt Completo

O prompt é construído dinamicamente em `processador.py` → `_construir_prompt_llm()`.

### Estrutura do Prompt

```python
Prompt = Instruções Gerais
        + Nota de Rejeição (se aplicável)
        + Nota de Anomalia (se texto curto)
        + Campos Obrigatórios
        + Exemplos Explícitos V3.0
        + Campos Opcionais
        + Regras Críticas
        + Documento (texto extraído)
```

---

## 📄 Conteúdo Detalhado

### Parte 1: Instruções Gerais

```
Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!
```

### Parte 2: Nota de Rejeição (Condicional)

```
⚠️ ATENÇÃO: Este ofício foi REJEITADO pelo DEPRE!
- Extraia apenas os dados disponíveis no documento
- Campos que não estiverem disponíveis devem ser null
- Não invente valores
- Marque rejeitado=true
```

**Quando:** Apenas se `oficio_rejeitado=True`

### Parte 3: Nota de Anomalia (Condicional)

```
⚠️ ATENÇÃO: Documento muito curto ou com formato anômalo!
- Se o documento não seguir o padrão esperado, marque anomalia=true
- Descreva o problema encontrado em descricao_anomalia
- Extraia o que for possível
```

**Quando:** Apenas se `len(texto_oficio) < 500 chars`

### Parte 4: Campos Obrigatórios

```
=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)
  ⚠️ ATENÇÃO - DIFERENÇA CRÍTICA:
  * CORRETO: "644/2015", "2913/2023", "12345/2024" (formato: números/ano)
  * ERRADO: "0181657-92.2021.8.26.0500" (isso é número do PROCESSO, não número de ordem!)
  * Buscar no TÍTULO: "OFÍCIO REQUISITÓRIO Nº XXX/YYYY"
  * OU na seção "PROCESSAMENTO": "Nº de Ordem: XXX/YYYY" ou "Ordem: XXX/YYYY"
  * Se NÃO encontrar o número de ordem, retorne null (não invente!)
- valor_principal_liquido: Valor principal líquido (número decimal)
- valor_principal_bruto: Valor principal bruto (número decimal)
- juros_moratorios: Juros moratórios (número decimal)
- valor_total_requisitado: Valor total requisitado (número decimal)
```

### Parte 5: Exemplos Explícitos V3.0 (CRÍTICO!)

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

"R$ 73.431,66"    →  73.43     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 88.994,41"    →  88.99     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 73.431,66"    →  "73431.66" ❌ ERRADO! (é string, deve ser NUMBER)
"R$ 177.969,22"   →  17796     ❌ ERRADO! (esqueceu decimais)

VERIFICAÇÃO OBRIGATÓRIA:
1. Todos valores monetários são NÚMEROS (type: number), NÃO strings
2. Valores realistas: R$ 1.000 a R$ 10.000.000 (se < R$ 100, REVISE!)
3. Líquido ≤ Bruto (se líquido > bruto, INVERTEU OS CAMPOS!)

ATENÇÃO - LÍQUIDO vs BRUTO:
- Valor Principal LÍQUIDO = APÓS descontos (sempre ≤ bruto)
- Valor Principal BRUTO = ANTES de descontos (sempre ≥ líquido)
```

**IMPORTANTE:** Esta parte foi adicionada na V3.0 e resolveu o bug crítico #4!

### Parte 6: Campos Opcionais (~40 campos)

```
=== CAMPOS OPCIONAIS (nível raiz do JSON) ===

DADOS BANCÁRIOS (ANEXO II):
- banco: Código do banco (apenas números, ex: 341)
- agencia: Número da agência
- conta: Número da conta (com dígito)
- conta_tipo: Tipo de conta (corrente/poupança)
- dados_bancarios_advogado: Se dados são do advogado (true/false)
- cpf_titular_conta: CPF do titular da conta

CONTRIBUIÇÕES:
- contrib_previdenciaria_iprem: INST.PREV. ou IPREMSAOPAULO (número)
- contrib_previdenciaria_hspm: ASSIST.MÉD. ou HSPMSAOPAULO (número)

DATAS (formato YYYY-MM-DD):
- data_nascimento: Data de nascimento do credor
- data_base_atualizacao: Data base para atualização
- data_ajuizamento: Data de ajuizamento
- data_transito_julgado: Data do trânsito em julgado

PREFERÊNCIAS (true/false):
- idoso: Credor com mais de 60 anos
- doenca_grave: Portador de doença grave
- pcd: Pessoa com deficiência

OUTROS VALORES:
- tipo_levantamento: Tipo de levantamento
- valor_compensado: Valor compensado (número)
- contribuicao_social: Contribuição social (número)
- salario_pericial: Salário pericial (número)
- assist_tecnico: Assistente técnico (número)
- custas: Custas (número)
- despesas: Despesas (número)
- multas: Multas (número)

OUTRAS INFORMAÇÕES:
- vara: Vara responsável
- credor_nome: Nome do credor
- credor_cpf_cnpj: CPF/CNPJ do credor
- devedor_ente: Ente devedor
- advogado_nome: Nome do advogado
- advogado_oab: OAB do advogado

CONTROLE:
- rejeitado: Se o ofício foi rejeitado (true/false)
- motivo_rejeicao: Motivo da rejeição (se houver)
- anomalia: Se o PDF tem formato anômalo (true/false)
- descricao_anomalia: Descrição do problema encontrado (se houver)
```

### Parte 7: Regras Críticas

```
=== REGRAS CRÍTICAS ===

1. ESTRUTURA: JSON FLAT (todos os campos no nível raiz, SEM objetos aninhados)
2. Campos não encontrados = null
3. Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
4. Datas: formato YYYY-MM-DD
5. Requerente: SEMPRE em MAIÚSCULAS
6. Booleanos: true ou false (minúsculas)
7. Número de ordem: buscar na seção "PROCESSAMENTO" (formato: XXX/YYYY)
```

### Parte 8: Documento

```
DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido:
```

---

## 🔧 Uso no Código

**Localização:** `1_parsing_PDF/app/processador.py` → método `_construir_prompt_llm()`

**Parâmetros:**
- `texto_oficio`: Texto completo extraído do PDF
- `tem_anexo_ii`: Se ANEXO II foi detectado
- `tem_processamento`: Se PROCESSAMENTO foi detectado
- `numero_ordem_titulo`: Número extraído do título (PDFs antigos)
- `oficio_rejeitado`: Flag de rejeição
- `motivo_rejeicao`: Texto do motivo (se houver)

**Retorno:** String completa do prompt pronto para envio ao LLM

---

## 📊 Versões

### V3.0 (Atual - 02/11/2025)
- ✅ Adicionados exemplos explícitos de valores brasileiros
- ✅ Verificações obrigatórias (líquido ≤ bruto)
- ✅ Validação de tipos (number vs string)

### V2.5.1 (Anterior - 01/11/2025)
- ✅ Modo híbrido Gemini + OpenAI
- ✅ Detecção de ANEXO II e PROCESSAMENTO
- ❌ Sem exemplos explícitos (bug do ponto decimal)

### V2.0 (Inicial)
- ✅ Estrutura básica
- ✅ Campos obrigatórios definidos

---

## 🎯 Melhorias Implementadas

### Bug Crítico #4 Resolvido

**Problema:**
```
PDF: "R$ 73.431,66"
V2.5.1 extraiu: 73.43 (erro 99.9%)
```

**Solução V3.0:**
```
Exemplos explícitos no prompt:
"R$ 73.431,66" → 73431.66 (NUMBER)
```

**Resultado:**
```
V3.0 extraiu: 73431.66 (100% correto!)
```

---

## 📝 Notas de Manutenção

1. **Nunca remover os exemplos explícitos** - Eles são críticos para parsing correto
2. **Manter estrutura FLAT** - Objetos aninhados quebram validação Pydantic
3. **Atualizar exemplos** se novos padrões forem descobertos
4. **Testar com PDFs reais** após qualquer modificação

---

**Criado por:** Claude Sonnet 4.5  
**Versão:** V3.0  
**Status:** ✅ EM PRODUÇÃO

