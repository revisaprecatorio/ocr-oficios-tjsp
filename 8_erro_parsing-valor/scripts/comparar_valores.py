#!/usr/bin/env python3
"""
Script para comparar valores processados vs esperados (CSV)
============================================================
Extrai valores do log de validação e compara com CSV de referência.
Identifica discrepâncias e gera relatório detalhado.
"""

import re
import pandas as pd
from pathlib import Path
from decimal import Decimal
from typing import Dict, List, Optional

# Caminhos
LOG_FILE = Path(__file__).parent.parent / "test_data" / "validacao_output.log"
CSV_REF = Path(__file__).parent.parent / "test_data" / "2025-10-31T23-26_export.csv"
OUTPUT_CSV = Path(__file__).parent.parent / "test_data" / "comparacao_valores.csv"
OUTPUT_MD = Path(__file__).parent.parent / "docs" / "TABELA_COMPARACAO_VALORES.md"


def extrair_valores_processados(log_file: Path) -> Dict:
    """Extrai valores processados de cada PDF do log"""
    
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Dividir log por processamentos
    pattern_processo = r'Processando: (\d+)/([\d\-\.]+)(.*?)(?=Processando:|$)'
    matches = re.finditer(pattern_processo, log_content, re.DOTALL)
    
    resultados = {}
    
    for match in matches:
        cpf = match.group(1)
        processo = match.group(2)
        bloco = match.group(3)
        
        key = f"{cpf}_{processo}"
        
        # Extrair valores do JSON retornado pelo LLM
        valores = {}
        
        # Padrão para valores no formato: 'campo': Decimal('valor')
        pattern_decimal = r"'([\w_]+)':\s*Decimal\('([\d.]+)'\)"
        
        for campo_match in re.finditer(pattern_decimal, bloco):
            campo = campo_match.group(1)
            valor = float(campo_match.group(2))
            
            if campo in ['valor_principal_liquido', 'valor_principal_bruto', 
                        'juros_moratorios', 'valor_total_requisitado']:
                valores[campo] = valor
        
        # Se não encontrou valores no formato Decimal, tentar formato JSON
        if not valores:
            pattern_json = r'"([\w_]+)":\s*(\d+\.?\d*)'
            
            for campo_match in re.finditer(pattern_json, bloco):
                campo = campo_match.group(1)
                valor_str = campo_match.group(2)
                
                if campo in ['valor_principal_liquido', 'valor_principal_bruto', 
                            'juros_moratorios', 'valor_total_requisitado']:
                    try:
                        valores[campo] = float(valor_str)
                    except:
                        pass
        
        # Extrair páginas
        pattern_paginas = r'Páginas enviadas: Ofício \[([\d, ]+)\].*?ANEXO II \[([\d, ]*)\].*?PROC \[([\d, ]*)\]'
        match_paginas = re.search(pattern_paginas, bloco)
        
        if match_paginas:
            paginas_oficio = match_paginas.group(1)
            paginas_anexo = match_paginas.group(2) if match_paginas.group(2) else 'N/A'
            paginas_proc = match_paginas.group(3) if match_paginas.group(3) else 'N/A'
        else:
            paginas_oficio = 'N/A'
            paginas_anexo = 'N/A'
            paginas_proc = 'N/A'
        
        # Verificar se houve discrepância no log
        tem_discrepancia = 'DISCREPÂNCIA ENCONTRADA' in bloco
        
        # Se teve discrepância, extrair valores de referência também
        valores_ref = {}
        if tem_discrepancia:
            pattern_disc = r'• ([\w_]+):\n\s+Processado: R\$ ([\d,\.]+)\n\s+Referência: R\$ ([\d,\.]+)'
            
            for disc_match in re.finditer(pattern_disc, bloco):
                campo = disc_match.group(1)
                valor_proc = float(disc_match.group(2).replace(',', ''))
                valor_ref = float(disc_match.group(3).replace(',', ''))
                
                valores[campo] = valor_proc
                valores_ref[campo] = valor_ref
        
        resultados[key] = {
            'cpf': cpf,
            'processo': processo,
            'valores_processados': valores,
            'valores_referencia_log': valores_ref,
            'paginas_oficio': paginas_oficio,
            'paginas_anexo_ii': paginas_anexo,
            'paginas_processamento': paginas_proc,
            'tem_discrepancia': tem_discrepancia
        }
    
    return resultados


def limpar_valor_csv(val):
    """Limpa e converte valor monetário do CSV"""
    if pd.isna(val) or val == '-' or val == '':
        return None
    val_str = str(val).replace('R$', '').replace(' ', '').replace(',', '').replace('"', '')
    try:
        return float(val_str)
    except:
        return None


