#!/usr/bin/env python
"""
Pipeline Consolidado de Processamento de Ofícios Requisitórios - V3.0

Script principal para processar PDFs de ofícios em lotes.
Utiliza ProcessadorOficio V3.0 (Schema Cleanup + Production Ready).

Funcionalidades:
- Processamento em lotes com tamanho configurável
- Validação de CPF e extração seletiva
- Barra de progresso (tqdm)
- Geração de CSVs e JSONs
- Tracking completo de execução

Uso:
    python3 processar_pipeline.py                    # Processar todos os lotes
    python3 processar_pipeline.py --lotes 4,5,6,7    # Processar lotes específicos
    python3 processar_pipeline.py --all --force      # Reprocessar tudo

Versão: V3.0 (Schema cleanup 50→35 cols + V2.7.6 fixes)
"""

import os
import sys
import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm  # Barra de progresso

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Adicionar pasta app ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.processador import ProcessadorOficio
from app.tracker_execucao import TrackerExecucao

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent.parent / ".env")

# Configurações
BASE_DIR = os.getenv("BASE_DIR", "../data/consultas")
OUTPUT_DIR = "./outputs"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAMANHO_LOTE = 5

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# def encontrar_pdfs(base_dir: str) -> List[Path]:
#     """Encontra todos os PDFs na estrutura de pastas"""
#     base_path = Path(base_dir)
#     if not base_path.exists():
#         base_path = Path(__file__).parent.parent / base_dir
    
#     pdfs = sorted(base_path.glob("*/*.pdf"))
#     return pdfs

def encontrar_pdfs(base_dir: str) -> List[Path]:
    """Encontra todos os PDFs na estrutura de pastas (Recursivo)"""
    base_path = Path(base_dir)
    if not base_path.exists():
        base_path = Path(__file__).parent.parent / base_dir
    
    # rglob = Recursive Glob (procura em toda a árvore de diretórios)
    pdfs = sorted(base_path.rglob("*.pdf"))
    
    # Filtro opcional: ignora arquivos que começam com '._' ou temporários
    pdfs = [p for p in pdfs if not p.name.startswith("._")]
    
    return pdfs

def analisar_campo(valor: Any) -> str:
    """Retorna status do campo: ✓ (presente), ✗ (ausente)"""
    if valor is None:
        return "✗"
    if isinstance(valor, bool):
        return "✓" if valor else "✗"
    if isinstance(valor, (int, float)) and valor == 0:
        return "0"
    if isinstance(valor, str) and len(valor.strip()) == 0:
        return "✗"
    if isinstance(valor, dict) and len(valor) == 0:
        return "✗"
    return "✓"


