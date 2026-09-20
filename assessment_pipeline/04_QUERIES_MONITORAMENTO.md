# Queries de Monitoramento — logs e process_tracking

**Revisado:** 20/09/2026 — **todas as queries corrigidas para o schema real** do banco `n8n` (`72.60.62.124:5432`).

> ⚠️ **Colunas corretas:** `process_tracking` usa **`timestamp_evento`** (não `created_at`), **`detalhes`** jsonb (não `metadata`) e **`concluido`** (não `sucesso`). `consultas_esaj` tem `whatsapp_from` **e** `whatsapp_phone_number` (mesmo valor). `REPORT_SENT` é terminal — laudo completo vs. parcial se distingue em `process_tracking`.

Tabelas: `logs`, `process_tracking`, `consultas_esaj`, `esaj_detalhe_processos`, `esaj_calc_precatorio_resumo`, `vw_precatorios_full`, `view_processados`.

---

## BLOCO 1 — Visão Geral do Pipeline

### Q01 — Contagem de jobs por estado atual

```sql
SELECT
    current_state,
    COUNT(*) AS total,
    MIN(state_updated_at) AS mais_antigo,
    MAX(state_updated_at) AS mais_recente
FROM consultas_esaj
GROUP BY current_state
ORDER BY total DESC;
```

> Interpretação: `REPORT_SENT` = concluído (verificar desfecho no tracking); `ALERTA_MANUAL_SENT` = aguardando tratamento manual; `PAYMENT_APPROVED` antigo = worker parado.

---

### Q02 — Jobs travados em PROCESSING (possível crash do worker)

```sql
SELECT
    id, cpf, state_updated_at,
    NOW() - state_updated_at AS tempo_travado
FROM consultas_esaj
WHERE current_state = 'PROCESSING'
  AND state_updated_at < NOW() - INTERVAL '1 hour'
ORDER BY state_updated_at;
```

**Ação:** verificar se worker está rodando na VPS; se não, resetar para `PAYMENT_APPROVED`.

---

### Q03 — Funil de conversão (últimos 7 dias)

```sql
SELECT
    COUNT(*) FILTER (WHERE cpf <> '00000000000')                                   AS consultas_reais,
    COUNT(*) FILTER (WHERE current_state NOT IN ('AWAITING_EMAIL','AWAITING_CODE',
             'AWAITING_CONFIRMATION') AND cpf <> '00000000000')                    AS passaram_da_captacao,
    COUNT(*) FILTER (WHERE current_state IN ('PROCESSING','REPORT_SENT',
             'FINAL_REPORT_SENT','PARTIAL_REPORT_SENT','PIPELINE_ERROR','AUTH_ERROR',
             'DOWNLOAD_FAILED','CALC_ERROR','MANUAL_PROCESS','ALERTA_MANUAL_SENT',
             'NO_VALID_PROCESS'))                                                  AS pagamento_aprovado,
    COUNT(*) FILTER (WHERE current_state = 'REPORT_SENT')                          AS pipeline_concluido,
    COUNT(*) FILTER (WHERE current_state IN ('PIPELINE_ERROR','AUTH_ERROR',
             'DOWNLOAD_FAILED','CALC_ERROR'))                                      AS falhas_tecnicas,
    COUNT(*) FILTER (WHERE current_state IN ('MANUAL_PROCESS','ALERTA_MANUAL_SENT')) AS intervenção_manual
FROM consultas_esaj
WHERE state_updated_at >= NOW() - INTERVAL '7 days';
```

> Para laudos completos vs. parciais, usar Q07 (tracking).

---

## BLOCO 2 — Erros de OCR

### Q04 — Todos os erros de OCR (últimos 30 dias)

```sql
SELECT
    pt.timestamp_evento::date AS data,
    pt.cpf,
    pt.mensagem_erro,
    pt.detalhes->>'processo' AS processo_falhou,
    pt.detalhes->>'workflow' AS workflow,
    ce.current_state AS estado_atual_job
FROM process_tracking pt
LEFT JOIN consultas_esaj ce ON pt.consulta_id = ce.id
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND pt.timestamp_evento >= NOW() - INTERVAL '30 days'
ORDER BY pt.timestamp_evento DESC;
```

---

### Q05 — PDFs antigos "700" detectados

