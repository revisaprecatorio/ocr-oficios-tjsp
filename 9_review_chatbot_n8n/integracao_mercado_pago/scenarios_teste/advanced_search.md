# Checklist para testes de integracao com Mercado Pago

## A forma mais “à prova de n8n” de operar Mercado Pago em **produção** (e receber confirmação de **pago / não pago / pendente**) é tratar o checkout como um processo em 2 etapas:

1. **Você gera uma cobrança (preference)** e entrega um **link (init_point)** ao usuário pagar (Pix, boleto, cartão etc.).
2. **Você confirma o resultado via Webhook/IPN + consulta do pagamento** (não confiar só no redirecionamento do navegador).

Abaixo vai o passo a passo completo, com os pontos que normalmente causam exatamente os bloqueios que você descreveu.

---

## 1) Decida o “tipo” de integração (para n8n, escolha isto primeiro)

### Opção A — Recomendada para n8n: **Checkout Pro (redirect)**

* Você gera a **preference** e recebe um **link de pagamento**.
* Mercado Pago mostra Pix/cartão/boleto etc. e permite **checkout como convidado (sem conta)**. ([Mercado Pago][1])
* Você confirma status via **Webhooks** (ou IPN) + consulta na API. ([Mercado Pago][2])

> Para o seu cenário (WhatsApp/n8n/workflow), esta é quase sempre a melhor escolha.

### Opção B — “Full API / Checkout Transparente (Bricks / Payments API)”

* Dá mais controle, mas normalmente exige front-end (tokenização de cartão, 3DS, etc.).
* Alguns ecossistemas/lojas citam até necessidade de **contrato específico** para risco/análise em integrações “transparentes”. ([Basede Conhecimento][3])

---

## 2) Por que R$ 0,01 / R$ 1 pode estar falhando (e como destravar)

### 2.1. **Existe mínimo documentado de cartão: R$ 1**

O Mercado Pago documenta **R$ 1** como valor mínimo para receber com cartão em vários cenários. ([Mercado Pago][4])

### 2.2. Mas… algumas configurações de checkout impõem **mínimo maior (muito comum R$ 5)**

Plataformas e tutoriais de configuração apontam que é comum existir um **“valor mínimo” configurável**, e o padrão em alguns checkouts é **R$ 5,00**. ([Mercado Pago][5])

Se você está usando link/preference e mesmo assim R$ 1 falha, as causas mais comuns em produção são:

* **Regra/parametrização do seu fluxo** (ou do template/node) impondo mínimo > R$1.
* **Motor antifraude** recusando “microtransações” como risco (especialmente em conta recém-ativada, device novo, comportamento de teste repetitivo). O próprio MP descreve recusas por requisitos de segurança/risco. ([Mercado Pago][6])

**Recomendação prática para destravar o “caminho feliz”:**

* Primeiro valide tudo com **R$ 5 ou R$ 10** (apenas para confirmar fluxo end-to-end).
* Depois tente descer (R$ 2, R$ 1) e compare a taxa de aprovação.
* Para entender a recusa, você precisa registrar o retorno do pagamento (ver seção 4).

### 2.3. Pix “mínimo”

O Mercado Pago tem variações por produto (Pix normal vs Pix parcelado etc.). Por exemplo, existe comunicação de Pix parcelado “a partir de R$ 15” em algumas ofertas. ([Mercado Pago][7])
Na prática, o que decide se aparece Pix/boleto e se aprova valores baixos é: **tipo de checkout + configuração da conta + risco**.

---

## 3) Checklist de produção (antes de culpar o n8n)

1. **Credenciais de Produção ativas** na conta do seu cliente (Access Token de produção). ([Mercado Pago][8])
2. Você não está misturando:

   * token de teste com fluxo de produção, ou vice-versa; e/ou
   * comprador e vendedor sendo a **mesma conta** (em teste isso quebra com frequência). ([GitHub][9])
3. Você tem estratégia de retorno correta:

   * **Back URLs** servem para redirecionar o navegador, mas **não são garantia de confirmação**.
   * Quem dá “verdade” é **Webhook/IPN + GET do pagamento**. ([Mercado Pago][2])

