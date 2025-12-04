"""
DetectorTermosJuridicos - Detecta termos jurídicos específicos em PDFs
Versão: 2.0.0
Data: 04/12/2025

MUDANÇAS v2.0:
- ❌ CESSÃO DE CRÉDITO: Desativado (sempre retorna False)
- ✅ HABILITAÇÃO DE HERDEIROS: Nova lógica validada por CPF
- ✅ PREFERENCIAL: Mantido sem alterações

Detecta 2 termos jurídicos específicos no texto completo do PDF:
1. Preferência/Preferencia
2. Habilitação de Herdeiros (VALIDADO por CPF do objeto)
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DetectorTermosJuridicos:
    """
    Detector de termos jurídicos específicos no texto completo do PDF.
    
    Utiliza regex case-insensitive com acentuação flexível para detectar:
    - Pedido de preferência
    - Habilitação de herdeiros
    - Cessão de crédito ou direitos creditórios
    """
    
    def __init__(self):
        """Inicializa os padrões regex para detecção dos termos."""

        # Pattern 1: Preferência (com ou sem acento)
        # Matches: preferência, preferencia, PREFERÊNCIA, etc.
        self.pattern_preferencial = re.compile(
            r'prefer[eê]ncia',
            re.IGNORECASE
        )

        # Pattern 2: Habilitação de Herdeiros (CÓDIGO 9270)
        # Matches: "9270 . Habilitação de Herdeiro de Precatório"
        # NOVA LÓGICA v2.0: Busca código específico do formulário
        self.pattern_habilitacao_codigo = re.compile(
            r'9270\s*[.\-–]*\s*Habilita[çc][aã]o\s+de\s+Herdeiro',
            re.IGNORECASE
        )

        # Pattern 3: CPF na seção "Dados da Sucessão"
        # Matches: "CPF: 576.290.808-91"
        self.pattern_cpf_sucessao = re.compile(
            r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            re.IGNORECASE
        )

        # ❌ Pattern DESATIVADO: Cessão de Crédito (v2.0)
        # MOTIVO: Removido a pedido do cliente
        # Mantido comentado para histórico e possível reativação futura
        # self.pattern_cessao = re.compile(
        #     r'cess[aã]o\s+de\s+(cr[ée]dito|direitos\s+credit[óo]rios)',
        #     re.IGNORECASE
        # )

        # Pattern 4: Doença Grave (v2.5.3)
        # Matches: "doença grave", "moléstia grave", "laudo médico", etc.
        self.pattern_doenca_grave = re.compile(
            r'(doen[çc]a\s+grave|mol[ée]stia\s+grave|grave\s+doen[çc]a|'
            r'laudo\s+m[ée]dico|atestado\s+m[ée]dico|'
            r'portador\s+de\s+doen[çc]a\s+grave)',
            re.IGNORECASE
        )

        logger.info("DetectorTermosJuridicos v2.5.3 inicializado (Cessão de Crédito DESATIVADO, Doença Grave ATIVO)")
    
    def detectar_termos(self, texto_completo: str, cpf_objeto: str = None) -> Dict[str, bool]:
        """
        Busca termos jurídicos no texto completo do PDF.

        MUDANÇAS v2.5.3:
        - Cessão de crédito sempre retorna False (desativado)
        - Habilitação de herdeiros validada por CPF (evita falso-positivos)
        - Doença grave detectada (novo campo)

        Args:
            texto_completo: Texto completo extraído do PDF
            cpf_objeto: CPF do objeto sendo analisado (formato: XXX.XXX.XXX-XX)
                       Obrigatório para validar habilitação de herdeiros

        Returns:
            Dict com 4 booleanos:
            {
                'preferencial': bool,
                'habilitacao_herdeiros': bool,
                'cessao_credito': bool,  # Sempre False em v2.5.3
                'doenca_grave': bool  # Novo em v2.5.3
            }

        Example:
            >>> detector = DetectorTermosJuridicos()
            >>> texto = "Reconheço a preferência para o credor com doença grave"
            >>> resultado = detector.detectar_termos(texto, "576.290.808-91")
            >>> print(resultado)
            {'preferencial': True, 'habilitacao_herdeiros': False, 'cessao_credito': False, 'doenca_grave': True}
        """
        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção de termos")
            return {
                'preferencial': False,
                'habilitacao_herdeiros': False,
                'cessao_credito': False,
                'doenca_grave': False
            }

        # 1. Buscar PREFERENCIAL (mantido sem mudanças)
        preferencial = bool(self.pattern_preferencial.search(texto_completo))

        # 2. Buscar HABILITAÇÃO DE HERDEIROS (nova lógica validada)
        habilitacao = self._detectar_habilitacao_validada(texto_completo, cpf_objeto)

        # 3. CESSÃO DE CRÉDITO = Sempre False (desativado v2.0)
        cessao = False

        # 4. Buscar DOENÇA GRAVE (v2.5.3)
        doenca_grave = bool(self.pattern_doenca_grave.search(texto_completo))

        # Log resultados
        logger.info(
            f"📋 Termos detectados: "
            f"preferencial={preferencial}, "
            f"habilitacao_herdeiros={habilitacao}, "
            f"cessao_credito={cessao} [DESATIVADO], "
            f"doenca_grave={doenca_grave}"
        )

        return {
            'preferencial': preferencial,
            'habilitacao_herdeiros': habilitacao,
            'cessao_credito': cessao,
            'doenca_grave': doenca_grave
        }

    def _detectar_habilitacao_validada(self, texto_completo: str, cpf_objeto: str) -> bool:
        """
        Detecta habilitação de herdeiros VALIDADA por CPF.

        LÓGICA v2.0 (evita falso-positivos):
        1. Busca código "9270" + "Habilitação de Herdeiro"
        2. Extrai seção "Dados da Sucessão" (próximas 30 linhas)
        3. Busca CPF nessa seção
        4. Valida se CPF encontrado == CPF objeto
        5. Retorna TRUE apenas se AMBOS critérios atenderem

        Args:
            texto_completo: Texto completo do PDF
            cpf_objeto: CPF formatado do objeto (XXX.XXX.XXX-XX)

        Returns:
            True se habilitação é para o CPF objeto, False caso contrário

        Example:
            >>> detector = DetectorTermosJuridicos()
            >>> texto = "9270 . Habilitação de Herdeiro\\nDados da Sucessão\\nCPF: 576.290.808-91"
            >>> resultado = detector._detectar_habilitacao_validada(texto, "576.290.808-91")
            >>> print(resultado)
            True
        """
        if not cpf_objeto:
            logger.warning("⚠️ CPF não fornecido, habilitação retorna False (evitar falso-positivos)")
            return False

        # Passo 1: Buscar código 9270
        match_codigo = self.pattern_habilitacao_codigo.search(texto_completo)
        if not match_codigo:
            logger.debug("Código 9270 não encontrado (sem habilitação de herdeiros)")
            return False

        logger.info(f"✅ Código 9270 encontrado na posição {match_codigo.start()}")

        # Passo 2: Extrair seção após o código (próximas 2000 chars ~ 30 linhas)
        inicio_secao = match_codigo.start()
        fim_secao = min(len(texto_completo), inicio_secao + 2000)
        secao_sucessao = texto_completo[inicio_secao:fim_secao]

        # Passo 3: Buscar CPF na seção
        match_cpf = self.pattern_cpf_sucessao.search(secao_sucessao)
        if not match_cpf:
            logger.warning("⚠️ Código 9270 encontrado, mas CPF não detectado em 'Dados da Sucessão'")
            return False

        cpf_encontrado = match_cpf.group(1)
        logger.info(f"📄 CPF encontrado na habilitação: {cpf_encontrado}")

        # Passo 4: Validar se CPF corresponde
        if cpf_encontrado == cpf_objeto:
            logger.info(f"✅ HABILITAÇÃO VALIDADA: CPF {cpf_objeto} corresponde!")
            return True
        else:
            logger.warning(
                f"⚠️ HABILITAÇÃO para OUTRO CPF: "
                f"Encontrado {cpf_encontrado}, esperado {cpf_objeto}"
            )
            return False
    
    def detectar_com_contexto(self, texto_completo: str, cpf_objeto: str = None) -> Dict[str, Any]:
        """
        Busca os termos E retorna o contexto (snippet) onde foram encontrados.
        Útil para debugging e validação manual.

        MUDANÇAS v2.0:
        - Cessão de crédito sempre False (desativado)
        - Habilitação validada por CPF

        Args:
            texto_completo: Texto completo extraído do PDF
            cpf_objeto: CPF do objeto (formato: XXX.XXX.XXX-XX)

        Returns:
            Dict com booleanos + snippets de contexto (50 chars antes e depois):
            {
                'preferencial': bool,
                'habilitacao_herdeiros': bool,
                'cessao_credito': bool,  # Sempre False
                'contexto_preferencial': str | None,
                'contexto_habilitacao': str | None,
                'contexto_cessao': None  # Sempre None
            }

        Example:
            >>> detector = DetectorTermosJuridicos()
            >>> texto = "Reconheço a preferência para o credor Cleber Roberto."
            >>> resultado = detector.detectar_com_contexto(texto)
            >>> print(resultado['contexto_preferencial'])
            'Reconheço a preferência para o credor Cleber Roberto.'
        """
        resultado = {
            'preferencial': False,
            'habilitacao_herdeiros': False,
            'cessao_credito': False,  # Sempre False em v2.0
            'contexto_preferencial': None,
            'contexto_habilitacao': None,
            'contexto_cessao': None  # Sempre None em v2.0
        }

        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção com contexto")
            return resultado

        # Buscar preferencial com contexto
        match = self.pattern_preferencial.search(texto_completo)
        if match:
            resultado['preferencial'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_preferencial'] = texto_completo[inicio:fim].strip()
            logger.debug(f"Contexto preferencial: {resultado['contexto_preferencial']}")

        # Buscar habilitação com contexto (código 9270)
        match = self.pattern_habilitacao_codigo.search(texto_completo)
        if match:
            # Validar por CPF
            resultado['habilitacao_herdeiros'] = self._detectar_habilitacao_validada(
                texto_completo, cpf_objeto
            )
            if resultado['habilitacao_herdeiros']:
                inicio = max(0, match.start() - 50)
                fim = min(len(texto_completo), match.start() + 200)
                resultado['contexto_habilitacao'] = texto_completo[inicio:fim].strip()
                logger.debug(f"Contexto habilitação: {resultado['contexto_habilitacao'][:100]}...")

        # ❌ CESSÃO DE CRÉDITO DESATIVADO (v2.0)
        # Sempre retorna False e None
        # match = self.pattern_cessao.search(texto_completo)
        # if match:
        #     resultado['cessao_credito'] = True
        #     inicio = max(0, match.start() - 50)
        #     fim = min(len(texto_completo), match.end() + 50)
        #     resultado['contexto_cessao'] = texto_completo[inicio:fim].strip()

        return resultado
    
    def validar_padroes(self) -> Dict[str, bool]:
        """
        Valida se os padrões regex estão funcionando corretamente.
        Útil para testes e debugging.

        MUDANÇAS v2.0:
        - Cessão sempre False (desativado)
        - Habilitação testa código 9270 + CPF

        Returns:
            Dict com resultado dos testes para cada padrão
        """
        testes = {
            'preferencial': False,
            'habilitacao_codigo_9270': False,
            'habilitacao_cpf_validado': False,
            'cessao': False  # Sempre False em v2.0
        }

        # Testar preferencial
        texto_teste = "Reconheço a preferência para o credor"
        if self.pattern_preferencial.search(texto_teste):
            testes['preferencial'] = True

        # Testar habilitação código 9270
        texto_teste = "9270 . Habilitação de Herdeiro de Precatório"
        if self.pattern_habilitacao_codigo.search(texto_teste):
            testes['habilitacao_codigo_9270'] = True

        # Testar habilitação validada com CPF
        texto_completo = """
        9270 . Habilitação de Herdeiro de Precatório
        Dados da Sucessão
        CPF: 576.290.808-91
        """
        resultado = self._detectar_habilitacao_validada(texto_completo, "576.290.808-91")
        if resultado:
            testes['habilitacao_cpf_validado'] = True

        # ❌ Cessão sempre False (desativado v2.0)
        # texto_teste = "conforme cessão de crédito anexa"
        # if self.pattern_cessao.search(texto_teste):
        #     testes['cessao'] = True

        logger.info(f"Validação de padrões v2.0: {testes}")
        return testes
