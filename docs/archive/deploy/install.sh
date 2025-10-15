#!/bin/bash

# Sistema OCR Ofícios Requisitórios TJSP - Script de Instalação Ubuntu
# Compatível com VPS Hostinger Ubuntu

set -e

echo "🚀 Iniciando instalação do Sistema OCR - Ofícios Requisitórios TJSP"
echo "============================================================"

# Verificar se está rodando como root ou com sudo
if [[ $EUID -eq 0 ]]; then
   echo "❌ Este script não deve ser executado como root"
   echo "   Execute: bash deploy/install.sh"
   exit 1
fi

# Verificar sistema operacional
if [[ ! -f /etc/os-release ]]; then
    echo "❌ Sistema operacional não suportado"
    exit 1
fi

source /etc/os-release
if [[ $ID != "ubuntu" ]]; then
    echo "❌ Este script é específico para Ubuntu"
    exit 1
fi

echo "✅ Sistema: Ubuntu $VERSION_ID"

# Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    curl \
    wget \
    unzip \
    build-essential \
    postgresql-client \
    nginx \
    supervisor

# Verificar se Python 3.11 está disponível
if ! command -v python3.11 &> /dev/null; then
    echo "📦 Instalando Python 3.11..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt-get update -y
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# Criar diretório do projeto
PROJECT_DIR="/opt/ocr-oficios-tjsp"
echo "📁 Criando diretório do projeto: $PROJECT_DIR"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Clonar repositório se não existir
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "📥 Clonando repositório..."
    git clone https://github.com/revisaprecatorio/ocr-oficios-tjsp.git $PROJECT_DIR
    cd $PROJECT_DIR
else
    echo "🔄 Atualizando repositório..."
    cd $PROJECT_DIR
    git pull origin main
fi

# Criar ambiente virtual Python
echo "🐍 Criando ambiente virtual Python..."
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependências Python
echo "📦 Instalando dependências Python..."
pip install --upgrade pip
pip install -r requirements.txt

# Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo "⚙️ Criando arquivo .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: Configure o arquivo .env com suas credenciais:"
    echo "   nano $PROJECT_DIR/.env"
    echo ""
fi

# Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p Processos logs

# Configurar permissões
echo "🔐 Configurando permissões..."
chmod +x run_sistema.py
chmod +x deploy/*.sh

# Criar serviço systemd
echo "🔧 Criando serviço systemd..."
sudo tee /etc/systemd/system/ocr-oficios.service > /dev/null <<EOF
[Unit]
Description=Sistema OCR Ofícios Requisitórios TJSP
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/.venv/bin
ExecStart=$PROJECT_DIR/.venv/bin/python run_sistema.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recarregar systemd
sudo systemctl daemon-reload

echo ""
echo "✅ Instalação concluída com sucesso!"
echo "============================================================"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo ""
echo "1. Configure o arquivo .env:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Configure o banco PostgreSQL (se não estiver usando VPS existente):"
echo "   sudo -u postgres psql -c \"CREATE DATABASE oficios_tjsp;\""
echo "   sudo -u postgres psql -d oficios_tjsp -f $PROJECT_DIR/schema.sql"
echo ""
echo "3. Teste a aplicação:"
echo "   cd $PROJECT_DIR"
echo "   source .venv/bin/activate"
echo "   python run_sistema.py"
echo ""
echo "4. Habilitar serviço automático (opcional):"
echo "   sudo systemctl enable ocr-oficios"
echo "   sudo systemctl start ocr-oficios"
echo ""
echo "5. Verificar logs:"
echo "   sudo systemctl status ocr-oficios"
echo "   tail -f $PROJECT_DIR/logs/ocr_oficios.log"
echo ""
echo "🎉 Sistema pronto para uso!"
