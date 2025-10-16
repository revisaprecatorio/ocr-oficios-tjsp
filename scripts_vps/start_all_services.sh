#!/bin/bash
# ============================================================================
# SCRIPT DE INICIALIZAÇÃO DE TODOS OS SERVIÇOS NA VPS
# ============================================================================
# Execute este script NA VPS para subir todos os serviços
# Uso: ./start_all_services.sh
# ============================================================================

set -e

echo "============================================================"
echo "🚀 INICIANDO TODOS OS SERVIÇOS NA VPS"
echo "============================================================"
echo ""

# 1. Traefik + n8n
echo "📦 1. Subindo Traefik e n8n..."
cd /root
docker-compose up -d
echo "   ✅ Traefik e n8n iniciados"
echo ""

# Aguardar Traefik inicializar
sleep 3

# 2. OCR + PostgreSQL
echo "📦 2. Subindo OCR API e PostgreSQL..."
cd /root/ocr-oficios-tjsp
docker-compose up -d
echo "   ✅ OCR API e PostgreSQL iniciados"
echo ""

# Aguardar PostgreSQL inicializar
sleep 3

# 3. Streamlit
echo "📦 3. Subindo Streamlit..."
cd /root/ocr-oficios-tjsp/3_streamlit
docker-compose up -d
echo "   ✅ Streamlit iniciado"
echo ""

# Aguardar todos inicializarem
sleep 5

# 4. Verificar status
echo "============================================================"
echo "📊 STATUS DOS SERVIÇOS"
echo "============================================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 5. Verificar saúde dos serviços
echo "============================================================"
echo "🔍 VERIFICAÇÃO DE SAÚDE"
echo "============================================================"

# Traefik
if curl -s -o /dev/null -w "%{http_code}" http://localhost:80 | grep -q "404\|200"; then
    echo "✅ Traefik: OK (porta 80)"
else
    echo "❌ Traefik: ERRO"
fi

# n8n
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5678 | grep -q "200"; then
    echo "✅ n8n: OK (porta 5678)"
else
    echo "❌ n8n: ERRO"
fi

# Streamlit
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; then
    echo "✅ Streamlit: OK (porta 8501)"
else
    echo "❌ Streamlit: ERRO"
fi

# PostgreSQL
if docker exec ocr-oficios-tjsp-postgres-1 pg_isready -U admin > /dev/null 2>&1; then
    echo "✅ PostgreSQL: OK"
else
    echo "❌ PostgreSQL: ERRO"
fi

echo ""

echo "============================================================"
echo "✅ TODOS OS SERVIÇOS INICIADOS!"
echo "============================================================"
echo ""
echo "🌐 URLs Disponíveis:"
echo "   - n8n:       https://n8n.srv987902.hstgr.cloud"
echo "   - Streamlit: http://72.60.62.124:8501"
echo ""
echo "📋 Comandos úteis:"
echo "   docker ps                    # Ver todos os containers"
echo "   docker logs -f <container>   # Ver logs em tempo real"
echo "   docker stats                 # Ver uso de recursos"
echo ""
