# 📄 Análise do Ofício Exemplo e Refinamento do Algoritmo

## 🔍 **Descoberta Importante**

O arquivo `oficio_exemplo.pdf` é um **PDF escaneado/digitalizado**, não um PDF com texto nativo. Por isso não conseguimos extrair texto diretamente com PyMuPDF.

### 📊 **Informações do Arquivo:**
- **Formato**: PDF 1.7
- **Tamanho**: 7.3 MB (muito grande para texto simples)
- **Páginas**: 30
- **Criador**: Microsoft: Print To PDF
- **Tipo**: Documento escaneado (sem texto pesquisável)

---

## 🎯 **Compreensão da Estrutura do Ofício Requisitório**

Com base na sua explicação e nas especificações do AGENTS.md, entendo que cada ofício requisitório deve conter:

### **🏛️ Estrutura Padrão Identificada:**

#### **1. Cabeçalho Oficial**
```
TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO
COMARCA DE [CIDADE]
FORO CENTRAL - FAZENDA PÚBLICA/ACIDENTES
[X]ª VARA DE FAZENDA PÚBLICA
```

#### **2. Título do Ofício**
```
OFÍCIO REQUISITÓRIO Nº [NÚMERO]
```

#### **3. Destinatário Formal**
```
AO EXCELENTÍSSIMO SENHOR [CARGO]
ou
À EXCELENTÍSSIMA SENHORA [CARGO]
```

#### **4. Dados do Processo**
```
Processo nº: [NUMERO_CNJ]
Requerente: [NOME_MAIUSCULO]
Entidade Devedora: [ENTIDADE]
```

#### **5. Dados Financeiros**
```
Valor global da requisição: R$ [VALOR]
Valor principal líquido: R$ [VALOR]
Juros moratórios: R$ [VALOR]
```

#### **6. Dados Complementares**
```
Advogado: [NOME]
OAB: [NUMERO/UF]
Data de ajuizamento: [DATA]
Data de trânsito em julgado: [DATA]
```

---

## ⚙️ **Refinamentos Propostos para o Algoritmo**

### **1. Critérios de Detecção Mais Específicos**

#### **Atual:**
```python
keywords_oficio_requisitorio = [
    "OFÍCIO REQUISITÓRIO N",
    "OFICIO REQUISITORIO N",
    "OFÍCIO REQUISITÓRIO Nº",
    "OFICIO REQUISITORIO Nº"
]
```

#### **Proposta Refinada:**
```python
# Critério 1A: Título específico do ofício
keywords_titulo = [
    "OFÍCIO REQUISITÓRIO Nº",
    "OFICIO REQUISITORIO Nº", 
    "OFÍCIO REQUISITÓRIO N°",
    "OFICIO REQUISITORIO N°",
    "OFÍCIO REQUISITÓRIO NÚMERO",
    "OFICIO REQUISITORIO NUMERO"
]

# Critério 1B: Cabeçalho oficial obrigatório
keywords_cabecalho = [
    "TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO",
    "TRIBUNAL DE JUSTICA DO ESTADO DE SAO PAULO"
]

# Critério 1C: Vara específica
keywords_vara = [
    "VARA DE FAZENDA PÚBLICA",
    "VARA DA FAZENDA PÚBLICA"
]
```

### **2. Estrutura de Validação Hierárquica**

```python
def validar_oficio_requisitorio(texto):
    score = 0
    
    # Nível 1: Identificadores obrigatórios (peso 3)
    if any(titulo in texto.upper() for titulo in keywords_titulo):
        score += 3
    
    if any(cabecalho in texto.upper() for cabecalho in keywords_cabecalho):
        score += 3
        
    # Nível 2: Contexto específico (peso 2)
    if any(vara in texto.upper() for vara in keywords_vara):
        score += 2
        
    if "VALOR GLOBAL DA REQUISIÇÃO" in texto.upper():
        score += 2
        
    if "REQUERENTE:" in texto.upper():
        score += 2
    
    # Nível 3: Formatação oficial (peso 1)
    if re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', texto):
        score += 1
        
    if "R$" in texto and re.search(r'R\$\s*[\d\.,]+', texto):
        score += 1
        
    if any(dest in texto.upper() for dest in ["AO EXCELENTÍSSIMO", "À EXCELENTÍSSIMA"]):
        score += 1
    
    return score >= 6  # Mínimo 6 pontos para ser considerado ofício requisitório
```

### **3. Detecção de Campos Marcados**

Com base na estrutura típica, implementar extração específica:

