# RevisaBot v2 - Switch State Machine

Bot de WhatsApp para consulta de precatórios no sistema e-SAJ do TJSP.

## Versão Atual: Stable 2025-12-09

### Funcionalidades
- ✅ Consulta de precatórios por CPF no e-SAJ
- ✅ Extração automática do nome do requerente
- ✅ Listagem de processos encontrados
- ✅ Fluxo de verificação de email com código
- ✅ Máquina de estados para controle de conversação

### Arquitetura

```
WhatsApp → Webhook → Process Input → Get User State → Merge State → Route Message Type
                                                                          ↓
                                                            [Switch por tipo de mensagem]
                                                                          ↓
                                          ┌─────────────────────────────────────────────────┐
                                          │ CPF → Consulta e-SAJ → Parse → Save Consulta   │
                                          │ EMAIL → Generate Code → Send Email             │
                                          │ CODE → Validate Code                           │
                                          │ CONFIRM_YES/NO → Response                      │
                                          │ MENU/INFO/CONSULTAR → Response                 │
                                          └─────────────────────────────────────────────────┘
                                                                          ↓
                                                              Update State → Send WhatsApp
```

### Estados da Máquina

| Estado | Descrição | Timeout |
|--------|-----------|---------|
| `IDLE` | Aguardando interação inicial | - |
| `AWAITING_CONFIRMATION` | Aguardando "sim" ou "não" após consulta CPF | 30 min |
| `AWAITING_EMAIL` | Aguardando email do usuário | 30 min |
| `AWAITING_CODE` | Aguardando código de verificação | 15 min |
| `AWAITING_PAYMENT` | Aguardando confirmação de pagamento | 60 min |

### Nodes Principais

| Node | Função |
|------|--------|
| `Get User State` | Busca estado atual do usuário (ordenado por `state_updated_at`) |
| `Route Message Type` | Switch que roteia mensagem baseado em regex e estado |
| `Consulta e-SAJ` | HTTP Request para API do e-SAJ |
| `Parse e-SAJ Response` | Extrai nome, processos e formata resposta |
| `Save Consulta` | Persiste dados da consulta no PostgreSQL (UPSERT) |
| `Update State` | Atualiza estado da conversação |

### Banco de Dados

Tabela: `consultas_esaj`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `whatsapp_from` | VARCHAR | Número do WhatsApp |
| `cpf` | VARCHAR | CPF consultado |
| `nome_requerente` | VARCHAR | Nome extraído do e-SAJ |
| `processos` | JSONB | Array de processos |
| `total_processos` | INTEGER | Quantidade de processos |
| `resposta_formatada` | TEXT | Resposta enviada ao usuário |
| `current_state` | VARCHAR | Estado atual da máquina |
| `state_updated_at` | TIMESTAMP | Última atualização de estado |
| `email` | VARCHAR | Email do usuário |
| `verification_code` | VARCHAR | Código de verificação |

### Arquivos

```
revisabot_v2_switch/
├── workflows/
│   ├── revisabot_v2_switch_stable_2025_12_09.json  # Versão estável atual
│   ├── revisabot_v2_switch_checkpoint_2025_12_09.json
│   └── revisabot_v2_switch_2025_12_08.json
├── README.md
└── CHANGELOG.md
```

### Credenciais Necessárias

- **Postgres account** (`b0F0gRzrpEq6BR3M`)
- **WhatsApp account** (`ejhZtEKHF0Kh9HeQ`)
- **SMTP** (para envio de emails)

### Workflow ID

- **Produção**: `bXqi8RykpGxXMBGE`
