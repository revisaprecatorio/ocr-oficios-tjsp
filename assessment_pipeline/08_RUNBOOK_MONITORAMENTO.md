# Runbook de Monitoramento — Agente Agendado (Hermes)

**Criado:** 20/09/2026 · **Escopo:** monitoramento 100% via PostgreSQL — **zero acesso à VPS Windows necessário**.

> **Princípio:** o worker é *pull-based*. Se a VPS cair com a fila vazia, nenhum cliente é afetado — e o primeiro pagamento que chegar dispara o alerta. Portanto **todo incidente com impacto em cliente é detectável pelo banco**. O que o banco não revela (qual componente morreu: Chrome, watchdog, orchestrator, disco) se resolve com o checklist manual da VPS — ver seção "Diagnóstico manual".

---

## 1. Modelo de operação

O agente roda como **task agendada no Hermes** (equivalente a um cron):

| Parâmetro | Valor recomendado |
|---|---|
| Frequência do ciclo | **a cada 15 minutos** |
| Digest diário | **1×/dia, 09:00** (opcional, ver §7) |
| Acesso necessário | PostgreSQL **somente leitura** |
| Acesso NÃO necessário | VPS Windows, n8n, GitHub, Mercado Pago |
| Canal de alerta | WhatsApp do gestor (via capacidade do próprio Hermes) |

### 1.1 Criar usuário read-only dedicado (rodar 1× no banco)

```sql
CREATE USER revisa_monitor WITH PASSWORD '<senha_forte>';
GRANT CONNECT ON DATABASE n8n TO revisa_monitor;
GRANT USAGE ON SCHEMA public TO revisa_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO revisa_monitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO revisa_monitor;
```

> Não usar o usuário `admin` no agente. O monitor nunca precisa escrever — se uma query dele falhar por permissão, é sinal de que tentou algo fora do escopo.

---

## 2. Checks do ciclo (rodar em ordem, a cada execução)

Cada check retorna linhas = **anomalia encontrada**. Query vazia = OK.

### CHECK 1 — Cliente pagou e nada aconteceu (severidade dinâmica)

```sql
SELECT id, cpf, email, state_updated_at,
       NOW() - state_updated_at AS espera
FROM consultas_esaj
WHERE current_state = 'PAYMENT_APPROVED'
  AND state_updated_at < NOW() - INTERVAL '30 minutes'
ORDER BY state_updated_at;
```

| Resultado | Severidade | Significado |
|---|---|---|
| Espera 30min–2h | ⚠️ ALTO | Fila acumulando — worker lento ou parado |
| Espera >2h | 🚨 CRÍTICO + meta-falha | O watchdog `Alerta_ERROS_GRAVES` deveria ter migrado para `ALERTA_MANUAL_SENT`. Se continua `PAYMENT_APPROVED`, **o próprio watchdog n8n está fora** → alertar imediatamente |

### CHECK 2 — Worker parado (fila com trabalho, zero atividade)

```sql
SELECT
  (SELECT COUNT(*) FROM consultas_esaj
   WHERE current_state IN ('PAYMENT_APPROVED','PROCESSING'))              AS fila,
  (SELECT COUNT(*) FROM logs
   WHERE processo = 'crawler'
     AND timestamp >= NOW() - INTERVAL '30 minutes')                     AS logs_30min;
```

`fila > 0` **e** `logs_30min = 0` → 🚨 **CRÍTICO** — a VPS/worker está morta *enquanto há cliente esperando*. Este é o check que resolve a ambiguidade "idle vs. down": silêncio com fila vazia é normal; silêncio com fila **não**.

### CHECK 3 — Job travado em PROCESSING

```sql
SELECT id, cpf, state_updated_at,
       NOW() - state_updated_at AS travado_ha
FROM consultas_esaj
WHERE current_state = 'PROCESSING'
  AND state_updated_at < NOW() - INTERVAL '1 hour';
```

Qualquer linha → 🚨 **CRÍTICO** — crash no meio do processamento (worker morreu durante o job).

### CHECK 4 — Laudo fantasma (cliente pago sem resposta)

```sql
SELECT ce.id, ce.cpf, ce.email, ce.state_updated_at
FROM consultas_esaj ce
WHERE ce.current_state = 'REPORT_SENT'
  AND ce.state_updated_at < NOW() - INTERVAL '45 minutes'
  AND NOT EXISTS (
      SELECT 1 FROM process_tracking pt
      WHERE pt.consulta_id = ce.id
        AND pt.evento IN ('LAUDO_ENVIADO','LAUDO_PARCIAL')
  );
```

Qualquer linha → 🚨 **CRÍTICO** — pipeline "concluiu" mas nenhum laudo foi entregue. (O watchdog cobre isso em ~30min migrando para `ALERTA_MANUAL_SENT`; se continua `REPORT_SENT` após 45min, o watchdog falhou.)

### CHECK 5 — Rajada de erros de infraestrutura