```sql
SELECT
    pt.timestamp_evento::date AS data,
    pt.cpf,
    pt.detalhes->>'processo' AS numero_processo,
    pt.mensagem_erro,
    pt.consulta_id
FROM process_tracking pt
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND pt.mensagem_erro ILIKE '%Nenhum ANEXO II detectado%'
  AND pt.detalhes->>'processo' ~ '^7[0-9]{6}-'
ORDER BY pt.timestamp_evento DESC;
```

---

### Q06 — Erros de CPF não encontrado / ANEXO II de outro credor

```sql
SELECT
    pt.timestamp_evento,
    pt.cpf,
    pt.mensagem_erro,
    pt.detalhes->>'processo' AS processo
FROM process_tracking pt
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND (
    pt.mensagem_erro ILIKE '%CPF esperado%'
    OR pt.mensagem_erro ILIKE '%não encontrado em nenhum ofício%'
    OR pt.mensagem_erro ILIKE '%ANEXO II encontrado%nenhum pertence%'
  )
ORDER BY pt.timestamp_evento DESC;
```

---

### Q07 — Laudos completos vs. parciais (desfecho real)

```sql
SELECT
    pt.timestamp_evento::date AS data,
    pt.cpf,
    pt.consulta_id,
    pt.evento AS desfecho,           -- LAUDO_ENVIADO | LAUDO_PARCIAL
    pt.detalhes->>'qtd_processos' AS qtd_processos,
    pt.detalhes->>'email_destino' AS destino,
    ce.current_state
FROM process_tracking pt
LEFT JOIN consultas_esaj ce ON pt.consulta_id = ce.id
WHERE pt.evento IN ('LAUDO_ENVIADO','LAUDO_PARCIAL')
ORDER BY pt.timestamp_evento DESC;
```

---

## BLOCO 3 — Falhas de Infraestrutura

### Q08 — Jobs em erro (estados cobertos pelo watchdog)

```sql
SELECT
    ce.id, ce.cpf, ce.current_state, ce.state_updated_at,
    ce.last_error_message,
    l.descricao AS ultimo_log
FROM consultas_esaj ce
LEFT JOIN LATERAL (
    SELECT descricao FROM logs
    WHERE cpf = ce.cpf::char(11)
    ORDER BY timestamp DESC LIMIT 1
) l ON true
WHERE ce.current_state IN ('AUTH_ERROR','DOWNLOAD_FAILED','PIPELINE_ERROR','CALC_ERROR',
                           'MANUAL_PROCESS','ALERTA_MANUAL_SENT')
ORDER BY ce.state_updated_at DESC;
```

---

### Q09 — Erros críticos na pipeline (detalhe nos logs)

```sql
SELECT
    ce.id, ce.cpf, ce.current_state, ce.state_updated_at,
    l.timestamp AS hora_log,
    l.descricao
FROM consultas_esaj ce
JOIN logs l ON l.cpf = ce.cpf::char(11)
WHERE ce.current_state IN ('PIPELINE_ERROR','CALC_ERROR')
  AND (l.descricao ILIKE '%ERRO%' OR l.descricao ILIKE '%falhou%' OR l.descricao ILIKE '%exit%')
ORDER BY ce.state_updated_at DESC, l.timestamp DESC;
```

---

### Q10 — Volume de logs por origem (últimas 24h)

```sql
SELECT
    processo,
    COUNT(*) AS total_eventos,
    COUNT(*) FILTER (WHERE descricao ILIKE '%ERRO%' OR descricao ILIKE '%❌%' OR descricao ILIKE '%falh%') AS erros,
    MIN(timestamp) AS primeiro_evento,
    MAX(timestamp) AS ultimo_evento
FROM logs
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY processo
ORDER BY total_eventos DESC;
```

---

## BLOCO 4 — Qualidade de Dados

### Q11 — Taxa de preenchimento de campos críticos (últimas 24h)

```sql
SELECT
    COUNT(*)                                                              AS total_processos,
    ROUND(COUNT(valor_total_requisitado)::NUMERIC / COUNT(*) * 100, 1)      AS pct_valor_requisitado,
    ROUND(COUNT(saldo_final)::NUMERIC / COUNT(*) * 100, 1)                  AS pct_saldo_final,
    ROUND(COUNT(banco)::NUMERIC / COUNT(*) * 100, 1)                        AS pct_banco,
    ROUND(COUNT(data_base_atualizacao)::NUMERIC / COUNT(*) * 100, 1)        AS pct_data_base,
    ROUND(COUNT(numero_ordem)::NUMERIC / COUNT(*) * 100, 1)                 AS pct_numero_ordem,
    COUNT(*) FILTER (WHERE rejeitado)                                       AS rejeitados,
    COUNT(*) FILTER (WHERE anomalia)                                        AS anomalias
FROM esaj_detalhe_processos
WHERE timestamp_ingestao >= NOW() - INTERVAL '24 hours';
```

