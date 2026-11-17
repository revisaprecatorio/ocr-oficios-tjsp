# OCR e Ingestão — Fase 4 por dentro

**Revisado:** 13/11/2026 contra o código do repo `ocr-oficios-tjsp` (branch `main`).

Este documento detalha o que acontece **dentro** das Etapas 2 a 6 do `pipeline_completo.sh` (ver `02_FLUXO_COMPLETO.md`, Fase 4). Substitui, para fins de entendimento do pipeline, o `../AGENTS.md`, que está defasado em vários pontos (ver §7).

---

## 1. Entradas e saídas

| Item | Valor real |
|---|---|
| Chamada | `pipeline_completo.sh {cpf}` (CPF só dígitos), disparado pelo `orchestrator_subprocess.py` do `crawler_tjsp` |
| PDFs de entrada | `C:/temp/RevisaDownloads/{cpf}/{numero_processo_cnj}.pdf` (nome do arquivo = número CNJ) |
| Python | `C:/Users/Administrator/Documents/revisa/ocr-oficios-tjsp/env/Scripts/python.exe` |
| Variáveis (`.env` na raiz) | `GOOGLE_API_KEY` (ou `GEMINI_API_KEY`), `OPENAI_API_KEY`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| JSONs por lote | `1_parsing_PDF/outputs/consultas/lote_NNN/{cpf}_{processo}.json` + CSV do lote + `estatisticas_globais.json` |
| Log por PDF | `1_parsing_PDF/outputs/consultas/logs/*.md` (`TrackerExecucao`) |
| JSONs centralizados | `1_parsing_PDF/outputs/json/` (Etapa 3) → depois movidos para `outputs/historico_processado/{cpf}/{ts}/` (Etapa 7) |
| PDFs processados | movidos para `C:/temp/RevisaDownloads_Processados/{cpf}/{data}_{ts}/` (Etapa 8) |
| Tabela de destino | `esaj_detalhe_processos` (66 colunas físicas), chave lógica `(cpf, numero_processo_cnj)` |

---

## 2. Etapa 2 — `processar_pipeline.py` (V3.1)

`processar_pipeline.py --input C:/temp/RevisaDownloads/{cpf} --output outputs/consultas` encontra os PDFs, processa em **lotes de 5** e chama `ProcessadorOficio.processar_arquivo(pdf, cpf)` para cada um. O CPF vem da pasta do PDF (ou da pasta-avó, se o PDF estiver em subpasta temporária).

Só PDFs com `sucesso=True` geram JSON. PDFs que falham **não derrubam o pipeline**: geram registro de falha (§4) e o pipeline segue com os demais.

### 2.1 Passos dentro de `ProcessadorOficio.processar_arquivo` (`app/processador.py`)

| # | Passo | Componente | Falha → |
|---|---|---|---|
| 1 | Validar PDF (PyMuPDF) | `DetectorOficio.validar_pdf` | retorna `None` (sem JSON, sem tracking) |
| 1.1 | Marcar "PDF antigo" se o número começa com `7` (formato `7xxxxxx-xx.20xx`) | — | só observação |
| 1.5 | **Indexar todos os ANEXOS II por CPF** antes de procurar o ofício | `DetectorAnexoII.indexar_anexos_por_cpf` | CPF esperado ausente do índice → **falha** ("ANEXO II encontrado... nenhum pertence ao CPF" ou "Nenhum ANEXO II detectado") |
| 2 | Localizar todos os ofícios no PDF | `DetectorOficio.buscar_todos_oficios` | nenhum → **falha** "Nenhum ofício detectado" |
| 3 | Escolher o ofício que contém o CPF; fallbacks: busca direta por CPF (PDF com 100+ ofícios) e **multi-credor** (usa o ofício imediatamente anterior ao ANEXO II do CPF) | `DetectorOficio.validar_cpf_no_oficio` / `extrair_oficio_por_cpf` | nenhum → **falha** "CPF ... não encontrado" |
| 3.1 | Termos jurídicos no texto completo do PDF | `DetectorTermosJuridicos.detectar_termos` | — |
| 3.2 | Habilitação de herdeiros / óbito | `DetectorHabilitacaoHerdeiros.detectar` | — |
| 4 | Recortar a seção do credor no ANEXO II | `DetectorAnexoII.extrair_secao_credor_no_anexo` | — |
| 5 | Número de ordem no título (PDFs antigos) | `DetectorProcessamento.extrair_numero_ordem_do_titulo` | — |
| 6 | **Rejeição primeiro** ("NOTA DE REJEIÇÃO"); se não rejeitado, buscar PROCESSAMENTO/certidão e número de ordem; fallback global no PDF | `DetectorProcessamento.detectar_rejeicao` / `detectar_processamento` / `buscar_numero_ordem_global` | — |
| 7–8.5 | Montar texto **só com as páginas relevantes** (ofício + ANEXO II + PROCESSAMENTO/rejeição), pré-extrair campos por regex, normalizar valores (`R$ 62.606,38` → `R$ 62606.38`) | `DetectorAnexoII.pre_extrair_dados_com_regex` | — |
| 9 | **LLM híbrido** (§3) com o CPF esperado no prompt | `_extrair_dados_llm_hibrido` | ambos LLMs falham → **falha** "Falha na extração LLM" |
| 9.1 | Regex sobrescreve LLM quando encontrou valor; vara detectada por regex entra se o LLM não trouxe | — | — |
| 9.2 | **CPF extraído ≠ CPF esperado** → descarta (credor errado em PDF multi-credor) | — | **falha** "CPF mismatch" |
| 9.3 | Alertas de sanidade de valores (só log) | `_validar_sanidade_valores` | — |
| 10 | Validação Pydantic `OficioRequisitorio` (com correção de tipos e nova tentativa) | `app/schemas.py` | erro → resultado com `sucesso=False` |
| 11 | Derivados: `idoso` (≥ 60 anos por `data_nascimento`), `preferencial`, `habilitacao_herdeiros`, `doenca_grave`, `obito`, `data_obito`, `cpf_sucessor` (zerado se igual ao CPF do credor) | — | — |
| 12 | Garantir `saldo_final` + `data_saldo_final` com origem | `DetectorSaldoFinal.extrair_saldo_e_data_com_origem` | fallback (§2.3) |
| 13 | `observacoes`: "PDF antigo", "Campos não extraídos: ..."; `banco/agencia/conta` vazios viram `"ERRO"`; `credor_cpf_cnpj` vazio vira `"ERRO"` | — | — |

