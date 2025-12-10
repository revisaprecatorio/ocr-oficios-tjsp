# 🧠 Memória ByteRover - OCR Ofícios TJSP v2.5.1

**Data:** 14/11/2025  
**Versão:** v2.5.1  
**Status:** Produção (96.1% taxa de sucesso)

---

## 📋 Visão Geral do Projeto

Sistema de extração automatizada de dados de **Ofícios Requisitórios do TJSP** a partir de PDFs nativos para banco PostgreSQL, com interface web Streamlit.

**Repositório:** https://github.com/revisaprecatorio/ocr-oficios-tjsp

---

## 🏗️ Arquitetura do Sistema

### **Pipeline Modular em 3 Etapas**

```
┌─────────┐    ┌──────────────┐    ┌────────────┐    ┌───────────┐
│  PDFs   │ -> │ 1_parsing_PDF│ -> │ 2_ingestao │ -> │ 3_streamlit│
│ (input) │    │   (JSONs)    │    │ (PostgreSQL)│    │   (Web)   │
└─────────┘    └──────────────┘    └────────────┘    └───────────┘
```

### **Componentes Principais**

#### **1. Parsing PDF (`1_parsing_PDF/`)**
```python
# Estrutura
app/
├── detector.py       # DetectorOficio + DetectorAnexoII
├── processador.py    # ProcessadorOficio (modo híbrido LLM)
├── schemas.py        # Pydantic models (OficioRequisitorio)
└── main.py          # Entry point

# Bibliotecas
import pymupdf                    # Extração texto PDF (única lib)
from openai import OpenAI         # GPT-4o-mini (fallback)
import google.generativeai as genai  # Gemini 2.5 Flash (primário)
from pydantic import BaseModel    # Validação dados
```

#### **2. Ingestão (`2_ingestao/`)**
```python
# Script principal
scripts/importar_postgres.py

# Função
- Lê JSONs do parsing
- Valida dados com Pydantic
- Faz upsert no PostgreSQL (ON CONFLICT DO UPDATE)
- Armazena texto_completo_oficio para auditoria
```

#### **3. Streamlit (`3_streamlit/`)**
```python
# Interface web
app.py              # Aplicação Streamlit
Dockerfile          # Container Docker
docker-compose.yml  # Orquestração
deploy_update.sh    # Script deploy VPS

# Funcionalidades
- 49 colunas disponíveis
- Filtros avançados
- Export CSV
- Visualização dados bancários (ANEXO II)
```

---

## 🚀 Modo Híbrido LLM (Principal Inovação)

### **Estratégia de Fallback Inteligente**

```python
def processar_oficio(pdf_path: str) -> OficioRequisitorio:
    """
    Pipeline com fallback automático Gemini → OpenAI
    """
    # 1. Detectar ofício no PDF
    paginas_oficio, texto_oficio = detector.detectar_oficio(pdf_path)
    
    # 2. Tentativa primária: Gemini 2.5 Flash
    try:
        response = genai.GenerativeModel('gemini-2.0-flash-exp').generate_content(
            prompt_estruturado(texto_oficio)
        )
        dados = json.loads(response.text)
        oficio = OficioRequisitorio(**dados)  # Validação Pydantic
        return oficio
        
    except Exception as e:
        logger.warning(f"Gemini falhou: {e}. Tentando OpenAI...")
        
        # 3. Fallback: GPT-4o-mini
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt_estruturado(texto_oficio)}],
            temperature=0
        )
        dados = json.loads(response.choices[0].message.content)
        oficio = OficioRequisitorio(**dados)
        return oficio
```

### **Por que Modo Híbrido?**

| Aspecto | Gemini 2.5 Flash | GPT-4o-mini |
|---------|------------------|-------------|
| **Custo** | Grátis | $0.150/1M input |
| **Contexto** | 1M tokens (60x maior) | 16k tokens |
| **Taxa sucesso** | ~96% | 100% |
| **Uso** | Primário (49/51 PDFs) | Fallback (2/51 PDFs) |

**Resultado:** 93% economia de custos mantendo 96.1% taxa de sucesso!

---

## 🔍 Detecção de Ofício

### **DetectorOficio (Ofício Requisitório)**

```python
def detectar_oficio(pdf_path: str) -> Tuple[List[int], str]:
    """
    Detecta páginas do ofício usando 3 critérios (mínimo 2/3)
    """
    criterios = {
        'keywords': ["OFÍCIO REQUISITÓRIO", "VARA DA FAZENDA PÚBLICA"],
        'cnj_pattern': r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}',
        'estrutura': "AO JUÍZO DA ... VARA"
    }
    
    # Retorna: (páginas_do_oficio, texto_completo)
    return paginas, texto
```

