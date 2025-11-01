#!/usr/bin/env python3
"""
Script para gerar tabela detalhada de análise dos PDFs processados
====================================================================

Extrai informações do log de validação e gera tabela com:
- CPF
- Número do Processo
- Valores calculados (processados)
- Valores esperados (CSV)
- Diferenças
- Páginas onde foram obtidos os valores
- Path do PDF
"""

import re
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict

# Caminhos
LOG_FILE = Path(__file__).parent.parent / "test_data" / "validacao_output.log"
CSV_REF = Path(__file__).parent.parent / "test_data" / "2025-10-31T23-26_export.csv"
OUTPUT_CSV = Path(__file__).parent.parent / "test_data" / "analise_detalhada.csv"
OUTPUT_MD = Path(__file__).parent.parent / "docs" / "TABELA_ANALISE_COMPLETA.md"


def extrair_dados_log(log_file: Path) -> List[Dict]:
    """Extrai dados estruturados do log de validação"""
    
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    resultados = []
    
    # Padrão para identificar cada processamento
    pattern_processamento = re.compile(
        r'\[(\d+)/\d+\] CPF: (\d+)\n.*?Processando: (\d+)/([\d\-\.]+\.pdf)\n'
        r'.*?Páginas enviadas: Ofício \[([\d, ]+)\].*?ANEXO II \[([\d, ]*)\].*?PROC \[([\d, ]*)\]\n'
        r'(.*?)(?=\n\[|\Z)',
        re.DOTALL
    )
    
    matches = pattern_processamento.finditer(log_content)
    
    for match in matches:
        idx = match.group(1)
        cpf = match.group(2)
        processo = match.group(4).replace('.pdf', '')
        
        # Páginas
        paginas_oficio = match.group(5)
        paginas_anexo = match.group(6) if match.group(6) else "N/A"
        paginas_proc = match.group(7) if match.group(7) else "N/A"
        
        resto_log = match.group(8)
        
        # Extrair valores processados
        valores_processados = {}
        
        # Buscar no JSON de resposta ou nos logs
        for campo in ['valor_principal_liquido', 'valor_principal_bruto', 'juros_moratorios', 'valor_total_requisitado']:
            # Tentar extrair do log
            pattern_valor = rf"'{campo}': Decimal\('([\d.]+)'\)"
            valor_match = re.search(pattern_valor, resto_log)
            if valor_match:
                valores_processados[campo] = float(valor_match.group(1))
            else:
                valores_processados[campo] = None
        
        # Verificar se houve discrepância
        discrepancia = "✓ Valores corretos" in resto_log
        tem_discrepancia = "DISCREPÂNCIA ENCONTRADA" in resto_log
        
        # Se teve discrepância, extrair valores de referência
        valores_referencia = {}
        diferencas = {}
        
        if tem_discrepancia:
            # Extrair valores da discrepância
            pattern_disc = r'• ([\w_]+):\n\s+Processado: R\$ ([\d,\.]+)\n\s+Referência: R\$ ([\d,\.]+)\n\s+Diferença: R\$ ([\d,\.]+) \(([\d\.]+)%\)'
            
            for disc_match in re.finditer(pattern_disc, resto_log):
                campo = disc_match.group(1)
                valor_proc = float(disc_match.group(2).replace(',', ''))
                valor_ref = float(disc_match.group(3).replace(',', ''))
                diferenca = float(disc_match.group(4).replace(',', ''))
                percentual = float(disc_match.group(5))
                
                valores_processados[campo] = valor_proc
                valores_referencia[campo] = valor_ref
                diferencas[campo] = {
                    'valor': diferenca,
                    'percentual': percentual
                }
        
        # Path do PDF
        pdf_path = f"data/consultas/{cpf}/{processo}.pdf"
        
        resultado = {
            'indice': idx,
            'cpf': cpf,
            'processo': processo,
            'pdf_path': pdf_path,
            'paginas_oficio': paginas_oficio,
            'paginas_anexo_ii': paginas_anexo,
            'paginas_processamento': paginas_proc,
            'status': '✅ OK' if discrepancia and not tem_discrepancia else ('⚠️ DISCREPÂNCIA' if tem_discrepancia else '❓ Desconhecido'),
            'tem_discrepancia': tem_discrepancia,
            **valores_processados,
            'valores_referencia': valores_referencia,
            'diferencas': diferencas
        }
        
        resultados.append(resultado)
    
    return resultados


