#!/bin/bash

# Monitor de progresso da validação V3.0
LOG_FILE="../test_data/validacao_v3_completa.log"

echo "📊 Monitor de Validação V3.0"
echo "════════════════════════════════════════"
echo ""

while true; do
    clear
    echo "📊 Monitor de Validação V3.0"
    echo "════════════════════════════════════════"
    echo ""
    
    # Contar processos processados
    PROCESSADOS=$(grep -c "Processando:" "$LOG_FILE" 2>/dev/null || echo "0")
    echo "✅ Processos processados: $PROCESSADOS / 51"
    
    # Contar sucessos
    SUCESSOS=$(grep -c "✅ Dados salvos no banco" "$LOG_FILE" 2>/dev/null || echo "0")
    echo "✅ Sucessos: $SUCESSOS"
    
    # Contar erros
    ERROS=$(grep -c "❌ Erro" "$LOG_FILE" 2>/dev/null || echo "0")
    echo "❌ Erros: $ERROS"
    
    echo ""
    echo "📋 Últimas 10 linhas:"
    echo "────────────────────────────────────────"
    tail -10 "$LOG_FILE" 2>/dev/null | grep -E "(Processando|✅|❌)" || echo "Aguardando dados..."
    
    echo ""
    echo "⏱️  Atualizado: $(date '+%H:%M:%S')"
    echo "Pressione Ctrl+C para sair"
    
    sleep 5
done

