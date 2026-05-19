"""
DetectorSaldoFinal - Detecta "Saldo Final" em PDFs de precatórios
Versão: 3.0.0
Data: 19/05/2026

V3.0.0: Novos padrões + isolamento por credor + campos de origem + fallbacks completos.
- Novo: padrões "Saldo Final em DD/MM/AA" e "Valores para Pagamento em DD/MM/AAAA"
- Novo: ResultadoSaldoFinal dataclass com campos de rastreabilidade de origem
- Novo: extrair_saldo_e_data_com_origem() com isolamento de contexto por credor
- Novo: suporte a ano com 2 dígitos (29/03/19 → 2019-03-29)
- Novo: _obter_contexto_saldo_credor() para PDFs multi-credor
V2.1.0: Prioridade ajustada - captura valor da linha TOTAL (não VALOR PRINCIPAL).
V2.0.0: Padrões regex corrigidos para detectar quebras de linha e texto intermediário.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class ResultadoSaldoFinal:
    """Resultado estruturado da extração de saldo final com rastreabilidade de origem."""
    saldo_final: Optional[Decimal] = None
    data_saldo_final: Optional[date] = None
    origem_saldo_final: Optional[str] = None
    origem_data_saldo_final: Optional[str] = None
    contexto: Optional[str] = None


class DetectorSaldoFinal:
    """
    Detector de "Saldo Final" em demonstrativos DEPRE.

    V3.0.0 — Hierarquia de detecção:
    1. SALDO FINAL APÓS O PAGAMENTO (padrões existentes V2.x)
    2. Saldo Final em DD/MM/AA(AA)  [NOVO]
    3. Valores para Pagamento em DD/MM/AAAA  [NOVO]
    4. Saldo Final genérico (fallback compatibilidade)

    Uso:
        detector = DetectorSaldoFinal()
        resultado = detector.extrair_saldo_e_data_com_origem(texto_pdf, cpf="24768225829")
    """

    def __init__(self):
        """Inicializa os padrões regex para detecção de saldo final."""

        # --- PADRÕES V2.x (SALDO FINAL APÓS O PAGAMENTO) ---

        # Pattern 1: "SALDO FINAL APÓS O PAGAMENTO" com quebra de linha (V2.0.0)
        self.pattern_saldo_apos_pag = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO\s*[\n\r\s]*'
            r'(?:.*?[\n\r])*?'
            r'(?:TOTAL|VALOR\s+PRINCIPAL)?\s*'
            r'(?:em\s+\d{2}/\d{2}/\d{4})?\s*'
            r'R?\$?\s*([\d.,]+)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        # Pattern 2: "SALDO FINAL APÓS O PAGAMENTO" + linha "TOTAL" (V2.1.0)
        # Captura TOTAL no início de linha (exclui SUB-TOTAL), formato "TOTAL\nVALOR\nR$" ou "TOTAL R$ VALOR"
        self.pattern_saldo_com_total = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO[^\n]*\n'
            r'(?:(?!SALDO\s+FINAL).){0,500}?'
            r'(?:^|\n)TOTAL\s+R?\$?\s*([\d.,]+)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        # Pattern: data "VALOR PRINCIPAL em DD/MM/YYYY" no bloco SALDO FINAL APÓS O PAGAMENTO
        self._pattern_data_saldo = re.compile(
            r'SALDO\s+FINAL\s+AP[ÓO]S\s+O?\s*PAGAMENTO.*?'
            r'VALOR\s+PRINCIPAL\s+em\s+(\d{2}/\d{2}/\d{4})',
            re.IGNORECASE | re.DOTALL
        )

        # --- PADRÕES V3.0 (NOVOS) ---

        # Pattern "Saldo Final em DD/MM/AA(AA)" + TOTAL
        # Formato multiline do DEPRE: TOTAL\n         48.783,56\nR$
        # Formato inline: TOTAL R$ 48.783,56
        # Exclusão: não cruza para outro bloco "Saldo Final em"
        self.pattern_saldo_final_em = re.compile(
            r'Saldo\s+Final\s+em\s+(\d{2}/\d{2}/\d{2,4})'
            r'(?:(?!Saldo\s+Final\s+em).){0,1500}?'
            r'(?:^|\n)\s*TOTAL\b\s*(?:R?\$\s*)?([\d.,]+)',
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        )

        # Pattern "Valores para Pagamento em DD/MM/AAAA" + TOTAL
        self.pattern_valores_para_pagamento = re.compile(
            r'Valores\s+para\s+Pagamento\s+em\s+(\d{2}/\d{2}/\d{4})'
            r'(?:(?!Valores\s+para\s+Pagamento).){0,1500}?'
            r'(?:^|\n)\s*TOTAL\b\s*(?:R?\$\s*)?([\d.,]+)',
            re.IGNORECASE | re.DOTALL | re.MULTILINE
        )

        # Pattern 3: "Saldo Final" genérico (fallback - compatibilidade)
        self.pattern_saldo_generico = re.compile(
            r'Saldo\s+[Ff]inal:?\s*R?\$?\s*([\d.,]+)',
            re.IGNORECASE
        )

        logger.info("DetectorSaldoFinal V3.0.0 inicializado (novos padrões + origem)")

    # =========================================================================
    # MÉTODO PRINCIPAL V3.0
    # =========================================================================

    def extrair_saldo_e_data_com_origem(
        self,
        texto_completo: str,
        cpf: Optional[str] = None
    ) -> ResultadoSaldoFinal:
        """
        Extrai saldo final e data com rastreabilidade de origem.

        Isola o contexto do credor (CPF) quando fornecido para evitar capturar
        dados de outro credor em PDFs multi-credor.

        Args:
            texto_completo: Texto completo extraído do PDF
            cpf: CPF do credor (com ou sem formatação) para isolamento de contexto

        Returns:
            ResultadoSaldoFinal com saldo, data e campos de origem
        """
        if not texto_completo:
            return ResultadoSaldoFinal()

        contexto = self._obter_contexto_saldo_credor(texto_completo, cpf) if cpf else texto_completo

        # Prioridade 1: SALDO FINAL APÓS O PAGAMENTO (padrão V2.x — mais específico)
        match = self.pattern_saldo_com_total.search(contexto)
        if match:
            valor = self._converter_valor_br(match.group(1))
            if valor:
                data_match = self._pattern_data_saldo.search(contexto)
                data = self._converter_data_br_2dig(data_match.group(1)) if data_match else None
                logger.info(f"💰 Saldo Final [saldo_apos_pagamento]: R$ {valor:,.2f} | data={data}")
                return ResultadoSaldoFinal(
                    saldo_final=valor,
                    data_saldo_final=data,
                    origem_saldo_final="saldo_apos_pagamento",
                    origem_data_saldo_final="valor_principal_em_no_bloco_saldo_apos_pagamento" if data else None,
                    contexto=contexto[:300]
                )

        match = self.pattern_saldo_apos_pag.search(contexto)
        if match:
            valor = self._converter_valor_br(match.group(1))
            if valor:
                data_match = self._pattern_data_saldo.search(contexto)
                data = self._converter_data_br_2dig(data_match.group(1)) if data_match else None
                logger.info(f"💰 Saldo Final [saldo_apos_pagamento_v1]: R$ {valor:,.2f} | data={data}")
                return ResultadoSaldoFinal(
                    saldo_final=valor,
                    data_saldo_final=data,
                    origem_saldo_final="saldo_apos_pagamento",
                    origem_data_saldo_final="valor_principal_em_no_bloco_saldo_apos_pagamento" if data else None,
                    contexto=contexto[:300]
                )

        # Prioridade 2: Saldo Final em DD/MM/AA(AA)
        match = self.pattern_saldo_final_em.search(contexto)
        if match:
            data = self._converter_data_br_2dig(match.group(1))
            valor = self._converter_valor_br(match.group(2))
            if valor:
                logger.info(f"💰 Saldo Final [saldo_final_em]: R$ {valor:,.2f} | data={data}")
                return ResultadoSaldoFinal(
                    saldo_final=valor,
                    data_saldo_final=data,
                    origem_saldo_final="saldo_final_em",
                    origem_data_saldo_final="titulo_saldo_final_em" if data else None,
                    contexto=contexto[:300]
                )

        # Prioridade 3: Valores para Pagamento em DD/MM/AAAA
        match = self.pattern_valores_para_pagamento.search(contexto)
        if match:
            data = self._converter_data_br_2dig(match.group(1))
            valor = self._converter_valor_br(match.group(2))
            if valor:
                logger.info(f"💰 Saldo Final [valores_para_pagamento]: R$ {valor:,.2f} | data={data}")
                return ResultadoSaldoFinal(
                    saldo_final=valor,
                    data_saldo_final=data,
                    origem_saldo_final="valores_para_pagamento",
                    origem_data_saldo_final="titulo_valores_para_pagamento" if data else None,
                    contexto=contexto[:300]
                )

        # Prioridade 4: Saldo Final genérico (fallback compatibilidade)
        match = self.pattern_saldo_generico.search(contexto)
        if match:
            valor = self._converter_valor_br(match.group(1))
            if valor:
                logger.info(f"💰 Saldo Final [saldo_final_generico]: R$ {valor:,.2f}")
                return ResultadoSaldoFinal(
                    saldo_final=valor,
                    data_saldo_final=None,
                    origem_saldo_final="saldo_final_generico",
                    origem_data_saldo_final=None,
                    contexto=contexto[:300]
                )

        logger.debug("Saldo Final não detectado (V3.0.0) — processador aplicará fallbacks")
        return ResultadoSaldoFinal()

    # =========================================================================
    # ISOLAMENTO DE CONTEXTO POR CREDOR (V3.0)
    # =========================================================================

    def _obter_contexto_saldo_credor(self, texto: str, cpf: str) -> str:
        """
        Isola o bloco de cálculo do credor alvo para evitar capturar saldo de outro credor.

        Estratégia: encontra blocos delimitados por "Calculo referente a" e retorna
        o bloco que contém o CPF. Se não houver estrutura de blocos, retorna o texto completo.

        Args:
            texto: Texto completo do PDF
            cpf: CPF do credor (com ou sem formatação)

        Returns:
            Texto do bloco isolado, ou texto completo como fallback
        """
        cpf_numerico = re.sub(r'\D', '', cpf)
        if len(cpf_numerico) < 11:
            return texto

        cpf_fmt = f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:]}"
        cpf_pattern = re.compile(
            re.escape(cpf_numerico) + '|' + re.escape(cpf_fmt),
            re.IGNORECASE
        )

        blocos_inicio = [m.start() for m in re.finditer(r'Calculo referente a', texto, re.IGNORECASE)]

        if not blocos_inicio:
            return texto

        blocos_inicio.append(len(texto))

        # Percorre os blocos e expande enquanto o bloco contiver o CPF alvo
        for i in range(len(blocos_inicio) - 1):
            chunk = texto[blocos_inicio[i]:blocos_inicio[i + 1]]
            if cpf_pattern.search(chunk):
                # Achou o bloco inicial; expande se blocos consecutivos também tiverem o CPF
                fim_idx = i + 1
                while fim_idx < len(blocos_inicio) - 1:
                    next_chunk = texto[blocos_inicio[fim_idx]:blocos_inicio[fim_idx + 1]]
                    if cpf_pattern.search(next_chunk):
                        fim_idx += 1
                    else:
                        break
                contexto = texto[blocos_inicio[i]:blocos_inicio[fim_idx]]
                logger.debug(f"Contexto isolado para CPF {cpf_fmt}: {len(contexto)} chars")
                return contexto

        # CPF não encontrado em nenhum bloco — janela ao redor da última ocorrência
        match_cpf = list(cpf_pattern.finditer(texto))
        if match_cpf:
            pos = match_cpf[-1].start()
            inicio = max(0, pos - 500)
            fim = min(len(texto), pos + 10000)
            logger.warning(f"CPF {cpf_fmt} fora de bloco 'Calculo referente a' — usando janela")
            return texto[inicio:fim]

        logger.warning(f"CPF {cpf_fmt} não encontrado no texto — usando texto completo")
        return texto

    # =========================================================================
    # MÉTODOS RETROCOMPATÍVEIS (V2.x)
    # =========================================================================

    def extrair_saldo_final(self, texto_completo: str) -> Optional[Decimal]:
        """
        Extrai valor de "Saldo Final" do texto completo do PDF.
        Mantido para compatibilidade — internamente chama extrair_saldo_e_data_com_origem().
        """
        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção de saldo final")
            return None
        resultado = self.extrair_saldo_e_data_com_origem(texto_completo)
        return resultado.saldo_final

    def extrair_saldo_e_data(self, texto_completo: str) -> Tuple[Optional[Decimal], Optional[date]]:
        """
        Extrai saldo final e data.
        Mantido para compatibilidade — internamente chama extrair_saldo_e_data_com_origem().
        """
        resultado = self.extrair_saldo_e_data_com_origem(texto_completo)
        return resultado.saldo_final, resultado.data_saldo_final

    def extrair_saldo_com_contexto(self, texto_completo: str) -> Dict[str, Any]:
        """
        Extrai saldo final e retorna contexto para validação.
        Mantido para compatibilidade.
        """
        resultado = self.extrair_saldo_e_data_com_origem(texto_completo)
        return {
            'saldo_final': resultado.saldo_final,
            'contexto': resultado.contexto
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _converter_data_br_2dig(self, data_str: str) -> Optional[date]:
        """
        Converte data no formato DD/MM/YYYY ou DD/MM/YY para objeto date Python.

        Regra para ano com 2 dígitos:
          00-49 → 2000-2049
          50-99 → 1950-1999

        Args:
            data_str: String com data (ex: "28/12/2023" ou "29/03/19")

        Returns:
            date ou None se conversão falhar
        """
        try:
            partes = data_str.strip().split('/')
            if len(partes) != 3:
                return None
            dia, mes, ano_str = partes
            ano = int(ano_str)
            if len(ano_str) == 2:
                ano = 2000 + ano if ano < 50 else 1900 + ano
            return date(ano, int(mes), int(dia))
        except Exception as e:
            logger.error(f"Erro ao converter data '{data_str}': {e}")
            return None

    def _converter_data_br(self, data_str: str) -> Optional[date]:
        """Converte data DD/MM/YYYY. Mantido para compatibilidade."""
        return self._converter_data_br_2dig(data_str)

    def _converter_valor_br(self, valor_str: str) -> Optional[Decimal]:
        """
        Converte valor monetário brasileiro (formato: 1.234,56) para Decimal.

        Examples:
            "62.606,38" → Decimal('62606.38')
            "1.234.567,89" → Decimal('1234567.89')
        """
        try:
            valor_limpo = valor_str.strip()
            if ',' in valor_limpo:
                valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            elif '.' in valor_limpo and valor_limpo.count('.') > 1:
                partes = valor_limpo.split('.')
                valor_limpo = ''.join(partes[:-1]) + '.' + partes[-1]

            valor_decimal = Decimal(valor_limpo)

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
        """
        testes = {
            'pattern_apos_pag_v2': False,
            'pattern_saldo_com_total_v2': False,
            'pattern_saldo_final_em': False,
            'pattern_valores_para_pagamento': False,
            'pattern_generico': False,
            'conversao_valor': False,
            'conversao_data_2dig': False,
        }

        texto_v2 = "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL em 23/05/2025  R$ 51.435,50"
        if self.pattern_saldo_apos_pag.search(texto_v2):
            testes['pattern_apos_pag_v2'] = True

        texto_total = "SALDO FINAL APÓS O PAGAMENTO\nVALOR PRINCIPAL  R$ 168.217,53\nTOTAL  R$ 243.228,11"
        if self.pattern_saldo_com_total.search(texto_total):
            testes['pattern_saldo_com_total_v2'] = True

        texto_sfe = "Saldo Final em 29/03/19\nVALOR PRINCIPAL em 29/03/2019\n         34.169,63\nR$\nSUB-TOTAL\n         34.169,63\nR$\nJUROS MORATÓRIOS\n         14.613,93\nR$\nTOTAL\n         48.783,56\nR$"
        if self.pattern_saldo_final_em.search(texto_sfe):
            testes['pattern_saldo_final_em'] = True

        texto_vpp = "Valores para Pagamento em 29/03/2019\nVALOR PRINCIPAL\n         34.169,63\nR$\nTOTAL\n         48.783,56\nR$"
        if self.pattern_valores_para_pagamento.search(texto_vpp):
            testes['pattern_valores_para_pagamento'] = True

        if self.pattern_saldo_generico.search("Saldo Final: R$ 1.234,56"):
            testes['pattern_generico'] = True

        valor = self._converter_valor_br("62.606,38")
        if valor and valor == Decimal('62606.38'):
            testes['conversao_valor'] = True

        d = self._converter_data_br_2dig("29/03/19")
        if d and d == date(2019, 3, 29):
            testes['conversao_data_2dig'] = True

        logger.info(f"Validação de padrões V3.0.0: {testes}")
        return testes
