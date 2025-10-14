# 🔄 Mudanças Implementadas - Validação v1

**Data**: 13 de outubro de 2025  
**Objetivo**: Preparar sistema para validação com premissas atualizadas

---

## 📝 Resumo das Mudanças

### 1. Atualização do AGENTS.md ✅

#### Estrutura de Pastas
**Antes**:
```
./Processos/{cpf}/{processo}.pdf
BASE_DIR=./Processos
```

**Depois**:
```
./data/consultas/{cpf}/{processo}.pdf
BASE_DIR=./data/consultas
```

#### Modelo LLM
**Antes**:
```python
modelo = "gpt-5-nano-2025-08-07"
pricing = "$0.05/1M input, $0.40/1M output"
```

**Depois**:
```python
modelo = "gpt-4o-mini"
pricing = "$0.150/1M input, $0.600/1M output"
```

#### Estimativas de Custo
**Antes**: 51 PDFs = $0.51

**Depois**: 50 PDFs/dia = $0.045/dia = $1.35/mês

---

### 2. Atualização do Código ✅

#### `app/processador.py`

**Linha 42** - Modelo atualizado:
```python
# Antes
self.modelo_gpt = "gpt-5-nano-2025-08-07"

# Depois
self.modelo_gpt = "gpt-4o-mini"
```

**Linha 183** - Docstring atualizada:
```python
# Antes
"""Extrai dados estruturados do texto do ofício usando GPT-5 Nano."""

# Depois
"""Extrai dados estruturados do texto do ofício usando GPT-4o-mini."""
```

**Linha 236** - Temperatura adicionada:
```python
# Antes
response = self.client.chat.completions.create(
    model=self.modelo_gpt,
    messages=[{"role": "user", "content": prompt}]
    # GPT-5 Nano usa temperatura padrão (1), não suporta temperature=0
)

# Depois
response = self.client.chat.completions.create(
    model=self.modelo_gpt,
    messages=[{"role": "user", "content": prompt}],
    temperature=0  # Determinístico para extração estruturada
)
```

---

### 3. Documentação Criada ✅

#### Novos Documentos em `_validation_v1/`

1. **PLANO_VALIDACAO.md**
   - Plano completo de validação em 4 fases
   - Análise detalhada do uso do LLM
   - Seleção e justificativa do modelo GPT-4o-mini
   - Estratégia de testes (3 → 10 → 30 → 100+ PDFs)
   - Tratamento de anomalias
   - Métricas de sucesso

2. **PREMISSAS.md**
   - Todas as premissas confirmadas documentadas
   - Estrutura de dados
   - Características dos PDFs
   - Dados obrigatórios (incluindo ANEXO II)
   - Critérios de detecção
   - Ambiente de desenvolvimento
   - Métricas de qualidade

3. **MUDANCAS_IMPLEMENTADAS.md** (este documento)
   - Resumo de todas as mudanças
   - Comparação antes/depois
   - Checklist de validação

---

### 4. Scripts de Validação ✅

#### `_validation_v1/scripts/validar_fase1.sh`
- Script automatizado para Fase 1 (3 PDFs)
- Verificações de ambiente
- Execução do processamento
- Análise de resultados
- Instruções de próximos passos

**Permissões**: Executável (`chmod +x`)

---

## 🎯 Análise do Modelo LLM

### Por Que GPT-4o-mini?

#### Requisitos do Sistema
| Requisito | GPT-4o-mini | GPT-4o | GPT-3.5-turbo |
|-----------|-------------|---------|---------------|
| **Contexto** | 128K ✅ | 128K ✅ | 16K ⚠️ |
| **Multimodal** | Não (OK) ✅ | Sim (desnecessário) | Não ✅ |
| **Português** | Excelente ✅ | Excelente ✅ | Bom ⚠️ |
| **Instruções** | Excelente ✅ | Máximo ✅ | Bom ⚠️ |
| **Custo/doc** | $0.0009 ✅ | $0.015 ❌ | $0.0012 ✅ |
| **Velocidade** | Rápido ✅ | Moderado ⚠️ | Muito rápido ✅ |

#### Decisão
**GPT-4o-mini** oferece o melhor **custo-benefício**:
- ✅ Contexto suficiente (128K tokens)
- ✅ Qualidade excelente para extração estruturada
- ✅ Custo baixo ($1.35/mês para 50 docs/dia)
- ✅ Velocidade adequada para testes iterativos

---

## 📊 Uso do LLM no Sistema

### Onde é Usado
**Arquivo**: `app/processador.py`  
**Método**: `_extrair_dados_llm()`  
**Linhas**: 181-257

### Input
```
TIPO: Texto extraído do PDF (PyMuPDF)
TAMANHO: 2.000-7.000 tokens (~8-28 KB)
CONTEÚDO:
  - Texto completo do Ofício Requisitório
  - Texto do ANEXO II (se presente)
  - Separadores de página
```

### Task
**Extração estruturada de informações** (Information Extraction)

**Características**:
- Prompt estruturado com instruções claras
- Lista de campos obrigatórios e opcionais
- Regras de normalização (datas, valores, formatação)
- Output: JSON válido

### Output
```json
{
  "processo_origem": "0158003-37.2025.8.26.0500",
  "requerente_caps": "NOME EM MAIÚSCULAS",
  "vara": "1ª Vara de Fazenda Pública",
  "valor_total_requisitado": 150000.00,
  "banco": "341",
  "agencia": "1234",
  "conta": "12345-6",
  "conta_tipo": "corrente",
  ...
}
```