def calcular_diferenca(processado: Optional[float], esperado: Optional[float]) -> tuple:
    """Calcula diferença absoluta e percentual"""
    if processado is None or esperado is None:
        return None, None
    
    diff = abs(processado - esperado)
    perc = (diff / esperado * 100) if esperado > 0 else 0
    
    return diff, perc


def classificar_severidade(perc_diff: Optional[float]) -> str:
    """Classifica severidade da discrepância"""
    if perc_diff is None:
        return '⚪ N/A'
    elif perc_diff < 0.01:
        return '✅ PERFEITO'
    elif perc_diff < 0.5:
        return '🟢 BAIXO'
    elif perc_diff < 5:
        return '🟡 MÉDIO'
    else:
        return '🔴 CRÍTICO'


def main():
    print("=" * 80)
    print("COMPARAÇÃO: VALORES PROCESSADOS VS ESPERADOS")
    print("=" * 80)
    
    # 1. Extrair valores processados do log
    print("\n1. Extraindo valores processados do log...")
    valores_processados = extrair_valores_processados(LOG_FILE)
    print(f"   ✓ {len(valores_processados)} processos encontrados")
    
    # 2. Carregar CSV de referência
    print("\n2. Carregando CSV de referência...")
    df_ref = pd.read_csv(CSV_REF)
    print(f"   ✓ {len(df_ref)} registros carregados")
    
    # 3. Comparar valores
    print("\n3. Comparando valores...")
    
    linhas = []
    
    for key, data in valores_processados.items():
        cpf = data['cpf']
        processo = data['processo']
        
        # Buscar no CSV de referência
        ref_row = df_ref[
            (df_ref['cpf'].astype(str) == cpf) & 
            (df_ref['numero_processo_cnj'] == processo)
        ]
        
        if ref_row.empty:
            print(f"   ⚠️  Processo {processo} não encontrado no CSV")
            continue
        
        ref_data = ref_row.iloc[0]
        
        # Extrair valores processados
        vals_proc = data['valores_processados']
        
        vlr_proc_liq = vals_proc.get('valor_principal_liquido')
        vlr_proc_bruto = vals_proc.get('valor_principal_bruto')
        vlr_proc_juros = vals_proc.get('juros_moratorios')
        vlr_proc_total = vals_proc.get('valor_total_requisitado')
        
        # Extrair valores esperados (CSV)
        vlr_esp_liq = limpar_valor_csv(ref_data.get('valor_principal_liquido'))
        vlr_esp_bruto = limpar_valor_csv(ref_data.get('valor_principal_bruto'))
        vlr_esp_juros = limpar_valor_csv(ref_data.get('juros_moratorios'))
        vlr_esp_total = limpar_valor_csv(ref_data.get('valor_total_requisitado'))
        
        # Calcular diferenças
        diff_liq, perc_liq = calcular_diferenca(vlr_proc_liq, vlr_esp_liq)
        diff_bruto, perc_bruto = calcular_diferenca(vlr_proc_bruto, vlr_esp_bruto)
        diff_juros, perc_juros = calcular_diferenca(vlr_proc_juros, vlr_esp_juros)
        diff_total, perc_total = calcular_diferenca(vlr_proc_total, vlr_esp_total)
        
        # Determinar maior discrepância
        max_perc = 0
        campo_critico = None
        
        for campo, perc in [
            ('valor_principal_liquido', perc_liq),
            ('valor_principal_bruto', perc_bruto),
            ('juros_moratorios', perc_juros),
            ('valor_total_requisitado', perc_total)
        ]:
            if perc and perc > max_perc:
                max_perc = perc
                campo_critico = campo
        
        severidade = classificar_severidade(max_perc)
        
        # CPF formatado
        cpf_fmt = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        
        linha = {
            'cpf': cpf,
            'cpf_formatado': cpf_fmt,
            'processo': processo,
            'requerente': ref_data.get('requerente_caps', '-'),
            'severidade': severidade,
            'max_discrepancia_perc': f"{max_perc:.4f}%" if max_perc else "0%",
            'campo_critico': campo_critico if campo_critico else '-',
            
            # Valor Principal Líquido
            'vlr_proc_liquido': vlr_proc_liq,
            'vlr_esp_liquido': vlr_esp_liq,
            'diff_liquido': diff_liq,
            'diff_liquido_perc': perc_liq,
            
            # Valor Principal Bruto
            'vlr_proc_bruto': vlr_proc_bruto,
            'vlr_esp_bruto': vlr_esp_bruto,
            'diff_bruto': diff_bruto,
            'diff_bruto_perc': perc_bruto,
            
            # Juros Moratórios
            'vlr_proc_juros': vlr_proc_juros,
            'vlr_esp_juros': vlr_esp_juros,
            'diff_juros': diff_juros,
            'diff_juros_perc': perc_juros,
            
            # Valor Total Requisitado
            'vlr_proc_total': vlr_proc_total,
            'vlr_esp_total': vlr_esp_total,
            'diff_total': diff_total,
            'diff_total_perc': perc_total,
            
            # Páginas
            'paginas_oficio': data['paginas_oficio'],
            'paginas_anexo_ii': data['paginas_anexo_ii'],
            'paginas_processamento': data['paginas_processamento'],
            
            # Path
            'pdf_path': f"data/consultas/{cpf}/{processo}.pdf"
        }
        
        linhas.append(linha)
    
    df_comparacao = pd.DataFrame(linhas)
    
    # Ordenar por severidade (críticos primeiro)
    ordem_severidade = {'🔴 CRÍTICO': 0, '🟡 MÉDIO': 1, '🟢 BAIXO': 2, '✅ PERFEITO': 3, '⚪ N/A': 4}
    df_comparacao['ordem'] = df_comparacao['severidade'].map(ordem_severidade)
    df_comparacao = df_comparacao.sort_values('ordem').drop('ordem', axis=1)
    
    # 4. Salvar CSV
    print(f"\n4. Salvando CSV: {OUTPUT_CSV}")
    df_comparacao.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print("   ✓ CSV salvo")
    
    # 5. Gerar Markdown
    print(f"\n5. Gerando Markdown: {OUTPUT_MD}")
    
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write("# 📊 Comparação: Valores Processados vs Esperados\n\n")
        f.write(f"**Data de Geração:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        f.write(f"**Total de Processos Comparados:** {len(df_comparacao)}\n\n")
        
        # Estatísticas por severidade
        severidade_counts = df_comparacao['severidade'].value_counts()
        
        f.write("## 📈 Resumo por Severidade\n\n")
        f.write("| Severidade | Quantidade | % |\n")
        f.write("|-----------|------------|---|\n")
        
        for sev in ['🔴 CRÍTICO', '🟡 MÉDIO', '🟢 BAIXO', '✅ PERFEITO', '⚪ N/A']:
            count = severidade_counts.get(sev, 0)
            perc = (count / len(df_comparacao) * 100) if len(df_comparacao) > 0 else 0
            f.write(f"| {sev} | {count} | {perc:.1f}% |\n")
        
        f.write("\n---\n\n")
        
        # Tabela resumida
        f.write("## 💰 Comparação: Valor Total Requisitado\n\n")
        f.write("| CPF | Processo | Severidade | Processado | Esperado | Diferença | % | Páginas |\n")
        f.write("|-----|----------|-----------|-----------|----------|-----------|---|----------|\n")
        
        for _, row in df_comparacao.iterrows():
            cpf_mask = f"{row['cpf_formatado'][:7]}***-**"
            proc_short = row['processo'][:25]
            
            vlr_proc = f"R$ {row['vlr_proc_total']:,.2f}" if row['vlr_proc_total'] else '-'
            vlr_esp = f"R$ {row['vlr_esp_total']:,.2f}" if row['vlr_esp_total'] else '-'
            diff = f"R$ {row['diff_total']:,.2f}" if row['diff_total'] else '-'
            perc = f"{row['diff_total_perc']:.2f}%" if row['diff_total_perc'] else '-'
            
            f.write(f"| {cpf_mask} ")
            f.write(f"| `{proc_short}` ")
            f.write(f"| {row['severidade']} ")
            f.write(f"| {vlr_proc} ")
            f.write(f"| {vlr_esp} ")
            f.write(f"| {diff} ")
            f.write(f"| {perc} ")
            f.write(f"| `{row['paginas_oficio'][:20]}...` " if len(row['paginas_oficio']) > 20 else f"| `{row['paginas_oficio']}` ")
            f.write("|\n")
        
        f.write("\n---\n\n")
        
        # Detalhes completos
        f.write("## 📋 Detalhes Completos por Processo\n\n")
        
        for idx, row in df_comparacao.iterrows():
            f.write(f"### {row['processo']} - {row['severidade']}\n\n")
            f.write(f"**CPF:** {row['cpf_formatado']}  \n")
            f.write(f"**Requerente:** {row['requerente']}  \n")
            
            if row['campo_critico'] != '-':
                f.write(f"**⚠️ Campo Crítico:** `{row['campo_critico']}` ({row['max_discrepancia_perc']})\n")
            
            f.write("\n")
            
            f.write("#### Comparação de Todos os Valores\n\n")
            f.write("| Campo | Processado | Esperado (CSV) | Diferença | % | Status |\n")
            f.write("|-------|-----------|----------------|-----------|---|--------|\n")
            
            # Líquido
            vlr_proc_liq = f"R$ {row['vlr_proc_liquido']:,.2f}" if row['vlr_proc_liquido'] else '-'
            vlr_esp_liq = f"R$ {row['vlr_esp_liquido']:,.2f}" if row['vlr_esp_liquido'] else '-'
            diff_liq = f"R$ {row['diff_liquido']:,.2f}" if row['diff_liquido'] else '-'
            perc_liq = f"{row['diff_liquido_perc']:.4f}%" if row['diff_liquido_perc'] else '-'
            status_liq = classificar_severidade(row['diff_liquido_perc'])
            
            f.write(f"| Valor Principal Líquido | {vlr_proc_liq} | {vlr_esp_liq} | {diff_liq} | {perc_liq} | {status_liq} |\n")
            
            # Bruto
            vlr_proc_bruto = f"R$ {row['vlr_proc_bruto']:,.2f}" if row['vlr_proc_bruto'] else '-'
            vlr_esp_bruto = f"R$ {row['vlr_esp_bruto']:,.2f}" if row['vlr_esp_bruto'] else '-'
            diff_bruto = f"R$ {row['diff_bruto']:,.2f}" if row['diff_bruto'] else '-'
            perc_bruto = f"{row['diff_bruto_perc']:.4f}%" if row['diff_bruto_perc'] else '-'
            status_bruto = classificar_severidade(row['diff_bruto_perc'])
            
            f.write(f"| Valor Principal Bruto | {vlr_proc_bruto} | {vlr_esp_bruto} | {diff_bruto} | {perc_bruto} | {status_bruto} |\n")
            
            # Juros
            vlr_proc_juros = f"R$ {row['vlr_proc_juros']:,.2f}" if row['vlr_proc_juros'] else '-'
            vlr_esp_juros = f"R$ {row['vlr_esp_juros']:,.2f}" if row['vlr_esp_juros'] else '-'
            diff_juros = f"R$ {row['diff_juros']:,.2f}" if row['diff_juros'] else '-'
            perc_juros = f"{row['diff_juros_perc']:.4f}%" if row['diff_juros_perc'] else '-'
            status_juros = classificar_severidade(row['diff_juros_perc'])
            
            f.write(f"| Juros Moratórios | {vlr_proc_juros} | {vlr_esp_juros} | {diff_juros} | {perc_juros} | {status_juros} |\n")
            
            # Total
            vlr_proc_total = f"R$ {row['vlr_proc_total']:,.2f}" if row['vlr_proc_total'] else '-'
            vlr_esp_total = f"R$ {row['vlr_esp_total']:,.2f}" if row['vlr_esp_total'] else '-'
            diff_total = f"R$ {row['diff_total']:,.2f}" if row['diff_total'] else '-'
            perc_total = f"{row['diff_total_perc']:.4f}%" if row['diff_total_perc'] else '-'
            status_total = classificar_severidade(row['diff_total_perc'])
            
            f.write(f"| **Valor Total Requisitado** | **{vlr_proc_total}** | **{vlr_esp_total}** | **{diff_total}** | **{perc_total}** | **{status_total}** |\n")
            
            f.write("\n")
            f.write("**Localização no PDF:**\n\n")
            f.write(f"- Páginas do Ofício: `{row['paginas_oficio']}`\n")
            f.write(f"- Páginas do ANEXO II: `{row['paginas_anexo_ii']}`\n")
            f.write(f"- Páginas do PROCESSAMENTO: `{row['paginas_processamento']}`\n")
            f.write("\n")
            f.write(f"**PDF:** `{row['pdf_path']}`\n\n")
            f.write("---\n\n")
    
    print("   ✓ Markdown gerado")
    
    # 6. Resumo
    print("\n" + "=" * 80)
    print("RESUMO DA COMPARAÇÃO")
    print("=" * 80)
    print(f"Total de processos comparados: {len(df_comparacao)}")
    print("\nDistribuição por severidade:")
    for sev, count in severidade_counts.items():
        perc = (count / len(df_comparacao) * 100)
        print(f"  {sev}: {count} ({perc:.1f}%)")
    
    # Casos críticos
    criticos = df_comparacao[df_comparacao['severidade'] == '🔴 CRÍTICO']
    if len(criticos) > 0:
        print(f"\n⚠️  ATENÇÃO: {len(criticos)} caso(s) crítico(s) detectado(s)!")
        for _, row in criticos.iterrows():
            print(f"   - {row['processo']}: {row['max_discrepancia_perc']} no campo {row['campo_critico']}")
    
    print("\n" + "=" * 80)
    print("ARQUIVOS GERADOS")
    print("=" * 80)
    print(f"✓ CSV: {OUTPUT_CSV}")
    print(f"✓ Markdown: {OUTPUT_MD}")
    print("\n✅ Processo concluído com sucesso!")


if __name__ == "__main__":
    main()

