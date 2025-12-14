# 🧪 Plano de Testes - Mercado Pago (Sem Acesso ao Painel)

**Data:** 14/12/2025  
**Última atualização:** 14/12/2025 19:40  
**Status:** ⏸️ BLOQUEADO - Aguardando credenciais de produção REAIS do cliente

---

## ⚠️ PRÉ-REQUISITO CRÍTICO (Descoberto em 14/12/2025)

### Problema Identificado
As credenciais atuais (`APP_USR-2720776717...`) apontam para uma **CONTA DE TESTE**, não de produção real.

**Evidência:**
```bash
curl -s https://api.mercadopago.com/users/me -H "Authorization: Bearer APP_USR-2720776717..."
# Retorna: "nickname": "TESTUSER8958288310358810898", "tags": ["test_user"]
```

### Por que isso bloqueia os testes?
- O prefixo `APP_USR-` parece ser de produção ✅
- Mas a CONTA associada é de teste ❌
- Resultado: erro *"Uma das partes com as quais você está tentando efetuar o pagamento é de teste"*

### O que precisa acontecer ANTES de executar os cenários:
1. **Cliente deve fornecer credenciais da conta REAL do MP**
   - Acessar: https://www.mercadopago.com.br/settings/account/credentials
   - Copiar Public Key e Access Token de PRODUÇÃO
2. **Validar novas credenciais:**
   ```bash
   curl -s https://api.mercadopago.com/users/me -H "Authorization: Bearer <NOVO_TOKEN>" | jq .nickname
   # Deve retornar nome real (não TESTUSER)
   ```
3. **Atualizar credencial no n8n** (id: `KytrAZe3o5ngsDTa`)

**Mensagem para cliente:** Ver arquivo `MENSAGEM_CLIENTE_CREDENCIAIS.md`

---

## Escopo: O que podemos fazer SEM o painel MP

| ✅ Podemos fazer | ❌ Não podemos fazer |
|------------------|---------------------|
| Verificar credencial no n8n | Ativar credenciais de produção |
| Alterar valor do pagamento | Registrar webhook no painel |
| Testar geração de link | Verificar status da aplicação |
| Testar webhook recebendo | Habilitar/desabilitar métodos |
| Analisar logs de erro | Solicitar estorno |
| Fazer pagamento real (Pix/cartão) | Verificar limites da conta |

---

## 📋 Cenários de Teste

### Cenário 0: Validação das Credenciais do Cliente (PRÉ-REQUISITO)
**Objetivo:** Confirmar que as novas credenciais são de conta REAL (não de teste)

**Passos:**
1. [ ] Receber novas credenciais do cliente
2. [ ] Testar via cURL:
   ```bash
   curl -s https://api.mercadopago.com/users/me -H "Authorization: Bearer <NOVO_TOKEN>" | jq '{nickname, email, tags}'
   ```
3. [ ] Verificar resultado:
   - ✅ **Conta REAL:** nickname é nome normal, email é real, sem tag "test_user"
   - ❌ **Conta TESTE:** nickname = "TESTUSER...", email = "test_user_...@testuser.com"

**Resultado:**
```
Nickname: ________________________________
Email: ________________________________
Tags: ________________________________
Tipo: [ ] Conta REAL ✅ / [ ] Conta de TESTE ❌
```

⚠️ **SÓ PROSSIGA para os cenários seguintes se for CONTA REAL**

---

### Cenário 1: Atualização da Credencial no n8n
**Objetivo:** Atualizar a credencial com o token de produção REAL

**Pré-requisito:** Cenário 0 passou (conta real confirmada)

**Passos:**
1. [ ] Acessar n8n: https://n8n.srv987902.hstgr.cloud
2. [ ] Ir em: Settings → Credentials → `Mercado Pago API` (id: `KytrAZe3o5ngsDTa`)
3. [ ] Atualizar o Access Token com o novo valor
4. [ ] Salvar credencial
5. [ ] Testar conexão (se disponível)

**Resultado:**
```
Credencial atualizada: [ ] Sim / [ ] Não
Teste de conexão: [ ] OK / [ ] Falhou
```

---

### Cenário 2: Teste de Geração de Link (valor R$ 5,00)
**Objetivo:** Validar se o workflow gera link com valor maior

**Pré-requisito:** Alterar `unit_price` de `1.00` para `5.00` no workflow

**Passos:**
1. [ ] Alterar valor no node `Generate Payment Link`
2. [ ] Executar chamada de teste:
```bash
curl -X POST https://n8n.srv987902.hstgr.cloud/webhook/generate-payment-link \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_payment": true,
    "whatsapp_from": "5511999999999",
    "email": "teste@teste.com"
  }'
```
3. [ ] Verificar resposta (deve retornar `init_point`)
4. [ ] Abrir o link gerado

**Resultado:**
```
Link gerado: [ ] Sim / [ ] Não
URL: ________________________________
Erro (se houver): ________________________________
```

---

### Cenário 3: Teste de Pagamento Real (Pix)
**Objetivo:** Fazer um pagamento real via Pix para validar fluxo completo

**IMPORTANTE:** Use uma conta bancária DIFERENTE da conta que recebe (não pode ser a mesma pessoa/CPF vinculado ao MP vendedor)

**Passos:**
1. [ ] Gerar link de pagamento (Cenário 2)
2. [ ] Abrir link no celular
3. [ ] Selecionar "Pix" como forma de pagamento
4. [ ] Copiar código Pix ou escanear QR code
5. [ ] Pagar pelo app do banco (conta diferente!)
6. [ ] Aguardar até 30 segundos
7. [ ] Verificar se webhook foi recebido no n8n

