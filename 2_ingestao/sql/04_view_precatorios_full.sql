-- ============================================================================
-- VIEW: vw_precatorios_full (V2.5.2)
-- Descrição: View consolidada com dados de ofícios + cálculos + consultas
-- Versão: V2.5.2 - Inclui novos campos (saldo_final, preferencial, habilitacao_herdeiros, cessao_credito)
-- Data: 04/12/2025
-- ============================================================================

DROP VIEW IF EXISTS vw_precatorios_full;

CREATE OR REPLACE VIEW vw_precatorios_full AS
SELECT
    -- ========================================================================
    -- TABELA PRINCIPAL: esaj_detalhe_processos (TODOS OS CAMPOS)
    -- ========================================================================
    d.cpf,
    d.numero_processo_cnj,
    d.processo_origem,
    d.requerente_caps,
    d.numero_ordem,
    d.vara,
    d.processo_execucao,
    d.processo_conhecimento,

    -- Datas
    d.data_ajuizamento,
    d.data_transito_julgado,
    d.data_base_atualizacao,
    d.data_nascimento,

    -- Partes envolvidas
    d.advogado_nome,
    d.advogado_oab,
    d.credor_nome,
    d.credor_cpf_cnpj,
    d.devedor_ente,

    -- Dados bancários
    d.banco,
    d.agencia,
    d.conta,
    d.conta_tipo,
    d.tipo_levantamento,
    d.dados_bancarios_advogado,
    d.cpf_titular_conta,

    -- Valores financeiros
    d.valor_principal_liquido,
    d.valor_principal_bruto,
    d.juros_moratorios,
    d.valor_total_requisitado,
    d.saldo_final,                        -- ✅ V2.5.2: NOVO CAMPO
    d.contrib_previdenciaria_iprem,
    d.contrib_previdenciaria_hspm,
    d.valor_compensado,
    d.contribuicao_social,
    d.salario_pericial,
    d.assist_tecnico,
    d.custas,
    d.despesas,
    d.multas,

    -- Preferências de pagamento
    d.idoso,
    d.doenca_grave,
    d.pcd,

    -- Termos jurídicos (V2.5.2)
    d.preferencial,                       -- ✅ V2.5.2: NOVO CAMPO
    d.habilitacao_herdeiros,              -- ✅ V2.5.2: NOVO CAMPO
    d.cessao_credito,                     -- ✅ V2.5.2: NOVO CAMPO

    -- Controle de processamento
    d.rejeitado,
    d.motivo_rejeicao,
    d.observacoes,
    d.anomalia,
    d.descricao_anomalia,
    d.process_diagnostico,
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
-- 4. V2.5.2 adiciona 4 novos campos da tabela principal:
--    - saldo_final (após pagamento parcial, ou = valor_total_requisitado)
--    - preferencial (detectado por regex)
--    - habilitacao_herdeiros (validado por código 9270 + CPF)
--    - cessao_credito (DESATIVADO - sempre FALSE)
-- ============================================================================
