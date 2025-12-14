#!/usr/bin/env python3
"""
Script para criar tabela e índices no PostgreSQL
Alternativa ao psql quando não está instalado
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def executar_sql_file(cursor, sql_file: Path):
    """Executa um arquivo SQL"""
    print(f"\n📄 Executando: {sql_file.name}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    try:
        cursor.execute(sql)
        print(f"   ✅ Sucesso!")
        return True
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False


def main():
    """Função principal"""
    
    print("=" * 60)
    print("🏗️  CRIAÇÃO DE TABELA E ÍNDICES")
    print("=" * 60)
    
    # Configuração do banco
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    # Validar configuração
    if not all(db_config.values()):
        print("❌ Configuração incompleta! Verifique o arquivo .env")
        sys.exit(1)
    
    # Conectar
    print(f"\n🔌 Conectando ao PostgreSQL...")
    print(f"   Host: {db_config['host']}")
    print(f"   Database: {db_config['database']}")
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)
    
    # Arquivos SQL
    sql_dir = Path(__file__).parent.parent / "sql"
    sql_files = [
        sql_dir / "01_create_table.sql",
        sql_dir / "02_create_indexes.sql"
    ]
    
    # Executar cada arquivo
    sucesso_total = True
    for sql_file in sql_files:
        if not sql_file.exists():
            print(f"\n❌ Arquivo não encontrado: {sql_file}")
            sucesso_total = False
            continue
        
        sucesso = executar_sql_file(cursor, sql_file)
        if not sucesso:
            sucesso_total = False
    
    # Verificar tabela criada
    print(f"\n🔍 Verificando tabela...")
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'esaj_detalhe_processos'
        );
    """)
    table_exists = cursor.fetchone()[0]
    
    if table_exists:
        # Contar colunas
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'esaj_detalhe_processos';
        """)
        num_colunas = cursor.fetchone()[0]
        
        print(f"   ✅ Tabela criada com sucesso!")
        print(f"   📊 Total de colunas: {num_colunas}")
    else:
        print(f"   ❌ Tabela não foi criada!")
        sucesso_total = False
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print("\n" + "=" * 60)
    if sucesso_total:
        print("✅ TABELA E ÍNDICES CRIADOS COM SUCESSO!")
    else:
        print("❌ HOUVE ERROS NA CRIAÇÃO!")
    print("=" * 60)
    
    sys.exit(0 if sucesso_total else 1)


if __name__ == "__main__":
    main()
