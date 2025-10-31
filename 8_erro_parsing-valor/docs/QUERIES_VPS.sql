-- QUERIES PARA INVESTIGAÇÃO DO BUG
-- Execute estas queries no PostgreSQL da VPS
-- Conectar: PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n

-- ============================================================================
-- 1. VER SCHEMA DA TABELA lista_processos
-- ============================================================================

\d lista_processos

-- ============================================================================
-- 2. LISTAR TODAS AS COLUNAS DA TABELA
-- ============================================================================

SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'lista_processos'
ORDER BY ordinal_position;

-- ============================================================================
-- 3. BUSCAR O PROCESSO PROBLEMÁTICO (apenas por numero_processo)
-- ============================================================================

SELECT *
FROM lista_processos
WHERE numero_processo = '0015796-15.2025.8.26.0500';

-- ============================================================================
-- 4. BUSCAR POR CPF (caso numero_processo não exista)
-- ============================================================================

SELECT *
FROM lista_processos
WHERE cpf = '27308157830';

-- ============================================================================
-- 5. BUSCAR PROCESSOS COM VALORES SUSPEITOS (88.99 ou 88994.41)
-- ============================================================================

-- Buscar por 88.99
SELECT 
    cpf,
    numero_processo,
    requerente_caps,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    timestamp_processamento
FROM lista_processos
WHERE valor_principal_liquido = 88.99
   OR valor_principal_bruto = 88.99
   OR valor_total_requisitado = 88.99;

-- Buscar por 88994.41
SELECT 
    cpf,
    numero_processo,
    requerente_caps,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    timestamp_processamento
FROM lista_processos
WHERE valor_principal_liquido = 88994.41
   OR valor_principal_bruto = 88994.41
   OR valor_total_requisitado = 88994.41;

-- ============================================================================
-- 6. VERIFICAR TODOS OS PROCESSOS DO CPF 273.081.578-30
-- ============================================================================

SELECT 
    cpf,
    numero_processo,
    requerente_caps,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    timestamp_processamento
FROM lista_processos
WHERE cpf = '27308157830'
ORDER BY timestamp_processamento DESC;

-- ============================================================================
-- 7. ESTATÍSTICAS DA TABELA
-- ============================================================================

SELECT 
    COUNT(*) as total_processos,
    COUNT(DISTINCT cpf) as total_cpfs,
    MIN(timestamp_processamento) as primeiro_processamento,
    MAX(timestamp_processamento) as ultimo_processamento
FROM lista_processos;

