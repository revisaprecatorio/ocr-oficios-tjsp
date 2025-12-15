# 📋 UAT V3.0 - User Acceptance Testing

**Versão:** V3.0.2
**Data Criação:** 14/12/2025
**Schema:** 35 colunas (reduzido de 50 em v2.5.1)
**Status:** ✅ Modernizado e pronto para uso

---

## 🆕 O Que Mudou (v2.5.1 → V3.0)

### ✅ Adicionado
- **Nova categoria:** `6_obito_sucessao/` - Processos com óbito do credor
- **Novos campos:** `obito`, `data_obito`, `cpf_sucessor`
- **Detecção melhorada:** V3.0.2 usa REGEX-first para rejeições

### ❌ Removido
- ~~`2_cessao_credito/`~~ - Campo `cessao_credito` não existe mais no schema
- ~~`8_multiplos_credores/`~~ - Dependia de `requerente_caps` (removido)
- **15 colunas** removidas do schema (50→35)

### 🔧 Atualizado
- `requerente_caps` → `credor_nome`
- `data_ajuizamento` → `data_base_atualizacao`
- Script adaptado para schema V3.0 (35 colunas)

---

## 📁 Estrutura de Categorias V3.0

| # | Categoria | Prioridade | Descrição |
|---|-----------|------------|-----------|
| 1 | `1_anomalia_formato/` | 🔴 ALTA | PDFs com formato antigo (7xxxxxx) |
| 3 | `3_herdeiros_nao_rejeitados/` | 🟡 MÉDIA | Habilitação de herdeiros aprovada |
| 4 | `4_preferencial/` | 🟡 MÉDIA | Idoso/doença grave/PCD |
| 5 | `5_rejeitados/` | 🔴 ALTA | V3.0.2: Detecção REGEX-first |
| 6 | `6_obito_sucessao/` | 🟡 MÉDIA | **V3.0: NOVO** - Óbito + sucessor |
| 7 | `7_dados_bancarios_incompletos/` | 🔵 SUGESTÃO | Dados bancários vazios |
| 9 | `9_sem_juros_moratorios/` | 🔵 SUGESTÃO | Sem juros moratórios |
| 10 | `10_amostra_baseline/` | 🔵 SUGESTÃO | Amostra aleatória 10% |
| 11 | `11_processos_ok_100/` | 🔵 BASELINE | Processos sem problemas |

---

## 🚀 Como Usar

### **1. Organizar PDFs para UAT**

```bash
# Certifique-se de ter um CSV export recente
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/4_UAT_refinamento

# Execute o script V3.0
python3 organizar_uat_v3.py
```

### **2. Validar PDFs Organizados**

1. **PRIORIDADE ALTA** (~45 min):
   - `1_anomalia_formato/` - Estrutura antiga
   - `5_rejeitados/` - V3.0.2: Confirmar motivo_rejeicao

2. **PRIORIDADE MÉDIA** (~2 horas):
   - `3_herdeiros_nao_rejeitados/` - Múltiplos credores
   - `4_preferencial/` - Marcadores corretos
   - `6_obito_sucessao/` - **V3.0: NOVO** - Validar óbito + sucessor

3. **SUGESTÕES** (~1 hora):
   - Validação complementar se houver tempo

---

## 📊 Schema V3.0 (35 Colunas)

### **Campos Essenciais**
- CPF, numero_processo_cnj, processo_origem
- numero_ordem, vara
- data_base_atualizacao, data_nascimento

### **Partes**
- credor_nome (substitui requerente_caps)
- credor_cpf_cnpj, devedor_ente

### **Dados Bancários**
- banco, agencia, conta

### **Valores**
- valor_principal_liquido, valor_principal_bruto
- juros_moratorios, valor_total_requisitado, saldo_final

### **Preferências**
- idoso, doenca_grave, pcd
- preferencial, habilitacao_herdeiros

### **Óbito/Sucessão (V3.0: NOVO)**
- obito, data_obito, cpf_sucessor

### **Controle**
- rejeitado, motivo_rejeicao
- observacoes, anomalia, descricao_anomalia

---

## 📚 Documentação

- **Script:** `organizar_uat_v3.py`
- **README Completo:** `README_UAT_V3.md` (gerado automaticamente)
- **Schema:** `../1_parsing_PDF/app/schemas.py`
- **CHANGELOG:** `../CHANGELOG.md` (V3.0.2)

---

## 🗂️ Histórico

### **V3.0.2** (14/12/2025)
- ✅ Script adaptado para schema 35 colunas
- ✅ Categoria `6_obito_sucessao` adicionada
- ❌ Categorias `cessao_credito` e `multiplos_credores` removidas
- 📦 UAT v2.5.1 arquivado em `2_ingestao/historico_evolucao_anteriores/`

### **v2.5.1** (14/11/2025) - LEGACY
- Baseado em schema 50 colunas
- 11 categorias (incluía cessao_credito e multiplos_credores)
- 48 processos validados
- **Status:** Arquivado (749 MB liberados)

---

## ⚠️ Migração v2.5.1 → V3.0

Se você tinha validações antigas:

1. **UAT v2.5.1:** Arquivado em `2_ingestao/historico_evolucao_anteriores/4_UAT_refinamento_v2.5.1_LEGACY/`
2. **PDFs antigos:** 64 PDFs (749 MB) preservados no arquivo
3. **Novo UAT:** Executar `organizar_uat_v3.py` com CSV atual

---

## 🎯 Próximos Passos

1. Exportar CSV atual do banco: `tests/LATEST_export.csv`
2. Executar `organizar_uat_v3.py`
3. Validar PDFs por prioridade
4. Documentar erros encontrados
5. Ajustar sistema se necessário
6. Deploy V3.1.0

---

**Autor:** Claude Code + Persival Balleste
**Última Atualização:** 14/12/2025
**Versão Sistema:** V3.0.2
