# 📋 Assessment: Integração Mercado Pago - RevisaBot

**Data:** 14/12/2025  
**Status:** Em análise para testes de produção

---

## 1. Histórico Recuperado (Byterover)

| Data | Status | Observação |
|------|--------|------------|
| 10/12/2025 | ✅ Sandbox OK | Implementação e testes em ambiente sandbox concluídos |
| 11/12/2025 | ⚠️ Produção Parcial | Credenciais de produção configuradas (`APP_USR-...`) |
| 11/12/2025 | ❌ Erro bloqueante | *"Uma das partes com as quais você está tentando efetuar o pagamento é de teste"* |

**Credenciais na memória:**
- **Public_Key:** `APP_USR-9581e9e6-2934-4e64-b549-1a730b21ec75` ✅ Produção
- **Access_Token:** `APP_USR-2720776717...` ✅ Produção

---

## 2. Análise do Workflow `Mercado Pago Unified`

**ID:** `6COT3ubybyI8QhYT`  
**Status:** Ativo  
**URL n8n:** https://n8n.srv987902.hstgr.cloud/workflow/6COT3ubybyI8QhYT

### ✅ O que está correto:

| Item | Status | Detalhe |
|------|--------|---------|
| Arquitetura | ✅ | 2 fluxos: Geração de link + Webhook de confirmação |
| Checkout Pro | ✅ | Usa `/checkout/preferences` (recomendado) |
| Webhook | ✅ | Configurado em `mercadopago-notification` |
| GET Payment | ✅ | Consulta API para confirmar status real |
| External Reference | ✅ | Usa `whatsapp_from_timestamp` para rastrear |
| Notification URL | ✅ | `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification` |

### ⚠️ Pontos de atenção:

| Item | Valor Atual | Risco |
|------|-------------|-------|
| `unit_price` | **R$ 1,00** | Motor antifraude pode recusar microtransações |
| Credencial | `KytrAZe3o5ngsDTa` | Precisa verificar se é realmente produção no n8n |

---

## 3. Diagnóstico: Por que os testes falharam?

### 🔴 Causa Principal Provável: **Mistura de Ambientes**

O erro *"Uma das partes com as quais você está tentando efetuar o pagamento é de teste"* indica:

```
┌─────────────────────────────────────────────────────────────────┐
│  VENDEDOR (sua conta)     ←→    COMPRADOR (quem paga)           │
│  ─────────────────────────────────────────────────────────────  │
│  Credencial: PRODUÇÃO     ←→    Conta: TESTE ou mesma conta     │
│                                                                  │
│  ❌ INCOMPATÍVEL - Mercado Pago bloqueia                        │
└─────────────────────────────────────────────────────────────────┘
```

### 🔴 Causas Secundárias:

1. **Valor muito baixo (R$ 1,00)**
   - Motor antifraude pode recusar microtransações
   - Comportamento repetitivo de teste é flag de risco
   - Recomendação: testar com **R$ 5,00 ou R$ 10,00** primeiro

2. **Comprador = Vendedor**
   - Se você tenta pagar usando a mesma conta que recebe, o MP bloqueia
   - Precisa usar uma conta/cartão diferente para pagar

3. **Credencial no n8n pode estar misturada**
   - A credencial `Mercado Pago API` (id: `KytrAZe3o5ngsDTa`) precisa ser verificada
   - Pode ter ficado com token de teste (`TEST-...`)

---

## 4. Checklist de Conformidade

| # | Requisito | Status | Ação |
|---|-----------|--------|------|
| 1 | Credenciais de PRODUÇÃO no n8n | ⚠️ Verificar | Confirmar que `KytrAZe3o5ngsDTa` usa `APP_USR-...` |
| 2 | Notification URL acessível | ✅ OK | `https://n8n.srv987902.hstgr.cloud/webhook/mercadopago-notification` |
| 3 | Webhook registrado no painel MP | ⏸️ Pendente | Requer acesso ao painel |
| 4 | Conta de produção ativada | ⏸️ Pendente | Requer acesso ao painel |
| 5 | Valor >= R$ 5,00 para teste | ❌ Não | Está com R$ 1,00 |
| 6 | Comprador ≠ Vendedor | ⚠️ Verificar | Usar conta/cartão diferente para pagar |
| 7 | Checkout como convidado habilitado | ⚠️ Verificar | Permite Pix/cartão sem conta MP |

---

## 5. Requisitos para Pix/Cartão sem conta MP

O Checkout Pro (que você usa) **já suporta nativamente**:

| Método | Sem conta MP | Observação |
|--------|--------------|------------|
| **Pix** | ✅ Sim | Qualquer pessoa com app de banco |
| **Cartão de crédito** | ✅ Sim | Checkout como convidado |
| **Cartão de débito** | ✅ Sim | Depende do banco/bandeira |
| **Boleto** | ✅ Sim | Qualquer pessoa |

---

## 6. Resumo Executivo

| Área | Situação | Próximo Passo |
|------|----------|---------------|
| **Workflow n8n** | ✅ Correto | Apenas ajustar valor para R$ 5,00 |
| **Arquitetura** | ✅ Correta | Checkout Pro + Webhook |
| **Credenciais** | ⚠️ A verificar | Confirmar no n8n |
| **Ambiente** | ❌ Problema | Erro indica mistura teste/produção |
| **Valor** | ⚠️ Risco | R$ 1,00 pode ser barrado por antifraude |
| **Comprador** | ⚠️ A verificar | Usar conta diferente para pagar |