### **DetectorAnexoII (Dados Bancários)**

```python
def detectar_anexo_ii(texto: str) -> bool:
    """
    Detecta ANEXO II com validações robustas (v2.4.0)
    """
    # Critérios (mínimo 3/5)
    1. Marcador "ANEXO II" presente
    2. CPF válido encontrado
    3. Nome do credor presente
    4. Dados bancários (banco, agência, conta)
    5. Valor requisitado presente
    
    # Resultado: 100% precisão (zero falsos positivos)
```

---

## 📊 Schema PostgreSQL

### **Tabela: `lista_processos`**

```sql
-- Primary Key
cpf VARCHAR(11)                    -- CPF do requerente (apenas números)
numero_processo VARCHAR(30)        -- Número CNJ do processo

-- Ofício (13 campos)
vara VARCHAR(200)
processo_execucao VARCHAR(30)
processo_conhecimento VARCHAR(30)
data_ajuizamento DATE
data_transito_julgado DATE
requerente_caps VARCHAR(500)       -- Nome em MAIÚSCULAS
advogado_nome VARCHAR(500)
advogado_oab VARCHAR(50)           -- Formato: OAB/UF 000.000

-- Financeiro (7 campos)
valor_principal_liquido DECIMAL(15,2)
valor_principal_bruto DECIMAL(15,2)
juros_moratorios DECIMAL(15,2)
contrib_previdenciaria_iprem DECIMAL(15,2)
contrib_previdenciaria_hspm DECIMAL(15,2)
valor_total_requisitado DECIMAL(15,2)
data_base_atualizacao DATE

-- ANEXO II - Dados Bancários (6 campos)
banco VARCHAR(10)                  -- Código banco (3 dígitos)
agencia VARCHAR(20)                -- Agência (com/sem dígito)
conta VARCHAR(30)                  -- Conta (com/sem dígito)
conta_tipo VARCHAR(20)             -- Corrente/Poupança
credor_nome VARCHAR(500)
credor_cpf_cnpj VARCHAR(20)

-- Preferências (3 campos booleanos)
idoso BOOLEAN                      -- >= 60 anos
doenca_grave BOOLEAN
pcd BOOLEAN

-- Controle (4 campos)
texto_completo_oficio TEXT         -- Auditoria
timestamp_processamento TIMESTAMP
data_envio DATE
processado BOOLEAN

-- Índices
PRIMARY KEY (cpf, numero_processo)
CREATE INDEX idx_requerente ON lista_processos(requerente_caps)
CREATE INDEX idx_vara ON lista_processos(vara)
CREATE INDEX idx_idoso ON lista_processos(idoso)
```

---

## ⚙️ Configuração (.env)

```ini
# Google Gemini (Primário - Grátis)
GOOGLE_API_KEY=AIza...

# OpenAI (Fallback)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini

# PostgreSQL Database
POSTGRES_HOST=seu-servidor-postgres
POSTGRES_PORT=5432
POSTGRES_DB=oficios_tjsp
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua-senha-segura
```

---

## 🚀 Deploy em Produção

### **Servidor VPS**

```bash
# Informações
Servidor: srv987902.hstgr.cloud
IP: 72.60.62.124
URL: http://72.60.62.124:8501
Projeto: /root/ocr-oficios-tjsp
Container: oficios-streamlit
```

### **Procedimento de Deploy**

```bash
# 1. Conectar via SSH
ssh root@srv987902.hstgr.cloud

# 2. Atualizar código
cd /root/ocr-oficios-tjsp
git pull origin main

# 3. Deploy Streamlit
cd 3_streamlit
./deploy_update.sh

# 4. Verificar status
docker ps | grep streamlit
docker logs -f oficios-streamlit

# 5. Testar URL
curl http://72.60.62.124:8501
```

### **Script de Deploy Automático**

```bash
#!/bin/bash
# deploy_update.sh

# 1. Pull do GitHub
git pull origin main

# 2. Parar container
docker stop oficios-streamlit

# 3. Remover container
docker rm oficios-streamlit

# 4. Rebuild imagem
docker-compose build --no-cache

# 5. Subir novo container
docker-compose up -d

# 6. Verificar status
docker ps | grep streamlit
docker logs --tail 20 oficios-streamlit
```

---

