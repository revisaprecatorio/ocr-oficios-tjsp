# 📋 Plano de Validação V3.0 Completa

**Data:** 01/11/2025 23:43  
**Status:** 🔄 EM ANDAMENTO  
**Objetivo:** Validar V3.0 com TODOS os 51 PDFs e comparar com CSV

---

## 🎯 Objetivo

Executar validação completa da V3.0 para:
1. ✅ Processar todos os 51 PDFs
2. ✅ Comparar valores extraídos com CSV de referência
3. ✅ Identificar casos perfeitos vs. discrepantes
4. ✅ Medir melhoria de V2.5.1 para V3.0

---

## 📊 Progresso

### Fase 1: Validação (EM ANDAMENTO)
- **Script:** `validacao_completa.py`
- **Status:** 🔄 9/51 processos iniciados
- **Log:** `test_data/validacao_v3_completa.log`
- **Tempo Estimado:** 3-5 minutos

### Fase 2: Comparação (AGUARDANDO)
- **Script:** `comparar_v3_com_csv.py`
- **Input:** Log de validação + CSV de referência
- **Output:** 
  - `docs/COMPARACAO_V3_VS_CSV.md` (relatório)
  - `test_data/comparacao_v3.csv` (dados detalhados)

---

## 📁 Arquivos Criados

### Scripts
- ✅ `scripts/monitor_validacao_v3.sh` - Monitor de progresso em tempo real
- ✅ `scripts/comparar_v3_com_csv.py` - Comparação com CSV

### Dados
- 🔄 `test_data/validacao_v3_completa.log` - Log da validação
- ⏸️ `test_data/comparacao_v3.csv` - Comparação detalhada
- ⏸️ `docs/COMPARACAO_V3_VS_CSV.md` - Relatório final

---

## 🔍 Critérios de Comparação

### Categorias de Status

| Status | Critério | Descrição |
|--------|----------|-----------|
| ✅ PERFEITO | Diferença < R$ 1,00 | Valores idênticos |
| ✅ ACEITÁVEL | Diferença < 1% | Pequeno arredondamento |
| ⚠️ BAIXO | Diferença < 10% | Discrepância baixa |
| ❌ CRÍTICO | Diferença ≥ 10% | Erro significativo |
| ⚠️ NÃO PROCESSADO | Sem dados | PDF não processado |

### Campos Comparados

1. **Valor Principal Líquido** - Campo principal de análise
2. **Valor Principal Bruto** - Validação cruzada
3. **Diferença Absoluta** - Em reais (R$)
4. **Diferença Percentual** - Em porcentagem (%)

---

## 📈 Métricas Esperadas

### Baseline V2.5.1 (Sessão 2)
- **Taxa de Sucesso:** 98% (49/50)
- **Acurácia Perfeita:** 56% (28/50)
- **Casos Críticos:** 10% (5/50)

### Meta V3.0
- **Taxa de Sucesso:** ≥98% (mantém robustez)
- **Acurácia Perfeita:** ≥68% (+12% vs V2.5.1)
- **Casos Críticos:** ≤6% (resolução de 3 casos)

---

## 📊 Estrutura do Relatório Final

```markdown
# Comparação V3.0 vs CSV

## Estatísticas Gerais
- Total de Processos
- Perfeitos / Aceitáveis / Baixos / Críticos
- Taxa de Sucesso
- Acurácia Perfeita

## Tabela Detalhada
| # | CPF | Processo | Status | CSV | V3 | Diff |
|---|-----|----------|--------|-----|----|----- |
| 1 | xxx | yyy      | ✅     | ... | ... | ... |

## Casos Críticos (se houver)
- Detalhamento dos casos com erro ≥10%

## Análise de Melhoria
- V2.5.1 vs V3.0
- Casos resolvidos
- Casos pendentes

## Conclusão
- Aprovação para produção?
```

---

## ⏱️ Timeline

| Etapa | Início | Duração | Status |
|-------|--------|---------|--------|
| Validação V3.0 | 23:42 | 3-5 min | 🔄 EM ANDAMENTO |
| Comparação CSV | 23:47 | 1 min | ⏸️ AGUARDANDO |
| Geração Relatório | 23:48 | 1 min | ⏸️ AGUARDANDO |
| Análise Final | 23:49 | 2 min | ⏸️ AGUARDANDO |
| **TOTAL** | - | **7-9 min** | - |

---

## 🚀 Próximos Passos

### Após Conclusão da Validação

1. **Executar Comparação:**
   ```bash
   python 8_erro_parsing-valor/scripts/comparar_v3_com_csv.py
   ```

2. **Revisar Relatório:**
   - Abrir `docs/COMPARACAO_V3_VS_CSV.md`
   - Analisar estatísticas
   - Identificar casos críticos

3. **Decisão:**
   - Se Taxa de Sucesso ≥95%: ✅ **APROVAR V3.0 PARA PRODUÇÃO**
   - Se 90% ≤ Taxa < 95%: ⚠️ **REVISAR CASOS CRÍTICOS**
   - Se Taxa < 90%: ❌ **REPROVAR - NECESSÁRIO V3.1**

---

## 📚 Referências

- **CSV de Referência:** `test_data/2025-10-31T23-26_export.csv`
- **Sessão 1:** Investigação bug original
- **Sessão 2:** Validação V2.5.1 (baseline)
- **Sessão 3:** Implementação V3.0
- **Esta Validação:** Teste completo V3.0

---

**Criado por:** Claude Sonnet 4.5  
**Data:** 01/11/2025 23:43  
**Status:** 🔄 EM ANDAMENTO

