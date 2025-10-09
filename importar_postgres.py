#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 2: Importador PostgreSQL - Ofícios Requisitórios TJSP
Lê JSONs gerados e insere/atualiza no banco PostgreSQL.

Compatível com Windows Server 2022 e Linux/macOS.

Uso:
    python importar_postgres.py --input ./output/json

Opções:
    --dry-run: Simula importação sem alterar banco
    --force: Força reimportação de todos os JSONs

Exemplo:
    # Importar todos os JSONs
    python importar_postgres.py --input ./output/json

    # Testar sem alterar banco
    python importar_postgres.py --input ./output/json --dry-run
"""

import os
import sys
import json
import logging
import argparse
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


def configurar_logging(log_dir: Path = Path('./logs')) -> logging.Logger:
    """Configura logging para arquivo e console."""
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"importacao_{timestamp}.log"

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def conectar_postgres(db_config: Dict[str, str]):
    """Conecta ao PostgreSQL com configurações fornecidas."""
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        logging.info(f"✓ Conectado ao PostgreSQL: {db_config['host']}:{db_config['port']}/{db_config['database']}")
        return conn
    except Exception as e:
        logging.error(f"Erro ao conectar ao PostgreSQL: {e}")
        raise


def inserir_oficio(conn, oficio_json: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Insere ou atualiza ofício no PostgreSQL.
    Usa UPSERT (ON CONFLICT DO UPDATE).
    """
    try:
        # Extrair dados do JSON
        metadata = oficio_json.get('metadata', {})
        oficio = oficio_json.get('oficio', {})

        if not metadata:
            logging.warning("JSON sem metadata, pulando")
            return False

        cpf = metadata.get('cpf')
        numero_processo = metadata.get('numero_processo')

        if not cpf or not numero_processo:
            logging.warning(f"JSON incompleto: cpf={cpf}, processo={numero_processo}")
            return False

        # SQL de upsert
        sql = """
        INSERT INTO lista_processos (
            cpf, numero_processo, vara, processo_execucao, processo_conhecimento,
            data_ajuizamento, data_transito_julgado, requerente_caps, advogado_nome,
            advogado_oab, valor_principal_liquido, valor_principal_bruto,
            juros_moratorios, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
            valor_total_requisitado, data_base_atualizacao, idoso, doenca_grave,
            pcd, texto_completo_oficio, timestamp_processamento, data_envio, processado,
            banco, agencia, conta, conta_tipo
        ) VALUES (
            %(cpf)s, %(numero_processo)s, %(vara)s, %(processo_execucao)s, %(processo_conhecimento)s,
            %(data_ajuizamento)s, %(data_transito_julgado)s, %(requerente_caps)s, %(advogado_nome)s,
            %(advogado_oab)s, %(valor_principal_liquido)s, %(valor_principal_bruto)s,
            %(juros_moratorios)s, %(contrib_previdenciaria_iprem)s, %(contrib_previdenciaria_hspm)s,
            %(valor_total_requisitado)s, %(data_base_atualizacao)s, %(idoso)s, %(doenca_grave)s,
            %(pcd)s, %(texto_completo_oficio)s, %(timestamp_processamento)s, %(data_envio)s, %(processado)s,
            %(banco)s, %(agencia)s, %(conta)s, %(conta_tipo)s
        )
        ON CONFLICT (cpf, numero_processo) DO UPDATE SET
            vara = EXCLUDED.vara,
            processo_execucao = EXCLUDED.processo_execucao,
            processo_conhecimento = EXCLUDED.processo_conhecimento,
            data_ajuizamento = EXCLUDED.data_ajuizamento,
            data_transito_julgado = EXCLUDED.data_transito_julgado,
            requerente_caps = EXCLUDED.requerente_caps,
            advogado_nome = EXCLUDED.advogado_nome,
            advogado_oab = EXCLUDED.advogado_oab,
            valor_principal_liquido = EXCLUDED.valor_principal_liquido,
            valor_principal_bruto = EXCLUDED.valor_principal_bruto,
            juros_moratorios = EXCLUDED.juros_moratorios,
            contrib_previdenciaria_iprem = EXCLUDED.contrib_previdenciaria_iprem,
            contrib_previdenciaria_hspm = EXCLUDED.contrib_previdenciaria_hspm,
            valor_total_requisitado = EXCLUDED.valor_total_requisitado,
            data_base_atualizacao = EXCLUDED.data_base_atualizacao,
            idoso = EXCLUDED.idoso,
            doenca_grave = EXCLUDED.doenca_grave,
            pcd = EXCLUDED.pcd,
            texto_completo_oficio = EXCLUDED.texto_completo_oficio,
            timestamp_processamento = EXCLUDED.timestamp_processamento,
            data_envio = EXCLUDED.data_envio,
            processado = EXCLUDED.processado,
            banco = EXCLUDED.banco,
            agencia = EXCLUDED.agencia,
            conta = EXCLUDED.conta,
            conta_tipo = EXCLUDED.conta_tipo
        """

        # Preparar dados
        dados = {
            # Metadata
            'cpf': cpf,
            'numero_processo': numero_processo,
            'texto_completo_oficio': metadata.get('texto_completo_oficio', ''),
            'timestamp_processamento': metadata.get('timestamp_processamento'),
            'processado': metadata.get('processado', False),
            'data_envio': oficio_json.get('data_envio'),

            # Dados do ofício
            'vara': oficio.get('vara'),
            'processo_execucao': oficio.get('processo_execucao'),
            'processo_conhecimento': oficio.get('processo_conhecimento'),
            'data_ajuizamento': oficio.get('data_ajuizamento'),
            'data_transito_julgado': oficio.get('data_transito_julgado'),
            'requerente_caps': oficio.get('requerente_caps'),
            'advogado_nome': oficio.get('advogado_nome'),
            'advogado_oab': oficio.get('advogado_oab'),
            'valor_principal_liquido': oficio.get('valor_principal_liquido'),
            'valor_principal_bruto': oficio.get('valor_principal_bruto'),
            'juros_moratorios': oficio.get('juros_moratorios'),
            'contrib_previdenciaria_iprem': oficio.get('contrib_previdenciaria_iprem'),
            'contrib_previdenciaria_hspm': oficio.get('contrib_previdenciaria_hspm'),
            'valor_total_requisitado': oficio.get('valor_total_requisitado'),
            'data_base_atualizacao': oficio.get('data_base_atualizacao'),
            'idoso': oficio.get('idoso'),
            'doenca_grave': oficio.get('doenca_grave'),
            'pcd': oficio.get('pcd'),

            # Dados bancários (ANEXO II)
            'banco': oficio.get('banco'),
            'agencia': oficio.get('agencia'),
            'conta': oficio.get('conta'),
            'conta_tipo': oficio.get('conta_tipo')
        }

        if dry_run:
            logging.info(f"[DRY-RUN] Inserir: CPF={cpf}, Processo={numero_processo}")
            return True

        # Executar upsert
        cursor = conn.cursor()
        cursor.execute(sql, dados)
        conn.commit()
        cursor.close()

        logging.info(f"✓ Inserido/Atualizado: CPF={cpf}, Processo={numero_processo}")
        return True

    except Exception as e:
        logging.error(f"Erro ao inserir ofício: {e}")
        conn.rollback()
        return False