---

### Q12 — Processos rejeitados pelo DEPRE

```sql
SELECT
    cpf, numero_processo_cnj, vara, motivo_rejeicao,
    valor_total_requisitado, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE rejeitado = true
ORDER BY timestamp_ingestao DESC;
```

---

### Q13 — Processos com anomalia (forçam laudo parcial)

```sql
SELECT
    cpf, numero_processo_cnj, descricao_anomalia,
    valor_total_requisitado, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE anomalia = true
ORDER BY timestamp_ingestao DESC;
```

> `anomalia=true` → `Check Processamento Completo` marca `'Não Processado'` → laudo parcial.

---

## BLOCO 5 — Saúde do Worker

### Q14 — Atividade recente do orquestrador (últimas 2h)

```sql
SELECT cpf, timestamp, descricao
FROM logs
WHERE processo = 'crawler'
  AND timestamp >= NOW() - INTERVAL '2 hours'
ORDER BY timestamp DESC
LIMIT 20;
```

> Silêncio em horário de pico + `PAYMENT_APPROVED` acumulando = worker parado (o watchdog alerta em >2h — ver Q15).

---

### Q15 — PAYMENT_APPROVED sem processamento

```sql
SELECT
    id, cpf, state_updated_at,
    NOW() - state_updated_at AS aguardando_ha,
    CASE WHEN state_updated_at < NOW() - INTERVAL '2 hours'
         THEN '⚠️ watchdog deve ter alertado (ALERTA_MANUAL_SENT)'
         ELSE 'aguardando worker' END AS situacao
FROM consultas_esaj
WHERE current_state = 'PAYMENT_APPROVED'
  AND state_updated_at < NOW() - INTERVAL '30 minutes'
ORDER BY state_updated_at;
```

---

### Q16 — Lista de trabalho: clientes pagos com problema

```sql
SELECT
    ce.id, ce.cpf, ce.email, ce.current_state, ce.state_updated_at,
    (SELECT COUNT(*) FROM process_tracking pt
     WHERE pt.consulta_id = ce.id AND pt.evento = 'OCR_ERRO')        AS qtd_ocr_erros,
    (SELECT COUNT(*) FROM process_tracking pt
     WHERE pt.consulta_id = ce.id AND pt.evento = 'LAUDO_PARCIAL')  AS qtd_laudos_parciais,
    (SELECT COUNT(*) FROM process_tracking pt
     WHERE pt.consulta_id = ce.id AND pt.evento = 'LAUDO_ENVIADO')  AS qtd_laudos_enviados,
    (SELECT COUNT(*) FROM esaj_detalhe_processos edp
     WHERE edp.cpf = ce.cpf)                                        AS registros_extraidos
FROM consultas_esaj ce
WHERE ce.current_state IN (
    'MANUAL_PROCESS','ALERTA_MANUAL_SENT','PIPELINE_ERROR','CALC_ERROR',
    'AUTH_ERROR','DOWNLOAD_FAILED','PAYMENT_APPROVED'
)
ORDER BY ce.state_updated_at DESC;
```

---

## BLOCO 6 — Rastreamento Individual

### Q17 — Timeline completa de um CPF

```sql
WITH cpf_alvo AS (SELECT '09978342850' AS cpf)   -- ← trocar CPF
SELECT origem, momento, evento, detalhe FROM (
    SELECT
        'process_tracking' AS origem,
        pt.timestamp_evento AS momento,
        pt.etapa || '/' || pt.evento AS evento,
        COALESCE(pt.mensagem_erro, pt.detalhes::text) AS detalhe
    FROM process_tracking pt, cpf_alvo
    WHERE pt.cpf = cpf_alvo.cpf
    UNION ALL
    SELECT 'logs', l.timestamp, l.processo, l.descricao
    FROM logs l, cpf_alvo
    WHERE l.cpf = cpf_alvo.cpf::char(11)
    UNION ALL
    SELECT 'consultas_esaj', ce.state_updated_at,
           'STATE/' || ce.current_state, ce.last_error_message
    FROM consultas_esaj ce, cpf_alvo
    WHERE ce.cpf = cpf_alvo.cpf
) t
ORDER BY momento;
```

