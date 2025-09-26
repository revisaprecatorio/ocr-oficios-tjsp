# AGENTS.md

Sistema de extração automatizada de dados de Ofícios Requisitórios do TJSP a partir de PDFs nativos para banco PostgreSQL.

---

## Dev environment tips

- Use Python 3.11+ com venv: `python3.11 -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Estrutura de pastas: `./Processos/{cpf_numerico}/{numero_processo_cnj}.pdf`
- Pasta base padrão: `Processos/` no diretório do projeto
- O nome do CPF = apenas números (sem pontos/traços)
- O nome do arquivo = número do processo CNJ
- Configure `.env` com OPENAI_API_KEY e credenciais PostgreSQL

## Project structure

```
projeto/
├── app/
│   ├── detector.py          # DetectorOficio - localiza ofício no PDF
│   ├── processador.py       # ProcessadorOficio - pipeline completo
│   ├── schemas.py           # Pydantic models para validação
│   └── main.py             # Entry point
├── Processos/              # Pasta base (padrão)
│   ├── 12345678909/        # CPF sem formatação
│   │   ├── 0035938-67.2018.8.26.0053.pdf
│   │   └── 0158003-37.2025.8.26.0500.pdf
│   └── 98765432100/
│       └── 7654321-12.2023.8.26.0053.pdf
└── .env                    # Variáveis de ambiente
```

**Componente-chave:** `DetectorOficio` identifica páginas do ofício dentro do PDF usando 3 critérios:
1. Keywords: "OFÍCIO REQUISITÓRIO", "OFICIO REQUISITORIO", "VARA DA FAZENDA PÚBLICA"
2. Padrão CNJ: `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
3. Estrutura: "AO JUÍZO DA ... VARA"

Mínimo 2/3 critérios para detectar início do ofício.

## Stack and dependencies

**Extração de texto:**
- Use `pymupdf` (PyMuPDF) - única lib para PDFs nativos
- Não use fallbacks ou OCR - PDFs são sempre nativos/digitais

**LLM para extração estruturada:**
- Model: `gpt-5-nano-2025-08-07` (OpenAI)
- Pricing: $0.05/1M input tokens, $0.40/1M output tokens
- Import: `from openai import OpenAI`
- Nunca use Gemini, Claude ou outros modelos

**Validação:**
- `pydantic>=2.5.0` para schemas
- Valide: formato CNJ, CPF/CNPJ, OAB
- Normalize: datas (ISO), valores (decimal)

**Database:**
- PostgreSQL com tabela `lista_processos`
- Primary key: `(cpf, numero_processo)`
- Use upsert (ON CONFLICT DO UPDATE)
- Sempre armazene `texto_completo_oficio`

## Environment variables

```bash
# OpenAI API
OPENAI_API_KEY=sk-...

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=oficios_tjsp
DB_USER=postgres
DB_PASSWORD=your_password

# Base directory (padrão: pasta "Processos" no projeto)
BASE_DIR=./Processos
```

## Running the system

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create DB table
psql -U postgres -d oficios_tjsp -f schema.sql

# Run processor
python -m app.main
```

## Schema PostgreSQL

Tabela `lista_processos` com campos:

**Keys:** cpf (VARCHAR 11), numero_processo (VARCHAR 30)

**Ofício:** vara, processo_execucao, processo_conhecimento, data_ajuizamento, data_transito_julgado, requerente_caps, advogado_nome, advogado_oab

**Financeiro:** valor_principal_liquido, valor_principal_bruto, juros_moratorios, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_total_requisitado, data_base_atualizacao

**Preferências:** idoso (BOOLEAN), doenca_grave (BOOLEAN), pcd (BOOLEAN)

**Controle:** texto_completo_oficio (TEXT), timestamp_processamento, data_envio, processado (BOOLEAN)

## Code conventions

**DetectorOficio:**
- Método principal: `detectar_oficio(pdf_path) -> (List[int], str)`
- Retorna: tupla (páginas_do_oficio, texto_completo)
- Use heurísticas para fim: assinatura + página curta (<500 chars)

**ProcessadorOficio:**
- Pipeline: detectar → extract (LLM) → validar → salvar
- Sempre extraia CPF do nome da pasta
- Sempre extraia número do processo do nome do arquivo
- Se ofício não encontrado, registre erro e continue

**LLM extraction:**
- Modelo: `gpt-5-nano-2025-08-07`
- Prompt: estruturado com schema JSON explícito
- Output: parse JSON do response.choices[0].message.content
- Strip markdown code blocks: `json_str.replace('```json', '').replace('```', '')`

**Pydantic validation:**
- Use `OficioRequisitorio` model
- Campos obrigatórios: `processo_origem`, `requerente_caps`
- Validadores: CNJ pattern, CPF/CNPJ format
- Datas: sempre ISO (YYYY-MM-DD)

## Testing instructions

- Test detector: `python -m pytest tests/test_detector.py`
- Test extractor: `python -m pytest tests/test_processador.py`
- Mock OpenAI API calls em testes
- Use sample PDFs em `tests/fixtures/`

**Teste crítico:** Detector deve encontrar ofício em qualquer posição do PDF (primeira, última ou meio do documento).

## Do's

✅ Use pasta `Processos/` no diretório do projeto como base padrão
✅ Use apenas `pymupdf` para extração de texto
✅ Use `gpt-5-nano-2025-08-07` para extração estruturada
✅ Detecte ofício com mínimo 2/3 critérios
✅ Envie apenas páginas do ofício para o LLM (não o PDF inteiro)
✅ Valide todos os dados com Pydantic antes de salvar
✅ Use upsert para evitar duplicatas: `ON CONFLICT (cpf, numero_processo) DO UPDATE`
✅ Armazene texto completo do ofício para auditoria
✅ Normalize valores: sem R$, sem pontos de milhar, vírgula = ponto decimal
✅ Normalize datas: sempre YYYY-MM-DD
✅ Calcule preferências: idoso se ≥60 anos

## Don'ts

❌ Não use fallback pypdf ou outros extractors
❌ Não use OCR (PDFs são nativos)
❌ Não use Gemini, Claude ou outros LLMs
❌ Não envie o PDF inteiro para o LLM (apenas páginas do ofício)
❌ Não assuma estrutura fixa (ofício pode estar em qualquer página)
❌ Não hardcode valores ou paths
❌ Não ignore erros de validação
❌ Não duplique registros (use upsert)
❌ Não deixe campos obrigatórios vazios (processo_origem, requerente_caps)

## GPT-5 Nano (gpt-5-nano-2025-08-07) prompt template

```python
prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo
FORMATO: JSON válido

