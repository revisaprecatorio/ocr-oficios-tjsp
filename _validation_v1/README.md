# 🧪 Validação v1 - Sistema OCR Ofícios Requisitórios TJSP

**Objetivo**: Validar extração de dados de PDFs de Ofícios Requisitórios para JSON estruturado  
**Escopo**: ETAPA 1 (PDFs → JSONs)  
**Data**: 13 de outubro de 2025

---

## 📚 Documentação

### Documentos Principais

1. **[PLANO_VALIDACAO.md](PLANO_VALIDACAO.md)** 📋
   - Plano completo de validação em 4 fases
   - Análise detalhada do uso do LLM
   - Seleção do modelo GPT-4o-mini
   - Estratégia de testes e métricas

2. **[PREMISSAS.md](PREMISSAS.md)** 📝
   - Todas as premissas confirmadas
   - Estrutura de dados
   - Características dos PDFs
   - Dados obrigatórios

3. **[MUDANCAS_IMPLEMENTADAS.md](MUDANCAS_IMPLEMENTADAS.md)** 🔄
   - Resumo de mudanças no código
   - Atualização do AGENTS.md
   - Checklist de validação

---

## 🚀 Quick Start

### 1. Preparar Ambiente

```bash
# Ativar ambiente virtual
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR
source .venv/bin/activate

# Verificar dependências
pip list | grep -E "pymupdf|openai|pydantic"

# Verificar .env
cat .env | grep -E "OPENAI_API_KEY|BASE_DIR|OPENAI_MODEL"
```

### 2. Executar Fase 1 (3 PDFs)

```bash
# Executar script de validação
./_validation_v1/scripts/validar_fase1.sh
```

### 3. Analisar Resultados

```bash
# Ver JSONs gerados
ls -lh _validation_v1/outputs/fase1_teste_unitario/jsons/*/*.json

# Ver logs
tail -50 _validation_v1/outputs/fase1_teste_unitario/logs/*.log

# Ver anomalias (se houver)
ls _validation_v1/outputs/fase1_teste_unitario/anomalias/
```

---

## 📊 Fases de Validação

### Fase 1: Teste Unitário ✅ (Pronto para executar)
- **PDFs**: 3
- **Objetivo**: Validar pipeline básico
- **Script**: `scripts/validar_fase1.sh`
- **Output**: `outputs/fase1_teste_unitario/`

### Fase 2: Amostra ⏳ (Aguardando aprovação Fase 1)
- **PDFs**: 10
- **Objetivo**: Validar robustez
- **Output**: `outputs/fase2_amostra_10/`

### Fase 3: Lote ⏳ (Aguardando aprovação Fase 2)
- **PDFs**: 30
- **Objetivo**: Validar em escala
- **Output**: `outputs/fase3_lote_30/`

### Fase 4: Massivo ⏳ (Aguardando aprovação Fase 3)
- **PDFs**: 100+
- **Objetivo**: Validação final
- **Output**: `outputs/fase4_massivo/`

---

## ✅ Checklist Pré-Execução

### Ambiente
- [ ] Ambiente virtual ativado
- [ ] Python 3.11+ instalado
- [ ] Dependências instaladas

### Configuração
- [ ] `.env` existe e está configurado
- [ ] `OPENAI_API_KEY` configurada
- [ ] `OPENAI_MODEL=gpt-4o-mini`
- [ ] `BASE_DIR=./data/consultas`

### Dados
- [ ] PDFs organizados em `data/consultas/{cpf}/{processo}.pdf`
- [ ] Pelo menos 3 PDFs disponíveis
- [ ] PDFs são nativos (não escaneados)

### Código
- [ ] Modelo atualizado para `gpt-4o-mini` em `app/processador.py`
- [ ] AGENTS.md atualizado com estrutura correta

---

## 📂 Estrutura de Outputs

```
_validation_v1/
├── README.md                       # Este arquivo
├── PLANO_VALIDACAO.md              # Plano completo
├── PREMISSAS.md                    # Premissas confirmadas
├── MUDANCAS_IMPLEMENTADAS.md       # Mudanças no código
│
├── scripts/
│   └── validar_fase1.sh            # Script Fase 1
│
└── outputs/
    └── fase1_teste_unitario/
        ├── jsons/                  # JSONs gerados
        │   └── {cpf}/
        │       └── {processo}.json
        ├── logs/                   # Logs de processamento
        │   └── exportacao_*.log
        └── anomalias/              # Logs de anomalias
            ├── anomalias_sem_anexo_ii.json
            ├── anomalias_oficio_nao_detectado.json
            └── ...
```

---

## 🎯 Critérios de Sucesso

### Métricas Primárias
| Métrica | Meta | Status |
|---------|------|--------|
| Taxa de detecção de ofícios | ≥95% | ⏳ |
| Taxa de extração completa | ≥90% | ⏳ |
| Taxa de validação Pydantic | 100% | ⏳ |
| Taxa de ANEXO II detectado | 100% | ⏳ |

### Aprovação para Próxima Fase
- ✅ Todas as métricas primárias atingidas
- ✅ Anomalias documentadas e compreendidas
- ✅ Qualidade dos dados validada manualmente
- ✅ Aprovação do responsável

---

## 🚨 Tratamento de Anomalias

