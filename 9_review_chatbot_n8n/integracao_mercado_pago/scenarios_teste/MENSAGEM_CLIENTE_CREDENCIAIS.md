# Mensagem para Cliente - Credenciais Mercado Pago

**Data:** 14/12/2025  
**Assunto:** Credenciais de Produção do Mercado Pago

---

## Mensagem (copiar e enviar):

---

Olá!

Estamos finalizando a integração de pagamento do sistema e identificamos que as credenciais atuais do Mercado Pago são de uma **conta de teste** (sandbox), não de produção.

Para que o sistema possa **receber pagamentos reais**, precisamos das credenciais da **conta oficial/real** do Mercado Pago da empresa.

### Como obter as credenciais corretas:

1. Acesse sua conta do Mercado Pago: https://www.mercadopago.com.br
2. Vá em: **Seu negócio → Configurações → Credenciais**
   - Ou acesse diretamente: https://www.mercadopago.com.br/settings/account/credentials
3. Na seção **"Credenciais de produção"**, copie:
   - **Public Key** (começa com `APP_USR-`)
   - **Access Token** (começa com `APP_USR-`)

### Importante:
- A conta deve ser a mesma que vai **receber** os pagamentos
- As credenciais devem ser de **produção**, não de teste
- Não compartilhe via meios não seguros (prefira email criptografado ou mensagem direta)

Assim que tivermos essas credenciais, conseguiremos finalizar a integração e liberar o sistema para receber pagamentos via Pix, cartão de crédito e boleto.

Qualquer dúvida, estou à disposição.

Abraço!

---

## Contexto Técnico (para referência interna):

**Problema identificado:**
- As credenciais fornecidas (`APP_USR-2720776717...`) apontam para uma conta de teste
- Evidência: GET /users/me retorna `"nickname": "TESTUSER..."` e `"tags": ["test_user"]`

**O que esperamos receber:**
- Credenciais de uma conta **real** do Mercado Pago
- GET /users/me deve retornar o nome/email real do cliente, não "TESTUSER"

**Após receber:**
1. Testar via cURL: `curl -s https://api.mercadopago.com/users/me -H "Authorization: Bearer <TOKEN>"`
2. Verificar que retorna dados reais (não TESTUSER)
3. Atualizar credencial no n8n (id: `KytrAZe3o5ngsDTa`)
4. Executar cenários de teste de pagamento
