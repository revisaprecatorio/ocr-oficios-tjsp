# Cenários de Execução — Comportamento das Tabelas

**Revisado:** 20/09/2026 — contra workflows vivos, código no GitHub e schema real do banco.

---

## Catálogo de Estados e Eventos

### Estados `consultas_esaj.current_state`

| Estado | Quem seta | Causa / Significado | Tipo |
|---|---|---|---|
| `IDLE` | Chatbot | Sem registro / início de conversa | Normal |
| `AWAITING_EMAIL` | Chatbot | CPF recebido, aguardando e-mail | Normal |
| `AWAITING_CODE` | Chatbot | Código de verificação enviado (15 min) | Normal |
| `AWAITING_CONFIRMATION` | Chatbot | Aguardando confirmação de dados | Normal |
| `AWAITING_PAYMENT` | Chatbot / MP Unified | Link MP gerado (60 min) | Normal |
| `PAYMENT_PENDING` | MP Unified | Pagamento em análise no MP | Transitório |
| `PAYMENT_APPROVED` | MP Unified / **CPF_batch** | Pagamento aprovado — pronto para worker. >2h = watchdog | Transitório |
| `PAYMENT_REJECTED` | MP Unified | Rejeitado/cancelado; "sim" gera novo link | Terminal |
| `NO_VALID_PROCESS` | Orchestrator | Nenhum processo classe Precatório | Terminal |
| `PROCESSING` | Orchestrator | Worker lockou o job | Transitório |
| `AUTH_ERROR` | Orchestrator | Falha autenticação e-SAJ | Erro → watchdog |
| `DOWNLOAD_FAILED` | Orchestrator | Nenhum PDF baixado | Erro → watchdog |
| `PIPELINE_ERROR` | Orchestrator | Falha OCR/cálculo (exit≠0) | Erro → watchdog |
| `CALC_ERROR` | Orchestrator | Falha específica do cálculo | Erro → watchdog |
| `MANUAL_PROCESS` | processador.py | OCR falhou em processo(s) — pode ser sobrescrito por `REPORT_SENT` se pipeline concluir | Intervenção |
| `ALERTA_MANUAL_SENT` | Alerta_ERROS_GRAVES / Alerta_Reporte_Manual | Cliente+equipe notificados; aguarda tratamento manual | **Terminal** |
| `FINAL_REPORT_SENT` | Laudo workflow | Laudo completo enviado — **transitório** (orchestrator sobrescreve) | Transitório |
| `PARTIAL_REPORT_SENT` | Laudo workflow | Laudo parcial enviado — **transitório** | Transitório |
| `REPORT_SENT` | Orchestrator | **Estado terminal de-facto** após pipeline exit 0 — engloba laudos completos E parciais | **Terminal** |
| `OCR_COMPLETE` | Manual | Reset manual para reenvio (legado) | Manual |

> **Regra de ouro:** `REPORT_SENT` sozinho não diz se o laudo foi completo ou parcial. O desfecho real está em `process_tracking`: `ENVIO_LAUDO/LAUDO_ENVIADO` = completo; `LAUDO_PARCIAL/LAUDO_PARCIAL` = parcial; ausência de ambos = ⚠️ verificar watchdog/Q19.

### Estados legados (não ativos)

`PDF_DOWNLOADED` (psc_calc_tjsp), `OCR_IN_PROGRESS`/`ERROR_OCR` (orchestrator_deu_ruim.py), `CALCULATION_IN_PROGRESS` (dashboard).

### Eventos `process_tracking` (confirmados no banco)

| etapa | evento | Quem grava | Significado |
|---|---|---|---|
| `CONSULTA` | `CONSULTA_SOLICITADA` | Chatbot | Cliente enviou CPF |
| `CONSULTA` | `CONSULTA_REALIZADA` | Chatbot | e-SAJ consultado; `detalhes.total_processos` |
| `PAYMENT` | `LINK_GERADO` | MP Unified | Link gerado |
| `PAYMENT` | `PAYMENT_APPROVED` | MP Unified | Pagamento aprovado |
| `PAYMENT` | `PAYMENT_REJECTED` | MP Unified | Pagamento rejeitado |
| `OCR` | `OCR_ERRO` | processador.py | Falha OCR de um PDF |
| `ENVIO_LAUDO` | `LAUDO_ENVIADO` | Laudo workflow | Laudo completo enviado |
| `LAUDO_PARCIAL` | `LAUDO_PARCIAL` | Laudo workflow | Laudo parcial gerado (destino: revisa.manual@) |
| `LAUDO_PARCIAL` | `PARCIAL_INFORMADO` | Alerta_Laudo_Parcial | Equipe notificada |

### `logs` — padrões de `processo`/`descricao`

