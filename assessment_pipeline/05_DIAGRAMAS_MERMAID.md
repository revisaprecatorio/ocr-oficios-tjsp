# Diagramas Mermaid — Pipeline Revisa Precatório

---

## 1. Pipeline Completo (Visão de Ponta a Ponta)

```mermaid
flowchart TD
    A([Cliente WhatsApp]) -->|CPF| B[Chatbot Revisa\nn8n]
    B -->|consulta e-SAJ| C[(consultas_esaj\nAWAITING_PAYMENT)]
    C -->|trigger_payment=true| D[Mercado Pago Unified\nn8n]
    D -->|Link MP gerado| A
    A -->|Paga| D
    D -->|MP webhook approved| E[(consultas_esaj\nPAYMENT_APPROVED)]
    D -->|DELETE dados antigos| F[(esaj_detalhe_processos\nesaj_calc_precatorio_resumo)]

    E -->|watchdog PM2| G[start_worker.py\nWindows Server]
    G --> H[orchestrator_subprocess.py]
    H -->|FOR UPDATE SKIP LOCKED| I[(consultas_esaj\nPROCESSING)]
    H --> J[crawler_full.py\nSelenium/Chrome]
    J -->|login e-SAJ + download| K[PDFs\nC:/Temp/RevisaDownloads/cpf/]

    K --> L[pipeline_completo.sh\nBash]
    L --> M[processar_pipeline.py\nOCR Python]
    M --> N[(esaj_detalhe_processos\n35 campos)]
    L --> O[calc-precatorio-tjsp\nmain.py]
    O -->|POST /reporte-email-cpf| P[Laudo envio email+cpf\nn8n]

    P -->|todos_processados=true| Q[Email ao cliente\nFINAL_REPORT_SENT]
    P -->|todos_processados=false| R[Email Revisa +\nWhatsApp cliente\nPARTIAL_REPORT_SENT]

    style A fill:#25D366,color:#fff
    style Q fill:#2196F3,color:#fff
    style R fill:#FF9800,color:#fff
    style I fill:#9C27B0,color:#fff
```

---

## 2. Máquina de Estados — `consultas_esaj.current_state`

```mermaid
stateDiagram-v2
    [*] --> IDLE : sem registro

    IDLE --> AWAITING_EMAIL : CPF recebido\n(Chatbot)
    AWAITING_EMAIL --> AWAITING_CODE : email enviado\n(Chatbot)
    AWAITING_CODE --> AWAITING_CONFIRMATION : código verificado\n(Chatbot)
    AWAITING_CONFIRMATION --> AWAITING_PAYMENT : confirmado\n(Chatbot)

    AWAITING_PAYMENT --> PAYMENT_APPROVED : MP approved\n(Mercado Pago Unified)
    AWAITING_PAYMENT --> PAYMENT_REJECTED : MP rejected
    AWAITING_PAYMENT --> IDLE : timeout 60min

    PAYMENT_APPROVED --> PROCESSING : orchestrator lock\n(FOR UPDATE SKIP LOCKED)

    PROCESSING --> FINAL_REPORT_SENT : todos_processados=true\n(Laudo envio email+cpf)
    PROCESSING --> PARTIAL_REPORT_SENT : todos_processados=false\n(Laudo envio email+cpf)
    PROCESSING --> MANUAL_PROCESS : OCR falhou\n(processador.py)
    PROCESSING --> PIPELINE_ERROR : OCR/cálculo crash\n(orchestrator)
    PROCESSING --> AUTH_ERROR : login e-SAJ falhou\n(orchestrator)
    PROCESSING --> DOWNLOAD_FAILED : PDFs não baixados\n(orchestrator)
    PROCESSING --> NO_VALID_PROCESS : sem precatórios\n(orchestrator)

    MANUAL_PROCESS --> ALERTA_MANUAL_SENT : alerta enviado\n(Alerta_Reporte_Manual)

    note right of PROCESSING
        REPORT_SENT é transitório:
        orchestrator → Laudo workflow
        substitui por FINAL ou PARTIAL
    end note
```

---

## 3. Workflow: Mercado Pago Unified

