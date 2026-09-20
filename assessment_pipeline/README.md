# Revisa Precatório — Documentação da Plataforma

**Pasta:** `assessment_pipeline/` | **Revisado:** 20/09/2026 contra produção viva (n8n API + PostgreSQL + GitHub)

> **Origem desta revisão:** todos os workflows foram re-baixados do n8n vivo (`n8n_workflows_live/`), o schema foi extraído diretamente do PostgreSQL e os repositórios foram confirmados via API do GitHub. Divergências da revisão anterior (ago/2026) foram corrigidas — ver "Mudanças relevantes" no final.

---

## O que é a Revisa Precatório

A **Revisa Precatório** é um serviço B2C que permite a qualquer cidadão descobrir se possui precatórios pendentes no TJSP, o valor atualizado desses créditos e orientações para levantamento. O cliente interage exclusivamente via **WhatsApp** e recebe por e-mail um **laudo de análise** com todos os dados dos seus precatórios.

**Produto:** Análise automatizada de precatórios do TJSP
**Canal de entrada:** WhatsApp (via Meta API + n8n)
**Entrega:** E-mail com laudo HTML personalizado (completo ou parcial)
**Pagamento:** Mercado Pago (checkout preferences, R$ 1,00 no cadastro atual)

---

## Arquitetura da Plataforma

O sistema é composto por **repositórios GitHub (`revisaprecatorio`)** e **7 workflows n8n ativos**, orquestrados por um worker Python rodando em Windows Server:

```
[Cliente WhatsApp]
        │
        ▼
[n8n: Chatbot Revisa]          ← captura CPF, consulta e-SAJ, verifica e-mail, gera pagamento
        │ PAYMENT_APPROVED
        ▼
[Windows Server VPS]
  ├── runtime/executar.bat          ← launcher (kill switch RUNTIME_DISABLED)
  ├── core/orchestrator_subprocess.py  ← polling do banco, 1 job por vez (SKIP LOCKED)
  ├── core/crawler_full.py          ← Selenium → e-SAJ (cert. A1 via Web Signer) → PDFs
  ├── pipeline_completo.sh          ← OCR + ingestão + cálculo (Etapas 1-9 + 9b)
  │     ├── processar_pipeline.py   ← extração estruturada (Gemini + GPT-4o-mini)
  │     ├── ingest_all_jsons.py     ← PostgreSQL (upsert)
  │     ├── calc-precatorio-tjsp/main.py  ← atualização monetária → webhook laudo
  │     └── Etapa 9b                ← webhook direto quando 100% rejeitado (Cenário F)
  └── Webhook → n8n: Laudo envio email+cpf  ← envia laudo ao cliente
        │
[n8n: Alertas] (3 workflows, polling a cada 10 min)
  ├── Alerta_ERROS_GRAVES      ← watchdog: erros + jobs travados → WhatsApp cliente + e-mail equipe
  ├── Alerta_Laudo_Parcial     ← laudos parciais → alerta interno
  └── Alerta_Reporte_Manual    ← MANUAL_PROCESS → notificação para equipe
```

---

## Repositórios do Sistema (GitHub: `github.com/revisaprecatorio`)

