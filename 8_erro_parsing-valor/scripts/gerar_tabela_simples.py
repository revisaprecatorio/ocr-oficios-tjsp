#!/usr/bin/env python3
"""
Script simplificado para gerar tabela de análise
=================================================
Usa o CSV de referência e adiciona informações extraídas do log.
"""

import re
import pandas as pd
from pathlib import Path

# Caminhos
LOG_FILE = Path(__file__).parent.parent / "test_data" / "validacao_output.log"
CSV_REF = Path(__file__).parent.parent / "test_data" / "2025-10-31T23-26_export.csv"
OUTPUT_CSV = Path(__file__).parent.parent / "test_data" / "analise_detalhada.csv"
OUTPUT_MD = Path(__file__).parent.parent / "docs" / "TABELA_ANALISE_COMPLETA.md"


def extrair_processos_do_log(log_file: Path):
    """Extrai lista de CPFs e processos que foram processados do log"""
    
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Padrão mais simples (sem .pdf)
    pattern = r'Processando: (\d+)/([\d\-\.]+)'
    matches = re.findall(pattern, log_content)
    
    processos_log = {}
    for cpf, processo in matches:
        key = f"{cpf}_{processo}"
        processos_log[key] = {'cpf': cpf, 'processo': processo}
        
        # Buscar páginas enviadas para este processo
        pattern_paginas = rf'Processando: {cpf}/{processo}.*?Páginas enviadas: Ofício \[([\d, ]+)\].*?ANEXO II \[([\d, ]*)\].*?PROC \[([\d, ]*)\]'
        match_paginas = re.search(pattern_paginas, log_content, re.DOTALL)
        
        if match_paginas:
            processos_log[key]['paginas_oficio'] = match_paginas.group(1)
            processos_log[key]['paginas_anexo_ii'] = match_paginas.group(2) if match_paginas.group(2) else 'N/A'
            processos_log[key]['paginas_processamento'] = match_paginas.group(3) if match_paginas.group(3) else 'N/A'
        else:
            processos_log[key]['paginas_oficio'] = 'N/A'
            processos_log[key]['paginas_anexo_ii'] = 'N/A'
            processos_log[key]['paginas_processamento'] = 'N/A'
    
    return processos_log


def limpar_valor(val):
    """Limpa e converte valor monetário"""
    if pd.isna(val) or val == '-' or val == '':
        return None
    val_str = str(val).replace('R$', '').replace(' ', '').replace(',', '').replace('"', '')
    try:
        return float(val_str)
    except:
        return None


