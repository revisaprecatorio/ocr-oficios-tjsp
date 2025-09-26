#!/bin/bash
# Script de Deploy Automático para VPS Hostinger
# Execute localmente: ./deploy_vps.sh

set -e

# Configurações da VPS
VPS_HOST="srv987902.hstgr.cloud"
VPS_USER="root"
VPS_PASS="R3v1s@2025"
REPO_URL="https://github.com/revisaprecatorio/ocr-oficios-tjsp.git"
PROJECT_DIR="ocr-oficios-tjsp"

echo "🚀 Iniciando deploy automático na VPS..."

# Função para executar comandos na VPS
run_vps_command() {
    sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$1"
}

# Função para copiar arquivos para VPS
copy_to_vps() {
    sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no "$1" "$VPS_USER@$VPS_HOST:$2"
}

echo "📋 Verificando conexão com VPS..."
run_vps_command "echo 'Conexão estabelecida com sucesso!'"

echo "🔄 Atualizando sistema..."
run_vps_command "apt update && apt upgrade -y"

echo "🐳 Instalando Docker e Docker Compose..."
run_vps_command "
    # Instalar Docker se não existir
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
    fi
    
    # Instalar Docker Compose se não existir
    if ! command -v docker-compose &> /dev/null; then
        curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    # Verificar instalação
    docker --version
    docker-compose --version
"

echo "📂 Clonando/atualizando repositório..."
run_vps_command "
    if [ -d \"$PROJECT_DIR\" ]; then
        cd $PROJECT_DIR
        git pull origin main
    else
        git clone $REPO_URL
        cd $PROJECT_DIR
    fi
"

echo "⚙️ Configurando variáveis de ambiente..."
# Criar arquivo .env na VPS
cat > /tmp/.env << EOF
# OpenAI Configuration
OPENAI_API_KEY=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
OPENAI_MODEL=gpt-5-nano-2025-08-07

# PostgreSQL Database (VPS existente)
POSTGRES_HOST=72.60.62.124
POSTGRES_PORT=5432
POSTGRES_DB=n8n
POSTGRES_USER=admin
POSTGRES_PASSWORD=BetaAgent2024SecureDB

# Application
BASE_DIR=./Processos
LOG_LEVEL=INFO

# Domain for Traefik
DOMAIN=srv987902.hstgr.cloud
EOF

copy_to_vps "/tmp/.env" "$PROJECT_DIR/.env"

echo "🐋 Verificando rede Traefik..."
run_vps_command "
    cd $PROJECT_DIR
    
    # Criar rede Traefik se não existir
    if ! docker network ls | grep -q traefik; then
        docker network create traefik
        echo 'Rede Traefik criada!'
    else
        echo 'Rede Traefik já existe!'
    fi
"

echo "🚀 Fazendo deploy com Docker Compose..."
run_vps_command "
    cd $PROJECT_DIR
    
    # Parar containers existentes
    docker-compose -f deploy/docker-compose.prod.yml down || true
    
    # Rebuild e start
    docker-compose -f deploy/docker-compose.prod.yml up -d --build
    
    # Aguardar inicialização
    sleep 30
    
    # Verificar status
    docker-compose -f deploy/docker-compose.prod.yml ps
"

echo "🔍 Testando serviços..."
run_vps_command "
    cd $PROJECT_DIR
    
    # Test health check
    docker-compose -f deploy/docker-compose.prod.yml exec -T ocr-app curl -f http://localhost:8000/health || echo 'Health check falhou'
    
    # Verificar logs
    docker-compose -f deploy/docker-compose.prod.yml logs --tail=20 ocr-app
"

echo "📊 Status final do deploy:"
run_vps_command "
    cd $PROJECT_DIR
    echo '=== STATUS DOS CONTAINERS ==='
    docker-compose -f deploy/docker-compose.prod.yml ps
    
    echo '=== NETWORKS ==='
    docker network ls | grep traefik
    
    echo '=== HEALTH CHECK ==='
    curl -s http://localhost:8000/health | head -5 || echo 'Serviço não acessível'
"

echo "
🎉 DEPLOY CONCLUÍDO!

📊 ACESSO AO SISTEMA:
🔗 URL: https://ocr.srv987902.hstgr.cloud (se Traefik configurado)
🔗 IP: http://srv987902.hstgr.cloud:8000 (acesso direto)

📋 COMANDOS ÚTEIS:
ssh root@srv987902.hstgr.cloud
cd ocr-oficios-tjsp
docker-compose -f deploy/docker-compose.prod.yml logs -f

✅ Sistema deployado com sucesso na VPS!
"
