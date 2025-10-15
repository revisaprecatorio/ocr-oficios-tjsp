#!/usr/bin/env python3
"""
Reprocessar apenas os 3 PDFs que falharam na Fase 2
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from app.processador import ProcessadorOficio

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def reprocessar():
    """Reprocessar os 3 PDFs que falharam"""
    
    # PDFs que falharam
    pdfs_erro = [
        ("10493829865", "7009029-90.2012.8.26.0500.pdf"),
        ("11144967821", "7009029-90.2012.8.26.0500.pdf"),
        ("51525003968", "7002920-94.2011.8.26.0500.pdf"),
    ]
    
    processador = ProcessadorOficio(
        openai_api_key=OPENAI_API_KEY,
        db_config=None
    )
    
    resultados = {
        "total": len(pdfs_erro),
        "sucesso": 0,
        "erros": 0,
        "detalhes": []
    }
    
    base_dir = Path(__file__).parent.parent / "data" / "consultas"
    
    for cpf, pdf_name in pdfs_erro:
        print(f"\n{'='*60}")
        print(f"📄 Processando: {pdf_name}")
        print(f"   CPF: {cpf}")
        print(f"{'='*60}")
        
        pdf_path = base_dir / cpf / pdf_name
        
        try:
            resultado = processador.processar_arquivo(str(pdf_path), cpf)
            
            if resultado['sucesso']:
                print("✅ SUCESSO!")
                resultados["sucesso"] += 1
                resultados["detalhes"].append({
                    "pdf": pdf_name,
                    "cpf": cpf,
                    "status": "sucesso"
                })
            else:
                print(f"❌ ERRO: {resultado.get('erro', 'N/A')}")
                resultados["erros"] += 1
                resultados["detalhes"].append({
                    "pdf": pdf_name,
                    "cpf": cpf,
                    "status": "erro",
                    "mensagem": resultado.get('erro', 'N/A')
                })
        
        except Exception as e:
            print(f"❌ EXCEÇÃO: {e}")
            resultados["erros"] += 1
            resultados["detalhes"].append({
                "pdf": pdf_name,
                "cpf": cpf,
                "status": "excecao",
                "mensagem": str(e)
            })
    
    # Resumo
    print(f"\n{'='*60}")
    print("📊 RESUMO DO REPROCESSAMENTO")
    print(f"{'='*60}")
    print(f"Total: {resultados['total']}")
    print(f"✅ Sucesso: {resultados['sucesso']}")
    print(f"❌ Erros: {resultados['erros']}")
    print(f"Taxa: {resultados['sucesso']/resultados['total']*100:.1f}%")
    print(f"{'='*60}\n")
    
    # Salvar resultados
    with open("reprocessamento_resultado.json", "w") as f:
        json.dump(resultados, f, indent=2)
    
    return resultados

if __name__ == "__main__":
    reprocessar()
