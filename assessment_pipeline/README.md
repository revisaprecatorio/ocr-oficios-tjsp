# Revisa Precatório — Documentação da Plataforma

**Pasta:** `assessment_pipeline/` | **Atualizado:** 06/2026

---

## O que é a Revisa Precatório

A **Revisa Precatório** é um serviço B2C que permite a qualquer cidadão descobrir se possui precatórios pendentes no TJSP, o valor atualizado desses créditos e orientações para levantamento. O cliente interage exclusivamente via **WhatsApp** e recebe por email um **laudo de análise** com todos os dados dos seus precatórios.

**Produto:** Análise automatizada de precatórios do TJSP  
**Canal de entrada:** WhatsApp (via Meta API + n8n)  
**Entrega:** Email com laudo HTML personalizado  
**Pagamento:** Mercado Pago (checkout preferences)

---

## Arquitetura da Plataforma

O sistema é composto por **4 repositórios** e **7 workflows n8n**, orquestrados por um worker Python rodando em Windows Server:

```
[Cliente WhatsApp]
        │
        ▼
[n8n: Chatbot Revisa]          ← captura CPF, verifica email, gera pagamento
        │ PAYMENT_APPROVED
        ▼
[Windows Server VPS]
  ├── orchestrator_subprocess.py    ← polling do banco, processa 1 job por vez
  ├── crawler_full.py               ← Selenium → e-SAJ → download PDFs
  ├── pipeline_completo.sh          ← OCR + ingestão + cálculo
  │     ├── processador.py          ← extração estruturada (Gemini + GPT-4o-mini)
  │     ├── ingest_v3_0.py          ← PostgreSQL (35 colunas)
  │     └── calc-precatorio-tjsp/main.py   ← atualização monetária
  └── Webhook → n8n: Laudo envio email+cpf  ← envia laudo ao cliente
        │
[n8n: Alertas] (3 workflows, polling a cada 10 min)
  ├── Alerta_ERROS_GRAVES      ← erros críticos → email + WhatsApp
  ├── Alerta_Laudo_Parcial     ← laudos parciais → alerta interno
  └── Alerta_Reporte_Manual    ← MANUAL_PROCESS → notificação para equipe
```

---

## Repositórios do Sistema

