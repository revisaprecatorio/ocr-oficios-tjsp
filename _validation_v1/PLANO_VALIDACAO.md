# 📋 Plano de Validação v1 - Sistema OCR Ofícios Requisitórios TJSP

**Data**: 13 de outubro de 2025  
**Objetivo**: Validar extração de dados de PDFs de Ofícios Requisitórios para JSON estruturado  
**Escopo**: ETAPA 1 (PDFs → JSONs) - PostgreSQL será testado posteriormente

---

## 🎯 Objetivos da Validação

### Objetivo Principal
Validar que o sistema consegue:
1. ✅ Detectar ofícios requisitórios em PDFs nativos do TJSP
2. ✅ Extrair dados estruturados usando LLM (OpenAI)
3. ✅ Validar dados com Pydantic
4. ✅ Gerar JSONs corretos e completos
5. ✅ Identificar anomalias e PDFs problemáticos

### Critérios de Sucesso
- **Taxa de detecção**: ≥95% dos PDFs válidos
- **Taxa de extração**: ≥90% dos campos obrigatórios
- **Qualidade dos dados**: 100% dos JSONs válidos segundo schema Pydantic
- **Dados bancários (ANEXO II)**: 100% dos processos devem ter dados bancários

---

## 📊 Análise do Uso do LLM

### Onde o LLM é Usado
**Arquivo**: `app/processador.py` (método `_extrair_dados_llm`)  
**Linha**: 181-257

### Input do LLM
```
TIPO: Texto extraído do PDF (PyMuPDF)
CONTEÚDO:
  - Texto completo do Ofício Requisitório
  - Texto do ANEXO II (se presente)
  - Separadores de página

TAMANHO ESTIMADO:
  - Ofício típico: 2.000-5.000 tokens (~8-20 KB de texto)
  - Ofício + ANEXO II: 3.000-7.000 tokens (~12-28 KB de texto)
  - Casos extremos: até 15.000 tokens (~60 KB de texto)
```

### Task do LLM
**Tarefa**: Extração estruturada de informações (Information Extraction)

**Prompt estruturado**:
- Instruções claras sobre formato de saída (JSON)
- Lista de campos obrigatórios e opcionais
- Regras de normalização (datas, valores, formatação)
- Contexto do documento (Ofício Requisitório TJSP)

**Características**:
- ❌ **NÃO precisa ser multimodal** (apenas texto)
- ✅ **Precisa de boa compreensão de português jurídico**
- ✅ **Precisa seguir instruções estruturadas rigorosamente**
- ✅ **Precisa gerar JSON válido**

### Output do LLM
```json
{
  "processo_origem": "0158003-37.2025.8.26.0500",
  "requerente_caps": "NOME COMPLETO EM MAIÚSCULAS",
  "vara": "1ª Vara de Fazenda Pública",
  "valor_total_requisitado": 150000.00,
  "banco": "341",
  "agencia": "1234",
  "conta": "12345-6",
  "conta_tipo": "corrente",
  ...
}
```

### Próxima Fase do Processamento
1. **Parse JSON** → Dicionário Python
2. **Validação Pydantic** → `OficioRequisitorio` model
3. **Combinação com Metadata** → `OficioCompleto`
4. **Serialização** → Arquivo JSON em `output/json/{cpf}/{processo}.json`

---

## 🤖 Seleção do Modelo OpenAI

### Análise de Requisitos

| Requisito | Necessidade |
|-----------|-------------|
| **Janela de contexto** | 16K-32K tokens (ofícios longos) |
| **Multimodal** | ❌ Não (apenas texto) |
| **Seguir instruções** | ✅ Crítico (JSON estruturado) |
| **Português** | ✅ Essencial (documentos jurídicos BR) |
| **Custo** | 💰 Moderado (50 docs/dia em produção) |
| **Velocidade** | ⚡ Não crítico (batch processing) |

### Modelos Disponíveis (OpenAI - Out 2025)

