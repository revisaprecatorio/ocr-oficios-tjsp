# Resultados da Validação Parcial do Sistema OCR

**Data:** 31 de outubro de 2025  
**Status:** Processamento parcial (16/51 PDFs processados)  
**Tempo de execução:** ~5 minutos (interrompido por timeout)

---

## Resumo Executivo

✅ **PDFs Processados:** 16/51 (31%)  
✅ **Sucessos:** 16/16 (100%)  
⚠️ **Discrepâncias Encontradas:** 3 (18.75% dos processados)

---

## Discrepâncias Identificadas

### 1. CPF: 10155175874 | Processo: 0176254-45.2021.8.26.0500

**Severidade:** BAIXA (0.4%)

| Campo | Processado | Referência | Diferença | % |
|-------|-----------|------------|-----------|---|
| `valor_principal_liquido` | R$ 45,495.57 | R$ 45,695.57 | R$ 200.00 | 0.4% |
| `valor_principal_bruto` | R$ 45,495.57 | R$ 45,695.57 | R$ 200.00 | 0.4% |
| `valor_total_requisitado` | R$ 45,495.57 | R$ 45,695.57 | R$ 200.00 | 0.4% |

**Análise:**
- Diferença consistente de R$ 200 em todos os campos
- Possível erro de arredondamento ou valor complementar não identificado
- Requer investigação manual do PDF original

---

### 2. CPF: 10155175874 | Processo: 7007859-54.2010.8.26.0500

**Severidade:** 🔴 ALTA (13.3%)

| Campo | Processado | Referência | Diferença | % |
|-------|-----------|------------|-----------|---|
| `valor_principal_bruto` | R$ 1,098,664.34 | R$ 1,097,665.34 | R$ 999.00 | 0.1% |
| `valor_total_requisitado` | R$ 1,087,665.34 | R$ 1,253,909.97 | **R$ 166,244.63** | **13.3%** |

**Análise:**
- **CRÍTICO:** Diferença de 13.3% no valor total requisitado
- Discrepância de ~R$ 166 mil reais
- Possível causa:
  - PDF multi-ofício com contexto confuso
  - Valores adicionais (juros, contribuições) não identificados corretamente
  - LLM pode ter extraído valores de ofício incorreto
- **REQUER INVESTIGAÇÃO URGENTE**

---

### 3. CPF: 10004525817 | Processo: 0302248-83.2021.8.26.0500

**Severidade:** BAIXA (0.2%)

| Campo | Processado | Referência | Diferença | % |
|-------|-----------|------------|-----------|---|
| `valor_principal_liquido` | R$ 55,351.65 | R$ 55,466.88 | R$ 115.23 | 0.2% |
| `valor_total_requisitado` | R$ 55,351.65 | R$ 55,466.88 | R$ 115.23 | 0.2% |

**Análise:**
- Diferença de ~R$ 115
- Similar ao caso 1 (diferença consistente)
- Pode ser erro de arredondamento ou valor complementar

---

## PDFs Processados com Sucesso (sem discrepâncias)

1. ✅ 11659296862/0220433-64.2021.8.26.0500
2. ✅ 10103818812/0179484-95.2021.8.26.0500
3. ✅ 47116781820/7002129-28.2011.8.26.0500 (PDF com 29 ofícios!)
4. ✅ 10149607890/0222597-02.2021.8.26.0500
5. ✅ 10149607890/0180896-61.2021.8.26.0500
6. ⚠️ 10155175874/0176254-45.2021.8.26.0500 (com discrepância)
7. ⚠️ 10155175874/7007859-54.2010.8.26.0500 (com discrepância)
8. ✅ 07620857893/0077044-50.2023.8.26.0500
9. ✅ 10077339851/0181664-84.2021.8.26.0500
10. ✅ 10381700879/0044489-48.2021.8.26.0500
11. ✅ 10381700879/0137880-57.2021.8.26.0500 (PDF com 13 ofícios!)
12. ✅ 12392368830/0181988-74.2021.8.26.0500
13. ⚠️ 10004525817/0302248-83.2021.8.26.0500 (com discrepância)
14. ✅ 06495530803/7007473-24.2010.8.26.0500 (PDF com 19 ofícios!)
15. ✅ 06495530803/0179487-50.2021.8.26.0500
16. ✅ 06495530803/0223266-55.2021.8.26.0500

---

## Observações Importantes

### PDFs Multi-Ofício Processados Corretamente
- **47116781820/7002129-28.2011.8.26.0500:** 29 ofícios ✅
- **10381700879/0137880-57.2021.8.26.0500:** 13 ofícios ✅
- **06495530803/7007473-24.2010.8.26.0500:** 19 ofícios ✅

O sistema está lidando bem com PDFs multi-ofício!

### Taxa de Sucesso
- **100%** dos PDFs foram processados sem erros
- **81.25%** dos PDFs apresentaram valores corretos
- **18.75%** dos PDFs apresentaram discrepâncias (pequenas ou críticas)

---

## Próximos Passos

### Investigação Prioritária

1. **🔴 URGENTE:** Investigar o caso 2 (CPF 10155175874, diferença de 13.3%)
   - Baixar e analisar o PDF `7007859-54.2010.8.26.0500`
   - Verificar se é um PDF multi-ofício
   - Identificar por que o valor total está tão diferente

2. **Casos Secundários:** Investigar casos 1 e 3 (diferenças pequenas)
   - Verificar se são erros de arredondamento sistemáticos
   - Identificar padrão comum

### Continuar Validação

3. **Processar os 35 PDFs restantes** (68% ainda não processados)
   - Aumentar timeout ou processar em lotes
   - Gerar relatório final completo

### Melhorias Sugeridas

4. **Implementar validação de sanidade:**
   - Alertar quando diferença percentual > 5%
   - Verificar se valor_total = soma dos componentes

5. **Logging detalhado:**
   - Salvar contexto enviado ao LLM para casos com discrepância
   - Facilitar debugging post-mortem

---

## Conclusões Parciais

1. **Sistema está funcionando bem** na maioria dos casos (81.25% de acurácia)
2. **PDFs multi-ofício estão sendo processados corretamente** (não causam problemas sistemáticos)
3. **Existe 1 caso crítico** com diferença de 13.3% que requer investigação urgente
4. **Diferenças pequenas (~R$ 115-200)** podem ser sistemáticas e merecem atenção

---

**Relatório gerado automaticamente pela ferramenta de validação**  
**Arquivo de log:** `validacao_output.log`  
**Script:** `validacao_completa.py`

