# 🚀 Comandos VPS - Sistema OCR

## 📋 Acesso à VPS
```bash
# Conectar via SSH
sshpass -p 'R3v1s@2025' ssh -o StrictHostKeyChecking=no root@srv987902.hstgr.cloud

# Ou usar o script automático
./deploy_vps.sh
```

## 🐳 Comandos Docker na VPS

### Deploy Inicial
```bash
# 1. Conectar na VPS
ssh root@srv987902.hstgr.cloud

# 2. Clonar repositório
git clone https://github.com/revisaprecatorio/ocr-oficios-tjsp.git
cd ocr-oficios-tjsp

# 3. Configurar environment
cp .env.example .env
nano .env  # Configurar credenciais

# 4. Criar rede Traefik
docker network create traefik

# 5. Deploy
docker-compose -f deploy/docker-compose.prod.yml up -d --build
```

### Comandos de Manutenção
```bash
# Status dos containers
docker-compose -f deploy/docker-compose.prod.yml ps

# Logs em tempo real
docker-compose -f deploy/docker-compose.prod.yml logs -f ocr-app

# Restart do serviço
docker-compose -f deploy/docker-compose.prod.yml restart ocr-app

# Update do código
git pull origin main
docker-compose -f deploy/docker-compose.prod.yml up -d --build

# Parar todos os serviços
docker-compose -f deploy/docker-compose.prod.yml down
```

## 🔍 Testes e Monitoramento

### Health Checks
```bash
# Test básico
curl http://localhost:8000/health

# Status detalhado
curl http://localhost:8000/status

# Logs via API
curl http://localhost:8000/logs?lines=50

# Trigger processamento
curl -X POST http://localhost:8000/process
```

### Verificações do Sistema
```bash
# Verificar se PostgreSQL está acessível
docker-compose exec ocr-app python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='72.60.62.124',
        port=5432,
        database='n8n',
        user='admin',
        password='BetaAgent2024SecureDB'
    )
    print('✅ PostgreSQL OK')
    conn.close()
except:
    print('❌ PostgreSQL erro')
"

# Verificar OpenAI API
docker-compose exec ocr-app python -c "
from openai import OpenAI
import os
try:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.models.list()
    print('✅ OpenAI API OK')
except:
    print('❌ OpenAI API erro')
"

# Test completo do sistema
docker-compose exec ocr-app python run_sistema.py
```

## 🌐 URLs de Acesso

### Desenvolvimento/Debug
- **Health Check**: http://srv987902.hstgr.cloud:8000/health
- **Status**: http://srv987902.hstgr.cloud:8000/status  
- **API Docs**: http://srv987902.hstgr.cloud:8000/docs
- **Logs**: http://srv987902.hstgr.cloud:8000/logs

### Produção (com Traefik)
- **Main**: https://ocr.srv987902.hstgr.cloud
- **Health**: https://ocr.srv987902.hstgr.cloud/health
- **Status**: https://ocr.srv987902.hstgr.cloud/status

## 🔧 Troubleshooting

### Problemas Comuns
```bash
# Container não inicia
docker-compose -f deploy/docker-compose.prod.yml logs ocr-app

# Erro de rede
docker network ls
docker network inspect traefik

# Erro de permissão
chmod -R 755 /root/ocr-oficios-tjsp
chown -R root:root /root/ocr-oficios-tjsp

# Limpar containers antigos
docker system prune -f

# Rebuild completo
docker-compose -f deploy/docker-compose.prod.yml down
docker-compose -f deploy/docker-compose.prod.yml build --no-cache
docker-compose -f deploy/docker-compose.prod.yml up -d
```

### Logs Importantes
```bash
# Logs do sistema
journalctl -u docker

# Logs do container
docker logs $(docker ps -q --filter name=ocr-app)

# Logs do aplicativo
docker-compose -f deploy/docker-compose.prod.yml exec ocr-app cat /app/logs/ocr_oficios.log
```

## 📊 Monitoramento Contínuo

### Script de Monitoramento
```bash
# Usar o script de monitoramento
./monitor_vps.sh

# Ou manualmente
watch -n 30 'curl -s http://localhost:8000/health'
```

### Alertas
```bash
# Criar cron job para verificação
echo "*/5 * * * * curl -f http://localhost:8000/health || echo 'Sistema OCR offline' | mail admin@example.com" | crontab -
```
