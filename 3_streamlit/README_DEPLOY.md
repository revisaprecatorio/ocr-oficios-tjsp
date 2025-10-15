# 🚀 Deploy Streamlit - Docker + Traefik

Guia completo para deploy do Streamlit em Docker com Traefik e BasicAuth.

---

## 📋 Pré-requisitos

- ✅ Docker instalado
- ✅ Docker Compose instalado
- ✅ Traefik rodando
- ✅ PostgreSQL acessível
- ✅ Rede Docker `traefik` criada

---

## 🎯 Deploy Rápido

### **1. Clonar Repositório na VPS**
```bash
cd /root
git clone https://github.com/revisaprecatorio/ocr-oficios-tjsp.git
cd ocr-oficios-tjsp/3_streamlit
```

### **2. Configurar Ambiente**
```bash
# Copiar .env.example
cp .env.example .env

# Gerar hash da senha
apt install -y apache2-utils
htpasswd -nb revisaprecatorio 'R3v1s@2025'

# Editar .env e substituir BASICAUTH_HASH
nano .env
```

**IMPORTANTE:** No `.env`, escape os `$` com `$$`:
```bash
# Exemplo:
# Hash gerado: revisaprecatorio:$apr1$abc123$xyz
# No .env:      revisaprecatorio:$$apr1$$abc123$$xyz
BASICAUTH_HASH=revisaprecatorio:$$apr1$$abc123$$xyz
```

### **3. Upload dos PDFs**

**Opção A: Via rsync (com chave SSH temporária)**
```bash
# No Mac: Criar chave SSH sem senha
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_temp -N ""
ssh-copy-id -i ~/.ssh/id_ed25519_temp root@srv987902.hstgr.cloud

# Comprimir PDFs
cd /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR
tar -czf data_consultas.tar.gz data/consultas/

# Upload
scp -i ~/.ssh/id_ed25519_temp data_consultas.tar.gz root@srv987902.hstgr.cloud:/root/

# Na VPS: Extrair
cd /root
tar -xzf data_consultas.tar.gz
cp -r data/consultas/* /root/ocr-oficios-tjsp/3_streamlit/data/consultas/
rm -rf data/ data_consultas.tar.gz
```

**Opção B: Via scp direto (se chave SSH funcionar)**
```bash
rsync -avz --progress \
  /Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/data/consultas/ \
  root@srv987902.hstgr.cloud:/root/ocr-oficios-tjsp/3_streamlit/data/consultas/
```

### **4. Deploy**
```bash
cd /root/ocr-oficios-tjsp/3_streamlit

# Build e iniciar
docker-compose build
docker-compose up -d

# Ver logs
docker-compose logs -f
```

---

## 📊 Comandos Úteis

### **Ver logs**
```bash
docker-compose logs -f
```

### **Reiniciar**
```bash
docker-compose restart
```

### **Parar**
```bash
docker-compose stop
```

### **Parar e remover**
```bash
docker-compose down
```

### **Rebuild (após mudanças no código)**
```bash
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### **Ver status**
```bash
docker-compose ps
docker-compose top
```

---

## 🔧 Troubleshooting

### **Container não inicia**
```bash
# Ver logs
docker-compose logs

# Verificar rede Traefik
docker network ls | grep traefik

# Criar rede se não existir
docker network create traefik
```

### **Erro de conexão com PostgreSQL**
```bash
# Testar conexão do container
docker-compose exec streamlit bash
apt update && apt install -y postgresql-client
psql -h 172.17.0.1 -p 5432 -U admin -d n8n
```

### **BasicAuth não funciona**
```bash
# Verificar hash no .env
cat .env | grep BASICAUTH_HASH

# Regenerar hash
htpasswd -nb revisaprecatorio 'R3v1s@2025'

# Editar .env e reiniciar
nano .env
docker-compose restart
```

### **PDFs não aparecem**
```bash
# Verificar se a pasta existe
ls -lh data/consultas/

# Verificar permissões
chmod -R 755 data/

# Verificar volume montado
docker-compose exec streamlit ls -lh /data/consultas/
```

---

## 🔄 Atualizar Aplicação

### **Método 1: Git Pull + Rebuild**
```bash
cd /root/ocr-oficios-tjsp/3_streamlit
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### **Método 2: Deploy Script**
```bash
./deploy.sh
```

---

## 🌐 Acesso

**URL:** http://72.60.62.124:8501

**Credenciais:**
- Usuário: `revisaprecatorio`
- Senha: `R3v1s@2025`

---

## 📈 Monitoramento

### **Recursos do Container**
```bash
docker stats oficios-streamlit
```

### **Logs em Tempo Real**
```bash
docker-compose logs -f --tail=100
```

### **Health Check**
```bash
docker inspect oficios-streamlit | grep -A 10 Health
```

---

## 🔐 Segurança

- ✅ Container roda com usuário não-root
- ✅ PDFs montados como read-only
- ✅ BasicAuth via Traefik
- ✅ Logs limitados (10MB, 3 arquivos)
- ✅ Limites de recursos (CPU e memória)

---

## 📝 Arquitetura

```
Internet
    ↓
Traefik (porta 80) + BasicAuth
    ↓
Docker Container: oficios-streamlit (porta 8501)
    ↓
PostgreSQL (172.17.0.1:5432)
```

---

## ✅ Checklist de Deploy

- [ ] Docker e Docker Compose instalados
- [ ] Repositório clonado
- [ ] `.env` configurado com hash correto
- [ ] PDFs enviados para `data/consultas/`
- [ ] Rede Traefik criada
- [ ] Deploy executado com sucesso
- [ ] Container rodando (`docker-compose ps`)
- [ ] Acesso funcionando (http://72.60.62.124:8501)
- [ ] BasicAuth funcionando
- [ ] Dados carregando corretamente

---

**Versão:** 2.1.0  
**Data:** 15/10/2025  
**Desenvolvedor:** Cascade AI + Persival Balleste
