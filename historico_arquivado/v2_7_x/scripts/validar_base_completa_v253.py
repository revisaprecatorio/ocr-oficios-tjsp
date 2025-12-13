#!/usr/bin/env python3
"""
Script de Validação Completa V2.5.3
Valida TODOS os CPFs da base de validação processados com V2.5.3
Gera relatório markdown com timestamp
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

# CPFs da base de validação (12 CPFs do Google Drive)
CPFS_VALIDACAO = [
    '03736870876',
    '07692595887',
    '08212993876',
    '10582304849',
    '10773800891',
    '11147105804',
    '13725004803',
    '16313887891',
    '28455260831',
    '36576414838',
    '57629080891',
    '93968396804'
]

def analisar_json(json_path: Path) -> Dict:
    """Extrai campos V2.5.3 de um JSON"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extrair CPF do nome do arquivo
        cpf = json_path.stem.split('_')[0]
        processo = json_path.stem.split('_')[1] if '_' in json_path.stem else 'N/A'

        return {
            'cpf': cpf,
            'processo': processo,
            'arquivo': json_path.name,
            'lote': json_path.parent.name,

            # Campos V2.5.3
            'obito': data.get('obito'),
            'data_obito': data.get('data_obito'),
            'cpf_sucessor': data.get('cpf_sucessor'),
            'doenca_grave': data.get('doenca_grave'),
            'habilitacao_herdeiros': data.get('habilitacao_herdeiros'),

            # Campos V2.5.2 (contexto)
            'idoso': data.get('idoso'),
            'pcd': data.get('pcd'),
            'preferencial': data.get('preferencial'),

            # Valores financeiros
            'saldo_final': data.get('saldo_final'),
            'valor_total_requisitado': data.get('valor_total_requisitado'),

            # Dados do credor
            'requerente_caps': data.get('requerente_caps'),
            'credor_nome': data.get('credor_nome'),
            'processo_origem': data.get('processo_origem'),
        }
    except Exception as e:
        return {
            'cpf': 'ERRO',
            'processo': 'ERRO',
            'arquivo': json_path.name,
            'lote': json_path.parent.name,
            'erro': str(e)
        }

