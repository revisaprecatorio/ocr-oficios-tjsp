# 📋 Schema Completo da Tabela `esaj_detalhe_processos`

Documentação completa de todas as 49 colunas da tabela PostgreSQL.

---

## 📊 **Resumo**

- **Tabela:** `esaj_detalhe_processos`
- **Total de colunas:** 49
- **Primary Key:** `id` (auto-increment)
- **Unique Constraint:** `(cpf, numero_processo_cnj)`
- **Banco:** PostgreSQL na VPS (72.60.62.124:5432)

---

## 🔑 **Chaves e Identificadores**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | integer | NO | ID auto-incrementado (Primary Key) |
| `cpf` | varchar | NO | CPF do requerente (11 dígitos sem formatação) |
| `numero_processo_cnj` | varchar | NO | Número do processo no formato CNJ |
| `processo_origem` | varchar | NO | Número do processo de origem |

**Exemplo:**
```json
{
  "id": 1,
  "cpf": "02174781824",
  "numero_processo_cnj": "0035938-67.2018.8.26.0053",
  "processo_origem": "0035938-67.2018.8.26.0053"
}
```

---

## 👤 **Dados do Requerente**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `requerente_caps` | varchar | NO | Nome do requerente em MAIÚSCULAS |
| `data_nascimento` | date | YES | Data de nascimento do credor |
| `credor_nome` | varchar | YES | Nome do credor (pode diferir do requerente) |
| `credor_cpf_cnpj` | varchar | YES | CPF ou CNPJ do credor |

**Exemplo:**
```json
{
  "requerente_caps": "FERNANDO SANTOS ERNESTO",
  "data_nascimento": "1960-05-15",
  "credor_nome": "Fernando Santos Ernesto",
  "credor_cpf_cnpj": "021.747.818-24"
}
```

---

## 🏛️ **Dados do Processo**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `numero_ordem` | varchar | YES | Número de ordem do precatório (ex: "6475/2022") |
| `vara` | varchar | YES | Vara responsável pelo processo |
| `processo_execucao` | varchar | YES | Número do processo de execução |
| `processo_conhecimento` | varchar | YES | Número do processo de conhecimento |
| `devedor_ente` | varchar | YES | Ente devedor (ex: "Município de São Paulo") |

**Exemplo:**
```json
{
  "numero_ordem": "6475/2022",
  "vara": "1ª VARA DE FAZENDA PÚBLICA",
  "processo_execucao": "0035938-67.2018.8.26.0053",
  "processo_conhecimento": null,
  "devedor_ente": "MUNICÍPIO DE SÃO PAULO"
}
```

---

## 📅 **Datas**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `data_ajuizamento` | date | YES | Data de ajuizamento do processo |
| `data_transito_julgado` | date | YES | Data do trânsito em julgado |
| `data_base_atualizacao` | date | YES | Data base para atualização monetária |
| `data_nascimento` | date | YES | Data de nascimento do credor |

**Formato:** `YYYY-MM-DD` (ISO 8601)

**Exemplo:**
```json
{
  "data_ajuizamento": "2018-01-15",
  "data_transito_julgado": "2021-06-30",
  "data_base_atualizacao": "2022-03-01",
  "data_nascimento": "1960-05-15"
}
```

---

## 👨‍⚖️ **Dados do Advogado**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `advogado_nome` | varchar | YES | Nome do advogado |
| `advogado_oab` | varchar | YES | Número OAB/UF (ex: "OAB/SP 123.456") |

**Exemplo:**
```json
{
  "advogado_nome": "João da Silva",
  "advogado_oab": "OAB/SP 123.456"
}
```

---

## 🏦 **Dados Bancários (ANEXO II)**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `banco` | varchar | YES | Código do banco (3 dígitos) |
| `agencia` | varchar | YES | Número da agência |
| `conta` | varchar | YES | Número da conta |
| `conta_tipo` | varchar | YES | Tipo de conta ("corrente", "poupança") |
| `tipo_levantamento` | varchar | YES | Tipo de levantamento |
| `dados_bancarios_advogado` | boolean | YES | Se os dados bancários são do advogado |
| `cpf_titular_conta` | varchar | YES | CPF do titular da conta |

