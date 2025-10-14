# 📥 Fase 2: Ingestão PostgreSQL

Pipeline completo de ingestão dos JSONs processados para PostgreSQL com interface Streamlit.

---

## 🎯 Objetivo

Ingerir todos os dados extraídos dos PDFs (JSONs) no PostgreSQL e criar interface web para consulta, filtros e visualização dos PDFs.

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
│   ├── ingest_json.py                # Script principal de ingestão
│   ├── validate_data.py              # Validação com Pydantic
│   └── test_connection.py            # Teste de conexão
├── app/
│   ├── streamlit_app.py              # Interface Streamlit
│   ├── pdf_viewer.py                 # Componente de visualização PDF
│   └── filters.py                    # Componentes de filtros
└── logs/
    └── ingestao.log                  # Logs de processamento
```

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
python scripts/ingest_json.py
```

### **5. Validar**

```bash
psql -h 72.60.62.124 -p 5432 -U admin -d n8n -f sql/03_test_queries.sql
```

### **6. Executar Streamlit**

```bash
streamlit run app/streamlit_app.py
```

---

## 📋 Funcionalidades

### **Script de Ingestão**
- ✅ Leitura de todos os JSONs
- ✅ Validação com Pydantic
- ✅ Upsert (ON CONFLICT DO UPDATE)
- ✅ Logs detalhados
- ✅ Barra de progresso
- ✅ Estatísticas de processamento

### **Interface Streamlit**
- ✅ Filtros múltiplos (CPF, processo, vara, status, etc.)
- ✅ Visualização de PDF inline
- ✅ Download de PDF
- ✅ Exportar resultados (CSV)
- ✅ Estatísticas em tempo real
- ✅ Gráficos interativos

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

**Status:** 🚀 Em desenvolvimento  
**Versão:** 1.0.0  
**Data:** 14/10/2025
