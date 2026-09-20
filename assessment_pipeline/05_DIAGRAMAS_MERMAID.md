# Diagramas Mermaid — Pipeline Revisa Precatório

**Revisado:** 20/09/2026 — reflete REPORT_SENT terminal, Etapa 9b, watchdog ampliado e destinatários reais.

---

## 1. Pipeline Completo (Ponta a Ponta)

```mermaid
flowchart TD
    A([Cliente WhatsApp]) -->|CPF| B[Chatbot Revisa\nn8n]
    B -->|consulta e-SAJ + email + código| C[(consultas_esaj\nAWAITING_PAYMENT)]
    C -->|POST /generate-payment-link| D[Mercado Pago Unified\nn8n]
    D -->|Link MP R$1,00| A
    A -->|Paga| MP[(Mercado Pago)]
    MP -->|webhook /mercadopago-notification| D
    D -->|approved → PAYMENT_APPROVED\n+ limpa dados antigos do CPF| E[(consultas_esaj)]
    D -->|WhatsApp: 24h + exceção 7 dias úteis| A

    E -->|executar.bat agendado| G[runtime/executar.bat\nkill switch RUNTIME_DISABLED]
    G --> H[core/orchestrator_subprocess.py\nFOR UPDATE SKIP LOCKED]
    H -->|lock| I[(consultas_esaj\nPROCESSING)]
    H --> J[core/crawler_full.py\nSelenium + Chrome :9222\ncert. A1 / Web Signer]
    J -->|download Pasta Digital| K[PDFs\nC:/Temp/RevisaDownloads/cpf/]

    K --> L[pipeline_completo.sh\nEtapas 1-9]
    L --> M[processar_pipeline.py\ndetectors + LLM híbrido]
    M --> N[(esaj_detalhe_processos\n66 colunas)]
    L --> O[calc-precatorio-tjsp/main.py\nIPCA-E + juros + EC113/136]
    O --> NA[(esaj_calc_precatorio_resumo\n47 colunas)]
    O -->|POST /reporte-email-cpf\nvia webhook_n8n.py| P[Laudo envio email+cpf\nn8n]
    L -.->|Etapa 9b: count(calc)=0\n→ chama webhook direto| P

    P -->|todos_processados=true| Q[E-mail ao cliente\nlaudo completo + LGPD]
    P -->|todos_processados=false| R[E-mail revisa.manual@\n+ WhatsApp cliente\nlaudo parcial + LGPD]
    P --> U1[(FINAL_REPORT_SENT /\nPARTIAL_REPORT_SENT\ntransitório)]
    H -->|exit 0| T[(REPORT_SENT\nTERMINAL de-facto)]

    style A fill:#25D366,color:#fff
    style Q fill:#2196F3,color:#fff
    style R fill:#FF9800,color:#fff
    style T fill:#4CAF50,color:#fff
```

---

## 2. Máquina de Estados — `consultas_esaj.current_state`

