# ✅ Checklist de Execução - Validação v1

**Data**: 13 de outubro de 2025  
**Objetivo**: Guia passo a passo para executar a validação

---

## 🎯 Pré-Requisitos

### Ambiente
```bash
# 1. Verificar Python
python --version
# Esperado: Python 3.11.x ou superior
```
- [ ] Python 3.11+ instalado

```bash
# 2. Ativar ambiente virtual
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR
source .venv/bin/activate
```
- [ ] Ambiente virtual ativado
- [ ] Prompt mostra `(.venv)`

```bash
# 3. Verificar dependências
pip list | grep -E "pymupdf|openai|pydantic"
```
- [ ] pymupdf ≥1.23.0
- [ ] openai ≥1.109.0
- [ ] pydantic ≥2.5.0

### Configuração (.env)

```bash
# 4. Verificar .env existe
ls -la .env
```
- [ ] Arquivo `.env` existe

```bash
# 5. Verificar variáveis
cat .env | grep -v "^#" | grep -v "^$"
```
- [ ] `OPENAI_API_KEY=sk-proj-...` (configurada)
- [ ] `OPENAI_MODEL=gpt-4o-mini` (configurada)
- [ ] `BASE_DIR=./data/consultas` (configurada)

### Dados

```bash
# 6. Verificar estrutura de PDFs
ls -R data/consultas/ | head -20
```
- [ ] Pasta `data/consultas/` existe
- [ ] Subpastas com CPFs (11 dígitos)
- [ ] PDFs com nome no formato CNJ

```bash
# 7. Contar PDFs disponíveis
find data/consultas -name "*.pdf" | wc -l
```
- [ ] Pelo menos 3 PDFs disponíveis

```bash
# 8. Verificar tamanho dos PDFs
find data/consultas -name "*.pdf" -exec du -h {} \; | sort -h | head -10
```
- [ ] PDFs com tamanho razoável (2-10 MB típico)
- [ ] Identificar PDFs muito grandes (>50 MB)

### Código

```bash
# 9. Verificar modelo no código
grep -n "gpt-4o-mini" app/processador.py
```
- [ ] Linha 42: `self.modelo_gpt = "gpt-4o-mini"`

```bash
# 10. Verificar AGENTS.md
grep "BASE_DIR" AGENTS.md
```
- [ ] `BASE_DIR=./data/consultas`

---

## 🚀 Execução Fase 1

### Preparação

```bash
# 11. Criar estrutura de output
mkdir -p _validation_v1/outputs/fase1_teste_unitario/{jsons,logs,anomalias}
```
- [ ] Diretórios criados

```bash
# 12. Verificar script executável
ls -la _validation_v1/scripts/validar_fase1.sh
```
- [ ] Permissão de execução (`-rwxr-xr-x`)

### Execução

```bash
# 13. Executar Fase 1
./_validation_v1/scripts/validar_fase1.sh
```
- [ ] Script iniciou sem erros
- [ ] Verificações de ambiente passaram
- [ ] Processamento iniciou

**Aguardar conclusão...**

### Durante a Execução

Abrir novo terminal e monitorar:

```bash
# 14. Monitorar logs em tempo real
tail -f _validation_v1/outputs/fase1_teste_unitario/logs/*.log
```
- [ ] Logs sendo gerados
- [ ] Detecção de ofícios funcionando
- [ ] Extração LLM funcionando
- [ ] Validação Pydantic funcionando

### Após Conclusão

```bash
# 15. Verificar JSONs gerados
ls -lh _validation_v1/outputs/fase1_teste_unitario/jsons/*/*.json
```
- [ ] JSONs gerados
- [ ] Quantidade esperada (1-3 arquivos)

```bash
# 16. Contar JSONs
find _validation_v1/outputs/fase1_teste_unitario/jsons -name "*.json" | wc -l
```
- [ ] Número de JSONs = Número de PDFs processados com sucesso

---

## 🔍 Análise de Resultados

### Validação de JSONs

```bash
# 17. Verificar estrutura de um JSON
cat _validation_v1/outputs/fase1_teste_unitario/jsons/*/*.json | jq . | head -50
```
- [ ] JSON válido
- [ ] Estrutura correta (metadata + oficio)

```bash
# 18. Verificar campos obrigatórios
cat _validation_v1/outputs/fase1_teste_unitario/jsons/*/*.json | jq '{processo: .oficio.processo_origem, requerente: .oficio.requerente_caps}'
```
- [ ] `processo_origem` presente e válido
- [ ] `requerente_caps` presente e em MAIÚSCULAS

```bash
# 19. Verificar dados bancários (ANEXO II)
cat _validation_v1/outputs/fase1_teste_unitario/jsons/*/*.json | jq '{banco: .oficio.banco, agencia: .oficio.agencia, conta: .oficio.conta, tipo: .oficio.conta_tipo}'
```
- [ ] `banco` presente
- [ ] `agencia` presente
- [ ] `conta` presente
- [ ] `conta_tipo` presente

**⚠️ CRÍTICO**: Se algum campo bancário estiver `null`, verificar anomalias!

### Análise de Logs

```bash
# 20. Ver resumo do processamento
tail -100 _validation_v1/outputs/fase1_teste_unitario/logs/*.log | grep -E "INFO|ERROR|WARNING"
```
- [ ] Sem erros críticos
- [ ] Warnings documentados

```bash
# 21. Verificar detecção de ofícios
grep "Ofício detectado" _validation_v1/outputs/fase1_teste_unitario/logs/*.log
```
- [ ] Ofícios detectados em todos os PDFs

