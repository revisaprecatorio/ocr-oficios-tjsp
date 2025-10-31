# 📚 ÍNDICE - Investigação Bug de Parsing de Valores

**Última atualização:** 31/10/2025  
**Status:** ✅ COMPLETO

---

## 🎯 INÍCIO RÁPIDO

### Para entender o problema:
1. 📄 **[SUMARIO_EXECUTIVO.md](./SUMARIO_EXECUTIVO.md)** ← **COMECE AQUI!**
2. 📋 **[README_FINAL.md](./README_FINAL.md)** ← Guia completo

### Para investigação técnica:
3. 🔍 **[docs/ROOT_CAUSE_ANALYSIS.md](./docs/ROOT_CAUSE_ANALYSIS.md)** ← Análise detalhada

### Para correção:
4. 🔧 **[scripts/reprocessar_pdf.py](./scripts/reprocessar_pdf.py)** ← Script de correção
5. 📊 **[docs/QUERIES_VPS_v2.sql](./docs/QUERIES_VPS_v2.sql)** ← Queries para banco

---

## 📂 ESTRUTURA DE ARQUIVOS

```
8_erro_parsing-valor/
│
├── 📄 INDEX.md                          ← VOCÊ ESTÁ AQUI
├── 📄 README.md                         ← Introdução ao bug
├── 📄 README_FINAL.md                   ← Guia completo (LEIA!)
├── 📄 SUMARIO_EXECUTIVO.md              ← Resumo executivo (LEIA!)
├── 📄 PLANO_INVESTIGACAO.md             ← Plano da investigação
├── 📄 INSTRUCOES_GITHUB.md              ← Como fazer push para Github
│
├── 📁 docs/
│   ├── ANALISE_BUG.md                   ← Análise inicial
│   ├── ROOT_CAUSE_ANALYSIS.md           ← ⭐ Análise completa
│   ├── QUERIES_VPS.sql                  ← Queries v1
│   └── QUERIES_VPS_v2.sql               ← ⭐ Queries atualizadas
│
├── 📁 test_data/
│   └── Precatório-RAF.pdf               ← PDF problemático
│
├── 📁 test_scripts/
│   └── test_parse_local.py              ← ⭐ Script de teste
│
├── 📁 scripts/
│   └── reprocessar_pdf.py               ← ⭐ Script de correção
│
├── 📁 scripts_revisados/                 ← ⭐ Scripts corrigidos
│   ├── processador_corrigido.py         ← ⭐ ProcessadorOficio V3
│   └── README_CORRECOES.md              ← ⭐ Documentação das melhorias
│
└── 📁 test_outputs/                      ← Outputs do teste (31/10/2025)
    ├── 1_texto_extraido.txt             ← Texto completo do PDF
    ├── 1a_texto_relevante.txt           ← Ofício + ANEXO II
    ├── 2_prompt_llm.txt                 ← Prompt enviado
    ├── 3_resposta_llm.json              ← ⭐ Resposta do LLM (CORRETA!)
    ├── 4_dados_validados.json           ← Dados validados
    ├── 5_sql_statement.sql              ← SQL gerado
    └── 6_tabela_comparacao.txt          ← Comparação valores
```

**Legenda:**
- ⭐ = Arquivos mais importantes
- 📄 = Documentação
- 📁 = Pasta
- 🔧 = Scripts executáveis

---

## 🎯 FLUXO DE LEITURA RECOMENDADO

### 1️⃣ Para Gestores/Stakeholders
```
SUMARIO_EXECUTIVO.md
└─> README_FINAL.md (seções: Problema, Solução, Próximos Passos)
```

### 2️⃣ Para Desenvolvedores
```
SUMARIO_EXECUTIVO.md
└─> ROOT_CAUSE_ANALYSIS.md
    └─> test_outputs/3_resposta_llm.json (comparar com JSON original)
        └─> test_scripts/test_parse_local.py (ver implementação)
```

### 3️⃣ Para Correção Imediata
```
README_FINAL.md (seção: Próximos Passos)
└─> QUERIES_VPS_v2.sql (executar queries 1-4)
    └─> reprocessar_pdf.py (executar script)
```

---

## 📊 RESUMO DO BUG

### O Problema
- **Valor esperado:** R$ 88.994,41
- **Valor obtido:** R$ 88,99
- **Erro:** 99,9% (R$ 88.905,42)

