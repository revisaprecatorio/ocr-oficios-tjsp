# Fluxo Completo do Pipeline — Passo a Passo

---

## Fase 1 — Captação (n8n: Chatbot Revisa)

**Trigger:** Mensagem WhatsApp recebida no webhook `whatsapp-beta-agent`.

O chatbot é uma **máquina de estados** que lê `consultas_esaj.current_state` por `whatsapp_from` a cada mensagem.

### Etapas conversacionais

| Estado em `consultas_esaj` | O que o bot faz |
|---|---|
| `IDLE` (sem registro) | Apresenta menu, pede CPF |
| `AWAITING_EMAIL` | Recebeu CPF → grava registro → pede email |
| `AWAITING_CODE` | Enviou código de verificação por email (expira em 15 min) |
| `AWAITING_CONFIRMATION` | Aguarda cliente confirmar nome e processos encontrados |
| `AWAITING_PAYMENT` | Link do Mercado Pago enviado (expira em 60 min) |

**Timeouts automáticos:**
- `AWAITING_CODE` → expira em 15 min
- `AWAITING_CONFIRMATION` / `AWAITING_EMAIL` → expira em 30 min
- `AWAITING_PAYMENT` → expira em 60 min

**Consulta ao e-SAJ:** acontece na etapa `AWAITING_EMAIL` → `AWAITING_CONFIRMATION`. O chatbot consulta o e-SAJ pelo CPF e grava os processos encontrados.

**Registros gerados em `process_tracking`:**
- `CONSULTA / CONSULTA_SOLICITADA` → `{"workflow": "Chatbot Revisa", "cpf_informado": "..."}`
- `CONSULTA / CONSULTA_REALIZADA` → `{"nome_extraido": "...", "total_processos": N}`

> Se `total_processos = 0`: cliente não tem precatórios. Fluxo encerra com mensagem de retorno.

---

## Fase 2 — Pagamento (n8n: Mercado Pago Unified)

Este workflow tem **dois pontos de entrada** independentes:

### 2a — Geração do Link (`POST /generate-payment-link`)
Chamado pelo Chatbot quando cliente está em `AWAITING_PAYMENT`.

1. Valida `trigger_payment=true` e `email` presentes
2. Cria preferência em `POST https://api.mercadopago.com/checkout/preferences`
3. Salva em `consultas_esaj`: `mp_preference_id`, `mp_external_reference`, `payment_link`
4. Seta `current_state = 'AWAITING_PAYMENT'`
5. Limpa registro temporário de sessão (`cpf = '00000000000'`)
6. Envia link por WhatsApp ao cliente

**Registros gerados em `process_tracking`:**
- `PAYMENT / LINK_GERADO` → `{"mp_preference_id": "...", "payment_link": "..."}`

### 2b — Notificação de Pagamento (`POST /mercadopago-notification`)
Chamado pelo webhook da Mercado Pago após status de pagamento.

1. Responde `{status: ok}` imediatamente ao MP (anti-timeout)
2. Filtra apenas eventos `type = 'payment'`
3. Consulta `GET /v1/payments/{id}` para obter detalhes completos
4. Interpreta status: `approved` → `PAYMENT_APPROVED` | `rejected` → `PAYMENT_REJECTED` | `pending` → `PAYMENT_PENDING`
5. Atualiza `consultas_esaj` com `mp_payment_id`, `mp_payment_status`, `current_state`, `payment_confirmed_at`
6. **Se `approved`:** apaga dados antigos de `esaj_detalhe_processos` e `esaj_calc_precatorio_resumo` para o CPF (limpeza antes de reprocessar)
7. Notifica cliente por WhatsApp com mensagem correspondente ao status

**Registros gerados em `process_tracking`:**
- `PAYMENT / PAYMENT_APPROVED` → `{"mp_payment_id": "...", "mp_status": "approved", "amount": 1}`
- `PAYMENT / PAYMENT_REJECTED` → `{"mp_status": "rejected"}` (com `erro=true`)

---

## Fase 3 — Download de PDFs (orchestrator_subprocess.py → crawler_full.py)

**Trigger:** Watchdog (PM2/Task Scheduler) dispara `start_worker.py` periodicamente.

### 3.1 — Lock do Job
```sql
UPDATE consultas_esaj
SET current_state = 'PROCESSING', state_updated_at = NOW()
WHERE id = (SELECT id FROM consultas_esaj WHERE current_state = 'PAYMENT_APPROVED'
            ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING id, cpf, processos;
```
O `FOR UPDATE SKIP LOCKED` garante que múltiplos workers não processem o mesmo job.

