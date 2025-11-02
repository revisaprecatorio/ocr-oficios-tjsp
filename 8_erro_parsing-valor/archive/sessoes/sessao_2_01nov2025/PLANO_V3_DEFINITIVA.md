# 🚀 PLANO: Implementação e Teste da V3 Definitiva

**Data:** 01/11/2025 20:00  
**Objetivo:** Criar V3 Definitiva = V2.5.1 + Melhorias V3 para atingir ~98% de sucesso  
**Status:** 📋 Planejamento

---

## 🎯 OBJETIVO

Criar e validar **ProcessadorOficio V3 Definitiva** que combine:

**De V2.5.1 (Sessão 2):**
- ✅ Modo híbrido Gemini + OpenAI (93% economia)
- ✅ Validador Pydantic robusto (int → str)
- ✅ Tratamento de lista retornada
- ✅ Fallback OpenAI em validação
- ✅ Logging completo

**De V3 (Sessão 1):**
- ✅ Exemplos explícitos no prompt (formato brasileiro)
- ✅ Validação de sanidade de valores
- ✅ Alerta de multi-ofício
- ✅ Isolamento rigoroso de ofícios
- ✅ Verificação de tipos

**Meta:** Taxa de sucesso ≥ 98% (vs 96.1% atual)

---

## 📊 LISTA DE PDFs PROBLEMÁTICOS (8 casos)

### 🔴 Casos Críticos (5 PDFs) - Prioridade Máxima

| # | CPF | Processo | Erro | Gravidade | V3 Resolve? |
|---|-----|----------|------|-----------|-------------|
| 1 | 10155175874 | **7007859-54.2010.8.26.0500** | Juros não capturados (R$ 166k - 13.3%) | 🔴 Crítica | ❓ Parcial |
| 2 | 10732506875 | **0064242-25.2020.8.26.0500** | Líquido/Bruto invertidos (R$ 121k - 39%) | 🟡 Média | ✅ **SIM** |
| 3 | 51525003968 | **7002920-94.2011.8.26.0500** | Parsing incorreto (R$ 160k - 90%) | 🔴 Crítica | ✅ **SIM** |
| 4 | 94706751853 | **0176088-13.2021.8.26.0500** | Ponto decimal (R$ 73k - 99.9%) | 🔴 Crítica | ✅ **100%** |
| 5 | 93661509853 | **7009758-92.2007.8.26.0500** | Valor não capturado (R$ 1,125 - 100%) | 🔴 Crítica | ❓ Parcial |

### 🟢 Casos de Arredondamento (3 PDFs) - Prioridade Média

| # | CPF | Processo | Erro | Gravidade | V3 Resolve? |
|---|-----|----------|------|-----------|-------------|
| 6 | 10155175874 | 0176254-45.2021.8.26.0500 | Arredondamento (R$ 200 - 0.44%) | 🟢 Baixa | ❌ Não |
| 7 | 10004525817 | 0302248-83.2021.8.26.0500 | Arredondamento (R$ 115 - 0.21%) | 🟢 Baixa | ❌ Não |
| 8 | 11858371830 | 0069919-75.2016.8.26.0500 | Arredondamento (R$ 1.67 - 2.45%) | 🟢 Baixa | ❌ Não |

**Foco Inicial:** Casos críticos #1-5 (onde V3 pode fazer diferença)

---

## 🔧 ESTRATÉGIA DE IMPLEMENTAÇÃO

### FASE 1: Criação da V3 Definitiva

#### 1.1. Estrutura de Arquivos

```
3_OCR/
├── 1_parsing_PDF/
│   └── app/
│       ├── processador_v3.py (NOVO - V3 Definitiva)
│       ├── processador.py (V2.5.1 - manter para comparação)
│       ├── llm_adapter.py (atualizar com melhorias V3)
│       ├── schemas.py (já tem melhorias V2.5.1)
│       └── detector.py (adicionar isolamento V3)
│
└── 8_erro_parsing-valor/
    └── test_v3_definitiva/
        ├── test_casos_criticos.py
        ├── test_progressivo.py
        ├── resultados/
        │   ├── fase1_criticos.json
        │   ├── fase2_aleatorios.json
        │   └── comparacao_v2.5_vs_v3.md
        └── pdfs_teste/
            ├── criticos/ (5 PDFs problemáticos)
            ├── aleatorios/ (5 PDFs aleatórios)
            └── grandes/ (5 PDFs >100 páginas)
```

