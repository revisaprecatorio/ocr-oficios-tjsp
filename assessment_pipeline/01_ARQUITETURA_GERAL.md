# Assessment do Pipeline Completo — Revisa Precatório
**Data:** 07/2026 | **Versão:** 1.0

---

## 1. Visão Geral

O pipeline da Revisa é um sistema de ponta a ponta que transforma uma solicitação de cliente (via WhatsApp) em um laudo de análise de precatório. Envolve 5 componentes em sequência:

```
[Cliente WhatsApp]
       │
       ▼
[n8n: Chatbot Revisa]  ──► consultas_esaj (PAYMENT_PENDING)
       │
       ▼ (pagamento aprovado)
[consultas_esaj: PAYMENT_APPROVED]
       │
       ▼ (watchdog via PM2/Task Scheduler)
[Windows Server: orchestrator_subprocess.py]
       ├── crawler_full.py (Selenium → e-SAJ → download PDFs)
       ├── pipeline_completo.sh (OCR → Ingestão → Cálculo)
       │     ├── processador.py (extração estruturada)
       │     ├── ingest_all_jsons.py (PostgreSQL)
       │     └── calc-precatorio-tjsp/main.py (cálculo)
       └── Webhook n8n → envio do laudo
```

---

## 2. Componentes e Repositórios

| Componente | Repositório | Caminho no VPS | Função |
|---|---|---|---|
| **Chatbot + Pagamento** | n8n (workflows) | — | Captura CPF, gera link MP, registra pagamento |
| **Crawler TJSP** | `crawler_tjsp` | `C:\...\crawler_tjsp\core\` | Download de PDFs do e-SAJ via Selenium |
| **OCR Pipeline** | `ocr-oficios-tjsp` | `C:\...\ocr-oficios-tjsp\` | Extração de dados dos PDFs |
| **Cálculo** | `calc-precatorio-tjsp` | `C:\...\calc-precatorio-tjsp\` | Cálculo dos valores do precatório |
| **Banco de Dados** | PostgreSQL externo | `72.60.62.124:5432 / n8n` | Estado, logs e dados extraídos |

---

## 3. Tabelas do Banco de Dados

### `consultas_esaj` — Estado do Job

Controla o ciclo de vida de cada solicitação de cliente.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL | PK |
| `cpf` | VARCHAR | CPF do cliente |
| `processos` | JSONB | Lista de processos `{"lista": [{"numero": "...", "classe": "Precatório"}]}` |
| `current_state` | VARCHAR | Estado atual do job (ver ciclo abaixo) |
| `state_updated_at` | TIMESTAMP | Última mudança de estado |
| `status` | BOOLEAN | `true` = processamento concluído |

**Ciclo de estados `current_state`** — completo, confirmado pelos workflows n8n:

```
IDLE  (ausência de registro ou timeout de sessão)
  └─► AWAITING_EMAIL         (chatbot pediu email)
        └─► AWAITING_CODE    (código de verificação enviado — expira em 15 min)
              └─► AWAITING_CONFIRMATION  (chatbot aguarda confirmação de dados)
                    └─► AWAITING_PAYMENT  (link MP gerado — expira em 60 min)
                          ├─► PAYMENT_APPROVED    (MP confirmou)
                          └─► PAYMENT_REJECTED    (MP rejeitou)

PAYMENT_APPROVED
    └─► PROCESSING            (orchestrator lockado — FOR UPDATE SKIP LOCKED)
            ├─► FINAL_REPORT_SENT   (laudo completo enviado — todos_processados=true)
            ├─► PARTIAL_REPORT_SENT (laudo parcial enviado — todos_processados=false)
            ├─► PIPELINE_ERROR      (OCR ou cálculo falharam totalmente)
            ├─► AUTH_ERROR          (autenticação e-SAJ falhou)
            ├─► DOWNLOAD_FAILED     (PDFs não baixados)
            ├─► NO_VALID_PROCESS    (nenhum precatório na lista)
            └─► MANUAL_PROCESS      (OCR falhou — set por processador.py)
                    └─► ALERTA_MANUAL_SENT  (Alerta_Reporte_Manual enviou alertas)
