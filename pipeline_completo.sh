#!/bin/bash
# ============================================================================
# PIPELINE COMPLETO DE PONTA A PONTA - V3.0.0
# (OCR + INGESTÃO + VALIDAÇÃO FORTE + CÁLCULO)
# ============================================================================

set -e
set -o pipefail

# ----------------------------------------------------------------------------
# FORÇAR UTF-8 (WINDOWS SAFE)
# ----------------------------------------------------------------------------
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export PYTHONLEGACYWINDOWSSTDIO=0
export CI=true
export NON_INTERACTIVE=true

# ----------------------------------------------------------------------------
# CONFIGURAÇÕES
# ----------------------------------------------------------------------------
PROJECT_ROOT="C:/Users/Administrator/Documents/revisa/ocr-oficios-tjsp"
VENV_PYTHON="${PROJECT_ROOT}/env/Scripts/python.exe"
OUTPUT_NAME="consultas"

CPF="$1"

if [ -z "$CPF" ]; then
  echo "❌ CPF não informado para o pipeline OCR"
  exit 1
fi

INPUT_DATA="C:/temp/RevisaDownloads/${CPF}"
ARCHIVE_DATA="C:/temp/RevisaDownloads_Processados"

DB_HOST="72.60.62.124"
DB_PORT="5432"
DB_NAME="n8n"
DB_USER="admin"
DB_PASS="BetaAgent2024SecureDB"

CALC_PROJECT="C:/Users/Administrator/Documents/revisa/calc-precatorio-tjsp"
CALC_SCRIPT="${CALC_PROJECT}/main.py"

N8N_WEBHOOK_BASE="http://72.60.62.124:5678"

