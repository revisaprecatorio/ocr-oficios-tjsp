# 🔧 Correção de Falsos Rejeitados

## 📋 Problema Identificado

**Data:** 15/10/2025  
**Descoberto por:** Persival Balleste

### **Descrição:**
13 processos foram marcados como `rejeitado = TRUE` mas na verdade foram **PROCESSADOS COM INFORMAÇÃO** pelo DEPRE.

### **Padrão Identificado:**
- ✅ Todos têm `numero_ordem` preenchido
- ✅ Todos têm título "PROCESSAMENTO COM INFORMAÇÃO"
- ✅ Campo `motivo_rejeicao` vazio
- ✅ Ofícios foram **ACEITOS** pelo DEPRE

---

## 📊 Casos Identificados (13 processos)

| CPF | Processo | Nº Ordem | Página |
|-----|----------|----------|--------|
| 95653511820 | 0221126-48.2021.8.26.0500 | 6475/2022 | 162 |
| 94706751853 | 0221189-73.2021.8.26.0500 | 6503/2022 | 162 |
| 94019940800 | 0247212-56.2021.8.26.0500 | 7799/2022 | 162 |
| 49783491920 | 0085911-66.2022.8.26.0500 | 5727/2023 | 163 |
| 41609824415 | 0220428-42.2021.8.26.0500 | 6406/2022 | 162 |
| 19884761434 | 0221004-35.2021.8.26.0500 | 6423/2022 | 162 |
| 11659296862 | 0220433-64.2021.8.26.0500 | 6407/2022 | 162 |
| 10185170811 | 0223256-11.2021.8.26.0500 | 6775/2022 | 178 |
| 10149607890 | 0222597-02.2021.8.26.0500 | 6677/2022 | 177 |
| 06495530803 | 0223266-55.2021.8.26.0500 | 6784/2022 | 184 |
| 03730461893 | 0220341-86.2021.8.26.0500 | 6375/2022 | 162 |
| 02174781824 | 0221031-18.2021.8.26.0500 | 6433/2022 | 162 |
| 01103192817 | 0015266-16.2022.8.26.0500 | 2913/2023 | 162 |

---

## 🔧 Correção Implementada

### **1. Ajuste na Lógica de Detecção**

**Arquivo:** `1_parsing_PDF/app/detector_processamento.py`

**Método:** `eh_oficio_rejeitado()`

**Regras Adicionadas:**

```python
# 🔴 REGRA CRÍTICA 1: Se tem "PROCESSAMENTO COM INFORMAÇÃO" → NÃO é rejeitado
if "PROCESSAMENTO COM INFORMAÇÃO" in texto_upper:
    return False

# 🔴 REGRA CRÍTICA 2: Se tem número de ordem → NÃO é rejeitado
if self.extrair_numero_ordem(texto):
    return False
```

**Lógica Antiga (INCORRETA):**
- Marcava como rejeitado se encontrava keywords de rejeição
- Não verificava "PROCESSAMENTO COM INFORMAÇÃO"
- Não validava presença de número de ordem

**Lógica Nova (CORRETA):**
1. ✅ Se tem "PROCESSAMENTO COM INFORMAÇÃO" → `rejeitado = FALSE`
2. ✅ Se tem `numero_ordem` → `rejeitado = FALSE`
3. ✅ Só marca como rejeitado se tem keywords de rejeição E não tem número de ordem

---

## 📝 Processo de Reprocessamento

### **PASSO 1: Limpar Tabela PostgreSQL**

```sql
-- Conectar ao banco
psql -h localhost -U admin -d n8n

-- Limpar tabela
TRUNCATE TABLE lista_processos CASCADE;

-- Verificar
SELECT COUNT(*) FROM lista_processos;
-- Resultado esperado: 0
```

### **PASSO 2: Reprocessar PDFs com Nova Lógica**

