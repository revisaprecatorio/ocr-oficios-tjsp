# Arquitetura Geral — Revisa Precatório

**Data:** 20/09/2026 | **Versão:** 2.0 — revisado contra produção viva (n8n API + PostgreSQL + GitHub API)

---

## 1. Visão Geral

O pipeline da Revisa transforma uma solicitação de cliente (WhatsApp) em um laudo de análise de precatório. Componentes em sequência:

```
[Cliente WhatsApp]
       │
       ▼
[n8n: Chatbot Revisa]  ──► consultas_esaj (AWAITING_*)
       │
       ▼ (pagamento aprovado via Mercado Pago Unified)
[consultas_esaj: PAYMENT_APPROVED]
       │
       ▼ (runtime/executar.bat — agendado na VPS Windows)
[core/orchestrator_subprocess.py]   (FOR UPDATE SKIP LOCKED, 1 job/ciclo)
       ├── core/crawler_full.py     (Selenium → e-SAJ → PDFs)
       ├── pipeline_completo.sh     (OCR → Ingestão → Cálculo → Etapa 9b)
       │     ├── processar_pipeline.py   (detectors + LLM híbrido)
       │     ├── ingest_all_jsons.py     (PostgreSQL upsert)
       │     └── calc-precatorio-tjsp/main.py (cálculo + webhook_n8n.py)
       └── estado terminal: REPORT_SENT / *_ERROR / NO_VALID_PROCESS
```

---

## 2. Componentes e Repositórios

