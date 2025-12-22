import os
import psycopg2
from dotenv import load_dotenv

# Carrega variáveis
load_dotenv()

# Configuração do banco (mesma do seu .env)
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
}

DDL_V3 = """
-- ADICIONADO CASCADE PARA REMOVER VIEWS DEPENDENTES
DROP TABLE IF EXISTS esaj_detalhe_processos CASCADE;

CREATE TABLE esaj_detalhe_processos (
    id SERIAL PRIMARY KEY,
    cpf VARCHAR(20),
    numero_processo_cnj VARCHAR(50),
    processo_origem VARCHAR(50),
    requerente_caps TEXT,               -- Nova coluna V3.0
    numero_ordem VARCHAR(50),
    vara VARCHAR(100),
    processo_execucao VARCHAR(50),
    processo_conhecimento VARCHAR(50),
    data_ajuizamento DATE,
    data_transito_julgado DATE,
    data_base_atualizacao DATE,
    data_nascimento DATE,
    advogado_nome TEXT,
    advogado_oab VARCHAR(50),
    credor_nome TEXT,
    credor_cpf_cnpj VARCHAR(20),
    devedor_ente TEXT,
    banco VARCHAR(50),
    agencia VARCHAR(20),
    conta VARCHAR(30),
    conta_tipo VARCHAR(20),
    tipo_levantamento VARCHAR(50),
    dados_bancarios_advogado BOOLEAN DEFAULT FALSE,
    cpf_titular_conta VARCHAR(20),
    valor_principal_liquido NUMERIC(15,2),
    valor_principal_bruto NUMERIC(15,2),
    juros_moratorios NUMERIC(15,2),
    valor_total_requisitado NUMERIC(15,2),
    saldo_final NUMERIC(15,2),
    contrib_previdenciaria_iprem NUMERIC(15,2),
    contrib_previdenciaria_hspm NUMERIC(15,2),
    valor_compensado NUMERIC(15,2),
    contribuicao_social NUMERIC(15,2),
    salario_pericial NUMERIC(15,2),
    assist_tecnico NUMERIC(15,2),
    custas NUMERIC(15,2),
    despesas NUMERIC(15,2),
    multas NUMERIC(15,2),
    idoso BOOLEAN DEFAULT FALSE,
    doenca_grave BOOLEAN DEFAULT FALSE,
    pcd BOOLEAN DEFAULT FALSE,
    preferencial BOOLEAN DEFAULT FALSE,
    habilitacao_herdeiros BOOLEAN DEFAULT FALSE,
    cessao_credito BOOLEAN DEFAULT FALSE,
    obito BOOLEAN DEFAULT FALSE,
    data_obito DATE,
    cpf_sucessor VARCHAR(20),
    rejeitado BOOLEAN DEFAULT FALSE,
    motivo_rejeicao TEXT,
    observacoes TEXT,
    anomalia BOOLEAN DEFAULT FALSE,
    descricao_anomalia TEXT,
    process_diagnostico BOOLEAN DEFAULT FALSE,
    caminho_pdf TEXT,
    timestamp_ingestao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_cpf_processo UNIQUE (cpf, numero_processo_cnj)
);

CREATE INDEX idx_cpf ON esaj_detalhe_processos(cpf);
CREATE INDEX idx_processo ON esaj_detalhe_processos(numero_processo_cnj);
"""

def main():
    print("="*50)
    print("🛠️  RECRIANDO TABELA PARA VERSÃO V3.0 (COM CASCADE)")
    print("="*50)
    
    try:
        print(f"🔌 Conectando em {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("🗑️  Apagando tabela antiga (e views dependentes)...")
        cur.execute(DDL_V3)
        conn.commit()
        
        print("✅ Tabela 'esaj_detalhe_processos' recriada com sucesso!")
        print("✅ Coluna 'requerente_caps' adicionada.")
        print("⚠️  Aviso: As views 'vw_precatorios_full' e 'vw_backoffice_processos' foram removidas e precisarão ser recriadas se você as usa.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    main()