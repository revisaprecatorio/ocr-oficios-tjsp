import os
import sys
import psycopg2
from dotenv import load_dotenv

# Configura encoding para imprimir caracteres especiais no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Carrega o arquivo .env da pasta atual
load_dotenv()

def testar_conexao():
    print("="*50)
    print("🧪 TESTE DE CONEXÃO COM POSTGRESQL")
    print("="*50)

    # 1. Verificar Variáveis de Ambiente
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    print(f"📂 Configurações lidas do .env:")
    print(f"   - Host: {host}")
    print(f"   - Port: {port}")
    print(f"   - Database: {dbname}")
    print(f"   - User: {user}")
    print(f"   - Password: {'OK (Oculto)' if password else '❌ AUSENTE'}")

    if not all([host, port, dbname, user, password]):
        print("\n❌ ERRO: Faltam variáveis no arquivo .env!")
        print("   Verifique se os nomes estão como DB_HOST, DB_PORT, etc.")
        return

    # 2. Tentar Conexão
    print("\n🔌 Tentando conectar ao banco de dados...")
    conn = None
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=dbname,
            user=user,
            password=password,
            connect_timeout=10
        )
        
        # 3. Testar Query Simples
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        
        # 4. Verificar se a tabela existe (opcional, mas bom pra saber)
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'public'
                AND    table_name   = 'esaj_detalhe_processos'
            );
        """)
        table_exists = cur.fetchone()[0]

        print("\n✅ CONEXÃO BEM SUCEDIDA!")
        print(f"   ℹ️  Versão do Banco: {db_version[0]}")
        print(f"   ℹ️  Tabela 'esaj_detalhe_processos' existe? {'Sim' if table_exists else 'Não (será criada pelo pipeline)'}")

        cur.close()

    except Exception as e:
        print("\n❌ FALHA NA CONEXÃO:")
        print(f"   Erro: {e}")
        print("\n   Dica: Verifique se o IP da VPS está acessível e se a senha está correta.")
    
    finally:
        if conn:
            conn.close()
            print("\n🔌 Conexão fechada.")

if __name__ == "__main__":
    testar_conexao()