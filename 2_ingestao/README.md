# Fase 2: Ingestão PostgreSQL

**Versão:** V3.0 | **Atualizado:** 13/12/2025  
**Etapa:** 2 de 2 do pipeline OCR (JSONs → PostgreSQL)

Recebe os JSONs gerados pela Etapa 1 (`1_parsing_PDF/outputs/json/`) e insere/atualiza os registros na tabela `esaj_detalhe_processos` via upsert.

Chamado automaticamente pelo `pipeline_completo.sh` — pode também ser executado manualmente.

---

## Estrutura de Arquivos

```
2_ingestao/
├── scripts/
│   ├── ingest_all_jsons.py           # Script principal de ingestão (V7 — produção)
│   ├── ingest_v3_0.py                # Versão V3.0 alternativa
│   ├── ingest_all_jsons_1301_550.py  # Variante de lote parcial (uso pontual)
│   ├── recalcular_idoso.py           # Recalcula tag idoso pós-ingestão
│   ├── recriar_tabela_v3.py          # Recria tabela via Python (alternativa ao psql)
│   └── test_connection.py            # Teste de conexão com o banco
├── sql/
│   ├── 01_create_table.sql           # DDL — esaj_detalhe_processos V3.0 (35 colunas)
│   ├── 02_create_indexes.sql         # Índices de performance
│   ├── 03_test_queries.sql           # Queries de validação pós-ingestão
│   ├── 04_view_precatorios_full.sql  # View vw_precatorios_full (OCR + calc)
│   └── 05_migrate_to_v3_0.sql        # Migration V2.7.6 → V3.0
├── historico_evolucao_anteriores/    # Scripts V2.x arquivados
├── requirements.txt                  # psycopg2-binary, tqdm, python-dotenv
└── .env.example                      # Template de variáveis de ambiente
```

---

## Tabela `esaj_detalhe_processos`

**Schema:** V3.0 (35 colunas) | **Chave única:** `(cpf, numero_processo_cnj)`

Ver DDL completo em `sql/01_create_table.sql`. Schema documentado em `assessment_pipeline/01_ARQUITETURA_GERAL.md`.

---

## Como usar

### 1. Configurar `.env`

```bash
cp .env.example .env
# Preencher DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
```

### 2. Criar tabela (primeira vez)

```bash
python scripts/test_connection.py
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f sql/01_create_table.sql
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f sql/02_create_indexes.sql
```

### 3. Ingerir JSONs

```bash
# Via pipeline completo (recomendado)
cd ..
./pipeline_completo.sh

# Ou manualmente
python scripts/ingest_all_jsons.py --input ../1_parsing_PDF/outputs/json
```

### 4. Recalcular tag idoso (pós-ingestão)

```bash
python scripts/recalcular_idoso.py
```

### 5. Validar

```sql
-- Via psql
\i sql/03_test_queries.sql

-- Verificação rápida
SELECT COUNT(*), SUM(CASE WHEN rejeitado THEN 1 ELSE 0 END) AS rejeitados
FROM esaj_detalhe_processos;
```

---

## Scripts

| Script | Função |
|---|---|
| `ingest_all_jsons.py` | Produção: lê JSONs, normaliza, upsert com COALESCE (protege dados existentes) |
| `ingest_v3_0.py` | Versão V3.0 com campos `origem_saldo_final` / `origem_data_saldo_final` |
| `recalcular_idoso.py` | Recalcula `idoso = TRUE` para credores com `data_nascimento` indicando idade ≥ 60 |
| `recriar_tabela_v3.py` | DROP + CREATE da tabela via Python (use só em ambiente de dev/reset) |
| `test_connection.py` | Testa conectividade com o banco e exibe versão do PostgreSQL |

---

## SQL

| Arquivo | Conteúdo |
|---|---|
| `01_create_table.sql` | DDL V3.0 — 35 colunas, constraints, comments |
| `02_create_indexes.sql` | Índices em `cpf`, `rejeitado`, `vara`, `idoso`, `doenca_grave`, `pcd` |
| `03_test_queries.sql` | Queries de validação pós-ingestão (totais, distribuições, anomalias) |
| `04_view_precatorios_full.sql` | `vw_precatorios_full`: join OCR + `esaj_calc_precatorio_resumo` |
| `05_migrate_to_v3_0.sql` | Migration incremental V2.7.6 → V3.0 (DROP colunas obsoletas) |