---

### Q18 — Dados extraídos de um CPF

```sql
SELECT
    cpf, numero_processo_cnj, vara, credor_nome,
    valor_total_requisitado, saldo_final,
    rejeitado, anomalia, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE cpf = '09978342850'   -- ← trocar CPF
ORDER BY timestamp_ingestao DESC;
```

---

## BLOCO 7 — Laudos fantasma / Cenário F residual

### Q19 — `REPORT_SENT` sem nenhum evento de laudo (cliente pago possivelmente sem resposta)

> Como `REPORT_SENT` é terminal, o que denuncia problema é a **ausência** de `LAUDO_ENVIADO`/`LAUDO_PARCIAL` no tracking da consulta.

```sql
SELECT
    ce.id AS consulta_id, ce.cpf, ce.email, ce.whatsapp_phone_number,
    ce.state_updated_at, NOW() - ce.state_updated_at AS ha_quanto_tempo,
    (SELECT COUNT(*) FROM esaj_detalhe_processos d WHERE d.cpf = ce.cpf)         AS processos_extraidos,
    (SELECT COUNT(*) FROM esaj_detalhe_processos d WHERE d.cpf = ce.cpf AND d.rejeitado) AS rejeitados,
    (SELECT COUNT(*) FROM esaj_calc_precatorio_resumo r WHERE r.cpf = ce.cpf)    AS registros_calc
FROM consultas_esaj ce
WHERE ce.current_state = 'REPORT_SENT'
  AND ce.state_updated_at < NOW() - INTERVAL '30 minutes'
  AND NOT EXISTS (
      SELECT 1 FROM process_tracking pt
      WHERE pt.consulta_id = ce.id
        AND pt.evento IN ('LAUDO_ENVIADO','LAUDO_PARCIAL')
  )
ORDER BY ce.state_updated_at;
```

**Interpretação:**
- `processos_extraidos > 0`, `rejeitados = processos_extraidos`, `registros_calc = 0` → Cenário F (Etapa 9b deveria ter disparado — verificar logs `Etapa 9b`)
- `processos_extraidos > 0`, `rejeitados < extraidos`, `registros_calc = 0` → laudo fantasma (watchdog ERROS_GRAVES cobre — deve estar `ALERTA_MANUAL_SENT` em ≤10 min)
- `processos_extraidos = 0` → pipeline não produziu nada (investigar logs do CPF — Q17)

**Ação manual (se watchdog não cobrir):**
```sql
UPDATE consultas_esaj
SET current_state = 'OCR_COMPLETE', state_updated_at = NOW()
WHERE id = <consulta_id>;
```
```bash
curl -X POST https://n8n.srv987902.hstgr.cloud/webhook/reporte-email-cpf \
  -H "Content-Type: application/json" \
  -d '{"cpf":"<cpf>","email":"<email_da_consulta>"}'
```

---

## BLOCO 8 — Pagamentos e Estados Comerciais

### Q20 — Pagamentos rejeitados

```sql
SELECT
    id, cpf, current_state, state_updated_at,
    mp_payment_status, mp_payment_id, payment_link,
    NOW() - state_updated_at AS ha_quanto_tempo
FROM consultas_esaj
WHERE current_state = 'PAYMENT_REJECTED'
  AND state_updated_at >= NOW() - INTERVAL '7 days'
ORDER BY state_updated_at DESC;
```

### Q21 — Pagamentos pendentes travados

```sql
SELECT
    id, cpf, current_state, state_updated_at,
    payment_link, mp_preference_id,
    NOW() - state_updated_at AS ha_quanto_tempo
FROM consultas_esaj
WHERE current_state IN ('PAYMENT_PENDING','AWAITING_PAYMENT')
  AND state_updated_at < NOW() - INTERVAL '1 hour'
ORDER BY state_updated_at DESC;
```

### Q22 — Sem precatórios válidos (NO_VALID_PROCESS)