```mermaid
stateDiagram-v2
    [*] --> IDLE : sem registro

    IDLE --> AWAITING_EMAIL : CPF recebido (Chatbot)
    AWAITING_EMAIL --> AWAITING_CODE : e-mail → código enviado\n(com aviso LGPD, 15 min)
    AWAITING_CODE --> AWAITING_CONFIRMATION : código correto
    AWAITING_CONFIRMATION --> AWAITING_PAYMENT : confirmado → link MP
    AWAITING_PAYMENT --> PAYMENT_APPROVED : MP approved
    AWAITING_PAYMENT --> PAYMENT_REJECTED : MP rejected
    PAYMENT_REJECTED --> AWAITING_PAYMENT : cliente digita "sim"

    PAYMENT_APPROVED --> PROCESSING : orchestrator\nSKIP LOCKED
    PAYMENT_APPROVED --> ALERTA_MANUAL_SENT : >2h parado\n(watchdog = worker caído)

    PROCESSING --> FINAL_REPORT_SENT : laudo completo\n(Laudo, durante Etapa 9)
    PROCESSING --> PARTIAL_REPORT_SENT : laudo parcial\n(Laudo, durante Etapa 9)
    PROCESSING --> MANUAL_PROCESS : OCR falhou\n(processador.py)
    PROCESSING --> PIPELINE_ERROR : exit≠0\n(orchestrator)
    PROCESSING --> CALC_ERROR : falha no cálculo
    PROCESSING --> AUTH_ERROR : login e-SAJ\n(orchestrator)
    PROCESSING --> DOWNLOAD_FAILED : 0 PDFs\n(orchestrator)
    PROCESSING --> NO_VALID_PROCESS : sem precatórios

    FINAL_REPORT_SENT --> REPORT_SENT : orchestrator\nsobrescreve ao concluir
    PARTIAL_REPORT_SENT --> REPORT_SENT : idem
    MANUAL_PROCESS --> REPORT_SENT : se pipeline concluiu\ncom outros processos OK

    PIPELINE_ERROR --> ALERTA_MANUAL_SENT : watchdog 10min
    CALC_ERROR --> ALERTA_MANUAL_SENT : watchdog 10min
    AUTH_ERROR --> ALERTA_MANUAL_SENT : watchdog 10min
    DOWNLOAD_FAILED --> ALERTA_MANUAL_SENT : watchdog 10min
    MANUAL_PROCESS --> ALERTA_MANUAL_SENT : watchdog 10min\n(Reporte_Manual/ERROS_GRAVES)
    REPORT_SENT --> ALERTA_MANUAL_SENT : >30min sem calc\n+ processo não-rejeitado\n(laudo fantasma)

    note right of REPORT_SENT
        TERMINAL de-facto.
        Desfecho real no tracking:
        LAUDO_ENVIADO=completo
        LAUDO_PARCIAL=parcial
    end note
    note right of ALERTA_MANUAL_SENT
        TERMINAL pós-alerta.
        Equipe atua via
        revisa.manual@gmail.com
    end note
```

---

## 3. Workflow: Mercado Pago Unified

```mermaid
flowchart LR
    subgraph "Fluxo A — Geração de Link"
        WH1([POST\n/generate-payment-link]) --> V{Validate\ntrigger_payment\n+ email?}
        V -->|Sim| GL[Generate Payment Link\nMP API — R$ 1,00\nexternal_ref=wa_ts]
        V -->|Não| SK[Log Skipped]
        GL --> SL[(Save Payment Link\nAWAITING_PAYMENT)]
        SL --> PT1[(PT: LINK_GERADO)]
        PT1 --> CL[(Cleanup Session\ncpf=00000000000)]
        CL --> WA1[WhatsApp\nlink ao cliente]
    end

    subgraph "Fluxo B — Notificação de Pagamento"
        WH2([POST\n/mercadopago-notification]) --> RES[Respond 200 OK\nimediato]
        WH2 --> F{type=payment?}
        F -->|Sim| GPD[GET /v1/payments/id]
        F -->|Não| IGN[Log Ignored]
        GPD --> PS[Process Payment Status\napproved/rejected/pending]
        PS --> UPS[(UPDATE consultas_esaj\n+ DELETE dados antigos\nse approved)]
        UPS --> PT2[(PT: PAYMENT_APPROVED\nou PAYMENT_REJECTED)]
        PT2 --> WA2[WhatsApp status\n24h + 7 dias úteis]
    end

    style SK fill:#ccc
    style IGN fill:#ccc
    style RES fill:#4CAF50,color:#fff
```

---

## 4. Workflow: Laudo envio email+cpf

