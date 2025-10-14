#!/usr/bin/env python
"""
Processador de Ofícios em Lotes com Relatório CSV Detalhado
Processa PDFs em lotes de 5 em 5 e gera CSV com status de cada campo
"""

import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

from app.processador import ProcessadorOficio
from app.detector import DetectorOficio
from app.detector_anexo import DetectorAnexoII

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
BASE_DIR = os.getenv("BASE_DIR", "./data/consultas")
OUTPUT_DIR = "./output/lotes"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAMANHO_LOTE = 5


def encontrar_pdfs(base_dir: str) -> List[Path]:
    """Encontra todos os PDFs na estrutura de pastas"""
    base_path = Path(base_dir)
    pdfs = sorted(base_path.glob("*/*.pdf"))
    return pdfs


def analisar_campo(valor: Any) -> str:
    """Retorna status do campo: ✓ (presente), ✗ (ausente), ou valor específico"""
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


def identificar_anomalias(resultado: Dict[str, Any]) -> str:
    """Identifica e descreve anomalias encontradas no processamento"""
    anomalias = []
    
    # Verificar se processou com sucesso
    if not resultado.get("sucesso"):
        return f"ERRO: {resultado.get('erro', 'Erro desconhecido')}"
    
    # Verificar detecção de ofício
    if not resultado.get("oficio_detectado"):
        anomalias.append("Ofício não detectado")
    
    # Verificar ANEXO II
    if not resultado.get("anexo_ii_detectado"):
        anomalias.append("ANEXO II ausente")
    
    # Verificar dados bancários
    dados = resultado.get("dados", {})
    if dados:
        tem_dados_bancarios = any([
            dados.get("banco"),
            dados.get("agencia"),
            dados.get("conta")
        ])
        
        if resultado.get("anexo_ii_detectado") and not tem_dados_bancarios:
            anomalias.append("ANEXO II detectado mas dados bancários não extraídos")
    
    # Verificar campos obrigatórios
    if dados and not dados.get("processo_origem"):
        anomalias.append("Processo origem ausente")
    
    if dados and not dados.get("requerente_caps"):
        anomalias.append("Requerente ausente")
    
    # Verificar se é PDF muito grande
    if resultado.get("num_paginas_oficio", 0) > 50:
        anomalias.append(f"PDF muito grande ({resultado.get('num_paginas_oficio')} páginas de ofício)")
    
    # Verificar se é PDF antigo (antes de 2015)
    processo = dados.get("processo_origem", "") if dados else ""
    if processo and len(processo) > 15:
        try:
            ano = int(processo.split(".")[2])
            if ano < 2015:
                anomalias.append(f"Processo antigo ({ano})")
        except:
            pass
    
    if not anomalias:
        return "OK"
    
    return " | ".join(anomalias)


def processar_pdf(pdf_path: Path, processador: ProcessadorOficio) -> Dict[str, Any]:
    """Processa um único PDF e retorna resultado detalhado"""
    resultado = {
        "pdf": pdf_path.name,
        "cpf": pdf_path.parent.name,
        "sucesso": False,
        "erro": None,
        "oficio_detectado": False,
        "anexo_ii_detectado": False,
        "num_paginas_oficio": 0,
        "num_paginas_anexo": 0,
        "dados": None,
        "tempo_processamento": 0
    }
    
    try:
        inicio = datetime.now()
        
        # Detectar ofício
        detector = DetectorOficio()
        paginas_oficio, texto_oficio = detector.detectar_oficio(str(pdf_path))
        resultado["oficio_detectado"] = len(paginas_oficio) > 0
        resultado["num_paginas_oficio"] = len(paginas_oficio)
        
        if not resultado["oficio_detectado"]:
            resultado["erro"] = "Ofício não detectado"
            return resultado
        
        # Detectar ANEXO II
        detector_anexo = DetectorAnexoII()
        paginas_anexo, texto_anexo = detector_anexo.detectar_anexo_ii(str(pdf_path))
        resultado["anexo_ii_detectado"] = len(paginas_anexo) > 0
        resultado["num_paginas_anexo"] = len(paginas_anexo)
        
        # Processar com LLM
        oficio_completo = processador.processar_arquivo(str(pdf_path))
        
        if oficio_completo and oficio_completo.oficio:
            resultado["sucesso"] = True
            resultado["dados"] = oficio_completo.oficio.model_dump()
        else:
            resultado["erro"] = "Falha na extração LLM"
        
        fim = datetime.now()
        resultado["tempo_processamento"] = (fim - inicio).total_seconds()
        
    except Exception as e:
        resultado["erro"] = str(e)
    
    return resultado


