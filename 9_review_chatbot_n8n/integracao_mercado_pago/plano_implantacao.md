# Plano de Implantação - Integração Mercado Pago

**Data:** 2025-12-10  
**Versão:** 1.0  
**Status:** Análise e Planejamento

---

## 1. Resumo Executivo

Este documento detalha a análise de impacto e o plano de implementação para adicionar a integração de pagamento via Mercado Pago ao workflow RevisaBot v2. O objetivo é permitir que usuários paguem R$ 99,90 pelo laudo completo de precatórios diretamente via WhatsApp.

---

## 2. Estado Atual do Workflow

### 2.1 Fluxo Existente

```
IDLE → CPF → AWAITING_CONFIRMATION → sim → AWAITING_EMAIL → email → AWAITING_CODE → código → AWAITING_PAYMENT
                                    → não → IDLE
```

### 2.2 Estados Atuais

| Estado | Descrição | Próximo Estado |
|--------|-----------|----------------|
| `IDLE` | Aguardando interação | Vários |
| `AWAITING_CONFIRMATION` | Aguardando "sim/não" após consulta | `AWAITING_EMAIL` ou `IDLE` |
| `AWAITING_EMAIL` | Aguardando email | `AWAITING_CODE` |
| `AWAITING_CODE` | Aguardando código 6 dígitos | `AWAITING_PAYMENT` |
| `AWAITING_PAYMENT` | **Estado terminal atual - sem ação** | ❌ Não implementado |

### 2.3 Problema Atual

O estado `AWAITING_PAYMENT` é um **dead-end**:
- Mensagem atual: "🔗 Link de pagamento: [Em breve]"
- Não há link real de pagamento
- Não há tracking de pagamento aprovado/recusado
- Usuário fica "preso" neste estado

---

## 3. Arquitetura Proposta

### 3.1 Novos Estados

| Estado | Descrição | Timeout |
|--------|-----------|---------|
| `AWAITING_PAYMENT` | Link gerado, aguardando pagamento | 24h |
| `PAYMENT_APPROVED` | Pagamento confirmado ✅ | - |
| `PAYMENT_REJECTED` | Pagamento recusado ❌ | - |
| `PAYMENT_PENDING` | Pagamento em análise ⏳ | 48h |

### 3.2 Fluxo Proposto

```
                                    ┌─────────────────────────────────────┐
                                    │         AWAITING_PAYMENT            │
                                    │  (Link MP gerado e enviado)         │
                                    └─────────────────────────────────────┘
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼               ▼               ▼
                            ┌───────────┐   ┌───────────┐   ┌───────────┐
                            │ APPROVED  │   │ PENDING   │   │ REJECTED  │
                            │ (Webhook) │   │ (Webhook) │   │ (Webhook) │
                            └───────────┘   └───────────┘   └───────────┘
                                    │               │               │
                                    ▼               ▼               ▼
                            ┌───────────┐   ┌───────────┐   ┌───────────┐
                            │ Envia     │   │ Aguarda   │   │ Oferece   │
                            │ Laudo     │   │ Resolução │   │ Retry     │
                            └───────────┘   └───────────┘   └───────────┘
```

### 3.3 Componentes Necessários

| Componente | Tipo | Função |
|------------|------|--------|
| `Create MP Preference` | HTTP Request | Cria preferência de pagamento no MP |
| `MP Webhook Trigger` | Webhook | Recebe notificações do MP |
| `Process MP Notification` | Code | Processa e valida notificação |
| `Get Payment Status` | HTTP Request | Consulta status do pagamento |
| `Response PAYMENT_*` | Set | Prepara respostas para cada status |

---

## 4. Análise de Impacto

### 4.1 Nodes Afetados

| Node | Impacto | Risco |
|------|---------|-------|
| `Validate Code` | **MODIFICAR** - Após validação, gerar link MP | 🟡 Médio |
| `Route Message Type` | **MODIFICAR** - Adicionar rota para AWAITING_PAYMENT | 🟡 Médio |
| `Update State` | **MANTER** - Já suporta novos estados | 🟢 Baixo |
| `Send WhatsApp Response` | **MANTER** - Já funciona | 🟢 Baixo |

### 4.2 Banco de Dados

**Novas colunas necessárias em `consultas_esaj`:**

```sql
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS mp_preference_id VARCHAR(255);
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS mp_payment_id VARCHAR(255);
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS mp_payment_status VARCHAR(50);
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS mp_payment_amount DECIMAL(10,2);
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS mp_external_reference VARCHAR(255);
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS payment_link TEXT;
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS payment_created_at TIMESTAMP;
ALTER TABLE consultas_esaj ADD COLUMN IF NOT EXISTS payment_confirmed_at TIMESTAMP;
```

### 4.3 Novo Webhook

