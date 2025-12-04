"""
DetectorHabilitacaoHerdeiros - Detector de Habilitação de Herdeiros V2.5.3
Versão: 1.0.0
Data: 04/12/2025

Detecta casos de óbito com herdeiros habilitados através do código 9270
e estrutura "Dados da Sucessão" do TERMO DE DECLARAÇÃO do e-SAJ.
"""

import re
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DetectorHabilitacaoHerdeiros:
    """
    Detector especializado para casos de habilitação de herdeiros em precatórios.

    Baseado no TERMO DE DECLARAÇÃO do e-SAJ que contém:
    - Código de petição: 9270 - Habilitação de Herdeiro de Precatório
    - Seção estruturada: "Dados da Sucessão"
    - Informações do requerente falecido
    - Informações do sucessor (herdeiro habilitado)

    Retorna níveis de confiança:
    - ALTA: Código 9270 + estrutura completa
    - MÉDIA: 2+ indicadores sem código explícito
    - BAIXA: 1 indicador apenas
    """

    # Padrões de ALTA confiança (código 9270 + estrutura)
    PADROES_ALTA_CONFIANCA = [
        r'9270\s*-\s*Habilita[çc][ãa]o\s+de\s+Herdeiro',
        r'Tipo\s+de\s+peti[çc][ãa]o:\s*9270',
        r'9270.*Herdeiro.*Precat[óo]rio',
    ]

    # Padrões de MÉDIA confiança
    PADROES_MEDIA_CONFIANCA = [
        r'Dados\s+da\s+Sucess[ãa]o',
        r'Sucessor:',
        r'Habilita[çc][ãa]o\s+de\s+Herdeiro',
        r'Data\s+de\s+[óo]bito:',
    ]

    # Padrões de BAIXA confiança (amplos)
    PADROES_BAIXA_CONFIANCA = [
        r'herdeiros?\s+habilitad[oa]s?',
        r'habilitad[oa]s?\s+herdeiros?',
        r'sucess[ãa]o',
        r'esp[óo]lio',
    ]

    # Padrões para detecção de óbito
    PADROES_OBITO = [
        r'[óo]bito',
        r'falecimento',
        r'falecid[oa]',
        r'de\s+cujus',
        r'autor\s+falecid[oa]',
        r'requerente\s+falecid[oa]',
    ]

    def __init__(self):
        """Inicializa o detector de habilitação de herdeiros."""
        logger.info("DetectorHabilitacaoHerdeiros v1.0 inicializado")

    def detectar(self, texto: str) -> Dict[str, any]:
        """
        Detecta habilitação de herdeiros no texto do PDF.

        Args:
            texto: Texto completo do PDF ou seção relevante

        Returns:
            Dicionário com:
            - habilitacao_herdeiros: bool
            - obito: bool
            - nivel_confianca: str ('ALTA', 'MÉDIA', 'BAIXA', None)
            - data_obito: str (formato DD/MM/YYYY) ou None
            - cpf_sucessor: str (formato XXX.XXX.XXX-XX) ou None
        """
        resultado = {
            'habilitacao_herdeiros': False,
            'obito': False,
            'nivel_confianca': None,
            'data_obito': None,
            'cpf_sucessor': None
        }

        # 1. Verificar padrões de ALTA confiança (código 9270)
        for padrao in self.PADROES_ALTA_CONFIANCA:
            if re.search(padrao, texto, re.IGNORECASE | re.MULTILINE):
                logger.info(f"✅ Código 9270 detectado (ALTA confiança): {padrao}")
                resultado['habilitacao_herdeiros'] = True
                resultado['obito'] = True
                resultado['nivel_confianca'] = 'ALTA'

                # Extrair informações adicionais
                self._extrair_detalhes_habilitacao(texto, resultado)

                return resultado

        # 2. Verificar padrões de MÉDIA confiança (estrutura sem código)
        matches_media = 0
        for padrao in self.PADROES_MEDIA_CONFIANCA:
            if re.search(padrao, texto, re.IGNORECASE | re.MULTILINE):
                matches_media += 1
                logger.debug(f"   Match MÉDIA confiança: {padrao}")

        if matches_media >= 2:
            logger.info(f"✅ Habilitação detectada (MÉDIA confiança): {matches_media} indicadores")
            resultado['habilitacao_herdeiros'] = True
            resultado['obito'] = True
            resultado['nivel_confianca'] = 'MÉDIA'

            # Extrair informações adicionais
            self._extrair_detalhes_habilitacao(texto, resultado)

            return resultado

        # 3. Verificar apenas ÓBITO (sem habilitação confirmada)
        obito_detectado = False
        for padrao in self.PADROES_OBITO:
            if re.search(padrao, texto, re.IGNORECASE | re.MULTILINE):
                obito_detectado = True
                logger.debug(f"   Óbito detectado: {padrao}")
                break

        if obito_detectado:
            # Verificar se há herdeiros NÃO habilitados
            # (óbito detectado mas sem estrutura de habilitação)
            matches_baixa = 0
            for padrao in self.PADROES_BAIXA_CONFIANCA:
                if re.search(padrao, texto, re.IGNORECASE | re.MULTILINE):
                    matches_baixa += 1

            if matches_baixa > 0:
                logger.info(f"⚠️ Óbito detectado com indicadores fracos: {matches_baixa}")
                resultado['habilitacao_herdeiros'] = False  # NÃO confirmado
                resultado['obito'] = True
                resultado['nivel_confianca'] = 'BAIXA'

                # Tentar extrair data de óbito mesmo assim
                data_obito = self._extrair_data_obito(texto)
                if data_obito:
                    resultado['data_obito'] = data_obito
            else:
                # Óbito mencionado mas sem herdeiros
                logger.info("ℹ️ Óbito detectado mas sem menção a herdeiros")
                resultado['obito'] = True
                resultado['nivel_confianca'] = 'BAIXA'

        return resultado

    def _extrair_detalhes_habilitacao(self, texto: str, resultado: Dict) -> None:
        """
        Extrai detalhes adicionais da habilitação de herdeiros.

        Args:
            texto: Texto completo
            resultado: Dicionário de resultado a ser atualizado (in-place)
        """
        # Extrair data de óbito
        data_obito = self._extrair_data_obito(texto)
        if data_obito:
            resultado['data_obito'] = data_obito
            logger.info(f"   📅 Data de óbito: {data_obito}")

        # Extrair CPF do sucessor
        cpf_sucessor = self._extrair_cpf_sucessor(texto)
        if cpf_sucessor:
            resultado['cpf_sucessor'] = cpf_sucessor
            logger.info(f"   👤 CPF do sucessor: {cpf_sucessor}")

    def _extrair_data_obito(self, texto: str) -> Optional[str]:
        """
        Extrai data de óbito do texto.

        Procura por padrões:
        - "Data de óbito: DD/MM/YYYY"
        - "Óbito em DD/MM/YYYY"

        Args:
            texto: Texto completo

        Returns:
            Data em formato DD/MM/YYYY ou None
        """
        padroes = [
            r'Data\s+de\s+[óo]bito:\s*(\d{2}/\d{2}/\d{4})',
            r'[óo]bito\s+em\s+(\d{2}/\d{2}/\d{4})',
            r'falecimento\s+em\s+(\d{2}/\d{2}/\d{4})',
        ]

        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                data = match.group(1)
                # Validar formato básico
                try:
                    datetime.strptime(data, '%d/%m/%Y')
                    return data
                except ValueError:
                    logger.warning(f"   ⚠️ Data inválida encontrada: {data}")
                    continue

        return None

    def _extrair_cpf_sucessor(self, texto: str) -> Optional[str]:
        """
        Extrai CPF do sucessor (herdeiro) do texto.

        Procura por:
        - "Sucessor:" seguido de CPF
        - "Herdeiro:" seguido de CPF

        Args:
            texto: Texto completo

        Returns:
            CPF formatado (XXX.XXX.XXX-XX) ou None
        """
        # Buscar seção "Sucessor:" ou "Herdeiro:"
        padroes_secao = [
            r'Sucessor:.*?CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            r'Herdeiro:.*?CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            r'Sucessor:.*?(\d{3}\.\d{3}\.\d{3}-\d{2})',
        ]

        for padrao in padroes_secao:
            match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
            if match:
                cpf = match.group(1)
                logger.debug(f"   CPF sucessor encontrado: {cpf}")
                return cpf

        # Buscar CPF próximo a "Sucessor" (fallback)
        match_sucessor = re.search(r'Sucessor:', texto, re.IGNORECASE)
        if match_sucessor:
            # Procurar CPF nos próximos 500 caracteres
            texto_proximo = texto[match_sucessor.start():match_sucessor.start() + 500]
            match_cpf = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', texto_proximo)
            if match_cpf:
                return match_cpf.group(1)

        return None

    def detectar_simples(self, texto: str) -> bool:
        """
        Versão simplificada que retorna apenas True/False.

        Args:
            texto: Texto completo do PDF

        Returns:
            True se habilitação de herdeiros detectada (confiança ALTA ou MÉDIA)
        """
        resultado = self.detectar(texto)
        return resultado['habilitacao_herdeiros'] and resultado['nivel_confianca'] in ['ALTA', 'MÉDIA']
