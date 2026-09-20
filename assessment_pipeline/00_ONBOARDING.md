# Onboarding — Revisa Precatório

**Para quem está chegando:** este documento ordena a leitura da pasta `assessment_pipeline/` e lista os acessos necessários para operar a plataforma. Tempo estimado de leitura completa: ~2h.

---

## 1. Leitura em 3 passadas

### Passada 1 — Entender o negócio (~30 min)

| Ordem | Arquivo | O que você aprende |
|---|---|---|
| 1 | `README.md` | O que a plataforma faz, arquitetura, máquina de estados, cenários |
| 2 | `02_FLUXO_COMPLETO.md` | O que acontece do "oi" do cliente no WhatsApp até o laudo no e-mail |
| 3 | `05_DIAGRAMAS_MERMAID.md` §1 e §2 | Visualizar o pipeline e a máquina de estados |

### Passada 2 — Operar (~45 min)

| Ordem | Arquivo | O que você aprende |
|---|---|---|
| 4 | `03_CENARIOS_E_TABELAS.md` | O que acontece em cada tipo de falha e como identificar nas tabelas |
| 5 | `04_QUERIES_MONITORAMENTO.md` | As queries do dia a dia — decore a tabela-resumo do final |
| 6 | `06_WORKFLOWS_N8N.md` | Os 7 workflows ativos, quem chama quem, destinatários |

### Passada 3 — Fundo técnico (~45 min)

| Ordem | Arquivo | O que você aprende |
|---|---|---|
| 7 | `01_ARQUITETURA_GERAL.md` | Schema completo das tabelas, paths da VPS, certificado digital |
| 8 | `07_FERRAMENTAS_AUXILIARES.md` | Backoffice Streamlit e CPF batch |
| 9 | `n8n_workflows_live/*.json` | Abrir 1-2 JSONs e comparar com a doc (opcional) |

### Complementos fora desta pasta

| Onde | Para quê |
|---|---|
| `../AGENTS.md` (raiz do repo) | Detalhes do OCR: detectors, LLM híbrido, schema Pydantic, testes |
| repo `crawler_tjsp/docs/` | Setup de certificado, troubleshooting de autenticação, deploy |
| repo `calc-precatorio-tjsp/README.md` | Regras de cálculo (IPCA-E, juros, EC113/EC136) |

---

## 2. Acessos a solicitar

| Sistema | O quê | Com quem |
|---|---|---|
| n8n | Login em `n8n.srv987902.hstgr.cloud` | Admin da instância |
| PostgreSQL | Credenciais `72.60.62.124:5432/n8n` (ficam no `.env` do repo, **não commitado**) | Persival |
| VPS Windows | Acesso RDP/SSH ao servidor do crawler | Persival |
| GitHub | Colaborador em `github.com/revisaprecatorio/*` | Owner do repo |
| Meta/WhatsApp | WABA — `phoneNumberId=772929385904854` | Quem administra a Meta Business |
| Mercado Pago | Conta que recebe os pagamentos | Flávio/financeiro |
| Caixas de e-mail | `revisa.manual@gmail.com` (alertas + laudos parciais), `contato@revisaprecatorio.com.br` (LGPD) | Equipe |

> ⚠️ Segredos (`n8n_api.env`, `github_credentials.env`, `.env`, senha do `.pfx`) **nunca** vão para o repo nem para conversas — passar por canal seguro.

---

## 3. Glossário — termos do domínio

| Termo | Significado |
|---|---|
| **Precatório** | Ordem judicial de pagamento de dívida do poder público (aqui: TJSP) |
| **Ofício Requisitório** | Documento que formaliza a requisição de pagamento do precatório |
| **ANEXO II** | Página do ofício com dados do credor (nome, CPF, valores, banco) — é o que o OCR extrai |
| **DEPRE** | Departamento que processa os ofícios — pode **rejeitar** (ofício inválido) |
| **Número de ordem** | Posição do precatório na fila de pagamento (`numero_ordem`) |
| **e-SAJ** | Portal do TJSP onde os processos/documentos são consultados |
| **Certificado A1** | Certificado digital que autentica o robô no e-SAJ (via Web Signer/Softplan no Chrome) |
| **Laudo** | Relatório HTML enviado ao cliente com processos, valores atualizados e prioridades |
| **Laudo parcial** | Quando parte dos processos não pôde ser processada — vai à equipe (`revisa.manual@`), cliente recebe WhatsApp com prazo de 7 dias úteis |
| **PDF "700"** | Formato antigo de processo (número começa com `7`, ex. `7007859-54.2010...`) — sem ANEXO II, falha no OCR |
| **Watchdog** | `Alerta_ERROS_GRAVES` — varre o banco a cada 10 min atrás de jobs travados/falhos |
| **Estado terminal** | `REPORT_SENT` (sucesso — completo ou parcial), `ALERTA_MANUAL_SENT` (precisa de ação humana), `PAYMENT_REJECTED`, `NO_VALID_PROCESS` |

---

## 4. Exercícios práticos (hands-on)

1. **Rodar Q01** (`04_QUERIES_MONITORAMENTO.md`) — quantos jobs há em cada estado agora?
2. **Rodar Q17** com um CPF real — reconstruir a timeline de um cliente: consulta → pagamento → OCR → laudo
3. **Abrir `n8n_workflows_live/Laudo envio email+cpf.json`** — encontrar o nó `Check Processamento Completo` e entender o que define "parcial"
4. **Simular um CPF de teste** via `CPF_batch_processing` (Q23 depois para conferir)
5. **Encontrar na doc:** o que acontece se o worker morrer com um job em `PAYMENT_APPROVED`? (resposta: watchdog em 2h → `ALERTA_MANUAL_SENT`)

---

## 5. Regras de ouro operacionais

1. **Nenhum cliente pago fica sem resposta** — se cair no seu colo, ou sai laudo ou sai comunicação de processamento manual (7 dias úteis)
2. **`REPORT_SENT` ≠ problema** — é o estado terminal normal; desfecho real está em `process_tracking` (`LAUDO_ENVIADO` vs `LAUDO_PARCIAL`)
3. **Laudo fantasma existe** — `REPORT_SENT` sem evento de laudo no tracking = bug; Q19 detecta; watchdog cobre
4. **A caixa `revisa.manual@gmail.com` é o coração operacional** — laudos parciais e alertas chegam lá
5. **Não commitar** `.env`, `n8n_api.env`, `github_credentials.env`, `*.pfx`, senhas de certificado
6. **VPS é sensível** — `RUNTIME_DISABLED` (arquivo na pasta do crawler) para o worker sem matar processos; não alterar sem avisar
