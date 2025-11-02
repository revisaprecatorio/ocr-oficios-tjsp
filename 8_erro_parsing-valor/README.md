# 📚 Investigação e Resolução: Bug de Parsing de Valores

**Status:** ✅ RESOLVIDO - V3.0 em Produção  
**Acurácia:** 76.5% (↑ 20.5% vs V2.5.1)  
**Data Conclusão:** 02/11/2025

---

## 🎯 Problema Original

**Sintoma:**
Valores monetários brasileiros sendo truncados incorretamente.

**Exemplo:**
- PDF: `R$ 88.994,41`
- Extraído: `R$ 88,99`
- **Erro:** 99.9%

**PDF Afetado:**
- `Precatório-RAF.pdf` (CPF: 273.081.578-30)

---

## ✅ Solução Implementada (V3.0)

### Principal Melhoria

**Prompt LLM com exemplos explícitos de valores brasileiros:**

```python
EXEMPLOS CORRETOS:
"R$ 73.431,66" → 73431.66  (NUMBER)
"R$ 88.994,41" → 88994.41  (NUMBER)
"R$ 1.234.567,89" → 1234567.89 (NUMBER)
```

### Resultado

✅ **Bug crítico #4:** 100% resolvido!  
✅ **Taxa de sucesso:** 100% (51/51 PDFs)  
✅ **Acurácia perfeita:** 76.5% (39/51 processos)

---

## 📁 Estrutura do Projeto

```
8_erro_parsing-valor/
├── README.md                          ← Você está aqui
├── CHANGELOG.md                       ← Histórico de versões
│
├── 📁 docs_producao/                  ← Documentação para produção
│   ├── DOCUMENTACAO_TECNICA_V3.md
│   ├── GUIA_VISUAL_PIPELINE.md
│   ├── GUIA_INSTALACAO.md
│   ├── PROMPT_LLM_V3.md
│   └── FAQ_TROUBLESHOOTING.md
│
├── 📁 docs_investigacao/              ← Análise e investigação
│   ├── SUMARIO_EXECUTIVO.md
│   ├── CRONOLOGIA_SESSOES.md
│   ├── ROOT_CAUSE_ANALYSIS.md
│   └── EVOLUCAO_VERSOES.md
│
├── 📁 relatorios_validacao/          ← Relatórios de testes
│   ├── RELATORIO_FINAL_V3.md
│   ├── TABELA_COMPARACAO_51_PDFS.md
│   └── ANALISE_ACURACIA.md
│
├── 📁 scripts/                        ← Scripts de validação
│   ├── validacao_completa.py
│   ├── comparar_valores.py
│   └── monitor_validacao_v3.sh
│
├── 📁 test_data/                      ← Dados essenciais
│   ├── 2025-10-31T23-26_export.csv   ← CSV referência
│   ├── Precatório-RAF.pdf             ← PDF teste principal
│   ├── validacao_v3_final.csv
│   └── discrepancias_v3_final.json
│
└── 📁 archive/                        ← Histórico organizado
    ├── sessoes/                       ← S1 e S2 sumarizadas
    ├── scripts_historicos/            ← Scripts de teste
    ├── test_data_historico/          ← Dados antigos
    └── ab_tests/                      ← Resultados A/B
```

---

## 🚀 Quick Start

### Validar Sistema Completo

```bash
cd scripts/
source ../../.venv/bin/activate
python validacao_completa.py
```

### Ver Resultados Finais

```bash
cat test_data/validacao_2025-11-01_23-51-03.csv
```

### Monitorar Validação em Tempo Real

```bash
cd scripts/
./monitor_validacao_v3.sh
```

---

## 📊 Métricas Finais

### Comparação V2.5.1 → V3.0

| Métrica | V2.5.1 | V3.0 | Melhoria |
|---------|--------|------|----------|
| **Taxa de Sucesso** | 98% | **100%** | +2% ✅ |
| **Acurácia Perfeita** | 56% | **76.5%** | +20.5% 🎉 |
| **Casos Críticos** | 10% | 11.8% | -1.8% |

### Evolução V1.0 → V3.0

| Métrica | V1.0 | V3.0 | Melhoria Total |
|---------|------|------|----------------|
| **Taxa de Sucesso** | 90% | 100% | **+10%** ✅ |
| **Acurácia Perfeita** | 45% | 76.5% | **+31.5%** 🎉 |
| **Custo/1k tokens** | $2.20 | $0.15 | **-93%** 💰 |

---