```mermaid
flowchart LR
    subgraph "Fluxo A — Geração de Link"
        WH1([POST\n/generate-payment-link]) --> V{Validate\ntrigger_payment\n+ email?}
        V -->|Sim| GL[Generate Payment Link\nMP API]
        V -->|Não| SK[Log Skipped]
        GL --> SL[(Save Payment Link\nconsultas_esaj)]
        SL --> PT1[(PT: LINK_GERADO)]
        PT1 --> CL[(Cleanup Session\ncpf=00000000000)]
        CL --> WA1[WhatsApp\nlink ao cliente]
    end

    subgraph "Fluxo B — Notificação de Pagamento"
        WH2([POST\n/mercadopago-notification]) --> RES[Respond 200 OK\nimediato]
        WH2 --> F{type=payment?}
        F -->|Sim| GPD[GET /v1/payments/id\nMP API]
        F -->|Não| IGN[Log Ignored]
        GPD --> PS[Process Payment Status\napproved/rejected/pending]
        PS --> UPS[(UPDATE consultas_esaj\ncurrent_state)]
        UPS --> PT2[(PT: PAYMENT_APPROVED\nou PAYMENT_REJECTED)]
        PT2 --> WA2[WhatsApp\nnotificação status]
        WA2 --> LPS[(Log + DELETE\ndados antigos OCR/Calc)]
    end

    style SK fill:#ccc
    style IGN fill:#ccc
    style RES fill:#4CAF50,color:#fff
```

---

## 4. Workflow: Laudo envio email+cpf

```mermaid
flowchart TD
    WH([POST /reporte-email-cpf\ncalc-precatorio-tjsp]) --> CPC[(Check Processamento Completo\nesaj_calc_precatorio_resumo)]
    CPC --> TP{todos_processados?}

    TP -->|true| FD[(Fetch Data\nvw_precatorios_full)]
    FD --> BH[Build HTML Content\nlaudo completo]
    BH --> SE[Send Report Email\nao cliente]
    SE --> LS[(Log Success)]
    LS --> WR[Webhook Response]
    WR --> UR[(UPDATE FINAL_REPORT_SENT)]
    UR --> PT1[(PT: ENVIO_LAUDO\nLAUDO_ENVIADO)]

    TP -->|false| FDP[(Fetch Data - parcial\nvw_precatorios_full)]
    FDP --> BHP[Build HTML Parcial]
    BHP --> SR[Send Report Revisa\nemail interno]
    SR --> PN[phone e nome]
    PN --> WP[WhatsApp Parcial\n7 dias úteis]
    WP --> LP[(Log Parcial e Manual)]
    LP --> WRP[Webhook Response Parcial]
    WRP --> UPR[(UPDATE PARTIAL_REPORT_SENT)]
    UPR --> PT2[(PT: LAUDO_PARCIAL\nLAUDO_PARCIAL)]

    style TP fill:#FF9800,color:#fff
    style PT1 fill:#2196F3,color:#fff
    style PT2 fill:#FF5722,color:#fff
```

---

## 5. Workflows de Alerta (Agendados — a cada 10 min)

```mermaid
flowchart LR
    subgraph "Alerta_Laudo_Parcial (ATIVO)"
        SC1([Schedule 10min]) --> Q1[(Query: LAUDO_PARCIAL\nsem PARCIAL_INFORMADO)]
        Q1 --> PM1[Prepara Mensagens]
        PM1 --> E1[Email contato@revisa]
        E1 --> E2[Email persival + rodrigo]
        E2 --> PT1[(Insert PARCIAL_INFORMADO\nprocess_tracking)]
        PT1 --> L1[(Log n8n)]
    end

    subgraph "Alerta_Reporte_Manual (ATIVO)"
        SC2([Schedule 10min]) --> Q2[(Query: current_state\n= MANUAL_PROCESS)]
        Q2 --> PM2[Prepara Mensagens]
        PM2 --> WA[WhatsApp Cliente\n7 dias úteis]
        WA --> E3[Email contato@revisa]
        E3 --> E4[Email persival + rodrigo]
        E4 --> UPD[(UPDATE ALERTA_MANUAL_SENT\nconsultas_esaj)]
        UPD --> L2[(Log n8n)]
    end

    subgraph "Alerta_PDF_antigo (INATIVO ⚠️)"
        SC3([Schedule 10min]) -. DESABILITADO .-> Q3[(Query: MANUAL_PROCESS\nidêntica ao Reporte_Manual)]
        Q3 -. DESABILITADO .-> PM3[Prepara Mensagens]
    end

    style SC3 fill:#ccc,stroke-dasharray:5
    style Q3 fill:#ccc,stroke-dasharray:5
    style PM3 fill:#ccc,stroke-dasharray:5
```

