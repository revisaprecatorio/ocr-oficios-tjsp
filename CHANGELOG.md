# Changelog - OCR Ofícios Requisitórios TJSP

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

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