```bash
# 22. Verificar detecção de ANEXO II
grep "ANEXO II" _validation_v1/outputs/fase1_teste_unitario/logs/*.log
```
- [ ] ANEXO II detectado em todos os PDFs

### Análise de Anomalias

```bash
# 23. Listar anomalias
ls -lh _validation_v1/outputs/fase1_teste_unitario/anomalias/
```
- [ ] Verificar se há arquivos de anomalias

```bash
# 24. Verificar anomalias críticas (sem ANEXO II)
cat _validation_v1/outputs/fase1_teste_unitario/anomalias/anomalias_sem_anexo_ii.json 2>/dev/null | jq .
```
- [ ] Nenhuma anomalia de ANEXO II (ideal)
- [ ] Se houver, documentar e investigar

---

## 📊 Cálculo de Métricas

### Taxa de Sucesso

```bash
# 25. Calcular métricas
TOTAL_PDFS=3
JSONS_GERADOS=$(find _validation_v1/outputs/fase1_teste_unitario/jsons -name "*.json" | wc -l | tr -d ' ')
TAXA_SUCESSO=$((JSONS_GERADOS * 100 / TOTAL_PDFS))

echo "PDFs processados: ${TOTAL_PDFS}"
echo "JSONs gerados: ${JSONS_GERADOS}"
echo "Taxa de sucesso: ${TAXA_SUCESSO}%"
```

**Metas**:
- [ ] Taxa de detecção ≥95% (≥3/3)
- [ ] Taxa de extração ≥90% (≥3/3)
- [ ] Taxa de validação 100% (3/3)
- [ ] Taxa de ANEXO II 100% (3/3)

### Validação Manual

Para cada JSON gerado:

```bash
# 26. Validar JSON individualmente
JSON_FILE="_validation_v1/outputs/fase1_teste_unitario/jsons/CPF/PROCESSO.json"
cat $JSON_FILE | jq .
```

**Checklist por JSON**:
- [ ] `metadata.cpf` correto (11 dígitos)
- [ ] `metadata.numero_processo` correto (formato CNJ)
- [ ] `metadata.processado` = true
- [ ] `oficio.processo_origem` presente
- [ ] `oficio.requerente_caps` em MAIÚSCULAS
- [ ] `oficio.banco` presente
- [ ] `oficio.agencia` presente
- [ ] `oficio.conta` presente
- [ ] `oficio.conta_tipo` presente
- [ ] Valores monetários sem R$, sem pontos de milhar
- [ ] Datas no formato ISO (YYYY-MM-DD)

---

## 📝 Documentação de Resultados

### Criar Relatório Fase 1

```bash
# 27. Criar relatório
cat > _validation_v1/outputs/fase1_teste_unitario/relatorio_fase1.md << 'EOF'
# Relatório Fase 1 - Teste Unitário

**Data**: $(date +%Y-%m-%d)
**PDFs processados**: 3

## Resultados

- **JSONs gerados**: X/3
- **Taxa de sucesso**: X%
- **Anomalias**: X

## Campos Obrigatórios

- **processo_origem**: ✅/❌
- **requerente_caps**: ✅/❌

## Dados Bancários (ANEXO II)

- **banco**: ✅/❌
- **agencia**: ✅/❌
- **conta**: ✅/❌
- **conta_tipo**: ✅/❌

## Observações

[Adicionar observações aqui]

## Decisão

- [ ] Aprovar para Fase 2
- [ ] Ajustes necessários

EOF
```
- [ ] Relatório criado
- [ ] Resultados preenchidos
- [ ] Observações documentadas

---

## ✅ Aprovação para Fase 2

### Critérios de Aprovação

- [ ] Taxa de detecção ≥95%
- [ ] Taxa de extração ≥90%
- [ ] Taxa de validação 100%
- [ ] Taxa de ANEXO II 100%
- [ ] Anomalias compreendidas e documentadas
- [ ] Qualidade dos dados validada manualmente
- [ ] Relatório Fase 1 completo

### Decisão

- [ ] ✅ **APROVADO** - Prosseguir para Fase 2
- [ ] ⚠️ **AJUSTES NECESSÁRIOS** - Documentar e corrigir
- [ ] ❌ **REPROVADO** - Revisar abordagem

---

## 🔄 Próximos Passos

### Se Aprovado

```bash
# 28. Preparar Fase 2 (10 PDFs)
mkdir -p _validation_v1/outputs/fase2_amostra_10/{jsons,logs,anomalias}

# 29. Executar Fase 2
python exportar_json.py \
    --input ./data/consultas \
    --output ./_validation_v1/outputs/fase2_amostra_10/jsons \
    --limite 10
```

### Se Ajustes Necessários

1. Documentar problemas encontrados
2. Ajustar código/configuração
3. Re-executar Fase 1
4. Validar novamente

---

## 📞 Comandos de Suporte

### Limpar e Recomeçar

```bash
# Limpar outputs da Fase 1
rm -rf _validation_v1/outputs/fase1_teste_unitario/*

# Recriar estrutura
mkdir -p _validation_v1/outputs/fase1_teste_unitario/{jsons,logs,anomalias}

# Executar novamente
./_validation_v1/scripts/validar_fase1.sh
```

### Debug

```bash
# Ver erros no log
grep "ERROR" _validation_v1/outputs/fase1_teste_unitario/logs/*.log

# Ver warnings
grep "WARNING" _validation_v1/outputs/fase1_teste_unitario/logs/*.log

# Ver chamadas LLM
grep "GPT" _validation_v1/outputs/fase1_teste_unitario/logs/*.log
```

---

**Status**: ⏳ Aguardando execução  
**Última atualização**: 13/10/2025
