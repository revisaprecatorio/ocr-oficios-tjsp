#!/usr/bin/env python3
"""
Script para debugar os 2 PDFs que falharam na V2.1
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

# Carregar variáveis de ambiente
load_dotenv()

from app.processador import ProcessadorOficio

# Configuração
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
BASE_DIR = Path(__file__).parent.parent / 'data' / 'consultas'

# PDFs que falharam
PDFS_ERRO = [
    ('03730461893', '0037256-10.2015.8.26.0500.pdf'),
    ('10155175874', '7007859-54.2010.8.26.0500.pdf')
]

def debug_pdf(cpf: str, pdf_name: str):
    """Debug um PDF específico"""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGANDO: {pdf_name}")
    print(f"   CPF: {cpf}")
    print(f"{'='*80}\n")
    
    pdf_path = BASE_DIR / cpf / pdf_name
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return
    
    # Criar processador (sem DB)
    processador = ProcessadorOficio(
        openai_api_key=OPENAI_API_KEY,
        db_config=None  # Não salvar no banco
    )
    
    # Processar
    try:
        resultado = processador.processar_arquivo(str(pdf_path), cpf)
        
        if resultado['sucesso']:
            print("✅ SUCESSO!")
            print(f"   Dados extraídos: {len(resultado.get('dados', {}))} campos")
        else:
            print("❌ ERRO!")
            print(f"   Mensagem: {resultado.get('erro', 'N/A')}")
            
            # Tentar extrair detalhes do erro
            if 'validation error' in resultado.get('erro', '').lower():
                print("\n📋 DETALHES DO ERRO DE VALIDAÇÃO:")
                print(resultado.get('erro', 'N/A'))
    
    except Exception as e:
        print(f"❌ EXCEÇÃO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("🔧 DEBUG DE ERROS - V2.1")
    print(f"Total de PDFs com erro: {len(PDFS_ERRO)}")
    
    for cpf, pdf_name in PDFS_ERRO:
        debug_pdf(cpf, pdf_name)
    
    print(f"\n{'='*80}")
    print("✅ Debug concluído")
    print(f"{'='*80}")