def gerar_relatorio_markdown(dados: List[Dict], output_path: Path):
    """Gera relatório markdown completo"""

    # Estatísticas gerais
    total_processos = len(dados)
    cpfs_unicos = len(set(d['cpf'] for d in dados if d['cpf'] != 'ERRO'))

    # Contadores V2.5.3
    total_obito = sum(1 for d in dados if d.get('obito') is True)
    total_doenca_grave = sum(1 for d in dados if d.get('doenca_grave') is True)
    total_habilitacao = sum(1 for d in dados if d.get('habilitacao_herdeiros') is True)
    total_sucessor = sum(1 for d in dados if d.get('cpf_sucessor'))
    total_data_obito = sum(1 for d in dados if d.get('data_obito'))

    # Contadores V2.5.2
    total_idoso = sum(1 for d in dados if d.get('idoso') is True)
    total_pcd = sum(1 for d in dados if d.get('pcd') is True)
    total_preferencial = sum(1 for d in dados if d.get('preferencial') is True)

    # Agrupar por CPF
    dados_por_cpf = defaultdict(list)
    for d in dados:
        dados_por_cpf[d['cpf']].append(d)

    # Gerar markdown
    md_lines = []
    md_lines.append("# 📊 RELATÓRIO DE VALIDAÇÃO V2.5.3 - BASE COMPLETA")
    md_lines.append("")
    md_lines.append(f"**Data/Hora**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    md_lines.append(f"**Versão**: V2.5.3")
    md_lines.append(f"**Base**: data/consultas/ (12 CPFs)")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # Estatísticas Gerais
    md_lines.append("## 📈 ESTATÍSTICAS GERAIS")
    md_lines.append("")
    md_lines.append(f"- **Total de Processos**: {total_processos}")
    md_lines.append(f"- **CPFs Únicos**: {cpfs_unicos}")
    md_lines.append(f"- **Média Processos/CPF**: {total_processos/cpfs_unicos:.1f}")
    md_lines.append("")

    # Detecções V2.5.3
    md_lines.append("### 🎯 Detecções V2.5.3 (Novos Campos)")
    md_lines.append("")
    md_lines.append("| Campo | Total | % do Total |")
    md_lines.append("|-------|-------|------------|")
    md_lines.append(f"| **Óbito** | {total_obito} | {total_obito/total_processos*100:.1f}% |")
    md_lines.append(f"| **Data Óbito** | {total_data_obito} | {total_data_obito/total_processos*100:.1f}% |")
    md_lines.append(f"| **CPF Sucessor** | {total_sucessor} | {total_sucessor/total_processos*100:.1f}% |")
    md_lines.append(f"| **Doença Grave** | {total_doenca_grave} | {total_doenca_grave/total_processos*100:.1f}% |")
    md_lines.append(f"| **Habilitação Herdeiros** | {total_habilitacao} | {total_habilitacao/total_processos*100:.1f}% |")
    md_lines.append("")

    # Detecções V2.5.2
    md_lines.append("### 📋 Detecções V2.5.2 (Campos Existentes)")
    md_lines.append("")
    md_lines.append("| Campo | Total | % do Total |")
    md_lines.append("|-------|-------|------------|")
    md_lines.append(f"| **Idoso** | {total_idoso} | {total_idoso/total_processos*100:.1f}% |")
    md_lines.append(f"| **PCD** | {total_pcd} | {total_pcd/total_processos*100:.1f}% |")
    md_lines.append(f"| **Preferencial** | {total_preferencial} | {total_preferencial/total_processos*100:.1f}% |")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

    # Detalhamento por CPF
    md_lines.append("## 👥 DETALHAMENTO POR CPF")
    md_lines.append("")

    for cpf in sorted(dados_por_cpf.keys()):
        if cpf == 'ERRO':
            continue

        processos_cpf = dados_por_cpf[cpf]
        n_processos = len(processos_cpf)

        # Nome do requerente (pegar do primeiro processo)
        nome = processos_cpf[0].get('requerente_caps') or processos_cpf[0].get('credor_nome') or 'N/A'

        # Verificar se CPF está na base de validação
        validacao_badge = "✅ **VALIDAÇÃO**" if cpf in CPFS_VALIDACAO else ""

        md_lines.append(f"### CPF {cpf} {validacao_badge}")
        md_lines.append("")
        md_lines.append(f"**Nome**: {nome}")
        md_lines.append(f"**Total de Processos**: {n_processos}")
        md_lines.append("")

        # Resumo dos campos V2.5.3 para este CPF
        cpf_obito = sum(1 for p in processos_cpf if p.get('obito') is True)
        cpf_doenca = sum(1 for p in processos_cpf if p.get('doenca_grave') is True)
        cpf_hab = sum(1 for p in processos_cpf if p.get('habilitacao_herdeiros') is True)
        cpf_sucessor = sum(1 for p in processos_cpf if p.get('cpf_sucessor'))

        md_lines.append("**Resumo V2.5.3:**")
        md_lines.append(f"- Óbito: {cpf_obito}/{n_processos}")
        md_lines.append(f"- Doença Grave: {cpf_doenca}/{n_processos}")
        md_lines.append(f"- Habilitação Herdeiros: {cpf_hab}/{n_processos}")
        md_lines.append(f"- CPF Sucessor: {cpf_sucessor}/{n_processos}")
        md_lines.append("")

        # Tabela de processos
        md_lines.append("| Processo | Lote | Óbito | Doença Grave | Habilitação | CPF Sucessor | Saldo Final |")
        md_lines.append("|----------|------|-------|--------------|-------------|--------------|-------------|")

        for p in processos_cpf:
            obito_icon = "✅" if p.get('obito') is True else "❌" if p.get('obito') is False else "⚠️"
            doenca_icon = "✅" if p.get('doenca_grave') is True else "❌" if p.get('doenca_grave') is False else "⚠️"
            hab_icon = "✅" if p.get('habilitacao_herdeiros') is True else "❌" if p.get('habilitacao_herdeiros') is False else "⚠️"
            sucessor = p.get('cpf_sucessor', '-')
            saldo = p.get('saldo_final', 'N/A')

            md_lines.append(f"| {p['processo']} | {p['lote']} | {obito_icon} | {doenca_icon} | {hab_icon} | {sucessor} | {saldo} |")

        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    # Casos Críticos
    md_lines.append("## 🔍 CASOS CRÍTICOS V2.5.3")
    md_lines.append("")

    # Habilitação de herdeiros
    casos_hab = [d for d in dados if d.get('habilitacao_herdeiros') is True]
    md_lines.append(f"### ✅ Habilitação de Herdeiros ({len(casos_hab)} casos)")
    md_lines.append("")
    if casos_hab:
        md_lines.append("| CPF | Processo | Óbito | CPF Sucessor | Doença Grave |")
        md_lines.append("|-----|----------|-------|--------------|--------------|")
        for c in casos_hab:
            obito = "✅" if c.get('obito') else "❌"
            doenca = "✅" if c.get('doenca_grave') else "❌"
            md_lines.append(f"| {c['cpf']} | {c['processo']} | {obito} | {c.get('cpf_sucessor', '-')} | {doenca} |")
        md_lines.append("")
    else:
        md_lines.append("*Nenhum caso detectado*")
        md_lines.append("")

    # Doença grave SEM óbito
    casos_doenca_sem_obito = [d for d in dados if d.get('doenca_grave') is True and d.get('obito') is not True]
    md_lines.append(f"### 🏥 Doença Grave SEM Óbito ({len(casos_doenca_sem_obito)} casos)")
    md_lines.append("")
    if casos_doenca_sem_obito:
        md_lines.append("| CPF | Processo | Habilitação | Idoso |")
        md_lines.append("|-----|----------|-------------|-------|")
        for c in casos_doenca_sem_obito:
            hab = "✅" if c.get('habilitacao_herdeiros') else "❌"
            idoso = "✅" if c.get('idoso') else "❌"
            md_lines.append(f"| {c['cpf']} | {c['processo']} | {hab} | {idoso} |")
        md_lines.append("")
    else:
        md_lines.append("*Nenhum caso detectado*")
        md_lines.append("")

    # Sucessores identificados
    casos_sucessor = [d for d in dados if d.get('cpf_sucessor')]
    md_lines.append(f"### 👤 Sucessores Identificados ({len(casos_sucessor)} casos)")
    md_lines.append("")
    if casos_sucessor:
        md_lines.append("| CPF Original | Processo | CPF Sucessor | Habilitação |")
        md_lines.append("|--------------|----------|--------------|-------------|")
        for c in casos_sucessor:
            hab = "✅" if c.get('habilitacao_herdeiros') else "❌"
            md_lines.append(f"| {c['cpf']} | {c['processo']} | {c['cpf_sucessor']} | {hab} |")
        md_lines.append("")
    else:
        md_lines.append("*Nenhum caso detectado*")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")

    # Campos Ausentes (NULL/None)
    md_lines.append("## ⚠️ CAMPOS V2.5.3 AUSENTES (NULL)")
    md_lines.append("")

    campos_ausentes = defaultdict(list)
    for d in dados:
        if d.get('obito') is None:
            campos_ausentes['obito'].append(f"{d['cpf']} - {d['processo']}")
        if d.get('doenca_grave') is None:
            campos_ausentes['doenca_grave'].append(f"{d['cpf']} - {d['processo']}")
        if d.get('habilitacao_herdeiros') is None:
            campos_ausentes['habilitacao_herdeiros'].append(f"{d['cpf']} - {d['processo']}")

    if campos_ausentes:
        for campo, casos in campos_ausentes.items():
            md_lines.append(f"### {campo} ({len(casos)} casos)")
            md_lines.append("")
            for caso in casos[:10]:  # Limitar a 10 exemplos
                md_lines.append(f"- {caso}")
            if len(casos) > 10:
                md_lines.append(f"- *...e mais {len(casos)-10} casos*")
            md_lines.append("")
    else:
        md_lines.append("✅ **Nenhum campo ausente!** Todos os processos têm valores V2.5.3.")
        md_lines.append("")

    md_lines.append("---")
    md_lines.append("")

    # Footer
    md_lines.append("## 📝 OBSERVAÇÕES")
    md_lines.append("")
    md_lines.append("- ✅ = Campo com valor `true`")
    md_lines.append("- ❌ = Campo com valor `false`")
    md_lines.append("- ⚠️ = Campo `null` ou ausente")
    md_lines.append("- **VALIDAÇÃO** = CPF da base de validação (Google Drive)")
    md_lines.append("")
    md_lines.append("**Versão do Processador**: V2.5.3")
    md_lines.append(f"**Data de Geração**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    md_lines.append("")

    # Escrever arquivo
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    print(f"✅ Relatório gerado: {output_path}")
    print(f"📊 Total de processos analisados: {total_processos}")
    print(f"👥 CPFs únicos: {cpfs_unicos}")

def main():
    print("🔍 Validação Completa V2.5.3 - Base de Validação")
    print("=" * 60)

    # Encontrar todos os JSONs processados
    outputs_dir = Path(__file__).parent / 'outputs'
    json_files = list(outputs_dir.glob('lote_*/*.json'))

    print(f"📁 Encontrados {len(json_files)} arquivos JSON em {outputs_dir}")
    print()

    # Analisar cada JSON
    dados = []
    for json_path in json_files:
        resultado = analisar_json(json_path)
        dados.append(resultado)

    print(f"✅ Analisados {len(dados)} processos")
    print()

    # Filtrar apenas CPFs da base de validação
    dados_validacao = [d for d in dados if d['cpf'] in CPFS_VALIDACAO]
    print(f"✅ Filtrados {len(dados_validacao)} processos da base de validação (12 CPFs)")
    print()

    # Gerar relatório com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path('/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/data') / f'VALIDACAO_V253_{timestamp}.md'

    print(f"📝 Gerando relatório em: {output_path}")
    gerar_relatorio_markdown(dados_validacao, output_path)
    print()
    print("=" * 60)
    print("✅ VALIDAÇÃO COMPLETA!")

if __name__ == '__main__':
    main()
