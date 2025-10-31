#!/usr/bin/env python3
"""
Script de Reprocessamento - Corrige valores no banco de dados

Reprocessa o PDF problemático e atualiza o banco com valores corretos.

Processo: 0015796-15.2025.8.26.0500
CPF: 27308157830 (273.081.578-30)
PDF: Precatório-RAF.pdf

Autor: Sistema OCR Debug
Data: 31/10/2025
"""

import os
import sys
import json
import psycopg2
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Adicionar path do sistema OCR
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "3_OCR" / "1_parsing_PDF"))

from dotenv import load_dotenv

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent.parent / "3_OCR" / ".env"
load_dotenv(env_path)

# Importar processador
from app.processador import ProcessadorOficio

print("\n" + "="*80)
print("🔄 SCRIPT DE REPROCESSAMENTO")
print("="*80 + "\n")

# Configurações
PDF_PATH = Path(__file__).parent.parent / "test_data" / "Precatório-RAF.pdf"
CPF = "27308157830"
NUMERO_PROCESSO = "0015796-15.2025.8.26.0500"

# Credenciais do banco
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '72.60.62.124'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'n8n'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'BetaAgent2024SecureDB')
}

# API Key OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("📋 CONFIGURAÇÕES:")
print(f"   PDF: {PDF_PATH.name}")
print(f"   CPF: {CPF}")
print(f"   Processo: {NUMERO_PROCESSO}")
print(f"   Banco: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
print()

# Verificar se PDF existe
if not PDF_PATH.exists():
    print(f"❌ ERRO: PDF não encontrado: {PDF_PATH}")
    sys.exit(1)

# Verificar credenciais
if not OPENAI_API_KEY:
    print("❌ ERRO: OPENAI_API_KEY não configurada")
    sys.exit(1)

print("1️⃣ CONSULTAR VALORES ATUAIS NO BANCO")
print("-" * 80)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Tentar em lista_processos
    cursor.execute("""
        SELECT numero_processo, requerente_caps,
               valor_principal_liquido, valor_principal_bruto,
               juros_moratorios, valor_total_requisitado,
               timestamp_processamento
        FROM lista_processos
        WHERE cpf = %s AND numero_processo = %s
    """, (CPF, NUMERO_PROCESSO))
    
    result = cursor.fetchone()
    
    if result:
        print("✅ Registro encontrado em lista_processos:")
        print(f"   Processo: {result[0]}")
        print(f"   Requerente: {result[1]}")
        print(f"   Valor Líquido: R$ {float(result[2]):,.2f}")
        print(f"   Valor Bruto: R$ {float(result[3]):,.2f}")
        print(f"   Juros: R$ {float(result[4]):,.2f}")
        print(f"   Total: R$ {float(result[5]):,.2f}")
        print(f"   Processamento: {result[6]}")
        print()
        
        valores_antigos = {
            'valor_principal_liquido': result[2],
            'valor_principal_bruto': result[3],
            'juros_moratorios': result[4],
            'valor_total_requisitado': result[5]
        }
    else:
        # Tentar em esaj_detalhe_processos
        cursor.execute("""
            SELECT numero_processo_cnj, requerente_caps,
                   valor_principal_liquido, valor_principal_bruto,
                   juros_moratorios, valor_total_requisitado,
                   timestamp_ingestao
            FROM esaj_detalhe_processos
            WHERE cpf = %s AND numero_processo_cnj = %s
        """, (CPF, NUMERO_PROCESSO))
        
        result = cursor.fetchone()
        
        if result:
            print("✅ Registro encontrado em esaj_detalhe_processos:")
            print(f"   Processo: {result[0]}")
            print(f"   Requerente: {result[1]}")
            print(f"   Valor Líquido: R$ {float(result[2]):,.2f}")
            print(f"   Valor Bruto: R$ {float(result[3]):,.2f}")
            print(f"   Juros: R$ {float(result[4]):,.2f}")
            print(f"   Total: R$ {float(result[5]):,.2f}")
            print(f"   Ingestão: {result[6]}")
            print()
            
            valores_antigos = {
                'valor_principal_liquido': result[2],
                'valor_principal_bruto': result[3],
                'juros_moratorios': result[4],
                'valor_total_requisitado': result[5]
            }
        else:
            print("⚠️  Registro NÃO encontrado no banco")
            valores_antigos = None
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ ERRO ao consultar banco: {e}")
    valores_antigos = None

print()
print("2️⃣ REPROCESSAR PDF COM CÓDIGO ATUAL")
print("-" * 80)

# Inicializar processador
processador = ProcessadorOficio(
    openai_api_key=OPENAI_API_KEY,
    db_config=DB_CONFIG
)

# Processar PDF
print("⏳ Processando PDF...")
resultado = processador.processar_pdf(str(PDF_PATH), CPF)

if resultado['status'] == 'sucesso':
    print("✅ Processamento concluído com sucesso!")
    print()
    
    dados = resultado['dados']
    
    print("💰 VALORES EXTRAÍDOS (NOVOS):")
    print(f"   Valor Líquido: R$ {float(dados['valor_principal_liquido']):,.2f}")
    print(f"   Valor Bruto: R$ {float(dados['valor_principal_bruto']):,.2f}")
    print(f"   Juros: R$ {float(dados['juros_moratorios']):,.2f}")
    print(f"   Total: R$ {float(dados['valor_total_requisitado']):,.2f}")
    print()
    
    valores_novos = {
        'valor_principal_liquido': Decimal(str(dados['valor_principal_liquido'])),
        'valor_principal_bruto': Decimal(str(dados['valor_principal_bruto'])),
        'juros_moratorios': Decimal(str(dados['juros_moratorios'])),
        'valor_total_requisitado': Decimal(str(dados['valor_total_requisitado']))
    }
    
    # Comparar valores
    if valores_antigos:
        print("3️⃣ COMPARAÇÃO: ANTIGO vs NOVO")
        print("-" * 80)
        print(f"{'Campo':<30} {'Antigo':<20} {'Novo':<20} {'Diferença'}")
        print("-" * 80)
        
        for campo in valores_antigos.keys():
            antigo = valores_antigos[campo]
            novo = valores_novos[campo]
            diff = novo - antigo
            
            print(f"{campo:<30} R$ {float(antigo):>15,.2f}  R$ {float(novo):>15,.2f}  R$ {float(diff):>15,.2f}")
        
        print()
        
        # Perguntar se deseja atualizar
        resposta = input("❓ Deseja atualizar o banco de dados com os novos valores? (S/n): ")
        
        if resposta.lower() in ('s', 'sim', 'y', 'yes', ''):
            print()
            print("4️⃣ ATUALIZAR BANCO DE DADOS")
            print("-" * 80)
            
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                cursor = conn.cursor()
                
                # Verificar qual tabela existe
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_name IN ('lista_processos', 'esaj_detalhe_processos')
                """)
                
                tabelas = [row[0] for row in cursor.fetchall()]
                
                if 'lista_processos' in tabelas:
                    cursor.execute("""
                        UPDATE lista_processos
                        SET valor_principal_liquido = %s,
                            valor_principal_bruto = %s,
                            juros_moratorios = %s,
                            valor_total_requisitado = %s,
                            timestamp_processamento = CURRENT_TIMESTAMP
                        WHERE cpf = %s AND numero_processo = %s
                    """, (
                        valores_novos['valor_principal_liquido'],
                        valores_novos['valor_principal_bruto'],
                        valores_novos['juros_moratorios'],
                        valores_novos['valor_total_requisitado'],
                        CPF,
                        NUMERO_PROCESSO
                    ))
                    
                    print(f"✅ Atualizado {cursor.rowcount} registro(s) em lista_processos")
                
                if 'esaj_detalhe_processos' in tabelas:
                    cursor.execute("""
                        UPDATE esaj_detalhe_processos
                        SET valor_principal_liquido = %s,
                            valor_principal_bruto = %s,
                            juros_moratorios = %s,
                            valor_total_requisitado = %s,
                            timestamp_ingestao = CURRENT_TIMESTAMP
                        WHERE cpf = %s AND numero_processo_cnj = %s
                    """, (
                        valores_novos['valor_principal_liquido'],
                        valores_novos['valor_principal_bruto'],
                        valores_novos['juros_moratorios'],
                        valores_novos['valor_total_requisitado'],
                        CPF,
                        NUMERO_PROCESSO
                    ))
                    
                    print(f"✅ Atualizado {cursor.rowcount} registro(s) em esaj_detalhe_processos")
                
                conn.commit()
                cursor.close()
                conn.close()
                
                print("✅ Banco de dados atualizado com sucesso!")
                
            except Exception as e:
                print(f"❌ ERRO ao atualizar banco: {e}")
                if conn:
                    conn.rollback()
        else:
            print("\n⏭️  Atualização cancelada pelo usuário")
    
else:
    print(f"❌ ERRO no processamento: {resultado.get('erro', 'Erro desconhecido')}")

print()
print("="*80)
print("✅ SCRIPT FINALIZADO")
print("="*80 + "\n")

