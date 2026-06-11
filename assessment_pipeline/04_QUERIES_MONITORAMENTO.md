# Queries de Monitoramento — logs e process_tracking

Todas as queries abaixo rodam no banco PostgreSQL `n8n` (host: `72.60.62.124`).
As tabelas usadas são: `logs`, `process_tracking`, `consultas_esaj`, `esaj_detalhe_processos`.

---

## BLOCO 1 — Visão Geral do Pipeline (Dashboard Executivo)

### Q01 — Contagem de jobs por estado atual

**Monitora:** Distribuição de todos os jobs ativos/pendentes por `current_state`.
Permite ver quantos estão aguardando pagamento, em processamento, com erro, etc.

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

---

### Q02 — Jobs travados em PROCESSING (possível crash do worker)

**Monitora:** Jobs bloqueados em `PROCESSING` por mais de 1 hora. Indica que o worker caiu no meio da execução sem liberar o lock. Ação: resetar para `PAYMENT_APPROVED`.

```sql
SELECT
    id, cpf, state_updated_at,
    NOW() - state_updated_at AS tempo_travado
FROM consultas_esaj
WHERE current_state = 'PROCESSING'
  AND state_updated_at < NOW() - INTERVAL '1 hour'
ORDER BY state_updated_at;
```

---

### Q03 — Funil completo de conversão (últimos 7 dias)

**Monitora:** Quantos clientes chegaram em cada etapa do funil.
Identifica onde há maior perda: pagamento, download, OCR, laudo.

```sql
SELECT
    COUNT(*)                                                                                   AS total_consultas,
    SUM(CASE WHEN current_state NOT IN ('AWAITING_EMAIL','AWAITING_CODE',
             'AWAITING_CONFIRMATION') THEN 1 ELSE 0 END)                                        AS chegaram_ao_pagamento,
    SUM(CASE WHEN current_state IN ('PROCESSING','FINAL_REPORT_SENT','PARTIAL_REPORT_SENT',
             'PIPELINE_ERROR','AUTH_ERROR','DOWNLOAD_FAILED','MANUAL_PROCESS',
             'ALERTA_MANUAL_SENT') THEN 1 ELSE 0 END)                                           AS pagamento_aprovado,
    SUM(CASE WHEN current_state IN ('FINAL_REPORT_SENT','PARTIAL_REPORT_SENT') THEN 1 ELSE 0 END) AS laudos_enviados,
    SUM(CASE WHEN current_state IN ('PIPELINE_ERROR','AUTH_ERROR',
             'DOWNLOAD_FAILED') THEN 1 ELSE 0 END)                                              AS falhas_tecnicas,
    SUM(CASE WHEN current_state IN ('MANUAL_PROCESS','ALERTA_MANUAL_SENT') THEN 1 ELSE 0 END)  AS requer_intervencao_manual
FROM consultas_esaj
WHERE state_updated_at >= NOW() - INTERVAL '7 days';
```

---

## BLOCO 2 — Monitoramento de Erros OCR

### Q04 — Todos os erros de OCR (últimos 30 dias)

**Monitora:** Todos os eventos `OCR_ERRO` com detalhes do processo e mensagem de erro.
Essencial para identificar padrões de falha.

```sql
SELECT
    pt.created_at::date AS data,
    pt.cpf,
    pt.mensagem_erro,
    pt.detalhes->>'processo' AS processo_falhou,
    pt.detalhes->>'workflow' AS workflow,
    ce.current_state AS estado_atual_job
FROM process_tracking pt
LEFT JOIN consultas_esaj ce ON pt.consulta_id = ce.id
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND pt.created_at >= NOW() - INTERVAL '30 days'
ORDER BY pt.created_at DESC;
```

---

### Q05 — PDFs antigos "700" detectados

**Monitora:** Especificamente erros de OCR causados por PDFs antigos (número do processo começando com "7" e ausência de ANEXO II). Permite quantificar a incidência de PDFs pré-formato-moderno.

```sql
SELECT
    pt.created_at::date AS data,
    pt.cpf,
    pt.detalhes->>'processo' AS numero_processo,
    pt.mensagem_erro,
    pt.consulta_id
FROM process_tracking pt
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND pt.mensagem_erro ILIKE '%Nenhum ANEXO II detectado%'
  AND (
       pt.detalhes->>'processo' ~ '^7[0-9]{6}-'   -- número começa com 7
    OR pt.detalhes->>'processo' ILIKE '7%2000%'    -- ano antigo no número
    OR pt.detalhes->>'processo' ILIKE '7%2008%'
    OR pt.detalhes->>'processo' ILIKE '7%2010%'
    OR pt.detalhes->>'processo' ILIKE '7%2011%'
  )
ORDER BY pt.created_at DESC;
```

---

