# Cenários de Execução — Comportamento das Tabelas

---

## Cenário A — Fluxo Normal (Sucesso Total)

**Definição:** Cliente tem processos precatórios; todos os PDFs têm ANEXO II válido; OCR bem-sucedido para todos.

**Exemplo real do log:** CPF `09978342850` (Dalmir Franco Marchon, 1 processo)

### Timeline de eventos

| Ordem | Tabela | Coluna/Evento | Valor |
|---|---|---|---|
| 1 | `consultas_esaj` | `current_state` | `PAYMENT_PENDING` |
| 2 | `process_tracking` | `CONSULTA / CONSULTA_SOLICITADA` | sucesso |
| 3 | `process_tracking` | `CONSULTA / CONSULTA_REALIZADA` | `total_processos: 1` |
| 4 | `process_tracking` | `PAYMENT / LINK_GERADO` | link do MP |
| 5 | `consultas_esaj` | `current_state` | `PAYMENT_APPROVED` |
| 6 | `process_tracking` | `PAYMENT / PAYMENT_APPROVED` | `mp_status: approved` |
| 7 | `consultas_esaj` | `current_state` | `PROCESSING` |
| 8 | `logs` | `descricao` | `"Job X iniciado"` \| processo=crawler |
| 9 | `logs` | `descricao` | `"Iniciando OCR (modo BLOQUEANTE)"` \| processo=OCR |
| 10 | `logs` | `descricao` | `"Pipeline iniciado"` \| processo=PIPELINE |
| 11 | `logs` | `descricao` | `"Etapa 1..9"` \| processo=PIPELINE |
| 12 | `logs` | `descricao` | `"OCR finalizado com sucesso"` \| processo=OCR |
| 13 | `esaj_detalhe_processos` | — | 1 registro inserido para o CPF |
| 14 | `process_tracking` | `ENVIO_LAUDO / LAUDO_ENVIADO` | `qtd_processos: 1` |
| 15 | `consultas_esaj` | `current_state` | `REPORT_SENT` *(orchestrator)* → `FINAL_REPORT_SENT` *(Laudo workflow)* |

**Estado final das tabelas:**
- `consultas_esaj.current_state = 'FINAL_REPORT_SENT'`
- `process_tracking`: sequência completa sem erros (`erro = false` em todos)
- `esaj_detalhe_processos`: todos os processos do CPF populados com 35 campos
- `logs`: nenhuma entrada com erro

---

## Cenário B — PDFs Antigos Série "700" (Laudo Parcial)

**Definição:** Cliente tem múltiplos processos. Um ou mais são do formato antigo (número CNJ iniciando com "7", ex: `7007859-54.2010.8.26.0500`). Esses PDFs não contêm ANEXO II — estrutura diferente dos PDFs modernos. Os demais processos do cliente têm PDFs válidos e são processados com sucesso.

**Exemplo real do log:** CPF `07084621890` (2 processos: 1 moderno + 1 antigo "700")
- Processo moderno: extraído com sucesso
- Processo antigo `7003479-56.2008.8.26.0500`: `"Nenhum ANEXO II detectado no PDF para qualquer CPF"`

**Exemplo real do log:** CPF `28721705534` (3 processos: 2 modernos + 1 antigo)
- `0467036-75.2025.8.26.0500`: "ANEXO II encontrado no PDF, mas nenhum pertence ao CPF esperado"

### Timeline de eventos

| Ordem | Tabela | Coluna/Evento | Valor |
|---|---|---|---|
| 1-6 | (igual ao cenário A) | — | — |
| 7 | `consultas_esaj` | `current_state` | `PROCESSING` |
| 8 | `logs` | `descricao` | `"Pipeline iniciado"` \| PIPELINE |
| 9 | `process_tracking` | `OCR / OCR_ERRO` | `erro=true` \| `"Nenhum ANEXO II detectado..."` |
| 10 | `consultas_esaj` | `current_state` | `MANUAL_PROCESS` *(set por processador.py)* |
| 11 | `logs` | `descricao` | `"Etapa 2: PDFs processados"` (continua!) |
| 12 | `esaj_detalhe_processos` | — | Processos modernos inseridos; antigos ausentes |
| 13 | `process_tracking` | `LAUDO_PARCIAL / LAUDO_PARCIAL` | `qtd_processos: N` (só processos bem-sucedidos) |
| 14 | `process_tracking` | `LAUDO_PARCIAL / PARCIAL_INFORMADO` | alerta interno enviado à Revisa |
| 15 | `consultas_esaj` | `current_state` | `REPORT_SENT` *(orchestrator sobrescreve MANUAL_PROCESS)* → `PARTIAL_REPORT_SENT` *(Laudo workflow)* |
| 16 | `process_tracking` | `LAUDO_PARCIAL / PARCIAL_INFORMADO` | alerta interno enviado (pelo `Alerta_Laudo_Parcial`, a cada 10 min) |

