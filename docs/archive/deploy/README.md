# 🚀 Guia de Deploy - Sistema OCR Ofícios Requisitórios TJSP

## 📋 Pré-requisitos

### VPS/Servidor Ubuntu
- Ubuntu 20.04+ 
- Mínimo 2GB RAM
- 10GB espaço livre
- Acesso sudo

### Credenciais Necessárias
- OpenAI API Key (GPT-5 Nano)
- PostgreSQL (existente na VPS ou novo)

## ⚡ Instalação Rápida

### 1. Clone o Repositório
```bash
git clone https://github.com/revisaprecatorio/ocr-oficios-tjsp.git
cd ocr-oficios-tjsp
```

### 2. Execute a Instalação
```bash
bash deploy/install.sh
```

### 3. Configure Credenciais
```bash
nano .env
```

Preencha com suas credenciais:
```bash
OPENAI_API_KEY=sk-proj-...
POSTGRES_HOST=72.60.62.124
POSTGRES_PORT=5432
POSTGRES_DB=n8n
POSTGRES_USER=admin
POSTGRES_PASSWORD=BetaAgent2024SecureDB
```

### 4. Teste o Sistema
```bash
source .venv/bin/activate
python run_sistema.py
```

## 🐳 Deploy com Docker (Alternativo)

### 1. Com Docker Compose
```bash
# Configurar .env primeiro
cp .env.example .env
nano .env

# Iniciar containers
docker-compose up -d
```

### 2. Verificar Status
```bash
docker-compose ps
docker-compose logs ocr-app
```

## 🔧 Configuração de Produção

### 1. Serviço Systemd
```bash
# Habilitar inicialização automática
sudo systemctl enable ocr-oficios
sudo systemctl start ocr-oficios

# Verificar status
sudo systemctl status ocr-oficios
```

### 2. Monitoramento
```bash
# Logs do sistema
tail -f logs/ocr_oficios.log

# Logs do serviço
sudo journalctl -u ocr-oficios -f
```

### 3. Nginx (Opcional)
```bash
# Copiar configuração
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ocr-oficios
sudo ln -s /etc/nginx/sites-available/ocr-oficios /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 📁 Estrutura de Arquivos

```
/opt/ocr-oficios-tjsp/
├── app/                    # Código da aplicação
├── Processos/             # PDFs para processamento
├── logs/                  # Logs do sistema
├── .env                   # Configurações (criar manualmente)
├── requirements.txt       # Dependências Python
└── run_sistema.py        # Script principal
```

## 🔄 Atualizações

### Atualizar Sistema
```bash
cd /opt/ocr-oficios-tjsp
bash deploy/update.sh
```

### Backup Manual
```bash
# Backup da configuração
cp .env .env.backup.$(date +%Y%m%d)

# Backup do banco (se local)
pg_dump oficios_tjsp > backup_$(date +%Y%m%d).sql
```

## 🐛 Troubleshooting

### Problemas Comuns

#### 1. Erro de Permissão
```bash
sudo chown -R $USER:$USER /opt/ocr-oficios-tjsp
```

#### 2. Dependências Python
```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Conexão PostgreSQL
```bash
# Testar conexão
psql -h POSTGRES_HOST -U POSTGRES_USER -d POSTGRES_DB -c "SELECT 1;"
```

#### 4. Verificar Logs
```bash
# Logs da aplicação
tail -50 logs/ocr_oficios.log

# Logs do sistema
sudo journalctl -u ocr-oficios --since "1 hour ago"
```

### Performance

#### Monitorar Recursos
```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Uso do Python
ps aux | grep python
```

## 📞 Suporte

### Logs Importantes
- Aplicação: `logs/ocr_oficios.log`
- Sistema: `sudo journalctl -u ocr-oficios`
- Nginx: `/var/log/nginx/ocr-oficios-*.log`

### Comandos Úteis
```bash
# Status completo
sudo systemctl status ocr-oficios --no-pager -l

# Reiniciar serviço
sudo systemctl restart ocr-oficios

# Testar configuração
python -c "from app.detector import DetectorOficio; print('✅ OK')"
```

## 🔐 Segurança

### Recomendações
1. **Firewall**: Configurar UFW
2. **SSH**: Usar chaves ao invés de senhas
3. **Updates**: Manter sistema atualizado
4. **Backup**: Backup regular do .env e dados
5. **Logs**: Monitorar logs de acesso

### Firewall Básico
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

---

**🎉 Sistema OCR pronto para produção na VPS!**
