# AGENTS.md

**Sistema OCR - Ofícios Requisitórios TJSP**

Sistema de extração automatizada de dados de Ofícios Requisitórios do TJSP a partir de PDFs nativos para banco PostgreSQL.

**Versão Atual:** V3.0 (13/12/2025)
**Última Atualização:** 13/12/2025

---

## Dev environment tips

- Use Python 3.11+ com venv: `python3 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Estrutura de pastas: `./data/consultas/{cpf_numerico}/{numero_processo_cnj}.pdf`
- Pasta base padrão: `data/consultas/` no diretório do projeto
- O nome do CPF = apenas números (sem pontos/traços)
- O nome do arquivo = número do processo CNJ
- Configure `.env` com GOOGLE_API_KEY (primary), OPENAI_API_KEY (fallback) e credenciais PostgreSQL

---

## Project structure V3.0

```
3_OCR/
├── 1_parsing_PDF/           # ETAPA 1: PDFs → JSONs
│   ├── app/
│   │   ├── detector.py                  # DetectorOficio - localiza ofício
│   │   ├── detector_anexo.py            # DetectorAnexoII - dados bancários
│   │   ├── detector_processamento.py    # DetectorProcessamento - número ordem
│   │   ├── detector_saldo_final.py      # V2.5.2: Saldo Final
│   │   ├── detector_habilitacao_herdeiros.py  # V2.5.3: Código 9270
│   │   ├── detector_termos_juridicos.py # V2.5.3: Preferencial, doença grave
│   │   ├── llm_adapter.py               # Modo Híbrido: Gemini + OpenAI
│   │   ├── processador.py               # ProcessadorOficio V3.0
│   │   ├── schemas.py                   # Pydantic models (35 campos)
│   │   └── tracker_execucao.py          # Logs Markdown
│   ├── tests/                          # 34 testes unitários (88%)
│   ├── outputs/
│   │   ├── consultas/                  # JSONs processados
│   │   └── json/                       # JSONs centralizados
│   └── processar_pipeline.py           # Script principal
│
├── 2_ingestao/              # ETAPA 2: JSONs → PostgreSQL
│   ├── scripts/
│   │   ├── ingest_v3_0.py              # Importação V3.0 (35 campos)
│   │   └── recalcular_idoso.py         # Recálculo tag idoso
│   └── sql/
│       ├── 01_create_table.sql         # Schema V3.0 (35 colunas)
│       └── 05_migrate_to_v3_0.sql      # Migration V2.7.6 → V3.0
│
├── historico_arquivado/     # Arquivos históricos V2.7.x
│   ├── scripts/             # 17 scripts obsoletos
│   ├── outputs/             # 2 outputs antigos
│   ├── sql/                 # 5 migrations antigas
│   └── docs/                # 9 documentações antigas
│
├── 3_streamlit/             # ETAPA 3: Interface Web
│   └── app/streamlit_app.py
│
├── data/consultas/          # PDFs originais
│   ├── 12345678909/         # CPF sem formatação
│   │   └── 0035938-67.2018.8.26.0053.pdf
│   └── 98765432100/
│       └── 7654321-12.2023.8.26.0053.pdf
│
├── pipeline_completo.sh     # Pipeline automatizado V2.6.0
├── .env                     # Variáveis de ambiente
└── requirements.txt         # Dependências (tqdm, tabulate, etc.)
```

---

## Components Architecture V3.0

### **1. DetectorOficio** (Core)
Identifica páginas do ofício dentro do PDF usando **3 critérios**:
1. **Keywords:** "OFÍCIO REQUISITÓRIO", "OFICIO REQUISITORIO", "VARA DA FAZENDA PÚBLICA"
2. **Padrão CNJ:** `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
3. **Estrutura:** "AO JUÍZO DA ... VARA"

**Lógica:** Mínimo **2/3 critérios** para detectar início do ofício.

### **2. DetectorAnexoII** (V2.4.0 - Dados Bancários)
Detecta páginas "ANEXO II" com validação robusta:
- ✅ CPF formatado (XXX.XXX.XXX-XX)
- ✅ Estrutura de credor ("Credor nº" + Nome)
- ✅ Valores monetários (R$ + Valor Total/Requisitado)
- ✅ Exclusão de DECISÕES judiciais e ÍNDICES
- **Impacto:** 90% redução de falsos positivos