def gerar_csv_lote(resultados: List[Dict[str, Any]], lote_num: int, output_dir: Path):
    """Gera CSV detalhado para um lote de processamento"""
    
    csv_path = output_dir / f"lote_{lote_num:03d}.csv"
    
    # Definir campos do CSV
    campos_basicos = [
        "pdf", "cpf", "sucesso", "tempo_s",
        "oficio_detectado", "anexo_ii_detectado",
        "num_pag_oficio", "num_pag_anexo"
    ]
    
    campos_dados = [
        "processo_origem", "requerente_caps", "vara",
        "banco", "agencia", "conta", "conta_tipo",
        "valor_total", "valor_principal", "juros",
        "contrib_iprem", "contrib_hspm",
        "data_ajuizamento", "data_transito", "data_base",
        "credor_nome", "credor_cpf", "devedor_ente",
        "advogado_nome", "advogado_oab",
        "idoso", "doenca_grave", "pcd"
    ]
    
    campos_finais = ["anomalias"]
    
    todos_campos = campos_basicos + campos_dados + campos_finais
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=todos_campos)
        writer.writeheader()
        
        for resultado in resultados:
            dados = resultado.get("dados", {}) or {}
            
            # Extrair dados financeiros se estiverem aninhados
            financeiro = dados.get("financeiro", {}) if isinstance(dados.get("financeiro"), dict) else {}
            datas = dados.get("datas", {}) if isinstance(dados.get("datas"), dict) else {}
            partes = dados.get("partes", {}) if isinstance(dados.get("partes"), dict) else {}
            preferencias = dados.get("preferências", {}) if isinstance(dados.get("preferências"), dict) else {}
            
            row = {
                # Básicos
                "pdf": resultado["pdf"],
                "cpf": resultado["cpf"],
                "sucesso": "✓" if resultado["sucesso"] else "✗",
                "tempo_s": f"{resultado['tempo_processamento']:.1f}",
                "oficio_detectado": "✓" if resultado["oficio_detectado"] else "✗",
                "anexo_ii_detectado": "✓" if resultado["anexo_ii_detectado"] else "✗",
                "num_pag_oficio": resultado["num_paginas_oficio"],
                "num_pag_anexo": resultado["num_paginas_anexo"],
                
                # Dados principais
                "processo_origem": analisar_campo(dados.get("processo_origem")),
                "requerente_caps": analisar_campo(dados.get("requerente_caps")),
                "vara": analisar_campo(dados.get("vara")),
                
                # Dados bancários
                "banco": analisar_campo(dados.get("banco")),
                "agencia": analisar_campo(dados.get("agencia")),
                "conta": analisar_campo(dados.get("conta")),
                "conta_tipo": analisar_campo(dados.get("conta_tipo")),
                
                # Financeiro
                "valor_total": analisar_campo(
                    financeiro.get("valor_total_requisitado") or dados.get("valor_total_requisitado")
                ),
                "valor_principal": analisar_campo(
                    financeiro.get("valor_principal_liquido") or dados.get("valor_principal_liquido")
                ),
                "juros": analisar_campo(
                    financeiro.get("juros_moratorios") or dados.get("juros_moratorios")
                ),
                "contrib_iprem": analisar_campo(
                    financeiro.get("contrib_previdenciaria_iprem") or dados.get("contrib_previdenciaria_iprem")
                ),
                "contrib_hspm": analisar_campo(
                    financeiro.get("contrib_previdenciaria_hspm") or dados.get("contrib_previdenciaria_hspm")
                ),
                
                # Datas
                "data_ajuizamento": analisar_campo(
                    datas.get("data_ajuizamento") or dados.get("data_ajuizamento")
                ),
                "data_transito": analisar_campo(
                    datas.get("data_transito_julgado") or dados.get("data_transito_julgado")
                ),
                "data_base": analisar_campo(
                    datas.get("data_base_atualizacao") or dados.get("data_base_atualizacao")
                ),
                
                # Partes
                "credor_nome": analisar_campo(
                    partes.get("credor_nome") or dados.get("credor_nome")
                ),
                "credor_cpf": analisar_campo(
                    partes.get("credor_cpf_cnpj") or dados.get("credor_cpf_cnpj")
                ),
                "devedor_ente": analisar_campo(
                    partes.get("devedor_ente") or dados.get("devedor_ente")
                ),
                "advogado_nome": analisar_campo(dados.get("advogado_nome")),
                "advogado_oab": analisar_campo(dados.get("advogado_oab")),
                
                # Preferências
                "idoso": analisar_campo(
                    preferencias.get("idoso") or dados.get("idoso")
                ),
                "doenca_grave": analisar_campo(
                    preferencias.get("doenca_grave") or dados.get("doenca_grave")
                ),
                "pcd": analisar_campo(
                    preferencias.get("pcd") or dados.get("pcd")
                ),
                
                # Anomalias
                "anomalias": identificar_anomalias(resultado)
            }
            
            writer.writerow(row)
    
    print(f"   📄 CSV salvo: {csv_path}")
    return csv_path