> O `ProcessadorOficio` **não grava** em `esaj_detalhe_processos` (`salvar_postgres()` não é implementado). Quem grava é a Etapa 4.

### 2.2 Detectores (`1_parsing_PDF/app/`)

| Detector | Regra principal |
|---|---|
| `DetectorOficio` (`detector.py`) | Página inicia ofício com **≥ 2 de 3 critérios**: (1) score ≥ 6 em título/cabeçalho/vara da Fazenda/"VALOR GLOBAL DA REQUISIÇÃO"/"CREDOR(S):"; (2) número CNJ `\d{7}-\d{2}.\d{4}.\d.\d{2}.\d{4}`; (3) endereçamento "AO EXCELENTÍSSIMO SENHOR", "AO JUÍZO DA" etc. Páginas com termos de rejeição de documento valem 0. |
| `DetectorAnexoII` (`detector_anexo.py`) | Indexa ANEXOS II por CPF (CPF formatado, nome do credor, tipo); recorta a seção do credor; pré-extrai banco/agência/conta/valores por regex. |
| `DetectorProcessamento` (`detector_processamento.py`) | "NOTA DE REJEIÇÃO" tem prioridade máxima (→ `rejeitado=true` + `motivo_rejeicao`, truncado em 500 chars); senão PROCESSAMENTO/certidão com `numero_ordem`. |
| `DetectorSaldoFinal` (`detector_saldo_final.py`, V3.0.0) | Padrões em ordem: `saldo_apos_pagamento` → `saldo_final_em` → `valores_para_pagamento` → `saldo_final_generico`, isolando o contexto do credor pelo CPF. Grava `origem_saldo_final` / `origem_data_saldo_final`. |
| `DetectorHabilitacaoHerdeiros` | Código de petição **9270** (alta confiança), indicadores de óbito + CPF sucessor (média), um indicador só (baixa). Retorna `obito`, `data_obito`, `cpf_sucessor`. |
| `DetectorTermosJuridicos` | `preferencial` por regex; `doenca_grave` **só se a resposta for "Sim"** em "Portador de doença grave: Sim/Não" (V2.7.6); `habilitacao_herdeiros` exige CPF do credor. `cessao_credito` desativado. |

### 2.3 Saldo final — hierarquia (`_garantir_saldo_final_e_data`, nunca sai `None`)

| `saldo_final` (ordem) | `origem_saldo_final` |
|---|---|
| 1. Valor já extraído pelo LLM | `llm_extraction` |
| 2. Regex do `DetectorSaldoFinal` isolado pelo CPF | `saldo_apos_pagamento`, `saldo_final_em`, `valores_para_pagamento` ou `saldo_final_generico` |
| 3. `valor_total_requisitado` | `fallback_valor_total_requisitado` |
| 4. `valor_principal_bruto + juros_moratorios` | `fallback_principal_bruto_mais_juros` |
| 5. `valor_principal_liquido + juros_moratorios` | `fallback_principal_liquido_mais_juros` |
| 6. `0.00` e `anomalia=true` | `fallback_zero_erro` |

| `data_saldo_final` (ordem) | `origem_data_saldo_final` |
|---|---|
| 1. Data do bloco encontrado pelo regex | origem do padrão |
| 2. `data_base_atualizacao` | `fallback_data_base_atualizacao` |
| 3. Data genérica de atualização no documento | `fallback_data_atualizacao_documento` |
| 4. `1900-01-01` e `anomalia=true` | `fallback_data_sentinela_1900_01_01` |

Na ingestão (§5) há mais uma rede: se `saldo_final`, `valor_principal_liquido` ou `valor_principal_bruto` chegarem vazios e houver `valor_total_requisitado > 0`, recebem o total.

