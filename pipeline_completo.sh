#!/bin/bash
# ============================================================================
# PIPELINE COMPLETO DE PONTA A PONTA
# ============================================================================
# Este script executa todo o pipeline:
# 1. Limpa JSONs antigos
# 2. Processa todos os PDFs
# 3. Importa JSONs para PostgreSQL (VPS)
# 4. Valida resultados
# ============================================================================

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo -e "${BLUE}🚀 PIPELINE COMPLETO - INÍCIO${NC}"
echo "============================================================"
echo ""

# ============================================================================
# ETAPA 1: LIMPAR OUTPUTS ANTIGOS
# ============================================================================
echo -e "${YELLOW}📁 ETAPA 1: Limpando JSONs antigos...${NC}"
cd 1_parsing_PDF

# Limpar pasta json/
if [ -d "outputs/json" ]; then
    rm -f outputs/json/*.json
    echo "   ✅ Pasta outputs/json/ limpa"
fi

# Limpar pastas lote_*
for dir in outputs/lote_*; do
    if [ -d "$dir" ]; then
        rm -f "$dir"/*.json
        echo "   ✅ Pasta $dir limpa"
    fi
done

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

# Ativar venv e processar
source ../.venv/bin/activate
python processar_lotes_v2.py

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

# Copiar todos os JSONs dos lotes para json/
find outputs/lote_* -name "*.json" -type f -exec cp {} outputs/json/ \; 2>/dev/null || true

total_jsons=$(ls outputs/json/*.json 2>/dev/null | wc -l | tr -d ' ')
echo "   ✅ $total_jsons JSONs copiados para outputs/json/"
echo ""

# ============================================================================
# ETAPA 4: IMPORTAR PARA POSTGRESQL (VPS)
# ============================================================================
echo -e "${YELLOW}💾 ETAPA 4: Importando para PostgreSQL (VPS)...${NC}"
echo ""

cd ../2_ingestao
source ../.venv/bin/activate

python scripts/ingest_all_jsons.py \
  --input ../1_parsing_PDF/outputs/json \
  --db-host 72.60.62.124 \
  --db-port 5432 \
  --db-name n8n \
  --db-user admin

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Erro na importação para PostgreSQL!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Importação concluída!${NC}"
echo ""

# ============================================================================
# ETAPA 5: VALIDAR RESULTADOS
# ============================================================================
echo -e "${YELLOW}🔍 ETAPA 5: Validando resultados...${NC}"
echo ""

python3 << 'PYEOF'
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
print("📊 VALIDAÇÃO FINAL")
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

conn.close()
PYEOF

echo ""

# ============================================================================
# RESUMO FINAL
# ============================================================================
echo "============================================================"
echo -e "${GREEN}✅ PIPELINE COMPLETO - CONCLUÍDO${NC}"
echo "============================================================"
echo ""
echo "📋 Próximos passos:"
echo "   1. Revisar logs de processamento"
echo "   2. Verificar casos de falsos rejeitados (se houver)"
echo "   3. Ajustar lógica se necessário"
echo ""
