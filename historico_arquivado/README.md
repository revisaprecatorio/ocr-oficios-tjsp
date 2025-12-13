# Histórico de Versões Arquivadas

Este diretório contém versões antigas, testes e outputs de desenvolvimento que foram arquivados durante a migração para V3.0 (13/12/2025).

## ⚠️ IMPORTANTE
**NÃO USAR EM PRODUÇÃO** - Apenas para referência histórica.

---

## 📂 Estrutura

### `v2_7_x/scripts/`
Scripts de desenvolvimento das versões 2.7.x:
- `processar_pipeline_v2_7*.py` - Pipelines de processamento
- `testar_v2_7_*.py` - Scripts de teste
- `teste_ab_v2_6_vs_v2_7.py` - Comparação de versões
- `validar_base_completa_v253.py` - Validação V2.5.3
- `processador_v2_7.py` - Processador antigo
- `detector_anexo_v2_7.py` - Detector de anexo antigo

**Ingestão:**
- `ingest_v2_7_1.py` - Primeira versão após V2.7
- `ingest_v2_7_2.py` - Remoção de requerente_caps
- ~~`ingest_v2_7_4.py`~~ - **MANTIDO** como baseline V3.0

### `v2_7_x/sql/`
Migrations SQL antigas:
- `03_add_saldo_final.sql` - Adição do campo saldo_final (V2.5.2)
- `03_migrate_to_v2_7_1.sql` - Migration V2.7.1
- `04_migrate_to_v2_7_2.sql` - Remoção de requerente_caps
- `04_view_old_backup.sql` - View antiga
- `migration_v2.5.3_add_obito_fields.sql` - Adição de campos de óbito

### `outputs_antigos/`
Outputs de testes intermediários:
- `outputs/` - Output vazio
- `outputs_v2_7_1_teste/` - Testes V2.7.1
- `outputs_v2_7_3_teste/` - Testes V2.7.3
- `outputs_v2_7_4/` - Processamento V2.7.4
- `outputs_v2_7_5/` - Testes V2.7.5
- `outputs_v2_7_final/` - Output final V2.7.x

### `docs_antigas/`
Documentação histórica:
- `ANALISE_ERROS_V2.md`
- `CORRECOES_IMPLEMENTADAS.md`
- `RELATORIO_V2.5.3_IMPLEMENTACAO.md`
- `RESULTADO_FINAL_V2.1.md`
- `RESUMO_EXECUTIVO_FINAL.md`
- `RESUMO_FINAL_V253.md`
- `RESUMO_RESULTADOS.md`
- `TESTE_MASSIVO.md`
- `VALIDACAO_ESTENDIDA.md`

---

## 📊 Histórico de Versões

### V2.7.6 (13/12/2025) - Stable Final v2
**Commit:** 1f4127b

**Fixes:**
- ✅ V2.7.5: detector_processamento - numero_ordem detection
- ✅ V2.7.6: detector_termos_juridicos - doenca_grave false positives

**Status:** STABLE - Baseline para V3.0

### V2.7.5 (13/12/2025)
Fix crítico: numero_ordem NULL
- Require ALL 3 fields (PROCESSAMENTO + DEPRE + numero_ordem)
- Reject "APROVAÇÃO DE REQUISITÓRIO"

### V2.7.4 (13/12/2025)
Fix LLM prompts após remoção de requerente_caps

### V2.7.2 (12/12/2025)
Remoção de requerente_caps (confusão em litisconsórcios)

### V2.7.1 (12/12/2025)
Fix data quality issues

### V2.5.3 (09/12/2025)
Detecção avançada de habilitação de herdeiros e doença grave

### V2.5.2 (04/12/2025)
Adição de saldo_final

---

## 🔄 Migração para V3.0

**Data:** 13/12/2025
**Baseline:** V2.7.6 (commit 1f4127b)

**Mudanças V3.0:**
- Schema: 50 → 35 colunas (-30%)
- Arquivos: 70 → 27 ativos (-62%)
- Fix: bug process_calculo em ingestion
- Estrutura: produção vs histórico separados

**Arquivos mantidos em produção:**
- `processador.py` V2.7.6
- `detector_processamento.py` V2.7.5
- `detector_termos_juridicos.py` V2.7.6
- `schemas.py` V2.7.2 → V3.0 (atualizado)
- `ingest_v2_7_4.py` → base para `ingest_v3_0.py`

---

**Para dúvidas sobre versões antigas, consulte:**
- Git history: `git log --all --oneline`
- Byterover: buscar por "V2.7.x"
- CHANGELOG.md do projeto principal
