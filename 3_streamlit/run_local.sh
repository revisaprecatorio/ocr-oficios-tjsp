#!/bin/bash
# ============================================================================
# Script para rodar Streamlit localmente para testes
# ============================================================================

set -e

echo "============================================================"
echo "🚀 INICIANDO STREAMLIT LOCAL"
echo "============================================================"
echo ""

# Verificar se .env existe
if [ ! -f ".env" ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "   Copie .env.example para .env e configure as credenciais"
    exit 1
fi

# Ativar venv se existir
if [ -d "../.venv" ]; then
    echo "📦 Ativando virtual environment..."
    source ../.venv/bin/activate
fi

# Verificar se streamlit está instalado
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit não encontrado!"
    echo "   Instale com: pip install streamlit"
    exit 1
fi

echo "✅ Ambiente configurado"
echo ""
echo "🌐 Abrindo Streamlit em: http://localhost:8501"
echo ""
echo "💡 Para parar o servidor: Ctrl+C"
echo ""
echo "============================================================"
echo ""

# Rodar streamlit
cd app
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
