# Changelog - OCR Ofícios Requisitórios TJSP

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

---

## [2.4.0] - 2025-11-01

### 🎯 Detector Robusto de ANEXO II (FINDING 05 & 06)

#### ✨ Adicionado

**Detector Robusto de ANEXO II Bancário**
- Detecção baseada em dados bancários REAIS (CPF + Credor + Valor)
- Eliminação de falsos positivos (páginas de DECISÃO e ÍNDICES)
- Logging detalhado de detecções e rejeições
- Impacto: **90% de redução** em falsos positivos

**Validações Implementadas**
- ✅ CPF formatado (XXX.XXX.XXX-XX)
- ✅ Estrutura de credor (Credor nº + Nome)
- ✅ Valores monetários (R$ + Valor Total/Requisitado)
- ✅ Exclusão de páginas de DECISÃO judicial
- ✅ Exclusão de ÍNDICES de documentos
- ✅ Exclusão de menções à Portaria sem dados

**Testes Unitários Completos**
- 15 testes implementados (100% de sucesso)
- 4 casos positivos (ANEXO II reais)
- 6 casos negativos (falsos positivos)
- 5 casos limite e edge cases

#### 🔧 Modificado

**Arquivo: `1_parsing_PDF/app/detector_anexo.py`**
- Método `_eh_pagina_anexo_ii()` completamente refatorado
- Lógica robusta com múltiplas verificações
- Logging INFO para confirmações
- Logging DEBUG para rejeições

#### 📊 Resultados

**Validação com PDFs Reais:**
- 20 PDFs analisados
- 18 PDFs com ANEXO II válido (90%)
- 21 páginas ANEXO II detectadas
- **0 falsos positivos** identificados

**Impacto Esperado:**
- Redução de tokens desperdiçados: -90%
- Economia de custo por documento: -90%
- Melhoria na precisão de extração: +7pp
- Custo desperdiçado (100 docs): $0.015 → $0.0015

#### 📚 Documentação

- `FINDING_05_ANALISE_ANEXO_II_PLANILHAS.md`: Análise do problema
- `FINDING_06_IMPLEMENTACAO_DETECTOR_ROBUSTO.md`: Documentação completa
- `test_detector_anexo_robusto.py`: Suite de testes completa

---

## [2.3.0] - 2025-10-16

### 🎂 Cálculo Automático da Tag IDOSO

#### ✨ Adicionado

**Recálculo Automático de Idoso**
- Script `recalcular_idoso.py` para atualizar registros existentes
- Cálculo automático no processamento de PDFs
- Lógica: `idade = data_atual - data_nascimento >= 60 anos`
- Integração com pipeline completo

**Funcionalidades**
- Recálculo em lote de todos os registros com `data_nascimento`
- Validação automática de inconsistências
- Relatório detalhado com estatísticas
- Ajuste correto para aniversários não completados

**Documentação**
- `README_RECALCULO_IDOSO.md` com guia completo
- Exemplos de uso e queries SQL
- Troubleshooting e casos especiais

#### 🔧 Implementação

**Processamento Automático**
- Arquivo: `1_parsing_PDF/app/processador.py`
- Cálculo após validação Pydantic
- Log de idade calculada para cada registro

**Script de Recálculo**
- Arquivo: `2_ingestao/scripts/recalcular_idoso.py`
- Atualiza registros existentes no PostgreSQL
- Validação final de consistência

**Pipeline Completo**
- Etapa 5 adicionada: Recálculo de tag idoso
- Execução automática após ingestão

#### 📊 Métricas

**Última Execução (16/10/2025):**
- Total processado: 44 registros
- Idosos (≥60 anos): 27 (61.4%)
- Não idosos (<60 anos): 17 (38.6%)
- Registros atualizados: 12
- Registros já corretos: 32
- Taxa de sucesso: 100%

---

## [2.2.0] - 2025-10-16

### 🎉 Pipeline Completo 100% Funcional

#### ✨ Adicionado

**Pipeline Automatizado End-to-End**
- Script `pipeline_completo.sh` para execução completa do pipeline
- Limpeza automática de JSONs antigos antes do processamento
- Organização automática de JSONs em pasta centralizada
- Importação automática para PostgreSQL (VPS)
- Validação automática de resultados com estatísticas