def processar_em_lotes(pdfs: List[Path], output_dir: Path, inicio_lote: int = 1):
    """Processa PDFs em lotes de 5 e gera CSVs"""
    
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
    
    print(f"\n📊 Total de PDFs: {len(pdfs)}")
    print(f"📦 Total de lotes: {total_lotes} (tamanho: {TAMANHO_LOTE})")
    print(f"🎯 Iniciando do lote: {inicio_lote}")
    print()
    
    estatisticas_globais = {
        "total_pdfs": 0,
        "sucesso": 0,
        "erros": 0,
        "com_oficio": 0,
        "com_anexo_ii": 0,
        "com_dados_bancarios": 0,
        "tempo_total": 0
    }
    
    for i in range(0, len(pdfs), TAMANHO_LOTE):
        lote_num = (i // TAMANHO_LOTE) + 1
        
        if lote_num < inicio_lote:
            continue
        
        lote_pdfs = pdfs[i:i + TAMANHO_LOTE]
        
        print(f"{'='*60}")
        print(f"📦 LOTE {lote_num}/{total_lotes}")
        print(f"{'='*60}")
        print(f"PDFs neste lote: {len(lote_pdfs)}")
        print()
        
        resultados_lote = []
        
        for j, pdf in enumerate(lote_pdfs, 1):
            print(f"   [{j}/{len(lote_pdfs)}] Processando: {pdf.name}")
            resultado = processar_pdf(pdf, processador)
            resultados_lote.append(resultado)
            
            # Atualizar estatísticas
            estatisticas_globais["total_pdfs"] += 1
            if resultado["sucesso"]:
                estatisticas_globais["sucesso"] += 1
            else:
                estatisticas_globais["erros"] += 1
            
            if resultado["oficio_detectado"]:
                estatisticas_globais["com_oficio"] += 1
            
            if resultado["anexo_ii_detectado"]:
                estatisticas_globais["com_anexo_ii"] += 1
            
            if resultado["dados"] and any([
                resultado["dados"].get("banco"),
                resultado["dados"].get("agencia"),
                resultado["dados"].get("conta")
            ]):
                estatisticas_globais["com_dados_bancarios"] += 1
            
            estatisticas_globais["tempo_total"] += resultado["tempo_processamento"]
            
            status = "✅" if resultado["sucesso"] else "❌"
            print(f"      {status} {resultado.get('erro', 'OK')}")
        
        print()
        
        # Gerar CSV do lote
        csv_path = gerar_csv_lote(resultados_lote, lote_num, output_dir)
        
        # Salvar JSONs individuais
        json_dir = output_dir / f"lote_{lote_num:03d}_jsons"
        json_dir.mkdir(exist_ok=True)
        
        for resultado in resultados_lote:
            if resultado["sucesso"] and resultado["dados"]:
                json_path = json_dir / f"{resultado['cpf']}_{resultado['pdf'].replace('.pdf', '.json')}"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(resultado["dados"], f, indent=2, ensure_ascii=False, default=str)
        
        print(f"   💾 JSONs salvos em: {json_dir}")
        print()
        
        # Resumo do lote
        sucesso_lote = sum(1 for r in resultados_lote if r["sucesso"])
        print(f"   ✅ Sucesso: {sucesso_lote}/{len(lote_pdfs)}")
        print(f"   ❌ Erros: {len(lote_pdfs) - sucesso_lote}/{len(lote_pdfs)}")
        print()
    
    # Estatísticas finais
    print(f"{'='*60}")
    print(f"📊 ESTATÍSTICAS FINAIS")
    print(f"{'='*60}")
    print(f"Total processado: {estatisticas_globais['total_pdfs']}")
    print(f"Sucesso: {estatisticas_globais['sucesso']} ({estatisticas_globais['sucesso']/estatisticas_globais['total_pdfs']*100:.1f}%)")
    print(f"Erros: {estatisticas_globais['erros']}")
    print(f"Com ofício: {estatisticas_globais['com_oficio']}")
    print(f"Com ANEXO II: {estatisticas_globais['com_anexo_ii']}")
    print(f"Com dados bancários: {estatisticas_globais['com_dados_bancarios']}")
    print(f"Tempo total: {estatisticas_globais['tempo_total']:.1f}s")
    print(f"Tempo médio: {estatisticas_globais['tempo_total']/estatisticas_globais['total_pdfs']:.1f}s/PDF")
    print()
    
    # Salvar estatísticas
    stats_path = output_dir / "estatisticas_globais.json"
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(estatisticas_globais, f, indent=2)
    
    print(f"💾 Estatísticas salvas em: {stats_path}")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Processar ofícios em lotes")
    parser.add_argument("--input", default=BASE_DIR, help="Diretório de entrada")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Diretório de saída")
    parser.add_argument("--inicio", type=int, default=1, help="Número do lote inicial")
    parser.add_argument("--limite", type=int, help="Limitar número de PDFs")
    
    args = parser.parse_args()
    
    # Criar diretório de saída
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("🔄 PROCESSADOR EM LOTES - Ofícios Requisitórios TJSP")
    print("="*60)
    print(f"📁 Input: {args.input}")
    print(f"📁 Output: {args.output}")
    print(f"📦 Tamanho do lote: {TAMANHO_LOTE}")
    print()
    
    # Encontrar PDFs
    pdfs = encontrar_pdfs(args.input)
    
    if args.limite:
        pdfs = pdfs[:args.limite]
        print(f"⚠️  Limitado a {args.limite} PDFs")
    
    if not pdfs:
        print("❌ Nenhum PDF encontrado!")
        return
    
    # Processar
    processar_em_lotes(pdfs, output_path, args.inicio)
    
    print("="*60)
    print("✅ PROCESSAMENTO CONCLUÍDO")
    print("="*60)


if __name__ == "__main__":
    main()