#### **Opção 1: GPT-4o-mini** ⭐ **RECOMENDADO**
```
Modelo: gpt-4o-mini
Contexto: 128K tokens
Custo: $0.150/1M input, $0.600/1M output
Velocidade: Rápido
Qualidade: Excelente para extração estruturada
```

**Vantagens**:
- ✅ Janela de contexto enorme (128K tokens)
- ✅ Excelente em seguir instruções estruturadas
- ✅ Ótimo custo-benefício
- ✅ Suporta português perfeitamente
- ✅ Rápido (importante para testes)

**Custo estimado**:
- Ofício médio: ~4.000 tokens input, ~500 tokens output
- Custo por documento: ~$0.0009 (menos de 1 centavo)
- 50 docs/dia: ~$0.045/dia = **$1.35/mês**

#### **Opção 2: GPT-4o**
```
Modelo: gpt-4o
Contexto: 128K tokens
Custo: $2.50/1M input, $10.00/1M output
Velocidade: Moderado
Qualidade: Máxima
```

**Vantagens**:
- ✅ Qualidade máxima
- ✅ Melhor compreensão de contexto complexo

**Desvantagens**:
- ❌ ~17x mais caro que gpt-4o-mini
- ❌ Mais lento

**Custo estimado**:
- 50 docs/dia: ~$0.75/dia = **$22.50/mês**

#### **Opção 3: GPT-3.5-turbo**
```
Modelo: gpt-3.5-turbo
Contexto: 16K tokens
Custo: $0.50/1M input, $1.50/1M output
Velocidade: Muito rápido
Qualidade: Boa
```

**Desvantagens**:
- ⚠️ Contexto limitado (16K pode ser insuficiente para ofícios longos)
- ⚠️ Menos preciso em seguir instruções estruturadas

### 🏆 Decisão: **GPT-4o-mini**

**Justificativa**:
1. **Custo-benefício ideal**: $1.35/mês em produção
2. **Contexto suficiente**: 128K tokens cobre todos os casos
3. **Qualidade comprovada**: Excelente em extração estruturada
4. **Velocidade**: Importante para testes iterativos

**Configuração**:
```python
modelo_gpt = "gpt-4o-mini"
```

---

## 📁 Estrutura de Dados Confirmada

### Estrutura de Pastas
```
data/consultas/
├── {cpf_11_digitos}/          # Ex: 02174781824
│   ├── {processo_cnj}.pdf     # Ex: 0158003-37.2025.8.26.0500.pdf
│   └── ...
└── ...
```

### Variável de Ambiente
```bash
BASE_DIR=./data/consultas
```

---

## 🧪 Estratégia de Testes

### Fase 1: Teste Unitário (3 PDFs)
**Objetivo**: Validar pipeline básico

**Seleção de PDFs**:
1. **PDF pequeno** (~2-3 MB) - caso típico
2. **PDF médio** (~5-7 MB) - com ANEXO II
3. **PDF diferente** - testar variações de formato

**Validações**:
- ✅ Detecção do ofício
- ✅ Detecção do ANEXO II
- ✅ Extração de campos obrigatórios
- ✅ Validação Pydantic
- ✅ Geração de JSON

### Fase 2: Teste de Amostra (10 PDFs)
**Objetivo**: Validar robustez e identificar padrões de erro

**Seleção de PDFs**:
- 10 PDFs aleatórios de diferentes CPFs
- Variedade de tamanhos (2-10 MB)
- Diferentes varas

**Validações**:
- ✅ Taxa de sucesso ≥90%
- ✅ Identificação de anomalias
- ✅ Qualidade dos dados extraídos
- ✅ Performance (tempo/custo)

### Fase 3: Teste de Lote (30 PDFs)
**Objetivo**: Validar em escala e refinar processo

**Seleção de PDFs**:
- 30 PDFs representativos
- Incluir casos extremos identificados na Fase 2

**Validações**:
- ✅ Taxa de sucesso ≥95%
- ✅ Consistência dos dados
- ✅ Logs de anomalias completos
- ✅ Estatísticas finais

### Fase 4: Teste Massivo (100+ PDFs)
**Objetivo**: Validação final antes de produção

**Após aprovação das fases anteriores**

