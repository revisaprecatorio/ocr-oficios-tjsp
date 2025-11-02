"""
Test Script: FASE 1 - Casos Críticos (5 PDFs)

Testa ProcessadorOficio V3 nos 5 casos mais críticos onde V2.5.1 falhou.

Objetivo: Resolver ≥3 de 5 casos (60% mínimo)

Casos:
1. 0176088-13.2021 - Ponto decimal (99.9% erro) ← OBRIGATÓRIO
2. 0064242-25.2020 - Inversão líquido/bruto (39% erro)
3. 7002920-94.2011 - Parsing incorreto (90% erro)
4. 7007859-54.2010 - Juros não capturados (13% erro)
5. 7009758-92.2007 - Valor não capturado (100% erro)
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from decimal import Decimal
import pandas as pd

# Adicionar path do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / "1_parsing_PDF"
sys.path.insert(0, str(PROJECT_ROOT))

# Carregar variáveis de ambiente
from dotenv import load_dotenv
ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

# Importar processador (V3 = versão com prompt melhorado)
from app.processador import ProcessadorOficio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestadorCasosCriticos:
    """Testador para os 5 casos críticos da FASE 1"""
    
    # Definir casos críticos com valores esperados CORRETOS (do PDF)
    CASOS_CRITICOS = [
        {
            'id': 1,
            'cpf': '94706751853',
            'processo': '0176088-13.2021.8.26.0500',
            'nome': 'Caso #4 - Ponto decimal (CRÍTICO)',
            'valor_esperado_liquido': 73431.66,  # Valor CORRETO do PDF
            'valor_esperado_bruto': 73431.66,
            'valor_esperado_total': 73431.66,
            'tipo_erro': 'ponto_decimal',
            'prioridade': 'MÁXIMA',
            'v2_falhou': True,
            'v3_deve_resolver': True
        },
        {
            'id': 2,
            'cpf': '10732506875',
            'processo': '0064242-25.2020.8.26.0500',
            'nome': 'Caso #2 - Inversão líquido/bruto',
            'valor_esperado_liquido': 190221.42,  # Valor CORRETO
            'valor_esperado_bruto': 311369.53,    # Valor CORRETO
            'valor_esperado_total': None,  # A determinar do PDF
            'tipo_erro': 'inversao',
            'prioridade': 'ALTA',
            'v2_falhou': True,
            'v3_deve_resolver': True
        },
        {
            'id': 3,
            'cpf': '51525003968',
            'processo': '7002920-94.2011.8.26.0500',
            'nome': 'Caso #3 - Parsing incorreto (90% erro)',
            'valor_esperado_liquido': 177969.22,  # Valor CORRETO
            'valor_esperado_bruto': 179769.22,     # Valor CORRETO
            'valor_esperado_total': 179769.22,
            'tipo_erro': 'parsing_truncado',
            'prioridade': 'ALTA',
            'v2_falhou': True,
            'v3_deve_resolver': True
        },
        {
            'id': 4,
            'cpf': '10155175874',
            'processo': '7007859-54.2010.8.26.0500',
            'nome': 'Caso #1 - Juros não capturados (356 pgs)',
            'valor_esperado_liquido': None,  # A determinar
            'valor_esperado_bruto': 1097665.34,
            'valor_esperado_total': 1253909.97,  # Total CORRETO (com juros)
            'tipo_erro': 'contexto_longo',
            'prioridade': 'MÉDIA',
            'v2_falhou': True,
            'v3_deve_resolver': False  # Melhoria parcial esperada
        },
        {
            'id': 5,
            'cpf': '93661509853',
            'processo': '7009758-92.2007.8.26.0500',
            'nome': 'Caso #5 - Valor não capturado',
            'valor_esperado_liquido': 1125.0,  # Valor CORRETO
            'valor_esperado_bruto': None,
            'valor_esperado_total': None,
            'tipo_erro': 'valor_ausente',
            'prioridade': 'MÉDIA',
            'v2_falhou': True,
            'v3_deve_resolver': False  # Melhoria parcial esperada
        }
    ]
    
    def __init__(self):
        """Inicializa testador"""
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.data_dir = self.base_dir / "data" / "consultas"
        self.resultados_dir = Path(__file__).parent.parent / "resultados"
        self.resultados_dir.mkdir(exist_ok=True)
        
        # Configurar processador V3
        self.processador_v3 = ProcessadorOficio(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            db_config={
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT'),
                'name': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }  # NÃO gravar no banco
        )
        
        self.resultados = []
    
    def encontrar_pdf(self, cpf: str, processo: str) -> Path:
        """Encontra PDF no diretório de dados"""
        pdf_path = self.data_dir / cpf / f"{processo}.pdf"
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")
        
        return pdf_path
    
    def processar_caso(self, caso: Dict) -> Dict:
        """Processa um caso crítico com V3"""
        logger.info("=" * 80)
        logger.info(f"🧪 TESTANDO: {caso['nome']}")
        logger.info(f"   CPF: {caso['cpf']}")
        logger.info(f"   Processo: {caso['processo']}")
        logger.info(f"   Prioridade: {caso['prioridade']}")
        logger.info("=" * 80)
        
        # Encontrar PDF
        try:
            pdf_path = self.encontrar_pdf(caso['cpf'], caso['processo'])
            logger.info(f"📄 PDF encontrado: {pdf_path}")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return {
                'caso': caso,
                'sucesso': False,
                'erro': str(e),
                'valores_extraidos': None
            }
        
        # Processar com V3
        try:
            inicio = datetime.now()
            
            resultado = self.processador_v3.processar_arquivo(
                pdf_path=str(pdf_path),
                cpf_numerico=caso['cpf']
            )
            
            tempo_processamento = (datetime.now() - inicio).total_seconds()
            
            if not resultado or 'dados' not in resultado:
                logger.error("❌ Processamento falhou")
                return {
                    'caso': caso,
                    'sucesso': False,
                    'erro': 'Processamento retornou None',
                    'valores_extraidos': None,
                    'tempo': tempo_processamento
                }
            
            # Extrair valores
            dados = resultado['dados']
            valores_extraidos = {
                'liquido': dados.get('valor_principal_liquido'),
                'bruto': dados.get('valor_principal_bruto'),
                'juros': dados.get('juros_moratorios'),
                'total': dados.get('valor_total_requisitado')
            }
            
            # Verificar alertas de sanidade
            alertas = resultado.get('_alertas_sanidade', [])
            
            logger.info("")
            logger.info("📊 VALORES EXTRAÍDOS:")
            logger.info(f"   Líquido: R$ {valores_extraidos['liquido']:,.2f}" if valores_extraidos['liquido'] else "   Líquido: None")
            logger.info(f"   Bruto: R$ {valores_extraidos['bruto']:,.2f}" if valores_extraidos['bruto'] else "   Bruto: None")
            logger.info(f"   Juros: R$ {valores_extraidos['juros']:,.2f}" if valores_extraidos['juros'] else "   Juros: None")
            logger.info(f"   Total: R$ {valores_extraidos['total']:,.2f}" if valores_extraidos['total'] else "   Total: None")
            
            if alertas:
                logger.info("")
                logger.info("🚨 ALERTAS DE SANIDADE:")
                for alerta in alertas:
                    logger.info(f"   {alerta}")
            
            # Verificar se resolveu o problema
            sucesso = self._verificar_sucesso(caso, valores_extraidos)
            
            resultado_teste = {
                'caso': caso,
                'sucesso': sucesso,
                'valores_extraidos': valores_extraidos,
                'valores_esperados': {
                    'liquido': caso['valor_esperado_liquido'],
                    'bruto': caso['valor_esperado_bruto'],
                    'total': caso['valor_esperado_total']
                },
                'alertas_sanidade': alertas,
                'tempo_processamento': tempo_processamento,
                'erro': None
            }
            
            logger.info("")
            if sucesso:
                logger.info("✅ CASO RESOLVIDO!")
            else:
                logger.info("❌ CASO NÃO RESOLVIDO")
            
            logger.info(f"⏱️  Tempo: {tempo_processamento:.2f}s")
            logger.info("=" * 80)
            
            return resultado_teste
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar: {e}", exc_info=True)
            return {
                'caso': caso,
                'sucesso': False,
                'erro': str(e),
                'valores_extraidos': None
            }
    
    def _verificar_sucesso(self, caso: Dict, valores_extraidos: Dict) -> bool:
        """
        Verifica se V3 resolveu o problema do caso.
        
        Critérios:
        - Valores corretos (tolerância de 1%)
        - Sem inversão líquido/bruto
        - Sem valores truncados
        """
        # Se não tem valor esperado, não pode verificar
        if caso['valor_esperado_liquido'] is None and caso['valor_esperado_bruto'] is None:
            return False
        
        tolerancia = 0.01  # 1%
        
        # Verificar líquido
        if caso['valor_esperado_liquido'] is not None:
            liquido_extraido = valores_extraidos.get('liquido', 0)
            if liquido_extraido:
                diferenca_pct = abs(liquido_extraido - caso['valor_esperado_liquido']) / caso['valor_esperado_liquido']
                if diferenca_pct > tolerancia:
                    return False
            else:
                return False
        
        # Verificar bruto
        if caso['valor_esperado_bruto'] is not None:
            bruto_extraido = valores_extraidos.get('bruto', 0)
            if bruto_extraido:
                diferenca_pct = abs(bruto_extraido - caso['valor_esperado_bruto']) / caso['valor_esperado_bruto']
                if diferenca_pct > tolerancia:
                    return False
            else:
                return False
        
        # Verificar se não há inversão
        liquido = valores_extraidos.get('liquido', 0)
        bruto = valores_extraidos.get('bruto', 0)
        if liquido > 0 and bruto > 0 and liquido > bruto:
            return False  # Invertido
        
        return True
    
    def executar_fase_1(self):
        """Executa todos os 5 casos críticos"""
        logger.info("\n" + "=" * 80)
        logger.info("🚀 INICIANDO FASE 1: CASOS CRÍTICOS (5 PDFs)")
        logger.info("=" * 80)
        logger.info(f"Data: {datetime.now().strftime('%d/%11/%Y %H:%M:%S')}")
        logger.info(f"Versão: ProcessadorOficio V3 DEFINITIVA")
        logger.info(f"Modo: TESTE (não grava no banco)")
        logger.info("=" * 80)
        
        # Processar cada caso
        for caso in self.CASOS_CRITICOS:
            resultado = self.processar_caso(caso)
            self.resultados.append(resultado)
        
        # Gerar relatório
        self._gerar_relatorio()
    
    def _gerar_relatorio(self):
        """Gera relatório consolidado da FASE 1"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 RELATÓRIO FINAL - FASE 1: CASOS CRÍTICOS")
        logger.info("=" * 80)
        
        total_casos = len(self.resultados)
        casos_resolvidos = sum(1 for r in self.resultados if r['sucesso'])
        taxa_sucesso = (casos_resolvidos / total_casos) * 100 if total_casos > 0 else 0
        
        logger.info(f"Total de casos testados: {total_casos}")
        logger.info(f"Casos resolvidos: {casos_resolvidos}")
        logger.info(f"Taxa de sucesso: {taxa_sucesso:.1f}%")
        logger.info("")
        
        # Detalhar cada caso
        for i, resultado in enumerate(self.resultados, 1):
            caso = resultado['caso']
            logger.info(f"{i}. {caso['nome']}")
            logger.info(f"   Processo: {caso['processo']}")
            logger.info(f"   Status: {'✅ RESOLVIDO' if resultado['sucesso'] else '❌ NÃO RESOLVIDO'}")
            
            if resultado['valores_extraidos']:
                vals = resultado['valores_extraidos']
                logger.info(f"   Valores: L={vals['liquido']:.2f if vals['liquido'] else 'N/A'} | "
                          f"B={vals['bruto']:.2f if vals['bruto'] else 'N/A'} | "
                          f"T={vals['total']:.2f if vals['total'] else 'N/A'}")
            
            if resultado.get('alertas_sanidade'):
                logger.info(f"   Alertas: {len(resultado['alertas_sanidade'])}")
            
            logger.info("")
        
        # Verificar critério mínimo de aprovação
        logger.info("=" * 80)
        if taxa_sucesso >= 60:
            logger.info("✅ FASE 1 APROVADA! (Taxa de sucesso ≥ 60%)")
            logger.info("   Pode prosseguir para FASE 2 (PDFs aleatórios)")
        else:
            logger.info("❌ FASE 1 REPROVADA (Taxa de sucesso < 60%)")
            logger.info("   Necessário revisar implementação V3")
        logger.info("=" * 80)
        
        # Salvar resultados em JSON
        self._salvar_resultados_json()
    
    def _salvar_resultados_json(self):
        """Salva resultados em arquivo JSON"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_file = self.resultados_dir / f"fase1_criticos_{timestamp}.json"
        
        # Converter Decimal para float para JSON
        resultados_json = []
        for r in self.resultados:
            r_copy = r.copy()
            if r_copy['valores_extraidos']:
                for k, v in r_copy['valores_extraidos'].items():
                    if isinstance(v, Decimal):
                        r_copy['valores_extraidos'][k] = float(v)
            resultados_json.append(r_copy)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'versao': 'V3_DEFINITIVA',
                'fase': 1,
                'total_casos': len(resultados_json),
                'casos_resolvidos': sum(1 for r in resultados_json if r['sucesso']),
                'resultados': resultados_json
            }, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"\n📄 Resultados salvos em: {output_file}")


def main():
    """Função principal"""
    testador = TestadorCasosCriticos()
    testador.executar_fase_1()


if __name__ == "__main__":
    main()

