#!/usr/bin/env python3
"""
Script de Ingestão V7 - PROTEÇÃO DE DADOS & FALLBACK TOTAL
- Fix 1: Fallback do 'valor_principal_bruto' (resolve Valor Original zerado)
- Fix 2: SQL com COALESCE (impede que um OCR vazio apague dados existentes como Vara/Advogado)
- Fix 3: Mantém limpeza de moeda e data
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from tqdm import tqdm

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- FUNÇÕES DE LIMPEZA ---
def limpar_moeda(valor):
    """Converte 'R$ 1.500,00' para 1500.00"""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    
    s = str(valor).strip().replace("R$", "").replace("r$", "").strip()
    if not s:
        return None

    try:
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return None

def converter_data(valor):
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'"""
    if not valor or valor == "":
        return None
    s = str(valor).strip()
    try:
        return datetime.strptime(s, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None

def extrair_numero_processo(json_path: Path) -> str:
    filename = json_path.stem
    filename = filename.split(" (")[0]
    if "_" in filename:
        return filename.split("_", 1)[1]
    return filename

def main():
    parser = argparse.ArgumentParser(description="Ingestão de JSONs para DB")
    parser.add_argument("--input", help="Pasta de entrada dos JSONs")
    parser.add_argument("--db-host", help="Host do banco")
    parser.add_argument("--db-port", help="Porta do banco")
    parser.add_argument("--db-name", help="Nome do banco")
    parser.add_argument("--db-user", help="Usuário do banco")
    parser.add_argument("--cpf", required=True, help="CPF da execução")

    args, unknown = parser.parse_known_args()
    cpf_execucao = args.cpf.strip()

    print("=" * 60)
    print("📥 INGESTÃO V7 (SAFE UPDATE & FULL FALLBACK)")
    print(f"👤 CPF DA EXECUÇÃO: {cpf_execucao}")
    print("=" * 60)

    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    db_config = {
        "host": args.db_host or os.getenv("DB_HOST"),
        "port": args.db_port or os.getenv("DB_PORT"),
        "database": args.db_name or os.getenv("DB_NAME"),
        "user": args.db_user or os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
    }

    if not db_config["password"]:
        print("❌ ERRO: Senha do banco não encontrada")
        sys.exit(1)

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print("🔌 Conectado ao PostgreSQL")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        sys.exit(1)

    if args.input:
        json_dir = Path(args.input)
    else:
        json_dir = Path(__file__).parent.parent.parent / "1_parsing_PDF" / "outputs" / "json"

    if not json_dir.exists():
        print(f"❌ Pasta de JSONs não encontrada: {json_dir}")
        sys.exit(1)

    json_files = sorted(json_dir.glob("*.json"))
    
    if not json_files:
        print("⚠️ Nenhum JSON encontrado.")
        sys.exit(0)

    stats = {"total": len(json_files), "sucesso": 0, "erros": 0, "atualizados": 0, "inseridos": 0}

    # Query Upsert Checks
    check_query = """
        SELECT 1 FROM public.esaj_detalhe_processos 
        WHERE cpf = %(cpf)s AND numero_processo_cnj = %(numero_processo_cnj)s
    """
    
    insert_query = """
        INSERT INTO public.esaj_detalhe_processos (
            cpf, numero_processo_cnj, processo_origem, requerente_caps, numero_ordem, vara,
            processo_execucao, processo_conhecimento, data_ajuizamento, data_transito_julgado,
            data_base_atualizacao, data_nascimento, advogado_nome, advogado_oab,
            credor_nome, credor_cpf_cnpj, devedor_ente, banco, agencia, conta,
            conta_tipo, tipo_levantamento, dados_bancarios_advogado, cpf_titular_conta,
            valor_principal_liquido, valor_principal_bruto, juros_moratorios, valor_total_requisitado, saldo_final,
            contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_compensado, contribuicao_social,
            salario_pericial, assist_tecnico, custas, despesas, multas,
            idoso, doenca_grave, pcd, preferencial, habilitacao_herdeiros, cessao_credito,
            obito, data_obito, cpf_sucessor,
            rejeitado, motivo_rejeicao, observacoes, anomalia, descricao_anomalia, process_diagnostico,
            caminho_pdf, timestamp_ingestao
        ) VALUES (
            %(cpf)s, %(numero_processo_cnj)s, %(processo_origem)s, %(requerente_caps)s, %(numero_ordem)s, %(vara)s,
            %(processo_execucao)s, %(processo_conhecimento)s, %(data_ajuizamento)s, %(data_transito_julgado)s,
            %(data_base_atualizacao)s, %(data_nascimento)s, %(advogado_nome)s, %(advogado_oab)s,
            %(credor_nome)s, %(credor_cpf_cnpj)s, %(devedor_ente)s, %(banco)s, %(agencia)s, %(conta)s,
            %(conta_tipo)s, %(tipo_levantamento)s, %(dados_bancarios_advogado)s, %(cpf_titular_conta)s,
            %(valor_principal_liquido)s, %(valor_principal_bruto)s, %(juros_moratorios)s, %(valor_total_requisitado)s, %(saldo_final)s,
            %(contrib_previdenciaria_iprem)s, %(contrib_previdenciaria_hspm)s, %(valor_compensado)s, %(contribuicao_social)s,
            %(salario_pericial)s, %(assist_tecnico)s, %(custas)s, %(despesas)s, %(multas)s,
            %(idoso)s, %(doenca_grave)s, %(pcd)s, %(preferencial)s, %(habilitacao_herdeiros)s, %(cessao_credito)s,
            %(obito)s, %(data_obito)s, %(cpf_sucessor)s,
            %(rejeitado)s, %(motivo_rejeicao)s, %(observacoes)s, %(anomalia)s, %(descricao_anomalia)s, %(process_diagnostico)s,
            %(caminho_pdf)s, %(timestamp_ingestao)s
        )
    """

    # --- [FIX CRÍTICO] UPDATE INTELIGENTE (COALESCE) ---
    # Só substitui o valor no banco se o novo valor (do JSON) NÃO for nulo.
    # Se o novo for nulo, mantém o antigo.
    update_query = """
        UPDATE public.esaj_detalhe_processos SET
            processo_origem = COALESCE(%(processo_origem)s, processo_origem),
            requerente_caps = COALESCE(%(requerente_caps)s, requerente_caps),
            numero_ordem = COALESCE(%(numero_ordem)s, numero_ordem),
            vara = COALESCE(%(vara)s, vara),
            processo_execucao = COALESCE(%(processo_execucao)s, processo_execucao),
            processo_conhecimento = COALESCE(%(processo_conhecimento)s, processo_conhecimento),
            data_ajuizamento = COALESCE(%(data_ajuizamento)s, data_ajuizamento),
            data_transito_julgado = COALESCE(%(data_transito_julgado)s, data_transito_julgado),
            data_nascimento = COALESCE(%(data_nascimento)s, data_nascimento),
            advogado_nome = COALESCE(%(advogado_nome)s, advogado_nome),
            advogado_oab = COALESCE(%(advogado_oab)s, advogado_oab),
            credor_nome = COALESCE(%(credor_nome)s, credor_nome),
            credor_cpf_cnpj = COALESCE(%(credor_cpf_cnpj)s, credor_cpf_cnpj),
            devedor_ente = COALESCE(%(devedor_ente)s, devedor_ente),
            
            -- Valores: Sobrescreve, pois cálculo novo é prioridade
            saldo_final = %(saldo_final)s,
            data_base_atualizacao = %(data_base_atualizacao)s,
            banco = %(banco)s,
            agencia = %(agencia)s,
            conta = %(conta)s,
            conta_tipo = %(conta_tipo)s,
            tipo_levantamento = %(tipo_levantamento)s,
            
            valor_total_requisitado = %(valor_total_requisitado)s,
            valor_principal_liquido = %(valor_principal_liquido)s,
            valor_principal_bruto = %(valor_principal_bruto)s,
            juros_moratorios = %(juros_moratorios)s,
            
            motivo_rejeicao = %(motivo_rejeicao)s,
            rejeitado = %(rejeitado)s,
            doenca_grave = %(doenca_grave)s,
            idoso = %(idoso)s,
            pcd = %(pcd)s,
            preferencial = %(preferencial)s,
            obito = %(obito)s,
            
            observacoes = %(observacoes)s,
            timestamp_ingestao = %(timestamp_ingestao)s,
            caminho_pdf = %(caminho_pdf)s
        WHERE cpf = %(cpf)s AND numero_processo_cnj = %(numero_processo_cnj)s
    """

    print("\n📋 Processando JSONs com Update Inteligente...\n")

    for json_file in tqdm(json_files, desc="Ingestão"):
        try:
            numero_processo = extrair_numero_processo(json_file)
            
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # --- Mapeamento Inicial ---
            valores = {
                "cpf": cpf_execucao,
                "numero_processo_cnj": numero_processo,
                "data_base_atualizacao": converter_data(data.get("data_base_atualizacao")),
                "data_ajuizamento": converter_data(data.get("data_ajuizamento")),
                "data_transito_julgado": converter_data(data.get("data_transito_julgado")),
                "data_nascimento": converter_data(data.get("data_nascimento")),
                "data_obito": converter_data(data.get("data_obito")),
                
                # Valores com limpeza
                "valor_principal_liquido": limpar_moeda(data.get("valor_principal_liquido")),
                "valor_principal_bruto": limpar_moeda(data.get("valor_principal_bruto")),
                "juros_moratorios": limpar_moeda(data.get("juros_moratorios")),
                "valor_total_requisitado": limpar_moeda(data.get("valor_total_requisitado")),
                "saldo_final": limpar_moeda(data.get("saldo_final")),
                "contrib_previdenciaria_iprem": limpar_moeda(data.get("contrib_previdenciaria_iprem")),
                "contrib_previdenciaria_hspm": limpar_moeda(data.get("contrib_previdenciaria_hspm")),
                "valor_compensado": limpar_moeda(data.get("valor_compensado")),
                "contribuicao_social": limpar_moeda(data.get("contribuicao_social")),
                "salario_pericial": limpar_moeda(data.get("salario_pericial")),
                "custas": limpar_moeda(data.get("custas")),
                "despesas": limpar_moeda(data.get("despesas")),
                "multas": limpar_moeda(data.get("multas")),
                "assist_tecnico": limpar_moeda(data.get("assist_tecnico")),

                # Restante dos campos
                "processo_origem": data.get("processo_origem"),
                "requerente_caps": data.get("requerente_caps"),
                "numero_ordem": data.get("numero_ordem"),
                "vara": data.get("vara"),
                "processo_execucao": data.get("processo_execucao"),
                "processo_conhecimento": data.get("processo_conhecimento"),
                "advogado_nome": data.get("advogado_nome"),
                "advogado_oab": data.get("advogado_oab"),
                "credor_nome": data.get("credor_nome"),
                "credor_cpf_cnpj": data.get("credor_cpf_cnpj"),
                "devedor_ente": data.get("devedor_ente"),
                "banco": data.get("banco"),
                "agencia": data.get("agencia"),
                "conta": data.get("conta"),
                "conta_tipo": data.get("conta_tipo"),
                "tipo_levantamento": data.get("tipo_levantamento"),
                "cpf_titular_conta": data.get("cpf_titular_conta"),
                "cpf_sucessor": data.get("cpf_sucessor"),
                "motivo_rejeicao": data.get("motivo_rejeicao"),
                "observacoes": data.get("observacoes"),
                "descricao_anomalia": data.get("descricao_anomalia"),
                "dados_bancarios_advogado": bool(data.get("dados_bancarios_advogado")),
                "idoso": bool(data.get("idoso")),
                "doenca_grave": bool(data.get("doenca_grave")),
                "pcd": bool(data.get("pcd")),
                "preferencial": bool(data.get("preferencial")),
                "habilitacao_herdeiros": bool(data.get("habilitacao_herdeiros")),
                "cessao_credito": bool(data.get("cessao_credito")),
                "obito": bool(data.get("obito")),
                "rejeitado": bool(data.get("rejeitado")),
                "anomalia": bool(data.get("anomalia")),
                "process_diagnostico": bool(data.get("process_diagnostico")),
                "caminho_pdf": f"../data/consultas/{cpf_execucao}/{numero_processo}.pdf",
                "timestamp_ingestao": datetime.now()
            }

            # --- LÓGICA DE FALLBACK APRIMORADA ---
            # Se faltar detalhe, usa o Total
            v_total = valores["valor_total_requisitado"]
            
            if v_total and v_total > 0:
                if not valores["saldo_final"]:
                    valores["saldo_final"] = v_total
                
                if not valores["valor_principal_liquido"]:
                    valores["valor_principal_liquido"] = v_total
                
                # [NOVO] Garante que Valor Original não fique zero
                if not valores["valor_principal_bruto"]:
                    valores["valor_principal_bruto"] = v_total

            # Upsert
            cursor.execute(check_query, valores)
            existe = cursor.fetchone()

            if existe:
                cursor.execute(update_query, valores)
                stats["atualizados"] += 1
            else:
                cursor.execute(insert_query, valores)
                stats["inseridos"] += 1
            
            conn.commit()
            stats["sucesso"] += 1

        except Exception as e:
            conn.rollback()
            stats["erros"] += 1
            print(f"❌ ERRO no arquivo {json_file.name}: {str(e)}")
            logger.exception(e)

    cursor.close()
    conn.close()

    print("\n" + "=" * 60)
    print("📊 RESUMO DA INGESTÃO")
    print(f"   CPF: {cpf_execucao}")
    print(f"   Total: {stats['total']}")
    print(f"   ✅ Sucesso: {stats['sucesso']}")
    print(f"   ❌ Erros: {stats['erros']}")
    print("=" * 60)

if __name__ == "__main__":
    main()