def carregar_csv_referencia(csv_file: Path) -> pd.DataFrame:
    """Carrega CSV de referência"""
    df = pd.read_csv(csv_file)
    return df


def gerar_tabela_completa(resultados: List[Dict], df_ref: pd.DataFrame) -> pd.DataFrame:
    """Gera tabela completa com todos os dados"""
    
    linhas = []
    
    for res in resultados:
        cpf = res['cpf']
        processo = res['processo']
        
        # Buscar valores de referência no CSV
        ref_row = df_ref[
            (df_ref['cpf'].astype(str) == cpf) & 
            (df_ref['numero_processo_cnj'] == processo)
        ]
        
        if not ref_row.empty:
            ref_data = ref_row.iloc[0]
            
            # Função para limpar valores do CSV
            def limpar_valor(val):
                if pd.isna(val) or val == '-':
                    return None
                val_str = str(val).replace('R$', '').replace(' ', '').replace(',', '')
                try:
                    return float(val_str)
                except:
                    return None
            
            vlr_proc_liq = res.get('valor_principal_liquido')
            vlr_proc_bruto = res.get('valor_principal_bruto')
            vlr_proc_juros = res.get('juros_moratorios')
            vlr_proc_total = res.get('valor_total_requisitado')
            
            vlr_ref_liq = limpar_valor(ref_data.get('valor_principal_liquido'))
            vlr_ref_bruto = limpar_valor(ref_data.get('valor_principal_bruto'))
            vlr_ref_juros = limpar_valor(ref_data.get('juros_moratorios'))
            vlr_ref_total = limpar_valor(ref_data.get('valor_total_requisitado'))
            
            # Calcular diferenças
            def calc_diff(proc, ref):
                if proc is None or ref is None:
                    return None, None
                diff = abs(proc - ref)
                perc = (diff / ref * 100) if ref > 0 else 0
                return diff, perc
            
            diff_liq, perc_liq = calc_diff(vlr_proc_liq, vlr_ref_liq)
            diff_bruto, perc_bruto = calc_diff(vlr_proc_bruto, vlr_ref_bruto)
            diff_juros, perc_juros = calc_diff(vlr_proc_juros, vlr_ref_juros)
            diff_total, perc_total = calc_diff(vlr_proc_total, vlr_ref_total)
            
            # Determinar status
            max_diff_perc = 0
            if perc_liq: max_diff_perc = max(max_diff_perc, perc_liq)
            if perc_bruto: max_diff_perc = max(max_diff_perc, perc_bruto)
            if perc_total: max_diff_perc = max(max_diff_perc, perc_total)
            
            if max_diff_perc == 0:
                status = '✅ PERFEITO'
            elif max_diff_perc < 0.01:
                status = '✅ OK (<0.01%)'
            elif max_diff_perc < 0.5:
                status = '🟡 BAIXO (<0.5%)'
            elif max_diff_perc < 5:
                status = '🟠 MÉDIO (<5%)'
            else:
                status = '🔴 CRÍTICO (≥5%)'
            
            linha = {
                'indice': res['indice'],
                'cpf': cpf,
                'cpf_formatado': f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}",
                'processo': processo,
                'status': status,
                'max_diferenca_percentual': f"{max_diff_perc:.2f}%" if max_diff_perc else "0%",
                
                # Valor Principal Líquido
                'vlr_proc_liquido': f"R$ {vlr_proc_liq:,.2f}" if vlr_proc_liq else "-",
                'vlr_ref_liquido': f"R$ {vlr_ref_liq:,.2f}" if vlr_ref_liq else "-",
                'diff_liquido': f"R$ {diff_liq:,.2f}" if diff_liq else "-",
                'diff_liquido_perc': f"{perc_liq:.2f}%" if perc_liq else "-",
                
                # Valor Principal Bruto
                'vlr_proc_bruto': f"R$ {vlr_proc_bruto:,.2f}" if vlr_proc_bruto else "-",
                'vlr_ref_bruto': f"R$ {vlr_ref_bruto:,.2f}" if vlr_ref_bruto else "-",
                'diff_bruto': f"R$ {diff_bruto:,.2f}" if diff_bruto else "-",
                'diff_bruto_perc': f"{perc_bruto:.2f}%" if perc_bruto else "-",
                
                # Juros Moratórios
                'vlr_proc_juros': f"R$ {vlr_proc_juros:,.2f}" if vlr_proc_juros else "-",
                'vlr_ref_juros': f"R$ {vlr_ref_juros:,.2f}" if vlr_ref_juros else "-",
                'diff_juros': f"R$ {diff_juros:,.2f}" if diff_juros else "-",
                'diff_juros_perc': f"{perc_juros:.2f}%" if perc_juros else "-",
                
                # Valor Total Requisitado
                'vlr_proc_total': f"R$ {vlr_proc_total:,.2f}" if vlr_proc_total else "-",
                'vlr_ref_total': f"R$ {vlr_ref_total:,.2f}" if vlr_ref_total else "-",
                'diff_total': f"R$ {diff_total:,.2f}" if diff_total else "-",
                'diff_total_perc': f"{perc_total:.2f}%" if perc_total else "-",
                
                # Páginas
                'paginas_oficio': res['paginas_oficio'],
                'paginas_anexo_ii': res['paginas_anexo_ii'],
                'paginas_processamento': res['paginas_processamento'],
                
                # Path
                'pdf_path': res['pdf_path'],
                'pdf_path_absoluto': f"/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/{res['pdf_path']}"
            }
            
            linhas.append(linha)
        else:
            # Não encontrado no CSV de referência
            linha = {
                'indice': res['indice'],
                'cpf': cpf,
                'cpf_formatado': f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}",
                'processo': processo,
                'status': '⚪ NÃO ENCONTRADO NO CSV',
                'max_diferenca_percentual': 'N/A',
                'vlr_proc_liquido': f"R$ {res.get('valor_principal_liquido', 0):,.2f}" if res.get('valor_principal_liquido') else "-",
                'vlr_ref_liquido': 'N/A',
                'diff_liquido': 'N/A',
                'diff_liquido_perc': 'N/A',
                'vlr_proc_bruto': f"R$ {res.get('valor_principal_bruto', 0):,.2f}" if res.get('valor_principal_bruto') else "-",
                'vlr_ref_bruto': 'N/A',
                'diff_bruto': 'N/A',
                'diff_bruto_perc': 'N/A',
                'vlr_proc_juros': f"R$ {res.get('juros_moratorios', 0):,.2f}" if res.get('juros_moratorios') else "-",
                'vlr_ref_juros': 'N/A',
                'diff_juros': 'N/A',
                'diff_juros_perc': 'N/A',
                'vlr_proc_total': f"R$ {res.get('valor_total_requisitado', 0):,.2f}" if res.get('valor_total_requisitado') else "-",
                'vlr_ref_total': 'N/A',
                'diff_total': 'N/A',
                'diff_total_perc': 'N/A',
                'paginas_oficio': res['paginas_oficio'],
                'paginas_anexo_ii': res['paginas_anexo_ii'],
                'paginas_processamento': res['paginas_processamento'],
                'pdf_path': res['pdf_path'],
                'pdf_path_absoluto': f"/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/{res['pdf_path']}"
            }
            
            linhas.append(linha)
    
    return pd.DataFrame(linhas)


