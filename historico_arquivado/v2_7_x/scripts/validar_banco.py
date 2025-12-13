#!/usr/bin/env python3
"""
Script de Validação do Banco V2.5.2
Verifica contagens e campos V2.5.2 no PostgreSQL
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def main():
    print("=" * 60)
    print("🔍 VALIDAÇÃO DO BANCO - V2.5.2")
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
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("📊 CONTAGENS")
    print("=" * 60)

    # 1. Total de registros
    cursor.execute("SELECT COUNT(*) as total FROM esaj_detalhe_processos;")
    total = cursor.fetchone()['total']
    print(f"✓ Total de registros: {total}")

    # 2. Distribuição do campo preferencial
    cursor.execute("""
        SELECT preferencial, COUNT(*) as count
        FROM esaj_detalhe_processos
        GROUP BY preferencial
        ORDER BY preferencial;
    """)
    print(f"\n📋 Campo 'preferencial':")
    for row in cursor.fetchall():
        valor = "TRUE" if row['preferencial'] else "FALSE"
        print(f"   {valor}: {row['count']} registros")

    # 3. Distribuição do campo habilitacao_herdeiros
    cursor.execute("""
        SELECT habilitacao_herdeiros, COUNT(*) as count
        FROM esaj_detalhe_processos
        GROUP BY habilitacao_herdeiros
        ORDER BY habilitacao_herdeiros;
    """)
    print(f"\n📋 Campo 'habilitacao_herdeiros':")
    for row in cursor.fetchall():
        valor = "TRUE" if row['habilitacao_herdeiros'] else "FALSE"
        print(f"   {valor}: {row['count']} registros")

    # 4. Distribuição do campo cessao_credito
    cursor.execute("""
        SELECT cessao_credito, COUNT(*) as count
        FROM esaj_detalhe_processos
        GROUP BY cessao_credito
        ORDER BY cessao_credito;
    """)
    print(f"\n📋 Campo 'cessao_credito':")
    for row in cursor.fetchall():
        valor = "TRUE" if row['cessao_credito'] else "FALSE"
        print(f"   {valor}: {row['count']} registros")

    # 5. Verificar saldo_final preenchido
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(saldo_final) as com_saldo,
            COUNT(*) - COUNT(saldo_final) as sem_saldo
        FROM esaj_detalhe_processos;
    """)
    saldo_stats = cursor.fetchone()
    print(f"\n📋 Campo 'saldo_final':")
    print(f"   Com saldo: {saldo_stats['com_saldo']} registros")
    print(f"   Sem saldo: {saldo_stats['sem_saldo']} registros")

    print("\n" + "=" * 60)
    print("📝 AMOSTRA DE DADOS (5 primeiros)")
    print("=" * 60)

    cursor.execute("""
        SELECT
            cpf,
            numero_processo_cnj,
            requerente_caps,
            saldo_final,
            preferencial,
            habilitacao_herdeiros,
            cessao_credito
        FROM esaj_detalhe_processos
        ORDER BY cpf
        LIMIT 5;
    """)

    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"\n{i}. CPF: {row['cpf']}")
        print(f"   Processo: {row['numero_processo_cnj']}")
        print(f"   Requerente: {row['requerente_caps'][:50] if row['requerente_caps'] else 'N/A'}")
        print(f"   Saldo Final: R$ {row['saldo_final']:,.2f}" if row['saldo_final'] else "   Saldo Final: NULL")
        print(f"   Preferencial: {'✅' if row['preferencial'] else '❌'}")
        print(f"   Habilitação: {'✅' if row['habilitacao_herdeiros'] else '❌'}")
        print(f"   Cessão: {'✅' if row['cessao_credito'] else '❌'}")

    # Fechar conexão
    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ VALIDAÇÃO CONCLUÍDA")
    print("=" * 60)

if __name__ == "__main__":
    main()