```mermaid
flowchart TD
    WH([POST /reporte-email-cpf\ncalc webhook_n8n.py ou Etapa 9b]) --> CPC[(Check Processamento Completo\ncpf+email, state ∉ REPORT_SENT/FINAL)]
    CPC --> TP{todos_processados?\nanomalia→Não Processado\nrejeitado→Processado}

    TP -->|true| FD[(Fetch Data\nvw_precatorios_full)]
    FD --> BH[Build HTML Content\nlaudo completo + LGPD]
    BH --> SE[Send Report Email\n→ email do cliente]
    SE --> LS[(Log Success)]
    LS --> WR[Webhook Response]
    WR --> UR[(UPDATE\nFINAL_REPORT_SENT)]
    UR --> PT1[(PT: ENVIO_LAUDO\nLAUDO_ENVIADO)]

    TP -->|false| FDP[(Fetch Data - parcial)]
    FDP --> BHP[Build HTML Parcial\n+ LGPD]
    BHP --> SR[Send Report Revisa\n→ revisa.manual@gmail.com]
    SR --> PN[phone e nome]
    PN --> WP[Whatsapp Parcial\n7 dias úteis]
    WP --> LP[(Log Parcial)]
    LP --> WRP[Webhook Response Parcial]
    WRP --> UPR[(UPDATE\nPARTIAL_REPORT_SENT)]
    UPR --> PT2[(PT: LAUDO_PARCIAL)]

    UR -.->|minutos depois| ORCH[orchestrator exit 0\n→ REPORT_SENT terminal]
    UPR -.->|minutos depois| ORCH

    style TP fill:#FF9800,color:#fff
    style PT1 fill:#2196F3,color:#fff
    style PT2 fill:#FF5722,color:#fff
    style ORCH fill:#4CAF50,color:#fff
```

---

## 5. Workflows de Alerta (Schedule — a cada 10 min)

```mermaid
flowchart LR
    subgraph "Alerta_ERROS_GRAVES — watchdog"
        SC1([10min]) --> Q1[(Query 3 grupos:\nerros pipeline +\nPAYMENT_APPROVED>2h +\nREPORT_SENT fantasma)]
        Q1 --> PM1[Prepara Mensagens\n+ erros OCR agregados]
        PM1 --> WA1[WhatsApp Cliente\n7 dias úteis]
        WA1 --> E1[Email\nrevisa.manual@gmail.com]
        E1 --> UPD1[(UPDATE\nALERTA_MANUAL_SENT)]
        UPD1 --> L1[(Log)]
    end

    subgraph "Alerta_Laudo_Parcial"
        SC2([10min]) --> Q2[(LAUDO_PARCIAL\nsem PARCIAL_INFORMADO)]
        Q2 --> PM2[Prepara Mensagens]
        PM2 --> E2[Email\nrevisa.manual@gmail.com]
        E2 --> PT2[(Insert PARCIAL_INFORMADO)]
        PT2 --> L2[(Log BATCH)]
    end

    subgraph "Alerta_Reporte_Manual"
        SC3([10min]) --> Q3[(current_state\n= MANUAL_PROCESS)]
        Q3 --> PM3[Prepara Mensagens]
        PM3 --> WA3[WhatsApp Cliente]
        WA3 --> E3[Email\nrevisa.manual@gmail.com]
        E3 --> UPD3[(UPDATE\nALERTA_MANUAL_SENT)]
        UPD3 --> L3[(Log BATCH)]
    end
```

> `Alerta_PDF_antigo` — 2 workflows homônimos **inativos** (`PMyNPcPlRZMZjCb1`, `Uck9WlB08COLVM1K`). Query idêntica ao Reporte_Manual; sem função atual.

---

## 6. OCR Pipeline Interno (`pipeline_completo.sh` — com Etapa 9b)

