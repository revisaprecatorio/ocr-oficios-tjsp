#!/usr/bin/env python3
"""
Script de Teste V2.5.3 - Validar Detecções com Amostra de 4 CPFs
Testa especificamente:
1. Habilitação de Herdeiros (2 casos): 576.290.808-91, 105.823.048-49
2. Doença Grave (1 caso): 137.250.048-03
3. Caso Normal (1 caso): 037.368.708-76

Data: 04/12/2025
"""

import sys
import os
from pathlib import Path
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent.parent / ".env")

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.processador import ProcessadorOficio

# CPFs de teste da amostra (com números de processo REAIS encontrados)
CASOS_TESTE = [
    {
        "cpf": "576.290.808-91",
        "processo": "0137448-33.2024.8.26.0500",  # CORRIGIDO
        "esperado": {
            "habilitacao_herdeiros": True,
            "obito": True,
            "doenca_grave": False
        },
        "descricao": "Herdeiros habilitados (código 9270 no PDF)"
    },
    {
        "cpf": "105.823.048-49",
        "processo": "0137452-70.2024.8.26.0500",  # CORRIGIDO
        "esperado": {
            "habilitacao_herdeiros": True,
            "obito": True,
            "doenca_grave": False
        },
        "descricao": "Herdeiros habilitados (código 9270 no PDF)"
    },
    {
        "cpf": "137.250.048-03",
        "processo": "0137634-56.2024.8.26.0500",  # CORRIGIDO
        "esperado": {
            "habilitacao_herdeiros": False,
            "obito": False,
            "doenca_grave": True
        },
        "descricao": "Doença grave (sem óbito)"
    },
    {
        "cpf": "037.368.708-76",
        "processo": "0137444-93.2024.8.26.0500",
        "esperado": {
            "habilitacao_herdeiros": False,
            "obito": False,
            "doenca_grave": False,
            "idoso": True,
            "preferencial": True
        },
        "descricao": "Caso normal (idoso + preferencial)"
    }
]