### A Causa
- PDF com **4 ofícios** (outros PDFs têm apenas 1)
- LLM confundiu dados entre documentos
- Valor "88.994,41" interpretado como "88.99"

### A Solução
- ✅ Código atual funciona (teste: 100% sucesso)
- ✅ Scripts de correção criados
- ✅ Documentação completa

---

## 🔧 SCRIPTS DISPONÍVEIS

### 1. `test_scripts/test_parse_local.py`
**Função:** Testar processamento sem gravar no banco

**Uso:**
```bash
cd 3_OCR && source .venv/bin/activate
cd ../8_erro_parsing-valor/test_scripts
python test_parse_local.py
```

**Output:** 7 arquivos em `test_outputs/`

---

### 2. `scripts/reprocessar_pdf.py`
**Função:** Reprocessar e atualizar banco

**Uso:**
```bash
cd 3_OCR && source .venv/bin/activate
cd ../8_erro_parsing-valor/scripts
python reprocessar_pdf.py
```

**Ações:**
1. Consulta valores no banco
2. Reprocessa PDF
3. Compara valores
4. Pergunta se deseja atualizar
5. Atualiza banco

⚠️ **ATENÇÃO:** Faz UPDATE no banco de produção!

---

## 📋 QUERIES SQL

### Arquivo: `docs/QUERIES_VPS_v2.sql`

**Principais queries:**

1. **Listar tabelas:**
   ```sql
   \dt
   ```

2. **Ver schema:**
   ```sql
   \d lista_processos
   ```

3. **Buscar por nome:**
   ```sql
   SELECT * FROM lista_processos 
   WHERE requerente_caps LIKE '%RODRIGO%AZEVEDO%FERRAO%';
   ```

4. **Buscar valor 88.99:**
   ```sql
   SELECT * FROM lista_processos 
   WHERE valor_principal_liquido = 88.99;
   ```

---

## 🎓 DOCUMENTAÇÃO TÉCNICA

### Por ordem de complexidade:

| Documento | Nível | Descrição |
|-----------|-------|-----------|
| **SUMARIO_EXECUTIVO.md** | 🟢 Básico | Resumo para todos |
| **README_FINAL.md** | 🟡 Intermediário | Guia completo |
| **ANALISE_BUG.md** | 🟡 Intermediário | Análise inicial |
| **ROOT_CAUSE_ANALYSIS.md** | 🔴 Avançado | Análise técnica detalhada |
| **PLANO_INVESTIGACAO.md** | 🟢 Básico | Plano da investigação |

---

## ✅ CHECKLIST DE AÇÕES

### Investigação (Completo)
- [x] Identificar onde erro apareceu
- [x] Reproduzir processamento localmente
- [x] Analisar resposta do LLM
- [x] Verificar validador Pydantic
- [x] Documentar root cause
- [x] Criar scripts de teste
- [x] Criar scripts de correção

### Correção (Pendente)
- [ ] Executar queries no banco
- [ ] Verificar valor armazenado (R$ 88,99?)
- [ ] Reprocessar PDF problemático
- [ ] Buscar outros processos afetados
- [ ] Atualizar banco com valores corretos

### Github (Pendente)
- [x] Commit local criado
- [ ] Push para repositório remoto
- [ ] Verificar arquivos no Github

---

## 📞 PRECISA DE AJUDA?

### Para entender o problema:
➡️ Leia **SUMARIO_EXECUTIVO.md**

### Para corrigir o banco:
➡️ Execute **reprocessar_pdf.py**

### Para investigar tecnicamente:
➡️ Leia **ROOT_CAUSE_ANALYSIS.md**

### Para queries SQL:
➡️ Use **QUERIES_VPS_v2.sql**

---

## 📈 ESTATÍSTICAS

- **Arquivos criados:** 19
- **Linhas de código:** 3.098+
- **Documentos:** 6
- **Scripts:** 2
- **Outputs:** 7
- **Queries SQL:** 10+

---

## 🎉 STATUS FINAL

| Item | Status |
|------|--------|
| **Bug identificado** | ✅ Completo |
| **Root cause documentado** | ✅ Completo |
| **Scripts criados** | ✅ Completo |
| **Testes executados** | ✅ Sucesso (100%) |
| **Documentação** | ✅ Completa |
| **Commit Git** | ✅ Criado |
| **Push Github** | ⏳ Pendente |
| **Correção banco** | ⏳ Pendente |

---

**Criado por:** Sistema OCR Debug  
**Data:** 31/10/2025  
**Versão:** 1.0

