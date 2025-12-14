#!/usr/bin/env python3
"""
Análise de Cobertura de Colunas - Tabela esaj_detalhe_processos
Verifica o preenchimento de TODAS as colunas da tabela
"""

import psycopg2
from typing import Dict, List, Tuple
import json

# Configuração do banco
DB_CONFIG = {
    'host': '72.60.62.124',
    'port': 5432,
    'database': 'n8n',
    'user': 'admin',
    'password': 'BetaAgent2024SecureDB'
}

class ColumnCoverageAnalyzer:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.total_records = 0
        self.columns = []
        self.coverage_data = {
            'full': [],      # 100% preenchidas
            'partial': [],   # Parcialmente preenchidas
            'empty': []      # 100% vazias
        }

    def get_total_records(self):
        """Obtém total de registros"""
        self.cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos;')
        self.total_records = self.cursor.fetchone()[0]
        return self.total_records

    def get_all_columns(self):
        """Obtém todas as colunas da tabela"""
        self.cursor.execute('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'esaj_detalhe_processos'
            ORDER BY ordinal_position;
        ''')
        self.columns = self.cursor.fetchall()
        return self.columns

    def analyze_column_coverage(self, column_name: str) -> Tuple[int, int, float]:
        """
        Analisa o preenchimento de uma coluna
        Retorna: (filled_count, null_count, percentage)
        """
        # Contar registros preenchidos
        self.cursor.execute(f'''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE {column_name} IS NOT NULL;
        ''')
        filled = self.cursor.fetchone()[0]

        null_count = self.total_records - filled
        percentage = (filled / self.total_records * 100) if self.total_records > 0 else 0

        return filled, null_count, percentage

    def categorize_columns(self):
        """Categoriza colunas por nível de preenchimento"""
        print(f'\n📊 Analisando {len(self.columns)} colunas...\n')

        for col_name, col_type, nullable in self.columns:
            filled, null_count, pct = self.analyze_column_coverage(col_name)

            col_data = {
                'name': col_name,
                'type': col_type,
                'nullable': nullable,
                'filled': filled,
                'null': null_count,
                'percentage': round(pct, 2)
            }

            if pct == 100.0:
                self.coverage_data['full'].append(col_data)
            elif pct == 0.0:
                self.coverage_data['empty'].append(col_data)
            else:
                self.coverage_data['partial'].append(col_data)

    def print_report(self):
        """Imprime relatório formatado"""
        total = len(self.columns)
        full_count = len(self.coverage_data['full'])
        partial_count = len(self.coverage_data['partial'])
        empty_count = len(self.coverage_data['empty'])

        print('=' * 100)
        print(f'📊 ANÁLISE DE COBERTURA - TABELA esaj_detalhe_processos')
        print('=' * 100)
        print(f'\n📈 Total de registros: {self.total_records}')
        print(f'📋 Total de colunas: {total}')
        print(f'\n  ✅ Colunas 100% preenchidas: {full_count}')
        print(f'  🟡 Colunas parcialmente preenchidas: {partial_count}')
        print(f'  ⚪ Colunas 100% vazias: {empty_count}')

        # Colunas 100% preenchidas
        print('\n' + '=' * 100)
        print(f'✅ COLUNAS 100% PREENCHIDAS ({full_count})')
        print('=' * 100)
        for col in sorted(self.coverage_data['full'], key=lambda x: x['name']):
            print(f"  • {col['name']:40} {col['type']:20} {col['filled']}/{self.total_records}")

        # Colunas parcialmente preenchidas
        print('\n' + '=' * 100)
        print(f'🟡 COLUNAS PARCIALMENTE PREENCHIDAS ({partial_count})')
        print('=' * 100)
        # Ordenar por percentual decrescente
        for col in sorted(self.coverage_data['partial'], key=lambda x: x['percentage'], reverse=True):
            bar = self._create_progress_bar(col['percentage'])
            print(f"  • {col['name']:40} {bar} {col['percentage']:5.1f}% ({col['filled']}/{self.total_records})")

        # Colunas 100% vazias
        print('\n' + '=' * 100)
        print(f'⚪ COLUNAS 100% VAZIAS ({empty_count})')
        print('=' * 100)
        for col in sorted(self.coverage_data['empty'], key=lambda x: x['name']):
            print(f"  • {col['name']:40} {col['type']:20} 0/{self.total_records}")

        # Estatísticas por categoria
        print('\n' + '=' * 100)
        print('📊 ESTATÍSTICAS POR CATEGORIA')
        print('=' * 100)

        categories = {
            'Identificação': ['cpf', 'numero_processo_cnj', 'processo_origem', 'requerente_caps', 'numero_ordem'],
            'Dados Processuais': ['vara', 'processo_execucao', 'processo_conhecimento'],
            'Datas': ['data_ajuizamento', 'data_transito_julgado', 'data_base_atualizacao', 'data_nascimento', 'data_obito'],
            'Dados Bancários': ['banco', 'agencia', 'conta', 'conta_tipo', 'dados_bancarios_advogado', 'cpf_titular_conta'],
            'Valores Financeiros': ['valor_principal_liquido', 'valor_principal_bruto', 'juros_moratorios',
                                   'valor_total_requisitado', 'saldo_final', 'valor_compensado'],
            'Deduções': ['contrib_previdenciaria_iprem', 'contrib_previdenciaria_hspm', 'contribuicao_social',
                        'salario_pericial', 'assist_tecnico', 'custas', 'despesas', 'multas'],
            'Partes': ['credor_nome', 'credor_cpf_cnpj', 'devedor_ente', 'advogado_nome', 'advogado_oab'],
            'Condições Especiais': ['idoso', 'doenca_grave', 'pcd', 'preferencial', 'obito', 'cpf_sucessor'],
            'Situações Processuais': ['habilitacao_herdeiros', 'cessao_credito', 'rejeitado', 'motivo_rejeicao', 'anomalia', 'descricao_anomalia'],
            'Controle': ['tipo_levantamento', 'observacoes', 'process_diagnostico', 'process_calculo', 'caminho_pdf', 'timestamp_ingestao']
        }

        all_cols = self.coverage_data['full'] + self.coverage_data['partial'] + self.coverage_data['empty']

        for category, col_names in categories.items():
            category_cols = [c for c in all_cols if c['name'] in col_names]
            if category_cols:
                avg_pct = sum(c['percentage'] for c in category_cols) / len(category_cols)
                full = sum(1 for c in category_cols if c['percentage'] == 100)
                empty = sum(1 for c in category_cols if c['percentage'] == 0)
                partial = len(category_cols) - full - empty

                print(f'\n{category}:')
                print(f'  Total: {len(category_cols)} colunas | Média: {avg_pct:.1f}%')
                print(f'  ✅ Completas: {full} | 🟡 Parciais: {partial} | ⚪ Vazias: {empty}')

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Cria barra de progresso visual"""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f'[{bar}]'

    def save_json_report(self):
        """Salva relatório em JSON"""
        report = {
            'total_records': self.total_records,
            'total_columns': len(self.columns),
            'summary': {
                'full': len(self.coverage_data['full']),
                'partial': len(self.coverage_data['partial']),
                'empty': len(self.coverage_data['empty'])
            },
            'columns': {
                'full': self.coverage_data['full'],
                'partial': sorted(self.coverage_data['partial'], key=lambda x: x['percentage'], reverse=True),
                'empty': self.coverage_data['empty']
            }
        }

        output_file = '/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/2_ingestao/column_coverage_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f'\n💾 Relatório JSON salvo em: {output_file}')

    def run(self):
        """Executa análise completa"""
        print('\n' + '=' * 100)
        print('🚀 INICIANDO ANÁLISE DE COBERTURA DE COLUNAS')
        print('=' * 100)

        try:
            self.get_total_records()
            self.get_all_columns()
            self.categorize_columns()
            self.print_report()
            self.save_json_report()
        finally:
            self.cursor.close()
            self.conn.close()

if __name__ == '__main__':
    analyzer = ColumnCoverageAnalyzer()
    analyzer.run()