CAMPOS OBRIGATÓRIOS:
- processo_origem: Número CNJ (0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS

CAMPOS OPCIONAIS:
- vara, processo_execucao, processo_conhecimento
- datas (YYYY-MM-DD): data_ajuizamento, data_transito_julgado, data_base_atualizacao
- partes: advogado_nome, advogado_oab (OAB/UF 000.000), credor_nome, credor_cpf_cnpj, devedor_ente
- financeiro (números puros): valor_principal_liquido, valor_principal_bruto, juros_moratorios, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_total_requisitado
- preferências (bool): idoso, doenca_grave, pcd

REGRAS:
- Campos não encontrados = null
- Valores numéricos sem R$, sem pontos de milhar
- Requerente SEMPRE em MAIÚSCULAS

DOCUMENTO:
{{texto_oficio}}

Retorne APENAS JSON válido:"""
```

## Performance targets

- **Extração de texto (PyMuPDF):** <0.1s por PDF
- **Detecção de ofício:** <0.2s
- **LLM extraction (gpt-5-nano-2025-08-07):** 0.5-1s
- **Validação + DB:** <0.05s
- **Total:** <1.3s por processo

**Custo (GPT-5 Nano):**
- Ofício médio: ~3k tokens input, ~500 tokens output
- Custo por doc: ~$0.00035
- 1000 docs: ~$0.35

## Debugging tips

```python
# Ver texto extraído do ofício
print(f"Páginas: {paginas_oficio}")
print(f"Texto: {texto_oficio[:500]}...")

# Ver JSON do LLM
import json
print(json.dumps(dados_raw, indent=2))

# Habilitar logs
import logging
logging.basicConfig(level=logging.INFO)
```

## Common errors and fixes

**Erro:** Ofício não encontrado
- Verifique se PDF tem palavras-chave: "OFÍCIO REQUISITÓRIO"
- Confirme formato CNJ: padrão `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
- Debug: imprima texto de cada página

**Erro:** Validação Pydantic falha
- Verifique campos obrigatórios: `processo_origem`, `requerente_caps`
- Confirme formato de datas: YYYY-MM-DD
- Valide padrão CNJ com regex

**Erro:** Duplicatas no banco
- Use upsert: `ON CONFLICT (cpf, numero_processo) DO UPDATE`
- Confirme que primary key está correta

## Integration with MCP tools

**ByteRover workflow:**
```bash
# Retrieve project knowledge
byterover-retrieve-knowledge(query="detector oficio")

# Store implementation notes
byterover-store-knowledge(
  category="implementation",
  content="Detector usa 3 critérios: keywords + CNJ + estrutura vara"
)
```

**Context7 usage:**
```bash
# Get OpenAI API docs
"Implementar extração com gpt-5-nano-2025-08-07. use context7"
"use library /openai/latest"

# Get PyMuPDF docs
"Extrair texto de PDF com PyMuPDF. use library /pymupdf/latest"
```

## Example implementation

```python
from openai import OpenAI
import pymupdf

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Extração com PyMuPDF
doc = pymupdf.open(pdf_path)
texto = "".join(page.get_text() for page in doc)

# Detecção do ofício
paginas_oficio, texto_oficio = detector.detectar_oficio(pdf_path)

# Extração estruturada com GPT-5 Nano
response = client.chat.completions.create(
    model="gpt-5-nano-2025-08-07",
    messages=[{"role": "user", "content": prompt}],
    temperature=0
)

dados = json.loads(response.choices[0].message.content)

# Validação
oficio = OficioRequisitorio(**dados)

# Persistência
salvar_postgres(cpf, numero_processo, oficio.dict(), texto_oficio)
```

## References

- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)
- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [PostgreSQL Upsert](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)
- [CNJ Numeração Única](https://www.cnj.jus.br/programas-e-acoes/numeracao-unica/)