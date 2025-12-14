# 🎂 Recálculo Automático da Tag IDOSO

Sistema de cálculo automático da preferência "idoso" baseado na data de nascimento do requerente.

---

## 📋 **Visão Geral**

A tag `idoso` indica se o requerente tem direito à preferência de tramitação por ter 60 anos ou mais, conforme legislação brasileira (Estatuto do Idoso - Lei 10.741/2003).

**Lógica:**
```python
idade = data_atual - data_nascimento
idoso = idade >= 60 anos
```

---

## 🔄 **Funcionamento**

### **1. Cálculo Automático no Processamento**

Quando um PDF é processado, o sistema:

1. ✅ Extrai `data_nascimento` do ofício (via GPT-4o-mini)
2. ✅ Calcula a idade atual
3. ✅ Define `idoso = TRUE` se idade ≥ 60 anos
4. ✅ Salva no JSON de saída

**Arquivo:** `1_parsing_PDF/app/processador.py`

```python
# 8.1. Calcular flag IDOSO automaticamente
if oficio_validado.data_nascimento:
    from datetime import date
    hoje = date.today()
    idade = hoje.year - oficio_validado.data_nascimento.year
    
    # Ajustar se ainda não fez aniversário este ano
    if (hoje.month, hoje.day) < (oficio_validado.data_nascimento.month, oficio_validado.data_nascimento.day):
        idade -= 1
    
    # Atualizar flag idoso
    oficio_validado.idoso = (idade >= 60)
    logger.info(f"🎂 Idade calculada: {idade} anos → idoso={oficio_validado.idoso}")
```

### **2. Recálculo em Lote (Registros Existentes)**

Para atualizar registros já existentes no banco:

```bash
cd 2_ingestao
python scripts/recalcular_idoso.py
```

**O que o script faz:**
1. ✅ Busca todos os registros com `data_nascimento`
2. ✅ Calcula a idade de cada um
3. ✅ Atualiza a flag `idoso` no PostgreSQL
4. ✅ Mostra relatório detalhado

---

## 📊 **Exemplo de Saída**

```
================================================================================
🔄 RECÁLCULO DA TAG IDOSO
================================================================================

🔌 Conectando ao PostgreSQL...
   ✅ Conectado!

📊 Buscando registros com data_nascimento...
   ✅ Encontrados 44 registros com data_nascimento

🔄 Processando registros...
--------------------------------------------------------------------------------
✅ IDOSO         | Idade: 63 anos | CPF: 95353291891 | ALBERTO MONTEIRO PUGLESI
✅ IDOSO         | Idade: 62 anos | CPF: 41609824415 | MARIA ELIZABETE DE SÁ
✅ IDOSO         | Idade: 60 anos | CPF: 10381700879 | FAUSTO BLASI
❌ NÃO IDOSO     | Idade: 57 anos | CPF: 10155175874 | JOÃO DA SILVA
❌ NÃO IDOSO     | Idade: 45 anos | CPF: 02174781824 | MARIA SANTOS
--------------------------------------------------------------------------------

================================================================================
📊 RESUMO DO RECÁLCULO
================================================================================
Data de referência: 16/10/2025

Total de registros processados: 44
   ✅ Idosos (≥60 anos):         27 (61.4%)
   ❌ Não idosos (<60 anos):     17 (38.6%)

Registros atualizados:          12
Registros já corretos:          32
Erros:                          0

🔍 Validação final...
   Total:      44
   Idosos:     27
   Não idosos: 17
   Sem flag:   0

✅ Todos os registros com data_nascimento têm flag idoso definida!

================================================================================
✅ RECÁLCULO CONCLUÍDO!
================================================================================
```

---

## 🔧 **Uso**

### **Opção 1: Pipeline Completo (Recomendado)**

O recálculo é executado automaticamente no pipeline:

```bash
./pipeline_completo.sh
```

**Etapas do pipeline:**
1. Limpa JSONs antigos
2. Processa PDFs
3. Organiza JSONs
4. Importa para PostgreSQL
5. **Recalcula tag idoso** ⭐
6. Valida resultados

### **Opção 2: Recálculo Manual**

Para recalcular apenas a tag idoso:

```bash
cd 2_ingestao
source ../.venv/bin/activate
python scripts/recalcular_idoso.py
```

### **Opção 3: Via SQL Direto**

```sql
-- Atualizar todos os registros com data_nascimento
UPDATE esaj_detalhe_processos
SET idoso = (
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) >= 60
)
WHERE data_nascimento IS NOT NULL;
```

---

## 📝 **Regras de Negócio**

### **Cálculo de Idade**

