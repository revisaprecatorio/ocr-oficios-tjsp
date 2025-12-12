#!/usr/bin/env python3
"""
Pipeline V2.7.1 - Teste Completo

Processa todos os 14 PDFs usando ProcessadorOficioV27 e gera relatório comparativo.
"""

import os
import sys
import json
import csv
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

# Adicionar pasta app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador_v2_7 import ProcessadorOficioV27

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent.parent / ".env")

# Configurações
BASE_DIR = "../data/consultas"
OUTPUT_DIR = "./outputs_v2_7_1_teste"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_CONFIG = {}


def encontrar_pdfs(base_dir: str):
    """Encontra todos os PDFs"""
    base_path = Path(base_dir)
    if not base_path.exists():
        base_path = Path(__file__).parent.parent / base_dir

    pdfs = sorted(base_path.glob("*/*.pdf"))
    return pdfs


def processar_todos_pdfs():
    """Processa todos os PDFs com V2.7.1"""

    print("=" * 80)
    print("🚀 PIPELINE V2.7.1 - TESTE COMPLETO")
    print("=" * 80)
    print()

    # Criar diretório de saída
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(exist_ok=True)

    # Encontrar PDFs
    pdfs = encontrar_pdfs(BASE_DIR)
    print(f"📊 Total de PDFs encontrados: {len(pdfs)}")
    print()

    # Inicializar processador V2.7.1
    print("🔧 Inicializando ProcessadorOficioV27...")
    processador = ProcessadorOficioV27(OPENAI_API_KEY, DB_CONFIG)
    print()

    resultados = []
    sucessos = 0
    erros = 0

    # Processar cada PDF
    for pdf_path in tqdm(pdfs, desc="Processando PDFs"):
        # Extrair CPF da pasta
        cpf = pdf_path.parent.name

        try:
            resultado = processador.processar_arquivo(str(pdf_path), cpf)

            if resultado and resultado.get('sucesso'):
                sucessos += 1
                dados = resultado.get('dados', {})

                resultados.append({
                    'pdf': pdf_path.name,
                    'cpf': cpf,
                    'sucesso': True,
                    'tempo': resultado.get('tempo_processamento', 0),
                    'numero_ordem': dados.get('numero_ordem'),
                    'credor_nome': dados.get('credor_nome'),
                    'credor_cpf_cnpj': dados.get('credor_cpf_cnpj'),
                    'requerente_caps': dados.get('requerente_caps'),
                    'valor_total': dados.get('valor_total_requisitado'),
                    'campos_regex': resultado.get('campos_regex', 0),
                    'campos_llm': resultado.get('campos_llm', 0),
                    'campos_totais': resultado.get('campos_totais', 0),
                    'cpf_validado': resultado.get('cpf_validado', False),
                    'anomalia': dados.get('anomalia', False),
                    'descricao_anomalia': dados.get('descricao_anomalia', '')
                })

                # Salvar JSON individual
                json_file = output_path / f"{cpf}_{pdf_path.stem}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False, default=str)

            else:
                erros += 1
                erro_msg = resultado.get('erro', 'Erro desconhecido') if resultado else 'Nenhum resultado'

                resultados.append({
                    'pdf': pdf_path.name,
                    'cpf': cpf,
                    'sucesso': False,
                    'erro': erro_msg,
                    'tempo': resultado.get('tempo_processamento', 0) if resultado else 0,
                })

        except Exception as e:
            erros += 1
            resultados.append({
                'pdf': pdf_path.name,
                'cpf': cpf,
                'sucesso': False,
                'erro': str(e),
                'tempo': 0,
            })

    # Gerar relatório
    print()
    print("=" * 80)
    print("📊 ESTATÍSTICAS FINAIS V2.7.1")
    print("=" * 80)
    print(f"Total processado: {len(pdfs)}")
    print(f"✅ Sucessos: {sucessos} ({100*sucessos/len(pdfs):.1f}%)")
    print(f"❌ Erros: {erros}")
    print()

    # Análise de numero_ordem
    with_numero_ordem = sum(1 for r in resultados if r.get('sucesso') and r.get('numero_ordem'))
    print(f"📋 numero_ordem extraído: {with_numero_ordem}/{sucessos} ({100*with_numero_ordem/sucessos:.1f}%)")

    # Análise de credor_nome
    with_credor_nome = sum(1 for r in resultados if r.get('sucesso') and r.get('credor_nome'))
    print(f"📋 credor_nome extraído: {with_credor_nome}/{sucessos} ({100*with_credor_nome/sucessos:.1f}%)")

    # CPF validado
    cpf_validados = sum(1 for r in resultados if r.get('sucesso') and r.get('cpf_validado'))
    print(f"✅ CPF validado: {cpf_validados}/{sucessos} ({100*cpf_validados/sucessos:.1f}%)")

    # Tempo médio
    tempo_total = sum(r.get('tempo', 0) for r in resultados if r.get('sucesso'))
    tempo_medio = tempo_total / sucessos if sucessos > 0 else 0
    print(f"⏱️  Tempo médio: {tempo_medio:.1f}s/PDF")
    print()

    # Campos extraídos
    if sucessos > 0:
        avg_regex = sum(r.get('campos_regex', 0) for r in resultados if r.get('sucesso')) / sucessos
        avg_llm = sum(r.get('campos_llm', 0) for r in resultados if r.get('sucesso')) / sucessos
        avg_total = sum(r.get('campos_totais', 0) for r in resultados if r.get('sucesso')) / sucessos

        print("📊 Média de campos extraídos:")
        print(f"  REGEX: {avg_regex:.1f}")
        print(f"  LLM: {avg_llm:.1f}")
        print(f"  Total: {avg_total:.1f}")
        print()

    # Salvar CSV resumo
    csv_file = output_path / "resumo_v2_7_1.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'pdf', 'cpf', 'sucesso', 'tempo', 'numero_ordem', 'credor_nome',
            'credor_cpf_cnpj', 'cpf_validado', 'campos_regex', 'campos_llm',
            'campos_totais', 'anomalia', 'erro'
        ])
        writer.writeheader()
        writer.writerows(resultados)

    print(f"💾 CSV salvo em: {csv_file}")

    # Salvar JSON completo
    json_file = output_path / "resultados_v2_7_1.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_pdfs': len(pdfs),
            'sucessos': sucessos,
            'erros': erros,
            'taxa_sucesso': sucessos / len(pdfs) if len(pdfs) > 0 else 0,
            'tempo_total': tempo_total,
            'tempo_medio': tempo_medio,
            'resultados': resultados
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"💾 JSON salvo em: {json_file}")
    print("=" * 80)

    # Mostrar erros
    if erros > 0:
        print()
        print("❌ ERROS ENCONTRADOS:")
        for r in resultados:
            if not r.get('sucesso'):
                print(f"  • {r['pdf']}: {r.get('erro', 'Erro desconhecido')}")
        print()

    # Mostrar PDFs sem numero_ordem
    sem_numero_ordem = [r for r in resultados if r.get('sucesso') and not r.get('numero_ordem')]
    if sem_numero_ordem:
        print()
        print("⚠️  PDFs sem numero_ordem:")
        for r in sem_numero_ordem:
            print(f"  • {r['pdf']} (CPF: {r['cpf']})")
        print()

    return resultados


if __name__ == "__main__":
    processar_todos_pdfs()
