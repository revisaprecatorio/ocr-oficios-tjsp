# 📋 Schema Real da Tabela `esaj_detalhe_processos`

Documentação baseada no schema **real de produção** (verificado via `\d esaj_detalhe_processos` em Jun/2026).

---

## ⚠️ Status da Migration

> **ATENÇÃO:** A migration `05_migrate_to_v3_0.sql` (que removeria 23 colunas legadas) **nunca foi executada em produção**.
> O banco tem ~60 colunas — o schema ideal V3.0 (35 cols) existe no DDL mas não foi aplicado.
> As colunas legadas ficam NULL e não afetam o funcionamento. A limpeza é opcional.

Para aplicar a migration (operação de DROP, faça backup antes):
```bash
psql -h 72.60.62.124 -U admin -d n8n -f 2_ingestao/sql/05_migrate_to_v3_0.sql
```

---

## 📊 **Resumo**

- **Tabela:** `esaj_detalhe_processos`
- **Total de colunas (produção):** ~60 (verificado Jun/2026)
- **Colunas ativas (código V3.0):** ~37
- **Colunas legadas (migration pendente):** ~23 — sempre NULL
- **Primary Key:** `id` (SERIAL auto-increment)
- **Unique Constraint:** `(cpf, numero_processo_cnj)`
- **Banco:** PostgreSQL na VPS (72.60.62.124:5432)

---

## ✅ Colunas Ativas (usadas pelo código V3.0)

### 🔑 Identificação

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | integer | NO | Primary Key (auto-increment) |
| `cpf` | varchar(20) | YES | CPF do credor (sem formatação) |
| `numero_processo_cnj` | text | YES | Número CNJ do processo |
| `processo_origem` | text | YES | Número do processo de origem |
| `numero_ordem` | text | YES | Número de ordem do precatório (ex: "6475/2022") |
| `vara` | varchar(100) | YES | Vara responsável |

### 👤 Partes

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `credor_nome` | text | YES | Nome do credor |
| `credor_cpf_cnpj` | varchar(20) | YES | CPF ou CNPJ do credor |
| `devedor_ente` | text | YES | Ente devedor (ex: "Município de São Paulo") |

### 🏦 Dados Bancários

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `banco` | text | YES | Código/nome do banco |
| `agencia` | text | YES | Número da agência |
| `conta` | text | YES | Número da conta |

### 💰 Valores Financeiros

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `valor_principal_liquido` | numeric | YES | Valor principal líquido |
| `valor_principal_bruto` | numeric | YES | Valor principal bruto |
| `juros_moratorios` | numeric | YES | Juros moratórios |
| `valor_total_requisitado` | numeric | YES | Valor total requisitado |
| `saldo_final` | numeric | YES | Saldo final após pagamento (V2.5.2) |
| `data_saldo_final` | date | YES | Data do saldo final (V3.0.0) |
| `origem_saldo_final` | text | YES | Origem da extração do saldo (V3.0.0) |
| `origem_data_saldo_final` | text | YES | Origem da extração da data do saldo (V3.0.0) — verificar se existe |

### 📅 Datas

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `data_base_atualizacao` | date | YES | Data base para atualização monetária |
| `data_nascimento` | date | YES | Data de nascimento do credor |

### 🪦 Óbito e Sucessão (V2.5.3)

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `obito` | boolean | YES | false | Se o credor faleceu |
| `data_obito` | date | YES | NULL | Data do óbito |
| `cpf_sucessor` | varchar(20) | YES | NULL | CPF do herdeiro habilitado |

### 🎯 Preferências

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `idoso` | boolean | YES | false | Credor idoso (≥60 anos, calculado) |
| `doenca_grave` | boolean | YES | false | Doença grave detectada (V2.5.3) |
| `pcd` | boolean | YES | false | Pessoa com deficiência |

### 📜 Termos Jurídicos

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `preferencial` | boolean | YES | false | Credor preferencial |
| `habilitacao_herdeiros` | boolean | YES | false | Habilitação detectada (código 9270) |

### ⚠️ Status e Controle

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `rejeitado` | boolean | YES | false | Ofício rejeitado pelo DEPRE |
| `motivo_rejeicao` | text | YES | | Motivo da rejeição |
| `observacoes` | text | YES | | Observações gerais |
| `anomalia` | boolean | YES | false | Anomalia detectada |
| `descricao_anomalia` | text | YES | | Descrição da anomalia |

### 📂 Metadados

| Coluna | Tipo | Nullable | Default | Descrição |
|--------|------|----------|---------|-----------|
| `caminho_pdf` | text | YES | | Caminho relativo do PDF original |
| `timestamp_ingestao` | timestamp | YES | CURRENT_TIMESTAMP | Data/hora da importação |

---

## 🗂️ Colunas Legadas (migration `05_migrate_to_v3_0.sql` não executada)

> Estas colunas existem no banco mas **nunca são preenchidas pelo código V3.0**. São resquícios do schema V2.x. Sempre `NULL` em novos registros.