```sql
-- 5a: consultas que caíram em erro no último ciclo
SELECT id, cpf, current_state, last_error_message, state_updated_at
FROM consultas_esaj
WHERE current_state IN ('AUTH_ERROR','DOWNLOAD_FAILED','PIPELINE_ERROR','CALC_ERROR')
  AND state_updated_at >= NOW() - INTERVAL '15 minutes'
ORDER BY state_updated_at DESC;

-- 5b: erros de OCR na última hora
SELECT COUNT(*) AS ocr_erros_1h
FROM process_tracking
WHERE evento = 'OCR_ERRO'
  AND timestamp_evento >= NOW() - INTERVAL '1 hour';
```

| Resultado | Severidade | Provável causa |
|---|---|---|
| `AUTH_ERROR` (qualquer) | 🚨 CRÍTICO | Certificado A1, Web Signer ou e-SAJ fora |
| `DOWNLOAD_FAILED` (qualquer) | ⚠️ ALTO | Chrome debug ou pasta de download |
| `PIPELINE_ERROR`/`CALC_ERROR` (qualquer) | ⚠️ ALTO | OCR/LLM ou rotina de cálculo |
| `ocr_erros_1h ≥ 3` | ⚠️ ALTO | Qualidade de extração degradando |

### CHECK 6 — Fila de tratamento manual acumulando

```sql
SELECT COUNT(*) AS backlog_manual,
       MIN(state_updated_at) AS mais_antigo
FROM consultas_esaj
WHERE current_state IN ('MANUAL_PROCESS','ALERTA_MANUAL_SENT');
```

`backlog_manual ≥ 3` ou item >24h → ⚠️ **ALTO** — a caixa `revisa.manual@gmail.com` tem trabalho acumulado sem tratamento.

---

## 3. Anti-ruído (dedup) — regras obrigatórias

1. **Dedup por consulta:** nunca re-alertar o mesmo `consulta_id` pelo mesmo motivo dentro de **24h**. O agente deve manter na memória da task a lista `{consulta_id, motivo, timestamp}`.
2. **Watchdog já agiu:** se a consulta está em `ALERTA_MANUAL_SENT`, a equipe já foi notificada no e-mail — o agente alerta **uma única vez** (resumo) e marca como dedup.
3. **Agrupar:** se 5 consultas falharem no mesmo ciclo, enviar **1 mensagem** com a lista — não 5 mensagens.
4. **Resolução:** se uma consulta alertada sair do estado de erro (ex.: `PAYMENT_APPROVED` → `PROCESSING`), opcionalmente enviar "✅ resolvido" na mesma thread e limpar o dedup.
5. **Job de batch/teste:** consultas com `mp_payment_id LIKE 'BATCH_%'` são testes internos — reportar em severidade reduzida (INFO).

---

## 4. Formato do alerta WhatsApp

```
🚨 REVISA — [CRÍTICO] <título curto>

CPF: 468***853 · consulta #10347
Detectado: 14:32 · Ocorrência: <descrição 1 linha>
Último log: "<descricao do último log do CPF>"
Ação sugerida: <ver seção 5>
```

Regras: **mascarar o CPF** (3 primeiros + 3 últimos dígitos — LGPD); 1 mensagem por ciclo no máximo; sempre incluir `consulta_id` para rastreio.

Ao alertar, o agente deve **anexar evidência automática**: rodar a timeline do CPF (Q17 de `04_QUERIES_MONITORAMENTO.md`) e incluir o último evento de `process_tracking` + último log na mensagem.

---

## 5. Fluxo de investigação ao alertar

Para cada alerta, o agente executa antes de notificar:

```sql
-- Timeline do CPF (substituir <CPF>)
SELECT 'tracking' AS origem, pt.timestamp_evento AS momento,
       pt.etapa || '/' || pt.evento AS evento,
       COALESCE(pt.mensagem_erro, pt.detalhes::text) AS detalhe
FROM process_tracking pt WHERE pt.cpf = '<CPF>'
UNION ALL
SELECT 'log', l.timestamp, l.processo, l.descricao
FROM logs l WHERE l.cpf = '<CPF>'::char(11)
ORDER BY momento DESC LIMIT 10;
```

Interpretação rápida do `processo`/`etapa` onde morreu:

| Onde parou | Provável causa | Quem resolve |
|---|---|---|
| `crawler` / `AUTH_ERROR` | Chrome, Web Signer, certificado ou e-SAJ | VPS (checklist §8) |
| `OCR` | Extração/LLM | Análise do PDF — geralmente manual |
| `calculo`/`PIPELINE` | Script de cálculo ou pipeline shell | VPS (logs do pipeline) |
| Sem evento nenhum após `PAYMENT_APPROVED` | Worker/watchdog/VPS morto | VPS (checklist §8) |

---

## 6. Meta-monitoramento (watchdog do watchdog)

