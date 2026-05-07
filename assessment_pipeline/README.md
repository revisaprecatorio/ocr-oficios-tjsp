# Assessment Pipeline — Revisa Precatório
**Criado:** 07/2026 | **Baseado em:** logs_202605010021.csv + process_tracking_202605010021.csv + análise do código

## Documentos desta pasta

| Arquivo | Conteúdo |
|---|---|
| `01_ARQUITETURA_GERAL.md` | Visão geral do sistema, componentes, repositórios e esquema das tabelas |
| `02_FLUXO_COMPLETO.md` | Passo a passo de cada fase do pipeline (captação → download → OCR → laudo → alertas) |
| `03_CENARIOS_E_TABELAS.md` | O que acontece nas tabelas em cada cenário: sucesso, PDF antigo, erros de OCR, falhas de infra |
| `04_QUERIES_MONITORAMENTO.md` | 18 queries SQL prontas para monitoramento, com explicação do que cada uma detecta |
| `05_DIAGRAMAS_MERMAID.md` | 7 diagramas Mermaid: pipeline completo, máquina de estados, cada workflow n8n, OCR interno |

## Ordem de leitura recomendada

1. `01_ARQUITETURA_GERAL.md` — entenda os componentes e tabelas
2. `02_FLUXO_COMPLETO.md` — entenda a sequência de execução
3. `03_CENARIOS_E_TABELAS.md` — entenda como cada tipo de problema se manifesta nas tabelas
4. `04_QUERIES_MONITORAMENTO.md` — use as queries para operar o sistema

## Cenários documentados

- **A** — Sucesso total (laudo completo enviado)
- **B** — PDFs antigos série "700" (laudo parcial + alerta interno)
- **C1** — CPF não encontrado no ofício
- **C2** — ANEXO II pertence a outro CPF (multi-credor)
- **C3** — Falha total de OCR (todos os PDFs falham)
- **D1** — Auth error (certificado A1 / e-SAJ)
- **D2** — Download failed (PDFs não baixados)
- **E** — Cliente sem precatórios

## Principais estados de `consultas_esaj.current_state`

```
IDLE → AWAITING_EMAIL → AWAITING_CODE → AWAITING_CONFIRMATION → AWAITING_PAYMENT
    ├── PAYMENT_APPROVED → PROCESSING →
    │       ├── FINAL_REPORT_SENT    (laudo completo)
    │       ├── PARTIAL_REPORT_SENT  (laudo parcial)
    │       ├── PIPELINE_ERROR       (OCR/cálculo falharam)
    │       ├── AUTH_ERROR           (certificado/login e-SAJ)
    │       ├── DOWNLOAD_FAILED      (PDFs não baixados)
    │       ├── NO_VALID_PROCESS     (sem precatórios)
    │       └── MANUAL_PROCESS → ALERTA_MANUAL_SENT
    └── PAYMENT_REJECTED

Nota: REPORT_SENT é transitório (orchestrator → Laudo workflow substitui)
```