**Endpoint:** `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification`

Este webhook será **separado** do webhook principal do WhatsApp para:
- Evitar conflitos de processamento
- Facilitar debugging
- Permitir retry independente

---

## 5. Pontos Críticos de Risco

### 5.1 Riscos de Quebra do Fluxo

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Webhook MP não chega | 🟡 Média | 🔴 Alto | Implementar polling de fallback |
| Timeout de resposta ao MP | 🟡 Média | 🟡 Médio | Responder 200 imediatamente, processar async |
| Estado inconsistente | 🟢 Baixa | 🔴 Alto | Usar transações no PostgreSQL |
| Link MP expira | 🟢 Baixa | 🟡 Médio | Gerar novo link se expirado |
| Usuário paga mas webhook falha | 🟢 Baixa | 🔴 Alto | Consulta manual + reconciliação |

### 5.2 Riscos de Segurança

| Risco | Mitigação |
|-------|-----------|
| Webhook falso (spoofing) | Validar assinatura x-signature do MP |
| Token exposto | Usar credenciais do n8n, não hardcode |
| Replay attack | Verificar se payment_id já foi processado |

### 5.3 Riscos de UX

| Risco | Mitigação |
|-------|-----------|
| Usuário não recebe link | Fallback: enviar link novamente se pedir |
| Usuário paga e não recebe confirmação | Mensagem proativa após webhook |
| Link expira antes do pagamento | Timeout de 24h + opção de gerar novo |

---

## 6. Estratégia de Implementação Segura

### 6.1 Abordagem: Feature Flag + Workflow Paralelo

**NÃO modificar o workflow de produção diretamente.**

1. **Fase 1**: Criar workflow separado para testes
2. **Fase 2**: Testar com sandbox do MP
3. **Fase 3**: Integrar ao workflow principal com feature flag
4. **Fase 4**: Rollout gradual

### 6.2 Ordem de Implementação

```
1. [DB] Adicionar novas colunas no PostgreSQL
2. [N8N] Criar credencial Header Auth para MP
3. [N8N] Criar webhook separado para notificações MP
4. [N8N] Criar node "Create MP Preference" (isolado)
5. [TEST] Testar geração de link em sandbox
6. [N8N] Criar node "Process MP Notification"
7. [TEST] Testar webhook com simulador do MP
8. [N8N] Modificar "Validate Code" para chamar MP
9. [N8N] Adicionar rotas para novos estados
10. [TEST] Teste end-to-end em sandbox
11. [PROD] Trocar credenciais para produção
12. [MONITOR] Monitorar primeiras transações
```

---

## 7. Detalhamento Técnico

### 7.1 Node: Create MP Preference

**Tipo:** HTTP Request  
**Método:** POST  
**URL:** `https://api.mercadopago.com/checkout/preferences`

**Headers:**
```
Authorization: Bearer {{ $credentials.mercadoPagoToken }}
Content-Type: application/json
```

**Body:**
```json
{
  "items": [
    {
      "title": "Laudo Completo de Precatórios",
      "description": "Relatório detalhado com valores atualizados - CPF {{ $json.cpf }}",
      "quantity": 1,
      "currency_id": "BRL",
      "unit_price": 99.90
    }
  ],
  "payer": {
    "email": "{{ $json.stored_email }}"
  },
  "external_reference": "{{ $json.whatsapp_from }}_{{ $json.cpf }}_{{ Date.now() }}",
  "back_urls": {
    "success": "https://revisaprecatorio.com.br/pagamento/sucesso",
    "failure": "https://revisaprecatorio.com.br/pagamento/erro",
    "pending": "https://revisaprecatorio.com.br/pagamento/pendente"
  },
  "auto_return": "approved",
  "notification_url": "https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification",
  "statement_descriptor": "REVISA PRECATORIO"
}
```

**Resposta esperada:**
```json
{
  "id": "1234567890-abcdef",
  "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=...",
  "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=..."
}
```

### 7.2 Webhook: MP Notification

**Payload recebido do MP:**
```json
{
  "action": "payment.created",
  "api_version": "v1",
  "data": {
    "id": "1234567890"
  },
  "date_created": "2025-12-10T10:00:00.000-03:00",
  "id": "notification-id",
  "live_mode": true,
  "type": "payment",
  "user_id": "3052968619"
}
```

**Fluxo de processamento:**
1. Responder 200 OK imediatamente
2. Extrair `data.id` (payment_id)
3. Chamar GET `/v1/payments/{id}` para obter detalhes
4. Verificar `status`: `approved`, `rejected`, `pending`, `in_process`
5. Atualizar estado no banco
6. Enviar mensagem WhatsApp apropriada

### 7.3 Status de Pagamento do MP

