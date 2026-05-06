"""
DetectorSaldoFinal - Detecta "Saldo Final" em PDFs de precatórios
Versão: 2.1.0
Data: 14/03/2026

Detecta valor de "Saldo Final" após pagamentos parciais em documentos DEPRE.
V2.1.0: Prioridade ajustada - captura valor da linha TOTAL (não VALOR PRINCIPAL).
V2.0.0: Padrões regex corrigidos para detectar quebras de linha e texto intermediário.
Se não encontrado, o processador usará fallback (valor_total_requisitado).
"""

import re
import logging
from datetime import date
from typing import Optional, Dict, Any, Tuple
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

        # Pattern 1: "SALDO FINAL APÓS O PAGAMENTO" com quebra de linha (V2.0.0)
        # Matches: "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL em 23/05/2025  R$ 51.435,50"
        # Aceita quebras de linha, texto intermediário e variações de formatação
        self.pattern_saldo_apos_pag = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO\s*[\n\r\s]*'  # Título
            r'(?:.*?[\n\r])*?'  # Linhas intermediárias (opcional)
            r'(?:TOTAL|VALOR\s+PRINCIPAL)?\s*'  # Pode ter "TOTAL" ou "VALOR PRINCIPAL"
            r'(?:em\s+\d{2}/\d{2}/\d{4})?\s*'  # Data opcional (DD/MM/YYYY)
            r'R?\$?\s*([\d.,]+)',  # Valor
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        # Pattern 2: "SALDO FINAL APÓS O PAGAMENTO" + "TOTAL" (V2.1.0)
        # Matches: "SALDO FINAL APÓS O PAGAMENTO\n...\nTOTAL  R$ 243.228,11"
        # Limitado a 500 caracteres após título para evitar capturar TOTAL de outras seções
        # Usa word boundary para evitar capturar SUB-TOTAL
        self.pattern_saldo_com_total = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO[^\n]*\n'  # Título completo
            r'(?:(?!SALDO\s+FINAL).){0,500}?'  # Até 500 chars, sem outro SALDO FINAL
            r'(?:^|\n)TOTAL\s+R?\$?\s*([\d.,]+)',  # TOTAL no início da linha (não SUB-TOTAL)
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        # Pattern 4: Data base na linha "VALOR PRINCIPAL em DD/MM/YYYY" dentro da seção SALDO FINAL
        # Matches: "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL em 28/12/2023  R$ ..."
        self._pattern_data_saldo = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO.*?'
            r'VALOR\s+PRINCIPAL\s+em\s+(\d{2}/\d{2}/\d{4})',
            re.IGNORECASE | re.DOTALL
        )

        # Pattern 3: "Saldo Final" genérico (fallback - mantido para compatibilidade)
        # Matches: "Saldo Final: R$ 62.606,38", "SALDO FINAL R$ 62606.38"
        self.pattern_saldo_generico = re.compile(
            r'Saldo\s+[Ff]inal:?\s*R?\$?\s*([\d.,]+)',
            re.IGNORECASE
        )

        logger.info("DetectorSaldoFinal V2.1.0 inicializado (prioridade TOTAL)")

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

        # V2.1.0: PRIORIDADE 1 - Pattern 2 (SALDO FINAL + TOTAL)
        # Busca linha "TOTAL" após "SALDO FINAL APÓS O PAGAMENTO"
        match = self.pattern_saldo_com_total.search(texto_completo)
        if match:
            valor_str = match.group(1)
            valor_decimal = self._converter_valor_br(valor_str)
            if valor_decimal:
                logger.info(f"💰 Saldo Final detectado (V2.1.0 - SALDO FINAL + TOTAL): R$ {valor_decimal:,.2f}")
                return valor_decimal

        # V2.0.0: PRIORIDADE 2 - Pattern 1 (VALOR PRINCIPAL - fallback)
        # Usado quando não há linha TOTAL
        match = self.pattern_saldo_apos_pag.search(texto_completo)
        if match:
            valor_str = match.group(1)
            valor_decimal = self._converter_valor_br(valor_str)
            if valor_decimal:
                logger.info(f"💰 Saldo Final detectado (V2.0.0 - VALOR PRINCIPAL): R$ {valor_decimal:,.2f}")
                return valor_decimal

        # Pattern 3: Genérico (fallback - compatibilidade)
        match = self.pattern_saldo_generico.search(texto_completo)
        if match:
            valor_str = match.group(1)
            valor_decimal = self._converter_valor_br(valor_str)
            if valor_decimal:
                logger.info(f"💰 Saldo Final detectado (genérico - fallback): R$ {valor_decimal:,.2f}")
                return valor_decimal

        # Nenhum padrão encontrado
        logger.debug("Saldo Final não detectado no PDF (V2.1.0)")
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

        # V2.1.0: Buscar com Pattern 2 PRIMEIRO (TOTAL)
        match = self.pattern_saldo_com_total.search(texto_completo)
        if not match:
            # Tentar Pattern 1 (VALOR PRINCIPAL - fallback)
            match = self.pattern_saldo_apos_pag.search(texto_completo)
        if not match:
            # Tentar Pattern 3 (genérico - fallback)
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

    def extrair_saldo_e_data(self, texto_completo: str) -> Tuple[Optional[Decimal], Optional[date]]:
        """
        Extrai saldo final E data base da seção SALDO FINAL APÓS O PAGAMENTO.

        A data corresponde à linha "VALOR PRINCIPAL em DD/MM/YYYY" dentro da seção.
        O método `extrair_saldo_final()` existente não é modificado.

        Args:
            texto_completo: Texto completo extraído do PDF

        Returns:
            Tuple (saldo: Optional[Decimal], data_saldo: Optional[date])
            Se saldo não detectado: (None, None)
            Se saldo detectado mas data ausente: (saldo, None)
        """
        saldo = self.extrair_saldo_final(texto_completo)
        if not saldo or not texto_completo:
            return None, None

        data_saldo = None
        match_data = self._pattern_data_saldo.search(texto_completo)
        if match_data:
            data_saldo = self._converter_data_br(match_data.group(1))
            if data_saldo:
                logger.info(f"📅 Data saldo final detectada: {data_saldo}")
            else:
                logger.warning(f"⚠️ Data saldo final encontrada mas não convertida: {match_data.group(1)}")
        else:
            logger.debug("Data base do saldo final não detectada no PDF")

        return saldo, data_saldo

    def _converter_data_br(self, data_str: str) -> Optional[date]:
        """
        Converte data no formato DD/MM/YYYY para objeto date Python.

        Args:
            data_str: String com data (ex: "28/12/2023")

        Returns:
            date ou None se conversão falhar
        """
        try:
            dia, mes, ano = data_str.strip().split('/')
            return date(int(ano), int(mes), int(dia))
        except Exception as e:
            logger.error(f"Erro ao converter data '{data_str}': {e}")
            return None

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
            'pattern_apos_pag_v2': False,
            'pattern_saldo_com_total_v2': False,
            'pattern_generico': False,
            'conversao_valor': False
        }

        # Testar Pattern 1 V2.0.0 (com quebra de linha)
        texto_teste_v2 = "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL em 23/05/2025  R$ 51.435,50"
        if self.pattern_saldo_apos_pag.search(texto_teste_v2):
            testes['pattern_apos_pag_v2'] = True

        # Testar Pattern 2 V2.0.0 (SALDO FINAL + TOTAL)
        texto_teste_total = "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL  R$ 168.217,53\nTOTAL  R$ 243.228,11"
        if self.pattern_saldo_com_total.search(texto_teste_total):
            testes['pattern_saldo_com_total_v2'] = True

        # Testar Pattern 3 (genérico - fallback)
        texto_teste = "Saldo Final: R$ 1.234,56"
        if self.pattern_saldo_generico.search(texto_teste):
            testes['pattern_generico'] = True

        # Testar conversão
        valor = self._converter_valor_br("62.606,38")
        if valor and valor == Decimal('62606.38'):
            testes['conversao_valor'] = True

        logger.info(f"Validação de padrões: {testes}")
        return testes