def main():
    print("=" * 80)
    print("🧪 TESTE V2.5.3 - Validação de Detecções com Amostra")
    print("=" * 80)

    # Inicializar processador V2.5.3
    print("\n🔧 Inicializando ProcessadorOficio V2.5.3...")

    # Configurar OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ OPENAI_API_KEY não encontrada no .env")
        sys.exit(1)

    # Configurar banco (não usado neste teste, mas requerido)
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }

    processador = ProcessadorOficio(
        openai_api_key=openai_api_key,
        db_config=db_config
    )

    # Base de dados (caminho absoluto corrigido)
    base_dir = Path("/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/data/consultas")

    # Resultados
    resultados = []
    sucessos = 0
    falhas = 0

    print(f"\n📋 Total de casos de teste: {len(CASOS_TESTE)}")
    print("=" * 80)

    for i, caso in enumerate(CASOS_TESTE, 1):
        cpf = caso["cpf"]
        processo = caso["processo"]
        esperado = caso["esperado"]
        descricao = caso["descricao"]

        print(f"\n{'=' * 80}")
        print(f"🧪 TESTE {i}/{len(CASOS_TESTE)}: {descricao}")
        print(f"{'=' * 80}")
        print(f"   CPF: {cpf}")
        print(f"   Processo: {processo}")

        # Construir caminho do PDF
        cpf_limpo = cpf.replace(".", "").replace("-", "")
        pdf_path = base_dir / cpf_limpo / f"{processo}.pdf"

        if not pdf_path.exists():
            print(f"   ❌ PDF não encontrado: {pdf_path}")
            falhas += 1
            resultados.append({
                "caso": i,
                "cpf": cpf,
                "status": "FALHA",
                "erro": "PDF não encontrado"
            })
            continue

        print(f"   📄 PDF: {pdf_path}")

        # Processar PDF
        try:
            print(f"\n   🔄 Processando com V2.5.3...")
            resultado = processador.processar_arquivo(str(pdf_path), cpf)

            if resultado["status"] != "sucesso":
                print(f"   ❌ Processamento falhou: {resultado.get('erro', 'Erro desconhecido')}")
                falhas += 1
                resultados.append({
                    "caso": i,
                    "cpf": cpf,
                    "status": "FALHA",
                    "erro": resultado.get("erro", "Erro desconhecido")
                })
                continue

            # Extrair dados do resultado
            dados = resultado["dados"]

            # Comparar com esperado
            print(f"\n   📊 COMPARAÇÃO:")
            print(f"   {'='*76}")
            print(f"   {'Campo':<30} {'Esperado':<20} {'Detectado':<20} {'Status':<10}")
            print(f"   {'-'*76}")

            comparacao = {}

            for campo, valor_esperado in esperado.items():
                valor_detectado = dados.get(campo)

                # Comparar valores
                match = valor_detectado == valor_esperado
                status = "✅" if match else "❌"

                print(f"   {campo:<30} {str(valor_esperado):<20} {str(valor_detectado):<20} {status}")

                comparacao[campo] = {
                    "esperado": valor_esperado,
                    "detectado": valor_detectado,
                    "match": match
                }

            # Verificar se todos os campos passaram
            todos_ok = all(c["match"] for c in comparacao.values())

            if todos_ok:
                print(f"\n   ✅ TESTE PASSOU - Todas as detecções corretas!")
                sucessos += 1
                resultados.append({
                    "caso": i,
                    "cpf": cpf,
                    "status": "SUCESSO",
                    "comparacao": comparacao
                })
            else:
                falhas_campos = [campo for campo, c in comparacao.items() if not c["match"]]
                print(f"\n   ❌ TESTE FALHOU - Divergências em: {', '.join(falhas_campos)}")
                falhas += 1
                resultados.append({
                    "caso": i,
                    "cpf": cpf,
                    "status": "FALHA",
                    "comparacao": comparacao,
                    "falhas_campos": falhas_campos
                })

            # Mostrar campos adicionais V2.5.3
            if dados.get("data_obito"):
                print(f"\n   📅 Data de Óbito: {dados['data_obito']}")
            if dados.get("cpf_sucessor"):
                print(f"   👤 CPF Sucessor: {dados['cpf_sucessor']}")

        except Exception as e:
            print(f"   ❌ ERRO no processamento: {str(e)}")
            import traceback
            traceback.print_exc()
            falhas += 1
            resultados.append({
                "caso": i,
                "cpf": cpf,
                "status": "ERRO",
                "erro": str(e)
            })

    # Resumo final
    print(f"\n{'=' * 80}")
    print("📊 RESUMO DOS TESTES V2.5.3")
    print("=" * 80)
    print(f"   Total de testes: {len(CASOS_TESTE)}")
    print(f"   ✅ Sucessos: {sucessos} ({sucessos/len(CASOS_TESTE)*100:.1f}%)")
    print(f"   ❌ Falhas: {falhas} ({falhas/len(CASOS_TESTE)*100:.1f}%)")

    # Salvar relatório JSON
    relatorio_path = Path(__file__).parent / "outputs" / "relatorio_testes_v2.5.3.json"
    relatorio_path.parent.mkdir(exist_ok=True)

    with open(relatorio_path, 'w', encoding='utf-8') as f:
        json.dump({
            "versao": "2.5.3",
            "data_teste": "2025-12-04",
            "total_testes": len(CASOS_TESTE),
            "sucessos": sucessos,
            "falhas": falhas,
            "taxa_sucesso": f"{sucessos/len(CASOS_TESTE)*100:.1f}%",
            "resultados": resultados
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n   📄 Relatório salvo: {relatorio_path}")
    print("=" * 80)

    # Exit code
    sys.exit(0 if falhas == 0 else 1)


if __name__ == "__main__":
    main()
