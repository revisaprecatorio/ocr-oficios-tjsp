-- ============================================================================
-- ÍNDICES: esaj_detalhe_processos
-- Descrição: Índices para otimizar queries de filtros e buscas
-- Versão: 1.0.0
-- Data: 14/10/2025
-- ============================================================================

-- ============================================================================
-- ÍNDICE PRINCIPAL: CPF (filtro mais comum)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_cpf 
ON esaj_detalhe_processos(cpf);

-- ============================================================================
-- ÍNDICE: Rejeitado (filtro importante para separar aprovados/rejeitados)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_rejeitado 
ON esaj_detalhe_processos(rejeitado);

-- ============================================================================
-- ÍNDICE: Diagnóstico (novo campo para controle)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_process_diagnostico 
ON esaj_detalhe_processos(process_diagnostico);

-- ============================================================================
-- ÍNDICES COMPOSTOS: Filtros combinados mais comuns
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_cpf_rejeitado 
ON esaj_detalhe_processos(cpf, rejeitado);

CREATE INDEX IF NOT EXISTS idx_cpf_diagnostico 
ON esaj_detalhe_processos(cpf, process_diagnostico);

-- ============================================================================
-- ÍNDICE: Vara (busca por vara específica)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_vara 
ON esaj_detalhe_processos(vara);

-- ============================================================================
-- ÍNDICES: Preferências (filtros de prioridade)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_idoso 
ON esaj_detalhe_processos(idoso);

CREATE INDEX IF NOT EXISTS idx_doenca_grave 
ON esaj_detalhe_processos(doenca_grave);

CREATE INDEX IF NOT EXISTS idx_pcd 
ON esaj_detalhe_processos(pcd);

-- ============================================================================
-- ÍNDICE: Data de Ajuizamento (ordenação temporal)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_data_ajuizamento 
ON esaj_detalhe_processos(data_ajuizamento);

-- ============================================================================
-- ÍNDICE: Timestamp de Ingestão (auditoria)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_timestamp_ingestao 
ON esaj_detalhe_processos(timestamp_ingestao);

-- ============================================================================
-- ANÁLISE DA TABELA (atualizar estatísticas para o otimizador)
-- ============================================================================
ANALYZE esaj_detalhe_processos;
