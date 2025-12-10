# Changelog - Integração Mercado Pago

## [2025-12-10] ✅ INTEGRAÇÃO COMPLETA - TESTADA COM SUCESSO

### ✅ Fase 1: Migração do Banco de Dados
- Adicionadas 8 novas colunas na tabela `consultas_esaj`:
  - `mp_preference_id` - ID da preferência de pagamento
  - `mp_payment_id` - ID do pagamento confirmado
  - `mp_payment_status` - Status do pagamento (approved, rejected, pending)
  - `mp_payment_amount` - Valor do pagamento
  - `mp_external_reference` - Referência externa (whatsapp_timestamp)
  - `payment_link` - Link de pagamento gerado
  - `payment_created_at` - Data de criação do link
  - `payment_confirmed_at` - Data de confirmação do pagamento
- Criados 4 índices para performance de busca

### ✅ Fase 2: Credenciais
- Criada credencial "Mercado Pago API" no n8n (Header Auth)
- Tipo: Bearer Token
- Ambiente: Sandbox/Teste
- Access Token corrigido (dígito faltante no final)

### ✅ Fase 3: Webhook de Notificações
- Workflow unificado: **Mercado Pago Unified** (ID: `6COT3ubybyI8QhYT`)
- URL de notificação: `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification`
- URL de geração de link: `https://n8n.srv987902.hstgr.cloud/webhook/generate-payment-link`
- Webhook registrado no painel do Mercado Pago (modo teste)
- Teste de notificação: ✅ 200 OK

### ✅ Fase 4: Geração de Link de Pagamento
- Modificado workflow principal (`revisabot_v2_switch`) para:
  - Após validação do código, definir estado `GENERATING_PAYMENT`
  - Disparar webhook interno para gerar link de pagamento
  - Enviar mensagem "Estamos gerando seu link de pagamento..."
- Criado node "Trigger Payment Workflow" no workflow principal
- Workflow de pagamento gera link via API Mercado Pago
- Link sandbox enviado via WhatsApp com instruções de teste

### ✅ Fase 5: Testes End-to-End em Sandbox
- **Teste realizado em:** 2025-12-10 03:45 UTC-3
- **Resultado:** ✅ SUCESSO
- **Fluxo testado:**
  1. Usuário valida código de email → ✅
  2. Webhook interno dispara geração de link → ✅
  3. API Mercado Pago cria preferência → ✅
  4. Link sandbox salvo no banco → ✅
  5. Mensagem WhatsApp enviada com link → ✅
  6. Usuário acessa link sandbox → ✅
  7. Login com usuário de teste → ✅
  8. Pagamento simulado → ✅
  9. Webhook de notificação recebido → ✅

#### Fluxo Completo do Workflow Unificado:

**Fluxo 1: Geração de Link**
```
Generate Link Webhook (POST /generate-payment-link)
        ↓
Generate Payment Link (POST /checkout/preferences)
        ↓
Save Payment Link (PostgreSQL)
        ↓
Send Payment Link WA (WhatsApp)
```

**Fluxo 2: Notificação de Pagamento**
```
MP Webhook Trigger (POST /mercadopago-notification)
        ↓
Respond OK to MP (200)
        ↓
Filter Payment Events (type = payment)
        ↓
Get Payment Details (GET /v1/payments/{id})
        ↓
Process Payment Status (mapeia status → estado)
        ↓
Update Payment Status (PostgreSQL)
        ↓
Send WhatsApp Notification
```

#### Mapeamento de Status:
| Status MP | Estado Workflow | Ação |
|-----------|-----------------|------|
| approved | PAYMENT_APPROVED | Envia confirmação |
| rejected | PAYMENT_REJECTED | Oferece retry |
| pending | PAYMENT_PENDING | Informa análise |
| cancelled | PAYMENT_REJECTED | Oferece retry |
| refunded | PAYMENT_REFUNDED | Informa reembolso |

### ⏳ Pendente para Produção
- Trocar credenciais de sandbox para produção
- Atualizar link de `sandbox_init_point` para `init_point`
- Remover instruções de teste da mensagem WhatsApp
- Monitorar primeiras transações reais

---

## Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `plano_implantacao.md` | Plano detalhado de implementação |
| `assessment_riscos.md` | Análise de riscos e mitigações |
| `migrations/001_add_payment_columns.sql` | Script SQL de migração |
| `migrations/credenciais_mercado_pago.env` | Credenciais (não commitar) |
| `usuario_teste.md` | Dados do usuário de teste Mercado Pago |
| `CHANGELOG.md` | Este arquivo |

---

## Configurações Importantes

### Workflows n8n

#### Workflow Principal (revisabot_v2_switch)
- **Workflow ID:** `bXqi8RykpGxXMBGE`
- **Webhook WhatsApp:** `https://n8n.srv987902.hstgr.cloud/webhook/whatsapp-beta-agent`
- **Node adicionado:** "Trigger Payment Workflow" - dispara geração de link após validação do código

#### Workflow Mercado Pago Unified
- **Workflow ID:** `6COT3ubybyI8QhYT`
- **Webhook Notificação:** `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification`
- **Webhook Geração Link:** `https://n8n.srv987902.hstgr.cloud/webhook/generate-payment-link`
- **Método:** POST
- **Autenticação:** None (validação via assinatura no código)

### Credenciais MP (Sandbox)
- **Public Key:** `APP_USR-14a86ba5-7347-4043-bebd-2687b6ec0f3a`
- **Access Token:** `APP_USR-7529371852440001-120923-fb2daa06020e5080dc223d79a64763b0-3052968619`
- **Credencial n8n:** "Mercado Pago API" (Header Auth com Bearer token)

### Usuário de Teste (Buyer)
- **User ID:** `3052968623`
- **Usuário:** `TESTUSER4040337204379755480`
- **Senha:** `PBcaoS1YWo`
- **Código de verificação:** Últimos 6 dígitos do User ID (`968623`)

### Cartões de Teste
| Resultado | Nome do Titular | CPF |
|-----------|-----------------|-----|
| Aprovado | APRO | 12345678909 |
| Recusado | OTHE | 12345678909 |
| Pendente | CONT | 12345678909 |

### Banco de Dados
- **Tabela:** `consultas_esaj`
- **Conexão:** Via credencial "Postgres account" existente
- **Colunas de pagamento:** mp_preference_id, mp_payment_id, mp_payment_status, payment_link, etc.
