# ❓ FAQ & Troubleshooting: Sistema OCR V3.0

**Versão:** V3.0  
**Última Atualização:** 02/11/2025

---

## 📋 Perguntas Frequentes

### Q1: Qual a diferença entre V2.5.1 e V3.0?

**A:** V3.0 adiciona exemplos explícitos de valores brasileiros no prompt LLM, aumentando a acurácia de 56% para 76.5% (+20.5%).

**Principais melhorias:**
- Exemplos explícitos: "R$ 73.431,66" → 73431.66
- Regras de verificação obrigatória
- Validação de sanidade de valores

### Q2: Por que usar Gemini + OpenAI (modo híbrido)?

**A:** 
- **Gemini:** Gratuito, contexto 1M tokens, sem chunking
- **OpenAI:** Fallback confiável, melhor para validação
- **Resultado:** 90% economia + mesma qualidade

### Q3: O que é "chunking" e quando é aplicado?

**A:** Chunking reduz o texto enviado ao LLM para evitar limites de contexto.

**Regras:**
- Se PDF >100 páginas SEM ANEXO II → primeiras 50 + últimas 50
- Se texto >200k chars → primeiras 30 + últimas 30
- Se Gemini disponível → SEM chunking (1M tokens!)

### Q4: Como funciona a detecção de ofícios rejeitados?

**A:** Ordem de verificação (prioridade):
1. TEM "PROCESSAMENTO COM INFORMAÇÃO"? → ACEITO ✅
2. TEM número de ordem? → ACEITO ✅
3. TEM "NOTA DE REJEIÇÃO"? → REJEITADO ❌
4. Nenhum dos acima? → ACEITO (benefício da dúvida) ✅

### Q5: Que dados estão ausentes em ofícios rejeitados?

**A:** 
- ❌ `numero_ordem` → SEMPRE null (nunca foi atribuído pelo DEPRE)
- ⚠️ Valores monetários podem estar parciais

### Q6: Como calcular acurácia?

**A:** 
```
Acurácia Perfeita = (Processos com diferença < R$ 1) / Total * 100
Taxa de Sucesso = (PERFEITOS + ACEITÁVEIS <1%) / Total * 100
```

**Tolerâncias:**
- PERFEITO: < R$ 1,00
- ACEITÁVEL: < 1%
- BAIXO: 1-10%
- CRÍTICO: > 10%

---

## 🔧 Problemas Comuns

### Erro 1: "ValidationError: valor_principal_liquido"

**Sintoma:**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error
valor_principal_liquido
  Input should be a valid number
```

**Causa:** LLM retornou string ao invés de number.

**Solução Automática:**
- V3.0 tem verificação de tipos
- Fallback para OpenAI se Gemini falhar

**Solução Manual:**
```python
# No prompt, reforçar:
# "TODOS valores monetários são NÚMEROS (type: number), NÃO strings"
```

### Erro 2: Valores truncados (R$ 88.994,41 → R$ 88,99)

**Sintoma:** Valores com ponto decimal sendo truncados.

**Causa:** LLM interpretou ponto como decimal (inglês) ao invés de milhares (português).

**Solução:** ✅ RESOLVIDO em V3.0 com exemplos explícitos no prompt.

**Verificação:**
```bash
# Executar validação
python scripts/validacao_completa.py

# Verificar caso específico
grep "88.994" test_data/validacao_v3_final.csv
```

### Erro 3: "ANEXO II não encontrado"

**Sintoma:**
```
⚠️ ANEXO II não encontrado
```

**Causa:** 
- PDF sem ANEXO II (possível rejeição)
- ANEXO II em formato não padrão

**Solução:**
1. Verificar se ofício foi rejeitado (normal não ter ANEXO II)
2. Se aceito, verificar manualmente o PDF
3. Adicionar keywords alternativas no `detector_anexo.py`

### Erro 4: "Ofício rejeitado mas tem valores"

**Sintoma:** Ofício marcado como rejeitado mas `valor_*` não é null.

**Causa:** Valores podem estar no corpo do ofício antes da rejeição.

**Solução:** ✅ Comportamento esperado. LLM extrai o que encontrar.

### Erro 5: Inversão líquido/bruto

**Sintoma:**
```
valor_principal_liquido: 190.221,42
valor_principal_bruto: 311.369,53
Mas líquido > bruto!
```

**Causa:** LLM inverteu os campos.

**Solução:** V3.0 tem regra no prompt:
```
3. Líquido ≤ Bruto (se líquido > bruto, INVERTEU OS CAMPOS!)
```

**Verificação Manual:**
```python
if dados['valor_principal_liquido'] > dados['valor_principal_bruto']:
    # Inverter
    dados['valor_principal_liquido'], dados['valor_principal_bruto'] = \
        dados['valor_principal_bruto'], dados['valor_principal_liquido']