> ⚠️ **Atenção — Race Condition:** `processador.py` seta `MANUAL_PROCESS` durante o OCR. Se o pipeline completo terminar com sucesso (outros JSONs válidos), o orchestrator sobrescreve com `REPORT_SENT` que o Laudo workflow sobrescreve com `PARTIAL_REPORT_SENT`. O sinal real de que houve PDF antigo não está no `current_state` final, mas sim nos eventos `OCR_ERRO` em `process_tracking`.

### Como identificar PDFs antigos "700"

1. **Em `process_tracking`:** `etapa = 'OCR'` AND `evento = 'OCR_ERRO'` AND `mensagem_erro ILIKE '%Nenhum ANEXO II%'`
2. **Em `process_tracking`.`detalhes`:** `detalhes->>'processo'` começa com `"7"` (número do processo antigo)
3. **Em `logs`:** `descricao ILIKE '%Nenhum ANEXO II detectado%'` AND `processo = 'PIPELINE'`
4. **Em `process_tracking`:** presença de `LAUDO_PARCIAL / LAUDO_PARCIAL` indica que houve OCR parcial

### Formato do número de processo antigo

```
7007859-54.2010.8.26.0500   ← antigo (começa com 7)
0035938-67.2018.8.26.0053   ← moderno (começa com 0)
```

---

## Cenário C — Falha de OCR (Motivo Não é PDF Antigo)

### C1 — CPF não encontrado em nenhum ofício do PDF

**Causa:** O PDF baixado pertence ao processo correto, mas o CPF esperado não aparece no texto do ofício. Pode indicar PDF com múltiplos credores onde o CPF não está no ofício principal.

**Erro registrado:** `"CPF XXX.XXX.XXX-XX não encontrado em nenhum ofício"`

**Comportamento das tabelas:**
- `process_tracking`: `OCR / OCR_ERRO` com `mensagem_erro` descrevendo o CPF não encontrado
- `consultas_esaj`: `MANUAL_PROCESS` (se for o único processo) → após alerta: `ALERTA_MANUAL_SENT`

### C2 — ANEXO II encontrado, mas pertence a outro CPF

**Causa:** PDF com múltiplos credores onde o ANEXO II indexado pertence a outro CPF. O sistema encontra o ANEXO II mas não consegue mapear ao CPF esperado.

**Exemplo real:** CPF `28721705534` — processo `0467036-75.2025.8.26.0500`
```
"ANEXO II encontrado no PDF, mas nenhum pertence ao CPF esperado.
CPF esperado: 287.217.055-34. CPF(s) encontrado(s): 473.290.198-01"
```

**Comportamento das tabelas:**
- `process_tracking`: `OCR / OCR_ERRO` com `erro=true`
- `esaj_detalhe_processos`: processo NÃO inserido
- Se outros processos do cliente passaram → `PARTIAL_REPORT_SENT` (via Laudo workflow)

### C3 — Falha total de OCR (todos os PDFs falham)

**Causa:** Todos os processos do cliente têm PDFs problemáticos.

**Comportamento das tabelas:**
- `process_tracking`: múltiplos `OCR / OCR_ERRO`
- `pipeline_completo.sh`: Etapa 3 detecta 0 JSONs → `exit 1`
- Orchestrator captura `CalledProcessError` → `update_status_in_db('PIPELINE_ERROR')`
- `consultas_esaj.current_state = 'PIPELINE_ERROR'`
- `esaj_detalhe_processos`: nenhum registro inserido para o CPF

---

## Cenário D — Falha no Download (AUTH_ERROR / DOWNLOAD_FAILED)

### D1 — Falha de Autenticação no e-SAJ

**Causa:** Certificado A1 expirado, sessão do Chrome corrompida, ou falha no Web Signer.

**Comportamento:**
- `crawler_full.py` retorna exit code != 0
- Orchestrator: `update_status_in_db('AUTH_ERROR')`
- `consultas_esaj.current_state = 'AUTH_ERROR'`, `status = true`
- `logs`: `"ERRO: Falha crítica na autenticação inicial"` | processo=crawler
- Nenhum PDF baixado; OCR não é executado
- `process_tracking`: sem evento OCR (apenas PAYMENT events existem)

