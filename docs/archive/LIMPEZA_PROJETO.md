# 🧹 Análise de Limpeza do Projeto

**Data:** 14/10/2025  
**Objetivo:** Remover duplicatas e arquivos desnecessários

---

## 📊 Análise de Espaço

| Diretório | Tamanho | Status | Ação |
|-----------|---------|--------|------|
| `data/` | 1.4 GB | ✅ Necessário | Manter (PDFs originais) |
| `Processos/` | 16 MB | ❌ Duplicata | **REMOVER** (duplicata de data/) |
| `_definition-e-specs/` | 7.6 MB | ⚠️ Documentação antiga | **MOVER** para `docs/archive/` |
| `various/` | 7 MB | ⚠️ Arquivos de teste | **REMOVER** (PDF exemplo) |
| `1_parsing_PDF/` | 1.5 MB | ✅ Necessário | **LIMPAR** lotes (manter só json/) |
| `_validation_v1/` | 700 KB | ⚠️ Testes antigos | **MOVER** para `docs/archive/` |
| `output_teste/` | 540 KB | ❌ Teste | **REMOVER** |
| `2_ingestao/` | 144 KB | ✅ Necessário | Manter |
| `tests/` | 144 KB | ✅ Necessário | Manter |
| `app/` | 136 KB | ❌ Duplicata | **REMOVER** (duplicata de 1_parsing_PDF/app/) |
| `deploy/` | 28 KB | ⚠️ Deploy antigo | **MOVER** para `docs/archive/` |

---

## 🗑️ Arquivos para Remover (Raiz)

### **Scripts Duplicados/Obsoletos:**
- ❌ `api.py` - API antiga, não usada
- ❌ `run_sistema.py` - Script antigo de execução
- ❌ `processar_lotes.py` - Substituído por 1_parsing_PDF/
- ❌ `exportar_json.py` - Funcionalidade já em 2_ingestao/
- ❌ `importar_postgres.py` - Substituído por 2_ingestao/scripts/
- ❌ `schema.sql` - Duplicata de 2_ingestao/sql/
- ❌ `teste_windows_compat.py` - Teste antigo
- ❌ `teste_pipeline_completo.sh` - Teste antigo
- ❌ `teste_pipeline_completo.bat` - Teste antigo

### **Deploy Scripts (Obsoletos):**
- ❌ `deploy_vps.sh`
- ❌ `deploy_vps_otimizado.sh`
- ❌ `monitor_vps.sh`
- ❌ `monitor_vps_avancado.sh`
- ❌ `vps_commands.md`
- ❌ `docker-compose.yml` - Não usado
- ❌ `Dockerfile` - Não usado

### **Documentação Duplicada/Antiga:**
- ⚠️ `DOCUMENTACAO_PROJETO.md` → Consolidar em README.md
- ⚠️ `RESUMO_EXECUTIVO.md` → Mover para docs/archive/
- ⚠️ `RESUMO_EXECUTIVO_FINAL.md` → Mover para docs/archive/
- ⚠️ `RESUMO_IMPLEMENTACAO.md` → Mover para docs/archive/
- ⚠️ `RELATORIO_TESTES.md` → Mover para docs/archive/
- ⚠️ `RELATORIO_FINAL_REFINAMENTO.md` → Mover para docs/archive/
- ⚠️ `HISTORICO_DEPLOY.md` → Mover para docs/archive/
- ⚠️ `DEPLOY_WINDOWS_SERVER.md` → Mover para docs/archive/
- ⚠️ `REFLEXAO_E_MELHORIAS.md` → Mover para docs/archive/
- ⚠️ `ANALISE_OFICIO_EXEMPLO.md` → Mover para docs/archive/
- ⚠️ `3.1.2 Parsing revisado.md` → Mover para docs/archive/
- ✅ `AGENTS.md` - Manter (documentação ativa)
- ✅ `README.md` - Manter (documentação principal)
- ✅ `CLAUDE.md` - Manter (instruções para IA)

