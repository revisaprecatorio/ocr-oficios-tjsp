#!/usr/bin/env python3
"""
Data Quality Analysis - V2.5.3
Validação completa dos campos do banco PostgreSQL
"""

import psycopg2
from decimal import Decimal
import json
from datetime import datetime
from typing import Dict, List

# Configuração do banco
DB_CONFIG = {
    'host': '72.60.62.124',
    'port': 5432,
    'database': 'n8n',
    'user': 'admin',
    'password': 'BetaAgent2024SecureDB'
}

class DataQualityAnalyzer:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.issues = []
        self.stats = {}

    def log_issue(self, severity: str, category: str, message: str, count: int = 1, details: str = None):
        """Registra um problema de qualidade"""
        self.issues.append({
            'severity': severity,
            'category': category,
            'message': message,
            'count': count,
            'details': details
        })

    def get_total_records(self):
        """Total de registros"""
        self.cursor.execute('SELECT COUNT(*) FROM esaj_detalhe_processos;')
        return self.cursor.fetchone()[0]

    def validate_required_fields(self):
        """1. Validar campos obrigatórios"""
        print('\n📋 1. VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS')
        print('=' * 80)

        required_fields = [
            'processo_origem',
            'requerente_caps',
            'credor_cpf_cnpj'
        ]

        for field in required_fields:
            self.cursor.execute(f"SELECT COUNT(*) FROM esaj_detalhe_processos WHERE {field} IS NULL;")
            null_count = self.cursor.fetchone()[0]

            if null_count > 0:
                self.log_issue('CRITICAL', 'REQUIRED_FIELDS',
                             f'Campo obrigatório {field} tem {null_count} valores NULL', null_count)
                print(f'  ❌ {field}: {null_count} NULLs encontrados')
            else:
                print(f'  ✅ {field}: OK')

    def validate_business_rules(self):
        """2. Validar regras de negócio"""
        print('\n🔍 2. VALIDAÇÃO DE REGRAS DE NEGÓCIO')
        print('=' * 80)

        # Regra 1: Se obito=True, deve ter cpf_sucessor OU habilitacao_herdeiros
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE obito = TRUE
            AND cpf_sucessor IS NULL
            AND habilitacao_herdeiros = FALSE;
        ''')
        obito_sem_sucessor = self.cursor.fetchone()[0]

        if obito_sem_sucessor > 0:
            self.log_issue('WARNING', 'BUSINESS_RULE',
                         f'Óbito sem sucessor nem habilitação de herdeiros', obito_sem_sucessor)
            print(f'  ⚠️  Óbito sem sucessor/habilitação: {obito_sem_sucessor}')
        else:
            print(f'  ✅ Óbito → sucessor/habilitação: OK')

        # Regra 2: Se preferencial=True, deve ter pelo menos uma condição
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE preferencial = TRUE
            AND idoso IS NOT TRUE
            AND doenca_grave IS NOT TRUE
            AND pcd IS NOT TRUE;
        ''')
        preferencial_sem_justificativa = self.cursor.fetchone()[0]

        if preferencial_sem_justificativa > 0:
            self.log_issue('WARNING', 'BUSINESS_RULE',
                         f'Preferencial sem justificativa (idoso/doença/PCD)',
                         preferencial_sem_justificativa)
            print(f'  ⚠️  Preferencial sem justificativa: {preferencial_sem_justificativa}')
        else:
            print(f'  ✅ Preferencial → condição: OK')

        # Regra 3: saldo_final <= valor_total_requisitado (se ambos preenchidos)
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE saldo_final IS NOT NULL
            AND valor_total_requisitado IS NOT NULL
            AND saldo_final::numeric > valor_total_requisitado::numeric;
        ''')
        saldo_maior_total = self.cursor.fetchone()[0]

        if saldo_maior_total > 0:
            self.log_issue('CRITICAL', 'BUSINESS_RULE',
                         f'Saldo final > Valor total requisitado', saldo_maior_total)
            print(f'  ❌ Saldo > Total: {saldo_maior_total}')
        else:
            print(f'  ✅ Saldo ≤ Total: OK')

        # Regra 4: Se cessao_credito=True, pode ter saldo_final=0
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE cessao_credito = TRUE;
        ''')
        total_cessoes = self.cursor.fetchone()[0]

        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE cessao_credito = TRUE AND (saldo_final = 0 OR saldo_final IS NULL);
        ''')
        cessoes_zeradas = self.cursor.fetchone()[0]

        print(f'  ℹ️  Cessões de crédito: {total_cessoes} (zeradas: {cessoes_zeradas})')

    def validate_numeric_ranges(self):
        """3. Validar valores numéricos e ranges"""
        print('\n💰 3. VALIDAÇÃO DE VALORES NUMÉRICOS')
        print('=' * 80)

        # Valores negativos
        numeric_fields = [
            'valor_principal_liquido',
            'valor_principal_bruto',
            'juros_moratorios',
            'valor_total_requisitado',
            'saldo_final'
        ]

        for field in numeric_fields:
            self.cursor.execute(f'''
                SELECT COUNT(*) FROM esaj_detalhe_processos
                WHERE {field} IS NOT NULL AND {field}::numeric < 0;
            ''')
            negative_count = self.cursor.fetchone()[0]

            if negative_count > 0:
                self.log_issue('CRITICAL', 'NUMERIC_RANGE',
                             f'Campo {field} tem valores negativos', negative_count)
                print(f'  ❌ {field}: {negative_count} valores negativos')
            else:
                print(f'  ✅ {field}: sem valores negativos')

        # Valores extremos (outliers)
        self.cursor.execute('''
            SELECT MAX(saldo_final::numeric), MIN(saldo_final::numeric), AVG(saldo_final::numeric)
            FROM esaj_detalhe_processos WHERE saldo_final IS NOT NULL;
        ''')
        max_saldo, min_saldo, avg_saldo = self.cursor.fetchone()
        print(f'\n  📊 Estatísticas de saldo_final:')
        print(f'     Máximo: R$ {max_saldo:,.2f}')
        print(f'     Mínimo: R$ {min_saldo:,.2f}')
        print(f'     Média: R$ {avg_saldo:,.2f}')

    def detect_anomalies(self):
        """4. Detectar anomalias e inconsistências"""
        print('\n🔎 4. DETECÇÃO DE ANOMALIAS')
        print('=' * 80)

        # Processos duplicados (mesmo processo_origem)
        self.cursor.execute('''
            SELECT processo_origem, COUNT(*) as cnt
            FROM esaj_detalhe_processos
            GROUP BY processo_origem
            HAVING COUNT(*) > 1;
        ''')
        duplicates = self.cursor.fetchall()

        if duplicates:
            total_dup = sum(count for _, count in duplicates)
            self.log_issue('WARNING', 'ANOMALY',
                         f'Processos duplicados encontrados', len(duplicates),
                         f'Total de duplicatas: {total_dup}')
            print(f'  ⚠️  Processos duplicados: {len(duplicates)} processos ({total_dup} registros)')
        else:
            print(f'  ✅ Sem processos duplicados')

        # Campos data_obito sem obito=True
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE data_obito IS NOT NULL AND obito IS NOT TRUE;
        ''')
        data_obito_sem_flag = self.cursor.fetchone()[0]

        if data_obito_sem_flag > 0:
            self.log_issue('WARNING', 'ANOMALY',
                         f'data_obito preenchida mas obito=FALSE', data_obito_sem_flag)
            print(f'  ⚠️  data_obito sem flag obito: {data_obito_sem_flag}')
        else:
            print(f'  ✅ Consistência data_obito ↔ obito: OK')

        # CPF sucessor sem obito
        self.cursor.execute('''
            SELECT COUNT(*) FROM esaj_detalhe_processos
            WHERE cpf_sucessor IS NOT NULL AND obito IS NOT TRUE;
        ''')
        sucessor_sem_obito = self.cursor.fetchone()[0]

        if sucessor_sem_obito > 0:
            self.log_issue('WARNING', 'ANOMALY',
                         f'cpf_sucessor preenchido mas obito=FALSE', sucessor_sem_obito)
            print(f'  ⚠️  CPF sucessor sem óbito: {sucessor_sem_obito}')
        else:
            print(f'  ✅ Consistência cpf_sucessor ↔ obito: OK')

    def validate_v2_5_3_fields(self):
        """5. Validação específica dos campos V2.5.3"""
        print('\n🆕 5. VALIDAÇÃO CAMPOS V2.5.3')
        print('=' * 80)

        total = self.get_total_records()

        # Estatísticas de preenchimento V2.5.3
        v253_fields = {
            'saldo_final': 'Saldo Final',
            'doenca_grave': 'Doença Grave',
            'obito': 'Óbito',
            'data_obito': 'Data Óbito',
            'cpf_sucessor': 'CPF Sucessor',
            'habilitacao_herdeiros': 'Habilitação Herdeiros',
            'preferencial': 'Preferencial',
            'cessao_credito': 'Cessão Crédito'
        }

        for field, label in v253_fields.items():
            self.cursor.execute(f'''
                SELECT COUNT(*) FROM esaj_detalhe_processos
                WHERE {field} IS NOT NULL;
            ''')
            filled = self.cursor.fetchone()[0]
            pct = (filled / total * 100) if total > 0 else 0

            print(f'  • {label:25} {filled:3}/{total} ({pct:5.1f}%)')

            if field in ['saldo_final', 'doenca_grave'] and pct < 80:
                self.log_issue('WARNING', 'V253_COVERAGE',
                             f'Campo {field} com cobertura baixa ({pct:.1f}%)', total - filled)

    def generate_report(self):
        """6. Gerar relatório final"""
        print('\n' + '=' * 80)
        print('📊 RELATÓRIO DE DATA QUALITY - V2.5.3')
        print('=' * 80)

        total = self.get_total_records()

        # Agrupar issues por severidade
        critical = [i for i in self.issues if i['severity'] == 'CRITICAL']
        warnings = [i for i in self.issues if i['severity'] == 'WARNING']
        info = [i for i in self.issues if i['severity'] == 'INFO']

        print(f'\n📈 Total de registros: {total}')
        print(f'\n🔴 Issues CRÍTICOS: {len(critical)}')
        for issue in critical:
            print(f'   • {issue["message"]} ({issue["count"]} registros)')

        print(f'\n🟡 Avisos (WARNINGS): {len(warnings)}')
        for issue in warnings:
            print(f'   • {issue["message"]} ({issue["count"]} registros)')

        if len(critical) == 0 and len(warnings) == 0:
            print('\n✅ NENHUM PROBLEMA DETECTADO - DATA QUALITY 100%')
        else:
            score = max(0, 100 - (len(critical) * 20 + len(warnings) * 5))
            print(f'\n📊 SCORE DE QUALIDADE: {score}/100')

        # Salvar relatório JSON
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_records': total,
            'issues': self.issues,
            'summary': {
                'critical': len(critical),
                'warnings': len(warnings),
                'info': len(info)
            }
        }

        report_file = '/Users/persivalballeste/Documents/@IANIA/PROJECTS/revisa/revisa/3_OCR/2_ingestao/data_quality_report_v2.5.3.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f'\n💾 Relatório salvo em: {report_file}')

    def run(self):
        """Executar todas as validações"""
        print('\n' + '=' * 80)
        print('🚀 INICIANDO DATA QUALITY ANALYSIS V2.5.3')
        print('=' * 80)
        print(f'Banco: {DB_CONFIG["host"]}:{DB_CONFIG["port"]}/{DB_CONFIG["database"]}')
        print(f'Tabela: esaj_detalhe_processos')
        print(f'Total de registros: {self.get_total_records()}')

        try:
            self.validate_required_fields()
            self.validate_business_rules()
            self.validate_numeric_ranges()
            self.detect_anomalies()
            self.validate_v2_5_3_fields()
            self.generate_report()
        finally:
            self.cursor.close()
            self.conn.close()

if __name__ == '__main__':
    analyzer = DataQualityAnalyzer()
    analyzer.run()