---

## 6. OCR Pipeline Interno (pipeline_completo.sh)

```mermaid
flowchart TD
    IN([Recebe CPF]) --> E1[Etapa 1\nLimpeza staging\noutputs/json/*]
    E1 --> CHK{PDFs existem\nem RevisaDownloads/cpf?}
    CHK -->|Não| ERR1([exit 1\nPIPELINE_ERROR])
    CHK -->|Sim| E2[Etapa 2\nprocessar_pipeline.py\nOCR de todos os PDFs]

    E2 --> DET[DetectorOficio\nDetectorAnexoII\nDetectorSaldoFinal\nDetectorHabilitacaoHerdeiros\nDetectorTermosJuridicos\nLLM Gemini + OpenAI]
    DET -->|OCR falha| OCR_ERR[(process_tracking\nOCR_ERRO\n+ MANUAL_PROCESS)]
    DET -->|OCR OK| JSON[JSONs em outputs/json/]

    JSON --> E3{Etapa 3\nTotal JSONs > 0?}
    E3 -->|Não| ERR2([exit 1\nPIPELINE_ERROR])
    E3 -->|Sim| E4[Etapa 4\ningest_all_jsons.py\nPostgreSQL upsert]
    E4 --> E5{Etapa 5\nCOUNT > 0 no banco?}
    E5 -->|Não| ERR3([exit 1\nPIPELINE_ERROR])
    E5 -->|Sim| E6[Etapa 6\nrecalcular_idoso.py]
    E6 --> E7[Etapa 7\nBackup JSONs\nhistorico_processado/]
    E7 --> E8[Etapa 8\nArquivar PDFs\nRevisaDownloads_Processados/]
    E8 --> E9[Etapa 9\ncalc-precatorio-tjsp\nmain.py --cpf]
    E9 --> OK([exit 0\nPIPELINE OK])

    style ERR1 fill:#F44336,color:#fff
    style ERR2 fill:#F44336,color:#fff
    style ERR3 fill:#F44336,color:#fff
    style OK fill:#4CAF50,color:#fff
    style OCR_ERR fill:#FF9800,color:#fff
```

---

## 7. Chatbot Revisa — Máquina de Estados Conversacional

```mermaid
stateDiagram-v2
    [*] --> IDLE : nova mensagem

    IDLE --> AWAITING_EMAIL : mensagem recebida\nregistra CPF
    note right of AWAITING_EMAIL
        Bot: "Informe seu email"
        Timeout: 30 min
    end note

    AWAITING_EMAIL --> AWAITING_CODE : email recebido\ncódigo enviado por email
    note right of AWAITING_CODE
        Bot: "Digite o código enviado"
        Timeout: 15 min
    end note

    AWAITING_CODE --> IDLE : timeout expirado
    AWAITING_CODE --> AWAITING_CONFIRMATION : código correto\nconsulta e-SAJ realizada

    AWAITING_CONFIRMATION --> AWAITING_PAYMENT : cliente confirmou\nchamada /generate-payment-link
    note right of AWAITING_PAYMENT
        Bot: "Link de pagamento enviado"
        Timeout: 60 min
        Estado gravado em consultas_esaj
    end note

    AWAITING_PAYMENT --> PAYMENT_APPROVED : MP webhook approved
    AWAITING_PAYMENT --> PAYMENT_REJECTED : MP webhook rejected
    AWAITING_PAYMENT --> IDLE : timeout expirado

    PAYMENT_REJECTED --> AWAITING_PAYMENT : cliente digita "sim"\nnovo link gerado
```
