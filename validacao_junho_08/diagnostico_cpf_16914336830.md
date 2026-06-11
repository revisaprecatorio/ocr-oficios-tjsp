# Diagnóstico: CPF 16914336830 — Geovane dos Santos Bazilio
**Data da ocorrência:** 08/06/2026  
**Data da análise:** 09/06/2026  
**Analista:** Cascade (IA) + Persival  
**Status:** ⚠️ Laudo NÃO enviado ao cliente — correção proposta, aguardando aprovação

---

## 1. Contexto

O cliente CPF `16914336830` (Geovane dos Santos Bazilio) realizou uma consulta, pagou R$ 1,00 pelo laudo e **não recebeu nenhuma mensagem ou email**. Os logs internos indicam `Status final: REPORT_SENT`, o que levou a acreditar que tudo havia funcionado. Após análise detalhada dos CSVs exportados e do código, identificamos a causa raiz.

---

## 2. O que foi processado

### PDF / Processo
- **Arquivo:** `0178547-85.2021.8.26.0500.pdf`
- **Processo CNJ:** `0178547-85.2021.8.26.0500`
- **Valor total requisitado:** R$ 39.788,57

### Resultado do OCR (Etapa 2)
O processador identificou, na **página 110**, um texto de **REJEIÇÃO do DEPRE**:

> *"O ofício requisitório encaminhado eletronicamente apresenta irregularidade(s) passível(eis) de REJEIÇÃO sem processamento no DEPRE, tendo em vista que, nos termos da Portaria nº 9.816/2019 e do Comunicado Conjunto nº 1.212/2018, o Instituto de Previdência e/ou Assistência Médica indicado no Anexo II não corresponde ao Devedor(a) constante do presente precatório."*

O processador gravou corretamente `rejeitado = true` e o `motivo_rejeicao` acima em `esaj_detalhe_processos`.

---

## 3. Linha do tempo completa (logs confirmados)

| Log ID | Hora | Descrição | Origem |
|--------|------|-----------|--------|
| 10535 | 13:55:44 | Job 8424 iniciado | crawler |
| 10536 | 13:56:17 | Iniciando OCR (modo BLOQUEANTE) | OCR |
| 10537 | 13:56:19 | Pipeline iniciado | PIPELINE |
| 10538 | 13:56:22 | Etapa 1: staging limpo | PIPELINE |
| **10539** | **13:56:29** | **⚠️ OFÍCIO REJEITADO detectado na página 110** | **OCR** |
| 10540 | 13:56:45 | Etapa 2: PDFs processados | PIPELINE |
| 10541 | 13:56:47 | Etapa 3: 1 JSONs preparados | PIPELINE |
| 10542 | 13:56:53 | Etapa 4: ingestão executada | PIPELINE |
| 10543 | 13:57:02 | Etapa 5: validação OK — 1 registros no banco | PIPELINE |
| 10544 | 13:57:05 | Etapa 6: tags recalculadas | PIPELINE |
| 10545 | 13:57:07 | Etapa 7: JSONs movidos | PIPELINE |
| 10546 | 13:57:10 | Etapa 8: PDFs arquivados | PIPELINE |
| 10547 | 13:57:13 | Etapa 9: iniciando cálculo final | PIPELINE |
| **10548** | **13:57:14** | **Nenhum processo pendente.** | **calculo** |
| 10549 | 13:57:18 | Etapa 9: cálculo final executado | PIPELINE |
| 10550 | 13:57:20 | Pipeline finalizado com sucesso | PIPELINE |
| 10551 | 13:57:22 | OCR finalizado com sucesso | OCR |
| **10552** | **13:57:31** | **Status final: REPORT_SENT** ← ❌ FALSO POSITIVO | **crawler** |

**Fato confirmado:** Nenhum evento `ENVIO_LAUDO` / `LAUDO_ENVIADO` foi registrado em `process_tracking` para este CPF.

---

## 4. Causa raiz — cadeia de falhas

### 4.1 Etapa 9 do pipeline não gerou cálculo

O script `calc-precatorio-tjsp/main.py` filtra processos que precisam de cálculo. Como o processo está marcado como `rejeitado = true` (e/ou `numero_ordem` vazio), o script retornou `"Nenhum processo pendente."` e **não criou nenhum registro em `esaj_calc_precatorio_resumo`**.

