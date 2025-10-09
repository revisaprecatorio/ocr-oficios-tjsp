#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 1: Exportador de JSONs - Ofícios Requisitórios TJSP
Processa PDFs e gera JSONs estruturados (sem inserir no banco).

Compatível com Windows Server 2022 e Linux/macOS.

Uso:
    python exportar_json.py --input ./data/consultas --output ./output/json

Estrutura de saída:
    output/
    ├── json/
    │   ├── {cpf}/
    │   │   └── {numero_processo}.json
    │   └── ...
    └── logs/
        └── exportacao_YYYYMMDD_HHMMSS.log
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador import ProcessadorOficio
from app.schemas import OficioCompleto


def configurar_logging(output_dir: Path) -> logging.Logger:
    """
    Configura logging para arquivo e console.
    Compatível com Windows Server.
    """
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"exportacao_{timestamp}.log"

    # Configurar formatação
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configurar logger raiz
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def salvar_json(oficio: OficioCompleto, output_dir: Path) -> bool:
    """
    Salva ofício completo em JSON.
    Estrutura: output/json/{cpf}/{processo}.json
    """
    try:
        # Criar diretório do CPF
        cpf_dir = output_dir / "json" / oficio.metadata.cpf
        cpf_dir.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo JSON
        json_file = cpf_dir / f"{oficio.metadata.numero_processo}.json"

        # Serializar com suporte a datetime e Decimal
        json_data = oficio.model_dump(mode='json')

        # Salvar JSON com indentação
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logging.info(f"JSON salvo: {json_file}")
        return True

    except Exception as e:
        logging.error(f"Erro ao salvar JSON: {e}")
        return False


def processar_diretorio(
    input_dir: Path,
    output_dir: Path,
    openai_api_key: str,
    limite: Optional[int] = None
) -> Dict[str, Any]:
    """
    Processa todos os PDFs do diretório de entrada.

    Args:
        input_dir: Diretório com estrutura {cpf}/{processo}.pdf
        output_dir: Diretório para salvar JSONs
        openai_api_key: Chave da API OpenAI
        limite: Número máximo de PDFs a processar (None = todos)

    Returns:
        Dicionário com estatísticas do processamento
    """
    stats = {
        "total_pdfs": 0,
        "processados_sucesso": 0,
        "processados_erro": 0,
        "com_oficio": 0,
        "com_anexo_ii": 0,
        "json_salvos": 0,
        "inicio": datetime.now(),
        "fim": None,
        "tempo_total": None
    }

    try:
        # Inicializar processador (sem DB config)
        # Passa config vazio pois não vai usar banco nesta etapa
        processador = ProcessadorOficio(
            openai_api_key=openai_api_key,
            db_config={}
        )

        # Buscar todos os PDFs
        pdf_files = list(input_dir.rglob("*.pdf"))
        stats["total_pdfs"] = len(pdf_files)

        # Aplicar limite se especificado
        if limite:
            pdf_files = pdf_files[:limite]
            logging.info(f"Limitando processamento a {limite} PDFs")

        logging.info(f"Encontrados {len(pdf_files)} PDFs para processar")

        # Processar cada PDF
        for idx, pdf_file in enumerate(pdf_files, 1):
            try:
                logging.info(f"[{idx}/{len(pdf_files)}] Processando: {pdf_file.name}")

                # Processar arquivo (sem salvar no banco)
                resultado = processador.processar_arquivo(str(pdf_file))

                if resultado:
                    stats["processados_sucesso"] += 1

                    if resultado.oficio:
                        stats["com_oficio"] += 1

                        # Verificar se tem dados bancários (ANEXO II)
                        if resultado.oficio.banco or resultado.oficio.conta:
                            stats["com_anexo_ii"] += 1

                    # Salvar JSON
                    if salvar_json(resultado, output_dir):
                        stats["json_salvos"] += 1
                else:
                    stats["processados_erro"] += 1

            except Exception as e:
                logging.error(f"Erro ao processar {pdf_file.name}: {e}")
                stats["processados_erro"] += 1

        # Finalizar estatísticas
        stats["fim"] = datetime.now()
        stats["tempo_total"] = str(stats["fim"] - stats["inicio"])

        logging.info("=" * 60)
        logging.info("PROCESSAMENTO CONCLUÍDO")
        logging.info("=" * 60)
        logging.info(f"Total de PDFs: {stats['total_pdfs']}")
        logging.info(f"Processados com sucesso: {stats['processados_sucesso']}")
        logging.info(f"Erros: {stats['processados_erro']}")
        logging.info(f"Com ofício requisitório: {stats['com_oficio']}")
        logging.info(f"Com ANEXO II: {stats['com_anexo_ii']}")
        logging.info(f"JSONs salvos: {stats['json_salvos']}")
        logging.info(f"Tempo total: {stats['tempo_total']}")

        # Salvar estatísticas em JSON
        stats_file = output_dir / "estatisticas.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            # Converter datetime para string
            stats_export = stats.copy()
            stats_export["inicio"] = stats["inicio"].isoformat()
            stats_export["fim"] = stats["fim"].isoformat()
            json.dump(stats_export, f, ensure_ascii=False, indent=2)

        logging.info(f"Estatísticas salvas em: {stats_file}")

        return stats

    except Exception as e:
        logging.error(f"Erro no processamento do diretório: {e}")
        raise


def main():
    """Função principal com argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description='Exportador de JSONs - Ofícios Requisitórios TJSP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Processar todos os PDFs
  python exportar_json.py --input ./data/consultas --output ./output

  # Processar apenas 5 PDFs (teste)
  python exportar_json.py --input ./data/consultas --output ./output --limite 5

  # Com .env customizado
  python exportar_json.py --input ./data/consultas --output ./output --env .env.local
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        default=Path('./data/consultas'),
        help='Diretório de entrada com PDFs (padrão: ./data/consultas)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('./output'),
        help='Diretório de saída para JSONs (padrão: ./output)'
    )

    parser.add_argument(
        '--limite',
        type=int,
        default=None,
        help='Número máximo de PDFs a processar (padrão: todos)'
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

    # Validar OpenAI API Key
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ ERRO: OPENAI_API_KEY não configurada!")
        print("   Configure no arquivo .env ou como variável de ambiente")
        sys.exit(1)

    # Validar diretório de entrada
    if not args.input.exists():
        print(f"❌ ERRO: Diretório de entrada não encontrado: {args.input}")
        sys.exit(1)

    # Criar diretório de saída
    args.output.mkdir(parents=True, exist_ok=True)

    # Configurar logging
    logger = configurar_logging(args.output)

    # Exibir configurações
    print("\n" + "=" * 60)
    print("EXPORTADOR DE JSONs - Ofícios Requisitórios TJSP")
    print("=" * 60)
    print(f"Entrada:  {args.input.resolve()}")
    print(f"Saída:    {args.output.resolve()}")
    print(f"Limite:   {args.limite or 'Sem limite'}")
    print(f"Log:      {args.output / 'logs'}")
    print("=" * 60 + "\n")

    # Executar processamento
    try:
        stats = processar_diretorio(
            input_dir=args.input,
            output_dir=args.output,
            openai_api_key=openai_api_key,
            limite=args.limite
        )

        print("\n✓ Processamento concluído com sucesso!")
        print(f"  JSONs salvos em: {args.output / 'json'}")
        print(f"  Logs salvos em:  {args.output / 'logs'}")

        sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        logging.exception("Erro fatal no processamento")
        sys.exit(1)


if __name__ == "__main__":
    main()
