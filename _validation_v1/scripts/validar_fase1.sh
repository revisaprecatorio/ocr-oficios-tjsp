#!/bin/bash
# Script de Validação - Fase 1: Teste Unitário (3 PDFs)
# Sistema OCR - Ofícios Requisitórios TJSP

set -e  # Exit on error

echo "=========================================="
echo "🧪 VALIDAÇÃO FASE 1 - Teste Unitário"
echo "=========================================="
echo ""

# Configurações
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VALIDATION_DIR="${PROJECT_DIR}/_validation_v1"
OUTPUT_DIR="${VALIDATION_DIR}/outputs/fase1_teste_unitario"
INPUT_DIR="${PROJECT_DIR}/data/consultas"

echo "📁 Diretórios:"
echo "   Projeto: ${PROJECT_DIR}"
echo "   Validação: ${VALIDATION_DIR}"
echo "   Input: ${INPUT_DIR}"
echo "   Output: ${OUTPUT_DIR}"
echo ""

# Verificar ambiente virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Ambiente virtual não ativado!"
    echo "   Execute: source .venv/bin/activate"
    exit 1
fi

echo "✅ Ambiente virtual ativado: ${VIRTUAL_ENV}"
echo ""

# Verificar .env
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "   Copie .env.example e configure as variáveis"
    exit 1
fi

echo "✅ Arquivo .env encontrado"
echo ""

# Verificar OPENAI_API_KEY
source "${PROJECT_DIR}/.env"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY não configurada no .env"
    exit 1
fi

echo "✅ OPENAI_API_KEY configurada"
echo ""

# Verificar estrutura de PDFs
if [ ! -d "$INPUT_DIR" ]; then
    echo "❌ Diretório de PDFs não encontrado: ${INPUT_DIR}"
    exit 1
fi

PDF_COUNT=$(find "$INPUT_DIR" -name "*.pdf" | wc -l | tr -d ' ')
echo "📊 Total de PDFs disponíveis: ${PDF_COUNT}"
echo ""

if [ "$PDF_COUNT" -lt 3 ]; then
    echo "⚠️  Menos de 3 PDFs disponíveis para teste"
    echo "   Continuando com ${PDF_COUNT} PDF(s)..."
fi

# Criar diretórios de output
mkdir -p "${OUTPUT_DIR}/jsons"
mkdir -p "${OUTPUT_DIR}/logs"
mkdir -p "${OUTPUT_DIR}/anomalias"

echo "📂 Estrutura de output criada"
echo ""

# Executar processamento
echo "=========================================="
echo "🚀 Iniciando processamento..."
echo "=========================================="
echo ""

cd "$PROJECT_DIR"

python exportar_json.py \
    --input "$INPUT_DIR" \
    --output "${OUTPUT_DIR}/jsons" \
    --limite 3

echo ""
echo "=========================================="
echo "✅ Processamento concluído!"
echo "=========================================="
echo ""

# Análise de resultados
echo "📊 Análise de Resultados:"
echo ""

JSON_COUNT=$(find "${OUTPUT_DIR}/jsons" -name "*.json" -type f | wc -l | tr -d ' ')
echo "   JSONs gerados: ${JSON_COUNT}"

if [ "$JSON_COUNT" -gt 0 ]; then
    echo ""
    echo "   Arquivos gerados:"
    find "${OUTPUT_DIR}/jsons" -name "*.json" -type f | while read -r file; do
        size=$(du -h "$file" | cut -f1)
        echo "      - $(basename "$file") (${size})"
    done
fi

echo ""
echo "📝 Logs disponíveis em:"
echo "   ${OUTPUT_DIR}/logs/"
echo ""

echo "=========================================="
echo "✅ FASE 1 CONCLUÍDA"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "1. Revisar JSONs gerados em: ${OUTPUT_DIR}/jsons/"
echo "2. Verificar logs em: ${OUTPUT_DIR}/logs/"
echo "3. Analisar anomalias (se houver)"
echo "4. Validar campos obrigatórios"
echo "5. Validar dados bancários (ANEXO II)"
echo ""
