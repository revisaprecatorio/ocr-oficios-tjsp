-- =====================================================
-- MIGRATION V2.5.3 - Adicionar campos de Óbito e Sucessão
-- Data: 04/12/2025
-- Descrição: Adiciona 3 novos campos para detecção de habilitação de herdeiros
-- =====================================================

-- 1. Adicionar campo: obito (booleano)
ALTER TABLE esaj_detalhe_processos
ADD COLUMN IF NOT EXISTS obito BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN esaj_detalhe_processos.obito IS
'Indica se o requerente faleceu (detectado via Detector de Habilitação de Herdeiros V2.5.3)';

-- 2. Adicionar campo: data_obito (data)
ALTER TABLE esaj_detalhe_processos
ADD COLUMN IF NOT EXISTS data_obito DATE;

COMMENT ON COLUMN esaj_detalhe_processos.data_obito IS
'Data do óbito do requerente (extraída da seção "Dados da Sucessão" do formulário 9270)';

-- 3. Adicionar campo: cpf_sucessor (CPF formatado do herdeiro)
ALTER TABLE esaj_detalhe_processos
ADD COLUMN IF NOT EXISTS cpf_sucessor VARCHAR(14);

COMMENT ON COLUMN esaj_detalhe_processos.cpf_sucessor IS
'CPF do herdeiro/sucessor habilitado (formato: XXX.XXX.XXX-XX, extraído do formulário 9270)';

-- 4. Criar índice para consultas por óbito
CREATE INDEX IF NOT EXISTS idx_esaj_obito
ON esaj_detalhe_processos(obito)
WHERE obito = TRUE;

-- 5. Criar índice para consultas por CPF sucessor
CREATE INDEX IF NOT EXISTS idx_esaj_cpf_sucessor
ON esaj_detalhe_processos(cpf_sucessor)
WHERE cpf_sucessor IS NOT NULL;

-- =====================================================
-- VERIFICAÇÃO (executar após migration)
-- =====================================================
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'esaj_detalhe_processos'
--   AND column_name IN ('obito', 'data_obito', 'cpf_sucessor')
-- ORDER BY ordinal_position;

-- =====================================================
-- ROLLBACK (caso necessário)
-- =====================================================
-- ALTER TABLE esaj_detalhe_processos DROP COLUMN IF EXISTS obito;
-- ALTER TABLE esaj_detalhe_processos DROP COLUMN IF EXISTS data_obito;
-- ALTER TABLE esaj_detalhe_processos DROP COLUMN IF EXISTS cpf_sucessor;
-- DROP INDEX IF EXISTS idx_esaj_obito;
-- DROP INDEX IF EXISTS idx_esaj_cpf_sucessor;
