#!/bin/bash
# ============================================================================
# SCRIPT PARA PARAR TODOS OS SERVIÇOS NA VPS
# ============================================================================
# Execute este script NA VPS para parar todos os serviços
# Uso: ./stop_all_services.sh
# ============================================================================

echo "============================================================"
echo "🛑 PARANDO TODOS OS SERVIÇOS NA VPS"
echo "============================================================"
echo ""

# 1. Streamlit
echo "📦 1. Parando Streamlit..."
cd /root/ocr-oficios-tjsp/3_streamlit
docker-compose stop
echo "   ✅ Streamlit parado"
echo ""

# 2. OCR + PostgreSQL
echo "📦 2. Parando OCR API e PostgreSQL..."
cd /root/ocr-oficios-tjsp
docker-compose stop
echo "   ✅ OCR API e PostgreSQL parados"
echo ""

# 3. Traefik + n8n
echo "📦 3. Parando Traefik e n8n..."
cd /root
docker-compose stop
echo "   ✅ Traefik e n8n parados"
echo ""

# 4. Verificar status
echo "============================================================"
echo "📊 STATUS DOS SERVIÇOS"
echo "============================================================"
docker ps -a --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "============================================================"
echo "✅ TODOS OS SERVIÇOS PARADOS!"
echo "============================================================"
echo ""
echo "📋 Para reiniciar:"
echo "   ./start_all_services.sh"
echo ""
