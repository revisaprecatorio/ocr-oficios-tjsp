# Passo a passo integração Mercado Pago com n8n


## 1. Configuração no Mercado Pago (Obter Credenciais)

Seguem abaixo as credencias já criadas no Mercado Pago para nossa conta de desenvolvimento:

Public_Key
APP_USR-14a86ba5-7347-4043-bebd-2687b6ec0f3a

Access_Token
APP_USR-7529371852440001-120923-fb2daa06020e5080dc223d79a64763b0-3052968619


## 2. Configuração no n8n
Adicionar o Nó:
No seu workflow do n8n, adicione um nó do tipo HTTP Request.
Renomeie para algo como Gera Link Mercado Pago.
Configurar Parâmetros do Nó:
Method: POST
URL: https://api.mercadopago.com/checkout/preferences
Authentication: Selecione Generic Credential Type.
Generic Auth Type: Escolha Header Auth.
Criar a Credencial no n8n:
Em Credential for Header Auth, selecione Create New.
Name: Authorization (Exatamente assim).
Value: Bearer SEU_ACCESS_TOKEN_AQUI (Escreva a palavra "Bearer", dê um espaço e cole o token copiado no passo 1).
Exemplo: Bearer TEST-123456-7890...
Clique em Save.
Configurar o Corpo da Requisição (JSON):
De volta ao nó HTTP Request:
Send Body: Ative essa opção (Toggle ON).
Body Content Type: Selecione JSON.
Specify Body: Selecione Using JSON.
No campo de texto que abrir, cole o seguinte JSON (adaptado do vídeo):

```json
{
  "items": [
    {
      "title": "Pedido Delivery",
      "description": "Pedido gerado via n8n",
      "picture_url": "http://www.myapp.com/myimage.jpg",
      "category_id": "food",
      "quantity": 1,
      "currency_id": "BRL",
      "unit_price": 34.00
    }
  ],
  "payer": {
    "email": "test_user_123456@testuser.com"
  },
  "back_urls": {
    "success": "https://www.google.com.br",
    "failure": "http://www.failure.com",
    "pending": "http://www.pending.com"
  },
  "auto_return": "approved",
  "notification_url": "https://seu-webhook-n8n.com/pagamento"
}
```


Dica Importante (Dinâmica): No tutorial que consultei, ele altera o valor fixo 34.00 para uma expressão dinâmica. Se você tiver o valor vindo de um nó anterior (como uma IA ou planilha), clique na engrenagem ao lado do campo JSON, selecione "Add Expression" e substitua o valor 34.00 pela variável do seu fluxo, exemplo: {{ $json.valor_total }}.


# 3. Testando e Diferença entre Sandbox e Produção
Ao executar o nó (clicando em "Execute Node"), o Mercado Pago retornará um JSON. Os campos mais importantes são:
init_point: Link oficial de pagamento (Produção).
sandbox_init_point: Link para teste (Sandbox).
Entendendo a Diferença (Sandbox vs. Produção):
Sandbox (Ambiente de Teste):
Use o link sandbox_init_point.
Ao abrir, você verá uma faixa vermelha/laranja indicando "Sandbox".
Para testar o pagamento: Você NÃO pode usar sua própria conta do Mercado Pago para pagar. Você deve usar cartões de teste fornecidos na documentação ou criar uma segunda conta de teste (Comprador) e logar nela em uma aba anônima.
As credenciais usadas no n8n devem ser as da aba "Credenciais de teste".
Produção (Ambiente Real):
Para valer de verdade (receber dinheiro real), vá ao painel do Mercado Pago Developers.
No menu lateral, clique em "Credenciais de produção".
Copie o novo Access Token de produção.
No n8n, atualize sua credencial (troque o token de teste pelo de produção).
Agora, use o link retornado no campo init_point.
Qualquer pagamento feito aqui será real e cobrará do cartão do cliente.


## Resumo dos Links e Scripts
URL da API: https://api.mercadopago.com/checkout/preferences
JSON Básico para o Body:

```json
{
  "items": [
    {
      "title": "Nome do Produto",
      "quantity": 1,
      "currency_id": "BRL",
      "unit_price": 10.00
    }
  ],
  "back_urls": {
    "success": "https://seusite.com/sucesso",
    "failure": "https://seusite.com/erro",
    "pending": "https://seusite.com/pendente"
  },
  "auto_return": "approved"
}
```


Seguindo esses passos, você terá uma automação capaz de gerar links de pagamento dinâmicos para cada pedido ou interação no seu sistema.