```

> ⚠️ **`REPORT_SENT` é transitório:** o orchestrator seta `REPORT_SENT`, mas o workflow **Laudo envio email+cpf** o substitui por `FINAL_REPORT_SENT` (completo) ou `PARTIAL_REPORT_SENT` (parcial) ao processar o envio. Nas queries de monitoramento, use esses dois estados para filtrar laudos enviados.

### `logs` — Log Textual da Pipeline

Registro cronológico de eventos durante execução.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL | PK |
| `cpf` | VARCHAR | CPF relacionado |
| `timestamp` | TIMESTAMP | Momento do evento |
| `descricao` | TEXT | Mensagem do evento |
| `processo` | VARCHAR | Tag da origem: `crawler`, `OCR`, `PIPELINE` |

### `process_tracking` — Rastreamento Estruturado por Evento

Registro de eventos estruturados por consulta/cliente, com metadados em JSON.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL | PK |
| `consulta_id` | INT | FK para `consultas_esaj.id` |
| `cpf` | VARCHAR | CPF do cliente |
| `whatsapp_phone_number` | VARCHAR | Telefone WhatsApp do cliente |
| `etapa` | VARCHAR | Grupo do evento: `CONSULTA`, `PAYMENT`, `OCR`, `ENVIO_LAUDO`, `LAUDO_PARCIAL` |
| `evento` | VARCHAR | Evento específico (ver lista abaixo) |
| `sucesso` | BOOLEAN | Se o evento foi bem-sucedido |
| `erro` | BOOLEAN | Se houve erro |
| `mensagem_erro` | TEXT | Detalhe do erro |
| `detalhes` | JSONB | Contexto adicional (node, workflow, valores, IDs). Exportado como `metadata` em dumps CSV. |
| `created_at` | TIMESTAMP | Momento do evento |

**Eventos registrados (`etapa.evento`):**

| etapa | evento | Quem registra | Significado |
|---|---|---|---|
| CONSULTA | CONSULTA_SOLICITADA | Chatbot n8n | Usuário enviou o CPF |
| CONSULTA | CONSULTA_REALIZADA | Chatbot n8n | e-SAJ consultado com sucesso |
| PAYMENT | LINK_GERADO | Mercado Pago Unified | Link de pagamento criado |
| PAYMENT | PAYMENT_APPROVED | Mercado Pago Unified | Pagamento confirmado |
| OCR | OCR_ERRO | processador.py | Falha ao extrair dados do PDF |
| ENVIO_LAUDO | LAUDO_ENVIADO | Laudo envio email+cpf | Laudo completo enviado |
| LAUDO_PARCIAL | LAUDO_PARCIAL | Laudo envio email+cpf | Laudo enviado com processos parciais |
| LAUDO_PARCIAL | PARCIAL_INFORMADO | Alerta_Laudo_Parcial | Alerta interno enviado para Revisa |

### `esaj_detalhe_processos` — Dados Extraídos dos PDFs

35 colunas com os dados estruturados de cada processo após OCR + ingestão. Alimentada pela Etapa 4 da pipeline.

---

## 4. Infraestrutura de Execução (Windows Server)

O worker roda no Windows Server (VPS) e é gerenciado por PM2 ou Task Scheduler:

```
PM2 / Task Scheduler
    └─► start_worker.py        (launcher: limpa Chrome, inicia orquestrador)
            └─► orchestrator_subprocess.py  (processa UM job por execução)
                    └─► crawler_full.py          (Selenium: navega e-SAJ, baixa PDFs)
```

**Paths críticos no VPS:**
- Downloads temporários: `C:\Temp\RevisaDownloads\{cpf}\`
- Downloads arquivados: `C:\Temp\RevisaDownloads_Processados\{cpf}\{data}\`
- OCR Script: `C:\...\ocr-oficios-tjsp\run_sh_wrapper.bat`
- OCR Pipeline: `C:\...\ocr-oficios-tjsp\pipeline_completo.sh`
- Cálculo: `C:\...\calc-precatorio-tjsp\main.py`
