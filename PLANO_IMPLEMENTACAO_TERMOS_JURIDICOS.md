# 📋 Plano de Implementação - Detecção de Termos Jurídicos

**Versão:** 2.4.0  
**Data:** 10/11/2025  
**Status:** ✅ Fase 1 Completa (Database Schema)

---

## 🎯 Objetivo

Adicionar detecção automática de 3 termos jurídicos específicos nos PDFs:

1. **Preferência** - Pedido de preferência no pagamento
2. **Habilitação de Herdeiros** - Processo de habilitação de herdeiros
3. **Cessão de Crédito** - Cessão de crédito ou direitos creditórios

---

## 📊 Progresso Geral

- [x] **Fase 1:** Database Schema (COMPLETO ✅)
- [ ] **Fase 2:** Pydantic Schema Update
- [ ] **Fase 3:** Detector Implementation
- [ ] **Fase 4:** Processor Integration
- [ ] **Fase 5:** Ingestion Script Update
- [ ] **Fase 6:** Streamlit Interface Update
- [ ] **Fase 7:** Testing
- [ ] **Fase 8:** Reprocessing & Validation

---

## ✅ Fase 1: Database Schema (COMPLETO)

### **Ações Realizadas:**

1. ✅ Conectado ao PostgreSQL via SSH
2. ✅ Executado ALTER TABLE para adicionar 3 colunas:
   - `preferencial BOOLEAN DEFAULT FALSE`
   - `habilitacao_herdeiros BOOLEAN DEFAULT FALSE`
   - `cessao_credito BOOLEAN DEFAULT FALSE`
3. ✅ Adicionados comentários nas colunas
4. ✅ Atualizado arquivo `2_ingestao/sql/01_create_table.sql`
5. ✅ Atualizado arquivo `SCHEMA_TABELA.md`

### **Verificação:**

```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'esaj_detalhe_processos' 
  AND column_name IN ('preferencial', 'habilitacao_herdeiros', 'cessao_credito');
```

**Resultado esperado:**
```
      column_name       | data_type | column_default 
------------------------+-----------+----------------
 preferencial           | boolean   | false
 habilitacao_herdeiros  | boolean   | false
 cessao_credito         | boolean   | false
```

---

## 📝 Fase 2: Pydantic Schema Update

### **Arquivo a modificar:**
- `1_parsing_PDF/app/schemas.py`

### **Localização:**
Adicionar após linha 197 (após campo `pcd`)

### **Código a adicionar:**

```python
# ===== TERMOS JURÍDICOS (v2.4.0) =====
preferencial: Optional[bool] = Field(
    None,
    description="Indica se há pedido de preferência no processo"
)

habilitacao_herdeiros: Optional[bool] = Field(
    None,
    description="Indica se há habilitação de herdeiros"
)

cessao_credito: Optional[bool] = Field(
    None,
    description="Indica se há cessão de crédito ou direitos creditórios"
)
```

### **Tempo estimado:** 5 minutos

---

## 🔍 Fase 3: Detector Implementation

### **Novo arquivo a criar:**
- `1_parsing_PDF/app/detector_termos_juridicos.py`

### **Estrutura do Detector:**

