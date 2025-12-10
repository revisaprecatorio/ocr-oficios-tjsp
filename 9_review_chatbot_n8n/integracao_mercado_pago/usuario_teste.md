# Usuário de Teste - Mercado Pago

## Buyer Test User (Comprador)

| Campo | Valor |
|-------|-------|
| **País** | Brasil |
| **User ID** | `3052968623` |
| **Usuário** | `TESTUSER4040337204379755480` |
| **Senha** | `PBcaoS1YWo` |
| **Código de verificação** | `968623` (últimos 6 dígitos do User ID) |

---

## Como usar para testes

1. Acesse o link sandbox gerado pelo sistema
2. Faça login com o usuário e senha acima
3. Quando pedir código de verificação, use: `968623`
4. Na tela de pagamento, use um cartão de teste

---

## Cartões de Teste

| Resultado | Nome do Titular | CPF | Número do Cartão |
|-----------|-----------------|-----|------------------|
| **Aprovado** | `APRO` | `12345678909` | `5031 4332 1540 6351` (Mastercard) |
| **Recusado** | `OTHE` | `12345678909` | Qualquer cartão de teste |
| **Pendente** | `CONT` | `12345678909` | Qualquer cartão de teste |

**CVV:** `123`  
**Validade:** Qualquer data futura (ex: `11/25`)

---

## Seller Test User (Vendedor)

| Campo | Valor |
|-------|-------|
| **User ID** | `3052968619` |
| **Aplicação** | `revisa-dev` |

---

## Teste Realizado

- **Data:** 2025-12-10 03:45 UTC-3
- **Resultado:** Pagamento simulado com sucesso
- **Payment ID:** `1343069867`
- **Webhook recebido:** `payment.created`
