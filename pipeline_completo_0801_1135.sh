#!/bin/bash
# ============================================================================
# PIPELINE COMPLETO DE PONTA A PONTA - V2.8.0 (FLUXO CONTÍNUO)
# ============================================================================
# 1. Limpa área de preparação
# 2. Processa PDFs (Lê de INPUT_DATA)
# 3. Organiza arquivos JSON
# 4. Importa para PostgreSQL (Incremental)
# 5. Valida resultados
# 6. Recalcula tags
# 7. Backup dos Outputs (JSONs)
# 8. ARQUIVAMENTO DOS INPUTS (PDFs) -> Nova Etapa
# ============================================================================

set -e  # Parar em caso de erro

# --- Forçar UTF-8 ---
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
OUTPUT_NAME="consultas"

# --- PASTAS DE TRABALHO ---
# Onde o Robô joga os arquivos (Entrada)
INPUT_DATA="C:/temp/RevisaDownloads"

# Onde guardamos os PDFs JÁ PROCESSADOS (Saída/Histórico)
ARCHIVE_DATA="C:/temp/RevisaDownloads_Processados"

# ===== BANCO DE DADOS =====
DB_HOST="72.60.62.124"
DB_PORT="5432"
DB_NAME="n8n"
DB_USER="admin"
DB_PASS="BetaAgent2024SecureDB"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "============================================================"
echo -e "${BLUE}🚀 PIPELINE COMPLETO V2.8.0 - INÍCIO${NC}"
echo "============================================================"
echo ""

# ============================================================================
# ETAPA 1: LIMPEZA DE PREPARAÇÃO
# ============================================================================
echo -e "${YELLOW}📁 ETAPA 1: Preparando ambiente...${NC}"
cd "${PROJECT_ROOT}/1_parsing_PDF"

if [ -d "outputs/json" ]; then
    rm -f outputs/json/*.json 2>/dev/null || true
fi

if [ -d "outputs/${OUTPUT_NAME}" ]; then
    rm -rf "outputs/${OUTPUT_NAME}"/lote_* 2>/dev/null || true
    rm -f "outputs/${OUTPUT_NAME}"/*.json 2>/dev/null || true
fi

echo "   ✅ Área de staging limpa."
echo ""

# ============================================================================
# ETAPA 2: PROCESSAR PDFs
# ============================================================================
echo -e "${YELLOW}🔄 ETAPA 2: Processando PDFs em ${INPUT_DATA}...${NC}"

# Verifica se tem arquivos para processar
if [ -z "$(ls -A ${INPUT_DATA} 2>/dev/null)" ]; then
   echo -e "${RED}⚠️  A pasta de entrada está vazia! Nada para processar.${NC}"
   exit 0
fi

"${VENV_PYTHON}" -X utf8 processar_pipeline.py \
    --input "${INPUT_DATA}" \
    --output "outputs/${OUTPUT_NAME}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro no processamento!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Processamento concluído!${NC}"
echo ""

# ============================================================================
# ETAPA 3: ORGANIZAR JSONs
# ============================================================================
echo -e "${YELLOW}📦 ETAPA 3: Centralizando arquivos...${NC}"
mkdir -p outputs/json

if [ -d "outputs/${OUTPUT_NAME}" ]; then
    find "outputs/${OUTPUT_NAME}" -name "*.json" -type f ! -name "estatisticas_globais.json" -exec cp {} outputs/json/ \; 2>/dev/null || true
fi

total_jsons=$(ls outputs/json/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "   ✅ $total_jsons JSONs novos prontos."
echo ""

# ============================================================================
# ETAPA 4: IMPORTAR PARA BANCO
# ============================================================================
echo -e "${YELLOW}💾 ETAPA 4: Gravando no Banco (Incremental)...${NC}"

SCRIPT_INGESTAO="${PROJECT_ROOT}/2_ingestao/scripts/ingest_all_jsons.py"

"${VENV_PYTHON}" -X utf8 "$SCRIPT_INGESTAO" \
  --input "../1_parsing_PDF/outputs/json" \
  --db-host "${DB_HOST}" \
  --db-port "${DB_PORT}" \
  --db-name "${DB_NAME}" \
  --db-user "${DB_USER}"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro na importação!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Gravação concluída!${NC}"
echo ""

# ============================================================================
# ETAPA 5: VALIDAÇÃO
# ============================================================================
echo -e "${YELLOW}🔍 ETAPA 5: Validando...${NC}"

"${VENV_PYTHON}" -X utf8 << PYEOF
import psycopg2
try:
    conn = psycopg2.connect(host='${DB_HOST}', port=${DB_PORT}, database='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM esaj_detalhe_processos;")
    print(f"   📊 Total de registros no banco: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"   ⚠️ Erro validação: {e}")
PYEOF
echo ""

# ============================================================================
# ETAPA 6: ATUALIZAR TAGS
# ============================================================================
echo -e "${YELLOW}📊 ETAPA 6: Atualizando tags...${NC}"
cd "${PROJECT_ROOT}/2_ingestao"
"${VENV_PYTHON}" -X utf8 scripts/recalcular_idoso.py
echo ""

# ============================================================================
# ETAPA 7: BACKUP DOS OUTPUTS (JSONs)
# ============================================================================
echo -e "${YELLOW}🧹 ETAPA 7: Backup dos JSONs...${NC}"
cd "${PROJECT_ROOT}/1_parsing_PDF"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="outputs/historico_processado/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

if [ -d "outputs/json" ]; then
    mv outputs/json/*.json "$BACKUP_DIR/" 2>/dev/null || true
fi
# Limpa lixo temporário
rm -rf "outputs/${OUTPUT_NAME}"/lote_* 2>/dev/null || true

echo "   ✅ JSONs movidos para histórico."
echo ""

# ============================================================================
# ETAPA 8: ARQUIVAR PDFs ORIGINAIS (A SOLUÇÃO)
# ============================================================================
echo -e "${YELLOW}📦 ETAPA 8: Arquivando PDFs processados...${NC}"

# Cria a pasta de arquivo se não existir
mkdir -p "${ARCHIVE_DATA}"

# Cria uma subpasta com a data de hoje para organizar o arquivo
DATA_HOJE=$(date +%Y-%m-%d)
DESTINO_FINAL="${ARCHIVE_DATA}/${DATA_HOJE}_${TIMESTAMP}"
mkdir -p "${DESTINO_FINAL}"

# Move tudo da pasta de entrada para a pasta de arquivo
# O comando mv move as pastas dos CPFs
if [ -n "$(ls -A ${INPUT_DATA} 2>/dev/null)" ]; then
    mv "${INPUT_DATA}"/* "${DESTINO_FINAL}/"
    echo -e "${GREEN}✅ PDFs movidos de:${NC} ${INPUT_DATA}"
    echo -e "${GREEN}   Para:${NC} ${DESTINO_FINAL}"
else
    echo "   ⚠️  Nada para mover (pasta já estava vazia)."
fi

echo ""
echo "============================================================"
echo "✅ CICLO V2.8.0 CONCLUÍDO! SISTEMA PRONTO PARA NOVOS DADOS."
echo "============================================================"
echo ""