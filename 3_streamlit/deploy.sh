#!/bin/bash
# Script de deploy automático para Streamlit em Docker

set -e

echo "=========================================="
echo "🚀 DEPLOY STREAMLIT - OFÍCIOS TJSP"
echo "=========================================="

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erro: Execute este script de dentro do diretório 3_streamlit/"
    exit 1
fi

# Verificar se o .env existe
if [ ! -f ".env" ]; then
    echo "⚠️  Arquivo .env não encontrado"
    echo "   Copiando .env.example para .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  ATENÇÃO: Edite o arquivo .env com as credenciais corretas!"
    echo "   1. Gere o hash da senha: htpasswd -nb revisaprecatorio 'R3v1s@2025'"
    echo "   2. Edite .env e substitua BASICAUTH_HASH"
    echo "   3. Execute este script novamente"
    exit 1
fi

# Verificar se a pasta data existe
if [ ! -d "data/consultas" ]; then
    echo "⚠️  Pasta data/consultas não encontrada"
    echo "   Criando estrutura de diretórios..."
    mkdir -p data/consultas
    echo ""
    echo "⚠️  ATENÇÃO: Faça upload dos PDFs para data/consultas/"
    echo "   Comando: rsync -avz --progress LOCAL/data/consultas/ root@srv987902.hstgr.cloud:/root/ocr-oficios-tjsp/3_streamlit/data/consultas/"
fi

echo ""
echo "🔍 Verificando configuração..."
echo ""

# Verificar se o Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker não está rodando"
    exit 1
fi

# Verificar se a rede Traefik existe
if ! docker network ls | grep -q traefik; then
    echo "❌ Rede Traefik não encontrada"
    echo "   Criando rede Traefik..."
    docker network create traefik
fi

echo "✅ Configuração OK"
echo ""
echo "🏗️  Fazendo build da imagem Docker..."
docker-compose build

echo ""
echo "🚀 Iniciando container..."
docker-compose up -d

echo ""
echo "⏳ Aguardando container inicializar..."
sleep 5

echo ""
echo "📊 Status do container:"
docker-compose ps

echo ""
echo "📝 Últimas linhas do log:"
docker-compose logs --tail=20

echo ""
echo "=========================================="
echo "✅ DEPLOY CONCLUÍDO!"
echo "=========================================="
echo ""
echo "🌐 Acesse: http://72.60.62.124:8501"
echo "🔐 Usuário: revisaprecatorio"
echo "🔐 Senha: R3v1s@2025"
echo ""
echo "📝 Comandos úteis:"
echo "   docker-compose logs -f          # Ver logs em tempo real"
echo "   docker-compose restart          # Reiniciar container"
echo "   docker-compose stop             # Parar container"
echo "   docker-compose down             # Parar e remover container"
echo ""