| Componente | Repositório | Caminho no VPS | Função |
|---|---|---|---|
| **Chatbot + Pagamento + Laudo + Alertas** | n8n (7 workflows) | `n8n.srv987902.hstgr.cloud` | Conversa, pagamento, entrega do laudo, watchdog |
| **Crawler TJSP** | [`crawler_tjsp`](https://github.com/revisaprecatorio/crawler_tjsp) | `C:\Users\Administrator\Documents\revisa\crawler_tjsp\` | Download de PDFs do e-SAJ via Selenium + cert. A1 |
| **OCR Pipeline** | [`ocr-oficios-tjsp`](https://github.com/revisaprecatorio/ocr-oficios-tjsp) | `C:\Users\Administrator\Documents\revisa\ocr-oficios-tjsp\` | Extração de dados dos PDFs + ingestão (`pipeline_completo.sh`) |
| **Cálculo** | [`calc-precatorio-tjsp`](https://github.com/revisaprecatorio/calc-precatorio-tjsp) | `C:\Users\Administrator\Documents\revisa\calc-precatorio-tjsp\` | Atualização monetária; chama webhook via `webhook_n8n.py` |
| **Banco de Dados** | PostgreSQL | `72.60.62.124:5432 / n8n` | Estado, logs, dados extraídos, cálculos |
| **Backoffice** | [`6.UI_backoffice`](https://github.com/revisaprecatorio/6.UI_backoffice) | VPS Linux, Docker `:8502` | Streamlit de monitoramento — **⚠️ depende de `vw_backoffice_processos` (ausente)** |

### Crawler TJSP — Detalhes

Roda em **Windows Server** (requisito: certificado digital A1 via Web Signer + Chrome). Tentativa anterior em Linux foi bloqueada pelo Native Messaging Protocol.

**Estrutura real do repo (GitHub, verificado 20/09/2026):**

```
crawler_tjsp/
├── core/
│   ├── orchestrator_subprocess.py   # Worker: polling do banco, 1 job por vez
│   ├── crawler_full.py              # Motor Selenium: autentica, navega e-SAJ, baixa PDFs
│   ├── dashboard.py                 # Dashboard legado
│   ├── manage_queue.py              # Gestão da fila
│   └── *_0801_1100.py / *_deu_ruim.py / etc.   # variantes de backup (não usar)
├── runtime/
│   ├── executar.bat                 # ✅ LAUNCHER DE PRODUÇÃO
│   ├── crawler_watchdog.ps1         # Watchdog PowerShell
│   └── reset_runtime.ps1            # Reset de runtime
├── websocket_cert_server.py         # Servidor WebSocket p/ certificado (sob demanda)
├── chrome/
│   ├── cert/25424636_pf.pfx         # PFX antigo (e-SAJ ainda o referencia?)
│   └── extension/chrome_extension/  # Extensão Web Signer
├── windows-server/scripts/          # Setup, testes de auth, chrome debug, export_certificado.ps1
├── start_worker.py                  # ⚠️ Legado — procura main.py na raiz
├── worker_pm2.bat                   # ⚠️ Quebrado — aponta para main.py inexistente
├── run_dashboard.bat / run_dashboard.py
└── env/                             # venv COMMITADO no repo (usado pelo executar.bat)
```

**Fluxo do worker:**

```
runtime/executar.bat
  │  (kill switch: se existe arquivo RUNTIME_DISABLED → exit 0)
  └─► env\Scripts\python.exe core\orchestrator_subprocess.py
          │  SELECT ... WHERE current_state='PAYMENT_APPROVED' FOR UPDATE SKIP LOCKED
          │  → UPDATE current_state='PROCESSING'
          ├─► filtra processos classe "Precatório" (senão → NO_VALID_PROCESS)
          ├─► por processo: crawler_full.py --doc {num} --attach --debugger-address 127.0.0.1:9222
          │                  --abrir-autos --baixar-pdf --turbo-download
          │                  --download-dir C:\Temp\RevisaDownloads\{cpf}\temp_{num}\
          ├─► run_sh_wrapper.bat pipeline_completo.sh {cpf}
          └─► exit 0 → update_status_in_db('REPORT_SENT')  ← sobrescreve FINAL/PARTIAL
              erro   → AUTH_ERROR / DOWNLOAD_FAILED / PIPELINE_ERROR
```

**Paths no Windows Server:**
- Downloads temporários: `C:\Temp\RevisaDownloads\{cpf}\`
- Downloads arquivados: `C:\Temp\RevisaDownloads_Processados\{cpf}\{data}_{timestamp}\`
- Launcher: `crawler_tjsp\runtime\executar.bat`
- Orchestrator: `crawler_tjsp\core\orchestrator_subprocess.py`
- Crawler: `crawler_tjsp\core\crawler_full.py`
- OCR wrapper: `ocr-oficios-tjsp\run_sh_wrapper.bat` → `pipeline_completo.sh`
- Cálculo: `calc-precatorio-tjsp\main.py` (+ `webhook_n8n.py`)

### Certificado Digital (situação 20/09/2026)

| Item | Valor |
|---|---|
| Certificado **novo** (ativo no Windows Store) | `FLAVIO EDUARDO CAPPI:51764890230`, AC Certisign RFB G5, válido **25/08/2026 → 25/08/2027** |
| Export local (Mac) | `~/.certs/cert_ecpf.pfx` (senha definida na exportação — não commitar) |
| Certificado **antigo** visto pelo e-SAJ | validade 09/09/2025 → 09/09/2026; NÃO está em `Cert:\CurrentUser`/`LocalMachine`; origem provável: `chrome/cert/25424636_pf.pfx` carregado por `websocket_cert_server.py` sob demanda ou config do Web Signer |
| Pendente | Identificar onde o cert antigo é carregado + remover `C:\temp\cert_ecpf.pfx` da VPS |

---

## 3. Tabelas do Banco de Dados — SCHEMA REAL (extraído 20/09/2026)

### `consultas_esaj` — Estado do Job (30 colunas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | bigint PK | ID da consulta |
| `whatsapp_from` | varchar | Telefone WhatsApp (chave de sessão do chatbot) |
| `whatsapp_phone_number` | varchar | Telefone (mesmo valor; usado pelo Laudo/alertas) |
| `cpf` | varchar | CPF do cliente (`'00000000000'` = registro temporário de sessão) |
| `nome_requerente` | varchar | Nome extraído do e-SAJ |
| `timestamp_consulta` | timestamptz | Momento da consulta e-SAJ |
| `processos` | jsonb | `{"lista": [{"numero","data","classe"...}]}` |
| `total_processos` | int | Quantidade de processos encontrados |
| `resposta_formatada` | text | Resposta formatada da consulta |
| `created_at` / `updated_at` | timestamptz | Criação/atualização do registro |
| `status` | boolean | `true` = processamento concluído (setado em TODO update do orchestrator) |
| `email` | varchar | E-mail verificado do cliente |
| `awaiting_code` | boolean | Flag auxiliar do fluxo de código |
| `current_state` | varchar | Estado atual (máquina de estados — ver README/03) |
| `state_updated_at` | timestamp | Última mudança de estado (base dos timeouts e watchdogs) |
| `verification_code` | varchar | Código de verificação de e-mail (6 dígitos) |
| `code_generated_at` | timestamp | Geração do código (expira 15 min) |
| `mp_preference_id` | varchar | Preferência Mercado Pago |
| `mp_payment_id` | varchar | ID do pagamento MP (`'BATCH_*'` quando inserido via batch) |
| `mp_payment_status` | varchar | `approved`/`rejected`/`pending` |
| `mp_payment_amount` | numeric | Valor (R$ 1,00) |
| `mp_external_reference` | varchar | `{whatsapp_from}_{timestamp}` |
| `payment_link` | text | Link de checkout |
| `payment_created_at` / `payment_confirmed_at` | timestamp | Ciclo do pagamento |
| `retries` / `last_retry_at` | int / timestamp | Controle de retentativa |
| `processing_started_at` / `processing_finished_at` | timestamp | Janela de execução do worker |
| `last_error_message` | text | Último erro registrado |

**Constraint:** `ON CONFLICT (whatsapp_from, cpf)` — usada pelo Chatbot (`Update State`) e pelo batch (`Upsert Consulta`).

### `process_tracking` — Eventos Estruturados (13 colunas)

> ⚠️ **Correção vs. doc antiga:** as colunas reais são `timestamp_evento`, `detalhes` (jsonb) e `concluido` — **não existem** `created_at`, `sucesso` nem `metadata`. Queries antigas que usam esses nomes estão quebradas.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | bigint PK | |
| `consulta_id` | bigint | FK lógica → `consultas_esaj.id` |
| `cpf` | varchar | |
| `whatsapp_phone_number` | varchar | |
| `etapa` | varchar | `CONSULTA`, `PAYMENT`, `OCR`, `ENVIO_LAUDO`, `LAUDO_PARCIAL` |
| `evento` | varchar | Evento específico (ver 03) |
| `retries` | int | |
| `concluido` | boolean | Evento concluído com sucesso |
| `erro` | boolean | Houve erro |
| `mensagem_erro` | text | Detalhe do erro |
| `detalhes` | jsonb | Contexto (node, workflow, qtd_processos, email_destino...) |
| `timestamp_evento` | timestamptz | Momento do evento |
| `timestamp_conclusao` | timestamptz | Conclusão (quando aplicável) |

### `logs` — Log Textual (5 colunas)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | int PK | |
| `cpf` | char | CPF ou tag (`'BATCH'`) |
| `timestamp` | timestamp | Momento |
| `descricao` | text | Mensagem |
| `processo` | varchar | Origem: `crawler`, `OCR`, `PIPELINE`, `n8n`, `calculo` |

### `esaj_detalhe_processos` — Dados OCR (66 colunas)

Schema físico real tem **66 colunas** — inclui as ~35 documentadas do V3.0 **mais** colunas legadas que nunca foram removidas fisicamente (`advogado_nome`, `custas`, `contrib_previdenciaria_*`, `processo_execucao`, `processo_conhecimento`, `dados_bancarios_advogado`, etc.) **mais** campos novos de diagnóstico:

**Campos novos pós-V3.0 presentes no banco:**
- `process_diagnostico`, `process_calculo` (flags/texto de etapa)
- `data_saldo_final`, `origem_saldo_final`, `origem_data_saldo_final`
- `valor_original_anexo_ii`, `valor_pago_prioridade`, `saldo_final_apos_pagamento`
- `origem_valor_original_anexo_ii`, `origem_valor_pago_prioridade`, `origem_saldo_final_apos_pagamento`

**Campos-chave para monitoramento:** `rejeitado`, `motivo_rejeicao`, `anomalia`, `descricao_anomalia`, `numero_ordem`, `idoso`, `doenca_grave`, `pcd`, `preferencial`, `habilitacao_herdeiros`, `obito`, `data_obito`, `cpf_sucessor`.

**Unique:** `(cpf, numero_processo_cnj)` — upsert.

### `esaj_calc_precatorio_resumo` — Resultado do Cálculo (47 colunas)

Além de `cpf`, `numero_processo_cnj`, `total_corrigido`, `criado_em`, contém a **trilha completa do cálculo**:

- **Fatores:** `fator_ipcae_antes`, `fator_ipcae_pos`, `fator_ipcae_graca`, `fator_ipcae_juros`, `fator_juros_2aa_simples`, `fator_juros_simples_pos`, `fator_ipcae_antes_ec113`, `fator_selic_ec113`, `fator_ec136`, `fator_total_correcao`
- **Meses:** `meses_antes`, `meses_pos`, `meses_graca`, `meses_juros`, `meses_para_2aa`, `meses_ec113`, `meses_ec136`
- **Valores intermediários:** `principal_original`, `principal_apos_antes`, `principal_apos_graca`, `principal_pos_ipca`, `principal_pos_juros`, `principal_final_ipca_2aa`, `principal_final`, `juros_mora_anteriores_base`, `juros_mora_apos_antes`, `juros_mora_apos_graca`, `juros_mora_final_corrigido`, `juros_ec136`
- **Metadados do cálculo:** `regime_calculo`, `regime_calculo_resumo`, `ente_devedor`, `natureza_credito`, `fonte_principal`, `fonte_data_original`, `fonte_graca`, `fonte_competencia_inicio`, `competencia_inicio_calculo`, `competencia_fim_calculo`, `numero_ordem`, `ano_ordem`, `inicio_graca`, `fim_graca`

> A presença de registro aqui é o que o Laudo workflow usa para marcar um processo como `'Processado'`. Processos com `rejeitado=true` também contam como processados (recebem laudo com motivo da rejeição).

### Views existentes

**`vw_precatorios_full`** — JOIN de `esaj_detalhe_processos` + `esaj_calc_precatorio_resumo`; usada pelo Laudo workflow e pela query de completude (marca `anomalia=true` como `'Não Processado'` → força laudo parcial).

**`view_processados`** — CPF/e-mail × processos esperados (`consultas_esaj.processos->'lista'`) com `status_calculo` = Processado/Não Processado conforme existência em `esaj_calc_precatorio_resumo`.

**`vw_backoffice_processos`** — JOIN `consultas_esaj` + `esaj_detalhe_processos` + `esaj_calc_precatorio_resumo` com `valorizacao_percentual` calculado (`(total_corrigido/valor_total_requisitado−1)×100`). Consumida pelo `6.UI_backoffice`. **Recriada em 20/09/2026** — havia sido perdida no wipe operacional; definição completa em `07_FERRAMENTAS_AUXILIARES.md`.

---

## 4. Infraestrutura de Execução (Windows Server)

```
Agendador (Task Scheduler/PM2)
    └─► runtime\executar.bat
          ├─ se existir RUNTIME_DISABLED → sai (kill switch)
          └─ env\Scripts\python.exe core\orchestrator_subprocess.py
                  └─► core\crawler_full.py  (Selenium → Chrome debug :9222 → e-SAJ)
```

> `worker_pm2.bat` (raiz) aponta para `main.py` inexistente; `start_worker.py` procura na raiz. O caminho de produção confirmado é `runtime\executar.bat` → `core\orchestrator_subprocess.py`.

## 5. Scripts Windows — Mapeamento

| Repositório | Arquivo | Estado | Observação |
|---|---|---|---|
| `crawler_tjsp` | `runtime/executar.bat` | ✅ **Produção** | Kill switch `RUNTIME_DISABLED`; roda `core/orchestrator_subprocess.py` |
| `crawler_tjsp` | `runtime/crawler_watchdog.ps1` | ✅ Ativo | Watchdog PowerShell do crawler |
| `crawler_tjsp` | `runtime/reset_runtime.ps1` | ✅ Auxiliar | Reset do ambiente |
| `crawler_tjsp` | `run_dashboard.bat` | Funcional | Streamlit legado (`dashboard.py`, porta 8501) |
| `crawler_tjsp` | `worker_pm2.bat` | ⚠️ Quebrado | Aponta para `main.py` inexistente |
| `crawler_tjsp` | `start_worker.py` | ⚠️ Desatualizado | Procura `main.py`/orchestrator na raiz |
| `crawler_tjsp` | `websocket_cert_server.py` | Sob demanda | Carrega `.pfx` via args (path+senha) — candidato à origem do cert antigo |
| `crawler_tjsp` | `windows-server/scripts/start_chrome_debug*.bat/.ps1` | Auxiliares | Chrome debugger porta 9222 |
| `crawler_tjsp` | `windows-server/scripts/export_certificado.ps1` | Auxiliar | Backup de certificado do Store |
| `psc_calc_tjsp` | `executar.bat` etc. | ❌ Legado | Versão anterior; não usar |