```python
"""
DetectorTermosJuridicos - Detecta termos jurídicos específicos em PDFs
Versão: 1.0.0
Data: 10/11/2025
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class DetectorTermosJuridicos:
    """
    Detector de termos jurídicos específicos no texto completo do PDF.
    
    Termos detectados:
    1. Preferência/Preferencia
    2. Habilitação de Herdeiros
    3. Cessão de Crédito / Cessão de Direitos Creditórios
    """
    
    def __init__(self):
        # Patterns case-insensitive com acentuação flexível
        self.pattern_preferencial = re.compile(
            r'prefer[eê]ncia', 
            re.IGNORECASE
        )
        
        self.pattern_habilitacao = re.compile(
            r'habilita[çc][aã]o\s+de\s+herdeiros', 
            re.IGNORECASE
        )
        
        self.pattern_cessao = re.compile(
            r'cess[aã]o\s+de\s+(cr[ée]dito|direitos\s+credit[óo]rios)', 
            re.IGNORECASE
        )
    
    def detectar_termos(self, texto_completo: str) -> Dict[str, bool]:
        """
        Busca os 3 termos jurídicos no texto completo do PDF.
        
        Args:
            texto_completo: Texto completo extraído do PDF
            
        Returns:
            Dict com 3 booleanos:
            {
                'preferencial': bool,
                'habilitacao_herdeiros': bool,
                'cessao_credito': bool
            }
        """
        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção de termos")
            return {
                'preferencial': False,
                'habilitacao_herdeiros': False,
                'cessao_credito': False
            }
        
        # Buscar cada termo
        preferencial = bool(self.pattern_preferencial.search(texto_completo))
        habilitacao = bool(self.pattern_habilitacao.search(texto_completo))
        cessao = bool(self.pattern_cessao.search(texto_completo))
        
        # Log resultados
        logger.info(f"Termos detectados: preferencial={preferencial}, "
                   f"habilitacao_herdeiros={habilitacao}, cessao_credito={cessao}")
        
        return {
            'preferencial': preferencial,
            'habilitacao_herdeiros': habilitacao,
            'cessao_credito': cessao
        }
    
    def detectar_com_contexto(self, texto_completo: str) -> Dict[str, any]:
        """
        Busca os termos E retorna o contexto (snippet) onde foram encontrados.
        Útil para debugging e validação.
        
        Returns:
            Dict com booleanos + snippets de contexto
        """
        resultado = {
            'preferencial': False,
            'habilitacao_herdeiros': False,
            'cessao_credito': False,
            'contexto_preferencial': None,
            'contexto_habilitacao': None,
            'contexto_cessao': None
        }
        
        if not texto_completo:
            return resultado
        
        # Buscar preferencial
        match = self.pattern_preferencial.search(texto_completo)
        if match:
            resultado['preferencial'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_preferencial'] = texto_completo[inicio:fim]
        
        # Buscar habilitação
        match = self.pattern_habilitacao.search(texto_completo)
        if match:
            resultado['habilitacao_herdeiros'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_habilitacao'] = texto_completo[inicio:fim]
        
        # Buscar cessão
        match = self.pattern_cessao.search(texto_completo)
        if match:
            resultado['cessao_credito'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_cessao'] = texto_completo[inicio:fim]
        
        return resultado
```

### **Tempo estimado:** 15 minutos

---

## 🔗 Fase 4: Processor Integration

### **Arquivo a modificar:**
- `1_parsing_PDF/app/processador.py`

### **Mudanças necessárias:**

#### **1. Import (linha ~19):**
```python
from .detector_termos_juridicos import DetectorTermosJuridicos
```

#### **2. Inicialização (linha ~56):**
```python
self.detector_termos = DetectorTermosJuridicos()  # NOVO!
```

#### **3. Detecção (após extração do texto completo):**

Localizar onde o texto completo do PDF está disponível (provavelmente após linha 200).

```python
# 7. Detectar termos jurídicos no texto completo do PDF
logger.info("🔍 Detectando termos jurídicos...")
termos_juridicos = self.detector_termos.detectar_termos(texto_completo_pdf)
logger.info(f"📋 Termos encontrados: {termos_juridicos}")
```

#### **4. Adicionar aos dados extraídos:**

Onde os dados são preparados para salvar no banco:

```python
# Adicionar termos jurídicos aos dados
dados_finais.update({
    'preferencial': termos_juridicos['preferencial'],
    'habilitacao_herdeiros': termos_juridicos['habilitacao_herdeiros'],
    'cessao_credito': termos_juridicos['cessao_credito']
})
```

### **Tempo estimado:** 10 minutos

