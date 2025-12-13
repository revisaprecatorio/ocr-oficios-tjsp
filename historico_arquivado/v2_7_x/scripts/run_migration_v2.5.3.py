#!/usr/bin/env python3
"""
Script para executar Migration V2.5.3 no PostgreSQL da VPS
Adiciona campos: obito, data_obito, cpf_sucessor
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

def main():
    print("=" * 60)
    print("🔄 MIGRATION V2.5.3 - Adicionar Campos de Óbito")
    print("=" * 60)

    # Conectar ao banco
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }

    print(f"\n🔌 Conectando ao PostgreSQL...")
    print(f"   Host: {db_config['host']}")
    print(f"   Database: {db_config['database']}")

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        sys.exit(1)

    # Ler arquivo SQL
    sql_file = Path(__file__).parent / "migration_v2.5.3_add_obito_fields.sql"
    print(f"\n📄 Lendo migration SQL: {sql_file.name}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Executar migration
    print(f"\n⚙️  Executando migration...")

    try:
        # Executar cada comando separadamente (evita problemas com comentários)
        commands = [
            # 1. Adicionar campo obito
            """
            ALTER TABLE esaj_detalhe_processos
            ADD COLUMN IF NOT EXISTS obito BOOLEAN DEFAULT FALSE;
            """,

            """
            COMMENT ON COLUMN esaj_detalhe_processos.obito IS
            'Indica se o requerente faleceu (detectado via Detector de Habilitação de Herdeiros V2.5.3)';
            """,

            # 2. Adicionar campo data_obito
            """
            ALTER TABLE esaj_detalhe_processos
            ADD COLUMN IF NOT EXISTS data_obito DATE;
            """,

            """
            COMMENT ON COLUMN esaj_detalhe_processos.data_obito IS
            'Data do óbito do requerente (extraída da seção "Dados da Sucessão" do formulário 9270)';
            """,

            # 3. Adicionar campo cpf_sucessor
            """
            ALTER TABLE esaj_detalhe_processos
            ADD COLUMN IF NOT EXISTS cpf_sucessor VARCHAR(14);
            """,

            """
            COMMENT ON COLUMN esaj_detalhe_processos.cpf_sucessor IS
            'CPF do herdeiro/sucessor habilitado (formato: XXX.XXX.XXX-XX, extraído do formulário 9270)';
            """,

            # 4. Criar índice para consultas por óbito
            """
            CREATE INDEX IF NOT EXISTS idx_esaj_obito
            ON esaj_detalhe_processos(obito)
            WHERE obito = TRUE;
            """,

            # 5. Criar índice para consultas por CPF sucessor
            """
            CREATE INDEX IF NOT EXISTS idx_esaj_cpf_sucessor
            ON esaj_detalhe_processos(cpf_sucessor)
            WHERE cpf_sucessor IS NOT NULL;
            """
        ]

        for i, cmd in enumerate(commands, 1):
            cmd = cmd.strip()
            if cmd:
                print(f"   └─ Executando comando {i}/{len(commands)}...")
                cursor.execute(cmd)

        conn.commit()
        print("   ✅ Migration executada com sucesso!")

    except Exception as e:
        print(f"   ❌ Erro na migration: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        sys.exit(1)

    # Verificar colunas criadas
    print(f"\n🔍 Verificando colunas criadas...")

    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'esaj_detalhe_processos'
          AND column_name IN ('obito', 'data_obito', 'cpf_sucessor')
        ORDER BY ordinal_position;
    """)

    colunas = cursor.fetchall()

    if colunas:
        print("   ✅ Colunas encontradas:")
        for col in colunas:
            print(f"      • {col[0]}: {col[1]} (nullable={col[2]}, default={col[3]})")
    else:
        print("   ⚠️  AVISO: Nenhuma coluna encontrada (pode ser normal se já existiam)")

    # Verificar índices criados
    print(f"\n🔍 Verificando índices criados...")

    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'esaj_detalhe_processos'
          AND indexname IN ('idx_esaj_obito', 'idx_esaj_cpf_sucessor');
    """)

    indices = cursor.fetchall()

    if indices:
        print("   ✅ Índices encontrados:")
        for idx in indices:
            print(f"      • {idx[0]}")
    else:
        print("   ⚠️  AVISO: Nenhum índice encontrado (pode ser normal se já existiam)")

    # Fechar conexão
    cursor.close()
    conn.close()

    print(f"\n" + "=" * 60)
    print("✅ MIGRATION V2.5.3 CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print("\n📋 Próximos passos:")
    print("   1. Reprocessar PDFs com novos detectores")
    print("   2. Executar ingest_all_jsons.py para popular novos campos")
    print("   3. Validar detecções com amostra de 4 CPFs")
    print("=" * 60)


if __name__ == "__main__":
    main()