| Coluna | Motivo da remoção |
|--------|-------------------|
| `requerente_caps` | Substituído por `credor_nome` (V2.7.2) |
| `processo_execucao` | 0% preenchimento em todos os PDFs |
| `processo_conhecimento` | 0% preenchimento em todos os PDFs |
| `data_ajuizamento` | Substituído por `data_base_atualizacao` |
| `data_transito_julgado` | 0% preenchimento (V2.7.1) |
| `advogado_nome` | Removido V2.7.1 |
| `advogado_oab` | Removido V2.7.1 |
| `conta_tipo` | 0% preenchimento |
| `tipo_levantamento` | 0% preenchimento |
| `dados_bancarios_advogado` | 0% preenchimento |
| `cpf_titular_conta` | 0% preenchimento |
| `contrib_previdenciaria_iprem` | 0% preenchimento |
| `contrib_previdenciaria_hspm` | 0% preenchimento |
| `valor_compensado` | 0% preenchimento |
| `contribuicao_social` | 0% preenchimento |
| `salario_pericial` | 0% preenchimento |
| `assist_tecnico` | 0% preenchimento |
| `custas` | 0% preenchimento |
| `despesas` | 0% preenchimento |
| `multas` | 0% preenchimento |
| `cessao_credito` | Desativado V2.5.3, removido V3.0 |
| `process_diagnostico` | Nunca implementado |
| `process_calculo` | Nunca implementado |

---

## 🔍 Queries Úteis

### 1. Ver schema real

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'esaj_detalhe_processos'
ORDER BY ordinal_position;
```

### 2. Verificar colunas legadas ainda preenchidas

```sql
SELECT
  COUNT(CASE WHEN requerente_caps IS NOT NULL THEN 1 END) as requerente_caps,
  COUNT(CASE WHEN processo_execucao IS NOT NULL THEN 1 END) as processo_execucao,
  COUNT(CASE WHEN data_ajuizamento IS NOT NULL THEN 1 END) as data_ajuizamento,
  COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as cessao_credito
FROM esaj_detalhe_processos;
```

### 3. Estatísticas gerais

```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN rejeitado = TRUE THEN 1 END) as rejeitados,
  COUNT(CASE WHEN numero_ordem IS NOT NULL THEN 1 END) as com_numero_ordem,
  COUNT(CASE WHEN idoso = TRUE THEN 1 END) as idosos,
  ROUND(SUM(valor_total_requisitado), 2) as valor_total
FROM esaj_detalhe_processos;
```

### 4. Análise de saldo final (V3.0.0)

```sql
SELECT
  origem_saldo_final,
  COUNT(*) as total,
  COUNT(CASE WHEN saldo_final > 0 THEN 1 END) as com_saldo_positivo,
  ROUND(AVG(saldo_final), 2) as media
FROM esaj_detalhe_processos
GROUP BY origem_saldo_final
ORDER BY total DESC;
```

### 5. Condições especiais

```sql
SELECT
  COUNT(CASE WHEN idoso = TRUE THEN 1 END) as idosos,
  COUNT(CASE WHEN doenca_grave = TRUE THEN 1 END) as doenca_grave,
  COUNT(CASE WHEN pcd = TRUE THEN 1 END) as pcds,
  COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as preferenciais,
  COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as habilitacoes,
  COUNT(CASE WHEN obito = TRUE THEN 1 END) as obitos
FROM esaj_detalhe_processos;
```

### 6. Verificar falsos rejeitados

```sql
SELECT cpf, numero_processo_cnj, numero_ordem, rejeitado
FROM esaj_detalhe_processos
WHERE numero_ordem IS NOT NULL AND rejeitado = TRUE;
-- Resultado esperado: 0 registros
```

### 7. Últimos 10 processados

```sql
SELECT cpf, numero_processo_cnj, credor_nome,
       numero_ordem, rejeitado, timestamp_ingestao
FROM esaj_detalhe_processos
ORDER BY timestamp_ingestao DESC
LIMIT 10;
```

---

## 🔄 Histórico (schema)

| Versão | Data | Mudança |
|--------|------|---------|
| V3.0.0 | Mai/2026 | +`data_saldo_final`, `origem_saldo_final`, `origem_data_saldo_final` |
| V3.0.2 | Dez/2025 | Detecção REGEX-first para rejeições. Migration V3.0 **não executada em produção** |
| V3.0 | Dez/2025 | DDL: schema ideal com 35 cols. Migration `05_migrate_to_v3_0.sql` criada |
| V2.7.x | Dez/2025 | Removidos `requerente_caps`, `advogado_*`, `data_ajuizamento` do **código** (ainda no banco) |
| V2.5.3 | Nov/2025 | +`obito`, `data_obito`, `cpf_sucessor`, `doenca_grave`, `habilitacao_herdeiros` |
| V2.5.2 | Nov/2025 | +`saldo_final` |

---

**Última atualização:** 11/06/2026
**Schema de produção verificado em:** Jun/2026
**Colunas ativas:** ~37 | **Colunas legadas:** ~23 | **Total produção:** ~60