#### 1.2. Componentes a Implementar

**A. `processador_v3.py` - Pipeline Principal**
```python
class ProcessadorOficioV3(ProcessadorOficio):
    """
    V3 Definitiva = V2.5.1 + Melhorias V3
    
    Herda de ProcessadorOficio (V2.5.1) e adiciona:
    - Isolamento rigoroso de ofícios
    - Validação de sanidade
    - Prompt otimizado com exemplos
    - Alerta de multi-ofício
    """
```

**B. Melhorias no Prompt (V3)**
```python
# Adicionar ao prompt existente:
"""
⚠️ VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️

NO PDF:           RETORNE COMO:
"R$ 88.994,41" →  88994.41 (NUMBER)
"R$ 73.431,66" →  73431.66 (NUMBER)
"R$ 1.234.567,89" → 1234567.89 (NUMBER)

EXEMPLOS ERRADOS:
❌ "R$ 88.994,41" → "88.99" (truncou!)
❌ "R$ 73.431,66" → "73.43" (ponto como decimal!)
❌ "R$ 88.994,41" → "88994.41" (string!)

ATENÇÃO - LÍQUIDO vs BRUTO:
- Valor Principal LÍQUIDO: Valor APÓS descontos (menor)
- Valor Principal BRUTO: Valor ANTES de descontos (maior)
Regra: valor_liquido ≤ valor_bruto
"""
```

**C. Validação de Sanidade (V3)**
```python
def validar_sanidade_valores(self, dados: Dict) -> List[str]:
    """Valida valores para detectar parsing incorreto"""
    alertas = []
    
    # 1. Valores muito baixos
    for campo in ['valor_principal_liquido', 'valor_principal_bruto', 'valor_total_requisitado']:
        valor = dados.get(campo, 0)
        if valor > 0:
            if valor < 100:
                alertas.append(f"🚨 {campo}: R$ {valor:,.2f} < R$ 100 (MUITO SUSPEITO!)")
            elif valor < 1000:
                alertas.append(f"⚠️ {campo}: R$ {valor:,.2f} < R$ 1.000 (SUSPEITO)")
    
    # 2. Inversão líquido/bruto
    liquido = dados.get('valor_principal_liquido', 0)
    bruto = dados.get('valor_principal_bruto', 0)
    if liquido > 0 and bruto > 0 and liquido > bruto:
        alertas.append(f"🚨 INVERSÃO: Líquido (R$ {liquido:,.2f}) > Bruto (R$ {bruto:,.2f})")
    
    # 3. Inconsistência de totais
    total_declarado = dados.get('valor_total_requisitado', 0)
    total_calculado = bruto + dados.get('juros_moratorios', 0)
    if total_declarado > 0 and abs(total_declarado - total_calculado) > 500:
        alertas.append(f"⚠️ Inconsistência: Total declarado (R$ {total_declarado:,.2f}) vs calculado (R$ {total_calculado:,.2f})")
    
    return alertas
```

**D. Isolamento Rigoroso (V3)**
```python
def isolar_oficio_por_cpf(self, pdf_path: str, cpf_esperado: str) -> Dict:
    """
    Isola ofício específico em PDFs multi-ofício
    
    V3: Garante que apenas texto do ofício correto seja enviado ao LLM
    """
    todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
    
    # Alerta se múltiplos ofícios
    if len(todos_oficios) > 1:
        logger.warning(f"🚨 PDF com {len(todos_oficios)} ofícios - ISOLAMENTO CRÍTICO!")
    
    # Buscar ofício com CPF correto
    for idx, oficio in enumerate(todos_oficios):
        if cpf_esperado in oficio['texto']:
            logger.info(f"✅ Ofício {idx+1} isolado (CPF: {cpf_esperado})")
            return oficio
    
    # Se não encontrou, retornar primeiro
    logger.warning(f"⚠️ CPF {cpf_esperado} não encontrado, usando primeiro ofício")
    return todos_oficios[0]
```

---

## 📋 PLANO DE TESTES PROGRESSIVOS

### FASE 1: Testes com Casos Críticos (5 PDFs)