### **3. DetectorProcessamento** (Aceite/Rejeição)
Busca seção "PROCESSAMENTO" após ANEXO II:
- Extrai `numero_ordem` com regex: `(\d{5,6}/\d{4})`
- Define `rejeitado = FALSE` se número de ordem encontrado
- Define `rejeitado = TRUE` se "SEM INFORMAÇÃO"

### **4. DetectorSaldoFinal** (V2.5.2)
Extrai saldo final após pagamento:
- **Regex primário:** `Saldo\s+(?:Líquido\s+)?Final.*?R?\$?\s*([\d.,]+)`
- **Fallback:** `saldo_final = valor_total_requisitado`
- **Cobertura:** 100% dos registros

### **5. DetectorHabilitacaoHerdeiros** (V2.5.3 - Código 9270)
Detecta habilitação de herdeiros em precatórios:
- **Alta confiança:** Código 9270 + estrutura completa
- **Média confiança:** 2+ indicadores (óbito + CPF sucessor)
- **Baixa confiança:** 1 indicador apenas
- **Extrai:** `obito` (bool), `data_obito` (date), `cpf_sucessor` (varchar 14)

### **6. DetectorTermosJuridicos** (V2.5.3)
Detecta termos jurídicos especiais:
- ✅ `preferencial` (bool) - Credor preferencial
- ✅ `doenca_grave` (bool) - Moléstia grave, laudo médico, CID-10
- ❌ `cessao_credito` (bool) - **DESATIVADO** (sempre FALSE)

---

## Stack and dependencies

### **Extração de texto:**
- **Use:** `pymupdf>=1.23.0` (PyMuPDF) - única lib para PDFs nativos
- **Não use:** pypdf, OCR ou outros extractors
- PDFs são sempre nativos/digitais

### **LLM para extração estruturada (Modo Híbrido V2.5.0):**

**Primary (96% dos casos):**
- **Model:** `gemini-2.0-flash-exp` (Google Gemini)
- **Context:** 1M tokens (60x maior que GPT-4o-mini)
- **Pricing:** **GRÁTIS** (tier grátis generoso)
- **Import:** `import google.generativeai as genai`

**Fallback (4% dos casos):**
- **Model:** `gpt-4o-mini` (OpenAI)
- **Pricing:** $0.150/1M input tokens, $0.600/1M output tokens
- **Import:** `from openai import OpenAI`
- **Uso:** Quando Gemini falha ou não configurado

**Economia:** 93% vs OpenAI solo (~$2/1000 PDFs vs $30/1000)

### **Validação:**
- `pydantic>=2.5.0` para schemas
- Valide: formato CNJ, CPF/CNPJ, OAB
- Normalize: datas (ISO), valores (decimal)

### **Database:**
- PostgreSQL com tabela `esaj_detalhe_processos` (35 colunas)
- Primary key: `id` (SERIAL)
- Unique constraint: `cpf, numero_processo_cnj`
- Use upsert: `ON CONFLICT (cpf, numero_processo_cnj) DO UPDATE`
- V3.0: 15 colunas removidas (0% preenchimento)

### **Utilities:**
- `tqdm>=4.67.0` - Progress bars
- `tabulate>=0.9.0` - Tabelas formatadas

---

## Environment variables

```bash
# Google Gemini (Primary - Grátis)
GOOGLE_API_KEY=AIza...

# OpenAI (Fallback)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# PostgreSQL (VPS)
DB_HOST=72.60.62.124
DB_PORT=5432
DB_NAME=n8n
DB_USER=admin
DB_PASSWORD=BetaAgent2024SecureDB

# Base directory (padrão: data/consultas no projeto)
BASE_DIR=./data/consultas
```

---

## Running the system V3.0

### **Pipeline Automatizado (Recomendado):**

```bash
# Executar pipeline completo (6 etapas)
./pipeline_completo.sh
```

**Etapas executadas automaticamente:**
1. ✅ Limpa outputs antigos (`outputs/consultas/`, `outputs/json/`)
2. ✅ Processa todos os PDFs (`processar_pipeline.py`)
3. ✅ **TRUNCATE automático do banco PostgreSQL** (V3.0)
4. ✅ Importa JSONs para PostgreSQL (`ingest_v3_0.py`)
5. ✅ Valida resultados (incluindo campos V2.5.3)
6. ✅ Recalcula tag idoso (idade >= 60 anos)

### **Execução Manual (Etapa por Etapa):**

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ETAPA 1: Extração PDFs → JSONs
cd 1_parsing_PDF
python3 processar_pipeline.py --input ../data/consultas --output outputs/consultas

