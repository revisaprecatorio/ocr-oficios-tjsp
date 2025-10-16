#!/bin/bash
# ============================================================================
# SCRIPT DE DEPLOY/UPDATE - Streamlit VPS
# ============================================================================
# Execute este script NA VPS via SSH
# ============================================================================

set -e  # Parar em caso de erro

echo "============================================================"
echo "🚀 ATUALIZANDO STREAMLIT NA VPS"
echo "============================================================"
echo ""

# 1. Pull do GitHub
echo "📥 1. Baixando alterações do GitHub..."
cd /root/3_OCR
git pull origin main
echo "   ✅ Pull concluído"
echo ""

# 2. Parar container
echo "🛑 2. Parando container atual..."
docker stop oficios-streamlit || true
echo "   ✅ Container parado"
echo ""

# 3. Remover container
echo "🗑️  3. Removendo container antigo..."
docker rm oficios-streamlit || true
echo "   ✅ Container removido"
echo ""

# 4. Rebuild
echo "🔨 4. Reconstruindo imagem..."
cd 3_streamlit
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
docker logs --tail 20 oficios-streamlit
echo ""

echo "============================================================"
echo "✅ DEPLOY CONCLUÍDO!"
echo "============================================================"
echo ""
echo "🌐 URL: http://72.60.62.124:8501"
echo ""
echo "📋 Para ver logs em tempo real:"
echo "   docker logs -f oficios-streamlit"
echo ""
