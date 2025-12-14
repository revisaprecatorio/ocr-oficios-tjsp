-- ============================================================================
-- VIEW: vw_precatorios_full (V3.0)
-- Descrição: View consolidada com dados de ofícios + cálculos + consultas
-- Versão: V3.0 - Schema cleanup (35 colunas essenciais)
-- Data: 13/12/2025
-- Changelog:
--   V3.0 (13/12/2025): Removed 15 unused columns (50→35)
--   V2.7.2 (12/12/2025): Removed requerente_caps
--   V2.7.1 (09/12/2025): Removed advogado_*, data_ajuizamento, cessao_credito
--   V2.5.3 (09/12/2025): Added obito, data_obito, cpf_sucessor
--   V2.5.2 (04/12/2025): Added saldo_final, preferencial, habilitacao_herdeiros
-- ============================================================================

DROP VIEW IF EXISTS vw_precatorios_full;

CREATE OR REPLACE VIEW vw_precatorios_full AS
SELECT
    -- ========================================================================
    -- TABELA PRINCIPAL: esaj_detalhe_processos (35 COLUNAS V3.0)
    -- ========================================================================

    -- Identificadores
    d.cpf,
    d.numero_processo_cnj,
    d.processo_origem,

    -- Campos Ofício
    d.numero_ordem,
    d.vara,
    -- V3.0: REMOVED processo_execucao, processo_conhecimento (0% filled)

    -- Datas
    -- V2.7.1: REMOVED data_ajuizamento, data_transito_julgado
    d.data_base_atualizacao,
    d.data_nascimento,

    -- Partes envolvidas
    -- V2.7.2: REMOVED requerente_caps
    -- V2.7.1: REMOVED advogado_nome, advogado_oab
    d.credor_nome,
    d.credor_cpf_cnpj,
    d.devedor_ente,

    -- Dados bancários
    d.banco,
    d.agencia,
    d.conta,
    -- V3.0: REMOVED conta_tipo, tipo_levantamento, dados_bancarios_advogado, cpf_titular_conta (0% filled)

    -- Valores financeiros
    d.valor_principal_liquido,
    d.valor_principal_bruto,
    d.juros_moratorios,
    d.valor_total_requisitado,
    d.saldo_final,
    -- V3.0: REMOVED contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_compensado,
    --       contribuicao_social, salario_pericial, assist_tecnico, custas, despesas, multas (0% filled)

    -- Preferências de pagamento
    d.idoso,
    d.doenca_grave,
    d.pcd,

    -- Termos jurídicos
    d.preferencial,
    d.habilitacao_herdeiros,
    -- V2.7.1: REMOVED cessao_credito

    -- Óbito e sucessão (V2.5.3)
    d.obito,
    d.data_obito,
    d.cpf_sucessor,

    -- Controle de processamento
    d.rejeitado,
    d.motivo_rejeicao,
    d.observacoes,
    d.anomalia,
    d.descricao_anomalia,
    -- V2.7.1: REMOVED process_diagnostico

    -- Metadados
    d.caminho_pdf,
    d.timestamp_ingestao,

    -- ========================================================================
    -- TABELA DE CÁLCULOS: esaj_calc_precatorio_resumo (LEFT JOIN)
    -- Se não houver cálculo, campos serão NULL
    -- ========================================================================
    c.fator_ipcae_antes,
    c.fator_ipcae_pos,
    c.fator_juros_2aa_simples,
    c.meses_para_2aa,
    c.principal_original,
    c.principal_apos_antes,
    c.principal_pos_ipca,
    c.principal_final_ipca_2aa,
    c.juros_mora_anteriores_base,
    c.juros_mora_apos_antes,
    c.juros_mora_final_corrigido,
    c.total_corrigido,
    c.criado_em AS data_calculo,

    -- ========================================================================
    -- TABELA DE CONSULTAS: consultas_esaj (LEFT JOIN)
    -- Busca a consulta mais recente de cada CPF
    -- Se não houver consulta, campos serão NULL
    -- ========================================================================
    q.nome_requerente,
    q.email AS email_requerente,
    q.timestamp_consulta AS data_ultima_consulta

FROM esaj_detalhe_processos d

-- LEFT JOIN com tabela de cálculos (pode não ter cálculo ainda)
LEFT JOIN esaj_calc_precatorio_resumo c
    ON c.cpf = d.cpf
    AND c.numero_processo_cnj = d.numero_processo_cnj

-- LEFT JOIN com consultas (busca última consulta de cada CPF)
LEFT JOIN (
    SELECT DISTINCT ON (cpf)
        cpf,
        nome_requerente,
        email,
        timestamp_consulta
    FROM consultas_esaj
    ORDER BY cpf, timestamp_consulta DESC
) q
    ON q.cpf = d.cpf;

-- ============================================================================
-- COMENTÁRIOS E OBSERVAÇÕES
-- ============================================================================
-- 1. VIEW usa LEFT JOIN para preservar TODOS os registros da tabela principal
-- 2. Se não houver cálculo, campos de cálculo serão NULL
-- 3. Se não houver consulta, campos de consulta serão NULL
-- 4. V3.0: Schema simplificado com 35 colunas essenciais (-30% vs V2.7.6)
-- 5. V2.5.3: Campos de óbito/sucessão: obito, data_obito, cpf_sucessor
-- 6. V2.5.2: Campos financeiros/jurídicos: saldo_final, preferencial, habilitacao_herdeiros
-- ============================================================================