**Exemplo:**
```json
{
  "banco": "341",
  "agencia": "1234",
  "conta": "12345-6",
  "conta_tipo": "corrente",
  "tipo_levantamento": "Alvará",
  "dados_bancarios_advogado": false,
  "cpf_titular_conta": "021.747.818-24"
}
```

---

## 💰 **Valores Financeiros**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `valor_principal_liquido` | numeric | YES | Valor principal líquido |
| `valor_principal_bruto` | numeric | YES | Valor principal bruto |
| `juros_moratorios` | numeric | YES | Juros moratórios |
| `valor_total_requisitado` | numeric | YES | Valor total requisitado |
| `contrib_previdenciaria_iprem` | numeric | YES | Contribuição previdenciária IPREM |
| `contrib_previdenciaria_hspm` | numeric | YES | Contribuição previdenciária HSPM |
| `valor_compensado` | numeric | YES | Valor compensado |
| `contribuicao_social` | numeric | YES | Contribuição social |
| `salario_pericial` | numeric | YES | Salário pericial |
| `assist_tecnico` | numeric | YES | Assistente técnico |
| `custas` | numeric | YES | Custas processuais |
| `despesas` | numeric | YES | Despesas |
| `multas` | numeric | YES | Multas |

**Formato:** `DECIMAL(15,2)` - Valores em reais (R$)

**Exemplo:**
```json
{
  "valor_principal_liquido": 150000.00,
  "valor_principal_bruto": 180000.00,
  "juros_moratorios": 30000.00,
  "valor_total_requisitado": 210000.00,
  "contrib_previdenciaria_iprem": 5000.00,
  "contrib_previdenciaria_hspm": 3000.00,
  "valor_compensado": 0.00,
  "contribuicao_social": 2000.00,
  "salario_pericial": 1500.00,
  "assist_tecnico": 800.00,
  "custas": 500.00,
  "despesas": 300.00,
  "multas": 0.00
}
```

---

## 🎯 **Preferências e Prioridades**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `idoso` | boolean | YES | Se o requerente é idoso (≥60 anos) |
| `doenca_grave` | boolean | YES | Se o requerente tem doença grave |
| `pcd` | boolean | YES | Se o requerente é PCD |

**Cálculo automático:**
- `idoso`: Calculado a partir de `data_nascimento` (idade ≥ 60 anos)

**Exemplo:**
```json
{
  "idoso": true,
  "doenca_grave": false,
  "pcd": false
}
```

---

## ⚠️ **Status e Controle**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `rejeitado` | boolean | YES | Se o ofício foi rejeitado pelo DEPRE |
| `motivo_rejeicao` | text | YES | Motivo da rejeição (se aplicável) |
| `observacoes` | text | YES | Observações gerais |
| `anomalia` | boolean | YES | Se há alguma anomalia detectada |
| `descricao_anomalia` | text | YES | Descrição da anomalia |
| `process_diagnostico` | boolean | YES | Se requer diagnóstico adicional |

**Regra importante:**
- Se `numero_ordem` existe → `rejeitado` deve ser `FALSE`
- Se `rejeitado` é `TRUE` → `numero_ordem` deve ser `NULL`

**Exemplo (Aceito):**
```json
{
  "rejeitado": false,
  "motivo_rejeicao": null,
  "observacoes": "Processamento normal",
  "anomalia": false,
  "descricao_anomalia": null,
  "process_diagnostico": false
}
```

**Exemplo (Rejeitado):**
```json
{
  "rejeitado": true,
  "motivo_rejeicao": "Documentação incompleta",
  "observacoes": "Falta certidão de trânsito em julgado",
  "anomalia": false,
  "descricao_anomalia": null,
  "process_diagnostico": true
}
```

---

## 📂 **Metadados e Auditoria**

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `caminho_pdf` | text | YES | Caminho relativo para o PDF original |
| `timestamp_ingestao` | timestamp | YES | Data/hora da importação no banco |

