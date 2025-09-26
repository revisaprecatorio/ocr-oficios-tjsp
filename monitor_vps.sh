#!/bin/bash
# Script de Monitoramento da VPS
# Execute: ./monitor_vps.sh

VPS_HOST="srv987902.hstgr.cloud"
VPS_USER="root"
VPS_PASS="R3v1s@2025"
PROJECT_DIR="ocr-oficios-tjsp"

# Função para executar comandos na VPS
run_vps_command() {
    sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$1"
}

echo "🔍 MONITORAMENTO DO SISTEMA OCR - VPS"
echo "======================================"

echo "📊 STATUS DOS CONTAINERS:"
run_vps_command "cd $PROJECT_DIR && docker-compose -f deploy/docker-compose.prod.yml ps"

echo ""
echo "🔥 HEALTH CHECK:"
run_vps_command "curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health"

echo ""
echo "📈 STATUS DETALHADO:"
run_vps_command "curl -s http://localhost:8000/status | jq . 2>/dev/null || curl -s http://localhost:8000/status"

echo ""
echo "📝 LOGS RECENTES (últimas 20 linhas):"
run_vps_command "cd $PROJECT_DIR && docker-compose -f deploy/docker-compose.prod.yml logs --tail=20 ocr-app"

echo ""
echo "💾 USO DE DISCO:"
run_vps_command "df -h /"

echo ""
echo "🐳 IMAGENS DOCKER:"
run_vps_command "docker images | head -10"

echo ""
echo "🌐 NETWORKS:"
run_vps_command "docker network ls"

echo ""
echo "⚡ PROCESSOS PYTHON:"
run_vps_command "ps aux | grep python | head -5"

echo ""
echo "📊 RESUMO:"
echo "✅ Sistema OCR deployado na VPS"
echo "🔗 Acesso: http://srv987902.hstgr.cloud:8000"
echo "📋 Health: http://srv987902.hstgr.cloud:8000/health"
echo "📈 Status: http://srv987902.hstgr.cloud:8000/status"