```python
def calcular_idade(data_nascimento: date) -> int:
    hoje = date.today()
    idade = hoje.year - data_nascimento.year
    
    # Ajustar se ainda não fez aniversário este ano
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    
    return idade
```

**Exemplos:**
- Nascimento: 15/05/1960, Hoje: 16/10/2025 → Idade: 65 anos → `idoso = TRUE`
- Nascimento: 20/12/1965, Hoje: 16/10/2025 → Idade: 59 anos → `idoso = FALSE`
- Nascimento: 01/01/1965, Hoje: 16/10/2025 → Idade: 60 anos → `idoso = TRUE`

### **Casos Especiais**

| Situação | Comportamento |
|----------|---------------|
| `data_nascimento` é NULL | `idoso` permanece como definido no JSON (default: FALSE) |
| Idade = 60 anos exatos | `idoso = TRUE` (≥ 60) |
| Idade = 59 anos e 11 meses | `idoso = FALSE` (< 60) |
| Data futura (erro) | Script reporta erro, não atualiza |

---

## 🔍 **Validação**

### **Verificar Registros com Flag Idoso**

```sql
-- Total por status
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN idoso = TRUE THEN 1 END) as idosos,
    COUNT(CASE WHEN idoso = FALSE THEN 1 END) as nao_idosos,
    COUNT(CASE WHEN idoso IS NULL THEN 1 END) as sem_flag
FROM esaj_detalhe_processos
WHERE data_nascimento IS NOT NULL;
```

### **Listar Idosos**

```sql
SELECT 
    cpf,
    requerente_caps,
    data_nascimento,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) as idade,
    idoso
FROM esaj_detalhe_processos
WHERE idoso = TRUE
ORDER BY data_nascimento;
```

### **Verificar Inconsistências**

```sql
-- Registros com idade ≥ 60 mas idoso = FALSE
SELECT 
    cpf,
    requerente_caps,
    data_nascimento,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) as idade,
    idoso
FROM esaj_detalhe_processos
WHERE data_nascimento IS NOT NULL
  AND EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) >= 60
  AND idoso = FALSE;
```

---

## 📊 **Estatísticas**

### **Última Execução (16/10/2025)**

- **Total processado:** 44 registros
- **Idosos:** 27 (61.4%)
- **Não idosos:** 17 (38.6%)
- **Atualizados:** 12
- **Já corretos:** 32
- **Erros:** 0
- **Taxa de sucesso:** 100%

### **Distribuição por Idade**

```sql
SELECT 
    CASE 
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) >= 70 THEN '70+'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) >= 65 THEN '65-69'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) >= 60 THEN '60-64'
        ELSE '<60'
    END as faixa_etaria,
    COUNT(*) as total
FROM esaj_detalhe_processos
WHERE data_nascimento IS NOT NULL
GROUP BY faixa_etaria
ORDER BY faixa_etaria;
```

---

## 🚨 **Troubleshooting**

### **Erro: "Nenhum registro para processar"**

**Causa:** Nenhum registro tem `data_nascimento` preenchido.

**Solução:**
1. Verificar se PDFs foram processados corretamente
2. Verificar se script de ingestão está incluindo `data_nascimento`
3. Reprocessar PDFs se necessário

### **Erro: "Idade negativa ou muito alta"**

**Causa:** `data_nascimento` com valor incorreto (data futura ou muito antiga).

**Solução:**
```sql
-- Identificar registros problemáticos
SELECT cpf, requerente_caps, data_nascimento
FROM esaj_detalhe_processos
WHERE data_nascimento > CURRENT_DATE
   OR EXTRACT(YEAR FROM AGE(CURRENT_DATE, data_nascimento)) > 120;
```

### **Erro: "Conexão com PostgreSQL falhou"**

**Causa:** Credenciais incorretas ou banco indisponível.

**Solução:**
1. Verificar `.env` em `2_ingestao/.env`
2. Testar conexão: `psql -h <host> -U <user> -d <database>`
3. Verificar firewall/VPN

---

## 📚 **Referências**

- **Estatuto do Idoso:** Lei 10.741/2003, Art. 71 (preferência de tramitação)
- **Código Civil:** Art. 1.211 (preferência em processos)
- **CPC:** Art. 1.048 (prioridade de tramitação)

---

## 🔄 **Histórico de Mudanças**

### **v2.3.0 (16/10/2025)**
- ✅ Implementado cálculo automático no processamento
- ✅ Criado script de recálculo em lote
- ✅ Adicionado ao pipeline completo
- ✅ Documentação completa

---

**Última atualização:** 16/10/2025  
**Versão:** 2.3.0  
**Status:** ✅ Funcional