---

## 4) Fluxo n8n “profissional”: gerar link + receber confirmação + conciliar status

### 4.1. Criar a cobrança (Checkout Pro / preference)

No n8n use **HTTP Request** para criar a preference e obter o `init_point`.

* **POST** (endpoint de Checkout/Preferences do Mercado Pago; você chamará via HTTP Request no n8n)
* Headers:

  * `Authorization: Bearer <ACCESS_TOKEN_PRODUCAO>`
  * `Content-Type: application/json`

Campos essenciais no body (conceito):

* `items`: título, quantidade, preço, moeda
* `notification_url`: seu webhook do n8n (abaixo)
* `external_reference`: seu ID interno (pedido/assinatura/CPF etc.)
* `back_urls`: success/failure/pending (opcional, mas útil)
* `auto_return`: “approved” (opcional)

Essa abordagem é a base do Checkout Pro. ([Mercado Pago][1])

**Saída:** o MP retorna um `init_point` (link). Você manda esse link ao usuário no WhatsApp.

### 4.2. Receber confirmação (Webhook/IPN) no n8n

Crie um node **Webhook** no n8n, por exemplo:

* `https://seu-dominio.com/webhook/mercadopago`

E configure para o MP notificar pagamentos via **Webhooks** (ou **IPN** como fallback). ([Mercado Pago][2])

O Webhook normalmente chega com um “evento” (ex.: pagamento) e um `id`. A partir daí:

1. **Webhook (entrada)**
2. **HTTP Request (consulta)**: faça **GET do pagamento pelo `id`** para buscar status oficial (`approved`, `pending`, `rejected`, etc.). O endpoint “Criar pagamento” e o modelo de API ficam na referência oficial de Payments. ([Mercado Pago][10])
3. **IF/Switch** no n8n:

   * `approved` → marcar como pago, liberar serviço, enviar confirmação
   * `pending` → manter pendente, avisar usuário (ex.: boleto/pix aguardando)
   * `rejected`/`cancelled` → falha, solicitar novo meio/pagamento
4. **Persistência**: grave o resultado no seu banco/planilha/CRM.
5. **Notificação ao usuário** (WhatsApp/email).

### 4.3. Validação de autenticidade do webhook (importante em produção)

O MP documenta o uso de chave/assinatura para validar autenticidade de notificações. ([Mercado Pago][11])
No n8n, você valida isso com um Function node (ou Code node) antes de processar.

---

## 5) Pagamento com ou sem conta Mercado Pago/Mercado Livre e com todos os meios (Pix/boleto/cartão)

Se você seguir a Opção A (**Checkout Pro**), o próprio Mercado Pago suporta:

* **Checkout como convidado (sem conta)** ([Mercado Pago][1])
* Meios populares no Brasil, incluindo **Pix** e outros, dependendo da configuração do vendedor/conta. ([Mercado Pago][12])

Para garantir que Pix/boleto apareçam:

* Confirme no painel do cliente que os meios estão habilitados para a conta/checkout.
* Não “force” um método no preference (a menos que você queira restringir).

---

## 6) Sobre sandbox: quando vale a pena (e como reduzir dor)

O Mercado Pago tem **contas de teste** e **cartões de teste** oficiais. ([Mercado Pago][13])
Dito isso, há relatos recorrentes de fricções no sandbox; um problema típico é tentar pagar com configuração incompleta de buyer/seller (ex.: buyer sem app), o que alguns devs relatam como causa de falhas no Checkout Pro de teste. ([DEV Community][14])

Se você optar por “testar em produção” com valor baixo:

* Faça isso com um **comprador real** (ou um cartão real) e trate como transação real (estorno/conciliar depois).
* Comece com **R$ 5–10** para validar o fluxo, depois tente baixar.

---

## 7) Diagnóstico rápido para o seu caso (pelos sintomas que você descreveu)

Pelo seu relato (“não aceita como aplicação de produção”, “gera link mas pagamento falha”, “sandbox não retorna”), os 3 culpados mais prováveis são:

