-- ============================================================================
-- QUERIES PARA INVESTIGAÇÃO DO BUG - VERSÃO 2
-- Execute estas queries no PostgreSQL da VPS
-- ============================================================================

-- Conectar:
-- PGPASSWORD="BetaAgent2024SecureDB" psql -h 72.60.62.124 -p 5432 -U admin -d n8n

-- ============================================================================
-- PASSO 1: DESCOBRIR TODAS AS TABELAS DO BANCO
-- ============================================================================

\dt

-- Ou via SQL:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- ============================================================================
-- PASSO 2: VER SCHEMA DA TABELA CORRETA
-- ============================================================================

-- Se for lista_processos:
\d lista_processos

-- Se for esaj_detalhe_processos:
\d esaj_detalhe_processos

-- ============================================================================
-- PASSO 3: BUSCAR O PROCESSO PROBLEMÁTICO
-- ============================================================================

-- Opção A: Se a tabela for lista_processos
SELECT *
FROM lista_processos
WHERE numero_processo = '0015796-15.2025.8.26.0500'
LIMIT 1;

-- Opção B: Se a tabela for esaj_detalhe_processos
SELECT *
FROM esaj_detalhe_processos
WHERE numero_processo_cnj = '0015796-15.2025.8.26.0500'
LIMIT 1;

-- ============================================================================
-- PASSO 4: BUSCAR POR CPF (273.081.578-30)
-- ============================================================================

-- Tentar ambas as tabelas:
SELECT 'lista_processos' as tabela, COUNT(*) as encontrados
FROM lista_processos
WHERE cpf = '27308157830'
UNION ALL
SELECT 'esaj_detalhe_processos' as tabela, COUNT(*) as encontrados
FROM esaj_detalhe_processos
WHERE cpf = '27308157830';

-- ============================================================================
-- PASSO 5: BUSCAR VALORES SUSPEITOS (88.99 vs 88994.41)
-- ============================================================================

-- Buscar valores próximos a 88.99 ou 88994.41 em ambas as tabelas

-- Em lista_processos (se existir):
SELECT 'lista_processos' as tabela,
       cpf,
       numero_processo,
       requerente_caps,
       valor_principal_liquido,
       valor_principal_bruto,
       valor_total_requisitado
FROM lista_processos
WHERE (valor_principal_liquido BETWEEN 88 AND 89000)
   OR (valor_principal_bruto BETWEEN 88 AND 89000)
   OR (valor_total_requisitado BETWEEN 88 AND 89000);

-- Em esaj_detalhe_processos (se existir):
SELECT 'esaj_detalhe_processos' as tabela,
       cpf,
       numero_processo_cnj,
       requerente_caps,
       valor_principal_liquido,
       valor_principal_bruto,
       valor_total_requisitado
FROM esaj_detalhe_processos
WHERE (valor_principal_liquido BETWEEN 88 AND 89000)
   OR (valor_principal_bruto BETWEEN 88 AND 89000)
   OR (valor_total_requisitado BETWEEN 88 AND 89000);

-- ============================================================================
-- PASSO 6: BUSCAR ESPECIFICAMENTE 88.99
-- ============================================================================

-- Em lista_processos:
SELECT 'lista_processos' as tabela, *
FROM lista_processos
WHERE valor_principal_liquido = 88.99
   OR valor_principal_bruto = 88.99
   OR valor_total_requisitado = 88.99;

-- Em esaj_detalhe_processos:
SELECT 'esaj_detalhe_processos' as tabela, *
FROM esaj_detalhe_processos
WHERE valor_principal_liquido = 88.99
   OR valor_principal_bruto = 88.99
   OR valor_total_requisitado = 88.99;

-- ============================================================================
-- PASSO 7: BUSCAR RODRIGO AZEVEDO FERRAO (requerente do processo)
-- ============================================================================

-- Em lista_processos:
SELECT 'lista_processos' as tabela, *
FROM lista_processos
WHERE requerente_caps LIKE '%RODRIGO%AZEVEDO%FERRAO%'
   OR requerente_caps LIKE '%RODRIGO AZEVEDO FERRAO%';

-- Em esaj_detalhe_processos:
SELECT 'esaj_detalhe_processos' as tabela, *
FROM esaj_detalhe_processos
WHERE requerente_caps LIKE '%RODRIGO%AZEVEDO%FERRAO%'
   OR requerente_caps LIKE '%RODRIGO AZEVEDO FERRAO%';

