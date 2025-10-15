#!/bin/bash

# Sistema OCR - Script de Atualização
# Para atualizar o sistema em produção

set -e

PROJECT_DIR="/opt/ocr-oficios-tjsp"

echo "🔄 Atualizando Sistema OCR - Ofícios Requisitórios TJSP"
echo "============================================================"

# Verificar se o diretório existe
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Projeto não encontrado em $PROJECT_DIR"
    echo "   Execute primeiro: bash deploy/install.sh"
    exit 1
fi

cd $PROJECT_DIR

# Parar serviço se estiver rodando
if systemctl is-active --quiet ocr-oficios; then
    echo "⏸️ Parando serviço..."
    sudo systemctl stop ocr-oficios
fi

# Fazer backup do .env atual
if [ -f .env ]; then
    echo "💾 Fazendo backup do .env..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Atualizar código
echo "📥 Atualizando código..."
git stash  # Salvar mudanças locais
git pull origin main
git stash pop 2>/dev/null || true  # Restaurar mudanças se houver

# Ativar ambiente virtual
echo "🐍 Ativando ambiente virtual..."
source .venv/bin/activate

# Atualizar dependências
echo "📦 Atualizando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Aplicar migrações de banco se necessário
if [ -f "migrations.sql" ]; then
    echo "🗄️ Aplicando migrações..."
    # Código para aplicar migrações aqui
fi

# Restartar serviço
if systemctl list-unit-files | grep -q ocr-oficios; then
    echo "🔄 Reiniciando serviço..."
    sudo systemctl start ocr-oficios
    sleep 2
    sudo systemctl status ocr-oficios --no-pager
fi

echo ""
echo "✅ Atualização concluída com sucesso!"
echo ""
echo "📋 Verificar logs:"
echo "   sudo systemctl status ocr-oficios"
echo "   tail -f logs/ocr_oficios.log"
