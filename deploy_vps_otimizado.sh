#!/bin/bash
# Script de Deploy Otimizado - Sistema OCR Ofícios Requisitórios TJSP
# Baseado na experiência real de deploy bem-sucedido na VPS Hostinger

set -e

# Configurações da VPS
VPS_HOST="srv987902.hstgr.cloud"
VPS_USER="root"
VPS_PASS="R3v1s@2025"
REPO_URL="https://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@github.com/revisaprecatorio/ocr-oficios-tjsp.git"
PROJECT_DIR="ocr-oficios-tjsp"
API_PROJECTS_DIR="/root/api_projects"

echo "🚀 DEPLOY OTIMIZADO - Sistema OCR Ofícios Requisitórios TJSP"
echo "=========================================================="

# Função para executar comandos na VPS
run_vps_command() {
    sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$1"
}

# Função para copiar arquivos para VPS
copy_to_vps() {
    sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no "$1" "$VPS_USER@$VPS_HOST:$2"
}

echo "📋 Verificando conexão com VPS..."
run_vps_command "echo '✅ Conexão estabelecida com sucesso!'"

echo "📁 Criando estrutura organizada..."
run_vps_command "mkdir -p $API_PROJECTS_DIR"

echo "🔄 Atualizando sistema (opcional)..."
run_vps_command "apt update -qq"

echo "🐳 Verificando Docker..."
run_vps_command "
    if ! command -v docker &> /dev/null; then
        echo 'Instalando Docker...'
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl start docker
        systemctl enable docker
    else
        echo '✅ Docker já instalado'
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo 'Instalando Docker Compose...'
        curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    else
        echo '✅ Docker Compose já instalado'
    fi
"

echo "📂 Clonando/atualizando repositório..."
run_vps_command "
    cd $API_PROJECTS_DIR
    
    if [ -d \"$PROJECT_DIR\" ]; then
        echo 'Atualizando repositório existente...'
        cd $PROJECT_DIR
        git pull origin main
    else
        echo 'Clonando repositório...'
        git clone $REPO_URL
        cd $PROJECT_DIR
    fi
    
    echo '✅ Repositório atualizado'
"

echo "⚙️ Configurando variáveis de ambiente..."
# Criar arquivo .env na VPS com configurações reais
cat > /tmp/.env << 'EOF'
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

copy_to_vps "/tmp/.env" "$API_PROJECTS_DIR/$PROJECT_DIR/.env"

echo "🌐 Configurando rede Traefik..."
run_vps_command "
    cd $API_PROJECTS_DIR/$PROJECT_DIR
    
    # Criar rede Traefik se não existir
    if ! docker network ls | grep -q traefik; then
        docker network create traefik
        echo '✅ Rede Traefik criada'
    else
        echo '✅ Rede Traefik já existe'
    fi
"

echo "🚀 Fazendo deploy com Docker Compose..."
run_vps_command "
    cd $API_PROJECTS_DIR/$PROJECT_DIR
    
    # Parar containers existentes
    docker compose down || true
    
    # Deploy principal (usar docker compose, não docker-compose)
    docker compose up -d --build
    
    # Aguardar inicialização
    echo 'Aguardando inicialização...'
    sleep 30
    
    # Verificar status
    docker compose ps
"

echo "🔍 Testando serviços..."
run_vps_command "
    cd $API_PROJECTS_DIR/$PROJECT_DIR
    
    # Test health check interno
    echo 'Testando health check interno...'
    docker compose exec -T ocr-app curl -f http://localhost:8000/health || echo 'Health check interno falhou'
    
    # Verificar logs
    echo 'Últimas linhas dos logs:'
    docker compose logs --tail=10 ocr-app
"

echo "📊 Status final do deploy:"
run_vps_command "
    cd $API_PROJECTS_DIR/$PROJECT_DIR
    
    echo '=== STATUS DOS CONTAINERS ==='
    docker compose ps
    
    echo '=== NETWORKS ==='
    docker network ls | grep traefik
    
    echo '=== HEALTH CHECK EXTERNO ==='
    curl -s http://localhost:8000/health | head -3 || echo 'Serviço não acessível externamente'
"

echo "
🎉 DEPLOY OTIMIZADO CONCLUÍDO!

📊 ACESSO AO SISTEMA:
🔗 Health Check: http://srv987902.hstgr.cloud:8000/health
🔗 Status: http://srv987902.hstgr.cloud:8000/status
🔗 API Docs: http://srv987902.hstgr.cloud:8000/docs
🔗 Interface: http://srv987902.hstgr.cloud:8000/

📋 COMANDOS ÚTEIS:
ssh root@srv987902.hstgr.cloud
cd $API_PROJECTS_DIR/$PROJECT_DIR
docker compose ps
docker compose logs -f ocr-app

✅ Sistema deployado com sucesso na VPS!
"
