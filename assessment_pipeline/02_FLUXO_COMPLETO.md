# Fluxo Completo do Pipeline — Passo a Passo

**Revisado:** 20/09/2026 contra workflows vivos (`n8n_workflows_live/`) e código no GitHub.

---

## Fase 1 — Captação (n8n: Chatbot Revisa, 35 nós)

**Trigger:** Webhook WhatsApp `whatsapp-beta-agent` (GET=verificação Meta, POST=mensagens).

Máquina de estados que lê `consultas_esaj` por `whatsapp_from` a cada mensagem. A query `Get User State` só considera estados conversacionais (`IDLE`, `AWAITING_*`, `PAYMENT_REJECTED`) — estados terminais de pipeline (`REPORT_SENT`, `ALERTA_MANUAL_SENT`, erros) **não sequestram a sessão**.

### Etapas conversacionais

| Estado | O que o bot faz |
|---|---|
| `IDLE` | Apresenta menu, pede CPF |
| `AWAITING_EMAIL` | Recebeu CPF → consulta e-SAJ (`GET esaj.tjsp.jus.br/cpopg/search.do?cbPesquisa=DOCPARTE&dadosConsulta.valorConsulta={cpf}&cdForo=-1`) → pede e-mail |
| `AWAITING_CODE` | Gerou código 6 dígitos → **e-mail de verificação com aviso LGPD** (expira em 15 min) |
| `AWAITING_CONFIRMATION` | Exibe nome + processos → aguarda confirmação |
| `AWAITING_PAYMENT` | Dispara `/generate-payment-link` no MP Unified |

**Rotas do `Route Message Type`:** `NOT_TEXT`, `CPF`, `EMAIL`, `CODE`, `CONFIRM_YES`, `CONFIRM_NO`, `MENU`, `INFO_PRECATORIOS`, `CONSULTAR`, `AGENT`.

**Registro de sessão temporário:** `Update State` insere/atualiza linha com `cpf='00000000000'` por `whatsapp_from` (`ON CONFLICT (whatsapp_from, cpf)`); o `Mercado Pago Unified` a remove ao gerar o link (`Cleanup Session Record`).

**Timeouts:** `AWAITING_CODE` → 15 min; `AWAITING_EMAIL`/`AWAITING_CONFIRMATION` → 30 min; `AWAITING_PAYMENT` → 60 min.

**Indisponibilidade e-SAJ:** se a consulta falha → `PT - TJSP Inoperante` (process_tracking) + `Email Alerta TJSP` + `WA Alerta Operacao TJSP` + mensagem ao cliente (`Send TJSP Out`).

**Registros em `process_tracking`:** `CONSULTA/CONSULTA_SOLICITADA`, `CONSULTA/CONSULTA_REALIZADA` (`detalhes.total_processos`).

> Se `total_processos = 0` → fluxo encerra com mensagem de retorno (sem precatórios).

---

## Fase 2 — Pagamento (n8n: Mercado Pago Unified, 18 nós)

Dois pontos de entrada independentes.

### 2a — Geração do Link (`POST /generate-payment-link`)

Chamado pelo Chatbot ao entrar em `AWAITING_PAYMENT`.

1. `Validate Trigger Payment` — exige `trigger_payment=true` + `email`
2. `Generate Payment Link` — `POST api.mercadopago.com/checkout/preferences`:
   - item: "Laudo Completo de Precatorios", **R$ 1,00**
   - `external_reference` = `{whatsapp_from}_{timestamp}`
   - `notification_url` = `.../webhook/mercadopago-notification`
   - `back_urls` = revisaprecatorio.com.br/pagamento-{sucesso,falha,pendente}
3. `Save Payment Link` — UPDATE `consultas_esaj` (`mp_preference_id`, `payment_link`, `current_state='AWAITING_PAYMENT'`)
4. `Cleanup Session Record` — remove o registro `cpf='00000000000'`
5. `Send Payment Link WA` + `PT Link Gerado`

### 2b — Notificação de Pagamento (`POST /mercadopago-notification`)

1. `Respond OK to MP` — responde 200 imediato (anti-timeout/retry storm)
2. `Filter Payment Events` — só `type='payment'`
3. `Get Payment Details` — `GET /v1/payments/{id}`
4. `Process Payment Status` — `approved`→`PAYMENT_APPROVED` | `rejected`→`PAYMENT_REJECTED` | `pending`/`in_process`→`PAYMENT_PENDING`
5. `Update Payment Status` — `mp_payment_id`, `mp_payment_status`, `payment_confirmed_at`, `current_state`
6. Se `approved` → limpa dados antigos do CPF (`esaj_detalhe_processos` + `esaj_calc_precatorio_resumo`) para reprocessamento limpo
7. `Send WhatsApp Notification` + `PT Status Pagamento`

**Mensagem ao cliente (approved) — texto vivo:**

