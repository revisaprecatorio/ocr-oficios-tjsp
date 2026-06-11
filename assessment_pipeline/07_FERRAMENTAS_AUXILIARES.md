# Ferramentas Auxiliares — Revisa Precatório

**Atualizado:** 06/2026

Estas ferramentas **não fazem parte do pipeline principal** de processamento de precatórios. São instrumentos de apoio operacional para uso interno da equipe.

---

## Índice

1. [Streamlit Backoffice](#1-streamlit-backoffice)
2. [CPF Batch Processing](#2-cpf-batch-processing)

---

## 1. Streamlit Backoffice

**Repositório:** [`revisaprecatorio/6.UI_backoffice`](https://github.com/revisaprecatorio/6.UI_backoffice)  
**Versão atual:** V3.0.0 (Dez/2025)  
**Produção:** `http://srv987902.hstgr.cloud:8502` | `https://revisaprecatorio.com.br/backoffice`

### O que é

Interface web de backoffice para monitoramento e gestão dos processos de precatórios. Exibe dados consolidados da view `vw_backoffice_processos` (join de 3 tabelas: `consultas_esaj`, `esaj_detalhe_processos`, `esaj_calc_precatorio_resumo`).

**Não faz parte do pipeline de produção** — é uma ferramenta interna para que a equipe possa monitorar o status de cada CPF, verificar cálculos e identificar casos que requerem atenção, sem necessidade de queries SQL.

> **Nota histórica:** Uma versão anterior mais simples (`3_streamlit/`) existia neste repositório, lendo apenas `esaj_detalhe_processos`. Foi removida em Jun/2026 após o `6.UI_backoffice` tornar-se a versão canônica com funcionalidades superiores.

### Funcionalidades

**Tabs disponíveis:**

| Tab | Conteúdo |
|---|---|
| **📋 Pipeline** | Visão geral por estado do processo (`current_state`) |
| **💰 Cálculos** | Valores atualizados: `total_corrigido`, `valorizacao_percentual` |
| **⚠️ Atenção** | Processos rejeitados, anomalias, óbito sem herdeiros |
| **👴 Preferenciais** | Idosos, doença grave, PCD |
| **📄 Detalhes** | Visualização completa + download PDF |

**Filtros sidebar:** Estado do pipeline, Status (rejeitado/anomalia/óbito), Preferências, Busca por CPF/Nome/Processo

### View consumida

```sql
-- vw_backoffice_processos consolida:
SELECT
    ce.current_state, ce.whatsapp_from, ce.email,
    edp.*,              -- todos os 35 campos OCR
    ecr.principal_final, ecr.juros_mora_final_corrigido,
    ecr.total_corrigido, ecr.valorizacao_percentual
FROM consultas_esaj ce
JOIN esaj_detalhe_processos edp ON edp.cpf = ce.cpf
LEFT JOIN esaj_calc_precatorio_resumo ecr ON ecr.cpf = edp.cpf
    AND ecr.numero_processo_cnj = edp.numero_processo_cnj;
```

### Deploy (na VPS)

```bash
cd ~/6.UI_backoffice
./deploy.sh
```

O script faz automaticamente: `git pull` → `docker stop` → `docker build --no-cache` → `docker up -d` → health check.

### Variáveis de ambiente

```bash
DB_HOST=72.60.62.124
DB_PORT=5432
DB_NAME=n8n
DB_USER=admin
DB_PASSWORD=<senha>
PDF_DIR=/data/consultas
STREAMLIT_PORT=8502
```

Para documentação completa, deploy manual e troubleshooting, ver o README do repositório [`6.UI_backoffice`](https://github.com/revisaprecatorio/6.UI_backoffice).

---

## 2. CPF Batch Processing

**Arquivo:** `workflows_n8n/CPF_batch_processing.json`  
**Webhook:** `POST /webhook/cpf-batch-processing`  
**Tipo:** Workflow n8n

### O que é

Ferramenta de ingestão direta no banco, sem passar pelo fluxo WhatsApp. Recebe um CPF via HTTP, consulta o e-SAJ e faz upsert em `consultas_esaj`.

Documentado em detalhes em `06_WORKFLOWS_N8N.md` — Seção 7.

### Quando usar

| Situação | Use CPF_batch_processing? |
|---|---|
| Reprocessar CPF após erro de pipeline | ✅ Sim |
| Cliente que entrou por canal diferente do WhatsApp | ✅ Sim |
| Testes de integração end-to-end | ✅ Sim |
| Inserção em lote de múltiplos CPFs | ✅ Sim (enviar um POST por CPF) |
| Novo cliente via WhatsApp | ❌ Não (usar Chatbot Revisa) |

### Como usar

```bash
# Inserir/atualizar um CPF
curl -s -X POST "http://<n8n-host>:5678/webhook/cpf-batch-processing" \
  -H "Content-Type: application/json" \
  -d '{"cpf": "12345678900"}'

# Resposta esperada (sucesso):
# {"success": true, "cpf": "12345678900", "processos": [...]}
```

> **Atenção:** O `whatsapp_from` é fixado em `5511941455345` (número da equipe). O cliente **não recebe notificação** via WhatsApp. Após a inserção, o orchestrator pode processar normalmente desde que `current_state` seja `PAYMENT_APPROVED` e `status = false`.

### Limitações

- Não gera link de pagamento
- Não coleta email do cliente automaticamente
- Não atualiza estado para além do upsert inicial — o orquestrador precisa detectar e assumir
