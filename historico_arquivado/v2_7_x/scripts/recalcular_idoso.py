#!/usr/bin/env python3
"""
Script para Recalcular Tag IDOSO baseado em data_nascimento
============================================================
Atualiza a coluna 'idoso' na tabela esaj_detalhe_processos
baseado na data de nascimento do requerente.

Lógica: idoso = TRUE se idade >= 60 anos
        onde idade = data_atual - data_nascimento

Uso:
    python recalcular_idoso.py
"""

import os
import sys
from pathlib import Path
from datetime import date, datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def calcular_idade(data_nascimento: date) -> int:
    """Calcula idade em anos a partir da data de nascimento"""
    hoje = date.today()
    idade = hoje.year - data_nascimento.year
    
    # Ajustar se ainda não fez aniversário este ano
    if (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    
    return idade


def conectar_db():
    """Conecta ao PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'n8n'),
        user=os.getenv('DB_USER', 'admin'),
        password=os.getenv('DB_PASSWORD')
    )


def main():
    """Função principal"""
    
    print("=" * 80)
    print("🔄 RECÁLCULO DA TAG IDOSO")
    print("=" * 80)
    print()
    
    # Conectar ao banco
    print("🔌 Conectando ao PostgreSQL...")
    try:
        conn = conectar_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    print()
    
    # 1. Buscar todos os registros com data_nascimento
    print("📊 Buscando registros com data_nascimento...")
    cur.execute("""
        SELECT id, cpf, numero_processo_cnj, requerente_caps, 
               data_nascimento, idoso
        FROM esaj_detalhe_processos
        WHERE data_nascimento IS NOT NULL
        ORDER BY data_nascimento;
    """)
    
    registros = cur.fetchall()
    total_registros = len(registros)
    
    print(f"   ✅ Encontrados {total_registros} registros com data_nascimento")
    print()
    
    if total_registros == 0:
        print("⚠️  Nenhum registro para processar!")
        conn.close()
        return
    
    # 2. Processar cada registro
    print("🔄 Processando registros...")
    print("-" * 80)
    
    stats = {
        "total": total_registros,
        "idosos": 0,
        "nao_idosos": 0,
        "atualizados": 0,
        "ja_corretos": 0,
        "erros": 0
    }
    
    data_hoje = date.today()
    
    for registro in registros:
        try:
            # Calcular idade
            idade = calcular_idade(registro['data_nascimento'])
            eh_idoso = idade >= 60
            
            # Verificar se precisa atualizar
            idoso_atual = registro['idoso']
            precisa_atualizar = (idoso_atual != eh_idoso)
            
            # Estatísticas
            if eh_idoso:
                stats["idosos"] += 1
            else:
                stats["nao_idosos"] += 1
            
            # Atualizar se necessário
            if precisa_atualizar:
                cur.execute("""
                    UPDATE esaj_detalhe_processos
                    SET idoso = %s
                    WHERE id = %s;
                """, (eh_idoso, registro['id']))
                
                stats["atualizados"] += 1
                
                status = "✅ IDOSO" if eh_idoso else "❌ NÃO IDOSO"
                print(f"{status:15} | Idade: {idade:2} anos | CPF: {registro['cpf']} | {registro['requerente_caps'][:40]}")
            else:
                stats["ja_corretos"] += 1
        
        except Exception as e:
            stats["erros"] += 1
            print(f"❌ ERRO | CPF: {registro['cpf']} | Erro: {str(e)[:50]}")
    
    # Commit das alterações
    conn.commit()
    
    print("-" * 80)
    print()
    
    # 3. Resumo final
    print("=" * 80)
    print("📊 RESUMO DO RECÁLCULO")
    print("=" * 80)
    print(f"Data de referência: {data_hoje.strftime('%d/%m/%Y')}")
    print()
    print(f"Total de registros processados: {stats['total']}")
    print(f"   ✅ Idosos (≥60 anos):         {stats['idosos']} ({stats['idosos']/stats['total']*100:.1f}%)")
    print(f"   ❌ Não idosos (<60 anos):     {stats['nao_idosos']} ({stats['nao_idosos']/stats['total']*100:.1f}%)")
    print()
    print(f"Registros atualizados:          {stats['atualizados']}")
    print(f"Registros já corretos:          {stats['ja_corretos']}")
    print(f"Erros:                          {stats['erros']}")
    print()
    
    # 4. Validação final
    print("🔍 Validação final...")
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN idoso = TRUE THEN 1 END) as idosos,
            COUNT(CASE WHEN idoso = FALSE THEN 1 END) as nao_idosos,
            COUNT(CASE WHEN idoso IS NULL THEN 1 END) as sem_flag
        FROM esaj_detalhe_processos
        WHERE data_nascimento IS NOT NULL;
    """)
    
    validacao = cur.fetchone()
    
    print(f"   Total:      {validacao['total']}")
    print(f"   Idosos:     {validacao['idosos']}")
    print(f"   Não idosos: {validacao['nao_idosos']}")
    print(f"   Sem flag:   {validacao['sem_flag']}")
    print()
    
    if validacao['sem_flag'] > 0:
        print("⚠️  ATENÇÃO: Existem registros sem flag idoso definida!")
    else:
        print("✅ Todos os registros com data_nascimento têm flag idoso definida!")
    
    print()
    print("=" * 80)
    print("✅ RECÁLCULO CONCLUÍDO!")
    print("=" * 80)
    
    # Fechar conexão
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
