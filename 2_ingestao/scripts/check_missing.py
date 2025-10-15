#!/usr/bin/env python3
"""
Script para identificar qual JSON não foi importado
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def main():
    """Função principal"""
    
    print("=" * 60)
    print("🔍 VERIFICANDO REGISTROS FALTANTES")
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
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)
    
    # Buscar todos os CPFs e processos do banco
    print(f"\n📊 Buscando registros do banco...")
    cursor.execute("""
        SELECT cpf, numero_processo_cnj 
        FROM esaj_detalhe_processos
        ORDER BY cpf, numero_processo_cnj;
    """)
    registros_banco = set((row[0], row[1]) for row in cursor.fetchall())
    print(f"   ✅ {len(registros_banco)} registros encontrados")
    
    # Listar todos os JSONs
    print(f"\n📁 Buscando JSONs processados...")
    outputs_dir = Path(__file__).parent.parent.parent / "1_parsing_PDF" / "outputs"
    json_files = list(outputs_dir.glob("lote_*/*.json"))
    
    registros_json = set()
    for json_file in json_files:
        # Extrair CPF e processo do nome do arquivo
        # Formato: {cpf}_{processo}.json
        filename = json_file.stem  # Remove .json
        
        # Remover sufixos como " (1)"
        filename = filename.split(" (")[0]
        
        parts = filename.split("_", 1)
        if len(parts) == 2:
            cpf = parts[0]
            processo = parts[1]
            registros_json.add((cpf, processo))
    
    print(f"   ✅ {len(registros_json)} JSONs encontrados")
    
    # Comparar
    print(f"\n🔍 Comparando...")
    faltantes = registros_json - registros_banco
    
    if faltantes:
        print(f"\n❌ REGISTROS FALTANTES NO BANCO: {len(faltantes)}")
        print("=" * 60)
        for cpf, processo in sorted(faltantes):
            print(f"   CPF: {cpf}")
            print(f"   Processo: {processo}")
            
            # Buscar arquivo JSON correspondente
            for json_file in json_files:
                if cpf in json_file.name and processo in json_file.name:
                    print(f"   Arquivo: {json_file.relative_to(outputs_dir)}")
                    break
            print()
    else:
        print("   ✅ Todos os JSONs estão no banco!")
    
    # Verificar se há registros no banco que não têm JSON
    extras = registros_banco - registros_json
    if extras:
        print(f"\n⚠️  REGISTROS NO BANCO SEM JSON: {len(extras)}")
        for cpf, processo in sorted(extras):
            print(f"   CPF: {cpf} | Processo: {processo}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICAÇÃO CONCLUÍDA")
    print("=" * 60)


if __name__ == "__main__":
    main()