def importar_jsons(
    json_dir: Path,
    db_config: Dict[str, str],
    dry_run: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """
    Importa todos os JSONs do diretório para o PostgreSQL.

    Args:
        json_dir: Diretório com JSONs (estrutura: {cpf}/{processo}.json)
        db_config: Configurações do PostgreSQL
        dry_run: Se True, simula sem alterar banco
        force: Se True, reimporta todos (ignora verificação de duplicatas)

    Returns:
        Estatísticas da importação
    """
    stats = {
        "total_jsons": 0,
        "importados_sucesso": 0,
        "importados_erro": 0,
        "pulados": 0,
        "inicio": datetime.now(),
        "fim": None,
        "tempo_total": None
    }

    try:
        # Conectar ao PostgreSQL (se não for dry-run)
        conn = None
        if not dry_run:
            conn = conectar_postgres(db_config)

        # Buscar todos os JSONs
        json_files = list(json_dir.rglob("*.json"))
        # Excluir estatisticas.json
        json_files = [f for f in json_files if f.name != "estatisticas.json"]
        stats["total_jsons"] = len(json_files)

        logging.info(f"Encontrados {len(json_files)} JSONs para importar")

        # Processar cada JSON
        for idx, json_file in enumerate(json_files, 1):
            try:
                logging.debug(f"[{idx}/{len(json_files)}] Lendo: {json_file.name}")

                # Ler JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    oficio_json = json.load(f)

                # Inserir no banco
                if dry_run:
                    sucesso = inserir_oficio(None, oficio_json, dry_run=True)
                else:
                    sucesso = inserir_oficio(conn, oficio_json)

                if sucesso:
                    stats["importados_sucesso"] += 1
                else:
                    stats["importados_erro"] += 1

            except Exception as e:
                logging.error(f"Erro ao processar {json_file.name}: {e}")
                stats["importados_erro"] += 1

        # Fechar conexão
        if conn:
            conn.close()
            logging.info("✓ Conexão PostgreSQL fechada")

        # Finalizar estatísticas
        stats["fim"] = datetime.now()
        stats["tempo_total"] = str(stats["fim"] - stats["inicio"])

        logging.info("=" * 60)
        logging.info("IMPORTAÇÃO CONCLUÍDA")
        logging.info("=" * 60)
        logging.info(f"Total de JSONs: {stats['total_jsons']}")
        logging.info(f"Importados com sucesso: {stats['importados_sucesso']}")
        logging.info(f"Erros: {stats['importados_erro']}")
        logging.info(f"Tempo total: {stats['tempo_total']}")

        return stats

    except Exception as e:
        logging.error(f"Erro na importação: {e}")
        raise


def main():
    """Função principal com argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description='Importador PostgreSQL - Ofícios Requisitórios TJSP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Importar todos os JSONs
  python importar_postgres.py --input ./output/json

  # Testar sem alterar banco
  python importar_postgres.py --input ./output/json --dry-run

  # Forçar reimportação
  python importar_postgres.py --input ./output/json --force
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        default=Path('./output/json'),
        help='Diretório com JSONs (padrão: ./output/json)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula importação sem alterar banco'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Força reimportação de todos os JSONs'
    )

    parser.add_argument(
        '--env',
        type=Path,
        default=Path('.env'),
        help='Arquivo .env com configurações (padrão: .env)'
    )

    args = parser.parse_args()

    # Carregar variáveis de ambiente
    if args.env.exists():
        load_dotenv(args.env)
        print(f"✓ Configurações carregadas de: {args.env}")
    else:
        print(f"⚠️  Arquivo {args.env} não encontrado, usando variáveis de ambiente")

    # Validar PostgreSQL config
    db_config = {
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }

    if not all([db_config['host'], db_config['database'], db_config['user'], db_config['password']]):
        print("❌ ERRO: Configurações do PostgreSQL incompletas!")
        print("   Configure POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD")
        sys.exit(1)

    # Validar diretório de entrada
    if not args.input.exists():
        print(f"❌ ERRO: Diretório de entrada não encontrado: {args.input}")
        sys.exit(1)

    # Configurar logging
    logger = configurar_logging()

    # Exibir configurações
    print("\n" + "=" * 60)
    print("IMPORTADOR PostgreSQL - Ofícios Requisitórios TJSP")
    print("=" * 60)
    print(f"Entrada:   {args.input.resolve()}")
    print(f"Banco:     {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"Dry-run:   {args.dry_run}")
    print(f"Force:     {args.force}")
    print("=" * 60 + "\n")

    # Executar importação
    try:
        stats = importar_jsons(
            json_dir=args.input,
            db_config=db_config,
            dry_run=args.dry_run,
            force=args.force
        )

        if args.dry_run:
            print("\n✓ Simulação concluída (nenhum dado foi alterado)")
        else:
            print("\n✓ Importação concluída com sucesso!")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        logging.exception("Erro fatal na importação")
        sys.exit(1)


if __name__ == "__main__":
    main()