1. **Credenciais / modo misturado** (token de teste vs produção; ou credenciais de produção não ativadas corretamente). ([Mercado Pago][8])
2. **Você não está confirmando por Webhook + GET payment**, então parece “sem retorno”, ou o retorno depende do navegador/back_url. ([Mercado Pago][2])
3. **Valor baixo + risco** (microtransação rejeitada) e você não está logando “motivo” via consulta do pagamento. ([Mercado Pago][6])

---

Se você colar aqui (removendo dados sensíveis) **um exemplo do payload que o n8n está enviando para criar a cobrança** e **um exemplo do erro/retorno** (ou o status retornado no GET do pagamento), eu consigo te dizer exatamente qual desses 3 (ou qual combinação) é o seu caso e te devolvo o workflow n8n já “fechado” (nós + campos) para Checkout Pro + Webhook + conciliação.

[1]: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro/overview?utm_source=chatgpt.com "Visão geral - Checkout Pro"
[2]: https://www.mercadopago.com.br/developers/en/docs/your-integrations/notifications/webhooks?utm_source=chatgpt.com "Webhooks - Notifications - Mercado Pago Developers"
[3]: https://basedeconhecimento.tray.com.br/hc/pt-br/articles/23263524843547-Como-habilitar-o-Mercado-Pago-transparente-na-sua-loja?utm_source=chatgpt.com "Como habilitar o Mercado Pago transparente na sua loja"
[4]: https://www.mercadopago.com.br/ajuda/21660?utm_source=chatgpt.com "Quais são os valores mínimos e máximos para receber ..."
[5]: https://www.mercadopago.com.br/developers/pt/docs/loja-integrada/payment-methods/configure-checkout?utm_source=chatgpt.com "Configurar checkout - Formas de pagamento"
[6]: https://www.mercadopago.com.br/developers/en/docs/checkout-pro/how-tos/improve-payment-approval/reasons-for-rejection?utm_source=chatgpt.com "Why is a payment rejected?"
[7]: https://www.mercadopago.com.br/ferramentas-para-vender/aceitar-pix?utm_source=chatgpt.com "Aceite Pix na sua loja, no seu site e até na rua"
[8]: https://www.mercadopago.com.br/developers/pt/docs/checkout-api/integration-test/go-to-production-requirements?utm_source=chatgpt.com "Requisitos para entrar em produção - Teste de integração"
[9]: https://github.com/mercadopago/sdk-js/discussions/62?utm_source=chatgpt.com "Checkout Pro: It's painfully hard to test · mercadopago sdk-js"
[10]: https://www.mercadopago.com.br/developers/pt/reference/payments/_payments/post?utm_source=chatgpt.com "Criar pagamento"
[11]: https://www.mercadopago.com.br/developers/en/docs/checkout-pro/payment-notifications?utm_source=chatgpt.com "Configure payment notifications - Stages of integration"
[12]: https://www.mercadopago.com.br/ferramentas-para-vender/check-out?utm_source=chatgpt.com "Cobre com Mercado Pago no seu site"
[13]: https://www.mercadopago.com.br/developers/pt/docs/your-integrations/test/accounts?utm_source=chatgpt.com "Contas de teste - Teste - Mercado Pago Developers"
[14]: https://dev.to/tadeubdev/integrando-mercado-pago-checkout-pro-com-contas-de-teste-problemas-reais-e-como-resolvi-343c?utm_source=chatgpt.com "Integrando Mercado Pago Checkout Pro com Contas de ..."

---

# Fonte 2 


### 🚀 O Template de Arquitetura (HTTP Request)

Você precisará de **dois workflows** separados:
1.  **Gerador de Link:** Recebe o pedido → Gera Link → Envia pro WhatsApp.
2.  **Webhook de Status:** Recebe notificação do MP → Verifica pagamento → Libera acesso.

#### 1. Workflow: Gerar Link de Pagamento (Checkout Pro)

Este fluxo cria aquele link clássico que o usuário clica e escolhe como pagar (PIX, Cartão, Boleto).

*   **Nó 1: Webhook (Trigger)**
    *   Method: `POST`
    *   Authentication: `Header Auth` (opcional, para segurança interna)