| Status MP | Estado Workflow | Ação |
|-----------|-----------------|------|
| `approved` | `PAYMENT_APPROVED` | Enviar laudo por email |
| `rejected` | `PAYMENT_REJECTED` | Oferecer novo link |
| `pending` | `PAYMENT_PENDING` | Informar que está em análise |
| `in_process` | `PAYMENT_PENDING` | Informar que está em análise |
| `cancelled` | `PAYMENT_REJECTED` | Oferecer novo link |
| `refunded` | `PAYMENT_REFUNDED` | Informar reembolso |

---

## 8. Mensagens WhatsApp

### 8.1 Após validação do código (gerar link)

```
✅ Email verificado com sucesso!

💳 Para receber o laudo completo com cálculo atualizado, efetue o pagamento de R$ 99,90.

🔗 Clique no link abaixo para pagar:
{{ init_point }}

⏰ Este link é válido por 24 horas.

Após o pagamento, você receberá o laudo no email: {{ stored_email }}
```

### 8.2 Pagamento Aprovado

```
🎉 Pagamento confirmado!

Seu laudo completo de precatórios está sendo gerado e será enviado para {{ stored_email }} em até 24 horas.

Obrigado por confiar na Revisa Precatórios!

Digite menu para voltar ao início.
```

### 8.3 Pagamento Recusado

```
❌ Pagamento não aprovado.

Houve um problema com seu pagamento. Isso pode acontecer por:
• Limite insuficiente
• Dados incorretos
• Bloqueio do banco

🔄 Deseja tentar novamente? Digite "sim" para gerar um novo link.
```

### 8.4 Pagamento Pendente

```
⏳ Pagamento em análise.

Seu pagamento está sendo processado pelo Mercado Pago. Isso pode levar até 2 dias úteis.

Assim que for confirmado, enviaremos o laudo para {{ stored_email }}.

Digite menu para voltar ao início.
```

---

## 9. Checklist de Implementação

### 9.1 Pré-requisitos

- [ ] Credenciais MP de produção obtidas
- [ ] Webhook URL configurada no painel MP
- [ ] Colunas adicionadas no PostgreSQL
- [ ] Backup do workflow atual

### 9.2 Desenvolvimento

- [ ] Criar credencial Header Auth no n8n
- [ ] Criar webhook separado para MP
- [ ] Implementar node Create MP Preference
- [ ] Implementar node Process MP Notification
- [ ] Implementar node Get Payment Status
- [ ] Modificar Validate Code para gerar link
- [ ] Adicionar rotas para novos estados
- [ ] Implementar Response nodes para cada status

### 9.3 Testes

- [ ] Teste em sandbox: pagamento aprovado
- [ ] Teste em sandbox: pagamento recusado
- [ ] Teste em sandbox: pagamento pendente
- [ ] Teste de timeout do webhook
- [ ] Teste de retry do webhook
- [ ] Teste end-to-end completo

### 9.4 Produção

- [ ] Trocar credenciais para produção
- [ ] Monitorar primeiras 10 transações
- [ ] Verificar logs de erro
- [ ] Confirmar recebimento de webhooks

---

## 10. Rollback Plan

Em caso de problemas críticos:

1. **Desativar** o node Create MP Preference
2. **Reverter** Validate Code para versão anterior (mensagem "[Em breve]")
3. **Manter** webhook MP ativo para processar pagamentos já iniciados
4. **Comunicar** usuários afetados manualmente

---

## 11. Cronograma Estimado

| Fase | Duração | Descrição |
|------|---------|-----------|
| Preparação | 1 dia | DB, credenciais, backup |
| Desenvolvimento | 2-3 dias | Nodes, webhooks, rotas |
| Testes Sandbox | 1-2 dias | Todos os cenários |
| Produção | 1 dia | Deploy + monitoramento |
| **Total** | **5-7 dias** | |

---

## 12. Próximos Passos

1. ✅ Análise de impacto (este documento)
2. ⏳ Aprovação do plano
3. ⏳ Executar migrations no PostgreSQL
4. ⏳ Criar credencial MP no n8n
5. ⏳ Implementar em ambiente de teste
6. ⏳ Testes com sandbox
7. ⏳ Deploy em produção

---

## Anexo A: Referências

- [Mercado Pago - Checkout Pro](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/landing)
- [Mercado Pago - Webhooks](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/notifications/webhooks)
- [Mercado Pago - API Reference](https://www.mercadopago.com.br/developers/pt/reference)

## Anexo B: Credenciais (Desenvolvimento)

```
Public_Key: APP_USR-14a86ba5-7347-4043-bebd-2687b6ec0f3a
Access_Token: APP_USR-7529371852440001-120923-fb2daa06020e5080dc223d79a64763b0-3052968619
```

⚠️ **ATENÇÃO**: Estas são credenciais de TESTE. Para produção, usar credenciais do painel de produção.
