# 🪟 Deploy Windows Server 2022 - Sistema OCR Ofícios TJSP

Guia completo para deploy e operação do sistema em Windows Server 2022.

---

## 📋 **Pré-requisitos**

### **Software Necessário**

1. **Python 3.11+**
   - Download: https://www.python.org/downloads/windows/
   - ✅ Marcar "Add Python to PATH" durante instalação
   - Testar: `python --version`

2. **Git para Windows** (opcional, para clone do repositório)
   - Download: https://git-scm.com/download/win
   - Testar: `git --version`

3. **PostgreSQL** (se banco for local)
   - Download: https://www.postgresql.org/download/windows/
   - Ou usar banco remoto (recomendado)

### **Acesso Necessário**

- ✅ Chave API OpenAI (GPT-5 Nano)
- ✅ Credenciais PostgreSQL (host, user, password, database)
- ✅ Acesso de administrador no Windows Server

---

## 🚀 **Instalação**

### **Passo 1: Preparar Diretório**

```powershell
# Criar diretório do projeto
cd C:\
mkdir projetos
cd projetos

# Clonar repositório (ou transferir arquivos via RDP/FTP)
git clone https://github.com/seu-usuario/ocr-oficios-tjsp.git
cd ocr-oficios-tjsp
```

### **Passo 2: Configurar Ambiente Python**

```powershell
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
.\venv\Scripts\Activate.ps1

# Se houver erro de execução de scripts:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Atualizar pip
python -m pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt
```

### **Passo 3: Configurar Variáveis de Ambiente**

```powershell
# Copiar template
copy .env.example .env

# Editar .env com Notepad
notepad .env
```

Configurar no `.env`:

```ini
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5-nano-2025-08-07

# PostgreSQL Database
POSTGRES_HOST=seu-servidor-postgres.com
POSTGRES_PORT=5432
POSTGRES_DB=oficios_tjsp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua-senha-segura
```

### **Passo 4: Preparar Estrutura de Dados**

```powershell
# Criar diretórios necessários
mkdir data\consultas
mkdir output
mkdir output\json
mkdir output\logs
mkdir logs
```

**Estrutura esperada dos PDFs:**

```
data\
└── consultas\
    ├── {cpf_11_digitos}\
    │   ├── {numero_processo_cnj}.pdf
    │   └── ...
    └── ...
```

Exemplo real:

```
data\
└── consultas\
    ├── 02174781824\
    │   ├── 0035938-67.2018.8.26.0053.pdf
    │   └── 0176505-63.2021.8.26.0500.pdf
    └── 27308157830\
        └── 0019125-86.2023.8.26.0053.pdf
```

### **Passo 5: Criar Tabelas no PostgreSQL**

```powershell
# Conectar ao PostgreSQL
psql -h seu-servidor -U postgres -d oficios_tjsp

# Executar schema
\i schema.sql

# Ou via arquivo
type schema.sql | psql -h seu-servidor -U postgres -d oficios_tjsp
```

---

## 🧪 **Testes**

### **Teste 1: Compatibilidade Windows**

```powershell
python teste_windows_compat.py
```

Resultado esperado:
```
✓ COMPATIBILIDADE OK PARA WINDOWS SERVER 2022
```

### **Teste 2: Pipeline Completo (3 PDFs)**

```powershell
# Executar teste
.\teste_pipeline_completo.bat
```

Resultado esperado:
```
✓ PIPELINE TESTADO COM SUCESSO!
Total de JSONs gerados: 3
```

---

## 📊 **Operação - Pipeline em 2 Etapas**

### **ETAPA 1: PDFs → JSONs**

```powershell
# Teste com 5 PDFs
python exportar_json.py --input data\consultas --output output --limite 5

# Processamento completo
python exportar_json.py --input data\consultas --output output
```

**Parâmetros:**
- `--input`: Diretório com PDFs (padrão: `data\consultas`)
- `--output`: Diretório de saída (padrão: `output`)
- `--limite`: Número máximo de PDFs (padrão: todos)

