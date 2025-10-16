#!/usr/bin/env python3
"""
Script de Ingestão de TODOS os JSONs no PostgreSQL
Lê JSONs da pasta json/ organizada e insere no banco
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
env_path = Path(__file__).parent.parent / ".env"
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
    # Remover sufixos como " (1)"
    filename = filename.split(" (")[0]
    parts = filename.split("_", 1)
    
    if len(parts) != 2:
        raise ValueError(f"Nome de arquivo inválido: {json_path.name}")
    
    return parts[0], parts[1]


def main():
    """Função principal"""
    
    print("=" * 60)
    print("📥 INGESTÃO DE TODOS OS JSONs")
    print("=" * 60)
    
    # Conectar ao banco
    db_config = {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD")
    }
    
    print(f"\n🔌 Conectando ao PostgreSQL...")
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("   ✅ Conectado!")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        sys.exit(1)
    
    # Buscar JSONs
    json_dir = Path(__file__).parent.parent.parent / "1_parsing_PDF" / "outputs" / "json"
    
    if not json_dir.exists():
        print(f"❌ Pasta não encontrada: {json_dir}")
        sys.exit(1)
    
    json_files = sorted(json_dir.glob("*.json"))
    print(f"\n📁 Pasta: {json_dir}")
    print(f"📊 Total de JSONs: {len(json_files)}")
    
    # Estatísticas
    stats = {
        "total": len(json_files),
        "sucesso": 0,
        "erros": 0,
        "duplicados": 0
    }
    
    # Query de INSERT com UPSERT
    insert_query = """
        INSERT INTO esaj_detalhe_processos (
            cpf, numero_processo_cnj, processo_origem, requerente_caps,
            numero_ordem, vara, processo_execucao, processo_conhecimento,
            data_ajuizamento, data_transito_julgado, data_base_atualizacao, data_nascimento,
            advogado_nome, advogado_oab, credor_nome, credor_cpf_cnpj, devedor_ente,
            banco, agencia, conta, conta_tipo, tipo_levantamento, 
            dados_bancarios_advogado, cpf_titular_conta,
            valor_principal_liquido, valor_principal_bruto, juros_moratorios,
            valor_total_requisitado, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
            valor_compensado, contribuicao_social, salario_pericial, 
            assist_tecnico, custas, despesas, multas,
            idoso, doenca_grave, pcd,
            rejeitado, motivo_rejeicao, observacoes, anomalia, descricao_anomalia,
            process_diagnostico, caminho_pdf, timestamp_ingestao
        ) VALUES (
            %(cpf)s, %(numero_processo_cnj)s, %(processo_origem)s, %(requerente_caps)s,
            %(numero_ordem)s, %(vara)s, %(processo_execucao)s, %(processo_conhecimento)s,
            %(data_ajuizamento)s, %(data_transito_julgado)s, %(data_base_atualizacao)s, %(data_nascimento)s,
            %(advogado_nome)s, %(advogado_oab)s, %(credor_nome)s, %(credor_cpf_cnpj)s, %(devedor_ente)s,
            %(banco)s, %(agencia)s, %(conta)s, %(conta_tipo)s, %(tipo_levantamento)s,
            %(dados_bancarios_advogado)s, %(cpf_titular_conta)s,
            %(valor_principal_liquido)s, %(valor_principal_bruto)s, %(juros_moratorios)s,
            %(valor_total_requisitado)s, %(contrib_previdenciaria_iprem)s, %(contrib_previdenciaria_hspm)s,
            %(valor_compensado)s, %(contribuicao_social)s, %(salario_pericial)s,
            %(assist_tecnico)s, %(custas)s, %(despesas)s, %(multas)s,
            %(idoso)s, %(doenca_grave)s, %(pcd)s,
            %(rejeitado)s, %(motivo_rejeicao)s, %(observacoes)s, %(anomalia)s, %(descricao_anomalia)s,
            %(process_diagnostico)s, %(caminho_pdf)s, %(timestamp_ingestao)s
        )
        ON CONFLICT (cpf, numero_processo_cnj) 
        DO UPDATE SET
            processo_origem = EXCLUDED.processo_origem,
            requerente_caps = EXCLUDED.requerente_caps,
            numero_ordem = EXCLUDED.numero_ordem,
            vara = EXCLUDED.vara,
            data_nascimento = EXCLUDED.data_nascimento,
            timestamp_ingestao = EXCLUDED.timestamp_ingestao;
    """
    
    # Processar JSONs
    print(f"\n📋 Processando JSONs...")
    
    for json_file in tqdm(json_files, desc="Ingerindo"):
        try:
            # Extrair CPF e processo
            cpf, numero_processo = extrair_cpf_processo(json_file)
            
            # Ler JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Preparar valores
            valores = {
                'cpf': cpf,
                'numero_processo_cnj': numero_processo,
                'processo_origem': data.get('processo_origem'),
                'requerente_caps': data.get('requerente_caps'),
                'numero_ordem': data.get('numero_ordem'),
                'vara': data.get('vara'),
                'processo_execucao': data.get('processo_execucao'),
                'processo_conhecimento': data.get('processo_conhecimento'),
                'data_ajuizamento': data.get('data_ajuizamento'),
                'data_transito_julgado': data.get('data_transito_julgado'),
                'data_base_atualizacao': data.get('data_base_atualizacao'),
                'data_nascimento': data.get('data_nascimento'),
                'advogado_nome': data.get('advogado_nome'),
                'advogado_oab': data.get('advogado_oab'),
                'credor_nome': data.get('credor_nome'),
                'credor_cpf_cnpj': data.get('credor_cpf_cnpj'),
                'devedor_ente': data.get('devedor_ente'),
                'banco': data.get('banco'),
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
                'rejeitado': data.get('rejeitado', False),
                'motivo_rejeicao': data.get('motivo_rejeicao'),
                'observacoes': data.get('observacoes'),
                'anomalia': data.get('anomalia', False),
                'descricao_anomalia': data.get('descricao_anomalia'),
                'process_diagnostico': data.get('process_diagnostico', False),
                'caminho_pdf': f"../data/consultas/{cpf}/{numero_processo}.pdf",
                'timestamp_ingestao': datetime.now()
            }
            
            # Executar INSERT
            cursor.execute(insert_query, valores)
            conn.commit()
            
            stats["sucesso"] += 1
            
        except Exception as e:
            stats["erros"] += 1
            logger.error(f"❌ {json_file.name}: {str(e)[:100]}")
            conn.rollback()
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Resumo
    print(f"\n" + "=" * 60)
    print(f"📊 RESUMO DA INGESTÃO")
    print("=" * 60)
    print(f"   Total de JSONs: {stats['total']}")
    print(f"   ✅ Sucesso: {stats['sucesso']}")
    print(f"   ❌ Erros: {stats['erros']}")
    print(f"   Taxa de sucesso: {stats['sucesso']/stats['total']*100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
