"""
DetectorTermosJuridicos - Detecta termos jurídicos específicos em PDFs
Versão: 1.0.0
Data: 10/11/2025

Detecta 3 termos jurídicos específicos no texto completo do PDF:
1. Preferência/Preferencia
2. Habilitação de Herdeiros
3. Cessão de Crédito / Cessão de Direitos Creditórios
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
        
        # Pattern 2: Habilitação de Herdeiros
        # Matches: habilitação de herdeiros, habilitação dos herdeiros, etc.
        self.pattern_habilitacao = re.compile(
            r'habilita[çc][aã]o\s+(de|dos)\s+herdeiros', 
            re.IGNORECASE
        )
        
        # Pattern 3: Cessão de Crédito ou Cessão de Direitos Creditórios
        # Matches: cessão de crédito, cessao de credito, cessão de direitos creditórios, etc.
        self.pattern_cessao = re.compile(
            r'cess[aã]o\s+de\s+(cr[ée]dito|direitos\s+credit[óo]rios)', 
            re.IGNORECASE
        )
        
        logger.info("DetectorTermosJuridicos inicializado")
    
    def detectar_termos(self, texto_completo: str) -> Dict[str, bool]:
        """
        Busca os 3 termos jurídicos no texto completo do PDF.
        
        Args:
            texto_completo: Texto completo extraído do PDF
            
        Returns:
            Dict com 3 booleanos:
            {
                'preferencial': bool,
                'habilitacao_herdeiros': bool,
                'cessao_credito': bool
            }
            
        Example:
            >>> detector = DetectorTermosJuridicos()
            >>> texto = "Reconheço a preferência para o credor"
            >>> resultado = detector.detectar_termos(texto)
            >>> print(resultado)
            {'preferencial': True, 'habilitacao_herdeiros': False, 'cessao_credito': False}
        """
        if not texto_completo:
            logger.warning("Texto vazio fornecido para detecção de termos")
            return {
                'preferencial': False,
                'habilitacao_herdeiros': False,
                'cessao_credito': False
            }
        
        # Buscar cada termo usando regex
        preferencial = bool(self.pattern_preferencial.search(texto_completo))
        habilitacao = bool(self.pattern_habilitacao.search(texto_completo))
        cessao = bool(self.pattern_cessao.search(texto_completo))
        
        # Log resultados
        logger.info(
            f"📋 Termos detectados: "
            f"preferencial={preferencial}, "
            f"habilitacao_herdeiros={habilitacao}, "
            f"cessao_credito={cessao}"
        )
        
        return {
            'preferencial': preferencial,
            'habilitacao_herdeiros': habilitacao,
            'cessao_credito': cessao
        }
    
    def detectar_com_contexto(self, texto_completo: str) -> Dict[str, Any]:
        """
        Busca os termos E retorna o contexto (snippet) onde foram encontrados.
        Útil para debugging e validação manual.
        
        Args:
            texto_completo: Texto completo extraído do PDF
            
        Returns:
            Dict com booleanos + snippets de contexto (50 chars antes e depois):
            {
                'preferencial': bool,
                'habilitacao_herdeiros': bool,
                'cessao_credito': bool,
                'contexto_preferencial': str | None,
                'contexto_habilitacao': str | None,
                'contexto_cessao': str | None
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
            'cessao_credito': False,
            'contexto_preferencial': None,
            'contexto_habilitacao': None,
            'contexto_cessao': None
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
        
        # Buscar habilitação com contexto
        match = self.pattern_habilitacao.search(texto_completo)
        if match:
            resultado['habilitacao_herdeiros'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_habilitacao'] = texto_completo[inicio:fim].strip()
            logger.debug(f"Contexto habilitação: {resultado['contexto_habilitacao']}")
        
        # Buscar cessão com contexto
        match = self.pattern_cessao.search(texto_completo)
        if match:
            resultado['cessao_credito'] = True
            inicio = max(0, match.start() - 50)
            fim = min(len(texto_completo), match.end() + 50)
            resultado['contexto_cessao'] = texto_completo[inicio:fim].strip()
            logger.debug(f"Contexto cessão: {resultado['contexto_cessao']}")
        
        return resultado
    
    def validar_padroes(self) -> Dict[str, bool]:
        """
        Valida se os padrões regex estão funcionando corretamente.
        Útil para testes e debugging.
        
        Returns:
            Dict com resultado dos testes para cada padrão
        """
        testes = {
            'preferencial': False,
            'habilitacao': False,
            'cessao': False
        }
        
        # Testar preferencial
        texto_teste = "Reconheço a preferência para o credor"
        if self.pattern_preferencial.search(texto_teste):
            testes['preferencial'] = True
        
        # Testar habilitação
        texto_teste = "Defiro a habilitação de herdeiros"
        if self.pattern_habilitacao.search(texto_teste):
            testes['habilitacao'] = True
        
        # Testar cessão
        texto_teste = "conforme cessão de crédito anexa"
        if self.pattern_cessao.search(texto_teste):
            testes['cessao'] = True
        
        logger.info(f"Validação de padrões: {testes}")
        return testes
