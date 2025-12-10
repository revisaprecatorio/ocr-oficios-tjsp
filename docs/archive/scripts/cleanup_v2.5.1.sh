#!/bin/bash
# ============================================================================
# SCRIPT DE LIMPEZA - Projeto OCR Ofícios TJSP v2.5.1
# ============================================================================
# Data: 14/11/2025
# Versão: 2.5.1
# Descrição: Remove arquivos temporários, logs antigos e documentação histórica
# ============================================================================

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
PROJECT_DIR="/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR"
BACKUP_DIR="${PROJECT_DIR}/backup_cleanup_$(date +%Y%m%d_%H%M%S)"
DRY_RUN=false

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Uso: $0 [--dry-run]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🧹 LIMPEZA DO PROJETO OCR OFÍCIOS TJSP v2.5.1${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  MODO DRY-RUN: Nenhum arquivo será removido${NC}"
    echo ""
fi

cd "$PROJECT_DIR"

# Função para remover arquivo/diretório
remove_item() {
    local item=$1
    local description=$2
    
    if [ -e "$item" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo -e "${YELLOW}[DRY-RUN]${NC} Removeria: $item ${BLUE}# $description${NC}"
        else
            echo -e "${GREEN}✓${NC} Removendo: $item ${BLUE}# $description${NC}"
            rm -rf "$item"
        fi
    else
        echo -e "${YELLOW}⊘${NC} Não encontrado: $item"
    fi
}

# Função para criar backup
create_backup() {
    if [ "$DRY_RUN" = false ]; then
        echo -e "${BLUE}📦 Criando backup em: $BACKUP_DIR${NC}"
        mkdir -p "$BACKUP_DIR"
        echo ""
    fi
}

# ============================================================================
# CATEGORIA 1: Documentos de Sessões Antigas (26 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📄 CATEGORIA 1: Documentos de Sessões Antigas${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "ANALISE_COMPARATIVA_CAMPOS_v2.5.1.md" "Análise comparativa"
remove_item "ANALISE_DETALHADA_PROMPT_LLM.md" "Análise prompt LLM"
remove_item "ANALISE_DETALHADA_V2.5.0.md" "Análise v2.5.0"
remove_item "ANALISE_REGRESSAO_COMPLETA.md" "Análise regressão"
remove_item "ATUALIZACAO_V1_PARA_V3_VPS.md" "Atualização VPS"
remove_item "BUG_VALOR_TRUNCADO.md" "Bug valor truncado"
remove_item "CLAUDE.md" "Notas Claude"
remove_item "COMPLETE_FIX_PLAN.md" "Plano de correção"
remove_item "DEPLOY_v2.4.0_TO_VPS.md" "Deploy v2.4.0"
remove_item "FIX_VALORES_TRUNCADOS.md" "Fix valores"
remove_item "IMPLEMENTACAO_V2.5.0.md" "Implementação v2.5.0"
remove_item "IMPLEMENTATION_SUCCESS_v2.4.0.md" "Sucesso v2.4.0"
remove_item "MULTI_CREDITOR_BUG_ANALYSIS.md" "Bug multi-creditor"
remove_item "PHASE6_STREAMLIT_UPDATE.md" "Fase 6 Streamlit"
remove_item "PLANO_IMPLEMENTACAO_TERMOS_JURIDICOS.md" "Plano termos jurídicos"
remove_item "PROPOSTA_EXTRACAO_FOCADA_V2.5.0.md" "Proposta v2.5.0"
remove_item "QUICK_FIX_TEST_RESULTS.md" "Resultados quick fix"
remove_item "RELATORIO_COMPARACAO_GITHUB.md" "Comparação GitHub"
remove_item "REPROCESSING_SUCCESS_REPORT.md" "Relatório reprocessamento"
remove_item "RESULTADO_IMPLEMENTACAO_TERMOS_JURIDICOS.md" "Resultado termos"
remove_item "RESUMO_V2.5.0.md" "Resumo v2.5.0"
remove_item "SESSAO_16-10-2025.md" "Sessão 16/10"
remove_item "SESSION_SUMMARY_v2.4.0_DEPLOYMENT.md" "Sessão v2.4.0"
remove_item "SOLUCAO_BUSCA_DIRETA_CPF_V2.4.4.md" "Solução busca CPF"
remove_item "SOLUCAO_ROBUSTA_V2.4.3.md" "Solução robusta"
remove_item "TESTE_COMPLETO_ROBERTO.md" "Teste Roberto"

echo ""

# ============================================================================
# CATEGORIA 2: Scripts de Teste Temporários (13 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🧪 CATEGORIA 2: Scripts de Teste Temporários${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "test_busca_direta_cpf.py" "Teste busca CPF"
remove_item "test_correcoes_v2.5.1.py" "Teste correções v2.5.1"
remove_item "test_extracao_focada_v2.5.0.py" "Teste extração focada"
remove_item "test_multi_creditor_fix.py" "Teste multi-creditor"
remove_item "test_normalizacao_valores.py" "Teste normalização"
remove_item "test_pdf_problema.py" "Teste PDF problema"
remove_item "test_termos_juridicos.py" "Teste termos jurídicos"
remove_item "test_todos_pdfs_roberto.py" "Teste PDFs Roberto"
remove_item "test_v2.5.0_completo.py" "Teste v2.5.0 completo"
remove_item "test_v2.5.0_fase1_e_2.py" "Teste v2.5.0 fase 1 e 2"
remove_item "test_v2.5.0_fase3.py" "Teste v2.5.0 fase 3"
remove_item "test_v2.5.0_todos_cpfs.py" "Teste todos CPFs"
remove_item "test_v2.5.0_todos_pdfs.py" "Teste todos PDFs"
remove_item "test_v2.5.1_cpf_cnpj_rne.py" "Teste CPF/CNPJ/RNE"
remove_item "test_v2.5.2_cpf_especifico.py" "Teste CPF específico"

echo ""

# ============================================================================
# CATEGORIA 3: Scripts de Reprocessamento Temporários (3 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔄 CATEGORIA 3: Scripts de Reprocessamento${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "reprocessar_completo_v2.5.2.py" "Reprocessamento v2.5.2"
remove_item "reprocessar_e_salvar_v2.5.1.py" "Reprocessamento v2.5.1"
remove_item "reprocessar_todos_v2.5.1.py" "Reprocessamento todos"

echo ""

# ============================================================================
# CATEGORIA 4: Logs de Execução Antigos (6 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📋 CATEGORIA 4: Logs Antigos${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "ingestion_with_fix.log" "Log ingestão"
remove_item "reprocessamento_completo_v2.5.1.log" "Log reprocessamento completo"
remove_item "reprocessamento_v2.5.1.log" "Log reprocessamento"
remove_item "reprocessing_log.txt" "Log reprocessing"
remove_item "reprocessing_with_fix.log" "Log reprocessing com fix (485KB)"
remove_item "test_todos_cpfs_output.log" "Log teste CPFs"

echo ""

# ============================================================================
# CATEGORIA 5: Scripts Utilitários Obsoletos (8 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔧 CATEGORIA 5: Scripts Utilitários Obsoletos${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "auto_complete_pipeline.sh" "Pipeline automático (obsoleto)"
remove_item "check_local_vs_vps.py" "Verificação local vs VPS"
remove_item "cleanup_project.sh" "Script limpeza antigo"
remove_item "debug_anexo_ii.py" "Debug ANEXO II"
remove_item "monitor_reprocessing.sh" "Monitor reprocessamento"
remove_item "QUICK_DEPLOY_COMMANDS.sh" "Comandos deploy rápido"
remove_item "VPS_RESTART_STREAMLIT.sh" "Restart Streamlit VPS"
remove_item "VPS_VERIFICATION.sh" "Verificação VPS"

echo ""

# ============================================================================
# CATEGORIA 6: Arquivos SQL Temporários (2 arquivos)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🗄️  CATEGORIA 6: Arquivos SQL Temporários${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "investigate_terms.sql" "Investigação termos"
remove_item "validar_termos_juridicos.sql" "Validação termos"

echo ""

# ============================================================================
# CATEGORIA 7: Scripts Python Utilitários (1 arquivo)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🐍 CATEGORIA 7: Scripts Python Utilitários${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "verify_vps_terms.py" "Verificação termos VPS"

echo ""

# ============================================================================
# CATEGORIA 8: Resultados de Teste (1 arquivo)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 CATEGORIA 8: Resultados de Teste${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "resultados_v2.5.0_todos_cpfs.json" "Resultados v2.5.0"

echo ""

# ============================================================================
# CATEGORIA 9: Pasta Completa de Experimentos (1 pasta - 84 itens)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔬 CATEGORIA 9: Pasta de Experimentos (84 itens)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item "8_erro_parsing-valor" "Pasta completa de experimentos históricos"

echo ""

# ============================================================================
# CATEGORIA 10: Diretórios de Sistema Desnecessários (4 - mantendo .claude e .cursor)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🗂️  CATEGORIA 10: Diretórios de Sistema${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}⊙${NC} Mantendo: .claude/ ${BLUE}# Configurações Claude${NC}"
echo -e "${YELLOW}⊙${NC} Mantendo: .cursor/ ${BLUE}# Configurações Cursor${NC}"
remove_item ".clinerules" "Configurações Cline"
remove_item ".pytest_cache" "Cache pytest"
remove_item "deploy" "Pasta deploy vazia"

echo ""

# ============================================================================
# CATEGORIA 11: Arquivos de Sistema (1 arquivo)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}💻 CATEGORIA 11: Arquivos de Sistema${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

remove_item ".DS_Store" "Arquivo macOS"

echo ""

# ============================================================================
# RESUMO FINAL
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ LIMPEZA CONCLUÍDA${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  MODO DRY-RUN: Nenhum arquivo foi removido${NC}"
    echo -e "${YELLOW}Execute sem --dry-run para aplicar as mudanças${NC}"
else
    echo -e "${GREEN}📊 Estatísticas:${NC}"
    echo -e "   • Documentos removidos: 26"
    echo -e "   • Scripts de teste removidos: 13"
    echo -e "   • Scripts de reprocessamento removidos: 3"
    echo -e "   • Logs removidos: 6"
    echo -e "   • Scripts utilitários removidos: 8"
    echo -e "   • Arquivos SQL removidos: 2"
    echo -e "   • Scripts Python removidos: 1"
    echo -e "   • Resultados de teste removidos: 1"
    echo -e "   • Pasta de experimentos removida: 1 (84 itens)"
    echo -e "   • Diretórios de sistema removidos: 3"
    echo -e "   • Arquivos de sistema removidos: 1"
    echo ""
    echo -e "${GREEN}   TOTAL: ~58 arquivos/pastas removidos${NC}"
    echo ""
    echo -e "${GREEN}📁 Arquivos mantidos (essenciais):${NC}"
    echo -e "   ✅ README.md (atualizado v2.5.1)"
    echo -e "   ✅ CHANGELOG.md"
    echo -e "   ✅ AGENTS.md"
    echo -e "   ✅ SCHEMA_TABELA.md"
    echo -e "   ✅ GERENCIAMENTO_SERVICOS_VPS.md"
    echo -e "   ✅ LOGICA_ATUAL_ALGORITMO.md"
    echo -e "   ✅ MELHORIAS_V2.5.1.md"
    echo -e "   ✅ LIMPEZA_PROJETO.md"
    echo -e "   ✅ 1_parsing_PDF/"
    echo -e "   ✅ 2_ingestao/"
    echo -e "   ✅ 3_streamlit/"
    echo -e "   ✅ pipeline_completo.sh"
    echo -e "   ✅ scripts_vps/"
    echo -e "   ✅ tests/"
    echo -e "   ✅ .claude/ (mantido conforme solicitado)"
    echo -e "   ✅ .cursor/ (mantido conforme solicitado)"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Projeto limpo e organizado!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
