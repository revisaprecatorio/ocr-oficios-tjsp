-- ============================================================================
-- QUERIES DE VALIDAÇÃO E TESTE
-- Descrição: Queries para validar a carga e explorar os dados
-- Versão: 1.0.0
-- Data: 14/10/2025
-- ============================================================================

-- ============================================================================
-- 1. ESTATÍSTICAS GERAIS
-- ============================================================================

-- Total de registros
SELECT COUNT(*) as total_processos 
FROM esaj_detalhe_processos;

-- Total por status
SELECT 
    rejeitado,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM esaj_detalhe_processos
GROUP BY rejeitado;

-- Total por diagnóstico
SELECT 
    process_diagnostico,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM esaj_detalhe_processos
GROUP BY process_diagnostico;

-- ============================================================================
-- 2. ANÁLISE POR CPF
-- ============================================================================

-- Processos por CPF (top 10)
SELECT 
    cpf,
    COUNT(*) as total_processos,
    SUM(CASE WHEN rejeitado = true THEN 1 ELSE 0 END) as rejeitados,
    SUM(CASE WHEN rejeitado = false THEN 1 ELSE 0 END) as aprovados
FROM esaj_detalhe_processos
GROUP BY cpf
ORDER BY total_processos DESC
LIMIT 10;

-- ============================================================================
-- 3. ANÁLISE FINANCEIRA
-- ============================================================================

-- Valor total requisitado (geral)
SELECT 
    COUNT(*) as total_processos,
    SUM(valor_total_requisitado) as valor_total,
    AVG(valor_total_requisitado) as valor_medio,
    MIN(valor_total_requisitado) as valor_minimo,
    MAX(valor_total_requisitado) as valor_maximo
FROM esaj_detalhe_processos
WHERE valor_total_requisitado IS NOT NULL;

-- Valor total por status
SELECT 
    rejeitado,
    COUNT(*) as total_processos,
    SUM(valor_total_requisitado) as valor_total,
    AVG(valor_total_requisitado) as valor_medio
FROM esaj_detalhe_processos
WHERE valor_total_requisitado IS NOT NULL
GROUP BY rejeitado;

-- ============================================================================
-- 4. ANÁLISE POR VARA
-- ============================================================================

-- Processos por vara (top 10)
SELECT 
    vara,
    COUNT(*) as total_processos,
    SUM(CASE WHEN rejeitado = true THEN 1 ELSE 0 END) as rejeitados,
    SUM(valor_total_requisitado) as valor_total
FROM esaj_detalhe_processos
WHERE vara IS NOT NULL
GROUP BY vara
ORDER BY total_processos DESC
LIMIT 10;

-- ============================================================================
-- 5. ANÁLISE DE PREFERÊNCIAS
-- ============================================================================

-- Distribuição de preferências
SELECT 
    'Idoso' as preferencia,
    COUNT(*) as total
FROM esaj_detalhe_processos
WHERE idoso = true
UNION ALL
SELECT 
    'Doença Grave' as preferencia,
    COUNT(*) as total
FROM esaj_detalhe_processos
WHERE doenca_grave = true
UNION ALL
SELECT 
    'PCD' as preferencia,
    COUNT(*) as total
FROM esaj_detalhe_processos
WHERE pcd = true;

-- ============================================================================
-- 6. ANÁLISE TEMPORAL
-- ============================================================================

-- Processos por ano de ajuizamento
SELECT 
    EXTRACT(YEAR FROM data_ajuizamento) as ano,
    COUNT(*) as total_processos,
    SUM(valor_total_requisitado) as valor_total
FROM esaj_detalhe_processos
WHERE data_ajuizamento IS NOT NULL
GROUP BY EXTRACT(YEAR FROM data_ajuizamento)
ORDER BY ano DESC;

-- ============================================================================
-- 7. QUALIDADE DOS DADOS
-- ============================================================================

-- Campos nulos (análise de completude)
SELECT 
    COUNT(*) as total,
    COUNT(numero_ordem) as tem_numero_ordem,
    COUNT(vara) as tem_vara,
    COUNT(data_ajuizamento) as tem_data_ajuizamento,
    COUNT(valor_total_requisitado) as tem_valor_total,
    COUNT(banco) as tem_dados_bancarios
FROM esaj_detalhe_processos;

-- Processos com anomalias
SELECT 
    anomalia,
    COUNT(*) as total
FROM esaj_detalhe_processos
GROUP BY anomalia;

-- ============================================================================
-- 8. ÚLTIMAS INGESTÕES
-- ============================================================================

-- Últimos 10 processos ingeridos
SELECT 
    cpf,
    numero_processo_cnj,
    requerente_caps,
    rejeitado,
    timestamp_ingestao
FROM esaj_detalhe_processos
ORDER BY timestamp_ingestao DESC
LIMIT 10;

-- ============================================================================
-- 9. PROCESSOS PENDENTES DE DIAGNÓSTICO
-- ============================================================================

-- Processos que precisam de diagnóstico
SELECT 
    cpf,
    numero_processo_cnj,
    requerente_caps,
    rejeitado,
    valor_total_requisitado
FROM esaj_detalhe_processos
WHERE process_diagnostico = false
ORDER BY timestamp_ingestao DESC
LIMIT 20;