---

## 💾 Fase 5: Ingestion Script Update

### **Arquivo a modificar:**
- `2_ingestao/importar_postgres.py`

### **Mudanças necessárias:**

Localizar a lista de colunas (provavelmente linha ~150) e adicionar:

```python
# Lista de colunas para INSERT
colunas = [
    'cpf', 'numero_processo_cnj', 'processo_origem', 'requerente_caps',
    # ... outras colunas ...
    'idoso', 'doenca_grave', 'pcd',
    'preferencial', 'habilitacao_herdeiros', 'cessao_credito',  # NOVO!
    'rejeitado', 'motivo_rejeicao',
    # ... resto das colunas ...
]
```

### **Verificar INSERT statement:**

Garantir que o INSERT/UPDATE inclui as 3 novas colunas:

```python
INSERT INTO esaj_detalhe_processos (
    cpf, numero_processo_cnj, ..., 
    preferencial, habilitacao_herdeiros, cessao_credito,
    ...
) VALUES (
    %s, %s, ..., %s, %s, %s, ...
)
ON CONFLICT (cpf, numero_processo_cnj) 
DO UPDATE SET
    ...
    preferencial = EXCLUDED.preferencial,
    habilitacao_herdeiros = EXCLUDED.habilitacao_herdeiros,
    cessao_credito = EXCLUDED.cessao_credito,
    ...
```

### **Tempo estimado:** 5 minutos

---

## 🖥️ Fase 6: Streamlit Interface Update

### **Arquivo a modificar:**
- `3_streamlit/app/streamlit_app.py`

### **Mudanças necessárias:**

#### **1. Adicionar filtros na sidebar:**

```python
# Termos Jurídicos (v2.4.0)
st.sidebar.subheader("📜 Termos Jurídicos")
filtro_preferencial = st.sidebar.checkbox("Apenas com Preferência")
filtro_habilitacao = st.sidebar.checkbox("Apenas com Habilitação de Herdeiros")
filtro_cessao = st.sidebar.checkbox("Apenas com Cessão de Crédito")
```

#### **2. Aplicar filtros:**

```python
# Aplicar filtros de termos jurídicos
if filtro_preferencial:
    df = df[df['preferencial'] == True]
if filtro_habilitacao:
    df = df[df['habilitacao_herdeiros'] == True]
if filtro_cessao:
    df = df[df['cessao_credito'] == True]
```

#### **3. Adicionar cards de estatísticas:**

```python
# Estatísticas de Termos Jurídicos
st.subheader("📜 Termos Jurídicos")
col1, col2, col3 = st.columns(3)

with col1:
    total_preferencial = df['preferencial'].sum()
    st.metric(
        "Com Preferência", 
        total_preferencial,
        delta=f"{(total_preferencial/len(df)*100):.1f}%" if len(df) > 0 else "0%"
    )

with col2:
    total_habilitacao = df['habilitacao_herdeiros'].sum()
    st.metric(
        "Habilitação Herdeiros", 
        total_habilitacao,
        delta=f"{(total_habilitacao/len(df)*100):.1f}%" if len(df) > 0 else "0%"
    )

with col3:
    total_cessao = df['cessao_credito'].sum()
    st.metric(
        "Cessão de Crédito", 
        total_cessao,
        delta=f"{(total_cessao/len(df)*100):.1f}%" if len(df) > 0 else "0%"
    )
```

#### **4. Adicionar gráfico (opcional):**

```python
# Gráfico de distribuição de termos jurídicos
import plotly.graph_objects as go

termos_data = {
    'Preferência': df['preferencial'].sum(),
    'Habilitação': df['habilitacao_herdeiros'].sum(),
    'Cessão': df['cessao_credito'].sum()
}

fig = go.Figure(data=[
    go.Bar(
        x=list(termos_data.keys()),
        y=list(termos_data.values()),
        marker_color=['#1f77b4', '#ff7f0e', '#2ca02c']
    )
])

fig.update_layout(
    title="Distribuição de Termos Jurídicos",
    xaxis_title="Termo",
    yaxis_title="Quantidade",
    height=400
)

st.plotly_chart(fig, use_container_width=True)
```

