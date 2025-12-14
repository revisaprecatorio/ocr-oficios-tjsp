#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para análise e correção de falsos rejeitados.

Identifica processos marcados como rejeitados mas que foram
PROCESSADOS COM INFORMAÇÃO pelo DEPRE (possuem numero_ordem).

Autor: Cascade AI + Persival Balleste
Data: 15/10/2025
"""

import sys
from pathlib import Path
import pymupdf
import json
from typing import Dict, List, Tuple
import re

# Adicionar path do projeto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Lista de casos identificados (CPF, Processo)
CASOS_FALSOS_REJEITADOS = [
    ("95653511820", "0221126-48.2021.8.26.0500"),
    ("94706751853", "0221189-73.2021.8.26.0500"),
    ("94019940800", "0247212-56.2021.8.26.0500"),
    ("49783491920", "0085911-66.2022.8.26.0500"),
    ("41609824415", "0220428-42.2021.8.26.0500"),
    ("19884761434", "0221004-35.2021.8.26.0500"),
    ("11659296862", "0220433-64.2021.8.26.0500"),
    ("10185170811", "0223256-11.2021.8.26.0500"),
    ("10149607890", "0222597-02.2021.8.26.0500"),
    ("06495530803", "0223266-55.2021.8.26.0500"),
    ("03730461893", "0220341-86.2021.8.26.0500"),
    ("02174781824", "0221031-18.2021.8.26.0500"),
    ("01103192817", "0015266-16.2022.8.26.0500"),
]


def buscar_processamento_com_informacao(pdf_path: Path) -> Tuple[bool, str, int]:
    """
    Busca por "PROCESSAMENTO COM INFORMAÇÃO" no PDF.
    
    Returns:
        (encontrado, numero_ordem, pagina)
    """
    try:
        doc = pymupdf.open(pdf_path)
        
        for page_num, page in enumerate(doc, start=1):
            texto = page.get_text()
            
            # Buscar título "PROCESSAMENTO COM INFORMAÇÃO"
            if "PROCESSAMENTO COM INFORMAÇÃO" in texto or "PROCESSAMENTO COM INFORMACAO" in texto:
                
                # Buscar número de ordem na mesma página ou próxima
                match_ordem = re.search(r"N[°º]\s*de\s*Ordem:\s*(\d+/\d+)", texto, re.IGNORECASE)
                
                if match_ordem:
                    numero_ordem = match_ordem.group(1)
                    return True, numero_ordem, page_num
                
                # Se não encontrou na mesma página, verificar próxima
                if page_num < len(doc):
                    texto_prox = doc[page_num].get_text()
                    match_ordem = re.search(r"N[°º]\s*de\s*Ordem:\s*(\d+/\d+)", texto_prox, re.IGNORECASE)
                    if match_ordem:
                        numero_ordem = match_ordem.group(1)
                        return True, numero_ordem, page_num + 1
        
        doc.close()
        return False, "", 0
        
    except Exception as e:
        print(f"❌ Erro ao processar {pdf_path.name}: {e}")
        return False, "", 0


def analisar_caso(cpf: str, processo: str, base_dir: Path) -> Dict:
    """Analisa um caso específico de falso rejeitado."""
    
    pdf_path = base_dir / cpf / f"{processo}.pdf"
    
    resultado = {
        "cpf": cpf,
        "processo": processo,
        "pdf_existe": pdf_path.exists(),
        "processamento_encontrado": False,
        "numero_ordem": "",
        "pagina": 0,
        "status": "❌ Não analisado"
    }
    
    if not pdf_path.exists():
        resultado["status"] = "❌ PDF não encontrado"
        return resultado
    
    # Buscar padrão de processamento
    encontrado, numero_ordem, pagina = buscar_processamento_com_informacao(pdf_path)
    
    resultado["processamento_encontrado"] = encontrado
    resultado["numero_ordem"] = numero_ordem
    resultado["pagina"] = pagina
    
    if encontrado:
        resultado["status"] = f"✅ PROCESSADO (Ordem: {numero_ordem}, Pág: {pagina})"
    else:
        resultado["status"] = "⚠️  Padrão não encontrado"
    
    return resultado


def main():
    """Função principal."""
    
    print("=" * 80)
    print("🔍 ANÁLISE DE FALSOS REJEITADOS")
    print("=" * 80)
    print()
    
    # Diretório base dos PDFs
    base_dir = project_root / "data" / "consultas"
    
    if not base_dir.exists():
        print(f"❌ Diretório não encontrado: {base_dir}")
        return
    
    print(f"📁 Base de PDFs: {base_dir}")
    print(f"📊 Total de casos: {len(CASOS_FALSOS_REJEITADOS)}")
    print()
    
    # Analisar cada caso
    resultados = []
    
    for i, (cpf, processo) in enumerate(CASOS_FALSOS_REJEITADOS, start=1):
        print(f"[{i:2d}/{len(CASOS_FALSOS_REJEITADOS)}] Analisando {cpf}/{processo}...", end=" ")
        
        resultado = analisar_caso(cpf, processo, base_dir)
        resultados.append(resultado)
        
        print(resultado["status"])
    
    print()
    print("=" * 80)
    print("📊 RESUMO DA ANÁLISE")
    print("=" * 80)
    print()
    
    # Estatísticas
    total = len(resultados)
    processados = sum(1 for r in resultados if r["processamento_encontrado"])
    nao_encontrados = sum(1 for r in resultados if not r["pdf_existe"])
    padrao_nao_encontrado = sum(1 for r in resultados if r["pdf_existe"] and not r["processamento_encontrado"])
    
    print(f"✅ Processos PROCESSADOS COM INFORMAÇÃO: {processados}/{total}")
    print(f"❌ PDFs não encontrados: {nao_encontrados}/{total}")
    print(f"⚠️  Padrão não encontrado: {padrao_nao_encontrado}/{total}")
    print()
    
    # Detalhes dos processados
    if processados > 0:
        print("📋 DETALHES DOS PROCESSADOS:")
        print()
        for r in resultados:
            if r["processamento_encontrado"]:
                print(f"  • CPF: {r['cpf']}")
                print(f"    Processo: {r['processo']}")
                print(f"    Nº Ordem: {r['numero_ordem']}")
                print(f"    Página: {r['pagina']}")
                print()
    
    # Salvar resultados em JSON
    output_file = Path(__file__).parent / "analise_falsos_rejeitados.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Resultados salvos em: {output_file}")
    print()
    
    # Conclusão
    print("=" * 80)
    print("🎯 CONCLUSÃO")
    print("=" * 80)
    print()
    
    if processados == total:
        print("✅ TODOS os 13 casos são FALSOS REJEITADOS!")
        print("   Todos possuem 'PROCESSAMENTO COM INFORMAÇÃO' e número de ordem.")
        print()
        print("🔧 AÇÃO NECESSÁRIA:")
        print("   1. Atualizar banco: rejeitado = FALSE para esses processos")
        print("   2. Ajustar lógica: se numero_ordem presente → rejeitado = FALSE")
        print("   3. Reprocessar PDFs com nova lógica")
    else:
        print(f"⚠️  {processados}/{total} casos confirmados como falsos rejeitados.")
        print(f"   {padrao_nao_encontrado} casos precisam de análise manual.")
    
    print()


if __name__ == "__main__":
    main()