*   **Nó 2: HTTP Request (Criar Preferência)**
    *   **Method:** `POST`
    *   **URL:** `https://api.mercadopago.com/checkout/preferences`
    *   **Authentication:** Generic Credential Type -> Header Auth (Name: `Authorization`, Value: `Bearer SUA_ACCESS_TOKEN`)
    *   **Body:** JSON
    ```json
    {
      "items": [
        {
          "title": "Consultoria AI",
          "quantity": 1,
          "currency_id": "BRL",
          "unit_price": 150.00
        }
      ],
      "payer": {
        "email": "cliente@email.com"
      },
      "back_urls": {
        "success": "https://seu-site.com/sucesso",
        "failure": "https://seu-site.com/erro",
        "pending": "https://seu-site.com/pendente"
      },
      "auto_return": "approved",
      "notification_url": "https://seu-n8n.com/webhook/mp-notification" // URL do seu Workflow 2
    }
    ```
*   **Nó 3: Set (Simplificar)**
    *   Extraia o campo `init_point` (link longo) ou `short_init_point` (link curto) do JSON de resposta.
*   **Nó 4: HTTP Request (Enviar WhatsApp)**
    *   Conecte na sua Evolution API/Z-API para enviar a mensagem:
    *   *"Olá! Aqui está seu link de pagamento seguro: {{ $json.init_point }}"*

***

#### 2. Workflow: Webhook de Confirmação (O "Ouvido")

O Mercado Pago envia notificações para tudo (criação, pendente, aprovado). Você precisa filtrar.

*   **Nó 1: Webhook (Receiver)**
    *   Method: `POST`
    *   Path: `/mp-notification` (mesmo usado no `notification_url` acima)
    *   *Dica:* O MP manda apenas um ID no corpo ou na query string (ex: `data.id` ou `id`).
*   **Nó 2: HTTP Request (Consultar Status)**
    *   **Method:** `GET`
    *   **URL:** `https://api.mercadopago.com/v1/payments/{{ $json.body.data.id }}`
    *   **Auth:** `Bearer SUA_ACCESS_TOKEN`
    *   *Por que isso?* O webhook não manda o status "aprovado" confiável, ele só avisa "algo mudou no pagamento X". Você DEVE consultar a API para ver a verdade.
*   **Nó 3: If / Switch**
    *   Condition: `status` equal to `approved`
*   **Nó 4: Ação Final**
    *   Se `true`: Envia WhatsApp de confirmação / Libera acesso no banco de dados.

### 💡 Dicas de Ouro (Pro Tips)
1.  **Credenciais:** Use sempre as `Credenciais de Produção` para valer, mas teste com `Credenciais de Teste` (Sandbox) para não gastar seu próprio dinheiro simulando.
2.  **PIX Copia e Cola:** Se preferir gerar direto o código PIX (sem link de checkout), o endpoint muda para `/v1/payments`. O JSON é diferente e retorna o `qr_code` (string copia e cola) e o `qr_code_base64` (imagem).
    *   *Vantagem:* Menos fricção para o usuário.
    *   *Desvantagem:* Se o usuário fechar o WhatsApp, ele perde o código (o link de checkout guarda a sessão). Para WhatsApp, **Link de Checkout (Preference)** costuma converter melhor pois é persistente.

[1](https://www.youtube.com/watch?v=zWJugh0-JzU)
[2](https://horadecodar.com.br/instalar-community-nodes-n8n-marketplace/)
[3](https://www.npmjs.com/package/mercadopago/v/1.5.10)
[4](https://www.youtube.com/watch?v=FtZ1lo0MIa4)
[5](https://www.npmjs.com/package/@mercadopago/n8n-nodes-mercadopago)
[6](https://www.youtube.com/watch?v=RdyI-vVTeXA)
[7](https://www.youtube.com/watch?v=0T-hR4bNii4)
[8](https://github.com/mercadopago/sdk-nodejs)
[9](https://comunidade.onovomercado.com/c/tecnologia/como-conectar-qualquer-api-no-n8n)
[10](https://n8n.io/integrations/)