| `processo` | `descricao` típica | Significado |
|---|---|---|
| `crawler` | `Job {id} iniciado` / `Status final: {estado}` | Ciclo do worker |
| `crawler` | `ERRO: Falha crítica na autenticação inicial` | `AUTH_ERROR` |
| `crawler` | `Nenhum PDF encontrado em ...` | `DOWNLOAD_FAILED` |
| `OCR` | `Iniciando OCR (modo BLOQUEANTE)` / `OCR finalizado com sucesso` / `OCR falhou (exit_code={n})` | Ciclo OCR |
| `PIPELINE` | `Etapa 1..9b ...` / `Pipeline finalizado com sucesso` | `pipeline_completo.sh` |
| `calculo` | `Nenhum processo pendente.` / `Webhook consolidado: SUCESSO|FALHA` | calc/main.py + Etapa 9b |
| `n8n` | `� Alerta erro grave enviado - ALERTA_MANUAL_SENT` | Alerta_ERROS_GRAVES |
| `n8n` | `🚨 Alerta reporte manual enviado em batch` | Alerta_Reporte_Manual |
| `n8n` | `📧 Alerta laudo parcial enviado em batch` | Alerta_Laudo_Parcial |

---

## Cenário A — Fluxo Normal (Sucesso)

**Definição:** Todos os processos têm PDFs válidos, OCR OK, cálculo gerado.

### Timeline

| # | Tabela | Evento/Coluna | Valor |
|---|---|---|---|
| 1-4 | `consultas_esaj`/`process_tracking` | AWAITING_* → `CONSULTA_SOLICITADA`/`CONSULTA_REALIZADA` | `total_processos: N` |
| 5 | `process_tracking` | `PAYMENT/LINK_GERADO` | link MP |
| 6 | `consultas_esaj` + `process_tracking` | `PAYMENT_APPROVED` | MP approved; dados antigos do CPF limpos |
| 7 | `consultas_esaj` | `PROCESSING` | lock do worker |
| 8-11 | `logs` | `Job iniciado` → `Etapa 1..9` | crawler/OCR/PIPELINE |
| 12 | `esaj_detalhe_processos` | upsert | N registros |
| 13 | `esaj_calc_precatorio_resumo` | insert | N registros |
| 14 | Laudo workflow | e-mail ao cliente + `ENVIO_LAUDO/LAUDO_ENVIADO` | `FINAL_REPORT_SENT` (transitório) |
| 15 | `consultas_esaj` | **`REPORT_SENT`** | terminal de-facto (orchestrator) |

---

## Cenário B — Laudo Parcial (processos sem detalhe/antigos "700")

**Definição:** Parte dos processos não chega a `esaj_detalhe_processos`/`esaj_calc` (PDF antigo "700..." sem ANEXO II, ANEXO II de outro CPF, anomalia, falha de download individual).

> A query `Check Processamento Completo` marca `'Não Processado'` quando o processo não tem cálculo **e** não está `rejeitado` — ou quando `anomalia=true`. `todos_processados=false` → caminho parcial.

### Timeline

| # | Tabela | Valor |
|---|---|---|
| 1-7 | (igual A) | — |
| 8 | `process_tracking` | `OCR/OCR_ERRO` `erro=true` (ex.: `"Nenhum ANEXO II detectado..."`) |
| 9 | `consultas_esaj` | `MANUAL_PROCESS` (set por processador.py — transitório) |
| 10 | `esaj_detalhe_processos`/`esaj_calc` | só processos bem-sucedidos |
| 11 | Laudo workflow | `todos_processados=false` → `Build HTML Parcial` → e-mail a **revisa.manual@gmail.com** + WhatsApp ao cliente (7 dias úteis) → `PARTIAL_REPORT_SENT` (transitório) |
| 12 | `consultas_esaj` | **`REPORT_SENT`** (orchestrator, terminal) |
| 13 | `process_tracking` | `LAUDO_PARCIAL/LAUDO_PARCIAL` → depois `PARCIAL_INFORMADO` (alerta 10 min) |

> **Identificar PDFs antigos:** `OCR_ERRO` com `mensagem_erro ILIKE '%Nenhum ANEXO II%'` e `detalhes->>'processo'` começando com `7`.

---

## Cenário C — Falha de OCR

- **C1** CPF não aparece no ofício → `OCR_ERRO`; único processo → `MANUAL_PROCESS` → `ALERTA_MANUAL_SENT` (com pipeline falho) ou `REPORT_SENT` parcial (se outros passaram).
- **C2** ANEXO II de outro CPF (multi-credor) → `OCR_ERRO` `"ANEXO II encontrado ... nenhum pertence ao CPF esperado"`; processo não ingerido → parcial ou manual.
- **C3** Todos os PDFs falham → Etapa 3 (0 JSONs) `exit 1` → `PIPELINE_ERROR` → `ALERTA_MANUAL_SENT` pelo watchdog.