**Correção de Falsos Rejeitados**
- Lógica de priorização de aceitação implementada
- Verificação de "PROCESSAMENTO COM INFORMAÇÃO" antes de rejeição
- Verificação de `numero_ordem` antes de rejeição
- 100% de precisão: 0 falsos rejeitados em 26 ofícios com número de ordem

**Colunas Completas no Streamlit**
- Adicionadas 11 colunas faltantes na query do Streamlit:
  - `data_nascimento` (data de nascimento do credor)
  - `tipo_levantamento`
  - `dados_bancarios_advogado`
  - `cpf_titular_conta`
  - `valor_compensado`
  - `contribuicao_social`
  - `salario_pericial`
  - `assist_tecnico`
  - `custas`
  - `despesas`
  - `multas`
- Total: 49 colunas agora disponíveis na interface

**Documentação**
- Arquivo `ANOMALIA-A-REVER.md` documentando caso anômalo
- README atualizado com seção "Pipeline Completo de Ponta a Ponta"
- Roadmap atualizado com tarefas concluídas

#### 🔧 Corrigido

**Lógica de Detecção de Rejeição**
- Problema: 13 ofícios com `numero_ordem` marcados incorretamente como rejeitados
- Solução: Priorizar verificação de aceitação antes de rejeição
- Arquivo: `1_parsing_PDF/app/processador.py`
- Resultado: 0 falsos rejeitados (100% de precisão)

**Streamlit - Colunas Faltantes**
- Problema: 11 colunas da tabela PostgreSQL não eram carregadas
- Solução: Atualizar query SQL para incluir todas as colunas
- Arquivo: `3_streamlit/app/streamlit_app.py`
- Resultado: 49/49 colunas agora disponíveis

#### 📊 Métricas

**Última Execução do Pipeline (16/10/2025):**
- Total processado: 51 PDFs
- Sucesso: 50 (98%)
- Tempo total: 598.9s (~10 minutos)
- Tempo médio: 11.7s/PDF
- Falsos rejeitados: 0 (100% de precisão)
- Taxa de correção: 100%

**Validação PostgreSQL:**
- 44/50 registros (88%) com `data_nascimento`
- 27/50 registros (54%) com `tipo_levantamento`
- 33/50 registros (66%) com `valor_compensado`

#### 🚀 Deploy

**Redeploy Streamlit VPS (16/10/2025):**
- ✅ Script de ingestão corrigido
- ✅ Tabela PostgreSQL limpa e reingerida
- ✅ Streamlit atualizado com 49 colunas
- ✅ Todas as colunas visíveis na interface
- ✅ Deploy validado em produção

---

## [2.1.0] - 2025-10-14

### 🎨 Interface Streamlit Otimizada

#### ✨ Adicionado

**Visualização de PDF Simplificada**
- Download destacado como solução principal
- Botão primary azul com tamanho do arquivo
- Mensagens informativas sobre disponibilidade
- Remoção de visualização inline (não funciona com PDFs grandes)

**Tabela Completa**
- Exibição de todas as 37+ colunas do banco de dados
- Formatação de múltiplos campos monetários
- Scroll horizontal para navegação
- Dados completos acessíveis

#### 🎨 Melhorado

**UX do Download de PDF**
- Botão centralizado e destacado (tipo primary)
- Informação de tamanho do arquivo no label
- Mensagens claras orientando uso
- Fallback confiável para qualquer tamanho de PDF

**Visualização de Dados**
- Todas as colunas visíveis na aba Dados
- Formatação de valor_principal_liquido
- Formatação de valor_principal_bruto
- Formatação de valor_total_requisitado

#### 🗑️ Removido

**Visualização Inline de PDF**
- Iframe base64 (não funciona com PDFs >3 MB)
- Expanders de visualização inline
- Tentativas de renderização que falhavam
- Código complexo e desnecessário

#### 🔧 Corrigido

**Erros de Renderização**
- TypeError com valores NA no campo rejeitado
- StreamlitDuplicateElementId (keys únicas adicionadas)
- Deprecation warning (use_container_width → width)
- PDFs grandes não renderizando

#### 📊 Estrutura Final

```
3_streamlit/                    # Módulo isolado
├── app/streamlit_app.py        # Interface otimizada
├── .env.example                # Config documentada
├── README.md                   # Docs completa
├── requirements.txt            # Deps específicas
└── run.sh                      # Execução facilitada
```

---

## [2.0.0] - 2025-10-14

### 🎉 Reorganização Completa do Projeto