---

## 3. LLM híbrido (`app/llm_adapter.py`)

| Ordem | Modelo | Configuração |
|---|---|---|
| 1º | **`gemini-2.5-flash`** (Google) | `response_mime_type=application/json`, `max_output_tokens=8192` |
| Fallback | **`gpt-4o-mini`** (OpenAI) | usado se o Gemini falhar (quota/429, safety filter, JSON inválido) ou se não houver `GOOGLE_API_KEY` |

- O mesmo prompt (`_construir_prompt_llm`) vai para os dois. Inclui: aviso se há ANEXO II/PROCESSAMENTO, dicas de `numero_ordem` (título/global), flag e motivo de rejeição e, desde a V3.1, um **bloco de identificação do credor pelo CPF esperado** (isolamento em PDFs multi-credor).
- Só as páginas relevantes vão ao LLM, nunca o PDF inteiro.
- Depois da resposta, `_verificar_e_corrigir_tipos` converte valores monetários em número; na validação Pydantic, `banco`/`agencia`/`conta` numéricos viram texto.

---

## 4. Falhas por PDF → `MANUAL_PROCESS` + `OCR_ERRO`

Quando um PDF cai em uma das falhas marcadas na tabela §2.1, `_criar_resultado_erro` faz três coisas:

1. `UPDATE consultas_esaj SET current_state='MANUAL_PROCESS'` para o CPF cuja `processos->'lista'` contém aquele número.
2. `INSERT process_tracking` com `etapa='OCR'`, `evento='OCR_ERRO'`, `erro=true`, `mensagem_erro` (até 500 chars), `detalhes={"processo", "node":"OCR Pipeline", "workflow":"processar_pipeline"}`.
3. Em várias falhas, também `INSERT logs (processo='OCR')` com a mensagem.

O pipeline segue. Se ao final o orchestrator receber `exit 0`, ele sobrescreve o estado com `REPORT_SENT`; o laudo sai parcial (o processo com falha fica "Não Processado" no `Check Processamento Completo`). Ver Cenários C1/C2/C3 em `03_CENARIOS_E_TABELAS.md`.

---

## 5. Etapa 4 — `2_ingestao/scripts/ingest_all_jsons.py` (V7)

Chamada: `ingest_all_jsons.py --input ../1_parsing_PDF/outputs/json --db-host ... --db-port ... --db-name ... --db-user ... --cpf {cpf}` (senha via `DB_PASSWORD`/`DB_PASS` do `.env`). `--cpf` é **obrigatório**.

- `cpf` gravado = o CPF da execução (não o do JSON). `numero_processo_cnj` = parte do nome do arquivo depois de `{cpf}_`.
- Para cada JSON: `SELECT` por `(cpf, numero_processo_cnj)` → **UPDATE** se existe, **INSERT** se não. Commit por arquivo; erro → rollback só daquele arquivo.
- **Não há TRUNCATE** nem DELETE na ingestão. A limpeza de dados antigos do CPF acontece no `Mercado Pago Unified` quando o pagamento é aprovado.
- **UPDATE com `COALESCE`** para identificação (origem, vara, ordem, credor, devedor, datas de nascimento etc.): valor vazio no JSON não apaga o que já existe. **Sobrescreve sempre** valores financeiros, saldo final e origens, dados bancários, flags (`rejeitado`, `doenca_grave`, `idoso`, `pcd`, `preferencial`, `obito`), `motivo_rejeicao`, `observacoes`, `caminho_pdf`, `timestamp_ingestao`.
- Limpeza: moeda (`R$ 1.500,00` → `1500.00`) e datas para ISO.
- O INSERT ainda preenche colunas que o `AGENTS.md` dá como "removidas na V3.0" — elas **existem fisicamente** no banco (66 colunas) e ficam majoritariamente nulas.

> `ingest_v3_0.py` e `ingest_all_jsons_1301_550.py` existem no repo, mas **não são chamados** pelo pipeline de produção.

## 6. Etapas 5 e 6

- **Etapa 5:** `SELECT count(*) FROM esaj_detalhe_processos WHERE cpf = {cpf}`. Zero → `exit 1` → `PIPELINE_ERROR`.
- **Etapa 6:** `recalcular_idoso.py` faz `UPDATE ... SET idoso=TRUE WHERE data_nascimento <= CURRENT_DATE - 60 anos AND idoso=FALSE` na **tabela inteira**. Nunca desmarca.

---

## 7. Onde o `../AGENTS.md` diverge da produção

| `AGENTS.md` diz | Realidade |
|---|---|
| Gemini `gemini-2.0-flash-exp` | `gemini-2.5-flash` |
| Pipeline em 6 etapas com **TRUNCATE** automático | 9 etapas + 9b, por CPF, **sem TRUNCATE** |
| Ingestão via `ingest_v3_0.py` | `ingest_all_jsons.py` (V7) |
| Schema com 35 colunas | 66 colunas físicas |
| 34 testes / 88% | 92 testes, 80 passando (13/11/2026) |

Para entender o pipeline, use esta pasta (`assessment_pipeline/`).
