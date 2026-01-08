import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from datetime import date

# Configuração de caminhos para achar o .env
# O script está em: 2_ingestao/scripts/recalcular_idoso.py
# O .env está na raiz: ocr-oficios-tjsp/.env
# Precisamos subir 2 níveis
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(env_path)

def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def main():
    print("=" * 50)
    print("👴 ATUALIZANDO TAG 'IDOSO' NO BANCO DE DADOS")
    print("=" * 50)

    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
    }

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # 1. Marca como IDOSO quem tem data de nascimento e idade >= 60 anos
        # Usando a função AGE do próprio PostgreSQL para ser mais rápido
        print("🔄 Recalculando flags...")
        
        update_query = """
            UPDATE esaj_detalhe_processos
            SET idoso = TRUE
            WHERE data_nascimento IS NOT NULL
              AND data_nascimento <= CURRENT_DATE - INTERVAL '60 years'
              AND idoso = FALSE;
        """
        cur.execute(update_query)
        updated_rows = cur.rowcount
        conn.commit()

        print(f"✅ Sucesso! {updated_rows} registros foram marcados como IDOSO.")
        
        # Opcional: Contagem total
        cur.execute("SELECT COUNT(*) FROM esaj_detalhe_processos WHERE idoso = TRUE;")
        total_idosos = cur.fetchone()[0]
        print(f"📊 Total de idosos no banco agora: {total_idosos}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Erro ao conectar ou atualizar: {e}")

if __name__ == "__main__":
    main()