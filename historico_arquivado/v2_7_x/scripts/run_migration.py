#!/usr/bin/env python3
"""
Script para executar migration 03_add_saldo_final.sql
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
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    conn.autocommit = True
    cursor = conn.cursor()

    print('🔧 EXECUTANDO MIGRATION v2.5.2...\n')

    # ETAPA 1: Adicionar coluna saldo_final
    print('1️⃣ Adicionando coluna saldo_final...')
    try:
        cursor.execute("""
            ALTER TABLE esaj_detalhe_processos
            ADD COLUMN IF NOT EXISTS saldo_final NUMERIC(15,2);
        """)
        print('   ✅ Coluna adicionada/verificada\n')
    except Exception as e:
        print(f'   ⚠️ Aviso: {e}\n')

    # ETAPA 2: Adicionar comentário
    print('2️⃣ Adicionando comentário...')
    try:
        cursor.execute("""
            COMMENT ON COLUMN esaj_detalhe_processos.saldo_final IS
            'Saldo final após pagamento parcial. Se não houver, igual a valor_total_requisitado (V2.5.2)';
        """)
        print('   ✅ Comentário adicionado\n')
    except Exception as e:
        print(f'   ⚠️ Aviso: {e}\n')

    # ETAPA 3: Verificar registros antes de limpar
    print('3️⃣ Verificando dados atuais...')
    cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos')
    total_antes = cursor.fetchone()[0]
    print(f'   📊 Total de registros: {total_antes}\n')

    # ETAPA 4: LIMPAR DADOS (conforme solicitado)
    print('4️⃣ LIMPANDO DADOS da tabela...')
    try:
        cursor.execute('TRUNCATE TABLE esaj_detalhe_processos CASCADE;')
        print('   ✅ Tabela limpa com sucesso!\n')
    except Exception as e:
        print(f'   ❌ Erro ao limpar: {e}\n')

    # ETAPA 5: Verificar depois da limpeza
    cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos')
    total_depois = cursor.fetchone()[0]

    # ETAPA 6: Verificar estrutura da coluna
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'esaj_detalhe_processos'
        AND column_name = 'saldo_final'
    """)
    info_coluna = cursor.fetchone()

    print('=' * 60)
    print('📊 RESUMO DA MIGRATION')
    print('=' * 60)
    print(f'✅ Coluna saldo_final: {info_coluna[0]} ({info_coluna[1]})')
    print(f'📋 Registros removidos: {total_antes}')
    print(f'📋 Registros atuais: {total_depois}')
    print('✅ Tabela pronta para testes!')
    print('=' * 60)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
