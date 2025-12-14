# ANOMALIA A REVER

**Data:** 2025-10-15  
**Status:** 🟡 PENDENTE CORREÇÃO  
**Prioridade:** BAIXA (1 caso em 51 PDFs)

---

## 📋 RESUMO

Durante o reprocessamento completo com a lógica corrigida, identificamos **1 caso anômalo** onde um ofício com `numero_ordem` foi incorretamente marcado como `rejeitado: true`.

---

## 🔍 CASO IDENTIFICADO

### **Arquivo:**
- **CPF:** 95653511820
- **Processo:** 0221126-48.2021.8.26.0500
- **JSON:** `outputs/lote_011/95653511820_0221126-48.2021.8.26.0500.json`

### **Dados extraídos:**
```json
{
  "processo_origem": "0035938-67.2018.8.26.0053",
  "requerente_caps": "IZAURA BATISTA DA SILVA",
  "numero_ordem": "6475/2022",
  "rejeitado": true,
  "motivo_rejeicao": null,
  "observacoes": "Campos não encontrados: juros_moratorios"
}
```

### **Problema:**
- ✅ Tem `numero_ordem`: **6475/2022**
- ❌ Marcado como `rejeitado: true`
- ❌ `motivo_rejeicao: null` (inconsistente)

---

## 🔬 ANÁLISE DOS LOGS

### **Logs do processamento:**

```
2025-10-15 22:20:19,122 - app.detector_processamento - INFO - ✅ PROCESSAMENTO detectado na página 162
2025-10-15 22:20:19,122 - app.detector_processamento - INFO - ✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO (não rejeitado)
2025-10-15 22:20:19,129 - app.detector_processamento - WARNING - ⚠️ Número de ordem não encontrado no texto
2025-10-15 22:20:19,129 - app.detector_processamento - WARNING - ⚠️ Keyword de rejeição encontrada: REJEIÇÃO
2025-10-15 22:20:19,129 - app.processador - WARNING - ⚠️ OFÍCIO REJEITADO detectado na página 156!
```

### **Interpretação:**

1. **Página 162:** Detectou "PROCESSAMENTO COM INFORMAÇÃO" → Ofício ACEITO ✅
2. **Página 156:** Detectou keyword "REJEIÇÃO" → Marcou como rejeitado ❌

**Conclusão:** O PDF contém **múltiplas páginas de PROCESSAMENTO**:
- Uma página com "PROCESSAMENTO COM INFORMAÇÃO" (aceito)
- Outra página com "NOTA DE REJEIÇÃO" (rejeitado)

A lógica atual verifica **todas as páginas** e a última detecção (rejeição) sobrescreve a primeira (aceito).

---

## 🐛 CAUSA RAIZ

### **Código atual em `detector_processamento.py`:**

```python
def eh_oficio_rejeitado(self, texto: str) -> bool:
    """
    Verifica se o texto indica que o ofício foi rejeitado.
    
    IMPORTANTE: "PROCESSAMENTO COM INFORMAÇÃO" NÃO é rejeição!
    Ofícios com número de ordem foram ACEITOS pelo DEPRE.
    """
    texto_upper = texto.upper()
    
    # 🔴 REGRA CRÍTICA: Se tem "PROCESSAMENTO COM INFORMAÇÃO" → NÃO é rejeitado
    if "PROCESSAMENTO COM INFORMAÇÃO" in texto_upper or "PROCESSAMENTO COM INFORMACAO" in texto_upper:
        logger.info("✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO (não rejeitado)")
        return False
    
    # 🔴 REGRA CRÍTICA: Se tem número de ordem → NÃO é rejeitado
    if self.extrair_numero_ordem(texto):
        logger.info("✅ Número de ordem detectado → Ofício ACEITO (não rejeitado)")
        return False
    
    # Verificar keywords de rejeição
    for keyword in self.keywords_rejeicao:
        if keyword.upper() in texto_upper:
            logger.warning(f"⚠️ Keyword de rejeição encontrada: {keyword}")
            return True
    
    return False
```

### **Problema:**