def gerar_markdown(df: pd.DataFrame, output_file: Path):
    """Gera tabela em Markdown"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 📊 Tabela de Análise Completa - Validação OCR\n\n")
        f.write(f"**Data de Geração:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(f"**Total de Processos Analisados:** {len(df)}\n\n")
        
        # Estatísticas
        status_counts = df['status'].value_counts()
        f.write("## 📈 Resumo por Status\n\n")
        for status, count in status_counts.items():
            f.write(f"- **{status}:** {count} processos\n")
        f.write("\n---\n\n")
        
        # Tabela principal - Valor Total Requisitado
        f.write("## 💰 Análise: Valor Total Requisitado\n\n")
        f.write("| # | CPF | Processo | Status | Processado | Esperado (CSV) | Diferença | % | Páginas Ofício | PDF |\n")
        f.write("|---|-----|----------|--------|-----------|----------------|-----------|---|----------------|-----|\n")
        
        for _, row in df.iterrows():
            cpf_mask = f"{row['cpf_formatado'][:7]}***-**"
            processo_short = row['processo'][:20] + "..." if len(row['processo']) > 20 else row['processo']
            
            f.write(f"| {row['indice']} ")
            f.write(f"| {cpf_mask} ")
            f.write(f"| `{processo_short}` ")
            f.write(f"| {row['status']} ")
            f.write(f"| {row['vlr_proc_total']} ")
            f.write(f"| {row['vlr_ref_total']} ")
            f.write(f"| {row['diff_total']} ")
            f.write(f"| {row['diff_total_perc']} ")
            f.write(f"| {row['paginas_oficio'][:30]}... " if len(row['paginas_oficio']) > 30 else f"| {row['paginas_oficio']} ")
            f.write(f"| [`PDF`]({row['pdf_path']}) |\n")
        
        f.write("\n---\n\n")
        
        # Tabela detalhada - Todos os valores
        f.write("## 📋 Análise Detalhada - Todos os Campos\n\n")
        
        for _, row in df.iterrows():
            f.write(f"### Processo {row['indice']}: {row['processo']}\n\n")
            f.write(f"**CPF:** {row['cpf_formatado']} | **Status:** {row['status']}\n\n")
            
            f.write("| Campo | Processado | Esperado (CSV) | Diferença | % |\n")
            f.write("|-------|-----------|----------------|-----------|---|\n")
            f.write(f"| Valor Principal Líquido | {row['vlr_proc_liquido']} | {row['vlr_ref_liquido']} | {row['diff_liquido']} | {row['diff_liquido_perc']} |\n")
            f.write(f"| Valor Principal Bruto | {row['vlr_proc_bruto']} | {row['vlr_ref_bruto']} | {row['diff_bruto']} | {row['diff_bruto_perc']} |\n")
            f.write(f"| Juros Moratórios | {row['vlr_proc_juros']} | {row['vlr_ref_juros']} | {row['diff_juros']} | {row['diff_juros_perc']} |\n")
            f.write(f"| **Valor Total Requisitado** | **{row['vlr_proc_total']}** | **{row['vlr_ref_total']}** | **{row['diff_total']}** | **{row['diff_total_perc']}** |\n")
            
            f.write(f"\n**Páginas:**\n")
            f.write(f"- Ofício: `{row['paginas_oficio']}`\n")
            f.write(f"- ANEXO II: `{row['paginas_anexo_ii']}`\n")
            f.write(f"- Processamento: `{row['paginas_processamento']}`\n")
            
            f.write(f"\n**PDF:** `{row['pdf_path']}`\n\n")
            f.write("---\n\n")


def main():
    """Função principal"""
    print("=" * 80)
    print("GERADOR DE TABELA DE ANÁLISE DETALHADA")
    print("=" * 80)
    
    # 1. Extrair dados do log
    print("\n1. Extraindo dados do log de validação...")
    resultados = extrair_dados_log(LOG_FILE)
    print(f"   ✓ {len(resultados)} processos extraídos do log")
    
    # 2. Carregar CSV de referência
    print("\n2. Carregando CSV de referência...")
    df_ref = carregar_csv_referencia(CSV_REF)
    print(f"   ✓ {len(df_ref)} registros carregados")
    
    # 3. Gerar tabela completa
    print("\n3. Gerando tabela completa...")
    df_analise = gerar_tabela_completa(resultados, df_ref)
    print(f"   ✓ Tabela gerada com {len(df_analise)} linhas")
    
    # 4. Salvar CSV
    print(f"\n4. Salvando CSV: {OUTPUT_CSV}")
    df_analise.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print("   ✓ CSV salvo")
    
    # 5. Gerar Markdown
    print(f"\n5. Gerando Markdown: {OUTPUT_MD}")
    gerar_markdown(df_analise, OUTPUT_MD)
    print("   ✓ Markdown gerado")
    
    # 6. Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    print(f"Total de processos analisados: {len(df_analise)}")
    print("\nDistribuição por status:")
    for status, count in df_analise['status'].value_counts().items():
        print(f"  {status}: {count}")
    
    print("\n" + "=" * 80)
    print("ARQUIVOS GERADOS")
    print("=" * 80)
    print(f"✓ CSV: {OUTPUT_CSV}")
    print(f"✓ Markdown: {OUTPUT_MD}")
    print("\n✅ Processo concluído com sucesso!")


if __name__ == "__main__":
    main()

