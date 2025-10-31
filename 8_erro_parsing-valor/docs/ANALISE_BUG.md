# 🔍 ANÁLISE DO BUG: Parsing de Valores

**Data:** 31 de Outubro de 2025  
**Status:** ✅ Bug NÃO reproduzido - Investigação em andamento

---

## 📋 RESUMO

**Problema Reportado:**
- Valor esperado: R$ 88.994,41
- Valor obtido: R$ 88,99  
- Diferença: -R$ 88.905,42

**Resultado do Teste:**
- ✅ Processamento local: **CORRETO** (R$ 88.994,41)
- ✅ LLM extração: **CORRETO**
- ✅ Validação Pydantic: **CORRETO**

---

## 🧪 TESTE REALIZADO

### Configuração
- **PDF:** Precatório-RAF.pdf
- **CPF:** 27308157830 (273.081.578-30)
- **Processo:** 0015796-15.2025.8.26.0500
- **Modelo LLM:** gpt-4o-mini
- **Data:** 31/10/2025 19:08

### Etapas Executadas

#### 1. Extração de Texto (PyMuPDF)
- ✅ Texto extraído: 7,207 caracteres
- ✅ Valor "88.994,41" **ENCONTRADO** no texto bruto
- ✅ Encoding: UTF-8

#### 2. Detecção de Estruturas
- ✅ Ofícios encontrados: 4
- ✅ CPF validado no ofício 3
- ✅ ANEXO II detectado na página 3
- ⚠️  PROCESSAMENTO não encontrado

#### 3. Extração via LLM (GPT-4o-mini)
```json
{
  "processo_origem": "0015796-15.2025.8.26.0500",
  "requerente_caps": "RODRIGO AZEVEDO FERRAO",
  "numero_ordem": "1/2025",
  "valor_principal_liquido": 88994.41,    ✅ CORRETO
  "valor_principal_bruto": 88994.41,      ✅ CORRETO
  "juros_moratorios": 0.00,               ✅ CORRETO
  "valor_total_requisitado": 88994.41     ✅ CORRETO
}
```

#### 4. Validação Pydantic
- ✅ Validação: **SUCESSO**
- ✅ Valores mantidos sem alteração
- ✅ Tipos convertidos corretamente (Decimal)

#### 5. Comparação com Valores Esperados

| Campo | Esperado | Obtido | Status |
|-------|----------|--------|--------|
| valor_principal_liquido | 88.994,41 | 88.994,41 | ✅ OK |
| valor_principal_bruto | 88.994,41 | 88.994,41 | ✅ OK |
| juros_moratorios | 0,00 | 0,00 | ✅ OK |
| valor_total_requisitado | 88.994,41 | 88.994,41 | ✅ OK |

**Resultado:** 4/4 valores corretos (100%)

---

## 🤔 ANÁLISE

### Por que o bug NÃO foi reproduzido?

**Possibilidades:**

#### 1. **Bug já foi corrigido no código**
- Validador `arredondar_decimais` pode ter sido atualizado
- Sistema atual processa corretamente

#### 2. **Dados antigos no banco de produção**
- Valor R$ 88,99 pode ser de processamento anterior
- Banco nunca foi atualizado com valores corretos

#### 3. **Problema na etapa de ingestão**
- Script `2_ingestao/` pode ter bug
- JSON correto, mas gravação no banco errada

#### 4. **JSON original diferente**
- Processamento em produção gerou JSON com erro
- Teste local gerou JSON correto

#### 5. **Diferença de ambiente**
- Versão diferente do Python
- Versão diferente das bibliotecas
- Configurações diferentes

---

## 🔍 INVESTIGAÇÃO NECESSÁRIA

### 1. Verificar Banco de Produção

```sql
SELECT 
    cpf,
    numero_processo,
    processo_origem,
    requerente_caps,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    timestamp_processamento
FROM lista_processos
WHERE numero_processo = '0015796-15.2025.8.26.0500'
   OR processo_origem = '0015796-15.2025.8.26.0500';
```

**Verificar:**
- Valores armazenados estão corretos?
- Data de processamento (timestamp)
- Há múltiplos registros?

### 2. Verificar JSON Original

**Localização provável:**
```
3_OCR/1_parsing_PDF/outputs/json/27308157830/0015796-15.2025.8.26.0500.json
```

**Comparar com JSON gerado no teste:**
```
8_erro_parsing-valor/test_outputs/3_resposta_llm.json
```

### 3. Verificar Interface Streamlit

- Onde o valor R$ 88,99 foi visualizado?
- Query SQL usada para exibição
- Há cache que pode estar desatualizado?

### 4. Verificar Logs de Processamento

```bash
# Buscar logs do processamento original
grep -r "0015796-15.2025.8.26.0500" 3_OCR/1_parsing_PDF/*.log
grep -r "27308157830" 3_OCR/2_ingestao/logs/*.log
```

---

## 📊 OUTPUTS GERADOS

Todos os outputs foram salvos em `test_outputs/`:

1. **1_texto_extraido.txt** - Texto completo do PDF (7,207 chars)
2. **1a_texto_relevante.txt** - Texto relevante (ofício + ANEXO II)
3. **2_prompt_llm.txt** - Prompt enviado ao GPT-4o-mini
4. **3_resposta_llm.json** - JSON retornado pelo LLM ✅
5. **4_dados_validados.json** - Dados após validação Pydantic ✅
6. **5_sql_statement.sql** - SQL que seria executado
7. **6_tabela_comparacao.txt** - Comparação valores

---

## 🎯 PRÓXIMOS PASSOS

1. ⏳ **Aguardar informações do usuário:**
   - Onde viu R$ 88,99?
   - Resultado da query no banco de produção
   - JSON original (se existir)

2. 📝 **Comparar ambientes:**
   - Versões de bibliotecas (local vs produção)
   - Configurações do sistema

3. 🔄 **Reprocessar em produção:**
   - Se necessário, reprocessar PDF com código atual
   - Atualizar banco com valores corretos

4. 📋 **Documentar solução:**
   - Identificar root cause
   - Criar guia de prevenção

---

## ✅ CONCLUSÃO PRELIMINAR

**O sistema ATUAL processa o PDF CORRETAMENTE.**

O valor incorreto (R$ 88,99) pode ser:
- Dado antigo no banco
- Bug já corrigido
- Problema na interface de visualização

**Aguardando mais informações do usuário para continuar investigação.**

---

**Última Atualização:** 31/10/2025 19:08  
**Autor:** Sistema OCR Debug

