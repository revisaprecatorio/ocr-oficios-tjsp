#!/usr/bin/env python3
"""
Teste V2.7.6 - Validar FIX de doenca_grave com detecção de resposta

V2.7.6 Fix:
- Detectar campo "Portador de doença grave: [Sim/Não]"
- Extrair e validar RESPOSTA (não apenas keyword)
- Retornar TRUE apenas se resposta = "Sim"

Casos de teste:
1. CPF 08212993876: Portador de doença grave: Não → esperado: FALSE
2. CPF 10582304849: Portador de doença grave: Não → esperado: FALSE
3. CPF 03736870876: Portador de doença grave: Não → esperado: FALSE
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Adicionar pasta app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador import ProcessadorOficio
from app.tracker_execucao import TrackerExecucao

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def main():
    print("=" * 80)
    print("🧪 TESTE V2.7.6 - FIX doenca_grave Detection Bug")
    print("=" * 80)
    print()
    print("🎯 Objetivo: Validar que doenca_grave retorna FALSE quando resposta = 'Não'")
    print("   (Bug v2.5.3: retornava TRUE apenas pela keyword, ignorando resposta)")
    print()

    # Configurações
    openai_api_key = os.getenv("OPENAI_API_KEY")
    db_config = {
        "host": "72.60.62.124",
        "port": 5432,
        "database": "n8n",
        "user": "admin",
        "password": "BetaAgent2024SecureDB"
    }

    # Inicializar processador V2.7.6
    processador = ProcessadorOficio(openai_api_key, db_config)

    # PDFs de teste (todos com "Portador de doença grave: Não")
    testes = [
        ("08212993876", "0137034-35.2024.8.26.0500"),
        ("10582304849", "0137452-70.2024.8.26.0500"),
        ("03736870876", "0137444-93.2024.8.26.0500"),
    ]

    resultados = []
    total_testes = len(testes)
    testes_passed = 0

    print(f"📊 Total de testes: {total_testes}\n")

    for cpf, processo in testes:
        print(f"{'='*60}")
        print(f"🔬 Teste: CPF {cpf}")
        print(f"{'='*60}")

        pdf_path = Path(__file__).parent.parent / "data" / "consultas" / cpf / f"{processo}.pdf"

        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {pdf_path}\n")
            continue

        print(f"📁 PDF: {pdf_path.name}")
        print(f"📄 Processo: {processo}")
        print()

        try:
            resultado = processador.processar_arquivo(
                str(pdf_path),
                cpf,
                tracker=None  # Sem tracker para simplificar output
            )

            if resultado['sucesso']:
                dados = resultado['dados']
                doenca_grave = dados.get('doenca_grave', False)

                print(f"✅ Processamento: SUCESSO")
                print(f"👤 Credor: {dados.get('credor_nome', 'N/A')}")
                print(f"🏥 doenca_grave: {doenca_grave}")
                print()

                # Validar: deve ser FALSE (resposta é "Não" no PDF)
                if doenca_grave == False:
                    print("🎉 TESTE PASSOU: doenca_grave = False (correto!)")
                    testes_passed += 1
                    resultados.append({
                        "cpf": cpf,
                        "processo": processo,
                        "passou": True,
                        "doenca_grave": doenca_grave
                    })
                else:
                    print("❌ TESTE FALHOU: doenca_grave = True (esperado: False)")
                    resultados.append({
                        "cpf": cpf,
                        "processo": processo,
                        "passou": False,
                        "doenca_grave": doenca_grave
                    })
            else:
                print(f"❌ Processamento: ERRO - {resultado.get('erro', 'Desconhecido')}")
                resultados.append({
                    "cpf": cpf,
                    "processo": processo,
                    "passou": False,
                    "erro": resultado.get('erro')
                })

        except Exception as e:
            print(f"❌ EXCEÇÃO: {str(e)}")
            resultados.append({
                "cpf": cpf,
                "processo": processo,
                "passou": False,
                "excecao": str(e)
            })

        print()

    # Resumo final
    print("=" * 80)
    print("📊 RESULTADO FINAL V2.7.6")
    print("=" * 80)
    print(f"Total de testes: {total_testes}")
    print(f"Testes passados: {testes_passed}/{total_testes}")
    print(f"Taxa de sucesso: {testes_passed/total_testes*100:.1f}%")
    print()

    if testes_passed == total_testes:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ V2.7.6 FIX: doenca_grave agora valida resposta (Sim/Não)")
        print()
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("Detalhes:")
        for r in resultados:
            if not r.get('passou'):
                print(f"  - CPF {r['cpf']}: {r.get('erro') or r.get('excecao', 'Unknown')}")
        print()
        return 1


if __name__ == "__main__":
    exit(main())
