#!/bin/bash
while true; do
    clear
    echo "🔄 VALIDAÇÃO V3.0 EM ANDAMENTO"
    echo "================================"
    echo ""
    echo "📈 Progresso:"
    grep -E "Processando:|completados" 8_erro_parsing-valor/validacao_v3_completa_*.log 2>/dev/null | tail -5
    echo ""
    echo "⏱️  $(date '+%H:%M:%S') - Atualizando a cada 30s..."
    echo "   Pressione Ctrl+C para parar o monitoramento (processo continua)"
    sleep 30
done
