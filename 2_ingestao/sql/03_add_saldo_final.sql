-- ============================================================================
-- MIGRATION: Adicionar coluna saldo_final
-- Descrição: Novo campo para armazenar saldo final após pagamento parcial
-- Versão: V2.5.2
-- Data: 04/12/2025
-- ============================================================================

-- ============================================================================
-- PARTE 1: Adicionar coluna saldo_final
-- ============================================================================

ALTER TABLE esaj_detalhe_processos
ADD COLUMN IF NOT EXISTS saldo_final NUMERIC(15,2);

-- ============================================================================
-- PARTE 2: Adicionar comentário à coluna
-- ============================================================================

COMMENT ON COLUMN esaj_detalhe_processos.saldo_final IS
'Saldo final após pagamento parcial. Se não houver pagamento parcial, igual a valor_total_requisitado. Campo detectado via regex ou LLM (V2.5.2)';

-- ============================================================================
-- PARTE 3: Preencher valores NULL com valor_total_requisitado (dados históricos)
-- ============================================================================

-- Para registros existentes, usar valor_total_requisitado como fallback
UPDATE esaj_detalhe_processos
SET saldo_final = valor_total_requisitado
WHERE saldo_final IS NULL AND valor_total_requisitado IS NOT NULL;

-- ============================================================================
-- PARTE 4 (OPCIONAL): Limpar dados da tabela para testes
-- ATENÇÃO: Descomente apenas se quiser LIMPAR TODOS OS DADOS!
-- ============================================================================

-- TRUNCATE TABLE esaj_detalhe_processos CASCADE;

-- ============================================================================
-- VERIFICAÇÃO: Contar registros atualizados
-- ============================================================================

-- SELECT
--     COUNT(*) as total_registros,
--     COUNT(saldo_final) as registros_com_saldo_final,
--     COUNT(*) - COUNT(saldo_final) as registros_sem_saldo_final
-- FROM esaj_detalhe_processos;

-- ============================================================================
-- FIM DA MIGRATION
-- ============================================================================