| Repositório | Último push | Onde roda | Função |
|---|---|---|---|
| [`crawler_tjsp`](https://github.com/revisaprecatorio/crawler_tjsp) | 2026-03-31 | Windows Server VPS | Autenticação e-SAJ via certificado A1 + Web Signer, busca por CPF, download de PDFs da Pasta Digital. Worker em `core/`, launcher em `runtime/executar.bat` |
| [`ocr-oficios-tjsp`](https://github.com/revisaprecatorio/ocr-oficios-tjsp) | 2026-06-17 | Windows Server VPS | OCR dos PDFs (extração de campos), ingestão no PostgreSQL, `pipeline_completo.sh` (inclui **Etapa 9b**) |
| [`calc-precatorio-tjsp`](https://github.com/revisaprecatorio/calc-precatorio-tjsp) | 2026-05-07 | Windows Server VPS | Atualização monetária (IPCA-E, juros, EC113/EC136); insere em `esaj_calc_precatorio_resumo` e chama webhook via `webhook_n8n.py` |
| [`6.UI_backoffice`](https://github.com/revisaprecatorio/6.UI_backoffice) | 2025-12-15 | VPS Linux (Docker :8502) | Streamlit backoffice — **ver pendência: view `vw_backoffice_processos` ausente** |
| [`n8n-source-code-docs`](https://github.com/revisaprecatorio/n8n-source-code-docs) | 2026-06-11 | — | Backup histórico dos workflows (desatualizado; snapshots atuais em `n8n_workflows_live/`) |
| `psc_calc_tjsp` | 2025-12-22 | — | ❌ Legado — versão anterior do crawler/orquestrador |
| `streamlit_consulta_esaj` | 2025-09-22 | — | ❌ Legado — primeira versão do backoffice |

---

## Fluxo End-to-End Resumido

```
1. Cliente envia CPF via WhatsApp
2. Chatbot Revisa consulta o e-SAJ, obtém lista de processos, pede e-mail
3. Envia código de verificação por e-mail (com aviso LGPD; expira em 15 min)
4. Cliente confirma dados → Chatbot gera link Mercado Pago
5. Cliente paga → webhook MP → PAYMENT_APPROVED no banco + limpeza de dados antigos do CPF
6. orchestrator_subprocess.py detecta job → seta PROCESSING (FOR UPDATE SKIP LOCKED)
7. crawler_full.py: autentica no e-SAJ via cert. A1, baixa PDFs para C:\Temp\RevisaDownloads\{cpf}\
8. pipeline_completo.sh:
   a. processar_pipeline.py extrai dados dos PDFs (Gemini → GPT-4o-mini fallback)
   b. ingest_all_jsons.py salva em esaj_detalhe_processos (upsert cpf+processo)
   c. calc-precatorio-tjsp/main.py calcula valores → esaj_calc_precatorio_resumo
      e chama POST /webhook/reporte-email-cpf (webhook_n8n.py)
   d. Etapa 9b: se NENHUM cálculo gerado (100% rejeitado) → chama o webhook direto
9. Laudo envio email+cpf: verifica completude, monta HTML, envia e-mail
   → seta FINAL_REPORT_SENT ou PARTIAL_REPORT_SENT
10. Orchestrator encerra o job → seta REPORT_SENT (estado terminal de-facto)
11. Alertas (10 min): cobrem erros, jobs travados, laudos parciais e intervenção manual
```

> ⚠️ **`REPORT_SENT` é o estado terminal real.** O Laudo workflow seta `FINAL_REPORT_SENT`/`PARTIAL_REPORT_SENT` durante a Etapa 9, mas o orchestrator sobrescreve com `REPORT_SENT` ao concluir o job. Para saber se o laudo foi completo ou parcial, consulte `process_tracking` (`LAUDO_ENVIADO` vs `LAUDO_PARCIAL`), não o `current_state`.

---

## Workflows n8n (7 ativos — instância `n8n.srv987902.hstgr.cloud`, 50 no total)

| Workflow | ID | Trigger | Função |
|---|---|---|---|
| **Chatbot Revisa** | `73xnqygBK9tk6aDK` | Webhook WhatsApp `whatsapp-beta-agent` | Máquina de estados conversacional: CPF → e-SAJ → e-mail/código → confirmação → pagamento |
| **Mercado Pago Unified** | `6COT3ubybyI8QhYT` | Webhooks `/generate-payment-link` + `/mercadopago-notification` | Gera link MP (R$ 1,00); processa notificações approved/rejected/pending |
| **Laudo envio email+cpf** | `UrxjrcPE2C7WTLa0` | Webhook `POST /reporte-email-cpf` | Verifica completude → laudo completo ao cliente ou parcial à equipe + WhatsApp |
| **Alerta_ERROS_GRAVES** | `GnL3nOy64DmpjHTD` | Schedule 10 min | **Watchdog**: `PIPELINE_ERROR`, `AUTH_ERROR`, `DOWNLOAD_FAILED`, `CALC_ERROR`, `PAYMENT_APPROVED`>2h, `REPORT_SENT`/`FINAL_REPORT_SENT`>30min sem cálculo → alerta cliente+equipe |
| **Alerta_Laudo_Parcial** | `nWttny9O5BjKabz2` | Schedule 10 min | `LAUDO_PARCIAL` sem `PARCIAL_INFORMADO` → e-mail interno |
| **Alerta_Reporte_Manual** | `XIx9gn1ifI7jsyoP` | Schedule 10 min | `MANUAL_PROCESS` → WhatsApp cliente + e-mail equipe → `ALERTA_MANUAL_SENT` |
| **CPF_batch_processing** | `jMzstMZfztUMz7O6` | Webhook `POST /cpf-batch-processing` | Insere CPF direto como `PAYMENT_APPROVED` (sem WhatsApp/pagamento) — ferramenta interna |

Snapshots JSON atualizados em `n8n_workflows_live/`. Documentação detalhada em `06_WORKFLOWS_N8N.md`.

**Destinatários de alerta:** todos os e-mails internos vão para **`revisa.manual@gmail.com`** (não contato@/persival/rodrigo como em versões antigas).

---

## Banco de Dados (PostgreSQL — `72.60.62.124:5432/n8n`, schema `public`)

| Tabela/View | Colunas | Alimentada por | Função |
|---|---|---|---|
| `consultas_esaj` | 30 | Chatbot, MP Unified, batch, orchestrator | Ciclo de vida completo: estado, pagamento, retries, timestamps de processamento |
| `process_tracking` | 13 | Chatbot, MP, OCR, Laudo, Alertas | Eventos estruturados por consulta (auditoria) |
| `logs` | 5 | orchestrator, crawler, pipeline, n8n | Log textual cronológico |
| `esaj_detalhe_processos` | 66 | ingest_all_jsons.py | Dados extraídos dos PDFs (OCR) + flags rejeição/anomalia |
| `esaj_calc_precatorio_resumo` | 47 | calc-precatorio-tjsp | Valores atualizados com fatores IPCA-E/juros detalhados |
| `vw_precatorios_full` | view | — | JOIN OCR + cálculo; consultada pelo Laudo workflow |
| `view_processados` | view | — | Processos esperados (`consultas_esaj.processos`) vs. calculados |
| `vw_backoffice_processos` | view | — | Consolidação para o backoffice Streamlit (recriada 20/09/2026) |

---

## Máquina de Estados (`consultas_esaj.current_state`)

```
IDLE
  └─► AWAITING_EMAIL         (chatbot pediu e-mail)
        └─► AWAITING_CODE    (código enviado — expira 15 min)
              └─► AWAITING_CONFIRMATION  (aguarda confirmação de dados)
                    └─► AWAITING_PAYMENT  (link MP gerado — expira 60 min)
                          ├─► PAYMENT_APPROVED
                          │       └─► PROCESSING  (orchestrator, SKIP LOCKED)
                          │               ├─► FINAL_REPORT_SENT   ← transitório (Laudo, Etapa 9)
                          │               ├─► PARTIAL_REPORT_SENT ← transitório (Laudo, Etapa 9)
                          │               ├─► REPORT_SENT         ← TERMINAL DE-FACTO (orchestrator)
                          │               ├─► PIPELINE_ERROR      ❌
                          │               ├─► CALC_ERROR          ❌
                          │               ├─► AUTH_ERROR          ❌
                          │               ├─► DOWNLOAD_FAILED     ❌
                          │               ├─► NO_VALID_PROCESS    ℹ️ terminal
                          │               └─► MANUAL_PROCESS      ⚠️
                          │                       └─► ALERTA_MANUAL_SENT  (terminal pós-alerta)
                          └─► PAYMENT_REJECTED  (terminal; "sim" gera novo link)
```

> Estados cobertos pelo watchdog `Alerta_ERROS_GRAVES`: `PIPELINE_ERROR`, `AUTH_ERROR`, `DOWNLOAD_FAILED`, `CALC_ERROR`, `PAYMENT_APPROVED` (>2h = worker caído), `REPORT_SENT`/`FINAL_REPORT_SENT` (>30min sem registro de cálculo = laudo fantasma).

---

## Cenários Documentados

| Cenário | Descrição | Estado final real |
|---|---|---|
| **A** | Sucesso total — todos os processos calculados, laudo completo ao cliente | `REPORT_SENT` (+ `LAUDO_ENVIADO` no tracking) |
| **B** | Parte dos processos sem detalhe/antigos — laudo parcial à equipe + WhatsApp ao cliente | `REPORT_SENT` (+ `LAUDO_PARCIAL` + `PARCIAL_INFORMADO`) |
| **C1/C2** | CPF não encontrado no ofício / ANEXO II de outro credor | `REPORT_SENT` (parcial) ou `MANUAL_PROCESS` → `ALERTA_MANUAL_SENT` |
| **C3** | Falha total de OCR — todos os PDFs falham | `PIPELINE_ERROR` → `ALERTA_MANUAL_SENT` |
| **D1** | Auth error — certificado A1 / login e-SAJ | `AUTH_ERROR` → `ALERTA_MANUAL_SENT` |
| **D2** | Download failed — PDFs não baixados | `DOWNLOAD_FAILED` → `ALERTA_MANUAL_SENT` |
| **E** | Cliente sem precatórios no TJSP | `NO_VALID_PROCESS` |
| **F** ✅ | 100% processos rejeitados DEPRE — **resolvido**: Etapa 9b chama webhook direto | `REPORT_SENT` (+ laudo de rejeição ao cliente) |

Ver detalhes em `03_CENARIOS_E_TABELAS.md`.

---

## Comunicação LGPD (adicionado set/2026)

| Ponto de contato | Onde | Conteúdo |
|---|---|---|
| Laudo completo | `Laudo envio email+cpf` → `Build HTML Content` | Aviso LGPD ao final do DISCLAIMER + link Política de Privacidade |
| Laudo parcial | `Laudo envio email+cpf` → `Build HTML Parcial` | Mesmo aviso |
| E-mail de verificação | `Chatbot Revisa` → `Send Verification Email` | Seção "Privacidade e proteção de dados" + link política + contato@ |
| WhatsApp pós-pagamento | `Mercado Pago Unified` → `Process Payment Status` | Prazo 24h + exceção até 7 dias úteis (2 typos pendentes: `e mail`, `scaneados`) |

Política publicada: `https://www.revisaprecatorio.com.br/politica-de-privacidade/`

---

## Documentos desta Pasta

| Arquivo | Conteúdo |
|---|---|
| `01_ARQUITETURA_GERAL.md` | Componentes, repositórios, schema real completo das tabelas |
| `02_FLUXO_COMPLETO.md` | Passo a passo detalhado de cada fase |
| `03_CENARIOS_E_TABELAS.md` | O que acontece nas tabelas em cada cenário (A–F) |
| `04_QUERIES_MONITORAMENTO.md` | Queries SQL corrigidas para o schema real (timestamp_evento, detalhes, concluido) |
| `05_DIAGRAMAS_MERMAID.md` | Diagramas Mermaid atualizados |
| `06_WORKFLOWS_N8N.md` | Documentação dos 7 workflows ativos (contra JSONs vivos) |
| `07_FERRAMENTAS_AUXILIARES.md` | Streamlit backoffice + CPF_batch_processing |
| `08_RUNBOOK_MONITORAMENTO.md` | Runbook do agente de monitoramento agendado (Hermes) — checks, severidades, dedup, formato de alerta |
| `n8n_workflows_live/*.json` | Snapshots dos 7 workflows ativos (baixados 20/09/2026) |
| `scripts/` | PowerShell de diagnóstico da VPS |

---

## Pendências Conhecidas

| Item | Descrição | Status |
|---|---|---|
| ~~`vw_backoffice_processos` ausente~~ | View recriada 20/09/2026 (com `valorizacao_percentual` calculado) — backoffice funcional novamente | ✅ Resolvido |
| **Typos mensagem MP aprovada** | `e mail` → `e-mail`, `scaneados` → `escaneados` no `Process Payment Status` | 🔴 Aberto (cosmético) |
| **Certificado e-SAJ antigo** | e-SAJ mostra cert. com validade até 09/09/2026; novo cert (até 08/2027) já está no Store e exportado em `~/.certs/cert_ecpf.pfx`. Origem do cert antigo não localizada (Web Signer/on-demand). Investigação pausada a pedido | ⏸️ Pausado |
| **Aviso LGPD antes do CPF** | Melhoria de transparência (art. 9º) — aguardando decisão do Flávio (receio de conversão) | ⏸️ Decisão de produto |
| **Dados sensíveis (art. 11)** | Política não explicita tratamento de saúde/PCD/óbito/sucessores — pergunta pendente para Flávio | ⏸️ Decisão jurídica |
| **Controles internos LGPD** | Procedimentos para contato@ (localizar/corrigir/excluir por CPF), retenção, acesso à caixa revisa.manual@, incidentes | ⏸️ Governança |
| **`worker_pm2.bat`/`start_worker.py`** | Apontam para `main.py` inexistente — produção usa `runtime/executar.bat`; remover/migrar referências antigas | 🟡 Cosmético |
| **Limpeza VPS** | `C:\temp\cert_ecpf.pfx` (cópia da chave privada) — remover se ainda presente | 🟡 Higiene |

---

## Mudanças relevantes desta revisão (20/09/2026 vs. ago/2026)

1. **`REPORT_SENT` documentado como estado terminal real** — antes era "transitório"
2. **Cenário F resolvido** — Etapa 9b do `pipeline_completo.sh` chama o webhook quando 100% rejeitado
3. **`Alerta_ERROS_GRAVES` virou watchdog completo** — cobre `CALC_ERROR`, `PAYMENT_APPROVED`>2h, `REPORT_SENT` fantasma
4. **Schema real corrigido** — `process_tracking` usa `timestamp_evento`/`detalhes`/`concluido` (não `created_at`/`metadata`/`sucesso`); tabelas com 30/66/47 colunas documentadas
5. **Destinatários de alerta corrigidos** — `revisa.manual@gmail.com` em todos
6. **LGPD adicionado** — laudos + e-mail de verificação
7. **`CPF_batch_processing` documentado corretamente** — insere `PAYMENT_APPROVED` direto com `BATCH_*`
8. **Repos confirmados** — `calc-precatorio-tjsp` existe; 7 repos no total
9. **`vw_backoffice_processos` recriada** — estava ausente (perdida no wipe); recriada com `valorizacao_percentual` calculado conforme uso do `6.UI_backoffice`