**Objetivo:** Validar que V3 resolve os casos onde V2.5.1 falhou

**PDFs a testar:**
1. ✅ `7007859-54.2010.8.26.0500` (juros não capturados)
2. ✅ `0064242-25.2020.8.26.0500` (líquido/bruto invertidos)
3. ✅ `7002920-94.2011.8.26.0500` (parsing incorreto)
4. ✅ `0176088-13.2021.8.26.0500` (ponto decimal - **caso crítico!**)
5. ✅ `7009758-92.2007.8.26.0500` (valor não capturado)

**Critérios de Sucesso:**
- [ ] Resolver caso #4 (ponto decimal) - **obrigatório**
- [ ] Resolver casos #2 e #3 (inversão + parsing)
- [ ] Melhorar casos #1 e #5 (alertar inconsistências)
- [ ] **Sucesso mínimo:** 3 de 5 resolvidos (60%)
- [ ] **Sucesso ideal:** 4 de 5 resolvidos (80%)

**Métricas a coletar:**
```json
{
  "pdf": "0176088-13.2021.8.26.0500",
  "versao": "V3",
  "valor_esperado": 73431.66,
  "valor_extraido": "?",
  "tempo_processamento": "?",
  "alertas_sanidade": [],
  "sucesso": true/false,
  "melhoria_vs_v2.5": "+99.9%"
}
```

---

### FASE 2: Testes com PDFs Aleatórios (5 PDFs)

**Objetivo:** Garantir que V3 não quebrou o que estava funcionando

**Critério de Seleção:**
- 5 PDFs aleatórios da lista de 50
- Excluir os 8 problemáticos
- Priorizar PDFs que tiveram 100% acurácia em V2.5.1

**PDFs sugeridos:**
```python
# Selecionar 5 aleatórios de:
pdfs_perfeitos = [
    "0033823-88.2021.8.26.0500",  # 2021, acurácia perfeita
    "0158003-37.2025.8.26.0500",  # 2025, processado perfeitamente
    "0220433-64.2021.8.26.0500",  # 2021, sem discrepâncias
    "0035938-67.2018.8.26.0053",  # 2018, histórico estável
    "0302248-83.2021.8.26.0500",  # 2021, valores corretos
]
```

**Critérios de Sucesso:**
- [ ] **Não regredir:** Manter 100% acurácia nos PDFs perfeitos
- [ ] **Tempo similar:** ±10% do tempo de V2.5.1
- [ ] **Custo mantido:** $2/1000 PDFs

---

### FASE 3: Testes com PDFs Grandes (5 PDFs)

**Objetivo:** Validar robustez em PDFs complexos

**Critério de Seleção:**
- 5 PDFs com >100 páginas
- Incluir o caso #1 (356 páginas)
- Testar chunking e contexto

**PDFs sugeridos:**
```python
pdfs_grandes = [
    "7007859-54.2010.8.26.0500",  # 356 páginas (já testado na Fase 1)
    # Identificar outros 4 PDFs grandes do dataset
]
```

**Critérios de Sucesso:**
- [ ] Processar sem timeout (<120s)
- [ ] Não perder contexto (juros capturados)
- [ ] Alertas de sanidade funcionando

---

## 🔄 PROCESSO DE TESTE PROGRESSIVO

### Passo 1: Preparação

```bash
# Criar ambiente de teste
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR
mkdir -p 8_erro_parsing-valor/test_v3_definitiva/{resultados,pdfs_teste/{criticos,aleatorios,grandes}}

# Copiar PDFs problemáticos
cp data/consultas/94706751853/0176088-13.2021.8.26.0500.pdf \
   8_erro_parsing-valor/test_v3_definitiva/pdfs_teste/criticos/

# (repetir para os outros 4 críticos)
```

### Passo 2: Implementação V3

```bash
# 1. Criar processador_v3.py
# 2. Atualizar llm_adapter.py com prompt V3
# 3. Adicionar validação de sanidade
# 4. Implementar isolamento robusto
```

### Passo 3: Teste Unitário (Caso Crítico #4)

```bash
# Testar apenas o caso mais crítico primeiro
python test_v3_definitiva/test_casos_criticos.py --pdf 0176088-13.2021.8.26.0500

# Verificar:
# ✅ Valor correto extraído (73431.66)
# ✅ Tipo NUMBER (não string)
# ✅ Alerta de sanidade não disparou
```

