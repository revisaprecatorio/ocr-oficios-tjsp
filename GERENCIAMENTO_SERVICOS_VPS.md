# 🐳 Gerenciamento de Serviços na VPS

Guia completo para gerenciar todos os serviços Docker na VPS Ubuntu.

---

## 📋 **Informações da VPS**

- **Servidor:** srv987902.hstgr.cloud
- **IP:** 72.60.62.124
- **OS:** Ubuntu
- **Usuário:** root
- **Docker Compose:** `/root/docker-compose.yml`

---

## 🚀 **Subir Todos os Serviços**

### **Comando Principal**

```bash
cd /root
docker-compose up -d
```

Este comando sobe **todos** os serviços definidos no `docker-compose.yml`:
- ✅ Traefik (proxy reverso)
- ✅ n8n (automação)

**Outros serviços independentes:**
- Backoffice Streamlit (em `/root/6.UI_backoffice` — porta 8502)
- OCR API (em `/root/ocr-oficios-tjsp`)
- PostgreSQL (em `/root/ocr-oficios-tjsp`)

---

## 📊 **Serviços Disponíveis**

### **1. Traefik (Proxy Reverso)**

**Função:** Gerencia HTTPS e roteamento de domínios

**Comandos:**
```bash
# Subir
docker-compose up -d traefik

# Ver logs
docker logs -f root_traefik_1

# Parar
docker-compose stop traefik

# Reiniciar
docker-compose restart traefik

# Status
docker ps | grep traefik
```

**Portas:**
- 80 (HTTP)
- 443 (HTTPS)

**Verificar:**
```bash
curl -I http://localhost:80
netstat -tulpn | grep -E ':(80|443)'
```

---

### **2. n8n (Automação)**

**Função:** Plataforma de automação de workflows

**Comandos:**
```bash
# Subir
docker-compose up -d n8n

# Ver logs
docker logs -f root_n8n_1

# Parar
docker-compose stop n8n

# Reiniciar
docker-compose restart n8n

# Status
docker ps | grep n8n
```

**Portas:**
- 5678 (interno, via Traefik)

**URL:** https://n8n.srv987902.hstgr.cloud

**Verificar:**
```bash
curl -I http://localhost:5678
```

---

### **3. Backoffice Streamlit (6.UI_backoffice)**

**Função:** Interface web de backoffice para monitoramento dos processos de precatórios

**Repositório:** `github.com/revisaprecatorio/6.UI_backoffice`

**Comandos:**
```bash
cd /root/6.UI_backoffice

# Deploy completo (recomendado)
./deploy.sh

# Ver logs
docker logs backoffice-streamlit -f

# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Status
docker ps | grep backoffice
```

**Portas:**
- 8502 (HTTP direto)

**URLs:**
- http://srv987902.hstgr.cloud:8502
- https://revisaprecatorio.com.br/backoffice

---

### **4. OCR API + PostgreSQL**

**Função:** API de OCR e banco de dados

**Comandos:**
```bash
cd /root/ocr-oficios-tjsp

# Subir todos
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar todos
docker-compose stop

# Reiniciar
docker-compose restart

# Status
docker ps | grep ocr
```

**Serviços:**
- `ocr-oficios-tjsp-ocr-app-1` (API OCR)
- `ocr-oficios-tjsp-ocr-web-1` (Nginx)
- `ocr-oficios-tjsp-postgres-1` (PostgreSQL)

**Portas:**
- 8000 (API OCR - interno)
- 80 (Nginx - interno)
- 5432 (PostgreSQL - interno)

---

## 🔄 **Script de Inicialização Completa**

Crie um script para subir todos os serviços de uma vez:

```bash
cat > /root/start_all_services.sh << 'EOF'
#!/bin/bash
# ============================================================================
# SCRIPT DE INICIALIZAÇÃO DE TODOS OS SERVIÇOS
# ============================================================================

set -e

echo "============================================================"
echo "🚀 INICIANDO TODOS OS SERVIÇOS NA VPS"
echo "============================================================"
echo ""

# 1. Traefik + n8n
echo "📦 1. Subindo Traefik e n8n..."
cd /root
docker-compose up -d
echo "   ✅ Traefik e n8n iniciados"
echo ""

# 2. OCR + PostgreSQL
echo "📦 2. Subindo OCR API e PostgreSQL..."
cd /root/ocr-oficios-tjsp
docker-compose up -d
echo "   ✅ OCR API e PostgreSQL iniciados"
echo ""

# 3. Backoffice Streamlit
echo "📦 3. Subindo Backoffice Streamlit..."
cd /root/6.UI_backoffice
docker-compose up -d
echo "   ✅ Backoffice Streamlit iniciado"
echo ""

# 4. Verificar status
echo "============================================================"
echo "📊 STATUS DOS SERVIÇOS"
echo "============================================================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "============================================================"
echo "✅ TODOS OS SERVIÇOS INICIADOS!"
echo "============================================================"
echo ""
echo "🌐 URLs Disponíveis:"
echo "   - n8n:        https://n8n.srv987902.hstgr.cloud"
echo "   - Backoffice: http://srv987902.hstgr.cloud:8502"
echo ""
EOF

chmod +x /root/start_all_services.sh
```