### Tipos de Anomalias

1. **PDFs Escaneados** → Não processar, registrar em log
2. **PDFs Muito Grandes** (>50 MB) → Não processar, registrar em log
3. **Ofício Não Detectado** → Não processar, analisar manualmente
4. **ANEXO II Não Encontrado** → ⚠️ **CRÍTICO** - Registrar e investigar
5. **Falha na Extração LLM** → Retry 3x, depois registrar
6. **Falha na Validação Pydantic** → Registrar com dados brutos

### Logs de Anomalias

Cada tipo de anomalia gera um arquivo JSON:
```
outputs/{fase}/anomalias/
├── anomalias_pdfs_escaneados.json
├── anomalias_pdfs_grandes.json
├── anomalias_oficio_nao_detectado.json
├── anomalias_sem_anexo_ii.json          # CRÍTICO
├── anomalias_falha_llm.json
└── anomalias_validacao_pydantic.json
```

---

## 🤖 Modelo LLM: GPT-4o-mini

### Por Que GPT-4o-mini?

✅ **Contexto**: 128K tokens (suficiente para ofícios longos)  
✅ **Custo**: $0.0009/documento (~$1.35/mês para 50 docs/dia)  
✅ **Qualidade**: Excelente em extração estruturada  
✅ **Velocidade**: Rápido (importante para testes)  
❌ **Multimodal**: Não necessário (apenas texto)

### Uso no Sistema

**Input**: Texto extraído do PDF (2.000-7.000 tokens)  
**Task**: Extração estruturada de informações  
**Output**: JSON com 20+ campos validados

---

## 📊 Análise de Resultados

### Após Executar Fase 1

1. **Verificar JSONs gerados**
   ```bash
   cat _validation_v1/outputs/fase1_teste_unitario/jsons/*/0*.json | jq .
   ```

2. **Verificar campos obrigatórios**
   ```bash
   cat output.json | jq '{processo: .oficio.processo_origem, requerente: .oficio.requerente_caps}'
   ```

3. **Verificar dados bancários**
   ```bash
   cat output.json | jq '{banco: .oficio.banco, agencia: .oficio.agencia, conta: .oficio.conta}'
   ```

4. **Calcular estatísticas**
   - Total de PDFs processados
   - Total de JSONs gerados
   - Taxa de sucesso
   - Anomalias encontradas

---

## 🔄 Próximos Passos

### Após Fase 1

1. ✅ Revisar JSONs gerados
2. ✅ Validar qualidade dos dados
3. ✅ Analisar anomalias
4. ✅ Documentar resultados em `relatorio_fase1.md`
5. ✅ Decidir se prosseguir para Fase 2

### Após Fase 2

1. Calcular taxa de sucesso
2. Identificar padrões de erro
3. Refinar detecção se necessário
4. Documentar em `relatorio_fase2.md`
5. Decidir se prosseguir para Fase 3

### Após Fase 3

1. Validar taxa de sucesso ≥95%
2. Consolidar logs de anomalias
3. Gerar estatísticas finais
4. Documentar em `relatorio_fase3.md`
5. Aprovar para Fase 4 (massivo)

---

## 📞 Comandos Úteis

### Verificação de Ambiente

```bash
# Verificar Python
python --version

# Verificar ambiente virtual
which python

# Verificar dependências
pip list | grep -E "pymupdf|openai|pydantic"

# Verificar .env
cat .env | grep -v "^#" | grep -v "^$"
```

### Análise de PDFs

```bash
# Contar PDFs disponíveis
find data/consultas -name "*.pdf" | wc -l

# Listar PDFs por tamanho
find data/consultas -name "*.pdf" -exec du -h {} \; | sort -h

# Ver estrutura de pastas
tree data/consultas -L 2
```

### Análise de Resultados

```bash
# Contar JSONs gerados
find _validation_v1/outputs -name "*.json" | wc -l

# Ver último log
tail -50 _validation_v1/outputs/fase1_teste_unitario/logs/*.log

# Verificar anomalias
ls -lh _validation_v1/outputs/fase1_teste_unitario/anomalias/
```

---

## ⚠️ Troubleshooting

### Erro: OPENAI_API_KEY não configurada

```bash
# Verificar .env
cat .env | grep OPENAI_API_KEY

# Configurar manualmente
export OPENAI_API_KEY=sk-proj-...
```

### Erro: PDFs não encontrados

```bash
# Verificar estrutura
ls -R data/consultas/ | head -20

# Verificar BASE_DIR
echo $BASE_DIR
```

### Erro: Módulo não encontrado

```bash
# Reinstalar dependências
pip install -r requirements.txt

# Verificar instalação
pip show pymupdf openai pydantic
```

---

## 📈 Progresso

- [x] Documentação criada
- [x] Premissas confirmadas
- [x] Código atualizado (GPT-4o-mini)
- [x] AGENTS.md atualizado
- [x] Script Fase 1 criado
- [ ] Fase 1 executada
- [ ] Resultados analisados
- [ ] Fase 2 aprovada
- [ ] Fase 3 aprovada
- [ ] Fase 4 aprovada

---

**Status**: 🟢 Pronto para executar Fase 1  
**Responsável**: Validação v1  
**Última atualização**: 13/10/2025