### D2 — Download Concluído mas PDFs Ausentes

**Causa:** Crawler executou mas nenhum arquivo .pdf foi encontrado na pasta de saída (ex.: download interrompido, problema de permissão de pasta).

**Comportamento:**
- `consultas_esaj.current_state = 'DOWNLOAD_FAILED'`
- `logs`: `"Nenhum PDF encontrado em ..."` | processo=crawler
- OCR não é executado

---

## Cenário F — Todos os Processos Rejeitados pelo DEPRE (Falso REPORT_SENT)

**Definição:** Cliente tem precatórios e o OCR funciona corretamente, porém **todos** os processos foram detectados como `rejeitado = true` (ofício rejeitado pelo DEPRE). Nesse caso, o `calc-precatorio-tjsp/main.py` retorna `"Nenhum processo pendente."` e **não chama** o webhook `/reporte-email-cpf`. O laudo nunca é enviado, mas o sistema registra `REPORT_SENT` como se tivesse sido.

**Exemplo real:** CPF `16914336830` (Geovane dos Santos Bazilio — 08/06/2026)

Motivo de rejeição extraído do PDF:
> *"O ofício requisitório encaminhado eletronicamente apresenta irregularidade(s) passível(eis) de REJEIÇÃO sem processamento no DEPRE, tendo em vista que, nos termos da Portaria nº 9.816/2019 e do Comunicado Conjunto nº 1.212/2018, o Instituto de Previdência e/ou Assistência Médica indicado no Anexo II não corresponde ao Devedor(a) constante do presente precatório."*

### Timeline de eventos

| Ordem | Tabela | Coluna/Evento | Valor |
|---|---|---|---|
| 1–6 | (igual ao cenário A) | — | — |
| 7 | `consultas_esaj` | `current_state` | `PROCESSING` |
| 8 | `logs` | `descricao` | `"⚠️ V3.0.2: OFÍCIO REJEITADO detectado na página N"` \| OCR |
| 9 | `esaj_detalhe_processos` | `rejeitado` | `true` + `motivo_rejeicao` populado |
| 10 | `logs` | `descricao` | `"Etapa 9: iniciando cálculo final"` \| PIPELINE |
| 11 | `logs` | `descricao` | **`"Nenhum processo pendente."`** \| calculo ← ponto de falha |
| 12 | `logs` | `descricao` | `"Etapa 9: cálculo final executado"` / `"Pipeline finalizado com sucesso"` \| PIPELINE |
| 13 | `consultas_esaj` | `current_state` | `REPORT_SENT` ← **FALSO POSITIVO** (orchestrator) |
| ~~14~~ | ~~`process_tracking`~~ | ~~`ENVIO_LAUDO / LAUDO_ENVIADO`~~ | **❌ NUNCA OCORRE** |
| ~~15~~ | ~~`consultas_esaj`~~ | ~~`current_state = FINAL_REPORT_SENT`~~ | **❌ NUNCA OCORRE** |

**Estado final das tabelas:**
- `consultas_esaj.current_state = 'REPORT_SENT'` ← travado neste estado transitório para sempre
- `esaj_detalhe_processos`: 1 registro com `rejeitado = true` e `motivo_rejeicao` populado
- `esaj_calc_precatorio_resumo`: **nenhum registro para o CPF** ← raiz do problema
- `process_tracking`: sem `ENVIO_LAUDO` — nenhum laudo foi enviado
- `logs`: nenhuma entrada de erro; pipeline aparece como "sucesso"

### Por que o laudo não é enviado

```
1. OCR detecta rejeitado=true → grava em esaj_detalhe_processos
2. calc/main.py: filtra processos com rejeitado=true → nada a calcular
3. calc/main.py: retorna sem chamar o webhook /reporte-email-cpf
4. Workflow "Laudo envio email+cpf": NUNCA É ACIONADO
5. orchestrator: seta REPORT_SENT ao detectar pipeline_exit=0
6. Cliente: não recebe NADA
```

> ⚠️ **Importante:** O workflow `"Laudo envio email+cpf"` JÁ trata processos rejeitados corretamente — o SQL `Check Processamento Completo` considera `rejeitado=true` como `'Processado'` e o HTML exibe o bloco ❌ com o motivo. O problema é apenas que o webhook nunca é chamado.

### Como identificar este cenário

