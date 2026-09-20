# Ferramentas Auxiliares — Revisa Precatório

**Revisado:** 20/09/2026 contra GitHub + banco vivo.

Ferramentas que **não fazem parte do pipeline principal** — apoio operacional interno.

---

## Índice

1. [Streamlit Backoffice (`6.UI_backoffice`)](#1-streamlit-backoffice)
2. [CPF Batch Processing (n8n)](#2-cpf-batch-processing)
3. [Dashboard legado do crawler](#3-dashboard-legado-do-crawler)
4. [Scripts de diagnóstico VPS](#4-scripts-de-diagnóstico-vps)

---

## 1. Streamlit Backoffice

**Repositório:** [`revisaprecatorio/6.UI_backoffice`](https://github.com/revisaprecatorio/6.UI_backoffice) (push: dez/2025)
**Estrutura:** `app/streamlit_app.py` (447 linhas), `deploy.sh`, `docker-compose.yml`
**Produção (referência):** `http://srv987902.hstgr.cloud:8502` | `https://revisaprecatorio.com.br/backoffice`

### O que é

Interface web interna para monitoramento dos processos — sem necessidade de queries SQL.

### ✅ View `vw_backoffice_processos` — recriada em 20/09/2026

A view havia sido perdida no wipe operacional (o app faz `SELECT * FROM vw_backoffice_processos` — `streamlit_app.py:99`). **Recriada** com todas as colunas que o app referencia, incluindo `valorizacao_percentual` (coluna **calculada** — não existe nas tabelas):

```sql
CREATE OR REPLACE VIEW vw_backoffice_processos AS
SELECT
    ce.id AS consulta_id,
    ce.current_state, ce.whatsapp_from, ce.whatsapp_phone_number,
    ce.email, ce.nome_requerente, ce.state_updated_at,
    edp.*,                                    -- 66 colunas OCR
    ecr.principal_final, ecr.juros_mora_final_corrigido,
    ecr.total_corrigido, ecr.regime_calculo,
    ecr.criado_em AS calculado_em,
    CASE WHEN ecr.total_corrigido IS NOT NULL
              AND edp.valor_total_requisitado > 0
         THEN ROUND((ecr.total_corrigido / edp.valor_total_requisitado - 1) * 100, 2)
    END AS valorizacao_percentual
FROM consultas_esaj ce
JOIN esaj_detalhe_processos edp ON edp.cpf = ce.cpf
LEFT JOIN esaj_calc_precatorio_resumo ecr
       ON ecr.cpf = edp.cpf AND ecr.numero_processo_cnj = edp.numero_processo_cnj;
```

> Colunas que o app usa: `current_state`, `cpf`, `credor_nome`, `numero_processo_cnj`, `valor_total_requisitado`, `saldo_final`, `rejeitado`, `motivo_rejeicao`, `anomalia`, `descricao_anomalia`, `obito`, `habilitacao_herdeiros`, `cpf_sucessor`, `preferencial`, `idoso`, `doenca_grave`, `pcd`, `process_calculo`, `timestamp_ingestao`, `principal_final`, `juros_mora_final_corrigido`, `total_corrigido`, `valorizacao_percentual`.

### Funcionalidades (conforme código)

- Tabs: Pipeline (por `current_state`), Cálculos (`total_corrigido`), Atenção (rejeitados/anomalias/óbito), Preferenciais (idoso/doença/PCD), Detalhes + export CSV
- Filtros: estado, status, preferências, busca por CPF/nome/processo

### Deploy (VPS Linux)

```bash
cd ~/6.UI_backoffice && ./deploy.sh   # git pull → docker build --no-cache → up -d → healthcheck
```

Env: `DB_HOST=72.60.62.124`, `DB_PORT=5432`, `DB_NAME=n8n`, `DB_USER`, `DB_PASSWORD`, `PDF_DIR`, `STREAMLIT_PORT=8502`.

---

## 2. CPF Batch Processing

**Workflow n8n:** `CPF_batch_processing` (`jMzstMZfztUMz7O6`, ativo)
**Webhook:** `POST https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing`
**Snapshot:** `n8n_workflows_live/CPF_batch_processing.json`

### O que é

Ingestão direta sem WhatsApp: recebe `{cpf}`, consulta o e-SAJ público e faz **upsert em `consultas_esaj` já como `PAYMENT_APPROVED`** — entra direto na fila do worker.

Marcadores do batch: `whatsapp_from='5511941455345'`, `mp_payment_id='BATCH_<epoch>'`, `mp_payment_amount=1.00`.

### Como usar

```bash
curl -s -X POST "https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing" \
  -H "Content-Type: application/json" \
  -d '{"cpf": "12345678900"}'
```

### Quando usar

| Situação | Usar? |
|---|---|
| Reprocessar CPF após erro | ✅ |
| Cliente por canal diferente | ✅ |
| Testes E2E sem conversa | ✅ |
| Inserção em lote (um POST por CPF) | ✅ |
| Novo cliente via WhatsApp | ❌ (Chatbot Revisa) |

### Limitações

- **Não coleta e-mail** — para laudo chegar ao cliente, garantir `consultas_esaj.email` preenchido (o webhook do laudo exige match `cpf`+`email`)
- WhatsApp de notificações iria para o número fixo da equipe
- Sem cobrança — uso interno apenas

---

## 3. Dashboard legado do crawler

`crawler_tjsp/core/dashboard.py` + `run_dashboard.bat`/`run_dashboard.py` — Streamlit antigo na VPS Windows (porta 8501). Usa `CALCULATION_IN_PROGRESS` e outras flags legadas. Substituído funcionalmente pelo `6.UI_backoffice`; manter apenas como referência.

## 4. Scripts de diagnóstico VPS

`assessment_pipeline/scripts/`:
- `diagnostico_vps.ps1` — diagnóstico completo da VPS Windows (crawler, Chrome, certificado, pastas)
- `diagnostico_vps_inline.ps1` — versão inline para execução remota rápida

Na VPS, utilitários do próprio repo: `runtime/crawler_watchdog.ps1`, `runtime/reset_runtime.ps1`, `windows-server/scripts/*` (chrome debug, export_certificado, testes de auth).