# ----------------------------------------------------------------------------
# CORES
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ----------------------------------------------------------------------------
# LOG NO BANCO (BEST-EFFORT)
# ----------------------------------------------------------------------------
log_db() {
    export LOG_DB_MSG="$1"
    "${VENV_PYTHON}" - <<END || true
import os, psycopg2
try:
    conn = psycopg2.connect(
        host='${DB_HOST}', port='${DB_PORT}',
        database='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO public.logs (id, cpf, "timestamp", descricao, processo)
        VALUES (nextval('logs_id_seq'), %s, CURRENT_TIMESTAMP, %s, 'PIPELINE')
    """, ('${CPF}', os.environ.get("LOG_DB_MSG","")))
    conn.commit()
    conn.close()
except Exception as e:
    print(f"[LOG_DB_ERRO] {e}")
END
}

# ----------------------------------------------------------------------------
# TRATAMENTO DE ERRO GLOBAL
# ----------------------------------------------------------------------------
handle_error() {
    msg="❌ ERRO CRÍTICO: Pipeline abortado na linha $1 (CPF=${CPF})"
    echo -e "${RED}$msg${NC}"
    log_db "$msg"
    exit 1
}
trap 'handle_error $LINENO' ERR

# ============================================================================
# INÍCIO
# ============================================================================
echo "============================================================"
echo -e "${BLUE}🚀 PIPELINE COMPLETO V3.0.0 — CPF ${CPF}${NC}"
echo "============================================================"
log_db "Pipeline iniciado"

# ============================================================================
# ETAPA 1 — LIMPEZA
# ============================================================================
echo -e "${YELLOW}📁 ETAPA 1: Preparando ambiente...${NC}"
cd "${PROJECT_ROOT}/1_parsing_PDF"

rm -f outputs/json/*.json 2>/dev/null || true
rm -rf "outputs/${OUTPUT_NAME}/lote_"* 2>/dev/null || true
rm -f "outputs/${OUTPUT_NAME}"/*.json 2>/dev/null || true

log_db "Etapa 1: staging limpo"

# ============================================================================
# ETAPA 2 — PROCESSAMENTO DE PDFs
# ============================================================================
echo -e "${YELLOW}🔄 ETAPA 2: Processando PDFs em ${INPUT_DATA}...${NC}"

if [ ! -d "${INPUT_DATA}" ] || [ -z "$(ls -A "${INPUT_DATA}" 2>/dev/null)" ]; then
    msg="❌ Pasta de entrada vazia para CPF ${CPF}. Abortando."
    echo -e "${RED}$msg${NC}"
    log_db "$msg"
    exit 1
fi

"${VENV_PYTHON}" -X utf8 processar_pipeline.py \
    --input "${INPUT_DATA}" \
    --output "outputs/${OUTPUT_NAME}"

log_db "Etapa 2: PDFs processados"

# ============================================================================
# ETAPA 3 — CENTRALIZAÇÃO DE JSONs
# ============================================================================
echo -e "${YELLOW}📦 ETAPA 3: Centralizando JSONs...${NC}"
mkdir -p outputs/json

find "outputs/${OUTPUT_NAME}" \
  -name "*.json" \
  ! -name "estatisticas_globais.json" \
  -exec cp {} outputs/json/ \;

TOTAL_JSONS=$(ls outputs/json/*.json 2>/dev/null | wc -l | tr -d ' ')

if [ "$TOTAL_JSONS" -eq 0 ]; then
    msg="❌ Nenhum JSON gerado para CPF ${CPF}. Abortando pipeline."
    echo -e "${RED}$msg${NC}"
    log_db "$msg"
    exit 1
fi

log_db "Etapa 3: ${TOTAL_JSONS} JSONs preparados"

# ============================================================================
# ETAPA 4 — INGESTÃO NO BANCO (CPF-SAFE)
# ============================================================================
echo -e "${YELLOW}💾 ETAPA 4: Ingestão no banco...${NC}"

SCRIPT_INGESTAO="${PROJECT_ROOT}/2_ingestao/scripts/ingest_all_jsons.py"

"${VENV_PYTHON}" -X utf8 "$SCRIPT_INGESTAO" \
  --input "../1_parsing_PDF/outputs/json" \
  --db-host "${DB_HOST}" \
  --db-port "${DB_PORT}" \
  --db-name "${DB_NAME}" \
  --db-user "${DB_USER}" \
  --cpf "${CPF}"

log_db "Etapa 4: ingestão executada"

# ============================================================================
# ETAPA 5 — VALIDAÇÃO FORTE (FAIL FAST)
# ============================================================================
echo -e "${YELLOW}🔍 ETAPA 5: Validação de ingestão por CPF...${NC}"

COUNT=$("${VENV_PYTHON}" - <<END
import psycopg2
conn = psycopg2.connect(
 host='${DB_HOST}', port='${DB_PORT}',
 database='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
)
cur = conn.cursor()
cur.execute("SELECT count(*) FROM esaj_detalhe_processos WHERE cpf = %s", ('${CPF}',))
print(cur.fetchone()[0])
conn.close()
END
)

if [ "$COUNT" -eq 0 ]; then
    msg="❌ Ingestão falhou: nenhum registro gravado para CPF ${CPF}. Abortando."
    echo -e "${RED}$msg${NC}"
    log_db "$msg"
    exit 1
fi

log_db "Etapa 5: validação OK — ${COUNT} registros no banco"

# ============================================================================
# ETAPA 6 — TAGS
# ============================================================================
echo -e "${YELLOW}📊 ETAPA 6: Recalculando tags...${NC}"
cd "${PROJECT_ROOT}/2_ingestao"

"${VENV_PYTHON}" -X utf8 scripts/recalcular_idoso.py

log_db "Etapa 6: tags recalculadas"

# ============================================================================
# ETAPA 7 — BACKUP JSONs (SÓ APÓS INGESTÃO OK)
# ============================================================================
echo -e "${YELLOW}🧹 ETAPA 7: Backup JSONs...${NC}"
cd "${PROJECT_ROOT}/1_parsing_PDF"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="outputs/historico_processado/${CPF}/${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

mv outputs/json/*.json "$BACKUP_DIR/"

log_db "Etapa 7: JSONs movidos para ${BACKUP_DIR}"

# ============================================================================
# ETAPA 8 — ARQUIVAR PDFs
# ============================================================================
echo -e "${YELLOW}📦 ETAPA 8: Arquivando PDFs...${NC}"

DATA_HOJE=$(date +%Y-%m-%d)
DESTINO_FINAL="${ARCHIVE_DATA}/${CPF}/${DATA_HOJE}_${TIMESTAMP}"
mkdir -p "${DESTINO_FINAL}"

mv "${INPUT_DATA}"/* "${DESTINO_FINAL}/"

log_db "Etapa 8: PDFs arquivados em ${DESTINO_FINAL}"

# ============================================================================
# ETAPA 9 — CÁLCULO FINAL (DB-DRIVEN REAL)
# ============================================================================
echo -e "${YELLOW}🧮 ETAPA 9: Executando cálculo final (DB-driven)...${NC}"
log_db "Etapa 9: iniciando cálculo final"

if [ ! -f "$CALC_SCRIPT" ]; then
    msg="❌ Script de cálculo não encontrado: ${CALC_SCRIPT}"
    echo -e "${RED}$msg${NC}"
    log_db "$msg"
    exit 1
fi

"${VENV_PYTHON}" -X utf8 "$CALC_SCRIPT" --cpf "${CPF}"

log_db "Etapa 9: cálculo final executado"

# ============================================================================
# ETAPA 9b — LAUDO DIRETO para processos 100% rejeitados (sem cálculo)
# Se o calc não gerou nenhum registro (todos rejeitados), aciona o
# webhook de laudo diretamente para que o cliente receba o email.
# ============================================================================
CALC_COUNT=$("${VENV_PYTHON}" -X utf8 - <<END
import psycopg2, sys
try:
    conn = psycopg2.connect(
        host='${DB_HOST}', port='${DB_PORT}',
        dbname='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM esaj_calc_precatorio_resumo WHERE cpf = %s", ('${CPF}',))
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print(0, file=sys.stderr)
    print(0)
END
)

if [ "${CALC_COUNT}" -eq 0 ]; then
    log_db "Etapa 9b: nenhum cálculo gerado (processos rejeitados) — buscando email para laudo direto"
    EMAIL=$("${VENV_PYTHON}" -X utf8 - <<END
import psycopg2, sys
try:
    conn = psycopg2.connect(
        host='${DB_HOST}', port='${DB_PORT}',
        dbname='${DB_NAME}', user='${DB_USER}', password='${DB_PASS}'
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT email FROM consultas_esaj
        WHERE cpf = %s AND email IS NOT NULL AND email != ''
        ORDER BY created_at DESC LIMIT 1
    """, ('${CPF}',))
    row = cur.fetchone()
    print(row[0] if row else '')
    conn.close()
except Exception as e:
    print('')
END
)
    if [ -n "${EMAIL}" ]; then
        curl -s -X POST "${N8N_WEBHOOK_BASE}/webhook/reporte-email-cpf" \
          -H "Content-Type: application/json" \
          -d "{\"cpf\": \"${CPF}\", \"email\": \"${EMAIL}\"}" || true
        log_db "Etapa 9b: laudo acionado para processo rejeitado (email: ${EMAIL})"
    else
        log_db "Etapa 9b: nenhum email encontrado para CPF ${CPF} — laudo não acionado"
    fi
fi

# ============================================================================
# FIM
# ============================================================================
echo "============================================================"
echo -e "${GREEN}✅ PIPELINE FINALIZADO COM SUCESSO — CPF ${CPF}${NC}"
echo "============================================================"
log_db "Pipeline finalizado com sucesso"

exit 0