```bash
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/1_parsing_PDF

# Ativar ambiente virtual
source ../.venv/bin/activate

# Reprocessar todos os PDFs
python processar_lotes_v2.py \
  --input ../data/consultas \
  --output outputs \
  --limite 0  # 0 = processar todos

# Tempo estimado: ~25 minutos para 51 PDFs
```

### **PASSO 3: Importar JSONs para PostgreSQL**

```bash
cd ../2_ingestao

# Importar todos os JSONs
python scripts/ingest_all_jsons.py \
  --input ../1_parsing_PDF/outputs/json \
  --db-host localhost \
  --db-port 5432 \
  --db-name n8n \
  --db-user admin

# Verificar importação
python scripts/validate_data.py
```

### **PASSO 4: Validar Correção**

```sql
-- Verificar total de registros
SELECT COUNT(*) FROM lista_processos;

-- Verificar processos com numero_ordem
SELECT COUNT(*) FROM lista_processos WHERE numero_ordem IS NOT NULL;

-- Verificar falsos rejeitados corrigidos (deve retornar 0)
SELECT cpf, numero_processo, numero_ordem, rejeitado, motivo_rejeicao
FROM lista_processos
WHERE numero_ordem IS NOT NULL 
  AND rejeitado = TRUE
  AND motivo_rejeicao IS NULL;

-- Verificar os 13 casos específicos
SELECT cpf, numero_processo, numero_ordem, rejeitado
FROM lista_processos
WHERE cpf IN (
  '95653511820', '94706751853', '94019940800', '49783491920',
  '41609824415', '19884761434', '11659296862', '10185170811',
  '10149607890', '06495530803', '03730461893', '02174781824',
  '01103192817'
)
ORDER BY cpf;
```

**Resultado Esperado:**
- ✅ Todos os 13 processos com `rejeitado = FALSE`
- ✅ Todos com `numero_ordem` preenchido
- ✅ Campo `motivo_rejeicao` vazio ou NULL

---

## 📈 Impacto da Correção

### **Antes:**
- ❌ 13 processos marcados incorretamente como rejeitados
- ❌ Processos válidos não apareciam como aprovados
- ❌ Estatísticas incorretas no Streamlit

### **Depois:**
- ✅ 13 processos corretamente marcados como aceitos
- ✅ Estatísticas corretas
- ✅ Lógica robusta para futuros processamentos

---

## 🎯 Lições Aprendidas

### **1. Validação de Regras de Negócio**
- Sempre validar regras com dados reais
- Não assumir que ausência de motivo = não rejeitado
- Presença de `numero_ordem` é indicador forte de aceitação

### **2. Padrões do DEPRE**
- "PROCESSAMENTO COM INFORMAÇÃO" = ofício aceito
- "NOTA DE REJEIÇÃO" = ofício rejeitado
- Número de ordem só existe em ofícios aceitos

### **3. Importância de Análise Manual**
- Descoberta feita por análise manual do CSV
- Ferramentas automatizadas não detectaram o padrão
- Validação humana é essencial

---

## 📚 Referências

- **Script de Análise:** `analisar_falsos_rejeitados.py`
- **Resultados JSON:** `analise_falsos_rejeitados.json`
- **CSV Original:** `rejeitados.csv`
- **Código Corrigido:** `1_parsing_PDF/app/detector_processamento.py`

---

## ✅ Checklist de Correção

- [x] Identificar padrão dos falsos rejeitados
- [x] Analisar todos os 13 casos
- [x] Confirmar 100% dos casos (13/13)
- [x] Ajustar lógica de detecção
- [ ] Limpar tabela PostgreSQL
- [ ] Reprocessar todos os PDFs
- [ ] Importar JSONs atualizados
- [ ] Validar correção no banco
- [ ] Verificar Streamlit
- [ ] Commit e documentação
- [ ] Deploy em produção

---

**Versão:** 1.0  
**Data:** 15/10/2025  
**Autor:** Cascade AI + Persival Balleste  
**Status:** ✅ Lógica corrigida, aguardando reprocessamento
