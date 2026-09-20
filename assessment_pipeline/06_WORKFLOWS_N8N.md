# Workflows n8n — Revisa Precatório

**Revisado:** 20/09/2026 | **Fonte:** JSONs baixados da instância viva `n8n.srv987902.hstgr.cloud` via API (`n8n_workflows_live/*.json`)

> A instância tem **50 workflows, 7 ativos**. Os 43 inativos são versões antigas/experimentais (inclui **2× `Alerta_PDF_antigo`** desabilitados: `PMyNPcPlRZMZjCb1`, `Uck9WlB08COLVM1K`). O backup GitHub `n8n-source-code-docs` (jun/2026) é histórico — a fonte de verdade é `n8n_workflows_live/` aqui.
>
> Para reimportar: **n8n → Import Workflow → Upload JSON**. A API key fica em `../n8n_api.env` (não commitar).

---

## Índice

| # | ID n8n | Workflow | Nós | Trigger | Última atualização |
|---|---|---|---|---|---|
| 1 | `73xnqygBK9tk6aDK` | [Chatbot Revisa](#1-chatbot-revisa) | 35 | Webhook WhatsApp | 20/09 (LGPD no e-mail de código) |
| 2 | `6COT3ubybyI8QhYT` | [Mercado Pago Unified](#2-mercado-pago-unified) | 18 | 2 webhooks | 02/05 |
| 3 | `UrxjrcPE2C7WTLa0` | [Laudo envio email+cpf](#3-laudo-envio-emailcpf) | 19 | `POST /reporte-email-cpf` | 19/09 (LGPD nos 2 HTMLs) |
| 4 | `GnL3nOy64DmpjHTD` | [Alerta_ERROS_GRAVES](#4-alerta_erros_graves) | 7 | Schedule 10 min | 17/09 (watchdog ampliado) |
| 5 | `nWttny9O5BjKabz2` | [Alerta_Laudo_Parcial](#5-alerta-laudo-parcial) | 6 | Schedule 10 min | 28/08 |
| 6 | `XIx9gn1ifI7jsyoP` | [Alerta_Reporte_Manual](#6-alerta-reporte-manual) | 7 | Schedule 10 min | 28/08 |
| 7 | `jMzstMZfztUMz7O6` | [CPF_batch_processing](#7-cpf-batch-processing) | 6 | `POST /cpf-batch-processing` | 18/04 |

---

## 1. Chatbot Revisa

**Arquivo:** `n8n_workflows_live/Chatbot Revisa.json`
**Webhook:** `GET/POST /webhook/whatsapp-beta-agent` (GET = verificação Meta via `Check Facebook Verification` → `Facebook Verification Response`)

### Função

Entrada da plataforma. Máquina de estados por `whatsapp_from` (telefone). Registro temporário de sessão usa `cpf='00000000000'` com `ON CONFLICT (whatsapp_from, cpf)`.

### Fluxo

```
Webhook → Process Input (filtra status; extrai texto/from; classifica tipo)
  → Get User State (SELECT ... WHERE whatsapp_from=? AND current_state IN
      ('IDLE','AWAITING_CONFIRMATION','AWAITING_EMAIL','AWAITING_CODE',
       'AWAITING_PAYMENT','PAYMENT_REJECTED'))
  → Merge State → Route Message Type
      rotas: NOT_TEXT | CPF | EMAIL | CODE | CONFIRM_YES | CONFIRM_NO |
             MENU | INFO_PRECATORIOS | CONSULTAR | AGENT
  → Response <tipo> (Set) → Update State (upsert sessão)
  → Send WhatsApp Response → Respond OK
```

### Nós (35 — todos)

`Webhook Trigger`, `Process Input`, `Get User State`, `Merge State`, `Route Message Type`, `Response NOT_TEXT/CPF/EMAIL/CODE/CONFIRM_YES/CONFIRM_NO/MENU/INFO_PRECATORIOS/CONSULTAR/AGENT`, `Update State`, `Consulta e-SAJ`, `Parse e-SAJ Response`, `Generate Verification Code`, `Validate Code`, `Send Verification Email`, `Check Facebook Verification`, `Facebook Verification Response`, `Send WhatsApp Response`, `Respond OK`, `Save Consulta`, `Trigger Payment Workflow`, `prepare response`, `If HTTP 200?`, `PT - TJSP Inoperante`, `Email Alerta TJSP`, `WA Alerta Operacao TJSP`, `Send TJSP Out`, `PT - Consulta Solicitada`, `Consulta Realizada`.

### Pontos notáveis

- **`Consulta e-SAJ`**: `GET https://esaj.tjsp.jus.br/cpopg/search.do?cbPesquisa=DOCPARTE&dadosConsulta.valorConsulta={cpf}&cdForo=-1` (HTML público — o crawler autenticado só roda **depois** do pagamento)
- **`Send Verification Email`**: HTML com código `{{ $json.verification_code }}` + **seção "Privacidade e proteção de dados"** (link Política de Privacidade + mailto `contato@revisaprecatorio.com.br`), `© 2026` — adicionado 20/09/2026
- **`Trigger Payment Workflow`** → `POST /generate-payment-link`; falha → alertas TJSP-inoperante por e-mail/WhatsApp
- **Timeouts:** código 15 min (`code_generated_at`); e-mail/confirmação 30 min; pagamento 60 min
- Estados de pipeline **não** sequestram a sessão — cliente com `REPORT_SENT`/`ALERTA_MANUAL_SENT` consegue usar o bot normalmente

---

## 2. Mercado Pago Unified

**Arquivo:** `n8n_workflows_live/Mercado Pago Unified.json`
**Webhooks:** `POST /generate-payment-link` (interno) + `POST /mercadopago-notification` (MP)

### Fluxo A — Geração de Link

`Generate Link Webhook` → `Validate Trigger Payment` → `Generate Payment Link` (MP API) → `Save Payment Link` → `PT Link Gerado` → `Cleanup Session Record` → `Send Payment Link WA` (falhas → `Log Skipped Payment`).

**Preferência MP criada:** item "Laudo Completo de Precatorios" **R$ 1,00**; `external_reference={whatsapp_from}_{ts}`; `notification_url=.../mercadopago-notification`; back_urls para `revisaprecatorio.com.br/pagamento-{sucesso,falha,pendente}`; `auto_return=approved`.

### Fluxo B — Notificação de Pagamento

`Webhook` → `Respond OK to MP` (200 imediato, anti-retry) → `Filter Payment Events` (`type='payment'`; demais → `Log Ignored Event`) → `Get Payment Details` → `Process Payment Status` → `Update Payment Status` → `Send WhatsApp Notification` → `PT Status Pagamento` + `Log Payment Success`.

**Mensagens do `Process Payment Status` (texto vivo):**

| Status | Estado | Mensagem |
|---|---|---|
| `approved` | `PAYMENT_APPROVED` | 🎉 confirmado + laudo em 24h + exceção 7 dias úteis + "menu". ⚠️ typos: `e mail`, `scaneados` |
| `rejected` | `PAYMENT_REJECTED` | ❌ não aprovado + "sim" para novo link |
| `pending`/`in_process` | `PAYMENT_PENDING` | ⏳ em análise + "menu" |

> Em `approved`, o workflow também **apaga dados antigos** do CPF em `esaj_detalhe_processos`/`esaj_calc_precatorio_resumo` (reprocessamento limpo).

---

## 3. Laudo envio email+cpf

**Arquivo:** `n8n_workflows_live/Laudo envio email+cpf.json`
**Webhook:** `POST /webhook/reporte-email-cpf` — body `{cpf, email}`; chamado por `calc-precatorio-tjsp/webhook_n8n.py` (Etapa 9) ou `pipeline_completo.sh` Etapa 9b.

### `Check Processamento Completo` (query real — resumo)

- `consulta_alvo`: última consulta do `cpf` **com o `email` informado** e `current_state NOT IN ('REPORT_SENT','FINAL_REPORT_SENT')`
- Expande `processos->'lista'`; para cada processo:
  - `anomalia=true` → `'Não Processado'`
  - existe em `esaj_calc_precatorio_resumo` → `'Processado'`
  - `rejeitado=true` → `'Processado'`
  - senão → `'Não Processado'`
- Retorna `todos_processados` (bool), `total_esperado`, `total_processado`, `retries`, `whatsapp_phone_number`

> ⚠️ O filtro por `email` é obrigatório — disparar o webhook com e-mail diferente do cadastrado não encontra a consulta (fluxo morre silenciosamente após `Fetch Data`).

### Caminho completo

`Todos Processados?` → `Fetch Data for CPF` (`vw_precatorios_full`) → **`Build HTML Content`** (15.045 chars; laudo com aviso LGPD no DISCLAIMER) → `Send Report Email` — **to=`{{email}}`, sem CC** — assunto `Laudo Diagnóstico de Precatório – CPF {cpf}` → `Log Success` → `Webhook Response` → `Update Report Status` (`FINAL_REPORT_SENT` por `consulta_id`) → `PT Report Enviado`.

### Caminho parcial

`Fetch Data for CPF - parcial` → **`Build HTML Parcial`** (15.403 chars; com LGPD) → `Send Report Revisa` — **to=`revisa.manual@gmail.com` (fixo)** — assunto `Laudo Diagnóstico Parcial – CPF {cpf}` → `phone e nome` → `Whatsapp Parcial` (cliente: "análise complementar... até 7 dias úteis... não precisa nova solicitação ou pagamento") → `Log Parcial e Manual` → `Webhook Response Parcial` → `Update Partial Report` (`PARTIAL_REPORT_SENT`, última consulta do CPF) → `PT Report  Parcial`.

> Depois do pipeline (`exit 0`), o orchestrator sobrescreve o estado com **`REPORT_SENT`** — FINAL/PARTIAL ficam no histórico apenas via `process_tracking`.

---

## 4. Alerta_ERROS_GRAVES — Watchdog

**Arquivo:** `n8n_workflows_live/Alerta_ERROS_GRAVES.json` | 7 nós | Schedule 10 min

### Query (3 grupos de detecção)

```sql
SELECT ce.id AS consulta_id, ce.cpf, ce.current_state, ce.whatsapp_from,
       ce.nome_requerente, ce.email, ce.processos,
       STRING_AGG(DISTINCT pt.mensagem_erro,' | ') AS erros_ocr
FROM consultas_esaj ce
LEFT JOIN process_tracking pt ON pt.consulta_id=ce.id
       AND pt.evento='OCR_ERRO' AND pt.mensagem_erro IS NOT NULL
WHERE
  -- (a) erros de pipeline sem laudo parcial associado
  ( ce.current_state IN ('PIPELINE_ERROR','AUTH_ERROR','DOWNLOAD_FAILED','CALC_ERROR')
    AND NOT EXISTS (SELECT 1 FROM process_tracking pt2
                    WHERE pt2.consulta_id=ce.id AND pt2.etapa='LAUDO_PARCIAL') )
  OR
  -- (b) pagamento aprovado e esquecido (worker parado)
  ( ce.current_state='PAYMENT_APPROVED'
    AND ce.state_updated_at < NOW() - INTERVAL '2 hours' )
  OR
  -- (c) laudo fantasma: REPORT_SENT/FINAL >30min sem cálculo e com processo não-rejeitado
  ( ce.current_state IN ('REPORT_SENT','FINAL_REPORT_SENT')
    AND ce.state_updated_at < NOW() - INTERVAL '30 minutes'
    AND NOT EXISTS (SELECT 1 FROM esaj_calc_precatorio_resumo r WHERE r.cpf=ce.cpf)
    AND EXISTS (SELECT 1 FROM esaj_detalhe_processos d
                WHERE d.cpf=ce.cpf AND COALESCE(d.rejeitado,false)=false) )
GROUP BY ...
```

### Ação

`Prepara Mensagens` → `WhatsApp Cliente` ("...análise complementar... até 7 dias úteis... não precisa realizar uma nova solicitação ou pagamento") → `Email contato@revisaprecatorio` (**destino real: `revisa.manual@gmail.com`**, assunto "Erro processamento CPF {cpf} necessita...") → `Update current_state ALERTA_MANUAL_SENT` (aceita origem `MANUAL_PROCESS|PIPELINE_ERROR|AUTH_ERROR|DOWNLOAD_FAILED|CALC_ERROR|REPORT_SENT|FINAL_REPORT_SENT|PAYMENT_APPROVED`) → `Log Alerta Manual`.

> É a rede de segurança que garante **nenhum cliente pago fica sem resposta**.

---

## 5. Alerta_Laudo_Parcial

**Arquivo:** `n8n_workflows_live/Alerta_Laudo_Parcial.json` | 6 nós | Schedule 10 min

`Schedule Trigger` → `Query Laudo Parcial` (`LAUDO_PARCIAL` sem `PARCIAL_INFORMADO` para mesmo cpf+consulta_id) → `Prepara Mensagens` → `Email contato@revisaprecatorio` (**real: `revisa.manual@gmail.com`**, assunto "Processamento PARCIAL CPF {cpf}...") → `Insert PARCIAL_INFORMADO` (guarda anti-reenvio) → `Log Laudo Parcial` (cpf='BATCH').

---

## 6. Alerta_Reporte_Manual

**Arquivo:** `n8n_workflows_live/Alerta_Reporte_Manual.json` | 7 nós | Schedule 10 min

`Schedule Trigger` → `Query consultas_esaj` (`current_state='MANUAL_PROCESS'`) → `Prepara Mensagens` → `WhatsApp Cliente` → `Email contato@revisaprecatorio` (**real: `revisa.manual@gmail.com`**) → `Update current_state ALERTA_MANUAL_SENT` → `Log Alerta Manual` (cpf='BATCH').

> Sobrepõe-se ao grupo (a) do ERROS_GRAVES quando `MANUAL_PROCESS` tem `OCR_ERRO` sem `LAUDO_PARCIAL` — ambos podem disparar; o `UPDATE` do primeiro a correr tira o estado de `MANUAL_PROCESS`, evitando duplicidade na prática.

---

## 7. CPF_batch_processing

**Arquivo:** `n8n_workflows_live/CPF_batch_processing.json` | 6 nós
**Webhook:** `POST /webhook/cpf-batch-processing` — body `{cpf}`

`Webhook Trigger` → `Extract CPF` (normaliza dígitos; **`whatsapp_from='5511941455345'` fixo**) → `Consulta e-SAJ` (mesma query pública do Chatbot) → `Parse e-SAJ Response` → `Upsert Consulta` → `Respond to Webhook`.

### Upsert — insere direto como pago

```sql
INSERT INTO consultas_esaj (whatsapp_from, whatsapp_phone_number, cpf, nome_requerente,
    processos, total_processos, resposta_formatada, current_state, state_updated_at,
    timestamp_consulta, created_at, updated_at,
    mp_payment_status, mp_payment_id, mp_payment_amount, payment_confirmed_at)
VALUES ('5511941455345','5511941455345','{cpf}','{nome}','{lista}'::jsonb,{n},'...',
        'PAYMENT_APPROVED', NOW(), NOW(), NOW(), NOW(),
        'approved', 'BATCH_' || EXTRACT(EPOCH FROM NOW())::text, 1.00, NOW())
ON CONFLICT (whatsapp_from, cpf) DO UPDATE SET ...
```

> **O registro entra direto na fila do worker** (`PAYMENT_APPROVED`) — é a ferramenta oficial de reprocessamento/teste sem WhatsApp nem cobrança. Identificável por `mp_payment_id LIKE 'BATCH_%'` (Q23).
>
> ⚠️ Como `whatsapp_from` é o número da equipe, o WhatsApp de "laudo parcial"/alertas iria para esse número; o laudo completo vai ao e-mail que estiver em `consultas_esaj.email` — cadastrar/atualizar o e-mail antes se o objetivo for entrega ao cliente.

---

## Credenciais utilizadas (resumo)

| Credencial | Usada em | Tipo |
|---|---|---|
| Postgres (`72.60.62.124:5432/n8n`) | Todos os workflows | PostgreSQL account |
| Mercado Pago | MP Unified (preferências + consulta pagamento) | HTTP Header / Access Token |
| SMTP | Chatbot (código), Laudo, Alertas | Email Send |
| Meta WhatsApp | Chatbot, Laudo (parcial), Alertas | WhatsApp Business node (`phoneNumberId=772929385904854`) |

## Convenções de destinatários

| Destino | Uso |
|---|---|
| `revisa.manual@gmail.com` | **Todos os alertas internos + laudo parcial** |
| `contato@revisaprecatorio.com.br` | Canal LGPD/direitos citado nos textos ao cliente |
| `5511941455345` | `whatsapp_from` fixo do batch (equipe) |
