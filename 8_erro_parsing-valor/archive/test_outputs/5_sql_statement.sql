-- SQL Statement para INSERT/UPDATE
-- Gerado em: 2025-10-31 19:08:44
-- ⚠️ ESTE SQL NÃO FOI EXECUTADO (modo debug)

INSERT INTO lista_processos (
    cpf,
    numero_processo,
    processo_origem,
    requerente_caps,
    numero_ordem,
    vara,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    contrib_previdenciaria_iprem,
    contrib_previdenciaria_hspm,
    banco,
    agencia,
    conta,
    conta_tipo,
    data_nascimento,
    idoso,
    doenca_grave,
    pcd,
    timestamp_processamento
) VALUES (
    '27308157830',
    '0015796-15.2025.8.26.0500',
    '0015796-15.2025.8.26.0500',
    'RODRIGO AZEVEDO FERRAO',
    '1/2025',
    NULL,
    88994.41,
    88994.41,
    NULL,
    88994.41,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    CURRENT_TIMESTAMP
)
ON CONFLICT (cpf, numero_processo) DO UPDATE SET
    valor_principal_liquido = EXCLUDED.valor_principal_liquido,
    valor_principal_bruto = EXCLUDED.valor_principal_bruto,
    juros_moratorios = EXCLUDED.juros_moratorios,
    valor_total_requisitado = EXCLUDED.valor_total_requisitado,
    timestamp_processamento = CURRENT_TIMESTAMP;
