#!/bin/bash
# Script para executar Streamlit com caminho correto

# Ir para o diretório correto
cd "$(dirname "$0")"

echo "📍 Diretório atual: $(pwd)"
echo "🔍 Verificando arquivo..."

if [ -f "app/streamlit_app.py" ]; then
    echo "✅ Arquivo encontrado: app/streamlit_app.py"
    echo ""
    echo "🚀 Iniciando Streamlit..."
    echo ""
    streamlit run app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0
else
    echo "❌ Erro: app/streamlit_app.py não encontrado!"
    echo "   Diretório atual: $(pwd)"
    echo "   Conteúdo:"
    ls -la
    exit 1
fi