1. `consultas_esaj.current_state = 'REPORT_SENT'` há mais de 10 minutos (nunca evoluiu para `FINAL_REPORT_SENT` ou `PARTIAL_REPORT_SENT`)
2. `esaj_detalhe_processos`: todos os registros do CPF têm `rejeitado = true`
3. `esaj_calc_precatorio_resumo`: **zero registros** para o CPF
4. `process_tracking`: **zero eventos** `ENVIO_LAUDO / LAUDO_ENVIADO`
5. `logs`: presença de `"Nenhum processo pendente."` com `processo='calculo'`

### Ação corretiva imediata (manual)

```sql
-- Passo 1: resetar o estado para que o workflow consiga encontrar a consulta
UPDATE consultas_esaj
SET current_state = 'OCR_COMPLETE', state_updated_at = NOW()
WHERE cpf = '16914336830'  -- substituir pelo CPF
  AND current_state = 'REPORT_SENT';
```

```bash
# Passo 2: chamar o webhook manualmente (VPS)
curl -X POST http://localhost:5678/webhook/reporte-email-cpf \
  -H "Content-Type: application/json" \
  -d '{"cpf":"16914336830","email":"email-do-cliente@dominio.com"}'
```

### Correção permanente (pendente de deploy)

Adicionar **Etapa 9b** no `pipeline_completo.sh`: após o cálculo, verificar se `esaj_calc_precatorio_resumo` gerou registros para o CPF. Se `COUNT = 0`, buscar o email em `consultas_esaj` e chamar o webhook diretamente. Ver detalhes em `validacao_junho_08/diagnostico_cpf_16914336830.md`.

---

## Cenário E — Cliente Sem Processos (NO_VALID_PROCESS)

**Causa:** A consulta ao e-SAJ retornou processos, mas nenhum deles é da classe "Precatório".

**Comportamento:**
- `consultas_esaj.current_state = 'NO_VALID_PROCESS'`
- Nenhum download ou OCR executado
- `process_tracking.CONSULTA_REALIZADA.metadata.total_processos = 0` já indica isso na fase 1

---

## Resumo Comparativo — Estado Final por Cenário

| Cenário | `current_state` final | `OCR_ERRO` em pt | `LAUDO_*` em pt | Registros em `esaj_detalhe` | Registros em `esaj_calc` |
|---|---|---|---|---|---|
| **A — Sucesso** | `FINAL_REPORT_SENT` | ❌ | `LAUDO_ENVIADO` | Todos os processos | ✅ 1+ registros |
| **B — PDF antigo (parcial)** | `PARTIAL_REPORT_SENT` | ✅ (por PDF antigo) | `LAUDO_PARCIAL` + `PARCIAL_INFORMADO` | Só processos modernos | ✅ processos modernos |
| **C1 — CPF não encontrado** | `ALERTA_MANUAL_SENT` ou `PARTIAL_REPORT_SENT` | ✅ | Depende | Processos onde CPF foi achado | Depende |
| **C2 — ANEXO II de outro CPF** | `ALERTA_MANUAL_SENT` ou `PARTIAL_REPORT_SENT` | ✅ | `LAUDO_PARCIAL` | Processos onde CPF foi achado | Depende |
| **C3 — Falha total OCR** | `PIPELINE_ERROR` | ✅ (múltiplos) | ❌ | Nenhum | ❌ nenhum |
| **D1 — Auth error** | `AUTH_ERROR` | ❌ | ❌ | Nenhum | ❌ nenhum |
| **D2 — Download falhou** | `DOWNLOAD_FAILED` | ❌ | ❌ | Nenhum | ❌ nenhum |
| **E — Sem precatórios** | `NO_VALID_PROCESS` | ❌ | ❌ | Nenhum | ❌ nenhum |
| **F — 100% rejeitados** | `REPORT_SENT` ⚠️ **TRAVADO** | ❌ | ❌ **LAUDO NÃO ENVIADO** | ✅ com `rejeitado=true` | ❌ nenhum ← raiz |

> `MANUAL_PROCESS` é transitório: após o `Alerta_Reporte_Manual` disparar (a cada 10 min), transiciona para `ALERTA_MANUAL_SENT`. Para casos mistos (parcial), o Laudo workflow seta `PARTIAL_REPORT_SENT`.

> `REPORT_SENT` normalmente é transitório (orchestrator → substituído pelo Laudo workflow). No **Cenário F**, o Laudo workflow nunca é chamado, então o estado fica travado em `REPORT_SENT` indefinidamente. Use Q19 para detectar esses casos.
