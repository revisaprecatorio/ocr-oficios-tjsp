# Relatório acumulado de consultas — n8n

**Workflow:** `Relatório Semanal Acumulado` · **ID:** `nUCThfJ7zsmYJvoR` · **Snapshot:** `n8n_workflows_live/Relatório Semanal Acumulado.json`  
**Revisado:** 13/11/2026

**Estado:** **ativo** desde 28/10/2026. Envio automático **toda sexta-feira às 10:00** (`America/Sao_Paulo`). O `Manual Trigger` continua disponível para disparos pelo editor.

**Destinatários:** `persival.balleste@gmail.com`, `ricazevedo.adv@gmail.com`, `dr.rodrigoferrao@gmail.com`, `adv.cappi@gmail.com`.

**Histórico de envios:** disparo único manual em 28/10/2026 (execução `125255`); agendados em 30/10 (`126215`) e 06/11/2026 (`129315`), todos com sucesso.

> ⚠️ O assunto ainda é `[TESTE] Relatório semanal acumulado — {data}` e o nó de envio ainda se chama "Enviar relatório de teste" — resquício da fase de testes.

## Apresentação

O relatório é enviado como HTML no corpo do e-mail e CSV anexo. Usa o cabeçalho/logo e a paleta azul `#004aad` do laudo. Cada linha representa **um CPF**; não se cria uma linha por processo.

A coluna **Processos / valor principal** contém a lista de processos em linhas separadas dentro da mesma célula. Cada processo mostra o CNJ e, quando disponível, a data e o valor principal bruto. Os outros campos do CPF são apresentados uma única vez na linha. O CSV contém a mesma estrutura, com quebras de linha dentro da célula de processos.

Ordem das colunas:

1. Consulta (timestamp mais recente)
2. WhatsApp
3. CPF
4. Nome TJSP
5. Quantidade de processos
6. Processos / valor principal (multilinha)
7. Status classificado
8. E-mail
9. Link gerado em
10. Dias desde a consulta
11. Evidência do status
12. Número de consultas daquele CPF
13. Primeira consulta do CPF
14. Última consulta do CPF
15. Indicação de CPF consultado novamente

## Cartões de resumo: definições e reconciliação

- **Consultas realizadas:** quantidade de eventos `CONSULTA/CONSULTA_REALIZADA` registrados em `process_tracking`, com `consulta_id` associado a uma consulta real.
- **Consultas únicas (1ª por CPF):** número de CPFs distintos consultados.
- **Reconsultas adicionais:** total de consultas realizadas menos CPFs distintos. Essas são as consultas além da primeira para cada CPF.
- **CPFs com repetição:** número de CPFs que aparecem mais de uma vez. É uma contagem de grupos de CPFs, não de eventos repetidos.
- **CPFs sem processos:** CPFs cujo último resultado tem `total_processos = 0`.
- **Pagos:** CPFs com evidência de pagamento aprovado.

Conferência em 13/11/2026 (query real do workflow): **196 consultas realizadas = 152 consultas únicas + 44 reconsultas adicionais**. Os 44 eventos adicionais foram gerados por **25 CPFs com repetição**. Distribuição: 127 CPFs consultados uma vez, 18 duas vezes, 5 três vezes, 1 oito vezes e 1 dez vezes. Período coberto: 22/09/2026 a 13/11/2026 (o banco foi limpo por volta de 20/09/2026).

Status por CPF: 87 sem processos, 37 "Consultou; sem avanço registrado", 22 aguardando confirmação, 3 com link gerado sem pagamento, 3 com código pendente e **0 pagos**.

Consultas com zero processos **não são descartadas**. O relatório exclui `CPF='00000000000'`, que identifica sessões temporárias do chatbot, e não um CPF consultado.

## Dados e limites históricos

- Fonte do histórico de consultas: `process_tracking`; fonte do estado atual e snapshot de processos: `consultas_esaj`.
- Uma nova consulta do mesmo CPF pode atualizar o snapshot em `consultas_esaj`. O tracking preserva timestamps e contagem de repetições, mas não o snapshot de processos de cada repetição antiga. Portanto, uma linha por CPF usa o snapshot de processos mais recente disponível.
- Se houver mais de um registro atual para o mesmo CPF (por exemplo, números de WhatsApp diferentes), o SQL seleciona o registro de consulta mais recente; as contagens e datas de repetição são agregadas por CPF.
- O nome de perfil do WhatsApp não é capturado pelo chatbot. `Nome TJSP` vem da consulta ao tribunal.
- O valor principal vem de `esaj_detalhe_processos`; fica vazio quando não há extração para o processo. A tabela só é preenchida pelo OCR depois de um pagamento aprovado — em 13/11/2026 ela está vazia (nenhum pagamento aprovado desde a limpeza de 20/09), então a coluna sai vazia para todos os CPFs.
- `Consultou; sem avanço registrado` não afirma que o usuário leu a mensagem ou desistiu. `E-mail informado; código pendente` usa o estado atual da sessão. `Link gerado; sem pagamento aprovado` é evidência de link, não de leitura.
- Não há eventos duráveis para toda resposta de confirmação/código. O status é limitado às evidências que as tabelas preservam.

## Estrutura do workflow

```text
Disparo semanal — sexta-feira 10h (Schedule)   Manual Trigger
                     └──────────────┬──────────────┘
                                    ↓
                  Relatório acumulado — PostgreSQL
                                    ↓
                        Montar HTML + CSV (Code)
                                    ↓
                 Enviar relatório de teste (Send Email)
```

- **Schedule:** `rule.interval = [{field: "weeks", triggerAtDay: [5], triggerAtHour: 10, triggerAtMinute: 0}]`; `settings.timezone = America/Sao_Paulo`.
- **Postgres:** `Execute Query`, credencial `Postgres account`, consulta somente leitura.
- **Code:** `Run Once for All Items`; monta o HTML e o CSV binário `data` (`revisa-relatorio-acumulado.csv`).
- **Send Email:** credencial `SMTP revisa`; remetente `Revisa Precatório <contato@revisaprecatorio.com.br>`; 4 destinatários (acima); assunto ainda marcado `[TESTE]`; anexo CSV em `data`.

O SQL e o JavaScript atuais são os armazenados nos nodes `Relatório acumulado — PostgreSQL` e `Montar HTML + CSV` do workflow vivo (cópia em `n8n_workflows_live/`). **A instância n8n é a fonte de verdade** para esses códigos.

## Comportamento do agendamento

A query **não filtra por período**: cada envio de sexta-feira traz o **histórico completo acumulado**, e não apenas os últimos 7 dias. Foi assim que o envio semanal foi pedido e configurado em 28/10/2026.

Se no futuro for necessário um recorte só da semana, alterar a query para um intervalo sem sobreposição (`início inclusivo`, `fim exclusivo`), por exemplo sexta 10:00 anterior até sexta 10:00 atual, em `America/Sao_Paulo`.