**Saídas:**
- `output\json\{cpf}\{processo}.json` - JSON por processo
- `output\estatisticas.json` - Estatísticas gerais
- `output\logs\exportacao_*.log` - Logs detalhados

### **ETAPA 2: JSONs → PostgreSQL**

```powershell
# Teste (dry-run, não altera banco)
python importar_postgres.py --input output\json --dry-run

# Importação real
python importar_postgres.py --input output\json
```

**Parâmetros:**
- `--input`: Diretório com JSONs (padrão: `output\json`)
- `--dry-run`: Simula sem alterar banco
- `--force`: Força reimportação de todos

**Saídas:**
- Logs em `logs\importacao_*.log`
- Dados inseridos/atualizados no PostgreSQL

---

## 📁 **Estrutura de Arquivos Windows**

```
C:\projetos\ocr-oficios-tjsp\
│
├── venv\                           # Ambiente virtual Python
├── app\                            # Código fonte
│   ├── __init__.py
│   ├── detector.py                 # Detecção de ofícios
│   ├── detector_anexo.py           # Detecção ANEXO II (novo)
│   ├── processador.py              # Pipeline principal
│   ├── schemas.py                  # Validação Pydantic
│   └── main.py
│
├── data\                           # Dados de entrada
│   └── consultas\                  # PDFs organizados por CPF
│       └── {cpf}\
│           └── {processo}.pdf
│
├── output\                         # Saídas do processamento
│   ├── json\                       # JSONs gerados
│   │   └── {cpf}\
│   │       └── {processo}.json
│   ├── logs\                       # Logs de exportação
│   └── estatisticas.json           # Estatísticas gerais
│
├── logs\                           # Logs de importação
│
├── exportar_json.py                # ETAPA 1: PDFs -> JSONs
├── importar_postgres.py            # ETAPA 2: JSONs -> PostgreSQL
├── teste_windows_compat.py         # Testes compatibilidade
├── teste_pipeline_completo.bat     # Teste completo (Windows)
│
├── .env                            # Configurações (NÃO versionar!)
├── .env.example                    # Template de configuração
├── requirements.txt                # Dependências Python
├── schema.sql                      # Schema PostgreSQL
└── README.md                       # Documentação principal
```

---

## 🔧 **Manutenção e Monitoramento**

### **Visualizar Logs**

```powershell
# Logs de exportação (últimos 50 linhas)
Get-Content output\logs\exportacao_*.log -Tail 50

# Logs de importação
Get-Content logs\importacao_*.log -Tail 50

# Monitorar em tempo real
Get-Content output\logs\exportacao_*.log -Wait
```

### **Consultar Estatísticas**

```powershell
# Visualizar estatísticas JSON
type output\estatisticas.json | python -m json.tool

# Consultar banco
psql -h servidor -U postgres -d oficios_tjsp -c "SELECT * FROM vw_estatisticas_processamento;"
```

### **Limpeza de Outputs**

```powershell
# Limpar JSONs de teste
rmdir /s /q output_teste

# Limpar logs antigos (manter últimos 7 dias)
forfiles /p output\logs /s /m *.log /d -7 /c "cmd /c del @path"
```

---

## 🔄 **Reprocessamento**

### **Reprocessar PDF Específico**

```powershell
# Deletar JSON existente
del output\json\02174781824\0035938-67.2018.8.26.0053.json

# Reprocessar apenas esse CPF
python exportar_json.py --input data\consultas\02174781824
```

### **Reprocessar Todos (Atualizar Banco)**

```powershell
# 1. Gerar JSONs novos
python exportar_json.py --input data\consultas --output output_novo

# 2. Importar (upsert automático)
python importar_postgres.py --input output_novo\json
```

---

## 📊 **Consultas PostgreSQL Úteis**