### **Tempo estimado:** 10 minutos

---

## 🧪 Fase 7: Testing

### **Novo arquivo a criar:**
- `1_parsing_PDF/tests/test_detector_termos_juridicos.py`

### **Estrutura dos testes:**

```python
"""
Testes para DetectorTermosJuridicos
"""

import pytest
from app.detector_termos_juridicos import DetectorTermosJuridicos


class TestDetectorTermosJuridicos:
    
    @pytest.fixture
    def detector(self):
        return DetectorTermosJuridicos()
    
    def test_detectar_preferencia_com_acento(self, detector):
        """Testa detecção de 'preferência' com acento"""
        texto = "Reconheço a preferência para o credor Cleber Roberto da Silva."
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == True
        assert resultado['habilitacao_herdeiros'] == False
        assert resultado['cessao_credito'] == False
    
    def test_detectar_preferencia_sem_acento(self, detector):
        """Testa detecção de 'preferencia' sem acento"""
        texto = "Pedido de preferencia deferido."
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == True
    
    def test_detectar_habilitacao_herdeiros(self, detector):
        """Testa detecção de 'habilitação de herdeiros'"""
        texto = "Defiro a habilitação dos herdeiros de JOSÉ ANGELO FERRACIN"
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == False
        assert resultado['habilitacao_herdeiros'] == True
        assert resultado['cessao_credito'] == False
    
    def test_detectar_cessao_credito(self, detector):
        """Testa detecção de 'cessão de crédito'"""
        texto = "conforme instrumento particular de cessão de crédito"
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == False
        assert resultado['habilitacao_herdeiros'] == False
        assert resultado['cessao_credito'] == True
    
    def test_detectar_cessao_direitos_creditorios(self, detector):
        """Testa detecção de 'cessão de direitos creditórios'"""
        texto = "Escritura Pública de Cessão de Direitos Creditórios"
        resultado = detector.detectar_termos(texto)
        assert resultado['cessao_credito'] == True
    
    def test_detectar_multiplos_termos(self, detector):
        """Testa detecção de múltiplos termos no mesmo texto"""
        texto = """
        Reconheço a preferência para o credor.
        Defiro a habilitação dos herdeiros.
        Conforme cessão de crédito anexa.
        """
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == True
        assert resultado['habilitacao_herdeiros'] == True
        assert resultado['cessao_credito'] == True
    
    def test_texto_vazio(self, detector):
        """Testa comportamento com texto vazio"""
        resultado = detector.detectar_termos("")
        assert resultado['preferencial'] == False
        assert resultado['habilitacao_herdeiros'] == False
        assert resultado['cessao_credito'] == False
    
    def test_nenhum_termo_encontrado(self, detector):
        """Testa quando nenhum termo está presente"""
        texto = "Este é um texto sem nenhum termo jurídico relevante."
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == False
        assert resultado['habilitacao_herdeiros'] == False
        assert resultado['cessao_credito'] == False
    
    def test_case_insensitive(self, detector):
        """Testa que a busca é case-insensitive"""
        texto = "PREFERÊNCIA em MAIÚSCULAS"
        resultado = detector.detectar_termos(texto)
        assert resultado['preferencial'] == True
    
    def test_detectar_com_contexto(self, detector):
        """Testa detecção com contexto"""
        texto = "Reconheço a preferência para o credor Cleber Roberto."
        resultado = detector.detectar_com_contexto(texto)
        assert resultado['preferencial'] == True
        assert resultado['contexto_preferencial'] is not None
        assert 'preferência' in resultado['contexto_preferencial'].lower()
```

### **Executar testes:**