```

### Erro 6: "Gemini quota exceeded"

**Sintoma:**
```
⚠️ Gemini falhou: 429 quota exceeded
```

**Causa:** Limite de requests do Gemini atingido.

**Solução:** ✅ Automático - sistema faz fallback para OpenAI.

**Prevenção:**
```python
# Adicionar delay entre requests
import time
time.sleep(1)  # 1 segundo entre PDFs
```

### Erro 7: PDF muito grande (>300 páginas)

**Sintoma:** Valores incorretos em PDFs enormes.

**Causa:** Chunking agressivo perde contexto.

**Solução Atual:**
- Chunking: primeiras 30 + últimas 30 páginas
- Mantém ANEXO II e PROCESSAMENTO

**Solução Recomendada:**
- Usar Gemini (1M tokens, sem chunking)
- Adicionar `GOOGLE_API_KEY` no `.env`

### Erro 8: "psycopg2.OperationalError: connection failed"

**Sintoma:**
```
psycopg2.OperationalError: connection to server on socket failed
```

**Causa:** PostgreSQL não está rodando ou credenciais incorretas.

**Solução:**
```bash
# Verificar status
sudo systemctl status postgresql

# Iniciar
sudo systemctl start postgresql

# Testar conexão
psql -U postgres -d revisa_db -c "SELECT 1"

# Verificar .env
cat .env | grep DB_
```

---

## 📊 Debugging

### Habilitar Logs Detalhados

```python
# No início do script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verificar Prompt Enviado ao LLM

```python
# Salvar prompt em arquivo
with open('prompt_debug.txt', 'w') as f:
    f.write(prompt)
```

### Testar PDF Específico

```python
from app.processador import ProcessadorOficio

processador = ProcessadorOficio(openai_api_key="...", db_config={...})
resultado = processador.processar_arquivo(
    pdf_path="test_data/Precatório-RAF.pdf",
    cpf_numerico="27308157830"
)
print(resultado)
```

### Comparar Valores Extraídos

```bash
# Executar validação
python scripts/validacao_completa.py

# Ver discrepâncias
cat test_data/discrepancias_v3_final.json | jq '.[] | select(.diferenca > 100)'
```

---

## 🔍 Diagnóstico Rápido

### Checklist de Problemas

- [ ] API Keys válidas?
- [ ] PostgreSQL rodando?
- [ ] Ambiente virtual ativado?
- [ ] Dependências atualizadas?
- [ ] PDF acessível?
- [ ] CPF correto (11 dígitos)?
- [ ] Logs sem erros críticos?

### Comando de Diagnóstico

```bash
# Testar tudo de uma vez
cd scripts/
python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env')

print('✓ OpenAI API Key:', 'OK' if os.getenv('OPENAI_API_KEY') else '❌ FALTA')
print('✓ Gemini API Key:', 'OK' if os.getenv('GOOGLE_API_KEY') else '⚠️ Opcional')
print('✓ DB Host:', os.getenv('DB_HOST'))
print('✓ DB Name:', os.getenv('DB_NAME'))

from app.processador import ProcessadorOficio
print('✓ Processador: OK')
"
```

---

## 📞 Suporte

### Documentação Adicional

- [`DOCUMENTACAO_TECNICA_V3.md`](DOCUMENTACAO_TECNICA_V3.md) - Pipeline completo
- [`GUIA_VISUAL_PIPELINE.md`](GUIA_VISUAL_PIPELINE.md) - Diagramas
- [`GUIA_INSTALACAO.md`](GUIA_INSTALACAO.md) - Setup

### Relatórios de Validação

- [`../relatorios_validacao/RELATORIO_FINAL_V3.md`](../relatorios_validacao/RELATORIO_FINAL_V3.md)
- [`../relatorios_validacao/ANALISE_ACURACIA.md`](../relatorios_validacao/ANALISE_ACURACIA.md)

---

**Última Atualização:** 02/11/2025  
**Versão:** V3.0