O n8n pode falhar sem sintoma no banco. Sinais indiretos que o agente deve cruzar:

| Sintoma | Conclusão |
|---|---|
| `PAYMENT_APPROVED` >2h **ainda em** `PAYMENT_APPROVED` | `Alerta_ERROS_GRAVES` não rodou → n8n ou o workflow caíram |
| `REPORT_SENT` fantasma >45min sem `ALERTA_MANUAL_SENT` | Idem |
| Cliente reclama de resposta no WhatsApp mas `consultas_esaj` sem linha nova | Webhook `whatsapp-beta-agent` ou Chatbot fora |

Se o Hermes tiver acesso à API do n8n (opcional), pode complementar verificando `GET /api/v1/workflows?active=true` — mas **não é necessário** para o modelo acima.

---

## 7. Digest diário (opcional — 09:00)

```sql
-- Resumo 24h
SELECT current_state, COUNT(*) FROM consultas_esaj
WHERE state_updated_at >= NOW() - INTERVAL '24 hours'
GROUP BY current_state ORDER BY 2 DESC;
```

```sql
-- Desfechos reais (laudos enviados × parciais × erros OCR)
SELECT evento, COUNT(*) FROM process_tracking
WHERE timestamp_evento >= NOW() - INTERVAL '24 hours'
  AND evento IN ('LAUDO_ENVIADO','LAUDO_PARCIAL','OCR_ERRO','PAYMENT_APPROVED')
GROUP BY evento;
```

Formato sugerido:

```
📊 REVISA — Digest 21/09 09:00
Laudos completos: 4 · Parciais: 1 · Pagos processando: 0
Erros: 0 · Backlog manual: 0 · Funil 24h: 6 consultas → 5 pagos
```

---

## 8. Diagnóstico manual na VPS (quando o agente alertar)

O agente detecta; **o humano diagnostica**. Checklist via RDP/PowerShell na VPS (`srv987902`):

```powershell
Get-Content C:\Users\Administrator\Documents\revisa\crawler_tjsp\logs\watchdog.log -Tail 30  # watchdog tickando?
netstat -ano | findstr :9222          # Chrome debug ouvindo?
Get-Process chrome                    # Chrome vivo?
Get-Process python                    # orchestrator rodando?
Get-PSDrive C                         # disco cheio?
```

Kill switch: arquivo `RUNTIME_DISABLED` na raiz do `crawler_tjsp` bloqueia execução (verificar se não foi esquecido).

---

## 9. Limitações conhecidas (não são bugs)

- **Não detecta VPS morta com fila vazia** — por design: sem cliente afetado, nada a alertar. CHECK 2 cobre o caso com fila.
- **Não diz qual componente morreu** — diz o sintoma e a etapa; causa-raiz é o checklist §8.
- **Efeitos de borda do relógio:** `state_updated_at`/`timestamp` são horário do servidor do banco — thresholds usam `NOW()` do próprio banco, sem problema de fuso.
- **Falso positivo possível:** `PROCESSING` >1h em job legítimo muito longo (CPF com muitos processos). Se recorrente, subir threshold para 2h.

---

## 10. Prompt pronto para a task no Hermes

> Cole como descrição da task agendada (a cada 15 min):

```text
Você é o monitor da plataforma Revisa Precatório. A cada execução:

1. Conecte no PostgreSQL (revisa_monitor, host 72.60.62.124:5432, db n8n) e rode
   os CHECKs 1–6 do documento assessment_pipeline/08_RUNBOOK_MONITORAMENTO.md,
   nesta ordem.

2. Para cada linha retornada, aplique as regras de severidade e anti-ruído (§3):
   dedup de 24h por consulta_id+motivo, agrupar em uma única mensagem,
   rebaixar BATCH_% para INFO.

3. Antes de alertar, rode a timeline do CPF (§5) e anexe o último evento de
   process_tracking + último log.

4. Envie ao WhatsApp do gestor no formato §4, mascarando o CPF.
   Se todos os checks vierem vazios: NÃO envie mensagem (silêncio = saudável).

5. Às 09:00, em vez do ciclo normal, envie o digest diário (§7).

NUNCA execute UPDATE/INSERT/DELETE — seu usuário é read-only.
Se a conexão com o banco falhar 2× seguidas, alerte: "banco de monitoramento
inacessível — verificar PostgreSQL/rede" (isso também é incidente).
```

---

## 11. Evolução futura (fora do escopo atual)

- **Heartbeat na VPS** (watchdog grava `logs` a cada tick) → detecção proativa mesmo idle. Exige deploy na VPS — adiado por decisão de não tocar na máquina.
- **Canary E2E** via webhook `cpf-batch-processing` com CPF-sonda → testa crawler+Chrome+e-SAJ periodicamente. Zero mudança na VPS; precisa validar comportamento para CPF sem processos.
- **SSH read-only** na VPS → diagnóstico remoto do componente. Exige habilitar OpenSSH Server — adiado.
