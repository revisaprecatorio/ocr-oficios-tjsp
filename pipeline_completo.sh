#!/bin/bash
# ============================================================================
# PIPELINE COMPLETO DE PONTA A PONTA - V2.6.0
# ============================================================================
# Este script executa todo o pipeline:
# 1. Limpa JSONs antigos
# 2. Processa todos os PDFs (processar_pipeline.py)
# 3. TRUNCATE do banco PostgreSQL
# 4. Importa JSONs para PostgreSQL (VPS)
# 5. Valida resultados (incluindo campos V2.5.3)
# 6. Recalcula tag idoso
# ============================================================================

set -e  # Parar em caso de erro

# --- Forçar UTF-8 (Windows/Python) ---
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONLEGACYWINDOWSSTDIO=0


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
PROJECT_ROOT="C:/Users/Administrator/Documents/revisa/ocr-oficios-tjsp"
VENV_PYTHON="${PROJECT_ROOT}/env/Scripts/python.exe"
INPUT_DATA="C:/temp/RevisaDownloads"
OUTPUT_NAME="consultas"

# ===== BANCO DE DADOS (Validado) =====
DB_HOST="72.60.62.124"
DB_PORT="5432"
DB_NAME="n8n"
DB_USER="admin"
DB_PASS="BetaAgent2024SecureDB"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo -e "${BLUE}🚀 PIPELINE COMPLETO V2.6.0 - INÍCIO${NC}"
echo "============================================================"
echo ""

# ============================================================================
# ETAPA 1: LIMPAR OUTPUTS ANTIGOS
# ============================================================================
echo -e "${YELLOW}📁 ETAPA 1: Limpando outputs antigos...${NC}"
cd "${PROJECT_ROOT}/1_parsing_PDF"

