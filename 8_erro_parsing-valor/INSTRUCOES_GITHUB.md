# 📤 INSTRUÇÕES PARA ATUALIZAR GITHUB

**Data:** 31/10/2025  
**Status:** ⚠️ Remote Git precisa ser configurado

---

## ⚠️ PROBLEMA DETECTADO

O repositório Git está configurado para um remote incorreto:
```
origin → https://github.com/revisaprecatorio/6.UI_backoffice.git
```

Este repositório não existe ou não está acessível.

---

## ✅ COMMIT JÁ REALIZADO

O commit foi criado com sucesso localmente:

```
Commit: 106a8af
Mensagem: 🐛 [DEBUG] Investigação completa do bug de parsing de valores
Arquivos: 18 novos arquivos (3.098 linhas adicionadas)
```

**Conteúdo commitado:**
- `8_erro_parsing-valor/` (pasta completa)
  - README_FINAL.md
  - SUMARIO_EXECUTIVO.md
  - PLANO_INVESTIGACAO.md
  - docs/ (4 documentos)
  - test_scripts/ (test_parse_local.py)
  - scripts/ (reprocessar_pdf.py)
  - test_outputs/ (7 arquivos)
  - test_data/ (Precatório-RAF.pdf)

---

## 🔧 PARA FAZER PUSH PARA O GITHUB

### Opção 1: Configurar remote correto

```bash
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa

# Remover remote atual
git remote remove origin

# Adicionar remote correto (ajuste o nome do repositório)
git remote add origin https://github.com/revisaprecatorio/revisa.git

# Ou se for outro nome:
# git remote add origin https://github.com/revisaprecatorio/[NOME_DO_REPO].git

# Fazer push
git push -u origin main
```

### Opção 2: Usar token de autenticação

Se o repositório existir mas precisar de autenticação:

```bash
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa

# Push com token
git push https://[SEU_TOKEN]@github.com/revisaprecatorio/revisa.git main
```

### Opção 3: Criar novo repositório

Se não houver repositório ainda:

1. Criar repositório no Github:
   - Nome: `revisa` ou `sistema-revisao-precatorios`
   - Visibilidade: Privado
   - Sem README inicial

2. Configurar remote e fazer push:
```bash
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa

git remote add origin https://github.com/revisaprecatorio/[NOME_CRIADO].git
git branch -M main
git push -u origin main
```

---

## 📊 VERIFICAÇÃO DO COMMIT

Para verificar o commit local:

```bash
# Ver último commit
git log -1 --stat

# Ver arquivos no commit
git show --name-only 106a8af

# Ver diff completo
git show 106a8af
```

---

## ✅ APÓS O PUSH

Verifique no Github:
1. Acesse: https://github.com/revisaprecatorio/[NOME_DO_REPO]
2. Navegue até: `8_erro_parsing-valor/`
3. Confirme que todos os arquivos estão lá:
   - ✅ README_FINAL.md
   - ✅ SUMARIO_EXECUTIVO.md
   - ✅ docs/ (4 arquivos)
   - ✅ test_scripts/ (1 arquivo)
   - ✅ scripts/ (1 arquivo)
   - ✅ test_outputs/ (7 arquivos)

---

## 📝 NOTA

O commit está salvo localmente e pode ser enviado para qualquer repositório remoto quando o remote correto for configurado.

**Comando para verificar status:**
```bash
git log --oneline -5
```

Deve mostrar:
```
106a8af (HEAD -> main) 🐛 [DEBUG] Investigação completa do bug de parsing de valores
[commits anteriores...]
```

---

**Última atualização:** 31/10/2025  
**Responsável:** Sistema OCR Debug

