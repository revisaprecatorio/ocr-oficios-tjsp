#!/bin/bash
# Script para limpar tabela e reprocessar todos os PDFs com lógica corrigida
# Autor: Cascade AI + Persival Balleste
# Data: 15/10/2025

set -e  # Parar em caso de erro

echo "================================================================================"
echo "🔧 CORREÇÃO DE FALSOS REJEITADOS - Reprocessamento Completo"
echo "================================================================================"
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretórios
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PARSING_DIR="$PROJECT_ROOT/1_parsing_PDF"
INGESTAO_DIR="$PROJECT_ROOT/2_ingestao"
DATA_DIR="$PROJECT_ROOT/data/consultas"

echo "📁 Diretórios:"
echo "   Project: $PROJECT_ROOT"
echo "   Parsing: $PARSING_DIR"
echo "   Data: $DATA_DIR"
echo ""

# Verificar se está no ambiente virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ Ambiente virtual não ativado!${NC}"
    echo "   Execute: source .venv/bin/activate"
    exit 1
fi

echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
echo ""

# ============================================================================
# PASSO 1: Limpar Tabela PostgreSQL
# ============================================================================

echo "================================================================================"
echo "📊 PASSO 1: Limpar Tabela PostgreSQL"
echo "================================================================================"
echo ""

echo -e "${YELLOW}⚠️  ATENÇÃO: Isso vai DELETAR todos os registros da tabela lista_processos!${NC}"
echo ""
read -p "Deseja continuar? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Operação cancelada pelo usuário"
    exit 1
fi

echo ""
echo "🗑️  Limpando tabela..."

# Carregar variáveis de ambiente
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Executar TRUNCATE
PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "TRUNCATE TABLE lista_processos CASCADE;"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Tabela limpa com sucesso${NC}"
else
    echo -e "${RED}❌ Erro ao limpar tabela${NC}"
    exit 1
fi

# Verificar
COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM lista_processos;")

echo "📊 Registros na tabela: $COUNT"
echo ""

# ============================================================================
# PASSO 2: Reprocessar PDFs
# ============================================================================

echo "================================================================================"
echo "🔄 PASSO 2: Reprocessar PDFs com Lógica Corrigida"
echo "================================================================================"
echo ""

cd "$PARSING_DIR"

echo "📁 Diretório de PDFs: $DATA_DIR"
echo "📊 Contando PDFs..."

PDF_COUNT=$(find "$DATA_DIR" -name "*.pdf" | wc -l | tr -d ' ')
echo "📄 Total de PDFs: $PDF_COUNT"
echo ""

echo "⏱️  Tempo estimado: ~30 segundos por PDF"
echo "⏱️  Total estimado: ~$((PDF_COUNT * 30 / 60)) minutos"
echo ""

read -p "Iniciar reprocessamento? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Reprocessamento cancelado"
    exit 1
fi

echo ""
echo "🚀 Iniciando reprocessamento..."
echo ""

python processar_lotes_v2.py \
    --input "$DATA_DIR" \
    --output outputs \
    --limite 0

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Reprocessamento concluído${NC}"
else
    echo ""
    echo -e "${RED}❌ Erro no reprocessamento${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASSO 3: Importar JSONs para PostgreSQL
# ============================================================================

echo "================================================================================"
echo "📥 PASSO 3: Importar JSONs para PostgreSQL"
echo "================================================================================"
echo ""

cd "$INGESTAO_DIR"

echo "📁 Diretório de JSONs: $PARSING_DIR/outputs/json"
echo ""

python scripts/ingest_all_jsons.py \
    --input "$PARSING_DIR/outputs/json" \
    --db-host "$POSTGRES_HOST" \
    --db-port "$POSTGRES_PORT" \
    --db-name "$POSTGRES_DB" \
    --db-user "$POSTGRES_USER"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Importação concluída${NC}"
else
    echo ""
    echo -e "${RED}❌ Erro na importação${NC}"
    exit 1
fi

echo ""

# ============================================================================
# PASSO 4: Validar Correção
# ============================================================================

echo "================================================================================"
echo "✅ PASSO 4: Validar Correção"
echo "================================================================================"
echo ""

echo "📊 Verificando falsos rejeitados..."
echo ""

# Query para verificar falsos rejeitados
FALSOS_REJEITADOS=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM lista_processos WHERE numero_ordem IS NOT NULL AND rejeitado = TRUE AND motivo_rejeicao IS NULL;")

echo "❌ Falsos rejeitados encontrados: $FALSOS_REJEITADOS"

if [ "$FALSOS_REJEITADOS" -eq 0 ]; then
    echo -e "${GREEN}✅ Nenhum falso rejeitado! Correção bem-sucedida!${NC}"
else
    echo -e "${RED}⚠️  Ainda existem $FALSOS_REJEITADOS falsos rejeitados${NC}"
fi

echo ""

# Estatísticas gerais
echo "📊 Estatísticas Gerais:"
echo ""

PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "
SELECT 
    COUNT(*) as total_processos,
    SUM(CASE WHEN rejeitado = TRUE THEN 1 ELSE 0 END) as rejeitados,
    SUM(CASE WHEN rejeitado = FALSE THEN 1 ELSE 0 END) as aceitos,
    SUM(CASE WHEN numero_ordem IS NOT NULL THEN 1 ELSE 0 END) as com_numero_ordem
FROM lista_processos;
"

echo ""

# Verificar os 13 casos específicos
echo "📋 Verificando os 13 casos corrigidos:"
echo ""

PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "
SELECT cpf, numero_processo, numero_ordem, rejeitado
FROM lista_processos
WHERE cpf IN (
  '95653511820', '94706751853', '94019940800', '49783491920',
  '41609824415', '19884761434', '11659296862', '10185170811',
  '10149607890', '06495530803', '03730461893', '02174781824',
  '01103192817'
)
ORDER BY cpf;
"

echo ""
echo "================================================================================"
echo "🎉 REPROCESSAMENTO CONCLUÍDO!"
echo "================================================================================"
echo ""
echo "📝 Próximos passos:"
echo "   1. Verificar interface Streamlit"
echo "   2. Commit das alterações"
echo "   3. Deploy em produção"
echo ""
