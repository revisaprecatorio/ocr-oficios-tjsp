# 📋 Premissas do Projeto - Sistema OCR Ofícios Requisitórios TJSP

**Data**: 13 de outubro de 2025  
**Versão**: 1.0

---

## 🎯 Premissas Gerais

### Escopo do Projeto
- **Objetivo**: Extrair dados estruturados de Ofícios Requisitórios de Precatórios do TJSP
- **Fonte**: PDFs nativos (com texto pesquisável)
- **Destino**: JSONs estruturados → PostgreSQL (fase futura)
- **Tribunal**: Exclusivamente TJSP (Tribunal de Justiça de São Paulo)

---

## 📁 Estrutura de Dados

### Organização de Arquivos
```
data/consultas/
├── {cpf_11_digitos}/          # CPF sem formatação (apenas números)
│   ├── {processo_cnj}.pdf     # Número do processo CNJ
│   └── ...
└── ...
```

**Exemplos reais**:
- `data/consultas/02174781824/0158003-37.2025.8.26.0500.pdf`
- `data/consultas/03730461893/0037256-10.2015.8.26.0500.pdf`

### Nomenclatura
- **CPF**: 11 dígitos numéricos (sem pontos, traços ou espaços)
- **Processo**: Formato CNJ `0000000-00.0000.0.00.0000`

### Variável de Ambiente
```bash
BASE_DIR=./data/consultas
```

---

## 📄 Características dos PDFs

### PDFs Válidos (Padrão)
- ✅ **Formato**: PDF nativo com texto pesquisável
- ✅ **Origem**: TJSP (Tribunal de Justiça de São Paulo)
- ✅ **Tipo**: Ofício Requisitório de Precatórios
- ✅ **Conteúdo**: Ofício Requisitório + ANEXO II (dados bancários)
- ✅ **Tamanho típico**: 2-10 MB
- ✅ **Páginas típicas**: 5-20 páginas

### PDFs Anômalos (Exceções)
- ❌ **PDFs escaneados**: Sem texto pesquisável, apenas imagens
- ❌ **PDFs muito grandes**: >50 MB ou >100 páginas
- ❌ **PDFs corrompidos**: Não abrem ou têm erros
- ❌ **PDFs sem ofício**: Não contêm ofício requisitório
- ❌ **PDFs sem ANEXO II**: Não contêm dados bancários

**Tratamento**: Anomalias são registradas em logs separados e **não processadas** na v1.

---

## 📊 Dados Obrigatórios

### Campos Obrigatórios do Ofício
1. **processo_origem**: Número CNJ do processo
2. **requerente_caps**: Nome do requerente em MAIÚSCULAS

### Dados Bancários Obrigatórios (ANEXO II)
1. **banco**: Código do banco (ex: 001, 341)
2. **agencia**: Número da agência
3. **conta**: Número da conta com dígito
4. **conta_tipo**: Tipo de conta (corrente, poupança)

**Premissa crítica**: **TODOS os processos devem ter ANEXO II**. Se não houver, é considerado anomalia.

---

## 🔍 Detecção de Ofícios

### Critérios de Detecção (Mínimo 2/3)

#### Critério 1: Keywords Hierárquicas (Score ≥5/9)
- **Título do ofício** (peso 3): "OFÍCIO REQUISITÓRIO Nº"
- **Cabeçalho TJSP** (peso 3): "TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO"
- **Vara específica** (peso 2): "VARA DE FAZENDA PÚBLICA"
- **Contexto** (peso 1): "VALOR GLOBAL DA REQUISIÇÃO", "REQUERENTE:"

#### Critério 2: Padrão CNJ
- Regex: `\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}`
- Exemplo: `0158003-37.2025.8.26.0500`

#### Critério 3: Estrutura Formal
- "AO EXCELENTÍSSIMO SENHOR"
- "AO EXMO. SR."
- "À EXCELENTÍSSIMA SENHORA"
- "AO JUÍZO DA"

### Detecção de ANEXO II
- Marcador: "ANEXO II" presente no texto
- Campos esperados: Nome, CPF/CNPJ, Banco, Agência, Conta
- Estrutura tabular: "Credor nº: X"

---

## 🤖 Uso do LLM (OpenAI)

### Modelo Selecionado
**GPT-4o-mini**

**Justificativa**:
- ✅ Contexto: 128K tokens (suficiente para ofícios longos)
- ✅ Custo: $0.150/1M input, $0.600/1M output (~$0.0009/documento)
- ✅ Qualidade: Excelente em extração estruturada
- ✅ Velocidade: Rápido (importante para testes)

### Input do LLM
- **Tipo**: Texto extraído do PDF (PyMuPDF)
- **Conteúdo**: Ofício Requisitório + ANEXO II (se presente)
- **Tamanho médio**: 2.000-7.000 tokens (~8-28 KB)

### Output do LLM
- **Formato**: JSON estruturado
- **Campos**: 20+ campos (obrigatórios + opcionais)
- **Validação**: Pydantic v2

### Características Necessárias
- ❌ **NÃO precisa ser multimodal** (apenas texto)
- ✅ **Precisa compreender português jurídico**
- ✅ **Precisa seguir instruções estruturadas**
- ✅ **Precisa gerar JSON válido**

---

## 📊 Volume de Dados

