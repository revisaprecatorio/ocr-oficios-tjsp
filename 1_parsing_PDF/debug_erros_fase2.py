#!/usr/bin/env python3
"""
Debug de erros específicos da Fase 2 (51 PDFs)
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador import ProcessadorOficio

# Carregar variáveis de ambiente
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def debug_pdf(cpf: str, pdf_name: str):
    """Debug de um PDF específico"""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGANDO: {pdf_name}")
    print(f"   CPF: {cpf}")
    print(f"{'='*80}\n")
    
    # Construir caminho
    base_dir = Path(__file__).parent.parent / "data" / "consultas"
    pdf_path = base_dir / cpf / pdf_name
    
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

if __name__ == "__main__":
    print("🔧 DEBUG DE ERROS - FASE 2")
    
    # PDFs que falharam na Fase 2
    erros = [
        ("10493829865", "7009029-90.2012.8.26.0500.pdf"),
        ("11144967821", "7009029-90.2012.8.26.0500.pdf"),
        ("51525003968", "7002920-94.2011.8.26.0500.pdf"),
    ]
    
    print(f"Total de PDFs com erro: {len(erros)}\n")
    
    for cpf, pdf_name in erros:
        debug_pdf(cpf, pdf_name)
    
    print(f"\n{'='*80}")
    print("✅ Debug concluído")
    print(f"{'='*80}")
