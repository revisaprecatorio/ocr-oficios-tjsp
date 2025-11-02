# 🚀 Guia de Instalação: Sistema OCR V3.0

**Versão:** V3.0  
**Data:** 02/11/2025  
**Ambiente:** Ubuntu VPS + Local Development

---

## 📋 Pré-requisitos

### Sistema Operacional
- Ubuntu 20.04+ (VPS)
- macOS 12+ (Desenvolvimento local)
- Python 3.11+

### Ferramentas Necessárias
- Git
- PostgreSQL 14+
- Python 3.11+
- pip
- virtualenv

---

## 🔧 Instalação

### 1. Clonar Repositório

```bash
git clone https://github.com/revisaprecatorio/ocr-oficios-tjsp.git
cd ocr-oficios-tjsp
```

### 2. Configurar Ambiente Virtual

```bash
# Criar ambiente virtual
python3.11 -m venv .venv

# Ativar ambiente
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

**Principais dependências:**
- `pymupdf` - Extração de texto de PDF
- `openai` - API OpenAI (GPT-4o-mini)
- `google-generativeai` - API Gemini (opcional)
- `pydantic==2.x` - Validação de dados
- `psycopg2-binary` - PostgreSQL
- `python-dotenv` - Variáveis de ambiente

### 4. Configurar Variáveis de Ambiente

Criar arquivo `.env` na raiz do projeto:

```bash
# API Keys
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=AIza...      # Opcional (para Gemini)

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=revisa_db
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui

# Configurações Opcionais
LOG_LEVEL=INFO
CHUNKING_ENABLED=true
```

### 5. Configurar PostgreSQL

```bash
# Conectar ao PostgreSQL
psql -U postgres

# Criar banco de dados
CREATE DATABASE revisa_db;

# Criar tabela (schema no README principal)
\i schema/lista_processos.sql
```

### 6. Testar Instalação

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Testar processador
cd 1_parsing_PDF
python -c "from app.processador import ProcessadorOficio; print('✅ OK')"

# Executar teste simples
python test_processador.py
```

---

## 🔐 Configuração de API Keys

### OpenAI API Key (Obrigatório)

1. Acessar: https://platform.openai.com/api-keys
2. Criar nova chave
3. Adicionar ao `.env`: `OPENAI_API_KEY=sk-proj-...`

### Gemini API Key (Opcional - Recomendado)

1. Acessar: https://makersuite.google.com/app/apikey
2. Criar nova chave
3. Adicionar ao `.env`: `GOOGLE_API_KEY=AIza...`

**Benefício:** Gemini é gratuito e tem contexto de 1M tokens!

---

## 📊 Validação de Instalação

### Checklist

- [ ] Python 3.11+ instalado
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas
- [ ] Arquivo `.env` configurado
- [ ] PostgreSQL configurado e acessível
- [ ] Tabela `lista_processos` criada
- [ ] API Keys válidas
- [ ] Teste de importação OK

### Comando de Validação Completa

```bash
cd 8_erro_parsing-valor/scripts
python validacao_completa.py
```

---

## 🚨 Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'pymupdf'"

**Solução:**
```bash
pip install pymupdf
```

### Erro: "connection to server on socket failed"

**Solução:**
```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql

# Iniciar se necessário
sudo systemctl start postgresql
```

### Erro: "OpenAI API key not found"

**Solução:**
```bash
# Verificar se .env existe
ls -la .env

# Verificar se variável está carregada
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

---

## 📚 Próximos Passos

1. Ler [`DOCUMENTACAO_TECNICA_V3.md`](DOCUMENTACAO_TECNICA_V3.md)
2. Revisar [`GUIA_VISUAL_PIPELINE.md`](GUIA_VISUAL_PIPELINE.md)
3. Consultar [`FAQ_TROUBLESHOOTING.md`](FAQ_TROUBLESHOOTING.md)
4. Executar validação em [`../scripts/validacao_completa.py`](../scripts/validacao_completa.py)

---

**Suporte:** Para dúvidas, consultar documentação técnica completa.

