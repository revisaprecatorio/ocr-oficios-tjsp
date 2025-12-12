#!/usr/bin/env python3
"""
Script de Teste V2.7.3 - Testa os 3 PDFs problemáticos

V2.7.3 Fixes:
1. Busca global de numero_ordem (sem limite de 50 páginas)
2. Detecção de CERTIDÃO DE PUBLICAÇÃO
3. Validação cpf_sucessor != credor_cpf_cnpj
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar diretório app ao path
sys.path.append(str(Path(__file__).parent / "app"))

from app.processador import ProcessadorOficio
from app.tracker_execucao import TrackerExecucao

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def main():
    print("=" * 80)
    print("🧪 TESTE V2.7.3 - 3 PDFs Problemáticos")
    print("=" * 80)

    # Configurações
    openai_api_key = os.getenv("OPENAI_API_KEY")
    db_config = {
        "host": "72.60.62.124",
        "port": 5432,
        "database": "n8n",
        "user": "admin",
        "password": "BetaAgent2024SecureDB"
    }

    # Inicializar processador V2.7.3
    processador = ProcessadorOficio(openai_api_key, db_config)

    # PDFs problemáticos
    test_cases = [
        {
            "nome": "PDF 1 - Missing numero_ordem (limite 50 páginas)",
            "cpf": "10773800891",
            "processo": "0118712-69.2021.8.26.0500",
            "esperado_numero_ordem": "4254/2022"
        },
        {
            "nome": "PDF 2 - CERTIDÃO DE PUBLICAÇÃO",
            "cpf": "13725004803",
            "processo": "0137634-56.2024.8.26.0500",
            "esperado_numero_ordem": "50228/2025"
        },
        {
            "nome": "PDF 3 - cpf_sucessor = credor_cpf_cnpj",
            "cpf": "93968396804",
            "processo": "0142161-51.2024.8.26.0500",
            "esperado_numero_ordem": "51446/2025",
            "validar_cpf_sucessor": True
        }
    ]

    # Diretório base
    data_dir = Path(__file__).parent.parent / "data" / "consultas"

    # Resultados
    resultados = []

    for test in test_cases:
        print(f"\n{'=' * 80}")
        print(f"📄 {test['nome']}")
        print(f"   CPF: {test['cpf']}")
        print(f"   Processo: {test['processo']}")
        print(f"{'=' * 80}\n")

        # Caminho do PDF
        pdf_path = data_dir / test['cpf'] / f"{test['processo']}.pdf"

        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {pdf_path}")
            resultados.append({"teste": test['nome'], "status": "PDF não encontrado"})
            continue

        # Processar (sem tracker para simplificar)
        try:
            resultado = processador.processar_arquivo(
                str(pdf_path),
                test['cpf'],
                tracker=None
            )

            # Validar resultado
            print("\n📊 Resultado:")
            print(f"   Status: {'✅ Sucesso' if resultado['sucesso'] else '❌ Erro'}")

            if resultado['sucesso']:
                dados = resultado['dados']
                numero_ordem = dados.get('numero_ordem')

                print(f"   numero_ordem: {numero_ordem}")

                # Validar numero_ordem
                if numero_ordem == test['esperado_numero_ordem']:
                    print(f"   ✅ numero_ordem CORRETO: {numero_ordem}")
                    resultado_teste = "✅ PASSOU"
                else:
                    print(f"   ❌ numero_ordem ERRADO: esperado {test['esperado_numero_ordem']}, obtido {numero_ordem}")
                    resultado_teste = "❌ FALHOU"

                # Validar cpf_sucessor se necessário
                if test.get('validar_cpf_sucessor'):
                    cpf_sucessor = dados.get('cpf_sucessor')
                    credor_cpf = dados.get('credor_cpf_cnpj')

                    print(f"   cpf_sucessor: {cpf_sucessor}")
                    print(f"   credor_cpf_cnpj: {credor_cpf}")

                    if cpf_sucessor is None:
                        print(f"   ✅ V2.7.3 FIX: cpf_sucessor corretamente zerado")
                        resultado_teste += " + FIX cpf_sucessor OK"
                    else:
                        print(f"   ❌ V2.7.3 FIX FALHOU: cpf_sucessor deveria ser NULL")
                        resultado_teste = "❌ FALHOU (cpf_sucessor)"

            else:
                print(f"   Erro: {resultado.get('erro', 'Desconhecido')}")
                resultado_teste = "❌ ERRO"

            resultados.append({"teste": test['nome'], "status": resultado_teste})

        except Exception as e:
            print(f"\n❌ EXCEÇÃO: {str(e)}")
            resultados.append({"teste": test['nome'], "status": f"❌ EXCEÇÃO: {str(e)[:100]}"})

    # Resumo
    print(f"\n{'=' * 80}")
    print("📊 RESUMO DOS TESTES V2.7.3")
    print(f"{'=' * 80}\n")

    for res in resultados:
        print(f"  {res['status']:<40} | {res['teste']}")

    print(f"\n{'=' * 80}")

    # Contar sucessos
    sucessos = sum(1 for r in resultados if "✅" in r['status'])
    total = len(resultados)

    print(f"\n✅ Sucessos: {sucessos}/{total}")

    if sucessos == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")
        return 1


if __name__ == "__main__":
    exit(main())
