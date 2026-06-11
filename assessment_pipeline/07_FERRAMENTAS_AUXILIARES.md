# Ferramentas Auxiliares — Revisa Precatório

**Atualizado:** 06/2026

Estas ferramentas **não fazem parte do pipeline principal** de processamento de precatórios. São instrumentos de apoio operacional para uso interno da equipe.

---

## Índice

1. [Streamlit Backoffice](#1-streamlit-backoffice)
2. [CPF Batch Processing](#2-cpf-batch-processing)

---

## 1. Streamlit Backoffice

**Pasta:** `3_streamlit/`  
**Versão atual:** 3.0  
**Status:** Produção (uso local / acesso interno)

### O que é

Interface web em Python/Streamlit para consulta, filtragem e análise dos dados extraídos pelo pipeline OCR. Conecta diretamente ao PostgreSQL (`esaj_detalhe_processos`) e exibe os registros em tabela interativa com filtros avançados, estatísticas e gráficos.

**Não faz parte do pipeline de produção** — é uma ferramenta de backoffice para que a equipe possa inspecionar os dados sem necessidade de queries SQL.

### Estrutura da pasta

```
3_streamlit/
├── app/
│   └── streamlit_app.py        # Aplicação principal (~500 linhas)
├── Dockerfile                  # Build da imagem Docker
├── docker-compose.yml          # Orquestração (porta 8501)
├── requirements.txt            # streamlit, pandas, psycopg2-binary, python-dotenv
├── .env.example                # Template de variáveis de ambiente
├── run.sh                      # Script de execução local
├── run_local.sh                # Execução sem Docker
├── deploy.sh                   # Deploy em servidor
├── deploy_update.sh            # Atualização sem downtime
├── PROCEDIMENTO_REDEPLOY.md    # Guia passo a passo de redeploy
└── test_connection.py          # Teste de conexão com o banco
```

### Como executar localmente

```bash
# 1. Ativar venv (raiz do projeto)
source .venv/bin/activate

# 2. Instalar dependências (se necessário)
pip install streamlit pandas psycopg2-binary python-dotenv

# 3. Configurar banco (já deve estar no .env da raiz)
# DB_HOST=72.60.62.124 | DB_PORT=5432 | DB_NAME=n8n | DB_USER=admin

# 4. Executar
cd 3_streamlit
streamlit run app/streamlit_app.py --server.port=8501

# 5. Acessar
# http://localhost:8501
```

### Como executar via Docker

```bash
cd 3_streamlit
docker compose up -d
# Acesse: http://localhost:8501

# Atualizar após mudanças no código
./deploy_update.sh
```

### Funcionalidades

**Sidebar (filtros):**
- CPF (apenas números)
- Número do processo CNJ
- Vara (selectbox com todas as varas)
- Status: Todos / Apenas Rejeitados / Apenas Aprovados
- Preferências: Idoso / Doença Grave / PCD (selectbox)
- Valores (min/max)
- Datas (início/fim)

**Área principal:**

| Seção | Conteúdo |
|---|---|
| **Cards de estatísticas** | Total de processos, rejeitados, valor total, idosos |
| **Gráficos** | Distribuição por status (pizza), Top 5 Varas (barras) |
| **Tabela interativa** | Todos os 35 campos, ordenável, exportável |
| **Visualização de PDF** | Abre PDF inline (se `caminho_pdf` configurado) |
| **Export CSV** | Download dos dados filtrados |

### Arquitetura de dados

```python
@st.cache_data(ttl=300)  # Cache de 5 minutos
def carregar_todos_dados():
    # Carrega TODOS os dados de esaj_detalhe_processos de uma vez
    # Todos os filtros são aplicados em memória (DataFrame pandas)
    # Sem queries adicionais ao banco
```

**Performance:**
- Carregamento inicial: ~2-3 s
- Filtros: <100 ms (memória)
- Cache expira: a cada 5 min

### Tabela consultada

`esaj_detalhe_processos` — 35 colunas, conexão direta ao PostgreSQL externo.

Para o schema completo, ver `SCHEMA_TABELA.md` na raiz do projeto.

### Deploy em servidor

O `PROCEDIMENTO_REDEPLOY.md` contém o passo a passo completo. Resumo:

```bash
# Na máquina servidora
git pull origin main
cd 3_streamlit
docker compose down
docker compose build --no-cache
docker compose up -d
docker compose logs -f  # verificar se subiu
```

### Variáveis de ambiente necessárias

```bash
DB_HOST=72.60.62.124
DB_PORT=5432
DB_NAME=n8n
DB_USER=admin
DB_PASSWORD=<senha>
```

> Usar `.env.example` como template. O arquivo `.env` não é commitado (`.gitignore`).

---

## 2. CPF Batch Processing

**Arquivo:** `workflows_n8n/CPF_batch_processing.json`  
**Webhook:** `POST /webhook/cpf-batch-processing`  
**Tipo:** Workflow n8n

### O que é

Ferramenta de ingestão direta no banco, sem passar pelo fluxo WhatsApp. Recebe um CPF via HTTP, consulta o e-SAJ e faz upsert em `consultas_esaj`.

Documentado em detalhes em `06_WORKFLOWS_N8N.md` — Seção 7.

### Quando usar

| Situação | Use CPF_batch_processing? |
|---|---|
| Reprocessar CPF após erro de pipeline | ✅ Sim |
| Cliente que entrou por canal diferente do WhatsApp | ✅ Sim |
| Testes de integração end-to-end | ✅ Sim |
| Inserção em lote de múltiplos CPFs | ✅ Sim (enviar um POST por CPF) |
| Novo cliente via WhatsApp | ❌ Não (usar Chatbot Revisa) |

### Como usar

```bash
# Inserir/atualizar um CPF
curl -s -X POST "http://<n8n-host>:5678/webhook/cpf-batch-processing" \
  -H "Content-Type: application/json" \
  -d '{"cpf": "12345678900"}'

# Resposta esperada (sucesso):
# {"success": true, "cpf": "12345678900", "processos": [...]}
```

> **Atenção:** O `whatsapp_from` é fixado em `5511941455345` (número da equipe). O cliente **não recebe notificação** via WhatsApp. Após a inserção, o orchestrator pode processar normalmente desde que `current_state` seja `PAYMENT_APPROVED` e `status = false`.

### Limitações

- Não gera link de pagamento
- Não coleta email do cliente automaticamente
- Não atualiza estado para além do upsert inicial — o orquestrador precisa detectar e assumir