---

## 📁 Estrutura Proposta (Limpa)

```
3_OCR/
├── .venv/                          ✅ Virtual environment
├── data/
│   └── consultas/                  ✅ PDFs originais (1.4GB)
├── 1_parsing_PDF/
│   ├── app/                        ✅ Código de parsing
│   ├── outputs/
│   │   └── json/                   ✅ JSONs processados (50 arquivos)
│   ├── tests/                      ✅ Testes
│   └── docs/                       ✅ Documentação específica
├── 2_ingestao/
│   ├── app/                        ✅ Streamlit
│   ├── scripts/                    ✅ Scripts de ingestão
│   ├── sql/                        ✅ Schemas SQL
│   └── logs/                       ✅ Logs de ingestão
├── tests/                          ✅ Testes gerais
├── docs/
│   ├── archive/                    📦 Documentação antiga
│   └── README.md                   📖 Índice de docs
├── .env                            ✅ Configuração
├── .gitignore                      ✅ Git
├── requirements.txt                ✅ Dependências
├── AGENTS.md                       ✅ Instruções IA
├── README.md                       ✅ Documentação principal
└── CLAUDE.md                       ✅ Instruções Claude
```

---

## 🎯 Ações Recomendadas

### **1. Remover Duplicatas (Economia: ~23 MB)**
```bash
rm -rf Processos/              # 16 MB - Duplicata de data/
rm -rf app/                    # 136 KB - Duplicata de 1_parsing_PDF/app/
rm -rf output_teste/           # 540 KB - Testes antigos
rm -rf various/                # 7 MB - PDF exemplo
```

### **2. Limpar Lotes Antigos (Economia: ~1 MB)**
```bash
# Manter apenas json/, remover lote_001 a lote_011
cd 1_parsing_PDF/outputs/
rm -rf lote_*
rm -f *.csv
rm -f estatisticas_globais.json
```

### **3. Arquivar Documentação Antiga**
```bash
mkdir -p docs/archive
mv _definition-e-specs/ docs/archive/
mv _validation_v1/ docs/archive/
mv deploy/ docs/archive/
mv RESUMO_*.md docs/archive/
mv RELATORIO_*.md docs/archive/
mv HISTORICO_*.md docs/archive/
mv DEPLOY_*.md docs/archive/
mv REFLEXAO_*.md docs/archive/
mv ANALISE_*.md docs/archive/
mv "3.1.2 Parsing revisado.md" docs/archive/
mv DOCUMENTACAO_PROJETO.md docs/archive/
```

### **4. Remover Scripts Obsoletos**
```bash
rm -f api.py
rm -f run_sistema.py
rm -f processar_lotes.py
rm -f exportar_json.py
rm -f importar_postgres.py
rm -f schema.sql
rm -f teste_*.py
rm -f teste_*.sh
rm -f teste_*.bat
rm -f deploy_*.sh
rm -f monitor_*.sh
rm -f vps_commands.md
rm -f docker-compose.yml
rm -f Dockerfile
```

### **5. Limpar Web (se não usado)**
```bash
rm -rf web/  # Se não houver frontend web
```

---

## 📊 Economia Estimada

| Categoria | Economia |
|-----------|----------|
| Duplicatas removidas | ~23 MB |
| Lotes antigos | ~1 MB |
| Scripts obsoletos | ~100 KB |
| **Total** | **~24 MB** |

**Nota:** Documentação antiga será arquivada (não deletada), podendo ser recuperada se necessário.

---

## ✅ Resultado Final

**Estrutura limpa e organizada:**
- ✅ Sem duplicatas
- ✅ Documentação consolidada
- ✅ Scripts atualizados e funcionais
- ✅ Fácil navegação
- ✅ Pronto para produção

**Próximo passo:** Executar script de limpeza automatizado
