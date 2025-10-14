# 🚀 Quick Start - Ingestão PostgreSQL

Guia rápido para executar a ingestão e interface Streamlit.

---

## ⚡ Início Rápido (5 minutos)

### **1. Configurar Ambiente**

```bash
cd 2_ingestao

# Copiar .env
cp .env.example .env

# Instalar dependências
pip install -r requirements.txt
```

### **2. Testar Conexão**

```bash
python scripts/test_connection.py
```

**Saída esperada:**
```
✅ CONEXÃO BEM-SUCEDIDA!
📊 Informações do Banco:
   Versão: PostgreSQL 16.10...
   Tabela 'esaj_detalhe_processos': ✅ Existe
   Total de registros: 50
```

### **3. Criar Tabela (se não existir)**

```bash
python scripts/create_table.py
```

### **4. Ingerir Dados**

```bash
python scripts/ingest_json.py
```

**Saída esperada:**
```
Ingestão: 100%|██████████| 50/50 [00:01<00:00]
✅ Sucesso: 50
❌ Erros: 0
Taxa de sucesso: 100.0%
```

### **5. Validar Dados**

```bash
python scripts/validate_data.py
```

### **6. Executar Streamlit**

```bash
streamlit run app/streamlit_app.py
```

**Acesse:** http://localhost:8501

---

## 🐳 Docker (Recomendado para Produção)

### **Build e Run**

```bash
# Build da imagem
docker-compose build

# Executar
docker-compose up -d

# Ver logs
docker-compose logs -f streamlit

# Parar
docker-compose down
```

**Acesse:** http://localhost:8501

---

## 📊 Funcionalidades da Interface

### **Filtros Disponíveis**
- ✅ CPF (texto)
- ✅ Número do Processo (texto)
- ✅ Vara (dropdown)
- ✅ Status (Rejeitado/Aprovado)
- ✅ Preferências (Idoso, Doença Grave, PCD)
- ✅ Range de Valores (R$)
- ✅ Range de Datas

### **Visualizações**
- ✅ Tabela de dados com paginação
- ✅ Gráficos interativos (Plotly)
- ✅ Estatísticas em tempo real
- ✅ PDF inline (iframe)
- ✅ Download de PDF
- ✅ Exportar CSV

---

## 🔧 Comandos Úteis

### **Reingerir Dados (Atualizar)**

```bash
python scripts/ingest_json.py
```

> ⚠️ Usa UPSERT - atualiza registros existentes sem duplicar

### **Verificar Logs**

```bash
tail -f logs/ingestao.log
```

### **Queries Manuais**

```bash
# Via Python
python scripts/validate_data.py

# Via psql (se instalado)
PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n
```

### **Limpar Tabela**

```sql
TRUNCATE TABLE esaj_detalhe_processos;
```

---

## 📈 Estatísticas Atuais

```
Total de Processos: 50
Rejeitados: 31 (62%)
Aprovados: 19 (38%)
Valor Total: R$ 6.124.893,36
Idosos: 15
Doença Grave: 3
PCD: 0
```

---

## 🐛 Troubleshooting

### **Erro: Conexão recusada**
```bash
# Verificar credenciais no .env
cat .env

# Testar conexão
python scripts/test_connection.py
```

### **Erro: Tabela não existe**
```bash
# Criar tabela
python scripts/create_table.py
```

### **Erro: PDF não encontrado**
```bash
# Verificar path no .env
PDF_DIR=../data/consultas

# Verificar se PDFs existem
ls -la ../data/consultas/
```

### **Streamlit não inicia**
```bash
# Instalar dependências
pip install -r requirements.txt

# Verificar porta
lsof -i :8501

# Usar porta alternativa
streamlit run app/streamlit_app.py --server.port=8502
```

---

## 📚 Documentação Completa

- **README.md** - Documentação completa
- **sql/03_test_queries.sql** - Queries de exemplo
- **Docker** - Dockerfile + docker-compose.yml

---

**Status:** ✅ Pronto para uso  
**Versão:** 1.0.0  
**Última atualização:** 14/10/2025
