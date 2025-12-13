-- ========================================================================
-- MIGRATION: V2.6.0 → V2.7.1
-- ========================================================================
--
-- Remove 7 campos desnecessários que foram eliminados no V2.7.1:
--
-- 1. data_ajuizamento
-- 2. data_transito_julgado
-- 3. advogado_nome
-- 4. advogado_oab
-- 5. cessao_credito
-- 6. anexo_ii
-- 7. process_diagnostico
--
-- Estes campos não são necessários para o negócio e foram removidos
-- para simplificar o modelo de dados e reduzir custos de LLM.
--
-- ========================================================================

-- Backup antes da migração (opcional)
-- CREATE TABLE esaj_detalhe_processos_backup_v2_6_0 AS
-- SELECT * FROM esaj_detalhe_processos;

-- Remover colunas V2.6.0 que não existem mais em V2.7.1
ALTER TABLE esaj_detalhe_processos
    DROP COLUMN IF EXISTS data_ajuizamento,
    DROP COLUMN IF EXISTS data_transito_julgado,
    DROP COLUMN IF EXISTS advogado_nome,
    DROP COLUMN IF EXISTS advogado_oab,
    DROP COLUMN IF EXISTS cessao_credito,
    DROP COLUMN IF EXISTS anexo_ii,
    DROP COLUMN IF EXISTS process_diagnostico;

-- Verificar schema após migração
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'esaj_detalhe_processos'
ORDER BY ordinal_position;
