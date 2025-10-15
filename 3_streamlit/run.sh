#!/bin/bash
# Script para executar a interface Streamlit

set -e

echo "=========================================="
echo "📊 INICIANDO INTERFACE STREAMLIT"
echo "=========================================="

# Verificar se está no diretório correto
if [ ! -f "app/streamlit_app.py" ]; then
    echo "❌ Erro: Execute este script de dentro do diretório 3_streamlit/"
    exit 1
fi

# Verificar se o virtual environment está ativado
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment não ativado"
    echo "   Ativando .venv do projeto..."
    
    if [ -f "../.venv/bin/activate" ]; then
        source ../.venv/bin/activate
        echo "   ✅ Virtual environment ativado"
    else
        echo "   ❌ Erro: .venv não encontrado"
        echo "   Execute: python3 -m venv ../.venv"
        exit 1
    fi
fi

# Verificar se o .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado"
    echo "   Copiando .env do projeto..."
    cp ../.env .
    echo "   ✅ .env copiado"
fi

# Verificar dependências
echo ""
echo "🔍 Verificando dependências..."
python3 -c "import streamlit" 2>/dev/null || {
    echo "   ⚠️  Streamlit não instalado"
    echo "   Instalando dependências..."
    pip install -r requirements.txt
}

# Executar Streamlit
echo ""
echo "=========================================="
echo "🚀 INICIANDO STREAMLIT"
echo "=========================================="
echo ""
echo "📍 URL: http://localhost:8501"
echo "⌨️  Pressione Ctrl+C para parar"
echo ""

streamlit run app/streamlit_app.py --server.port=8501
