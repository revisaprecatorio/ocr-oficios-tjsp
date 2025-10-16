# 🐳 Scripts de Gerenciamento VPS

Scripts para gerenciar serviços Docker na VPS Ubuntu.

---

## 📋 **Scripts Disponíveis**

### **1. start_all_services.sh**

Inicia todos os serviços na VPS.

**Uso:**
```bash
# Na VPS
cd /root/ocr-oficios-tjsp/scripts_vps
./start_all_services.sh
```

**O que faz:**
1. ✅ Sobe Traefik (proxy reverso)
2. ✅ Sobe n8n (automação)
3. ✅ Sobe OCR API + PostgreSQL
4. ✅ Sobe Streamlit
5. ✅ Verifica saúde de todos os serviços
6. ✅ Mostra status e URLs

---

### **2. stop_all_services.sh**

Para todos os serviços na VPS.

**Uso:**
```bash
# Na VPS
cd /root/ocr-oficios-tjsp/scripts_vps
./stop_all_services.sh
```

**O que faz:**
1. ✅ Para Streamlit
2. ✅ Para OCR API + PostgreSQL
3. ✅ Para Traefik + n8n
4. ✅ Mostra status final

---

## 🚀 **Deploy dos Scripts na VPS**

### **Opção 1: Via Git (Recomendado)**

```bash
# Na VPS
cd /root/ocr-oficios-tjsp
git pull origin main
chmod +x scripts_vps/*.sh
```

### **Opção 2: Copiar Manualmente**

```bash
# No Mac
scp scripts_vps/*.sh root@srv987902.hstgr.cloud:/root/

# Na VPS
chmod +x /root/*.sh
```

---

## 📊 **Exemplo de Uso**

```bash
# Conectar na VPS
ssh root@srv987902.hstgr.cloud

# Subir todos os serviços
cd /root/ocr-oficios-tjsp/scripts_vps
./start_all_services.sh

# Saída esperada:
# ============================================================
# 🚀 INICIANDO TODOS OS SERVIÇOS NA VPS
# ============================================================
# 
# 📦 1. Subindo Traefik e n8n...
#    ✅ Traefik e n8n iniciados
# 
# 📦 2. Subindo OCR API e PostgreSQL...
#    ✅ OCR API e PostgreSQL iniciados
# 
# 📦 3. Subindo Streamlit...
#    ✅ Streamlit iniciado
# 
# ============================================================
# 📊 STATUS DOS SERVIÇOS
# ============================================================
# NAMES                           STATUS                  PORTS
# oficios-streamlit               Up 5 seconds (healthy)  0.0.0.0:8501->8501/tcp
# root_n8n_1                      Up 8 seconds            127.0.0.1:5678->5678/tcp
# root_traefik_1                  Up 10 seconds           0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
# ocr-oficios-tjsp-ocr-app-1      Up 7 seconds (healthy)  8000/tcp
# ocr-oficios-tjsp-postgres-1     Up 7 seconds            5432/tcp
# 
# ============================================================
# 🔍 VERIFICAÇÃO DE SAÚDE
# ============================================================
# ✅ Traefik: OK (porta 80)
# ✅ n8n: OK (porta 5678)
# ✅ Streamlit: OK (porta 8501)
# ✅ PostgreSQL: OK
# 
# ============================================================
# ✅ TODOS OS SERVIÇOS INICIADOS!
# ============================================================
# 
# 🌐 URLs Disponíveis:
#    - n8n:       https://n8n.srv987902.hstgr.cloud
#    - Streamlit: http://72.60.62.124:8501
```

---

## 🔧 **Troubleshooting**

### **Erro: Permission denied**

```bash
chmod +x scripts_vps/*.sh
```

### **Erro: docker-compose not found**

```bash
# Instalar docker-compose
apt update
apt install docker-compose -y
```

### **Erro: Container já existe**

```bash
# Remover containers antigos
docker container prune -f

# Executar novamente
./start_all_services.sh
```

---

## 📝 **Documentação Completa**

Para mais detalhes, consulte:
- **[GERENCIAMENTO_SERVICOS_VPS.md](../GERENCIAMENTO_SERVICOS_VPS.md)** - Guia completo

---

**Última atualização:** 16/10/2025  
**Versão:** 1.0
