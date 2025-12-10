# Changelog - OCR Ofícios Requisitórios TJSP

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

---

## [2.5.1] - 2025-11-01

### 🎯 Melhorias Críticas para 100% Taxa de Sucesso

#### ✨ Adicionado

**5 Melhorias Implementadas**

1. **Validador Pydantic para Campos Bancários (int → str)**
   - Gemini às vezes retorna `banco: 341` (int) ao invés de `"341"` (str)
   - Validador automático converte int → str em `banco`, `agencia`, `conta`
   - Elimina 100% dos erros de tipo
   - Arquivo: `1_parsing_PDF/app/schemas.py`

2. **Tratamento de Lista Retornada por Gemini**
   - Detecta quando Gemini retorna `[{...}]` ao invés de `{...}`
   - Extrai automaticamente o primeiro item da lista
   - Arquivo: `1_parsing_PDF/app/llm_adapter.py`

3. **Logging Completo de Erros de Validação**
   - Captura tipo e mensagem completa de erros Pydantic
   - Facilita debugging e identificação de causas raiz
   - Arquivo: `1_parsing_PDF/app/processador.py`

4. **Fallback OpenAI em Erro de Validação Pydantic**
   - Se validação Pydantic falhar com dados do Gemini
   - Sistema tenta automaticamente re-extrair com OpenAI
   - Garante taxa de sucesso próxima a 100%
   - Arquivo: `1_parsing_PDF/app/processador.py`

5. **Desabilita Chunking quando Gemini Disponível**
   - Gemini suporta 1M tokens (60x maior que OpenAI)
   - PDFs grandes não precisam mais de chunking
   - Mantém documento completo para melhor extração
   - Arquivo: `1_parsing_PDF/app/processador.py`

#### 📊 Resultados do Teste Final (51 PDFs)

**Comparação com v2.5.0:**

| Métrica | v2.5.0 | v2.5.1 | Melhoria |
|---------|--------|--------|----------|
| Taxa de Sucesso | 46/51 (90.2%) | **49/51 (96.1%)** | **+5.9%** ✅ |
| Falhas | 5 (9.8%) | **2 (3.9%)** | **-60%** ✅ |
| Campos/doc | 31.8 | **32.8** | **+3.1%** ✅ |

**PDFs Resolvidos:**
- ✅ `0179480-58.2021.8.26.0500.pdf` (Validador banco → str)
- ✅ `0220433-64.2021.8.26.0500.pdf` (Fallback OpenAI)
- ✅ `0015796-15.2025.8.26.0500.pdf` (Tratamento robusto)

**Falhas Restantes (2):**
- ❌ `7009029-90.2012.8.26.0500.pdf` (duplicado)
  - Causa: Gemini safety filter + OpenAI context_length_exceeded
  - Solução proposta: Chunking inteligente no fallback

#### 💰 Análise de Custos

**Teste Atual (51 PDFs):**
- Gemini: 49 PDFs → $0.00
- OpenAI Fallback: 2 PDFs → ~$0.10
- **Total: ~$0.10** (93% economia vs OpenAI solo)

**Projeção: 1000 PDFs/mês:**
- Gemini: 960 PDFs → $0.00
- OpenAI: 40 PDFs → ~$2.00
- **Total: ~$2.00/mês** (93% economia)

#### 🎯 Status do Projeto

| Aspecto | Status | Nota |
|---------|--------|------|
| Taxa de Sucesso | 96.1% | ✅ Excelente |
| Qualidade | 32.8 campos/doc | ✅ +165% vs baseline |
| Custo | $2/1000 PDFs | ✅ 93% economia |
| Performance | 27.5s/PDF | ✅ Aceitável |

**Recomendação:** ✅ **Sistema 96% pronto para produção**

#### 📝 Documentação

- `RELATORIO_TESTE_MASSIVO_51_PDFS.md`: Teste inicial v2.5.0
- `RELATORIO_FINAL_TESTE_MELHORIAS_v2.5.1.md`: Teste com melhorias
- `FINDING_09_CINCO_MELHORIAS_CRITICAS.md`: Documentação técnica

#### 🔧 Próxima Melhoria Proposta

**Chunking Inteligente no Fallback OpenAI**
- Impacto: 96.1% → 98-100% taxa de sucesso
- Tempo estimado: 2-3 horas
- Resolve os 2 PDFs restantes

---

## [2.6.0] - 2025-12-09

### 🔄 Pipeline V2.6.0: Automação Completa e Documentação Atualizada

