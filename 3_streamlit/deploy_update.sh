#!/bin/bash
# ============================================================================
# SCRIPT DE DEPLOY/UPDATE - Streamlit VPS
# ============================================================================
# Execute este script NA VPS via SSH
# Versão: 2.2.0
# Data: 16/10/2025
# ============================================================================

set -e  # Parar em caso de erro

# Configurações
PROJECT_DIR="/root/ocr-oficios-tjsp"
STREAMLIT_DIR="${PROJECT_DIR}/3_streamlit"
CONTAINER_NAME="oficios-streamlit"

echo "============================================================"
echo "🚀 ATUALIZANDO STREAMLIT NA VPS - v2.2.0"
echo "============================================================"
echo ""
echo "📁 Diretório: ${PROJECT_DIR}"
echo "🐳 Container: ${CONTAINER_NAME}"
echo ""

# 1. Pull do GitHub
echo "📥 1. Baixando alterações do GitHub..."
cd ${PROJECT_DIR}
git pull origin main
echo "   ✅ Pull concluído"
echo ""

# 2. Parar container
echo "🛑 2. Parando container atual..."
docker stop ${CONTAINER_NAME} || true
echo "   ✅ Container parado"
echo ""

# 3. Remover container
echo "🗑️  3. Removendo container antigo..."
docker rm ${CONTAINER_NAME} || true
echo "   ✅ Container removido"
echo ""

# 4. Rebuild
echo "🔨 4. Reconstruindo imagem..."
cd ${STREAMLIT_DIR}
docker-compose build --no-cache
echo "   ✅ Imagem reconstruída"
echo ""

# 5. Subir container
echo "🚀 5. Subindo novo container..."
docker-compose up -d
echo "   ✅ Container iniciado"
echo ""

# 6. Aguardar healthcheck
echo "⏳ 6. Aguardando healthcheck..."
sleep 10
echo ""

# 7. Verificar status
echo "🔍 7. Verificando status..."
docker ps | grep streamlit
echo ""

# 8. Mostrar logs
echo "📋 8. Últimas linhas do log:"
docker logs --tail 20 ${CONTAINER_NAME}
echo ""

echo "============================================================"
echo "✅ DEPLOY CONCLUÍDO - v2.2.0!"
echo "============================================================"
echo ""
echo "🌐 URL: http://72.60.62.124:8501"
echo ""
echo "📋 Comandos úteis:"
echo "   docker logs -f ${CONTAINER_NAME}        # Ver logs em tempo real"
echo "   docker ps | grep streamlit              # Verificar status"
echo "   docker restart ${CONTAINER_NAME}        # Reiniciar container"
echo ""
echo "📊 Novidades v2.2.0:"
echo "   ✅ 49 colunas disponíveis (incluindo data_nascimento)"
echo "   ✅ 0 falsos rejeitados (100% precisão)"
echo "   ✅ Pipeline completo automatizado"
echo ""