---

## 📝 Premissas Confirmadas

### Sobre os PDFs
1. ✅ **Todos são PDFs nativos** (com texto pesquisável)
2. ✅ **Todos são do TJSP** (Tribunal de Justiça de São Paulo)
3. ✅ **Todos seguem padrão de Ofício Requisitório**
4. ✅ **Todos devem ter ANEXO II** (dados bancários obrigatórios)
5. ⚠️ **PDFs escaneados** são anomalias (tratar separadamente)
6. ⚠️ **PDFs muito grandes** (>50 MB) são anomalias (tratar separadamente)

### Sobre a Extração
1. ✅ **Campos obrigatórios**: `processo_origem`, `requerente_caps`
2. ✅ **Dados bancários obrigatórios**: `banco`, `agencia`, `conta`, `conta_tipo`
3. ✅ **Validação rigorosa**: Pydantic com validadores customizados
4. ✅ **Dados extraídos mantidos como estão** (sem transformações adicionais)

### Sobre o Processamento
1. ✅ **Ambiente de dev**: Mac (local)
2. ✅ **Processamento em batch** (sem preocupação com latência)
3. ✅ **Foco em qualidade** (não em velocidade)
4. ✅ **Subsets de 10 em 10** para testes iterativos
5. ✅ **Logs detalhados** de anomalias

---

## 🚨 Tratamento de Anomalias

### Tipos de Anomalias Identificadas

#### 1. PDFs Escaneados (Baixa Qualidade)
**Detecção**:
- PyMuPDF extrai pouco ou nenhum texto
- Tamanho do arquivo muito grande (>20 MB) para poucas páginas

**Ação**:
- ❌ Não processar
- 📝 Registrar em `anomalias_pdfs_escaneados.json`
- 🔄 Tratar em fase futura (OCR)

#### 2. PDFs Muito Grandes
**Detecção**:
- Tamanho do arquivo >50 MB
- Número de páginas >100

**Ação**:
- ❌ Não processar
- 📝 Registrar em `anomalias_pdfs_grandes.json`
- 🔄 Tratar separadamente

#### 3. Ofício Não Detectado
**Detecção**:
- Detector retorna páginas vazias
- Score de critérios <2/3

**Ação**:
- ❌ Não processar
- 📝 Registrar em `anomalias_oficio_nao_detectado.json`
- 🔍 Analisar manualmente

#### 4. ANEXO II Não Encontrado
**Detecção**:
- Detector ANEXO II retorna vazio
- Campos bancários ausentes no JSON

**Ação**:
- ⚠️ Processar ofício normalmente
- 📝 Registrar em `anomalias_sem_anexo_ii.json`
- 🔴 **CRÍTICO**: Todos devem ter ANEXO II

#### 5. Falha na Extração LLM
**Detecção**:
- Erro na chamada OpenAI API
- JSON inválido retornado
- Timeout

**Ação**:
- 🔄 Retry automático (até 3 tentativas)
- ❌ Se falhar, registrar em `anomalias_falha_llm.json`
- 📝 Incluir resposta do LLM para debug

#### 6. Falha na Validação Pydantic
**Detecção**:
- Campos obrigatórios ausentes
- Formato inválido (CNJ, CPF, etc.)
- Valores fora do range

**Ação**:
- ❌ Não gerar JSON
- 📝 Registrar em `anomalias_validacao_pydantic.json`
- 📝 Incluir dados brutos do LLM

### Estrutura de Logs de Anomalias

```json
{
  "timestamp": "2025-10-13T14:30:00",
  "tipo_anomalia": "sem_anexo_ii",
  "cpf": "02174781824",
  "numero_processo": "0158003-37.2025.8.26.0500",
  "arquivo_pdf": "data/consultas/02174781824/0158003-37.2025.8.26.0500.pdf",
  "tamanho_arquivo_mb": 6.2,
  "detalhes": {
    "paginas_oficio_detectadas": [1, 2, 3],
    "paginas_anexo_ii_detectadas": [],
    "texto_extraido_length": 5234
  },
  "acao_recomendada": "Verificar manualmente se ANEXO II existe no PDF"
}
```

