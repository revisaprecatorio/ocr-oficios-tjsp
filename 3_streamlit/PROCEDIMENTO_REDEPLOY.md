# 🔄 Procedimento de Redeploy - Streamlit VPS Ubuntu

Guia passo a passo para atualizar o Streamlit em produção na VPS Ubuntu.

---

## 📋 **Informações da VPS**

- **Servidor:** srv987902.hstgr.cloud
- **IP:** 72.60.62.124
- **OS:** Ubuntu
- **Usuário:** root
- **Diretório do Projeto:** `/root/ocr-oficios-tjsp`
- **Container:** `oficios-streamlit`
- **Porta:** 8501
- **URL:** http://72.60.62.124:8501

---

## 🚀 **Procedimento Padrão de Redeploy**

### **1. Conectar via SSH**

```bash
ssh root@srv987902.hstgr.cloud
# ou
ssh root@72.60.62.124
```

### **2. Navegar para o Projeto**

```bash
cd /root/ocr-oficios-tjsp
```

### **3. Verificar Branch Atual**

```bash
git branch
# Deve estar em: main
```

### **4. Baixar Atualizações do GitHub**

```bash
git pull origin main
```

**Saída esperada:**
```
Updating 9ad597d..0286f87
Fast-forward
 3_streamlit/app/streamlit_app.py | 10 ++++++++--
 2_ingestao/scripts/ingest_all_jsons.py | 26 ++++++++++++++++++++++----
 2 files changed, 30 insertions(+), 6 deletions(-)
```

### **5. Executar Script de Deploy**

```bash
cd 3_streamlit
chmod +x deploy_update.sh
./deploy_update.sh
```

**O script automaticamente:**
1. ✅ Para o container atual
2. ✅ Remove o container antigo
3. ✅ Reconstrói a imagem (sem cache)
4. ✅ Sobe o novo container
5. ✅ Verifica o status
6. ✅ Mostra os logs

### **6. Verificar Deploy**

```bash
# Ver status do container
docker ps | grep streamlit

# Ver logs em tempo real
docker logs -f oficios-streamlit

# Sair dos logs: Ctrl+C
```

**Saída esperada:**
```
CONTAINER ID   IMAGE                      STATUS                  PORTS
bb599d4f97c3   3_streamlit_streamlit      Up 2 minutes (healthy)  0.0.0.0:8501->8501/tcp
```

### **7. Testar no Navegador**

Acessar: **http://72.60.62.124:8501**

Verificar:
- ✅ Interface carrega corretamente
- ✅ Dados aparecem na aba "Dados"
- ✅ Todas as 49 colunas estão visíveis
- ✅ Filtros funcionam
- ✅ Gráficos renderizam

---

## 🔧 **Comandos Úteis**

### **Gerenciamento do Container**

```bash
# Ver status
docker ps | grep streamlit

# Ver logs (últimas 50 linhas)
docker logs --tail 50 oficios-streamlit

# Ver logs em tempo real
docker logs -f oficios-streamlit

# Reiniciar container
docker restart oficios-streamlit

# Parar container
docker stop oficios-streamlit

# Remover container
docker rm oficios-streamlit

# Ver uso de recursos
docker stats oficios-streamlit
```

### **Verificação de Saúde**

```bash
# Healthcheck do container
docker inspect oficios-streamlit | grep -A 10 Health

# Ver processos dentro do container
docker top oficios-streamlit

# Executar comando dentro do container
docker exec -it oficios-streamlit bash
```

### **Troubleshooting**

```bash
# Container não inicia
docker logs oficios-streamlit
docker-compose logs

# Verificar portas
netstat -tulpn | grep 8501

# Verificar imagens
docker images | grep streamlit

# Limpar imagens antigas
docker image prune -a
```

---

## 📊 **Checklist de Validação Pós-Deploy**

Após o deploy, verificar:

- [ ] Container está rodando (`docker ps`)
- [ ] Healthcheck está "healthy"
- [ ] Porta 8501 está acessível
- [ ] Interface web carrega
- [ ] Dados aparecem na aba "Dados"
- [ ] Todas as 49 colunas estão visíveis
- [ ] Coluna `data_nascimento` aparece
- [ ] Filtros funcionam corretamente
- [ ] Gráficos renderizam
- [ ] Download de PDF funciona
- [ ] Export CSV funciona
- [ ] Sem erros nos logs

---

## 🔄 **Rollback (Se Necessário)**

Se algo der errado, fazer rollback:

```bash
# 1. Voltar para commit anterior
cd /root/ocr-oficios-tjsp
git log --oneline -5
git checkout <commit_anterior>

# 2. Rebuild e restart
cd 3_streamlit
./deploy_update.sh

# 3. Voltar para main quando corrigir
git checkout main
```

---

## 📝 **Histórico de Deploys**

### **v2.2.0 (16/10/2025)**
- ✅ Adicionadas 49 colunas no Streamlit
- ✅ Corrigido script de ingestão (11 colunas faltantes)
- ✅ 0 falsos rejeitados (100% precisão)
- ✅ Pipeline completo automatizado

**Commits:**
- `0286f87` - fix: Adicionar 11 colunas faltantes no script de ingestão
- `9ad597d` - fix: Corrigir caminho do projeto na VPS
- `51f9e5b` - feat: Script de deploy automático
- `52dc7e4` - feat: Pipeline completo v2.2.0

### **v2.1.0 (14/10/2025)**
- ✅ Interface Streamlit otimizada
- ✅ Download de PDF destacado
- ✅ Formatação de valores monetários

---

## ⚠️ **Avisos Importantes**

1. **Sempre fazer backup antes de deploy em produção**
2. **Testar em ambiente local antes de fazer deploy**
3. **Verificar logs após deploy**
4. **Manter documentação atualizada**
5. **Comunicar usuários sobre manutenção**

---

## 📞 **Contatos de Emergência**

- **Desenvolvedor:** [seu contato]
- **VPS Provider:** Hostinger
- **Suporte:** [link do suporte]

---

**Última atualização:** 16/10/2025  
**Versão:** 2.2.0  
**Responsável:** Persival Balleste
