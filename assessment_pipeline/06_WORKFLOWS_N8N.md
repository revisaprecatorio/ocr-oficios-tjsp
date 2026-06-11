# Workflows n8n — Revisa Precatório

**Atualizado:** 06/2026 | **Fonte:** análise dos JSONs em `workflows_n8n/`

Os workflows JSON ficam em `workflows_n8n/` na raiz deste repositório. Para importar no n8n: **Settings → Import Workflow → Upload JSON**.

---

## Índice

| # | Workflow | Tipo | Trigger |
|---|---|---|---|
| 1 | [Chatbot Revisa](#1-chatbot-revisa) | Pipeline | Webhook WhatsApp |
| 2 | [Mercado Pago Unified](#2-mercado-pago-unified) | Pipeline | Webhook MP + Webhook interno |
| 3 | [Laudo envio email+cpf](#3-laudo-envio-emailcpf) | Pipeline | Webhook `POST /reporte-email-cpf` |
| 4 | [Alerta_ERROS_GRAVES](#4-alerta_erros_graves) | Monitoramento | Schedule (10 min) |
| 5 | [Alerta_Laudo_Parcial](#5-alerta_laudo_parcial) | Monitoramento | Schedule (10 min) |
| 6 | [Alerta_Reporte_Manual](#6-alerta_reporte_manual) | Monitoramento | Schedule (10 min) |
| 7 | [CPF_batch_processing](#7-cpf_batch_processing) | Ferramenta auxiliar | Webhook `POST /cpf-batch-processing` |

---

## 1. Chatbot Revisa

**Arquivo:** `workflows_n8n/Chatbot Revisa.json`  
**Webhook:** `POST/GET /webhook/whatsapp-beta-agent`  
**Nós:** 35 | **Linguagem principal:** JavaScript (Code nodes)

### Função

Ponto de entrada da plataforma. Recebe mensagens do WhatsApp via Meta API e implementa uma **máquina de estados conversacional** que guia o cliente do CPF até o pagamento.

### Lógica geral

```
Mensagem WhatsApp recebida
  → Process Input (filtra status webhooks — delivered/read/sent)
  → Get User State (consulta current_state por whatsapp_from)
  → Route Message Type (switch: CPF | EMAIL | CODE | CONFIRM_YES | CONFIRM_NO | MENU | AGENT | ...)
  → Update State (grava novo estado no banco)
  → Send WhatsApp Response (envia resposta ao cliente)
```

### Estados que o chatbot gerencia

| Estado entrada | Ação do chatbot | Próximo estado |
|---|---|---|
| `IDLE` (sem registro) | Apresenta menu, solicita CPF | `AWAITING_EMAIL` |
| `AWAITING_EMAIL` | Recebe CPF → consulta e-SAJ → solicita email | `AWAITING_CODE` |
| `AWAITING_CODE` | Gera código → envia por email → aguarda código | `AWAITING_CONFIRMATION` |
| `AWAITING_CONFIRMATION` | Exibe nome e processos encontrados → aguarda confirmação | `AWAITING_PAYMENT` |
| `AWAITING_PAYMENT` | Dispara geração de link MP | `PAYMENT_APPROVED` (via MP) |

**Timeouts tratados pelo bot:**
- `AWAITING_CODE` → expira em 15 min
- `AWAITING_EMAIL` / `AWAITING_CONFIRMATION` → expira em 30 min
- `AWAITING_PAYMENT` → expira em 60 min

### Nós principais

| Nó | Tipo | Função |
|---|---|---|
| `Webhook Trigger` | Webhook | Recebe mensagens WhatsApp (`GET,POST`) |
| `Process Input` | Code | Filtra status webhooks; extrai `message_text`, `from` |
| `Get User State` | Postgres | `SELECT current_state, minutes_since_update, stored_code, stored_email` por `whatsapp_from` |
| `Merge State` | Set | Normaliza estado para roteamento |
| `Route Message Type` | Switch | Decide fluxo: CPF / EMAIL / CODE / CONFIRM / MENU / AGENT |
| `Consulta e-SAJ` | HTTP Request | Chama TJSP para buscar processos por CPF |
| `Parse e-SAJ Response` | Code | Extrai lista de processos do HTML do TJSP |
| `Generate Verification Code` | Code | Gera código de 6 dígitos |
| `Send Verification Email` | Email Send | Envia código por email via SMTP |
| `Validate Code` | Code | Compara código digitado com `stored_code` |
| `Save Consulta` | Postgres | INSERT em `consultas_esaj` com CPF, processos, email |
| `Trigger Payment Workflow` | HTTP Request | POST para `Mercado Pago Unified` (`/generate-payment-link`) |
| `Update State` | Postgres | UPDATE `consultas_esaj.current_state` |
| `Send WhatsApp Response` | WhatsApp | Envia resposta ao cliente |
| `PT - Consulta Solicitada` | Postgres | INSERT em `process_tracking` (evento `CONSULTA_SOLICITADA`) |
| `Consulta Realizada` | Postgres | INSERT em `process_tracking` (evento `CONSULTA_REALIZADA`) |
| `PT - TJSP Inoperante` | Postgres | Registra indisponibilidade do e-SAJ |
| `Email Alerta TJSP` | Email Send | Notifica equipe quando e-SAJ está fora |
| `WA Alerta Operacao TJSP` | WhatsApp | WhatsApp interno quando e-SAJ está fora |

### Tabelas afetadas

- **`consultas_esaj`** — INSERT (novo registro) + UPDATE (estado, email, processos)
- **`process_tracking`** — INSERT (`CONSULTA_SOLICITADA`, `CONSULTA_REALIZADA`)

---

## 2. Mercado Pago Unified

**Arquivo:** `workflows_n8n/Mercado Pago Unified.json`  
**Webhooks:** `POST /generate-payment-link` (interno) + `POST /mercadopago-notification` (MP)  
**Nós:** 18

### Função

Workflow com **dois pontos de entrada independentes**:

1. **Geração de link:** chamado pelo Chatbot quando cliente chega em `AWAITING_PAYMENT`
2. **Notificação de pagamento:** chamado automaticamente pelo Mercado Pago após eventos de pagamento

### Fluxo 2a — Geração do Link

```
Webhook (POST /generate-payment-link)
  → Validate Trigger Payment (IF: trigger_payment=true && email presente)
  → Generate Payment Link (POST https://api.mercadopago.com/checkout/preferences)
  → Save Payment Link (UPDATE consultas_esaj: mp_preference_id, payment_link, current_state=AWAITING_PAYMENT)
  → Cleanup Session Record (DELETE registro temporário cpf='00000000000')
  → Send Payment Link WA (envia link ao cliente via WhatsApp)
  → PT Link Gerado (INSERT process_tracking: PAYMENT/LINK_GERADO)
```

### Fluxo 2b — Notificação de Pagamento

```
Webhook (POST /mercadopago-notification)
  → Respond OK to MP (responde {status: ok} imediatamente — anti-timeout)
  → Filter Payment Events (IF: type = 'payment')
  → Get Payment Details (GET https://api.mercadopago.com/v1/payments/{id})
  → Process Payment Status (Code: approved → PAYMENT_APPROVED | rejected → PAYMENT_REJECTED | pending → PAYMENT_PENDING)
  → Update Payment Status (UPDATE consultas_esaj: mp_payment_id, mp_payment_status, current_state, payment_confirmed_at)
  → Send WhatsApp Notification (notifica cliente sobre status)
  → PT Status Pagamento (INSERT process_tracking: PAYMENT/PAYMENT_APPROVED ou PAYMENT_REJECTED)
```

> **Importante:** O webhook responde `200 OK` ao MP **antes** de processar os dados. Isso evita retry storms do Mercado Pago por timeout.

### Nós principais

| Nó | Tipo | Função |
|---|---|---|
| `Webhook` | Webhook | Recebe notificações do MP (`/mercadopago-notification`) |
| `Generate Link Webhook` | Webhook | Recebe chamada interna do Chatbot (`/generate-payment-link`) |
| `Respond OK to MP` | Respond to Webhook | Retorna 200 imediatamente ao MP |
| `Filter Payment Events` | IF | Filtra apenas eventos `type='payment'` |
| `Get Payment Details` | HTTP Request | `GET /v1/payments/{id}` na API do MP |
| `Process Payment Status` | Code | Mapeia status MP → estado interno |
| `Validate Trigger Payment` | IF | Valida `trigger_payment=true` e `email` não vazio |
| `Generate Payment Link` | HTTP Request | `POST /checkout/preferences` na API do MP |
| `Save Payment Link` | Postgres | UPDATE `consultas_esaj` com dados do link |
| `Cleanup Session Record` | Postgres | Remove registro temporário de sessão |
| `Update Payment Status` | Postgres | UPDATE estado e dados do pagamento |
| `Send WhatsApp Notification` | WhatsApp | Notifica cliente sobre resultado do pagamento |
| `Send Payment Link WA` | WhatsApp | Envia link de pagamento ao cliente |
| `Log Payment Success` | Postgres | INSERT em `logs` |
| `PT Link Gerado` | Postgres | INSERT `process_tracking` (evento `LINK_GERADO`) |
| `PT Status Pagamento` | Postgres | INSERT `process_tracking` (evento `PAYMENT_APPROVED/REJECTED`) |

### Tabelas afetadas

- **`consultas_esaj`** — UPDATE (mp_preference_id, payment_link, mp_payment_id, current_state)
- **`process_tracking`** — INSERT (`PAYMENT/LINK_GERADO`, `PAYMENT/PAYMENT_APPROVED`)
- **`logs`** — INSERT (log textual)

---

## 3. Laudo envio email+cpf

**Arquivo:** `workflows_n8n/Laudo envio email+cpf.json`  
**Webhook:** `POST /webhook/reporte-email-cpf`  
**Nós:** 19 | **Chamado por:** `orchestrator_subprocess.py` (Windows Server)

### Função

Recebe CPF + email do orchestrator, consulta `vw_precatorios_full`, monta laudo HTML personalizado e envia por email. Atualiza o estado final do job.

### Fluxo principal

```
Webhook (POST /reporte-email-cpf)  ← body: {cpf, email}
  → Check Processamento Completo (SELECT todos_processados de esaj_detalhe_processos)
  → Todos Processados? (IF: todos_processados=true)
  │
  ├── [SIM — laudo completo]
  │     → Fetch Data for CPF (SELECT * FROM vw_precatorios_full WHERE cpf=?)
  │     → Build HTML Content (Code: monta HTML com todos os processos, valores, indicadores)
  │     → Send Report Email (envia email ao cliente)
  │     → Update Report Status (UPDATE consultas_esaj: current_state=FINAL_REPORT_SENT)
  │     → Log Success / PT Report Enviado
  │     → Webhook Response (200 OK)
  │
  └── [NÃO — laudo parcial]
        → Fetch Data for CPF - parcial (SELECT * FROM vw_precatorios_full WHERE cpf=?)
        → Build HTML Parcial (Code: monta HTML parcial, indica processos pendentes)
        → Send Report Revisa (envia cópia interna para contato@revisaprecatorio.com.br)
        → Whatsapp Parcial (notifica cliente via WhatsApp sobre laudo parcial)
        → Update Partial Report (UPDATE consultas_esaj: current_state=PARTIAL_REPORT_SENT)
        → Log Parcial e Manual / PT Report Parcial
        → Webhook Response Parcial (200 OK)
```

### Build HTML Content

O nó `Build HTML Content` (Function node, ~200 linhas JS) monta o laudo com:
- Nome do credor, vara, número CNJ
- Valor corrigido (`total_corrigido` de `esaj_calc_precatorio_resumo`)
- Saldo final, data base de atualização
- Status de cada processo (rejeitado / pendente)
- Motivo de rejeição (quando aplicável)
- Indicadores: idoso, doença grave, PCD, preferencial, habilitação de herdeiros, óbito
- Dados bancários (banco, agência, conta)
- Total consolidado de todos os processos não rejeitados

### Nós principais

| Nó | Tipo | Função |
|---|---|---|
| `Webhook Email + CPF` | Webhook | Recebe `{cpf, email}` do orchestrator |
| `Check Processamento Completo` | Postgres | Verifica se todos os processos foram processados |
| `Todos Processados?` | IF | Bifurca entre laudo completo e parcial |
| `Fetch Data for CPF` | Postgres | `SELECT * FROM vw_precatorios_full WHERE cpf=?` |
| `Build HTML Content` | Function | Monta laudo HTML completo (~200 linhas JS) |
| `Send Report Email` | Email Send | Envia laudo ao email do cliente |
| `Update Report Status` | Postgres | UPDATE `current_state = FINAL_REPORT_SENT` |
| `phone e nome` | Set | Extrai telefone e nome para notificações parciais |
| `Build HTML Parcial` | Function | Monta versão parcial do laudo |
| `Send Report Revisa` | Email Send | Envia cópia interna para equipe |
| `Whatsapp Parcial` | WhatsApp | Notifica cliente sobre laudo parcial |
| `Update Partial Report` | Postgres | UPDATE `current_state = PARTIAL_REPORT_SENT` |
| `PT Report Enviado` | Postgres | INSERT `process_tracking` (evento `LAUDO_ENVIADO`) |
| `PT Report Parcial` | Postgres | INSERT `process_tracking` (evento `LAUDO_PARCIAL`) |

### Tabelas afetadas

- **`consultas_esaj`** — UPDATE (`current_state`: `FINAL_REPORT_SENT` ou `PARTIAL_REPORT_SENT`)
- **`process_tracking`** — INSERT (`ENVIO_LAUDO/LAUDO_ENVIADO` ou `LAUDO_PARCIAL/LAUDO_PARCIAL`)

---

## 4. Alerta_ERROS_GRAVES

**Arquivo:** `workflows_n8n/Alerta_ERROS_GRAVES.json`  
**Trigger:** Schedule a cada **10 minutos**  
**Nós:** 8

### Função

Monitora CPFs em estados de erro crítico e notifica o cliente (WhatsApp) + equipe interna (email). Atualiza estado para `ALERTA_MANUAL_SENT` para evitar reenvios.

### Estados monitorados

```sql
WHERE current_state IN ('MANUAL_PROCESS', 'PIPELINE_ERROR', 'AUTH_ERROR', 'DOWNLOAD_FAILED')
```

### Fluxo

```
Schedule Trigger (a cada 10 min)
  → Query consultas_esaj (SELECT CPFs em estados de erro, com mensagens de OCR via LEFT JOIN process_tracking)
  → Prepara Mensagens (Code: monta msg_cliente + msg_interna_html com lista de processos e detalhes do erro)
  → WhatsApp Cliente (avisa cliente que laudo chegará em 7 dias úteis)
  → Email contato@revisaprecatorio (alerta interno com detalhes técnicos)
  → Email persival@gmail (cópia para desenvolvedor)
  → Update current_state ALERTA_MANUAL_SENT (UPDATE consultas_esaj)
  → Log Alerta Manual (INSERT logs)
```

### Mensagem ao cliente

> *"Verificamos que o seu precatório tem documentos escaneados ou com incompatibilidade de configuração no sistema do Tribunal de Justiça, motivo pelo qual o laudo será encaminhado em até 7 dias úteis em seu email."*

### Nós principais

| Nó | Tipo | Função |
|---|---|---|
| `Schedule Trigger` | scheduleTrigger | Dispara a cada 10 min |
| `Query consultas_esaj` | Postgres | Busca CPFs em erro + mensagens OCR via `process_tracking` |
| `Prepara Mensagens` | Code | Monta texto do cliente e HTML interno com processos envolvidos |
| `WhatsApp Cliente` | WhatsApp | Notifica cliente |
| `Email contato@revisaprecatorio` | Email Send | Alerta operacional interno |
| `Email persival@gmail` | Email Send | Cópia para desenvolvedor |
| `Update current_state ALERTA_MANUAL_SENT` | Postgres | Evita reenvio do alerta |
| `Log Alerta Manual` | Postgres | INSERT em `logs` |

### Tabelas afetadas

- **`consultas_esaj`** — UPDATE (`current_state = ALERTA_MANUAL_SENT`)
- **`logs`** — INSERT

---

## 5. Alerta_Laudo_Parcial

**Arquivo:** `workflows_n8n/Alerta_Laudo_Parcial.json`  
**Trigger:** Schedule a cada **10 minutos**  
**Nós:** 7

### Função

Detecta CPFs que receberam laudo parcial (`LAUDO_PARCIAL` em `process_tracking`) mas ainda **não tiveram o alerta interno enviado** (`PARCIAL_INFORMADO` ausente). Notifica equipe interna para reprocessamento manual.

### Query de detecção

```sql
SELECT pt.*, ce.whatsapp_from, ce.nome_requerente, ce.email, ce.processos
FROM process_tracking pt
JOIN consultas_esaj ce ON ce.cpf = pt.cpf
WHERE pt.evento = 'LAUDO_PARCIAL'
AND NOT EXISTS (
    SELECT 1 FROM process_tracking pt2
    WHERE pt2.cpf = pt.cpf
    AND pt2.consulta_id IS NOT DISTINCT FROM pt.consulta_id
    AND pt2.evento = 'PARCIAL_INFORMADO'
)
```

### Fluxo

```
Schedule Trigger (a cada 10 min)
  → Query Laudo Parcial (detecta LAUDO_PARCIAL sem PARCIAL_INFORMADO)
  → Prepara Mensagens (Code: monta lista de processos para alerta interno)
  → Email contato@revisaprecatorio (notifica equipe para reprocessamento)
  → Email persival@gmail (cópia para desenvolvedor)
  → Insert PARCIAL_INFORMADO (INSERT process_tracking: evento=PARCIAL_INFORMADO — evita reenvio)
  → Log Laudo Parcial (INSERT logs)
```

### Nós principais

| Nó | Tipo | Função |
|---|---|---|
| `Schedule Trigger` | scheduleTrigger | Dispara a cada 10 min |
| `Query Laudo Parcial` | Postgres | Detecta laudos parciais sem alerta enviado |
| `Prepara Mensagens` | Code | Monta HTML com lista de processos e email do cliente |
| `Email contato@revisaprecatorio` | Email Send | Notificação interna para equipe |
| `Email persival@gmail` | Email Send | Cópia para desenvolvedor |
| `Insert PARCIAL_INFORMADO` | Postgres | Marca alerta como enviado em `process_tracking` |
| `Log Laudo Parcial` | Postgres | INSERT em `logs` |

### Tabelas afetadas

- **`process_tracking`** — INSERT (evento `LAUDO_PARCIAL/PARCIAL_INFORMADO`)
- **`logs`** — INSERT

---

## 6. Alerta_Reporte_Manual

**Arquivo:** `workflows_n8n/Alerta_Reporte_Manual.json`  
**Trigger:** Schedule a cada **10 minutos**  
**Nós:** 8

### Função

Monitora CPFs em estado `MANUAL_PROCESS` (OCR falhou, requer intervenção humana) e notifica cliente + equipe. Similar ao `Alerta_ERROS_GRAVES` mas focado exclusivamente no estado `MANUAL_PROCESS`.

> **Nota sobre sobreposição:** `Alerta_ERROS_GRAVES` já monitora `MANUAL_PROCESS` entre outros estados. Este workflow trata especificamente o caso de OCR parcial/falho, com mensagens ligeiramente diferentes.

### Fluxo

```
Schedule Trigger (a cada 10 min)
  → Query consultas_esaj (SELECT WHERE current_state = 'MANUAL_PROCESS')
  → Prepara Mensagens (Code: monta msg_cliente + msg_interna_html)
  → WhatsApp Cliente (avisa cliente que laudo chegará em 7 dias úteis)
  → Email contato@revisaprecatorio (alerta operacional interno)
  → Email persival@gmail (cópia para desenvolvedor)
  → Update current_state ALERTA_MANUAL_SENT
  → Log Alerta Manual (INSERT logs)
```

### Tabelas afetadas

- **`consultas_esaj`** — UPDATE (`current_state = ALERTA_MANUAL_SENT`)
- **`logs`** — INSERT

---

## 7. CPF_batch_processing

**Arquivo:** `workflows_n8n/CPF_batch_processing.json`  
**Webhook:** `POST /webhook/cpf-batch-processing`  
**Nós:** 6 | **Tipo:** Ferramenta auxiliar (não faz parte do pipeline principal)

### Função

Permite processar um CPF diretamente, **sem passar pelo fluxo WhatsApp**. Consulta o e-SAJ pelo CPF e insere/atualiza o registro em `consultas_esaj`, atribuindo um `whatsapp_from` fixo de suporte.

**Casos de uso:**
- Reprocessar um CPF manualmente após erro
- Cadastrar clientes que chegaram por fora do WhatsApp
- Testes de integração sem interação conversacional
- Inserção em lote de CPFs via API

### Fluxo

```
Webhook (POST /cpf-batch-processing)  ← body: {cpf}
  → Extract CPF (Set: normaliza CPF — remove pontos/traços; hardcodes whatsapp_from='5511941455345')
  → Consulta e-SAJ (HTTP Request: GET TJSP — busca processos por CPF)
  → Parse e-SAJ Response (Code: extrai lista de processos do HTML TJSP)
  → Upsert Consulta (Postgres: INSERT ON CONFLICT (cpf) DO UPDATE em consultas_esaj)
  → Respond to Webhook (200 OK com resultado)
```

### Nós

| Nó | Tipo | Função |
|---|---|---|
| `Webhook Trigger` | Webhook | Recebe `{cpf}` |
| `Extract CPF` | Set | Normaliza CPF; define `whatsapp_from` fixo |
| `Consulta e-SAJ` | HTTP Request | GET TJSP pelo CPF |
| `Parse e-SAJ Response` | Code | Extrai processos do HTML |
| `Upsert Consulta` | Postgres | `INSERT ON CONFLICT DO UPDATE` em `consultas_esaj` |
| `Respond to Webhook` | Respond to Webhook | Retorna resultado |

### Tabelas afetadas

- **`consultas_esaj`** — INSERT (ou UPDATE via ON CONFLICT)

### Observações

- O `whatsapp_from` é fixado em `5511941455345` (número da equipe) — o cliente não é notificado via WhatsApp
- Após o upsert, o registro entra no fluxo normal: o orchestrator detecta `PAYMENT_APPROVED` e processa normalmente se `current_state` for setado corretamente
- **Não há cobrança** neste fluxo — use apenas para reprocessamento interno

---

## Credenciais utilizadas (resumo)

| Credencial | Usada em | Tipo |
|---|---|---|
| `Postgres account` (id: `b0F0gRzrpEq6BR3M`) | Todos os workflows | PostgreSQL — `72.60.62.124:5432/n8n` |
| `Mercado Pago API` | Mercado Pago Unified | HTTP Header Auth (Access Token) |
| SMTP | Chatbot (código), Laudo, Alertas | Email Send |
| Meta WhatsApp API | Chatbot, Laudo, Alertas | HTTP Header Auth |
