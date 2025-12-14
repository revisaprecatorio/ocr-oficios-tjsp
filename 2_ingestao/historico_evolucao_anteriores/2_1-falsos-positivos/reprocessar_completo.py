#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Python para limpar tabela e reprocessar todos os PDFs.
Alternativa ao script bash para ambientes sem psql no PATH.

Autor: Cascade AI + Persival Balleste
Data: 15/10/2025
"""

import os
import sys
import subprocess
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Cores para terminal
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(text):
    """Imprime cabeçalho formatado."""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")

def print_success(text):
    """Imprime mensagem de sucesso."""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_error(text):
    """Imprime mensagem de erro."""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def print_warning(text):
    """Imprime mensagem de aviso."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")

def print_info(text):
    """Imprime mensagem informativa."""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.NC}")


def conectar_postgres():
    """Conecta ao PostgreSQL usando variáveis de ambiente."""
    try:
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'oficios_tjsp')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD')
        
        print_info(f"Conectando: {user}@{host}:{port}/{database}")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        print_error(f"Erro ao conectar ao PostgreSQL: {e}")
        return None


def limpar_tabela():
    """Limpa a tabela lista_processos."""
    print_header("📊 PASSO 1: Limpar Tabela PostgreSQL")
    
    print_warning("ATENÇÃO: Isso vai DELETAR todos os registros da tabela lista_processos!")
    resposta = input("\nDeseja continuar? (s/N): ").strip().lower()
    
    if resposta != 's':
        print_error("Operação cancelada pelo usuário")
        return False
    
    print("\n🗑️  Limpando tabela...")
    
    conn = conectar_postgres()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE lista_processos CASCADE;")
        conn.commit()
        
        # Verificar
        cursor.execute("SELECT COUNT(*) FROM lista_processos;")
        count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print_success("Tabela limpa com sucesso")
        print(f"📊 Registros na tabela: {count}")
        
        return True
        
    except Exception as e:
        print_error(f"Erro ao limpar tabela: {e}")
        if conn:
            conn.close()
        return False


def reprocessar_pdfs():
    """Reprocessa todos os PDFs com a nova lógica."""
    print_header("🔄 PASSO 2: Reprocessar PDFs com Lógica Corrigida")
    
    project_root = Path(__file__).parent.parent.parent
    parsing_dir = project_root / "1_parsing_PDF"
    data_dir = project_root / "data" / "consultas"
    
    print(f"📁 Diretório de PDFs: {data_dir}")
    
    # Contar PDFs
    pdf_count = len(list(data_dir.rglob("*.pdf")))
    print(f"📄 Total de PDFs: {pdf_count}")
    print(f"⏱️  Tempo estimado: ~{pdf_count * 30 // 60} minutos\n")
    
    resposta = input("Iniciar reprocessamento? (s/N): ").strip().lower()
    
    if resposta != 's':
        print_error("Reprocessamento cancelado")
        return False
    
    print("\n🚀 Iniciando reprocessamento...\n")
    
    # Executar script de processamento
    try:
        result = subprocess.run(
            [
                sys.executable,
                "processar_lotes_v2.py",
                "--input", str(data_dir),
                "--output", "outputs",
                "--limite", "0"
            ],
            cwd=parsing_dir,
            check=True,
            capture_output=False
        )
        
        print()
        print_success("Reprocessamento concluído")
        return True
        
    except subprocess.CalledProcessError as e:
        print()
        print_error(f"Erro no reprocessamento: {e}")
        return False


def importar_jsons():
    """Importa JSONs para PostgreSQL."""
    print_header("📥 PASSO 3: Importar JSONs para PostgreSQL")
    
    project_root = Path(__file__).parent.parent.parent
    ingestao_dir = project_root / "2_ingestao"
    parsing_dir = project_root / "1_parsing_PDF"
    json_dir = parsing_dir / "outputs" / "json"
    
    print(f"📁 Diretório de JSONs: {json_dir}\n")
    
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/ingest_all_jsons.py",
                "--input", str(json_dir),
                "--db-host", os.getenv('POSTGRES_HOST', 'localhost'),
                "--db-port", os.getenv('POSTGRES_PORT', '5432'),
                "--db-name", os.getenv('POSTGRES_DB', 'oficios_tjsp'),
                "--db-user", os.getenv('POSTGRES_USER', 'postgres')
            ],
            cwd=ingestao_dir,
            check=True,
            capture_output=False
        )
        
        print()
        print_success("Importação concluída")
        return True
        
    except subprocess.CalledProcessError as e:
        print()
        print_error(f"Erro na importação: {e}")
        return False