> 🎉 *Pagamento confirmado!*
> Seu laudo completo de precatórios será enviado para o seu **e mail** em até 24 horas. Lembre-se de verificar também a caixa de spam.
> Em casos de processos físicos **scaneados** ou que apresentem problemas de configuração, o prazo poderá ser prorrogado em até 7 dias úteis...
> Digite menu para voltar ao início.

> ⚠️ Typos conhecidos vs. texto aprovado: `e mail`→`e-mail`, `scaneados`→`escaneados`. Mensagens de `rejected`/`pending` não foram alteradas por decisão.

---

## Fase 3 — Download de PDFs (orchestrator + crawler)

**Trigger:** `runtime/executar.bat` (agendado) → `core/orchestrator_subprocess.py` (1 job/ciclo).

### 3.1 — Lock do Job

```sql
UPDATE consultas_esaj
SET current_state='PROCESSING', processing_started_at=NOW(), state_updated_at=NOW()
WHERE id = (SELECT id FROM consultas_esaj WHERE current_state='PAYMENT_APPROVED'
            ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING id, cpf, processos;
```

Filtra `processos` por classe "Precatório" (sinônimos). Lista vazia → `NO_VALID_PROCESS`.

### 3.2 — Download por Processo

1. Pasta temp: `C:\Temp\RevisaDownloads\{cpf}\temp_{numero}\`
2. `crawler_full.py --doc {numero} --attach --debugger-address 127.0.0.1:9222 --abrir-autos --baixar-pdf --turbo-download --download-dir ...`
3. TURBO: JS seleciona todos os docs da Pasta Digital → PDF consolidado
4. Move para `C:\Temp\RevisaDownloads\{cpf}\`

**Falhas:** `AUTH_ERROR` (cert. A1/Web Signer/CAS), `DOWNLOAD_FAILED` (0 PDFs).

---

## Fase 4 — OCR + Ingestão + Cálculo (`pipeline_completo.sh {cpf}`)

Script real no GitHub (`ocr-oficios-tjsp/pipeline_completo.sh`). Etapas confirmadas:

| Etapa | Ação | Falha → |
|---|---|---|
| 1 | Limpeza do staging (`outputs/`) | — |
| 2 | `processar_pipeline.py` — todos os PDFs do CPF: DetectorOficio + DetectorAnexoII + DetectorSaldoFinal + DetectorHabilitacaoHerdeiros + DetectorTermosJuridicos + LLM híbrido (Gemini → GPT-4o-mini) → JSONs em `outputs/consultas/{cpf}/` | OCR falha num PDF → `OCR_ERRO` em tracking + `MANUAL_PROCESS` (pipeline continua) |
| 3 | Centraliza JSONs em `outputs/json/` | 0 JSONs → `exit 1` → `PIPELINE_ERROR` |
| 4 | `ingest_all_jsons.py` — upsert em `esaj_detalhe_processos` filtrado por CPF | — |
| 5 | Validação forte: `COUNT > 0` no banco para o CPF | 0 → `exit 1` → `PIPELINE_ERROR` |
| 6 | `recalcular_idoso.py` — flag `idoso` por `data_nascimento` | — |
| 7 | Backup JSONs → `outputs/historico_processado/{cpf}/{ts}/` | — |
| 8 | Arquiva PDFs → `RevisaDownloads_Processados\{cpf}\{data}_{ts}\` | — |
| 9 | `calc-precatorio-tjsp/main.py` → insere `esaj_calc_precatorio_resumo` + chama webhook `/reporte-email-cpf` (via `webhook_n8n.py`) | exit≠0 → `PIPELINE_ERROR`/`CALC_ERROR` |
| **9b** ✅ | **Se `COUNT(esaj_calc)=0` (100% rejeitado): busca e-mail em `consultas_esaj` e chama o webhook direto** — resolve o Cenário F | sem e-mail → log apenas |

**Logs em `logs`:** `"Etapa N: ..."` (processo=`PIPELINE`), `"Nenhum processo pendente."` (processo=`calculo`), `"Webhook consolidado: SUCESSO|FALHA"`.

---

## Fase 5 — Envio do Laudo (n8n: Laudo envio email+cpf, 19 nós)

**Trigger:** `POST /webhook/reporte-email-cpf` com `{cpf, email}` — chamado por `calc/webhook_n8n.py` (Etapa 9) ou pela Etapa 9b.

### 5.0 — `Check Processamento Completo` (query real)

- Localiza a consulta por `cpf` **+ `email`** e `current_state NOT IN ('REPORT_SENT','FINAL_REPORT_SENT')` (mais recente por `created_at`)
- Expande `processos->'lista'` e cruza com `esaj_calc_precatorio_resumo` + `vw_precatorios_full`
- Status por processo: `anomalia=true` → `'Não Processado'`; tem cálculo → `'Processado'`; `rejeitado=true` → `'Processado'`; senão `'Não Processado'`
- `todos_processados = BOOL_AND(status='Processado')`

### 5a — Caminho completo (`todos_processados=true`)

`Fetch Data for CPF` (`vw_precatorios_full`) → `Build HTML Content` (15.045 chars, **com aviso LGPD** no DISCLAIMER) → `Send Report Email` (**to = e-mail do webhook, sem CC**; assunto `Laudo Diagnóstico de Precatório – CPF {cpf}`) → `Update Report Status` (`FINAL_REPORT_SENT`) → `PT Report Enviado` (`ENVIO_LAUDO/LAUDO_ENVIADO`) → `Webhook Response`.

### 5b — Caminho parcial (`todos_processados=false`)

`Fetch Data for CPF - parcial` → `Build HTML Parcial` (15.403 chars, **com aviso LGPD**) → `Send Report Revisa` (**to = `revisa.manual@gmail.com` — fixo**; assunto `Laudo Diagnóstico Parcial – CPF {cpf}`) → `Whatsapp Parcial` ao cliente ("...análise complementar... até 7 dias úteis... não precisa realizar nova solicitação ou pagamento") → `Update Partial Report` (`PARTIAL_REPORT_SENT`) → `PT Report  Parcial` (`LAUDO_PARCIAL/LAUDO_PARCIAL`) → `Webhook Response Parcial`.

> ⚠️ O laudo parcial **não vai ao e-mail do cliente** — vai para a caixa interna; o cliente recebe WhatsApp.

### 5.3 — Sobrescrita final pelo orchestrator

Após `pipeline_completo.sh` sair com `exit 0`, o orchestrator executa `update_status_in_db('REPORT_SENT')` — **sobrescrevendo** `FINAL_REPORT_SENT`/`PARTIAL_REPORT_SENT`. Estado terminal real = `REPORT_SENT`. Para saber o desfecho, consultar `process_tracking`.

---

## Fase 6 — Alertas (3 workflows agendados, a cada 10 min)

### Alerta_ERROS_GRAVES — watchdog ampliado (7 nós)

Query real cobre **três grupos**:

```sql
-- (a) Erros de pipeline sem laudo parcial associado
current_state IN ('PIPELINE_ERROR','AUTH_ERROR','DOWNLOAD_FAILED','CALC_ERROR')
  AND NOT EXISTS (LAUDO_PARCIAL no tracking da consulta)

