#!/usr/bin/env python3
"""
Script de Ingestão V2.7.2 - Ingest JSONs do outputs_v2_7_1_teste/
Remove requerente_caps (V2.7.2 change)
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from tqdm import tqdm

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extrair_cpf_processo(json_path: Path) -> tuple:
    """Extrai CPF e número do processo do nome do arquivo"""
    filename = json_path.stem
    # Formato: CPF_NumeroProcesso.json
    parts = filename.split("_", 1)

    if len(parts) != 2:
        raise ValueError(f"Nome de arquivo inválido: {json_path.name}")

    return parts[0], parts[1]


def main():
    """Função principal"""

    print("=" * 80)
    print("📥 INGESTÃO V2.7.2 - outputs_v2_7_1_teste/")
    print("=" * 80)

    # Conectar ao banco
    db_config = {
        "host": "72.60.62.124",
        "port": 5432,
        "database": "n8n",
        "user": "admin",
        "password": "BetaAgent2024SecureDB"
    }

    print(f"\n🔌 Conectando ao PostgreSQL...")
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)

    # Buscar JSONs na pasta V2.7.1 (com código V2.7.2)
    json_dir = Path(__file__).parent.parent.parent / "1_parsing_PDF" / "outputs_v2_7_1_teste"

    if not json_dir.exists():
        print(f"❌ Pasta não encontrada: {json_dir}")
        sys.exit(1)

    json_files = sorted(json_dir.glob("*.json"))
    # Filtrar apenas os JSONs individuais (não resumos)
    json_files = [f for f in json_files if not f.stem.startswith("resumo") and not f.stem.startswith("resultados")]

    print(f"\n📁 Pasta: {json_dir}")
    print(f"📊 Total de JSONs: {len(json_files)}")

    # Estatísticas
    stats = {
        "total": len(json_files),
        "sucesso": 0,
        "erros": 0,
    }

    # Query de INSERT V2.7.2 (SEM requerente_caps)
    insert_query = """
        INSERT INTO esaj_detalhe_processos (
            cpf, numero_processo_cnj, processo_origem,
            numero_ordem, vara, processo_execucao, processo_conhecimento,
            data_base_atualizacao, data_nascimento,
            credor_nome, credor_cpf_cnpj, devedor_ente,
            banco, agencia, conta, conta_tipo, tipo_levantamento,
            dados_bancarios_advogado, cpf_titular_conta,
            valor_principal_liquido, valor_principal_bruto, juros_moratorios,
            valor_total_requisitado, saldo_final, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
            valor_compensado, contribuicao_social, salario_pericial,
            assist_tecnico, custas, despesas, multas,
            idoso, doenca_grave, pcd,
            preferencial, habilitacao_herdeiros,
            obito, data_obito, cpf_sucessor,
            rejeitado, motivo_rejeicao, observacoes, anomalia, descricao_anomalia,
            process_calculo, caminho_pdf, timestamp_ingestao
        ) VALUES (
            %(cpf)s, %(numero_processo_cnj)s, %(processo_origem)s,
            %(numero_ordem)s, %(vara)s, %(processo_execucao)s, %(processo_conhecimento)s,
            %(data_base_atualizacao)s, %(data_nascimento)s,
            %(credor_nome)s, %(credor_cpf_cnpj)s, %(devedor_ente)s,
            %(banco)s, %(agencia)s, %(conta)s, %(conta_tipo)s, %(tipo_levantamento)s,
            %(dados_bancarios_advogado)s, %(cpf_titular_conta)s,
            %(valor_principal_liquido)s, %(valor_principal_bruto)s, %(juros_moratorios)s,
            %(valor_total_requisitado)s, %(saldo_final)s, %(contrib_previdenciaria_iprem)s, %(contrib_previdenciaria_hspm)s,
            %(valor_compensado)s, %(contribuicao_social)s, %(salario_pericial)s,
            %(assist_tecnico)s, %(custas)s, %(despesas)s, %(multas)s,
            %(idoso)s, %(doenca_grave)s, %(pcd)s,
            %(preferencial)s, %(habilitacao_herdeiros)s,
            %(obito)s, %(data_obito)s, %(cpf_sucessor)s,
            %(rejeitado)s, %(motivo_rejeicao)s, %(observacoes)s, %(anomalia)s, %(descricao_anomalia)s,
            %(process_calculo)s, %(caminho_pdf)s, %(timestamp_ingestao)s
        )
        ON CONFLICT (cpf, numero_processo_cnj)
        DO UPDATE SET
            processo_origem = EXCLUDED.processo_origem,
            numero_ordem = EXCLUDED.numero_ordem,
            vara = EXCLUDED.vara,
            data_nascimento = EXCLUDED.data_nascimento,
            saldo_final = EXCLUDED.saldo_final,
            preferencial = EXCLUDED.preferencial,
            habilitacao_herdeiros = EXCLUDED.habilitacao_herdeiros,
            obito = EXCLUDED.obito,
            data_obito = EXCLUDED.data_obito,
            cpf_sucessor = EXCLUDED.cpf_sucessor,
            timestamp_ingestao = EXCLUDED.timestamp_ingestao;
    """

    # Processar JSONs
    print(f"\n📋 Processando JSONs V2.7.2...")
    print("="*80)

    for json_file in tqdm(json_files, desc="Ingerindo"):
        try:
            # Extrair CPF e processo
            cpf, numero_processo = extrair_cpf_processo(json_file)

            print(f"\n📄 {json_file.name}")
            print(f"   CPF: {cpf} | Processo: {numero_processo}")

            # Ler JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Log dos campos principais V2.7.2
            print(f"   Credor: {data.get('credor_nome', 'N/A')[:40]}")
            print(f"   Numero Ordem: {data.get('numero_ordem', 'N/A')}")
            print(f"   Saldo Final: {data.get('saldo_final', 0)}")

            # Preparar valores V2.7.2 (SEM requerente_caps)
            # Extrair apenas código do banco (primeiros 3 dígitos)
            banco_raw = data.get('banco')
            banco = None
            if banco_raw:
                if ' - ' in banco_raw or 'Agência' in banco_raw:
                    banco = banco_raw.split()[0].strip()
                else:
                    banco = banco_raw[:10]

            valores = {
                'cpf': cpf,
                'numero_processo_cnj': numero_processo,
                'processo_origem': data.get('processo_origem'),
                # V2.7.2: REMOVED requerente_caps
                'numero_ordem': data.get('numero_ordem'),
                'vara': data.get('vara'),
                'processo_execucao': data.get('processo_execucao'),
                'processo_conhecimento': data.get('processo_conhecimento'),
                'data_base_atualizacao': data.get('data_base_atualizacao'),
                'data_nascimento': data.get('data_nascimento'),
                'credor_nome': data.get('credor_nome'),
                'credor_cpf_cnpj': data.get('credor_cpf_cnpj'),
                'devedor_ente': data.get('devedor_ente'),
                'banco': banco,
                'agencia': data.get('agencia'),
                'conta': data.get('conta'),
                'conta_tipo': data.get('conta_tipo'),
                'tipo_levantamento': data.get('tipo_levantamento'),
                'dados_bancarios_advogado': data.get('dados_bancarios_advogado', False),
                'cpf_titular_conta': data.get('cpf_titular_conta'),
                'valor_principal_liquido': data.get('valor_principal_liquido'),
                'valor_principal_bruto': data.get('valor_principal_bruto'),
                'juros_moratorios': data.get('juros_moratorios'),
                'valor_total_requisitado': data.get('valor_total_requisitado'),
                'saldo_final': data.get('saldo_final'),
                'contrib_previdenciaria_iprem': data.get('contrib_previdenciaria_iprem'),
                'contrib_previdenciaria_hspm': data.get('contrib_previdenciaria_hspm'),
                'valor_compensado': data.get('valor_compensado'),
                'contribuicao_social': data.get('contribuicao_social'),
                'salario_pericial': data.get('salario_pericial'),
                'assist_tecnico': data.get('assist_tecnico'),
                'custas': data.get('custas'),
                'despesas': data.get('despesas'),
                'multas': data.get('multas'),
                'idoso': data.get('idoso', False),
                'doenca_grave': data.get('doenca_grave', False),
                'pcd': data.get('pcd', False),
                'preferencial': data.get('preferencial', False),
                'habilitacao_herdeiros': data.get('habilitacao_herdeiros', False),
                'obito': data.get('obito', False),
                'data_obito': data.get('data_obito'),
                'cpf_sucessor': data.get('cpf_sucessor'),
                'rejeitado': data.get('rejeitado', False),
                'motivo_rejeicao': data.get('motivo_rejeicao'),
                'observacoes': data.get('observacoes'),
                'anomalia': data.get('anomalia', False),
                'descricao_anomalia': data.get('descricao_anomalia'),
                'process_calculo': False,
                'caminho_pdf': f"../data/consultas/{cpf}/{numero_processo}.pdf",
                'timestamp_ingestao': datetime.now()
            }

            # Executar INSERT
            cursor.execute(insert_query, valores)
            conn.commit()

            stats["sucesso"] += 1
            print(f"   ✅ Inserido!")

        except Exception as e:
            stats["erros"] += 1
            print(f"   ❌ ERRO: {str(e)[:100]}")
            logger.error(f"❌ {json_file.name}: {str(e)}")
            conn.rollback()

    # Fechar conexão
    cursor.close()
    conn.close()

    # Resumo
    print(f"\n" + "=" * 80)
    print(f"📊 RESUMO DA INGESTÃO V2.7.2")
    print("=" * 80)
    print(f"   Total de JSONs: {stats['total']}")
    print(f"   ✅ Sucesso: {stats['sucesso']}")
    print(f"   ❌ Erros: {stats['erros']}")
    if stats['total'] > 0:
        print(f"   Taxa de sucesso: {stats['sucesso']/stats['total']*100:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