```mermaid
flowchart TD
    IN([Recebe CPF]) --> E1[Etapa 1\nLimpeza staging]
    E1 --> CHK{PDFs em\nRevisaDownloads/cpf?}
    CHK -->|Não| ERR1([exit 1 → PIPELINE_ERROR])
    CHK -->|Sim| E2[Etapa 2\nprocessar_pipeline.py\nOCR de todos os PDFs]

    E2 --> DET[DetectorOficio\nDetectorAnexoII\nDetectorSaldoFinal\nDetectorHabilitacaoHerdeiros\nDetectorTermosJuridicos\nLLM Gemini → GPT-4o-mini]
    DET -->|falha num PDF| OCR_ERR[(process_tracking\nOCR_ERRO\n+ MANUAL_PROCESS)]
    OCR_ERR --> JSON
    DET -->|OK| JSON[JSONs\noutputs/consultas/cpf/]

    JSON --> E3{Etapa 3\nJSONs > 0?}
    E3 -->|Não| ERR2([exit 1 → PIPELINE_ERROR])
    E3 -->|Sim| E4[Etapa 4\ningest_all_jsons.py\nupsert esaj_detalhe_processos]
    E4 --> E5{Etapa 5\nCOUNT>0 no banco?}
    E5 -->|Não| ERR3([exit 1 → PIPELINE_ERROR])
    E5 -->|Sim| E6[Etapa 6\nrecalcular_idoso.py]
    E6 --> E7[Etapa 7\nBackup JSONs]
    E7 --> E8[Etapa 8\nArquivar PDFs]
    E8 --> E9[Etapa 9\ncalc/main.py\ncalcula + webhook_n8n.py]
    E9 --> C9{calc gerou\nregistros?}
    C9 -->|Sim| WH[POST /reporte-email-cpf\npor calc/main.py]
    C9 -->|Não\n'Nenhum processo pendente'| E9B[Etapa 9b ✅\nbusca email em consultas_esaj\n→ chama webhook direto]
    E9B --> WH
    WH --> OK([exit 0 → orchestrator\nseta REPORT_SENT])

    style ERR1 fill:#F44336,color:#fff
    style ERR2 fill:#F44336,color:#fff
    style ERR3 fill:#F44336,color:#fff
    style OK fill:#4CAF50,color:#fff
    style OCR_ERR fill:#FF9800,color:#fff
    style E9B fill:#9C27B0,color:#fff
```

> ✅ **Cenário F resolvido:** a Etapa 9b garante que CPF 100% rejeitado acione o webhook mesmo sem registros em `esaj_calc_precatorio_resumo` — o cliente recebe o laudo informando a rejeição DEPRE.

---

## 7. Chatbot Revisa — Máquina de Estados Conversacional

```mermaid
stateDiagram-v2
    [*] --> IDLE : nova mensagem\n(Get User State por whatsapp_from)

    IDLE --> AWAITING_EMAIL : CPF válido
    note right of AWAITING_EMAIL
        Bot pede e-mail
        Timeout: 30 min
    end note

    AWAITING_EMAIL --> AWAITING_CODE : e-mail recebido\nconsulta e-SAJ + código enviado
    note right of AWAITING_CODE
        E-mail: código 6 dígitos + aviso LGPD
        Timeout: 15 min (code_generated_at)
    end note

    AWAITING_CODE --> IDLE : timeout/código errado
    AWAITING_CODE --> AWAITING_CONFIRMATION : código correto

    AWAITING_CONFIRMATION --> AWAITING_PAYMENT : CONFIRM_YES\n→ /generate-payment-link
    AWAITING_CONFIRMATION --> IDLE : CONFIRM_NO/MENU
    note right of AWAITING_PAYMENT
        Link MP enviado
        Timeout: 60 min
    end note

    AWAITING_PAYMENT --> PAYMENT_APPROVED : MP webhook approved
    AWAITING_PAYMENT --> PAYMENT_REJECTED : MP webhook rejected
    PAYMENT_REJECTED --> AWAITING_PAYMENT : "sim" → novo link

    note right of [*]
        Rotas: NOT_TEXT, CPF, EMAIL, CODE,
        CONFIRM_YES/NO, MENU,
        INFO_PRECATORIOS, CONSULTAR, AGENT
        Estados de pipeline (REPORT_SENT, erros)
        não entram na sessão → cliente pode
        reiniciar fluxo normalmente
    end note
```

---

## 8. Comunicação LGPD — pontos de contato

```mermaid
flowchart LR
    C([Cliente]) -->|WhatsApp| W1[Mensagem pós-pagamento\n24h + exceção 7 dias úteis]
    C -->|E-mail código| W2[Verificação\n+ Privacidade e proteção de dados\n+ link Política + contato@]
    C -->|E-mail laudo| W3[Laudo completo\nDISCLAIMER + aviso LGPD + link]
    EQ([Equipe revisa.manual@]) --> W4[Laudo parcial\nDISCLAIMER + aviso LGPD + link]

    style W2 fill:#1a5f7a,color:#fff
    style W3 fill:#1a5f7a,color:#fff
    style W4 fill:#1a5f7a,color:#fff
```