| Repositório | Linguagem | Onde roda | Função |
|---|---|---|---|
| [`crawler_tjsp`](https://github.com/revisaprecatorio/crawler_tjsp) | Python 80%, PowerShell 16% | Windows Server VPS | Autenticação no e-SAJ via certificado A1, busca de processos por CPF, download de PDFs da Pasta Digital |
| [`ocr-oficios-tjsp`](https://github.com/revisaprecatorio/ocr-oficios-tjsp) | Python | Windows Server VPS | OCR dos PDFs (extração de 35 campos), ingestão no PostgreSQL, Streamlit backoffice |
| `calc-precatorio-tjsp` | Python | Windows Server VPS | Atualização monetária dos valores do precatório; insere resultado em `esaj_calc_precatorio_resumo` |
| n8n (workflows) | JSON / JavaScript | VPS n8n (self-hosted) | Chatbot, pagamento, entrega do laudo, alertas operacionais |

---

## Fluxo End-to-End Resumido

```
1. Cliente envia CPF via WhatsApp
2. Chatbot Revisa consulta o e-SAJ, obtém lista de processos, pede email
3. Envia código de verificação por email (expira em 15 min)
4. Cliente confirma dados → Chatbot gera link Mercado Pago
5. Cliente paga → webhook MP → PAYMENT_APPROVED no banco
6. orchestrator_subprocess.py detecta job → seta PROCESSING
7. crawler_full.py: autentica no e-SAJ via cert. A1, baixa PDFs para C:\Temp\RevisaDownloads\{cpf}\
8. pipeline_completo.sh:
   a. processador.py extrai dados dos PDFs (Gemini → GPT-4o-mini fallback)
   b. ingest_v3_0.py salva em esaj_detalhe_processos (35 colunas)
   c. calc-precatorio-tjsp/main.py calcula valores → esaj_calc_precatorio_resumo
9. Orchestrator chama POST /webhook/reporte-email-cpf
10. Laudo envio email+cpf: consulta vw_precatorios_full, monta HTML, envia email
11. Atualiza current_state → FINAL_REPORT_SENT ou PARTIAL_REPORT_SENT
```

---

## Workflows n8n

| Workflow | Trigger | Função | Faz parte do pipeline |
|---|---|---|---|
| **Chatbot Revisa** | Webhook WhatsApp | Máquina de estados conversacional; CPF → consulta e-SAJ → pagamento | ✅ Entrada do pipeline |
| **Mercado Pago Unified** | Webhook MP + Webhook interno | Gera link de pagamento; processa notificações do MP | ✅ Fase 2 |
| **Laudo envio email+cpf** | Webhook `POST /reporte-email-cpf` | Busca dados em `vw_precatorios_full`, monta laudo HTML, envia email | ✅ Fase final |
| **Alerta_ERROS_GRAVES** | Schedule (a cada 10 min) | Monitora `MANUAL_PROCESS`, `PIPELINE_ERROR`, `AUTH_ERROR`, `DOWNLOAD_FAILED`; notifica cliente + equipe | ✅ Monitoramento |
| **Alerta_Laudo_Parcial** | Schedule (a cada 10 min) | Detecta `LAUDO_PARCIAL` sem `PARCIAL_INFORMADO`; notifica equipe | ✅ Monitoramento |
| **Alerta_Reporte_Manual** | Schedule (a cada 10 min) | Detecta `MANUAL_PROCESS`; notifica equipe para reprocessamento manual | ✅ Monitoramento |
| **CPF_batch_processing** | Webhook `POST /cpf-batch-processing` | Consulta e-SAJ e insere/atualiza `consultas_esaj` em lote, sem passar pelo WhatsApp | ⬛ Ferramenta auxiliar |

Ver documentação completa em `06_WORKFLOWS_N8N.md`.

---

## Banco de Dados (PostgreSQL — `72.60.62.124:5432/n8n`)

| Tabela | Alimentada por | Função |
|---|---|---|
| `consultas_esaj` | Chatbot Revisa, Mercado Pago Unified | Estado do job: ciclo de vida completo de cada solicitação |
| `process_tracking` | Chatbot, MP, OCR, Laudo workflow | Eventos estruturados por consulta (auditoria completa) |
| `logs` | orchestrator, crawler, processador | Log textual cronológico da execução |
| `esaj_detalhe_processos` | ingest_v3_0.py | 35 colunas com dados extraídos dos PDFs (OCR) |
| `esaj_calc_precatorio_resumo` | calc-precatorio-tjsp | Valores atualizados; sua presença dispara o envio do laudo |
| `vw_precatorios_full` | — (view) | JOIN entre `esaj_detalhe_processos` e `esaj_calc_precatorio_resumo`; consultada pelo laudo |

---

## Máquina de Estados (`consultas_esaj.current_state`)

```
IDLE
  └─► AWAITING_EMAIL         (chatbot pediu email)
        └─► AWAITING_CODE    (código enviado — expira 15 min)
              └─► AWAITING_CONFIRMATION  (aguarda confirmação de dados)
                    └─► AWAITING_PAYMENT  (link MP gerado — expira 60 min)
                          ├─► PAYMENT_APPROVED
                          │       └─► PROCESSING
                          │               ├─► FINAL_REPORT_SENT    ✅ (laudo completo)
                          │               ├─► PARTIAL_REPORT_SENT  ⚠️ (laudo parcial)
                          │               ├─► PIPELINE_ERROR       ❌ (OCR/cálculo falharam)
                          │               ├─► AUTH_ERROR           ❌ (cert. A1 / login e-SAJ)
                          │               ├─► DOWNLOAD_FAILED      ❌ (PDFs não baixados)
                          │               ├─► NO_VALID_PROCESS     ℹ️ (sem precatórios)
                          │               └─► MANUAL_PROCESS       ⚠️ (OCR parcial)
                          │                       └─► ALERTA_MANUAL_SENT
                          └─► PAYMENT_REJECTED
```

> `REPORT_SENT` é transitório: o orchestrator seta, mas o workflow **Laudo envio email+cpf** o substitui por `FINAL_REPORT_SENT` ou `PARTIAL_REPORT_SENT` ao processar.

---

## Cenários Documentados

| Cenário | Descrição | Estado final |
|---|---|---|
| **A** | Sucesso total — todos os PDFs processados, laudo completo enviado | `FINAL_REPORT_SENT` |
| **B** | PDFs antigos série "700" — OCR falha em parte, laudo parcial enviado | `PARTIAL_REPORT_SENT` |
| **C1** | CPF do cliente não encontrado em nenhum ofício | `MANUAL_PROCESS` |
| **C2** | ANEXO II pertence a outro CPF (multi-credor no mesmo ofício) | `MANUAL_PROCESS` |
| **C3** | Falha total de OCR — todos os PDFs falham | `MANUAL_PROCESS` |
| **D1** | Auth error — certificado A1 expirado ou login e-SAJ falhou | `AUTH_ERROR` |
| **D2** | Download failed — PDFs não foram baixados do e-SAJ | `DOWNLOAD_FAILED` |
| **E** | Cliente sem precatórios registrados no TJSP | `NO_VALID_PROCESS` |
| **F** | 100% dos processos rejeitados pelo DEPRE — sem cálculo gerado, laudo nunca enviado | `PROCESSING` (falso) |

Ver detalhes em `03_CENARIOS_E_TABELAS.md`.

---

## Documentos desta Pasta

| Arquivo | Conteúdo |
|---|---|
| `01_ARQUITETURA_GERAL.md` | Componentes, repositórios, schema completo de todas as tabelas |
| `02_FLUXO_COMPLETO.md` | Passo a passo detalhado de cada fase (Chatbot → Crawler → OCR → Laudo → Alertas) |
| `03_CENARIOS_E_TABELAS.md` | O que acontece nas tabelas em cada cenário (A a F) |
| `04_QUERIES_MONITORAMENTO.md` | 19 queries SQL prontas para monitoramento e diagnóstico operacional |
| `05_DIAGRAMAS_MERMAID.md` | 7 diagramas Mermaid: pipeline completo, máquina de estados, workflows n8n, OCR interno |
| `06_WORKFLOWS_N8N.md` | Documentação detalhada dos 7 workflows n8n (nós, lógica, integrações) |
| `07_FERRAMENTAS_AUXILIARES.md` | Streamlit backoffice + CPF_batch_processing (ferramentas fora do pipeline principal) |

### Ordem de leitura recomendada

1. **Este arquivo** — visão geral da plataforma
2. `01_ARQUITETURA_GERAL.md` — schema de tabelas e infraestrutura
3. `02_FLUXO_COMPLETO.md` — execução passo a passo
4. `03_CENARIOS_E_TABELAS.md` — comportamento em cada tipo de falha
5. `04_QUERIES_MONITORAMENTO.md` — queries para operar o sistema
6. `06_WORKFLOWS_N8N.md` — detalhe dos workflows n8n
7. `07_FERRAMENTAS_AUXILIARES.md` — ferramentas de apoio

---

## Pendências Conhecidas

| Item | Descrição | Status |
|---|---|---|
| **Cenário F** | Implementar Etapa 9b no `pipeline_completo.sh` — laudo direto para processos 100% rejeitados | ⏳ Aguardando validação do `validacao_junho_08/diagnostico_cpf_16914336830.md` |
| **DetectorSaldoFinal V3.0.0** | Commit `e867264` local — push + git pull na VPS + restart do serviço | ⏳ Aguardando confirmação do repo usado na VPS |
| **Calc repo** | Confirmar nome e URL do repositório `calc-precatorio-tjsp` | ❓ Não confirmado |
