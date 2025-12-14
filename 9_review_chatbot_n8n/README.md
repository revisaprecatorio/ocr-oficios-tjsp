# RevisaBot - Sistema de Consulta de Precatórios

Sistema automatizado de consulta de precatórios no e-SAJ do TJSP via WhatsApp, com integração de pagamentos via Mercado Pago.

## Visão Geral

O RevisaBot é um chatbot de WhatsApp que permite aos usuários consultar processos de precatórios usando seu CPF. O sistema extrai automaticamente informações do portal e-SAJ do Tribunal de Justiça de São Paulo, gerencia o fluxo de conversação através de uma máquina de estados, e processa pagamentos via Mercado Pago.

## Arquitetura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    WhatsApp     │────▶│  n8n Workflows   │────▶│    PostgreSQL   │
│   (Meta API)    │◀────│                  │◀────│                 │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                        ┌────────┴─────────┐
                        │                  │
                        ▼                  ▼
               ┌─────────────┐    ┌─────────────────┐
               │   e-SAJ     │    │  Mercado Pago   │
               │    TJSP     │    │      API        │
               └─────────────┘    └─────────────────┘
```

## Estrutura do Projeto

```
9_review_chatbot_n8n/
├── README.md                      # Este arquivo
├── revisabot_v2_switch/           # Workflow principal do bot
│   ├── workflows/                 # Versões do workflow
│   ├── README.md                  # Documentação detalhada
│   └── CHANGELOG.md               # Histórico de alterações
├── integracao_mercado_pago/       # Integração de pagamentos
│   ├── integracao_mercado_pago.md # Guia de integração
│   ├── plano_implantacao.md       # Plano de implantação
│   ├── assessment_riscos.md       # Análise de riscos
│   ├── migrations/                # Migrações de banco
│   └── CHANGELOG.md               # Histórico
└── tests_workflows/               # Workflows de teste
    ├── CPF_batch_processing.json  # Workflow de teste batch
    ├── batch_test_cpfs.sh         # Script de teste em lote
    └── README.md                  # Documentação de testes
```

## Evolução do Sistema

### Fase 1: RevisaBot v2 Switch (revisabot_v2_switch/)

**Objetivo:** Criar um bot de WhatsApp funcional para consulta de precatórios.

**Principais funcionalidades:**
- Máquina de estados para controle de conversação
- Consulta ao e-SAJ do TJSP por CPF
- Extração automática de nome e processos
- Verificação de email com código de 6 dígitos
- Persistência em PostgreSQL com UPSERT

**Workflow principal:** `bXqi8RykpGxXMBGE`

**Estados da máquina:**
| Estado | Descrição |
|--------|-----------|
| `IDLE` | Aguardando interação |
| `AWAITING_CONFIRMATION` | Aguardando confirmação |
| `AWAITING_EMAIL` | Aguardando email |
| `AWAITING_CODE` | Aguardando código |
| `GENERATING_PAYMENT` | Gerando link |
| `AWAITING_PAYMENT` | Aguardando pagamento |
| `PAYMENT_APPROVED` | Pagamento confirmado |

### Fase 2: Integração Mercado Pago (integracao_mercado_pago/)

**Objetivo:** Monetizar o serviço com pagamentos online.

**Principais funcionalidades:**
- Geração dinâmica de links de pagamento
- Webhook para receber notificações do Mercado Pago
- Atualização automática de status no banco
- Envio de confirmação via WhatsApp

**Workflow:** `Mercado Pago Unified` (`6COT3ubybyI8QhYT`)

**Webhooks:**
| Endpoint | Função |
|----------|--------|
| `/webhook/generate-payment-link` | Gera link de pagamento |
| `/webhook/mercadopago-notification` | Recebe notificações |

**Documentação incluída:**
- Guia passo a passo de integração
- Assessment de riscos
- Plano de implantação
- Migrações de banco de dados

### Fase 3: Workflows de Teste (tests_workflows/)

**Objetivo:** Validar parsing do e-SAJ e testar em lote.

**Principais funcionalidades:**
- Workflow simplificado `CPF_batch_processing`
- Script bash para teste em lote (`batch_test_cpfs.sh`)
- Parser otimizado para página única e lista de processos

**Workflow:** `CPF_batch_processing` (`jMzstMZfztUMz7O6`)

**Regex para parsing e-SAJ:**

*Página de Lista:*
```javascript
// Nome
/class="[^"]*nomeParte[^"]*"[^>]*>\s*([^<]+)/i

// Número do processo
/class="linkProcesso"[^>]*>\s*(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/i

// Classe
/class="classeProcesso"[^>]*>([^<]+)/i
```

*Página Única:*
```javascript
// Nome
/nomeParteEAdvogado[^>]*>[\s\n]*([A-ZÀ-Ú][A-Za-zÀ-ÿ\s]+?)(?:\s*<br|\s*Advogad)/i

// Classe
/id="classeProcesso"[^>]*>([^<]+)/i
```

## Workflows n8n

| Workflow | ID | Webhook | Função |
|----------|-----|---------|--------|
| **revisabot_v2_switch** | `bXqi8RykpGxXMBGE` | `/webhook/whatsapp-beta-agent` | Bot principal |
| **Mercado Pago Unified** | `6COT3ubybyI8QhYT` | `/webhook/generate-payment-link` | Pagamentos |
| **CPF_batch_processing** | `jMzstMZfztUMz7O6` | `/webhook/cpf-batch-processing` | Testes |

## Banco de Dados

**Tabela:** `consultas_esaj`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `whatsapp_from` | VARCHAR | Número do WhatsApp |
| `cpf` | VARCHAR | CPF consultado |
| `nome_requerente` | VARCHAR | Nome extraído |
| `processos` | JSONB | Array de processos |
| `total_processos` | INTEGER | Quantidade |
| `current_state` | VARCHAR | Estado atual |
| `email` | VARCHAR | Email do usuário |
| `verification_code` | VARCHAR | Código de verificação |
| `mp_payment_id` | VARCHAR | ID do pagamento MP |
| `mp_payment_status` | VARCHAR | Status do pagamento |
| `mp_payment_amount` | DECIMAL | Valor do pagamento |

**Constraint:** `UNIQUE (whatsapp_from, cpf)`

## Credenciais Necessárias

| Credencial | ID | Tipo |
|------------|-----|------|
| Postgres account | `b0F0gRzrpEq6BR3M` | PostgreSQL |
| WhatsApp account | `ejhZtEKHF0Kh9HeQ` | Meta API |
| Mercado Pago API | `KytrAZe3o5ngsDTa` | Header Auth |
| SMTP | - | Email |

## Testes

### Teste unitário (um CPF):
```bash
curl -X POST https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing \
  -H "Content-Type: application/json" \
  -d '{"cpf": "08212993876"}' | jq .
```

### Teste em lote:
```bash
cd tests_workflows/
./batch_test_cpfs.sh
```

## Infraestrutura

- **n8n:** `https://n8n.srv987902.hstgr.cloud`
- **Servidor:** Hostinger VPS
- **Banco:** PostgreSQL

## Changelog

### 2025-12-14
- Corrigido parser para extrair nomes de páginas de lista do e-SAJ
- Implementados regex específicos para classes CSS do e-SAJ
- 100% de sucesso em batch test com 12 CPFs

### 2025-12-11
- Integração Mercado Pago concluída
- Workflow unificado para geração de links e notificações

### 2025-12-09
- Versão estável do revisabot_v2_switch
- Máquina de estados funcional
- Save Consulta com UPSERT

---

**Revisa Precatório** - Sistema de Gestão de Precatórios