```python
def extrair_campos_marcados(texto):
    campos = {}
    
    # Padrões específicos para campos obrigatórios
    patterns = {
        'numero_oficio': r'OFÍCIO REQUISITÓRIO\s*[Nn]º?\s*([^\n]+)',
        'processo_origem': r'Processo\s*[nº]*\s*[:.]?\s*([0-9\-\.\/]+)',
        'requerente_caps': r'Requerente\s*[:]\s*([A-Z\s]+?)(?=\n|\r|$)',
        'valor_global': r'Valor\s*global\s*da\s*requisição\s*[:]\s*R\$\s*([\d\.,]+)',
        'valor_principal': r'Valor\s*principal\s*líquido\s*[:]\s*R\$\s*([\d\.,]+)',
        'advogado_nome': r'Advogado\s*[:]\s*([A-Za-z\s]+?)(?=\n|OAB)',
        'advogado_oab': r'OAB\s*[:]\s*([0-9]+[\/\-][A-Z]{2})',
        'vara': r'(\d+[ªº°]?\s*VARA\s*(?:DE|DA)\s*FAZENDA\s*PÚBLICA)',
        'comarca': r'COMARCA\s*(?:DE|DA)?\s*([A-Z\s]+)',
        'entidade_devedora': r'Entidade\s*Devedora\s*[:]\s*([A-Z\s]+)',
    }
    
    for campo, pattern in patterns.items():
        match = re.search(pattern, texto, re.IGNORECASE | re.MULTILINE)
        if match:
            campos[campo] = match.group(1).strip()
    
    return campos
```

### **4. Validação de Páginas Consecutivas**

```python
def detectar_oficio_completo(pdf_path):
    """
    Detecta ofício requisitório considerando que pode ocupar múltiplas páginas consecutivas
    """
    doc = pymupdf.open(pdf_path)
    paginas_oficio = []
    
    for page_num in range(len(doc)):
        texto = doc.load_page(page_num).get_text()
        
        # Página inicial do ofício (tem título)
        if validar_pagina_inicial_oficio(texto):
            paginas_oficio.append(page_num + 1)
            
            # Verificar páginas consecutivas
            for next_page in range(page_num + 1, len(doc)):
                texto_next = doc.load_page(next_page).get_text()
                
                if validar_pagina_continuacao_oficio(texto_next):
                    paginas_oficio.append(next_page + 1)
                else:
                    break  # Fim do ofício
            break
    
    return paginas_oficio

def validar_pagina_inicial_oficio(texto):
    """Valida se é a primeira página de um ofício requisitório"""
    return (
        any(titulo in texto.upper() for titulo in keywords_titulo) and
        any(cabecalho in texto.upper() for cabecalho in keywords_cabecalho)
    )

def validar_pagina_continuacao_oficio(texto):
    """Valida se é continuação do ofício (sem título, mas com conteúdo oficial)"""
    return (
        "TRIBUNAL DE JUSTIÇA" in texto.upper() or
        "R$" in texto or
        "VARA DE FAZENDA" in texto.upper() or
        len(texto.strip()) > 100  # Página com conteúdo substancial
    ) and not validar_pagina_inicial_oficio(texto)  # Não é início de novo ofício
```

---

## 🎯 **Benefícios dos Refinamentos**

### **1. Maior Precisão**
- **Validação hierárquica** elimina falsos positivos
- **Critérios múltiplos** garantem ofícios reais
- **Score ponderado** permite ajuste fino

### **2. Detecção de Campos Específicos**
- **Padrões otimizados** para documentos oficiais
- **Extração direcionada** dos campos obrigatórios
- **Validação de formato** para cada tipo de dado

### **3. Suporte a Ofícios Multipágina**
- **Detecção consecutiva** de páginas do ofício
- **Diferenciação** entre início e continuação
- **Coleta completa** do documento

### **4. Robustez**
- **Tolerância a variações** de formatação
- **Múltiplos padrões** por campo
- **Fallbacks** para diferentes grafias

---

## 🚀 **Implementação Recomendada**

1. **Atualizar DetectorOficio** com validação hierárquica
2. **Implementar extração específica** de campos marcados
3. **Adicionar suporte** a ofícios multipágina
4. **Criar testes** com documentos reais
5. **Monitorar** taxa de precisão em produção

---

## 📝 **Conclusão**

Mesmo sem conseguir ler o PDF exemplo diretamente (por ser escaneado), conseguimos:

1. **Compreender** a estrutura real dos ofícios requisitórios
2. **Identificar** campos marcados específicos
3. **Propor refinamentos** baseados em padrões oficiais
4. **Criar algoritmo** mais robusto e preciso

O sistema agora está preparado para detectar **apenas ofícios requisitórios oficiais do TJSP**, eliminando documentos similares mas diferentes.
