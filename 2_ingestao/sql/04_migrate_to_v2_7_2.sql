-- ========================================================================
-- MIGRATION: V2.7.1 → V2.7.2
-- ========================================================================
--
-- Remove campo requerente_caps que causa confusão em litisconsórcios.
--
-- MOTIVO:
-- - requerente_caps contém o nome do advogado/representante legal
-- - credor_nome contém o verdadeiro credor (extraído do ANEXO II)
-- - Em litisconsórcios (processo coletivo), requerente_caps é igual para
--   múltiplos credores diferentes, causando confusão visual
-- - Exemplo: CPF 03736870876 (ROBERTO FURIAN) e CPF 07692595887 (CICERO TAVARES)
--   ambos mostram requerente_caps = "LUIZ GONZAGA PRADO" (o advogado)
-- - Para o negócio, só importa credor_nome
--
-- ========================================================================

-- Remover coluna requerente_caps
ALTER TABLE esaj_detalhe_processos
    DROP COLUMN IF EXISTS requerente_caps CASCADE;

-- Verificar schema após migração
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'esaj_detalhe_processos'
ORDER BY ordinal_position;
