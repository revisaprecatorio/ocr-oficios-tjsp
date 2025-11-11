-- ============================================================================
-- VALIDAÇÃO DOS TERMOS JURÍDICOS (v2.4.0)
-- ============================================================================

-- 1. Verificar se as colunas existem
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'esaj_detalhe_processos' 
  AND column_name IN ('preferencial', 'habilitacao_herdeiros', 'cessao_credito')
ORDER BY column_name;

-- 2. Estatísticas gerais dos termos
SELECT 
    COUNT(*) as total_registros,
    COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as com_preferencial,
    COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as com_habilitacao,
    COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as com_cessao,
    COUNT(CASE WHEN preferencial = TRUE OR habilitacao_herdeiros = TRUE OR cessao_credito = TRUE THEN 1 END) as com_algum_termo
FROM esaj_detalhe_processos;

-- 3. Distribuição detalhada
SELECT 
    'Preferencial' as termo,
    COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as quantidade,
    ROUND(100.0 * COUNT(CASE WHEN preferencial = TRUE THEN 1 END) / COUNT(*), 2) as percentual
FROM esaj_detalhe_processos
UNION ALL
SELECT 
    'Habilitação de Herdeiros',
    COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END),
    ROUND(100.0 * COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) / COUNT(*), 2)
FROM esaj_detalhe_processos
UNION ALL
SELECT 
    'Cessão de Crédito',
    COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END),
    ROUND(100.0 * COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) / COUNT(*), 2)
FROM esaj_detalhe_processos;

-- 4. Combinações de termos
SELECT 
    preferencial,
    habilitacao_herdeiros,
    cessao_credito,
    COUNT(*) as quantidade
FROM esaj_detalhe_processos
GROUP BY preferencial, habilitacao_herdeiros, cessao_credito
ORDER BY quantidade DESC;

-- 5. Amostra de registros com termos detectados
SELECT 
    cpf,
    numero_processo_cnj,
    requerente_caps,
    preferencial,
    habilitacao_herdeiros,
    cessao_credito
FROM esaj_detalhe_processos
WHERE preferencial = TRUE 
   OR habilitacao_herdeiros = TRUE 
   OR cessao_credito = TRUE
ORDER BY cpf
LIMIT 10;

-- 6. Verificar se algum registro tem todos os 3 termos
SELECT 
    cpf,
    numero_processo_cnj,
    requerente_caps,
    preferencial,
    habilitacao_herdeiros,
    cessao_credito
FROM esaj_detalhe_processos
WHERE preferencial = TRUE 
  AND habilitacao_herdeiros = TRUE 
  AND cessao_credito = TRUE;