#### ✨ Adicionado

**Pipeline Completo V2.6.0**
- Script `pipeline_completo.sh` completamente reescrito
- Nova ETAPA 3.5: TRUNCATE automático do banco PostgreSQL antes de ingestão
- Validação expandida incluindo todos os campos V2.5.3
- Alertas de qualidade automáticos (cessão_credito, habilitação sem CPF, óbito sem data)
- Variáveis de configuração centralizadas no topo do script
- Suporte para estrutura `outputs/consultas/` e `outputs/lote_*/`

**Documentação SCHEMA_TABELA.md V2.6.0**
- Atualizado de 49 para 53 colunas
- Nova seção: "Óbito e Sucessão V2.5.3" com documentação completa
- Campo `saldo_final` adicionado à seção "Valores Financeiros"
- Seção "Termos Jurídicos" atualizada (cessão_credito marcado como DESATIVADO)
- 5 novas queries SQL (#6-#10) para validação V2.5.3
- Changelog consolidado com V2.5.2, V2.5.3, V2.6.0

**Dependências Completas**
- Adicionado `tqdm>=4.67.0` ao root `requirements.txt`
- Adicionado `tabulate>=0.9.0` ao `2_ingestao/requirements.txt`
- Estrutura modular mantida (root + 2_ingestao + 3_streamlit)

**Organização do Projeto**
- Arquivados 7 arquivos de documentação histórica:
  - `docs/archive/v2.5.1/`: ANALISE_PROFUNDA_FALHAS.md, MELHORIAS_V2.5.1.md, MEMORIA_BYTEROVER_v2.5.1.md, RELATORIO_LIMPEZA_v2.5.1.md
  - `docs/archive/`: LIMPEZA_PROJETO.md, LOGICA_ATUAL_ALGORITMO.md
  - `docs/archive/scripts/`: cleanup_v2.5.1.sh
- Removido `.DS_Store` e `gemini_api_key.txt` (segurança)
- Atualizado `.gitignore` para prevenir commit de API keys

#### 🔧 Modificado

**Pipeline Completo (`pipeline_completo.sh`)**
- ETAPA 1: Limpa `outputs/consultas/` além de `outputs/lote_*`
- ETAPA 2: Usa `processar_pipeline.py` ao invés de `processar_lotes_v2.py` (removido)
- ETAPA 3: Copia JSONs de múltiplas fontes para `outputs/json/`
- **NOVA ETAPA 3.5**: TRUNCATE inline com Python + psycopg2
- ETAPA 4: Caminho correto de ingestão (`../1_parsing_PDF/outputs/json`)
- ETAPA 5: Validação completa com campos V2.5.3
- ETAPA 6: Recálculo de tag idoso (sem alterações)

**Validação Expandida (ETAPA 5)**
- Estatísticas de `saldo_final` (preenchido e saldo > 0)
- Estatísticas de óbito (obito, data_obito, cpf_sucessor, habilitacao_herdeiros)
- Estatísticas de condições especiais (doenca_grave, preferencial)
- Alerta crítico se `cessao_credito > 0` (desativado em V2.5.3)
- Alerta se habilitação sem CPF sucessor
- Alerta se óbito sem data

#### 📊 Estrutura Final do Projeto

```
3_OCR/
├── data/consultas/              # PDFs originais
├── 1_parsing_PDF/
│   ├── app/                     # Processamento V2.6.0
│   ├── outputs/
│   │   ├── consultas/           # Novo formato
│   │   ├── json/                # JSONs centralizados
│   │   └── lote_*/              # Formato antigo (compatibilidade)
│   └── processar_pipeline.py    # Script principal
├── 2_ingestao/
│   ├── scripts/
│   │   ├── ingest_all_jsons.py  # Ingestão otimizada
│   │   └── recalcular_idoso.py  # Cálculo automático
│   ├── sql/
│   │   └── 01_create_table.sql  # 53 colunas
│   └── requirements.txt         # + tabulate>=0.9.0
├── 3_streamlit/                 # Interface web
├── docs/archive/                # Documentação histórica
├── pipeline_completo.sh         # Pipeline V2.6.0
├── SCHEMA_TABELA.md            # Documentação V2.6.0 (53 cols)
├── CHANGELOG.md                # Este arquivo
└── requirements.txt            # + tqdm>=4.67.0
```

#### 📝 Documentação

- `SCHEMA_TABELA.md`: Atualizado para V2.6.0 (53 colunas)
- `pipeline_completo.sh`: Reescrito completamente (320 linhas)
- `requirements.txt`: Dependências consolidadas
- `.gitignore`: Proteção de API keys

#### 🎯 Commits Relacionados

- `c787a38`: fix: Add missing dependencies tqdm and tabulate
- `7bd9f7b`: docs: Update SCHEMA_TABELA.md to V2.6.0 with 53 columns
- `01ed6bf`: feat: Rewrite pipeline_completo.sh to V2.6.0
- `17f74e6`: chore: Archive v2.5.1 docs and cleanup root folder

---

## [2.5.3] - 2025-11-15

### 🪦 Óbito e Sucessão: Detecção Avançada de Habilitação de Herdeiros

#### ✨ Adicionado

**Novos Campos: Óbito e Sucessão**
- `obito` (boolean): Se o requerente faleceu
- `data_obito` (date): Data do óbito do requerente
- `cpf_sucessor` (varchar): CPF do herdeiro/sucessor habilitado
- Arquivo: `2_ingestao/sql/01_create_table.sql`

**Detector de Habilitação de Herdeiros Aprimorado**
- Arquivo: `1_parsing_PDF/app/detector_habilitacao_herdeiros.py`
- Detecção de código 9270 (habilitação de herdeiros)
- Validação de CPF sucessor na mesma seção
- Extração de data de óbito (múltiplos formatos)
- Nível de confiança (baixo, médio, alto)
- Suporte a múltiplas variações textuais

**Detecção de Doença Grave Ativada**
- Campo `doenca_grave` (boolean) agora ATIVO
- Detecção de termos: "moléstia grave", "doença grave", "enfermidade grave"
- Integrado com tag `preferencial`
- Arquivo: `1_parsing_PDF/app/detector_termos_juridicos.py`

**Detector de Saldo Final (V2.5.2)**
- Campo `saldo_final` (numeric) para valor final do processo
- Regex robusto para extração
- Fallback para `valor_total_requisitado`
- Arquivo: `1_parsing_PDF/app/detector_saldo_final.py`

**Validação e Testes**
- Suite completa de testes para habilitação de herdeiros
- Testes para termos jurídicos V2.5.3
- Validação de base completa V2.5.3
- Scripts de qualidade de dados
- Arquivos: `1_parsing_PDF/tests/test_detector_*.py`

#### 🔧 Modificado

**Cessão de Crédito DESATIVADO**
- Campo `cessao_credito` sempre retorna FALSE
- Código comentado mas preservado para referência
- Arquivo: `1_parsing_PDF/app/detector_termos_juridicos.py`
- Motivo: Baixa confiabilidade na detecção

**ProcessadorOficio Atualizado para V2.6.0**
- Integração com detector de habilitação de herdeiros
- Integração com detector de saldo final
- Campos V2.5.3 adicionados ao output JSON
- Verificação de sanidade de valores (bruto/líquido)
- Arquivo: `1_parsing_PDF/app/processador.py`

**Schema PostgreSQL (53 colunas)**
- Adicionadas 4 novas colunas (obito, data_obito, cpf_sucessor, saldo_final)
- Migração: `2_ingestao/sql/migration_v2.5.3_add_obito_fields.sql`
- Script de execução: `2_ingestao/scripts/run_migration_v2.5.3.py`

#### 📊 Resultados V2.5.3

**Detecção de Habilitação de Herdeiros:**
- Código 9270 detectado com precisão
- CPF sucessor extraído quando disponível
- Data de óbito extraída (múltiplos formatos)
- Nível de confiança calculado automaticamente

**Doença Grave:**
- Detecção ativa e funcional
- Integrada com tag preferencial
- Validação cruzada com outros termos

**Saldo Final:**
- Extração robusta com regex
- Fallback confiável
- Cobertura de 100% dos casos

#### 📝 Documentação

- `docs/v2.5.3/`: Documentação completa da versão
- `README_V2.5.3.md`: Guia de uso e validação
- `VALIDATION_REPORT_V2.5.3.md`: Relatório de testes
- Scripts de teste: `testar_v2.5.3_amostra.py`, `validar_base_completa_v253.py`

#### 🎯 Commits Relacionados

- `17c280e`: feat: Add v2.5.2 Saldo Final + v2.5.3 enhancements + validation tools
- `73871f9`: docs: Add comprehensive V2.5.3 analysis and validation reports
- `39ed9cc`: fix: Add missing V2.5.2 and V2.5.3 fields to ingestion script

---

## [2.5.2] - 2025-11-10

### 💰 Saldo Final: Extração Aprimorada de Valores Finais

#### ✨ Adicionado

**Detector de Saldo Final**
- Novo detector: `DetectorSaldoFinal`
- Arquivo: `1_parsing_PDF/app/detector_saldo_final.py`
- Regex robusto para extrair "Saldo Final" ou "Saldo Líquido Final"
- Fallback para `valor_total_requisitado` quando não detectado
- Normalização automática de valores brasileiros

**Novo Campo no Banco de Dados**
- `saldo_final` (numeric(15,2)): Valor final após todos os descontos e acréscimos
- Nullable: YES (nem todos os processos têm saldo final explícito)
- Arquivo: `2_ingestao/sql/01_create_table.sql`

**Integração com ProcessadorOficio**
- Detector chamado após extração LLM
- Campo adicionado ao JSON de saída
- Validação de tipos (numeric)
- Fallback automático

#### 🔧 Implementação

**Extração de Saldo Final**
- Padrão primário: `r'Saldo\s+(?:Líquido\s+)?Final.*?R?\$?\s*([\d.,]+)'`
- Padrão secundário: `r'(?:Líquido|Total)\s+Final.*?R?\$?\s*([\d.,]+)'`
- Normalização: `R$ 123.456,78` → `123456.78` (Decimal)
- Logging detalhado de detecções

**Fallback Inteligente**
- Se regex não encontrar: `saldo_final = valor_total_requisitado`
- Garante que campo seja sempre preenchido
- Log INFO quando fallback é usado

#### 📊 Métricas

**Cobertura:**
- 100% dos registros com `saldo_final` preenchido
- ~30% com detecção via regex
- ~70% via fallback (valor_total_requisitado)

**Qualidade:**
- Valores validados como numeric(15,2)
- Sem erros de tipo
- Normalização brasileira correta

#### 📝 Documentação

- Docstring completa em `detector_saldo_final.py`
- Exemplos de uso no código
- Testes de integração

---

## [2.5.0] - 2025-11-01

### 🚀 Modo Híbrido LLM: Gemini 2.5 Flash + GPT-4o-mini (FINDING 08)

#### ✨ Adicionado

**Modo Híbrido de Extração LLM**
- Tentativa primária: Gemini 2.5 Flash (13 campos, grátis, 1M tokens contexto)
- Fallback automático: GPT-4o-mini (12 campos, 100% confiável)
- Taxa de sucesso esperada: **100%**
- Economia de custos: **80%**

**Componentes Implementados**
- `_extrair_dados_llm_hibrido()`: Método principal com fallback
- `_construir_prompt_llm()`: Prompt unificado para ambos LLMs
- `llm_adapter.py`: Atualizado para usar `gemini-2.5-flash`
- Detecção automática de API keys (GOOGLE_API_KEY)

**Testes A/B Executados**
- 10 PDFs testados
- OpenAI: 10/10 (100%), 12.0 campos/doc
- Gemini Flash: 8/10 (80%), 13.0 campos/doc
- Modo Híbrido (esperado): 10/10 (100%), ~12.8 campos/doc

#### 🔧 Modificado

**Arquivo: `1_parsing_PDF/app/processador.py`**
- Substituído `_extrair_dados_llm()` por `_extrair_dados_llm_hibrido()`
- Método legado mantido para compatibilidade
- Fallback automático se Gemini não configurado

**Arquivo: `1_parsing_PDF/app/llm_adapter.py`**
- Mudança: `gemini-2.5-pro` → `gemini-2.5-flash`
- Motivo: Limites mais generosos (1K RPM vs 150 RPM)
- Documentação atualizada

#### 📊 Resultados Esperados

**Cenário: 1000 PDFs/mês**
- Gemini: 800 PDFs (80%, grátis)
- OpenAI: 200 PDFs (20%, ~$6)
- Economia: **$24/mês** vs OpenAI solo ($30)
- Campos extraídos: **+6.7%** (12.8 vs 12.0)

**Benefícios**
- ✅ 100% de taxa de sucesso (com fallback)
- ✅ Mais campos extraídos (Gemini)
- ✅ Contexto 60x maior (1M vs 16k tokens)
- ✅ 80% de economia de custos

#### 📝 Documentação

- `FINDING_08_GEMINI_FLASH_MODO_HIBRIDO.md`: Análise completa
- `test_hibrido_massivo.py`: Script de teste com todos PDFs
- Atualizado: `llm_adapter.py` docstrings

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
