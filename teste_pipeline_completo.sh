#!/bin/bash
# -*- coding: utf-8 -*-
#
# Script de Teste Completo do Pipeline
# Testa ETAPA 1 (PDFs -> JSONs) com 3 PDFs reais
#
# Uso:
#   chmod +x teste_pipeline_completo.sh
#   ./teste_pipeline_completo.sh

set -e  # Parar em caso de erro

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  TESTE COMPLETO DO PIPELINE - Ofícios Requisitórios TJSP       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
    echo "   Copie .env.example e configure OPENAI_API_KEY"
    exit 1
fi

# Carregar OPENAI_API_KEY
source .env
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY não configurada no .env!${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Configurações carregadas de .env"
echo ""

# Limpar diretório de output de testes anteriores
echo "═══════════════════════════════════════════════════════════════"
echo "1. LIMPEZA DE OUTPUTS ANTERIORES"
echo "═══════════════════════════════════════════════════════════════"

if [ -d "./output_teste" ]; then
    echo "Removendo ./output_teste anterior..."
    rm -rf ./output_teste
fi

echo -e "${GREEN}✓${NC} Diretório limpo"
echo ""

# ETAPA 1: Exportar JSONs (apenas 3 PDFs para teste)
echo "═══════════════════════════════════════════════════════════════"
echo "2. ETAPA 1: PDFs -> JSONs (3 PDFs de teste)"
echo "═══════════════════════════════════════════════════════════════"

python3 exportar_json.py \
    --input ./data/consultas \
    --output ./output_teste \
    --limite 3

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} ETAPA 1 concluída com sucesso"
else
    echo -e "${RED}❌ ETAPA 1 falhou!${NC}"
    exit 1
fi

echo ""

# Verificar JSONs gerados
echo "═══════════════════════════════════════════════════════════════"
echo "3. VERIFICAÇÃO DOS JSONs GERADOS"
echo "═══════════════════════════════════════════════════════════════"

TOTAL_JSONS=$(find ./output_teste/json -name "*.json" | wc -l | tr -d ' ')
echo "Total de JSONs gerados: $TOTAL_JSONS"

if [ "$TOTAL_JSONS" -eq 0 ]; then
    echo -e "${RED}❌ Nenhum JSON gerado!${NC}"
    exit 1
fi

echo ""
echo "JSONs gerados:"
find ./output_teste/json -name "*.json" -exec echo "  - {}" \;

echo ""
echo "Amostra do primeiro JSON:"
FIRST_JSON=$(find ./output_teste/json -name "*.json" | head -1)
echo "Arquivo: $FIRST_JSON"
echo "---"
cat "$FIRST_JSON" | python3 -m json.tool | head -40
echo "..."

echo ""
echo -e "${GREEN}✓${NC} JSONs verificados"
echo ""

# Mostrar estatísticas
echo "═══════════════════════════════════════════════════════════════"
echo "4. ESTATÍSTICAS DO PROCESSAMENTO"
echo "═══════════════════════════════════════════════════════════════"

if [ -f "./output_teste/estatisticas.json" ]; then
    cat ./output_teste/estatisticas.json | python3 -m json.tool
else
    echo -e "${YELLOW}⚠️  Arquivo de estatísticas não encontrado${NC}"
fi

echo ""

# Verificar se algum JSON tem dados bancários
echo "═══════════════════════════════════════════════════════════════"
echo "5. VERIFICAÇÃO DE DADOS BANCÁRIOS (ANEXO II)"
echo "═══════════════════════════════════════════════════════════════"

COM_BANCO=0
for json_file in $(find ./output_teste/json -name "*.json"); do
    if grep -q '"banco"' "$json_file"; then
        echo -e "${GREEN}✓${NC} $json_file contém dados bancários"
        COM_BANCO=$((COM_BANCO + 1))
    fi
done

echo ""
echo "JSONs com dados bancários: $COM_BANCO/$TOTAL_JSONS"

if [ "$COM_BANCO" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Nenhum ANEXO II detectado (normal se PDFs não tiverem)${NC}"
fi

echo ""

# Resumo final
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                         TESTE CONCLUÍDO                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Resultados salvos em: ./output_teste/"
echo ""
echo -e "${GREEN}✓ PIPELINE TESTADO COM SUCESSO!${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Revisar JSONs em: ./output_teste/json/"
echo "  2. Se OK, processar todos os PDFs: python3 exportar_json.py --input ./data/consultas --output ./output"
echo "  3. Importar para PostgreSQL: python3 importar_postgres.py --input ./output/json"
echo ""