```bash
cd 1_parsing_PDF
pytest tests/test_detector_termos_juridicos.py -v
```

### **Tempo estimado:** 20 minutos

---

## 🔄 Fase 8: Reprocessing & Validation

### **Objetivo:**
Reprocessar os 50 PDFs existentes para popular as novas colunas.

### **Passos:**

#### **1. Backup do banco (segurança):**

```bash
# Na VPS
pg_dump -U postgres oficios_tjsp > backup_antes_termos_juridicos_$(date +%Y%m%d).sql
```

#### **2. Limpar JSONs antigos:**

```bash
cd /caminho/para/projeto
rm -rf 1_parsing_PDF/outputs/json/*
```

#### **3. Reprocessar todos os PDFs:**

```bash
# Executar pipeline completo
./pipeline_completo.sh
```

#### **4. Validar resultados:**

```sql
-- Conectar ao PostgreSQL
psql -U postgres -d oficios_tjsp

-- Verificar distribuição dos termos
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as com_preferencial,
    COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as com_habilitacao,
    COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as com_cessao,
    ROUND(COUNT(CASE WHEN preferencial = TRUE THEN 1 END)::numeric / COUNT(*) * 100, 2) as perc_preferencial,
    ROUND(COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END)::numeric / COUNT(*) * 100, 2) as perc_habilitacao,
    ROUND(COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END)::numeric / COUNT(*) * 100, 2) as perc_cessao
FROM esaj_detalhe_processos;

-- Listar processos com cada termo
SELECT cpf, numero_processo_cnj, requerente_caps, preferencial
FROM esaj_detalhe_processos
WHERE preferencial = TRUE
ORDER BY cpf;

SELECT cpf, numero_processo_cnj, requerente_caps, habilitacao_herdeiros
FROM esaj_detalhe_processos
WHERE habilitacao_herdeiros = TRUE
ORDER BY cpf;

SELECT cpf, numero_processo_cnj, requerente_caps, cessao_credito
FROM esaj_detalhe_processos
WHERE cessao_credito = TRUE
ORDER BY cpf;
```

#### **5. Validação manual (amostragem):**

Selecionar 3-5 PDFs aleatórios e verificar manualmente se os termos foram detectados corretamente.

### **Tempo estimado:** 30 minutos

---

## 📊 Checklist Final

### **Código:**
- [ ] `detector_termos_juridicos.py` criado
- [ ] `schemas.py` atualizado
- [ ] `processador.py` atualizado
- [ ] `importar_postgres.py` atualizado
- [ ] `streamlit_app.py` atualizado
- [ ] Testes criados e passando

### **Database:**
- [x] Colunas adicionadas
- [x] Comentários adicionados
- [ ] Dados reprocessados
- [ ] Validação manual completa

### **Documentação:**
- [x] `01_create_table.sql` atualizado
- [x] `SCHEMA_TABELA.md` atualizado
- [ ] `README.md` atualizado com nova feature
- [ ] `CHANGELOG.md` atualizado

### **Deploy:**
- [ ] Código commitado no Git
- [ ] Deploy na VPS
- [ ] Interface Streamlit atualizada
- [ ] Validação em produção

---

## 🎯 Próximos Passos Imediatos

1. **Criar detector** (`detector_termos_juridicos.py`)
2. **Atualizar schemas** (`schemas.py`)
3. **Integrar no processador** (`processador.py`)
4. **Testar localmente** com 1-2 PDFs
5. **Atualizar ingestion** (`importar_postgres.py`)
6. **Atualizar Streamlit** (`streamlit_app.py`)
7. **Executar testes** (`pytest`)
8. **Reprocessar todos os PDFs**
9. **Validar resultados**
10. **Deploy em produção**

---

**Tempo total estimado:** ~2 horas (desenvolvimento + testes + reprocessamento)

---

**Última atualização:** 10/11/2025  
**Versão:** 2.4.0