### 4.2 O workflow "Laudo envio email+cpf" nunca foi acionado

O mecanismo de disparo do laudo depende da existência de um registro recente em `esaj_calc_precatorio_resumo`. Sem esse registro, o trigger nunca aconteceu.

> Comprovação: para o CPF `23926392568` (que funcionou), o calc criou o registro às **13:54:45** e o laudo foi enviado às **13:54:52** (7 segundos depois). Para o CPF `16914336830`, nenhum registro foi criado → nenhum laudo enviado.

### 4.3 O crawler setou `REPORT_SENT` incorretamente

Após o pipeline finalizar, o Chatbot Revisa atualizou `consultas_esaj.current_state = 'REPORT_SENT'` (às 13:57:29) **independentemente** de o laudo ter sido enviado ou não. Este é um bug secundário.

### 4.4 Diagrama da falha

```
PDF processado → rejeitado = true
        ↓
Etapa 9 (calc): "Nenhum processo pendente" → sem registro em esaj_calc_precatorio_resumo
        ↓
Trigger do "Laudo envio email+cpf": depende do registro → NUNCA DISPARADO
        ↓
Cliente não recebe NADA
        ↓
Crawler seta REPORT_SENT de qualquer forma ← BUG SECUNDÁRIO
```

---

## 5. Por que outros CPFs funcionam

Para processos **não rejeitados**, o fluxo é:

```
Etapa 9 (calc): calcula → cria registro em esaj_calc_precatorio_resumo
        ↓
Trigger detecta novo registro → chama webhook "reporte-email-cpf"
        ↓
Workflow "Laudo envio": Check Processamento Completo → todos_processados = true
        ↓
Build HTML → Send Email → WhatsApp → LAUDO_ENVIADO registrado
```

O problema é **exclusivo** para CPFs cujos processos são todos `rejeitado = true`.

---

## 6. Ponto importante: o n8n já está preparado

Ao inspecionar o workflow **"Laudo envio email+cpf"** (ID: `UrxjrcPE2C7WTLa0`), constatamos que ele **já trata processos rejeitados corretamente** em dois lugares:

### 6.1 SQL `Check Processamento Completo` — já marca rejeitados como processados

```sql
CASE
    WHEN r.numero_processo_cnj IS NOT NULL THEN 'Processado'  -- tem cálculo
    WHEN COALESCE(vp.rejeitado, false) = true THEN 'Processado'  -- ← rejeitado = OK
    ELSE 'Não Processado'
END AS status_calculo
```

→ Se todos os processos são rejeitados, `todos_processados = true` → segue para o caminho de laudo completo.

### 6.2 HTML `Build HTML Content` — já exibe bloco de rejeição

```javascript
${rejeitado ? `
  <div style="background-color: #ffe6e6; border-left: 4px solid #c1121f;">
    <p>❌ Motivo da Rejeição</p>
    <p>${p.motivo_rejeicao || 'Não especificado'}</p>
    <p>⚠️ Este precatório não é somado ao valor total do laudo 
       devido à pendência de rejeição.</p>
  </div>` : ''}
```

→ O laudo já seria gerado com o motivo da rejeição visível para o cliente.

**Conclusão: o n8n não precisa de nenhuma alteração. Só precisa receber o trigger.**

---

## 7. Correção proposta

### 7.1 Ação imediata para o CPF 16914336830

O `current_state` já está como `'REPORT_SENT'` no banco. O SQL do `Check Processamento Completo` filtra `current_state NOT IN ('REPORT_SENT', 'FINAL_REPORT_SENT')`, então seria necessário resetar o estado antes de chamar o webhook.

**Passo 1 — Resetar estado (SQL no banco VPS):**
```sql
UPDATE consultas_esaj
SET current_state = 'OCR_COMPLETE',
    state_updated_at = NOW()
WHERE id = 8424;
```

**Passo 2 — Chamar o webhook manualmente (VPS):**
```bash
curl -X POST http://localhost:5678/webhook/reporte-email-cpf \
  -H "Content-Type: application/json" \
  -d '{"cpf":"16914336830","email":"roferro@uol.com.br"}'
```

O laudo será enviado para `roferro@uol.com.br` com o processo exibido como ❌ Rejeitado, com o motivo completo e previsão de pagamento "Sem previsão (precatório rejeitado)".