**Exemplo:**
```json
{
  "caminho_pdf": "../data/consultas/02174781824/0035938-67.2018.8.26.0053.pdf",
  "timestamp_ingestao": "2025-10-16T00:24:02.123456"
}
```

---

## 🔍 **Queries Úteis**

### **1. Listar todas as colunas**

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'esaj_detalhe_processos'
ORDER BY ordinal_position;
```

### **2. Verificar falsos rejeitados**

```sql
SELECT cpf, numero_processo_cnj, numero_ordem, rejeitado
FROM esaj_detalhe_processos
WHERE numero_ordem IS NOT NULL 
  AND rejeitado = TRUE;
```

**Resultado esperado:** 0 registros (após correção v2.2.0)

### **3. Estatísticas por status**

```sql
SELECT 
  COUNT(*) as total,
  COUNT(CASE WHEN rejeitado = TRUE THEN 1 END) as rejeitados,
  COUNT(CASE WHEN numero_ordem IS NOT NULL THEN 1 END) as com_numero_ordem,
  COUNT(CASE WHEN idoso = TRUE THEN 1 END) as idosos,
  SUM(valor_total_requisitado) as valor_total
FROM esaj_detalhe_processos;
```

### **4. Processos com dados bancários completos**

```sql
SELECT cpf, numero_processo_cnj, requerente_caps,
       banco, agencia, conta, conta_tipo
FROM esaj_detalhe_processos
WHERE banco IS NOT NULL 
  AND agencia IS NOT NULL 
  AND conta IS NOT NULL;
```

### **5. Últimos 10 processados**

```sql
SELECT cpf, numero_processo_cnj, requerente_caps,
       numero_ordem, rejeitado, timestamp_ingestao
FROM esaj_detalhe_processos
ORDER BY timestamp_ingestao DESC
LIMIT 10;
```

---

## ✅ **Validações Implementadas**

### **1. Pydantic Schema**

Todas as colunas são validadas pelo schema `OficioRequisitorio` em `1_parsing_PDF/app/schemas.py`:

- ✅ Formato CNJ para `processo_origem`
- ✅ CPF/CNPJ válido para `credor_cpf_cnpj`
- ✅ Datas no formato ISO (YYYY-MM-DD)
- ✅ Valores numéricos sem formatação (sem R$, sem pontos de milhar)
- ✅ Requerente sempre em MAIÚSCULAS

### **2. Constraints PostgreSQL**

```sql
-- Primary Key
PRIMARY KEY (id)

-- Unique Constraint
UNIQUE (cpf, numero_processo_cnj)

-- Not Null
cpf NOT NULL
numero_processo_cnj NOT NULL
processo_origem NOT NULL
requerente_caps NOT NULL
```

### **3. Validação de Negócio**

- ✅ Se `numero_ordem` existe → `rejeitado = FALSE`
- ✅ Se `rejeitado = TRUE` → `numero_ordem = NULL`
- ✅ `idoso` calculado automaticamente a partir de `data_nascimento`

---

## 📊 **Estatísticas Atuais (16/10/2025)**

```
Total de registros: 50
Com número de ordem: 26
Rejeitados: 16
Falsos rejeitados: 0 ✅
Taxa de correção: 100%
```

---

## 🔄 **Histórico de Mudanças**

### **v2.2.0 (16/10/2025)**
- ✅ Adicionadas 11 colunas faltantes no Streamlit
- ✅ Correção de falsos rejeitados (0 casos)
- ✅ Documentação completa do schema

### **v2.1.0 (14/10/2025)**
- ✅ Interface Streamlit otimizada
- ✅ Todas as 49 colunas disponíveis

---

## 📝 **Notas Importantes**

1. **Data de Nascimento:** Campo `data_nascimento` é capturado pelo GPT-4o-mini e usado para calcular `idoso`
2. **Dados Bancários:** Extraídos do ANEXO II quando disponível
3. **Valores Financeiros:** Sempre em formato decimal sem formatação (ex: 150000.00)
4. **Datas:** Sempre no formato ISO (YYYY-MM-DD)
5. **Requerente:** Sempre em MAIÚSCULAS conforme padrão TJSP

---

**Última atualização:** 16/10/2025  
**Versão:** 2.2.0
