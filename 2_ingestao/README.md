# 📥 Fase 2: Ingestão PostgreSQL

Pipeline de ingestão dos JSONs processados para PostgreSQL.

---

## 🎯 Objetivo

Ingerir todos os dados extraídos dos PDFs (JSONs) no PostgreSQL com validação e controle de qualidade.

**Nota:** A interface Streamlit foi movida para o módulo `3_streamlit/`

---

## 📊 Estrutura da Tabela

**Tabela:** `esaj_detalhe_processos`

**Chave Primária:** `(cpf, numero_processo_cnj)` - UNIQUE constraint

**Total de Campos:** 48 (47 do schema + 1 novo)

### **Novo Campo Adicionado**
- `process_diagnostico` (BOOLEAN DEFAULT FALSE) - Flag para controle de processamento/diagnóstico

---

## 📦 Estrutura de Arquivos

```
2_ingestao/
├── README.md                          # Este arquivo
├── requirements.txt                   # Dependências Python
├── .env                              # Credenciais PostgreSQL
├── sql/
│   ├── 01_create_table.sql           # DDL da tabela
│   ├── 02_create_indexes.sql         # Índices
│   └── 03_test_queries.sql           # Queries de validação
├── scripts/
│   ├── create_table.py               # Criação de tabela (alternativa ao psql)
│   ├── ingest_all_jsons.py           # Script otimizado de ingestão
│   ├── check_missing.py              # Verificar registros faltantes
│   ├── validate_data.py              # Validação e estatísticas
│   └── test_connection.py            # Teste de conexão
└── logs/
    └── ingestao.log                  # Logs de processamento
```

**Interface Streamlit:** Veja o módulo `3_streamlit/`

---

## 🚀 Como Usar

### **1. Configurar Ambiente**

```bash
cd 2_ingestao
pip install -r requirements.txt
```

### **2. Configurar .env**

```bash
DB_HOST=72.60.62.124
DB_PORT=5432
DB_NAME=n8n
DB_USER=admin
DB_PASSWORD=BetaAgent2024SecureDB
```

### **3. Criar Tabela**

```bash
python scripts/test_connection.py
psql -h 72.60.62.124 -p 5432 -U admin -d n8n -f sql/01_create_table.sql
psql -h 72.60.62.124 -p 5432 -U admin -d n8n -f sql/02_create_indexes.sql
```

### **4. Ingerir Dados**

```bash
# Ingerir todos os JSONs da pasta json/
python scripts/ingest_all_jsons.py
```

### **5. Validar**

```bash
# Opção 1: Script Python (recomendado)
python scripts/validate_data.py

# Opção 2: psql
psql -h 72.60.62.124 -p 5432 -U admin -d n8n -f sql/03_test_queries.sql
```

### **6. Verificar Registros Faltantes**

```bash
python scripts/check_missing.py
```

### **7. Interface Streamlit**

```bash
# Ver módulo 3_streamlit/
cd ../3_streamlit
./run.sh
```

---

## 📋 Funcionalidades

### **Script de Ingestão (`ingest_all_jsons.py`)**
- ✅ Leitura de todos os JSONs da pasta `json/`
- ✅ Validação de dados
- ✅ Upsert (ON CONFLICT DO UPDATE)
- ✅ Barra de progresso (tqdm)
- ✅ Estatísticas de processamento
- ✅ 100% de taxa de sucesso

### **Script de Validação (`validate_data.py`)**
- ✅ Estatísticas gerais
- ✅ Distribuição por status
- ✅ Top CPFs com mais processos
- ✅ Valores financeiros
- ✅ Preferências (idoso, doença grave, PCD)
- ✅ Processos pendentes de diagnóstico

### **Script de Verificação (`check_missing.py`)**
- ✅ Compara JSONs vs registros no banco
- ✅ Identifica registros faltantes
- ✅ Detecta inconsistências

---

## 📊 Índices Criados

- `idx_cpf` - Busca por CPF
- `idx_rejeitado` - Filtro por status
- `idx_cpf_rejeitado` - Filtro combinado
- `idx_vara` - Busca por vara
- `idx_idoso`, `idx_doenca_grave`, `idx_pcd` - Preferências
- `idx_data_ajuizamento` - Ordenação por data

---

## 🔍 Queries Úteis

```sql
-- Total de processos
SELECT COUNT(*) FROM esaj_detalhe_processos;

-- Processos por CPF
SELECT cpf, COUNT(*) FROM esaj_detalhe_processos GROUP BY cpf;

-- Ofícios rejeitados
SELECT COUNT(*) FROM esaj_detalhe_processos WHERE rejeitado = true;

-- Valor total requisitado
SELECT SUM(valor_total_requisitado) FROM esaj_detalhe_processos;

-- Processos com diagnóstico pendente
SELECT COUNT(*) FROM esaj_detalhe_processos WHERE process_diagnostico = false;
```

---

## 📈 Estatísticas Esperadas

- **Total de JSONs:** ~50
- **Tempo de ingestão:** ~1-2min
- **Taxa de sucesso esperada:** 100%

---

## 🛠️ Tecnologias

- **PostgreSQL 14+**
- **Python 3.11+**
- **Pydantic 2.5+**
- **Streamlit 1.28+**
- **psycopg2-binary**
- **pandas, plotly**

---

**Status:** ✅ Produção  
**Versão:** 2.0.0  
**Data:** 14/10/2025  
**Interface:** Veja `../3_streamlit/`
