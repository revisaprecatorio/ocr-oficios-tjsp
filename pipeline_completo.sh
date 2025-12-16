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

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
#PROJECT_ROOT="/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR"
PROJECT_ROOT="C:/Users/Administrator/Documents/revisa/ocr-oficios-tjsp"
#VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"
VENV_PYTHON="${PROJECT_ROOT}/env/Scripts/python.exe"
INPUT_DATA="../data/consultas"
OUTPUT_NAME="consultas"

# Database
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
"${VENV_PYTHON}" processar_pipeline.py \
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
echo -e "${YELLOW}📦 ETAPA 3: Organizando JSONs...${NC}"

# Criar pasta json/ se não existir
mkdir -p outputs/json

# Copiar JSONs do novo formato (outputs/consultas/)
if [ -d "outputs/${OUTPUT_NAME}" ]; then
    find "outputs/${OUTPUT_NAME}" -name "*.json" -type f ! -name "estatisticas_globais.json" -exec cp {} outputs/json/ \; 2>/dev/null || true
fi

# Copiar JSONs do formato antigo (outputs/lote_*)
find outputs/lote_* -name "*.json" -type f -exec cp {} outputs/json/ \; 2>/dev/null || true

total_jsons=$(ls outputs/json/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "   ✅ $total_jsons JSONs copiados para outputs/json/"
echo ""

# ============================================================================
# ETAPA 3.5: TRUNCATE DO BANCO POSTGRESQL
# ============================================================================
echo -e "${YELLOW}🗑️  ETAPA 3.5: Limpando banco PostgreSQL...${NC}"
echo ""

"${VENV_PYTHON}" << PYEOF
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
    cursor.execute('TRUNCATE TABLE esaj_detalhe_processos RESTART IDENTITY CASCADE;')
    conn.commit()
    print('✅ Tabela TRUNCADA com sucesso!')

    # Verificar
    cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos;')
    count = cursor.fetchone()[0]
    print(f'📊 Total após TRUNCATE: {count} registros')

    cursor.close()
    conn.close()
except Exception as e:
    print(f'❌ Erro: {e}')
    exit(1)
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro no TRUNCATE do banco!${NC}"
    exit 1
fi

echo ""

# ============================================================================
# ETAPA 4: IMPORTAR PARA POSTGRESQL (VPS)
# ============================================================================
echo -e "${YELLOW}💾 ETAPA 4: Importando para PostgreSQL (VPS)...${NC}"
echo ""

cd "${PROJECT_ROOT}/2_ingestao"

"${VENV_PYTHON}" scripts/ingest_all_jsons.py \
  --input ../1_parsing_PDF/outputs/json \
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

"${VENV_PYTHON}" << 'PYEOF'
import psycopg2

conn = psycopg2.connect(
    host='72.60.62.124',
    port=5432,
    database='n8n',
    user='admin',
    password='BetaAgent2024SecureDB'
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

total, rejeitados, com_ordem, falsos = cur.fetchone()

print("=" * 70)
print("📊 VALIDAÇÃO FINAL - V2.5.3")
print("=" * 70)
print(f"\n✅ Total de registros: {total}")
print(f"📋 Com número de ordem: {com_ordem}")
print(f"❌ Rejeitados: {rejeitados}")
print(f"⚠️  Falsos rejeitados: {falsos}")

if falsos > 0:
    print(f"\n🔴 ATENÇÃO: {falsos} casos com número de ordem marcados como rejeitados!")
    print("   Isso indica que a lógica ainda precisa de ajustes.")
else:
    print(f"\n🎉 SUCESSO! Nenhum falso rejeitado detectado!")

# Taxa de sucesso
if com_ordem > 0:
    taxa = ((com_ordem - falsos) / com_ordem * 100)
    print(f"\n🎯 Taxa de correção: {taxa:.1f}%")

# ========== VALIDAÇÃO CAMPOS V2.5.3 ==========
print("\n" + "=" * 70)
print("📋 ANÁLISE DOS CAMPOS V2.5.3")
print("=" * 70)

cur.execute("""
SELECT
  COUNT(CASE WHEN saldo_final IS NOT NULL THEN 1 END) as com_saldo_final,
  COUNT(CASE WHEN saldo_final > 0 THEN 1 END) as saldo_final_positivo,
  COUNT(CASE WHEN obito = TRUE THEN 1 END) as com_obito,
  COUNT(CASE WHEN data_obito IS NOT NULL THEN 1 END) as com_data_obito,
  COUNT(CASE WHEN cpf_sucessor IS NOT NULL THEN 1 END) as com_cpf_sucessor,
  COUNT(CASE WHEN doenca_grave = TRUE THEN 1 END) as com_doenca_grave,
  COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as com_habilitacao,
  COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as com_preferencial,
  COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as com_cessao
FROM esaj_detalhe_processos;
""")

(saldo_final, saldo_pos, obito, data_obito, cpf_suces,
 doenca, habilitacao, prefer, cessao) = cur.fetchone()

print(f"\n💰 Saldo Final:")
print(f"   ✓ Preenchido: {saldo_final}/{total} ({saldo_final/total*100:.1f}%)")
print(f"   ✓ Saldo > 0: {saldo_pos}/{total} ({saldo_pos/total*100:.1f}%)")

print(f"\n🪦 Óbito e Sucessão:")
print(f"   ✓ Óbito detectado: {obito}")
print(f"   ✓ Data óbito preenchida: {data_obito}")
print(f"   ✓ CPF sucessor preenchido: {cpf_suces}")
print(f"   ✓ Habilitação herdeiros: {habilitacao}")

print(f"\n🏥 Condições Especiais:")
print(f"   ✓ Doença grave: {doenca}")
print(f"   ✓ Preferencial: {prefer}")

print(f"\n📄 Cessão de Crédito:")
print(f"   ✓ Cessão detectada: {cessao} (esperado: 0 - desativado em V2.5.3)")

# Alertas de qualidade
print("\n" + "=" * 70)
print("⚠️  ALERTAS DE QUALIDADE")
print("=" * 70)

if cessao > 0:
    print(f"\n🔴 CRÍTICO: {cessao} casos com cessão_credito=TRUE")
    print("   Cessão de crédito foi DESATIVADO em V2.5.3!")

if habilitacao > 0 and cpf_suces == 0:
    print(f"\n🟡 WARNING: {habilitacao} habilitações sem CPF sucessor")
    print("   Verificar lógica de extração de CPF sucessor")

if obito > 0 and data_obito == 0:
    print(f"\n🟡 WARNING: {obito} óbitos sem data")
    print("   Verificar lógica de extração de data de óbito")

conn.close()
PYEOF

echo ""

# ============================================================================
# ETAPA 6: RECALCULAR TAG IDOSO
# ============================================================================
echo "============================================================"
echo "📊 ETAPA 6: RECALCULAR TAG IDOSO"
echo "============================================================"
echo ""

cd "${PROJECT_ROOT}/2_ingestao"
"${VENV_PYTHON}" scripts/recalcular_idoso.py

echo ""
echo "============================================================"
echo "✅ PIPELINE COMPLETO V2.6.0 CONCLUÍDO!"
echo "============================================================"
echo ""
echo "📋 Próximos passos:"
echo "   1. Revisar logs de processamento em 1_parsing_PDF/outputs/${OUTPUT_NAME}/logs/"
echo "   2. Verificar casos de falsos rejeitados (se houver)"
echo "   3. Ajustar lógica se necessário"
echo "   4. Verificar alertas de qualidade V2.5.3"
echo ""
