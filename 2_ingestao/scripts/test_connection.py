#!/usr/bin/env python3
"""
Script de Teste de Conexão PostgreSQL
Valida credenciais e conectividade com o banco de dados
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def test_connection():
    """Testa conexão com PostgreSQL"""
    
    print("=" * 60)
    print("🔌 TESTE DE CONEXÃO POSTGRESQL")
    print("=" * 60)
    
    # Ler configurações
    config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    # Exibir configuração (sem senha)
    print(f"\n📋 Configuração:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Database: {config['database']}")
    print(f"   User: {config['user']}")
    print(f"   Password: {'*' * len(config['password']) if config['password'] else 'NOT SET'}")
    
    # Validar configuração
    if not all(config.values()):
        print("\n❌ ERRO: Configuração incompleta!")
        print("   Verifique se o arquivo .env existe e está configurado corretamente.")
        return False
    
    # Tentar conectar
    print(f"\n🔄 Tentando conectar...")
    
    try:
        conn = psycopg2.connect(**config)
        cursor = conn.cursor()
        
        # Testar query simples
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'esaj_detalhe_processos'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        # Contar registros (se tabela existe)
        total_registros = 0
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM esaj_detalhe_processos;")
            total_registros = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        # Sucesso!
        print("\n✅ CONEXÃO BEM-SUCEDIDA!")
        print(f"\n📊 Informações do Banco:")
        print(f"   Versão: {version[:50]}...")
        print(f"   Tabela 'esaj_detalhe_processos': {'✅ Existe' if table_exists else '❌ Não existe'}")
        if table_exists:
            print(f"   Total de registros: {total_registros}")
        
        print("\n" + "=" * 60)
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ ERRO DE CONEXÃO:")
        print(f"   {str(e)}")
        print("\n💡 Possíveis causas:")
        print("   - Host/porta incorretos")
        print("   - Credenciais inválidas")
        print("   - Firewall bloqueando conexão")
        print("   - PostgreSQL não está rodando")
        print("\n" + "=" * 60)
        return False
        
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO:")
        print(f"   {str(e)}")
        print("\n" + "=" * 60)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