**Resultado:**
```
Pagamento: [ ] Aprovado / [ ] Rejeitado / [ ] Pendente
Webhook recebido: [ ] Sim / [ ] Não
Status no banco: ________________________________
Erro (se houver): ________________________________
```

---

### Cenário 4: Teste de Pagamento Real (Cartão de Crédito)
**Objetivo:** Fazer um pagamento real via cartão para validar fluxo completo

**IMPORTANTE:** Use um cartão de crédito que NÃO esteja vinculado à conta MP vendedora

**Passos:**
1. [ ] Gerar link de pagamento (Cenário 2)
2. [ ] Abrir link no celular ou desktop
3. [ ] Selecionar "Cartão de crédito" como forma de pagamento
4. [ ] NÃO fazer login no Mercado Pago (pagar como convidado)
5. [ ] Preencher dados do cartão
6. [ ] Confirmar pagamento
7. [ ] Verificar se webhook foi recebido no n8n

**Resultado:**
```
Pagamento: [ ] Aprovado / [ ] Rejeitado / [ ] Pendente
Webhook recebido: [ ] Sim / [ ] Não
Status no banco: ________________________________
Erro (se houver): ________________________________
```

---

### Cenário 5: Verificação do Webhook
**Objetivo:** Confirmar que o webhook está acessível externamente

**Passos:**
1. [ ] Testar acesso ao webhook:
```bash
curl -X POST https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification \
  -H "Content-Type: application/json" \
  -d '{"type": "payment", "data": {"id": "123456789"}}'
```
2. [ ] Verificar no n8n se a execução apareceu

**Resultado:**
```
Webhook acessível: [ ] Sim / [ ] Não
Execução no n8n: [ ] Sim / [ ] Não
Resposta HTTP: ________________________________
```

---

### Cenário 6: Análise de Logs de Erro
**Objetivo:** Verificar execuções anteriores para identificar padrões de erro

**Passos:**
1. [ ] Acessar n8n → Executions
2. [ ] Filtrar por workflow `Mercado Pago Unified`
3. [ ] Analisar as últimas 10 execuções com erro
4. [ ] Documentar padrões

**Resultado:**
```
Execuções analisadas: ____
Padrão de erro mais comum: ________________________________
Mensagem de erro típica: ________________________________
```

---

## 📝 Ordem de Execução Recomendada

```
┌─────────────────────────────────────────────────────────────┐
│  0. Cenário 0: Validar credenciais do cliente (5 min)       │
│     ↓  ⚠️ BLOQUEANTE - só prossiga se conta for REAL        │
│  1. Cenário 1: Atualizar credencial no n8n (5 min)          │
│     ↓                                                        │
│  2. Cenário 5: Testar webhook acessível (2 min)             │
│     ↓                                                        │
│  3. Alterar valor para R$ 5,00 no workflow                  │
│     ↓                                                        │
│  4. Cenário 2: Gerar link de teste (5 min)                  │
│     ↓                                                        │
│  5. Cenário 3 OU 4: Pagamento real (10 min)                 │
│     ↓                                                        │
│  6. Cenário 6: Analisar logs se houver erro                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Alterações Necessárias no Workflow

### Alteração 1: Valor do Pagamento
**Node:** `Generate Payment Link`  
**Campo:** `unit_price`  
**De:** `1.00`  
**Para:** `5.00`

### Alteração 2 (Opcional): Timeout do Webhook
Se necessário aumentar timeout para debug.

---

## ⚠️ Pré-requisitos para Pagamento Real

1. **Para Pix:**
   - Conta bancária diferente da vinculada ao MP vendedor
   - Saldo disponível de R$ 5,00

2. **Para Cartão:**
   - Cartão de crédito não vinculado à conta MP vendedora
   - Limite disponível de R$ 5,00
   - Preferencialmente de outra pessoa ou cartão corporativo

---

## 📊 Resultado Final

| Cenário | Status | Observação |
|---------|--------|------------|
| 0. Credenciais Cliente | [ ] OK / [ ] FALHA | ⚠️ Aguardando novas credenciais |
| 1. Atualização n8n | [ ] OK / [ ] FALHA | |
| 2. Geração Link | [ ] OK / [ ] FALHA | |
| 3. Pagamento Pix | [ ] OK / [ ] FALHA | |
| 4. Pagamento Cartão | [ ] OK / [ ] FALHA | |
| 5. Webhook | [ ] OK / [ ] FALHA | |
| 6. Logs | [ ] OK / [ ] FALHA | |

---

## 🎯 Critérios de Sucesso

**Integração APROVADA se:**
- [ ] Credenciais são de conta REAL (não TESTUSER)
- [ ] Credencial atualizada no n8n
- [ ] Link é gerado com sucesso
- [ ] Pagamento (Pix ou Cartão) é aprovado
- [ ] Webhook é recebido e processado
- [ ] Status é atualizado no banco de dados

**Próximos passos após sucesso:**
1. Ajustar valor para o real (ex: R$ 49,90)
2. Documentar na memória Byterover
3. Commit das alterações

---

## 📚 Arquivos Relacionados

- `ASSESSMENT_MERCADO_PAGO.md` - Diagnóstico completo da integração
- `MENSAGEM_CLIENTE_CREDENCIAIS.md` - Mensagem para solicitar credenciais ao cliente
- `advanced_search.md` - Referências e documentação de pesquisa
