#!/usr/bin/env python3
"""
Script simplificado para comparar V3.0 com CSV usando dados do PostgreSQL.
"""

import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Caminhos
BASE_DIR = Path(__file__).parent.parent
CSV_REFERENCIA = BASE_DIR / "test_data" / "2025-10-31T23-26_export.csv"
OUTPUT_MD = BASE_DIR / "docs" / "COMPARACAO_V3_VS_CSV.md"
OUTPUT_CSV = BASE_DIR / "test_data" / "comparacao_v3.csv"

def conectar_db():
    """Conecta ao PostgreSQL"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def comparar_valores(v1: float, v2: float, tolerancia: float = 1.0) -> tuple:
    """Compara dois valores e retorna status"""
    if v1 is None or v2 is None:
        return ("N/A", None, None)
    
    diff_abs = abs(v1 - v2)
    diff_pct = (diff_abs / v2 * 100) if v2 != 0 else 0
    
    if diff_abs < tolerancia:
        return ("✅ PERFEITO", diff_abs, diff_pct)
    elif diff_pct < 1:
        return ("✅ ACEITÁVEL", diff_abs, diff_pct)
    elif diff_pct < 10:
        return ("⚠️ BAIXO", diff_abs, diff_pct)
    else:
        return ("❌ CRÍTICO", diff_abs, diff_pct)

def main():
    print("🔍 Comparando V3.0 (PostgreSQL) com CSV de Referência")
    print("=" * 80)
    print()
    
    # Carregar CSV de referência
    print("📄 Carregando CSV de referência...")
    df_csv = pd.read_csv(CSV_REFERENCIA)
    print(f"   ✅ {len(df_csv)} registros carregados")
    
    # Conectar ao PostgreSQL
    print("🔌 Conectando ao PostgreSQL...")
    conn = conectar_db()
    cursor = conn.cursor()
    print(f"   ✅ Conectado!")
    
    # Buscar dados do banco
    print("📊 Buscando dados processados...")
    query = """
    SELECT 
        cpf,
        processo_origem,
        valor_principal_liquido,
        valor_principal_bruto
    FROM lista_processos
    WHERE timestamp_ingestao >= CURRENT_DATE
    ORDER BY cpf, processo_origem
    """
    df_db = pd.read_sql_query(query, conn)
    print(f"   ✅ {len(df_db)} registros encontrados no banco")
    print()
    
    # Preparar dados para comparação
    comparacoes = []
    
    def parse_valor_csv(val):
        """Parse valor do CSV: 'R$ 78,384.27' -> 78384.27"""
        if pd.isna(val):
            return None
        val_str = str(val).replace('R$', '').replace(' ', '').strip()
        if not val_str or val_str in ['', 'null', 'None']:
            return None
        try:
            return float(val_str.replace(',', ''))
        except ValueError:
            return None
    
    for idx, row_csv in df_csv.iterrows():
        cpf_csv = str(row_csv['cpf']).replace('.', '').replace('-', '').zfill(11)
        processo_csv = str(row_csv['numero_processo_cnj'])
        
        # Buscar no DataFrame do banco
        row_db = df_db[(df_db['cpf'] == cpf_csv) & (df_db['processo_origem'] == processo_csv)]
        
        # Valores CSV (referência)
        csv_liquido = parse_valor_csv(row_csv['valor_principal_liquido'])
        csv_bruto = parse_valor_csv(row_csv['valor_principal_bruto'])
        
        # Valores V3.0 do banco
        if len(row_db) > 0:
            v3_liquido = float(row_db.iloc[0]['valor_principal_liquido']) if pd.notna(row_db.iloc[0]['valor_principal_liquido']) else None
            v3_bruto = float(row_db.iloc[0]['valor_principal_bruto']) if pd.notna(row_db.iloc[0]['valor_principal_bruto']) else None
        else:
            v3_liquido = None
            v3_bruto = None
        
        # Comparar
        status_liq, diff_liq_abs, diff_liq_pct = comparar_valores(v3_liquido, csv_liquido)
        status_bruto, diff_bruto_abs, diff_bruto_pct = comparar_valores(v3_bruto, csv_bruto)
        
        # Determinar status geral
        if status_liq == "✅ PERFEITO" and status_bruto == "✅ PERFEITO":
            status_geral = "✅ PERFEITO"
        elif status_liq in ["✅ PERFEITO", "✅ ACEITÁVEL"] and status_bruto in ["✅ PERFEITO", "✅ ACEITÁVEL"]:
            status_geral = "✅ ACEITÁVEL"
        elif "❌ CRÍTICO" in [status_liq, status_bruto]:
            status_geral = "❌ CRÍTICO"
        elif v3_liquido is None or v3_bruto is None:
            status_geral = "⚠️ NÃO PROCESSADO"
        else:
            status_geral = "⚠️ BAIXO"
        
        comparacoes.append({
            'cpf': cpf_csv,
            'processo': processo_csv,
            'csv_liquido': csv_liquido,
            'v3_liquido': v3_liquido,
            'diff_liquido_abs': diff_liq_abs,
            'diff_liquido_pct': diff_liq_pct,
            'status_liquido': status_liq,
            'csv_bruto': csv_bruto,
            'v3_bruto': v3_bruto,
            'diff_bruto_abs': diff_bruto_abs,
            'diff_bruto_pct': diff_bruto_pct,
            'status_bruto': status_bruto,
            'status_geral': status_geral
        })
    
    # Fechar conexão
    cursor.close()
    conn.close()
    
    # Criar DataFrame
    df_comp = pd.DataFrame(comparacoes)
    
    # Estatísticas
    total = len(df_comp)
    perfeitos = len(df_comp[df_comp['status_geral'] == "✅ PERFEITO"])
    aceitaveis = len(df_comp[df_comp['status_geral'] == "✅ ACEITÁVEL"])
    baixos = len(df_comp[df_comp['status_geral'] == "⚠️ BAIXO"])
    criticos = len(df_comp[df_comp['status_geral'] == "❌ CRÍTICO"])
    nao_proc = len(df_comp[df_comp['status_geral'] == "⚠️ NÃO PROCESSADO"])
    
    # Gerar relatório Markdown
    print("📝 Gerando relatório Markdown...")
    with open(OUTPUT_MD, 'w', encoding='utf-8') as f:
        f.write(f"# 📊 Comparação V3.0 vs CSV de Referência\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}  \n")
        f.write(f"**Total de Processos:** {total}  \n\n")
        
        f.write("---\n\n")
        f.write("## 📈 Estatísticas Gerais\n\n")
        f.write(f"| Status | Quantidade | Percentual |\n")
        f.write(f"|--------|------------|------------|\n")
        f.write(f"| ✅ **PERFEITO** | {perfeitos} | {perfeitos/total*100:.1f}% |\n")
        f.write(f"| ✅ **ACEITÁVEL** | {aceitaveis} | {aceitaveis/total*100:.1f}% |\n")
        f.write(f"| ⚠️ **BAIXO** | {baixos} | {baixos/total*100:.1f}% |\n")
        f.write(f"| ❌ **CRÍTICO** | {criticos} | {criticos/total*100:.1f}% |\n")
        f.write(f"| ⚠️ **NÃO PROCESSADO** | {nao_proc} | {nao_proc/total*100:.1f}% |\n\n")
        
        f.write("---\n\n")
        f.write("## 📋 Tabela de Comparação Detalhada\n\n")
        f.write("| # | CPF | Processo | Status | CSV Líquido | V3 Líquido | Diff | CSV Bruto | V3 Bruto | Diff |\n")
        f.write("|---|-----|----------|--------|-------------|------------|------|-----------|----------|------|\n")
        
        for idx, row in df_comp.iterrows():
            cpf_fmt = f"{row['cpf'][:3]}.{row['cpf'][3:6]}.{row['cpf'][6:9]}-{row['cpf'][9:]}"
            processo_short = row['processo'][:20] + "..." if len(row['processo']) > 20 else row['processo']
            
            csv_liq_fmt = f"R$ {row['csv_liquido']:,.2f}" if row['csv_liquido'] else "N/A"
            v3_liq_fmt = f"R$ {row['v3_liquido']:,.2f}" if row['v3_liquido'] else "N/A"
            diff_liq_fmt = f"R$ {row['diff_liquido_abs']:,.2f}" if row['diff_liquido_abs'] is not None else "N/A"
            
            csv_bruto_fmt = f"R$ {row['csv_bruto']:,.2f}" if row['csv_bruto'] else "N/A"
            v3_bruto_fmt = f"R$ {row['v3_bruto']:,.2f}" if row['v3_bruto'] else "N/A"
            diff_bruto_fmt = f"R$ {row['diff_bruto_abs']:,.2f}" if row['diff_bruto_abs'] is not None else "N/A"
            
            f.write(f"| {idx+1} | `{cpf_fmt}` | `{processo_short}` | {row['status_geral']} | {csv_liq_fmt} | {v3_liq_fmt} | {diff_liq_fmt} | {csv_bruto_fmt} | {v3_bruto_fmt} | {diff_bruto_fmt} |\n")
        
        f.write("\n---\n\n")
        f.write("## 🎯 Casos Críticos\n\n")
        
        criticos_df = df_comp[df_comp['status_geral'] == "❌ CRÍTICO"]
        if len(criticos_df) > 0:
            f.write(f"**Total:** {len(criticos_df)} casos críticos identificados\n\n")
            for idx, row in criticos_df.iterrows():
                f.write(f"### Caso #{idx+1}: {row['processo']}\n\n")
                f.write(f"- **CPF:** {row['cpf']}\n")
                f.write(f"- **Líquido CSV:** R$ {row['csv_liquido']:,.2f}\n")
                f.write(f"- **Líquido V3:** R$ {row['v3_liquido']:,.2f}\n")
                f.write(f"- **Diferença:** R$ {row['diff_liquido_abs']:,.2f} ({row['diff_liquido_pct']:.1f}%)\n\n")
        else:
            f.write("✅ **Nenhum caso crítico detectado!**\n\n")
        
        f.write("---\n\n")
        f.write("## 📊 Conclusão\n\n")
        
        taxa_sucesso = (perfeitos + aceitaveis) / total * 100
        f.write(f"- **Taxa de Sucesso:** {taxa_sucesso:.1f}%\n")
        f.write(f"- **Acurácia Perfeita:** {perfeitos/total*100:.1f}%\n")
        f.write(f"- **Casos Críticos:** {criticos} ({criticos/total*100:.1f}%)\n\n")
        
        if taxa_sucesso >= 95:
            f.write("✅ **V3.0 APROVADA PARA PRODUÇÃO!**\n")
        elif taxa_sucesso >= 90:
            f.write("⚠️ **V3.0 precisa de ajustes antes da produção**\n")
        else:
            f.write("❌ **V3.0 NÃO APROVADA - requer revisão crítica**\n")
    
    print(f"   ✅ Relatório salvo: {OUTPUT_MD}")
    
    # Salvar CSV
    print("📄 Salvando CSV detalhado...")
    df_comp.to_csv(OUTPUT_CSV, index=False)
    print(f"   ✅ CSV salvo: {OUTPUT_CSV}")
    
    # Imprimir resumo no console
    print()
    print("=" * 80)
    print("📊 RESUMO DA COMPARAÇÃO V3.0")
    print("=" * 80)
    print()
    print(f"Total de Processos: {total}")
    print(f"✅ PERFEITO: {perfeitos} ({perfeitos/total*100:.1f}%)")
    print(f"✅ ACEITÁVEL: {aceitaveis} ({aceitaveis/total*100:.1f}%)")
    print(f"⚠️ BAIXO: {baixos} ({baixos/total*100:.1f}%)")
    print(f"❌ CRÍTICO: {criticos} ({criticos/total*100:.1f}%)")
    print(f"⚠️ NÃO PROCESSADO: {nao_proc} ({nao_proc/total*100:.1f}%)")
    print()
    print(f"Taxa de Sucesso: {taxa_sucesso:.1f}%")
    print(f"Acurácia Perfeita: {perfeitos/total*100:.1f}%")
    print()
    
    # Casos críticos
    if criticos > 0:
        print("❌ CASOS CRÍTICOS DETECTADOS:")
        print()
        for idx, row in criticos_df.iterrows():
            print(f"  {idx+1}. {row['processo']}")
            print(f"     CPF: {row['cpf']}")
            print(f"     CSV: R$ {row['csv_liquido']:,.2f}")
            print(f"     V3:  R$ {row['v3_liquido']:,.2f}")
            print(f"     Diff: R$ {row['diff_liquido_abs']:,.2f} ({row['diff_liquido_pct']:.1f}%)")
            print()
    
    print("=" * 80)

if __name__ == "__main__":
    main()