**Executar:**
```bash
/root/start_all_services.sh
```

---

## 🛑 **Parar Todos os Serviços**

```bash
cat > /root/stop_all_services.sh << 'EOF'
#!/bin/bash
# ============================================================================
# SCRIPT PARA PARAR TODOS OS SERVIÇOS
# ============================================================================

echo "🛑 Parando todos os serviços..."

# Traefik + n8n
cd /root
docker-compose stop

# OCR + PostgreSQL
cd /root/ocr-oficios-tjsp
docker-compose stop

# Backoffice Streamlit
cd /root/6.UI_backoffice
docker-compose stop

echo "✅ Todos os serviços parados!"
docker ps
EOF

chmod +x /root/stop_all_services.sh
```

**Executar:**
```bash
/root/stop_all_services.sh
```

---

## 🔍 **Verificação de Status**

### **Ver Todos os Containers**
```bash
docker ps
```

### **Ver Todos (incluindo parados)**
```bash
docker ps -a
```

### **Ver Uso de Recursos**
```bash
docker stats
```

### **Ver Logs de Todos**
```bash
docker-compose logs -f
```

---

## 🔧 **Troubleshooting**

### **Problema: Container não sobe**

**Solução:**
```bash
# Ver logs do container
docker logs <container_name>

# Remover container corrompido
docker stop <container_name>
docker rm <container_name>

# Recriar
docker-compose up -d
```

### **Problema: Porta já em uso**

**Solução:**
```bash
# Ver o que está usando a porta
netstat -tulpn | grep :<porta>

# Matar processo
kill -9 <PID>

# Ou parar container conflitante
docker stop <container_name>
```

### **Problema: n8n não acessível via HTTPS**

**Causa:** Traefik não está rodando

**Solução:**
```bash
docker-compose up -d traefik
docker ps | grep traefik
```

### **Problema: Backoffice não carrega dados**

**Causa:** PostgreSQL não está rodando

**Solução:**
```bash
cd /root/ocr-oficios-tjsp
docker-compose up -d postgres
docker ps | grep postgres
```

---

## 🔄 **Reiniciar Serviços Específicos**

### **Reiniciar n8n**
```bash
cd /root
docker-compose restart n8n
```

### **Reiniciar Backoffice Streamlit**
```bash
cd /root/6.UI_backoffice
docker-compose restart
```

### **Reiniciar PostgreSQL**
```bash
cd /root/ocr-oficios-tjsp
docker-compose restart postgres
```

---

## 📊 **Monitoramento**

### **Ver Logs em Tempo Real**

**Todos os serviços:**
```bash
docker-compose logs -f
```

**Serviço específico:**
```bash
docker logs -f <container_name>
```

**Últimas 50 linhas:**
```bash
docker logs --tail 50 <container_name>
```

### **Ver Uso de Disco**
```bash
docker system df
```

### **Limpar Recursos Não Utilizados**
```bash
# Containers parados
docker container prune -f

# Imagens não utilizadas
docker image prune -a -f

# Volumes não utilizados
docker volume prune -f

# Tudo (cuidado!)
docker system prune -a -f
```

---

## 🔐 **Backup e Restore**

### **Backup de Volumes**

**n8n:**
```bash
docker run --rm -v n8n_data:/data -v $(pwd):/backup alpine tar czf /backup/n8n_backup.tar.gz -C /data .
```

**PostgreSQL:**
```bash
docker exec ocr-oficios-tjsp-postgres-1 pg_dump -U admin n8n > n8n_backup.sql
```

### **Restore de Volumes**

**n8n:**
```bash
docker run --rm -v n8n_data:/data -v $(pwd):/backup alpine tar xzf /backup/n8n_backup.tar.gz -C /data
```

**PostgreSQL:**
```bash
docker exec -i ocr-oficios-tjsp-postgres-1 psql -U admin n8n < n8n_backup.sql
```

---

## 📝 **Checklist de Inicialização**

Após reiniciar a VPS, execute:

- [ ] `docker-compose up -d` (Traefik + n8n)
- [ ] Verificar: https://n8n.srv987902.hstgr.cloud
- [ ] `cd /root/ocr-oficios-tjsp && docker-compose up -d` (OCR + PostgreSQL)
- [ ] `cd /root/6.UI_backoffice && docker-compose up -d` (Backoffice Streamlit)
- [ ] Verificar: http://srv987902.hstgr.cloud:8502
- [ ] `docker ps` (verificar todos rodando)

---

## 🌐 **URLs de Acesso**

| Serviço | URL | Porta |
|---------|-----|-------|
| **n8n** | https://n8n.srv987902.hstgr.cloud | 5678 (interno) |
| **Backoffice** | http://srv987902.hstgr.cloud:8502 | 8502 |
| **Traefik Dashboard** | http://72.60.62.124:8080 | 8080 |

---

## 📞 **Suporte**

Em caso de problemas:

1. Verificar logs: `docker logs <container_name>`
2. Verificar status: `docker ps -a`
3. Reiniciar serviço: `docker-compose restart <service>`
4. Último recurso: `docker-compose down && docker-compose up -d`

---

**Última atualização:** 11/06/2026
**Versão:** 1.1
**Responsável:** Persival Balleste