### Q06 — Erros de CPF não encontrado no ofício

**Monitora:** Casos onde o ANEXO II existe mas não pertence ao CPF esperado (possível multi-credor), ou onde o CPF simplesmente não aparece no ofício.

```sql
SELECT
    pt.created_at,
    pt.cpf,
    pt.mensagem_erro,
    pt.metadata->>'processo' AS processo
FROM process_tracking pt
WHERE pt.etapa = 'OCR'
  AND pt.evento = 'OCR_ERRO'
  AND (
    pt.mensagem_erro ILIKE '%CPF esperado%'
    OR pt.mensagem_erro ILIKE '%não encontrado em nenhum ofício%'
    OR pt.mensagem_erro ILIKE '%ANEXO II encontrado%mas nenhum pertence%'
  )
ORDER BY pt.created_at DESC;
```

---

### Q07 — CPFs com laudo parcial (tiveram pelo menos 1 processo com OCR falho)

**Monitora:** Clientes que receberam laudo parcial — ou seja, têm processos antigos mas também modernos. Candidatos para ação manual nos processos faltantes.

```sql
SELECT
    pt.cpf,
    ce.id AS consulta_id,
    COUNT(CASE WHEN pt.evento = 'OCR_ERRO' THEN 1 END)     AS processos_com_erro,
    COUNT(CASE WHEN pt.evento = 'LAUDO_PARCIAL' THEN 1 END) AS laudos_parciais,
    MAX(pt.created_at) AS ultimo_evento,
    ce.current_state
FROM process_tracking pt
LEFT JOIN consultas_esaj ce ON pt.consulta_id = ce.id
WHERE pt.cpf IN (
    SELECT DISTINCT cpf FROM process_tracking
    WHERE etapa = 'LAUDO_PARCIAL' AND evento = 'LAUDO_PARCIAL'
)
GROUP BY pt.cpf, ce.id, ce.current_state
ORDER BY ultimo_evento DESC;
```

---

## BLOCO 3 — Monitoramento de Falhas de Infra

### Q08 — Jobs com falha de autenticação ou download

**Monitora:** Falhas de infraestrutura que exigem atenção imediata: certificado expirado, Chrome com problema, ou pasta de download vazia.

```sql
SELECT
    ce.id, ce.cpf, ce.current_state, ce.state_updated_at,
    l.descricao AS ultimo_log_erro
FROM consultas_esaj ce
LEFT JOIN LATERAL (
    SELECT descricao FROM logs
    WHERE cpf = ce.cpf
    ORDER BY timestamp DESC
    LIMIT 1
) l ON true
WHERE ce.current_state IN ('AUTH_ERROR', 'DOWNLOAD_FAILED', 'PIPELINE_ERROR')
ORDER BY ce.state_updated_at DESC;
```

---

### Q09 — Erros críticos na pipeline (PIPELINE_ERROR)

**Monitora:** Jobs onde a pipeline falhou totalmente após o download. Pode indicar problema no script OCR, na ingestão ou no cálculo.

```sql
SELECT
    ce.id, ce.cpf, ce.current_state, ce.state_updated_at,
    l.timestamp AS hora_erro,
    l.descricao AS mensagem_erro_log
FROM consultas_esaj ce
JOIN logs l ON l.cpf = ce.cpf
WHERE ce.current_state = 'PIPELINE_ERROR'
  AND l.descricao ILIKE '%ERRO%'
ORDER BY ce.state_updated_at DESC, l.timestamp DESC;
```

---

### Q10 — Volume de logs por tipo de processo (últimas 24h)

**Monitora:** Saúde operacional do sistema. Quantos eventos de cada tipo (`crawler`, `OCR`, `PIPELINE`) ocorreram nas últimas 24 horas.

```sql
SELECT
    processo,
    COUNT(*) AS total_eventos,
    SUM(CASE WHEN descricao ILIKE '%ERRO%' OR descricao ILIKE '%❌%' THEN 1 ELSE 0 END) AS erros,
    MIN(timestamp) AS primeiro_evento,
    MAX(timestamp) AS ultimo_evento
FROM logs
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY processo
ORDER BY total_eventos DESC;
```

---

## BLOCO 4 — Monitoramento de Qualidade de Dados

### Q11 — Taxa de preenchimento dos campos críticos (últimas 24h)

**Monitora:** Qualidade dos dados extraídos pelo OCR. Se a taxa cair, pode indicar regressão no detector ou novo formato de PDF.