# ETAPA 2: Importação JSONs → PostgreSQL
cd ../2_ingestao/scripts
python3 ingest_all_jsons.py --input ../../1_parsing_PDF/outputs/json

# ETAPA 3: Interface Streamlit
cd ../../3_streamlit
streamlit run app/streamlit_app.py
```

---

## Schema PostgreSQL V3.0 (35 colunas)

**Tabela:** `esaj_detalhe_processos`

**Primary Key:** `id` (SERIAL)
**Unique:** `cpf, numero_processo_cnj` (UNIQUE CONSTRAINT)

**V3.0 Changes:** Removed 15 unused columns (0% fill rate)

### **Campos Principais:**

**Identificação (5 campos):**
- `cpf` (VARCHAR 11) - CPF do credor
- `numero_processo_cnj` (VARCHAR 30) - Número CNJ
- `processo_origem` (VARCHAR 30) - Número do processo origem
- `numero_ordem` (VARCHAR 15) - Número de ordem do ofício
- `vara` (VARCHAR 200) - Vara judicial
-- V3.0 REMOVED: processo_execucao, processo_conhecimento (0% filled)

**Partes (3 campos):**
- `credor_nome` (VARCHAR 200)
- `credor_cpf_cnpj` (VARCHAR 18)
- `devedor_ente` (VARCHAR 200)
-- V2.7.2 REMOVED: requerente_caps
-- V2.7.1 REMOVED: advogado_nome, advogado_oab
-- V3.0 REMOVED: cpf_titular_conta, tipo_levantamento, dados_bancarios_advogado (0% filled)

**Dados Bancários (3 campos):**
- `banco` (VARCHAR 100)
- `agencia` (VARCHAR 20)
- `conta` (VARCHAR 30)
-- V3.0 REMOVED: conta_tipo, tipo_levantamento, dados_bancarios_advogado, cpf_titular_conta (0% filled)

**Valores Financeiros (5 campos):**
- `valor_principal_bruto` (NUMERIC 15,2)
- `valor_principal_liquido` (NUMERIC 15,2)
- `juros_moratorios` (NUMERIC 15,2)
- `valor_total_requisitado` (NUMERIC 15,2)
- `saldo_final` (NUMERIC 15,2) - **V2.5.2**
-- V3.0 REMOVED: contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_compensado,
--              contribuicao_social, salario_pericial, assist_tecnico, custas, despesas, multas (0% filled)

**Datas (2 campos):**
- `data_base_atualizacao` (DATE)
- `data_nascimento` (DATE)
-- V2.7.1 REMOVED: data_ajuizamento, data_transito_julgado

**Óbito e Sucessão V2.5.3 (3 campos):**
- `obito` (BOOLEAN DEFAULT FALSE)
- `data_obito` (DATE)
- `cpf_sucessor` (VARCHAR 14)

**Preferências (3 campos):**
- `idoso` (BOOLEAN DEFAULT FALSE)
- `doenca_grave` (BOOLEAN DEFAULT FALSE) - **V2.5.3**
- `pcd` (BOOLEAN DEFAULT FALSE)

**Termos Jurídicos (2 campos):**
- `preferencial` (BOOLEAN DEFAULT FALSE)
- `habilitacao_herdeiros` (BOOLEAN DEFAULT FALSE) - **V2.5.3**
-- V2.7.1 REMOVED: cessao_credito (always FALSE)

**Controle de Processamento (5 campos):**
- `rejeitado` (BOOLEAN)
- `motivo_rejeicao` (TEXT)
- `observacoes` (TEXT)
- `anomalia` (BOOLEAN)
- `descricao_anomalia` (TEXT)

**Metadados (2 campos):**
- `caminho_pdf` (TEXT)
- `timestamp_ingestao` (TIMESTAMP DEFAULT NOW())

**TOTAL: 35 colunas essenciais (V3.0)**

---

## Code conventions

### **ProcessadorOficio V3.0:**
Pipeline completo em 7 passos:

```python
class ProcessadorOficio:
    def processar_v2(pdf_path, cpf_esperado):
        # 1. Detectar todos os ofícios no PDF
        oficios = detector.buscar_todos_oficios(pdf_path)

        # 2. Encontrar ofício com CPF esperado
        oficio_cpf = encontrar_oficio_com_cpf(oficios, cpf_esperado)

        # 3. Detectar termos jurídicos (V2.5.3)
        termos = detector_termos.detectar_termos(texto_pdf_completo)
        habilitacao = detector_herdeiros.detectar(texto_pdf_completo)

        # 4. Detectar ANEXO II
        anexo_pagina = detector_anexo.detectar(pdf_path, oficio_cpf)

        # 5. Buscar seção do credor
        secao_credor = extrair_secao_credor(anexo_pagina, cpf_esperado)

        # 6. Detectar PROCESSAMENTO
        processamento = detector_processamento.buscar(pdf_path, anexo_pagina)

        # 7. Extração LLM (Modo Híbrido)
        dados = extrair_dados_llm_hibrido(
            texto_oficio=oficio_cpf['texto'],
            secao_anexo=secao_credor,
            secao_processamento=processamento
        )

        # 8. Validação Pydantic
        oficio_validado = OficioRequisitorio(**dados)

        # 9. Detectar Saldo Final (V2.5.2)
        saldo_final = detector_saldo.detectar(processamento) or dados['valor_total_requisitado']

        # 10. Salvar JSON
        salvar_json(cpf, processo, oficio_validado, saldo_final, termos, habilitacao)