### Ambiente de Desenvolvimento (Testes)
- **Volume**: Variável (subsets de 3, 10, 30, 100+ PDFs)
- **Objetivo**: Validar qualidade e identificar anomalias
- **Processamento**: Batch (sem preocupação com latência)

### Ambiente de Produção (Futuro)
- **Volume**: ~50 PDFs/dia
- **Custo estimado**: ~$1.35/mês (OpenAI)
- **Processamento**: Batch diário

---

## 🧪 Estratégia de Testes

### Fases de Validação
1. **Fase 1**: 3 PDFs (teste unitário)
2. **Fase 2**: 10 PDFs (amostra)
3. **Fase 3**: 30 PDFs (lote)
4. **Fase 4**: 100+ PDFs (massivo - após aprovação)

### Critérios de Aprovação
- **Taxa de detecção**: ≥95%
- **Taxa de extração**: ≥90%
- **Taxa de validação**: 100%
- **Taxa de ANEXO II**: 100%

### Incremento
- Testes em **subsets de 10 em 10**
- Análise de resultados entre cada subset
- Ajustes incrementais conforme necessário

---

## 🚨 Tratamento de Anomalias

### Tipos de Anomalias
1. **PDFs escaneados** (baixa qualidade)
2. **PDFs muito grandes** (>50 MB)
3. **Ofício não detectado**
4. **ANEXO II não encontrado** ⚠️ **CRÍTICO**
5. **Falha na extração LLM**
6. **Falha na validação Pydantic**

### Ação para Anomalias
- ❌ **Não processar** (exceto ofício sem ANEXO II, que processa mas registra)
- 📝 **Registrar em logs** específicos por tipo
- 🔄 **Tratar em fase futura** (OCR, processamento manual, etc.)

### Logs de Anomalias
```
_validation_v1/outputs/{fase}/anomalias/
├── anomalias_pdfs_escaneados.json
├── anomalias_pdfs_grandes.json
├── anomalias_oficio_nao_detectado.json
├── anomalias_sem_anexo_ii.json          # CRÍTICO
├── anomalias_falha_llm.json
└── anomalias_validacao_pydantic.json
```

---

## 🔧 Ambiente de Desenvolvimento

### Sistema Operacional
- **Dev**: macOS (local)
- **Produção futura**: Windows Server 2022 (já compatível)

### Dependências
- **Python**: 3.11+
- **PyMuPDF**: Extração de texto de PDFs nativos
- **OpenAI**: API para GPT-4o-mini
- **Pydantic**: Validação de dados v2
- **PostgreSQL**: Persistência (fase futura)

### Ambiente Virtual
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Configuração (.env)
```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
BASE_DIR=./data/consultas
```

---

## 📝 Validação de Dados

### Validação Pydantic

#### Campos Obrigatórios
- `processo_origem`: Formato CNJ válido
- `requerente_caps`: TODO EM MAIÚSCULAS

#### Validadores Customizados
- **CNJ**: Regex `^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$`
- **CPF/CNPJ**: 11 ou 14 dígitos
- **OAB**: Formato `OAB/UF 000.000`
- **Valores**: ≥0 (não negativos)
- **Datas**: ISO format `YYYY-MM-DD`

#### Normalização
- **Valores monetários**: Sem R$, sem pontos de milhar, ponto decimal
- **Datas**: Sempre ISO (YYYY-MM-DD)
- **Requerente**: Sempre MAIÚSCULAS

---

## 🎯 Foco da Validação v1

### O Que Está no Escopo
- ✅ **ETAPA 1**: PDFs → JSONs
- ✅ Detecção de ofícios
- ✅ Detecção de ANEXO II
- ✅ Extração com LLM
- ✅ Validação Pydantic
- ✅ Geração de JSONs
- ✅ Logs de anomalias
- ✅ Estatísticas de processamento

### O Que NÃO Está no Escopo (v1)
- ❌ **ETAPA 2**: JSONs → PostgreSQL (fase futura)
- ❌ OCR para PDFs escaneados
- ❌ Processamento de PDFs muito grandes
- ❌ Interface web
- ❌ Processamento paralelo
- ❌ Dashboard de monitoramento

---

## 📊 Métricas de Qualidade

### Métricas Primárias
- **Taxa de detecção de ofícios**: ≥95%
- **Taxa de extração completa**: ≥90%
- **Taxa de validação Pydantic**: 100%
- **Taxa de ANEXO II detectado**: 100%

### Métricas Secundárias
- **Tempo médio por PDF**: <60s (não crítico)
- **Custo médio por PDF**: <$0.001
- **Taxa de anomalias**: <5%

---

## ✅ Premissas Confirmadas - Checklist

- [x] Estrutura de pastas: `data/consultas/{cpf}/{processo}.pdf`
- [x] PDFs nativos (não escaneados) como padrão
- [x] Modelo LLM: GPT-4o-mini
- [x] ANEXO II obrigatório em todos os processos
- [x] Ambiente de dev: macOS
- [x] Processamento em batch (sem urgência de latência)
- [x] Foco em qualidade (não em velocidade)
- [x] Testes incrementais (subsets de 10 em 10)
- [x] Logs detalhados de anomalias
- [x] Validação rigorosa com Pydantic

---

**Status**: ✅ Premissas confirmadas e documentadas  
**Última atualização**: 13/10/2025