## 📈 Métricas de Produção (v2.5.1)

### **Performance**

| Métrica | Valor | Detalhes |
|---------|-------|----------|
| **Taxa de sucesso** | **96.1%** | 49/51 PDFs processados |
| **Tempo por PDF** | **27.5s** | Média em produção |
| **Custo por PDF** | **$0.002** | 93% economia vs OpenAI solo |
| **Campos extraídos** | **32.8/doc** | +165% vs baseline (12.4) |
| **Taxa de detecção** | **100%** | Zero falsos negativos |
| **Precisão ANEXO II** | **100%** | Zero falsos positivos |

### **Custos Reais**

**Teste com 51 PDFs:**
- Gemini 2.5 Flash: 49 PDFs → **$0.00** (grátis)
- OpenAI GPT-4o-mini: 2 PDFs → **~$0.10**
- **Total: ~$0.10** (93% economia)

**Projeção: 1000 PDFs/mês:**
- Gemini: 960 PDFs → **$0.00**
- OpenAI: 40 PDFs → **~$2.00**
- **Total: ~$2.00/mês** (vs $30/mês com OpenAI solo)

---

## 🛠️ Comandos Úteis

### **Pipeline Completo**

```bash
# Executar pipeline completo
./pipeline_completo.sh

# Processar CPF específico
cd 1_parsing_PDF
python -m app.main --cpf 12345678909

# Importar JSONs para PostgreSQL
cd 2_ingestao
python scripts/importar_postgres.py --input ../1_parsing_PDF/output/json

# Testes unitários
cd tests
pytest -v
pytest tests/test_detector.py -v
```

### **Gerenciamento VPS**

```bash
# Logs em tempo real
docker logs -f oficios-streamlit

# Restart container
docker restart oficios-streamlit

# Verificar status
docker ps | grep streamlit

# Entrar no container
docker exec -it oficios-streamlit bash

# Verificar recursos
docker stats oficios-streamlit
```

---

## 🔧 Melhorias Críticas v2.5.1

### **5 Melhorias Implementadas (01/11/2025)**

1. **Validador Pydantic para campos bancários**
   ```python
   # Problema: Gemini retornava int, esperava-se str
   banco: str = Field(..., description="Código banco (3 dígitos)")
   
   # Solução: Validador com conversão automática
   @validator('banco', 'agencia', 'conta', pre=True)
   def convert_to_string(cls, v):
       return str(v) if v is not None else None
   ```

2. **Tratamento de lista retornada por Gemini**
   ```python
   # Problema: Gemini às vezes retorna lista em vez de dict
   # Solução: Detectar e extrair primeiro elemento
   if isinstance(dados, list) and len(dados) > 0:
       dados = dados[0]
   ```

3. **Logging completo de erros de validação**
   ```python
   except ValidationError as e:
       logger.error(f"Erro validação Pydantic: {e}")
       logger.error(f"Dados recebidos: {dados}")
       # Fallback para OpenAI
   ```

4. **Fallback OpenAI em erro de validação Pydantic**
   - Se Gemini retornar dados inválidos → OpenAI
   - Aumenta robustez do sistema

5. **Desabilita chunking quando Gemini disponível**
   - Gemini tem 1M tokens contexto
   - Não precisa chunking (mais rápido e preciso)

**Resultado:** Taxa de sucesso subiu de 90% (v2.5.0) para 96.1% (v2.5.1)

---

## 📚 Estrutura de Arquivos

```
3_OCR/
├── 1_parsing_PDF/              # Pipeline extração (CORE)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── detector.py         # DetectorOficio + DetectorAnexoII
│   │   ├── processador.py      # ProcessadorOficio (modo híbrido)
│   │   ├── schemas.py          # Pydantic models
│   │   └── main.py            # Entry point
│   ├── tests/
│   │   └── test_detector_anexo_robusto.py
│   └── output/
│       ├── json/              # JSONs extraídos
│       └── csv/               # CSVs para análise
│
├── 2_ingestao/                # Pipeline ingestão (CORE)
│   ├── scripts/
│   │   ├── importar_postgres.py
│   │   └── test_connection.py
│   └── logs/
│
├── 3_streamlit/               # Interface web (CORE)
│   ├── app.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── deploy_update.sh
│   └── requirements.txt
│
├── data/                      # PDFs de entrada
│   └── consultas/
│       └── {cpf}/
│           └── {numero_processo_cnj}.pdf
│
├── scripts_vps/               # Scripts gestão VPS
│   ├── start_all_services.sh
│   └── stop_all_services.sh
│
├── tests/                     # Testes unitários (pytest)
│   ├── test_detector.py
│   ├── test_processador.py
│   └── test_schemas.py
│
├── docs/                      # Documentação
│   └── archive/              # Histórico
│
├── README.md                  # Documentação principal (v2.5.1)
├── CHANGELOG.md               # Histórico de versões
├── AGENTS.md                  # Especificações do sistema
├── SCHEMA_TABELA.md          # Schema PostgreSQL
├── pipeline_completo.sh       # Pipeline automatizado
├── cleanup_v2.5.1.sh         # Script de limpeza
├── requirements.txt           # Dependências Python
├── .env                       # Configurações (não versionado)
└── .env.example              # Template configurações
```