```sql
SELECT
    COUNT(*)                                                              AS total_processos,
    ROUND(COUNT(valor_total_requisitado)::NUMERIC / COUNT(*) * 100, 1)   AS pct_valor_requisitado,
    ROUND(COUNT(saldo_final)::NUMERIC / COUNT(*) * 100, 1)               AS pct_saldo_final,
    ROUND(COUNT(banco)::NUMERIC / COUNT(*) * 100, 1)                     AS pct_banco,
    ROUND(COUNT(data_base_atualizacao)::NUMERIC / COUNT(*) * 100, 1)     AS pct_data_base,
    ROUND(COUNT(numero_ordem)::NUMERIC / COUNT(*) * 100, 1)              AS pct_numero_ordem
FROM esaj_detalhe_processos
WHERE timestamp_ingestao >= NOW() - INTERVAL '24 hours';
```

---

### Q12 — Processos rejeitados (OFÍCIO REJEITADO)

**Monitora:** Processos marcados como `rejeitado = true`, ou seja, ofícios que foram detectados como "SEM INFORMAÇÃO" pelo DetectorProcessamento. Esses processos existem mas foram rejeitados judicialmente.

```sql
SELECT
    cpf, numero_processo_cnj, vara, motivo_rejeicao,
    valor_total_requisitado, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE rejeitado = true
ORDER BY timestamp_ingestao DESC;
```

---

### Q13 — Processos com anomalia detectada

**Monitora:** Registros onde o OCR detectou inconsistências (ex.: CPF divergente, valores suspeitos). Requerem revisão manual.

```sql
SELECT
    cpf, numero_processo_cnj, descricao_anomalia,
    valor_total_requisitado, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE anomalia = true
ORDER BY timestamp_ingestao DESC;
```

---

## BLOCO 5 — Monitoramento Operacional do Worker

### Q14 — Atividade recente do orquestrador (últimas 2h)

**Monitora:** Se o worker está ativo. Se não houver nenhuma entrada de `processo='crawler'` nas últimas 2h em horário de pico, pode indicar que o worker caiu.

```sql
SELECT
    cpf, timestamp, descricao
FROM logs
WHERE processo = 'crawler'
  AND timestamp >= NOW() - INTERVAL '2 hours'
ORDER BY timestamp DESC
LIMIT 20;
```

---

### Q15 — Jobs com pagamento aprovado há mais de 30 minutos sem iniciar processamento

**Monitora:** Clientes que pagaram mas cujo job ainda não foi pego pelo worker. Indica que o worker pode estar inativo.

```sql
SELECT
    id, cpf, state_updated_at,
    NOW() - state_updated_at AS aguardando_ha
FROM consultas_esaj
WHERE current_state = 'PAYMENT_APPROVED'
  AND state_updated_at < NOW() - INTERVAL '30 minutes'
ORDER BY state_updated_at;
```

---

### Q16 — Clientes que precisam de intervenção manual

**Monitora:** Todos os clientes que pagaram e têm algum problema — independente do motivo. Lista de trabalho para o time de operações.

```sql
SELECT
    ce.id,
    ce.cpf,
    ce.current_state,
    ce.state_updated_at,
    -- Verifica se teve OCR_ERRO
    (SELECT COUNT(*) FROM process_tracking pt
     WHERE pt.consulta_id = ce.id AND pt.evento = 'OCR_ERRO') AS qtd_ocr_erros,
    -- Verifica se teve laudo parcial
    (SELECT COUNT(*) FROM process_tracking pt
     WHERE pt.consulta_id = ce.id AND pt.evento = 'LAUDO_PARCIAL') AS qtd_laudos_parciais,
    -- Registros no banco
    (SELECT COUNT(*) FROM esaj_detalhe_processos edp
     WHERE edp.cpf = ce.cpf) AS registros_extraidos
FROM consultas_esaj ce
WHERE ce.current_state IN (
    'MANUAL_PROCESS', 'ALERTA_MANUAL_SENT', 'PIPELINE_ERROR',
    'AUTH_ERROR', 'DOWNLOAD_FAILED',
    'PAYMENT_APPROVED'  -- PAYMENT_APPROVED antigo = worker caído
)
ORDER BY ce.state_updated_at DESC;
```

---

## BLOCO 6 — Rastreamento Individual de CPF

### Q17 — Timeline completa de um CPF específico

**Monitora:** Rastreia todos os eventos de um cliente específico em ordem cronológica. Útil para debugging de casos individuais.

```sql
-- Substitua '09978342850' pelo CPF desejado
WITH cpf_alvo AS (SELECT '09978342850' AS cpf)

SELECT
    'process_tracking' AS origem,
    pt.created_at AS momento,
    pt.etapa || '/' || pt.evento AS evento,
    COALESCE(pt.mensagem_erro, pt.metadata::text) AS detalhe
FROM process_tracking pt, cpf_alvo
WHERE pt.cpf = cpf_alvo.cpf

UNION ALL

SELECT
    'logs' AS origem,
    l.timestamp AS momento,
    l.processo AS evento,
    l.descricao AS detalhe
FROM logs l, cpf_alvo
WHERE l.cpf = cpf_alvo.cpf

ORDER BY momento;
```

