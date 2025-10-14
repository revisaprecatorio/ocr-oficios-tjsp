#!/usr/bin/env python3
"""
Script de Ingestão de JSONs no PostgreSQL
Lê todos os JSONs processados e insere no banco com validação Pydantic
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

# Adicionar path do schema Pydantic
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "1_parsing_PDF"))
from app.schemas import OficioRequisitorio

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Configurar logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "ingestao.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extrair_cpf_processo(json_path: Path) -> tuple[str, str]:
    """
    Extrai CPF e número do processo do nome do arquivo JSON
    Formato: {cpf}_{numero_processo}.json
    """
    filename = json_path.stem
    parts = filename.split("_", 1)
    
    if len(parts) != 2:
        raise ValueError(f"Nome de arquivo inválido: {filename}")
    
    cpf, numero_processo = parts
    return cpf, numero_processo


def validar_json(data: Dict[str, Any]) -> OficioRequisitorio:
    """Valida JSON com schema Pydantic"""
    try:
        return OficioRequisitorio(**data)
    except Exception as e:
        raise ValueError(f"Validação Pydantic falhou: {e}")


def montar_insert_query() -> str:
    """Monta query INSERT com ON CONFLICT DO UPDATE"""
    return """
        INSERT INTO esaj_detalhe_processos (
            cpf, numero_processo_cnj, processo_origem, requerente_caps,
            numero_ordem, vara, processo_execucao, processo_conhecimento,
            data_ajuizamento, data_transito_julgado, data_base_atualizacao, data_nascimento,
            advogado_nome, advogado_oab, credor_nome, credor_cpf_cnpj, devedor_ente,
            banco, agencia, conta, conta_tipo, tipo_levantamento, dados_bancarios_advogado, cpf_titular_conta,
            valor_principal_liquido, valor_principal_bruto, juros_moratorios, valor_total_requisitado,
            contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
            valor_compensado, contribuicao_social, salario_pericial, assist_tecnico, custas, despesas, multas,
            idoso, doenca_grave, pcd,
            rejeitado, motivo_rejeicao, observacoes, anomalia, descricao_anomalia,
            process_diagnostico, caminho_pdf, timestamp_ingestao
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (cpf, numero_processo_cnj) 
        DO UPDATE SET
            processo_origem = EXCLUDED.processo_origem,
            requerente_caps = EXCLUDED.requerente_caps,
            numero_ordem = EXCLUDED.numero_ordem,
            vara = EXCLUDED.vara,
            processo_execucao = EXCLUDED.processo_execucao,
            processo_conhecimento = EXCLUDED.processo_conhecimento,
            data_ajuizamento = EXCLUDED.data_ajuizamento,
            data_transito_julgado = EXCLUDED.data_transito_julgado,
            data_base_atualizacao = EXCLUDED.data_base_atualizacao,
            data_nascimento = EXCLUDED.data_nascimento,
            advogado_nome = EXCLUDED.advogado_nome,
            advogado_oab = EXCLUDED.advogado_oab,
            credor_nome = EXCLUDED.credor_nome,
            credor_cpf_cnpj = EXCLUDED.credor_cpf_cnpj,
            devedor_ente = EXCLUDED.devedor_ente,
            banco = EXCLUDED.banco,
            agencia = EXCLUDED.agencia,
            conta = EXCLUDED.conta,
            conta_tipo = EXCLUDED.conta_tipo,
            tipo_levantamento = EXCLUDED.tipo_levantamento,
            dados_bancarios_advogado = EXCLUDED.dados_bancarios_advogado,
            cpf_titular_conta = EXCLUDED.cpf_titular_conta,
            valor_principal_liquido = EXCLUDED.valor_principal_liquido,
            valor_principal_bruto = EXCLUDED.valor_principal_bruto,
            juros_moratorios = EXCLUDED.juros_moratorios,
            valor_total_requisitado = EXCLUDED.valor_total_requisitado,
            contrib_previdenciaria_iprem = EXCLUDED.contrib_previdenciaria_iprem,
            contrib_previdenciaria_hspm = EXCLUDED.contrib_previdenciaria_hspm,
            valor_compensado = EXCLUDED.valor_compensado,
            contribuicao_social = EXCLUDED.contribuicao_social,
            salario_pericial = EXCLUDED.salario_pericial,
            assist_tecnico = EXCLUDED.assist_tecnico,
            custas = EXCLUDED.custas,
            despesas = EXCLUDED.despesas,
            multas = EXCLUDED.multas,
            idoso = EXCLUDED.idoso,
            doenca_grave = EXCLUDED.doenca_grave,
            pcd = EXCLUDED.pcd,
            rejeitado = EXCLUDED.rejeitado,
            motivo_rejeicao = EXCLUDED.motivo_rejeicao,
            observacoes = EXCLUDED.observacoes,
            anomalia = EXCLUDED.anomalia,
            descricao_anomalia = EXCLUDED.descricao_anomalia,
            caminho_pdf = EXCLUDED.caminho_pdf,
            timestamp_ingestao = NOW()
    """


def preparar_valores(cpf: str, numero_processo: str, oficio: OficioRequisitorio, caminho_pdf: str) -> tuple:
    """Prepara tupla de valores para INSERT"""
    return (
        cpf, numero_processo, oficio.processo_origem, oficio.requerente_caps,
        oficio.numero_ordem, oficio.vara, oficio.processo_execucao, oficio.processo_conhecimento,
        oficio.data_ajuizamento, oficio.data_transito_julgado, oficio.data_base_atualizacao, oficio.data_nascimento,
        oficio.advogado_nome, oficio.advogado_oab, oficio.credor_nome, oficio.credor_cpf_cnpj, oficio.devedor_ente,
        oficio.banco, oficio.agencia, oficio.conta, oficio.conta_tipo, oficio.tipo_levantamento, 
        oficio.dados_bancarios_advogado, oficio.cpf_titular_conta,
        oficio.valor_principal_liquido, oficio.valor_principal_bruto, oficio.juros_moratorios, oficio.valor_total_requisitado,
        oficio.contrib_previdenciaria_iprem, oficio.contrib_previdenciaria_hspm,
        oficio.valor_compensado, oficio.contribuicao_social, oficio.salario_pericial, oficio.assist_tecnico,
        oficio.custas, oficio.despesas, oficio.multas,
        oficio.idoso, oficio.doenca_grave, oficio.pcd,
        oficio.rejeitado, oficio.motivo_rejeicao, oficio.observacoes, oficio.anomalia, oficio.descricao_anomalia,
        False,  # process_diagnostico (sempre FALSE inicialmente)
        caminho_pdf,
        datetime.now()
    )


def ingerir_jsons(json_dir: Path, db_config: Dict[str, str]):
    """Ingere todos os JSONs no PostgreSQL"""
    
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO INGESTÃO DE JSONS")
    logger.info("=" * 60)
    
    # Buscar todos os JSONs
    json_files = list(json_dir.rglob("*.json"))
    # Filtrar apenas arquivos de processos (não estatísticas)
    json_files = [f for f in json_files if not f.name.startswith("estatisticas")]
    
    logger.info(f"📁 Diretório: {json_dir}")
    logger.info(f"📄 Total de JSONs encontrados: {len(json_files)}")
    
    if not json_files:
        logger.warning("⚠️  Nenhum JSON encontrado!")
        return
    
    # Conectar ao banco
    logger.info(f"🔌 Conectando ao PostgreSQL...")
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        logger.info("✅ Conexão estabelecida")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        return
    
    # Estatísticas
    stats = {
        "sucesso": 0,
        "erros": 0,
        "atualizados": 0,
        "novos": 0
    }
    
    # Query INSERT
    insert_query = montar_insert_query()
    
    # Processar cada JSON
    logger.info(f"\n📥 Processando JSONs...")
    
    for json_file in tqdm(json_files, desc="Ingestão"):
        try:
            # Extrair CPF e processo do nome do arquivo
            cpf, numero_processo = extrair_cpf_processo(json_file)
            
            # Ler JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validar com Pydantic
            oficio = validar_json(data)
            
            # Caminho relativo do PDF
            caminho_pdf = f"../data/consultas/{cpf}/{numero_processo}.pdf"
            
            # Preparar valores
            valores = preparar_valores(cpf, numero_processo, oficio, caminho_pdf)
            
            # Executar INSERT
            cursor.execute(insert_query, valores)
            conn.commit()
            
            stats["sucesso"] += 1
            logger.debug(f"✅ {json_file.name}")
            
        except Exception as e:
            stats["erros"] += 1
            logger.error(f"❌ {json_file.name}: {str(e)[:100]}")
            conn.rollback()
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMO DA INGESTÃO")
    logger.info("=" * 60)
    logger.info(f"Total de JSONs: {len(json_files)}")
    logger.info(f"✅ Sucesso: {stats['sucesso']}")
    logger.info(f"❌ Erros: {stats['erros']}")
    logger.info(f"Taxa de sucesso: {stats['sucesso']/len(json_files)*100:.1f}%")
    logger.info("=" * 60)


def main():
    """Função principal"""
    
    # Configuração do banco
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    # Validar configuração
    if not all(db_config.values()):
        logger.error("❌ Configuração incompleta! Verifique o arquivo .env")
        sys.exit(1)
    
    # Diretório dos JSONs
    json_dir = Path(os.getenv("JSON_DIR", "../1_parsing_PDF/outputs"))
    json_dir = Path(__file__).parent.parent / json_dir
    
    if not json_dir.exists():
        logger.error(f"❌ Diretório não encontrado: {json_dir}")
        sys.exit(1)
    
    # Executar ingestão
    ingerir_jsons(json_dir, db_config)


if __name__ == "__main__":
    main()