---

## 🎯 Roadmap

### **v2.6.0 - Otimização Final (PRÓXIMO)**
- [ ] Chunking inteligente no fallback OpenAI
- [ ] Resolver 2 PDFs restantes (3.9%)
- [ ] Meta: 98-100% taxa de sucesso
- [ ] Tempo estimado: 2-3 horas

### **v2.7.0 - Segurança e Monitoramento**
- [ ] BasicAuth via Traefik
- [ ] HTTPS com Let's Encrypt
- [ ] Sistema de logs de auditoria
- [ ] Monitoramento (Prometheus/Grafana)
- [ ] Backup automático de PDFs

### **v3.0.0 - Expansão**
- [ ] Interface web para upload de PDFs
- [ ] API REST para integração externa
- [ ] Dashboard de analytics avançado
- [ ] Processamento paralelo (múltiplos workers)
- [ ] Integração com n8n

---

## 🔑 Padrões e Convenções

### **Nomenclatura de Arquivos**
```
# PDFs de entrada
{cpf_numerico}/{numero_processo_cnj}.pdf
Exemplo: 12345678909/0035938-67.2018.8.26.0053.pdf

# JSONs de saída
{cpf}_{numero_processo}.json
Exemplo: 12345678909_0035938-67.2018.8.26.0053.json
```

### **Validações Pydantic**
```python
class OficioRequisitorio(BaseModel):
    # Campos obrigatórios
    processo_origem: str = Field(..., pattern=r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
    requerente_caps: str = Field(..., min_length=3)
    
    # Campos opcionais com validação
    cpf: Optional[str] = Field(None, pattern=r'^\d{11}$')
    data_ajuizamento: Optional[date] = None
    
    # Validadores customizados
    @validator('requerente_caps')
    def uppercase_requerente(cls, v):
        return v.upper() if v else None
    
    @validator('valor_principal_liquido', pre=True)
    def parse_valor(cls, v):
        if isinstance(v, str):
            return float(v.replace('R$', '').replace('.', '').replace(',', '.'))
        return v
```

### **Logging**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Uso
logger.info(f"Processando PDF: {pdf_path}")
logger.warning(f"Gemini falhou, usando OpenAI")
logger.error(f"Erro validação: {e}")
```

---

## 🐛 Troubleshooting

### **Problema: Ofício não detectado**
```python
# Verificar critérios de detecção
print(f"Keywords encontradas: {keywords_count}")
print(f"Padrão CNJ encontrado: {cnj_found}")
print(f"Estrutura vara encontrada: {vara_found}")

# Mínimo 2/3 critérios necessários
```

### **Problema: Validação Pydantic falha**
```python
# Ver campos que falharam
try:
    oficio = OficioRequisitorio(**dados)
except ValidationError as e:
    print(e.json())  # Detalhe dos erros
```

### **Problema: Duplicatas no banco**
```sql
-- Verificar duplicatas
SELECT cpf, numero_processo, COUNT(*)
FROM lista_processos
GROUP BY cpf, numero_processo
HAVING COUNT(*) > 1;

-- Usar upsert para evitar
INSERT INTO lista_processos (...)
VALUES (...)
ON CONFLICT (cpf, numero_processo) 
DO UPDATE SET ...;
```

---

## 📞 Contatos e Links

- **Repositório:** https://github.com/revisaprecatorio/ocr-oficios-tjsp
- **VPS URL:** http://72.60.62.124:8501
- **Servidor:** srv987902.hstgr.cloud
- **Versão Atual:** v2.5.1 (14/11/2025)
- **Status:** ✅ Produção (96.1% taxa de sucesso)

---

**Última atualização:** 14/11/2025  
**Responsável:** Persival Balleste + Cascade AI  
**Commit:** 8ce295e