def gerar_csv_lote(resultados: List[Dict[str, Any]], lote_num: int, output_dir: Path):
    """Gera CSV detalhado para um lote"""
    
    csv_path = output_dir / f"lote_{lote_num:03d}.csv"
    
    # Campos do CSV
    campos = [
        # Básicos
        "pdf", "cpf", "sucesso", "tempo_s",
        # Detecção
        "oficios_encontrados", "cpf_validado",
        # Controle V2
        "rejeitado", "motivo_rejeicao", "anomalia", "descricao_anomalia",
        # Campos obrigatórios V2
        "processo_origem", "requerente_caps", "numero_ordem",
        # Valores obrigatórios V2
        "valor_principal_liquido", "valor_principal_bruto",
        "juros_moratorios", "valor_total",
        # Dados bancários
        "banco", "agencia", "conta", "conta_tipo",
        # Outros
        "vara", "contrib_iprem", "contrib_hspm",
        "data_nascimento", "data_base",
        "idoso", "doenca_grave", "pcd",
        # Anomalias
        "anomalias"
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        
        for resultado in resultados:
            dados = resultado.get("dados", {}) or {}
            
            row = {
                # Básicos
                "pdf": resultado["pdf"],
                "cpf": resultado["cpf"],
                "sucesso": "" if resultado["sucesso"] else "✗",
                "tempo_s": f"{resultado['tempo_processamento']:.1f}",
                
                # Detecção
                "oficios_encontrados": resultado.get("num_oficios", 0),
                "cpf_validado": "" if resultado.get("cpf_validado") else "✗",
                
                # Controle V2
                "rejeitado": "" if dados.get("rejeitado") else "✗",
                "motivo_rejeicao": (dados.get("motivo_rejeicao", "")[:50] + "...") if dados.get("motivo_rejeicao") else "",
                "anomalia": "" if dados.get("anomalia") else "✗",
                "descricao_anomalia": (dados.get("descricao_anomalia", "")[:50] + "...") if dados.get("descricao_anomalia") else "",
                
                # Campos obrigatórios
                "processo_origem": analisar_campo(dados.get("processo_origem")),
                "requerente_caps": analisar_campo(dados.get("requerente_caps")),
                "numero_ordem": analisar_campo(dados.get("numero_ordem")),
                
                # Valores obrigatórios
                "valor_principal_liquido": analisar_campo(dados.get("valor_principal_liquido")),
                "valor_principal_bruto": analisar_campo(dados.get("valor_principal_bruto")),
                "juros_moratorios": analisar_campo(dados.get("juros_moratorios")),
                "valor_total": analisar_campo(dados.get("valor_total_requisitado")),
                
                # Dados bancários
                "banco": analisar_campo(dados.get("banco")),
                "agencia": analisar_campo(dados.get("agencia")),
                "conta": analisar_campo(dados.get("conta")),
                "conta_tipo": analisar_campo(dados.get("conta_tipo")),
                
                # Outros
                "vara": analisar_campo(dados.get("vara")),
                "contrib_iprem": analisar_campo(dados.get("contrib_previdenciaria_iprem")),
                "contrib_hspm": analisar_campo(dados.get("contrib_previdenciaria_hspm")),
                "data_nascimento": analisar_campo(dados.get("data_nascimento")),
                "data_base": analisar_campo(dados.get("data_base_atualizacao")),
                "idoso": analisar_campo(dados.get("idoso")),
                "doenca_grave": analisar_campo(dados.get("doenca_grave")),
                "pcd": analisar_campo(dados.get("pcd")),
                
                # Anomalias
                "anomalias": resultado.get("erro", "OK") if not resultado["sucesso"] else "OK"
            }
            
            writer.writerow(row)
    
    logger.info(f"    CSV salvo: {csv_path}")
    return csv_path


def processar_pdf(pdf_path: Path, processador: ProcessadorOficio, logs_dir: Path) -> Dict[str, Any]:
    """Processa um único PDF com tracking completo"""
    resultado = {
        "pdf": pdf_path.name,
        "cpf": pdf_path.parent.name,
        "sucesso": False,
        "erro": None,
        "num_oficios": 0,
        "cpf_validado": False,
        "dados": None,
        "tempo_processamento": 0
    }

    try:
        # Extrair CPF e número do processo do nome do arquivo
        cpf = pdf_path.parent.name  # CPF da pasta
        processo = pdf_path.stem  # Número do processo sem .pdf

        # Criar tracker para este CPF
        tracker = TrackerExecucao(cpf=cpf, processo=processo)

        # Processar com V3.0 + tracker
        resultado = processador.processar_arquivo(str(pdf_path), cpf, tracker=tracker)

        # Salvar Markdown
        if tracker:
            try:
                tracker.salvar(str(logs_dir))
                logger.info(f" Markdown salvo: {cpf}_{processo}_execution.md")
            except Exception as e_save:
                logger.error(f" Erro ao salvar Markdown: {e_save}")

    except Exception as e:
        resultado["erro"] = str(e)
        logger.error(f"Erro ao processar {pdf_path.name}: {e}")

    return resultado


def processar_em_lotes(pdfs: List[Path], output_dir: Path, inicio_lote: int = 1):
    """Processa PDFs em lotes de 5"""

    # Criar diretório de logs
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f" Logs Markdown: {logs_dir}")

    # Criar processador
    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "oficios_tjsp"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", "")
    }

    processador = ProcessadorOficio(OPENAI_API_KEY, db_config)
    
    # Processar em lotes
    total_lotes = (len(pdfs) + TAMANHO_LOTE - 1) // TAMANHO_LOTE
    
    print(f"\n Total de PDFs: {len(pdfs)}")
    print(f" Total de lotes: {total_lotes} (tamanho: {TAMANHO_LOTE})")
    print(f" Iniciando do lote: {inicio_lote}")
    print()
    
    estatisticas_globais = {
        "total_pdfs": 0,
        "sucesso": 0,
        "erros": 0,
        "cpf_validado": 0,
        "tempo_total": 0
    }
    
    # Barra de progresso global
    with tqdm(total=len(pdfs), desc=" Processamento Geral", unit="PDF", 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar_global:
        
        for i in range(0, len(pdfs), TAMANHO_LOTE):
            lote_num = (i // TAMANHO_LOTE) + 1
            
            if lote_num < inicio_lote:
                pbar_global.update(len(pdfs[i:i + TAMANHO_LOTE]))
                continue
            
            lote_pdfs = pdfs[i:i + TAMANHO_LOTE]
            
            print(f"\n{'='*60}")
            print(f" LOTE {lote_num}/{total_lotes}")
            print(f"{'='*60}")
            
            resultados_lote = []
            lote_dir = output_dir / f"lote_{lote_num:03d}"
            lote_dir.mkdir(parents=True, exist_ok=True)
            
            # Barra de progresso do lote
            for pdf in tqdm(lote_pdfs, desc=f"  Lote {lote_num}", unit="PDF", leave=False):
                resultado = processar_pdf(pdf, processador, logs_dir)
                resultados_lote.append(resultado)
                
                # Atualizar estatísticas
                estatisticas_globais["total_pdfs"] += 1
                if resultado["sucesso"]:
                    estatisticas_globais["sucesso"] += 1
                else:
                    estatisticas_globais["erros"] += 1
                
                if resultado["cpf_validado"]:
                    estatisticas_globais["cpf_validado"] += 1
                
                estatisticas_globais["tempo_total"] += resultado["tempo_processamento"]
                
                # Atualizar barra global
                pbar_global.update(1)
                
                # Log de erro (se houver)
                if not resultado["sucesso"]:
                    erro_msg = resultado.get('erro', 'N/A')
                    tqdm.write(f"       {pdf.name}: {erro_msg[:60]}")
            
            # Salvar JSONs individuais
            for resultado in resultados_lote:
                if resultado["sucesso"] and resultado["dados"]:
                    json_path = lote_dir / f"{resultado['cpf']}_{resultado['pdf'].replace('.pdf', '.json')}"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(resultado["dados"], f, indent=2, ensure_ascii=False, default=str)
            
            # Gerar CSV do lote
            csv_path = gerar_csv_lote(resultados_lote, lote_num, output_dir)
            
            # Resumo do lote
            sucesso_lote = sum(1 for r in resultados_lote if r["sucesso"])
            print(f"\n   Sucesso: {sucesso_lote}/{len(lote_pdfs)}")
            print(f"    Erros: {len(lote_pdfs) - sucesso_lote}/{len(lote_pdfs)}")
    
    # Estatísticas finais
    print(f"{'='*60}")
    print(f" ESTATÍSTICAS FINAIS V3.0")
    print(f"{'='*60}")
    print(f"Total processado: {estatisticas_globais['total_pdfs']}")
    print(f"Sucesso: {estatisticas_globais['sucesso']} ({estatisticas_globais['sucesso']/estatisticas_globais['total_pdfs']*100:.1f}%)")
    print(f"Erros: {estatisticas_globais['erros']}")
    print(f"CPF validado: {estatisticas_globais['cpf_validado']}")
    print(f"Tempo total: {estatisticas_globais['tempo_total']:.1f}s")
    print(f"Tempo médio: {estatisticas_globais['tempo_total']/estatisticas_globais['total_pdfs']:.1f}s/PDF")
    print()
    
    # Salvar estatísticas
    stats_path = output_dir / "estatisticas_globais.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(estatisticas_globais, f, indent=2)
    
    print(f" Estatísticas salvas em: {stats_path}")


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Processar ofícios em lotes V3.0")
    parser.add_argument("--input", default=BASE_DIR, help="Diretório de entrada")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Diretório de saída")
    parser.add_argument("--inicio", type=int, default=1, help="Número do lote inicial")
    parser.add_argument("--limite", type=int, help="Limitar número de PDFs")
    
    args = parser.parse_args()
    
    # Criar diretório de saída
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("[PROCESSADOR] PROCESSADOR EM LOTES V3.0 - Ofícios Requisitórios TJSP")
    print("="*60)
    print(f"Input: {args.input}")
    print(f" Output: {args.output}")
    print(f"Tamanho do lote: {TAMANHO_LOTE}")
    print()
    
    # Encontrar PDFs
    pdfs = encontrar_pdfs(args.input)
    
    if args.limite:
        pdfs = pdfs[:args.limite]
        print(f" Limitado a {args.limite} PDFs")
    
    if not pdfs:
        print("Nenhum PDF encontrado!")
        return
    
    # Processar
    processar_em_lotes(pdfs, output_path, args.inicio)

    print("="*60)
    print(" PROCESSAMENTO V3.0 CONCLUÍDO")
    print("="*60)


if __name__ == "__main__":
    main()
