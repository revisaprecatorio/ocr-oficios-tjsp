# 📸 Exemplos Visuais - Padrões nos PDFs

**Propósito:** Referência visual de padrões e estruturas encontradas nos Ofícios Requisitórios do TJSP.

---

## 📁 Imagens Disponíveis

### 1. **Habilitação de Herdeiros** (`habilitacao_herdeiro.png`)
**Tamanho:** 130 KB
**Origem:** V2.5.2 (Dez 2024)
**Mostra:**
- Código `9270` - Identificador único de habilitação de herdeiros de precatório
- Estrutura "Dados da Sucessão"
- Localização do CPF do sucessor (3ª linha após "Dados da Sucessão")

**Uso no Sistema (V3.0.2):**
```python
# detector_termos_juridicos.py: detectar_habilitacao_avancada()
# Busca código 9270 + valida CPF corresponde ao CPF objeto
```

**Versão Atual:** V3.0.2 usa `habilitacao_herdeiros` (boolean) validado por REGEX (código 9270) + CPF.

---

### 2. **Saldo Final - Contexto Completo** (`valor_final_apos_pagmento_pagina.png`)
**Tamanho:** 1.3 MB
**Origem:** V2.5.2 (Dez 2024)
**Mostra:**
- Contexto completo da página com "Saldo final após pagamento"
- Estrutura do ANEXO II
- Localização típica do campo (seção de valores)

**Uso no Sistema (V3.0.2):**
```python
# processador.py: _calcular_saldo_final()
# Pattern: r'Saldo\s+final\s+após\s+pagamento[:\s]+R\$?\s*([\d.,]+)'
```

---

### 3. **Saldo Final - Recorte** (`Valor_final_apos_pagmento.png`)
**Tamanho:** 147 KB
**Origem:** V2.5.2 (Dez 2024)
**Mostra:**
- Recorte focado no padrão "Saldo final após pagamento: R$ X.XXX,XX"
- Formato típico do valor brasileiro (ponto=milhar, vírgula=decimal)

**Uso no Sistema (V3.0.2):**
```python
# processador.py: _calcular_saldo_final()
# Fallback: Se não encontrado, usa valor_total_requisitado
```

**Versão Atual:** V3.0.2 usa `saldo_final` (DECIMAL) com fallback para `valor_total_requisitado`.

---

## 🔗 Referências no Código Atual (V3.0.2)

### Habilitação de Herdeiros
- **Arquivo:** `1_parsing_PDF/app/detector_termos_juridicos.py`
- **Função:** `detectar_habilitacao_avancada()`
- **Lógica:**
  1. Busca código `9270`
  2. Localiza seção "Dados da Sucessão"
  3. Extrai CPF (3ª linha)
  4. Valida se CPF = CPF objeto

### Saldo Final
- **Arquivo:** `1_parsing_PDF/app/processador.py`
- **Função:** `_calcular_saldo_final()`
- **Lógica:**
  1. REGEX: "Saldo final após pagamento"
  2. Fallback: `valor_total_requisitado`
  3. Prioridade: REGEX > Fallback

---

## 📊 Schema Atual (V3.0.2)

```python
# 1_parsing_PDF/app/schemas.py
class OficioRequisitorioOutput(BaseModel):
    # ... outros campos ...
    habilitacao_herdeiros: Optional[bool] = Field(None)  # V2.5.3+
    saldo_final: Optional[str] = Field(None)             # V2.5.2+
```

---

## 🗂️ Histórico

### V2.5.2 (4 Dez 2024)
- ✅ Adicionado `saldo_final` com REGEX + fallback
- ✅ Desativado `cessao_credito` (sempre False)
- ✅ Melhorado `habilitacao_herdeiros` (código 9270 + CPF)

### V3.0 (13 Dez 2024)
- ✅ Removido completamente `cessao_credito` do schema
- ✅ Schema: 50→35 colunas (-15 campos não utilizados)
- ✅ Mantido: `saldo_final`, `habilitacao_herdeiros`

### V3.0.2 (14 Dez 2024)
- ✅ Fix crítico: Detecção de rejeições (REGEX-first)
- ✅ Modernização UAT (v2.5.1 → V3.0)

---

## 📝 Documentação Relacionada

- **CHANGELOG:** `CHANGELOG.md` (linhas 921-950: V2.5.2)
- **Código:** `1_parsing_PDF/app/detector_termos_juridicos.py`
- **Código:** `1_parsing_PDF/app/processador.py`
- **Schema:** `1_parsing_PDF/app/schemas.py`

---

## ⚠️ Notas

1. **Imagens preservadas:** Estes exemplos visuais foram extraídos durante desenvolvimento V2.5.2 e continuam relevantes para V3.0.2
2. **Origem:** Documentação de `5_revisao_termos/` (arquivada em `historico_arquivado/5_revisao_termos_v2.5.2_LEGACY/`)
3. **Uso:** Referência para entender padrões visuais nos PDFs ao fazer manutenção ou adicionar novos detectores

---

**Última Atualização:** 14/12/2025
**Versão Sistema:** V3.0.2
**Status:** ✅ Exemplos preservados e documentados