def validar_correcao():
    """Valida se a correção foi bem-sucedida."""
    print_header("✅ PASSO 4: Validar Correção")
    
    conn = conectar_postgres()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar falsos rejeitados
        print("📊 Verificando falsos rejeitados...\n")
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM lista_processos 
            WHERE numero_ordem IS NOT NULL 
              AND rejeitado = TRUE 
              AND motivo_rejeicao IS NULL
        """)
        falsos_rejeitados = cursor.fetchone()[0]
        
        print(f"❌ Falsos rejeitados encontrados: {falsos_rejeitados}")
        
        if falsos_rejeitados == 0:
            print_success("Nenhum falso rejeitado! Correção bem-sucedida!")
        else:
            print_warning(f"Ainda existem {falsos_rejeitados} falsos rejeitados")
        
        print()
        
        # Estatísticas gerais
        print("📊 Estatísticas Gerais:\n")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_processos,
                SUM(CASE WHEN rejeitado = TRUE THEN 1 ELSE 0 END) as rejeitados,
                SUM(CASE WHEN rejeitado = FALSE THEN 1 ELSE 0 END) as aceitos,
                SUM(CASE WHEN numero_ordem IS NOT NULL THEN 1 ELSE 0 END) as com_numero_ordem
            FROM lista_processos
        """)
        
        stats = cursor.fetchone()
        print(f"  Total de processos: {stats[0]}")
        print(f"  Rejeitados: {stats[1]}")
        print(f"  Aceitos: {stats[2]}")
        print(f"  Com número de ordem: {stats[3]}")
        print()
        
        # Verificar os 13 casos específicos
        print("📋 Verificando os 13 casos corrigidos:\n")
        
        cpfs = [
            '95653511820', '94706751853', '94019940800', '49783491920',
            '41609824415', '19884761434', '11659296862', '10185170811',
            '10149607890', '06495530803', '03730461893', '02174781824',
            '01103192817'
        ]
        
        cursor.execute(f"""
            SELECT cpf, numero_processo, numero_ordem, rejeitado
            FROM lista_processos
            WHERE cpf IN ({','.join(['%s'] * len(cpfs))})
            ORDER BY cpf
        """, cpfs)
        
        casos = cursor.fetchall()
        
        if casos:
            print(f"{'CPF':<15} {'Processo':<30} {'Ordem':<15} {'Rejeitado'}")
            print("-" * 80)
            for caso in casos:
                rejeitado_str = "❌ SIM" if caso[3] else "✅ NÃO"
                print(f"{caso[0]:<15} {caso[1]:<30} {caso[2] or 'N/A':<15} {rejeitado_str}")
        else:
            print_warning("Nenhum dos 13 casos encontrado no banco!")
        
        cursor.close()
        conn.close()
        
        print()
        return True
        
    except Exception as e:
        print_error(f"Erro na validação: {e}")
        if conn:
            conn.close()
        return False


def main():
    """Função principal."""
    print_header("🔧 CORREÇÃO DE FALSOS REJEITADOS - Reprocessamento Completo")
    
    # Carregar variáveis de ambiente
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print_info(f"Variáveis carregadas de: {env_file}")
    else:
        print_warning(f"Arquivo .env não encontrado: {env_file}")
    
    print()
    
    # Verificar ambiente virtual
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_warning("Ambiente virtual não detectado!")
        resposta = input("Continuar mesmo assim? (s/N): ").strip().lower()
        if resposta != 's':
            print_error("Operação cancelada")
            return
    else:
        print_success("Ambiente virtual ativado")
    
    print()
    
    # Executar passos
    if not limpar_tabela():
        print_error("Falha ao limpar tabela. Abortando.")
        return
    
    if not reprocessar_pdfs():
        print_error("Falha ao reprocessar PDFs. Abortando.")
        return
    
    if not importar_jsons():
        print_error("Falha ao importar JSONs. Abortando.")
        return
    
    if not validar_correcao():
        print_error("Falha na validação.")
        return
    
    # Conclusão
    print_header("🎉 REPROCESSAMENTO CONCLUÍDO!")
    
    print("📝 Próximos passos:")
    print("   1. Verificar interface Streamlit")
    print("   2. Commit das alterações")
    print("   3. Deploy em produção")
    print()


if __name__ == "__main__":
    main()
