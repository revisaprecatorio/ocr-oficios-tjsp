#!/bin/bash
# Script de Limpeza do Projeto OCR
# Remove duplicatas e arquiva documentação antiga

set -e

echo "=========================================="
echo "🧹 LIMPEZA DO PROJETO OCR"
echo "=========================================="

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para confirmar ação
confirm() {
    read -p "$1 (s/N): " response
    case "$response" in
        [sS][iI][mM]|[sS]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Criar diretório de archive
echo -e "\n${YELLOW}📁 Criando diretório docs/archive...${NC}"
mkdir -p docs/archive

# 1. REMOVER DUPLICATAS
echo -e "\n${YELLOW}🗑️  PASSO 1: Remover Duplicatas${NC}"

if [ -d "Processos" ]; then
    if confirm "Remover Processos/ (duplicata de data/)?"; then
        rm -rf Processos/
        echo -e "${GREEN}✅ Processos/ removido${NC}"
    fi
fi

if [ -d "app" ]; then
    if confirm "Remover app/ (duplicata de 1_parsing_PDF/app/)?"; then
        rm -rf app/
        echo -e "${GREEN}✅ app/ removido${NC}"
    fi
fi

if [ -d "output_teste" ]; then
    if confirm "Remover output_teste/?"; then
        rm -rf output_teste/
        echo -e "${GREEN}✅ output_teste/ removido${NC}"
    fi
fi

if [ -d "various" ]; then
    if confirm "Remover various/?"; then
        rm -rf various/
        echo -e "${GREEN}✅ various/ removido${NC}"
    fi
fi

# 2. LIMPAR LOTES ANTIGOS
echo -e "\n${YELLOW}🗑️  PASSO 2: Limpar Lotes Antigos${NC}"

if [ -d "1_parsing_PDF/outputs" ]; then
    if confirm "Remover lote_* de 1_parsing_PDF/outputs/ (manter apenas json/)?"; then
        cd 1_parsing_PDF/outputs/
        rm -rf lote_*
        rm -f *.csv
        rm -f estatisticas_globais.json
        rm -f organize_jsons.py
        cd ../..
        echo -e "${GREEN}✅ Lotes antigos removidos${NC}"
    fi
fi

# 3. ARQUIVAR DOCUMENTAÇÃO ANTIGA
echo -e "\n${YELLOW}📦 PASSO 3: Arquivar Documentação Antiga${NC}"

if confirm "Mover documentação antiga para docs/archive/?"; then
    # Diretórios
    [ -d "_definition-e-specs" ] && mv _definition-e-specs/ docs/archive/
    [ -d "_validation_v1" ] && mv _validation_v1/ docs/archive/
    [ -d "deploy" ] && mv deploy/ docs/archive/
    
    # Arquivos MD
    [ -f "RESUMO_EXECUTIVO.md" ] && mv RESUMO_EXECUTIVO.md docs/archive/
    [ -f "RESUMO_EXECUTIVO_FINAL.md" ] && mv RESUMO_EXECUTIVO_FINAL.md docs/archive/
    [ -f "RESUMO_IMPLEMENTACAO.md" ] && mv RESUMO_IMPLEMENTACAO.md docs/archive/
    [ -f "RELATORIO_TESTES.md" ] && mv RELATORIO_TESTES.md docs/archive/
    [ -f "RELATORIO_FINAL_REFINAMENTO.md" ] && mv RELATORIO_FINAL_REFINAMENTO.md docs/archive/
    [ -f "HISTORICO_DEPLOY.md" ] && mv HISTORICO_DEPLOY.md docs/archive/
    [ -f "DEPLOY_WINDOWS_SERVER.md" ] && mv DEPLOY_WINDOWS_SERVER.md docs/archive/
    [ -f "REFLEXAO_E_MELHORIAS.md" ] && mv REFLEXAO_E_MELHORIAS.md docs/archive/
    [ -f "ANALISE_OFICIO_EXEMPLO.md" ] && mv ANALISE_OFICIO_EXEMPLO.md docs/archive/
    [ -f "3.1.2 Parsing revisado.md" ] && mv "3.1.2 Parsing revisado.md" docs/archive/
    [ -f "DOCUMENTACAO_PROJETO.md" ] && mv DOCUMENTACAO_PROJETO.md docs/archive/
    
    echo -e "${GREEN}✅ Documentação arquivada${NC}"
fi

# 4. REMOVER SCRIPTS OBSOLETOS
echo -e "\n${YELLOW}🗑️  PASSO 4: Remover Scripts Obsoletos${NC}"

if confirm "Remover scripts obsoletos?"; then
    rm -f api.py
    rm -f run_sistema.py
    rm -f processar_lotes.py
    rm -f exportar_json.py
    rm -f importar_postgres.py
    rm -f schema.sql
    rm -f teste_windows_compat.py
    rm -f teste_pipeline_completo.sh
    rm -f teste_pipeline_completo.bat
    rm -f deploy_vps.sh
    rm -f deploy_vps_otimizado.sh
    rm -f monitor_vps.sh
    rm -f monitor_vps_avancado.sh
    rm -f vps_commands.md
    rm -f docker-compose.yml
    rm -f Dockerfile
    
    echo -e "${GREEN}✅ Scripts obsoletos removidos${NC}"
fi

# 5. LIMPAR WEB (se não usado)
echo -e "\n${YELLOW}🗑️  PASSO 5: Limpar Web${NC}"

if [ -d "web" ]; then
    if confirm "Remover web/ (se não houver frontend)?"; then
        rm -rf web/
        echo -e "${GREEN}✅ web/ removido${NC}"
    fi
fi

# RESUMO
echo -e "\n=========================================="
echo -e "${GREEN}✅ LIMPEZA CONCLUÍDA!${NC}"
echo "=========================================="
echo ""
echo "📊 Estrutura final:"
echo "   ✅ data/ - PDFs originais"
echo "   ✅ 1_parsing_PDF/ - Código de parsing"
echo "   ✅ 2_ingestao/ - Ingestão e Streamlit"
echo "   ✅ tests/ - Testes"
echo "   ✅ docs/archive/ - Documentação antiga"
echo ""
echo "📁 Arquivos mantidos:"
echo "   ✅ AGENTS.md"
echo "   ✅ README.md"
echo "   ✅ CLAUDE.md"
echo "   ✅ requirements.txt"
echo "   ✅ .env"
echo ""
echo "🎯 Próximo passo: git add . && git commit -m 'chore: Limpar projeto'"
echo "=========================================="
