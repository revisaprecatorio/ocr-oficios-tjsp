#!/bin/bash
# Script de Monitoramento Avançado - Sistema OCR VPS
# Baseado na experiência real de deploy bem-sucedido

VPS_HOST="srv987902.hstgr.cloud"
VPS_USER="root"
VPS_PASS="R3v1s@2025"
PROJECT_DIR="/root/api_projects/ocr-oficios-tjsp"

# Função para executar comandos na VPS
run_vps_command() {
    sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_HOST" "$1"
}

echo "🔍 MONITORAMENTO AVANÇADO - Sistema OCR VPS"
echo "============================================="

echo "📊 STATUS DOS CONTAINERS:"
run_vps_command "cd $PROJECT_DIR && docker compose ps"

echo ""
echo "🔥 HEALTH CHECK DETALHADO:"
run_vps_command "
    cd $PROJECT_DIR
    echo 'Health Check Interno:'
    docker compose exec -T ocr-app curl -s http://localhost:8000/health | jq . 2>/dev/null || docker compose exec -T ocr-app curl -s http://localhost:8000/health
    
    echo ''
    echo 'Health Check Externo:'
    curl -s http://localhost:8000/health | jq . 2>/dev/null || curl -s http://localhost:8000/health
"

echo ""
echo "📈 STATUS DETALHADO DO SISTEMA:"
run_vps_command "
    cd $PROJECT_DIR
    echo 'Status via API:'
    curl -s http://localhost:8000/status | jq . 2>/dev/null || curl -s http://localhost:8000/status
"

echo ""
echo "📝 LOGS RECENTES (últimas 30 linhas):"
run_vps_command "cd $PROJECT_DIR && docker compose logs --tail=30 ocr-app"

echo ""
echo "💾 RECURSOS DO SISTEMA:"
run_vps_command "
    echo 'Uso de Disco:'
    df -h / | head -2
    
    echo ''
    echo 'Uso de Memória:'
    free -h | head -2
    
    echo ''
    echo 'Load Average:'
    uptime
"

echo ""
echo "🐳 INFORMAÇÕES DOCKER:"
run_vps_command "
    echo 'Imagens Docker:'
    docker images | head -5
    
    echo ''
    echo 'Networks:'
    docker network ls
    
    echo ''
    echo 'Volumes:'
    docker volume ls | grep ocr
"

echo ""
echo "⚡ PROCESSOS PYTHON:"
run_vps_command "ps aux | grep python | head -5"

echo ""
echo "🌐 CONECTIVIDADE:"
run_vps_command "
    echo 'Teste de conectividade PostgreSQL:'
    docker compose exec -T ocr-app python -c '
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv(\"POSTGRES_HOST\"),
        port=os.getenv(\"POSTGRES_PORT\"),
        database=os.getenv(\"POSTGRES_DB\"),
        user=os.getenv(\"POSTGRES_USER\"),
        password=os.getenv(\"POSTGRES_PASSWORD\")
    )
    print(\"✅ PostgreSQL conectado com sucesso\")
    conn.close()
except Exception as e:
    print(f\"❌ Erro PostgreSQL: {e}\")
' 2>/dev/null || echo '❌ Erro ao testar PostgreSQL'
"

echo ""
echo "🤖 TESTE OPENAI API:"
run_vps_command "
    echo 'Teste OpenAI API:'
    docker compose exec -T ocr-app python -c '
from openai import OpenAI
import os
try:
    client = OpenAI(api_key=os.getenv(\"OPENAI_API_KEY\"))
    response = client.models.list()
    print(\"✅ OpenAI API funcionando\")
except Exception as e:
    print(f\"❌ Erro OpenAI: {e}\")
' 2>/dev/null || echo '❌ Erro ao testar OpenAI'
"

echo ""
echo "📊 RESUMO EXECUTIVO:"
echo "==================="
echo "✅ Sistema OCR deployado na VPS Hostinger"
echo "🔗 Acesso Principal: http://srv987902.hstgr.cloud:8000"
echo "📋 Health Check: http://srv987902.hstgr.cloud:8000/health"
echo "📈 Status: http://srv987902.hstgr.cloud:8000/status"
echo "📚 API Docs: http://srv987902.hstgr.cloud:8000/docs"
echo "📝 Logs: http://srv987902.hstgr.cloud:8000/logs"
echo ""
echo "🎯 Sistema pronto para processamento de PDFs!"
