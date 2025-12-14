#!/bin/bash

# Script de teste em batch para o workflow CPF_batch_processing
# Faz chamadas cURL para cada CPF da lista

WEBHOOK_URL="https://n8n.srv987902.hstgr.cloud/webhook/cpf-batch-processing"

# Lista de CPFs extraídos
CPFS=(
  "03736870876"
  "07692595887"
  "08212993876"
  "10582304849"
  "10773800891"
  "11147105804"
  "13725004803"
  "16313887891"
  "28455260831"
  "36576414838"
  "57629080891"
  "93968396804"
)

echo "=========================================="
echo "  Batch Test - CPF_batch_processing"
echo "  Total de CPFs: ${#CPFS[@]}"
echo "=========================================="
echo ""

# Contador
COUNT=0
SUCCESS=0
FAILED=0

for CPF in "${CPFS[@]}"; do
  COUNT=$((COUNT + 1))
  echo "[$COUNT/${#CPFS[@]}] Processando CPF: $CPF"
  echo "-------------------------------------------"
  
  # Fazer a chamada cURL
  RESPONSE=$(curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"cpf\": \"$CPF\"}")
  
  # Verificar se teve sucesso
  if echo "$RESPONSE" | grep -q '"success":true'; then
    SUCCESS=$((SUCCESS + 1))
    NOME=$(echo "$RESPONSE" | grep -o '"nome":"[^"]*"' | cut -d'"' -f4)
    TOTAL=$(echo "$RESPONSE" | grep -o '"total_processos":[0-9]*' | cut -d':' -f2)
    echo "✅ Sucesso!"
    echo "   Nome: $NOME"
    echo "   Processos: $TOTAL"
  else
    FAILED=$((FAILED + 1))
    echo "❌ Falha!"
    echo "   Resposta: $RESPONSE"
  fi
  
  echo ""
  
  # Aguardar 2 segundos entre requisições para não sobrecarregar
  if [ $COUNT -lt ${#CPFS[@]} ]; then
    echo "Aguardando 2 segundos..."
    sleep 2
  fi
done

echo "=========================================="
echo "  RESUMO"
echo "=========================================="
echo "  Total processados: $COUNT"
echo "  Sucesso: $SUCCESS"
echo "  Falhas: $FAILED"
echo "=========================================="
