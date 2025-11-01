#!/bin/bash
# Script de monitoramento do processamento

LOG_FILE="../test_data/validacao_completa_full.log"

echo "=================================================="
echo "MONITOR DE PROGRESSO - Validação Completa"
echo "=================================================="
echo ""

# Contar processos
total=$(grep -c "^\[" "$LOG_FILE" 2>/dev/null || echo "0")
sucesso=$(grep -c "✅ Processamento V2 concluído com sucesso!" "$LOG_FILE" 2>/dev/null || echo "0")
discrepancias=$(grep -c "🚨 DISCREPÂNCIA ENCONTRADA" "$LOG_FILE" 2>/dev/null || echo "0")
perfeitos=$(grep -c "✓ Valores corretos" "$LOG_FILE" 2>/dev/null || echo "0")

echo "📊 ESTATÍSTICAS:"
echo "  Total de processos iniciados: $total"
echo "  Processamentos concluídos: $sucesso"
echo "  Valores perfeitos: $perfeitos"
echo "  Discrepâncias encontradas: $discrepancias"
echo ""

# Taxa de progresso
if [ "$total" -gt 0 ]; then
    progresso=$((sucesso * 100 / total))
    echo "  Progresso: $progresso% ($sucesso/$total)"
else
    echo "  Progresso: Iniciando..."
fi

echo ""
echo "=================================================="
echo "ÚLTIMAS 15 LINHAS DO LOG:"
echo "=================================================="
tail -15 "$LOG_FILE"

