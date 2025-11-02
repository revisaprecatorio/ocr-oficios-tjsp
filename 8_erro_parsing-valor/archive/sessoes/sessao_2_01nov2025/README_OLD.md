# 🐛 Investigação: Erro de Parsing de Valores

**Data:** 31 de Outubro de 2025  
**Status:** Em Investigação

---

## 📋 Descrição do Problema

### Processo Afetado
- **Número do Processo:** 0015796-15.2025.8.26.0500
- **Número de Ordem:** 9594/2026
- **Vara:** 8ª VARA DE FAZENDA PÚBLICA
- **PDF:** `Precatório-RAF.pdf`

### Valores Incorretos

| Campo | Valor Correto (PDF) | Valor Extraído (Sistema) | Diferença |
|-------|---------------------|--------------------------|-----------|
| `valor_principal_liquido` | R$ 88.994,41 | R$ 88,99 | ❌ -88.905,42 |
| `valor_principal_bruto` | R$ 88.994,41 | R$ 88,99 | ❌ -88.905,42 |

### Hipótese do Bug

O sistema está interpretando incorretamente o separador de milhares:

```
Formato Brasileiro: 88.994,41
                       ↑      ↑
                    milhar  decimal

Sistema leu: 88.994 → 88 (ou 88,99?)
Ignorou: .994,41
```

**Root Cause Provável:**
- Validador Pydantic em `schemas.py` (método `arredondar_decimais`)
- Lógica de parsing assume formato americano (`.` = decimal)

---

## 📁 Estrutura da Pasta

```
8_erro_parsing-valor/
├── README.md                      # Este arquivo
├── test_data/
│   └── Precatório-RAF.pdf        # PDF problemático
├── test_outputs/
│   ├── json_extraido.json        # JSON gerado pelo processamento
│   ├── sql_statement.sql         # SQL que seria executado
│   └── tabela_valores.txt        # Tabela formatada com valores
├── test_scripts/
│   ├── test_parse_local.py       # Script de teste isolado
│   └── compare_values.py         # Comparação valores corretos vs extraídos
└── docs/
    ├── ANALISE_BUG.md            # Análise detalhada do bug
    └── SOLUCAO_PROPOSTA.md       # Solução proposta
```

---

## 🔧 Como Usar o Ambiente de Teste

### 1. Executar Teste Isolado

```bash
cd 8_erro_parsing-valor/test_scripts
python test_parse_local.py
```

**O script irá:**
- ✅ Processar o PDF localmente
- ✅ Extrair dados com GPT-4o-mini
- ✅ Validar com Pydantic
- ❌ **NÃO** gravar no banco de dados
- ✅ Gerar outputs em `test_outputs/`:
  - `json_extraido.json` - JSON completo
  - `sql_statement.sql` - SQL que seria executado
  - `tabela_valores.txt` - Tabela formatada

### 2. Comparar Valores

```bash
python compare_values.py
```

Compara valores extraídos vs valores corretos do PDF.

---

## 📊 Valores Corretos (Referência)

Extraídos manualmente do ANEXO II do PDF:

```
Total requerido: R$ 88.994,41 (OITENTA E OITO MIL, NOVECENTOS E NOVENTA E QUATRO REAIS E QUARENTA E UM CENTAVOS)

Principal/Indenização: R$ 88.994,41
Juros Moratórios: R$ 0,00 (ZERO)

Valor compensado (Art. 100): R$ 0,00 (ZERO)

Contribuições:
- INST.PREV. (IPREMSAOPAULO): R$ 0,00 (ZERO)
- ASSIST.MED. (HSPMSAOPAULO): R$ 0,00 (ZERO)
- Salário Pericial: R$ 0,00 (ZERO)
- Assist. Técnico: R$ 0,00 (ZERO)
- Custas: R$ 0,00 (ZERO)
- Despesas: R$ 0,00 (ZERO)
- Multas: R$ 0,00 (ZERO)
```

---

## 🎯 Próximos Passos

1. ✅ Criar ambiente de teste isolado
2. 🔄 Executar `test_parse_local.py` e analisar outputs
3. 🔍 Identificar onde o erro ocorre:
   - LLM extraction (GPT-4o-mini)?
   - Validação Pydantic (`arredondar_decimais`)?
   - Conversão String → Decimal?
4. 🛠️ Implementar correção
5. ✅ Validar com teste
6. 📝 Documentar solução

---

## 🔗 Arquivos Relacionados

**Sistema OCR:**
- `3_OCR/1_parsing_PDF/app/schemas.py` - Validadores Pydantic
- `3_OCR/1_parsing_PDF/app/processador.py` - Pipeline de processamento
- `3_OCR/README.md` - Documentação geral

**Teste:**
- `test_scripts/test_parse_local.py` - Script de teste
- `test_outputs/` - Resultados do processamento

---

**Última Atualização:** 31/10/2025

