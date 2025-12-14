# Tests Workflows

Pasta contendo workflows de teste para o projeto RevisaBot.

## Workflows

### CPF_batch_processing.json

**ID no n8n:** `jMzstMZfztUMz7O6`

**Descrição:** Workflow simplificado para consulta de CPF no e-SAJ TJSP. Recebe CPF via webhook, consulta TJSP, extrai nome e processos, salva no banco com UPSERT e simula pagamento aprovado.

**Fluxo:**
```
Webhook → Extract CPF → Consulta e-SAJ → Parse e-SAJ Response → Upsert Consulta → Respond
```

**Endpoint:**
```
POST https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing
```

**Teste:**
```bash
curl -X POST https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing \
  -H "Content-Type: application/json" \
  -d '{"cpf": "08212993876"}' | jq .
```

**Características:**
- Usa UPSERT (ON CONFLICT) para evitar duplicatas
- Simula pagamento aprovado (PAYMENT_APPROVED)
- WhatsApp fixo: 5511941455345
- Parser com regex otimizados para e-SAJ TJSP

**Regex importantes:**
- **Classe:** `id="classeProcesso"[^>]*>([^<]+)`
- **Nome:** `nomeParteEAdvogado[^>]*>[\s\n]*([A-ZÀ-Ú][A-Za-zÀ-ÿ\s]+?)(?:\s*<br|\s*Advogad)`

---

*Última atualização: 14/12/2025*