```sql
-- Total de registros
SELECT COUNT(*) FROM lista_processos;

-- Processos com ANEXO II
SELECT COUNT(*) FROM lista_processos
WHERE banco IS NOT NULL AND conta IS NOT NULL;

-- Estatísticas gerais
SELECT * FROM vw_estatisticas_processamento;

-- Processos por vara
SELECT * FROM vw_processos_por_vara;

-- Processos com erro de processamento
SELECT cpf, numero_processo, timestamp_processamento
FROM lista_processos
WHERE processado = FALSE;

-- Últimos 10 processados
SELECT cpf, numero_processo, requerente_caps, timestamp_processamento
FROM lista_processos
ORDER BY timestamp_processamento DESC
LIMIT 10;
```

---

## ⚠️ **Troubleshooting Windows**

### **Problema: "python não é reconhecido"**

```powershell
# Verificar instalação
where python

# Se não aparecer, adicionar ao PATH
$env:Path += ";C:\Users\Administrator\AppData\Local\Programs\Python\Python311"

# Ou reinstalar Python marcando "Add to PATH"
```

### **Problema: Erro de encoding UTF-8**

```powershell
# Configurar console para UTF-8
chcp 65001

# Adicionar ao início dos scripts Python
# -*- coding: utf-8 -*-
```

### **Problema: Permissão negada ao executar scripts**

```powershell
# Permitir execução de scripts PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Problema: PyMuPDF não instala**

```powershell
# Instalar versão específica
pip install pymupdf==1.23.8

# Se persistir, baixar wheel manualmente
```

### **Problema: Conexão PostgreSQL falha**

```powershell
# Testar conexão
Test-NetConnection -ComputerName seu-servidor -Port 5432

# Verificar firewall Windows
netsh advfirewall firewall show rule name="PostgreSQL"

# Verificar credenciais no .env
```

---

## 🚀 **Automação com Task Scheduler**

### **Criar Tarefa Agendada (Processamento Diário)**

```powershell
# Criar script de processamento diário
notepad processar_diario.bat
```

Conteúdo do `processar_diario.bat`:

```batch
@echo off
cd C:\projetos\ocr-oficios-tjsp
call venv\Scripts\activate.bat
python exportar_json.py --input data\consultas --output output
python importar_postgres.py --input output\json
```

**Agendar via Task Scheduler:**

1. Abrir **Task Scheduler** (taskschd.msc)
2. **Create Basic Task** → Nome: "OCR Ofícios TJSP - Diário"
3. **Trigger**: Diariamente às 02:00
4. **Action**: Start a Program
   - Program: `C:\projetos\ocr-oficios-tjsp\processar_diario.bat`
   - Start in: `C:\projetos\ocr-oficios-tjsp`
5. **Finish**

---

## 📈 **Performance e Custos**

### **Estimativas (baseadas em testes)**

| Métrica | Valor |
|---------|-------|
| Tempo por PDF | ~30s |
| Custo por PDF (OpenAI) | <$0.01 |
| PDFs/hora | ~120 |
| Taxa de sucesso | 100% |

### **Otimizações**

- ✅ Processar em lote durante madrugada
- ✅ Usar limite para testes (`--limite 10`)
- ✅ Verificar JSONs antes de importar
- ✅ Monitorar custos OpenAI regularmente

---

## 🔒 **Segurança**

### **Boas Práticas**

1. **Nunca versionar o .env** (já está no .gitignore)
2. **Rotação de senhas** PostgreSQL periodicamente
3. **Backup regular** do banco de dados
4. **Logs**: Revisar periodicamente e limpar antigos
5. **OpenAI API Key**: Monitorar uso no dashboard

### **Backup PostgreSQL**

```powershell
# Backup completo
pg_dump -h servidor -U postgres -d oficios_tjsp > backup_oficios_YYYYMMDD.sql

# Restaurar backup
psql -h servidor -U postgres -d oficios_tjsp < backup_oficios_20250109.sql
```

---

## 📞 **Suporte**

- **Documentação**: README.md
- **Issues**: GitHub Issues
- **Logs**: `output\logs\` e `logs\`

---

**✅ Sistema pronto para produção em Windows Server 2022!**
