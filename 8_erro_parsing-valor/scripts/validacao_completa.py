#!/usr/bin/env python3
"""
Script de Validação Completa do Sistema OCR
============================================

Processa todos os PDFs da pasta data/consultas/ e compara com resultados do CSV exportado.
Identifica discrepâncias nos valores extraídos e gera relatório detalhado.

Uso:
    python validacao_completa.py

Saída:
    - Console: Progresso e resumo
    - CSV: relatorio_validacao_TIMESTAMP.csv
    - JSON: discrepancias_TIMESTAMP.json
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
from decimal import Decimal
from typing import Dict, List, Tuple
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
ENV_PATH = Path(__file__).parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

# Adicionar o diretório pai ao path para importar os módulos do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent / "1_parsing_PDF"
sys.path.insert(0, str(PROJECT_ROOT))

from app.processador import ProcessadorOficio
from app.detector import DetectorOficio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidadorCompleto:
    """Processa todos os PDFs e compara com CSV de referência"""
    
    def __init__(self, pasta_consultas: str, csv_referencia: str):
        self.pasta_consultas = Path(pasta_consultas)
        self.csv_referencia = Path(csv_referencia)
        
        # Configurar processador com credenciais do .env
        openai_api_key = os.getenv('OPENAI_API_KEY')
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        self.processador = ProcessadorOficio(
            openai_api_key=openai_api_key,
            db_config=db_config
        )
        self.resultados = []
        self.discrepancias = []
        
    def carregar_csv_referencia(self) -> pd.DataFrame:
        """Carrega CSV de referência e indexa por CPF + Processo"""
        logger.info(f"Carregando CSV de referência: {self.csv_referencia}")
        df = pd.read_csv(self.csv_referencia)
        logger.info(f"✓ {len(df)} registros carregados")
        return df
        
    def listar_pdfs(self) -> List[Tuple[str, str]]:
        """Lista todos os PDFs na pasta consultas/"""
        logger.info(f"Listando PDFs em: {self.pasta_consultas}")
        pdfs = []
        
        for cpf_dir in self.pasta_consultas.iterdir():
            if not cpf_dir.is_dir():
                continue
                
            cpf = cpf_dir.name
            for pdf_file in cpf_dir.glob("*.pdf"):
                pdfs.append((cpf, str(pdf_file)))
                
        logger.info(f"✓ {len(pdfs)} PDFs encontrados")
        return pdfs
        
    def processar_pdf(self, cpf: str, caminho_pdf: str) -> Dict:
        """Processa um PDF e retorna os dados extraídos"""
        try:
            numero_processo = Path(caminho_pdf).stem
            
            logger.info(f"  Processando: {cpf}/{numero_processo}")
            
            # Processar PDF
            resultado = self.processador.processar_arquivo(
                pdf_path=caminho_pdf,
                cpf_numerico=cpf
            )
            
            if not resultado['sucesso']:
                logger.warning(f"    ⚠️  Erro: {resultado.get('erro', 'Desconhecido')}")
                return {
                    'cpf': cpf,
                    'numero_processo_cnj': numero_processo,
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro desconhecido')
                }
            
            # Extrair valores monetários
            dados = resultado['dados']
            return {
                'cpf': cpf,
                'numero_processo_cnj': numero_processo,
                'sucesso': True,
                'processo_origem': dados.get('processo_origem'),
                'requerente_caps': dados.get('requerente_caps'),
                'numero_ordem': dados.get('numero_ordem'),
                'valor_principal_liquido': float(dados.get('valor_principal_liquido') or 0),
                'valor_principal_bruto': float(dados.get('valor_principal_bruto') or 0),
                'juros_moratorios': float(dados.get('juros_moratorios') or 0),
                'valor_total_requisitado': float(dados.get('valor_total_requisitado') or 0),
                'caminho_pdf': caminho_pdf
            }
            
        except Exception as e:
            logger.error(f"    ❌ Exceção: {str(e)}")
            return {
                'cpf': cpf,
                'numero_processo_cnj': Path(caminho_pdf).stem,
                'sucesso': False,
                'erro': str(e)
            }
            
    def comparar_valores(self, processado: Dict, referencia: pd.Series) -> Dict:
        """Compara valores extraídos com CSV de referência"""
        discrepancias_encontradas = []
        
        campos_monetarios = [
            'valor_principal_liquido',
            'valor_principal_bruto',
            'juros_moratorios',
            'valor_total_requisitado'
        ]
        
        for campo in campos_monetarios:
            valor_processado = processado.get(campo, 0)
            
            # Limpar valor de referência (pode estar como string com "R$")
            valor_ref_str = str(referencia.get(campo, "0"))
            valor_ref_str = valor_ref_str.replace('R$', '').replace(' ', '').replace(',', '')
            
            try:
                valor_referencia = float(valor_ref_str) if valor_ref_str and valor_ref_str != '-' else 0
            except:
                valor_referencia = 0
            
            # Calcular diferença (tolerância de R$ 0.01)
            diferenca = abs(valor_processado - valor_referencia)
            
            if diferenca > 0.01:
                discrepancias_encontradas.append({
                    'campo': campo,
                    'valor_processado': valor_processado,
                    'valor_referencia': valor_referencia,
                    'diferenca': diferenca,
                    'percentual': (diferenca / valor_referencia * 100) if valor_referencia > 0 else 0
                })
        
        return {
            'tem_discrepancia': len(discrepancias_encontradas) > 0,
            'discrepancias': discrepancias_encontradas
        }
        
    def executar_validacao(self):
        """Executa validação completa"""
        logger.info("=" * 80)
        logger.info("VALIDAÇÃO COMPLETA DO SISTEMA OCR")
        logger.info("=" * 80)
        
        # 1. Carregar CSV de referência
        df_ref = self.carregar_csv_referencia()
        
        # 2. Listar PDFs
        pdfs = self.listar_pdfs()
        
        # 3. Processar cada PDF
        logger.info("\n" + "=" * 80)
        logger.info("PROCESSANDO PDFs")
        logger.info("=" * 80)
        
        total = len(pdfs)
        sucessos = 0
        erros = 0
        discrepancias_total = 0
        
        for idx, (cpf, caminho_pdf) in enumerate(pdfs, 1):
            logger.info(f"\n[{idx}/{total}] CPF: {cpf}")
            
            # Processar PDF
            resultado = self.processar_pdf(cpf, caminho_pdf)
            
            if not resultado['sucesso']:
                erros += 1
                self.resultados.append(resultado)
                continue
                
            sucessos += 1
            
            # Comparar com CSV de referência
            numero_processo = resultado['numero_processo_cnj']
            ref_row = df_ref[
                (df_ref['cpf'].astype(str) == cpf) & 
                (df_ref['numero_processo_cnj'] == numero_processo)
            ]
            
            if ref_row.empty:
                logger.warning(f"    ⚠️  Não encontrado no CSV de referência")
                resultado['referencia_encontrada'] = False
            else:
                resultado['referencia_encontrada'] = True
                ref_data = ref_row.iloc[0]
                
                # Comparar valores
                comparacao = self.comparar_valores(resultado, ref_data)
                resultado['comparacao'] = comparacao
                
                if comparacao['tem_discrepancia']:
                    discrepancias_total += 1
                    logger.warning(f"    🚨 DISCREPÂNCIA ENCONTRADA:")
                    for disc in comparacao['discrepancias']:
                        logger.warning(f"       • {disc['campo']}:")
                        logger.warning(f"         Processado: R$ {disc['valor_processado']:,.2f}")
                        logger.warning(f"         Referência: R$ {disc['valor_referencia']:,.2f}")
                        logger.warning(f"         Diferença: R$ {disc['diferenca']:,.2f} ({disc['percentual']:.1f}%)")
                    
                    self.discrepancias.append({
                        'cpf': cpf,
                        'numero_processo': numero_processo,
                        'caminho_pdf': caminho_pdf,
                        'discrepancias': comparacao['discrepancias']
                    })
                else:
                    logger.info(f"    ✓ Valores corretos")
            
            self.resultados.append(resultado)
        
        # 4. Gerar relatório
        self.gerar_relatorio(total, sucessos, erros, discrepancias_total)
        
    def gerar_relatorio(self, total: int, sucessos: int, erros: int, discrepancias: int):
        """Gera relatório de validação"""
        logger.info("\n" + "=" * 80)
        logger.info("RESUMO DA VALIDAÇÃO")
        logger.info("=" * 80)
        logger.info(f"Total de PDFs: {total}")
        logger.info(f"Sucessos: {sucessos} ({sucessos/total*100:.1f}%)")
        logger.info(f"Erros: {erros} ({erros/total*100:.1f}%)")
        logger.info(f"Discrepâncias: {discrepancias} ({discrepancias/sucessos*100:.1f}% dos sucessos)")
        
        # Salvar resultados em CSV
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_output = Path(__file__).parent.parent / "test_data" / f"validacao_{timestamp}.csv"
        
        df_resultados = pd.DataFrame(self.resultados)
        df_resultados.to_csv(csv_output, index=False)
        logger.info(f"\n✓ Resultados salvos em: {csv_output}")
        
        # Salvar discrepâncias em JSON
        if self.discrepancias:
            json_output = Path(__file__).parent.parent / "test_data" / f"discrepancias_{timestamp}.json"
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump(self.discrepancias, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Discrepâncias detalhadas em: {json_output}")
            
            # Listar top discrepâncias
            logger.info("\n" + "=" * 80)
            logger.info("TOP 10 MAIORES DISCREPÂNCIAS")
            logger.info("=" * 80)
            
            todas_disc = []
            for item in self.discrepancias:
                for disc in item['discrepancias']:
                    todas_disc.append({
                        'cpf': item['cpf'],
                        'processo': item['numero_processo'],
                        'campo': disc['campo'],
                        'diferenca': disc['diferenca'],
                        'percentual': disc['percentual']
                    })
            
            top_10 = sorted(todas_disc, key=lambda x: x['diferenca'], reverse=True)[:10]
            
            for idx, disc in enumerate(top_10, 1):
                logger.info(f"{idx}. {disc['cpf']}/{disc['processo']}")
                logger.info(f"   Campo: {disc['campo']}")
                logger.info(f"   Diferença: R$ {disc['diferenca']:,.2f} ({disc['percentual']:.1f}%)")
        
        logger.info("\n" + "=" * 80)
        logger.info("VALIDAÇÃO CONCLUÍDA")
        logger.info("=" * 80)


def main():
    """Função principal"""
    # Caminhos
    PASTA_CONSULTAS = Path(__file__).parent.parent.parent / "data" / "consultas"
    CSV_REFERENCIA = Path(__file__).parent.parent / "test_data" / "2025-10-31T23-26_export.csv"
    
    # Validar existência
    if not PASTA_CONSULTAS.exists():
        logger.error(f"❌ Pasta não encontrada: {PASTA_CONSULTAS}")
        sys.exit(1)
        
    if not CSV_REFERENCIA.exists():
        logger.error(f"❌ CSV não encontrado: {CSV_REFERENCIA}")
        sys.exit(1)
    
    # Executar validação
    validador = ValidadorCompleto(PASTA_CONSULTAS, CSV_REFERENCIA)
    validador.executar_validacao()


if __name__ == "__main__":
    main()