```

### **LLM extraction (Modo Híbrido):**

```python
def _extrair_dados_llm_hibrido(texto_oficio, secao_anexo, secao_processamento):
    # 1ª tentativa: Gemini 2.5 Flash (grátis)
    if os.getenv('GOOGLE_API_KEY'):
        try:
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            dados = json.loads(response.text)
            return dados
        except Exception as e:
            logger.warning(f"Gemini falhou: {e}, usando fallback OpenAI")

    # Fallback: GPT-4o-mini
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    dados = json.loads(response.choices[0].message.content)
    return dados
```

### **Pydantic validation:**

```python
from pydantic import BaseModel, Field, field_validator

class OficioRequisitorio(BaseModel):
    # Obrigatórios
    processo_origem: str = Field(..., pattern=r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    # Financeiros (V3.0: 5 campos essenciais)
    valor_principal_liquido: Optional[Decimal] = None
    valor_principal_bruto: Optional[Decimal] = None
    juros_moratorios: Optional[Decimal] = None
    valor_total_requisitado: Optional[Decimal] = None
    saldo_final: Optional[Decimal] = None  # V2.5.2

    # Óbito e Sucessão V2.5.3
    obito: bool = False
    data_obito: Optional[date] = None
    cpf_sucessor: Optional[str] = None

    # Termos Jurídicos V2.5.3
    preferencial: bool = False
    doenca_grave: bool = False
    habilitacao_herdeiros: bool = False
    # V2.7.1: cessao_credito removed

    # V3.0: 15 campos removidos (0% preenchimento)

    @field_validator('banco', 'agencia', 'conta', mode='before')
    def convert_int_to_str(cls, value):
        # Gemini às vezes retorna int ao invés de str
        if isinstance(value, int):
            return str(value)
        return value
```

---

## Testing V3.0

### **Infraestrutura:**

```
1_parsing_PDF/tests/
├── pytest.ini                          # Configuração pytest
├── conftest.py                         # Fixtures compartilhadas
├── test_detector_habilitacao_herdeiros_v253.py  # 17 testes
└── test_detector_termos_juridicos_v253.py       # 17 testes
```

### **Executar testes:**

```bash
cd 1_parsing_PDF

# Todos os testes
pytest tests/ -v

# Apenas V2.5.3
pytest tests/ -v -m v253

# Com coverage
pytest tests/ --cov=app --cov-report=html
```

### **Resultados V3.0 (baseado em V2.7.6):**
- **Total:** 34 testes, 30 passando **(88% success rate)**
- **DetectorHabilitacaoHerdeiros:** 13/17 passando (76%)
- **DetectorTermosJuridicos:** 17/17 passando (100%)
- **V3.0:** Schema cleanup não afeta testes (apenas remoção de colunas não usadas)

**Teste crítico:** Detector deve encontrar ofício em qualquer posição do PDF (primeira, última ou meio do documento).

---

## Do's V3.0

✅ Use pasta `data/consultas/` no diretório do projeto como base padrão
✅ Use apenas `pymupdf` para extração de texto
✅ Use **Modo Híbrido:** Gemini 2.5 Flash (primary) + GPT-4o-mini (fallback)
✅ Configure `GOOGLE_API_KEY` para 93% economia de custos
✅ Detecte ofício com mínimo 2/3 critérios
✅ Envie apenas páginas do ofício para o LLM (não o PDF inteiro)
✅ Valide todos os dados com Pydantic antes de salvar
✅ Use upsert para evitar duplicatas: `ON CONFLICT (cpf, numero_processo_cnj) DO UPDATE`
✅ Normalize valores: sem R$, sem pontos de milhar, vírgula = ponto decimal
✅ Normalize datas: sempre YYYY-MM-DD
✅ Calcule preferências: `idoso` se ≥60 anos
✅ Execute **TRUNCATE antes de ingestão** para evitar duplicatas
✅ Use `pipeline_completo.sh` ou `ingest_v3_0.py` para execução automatizada
✅ Gere logs Markdown com `TrackerExecucao` (V2.5.3)
✅ Detecte Saldo Final com fallback para `valor_total_requisitado` (V2.5.2)
✅ Detecte habilitação de herdeiros com código 9270 (V2.5.3)
✅ V3.0: Foco em 35 campos essenciais (0% preenchimento removido)

---

## Don'ts

❌ Não use fallback pypdf ou outros extractors
❌ Não use OCR (PDFs são nativos)
❌ Não use apenas OpenAI (configure Gemini para economia)
❌ Não envie o PDF inteiro para o LLM (apenas páginas do ofício)
❌ Não assuma estrutura fixa (ofício pode estar em qualquer página)
❌ Não hardcode valores ou paths
❌ Não ignore erros de validação
❌ Não duplique registros (use upsert com `processo_origem`)
❌ Não deixe campo obrigatório `processo_origem` vazio
❌ Não use tabela `lista_processos` (use `esaj_detalhe_processos`)
❌ Não use modelo `gpt-5-nano` (não existe, use `gpt-4o-mini`)
❌ Não processe sem TRUNCATE (pode gerar duplicatas)
❌ Não use constraint antiga `processo_origem` (use `cpf, numero_processo_cnj`)
❌ Não referencie 15 campos removidos V3.0 (processo_execucao, conta_tipo, custas, etc.)

---

## GPT-4o-mini / Gemini 2.5 Flash prompt template

```python
prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo
FORMATO: JSON válido

CAMPOS OBRIGATÓRIOS:
- processo_origem: Número CNJ (0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS

CAMPOS OPCIONAIS:
- vara, processo_execucao, processo_conhecimento
- datas (YYYY-MM-DD): data_ajuizamento, data_transito_julgado, data_base_atualizacao, data_nascimento
- partes: advogado_nome, advogado_oab (OAB/UF 000.000), credor_nome, credor_cpf_cnpj, devedor_ente
- financeiro (números puros): valor_principal_liquido, valor_principal_bruto, juros_moratorios,
  contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_total_requisitado
- bancário: banco, agencia, conta, variacao
- preferências (bool): idoso, doenca_grave, pcd

REGRAS:
- Campos não encontrados = null
- Valores numéricos sem R$, sem pontos de milhar
- Requerente SEMPRE em MAIÚSCULAS
- Banco/agência/conta sempre como STRING (não número)

DOCUMENTO:
{texto_oficio}

ANEXO II (DADOS BANCÁRIOS):
{secao_anexo}

PROCESSAMENTO:
{secao_processamento}

Retorne APENAS JSON válido:"""
```

---

## Performance targets V3.0

### **Tempo de Processamento:**
- **Extração de texto (PyMuPDF):** <0.1s por PDF
- **Detecção de ofício:** <0.2s
- **Detecção ANEXO II:** <0.3s
- **LLM extraction (modo híbrido):** 0.5-1s
- **Validação + DB:** <0.05s
- **Total:** **~8.8s por processo** (baseado em V2.7.6)

### **Custo (Modo Híbrido):**
- **Gemini 2.5 Flash:** 96% PDFs → **$0.00** (grátis)
- **GPT-4o-mini:** 4% PDFs → ~$0.002 por PDF
- **Total:** ~$2/1000 PDFs
- **Economia:** 93% vs OpenAI solo ($30/1000 PDFs)

### **Taxa de Sucesso:**
- **V2.7.6 (stable baseline):** 100% (15/15 PDFs testados)
  - Fix V2.7.5: numero_ordem detection
  - Fix V2.7.6: doenca_grave false positives
- **V3.0:** 100% (schema cleanup mantém todos os fixes)
  - Query performance esperado: +20-30% (menos colunas)

---

## Debugging tips

```python
# Ver texto extraído do ofício
print(f"Páginas: {paginas_oficio}")
print(f"Texto: {texto_oficio[:500]}...")

# Ver JSON do LLM
import json
print(json.dumps(dados_raw, indent=2, ensure_ascii=False))

# Habilitar logs
import logging
logging.basicConfig(level=logging.INFO)

# Ver logs Markdown (V2.5.3)
cat 1_parsing_PDF/outputs/consultas/logs/{cpf}_{processo}_execution.md

# Verificar TRUNCATE
psql -h HOST -U USER -d DB -c "SELECT COUNT(*) FROM esaj_detalhe_processos;"

# Validar campos V2.5.3
psql -h HOST -U USER -d DB -c "
SELECT obito, data_obito, cpf_sucessor, doenca_grave, habilitacao_herdeiros
FROM esaj_detalhe_processos
WHERE obito = TRUE OR doenca_grave = TRUE
LIMIT 10;
"
```

---

## Common errors and fixes

### **Erro: Ofício não encontrado**
- Verifique se PDF tem palavras-chave: "OFÍCIO REQUISITÓRIO"
- Confirme formato CNJ: padrão `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
- Debug: imprima texto de cada página

### **Erro: Validação Pydantic falha**
- Verifique campos obrigatórios: `processo_origem`, `requerente_caps`
- Confirme formato de datas: YYYY-MM-DD
- Valide padrão CNJ com regex
- Gemini retornando int ao invés de str → Validador automático corrige

### **Erro: Duplicatas no banco**
- Execute `TRUNCATE` antes de ingestão (V2.6.0)
- Use upsert: `ON CONFLICT (processo_origem) DO UPDATE`
- Confirme que unique constraint está em `processo_origem`

### **Erro: Taxa de sucesso baixa**
- V2.6.0 real: 73.3% (11/15 PDFs)
- Principais causas: ValidationError, CPF mismatch
- Próxima versão V2.6.1: melhorias planejadas para 90%+

### **Erro: Gemini API não configurada**
- Configure `GOOGLE_API_KEY` no `.env`
- Sistema usa fallback OpenAI (aumenta custo)
- Economia perdida: $28/1000 PDFs se não usar Gemini

---

## Integration with MCP tools

### **ByteRover workflow:**
```bash
# Retrieve project knowledge
byterover-retrieve-knowledge(query="detector habilitacao herdeiros v2.5.3")

# Store implementation notes
byterover-store-knowledge(
  messages="V2.6.0 pipeline automatizado com TRUNCATE antes de ingestão.
  Schema 53 colunas. Modo Híbrido: Gemini primary + OpenAI fallback (93% economia)."
)
```

---

## References V3.0

- **[README.md](README.md)** - Guia completo V3.0
- **[CHANGELOG.md](CHANGELOG.md)** - Histórico de versões (inclui V3.0)
- **[SCHEMA_TABELA.md](SCHEMA_TABELA.md)** - Schema 35 colunas + queries
- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [PostgreSQL Upsert](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)
- [CNJ Numeração Única](https://www.cnj.jus.br/programas-e-acoes/numeracao-unica/)

---

[byterover-mcp]

You are given two tools from Byterover MCP server, including:

## 1. `byterover-store-knowledge`
You `MUST` always use this tool when:
+ Learning new patterns, APIs, or architectural decisions from the codebase
+ Encountering error solutions or debugging techniques
+ Finding reusable code patterns or utility functions
+ Completing any significant task or plan implementation

## 2. `byterover-retrieve-knowledge`
You `MUST` always use this tool when:
+ Starting any new task or implementation to gather relevant context
+ Before making architectural decisions to understand existing patterns
+ When debugging issues to check for previous solutions
+ Working with unfamiliar parts of the codebase

[byterover-mcp]

[byterover-mcp]

You are given two tools from Byterover MCP server, including
## 1. `byterover-store-knowledge`
You `MUST` always use this tool when:

+ Learning new patterns, APIs, or architectural decisions from the codebase
+ Encountering error solutions or debugging techniques
+ Finding reusable code patterns or utility functions
+ Completing any significant task or plan implementation

## 2. `byterover-retrieve-knowledge`
You `MUST` always use this tool when:

+ Starting any new task or implementation to gather relevant context
+ Before making architectural decisions to understand existing patterns
+ When debugging issues to check for previous solutions
+ Working with unfamiliar parts of the codebase