---

### Q18 — Verificar se um CPF já tem dados extraídos no banco

**Monitora:** Valida se o OCR + ingestão funcionaram para um CPF específico e quais processos foram extraídos.

```sql
SELECT
    cpf, numero_processo_cnj, vara, credor_nome,
    valor_total_requisitado, saldo_final,
    rejeitado, anomalia, timestamp_ingestao
FROM esaj_detalhe_processos
WHERE cpf = '09978342850'  -- substituir pelo CPF
ORDER BY timestamp_ingestao DESC;
```

---

## BLOCO 7 — Cenário F: Falso REPORT_SENT (100% Rejeitados)

### Q19 — CPFs travados em REPORT_SENT sem laudo enviado (Cenário F)

**Monitora:** Clientes cujo precatório foi 100% rejeitado pelo DEPRE. O pipeline concluiu com sucesso, `current_state` ficou em `REPORT_SENT`, mas nenhum laudo foi enviado e nenhum cálculo foi gerado. Esses clientes pagaram e não receberam nada. Exigem ação manual de envio (ver Cenário F em `03_CENARIOS_E_TABELAS.md`).

```sql
-- CPFs com REPORT_SENT há mais de 15 minutos + sem registro de calc + todos rejeitados
SELECT
    ce.id AS consulta_id,
    ce.cpf,
    ce.email,
    ce.whatsapp_phone_number,
    ce.state_updated_at,
    NOW() - ce.state_updated_at AS ha_quanto_tempo,
    COUNT(edp.numero_processo_cnj)  AS processos_extraidos,
    COUNT(CASE WHEN edp.rejeitado = true THEN 1 END) AS processos_rejeitados,
    COUNT(ecr.numero_processo_cnj)  AS registros_calc,
    COUNT(pt.id)                    AS eventos_laudo_enviado
FROM consultas_esaj ce
-- registros OCR
LEFT JOIN esaj_detalhe_processos edp ON edp.cpf = ce.cpf
-- registros de cálculo
LEFT JOIN esaj_calc_precatorio_resumo ecr ON ecr.cpf = ce.cpf
-- eventos de laudo enviado
LEFT JOIN process_tracking pt
    ON pt.consulta_id = ce.id
   AND pt.etapa = 'ENVIO_LAUDO'
   AND pt.evento = 'LAUDO_ENVIADO'
WHERE ce.current_state = 'REPORT_SENT'
  AND ce.state_updated_at < NOW() - INTERVAL '15 minutes'
GROUP BY ce.id, ce.cpf, ce.email, ce.whatsapp_phone_number, ce.state_updated_at
HAVING
    -- nenhum cálculo foi gerado
    COUNT(ecr.numero_processo_cnj) = 0
    -- nenhum laudo foi enviado
    AND COUNT(pt.id) = 0
    -- todos os processos extraídos são rejeitados
    AND COUNT(edp.numero_processo_cnj) > 0
    AND COUNT(edp.numero_processo_cnj) = COUNT(CASE WHEN edp.rejeitado = true THEN 1 END)
ORDER BY ce.state_updated_at;
```

**Resultado esperado:** Cada linha é um cliente que pagou e não recebeu o laudo. Para cada um:
1. Resetar `current_state` para `'OCR_COMPLETE'`
2. Chamar `POST /reporte-email-cpf` com `{cpf, email}`

---

## Tabela Resumo — Qual Query usar para cada problema

| Sintoma | Query a usar |
|---|---|
| "Quantos jobs estão em cada estado?" | Q01 |
| "Worker travou? Job parado em PROCESSING?" | Q02 |
| "Qual é a taxa de sucesso geral?" | Q03 |
| "Quais CPFs tiveram erro de OCR hoje?" | Q04 |
| "Quantos PDFs antigos '700' estamos encontrando?" | Q05 |
| "CPF não foi encontrado no ofício — qual processo?" | Q06 |
| "Quais clientes receberam laudo parcial?" | Q07 |
| "Tivemos falha de autenticação no e-SAJ ou download?" | Q08 |
| "Quais jobs falharam completamente?" | Q09 |
| "O sistema está rodando? Worker ativo?" | Q10 + Q14 |
| "Qualidade dos dados extraídos está boa?" | Q11 |
| "Clientes com processos rejeitados?" | Q12 |
| "CPF pagou e não recebeu laudo por rejeição DEPRE? (Cenário F)" | Q19 |
| "Há anomalias nos dados?" | Q13 |
| "Worker caiu? Jobs pagos sem processar?" | Q15 |
| "Lista de trabalho: quem precisa de ação manual?" | Q16 |
| "Rastrear o que aconteceu com CPF X?" | Q17 |
| "CPF X tem dados extraídos no banco?" | Q18 |
