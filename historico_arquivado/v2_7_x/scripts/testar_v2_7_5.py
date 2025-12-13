#!/usr/bin/env python3
"""
Teste V2.7.5 - Reprocessar CPF 08212993876 com fixes de detecção PROCESSAMENTO

V2.7.5 Fixes:
1. Exigir TODOS os 3 campos: PROCESSAMENTO + DEPRE + numero_ordem
2. Validar numero_ordem imediatamente ao detectar PROCESSAMENTO
3. Excluir "APROVAÇÃO DE REQUISITÓRIO"
4. Fallback global melhorado
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
    print("🧪 TESTE V2.7.5 - CPF 08212993876 (processo 0137034-35.2024.8.26.0500)")
    print("=" * 80)
    print()
    print("🎯 Objetivo: Validar que numero_ordem = 50112/2025 é encontrado na página 36")
    print("   (não na página 35 - APROVAÇÃO DE REQUISITÓRIO)")
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

    # Inicializar processador V2.7.5
    processador = ProcessadorOficio(openai_api_key, db_config)

    # PDF problemático
    cpf = "08212993876"
    processo = "0137034-35.2024.8.26.0500"
    pdf_path = Path(__file__).parent.parent / "data" / "consultas" / cpf / f"{processo}.pdf"

    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return 1

    print(f"📁 PDF: {pdf_path}")
    print(f"👤 CPF: {cpf}")
    print(f"📄 Processo: {processo}")
    print()

    # Processar
    print("🔄 Processando com V2.7.5...")
    print()

    try:
        resultado = processador.processar_arquivo(
            str(pdf_path),
            cpf,
            tracker=None  # Sem tracker para simplificar output
        )

        # Validar resultado
        print("=" * 80)
        print("📊 RESULTADO V2.7.5")
        print("=" * 80)
        print()

        if resultado['sucesso']:
            dados = resultado['dados']
            numero_ordem = dados.get('numero_ordem')

            print(f"✅ Status: SUCESSO")
            print(f"👤 Credor: {dados.get('credor_nome')}")
            print(f"📋 Processo Origem: {dados.get('processo_origem')}")
            print(f"🔢 Numero Ordem: {numero_ordem}")
            print(f"💰 Saldo Final: R$ {dados.get('saldo_final'):,.2f}" if dados.get('saldo_final') else "N/A")
            print()

            # Validar numero_ordem
            if numero_ordem == "50112/2025":
                print("=" * 80)
                print("🎉 TESTE V2.7.5: PASSOU!")
                print("=" * 80)
                print(f"✅ numero_ordem correto: {numero_ordem}")
                print("✅ V2.7.5 FIX 1: Regra rigorosa (3 campos) funcionando")
                print("✅ V2.7.5 FIX 2: Validação imediata funcionando")
                print("✅ V2.7.5 FIX 3: APROVAÇÃO DE REQUISITÓRIO rejeitada")
                print()

                # Salvar JSON
                output_dir = Path(__file__).parent / "outputs_v2_7_5"
                output_dir.mkdir(exist_ok=True)
                json_path = output_dir / f"{cpf}_{processo}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
                print(f"💾 JSON salvo: {json_path}")

                return 0
            else:
                print("=" * 80)
                print("❌ TESTE V2.7.5: FALHOU!")
                print("=" * 80)
                print(f"❌ numero_ordem esperado: 50112/2025")
                print(f"❌ numero_ordem obtido: {numero_ordem}")
                return 1
        else:
            print(f"❌ Status: ERRO")
            print(f"❌ Mensagem: {resultado.get('erro', 'Desconhecido')}")
            return 1

    except Exception as e:
        print(f"\n❌ EXCEÇÃO: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
