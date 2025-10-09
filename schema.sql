-- Schema PostgreSQL para Sistema OCR - Ofícios Requisitórios TJSP
-- Conforme especificações do AGENTS.md

-- Criar banco de dados (executar separadamente se necessário)
-- CREATE DATABASE oficios_tjsp;

-- Conectar ao banco
-- \c oficios_tjsp;

-- Tabela principal conforme AGENTS.md
CREATE TABLE IF NOT EXISTS lista_processos (
    -- Primary Key (cpf, numero_processo)
    cpf VARCHAR(11) NOT NULL,                    -- CPF apenas números
    numero_processo VARCHAR(30) NOT NULL,        -- Número processo CNJ
    
    -- Campos do Ofício
    vara VARCHAR(100),                           -- Vara responsável
    processo_execucao VARCHAR(30),               -- Processo de execução
    processo_conhecimento VARCHAR(30),           -- Processo de conhecimento
    data_ajuizamento DATE,                       -- Data ajuizamento (ISO)
    data_transito_julgado DATE,                  -- Data trânsito em julgado (ISO)
    requerente_caps VARCHAR(200),                -- Nome requerente MAIÚSCULAS
    advogado_nome VARCHAR(200),                  -- Nome do advogado
    advogado_oab VARCHAR(20),                    -- OAB do advogado
    
    -- Campos Financeiros (DECIMAL para precisão monetária)
    valor_principal_liquido DECIMAL(15,2),       -- Valor principal líquido
    valor_principal_bruto DECIMAL(15,2),         -- Valor principal bruto
    juros_moratorios DECIMAL(15,2),              -- Juros moratórios
    contrib_previdenciaria_iprem DECIMAL(15,2),  -- Contribuição IPREM
    contrib_previdenciaria_hspm DECIMAL(15,2),   -- Contribuição HSPM
    valor_total_requisitado DECIMAL(15,2),       -- Valor total requisitado
    data_base_atualizacao DATE,                  -- Data base atualização (ISO)
    
    -- Preferências (BOOLEAN)
    idoso BOOLEAN DEFAULT FALSE,                 -- Idoso (≥60 anos)
    doenca_grave BOOLEAN DEFAULT FALSE,          -- Doença grave
    pcd BOOLEAN DEFAULT FALSE,                   -- Pessoa com deficiência
    
    -- Campos Bancários (ANEXO II)
    banco VARCHAR(10),                           -- Código do banco (ex: 001, 341)
    agencia VARCHAR(20),                         -- Número da agência
    conta VARCHAR(30),                           -- Número da conta com dígito
    conta_tipo VARCHAR(20),                      -- Tipo de conta (corrente, poupança)

    -- Campos de Controle
    texto_completo_oficio TEXT NOT NULL,         -- Texto completo para auditoria
    timestamp_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp processamento
    data_envio DATE,                             -- Data de envio do ofício
    processado BOOLEAN DEFAULT FALSE,            -- Status do processamento

    -- Definir Primary Key
    PRIMARY KEY (cpf, numero_processo)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_lista_processos_cpf ON lista_processos(cpf);
CREATE INDEX IF NOT EXISTS idx_lista_processos_numero_processo ON lista_processos(numero_processo);
CREATE INDEX IF NOT EXISTS idx_lista_processos_processado ON lista_processos(processado);
CREATE INDEX IF NOT EXISTS idx_lista_processos_timestamp ON lista_processos(timestamp_processamento);
CREATE INDEX IF NOT EXISTS idx_lista_processos_vara ON lista_processos(vara);
CREATE INDEX IF NOT EXISTS idx_lista_processos_banco ON lista_processos(banco);

-- Comentários nas colunas
COMMENT ON TABLE lista_processos IS 'Tabela principal para armazenar dados extraídos de Ofícios Requisitórios TJSP';
COMMENT ON COLUMN lista_processos.cpf IS 'CPF do requerente (apenas números, sem formatação)';
COMMENT ON COLUMN lista_processos.numero_processo IS 'Número do processo no formato CNJ';
COMMENT ON COLUMN lista_processos.requerente_caps IS 'Nome do requerente em MAIÚSCULAS (campo obrigatório)';
COMMENT ON COLUMN lista_processos.banco IS 'Código do banco extraído do ANEXO II';
COMMENT ON COLUMN lista_processos.agencia IS 'Número da agência bancária extraído do ANEXO II';
COMMENT ON COLUMN lista_processos.conta IS 'Número da conta bancária com dígito extraído do ANEXO II';
COMMENT ON COLUMN lista_processos.conta_tipo IS 'Tipo de conta bancária (corrente, poupança) extraído do ANEXO II';
COMMENT ON COLUMN lista_processos.texto_completo_oficio IS 'Texto completo do ofício para auditoria e reprocessamento';
COMMENT ON COLUMN lista_processos.processado IS 'Indica se o processamento foi concluído com sucesso';

-- Constraint para validar CPF (11 dígitos)
ALTER TABLE lista_processos ADD CONSTRAINT chk_cpf_formato 
    CHECK (cpf ~ '^[0-9]{11}$');

-- Constraint para validar formato básico processo CNJ
ALTER TABLE lista_processos ADD CONSTRAINT chk_processo_formato 
    CHECK (numero_processo ~ '^[0-9]{7}-[0-9]{2}\.[0-9]{4}\.[0-9]\.[0-9]{2}\.[0-9]{4}$');

-- Constraint para validar valores monetários não negativos
ALTER TABLE lista_processos ADD CONSTRAINT chk_valores_positivos 
    CHECK (
        (valor_principal_liquido IS NULL OR valor_principal_liquido >= 0) AND
        (valor_principal_bruto IS NULL OR valor_principal_bruto >= 0) AND
        (juros_moratorios IS NULL OR juros_moratorios >= 0) AND
        (contrib_previdenciaria_iprem IS NULL OR contrib_previdenciaria_iprem >= 0) AND
        (contrib_previdenciaria_hspm IS NULL OR contrib_previdenciaria_hspm >= 0) AND
        (valor_total_requisitado IS NULL OR valor_total_requisitado >= 0)
    );

-- Função para atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_timestamp_processamento()
RETURNS TRIGGER AS $$
BEGIN
    NEW.timestamp_processamento = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar timestamp em updates
CREATE TRIGGER trg_update_timestamp_processamento
    BEFORE UPDATE ON lista_processos
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp_processamento();

-- View para estatísticas
CREATE OR REPLACE VIEW vw_estatisticas_processamento AS
SELECT
    COUNT(*) as total_registros,
    COUNT(CASE WHEN processado = true THEN 1 END) as processados_sucesso,
    COUNT(CASE WHEN processado = false THEN 1 END) as processados_erro,
    COUNT(CASE WHEN requerente_caps IS NOT NULL THEN 1 END) as com_dados_extraidos,
    COUNT(CASE WHEN valor_total_requisitado IS NOT NULL THEN 1 END) as com_valores_financeiros,
    COUNT(CASE WHEN banco IS NOT NULL AND conta IS NOT NULL THEN 1 END) as com_dados_bancarios,
    COUNT(CASE WHEN idoso = true THEN 1 END) as beneficiarios_idosos,
    COUNT(CASE WHEN doenca_grave = true THEN 1 END) as beneficiarios_doenca_grave,
    COUNT(CASE WHEN pcd = true THEN 1 END) as beneficiarios_pcd,
    MIN(timestamp_processamento) as primeiro_processamento,
    MAX(timestamp_processamento) as ultimo_processamento
FROM lista_processos;

-- View para processos por vara
CREATE OR REPLACE VIEW vw_processos_por_vara AS
SELECT 
    vara,
    COUNT(*) as total_processos,
    COUNT(CASE WHEN processado = true THEN 1 END) as processados_sucesso,
    SUM(valor_total_requisitado) as valor_total_vara
FROM lista_processos
WHERE vara IS NOT NULL
GROUP BY vara
ORDER BY total_processos DESC;

-- Comentários nas views
COMMENT ON VIEW vw_estatisticas_processamento IS 'Estatísticas gerais do processamento de ofícios';
COMMENT ON VIEW vw_processos_por_vara IS 'Resumo de processos agrupados por vara';

-- Conceder permissões (ajustar conforme necessário)
-- GRANT ALL PRIVILEGES ON TABLE lista_processos TO oficios_user;
-- GRANT SELECT ON vw_estatisticas_processamento TO oficios_user;
-- GRANT SELECT ON vw_processos_por_vara TO oficios_user;
