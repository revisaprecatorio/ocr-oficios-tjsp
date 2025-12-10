# Assessment de Riscos - Integração Mercado Pago

**Data:** 2025-12-10  
**Autor:** Cascade AI  
**Projeto:** RevisaBot v2 - Integração de Pagamentos

---

## 1. Contexto

Este documento analisa os riscos técnicos e operacionais da integração do Mercado Pago ao workflow RevisaBot v2, com foco em garantir a estabilidade do fluxo existente.

---

## 2. Análise do Workflow Atual

### 2.1 Pontos de Integração

O pagamento será integrado **após** a validação do código de email:

```
[Validate Code] ──✅──> [Create MP Preference] ──> [Update State] ──> [Send WhatsApp]
                                │
                                ▼
                    [MP Webhook Trigger] ──> [Process Notification] ──> [Update State] ──> [Send WhatsApp]
```

### 2.2 Dependências Críticas

| Componente | Dependência | Criticidade |
|------------|-------------|-------------|
| Validate Code | Merge State (stored_email) | 🔴 Alta |
| Create MP Preference | API Mercado Pago | 🔴 Alta |
| MP Webhook | Conectividade n8n | 🔴 Alta |
| Update State | PostgreSQL | 🔴 Alta |
| Send WhatsApp | WhatsApp API | 🔴 Alta |

---

## 3. Matriz de Riscos

### 3.1 Riscos Técnicos

| ID | Risco | Prob. | Impacto | Score | Mitigação |
|----|-------|-------|---------|-------|-----------|
| T1 | API MP indisponível | 🟡 Média | 🔴 Alto | 8 | Retry com backoff + fallback manual |
| T2 | Webhook não recebido | 🟡 Média | 🔴 Alto | 8 | Polling de fallback a cada 5min |
| T3 | Timeout na criação de preferência | 🟢 Baixa | 🟡 Médio | 4 | Timeout de 30s + retry |
| T4 | Resposta MP malformada | 🟢 Baixa | 🟡 Médio | 4 | Validação de schema + log |
| T5 | Webhook duplicado | 🟡 Média | 🟢 Baixo | 3 | Idempotência via payment_id |
| T6 | Estado inconsistente no DB | 🟢 Baixa | 🔴 Alto | 6 | Transações + verificação |

### 3.2 Riscos de Integração

| ID | Risco | Prob. | Impacto | Score | Mitigação |
|----|-------|-------|---------|-------|-----------|
| I1 | Conflito com webhook WhatsApp | 🟢 Baixa | 🔴 Alto | 6 | Webhooks separados |
| I2 | Quebra do fluxo existente | 🟢 Baixa | 🔴 Alto | 6 | Feature flag + rollback |
| I3 | Perda de contexto do usuário | 🟡 Média | 🟡 Médio | 6 | external_reference com whatsapp_from |
| I4 | Múltiplos pagamentos mesmo CPF | 🟡 Média | 🟡 Médio | 6 | Verificar status antes de gerar link |

### 3.3 Riscos de Segurança

| ID | Risco | Prob. | Impacto | Score | Mitigação |
|----|-------|-------|---------|-------|-----------|
| S1 | Webhook spoofing | 🟡 Média | 🔴 Alto | 8 | Validar x-signature do MP |
| S2 | Token exposto em logs | 🟢 Baixa | 🔴 Alto | 6 | Usar credenciais n8n |
| S3 | Replay attack | 🟢 Baixa | 🟡 Médio | 4 | Verificar payment_id único |
| S4 | Man-in-the-middle | 🟢 Baixa | 🔴 Alto | 6 | HTTPS obrigatório |

### 3.4 Riscos de UX

| ID | Risco | Prob. | Impacto | Score | Mitigação |
|----|-------|-------|---------|-------|-----------|
| U1 | Link não enviado | 🟢 Baixa | 🔴 Alto | 6 | Retry + log + alerta |
| U2 | Pagamento sem confirmação | 🟡 Média | 🔴 Alto | 8 | Webhook + polling backup |
| U3 | Link expirado | 🟡 Média | 🟡 Médio | 6 | Opção de gerar novo link |
| U4 | Usuário confuso com status | 🟡 Média | 🟢 Baixo | 3 | Mensagens claras |

---

## 4. Análise de Pontos de Quebra

### 4.1 Cenário: Falha na Criação de Preferência MP

```
[Validate Code] ──✅──> [Create MP Preference] ──❌ ERRO
```

**Impacto:** Usuário validou email mas não recebe link de pagamento.

**Mitigação:**
1. `onError: continueRegularOutput` no node
2. Verificar se `init_point` existe na resposta
3. Se falhar, enviar mensagem: "Estamos com dificuldades técnicas. Tente novamente em alguns minutos."
4. Manter estado como `AWAITING_PAYMENT` para retry

### 4.2 Cenário: Webhook MP Não Chega

```
[Usuário paga] ──> [MP processa] ──> [Webhook] ──❌ NÃO CHEGA
```

**Impacto:** Pagamento aprovado mas usuário não recebe confirmação.

**Mitigação:**
1. Implementar polling de fallback:
   - A cada 5 minutos, verificar pagamentos pendentes
   - Chamar GET `/v1/payments/search?external_reference=...`
