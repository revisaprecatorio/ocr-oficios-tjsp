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
| **Crawler TJSP** | [`crawler_tjsp`](https://github.com/revisaprecatorio/crawler_tjsp) | `C:\...\crawler_tjsp\` | Download de PDFs do e-SAJ via Selenium + cert. A1 |
| **OCR Pipeline** | [`ocr-oficios-tjsp`](https://github.com/revisaprecatorio/ocr-oficios-tjsp) | `C:\...\ocr-oficios-tjsp\` | Extração de dados dos PDFs (35 campos) + ingestão |
| **Cálculo** | `calc-precatorio-tjsp` | `C:\...\calc-precatorio-tjsp\` | Atualização monetária; insere em `esaj_calc_precatorio_resumo` |
| **Banco de Dados** | PostgreSQL externo | `72.60.62.124:5432 / n8n` | Estado, logs e dados extraídos |

### Crawler TJSP — Detalhes

O `crawler_tjsp` roda em **Windows Server** (requisito para o certificado digital A1 via Web Signer + Chrome). Uma tentativa anterior de rodar em Linux foi bloqueada pelo Native Messaging Protocol do Chrome em modo headless via Selenium.

**Componentes internos:**

```
crawler_tjsp/
├── crawler_full.py              # Motor Selenium: autentica, navega e-SAJ, baixa PDFs
├── orchestrator_subprocess.py   # Worker daemon: polling do banco, 1 job por vez
├── start_worker.py              # Launcher: limpa processos Chrome, inicia orquestrador
└── requirements.txt             # selenium==4.25, psycopg2, fastapi, requests
```

**Fluxo do crawler:**

```
start_worker.py
  └─► orchestrator_subprocess.py  (FOR UPDATE SKIP LOCKED — previne jobs duplos)
          └─► crawler_full.py --doc {cpf} --abrir-autos --baixar-pdf --turbo-download
                  1. Inicia Chrome com perfil configurado (certificado A1 importado)
                  2. Acessa https://esaj.tjsp.jus.br
                  3. Autentica via certificado digital A1 (Web Signer)
                  4. Busca processos por CPF (formulário TJSP)
                  5. Abre Pasta Digital de cada processo
                  6. Seleciona documentos (jstree)
                  7. Baixa PDFs (modo TURBO via JavaScript ou fallback HTTP)
                  8. Retorna JSON com metadados
```

**Parâmetros do crawler_full.py:**

| Parâmetro | Descrição |
|---|---|
| `--doc` | CPF/CNPJ ou Número CNJ |
| `--abrir-autos` | Abre Pasta Digital |
| `--baixar-pdf` | Baixa PDFs |
| `--turbo-download` | Seleção de docs via JavaScript (mais rápido) |
| `--download-dir` | Diretório de saída (padrão: `downloads/`) |
| `--headless` | Sem interface gráfica |
| `--debugger-address` | Anexa a Chrome existente |

**Paths no Windows Server:**

```
Downloads temporários: C:\Temp\RevisaDownloads\{cpf}\
Downloads arquivados:  C:\Temp\RevisaDownloads_Processados\{cpf}\{data}\
```

**Gerenciado por:** PM2 ou Task Scheduler do Windows

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

35 colunas com os dados estruturados de cada processo após OCR + ingestão. Alimentada pela Etapa 4 da pipeline. Ver `SCHEMA_TABELA.md` para o schema completo.

**Campos-chave para monitoramento:**
- `rejeitado` (BOOLEAN) — ofício rejeitado pelo DEPRE
- `motivo_rejeicao` (TEXT) — motivo completo extraído do PDF
- `anomalia` (BOOLEAN) — inconsistência detectada no OCR
- `numero_ordem` (VARCHAR) — número de ordem do ofício (vazio = sem aceite DEPRE)

### `esaj_calc_precatorio_resumo` — Resultado do Cálculo

Alimentada pelo script `calc-precatorio-tjsp/main.py` após OCR. **A existência de um registro nesta tabela para um dado CPF é o que dispara o envio do laudo.** Se esta tabela não tiver registros para um CPF, o laudo nunca será enviado.

| Coluna | Tipo | Descrição |
|---|---|---|
| `cpf` | VARCHAR | CPF do credor |
| `numero_processo_cnj` | VARCHAR | Número do processo CNJ |
| `total_corrigido` | NUMERIC | Valor total atualizado com correção monetária |
| *(demais colunas)* | *—* | *Schema completo no repositório `calc-precatorio-tjsp`* |

> ⚠️ **Atenção — Cenário F:** Quando todos os processos de um CPF estão `rejeitado = true`, o `main.py` retorna `"Nenhum processo pendente."` e **não insere registros** nesta tabela. Consequentemente, o webhook `/reporte-email-cpf` nunca é chamado e o cliente não recebe o laudo. Ver detalhes em `03_CENARIOS_E_TABELAS.md` — Cenário F.

### `vw_precatorios_full` — View de Consolidação

View do PostgreSQL que faz `LEFT JOIN` entre `esaj_detalhe_processos` (dados OCR) e `esaj_calc_precatorio_resumo` (dados de cálculo). É consultada pelo workflow `"Laudo envio email+cpf"` para construir o HTML do laudo.

```
Colunas relevantes retornadas pela view:
  (de esaj_detalhe_processos)
  cpf, numero_processo_cnj, credor_nome, vara, banco, agencia, conta,
  valor_total_requisitado, saldo_final, rejeitado, motivo_rejeicao,
  idoso, doenca_grave, pcd, preferencial, habilitacao_herdeiros,
  obito, data_obito, cpf_sucessor, numero_ordem, data_nascimento
  (de esaj_calc_precatorio_resumo)
  total_corrigido

Usa LEFT JOIN: retorna processos mesmo sem cálculo (total_corrigido = NULL).
```

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
