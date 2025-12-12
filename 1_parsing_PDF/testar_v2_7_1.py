#!/usr/bin/env python3
"""
Teste V2.7.1 - Validação de Correções Críticas

Testa os 2 bugs corrigidos em V2.7.1:
1. Bug #1: numero_ordem sempre null → DEVE extrair corretamente
2. Bug #2: Contaminação de dados → DEVE prevenir dados errados

PDFs de teste:
- CPF 03736870876: Deve ter numero_ordem = "50155/2025"
- CPF 07692595887: Deve ter dados DIFERENTES do anterior (sem contaminação)
- CPF 08212993876: Deve ter numero_ordem = "50112/2025"
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Adicionar pasta app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador_v2_7 import ProcessadorOficioV27

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent.parent / ".env")

# Configurações
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_CONFIG = {}  # Não vamos salvar no DB neste teste

# PDFs de teste com valores esperados
TESTES = [
    {
        "cpf": "03736870876",
        "pdf": "../data/consultas/03736870876/0137444-93.2024.8.26.0500.pdf",
        "numero_ordem_esperado": "50155/2025",
        "requerente_esperado": None  # Vamos descobrir
    },
    {
        "cpf": "07692595887",
        "pdf": "../data/consultas/07692595887/0137451-85.2024.8.26.0500.pdf",
        "numero_ordem_esperado": "50158/2025",
        "requerente_esperado": "CICERO CONSTANTINO TAVARES"  # NÃO deve ser LUIZ GONZAGA PRADO!
    },
    {
        "cpf": "08212993876",
        "pdf": "../data/consultas/08212993876/0137034-35.2024.8.26.0500.pdf",
        "numero_ordem_esperado": "50112/2025",
        "requerente_esperado": None  # Vamos descobrir
    }
]


def testar_v2_7_1():
    """Executa testes de V2.7.1"""

    print("=" * 80)
    print("🧪 TESTE V2.7.1 - VALIDAÇÃO DE CORREÇÕES CRÍTICAS")
    print("=" * 80)
    print()

    # Inicializar processador V2.7.1
    print("🚀 Inicializando ProcessadorOficioV27...")
    processador = ProcessadorOficioV27(OPENAI_API_KEY, DB_CONFIG)
    print()

    resultados = []

    for i, teste in enumerate(TESTES, 1):
        print("=" * 80)
        print(f"📋 TESTE {i}/3: CPF {teste['cpf']}")
        print("=" * 80)
        print(f"📄 PDF: {teste['pdf']}")
        print(f"✅ numero_ordem esperado: {teste['numero_ordem_esperado']}")
        if teste['requerente_esperado']:
            print(f"✅ requerente esperado: {teste['requerente_esperado']}")
        print()

        # Verificar se PDF existe
        pdf_path = Path(teste['pdf'])
        if not pdf_path.exists():
            # Tentar caminho relativo ao script
            pdf_path = Path(__file__).parent / teste['pdf']

        if not pdf_path.exists():
            print(f"❌ PDF não encontrado: {teste['pdf']}")
            resultados.append({
                **teste,
                "sucesso": False,
                "erro": "PDF não encontrado"
            })
            continue

        # Processar PDF
        try:
            resultado = processador.processar_arquivo(str(pdf_path), teste['cpf'])

            if resultado and resultado.get('sucesso'):
                dados = resultado.get('dados', {})

                # Validar numero_ordem
                numero_ordem = dados.get('numero_ordem')
                print(f"📊 numero_ordem extraído: {numero_ordem}")

                if numero_ordem == teste['numero_ordem_esperado']:
                    print(f"✅ Bug #1 CORRIGIDO: numero_ordem correto!")
                else:
                    print(f"❌ Bug #1 PERSISTE: esperado {teste['numero_ordem_esperado']}, obteve {numero_ordem}")

                # Validar requerente (anti-contaminação)
                requerente = dados.get('requerente_caps')
                print(f"📊 requerente extraído: {requerente}")

                if teste['requerente_esperado']:
                    if requerente == teste['requerente_esperado']:
                        print(f"✅ Bug #2 CORRIGIDO: requerente correto (sem contaminação)!")
                    else:
                        print(f"❌ Bug #2 PERSISTE: esperado {teste['requerente_esperado']}, obteve {requerente}")

                # Validar CPF
                cpf_extraido = dados.get('credor_cpf_cnpj', '').replace('.', '').replace('-', '')
                if cpf_extraido == teste['cpf']:
                    print(f"✅ CPF validado: {dados.get('credor_cpf_cnpj')}")
                else:
                    print(f"❌ CPF inconsistente: extraído {dados.get('credor_cpf_cnpj')}, esperado {teste['cpf']}")

                print()
                print(f"⏱️  Tempo: {resultado.get('tempo_processamento', 0):.1f}s")
                print(f"📊 Campos REGEX: {resultado.get('campos_regex', 0)}")
                print(f"📊 Campos LLM: {resultado.get('campos_llm', 0)}")
                print(f"📊 Campos totais: {resultado.get('campos_totais', 0)}")

                resultados.append({
                    **teste,
                    "sucesso": True,
                    "numero_ordem": numero_ordem,
                    "requerente": requerente,
                    "cpf_validado": cpf_extraido == teste['cpf'],
                    "tempo": resultado.get('tempo_processamento', 0)
                })

            else:
                erro = resultado.get('erro', 'Processamento falhou') if resultado else 'Nenhum resultado retornado'
                print(f"❌ Processamento falhou: {erro}")

                resultados.append({
                    **teste,
                    "sucesso": False,
                    "erro": erro
                })

        except Exception as e:
            print(f"❌ Erro durante processamento: {e}")
            import traceback
            traceback.print_exc()

            resultados.append({
                **teste,
                "sucesso": False,
                "erro": str(e)
            })

        print()

    # Resumo final
    print("=" * 80)
    print("📊 RESUMO DOS TESTES V2.7.1")
    print("=" * 80)
    print()

    sucessos = sum(1 for r in resultados if r.get('sucesso'))
    print(f"✅ Sucessos: {sucessos}/3")
    print(f"❌ Falhas: {3 - sucessos}/3")
    print()

    # Validação de bugs
    print("🔍 VALIDAÇÃO DE BUGS CRÍTICOS:")
    print()

    # Bug #1: numero_ordem
    bug1_corrigido = all(
        r.get('numero_ordem') == r.get('numero_ordem_esperado')
        for r in resultados if r.get('sucesso')
    )

    if bug1_corrigido:
        print("✅ Bug #1 (numero_ordem null) → CORRIGIDO!")
    else:
        print("❌ Bug #1 (numero_ordem null) → PERSISTE")

    # Bug #2: Contaminação (verificar CPF 07692595887)
    teste_contaminacao = next((r for r in resultados if r['cpf'] == '07692595887'), None)

    if teste_contaminacao and teste_contaminacao.get('sucesso'):
        requerente = teste_contaminacao.get('requerente')
        if requerente and requerente != 'LUIZ GONZAGA PRADO':
            print("✅ Bug #2 (contaminação de dados) → CORRIGIDO!")
        else:
            print(f"❌ Bug #2 (contaminação de dados) → PERSISTE (requerente = {requerente})")
    else:
        print("⚠️  Bug #2 (contaminação de dados) → NÃO TESTADO (processamento falhou)")

    print()
    print("=" * 80)

    # Salvar resultados
    output_file = Path(__file__).parent / "teste_v2_7_1_resultados.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 Resultados salvos em: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    testar_v2_7_1()