#### ✨ Adicionado

**Novo Módulo Streamlit Isolado (3_streamlit/)**
- Interface web agora em módulo independente e reutilizável
- Estrutura completa com documentação, scripts e configuração
- `README.md` detalhado com instruções de uso
- `requirements.txt` específico para dependências
- `run.sh` para execução facilitada
- `.env.example` para documentação de configuração
- `.gitignore` específico para o módulo

**Documentação Arquivada**
- Criado `docs/archive/` para documentação histórica
- Movidos 15+ arquivos de documentação antiga
- Mantida documentação ativa e relevante

**Scripts de Ingestão Otimizados**
- `ingest_all_jsons.py` - Ingestão otimizada de todos os JSONs
- `check_missing.py` - Verificação de registros faltantes
- `validate_data.py` - Validação e estatísticas completas

#### 🎨 Melhorado

**Interface Streamlit**
- Substituição de checkboxes por selectbox (dropdown) nas preferências
- Economia de 66% de espaço vertical na sidebar
- Renderização instantânea sem latência
- Layout compacto e profissional
- Título visível sem cortes no topo
- CSS otimizado para melhor UX

**Performance**
- Cache em memória para dados do PostgreSQL
- Filtros processados em memória (instantâneos)
- Carregamento inicial otimizado

#### 🗑️ Removido

**Duplicatas e Arquivos Obsoletos (~24 MB)**
- `Processos/` (16 MB) - Duplicata de `data/consultas/`
- `app/` (136 KB) - Duplicata de `1_parsing_PDF/app/`
- `output_teste/` (540 KB) - Testes antigos
- `various/` (7 MB) - PDF exemplo
- `lote_001/` a `lote_011/` - Lotes antigos (mantido apenas `json/`)
- Scripts obsoletos: `api.py`, `run_sistema.py`, `processar_lotes.py`, etc.
- Deploy scripts não utilizados: Docker, VPS, etc.
- Documentação duplicada: 15+ arquivos `.md`

#### 🔧 Corrigido

**Interface Streamlit**
- Título cortado no topo da página
- Espaçamento vertical inadequado
- Latência na renderização de filtros
- Configuração do banco de dados (`.env`)

#### 📊 Estrutura Final

```
3_OCR/
├── data/consultas/         # 51 PDFs originais (1.4 GB)
├── 1_parsing_PDF/          # Extração de dados
│   ├── app/                # Código de parsing
│   ├── outputs/json/       # 50 JSONs processados
│   └── tests/              # Testes
├── 2_ingestao/             # Importação para PostgreSQL
│   ├── scripts/            # Scripts de ingestão
│   ├── sql/                # Schemas SQL
│   └── logs/               # Logs
├── 3_streamlit/            # Interface web (NOVO!)
│   ├── app/                # Streamlit app
│   ├── .env.example        # Config exemplo
│   ├── README.md           # Documentação
│   ├── requirements.txt    # Dependências
│   └── run.sh              # Script de execução
├── tests/                  # Testes gerais
├── docs/archive/           # Documentação histórica
├── .venv/                  # Virtual environment
├── AGENTS.md               # Instruções IA
├── README.md               # Documentação principal
└── CHANGELOG.md            # Este arquivo
```

#### 🎯 Benefícios

**Modularidade**
- Cada módulo é independente e pode ser deployado separadamente
- Facilita manutenção e escalabilidade
- Separação clara de responsabilidades

**Documentação**
- README específico para cada módulo
- Instruções claras de uso
- Exemplos de configuração

**Performance**
- Interface otimizada e responsiva
- Cache eficiente
- Renderização instantânea

#### 📈 Estatísticas

- ✅ **51 processos** no PostgreSQL
- ✅ **50 JSONs** processados e organizados
- ✅ **100% taxa de sucesso** na ingestão
- ✅ **Interface Streamlit** 100% funcional
- ✅ **~24 MB** de arquivos desnecessários removidos
- ✅ **7 commits** consolidados

#### 🚀 Status

**Pronto para produção!**

---

## [1.0.0] - 2025-10-13

### Versão Inicial

- ✅ Pipeline de parsing de PDFs
- ✅ Extração de dados com GPT-4o-mini
- ✅ Ingestão no PostgreSQL
- ✅ Interface Streamlit básica
- ✅ 51 processos processados

---

**Formato baseado em [Keep a Changelog](https://keepachangelog.com/)**