def main():
    print("=" * 80)
    print("GERADOR DE TABELA DE ANÁLISE DETALHADA")
    print("=" * 80)
    
    # 1. Carregar CSV de referência
    print("\n1. Carregando CSV de referência...")
    df_ref = pd.read_csv(CSV_REF)
    print(f"   ✓ {len(df_ref)} registros carregados")
    
    # 2. Extrair processos do log
    print("\n2. Extraindo processos do log...")
    processos_log = extrair_processos_do_log(LOG_FILE)
    print(f"   ✓ {len(processos_log)} processos encontrados no log")
    
    # 3. Criar tabela de análise
    print("\n3. Gerando tabela de análise...")
    
    linhas = []
    indice = 1
    
    for _, row in df_ref.iterrows():
        cpf = str(row['cpf'])
        processo = row['numero_processo_cnj']
        key = f"{cpf}_{processo}"
        
        # Verificar se foi processado
        foi_processado = key in processos_log
        
        if foi_processado:
            info_log = processos_log[key]
            paginas_oficio = info_log.get('paginas_oficio', 'N/A')
            paginas_anexo = info_log.get('paginas_anexo_ii', 'N/A')
            paginas_proc = info_log.get('paginas_processamento', 'N/A')
        else:
            paginas_oficio = 'Não processado'
            paginas_anexo = 'Não processado'
            paginas_proc = 'Não processado'
        
        # Extrair valores do CSV
        vlr_liq = limpar_valor(row.get('valor_principal_liquido'))
        vlr_bruto = limpar_valor(row.get('valor_principal_bruto'))
        vlr_juros = limpar_valor(row.get('juros_moratorios'))
        vlr_total = limpar_valor(row.get('valor_total_requisitado'))
        
        # Formatar CPF
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        
        # Path do PDF
        pdf_path = f"data/consultas/{cpf}/{processo}.pdf"
        pdf_path_abs = f"/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/{pdf_path}"
        
        linha = {
            'indice': indice if foi_processado else '-',
            'cpf': cpf,
            'cpf_formatado': cpf_fmt,
            'processo': processo,
            'requerente': row.get('requerente_caps', '-'),
            'foi_processado': '✅ Sim' if foi_processado else '❌ Não',
            
            # Valores (sempre do CSV - que é esperado)
            'vlr_principal_liquido': f"R$ {vlr_liq:,.2f}" if vlr_liq else '-',
            'vlr_principal_bruto': f"R$ {vlr_bruto:,.2f}" if vlr_bruto else '-',
            'vlr_juros_moratorios': f"R$ {vlr_juros:,.2f}" if vlr_juros else '-',
            'vlr_total_requisitado': f"R$ {vlr_total:,.2f}" if vlr_total else '-',
            
            # Páginas
            'paginas_oficio': paginas_oficio,
            'paginas_anexo_ii': paginas_anexo,
            'paginas_processamento': paginas_proc,
            
            # Path
            'pdf_path_relativo': pdf_path,
            'pdf_path_absoluto': pdf_path_abs,
            
            # Observações
            'rejeitado': 'Sim' if row.get('rejeitado', False) else 'Não',
            'motivo_rejeicao': row.get('motivo_rejeicao', '-') if row.get('motivo_rejeicao') else '-'
        }
        
        linhas.append(linha)
        if foi_processado:
            indice += 1
    
    df_analise = pd.DataFrame(linhas)
    
    # 4. Salvar CSV
    print(f"\n4. Salvando CSV: {OUTPUT_CSV}")
    df_analise.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print("   ✓ CSV salvo")
    
    # 5. Gerar Markdown
    print(f"\n5. Gerando Markdown: {OUTPUT_MD}")
    
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("# 📊 Tabela de Análise Completa - Validação OCR\n\n")
        f.write(f"**Data de Geração:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(f"**Total de Processos no CSV:** {len(df_analise)}\n")
        f.write(f"**Processos Validados:** {df_analise['foi_processado'].value_counts().get('✅ Sim', 0)}\n")
        f.write(f"**Processos Pendentes:** {df_analise['foi_processado'].value_counts().get('❌ Não', 0)}\n\n")
        
        f.write("---\n\n")
        
        # Tabela principal - Processos processados
        f.write("## ✅ Processos Validados (do Log)\n\n")
        
        df_processados = df_analise[df_analise['foi_processado'] == '✅ Sim']
        
        if len(df_processados) > 0:
            f.write("| # | CPF | Processo | Requerente | Valor Total | Páginas Ofício | PDF |\n")
            f.write("|---|-----|----------|------------|-------------|----------------|-----|\n")
            
            for _, row in df_processados.iterrows():
                cpf_mask = f"{row['cpf_formatado'][:7]}***-**"
                requerente_short = (row['requerente'][:30] + "...") if len(str(row['requerente'])) > 30 else row['requerente']
                processo_short = row['processo'][:25]
                
                f.write(f"| {row['indice']} ")
                f.write(f"| {cpf_mask} ")
                f.write(f"| `{processo_short}` ")
                f.write(f"| {requerente_short} ")
                f.write(f"| **{row['vlr_total_requisitado']}** ")
                f.write(f"| `{row['paginas_oficio'][:30]}{'...' if len(row['paginas_oficio']) > 30 else ''}` ")
                f.write(f"| [`🔗`]({row['pdf_path_relativo']}) |\n")
            
            f.write("\n---\n\n")
            
            # Detalhes completos
            f.write("## 📋 Detalhes Completos dos Processos Validados\n\n")
            
            for _, row in df_processados.iterrows():
                f.write(f"### [{row['indice']}] {row['processo']}\n\n")
                f.write(f"- **CPF:** {row['cpf_formatado']}\n")
                f.write(f"- **Requerente:** {row['requerente']}\n")
                f.write(f"- **Rejeitado:** {row['rejeitado']}\n")
                if row['motivo_rejeicao'] != '-':
                    f.write(f"- **Motivo Rejeição:** {row['motivo_rejeicao']}\n")
                f.write("\n")
                
                f.write("**Valores Monetários:**\n\n")
                f.write("| Campo | Valor (CSV) |\n")
                f.write("|-------|-------------|\n")
                f.write(f"| Valor Principal Líquido | {row['vlr_principal_liquido']} |\n")
                f.write(f"| Valor Principal Bruto | {row['vlr_principal_bruto']} |\n")
                f.write(f"| Juros Moratórios | {row['vlr_juros_moratorios']} |\n")
                f.write(f"| **Valor Total Requisitado** | **{row['vlr_total_requisitado']}** |\n")
                f.write("\n")
                
                f.write("**Localização no PDF:**\n\n")
                f.write(f"- Páginas do Ofício: `{row['paginas_oficio']}`\n")
                f.write(f"- Páginas do ANEXO II: `{row['paginas_anexo_ii']}`\n")
                f.write(f"- Páginas do PROCESSAMENTO: `{row['paginas_processamento']}`\n")
                f.write("\n")
                
                f.write(f"**Path do PDF:**\n")
                f.write(f"```\n{row['pdf_path_absoluto']}\n```\n\n")
                
                f.write("---\n\n")
        else:
            f.write("*Nenhum processo foi validado ainda.*\n\n")
        
        # Processos pendentes
        df_pendentes = df_analise[df_analise['foi_processado'] == '❌ Não']
        
        if len(df_pendentes) > 0:
            f.write(f"## ⏳ Processos Pendentes de Validação ({len(df_pendentes)})\n\n")
            
            f.write("| CPF | Processo | Requerente | Valor Total | PDF |\n")
            f.write("|-----|----------|------------|-------------|-----|\n")
            
            for _, row in df_pendentes.iterrows():
                cpf_mask = f"{row['cpf_formatado'][:7]}***-**"
                requerente_short = (row['requerente'][:30] + "...") if len(str(row['requerente'])) > 30 else row['requerente']
                
                f.write(f"| {cpf_mask} ")
                f.write(f"| `{row['processo'][:25]}` ")
                f.write(f"| {requerente_short} ")
                f.write(f"| {row['vlr_total_requisitado']} ")
                f.write(f"| [`🔗`]({row['pdf_path_relativo']}) |\n")
    
    print("   ✓ Markdown gerado")
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO")
    print("=" * 80)
    print(f"Total de processos no CSV: {len(df_analise)}")
    print(f"Processos validados: {len(df_processados)}")
    print(f"Processos pendentes: {len(df_pendentes)}")
    
    print("\n" + "=" * 80)
    print("ARQUIVOS GERADOS")
    print("=" * 80)
    print(f"✓ CSV: {OUTPUT_CSV}")
    print(f"✓ Markdown: {OUTPUT_MD}")
    print("\n✅ Processo concluído com sucesso!")


if __name__ == "__main__":
    main()