---

## 📂 Estrutura de Outputs

### Diretório de Validação
```
_validation_v1/
├── PLANO_VALIDACAO.md              # Este documento
├── PREMISSAS.md                    # Premissas detalhadas
├── MODELO_LLM_ANALISE.md           # Análise de seleção do modelo
├── outputs/
│   ├── fase1_teste_unitario/
│   │   ├── jsons/                  # JSONs gerados
│   │   ├── logs/                   # Logs de processamento
│   │   ├── anomalias/              # Logs de anomalias
│   │   └── relatorio_fase1.md      # Relatório da fase
│   ├── fase2_amostra_10/
│   ├── fase3_lote_30/
│   └── fase4_massivo/
└── scripts/
    ├── validar_fase1.sh            # Script para Fase 1
    ├── validar_fase2.sh            # Script para Fase 2
    └── analisar_anomalias.py       # Script de análise
```

---

## ✅ Checklist de Validação

### Pré-requisitos
- [ ] Ambiente virtual Python criado e ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] `.env` configurado com `OPENAI_API_KEY`
- [ ] `.env` configurado com `BASE_DIR=./data/consultas`
- [ ] Modelo atualizado para `gpt-4o-mini`
- [ ] PDFs organizados em `data/consultas/{cpf}/{processo}.pdf`

### Fase 1: Teste Unitário (3 PDFs)
- [ ] Selecionar 3 PDFs representativos
- [ ] Executar `python exportar_json.py --input ./data/consultas --output ./_validation_v1/outputs/fase1_teste_unitario --limite 3`
- [ ] Verificar JSONs gerados
- [ ] Analisar logs de processamento
- [ ] Identificar anomalias
- [ ] Validar campos obrigatórios
- [ ] Validar dados bancários (ANEXO II)
- [ ] Gerar relatório da Fase 1

### Fase 2: Amostra (10 PDFs)
- [ ] Selecionar 10 PDFs aleatórios
- [ ] Executar processamento
- [ ] Calcular taxa de sucesso
- [ ] Analisar padrões de erro
- [ ] Refinar detecção se necessário
- [ ] Gerar relatório da Fase 2

### Fase 3: Lote (30 PDFs)
- [ ] Selecionar 30 PDFs representativos
- [ ] Executar processamento
- [ ] Validar taxa de sucesso ≥95%
- [ ] Consolidar logs de anomalias
- [ ] Gerar estatísticas finais
- [ ] Gerar relatório da Fase 3

### Fase 4: Massivo (Aprovação)
- [ ] Revisar resultados das fases anteriores
- [ ] Aprovar para processamento massivo
- [ ] Executar em todos os PDFs disponíveis
- [ ] Gerar relatório final

---

## 📊 Métricas de Sucesso

### Métricas Primárias
| Métrica | Meta | Crítico |
|---------|------|---------|
| Taxa de detecção de ofícios | ≥95% | ✅ |
| Taxa de extração completa | ≥90% | ✅ |
| Taxa de validação Pydantic | 100% | ✅ |
| Taxa de ANEXO II detectado | 100% | ✅ |

### Métricas Secundárias
| Métrica | Meta | Crítico |
|---------|------|---------|
| Tempo médio por PDF | <60s | ❌ |
| Custo médio por PDF | <$0.001 | ❌ |
| Taxa de anomalias | <5% | ⚠️ |

---

## 🔄 Próximos Passos

1. **Atualizar AGENTS.md** com estrutura correta (`data/consultas/`)
2. **Atualizar modelo** de `gpt-5-nano-2025-08-07` para `gpt-4o-mini`
3. **Confirmar BASE_DIR** no `.env`
4. **Criar scripts de validação** para cada fase
5. **Executar Fase 1** (3 PDFs)
6. **Revisar resultados** e ajustar se necessário
7. **Prosseguir para Fase 2**

---

**Status**: 🟡 Aguardando aprovação para iniciar testes  
**Responsável**: Validação v1  
**Última atualização**: 13/10/2025
