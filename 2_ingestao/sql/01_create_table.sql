-- ============================================================================
-- TABELA: esaj_detalhe_processos
-- Descrição: Armazena dados extraídos de Ofícios Requisitórios do TJSP
-- Versão: 3.0
-- Data: 13/12/2025
-- Changelog:
--   V3.0 (13/12/2025): Schema cleanup - 50→35 colunas (-30%)
--   V2.5.3 (04/12/2025): + obito, data_obito, cpf_sucessor
--   V2.5.2 (04/12/2025): + saldo_final
--   V2.6.0 (09/12/2025): Schema consolidado
-- ============================================================================

CREATE TABLE IF NOT EXISTS esaj_detalhe_processos (
    -- ========================================================================
    -- CHAVE PRIMÁRIA
    -- ========================================================================
    id SERIAL PRIMARY KEY,
    
    -- ========================================================================
    -- IDENTIFICADORES (extraídos do nome do arquivo JSON)
    -- Formato do arquivo: {cpf}_{numero_processo_cnj}.json
    -- ========================================================================
    cpf VARCHAR(11) NOT NULL,
    numero_processo_cnj VARCHAR(30) NOT NULL,
    
    -- ========================================================================
    -- CAMPOS OBRIGATÓRIOS DO JSON
    -- ========================================================================
    processo_origem VARCHAR(30) NOT NULL,
    -- V2.7.2: REMOVED (advogado/representante, not actual credor - causes confusion in litisconsórcios):
    -- requerente_caps VARCHAR(200) NOT NULL,

    -- ========================================================================
    -- CAMPOS OPCIONAIS - OFÍCIO
    -- ========================================================================
    numero_ordem VARCHAR(15),
    vara VARCHAR(200),
    -- V3.0: REMOVED processo_execucao, processo_conhecimento (0% filled)
    
    -- ========================================================================
    -- DATAS
    -- ========================================================================
    -- V2.7.1: REMOVED (not needed):
    -- data_ajuizamento DATE,
    -- data_transito_julgado DATE,
    data_base_atualizacao DATE,
    data_nascimento DATE,
    
    -- ========================================================================
    -- PARTES ENVOLVIDAS
    -- ========================================================================
    -- V2.7.1: REMOVED (not needed):
    -- advogado_nome VARCHAR(200),
    -- advogado_oab VARCHAR(20),
    credor_nome VARCHAR(200),
    credor_cpf_cnpj VARCHAR(18),
    devedor_ente VARCHAR(200),
    
    -- ========================================================================
    -- DADOS BANCÁRIOS (ANEXO II)
    -- ========================================================================
    banco VARCHAR(100),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    -- V3.0: REMOVED conta_tipo, tipo_levantamento, dados_bancarios_advogado, cpf_titular_conta (0% filled)
    
    -- ========================================================================
    -- VALORES FINANCEIROS (NUMERIC(15,2) para precisão monetária)
    -- ========================================================================
    valor_principal_liquido NUMERIC(15,2),
    valor_principal_bruto NUMERIC(15,2),
    juros_moratorios NUMERIC(15,2),
    valor_total_requisitado NUMERIC(15,2),
    saldo_final NUMERIC(15,2),
    -- V3.0: REMOVED contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_compensado,
    --       contribuicao_social, salario_pericial, assist_tecnico, custas, despesas, multas (0% filled)
    
    -- ========================================================================
    -- PREFERÊNCIAS (Prioridades de Pagamento)
    -- ========================================================================
    idoso BOOLEAN,
    doenca_grave BOOLEAN,
    pcd BOOLEAN,
    
    -- ========================================================================
    -- TERMOS JURÍDICOS (Detectados via Regex - v2.4.0)
    -- ========================================================================
    preferencial BOOLEAN DEFAULT FALSE,
    habilitacao_herdeiros BOOLEAN DEFAULT FALSE,
    -- V2.7.1: REMOVED (not needed):
    -- cessao_credito BOOLEAN DEFAULT FALSE,

    -- ========================================================================
    -- ÓBITO E SUCESSÃO (V2.5.3 - Detector de Habilitação de Herdeiros)
    -- ========================================================================
    obito BOOLEAN DEFAULT FALSE,  -- V2.5.3: Indica se requerente faleceu
    data_obito DATE,  -- V2.5.3: Data do óbito do requerente
    cpf_sucessor VARCHAR(14),  -- V2.5.3: CPF do herdeiro/sucessor habilitado

    -- ========================================================================
    -- CONTROLE DE PROCESSAMENTO
    -- ========================================================================
    rejeitado BOOLEAN,
    motivo_rejeicao TEXT,
    observacoes TEXT,
    anomalia BOOLEAN,
    descricao_anomalia TEXT,

    -- V2.7.1: REMOVED (not needed):
    -- process_diagnostico BOOLEAN DEFAULT FALSE,

    -- ========================================================================
    -- METADADOS
    -- ========================================================================
    caminho_pdf TEXT,
    timestamp_ingestao TIMESTAMP DEFAULT NOW(),
    
    -- ========================================================================
    -- CONSTRAINT ÚNICA: Um processo por CPF
    -- Permite ON CONFLICT DO UPDATE para upsert
    -- ========================================================================
    CONSTRAINT uk_cpf_processo UNIQUE(cpf, numero_processo_cnj)
);

-- ============================================================================
-- COMENTÁRIOS NA TABELA
-- ============================================================================
COMMENT ON TABLE esaj_detalhe_processos IS 'V3.0: Dados extraídos de Ofícios Requisitórios do TJSP (35 colunas essenciais)';
COMMENT ON COLUMN esaj_detalhe_processos.id IS 'ID auto-incremento (chave primária)';
COMMENT ON COLUMN esaj_detalhe_processos.cpf IS 'CPF do requerente (extraído do nome da pasta)';
COMMENT ON COLUMN esaj_detalhe_processos.numero_processo_cnj IS 'Número do processo CNJ (extraído do nome do arquivo)';
-- V2.7.1: REMOVED process_diagnostico
COMMENT ON COLUMN esaj_detalhe_processos.rejeitado IS 'Indica se o ofício foi rejeitado pelo DEPRE';
COMMENT ON COLUMN esaj_detalhe_processos.timestamp_ingestao IS 'Data/hora da ingestão no banco';
COMMENT ON COLUMN esaj_detalhe_processos.preferencial IS 'Indica se há pedido de preferência no processo (detectado via regex: preferência|preferencia)';
COMMENT ON COLUMN esaj_detalhe_processos.habilitacao_herdeiros IS 'Indica se há habilitação de herdeiros no processo (V2.5.3: detectado via código 9270 e termos jurídicos)';
-- V2.7.1: REMOVED cessao_credito
COMMENT ON COLUMN esaj_detalhe_processos.saldo_final IS 'Saldo final após pagamento parcial. Se não houver, igual a valor_total_requisitado (V2.5.2)';
COMMENT ON COLUMN esaj_detalhe_processos.obito IS 'Indica se o requerente faleceu (V2.5.3: detectado via Detector de Habilitação de Herdeiros)';
COMMENT ON COLUMN esaj_detalhe_processos.data_obito IS 'Data do óbito do requerente (V2.5.3)';
COMMENT ON COLUMN esaj_detalhe_processos.cpf_sucessor IS 'CPF do herdeiro/sucessor habilitado (V2.5.3: formato XXX.XXX.XXX-XX)';
