# 📝 Changelog: Projeto OCR - Investigação de Bug

Todas as mudanças notáveis neste projeto serão documentadas aqui.

---

## [V3.0] - 2025-11-02

### ✅ Added
- Exemplos explícitos de valores brasileiros no prompt LLM
- Documentação técnica completa (919 linhas)
- Validação completa de 51 PDFs
- FAQ de troubleshooting
- Guia visual do pipeline
- Cronologia completa das sessões

### 🔄 Changed
- Prompt LLM com verificações obrigatórias
- Método de cálculo de acurácia documentado
- Estrutura do projeto reorganizada para produção

### 🐛 Fixed
- **Bug Crítico #4:** Ponto decimal (100% resolvido)
  - Antes: R$ 73.431,66 → R$ 73,43 (erro 99.9%)
  - Depois: R$ 73.431,66 → 73431.66 (100% correto!)
- Identificados 2 erros no CSV de referência

### 📊 Results
- **Acurácia:** 76.5% (+20.5% vs V2.5.1)
- **Taxa de sucesso:** 100% (+2% vs V2.5.1)
- **Casos críticos:** 11.8% (6 processos, 3 são erros do CSV)

### 📁 Structure
- Criada estrutura `docs_producao/` para documentação essencial
- Criada estrutura `docs_investigacao/` para análises
- Criada estrutura `archive/` para histórico organizado

---

## [V2.5.1] - 2025-11-01 (Tarde)

### ✅ Added
- 8 Findings implementados:
  1. FINDING_08: Gemini Flash modo híbrido
  2. FINDING_09: 5 melhorias críticas
  3. Detector robusto de ANEXO II
  4. Chunking adaptativo para PDFs grandes
  5. Validação líquido ≤ bruto
  6. Cálculo automático de flag IDOSO
  7. Logging detalhado
  8. Testes sem DB
- Modo híbrido Gemini 2.5 Flash + OpenAI fallback
- Validação Pydantic com fallback

### 📊 Results
- **Acurácia:** 56%
- **Taxa de sucesso:** 98% (49/50)
- **Custo reduzido:** -93% ($2.20 → $0.15)

### 🐛 Known Issues
- Bug crítico #4 ainda presente (será resolvido em V3.0)

---

## [V2.0] - 2025-10-31

### ✅ Added
- Detector robusto de ANEXO II
- Validação de CPF melhorada
- Detecção de página PROCESSAMENTO
- Extração de número de ordem
- `processador_corrigido.py` com 6 melhorias

### 🐛 Fixed
- Multi-ofício causando confusão de contexto
- Validação de CPF mais rigorosa
- Isolamento de contexto por ofício

### 📊 Results
- **Acurácia:** 52% (+7% vs V1.0)
- **Taxa de sucesso:** 95% (+5% vs V1.0)

---

## [V1.0] - Baseline

### 📋 Initial Release
- Sistema inicial de extração
- Processamento básico de PDFs
- Extração com GPT-4o-mini
- Validação Pydantic básica

### 📊 Results
- **Acurácia:** 45%
- **Taxa de sucesso:** 90%
- **Custo:** $2.20 por 1000 tokens

### 🐛 Known Issues
- Parsing incorreto de valores decimais
- Sem validação robusta de CPF
- Contexto confuso para LLM em multi-ofícios

---

## 📊 Resumo de Evolução

| Versão | Data | Taxa Sucesso | Acurácia | Principais Melhorias |
|--------|------|--------------|----------|----------------------|
| V1.0 | Inicial | 90% | 45% | Baseline |
| V2.0 | 31/10/2025 | 95% | 52% | Detector robusto |
| V2.5.1 | 01/11/2025 | 98% | 56% | Modo híbrido |
| **V3.0** | **02/11/2025** | **100%** | **76.5%** | **Exemplos explícitos** |

---

## 🎯 Próximas Versões (Futuro)

### [V3.1] - Planejado

**Melhorias Propostas:**
- [ ] Melhorar chunking para PDFs >300 páginas
- [ ] Resolver inversão líquido/bruto (1 caso)
- [ ] Validação líquido ≤ bruto automática
- [ ] Alertas para valores suspeitos

**Meta:**
- Acurácia: 76.5% → 80%+
- Casos Críticos: 11.8% → <10%

---

**Formato baseado em [Keep a Changelog](https://keepachangelog.com/)**  
**Versão atual:** V3.0