---

## Cenário D — Falha de Download

- **D1 `AUTH_ERROR`:** certificado A1/Web Signer/CAS. Sem PDFs, sem OCR. → watchdog → `ALERTA_MANUAL_SENT`.
- **D2 `DOWNLOAD_FAILED`:** crawler rodou mas 0 PDFs na pasta. → watchdog → `ALERTA_MANUAL_SENT`.

---

## Cenário E — Sem Precatórios

Consulta retornou processos mas nenhum classe "Precatório" → `NO_VALID_PROCESS` (terminal). Cliente não recebe laudo — tratar comercialmente (reembolso) conforme política.

---

## Cenário F — 100% Rejeitados pelo DEPRE ✅ **RESOLVIDO**

**Antes (bug, até ago/2026):** todos `rejeitado=true` → `main.py` retornava `"Nenhum processo pendente."` sem chamar webhook → laudo nunca enviado, estado travado em `REPORT_SENT`.

**Correção em produção:** **`pipeline_completo.sh` — Etapa 9b** (linhas ~253-302 do script no GitHub): após o cálculo, se `COUNT(esaj_calc_precatorio_resumo WHERE cpf)=0`, busca o e-mail em `consultas_esaj` e chama `POST /reporte-email-cpf` diretamente. O Laudo workflow trata `rejeitado=true` como `'Processado'` e o HTML exibe o bloco de rejeição com `motivo_rejeicao` — o cliente **recebe o laudo** informando que o(s) ofício(s) foi/foram rejeitado(s).

**Proteção adicional:** `Alerta_ERROS_GRAVES` cobre `REPORT_SENT`/`FINAL_REPORT_SENT` >30min **sem registro de cálculo e com processo não-rejeitado** (laudo fantasma) e `PAYMENT_APPROVED` >2h (worker caído).

### Identificar um caso F histórico/residual

```sql
-- estado REPORT_SENT + sem calc + todos rejeitados + sem LAUDO_ENVIADO
SELECT ce.id, ce.cpf, ce.email, ce.state_updated_at
FROM consultas_esaj ce
WHERE ce.current_state = 'REPORT_SENT'
  AND NOT EXISTS (SELECT 1 FROM esaj_calc_precatorio_resumo r WHERE r.cpf = ce.cpf)
  AND NOT EXISTS (SELECT 1 FROM process_tracking pt
                  WHERE pt.consulta_id = ce.id AND pt.evento = 'LAUDO_ENVIADO')
  AND EXISTS (SELECT 1 FROM esaj_detalhe_processos d
              WHERE d.cpf = ce.cpf GROUP BY d.cpf
              HAVING BOOL_AND(COALESCE(d.rejeitado,false)));
```

Se aparecerem linhas **recentes** aqui → Etapa 9b não disparou (verificar logs `Etapa 9b` e `webhook`).

---

## Resumo Comparativo — Estado Final Real por Cenário

| Cenário | `current_state` final | `OCR_ERRO` | Tracking de laudo | `esaj_detalhe` | `esaj_calc` |
|---|---|---|---|---|---|
| **A** Sucesso | `REPORT_SENT` | ❌ | `LAUDO_ENVIADO` | Todos | ✅ |
| **B** Parcial | `REPORT_SENT` | ✅ | `LAUDO_PARCIAL` + `PARCIAL_INFORMADO` | Só processados | ✅ (dos processados) |
| **C1/C2** | `REPORT_SENT` (parcial) ou `ALERTA_MANUAL_SENT` | ✅ | Depende | Parcial | Depende |
| **C3** Falha total | `ALERTA_MANUAL_SENT` (via `PIPELINE_ERROR`) | ✅×N | ❌ | ❌ | ❌ |
| **D1** Auth | `ALERTA_MANUAL_SENT` (via `AUTH_ERROR`) | ❌ | ❌ | ❌ | ❌ |
| **D2** Download | `ALERTA_MANUAL_SENT` (via `DOWNLOAD_FAILED`) | ❌ | ❌ | ❌ | ❌ |
| **E** Sem precatórios | `NO_VALID_PROCESS` | ❌ | ❌ | ❌ | ❌ |
| **F** 100% rejeitado | `REPORT_SENT` | ❌ | `LAUDO_ENVIADO` (laudo de rejeição) | ✅ `rejeitado=true` | ❌ (esperado) |

> **Garantia "cliente pago nunca fica órfão":** todo estado de falha alimenta o watchdog → `ALERTA_MANUAL_SENT` + WhatsApp ao cliente + e-mail a `revisa.manual@gmail.com`. O único buraco remanescente conhecido: processo 100% rejeitado **onde a Etapa 9b não achou e-mail** (log `"Etapa 9b: nenhum email encontrado"`).
