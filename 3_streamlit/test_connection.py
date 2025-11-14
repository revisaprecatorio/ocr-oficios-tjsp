#!/usr/bin/env python3
"""
Quick test to verify PostgreSQL connection
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=" * 60)
print("🔍 TESTANDO CONEXÃO COM POSTGRESQL")
print("=" * 60)
print()

# Show config (hide password)
print("📋 Configuração:")
print(f"   Host: {os.getenv('DB_HOST')}")
print(f"   Port: {os.getenv('DB_PORT')}")
print(f"   Database: {os.getenv('DB_NAME')}")
print(f"   User: {os.getenv('DB_USER')}")
print(f"   Password: {'*' * len(os.getenv('DB_PASSWORD', ''))}")
print()

try:
    print("🔌 Conectando...")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    
    print("✅ Conexão estabelecida!")
    print()
    
    # Test query
    print("📊 Testando query...")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN preferencial = TRUE THEN 1 END) as preferencial,
            COUNT(CASE WHEN habilitacao_herdeiros = TRUE THEN 1 END) as habilitacao,
            COUNT(CASE WHEN cessao_credito = TRUE THEN 1 END) as cessao
        FROM esaj_detalhe_processos
    """)
    
    result = cursor.fetchone()
    
    print("✅ Query executada com sucesso!")
    print()
    print("📈 Resultados:")
    print(f"   Total de processos: {result[0]}")
    print(f"   Com preferência: {result[1]}")
    print(f"   Com habilitação: {result[2]}")
    print(f"   Com cessão: {result[3]}")
    print()
    
    cursor.close()
    conn.close()
    
    print("=" * 60)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    print()
    print("💡 Possíveis causas:")
    print("   1. VPS não está acessível")
    print("   2. Credenciais incorretas")
    print("   3. Database 'oficios_tjsp' não existe")
    print("   4. Firewall bloqueando porta 5432")
    print()
    exit(1)