2. Timeout de 24h para estado `AWAITING_PAYMENT`
3. Após timeout, enviar: "Não identificamos seu pagamento. Se já pagou, responda 'paguei'."

### 4.3 Cenário: Webhook Duplicado

```
[MP] ──> [Webhook 1] ──> [Processa] ──✅
[MP] ──> [Webhook 2] ──> [Processa] ──? DUPLICADO
```

**Impacto:** Mensagem duplicada para usuário ou estado corrompido.

**Mitigação:**
1. Verificar se `mp_payment_id` já existe no banco
2. Se existir e status igual, ignorar (return 200)
3. Se existir e status diferente, atualizar (transição válida)

### 4.4 Cenário: Estado Inconsistente

```
[Update State] ──> [AWAITING_PAYMENT]
[Webhook] ──> [PAYMENT_APPROVED]
[Usuário envia msg] ──> [Get User State] ──? QUAL ESTADO?
```

**Impacto:** Fluxo não sabe como responder.

**Mitigação:**
1. `Get User State` já usa `ORDER BY state_updated_at DESC`
2. Webhook atualiza `state_updated_at` ao mudar estado
3. Sempre pegar o estado mais recente

---

## 5. Estratégia de Rollback

### 5.1 Níveis de Rollback

| Nível | Trigger | Ação |
|-------|---------|------|
| 1 - Parcial | Erro em 1 transação | Retry automático |
| 2 - Node | Erros recorrentes em node | Desativar node específico |
| 3 - Feature | Múltiplos erros | Reverter Validate Code |
| 4 - Total | Quebra do fluxo | Restaurar backup do workflow |

### 5.2 Procedimento de Rollback Nível 3

1. Acessar n8n: `https://n8n.srv987902.hstgr.cloud`
2. Abrir workflow `revisabot_v2_switch`
3. Editar node `Validate Code`
4. Substituir código por versão anterior (sem MP)
5. Salvar e ativar
6. Manter webhook MP ativo para processar pagamentos em andamento

### 5.3 Backup Necessário

Antes de implementar:
```bash
# Exportar workflow atual
curl -X GET "https://n8n.srv987902.hstgr.cloud/api/v1/workflows/bXqi8RykpGxXMBGE" \
  -H "X-N8N-API-KEY: $API_KEY" \
  > backup_pre_mp_$(date +%Y%m%d).json
```

---

## 6. Testes Obrigatórios

### 6.1 Testes Unitários (por node)

| Node | Teste | Critério de Sucesso |
|------|-------|---------------------|
| Create MP Preference | Gerar link válido | `init_point` retornado |
| Create MP Preference | Falha de API | Mensagem de erro amigável |
| Process MP Notification | Pagamento aprovado | Estado = PAYMENT_APPROVED |
| Process MP Notification | Pagamento recusado | Estado = PAYMENT_REJECTED |
| Process MP Notification | Webhook duplicado | Ignorar sem erro |

### 6.2 Testes de Integração

| Cenário | Fluxo | Critério de Sucesso |
|---------|-------|---------------------|
| Happy path | CPF → sim → email → código → link → paga → confirmação | Laudo enviado |
| Pagamento recusado | ... → link → recusa → nova tentativa | Novo link gerado |
| Timeout | ... → link → 24h sem pagar | Mensagem de expiração |
| Retry webhook | ... → webhook falha → retry | Processado no retry |

### 6.3 Testes de Carga

| Métrica | Limite Aceitável |
|---------|------------------|
| Tempo de resposta MP | < 5s |
| Tempo de processamento webhook | < 2s |
| Webhooks simultâneos | 10/s |

---

## 7. Monitoramento Pós-Deploy

### 7.1 Métricas a Monitorar

| Métrica | Alerta |
|---------|--------|
| Taxa de sucesso Create MP Preference | < 95% |
| Tempo médio de resposta MP | > 5s |
| Webhooks recebidos vs pagamentos | Diferença > 5% |
| Estados AWAITING_PAYMENT > 24h | > 10 |

### 7.2 Logs Críticos

```javascript
// Adicionar em cada node crítico
console.log('🔵 [MP] Criando preferência para:', whatsapp_from, cpf);
console.log('🟢 [MP] Preferência criada:', preference_id);
console.log('🔴 [MP] Erro ao criar preferência:', error);
console.log('📥 [MP] Webhook recebido:', payment_id, status);
```

---

## 8. Decisão de Go/No-Go

### 8.1 Critérios de Go

- [ ] Todos os testes unitários passando
- [ ] Testes de integração em sandbox OK
- [ ] Backup do workflow criado
- [ ] Credenciais de produção configuradas
- [ ] Webhook URL registrada no MP
- [ ] Monitoramento configurado

### 8.2 Critérios de No-Go

- [ ] Taxa de erro em sandbox > 5%
- [ ] Tempo de resposta MP > 10s
- [ ] Webhook não chegando em sandbox
- [ ] Qualquer erro crítico não mitigado

---

## 9. Conclusão

A integração do Mercado Pago é **viável** com risco **controlado**, desde que:

1. ✅ Implementação seja feita em fases
2. ✅ Testes completos em sandbox antes de produção
3. ✅ Webhooks separados para evitar conflitos
4. ✅ Rollback plan documentado e testado
5. ✅ Monitoramento ativo nas primeiras 48h

**Recomendação:** Prosseguir com implementação seguindo o plano de fases.