---

### 7.2 Correção permanente no `pipeline_completo.sh`

**Arquivo:** `C:/Users/Administrator/Documents/revisa/ocr-oficios-tjsp/pipeline_completo.sh`  
**Onde:** Após a linha `log_db "Etapa 9: cálculo final executado"` (aproximadamente linha 247)  
**O que faz:** Detecta quando nenhum cálculo foi gerado (100% rejeitados) e aciona o webhook diretamente.

**Trecho a inserir:**

```bash
# ============================================================================
# ETAPA 9b — LAUDO DIRETO para processos 100% rejeitados (sem cálculo)
# ============================================================================
CALC_COUNT=$("${VENV_PYTHON}" - <<END
import psycopg2
conn = psycopg2.connect(
 host='${DB_HOST}', port='${DB_PORT}',
 database='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM esaj_calc_precatorio_resumo WHERE cpf = %s", ('${CPF}',))
print(cur.fetchone()[0])
conn.close()
END
)

if [ "$CALC_COUNT" -eq 0 ]; then
    log_db "Etapa 9b: nenhum cálculo gerado (processos rejeitados) — acionando laudo diretamente"
    EMAIL=$("${VENV_PYTHON}" - <<END
import psycopg2
conn = psycopg2.connect(
 host='${DB_HOST}', port='${DB_PORT}',
 database='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
)
cur = conn.cursor()
cur.execute("""
    SELECT email FROM consultas_esaj
    WHERE cpf = %s AND email IS NOT NULL AND email != ''
    ORDER BY created_at DESC LIMIT 1
""", ('${CPF}',))
row = cur.fetchone()
print(row[0] if row else '')
conn.close()
END
)
    if [ -n "$EMAIL" ]; then
        curl -s -X POST "http://localhost:5678/webhook/reporte-email-cpf" \
          -H "Content-Type: application/json" \
          -d "{\"cpf\": \"${CPF}\", \"email\": \"${EMAIL}\"}" || true
        log_db "Etapa 9b: laudo acionado para processo rejeitado (email: ${EMAIL})"
    else
        log_db "Etapa 9b: nenhum email encontrado para CPF ${CPF} — laudo não acionado"
    fi
fi
```

---

## 8. O que esta correção NÃO toca

| Componente | Alterado? |
|---|---|
| `calc-precatorio-tjsp/main.py` | ❌ Não |
| Workflows n8n | ❌ Não |
| `processador.py` (OCR) | ❌ Não |
| `ingest_all_jsons.py` | ❌ Não |
| Schema PostgreSQL | ❌ Não |
| `pipeline_completo.sh` | ✅ Sim — adiciona ~20 linhas após Etapa 9 |

---

## 9. Riscos e considerações

1. **Idempotência:** O `Check Processamento Completo` filtra `current_state NOT IN ('REPORT_SENT', 'FINAL_REPORT_SENT')`, então se chamado duas vezes não reenvia laudo já enviado.
2. **Email ausente:** O código verifica se o email existe antes de chamar o webhook. Se não houver, apenas loga e segue.
3. **Falha silenciosa:** O `curl` usa `|| true` para não abortar o pipeline em caso de falha da chamada — comportamento conservador igual ao resto do pipeline.
4. **Casos mistos (parte rejeitado, parte com cálculo):** A Etapa 9b só é acionada quando `CALC_COUNT = 0`, ou seja, **nenhum** processo gerou cálculo. Se houver ao menos um processo com cálculo, o fluxo normal já inclui os rejeitados no laudo via `vw_precatorios_full`.

---

## 10. Perguntas para o colega

1. O script `main.py` (calc) aciona o webhook diretamente após calcular? Ou o trigger é outro mecanismo?
2. Existe alguma razão para **não** chamar o webhook quando `CALC_COUNT = 0`?
3. A URL `http://localhost:5678/webhook/reporte-email-cpf` está correta para o ambiente de produção da VPS?
4. O reset de `current_state` para o CPF 16914336830 pode ser feito com segurança agora?

---

*Documento gerado em 09/06/2026 — baseado na análise dos arquivos em `validacao_junho_08/csv/` e inspeção direta do workflow n8n `UrxjrcPE2C7WTLa0`.*