```sql
SELECT id, cpf, current_state, state_updated_at, processos
FROM consultas_esaj
WHERE current_state = 'NO_VALID_PROCESS'
  AND state_updated_at >= NOW() - INTERVAL '7 days'
ORDER BY state_updated_at DESC;
```

---

## BLOCO 9 — NOVAS QUERIES (revisão 20/09/2026)

### Q23 — Jobs inseridos via CPF_batch_processing (pagamento simulado)

```sql
SELECT id, cpf, nome_requerente, email, current_state, mp_payment_id, created_at
FROM consultas_esaj
WHERE mp_payment_id LIKE 'BATCH_%'
ORDER BY created_at DESC;
```

> Batch insere `PAYMENT_APPROVED` direto com `whatsapp_from='5511941455345'` e `mp_payment_amount=1.00` — útil para distinguir clientes reais de testes internos.

### Q24 — Sessões de chatbot ativas agora (inclui registro temporário)

```sql
SELECT whatsapp_from, cpf, current_state, state_updated_at,
       verification_code, code_generated_at,
       NOW() - state_updated_at AS idle_ha
FROM consultas_esaj
WHERE current_state IN ('AWAITING_EMAIL','AWAITING_CODE','AWAITING_CONFIRMATION',
                        'AWAITING_PAYMENT','PAYMENT_PENDING')
ORDER BY state_updated_at DESC;
```

### Q25 — Completude por consulta (visão `view_processados`)

```sql
SELECT *
FROM view_processados
WHERE cpf = '09978342850'   -- ← trocar CPF
ORDER BY numero_processo;
```

> View oficial de completude: processos esperados (`consultas_esaj.processos`) × `status_calculo`.

### Q26 — Verificar se `vw_backoffice_processos` existe (dependência do backoffice)

```sql
SELECT COUNT(*) AS view_existe
FROM information_schema.views
WHERE table_schema = 'public' AND table_name = 'vw_backoffice_processos';
```

> `0` = backoffice quebrado. A view foi **recriada em 20/09/2026** (definição em `07_FERRAMENTAS_AUXILIARES.md`) — esta query serve para checar se continua existindo após manutenções/wipes.

### Q27 — LGPD: localizar todos os dados de um titular (atendimento de direitos)

```sql
-- Localização completa para solicitações enviadas a contato@revisaprecatorio.com.br
SELECT 'consultas_esaj' AS tabela, id::text AS ref, cpf, email, whatsapp_from,
       current_state, created_at::text AS quando
FROM consultas_esaj WHERE cpf = '<CPF>' OR email ILIKE '%<email>%'
UNION ALL
SELECT 'process_tracking', id::text, cpf, whatsapp_phone_number,
       etapa || '/' || evento, timestamp_evento::text
FROM process_tracking WHERE cpf = '<CPF>'
UNION ALL
SELECT 'esaj_detalhe_processos', id::text, cpf, credor_nome,
       numero_processo_cnj, timestamp_ingestao::text
FROM esaj_detalhe_processos WHERE cpf = '<CPF>' OR credor_cpf_cnpj LIKE '%<CPF>%'
UNION ALL
SELECT 'esaj_calc_precatorio_resumo', id::text, cpf, numero_processo_cnj,
       'total_corrigido=' || total_corrigido, criado_em::text
FROM esaj_calc_precatorio_resumo WHERE cpf = '<CPF>';
```

---

## Tabela Resumo — Sintoma → Query

| Sintoma | Query |
|---|---|
| Jobs por estado | Q01 |
| Job travado em PROCESSING | Q02 |
| Taxa de sucesso geral | Q03 + Q07 |
| Erros de OCR | Q04, Q05, Q06 |
| Laudo completo vs parcial | Q07 |
| Falhas auth/download/pipeline | Q08, Q09 |
| Worker ativo? | Q10, Q14, Q15 |
| Qualidade dos dados | Q11 |
| Rejeitados DEPRE / anomalias | Q12, Q13 |
| Lista de trabalho manual | Q16 |
| Rastrear CPF específico | Q17, Q18, Q25 |
| Cliente pago sem resposta (laudo fantasma / Cenário F) | **Q19** |
| Pagamentos rejeitados/pendentes | Q20, Q21 |
| Sem precatórios | Q22 |
| Jobs de teste/batch | Q23 |
| Sessões ativas do bot | Q24 |
| Backoffice funcionando? | Q26 |
| Solicitação LGPD (localizar dados do titular) | Q27 |