-- (b) Pagamento aprovado e esquecido (worker caído/lock perdido)
current_state = 'PAYMENT_APPROVED' AND state_updated_at < NOW() - INTERVAL '2 hours'

-- (c) Laudo fantasma: report marcado enviado mas SEM cálculo e COM processo não-rejeitado
current_state IN ('REPORT_SENT','FINAL_REPORT_SENT')
  AND state_updated_at < NOW() - INTERVAL '30 minutes'
  AND NOT EXISTS (registro em esaj_calc_precatorio_resumo)
  AND EXISTS (processo em esaj_detalhe_processos com rejeitado=false)
```

Ação: WhatsApp ao cliente ("análise complementar... 7 dias úteis... não precisa nova solicitação ou pagamento") + e-mail interno a `revisa.manual@gmail.com` com erros OCR agregados → `UPDATE → ALERTA_MANUAL_SENT` (aceita origem MANUAL_PROCESS/PIPELINE_ERROR/AUTH_ERROR/DOWNLOAD_FAILED/CALC_ERROR/REPORT_SENT/FINAL_REPORT_SENT/PAYMENT_APPROVED) → log.

### Alerta_Laudo_Parcial (6 nós)

Detecta `LAUDO_PARCIAL` sem `PARCIAL_INFORMADO` (por cpf+consulta_id) → e-mail interno a `revisa.manual@gmail.com` com lista de processos → insere `PARCIAL_INFORMADO` → log `'BATCH'`.

### Alerta_Reporte_Manual (7 nós)

`current_state='MANUAL_PROCESS'` → WhatsApp ao cliente + e-mail a `revisa.manual@gmail.com` → `UPDATE → ALERTA_MANUAL_SENT` → log `'BATCH'`.

### Alerta_PDF_antigo (INATIVO ×2)

Existem **2 workflows inativos** com esse nome (`PMyNPcPlRZMZjCb1`, `Uck9WlB08COLVM1K`) — query idêntica ao Reporte_Manual, sem distinção de causa. Desabilitados; não fazem parte da operação.

---

## Destinatários reais de comunicação (verificado 20/09/2026)

| Mensagem | Destino |
|---|---|
| Laudo completo | `email` do webhook (cliente) — **sem CC** |
| Laudo parcial | `revisa.manual@gmail.com` (fixo) |
| WhatsApp laudo parcial | `whatsapp_phone_number` da consulta |
| Alertas internos (3 workflows) | `revisa.manual@gmail.com` |
| WhatsApp alerta ao cliente | `whatsapp_from` da consulta |
| E-mail verificação | `email` informado no chatbot |