### Próxima Fase
1. Parse JSON → Dict Python
2. Validação Pydantic → `OficioRequisitorio`
3. Combinação com Metadata → `OficioCompleto`
4. Serialização → `output/json/{cpf}/{processo}.json`

---

## 🚨 Premissas Críticas Confirmadas

### Dados Obrigatórios

#### Campos do Ofício
- ✅ `processo_origem` (formato CNJ)
- ✅ `requerente_caps` (MAIÚSCULAS)

#### Dados Bancários (ANEXO II) - **OBRIGATÓRIOS**
- ✅ `banco` (código do banco)
- ✅ `agencia` (número da agência)
- ✅ `conta` (número da conta com dígito)
- ✅ `conta_tipo` (corrente/poupança)

**⚠️ IMPORTANTE**: Todos os processos **DEVEM** ter ANEXO II. Se não houver, é considerado **anomalia crítica**.

### Estrutura de Pastas
```
data/consultas/
├── {cpf_11_digitos}/
│   ├── {processo_cnj}.pdf
│   └── ...
└── ...
```

**Variável de ambiente**:
```bash
BASE_DIR=./data/consultas
```

### PDFs
- ✅ **Nativos** (com texto pesquisável) - padrão
- ❌ **Escaneados** (apenas imagens) - anomalia
- ❌ **Muito grandes** (>50 MB) - anomalia

---

## ✅ Checklist de Validação

### Pré-requisitos
- [ ] Ambiente virtual ativado (`source .venv/bin/activate`)
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] `.env` configurado com `OPENAI_API_KEY`
- [ ] `.env` configurado com `OPENAI_MODEL=gpt-4o-mini`
- [ ] `.env` configurado com `BASE_DIR=./data/consultas`
- [ ] PDFs organizados em `data/consultas/{cpf}/{processo}.pdf`
- [ ] Código atualizado (modelo GPT-4o-mini)
- [ ] AGENTS.md atualizado

### Validação do Ambiente
- [ ] Executar `python --version` (deve ser 3.11+)
- [ ] Executar `which python` (deve apontar para .venv)
- [ ] Verificar `echo $OPENAI_API_KEY` (deve estar configurada)
- [ ] Listar PDFs: `find data/consultas -name "*.pdf" | head -5`

### Fase 1: Teste Unitário (3 PDFs)
- [ ] Executar `./validation_v1/scripts/validar_fase1.sh`
- [ ] Verificar JSONs em `_validation_v1/outputs/fase1_teste_unitario/jsons/`
- [ ] Verificar logs em `_validation_v1/outputs/fase1_teste_unitario/logs/`
- [ ] Analisar anomalias (se houver)
- [ ] Validar campos obrigatórios em cada JSON
- [ ] Validar presença de dados bancários (ANEXO II)
- [ ] Calcular taxa de sucesso
- [ ] Documentar resultados

### Aprovação para Fase 2
- [ ] Taxa de detecção ≥95%
- [ ] Taxa de extração ≥90%
- [ ] Taxa de validação 100%
- [ ] Taxa de ANEXO II 100%
- [ ] Anomalias documentadas
- [ ] Aprovação do responsável

---

## 📂 Estrutura de Outputs

```
_validation_v1/
├── PLANO_VALIDACAO.md
├── PREMISSAS.md
├── MUDANCAS_IMPLEMENTADAS.md
├── outputs/
│   ├── fase1_teste_unitario/
│   │   ├── jsons/
│   │   │   └── {cpf}/
│   │   │       └── {processo}.json
│   │   ├── logs/
│   │   │   └── exportacao_YYYYMMDD_HHMMSS.log
│   │   ├── anomalias/
│   │   │   ├── anomalias_sem_anexo_ii.json
│   │   │   ├── anomalias_oficio_nao_detectado.json
│   │   │   └── ...
│   │   └── relatorio_fase1.md
│   ├── fase2_amostra_10/
│   ├── fase3_lote_30/
│   └── fase4_massivo/
└── scripts/
    └── validar_fase1.sh
```

---

## 🔄 Próximos Passos

1. ✅ **Confirmar .env** está configurado corretamente
2. ✅ **Ativar ambiente virtual**
3. ✅ **Executar Fase 1** (3 PDFs)
4. ⏳ **Revisar resultados**
5. ⏳ **Ajustar se necessário**
6. ⏳ **Aprovar para Fase 2**

---

## 📞 Suporte

### Comandos Úteis

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Verificar configuração
cat .env | grep -E "OPENAI|BASE_DIR"

# Listar PDFs disponíveis
find data/consultas -name "*.pdf" | wc -l

# Executar Fase 1
./validation_v1/scripts/validar_fase1.sh

# Ver logs em tempo real
tail -f _validation_v1/outputs/fase1_teste_unitario/logs/*.log
```

### Troubleshooting

**Erro: OPENAI_API_KEY não configurada**
```bash
# Verificar .env
cat .env | grep OPENAI_API_KEY

# Configurar manualmente
export OPENAI_API_KEY=sk-proj-...
```

**Erro: PDFs não encontrados**
```bash
# Verificar estrutura
ls -R data/consultas/ | head -20

# Verificar BASE_DIR
echo $BASE_DIR
```

**Erro: Módulo não encontrado**
```bash
# Reinstalar dependências
pip install -r requirements.txt
```

---

**Status**: ✅ Mudanças implementadas e documentadas  
**Pronto para**: Fase 1 - Teste Unitário (3 PDFs)  
**Última atualização**: 13/10/2025