O método `eh_oficio_rejeitado()` é chamado **múltiplas vezes** (uma para cada página de PROCESSAMENTO encontrada). Quando há múltiplas páginas:

1. Primeira chamada (página 162): Retorna `False` (PROCESSAMENTO COM INFORMAÇÃO) ✅
2. Segunda chamada (página 156): Retorna `True` (REJEIÇÃO) ❌

O processador usa o **último resultado**, sobrescrevendo o correto.

---

## 🔧 SOLUÇÕES POSSÍVEIS

### **Opção A: Priorizar "PROCESSAMENTO COM INFORMAÇÃO"** ⭐ RECOMENDADO

Modificar `processador.py` para que, se **qualquer** página de PROCESSAMENTO tiver "PROCESSAMENTO COM INFORMAÇÃO", o ofício seja considerado **ACEITO**, independente de outras páginas terem "REJEIÇÃO".

```python
# Pseudocódigo
tem_processamento_com_informacao = False
tem_rejeicao = False

for pagina in paginas_processamento:
    if "PROCESSAMENTO COM INFORMAÇÃO" in pagina:
        tem_processamento_com_informacao = True
    if "REJEIÇÃO" in pagina:
        tem_rejeicao = True

# Prioridade: PROCESSAMENTO COM INFORMAÇÃO > REJEIÇÃO
if tem_processamento_com_informacao:
    rejeitado = False
elif tem_rejeicao:
    rejeitado = True
```

### **Opção B: Parar na primeira página "PROCESSAMENTO COM INFORMAÇÃO"**

Modificar `detector_processamento.py` para **parar a busca** assim que encontrar "PROCESSAMENTO COM INFORMAÇÃO".

### **Opção C: Correção manual/script**

Criar script para corrigir apenas este caso:
```sql
UPDATE lista_processos 
SET rejeitado = FALSE 
WHERE cpf = '95653511820' 
  AND numero_processo = '0221126-48.2021.8.26.0500'
  AND numero_ordem IS NOT NULL;
```

---

## 📊 IMPACTO

### **Estatísticas:**
- **Total de PDFs:** 51
- **Processados com sucesso:** 50 (98%)
- **Casos anômalos:** 1 (2%)
- **Falsos rejeitados corrigidos:** 12 (dos 13 identificados)
- **Falsos rejeitados restantes:** 1

### **Impacto no negócio:**
- ✅ 98% de precisão
- ⚠️ 1 ofício com `numero_ordem` pode ser processado incorretamente como rejeitado
- 💰 Impacto financeiro: Baixo (1 caso)

---

## ✅ AÇÃO IMEDIATA

**Decisão:** Seguir com importação e corrigir depois (Opção 1)

**Justificativa:**
- 98% de sucesso é excelente
- 1 caso pode ser corrigido manualmente após importação
- Não vale a pena atrasar o pipeline inteiro por 1 anomalia

**Próximos passos:**
1. ✅ Documentar anomalia (este arquivo)
2. 🔄 Importar 50 JSONs para PostgreSQL
3. 🔍 Validar importação
4. 🔧 Corrigir caso anômalo via SQL ou reprocessamento pontual

---

## 📝 OBSERVAÇÕES ADICIONAIS

### **Warnings comuns (não são erros):**

```
⚠️ Número de ordem não encontrado no texto
⚠️ Campos não encontrados: juros_moratorios
```

Estes warnings são **normais** e **esperados**:
- Nem todos os ofícios têm número de ordem (rejeitados não têm)
- Campo `juros_moratorios` é opcional

### **Logs de sucesso:**

```
✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO (não rejeitado)
✅ Número de ordem extraído: 6475/2022
✅ Número de ordem detectado → Ofício ACEITO (não rejeitado)
```

A lógica **está funcionando corretamente** na maioria dos casos!

---

## 🎯 RECOMENDAÇÃO FINAL

**Implementar Opção A** em uma próxima iteração para garantir 100% de precisão em casos com múltiplas páginas de PROCESSAMENTO.

**Prioridade:** BAIXA (sistema já está 98% funcional)

---

**Criado por:** Cascade AI  
**Revisado por:** Pendente  
**Última atualização:** 2025-10-15 22:23