### Passo 4: Teste Completo - Fase 1 (5 Críticos)

```bash
# Testar todos os 5 casos críticos
python test_v3_definitiva/test_casos_criticos.py --todos

# Gerar relatório comparativo
python test_v3_definitiva/gerar_relatorio.py --fase 1
```

### Passo 5: Análise de Resultados - Fase 1

**Critérios de Aprovação:**
- Se ≥3 resolvidos → **Prosseguir para Fase 2**
- Se <3 resolvidos → **Revisar implementação V3**

### Passo 6: Teste Completo - Fase 2 (5 Aleatórios)

```bash
# Testar PDFs aleatórios
python test_v3_definitiva/test_progressivo.py --fase 2

# Verificar regressões
python test_v3_definitiva/comparar_v2.5_vs_v3.py
```

### Passo 7: Teste Completo - Fase 3 (5 Grandes)

```bash
# Testar PDFs grandes
python test_v3_definitiva/test_progressivo.py --fase 3

# Avaliar performance
python test_v3_definitiva/avaliar_performance.py
```

### Passo 8: Decisão Final

**Critérios de Deploy:**
- ✅ Fase 1: ≥60% casos críticos resolvidos
- ✅ Fase 2: 0 regressões em PDFs perfeitos
- ✅ Fase 3: Processamento estável de PDFs grandes
- ✅ Custo: Mantém $2/1000 PDFs

**Se aprovado:** Deploy V3 em produção  
**Se reprovado:** Iteração adicional

---

## 📊 MÉTRICAS DE SUCESSO

### Métricas Primárias

| Métrica | V2.5.1 (Atual) | V3 (Meta) | Melhoria |
|---------|----------------|-----------|----------|
| **Taxa de Sucesso** | 96.1% (49/51) | **≥98%** | **+1.9%** |
| **Discrepâncias Totais** | 16% (8/50) | **≤10%** | **-6%** |
| **Casos Críticos** | 10% (5/50) | **≤4%** | **-6%** |
| **Custo** | $2/1000 | **≤$2.5/1000** | **≤+25%** |

### Métricas Secundárias

| Métrica | V2.5.1 (Atual) | V3 (Meta) |
|---------|----------------|-----------|
| **Tempo Médio/PDF** | 27.5s | ≤35s (+27%) |
| **Alertas de Sanidade** | 0 | ≥5 (detecta problemas) |
| **Regressões** | N/A | 0 |

---

## 🤔 DÚVIDAS PARA CONFIRMAR

### 1. **Acesso aos PDFs Problemáticos**

❓ **Você tem acesso aos 5 PDFs críticos localmente?**

Caminhos esperados:
```
/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/data/consultas/
├── 94706751853/0176088-13.2021.8.26.0500.pdf  # Caso #4 - CRÍTICO!
├── 10732506875/0064242-25.2020.8.26.0500.pdf  # Caso #2
├── 51525003968/7002920-94.2011.8.26.0500.pdf  # Caso #3
├── 10155175874/7007859-54.2010.8.26.0500.pdf  # Caso #1
└── 93661509853/7009758-92.2007.8.26.0500.pdf  # Caso #5
```

---

### 2. **Estratégia de Implementação**

❓ **Preferência de abordagem:**

**Opção A (Recomendada):** Criar `processador_v3.py` como **classe herdada**
```python
class ProcessadorOficioV3(ProcessadorOficio):
    # Herda V2.5.1 e sobrescreve apenas métodos necessários
```
✅ Vantagem: Mantém V2.5.1 funcionando, fácil rollback  
❌ Desvantagem: Mais código duplicado

**Opção B:** Modificar `processador.py` diretamente
```python
# Adiciona flag: usar_melhorias_v3=True
```
✅ Vantagem: Um único arquivo  
❌ Desvantagem: Risco de quebrar V2.5.1

**Recomendação:** Opção A (herança)

---

### 3. **Modo de Teste**

❓ **Como testar sem afetar produção?**

**Proposta:**
```python
# Criar flag especial no processador:
processador = ProcessadorOficioV3(
    openai_api_key=...,
    db_config=...,
    modo_teste=True  # NÃO grava no banco
)
```

