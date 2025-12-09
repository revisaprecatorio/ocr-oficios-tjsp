"""
DetectorSaldoFinal - Detecta "Saldo Final" em PDFs de precatórios
Versão: 1.0.0
Data: 04/12/2025

Detecta valor de "Saldo Final" após pagamentos parciais em documentos DEPRE.
Se não encontrado, o processador usará fallback (valor_total_requisitado).
"""

import re
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class DetectorSaldoFinal:
    """
    Detector de "Saldo Final" em demonstrativos DEPRE.

    Busca padrões como:
    - "Saldo final após pagamento: R$ XX.XXX,XX"
    - "Saldo Final: R$ XX.XXX,XX"
    - Tabelas DEPRE com coluna "Saldo Final"

    Uso:
        detector = DetectorSaldoFinal()
        saldo = detector.extrair_saldo_final(texto_pdf)
    """

    def __init__(self):
        """Inicializa os padrões regex para detecção de saldo final."""

        # Pattern 1: "Saldo final após pagamento" (mais comum)
        # Matches: "Saldo final após pagamento: R$ 62.606,38"
        self.pattern_saldo_apos_pag = re.compile(
            r'Saldo\s+[Ff]inal\s+após\s+pagamento:?\s*R?\$?\s*([\d.,]+)',
            re.IGNORECASE
        )

        # Pattern 2: "Saldo Final" genérico
        # Matches: "Saldo Final: R$ 62.606,38", "SALDO FINAL R$ 62606.38"
        self.pattern_saldo_generico = re.compile(
            r'Saldo\s+[Ff]inal:?\s*R?\$?\s*([\d.,]+)',
            re.IGNORECASE
        )

        # Pattern 3: Tabela DEPRE (formato estruturado)
        # Busca por linhas com "Saldo" e valor monetário próximo
        self.pattern_tabela_depre = re.compile(
            r'(?:Saldo|SALDO).*?R?\$?\s*([\d.,]+)',
            re.IGNORECASE
        )

        logger.info("DetectorSaldoFinal inicializado")

    def extrair_saldo_final(self, texto_completo: str) -> Optional[Decimal]:
        """
        Extrai valor de "Saldo Final" do texto completo do PDF.

        Args:
            texto_completo: Texto completo extraído do PDF

        Returns:
            Decimal com o valor do saldo final, ou None se não encontrado

        Example:
            >>> detector = DetectorSaldoFinal()
            >>> texto = "Saldo final após pagamento: R$ 62.606,38"
            >>> saldo = detector.extrair_saldo_final(texto)
            >>> print(saldo)
            Decimal('62606.38')
        """
        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção de saldo final")
            return None

        # Tentar Pattern 1 (mais específico)
        match = self.pattern_saldo_apos_pag.search(texto_completo)
        if match:
            valor_str = match.group(1)
            valor_decimal = self._converter_valor_br(valor_str)
            if valor_decimal:
                logger.info(f"💰 Saldo Final detectado (após pagamento): R$ {valor_decimal:,.2f}")
                return valor_decimal

        # Tentar Pattern 2 (genérico)
        match = self.pattern_saldo_generico.search(texto_completo)
        if match:
            valor_str = match.group(1)
            valor_decimal = self._converter_valor_br(valor_str)
            if valor_decimal:
                logger.info(f"💰 Saldo Final detectado (genérico): R$ {valor_decimal:,.2f}")
                return valor_decimal

        # Nenhum padrão encontrado
        logger.debug("Saldo Final não detectado no PDF")
        return None

    def extrair_saldo_com_contexto(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extrai saldo final E retorna contexto (snippet) para validação.

        Args:
            texto_completo: Texto completo extraído do PDF

        Returns:
            Dict com valor e contexto:
            {
                'saldo_final': Decimal ou None,
                'contexto': str com snippet onde foi encontrado
            }
        """
        resultado = {
            'saldo_final': None,
            'contexto': None
        }

        if not texto_completo:
            return resultado

        # Buscar com Pattern 1
        match = self.pattern_saldo_apos_pag.search(texto_completo)
        if not match:
            # Tentar Pattern 2
            match = self.pattern_saldo_generico.search(texto_completo)

        if match:
            # Extrair valor
            valor_str = match.group(1)
            resultado['saldo_final'] = self._converter_valor_br(valor_str)

            # Extrair contexto (100 chars antes e depois)
            inicio = max(0, match.start() - 100)
            fim = min(len(texto_completo), match.end() + 100)
            resultado['contexto'] = texto_completo[inicio:fim].strip()

            logger.debug(f"Contexto saldo final: {resultado['contexto'][:150]}...")

        return resultado

    def _converter_valor_br(self, valor_str: str) -> Optional[Decimal]:
        """
        Converte valor monetário brasileiro (formato: 1.234,56) para Decimal.

        Args:
            valor_str: String com valor (ex: "62.606,38", "1234,56")

        Returns:
            Decimal ou None se conversão falhar

        Examples:
            "62.606,38" → Decimal('62606.38')
            "1.234.567,89" → Decimal('1234567.89')
            "62606,38" → Decimal('62606.38')
        """
        try:
            # Limpar espaços
            valor_limpo = valor_str.strip()

            # Remover pontos de milhar e converter vírgula para ponto
            if ',' in valor_limpo:
                # Formato brasileiro: 1.234,56
                valor_limpo = valor_limpo.replace('.', '')  # Remove pontos de milhar
                valor_limpo = valor_limpo.replace(',', '.')  # Converte vírgula em ponto
            elif '.' in valor_limpo and valor_limpo.count('.') > 1:
                # Múltiplos pontos = milhares (ex: 1.234.567)
                partes = valor_limpo.split('.')
                valor_limpo = ''.join(partes[:-1]) + '.' + partes[-1]

            # Converter para Decimal
            valor_decimal = Decimal(valor_limpo)

            # Validar se é um valor razoável (>= R$ 0,01 e <= R$ 100 milhões)
            if valor_decimal < Decimal('0.01') or valor_decimal > Decimal('100000000'):
                logger.warning(f"Valor fora do range esperado: R$ {valor_decimal:,.2f}")
                return None

            return valor_decimal

        except Exception as e:
            logger.error(f"Erro ao converter valor '{valor_str}': {e}")
            return None

    def validar_padroes(self) -> Dict[str, bool]:
        """
        Valida se os padrões regex estão funcionando corretamente.
        Útil para testes e debugging.

        Returns:
            Dict com resultado dos testes para cada padrão
        """
        testes = {
            'pattern_apos_pag': False,
            'pattern_generico': False,
            'conversao_valor': False
        }

        # Testar Pattern 1
        texto_teste = "Saldo final após pagamento: R$ 62.606,38"
        if self.pattern_saldo_apos_pag.search(texto_teste):
            testes['pattern_apos_pag'] = True

        # Testar Pattern 2
        texto_teste = "Saldo Final: R$ 1.234,56"
        if self.pattern_saldo_generico.search(texto_teste):
            testes['pattern_generico'] = True

        # Testar conversão
        valor = self._converter_valor_br("62.606,38")
        if valor and valor == Decimal('62606.38'):
            testes['conversao_valor'] = True

        logger.info(f"Validação de padrões: {testes}")
        return testes