# Limpar pasta json/ centralizada
if [ -d "outputs/json" ]; then
    rm -f outputs/json/*.json
    echo "   ✅ Pasta outputs/json/ limpa"
fi

# Limpar pasta outputs/consultas/ (novo formato)
if [ -d "outputs/${OUTPUT_NAME}" ]; then
    rm -f "outputs/${OUTPUT_NAME}"/*.json
    rm -f "outputs/${OUTPUT_NAME}"/logs/*.md 2>/dev/null || true
    echo "   ✅ Pasta outputs/${OUTPUT_NAME}/ limpa"
fi

# Limpar pastas lote_* (formato antigo)
for dir in outputs/lote_*; do
    if [ -d "$dir" ]; then
        rm -f "$dir"/*.json
        echo "   ✅ Pasta $dir limpa"
    fi
done

# Limpar CSVs de lotes
rm -f outputs/lote_*.csv 2>/dev/null || true

# Limpar estatísticas
if [ -f "outputs/estatisticas_globais.json" ]; then
    rm -f outputs/estatisticas_globais.json
    echo "   ✅ Estatísticas antigas removidas"
fi

echo ""

# ============================================================================
# ETAPA 2: PROCESSAR TODOS OS PDFs
# ============================================================================
echo -e "${YELLOW}🔄 ETAPA 2: Processando todos os PDFs...${NC}"
echo ""

# Executar processar_pipeline.py com parâmetros
"${VENV_PYTHON}" -X utf8 processar_pipeline.py \
    --input "${INPUT_DATA}" \
    --output "outputs/${OUTPUT_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro no processamento dos PDFs!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Processamento concluído!${NC}"
echo ""

# ============================================================================
# ETAPA 3: COPIAR JSONs PARA PASTA CENTRALIZADA
# ============================================================================
echo -e "${YELLOW}📦 ETAPA 3: Organizando JSONs Automaticamente...${NC}"

# Criar pasta json/ se não existir
mkdir -p outputs/json

# 1. Copiar JSONs da raiz de outputs/consultas (se houver)
if [ -d "outputs/${OUTPUT_NAME}" ]; then
    find "outputs/${OUTPUT_NAME}" -maxdepth 1 -name "*.json" -type f ! -name "estatisticas_globais.json" -exec cp {} outputs/json/ \; 2>/dev/null || true
fi

# 2. Copiar JSONs das subpastas de lote (lote_001, lote_002, etc.)
# Esta parte garante que os arquivos gerados nos lotes vão para a pasta de ingestão
if [ -d "outputs/${OUTPUT_NAME}" ]; then
    find "outputs/${OUTPUT_NAME}" -mindepth 2 -name "*.json" -type f -exec cp {} outputs/json/ \; 2>/dev/null || true
fi

total_jsons=$(ls outputs/json/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "   ✅ $total_jsons JSONs copiados para outputs/json/"
echo ""

# ============================================================================
# ETAPA 3.5: TRUNCATE DO BANCO POSTGRESQL
# ============================================================================
echo -e "${YELLOW}🗑️  ETAPA 3.5: Limpando banco PostgreSQL...${NC}"
echo ""

"${VENV_PYTHON}" -X utf8 << PYEOF

import psycopg2

print('🗑️  Executando TRUNCATE...')
try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port=${DB_PORT},
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASS}'
    )
    cursor = conn.cursor()
    
    # Verifica se a tabela existe antes de truncar
    cursor.execute("SELECT to_regclass('public.esaj_detalhe_processos');")
    if cursor.fetchone()[0]:
        cursor.execute('TRUNCATE TABLE esaj_detalhe_processos RESTART IDENTITY CASCADE;')
        conn.commit()
        print('✅ Tabela TRUNCADA com sucesso!')
        
        # Verificar
        cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos;')
        count = cursor.fetchone()[0]
        print(f'📊 Total após TRUNCATE: {count} registros')
    else:
        print('⚠️ Tabela não encontrada (será criada na ingestão).')

    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Erro no Truncate: {e}')
    # Não sai com erro fatal aqui para tentar criar a tabela na próxima etapa
    pass
PYEOF

echo ""

# ============================================================================
# ETAPA 4: IMPORTAR PARA POSTGRESQL (VPS)
# ============================================================================
echo -e "${YELLOW}💾 ETAPA 4: Importando para PostgreSQL (VPS)...${NC}"
echo ""

# Ajuste do caminho para onde o usuário moveu o arquivo
SCRIPT_INGESTAO="${PROJECT_ROOT}/2_ingestao/scripts/ingest_all_jsons.py"

"${VENV_PYTHON}" -X utf8 "$SCRIPT_INGESTAO" \
  --input "../1_parsing_PDF/outputs/json" \
  --db-host "${DB_HOST}" \
  --db-port "${DB_PORT}" \
  --db-name "${DB_NAME}" \
  --db-user "${DB_USER}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro na importação para PostgreSQL!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Importação concluída!${NC}"
echo ""

# ============================================================================
# ETAPA 5: VALIDAR RESULTADOS (V2.5.3)
# ============================================================================
echo -e "${YELLOW}🔍 ETAPA 5: Validando resultados...${NC}"
echo ""

"${VENV_PYTHON}" -X utf8 << PYEOF

import psycopg2

try:
    conn = psycopg2.connect(
        host='${DB_HOST}',
        port=${DB_PORT},
        database='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASS}'
    )

    cur = conn.cursor()

    # Estatísticas gerais
    cur.execute("""
    SELECT
      COUNT(*) as total,
      COUNT(CASE WHEN rejeitado = TRUE THEN 1 END) as rejeitados,
      COUNT(CASE WHEN numero_ordem IS NOT NULL THEN 1 END) as com_ordem,
      COUNT(CASE WHEN numero_ordem IS NOT NULL AND rejeitado = TRUE THEN 1 END) as falsos_rejeitados
    FROM esaj_detalhe_processos;
    """)

    result = cur.fetchone()
    if result:
        total, rejeitados, com_ordem, falsos = result
        
        print("=" * 70)
        print("📊 VALIDAÇÃO FINAL - V2.5.3")
        print("=" * 70)
        print(f"\\n✅ Total de registros: {total}")
        print(f"📋 Com número de ordem: {com_ordem}")
        print(f"❌ Rejeitados: {rejeitados}")
        print(f"⚠️  Falsos rejeitados: {falsos}")
    else:
        print("Nenhum dado encontrado para validar.")

    conn.close()
except Exception as e:
    print(f"Erro na validação: {e}")

PYEOF

echo ""
echo "============================================================"
echo "✅ PIPELINE COMPLETO V2.6.0 CONCLUÍDO!"
echo "============================================================"
echo ""