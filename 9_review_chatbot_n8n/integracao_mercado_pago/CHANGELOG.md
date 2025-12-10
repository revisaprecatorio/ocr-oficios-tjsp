# Changelog - Integração Mercado Pago

## [2025-12-10] Fase 1-3 Implementadas

### ✅ Fase 1: Migração do Banco de Dados
- Adicionadas 8 novas colunas na tabela `consultas_esaj`:
  - `mp_preference_id` - ID da preferência de pagamento
  - `mp_payment_id` - ID do pagamento confirmado
  - `mp_payment_status` - Status do pagamento (approved, rejected, pending)
  - `mp_payment_amount` - Valor do pagamento
  - `mp_external_reference` - Referência externa (whatsapp_cpf_timestamp)
  - `payment_link` - Link de pagamento gerado
  - `payment_created_at` - Data de criação do link
  - `payment_confirmed_at` - Data de confirmação do pagamento
- Criados 4 índices para performance de busca

### ✅ Fase 2: Credenciais
- Criada credencial "Mercado Pago API" no n8n (Header Auth)
- Tipo: Bearer Token
- Ambiente: Sandbox/Teste

### ✅ Fase 3: Webhook de Notificações
- Criado workflow separado: **MP Payment Webhook** (ID: `6COT3ubybyI8QhYT`)
- URL de produção: `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification`
- Webhook registrado no painel do Mercado Pago (modo teste)
- Teste de notificação: ✅ 200 OK

#### Fluxo do Webhook:
```
MP Webhook Trigger → Respond OK (200)
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

### ⏳ Fase 4: Pendente
- Modificar workflow principal para gerar link de pagamento
- Integrar após validação do código de email

### ⏳ Fase 5: Pendente
- Testes end-to-end em sandbox
- Validação completa do fluxo

---

## Arquivos Criados

| Arquivo | Descrição |
|---------|-----------|
| `plano_implantacao.md` | Plano detalhado de implementação |
| `assessment_riscos.md` | Análise de riscos e mitigações |
| `migrations/001_add_payment_columns.sql` | Script SQL de migração |
| `migrations/credenciais_mercado_pago.env` | Credenciais (não commitar) |
| `CHANGELOG.md` | Este arquivo |

---

## Configurações Importantes

### Webhook n8n
- **Workflow ID:** `6COT3ubybyI8QhYT`
- **Path:** `mercadopago-notification`
- **Método:** POST
- **Autenticação:** None (validação via assinatura no código)

### Credenciais MP (Sandbox)
- **Public Key:** `APP_USR-14a86ba5-7347-4043-bebd-2687b6ec0f3a`
- **Access Token:** Configurado no n8n como "Mercado Pago API"

### Banco de Dados
- **Tabela:** `consultas_esaj`
- **Conexão:** Via credencial "Postgres account" existente
