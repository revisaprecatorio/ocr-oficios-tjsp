#!/usr/bin/env python3
"""
Script de Validação de Dados
Executa queries de teste e exibe estatísticas
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from tabulate import tabulate

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def executar_query(cursor, titulo: str, query: str):
    """Executa uma query e exibe resultados"""
    print(f"\n{'='*60}")
    print(f"📊 {titulo}")
    print(f"{'='*60}")
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        
        if results:
            # Pegar nomes das colunas
            colnames = [desc[0] for desc in cursor.description]
            print(tabulate(results, headers=colnames, tablefmt="grid"))
        else:
            print("   (Nenhum resultado)")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False


def main():
    """Função principal"""
    
    print("=" * 60)
    print("🔍 VALIDAÇÃO DE DADOS")
    print("=" * 60)
    
    # Configuração do banco
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    # Conectar
    print(f"\n🔌 Conectando ao PostgreSQL...")
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)
    
    # Queries de validação
    queries = [
        ("Total de Registros", "SELECT COUNT(*) as total FROM esaj_detalhe_processos;"),
        
        ("Distribuição por Status", """
            SELECT 
                CASE WHEN rejeitado THEN 'Rejeitado' ELSE 'Aprovado' END as status,
                COUNT(*) as total,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
            FROM esaj_detalhe_processos
            GROUP BY rejeitado;
        """),
        
        ("Top 5 CPFs com Mais Processos", """
            SELECT 
                cpf,
                COUNT(*) as total_processos
            FROM esaj_detalhe_processos
            GROUP BY cpf
            ORDER BY total_processos DESC
            LIMIT 5;
        """),
        
        ("Valores Financeiros", """
            SELECT 
                COUNT(*) as total_processos,
                TO_CHAR(SUM(valor_total_requisitado), 'FM999,999,999.00') as valor_total,
                TO_CHAR(AVG(valor_total_requisitado), 'FM999,999.00') as valor_medio
            FROM esaj_detalhe_processos
            WHERE valor_total_requisitado IS NOT NULL;
        """),
        
        ("Preferências", """
            SELECT 
                SUM(CASE WHEN idoso THEN 1 ELSE 0 END) as idosos,
                SUM(CASE WHEN doenca_grave THEN 1 ELSE 0 END) as doenca_grave,
                SUM(CASE WHEN pcd THEN 1 ELSE 0 END) as pcd
            FROM esaj_detalhe_processos;
        """),
        
        ("Processos Pendentes de Diagnóstico", """
            SELECT COUNT(*) as pendentes
            FROM esaj_detalhe_processos
            WHERE process_diagnostico = false;
        """),
    ]
    
    # Executar queries
    for titulo, query in queries:
        executar_query(cursor, titulo, query)
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ VALIDAÇÃO CONCLUÍDA")
    print("=" * 60)


if __name__ == "__main__":
    main()