### 3.2 — Download por Processo
Para cada processo da lista:
1. Cria pasta temporária: `C:\Temp\RevisaDownloads\{cpf}\temp_{numero_processo}\`
2. Executa `crawler_full.py` via subprocess:
   ```
   python crawler_full.py --doc {numero_processo} --attach
       --debugger-address 127.0.0.1:9222
       --abrir-autos --baixar-pdf --turbo-download
       --download-dir C:\Temp\RevisaDownloads\{cpf}\temp_{num}\
   ```
3. **Modo TURBO:** Selenium usa JavaScript para selecionar e baixar todos os documentos da Pasta Digital em um único PDF consolidado
4. Move o PDF para `C:\Temp\RevisaDownloads\{cpf}\`

**Falhas possíveis nesta fase:**
- `AUTH_ERROR`: autenticação no e-SAJ falhou (certificado A1 / CAS)
- `DOWNLOAD_FAILED`: nenhum PDF encontrado após o loop de downloads

**Registros gerados em `logs`:**
- `"Job {id} iniciado"` | processo=`crawler`
- `"Erro: ..."` | processo=`crawler` (em caso de falha)
- `"Status final: ..."` | processo=`crawler`

---

## Fase 4 — OCR (pipeline_completo.sh)

**Trigger:** Orchestrator executa `run_sh_wrapper.bat pipeline_completo.sh {cpf}`

O script recebe o CPF e processa TODOS os PDFs em `C:\Temp\RevisaDownloads\{cpf}\`.

### Etapa 1 — Limpeza do staging
Limpa outputs anteriores para evitar contaminação de dados.

**Log:** `"Etapa 1: staging limpo"` | processo=`PIPELINE`

### Etapa 2 — Processamento dos PDFs (`processar_pipeline.py`)
Para cada PDF em `C:\Temp\RevisaDownloads\{cpf}\`:

1. **DetectorOficio:** Localiza páginas do ofício (3 critérios: keywords, CNJ pattern, estrutura)
2. **DetectorAnexoII:** Detecta páginas "ANEXO II" com validação robusta
3. **DetectorSaldoFinal V2.5.2:** Extrai saldo final após pagamento
4. **DetectorHabilitacaoHerdeiros V2.5.3:** Detecta habilitação de herdeiros (código 9270)
5. **DetectorTermosJuridicos V2.5.3:** Detecta preferencial / doença grave
6. **LLM Híbrido (Gemini + OpenAI fallback):** Extração estruturada dos 35 campos
7. Salva resultado em `1_parsing_PDF/outputs/consultas/{cpf}/` como JSON

**Em caso de falha do OCR para um PDF:**
- `processador.py._criar_resultado_erro()` registra `OCR_ERRO` em `process_tracking`
- Atualiza `consultas_esaj.current_state = 'MANUAL_PROCESS'`
- O pipeline continua (processa outros PDFs do CPF)

**Log:** `"Etapa 2: PDFs processados"` | processo=`PIPELINE`

### Etapa 3 — Centralização de JSONs
Copia JSONs gerados para `outputs/json/`.
Se nenhum JSON foi gerado → `exit 1` (pipeline abortado → `PIPELINE_ERROR`).

**Log:** `"Etapa 3: {N} JSONs preparados"` | processo=`PIPELINE`

### Etapa 4 — Ingestão no PostgreSQL (`ingest_all_jsons.py`)
Importa cada JSON para `esaj_detalhe_processos` usando upsert:
```sql
INSERT INTO esaj_detalhe_processos (...) VALUES (...)
ON CONFLICT (cpf, numero_processo_cnj) DO UPDATE SET ...
```
Filtrado pelo CPF específico para evitar sobrescrever dados de outros clientes.

**Log:** `"Etapa 4: ingestão executada"` | processo=`PIPELINE`

### Etapa 5 — Validação Forte
Verifica se pelo menos 1 registro foi gravado no banco para o CPF.
Se `COUNT = 0` → `exit 1` (pipeline abortado → `PIPELINE_ERROR`).

**Log:** `"Etapa 5: validação OK — {N} registros no banco"` | processo=`PIPELINE`

### Etapa 6 — Recálculo de Tags
Executa `recalcular_idoso.py` para atualizar a flag `idoso` baseada em `data_nascimento`.

**Log:** `"Etapa 6: tags recalculadas"` | processo=`PIPELINE`

### Etapa 7 — Backup dos JSONs
Move JSONs processados para `outputs/historico_processado/{cpf}/{timestamp}/`.

**Log:** `"Etapa 7: JSONs movidos para ..."` | processo=`PIPELINE`

### Etapa 8 — Arquivamento dos PDFs
Move PDFs de `C:\Temp\RevisaDownloads\{cpf}\` para
`C:\Temp\RevisaDownloads_Processados\{cpf}\{data}_{timestamp}\`.

**Log:** `"Etapa 8: PDFs arquivados em ..."` | processo=`PIPELINE`

### Etapa 9 — Cálculo Final (`calc-precatorio-tjsp/main.py`)
Lê dados de `esaj_detalhe_processos` para o CPF, calcula os valores atualizados e aciona webhook n8n para envio do laudo.

**Log:** `"Etapa 9: cálculo final executado"` | processo=`PIPELINE`
**Log:** `"Pipeline finalizado com sucesso"` | processo=`PIPELINE`

---

## Fase 5 — Envio do Laudo (n8n: Laudo envio email+cpf)

**Trigger:** `POST /reporte-email-cpf` chamado por `calc-precatorio-tjsp/main.py` com `{cpf, email}`.

### Verificação de completude

1. Consulta `consultas_esaj` + `esaj_calc_precatorio_resumo` para verificar se todos os processos esperados foram calculados (`todos_processados` bool)
2. **Fork:** `todos_processados = true` → caminho normal | `false` → caminho parcial

### Caminho Normal (todos_processados = true)

1. Busca dados em `vw_precatorios_full` (view que consolida OCR + cálculo)
2. Gera HTML do laudo (consolidação de dados: varas, valores, indicadores de prioridade, anomalias)
3. Envia email ao cliente (`toEmail = email`, CC `revisaprecatorio@dr.com`)
4. Responde ao webhook de sucesso
5. Atualiza `consultas_esaj.current_state = 'FINAL_REPORT_SENT'`

**Registros gerados em `process_tracking`:**
- `ENVIO_LAUDO / LAUDO_ENVIADO` → `{"email_destino": "...", "qtd_processos": N}`

**Logs:** `"📬 Relatório enviado por email"` | processo=`n8n`

### Caminho Parcial (todos_processados = false)

1. Busca dados em `vw_precatorios_full` (apenas processos disponíveis)
2. Gera HTML parcial
3. Envia laudo parcial para **Revisa** (`contato@revisaprecatorio.com.br` + CC `revisaprecatorio@dr.com`), não para o cliente
4. Envia WhatsApp ao cliente avisando prazo de 7 dias úteis (instabilidade do TJSP)
5. Atualiza `consultas_esaj.current_state = 'PARTIAL_REPORT_SENT'`

**Registros gerados em `process_tracking`:**
- `LAUDO_PARCIAL / LAUDO_PARCIAL` → `{"email_destino": "contato@revisaprecatorio.com.br", "qtd_processos": N}` (guarda com `NOT EXISTS` para não duplicar)

**Logs:** `"PARCIAL e enviado Revisa"` | processo=`n8n`

---

## Fase 6 — Alertas Pós-Pipeline (n8n: workflows agendados)

### Alerta_Laudo_Parcial (a cada 10 min)

- **Trigger:** Schedule (10 min)
- **Condição:** `process_tracking` com `evento='LAUDO_PARCIAL'` sem `PARCIAL_INFORMADO` correspondente
- **Ação:** Envia email interno para `contato@revisaprecatorio.com.br` e `persival.balleste@gmail.com` + `dr.rodrigoferrao@gmail.com`
- **Grava:** `process_tracking.LAUDO_PARCIAL / PARCIAL_INFORMADO` → evita reenvio
- **Logs:** `"📧 Alerta laudo parcial enviado"` | processo=`n8n`

### Alerta_Reporte_Manual (a cada 10 min)

- **Trigger:** Schedule (10 min)
- **Condição:** `consultas_esaj.current_state = 'MANUAL_PROCESS'`
- **Ação:** Envia WhatsApp ao cliente (prazo 7 dias) + email interno para equipe
- **Transição de estado:** `MANUAL_PROCESS` → `ALERTA_MANUAL_SENT`
- **Logs:** `"🚨 Alerta reporte manual enviado em batch"` | processo=`n8n`

### Alerta_PDF_antigo (INATIVO)

- **Status:** `active: false` — **aguarda revisão**
- Mesma lógica do `Alerta_Reporte_Manual` (query em `MANUAL_PROCESS`)
- Destinado a tratar especificamente PDFs antigos série "700"
- **Problema atual:** query idêntica ao `Alerta_Reporte_Manual`, sem distinção de causa