## 📚 Documentação

### Para Produção

- [`docs_producao/`](docs_producao/) - Guias técnicos e operacionais
  - Instalação e configuração
  - Documentação técnica completa
  - Prompt LLM V3.0
  - FAQ e troubleshooting

### Investigação e Análise

- [`docs_investigacao/`](docs_investigacao/) - Análise root cause e evolução
  - Cronologia das 3 sessões
  - Evolução V1 → V2 → V3
  - Análise root cause do bug
  - Sumário executivo

### Relatórios de Validação

- [`relatorios_validacao/`](relatorios_validacao/) - Resultados dos testes
  - Relatório final V3.0
  - Comparação completa (51 PDFs)
  - Análise de acurácia detalhada

### Histórico

- [`archive/`](archive/) - Documentação histórica sumarizada
  - Resumos das sessões 1 e 2
  - Scripts de teste históricos
  - Dados de validações anteriores
  - Resultados de A/B tests

---

## 🎯 Caso de Teste Principal

### PDF: `Precatório-RAF.pdf`

**Especificações:**
- CPF: 273.081.578-30
- 4 páginas
- Contém 4 ofícios (multi-ofício)
- Valor esperado: R$ 88.994,41

**Resultados:**
- ✅ V3.0: **R$ 88.994,41** (100% correto!)
- ❌ V2.5.1: R$ 88,99 (erro 99.9%)
- ❌ V1.0: R$ 88,99 (erro 99.9%)

---

## 💡 Descobertas Importantes

### 1. CSV de Referência Tem Erros

**Descobrimos 2 processos com valores incorretos no CSV:**
- Processo 7009758: CSV R$ 1.125 vs Real R$ 1.125.002,73
- Processo 0179480: CSV R$ 64,37 vs Real R$ 64.370,22

**Conclusão:** V3.0 está **mais correto** que o CSV usado como referência!

### 2. Bug Era Específico de Multi-Ofício

**Root Cause:**
- PDFs com múltiplos ofícios causavam confusão de contexto
- LLM misturava valores entre ofícios
- Solução: Isolamento de contexto + validação de CPF rigorosa

---

## 🔧 Scripts Disponíveis

### Validação Completa

```bash
python scripts/validacao_completa.py
```

**Funcionalidade:**
- Processa todos os PDFs em `data/consultas/`
- Compara com CSV de referência
- Gera relatório detalhado

### Comparação de Valores

```bash
python scripts/comparar_valores.py
```

**Funcionalidade:**
- Compara valores extraídos com CSV
- Identifica discrepâncias
- Gera tabela de análise

### Monitor de Validação

```bash
./scripts/monitor_validacao_v3.sh
```

**Funcionalidade:**
- Monitora progresso em tempo real
- Mostra estatísticas atualizadas
- Útil para validações longas

---

## 📈 Estatísticas de Validação V3.0

**Total de PDFs:** 51  
**Taxa de Sucesso:** 100% (51/51)  
**Acurácia Perfeita:** 76.5% (39/51)  
**Casos Aceitáveis:** 11.8% (6/51)  
**Casos Críticos:** 11.8% (6/51)

**Casos Críticos Identificados:**
1. Processo 7007859 (356 páginas - chunking limitou contexto)
2. Processo 7009758 (CSV tinha erro)
3. Processo 0179480 (CSV tinha erro)
4. Processo 51525003968 (parsing incorreto)
5. Processo 10732506875 (inversão líquido/bruto)
6. Processo 10368599833 (CSV tinha erro)

**Conclusão:** 3 dos 6 "críticos" são na verdade erros no CSV, não no sistema!

---

## ✅ Status Final

### V3.0 APROVADO PARA PRODUÇÃO

**Justificativa:**
1. ✅ 100% taxa de sucesso (zero erros de processamento)
2. ✅ 76.5% acurácia perfeita (+20.5% vs V2.5.1)
3. ✅ Bug crítico #4 completamente resolvido
4. ✅ Custo reduzido 93% (Gemini híbrido)
5. ✅ Documentação técnica completa

---

## 👥 Contribuidores

- **Investigação:** Claude Sonnet 4.5
- **Supervisão:** Persival Balleste
- **Testes:** 51 PDFs reais de produção

---

## 📝 Licença

Este projeto faz parte do sistema OCR de Ofícios Requisitórios TJSP.

---

**Última Atualização:** 02/11/2025  
**Versão:** V3.0  
**Status:** ✅ **EM PRODUÇÃO**