**Alternativa:** Usar banco de teste separado

---

### 4. **CSV de Referência**

❓ **Arquivo `2025-10-31T23-26_export.csv` ainda está atualizado?**

Caminho:
```
/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/8_erro_parsing-valor/test_data/2025-10-31T23-26_export.csv
```

Precisa conter os valores esperados para os 5 casos críticos.

---

### 5. **Seleção de PDFs para Fases 2 e 3**

❓ **Quer que eu selecione aleatoriamente os 10 PDFs ou você prefere escolher manualmente?**

**Proposta de Script:**
```python
# Selecionar automaticamente:
# - 5 aleatórios de PDFs perfeitos
# - 5 maiores (>100 páginas)
```

---

### 6. **Threshold de Sanidade**

❓ **Valores para alertas de sanidade:**

**Proposta:**
```python
THRESHOLDS = {
    'valor_muito_suspeito': 100,   # < R$ 100
    'valor_suspeito': 1000,        # < R$ 1.000
    'diferenca_total': 500,        # Diferença >R$ 500 em totais
}
```

Ajustar?

---

### 7. **Prioridade de Implementação**

❓ **Todas as 6 melhorias V3 ou focar nas mais críticas?**

**Sugestão de Priorização:**

**Prioridade ALTA (implementar já):**
1. ✅ Exemplos explícitos no prompt (valores brasileiros) ← Resolve caso #4
2. ✅ Validação de sanidade ← Detecta casos #2, #3, #5
3. ✅ Verificação de tipos ← Previne strings

**Prioridade MÉDIA (se tempo permitir):**
4. ✅ Isolamento rigoroso de ofícios ← Útil para multi-ofício
5. ✅ Alerta de multi-ofício ← Informativo

**Prioridade BAIXA (pode ficar para V3.1):**
6. ⏳ Logs ainda mais detalhados

---

## 📅 CRONOGRAMA SUGERIDO

### Hoje (01/11 - Noite)

- [x] ✅ Planejar V3 Definitiva
- [ ] ⏳ Confirmar dúvidas com usuário
- [ ] ⏳ Preparar ambiente de teste

### Amanhã (02/11)

- [ ] 🔧 Implementar V3 Definitiva
- [ ] 🧪 Testar Fase 1 (5 críticos)
- [ ] 📊 Analisar resultados
- [ ] ✅ Decidir prosseguir ou iterar

### Depois

- [ ] 🧪 Testar Fase 2 (5 aleatórios)
- [ ] 🧪 Testar Fase 3 (5 grandes)
- [ ] 📈 Relatório final
- [ ] 🚀 Deploy (se aprovado)

---

## ✅ PRÓXIMOS PASSOS IMEDIATOS

### 1. **Você confirma:**

- [ ] Acesso aos 5 PDFs críticos
- [ ] CSV de referência atualizado
- [ ] Preferência de implementação (Opção A ou B)
- [ ] Thresholds de sanidade OK
- [ ] Seleção automática de PDFs para Fases 2-3

### 2. **Eu vou:**

- [ ] Criar estrutura de teste
- [ ] Implementar `processador_v3.py`
- [ ] Criar scripts de teste progressivo
- [ ] Executar Fase 1 (5 críticos)
- [ ] Apresentar resultados

---

## 🎯 RESUMO EXECUTIVO

**O que vamos fazer:**
1. ✅ Criar V3 Definitiva (V2.5.1 + Melhorias V3)
2. ✅ Testar em 3 fases progressivas (5+5+5 PDFs)
3. ✅ Focar em resolver casos críticos primeiro
4. ✅ Garantir que não quebramos o que funciona
5. ✅ Decidir deploy baseado em métricas objetivas

**Resultado esperado:**
- Taxa de sucesso: 96.1% → ~98%
- Casos críticos: 10% → ~4%
- Custo mantido: $2/1000 PDFs

**Risco:** Baixo (testes progressivos, rollback fácil)

---

**Data de Criação:** 01/11/2025 20:00  
**Status:** 📋 Aguardando Confirmação  
**Próxima Ação:** Responder dúvidas 1-7

---

## ❓ CONFIRME AS DÚVIDAS ACIMA PARA PROSSEGUIR! 🚀

