# Changelog - Streamlit Ofícios TJSP

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

---

## [2.1.0] - 2025-10-15

### ✅ Adicionado
- Deploy completo via Docker + Docker Compose
- Dockerfile otimizado com Python 3.11-slim
- Integração com PostgreSQL via IP do host (172.17.0.1)
- Acesso direto via porta 8501
- Upload de PDFs (1.4GB) via scp com chave SSH temporária
- Documentação completa de deploy (README_DEPLOY.md)
- Script automatizado de deploy (deploy.sh)
- Health check automático do container
- Logs rotativos (10MB, 3 arquivos)
- Limites de recursos (CPU/memória)

### 🔧 Corrigido
- Adicionado `plotly>=5.18.0` ao requirements.txt
- Exposta porta 8501 no docker-compose.yml
- Corrigido processo de upload de PDFs
- Resolvido erro de autenticação SSH

### ⚠️ Limitações Conhecidas
- **Validação de Falsos Rejeitados:** Sistema não valida se ofícios foram incorretamente rejeitados durante o processamento
- **Logs de Auditoria:** Falta rastreabilidade completa de ações do usuário
- **Testes Automatizados:** Ausência de testes unitários e de integração
- **Backup Automático:** PDFs e dados não possuem backup automatizado
- **Monitoramento:** Falta alertas de falhas e métricas de performance
- **BasicAuth:** Configurado mas não ativo (acesso direto via porta)

### 📝 Notas Técnicas
- Container roda com usuário não-root (segurança)
- PDFs montados como read-only
- Build time: ~2-3 minutos
- Tamanho da imagem: ~500MB
- Consumo de memória: ~512MB em idle

---

## [2.0.0] - 2025-10-14

### ✅ Adicionado
- Interface Streamlit inicial
- Conexão com PostgreSQL
- Visualização de dados de ofícios
- Filtros básicos

---

## Roadmap

### v2.2.0 (Planejado)
- [ ] Implementar validação de falsos rejeitados
- [ ] Adicionar sistema de logs de auditoria
- [ ] Criar testes automatizados (pytest)
- [ ] Implementar backup automático de PDFs
- [ ] Adicionar monitoramento (Prometheus/Grafana)

### v2.3.0 (Planejado)
- [ ] Ativar BasicAuth via Traefik
- [ ] Adicionar HTTPS com Let's Encrypt
- [ ] Implementar rate limiting
- [ ] Adicionar cache Redis
- [ ] Otimizar queries do banco

### v3.0.0 (Futuro)
- [ ] API REST para integração externa
- [ ] Sistema de notificações
- [ ] Dashboard de analytics
- [ ] Export para Excel/PDF
- [ ] Integração com n8n

---

**Mantido por:** Cascade AI + Persival Balleste  
**Repositório:** https://github.com/revisaprecatorio/ocr-oficios-tjsp
