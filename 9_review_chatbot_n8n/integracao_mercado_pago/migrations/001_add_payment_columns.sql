-- ============================================================
-- Migration: 001_add_payment_columns.sql
-- Descrição: Adiciona colunas para integração Mercado Pago
-- Data: 2025-12-10
-- ============================================================

-- Verificar estrutura atual da tabela (execute primeiro para confirmar)
-- \d consultas_esaj

-- ============================================================
-- PASSO 1: Adicionar colunas de pagamento
-- ============================================================

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS mp_preference_id VARCHAR(255);

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS mp_payment_id VARCHAR(255);

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS mp_payment_status VARCHAR(50);

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS mp_payment_amount DECIMAL(10,2);

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS mp_external_reference VARCHAR(255);

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS payment_link TEXT;

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS payment_created_at TIMESTAMP;

ALTER TABLE consultas_esaj 
ADD COLUMN IF NOT EXISTS payment_confirmed_at TIMESTAMP;

-- ============================================================
-- PASSO 2: Criar índices para performance
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_consultas_mp_preference_id 
ON consultas_esaj(mp_preference_id);

CREATE INDEX IF NOT EXISTS idx_consultas_mp_payment_id 
ON consultas_esaj(mp_payment_id);

CREATE INDEX IF NOT EXISTS idx_consultas_mp_external_reference 
ON consultas_esaj(mp_external_reference);

CREATE INDEX IF NOT EXISTS idx_consultas_mp_payment_status 
ON consultas_esaj(mp_payment_status);

-- ============================================================
-- PASSO 3: Verificar se as colunas foram criadas
-- ============================================================

SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'consultas_esaj' 
AND column_name LIKE 'mp_%' OR column_name LIKE 'payment_%'
ORDER BY ordinal_position;

-- ============================================================
-- ROLLBACK (caso necessário)
-- ============================================================
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS mp_preference_id;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS mp_payment_id;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS mp_payment_status;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS mp_payment_amount;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS mp_external_reference;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS payment_link;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS payment_created_at;
-- ALTER TABLE consultas_esaj DROP COLUMN IF EXISTS payment_confirmed_at;
-- DROP INDEX IF EXISTS idx_consultas_mp_preference_id;
-- DROP INDEX IF EXISTS idx_consultas_mp_payment_id;
-- DROP INDEX IF EXISTS idx_consultas_mp_external_reference;
-- DROP INDEX IF EXISTS idx_consultas_mp_payment_status;
