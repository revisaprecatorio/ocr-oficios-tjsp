-- ============================================================================
-- TABELA: esaj_detalhe_processos
-- Descrição: Armazena dados extraídos de Ofícios Requisitórios do TJSP
-- Versão: 1.0.0
-- Data: 14/10/2025
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
    requerente_caps VARCHAR(200) NOT NULL,
    
    -- ========================================================================
    -- CAMPOS OPCIONAIS - OFÍCIO
    -- ========================================================================
    numero_ordem VARCHAR(15),
    vara VARCHAR(200),
    processo_execucao VARCHAR(30),
    processo_conhecimento VARCHAR(30),
    
    -- ========================================================================
    -- DATAS
    -- ========================================================================
    data_ajuizamento DATE,
    data_transito_julgado DATE,
    data_base_atualizacao DATE,
    data_nascimento DATE,
    
    -- ========================================================================
    -- PARTES ENVOLVIDAS
    -- ========================================================================
    advogado_nome VARCHAR(200),
    advogado_oab VARCHAR(20),
    credor_nome VARCHAR(200),
    credor_cpf_cnpj VARCHAR(18),
    devedor_ente VARCHAR(200),
    
    -- ========================================================================
    -- DADOS BANCÁRIOS (ANEXO II)
    -- ========================================================================
    banco VARCHAR(10),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    conta_tipo VARCHAR(20),
    tipo_levantamento VARCHAR(200),
    dados_bancarios_advogado BOOLEAN,
    cpf_titular_conta VARCHAR(18),
    
    -- ========================================================================
    -- VALORES FINANCEIROS (NUMERIC(15,2) para precisão monetária)
    -- ========================================================================
    valor_principal_liquido NUMERIC(15,2),
    valor_principal_bruto NUMERIC(15,2),
    juros_moratorios NUMERIC(15,2),
    valor_total_requisitado NUMERIC(15,2),
    contrib_previdenciaria_iprem NUMERIC(15,2),
    contrib_previdenciaria_hspm NUMERIC(15,2),
    valor_compensado NUMERIC(15,2),
    contribuicao_social NUMERIC(15,2),
    salario_pericial NUMERIC(15,2),
    assist_tecnico NUMERIC(15,2),
    custas NUMERIC(15,2),
    despesas NUMERIC(15,2),
    multas NUMERIC(15,2),
    
    -- ========================================================================
    -- PREFERÊNCIAS (Prioridades de Pagamento)
    -- ========================================================================
    idoso BOOLEAN,
    doenca_grave BOOLEAN,
    pcd BOOLEAN,
    
    -- ========================================================================
    -- CONTROLE DE PROCESSAMENTO
    -- ========================================================================
    rejeitado BOOLEAN,
    motivo_rejeicao TEXT,
    observacoes TEXT,
    anomalia BOOLEAN,
    descricao_anomalia TEXT,
    
    -- ========================================================================
    -- NOVO CAMPO: Controle de Diagnóstico
    -- ========================================================================
    process_diagnostico BOOLEAN DEFAULT FALSE,
    
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
COMMENT ON TABLE esaj_detalhe_processos IS 'Dados extraídos de Ofícios Requisitórios do TJSP';
COMMENT ON COLUMN esaj_detalhe_processos.id IS 'ID auto-incremento (chave primária)';
COMMENT ON COLUMN esaj_detalhe_processos.cpf IS 'CPF do requerente (extraído do nome da pasta)';
COMMENT ON COLUMN esaj_detalhe_processos.numero_processo_cnj IS 'Número do processo CNJ (extraído do nome do arquivo)';
COMMENT ON COLUMN esaj_detalhe_processos.process_diagnostico IS 'Flag para controle de processamento/diagnóstico (DEFAULT FALSE)';
COMMENT ON COLUMN esaj_detalhe_processos.rejeitado IS 'Indica se o ofício foi rejeitado pelo DEPRE';
COMMENT ON COLUMN esaj_detalhe_processos.timestamp_ingestao IS 'Data/hora da ingestão no banco';
