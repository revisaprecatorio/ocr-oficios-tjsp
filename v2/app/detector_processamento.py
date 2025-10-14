"""
DetectorProcessamento - Localiza página PROCESSAMENTO e extrai número de ordem/precatório
Versão 2.0 - Otimizado para extração seletiva de páginas
"""

import re
import logging
from typing import Optional, Tuple
import pymupdf

logger = logging.getLogger(__name__)


class DetectorProcessamento:
    """
    Detecta página com título "PROCESSAMENTO" e extrai número de ordem/precatório.
    
    O número de ordem (também chamado "número do precatório") é um identificador
    único no formato XXX/YYYY (ex: 822/2026) encontrado na página PROCESSAMENTO.
    """
    
    def __init__(self):
        """Inicializa detector com keywords e padrões"""
        
        # Keywords para identificar página PROCESSAMENTO
        self.keywords = [
            "PROCESSAMENTO",
            "Nº de Ordem:",
            "Número do Precatório",
            "DEPRE - Diretoria de Execuções de Precatórios"
        ]
        
        # Keywords para identificar REJEIÇÃO
        self.keywords_rejeicao = [
            "NOTA DE REJEIÇÃO",
            "REJEIÇÃO",
            "irregularidade(s) passível(eis) de REJEIÇÃO"
        ]
        
        # Padrão regex para número de ordem no PROCESSAMENTO: 822/2026
        self.padrao_numero_ordem = re.compile(
            r'(?:Nº de Ordem:|Número do Precatório:?)\s*(\d{1,5}/\d{4})',
            re.IGNORECASE
        )
        
        # Padrão para número no TÍTULO do ofício (PDFs antigos): "OFÍCIO REQUISITÓRIO Nº 644/2015"
        self.padrao_titulo_oficio = re.compile(
            r'OFÍCIO\s+REQUISITÓRIO\s+N[ºO°]\s*(\d{1,5}/\d{4})',
            re.IGNORECASE
        )
        
        # Padrão alternativo (caso esteja em linha separada)
        self.padrao_numero_simples = re.compile(r'\b(\d{1,5}/\d{4})\b')
    
    def detectar_processamento(
        self, 
        pdf_path: str, 
        inicio: int = 0,
        limite: int = 50
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Detecta página com PROCESSAMENTO após o ofício/ANEXO II.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            inicio: Página para começar busca (0-indexed)
            limite: Máximo de páginas para buscar após início
            
        Returns:
            Tupla (numero_pagina, texto_pagina) ou (None, None) se não encontrado
            
        Example:
            >>> detector = DetectorProcessamento()
            >>> pagina, texto = detector.detectar_processamento("oficio.pdf", inicio=20)
            >>> if pagina:
            ...     numero_ordem = detector.extrair_numero_ordem(texto)
        """
        try:
            logger.info(f"Buscando PROCESSAMENTO a partir da página {inicio + 1}")
            
            doc = pymupdf.open(pdf_path)
            total_paginas = len(doc)
            
            # Limitar busca
            fim = min(inicio + limite, total_paginas)
            
            for page_num in range(inicio, fim):
                page = doc.load_page(page_num)
                texto = page.get_text()
                
                # Verificar se tem "PROCESSAMENTO" no texto
                if self._eh_pagina_processamento(texto):
                    logger.info(f"✅ PROCESSAMENTO detectado na página {page_num + 1}")
                    doc.close()
                    return (page_num + 1, texto)  # 1-indexed
            
            doc.close()
            logger.warning(f"⚠️ PROCESSAMENTO não encontrado (buscou {fim - inicio} páginas)")
            return (None, None)
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar PROCESSAMENTO: {e}")
            return (None, None)
    
    def _eh_pagina_processamento(self, texto: str) -> bool:
        """
        Verifica se texto contém indicadores de página PROCESSAMENTO.
        
        Args:
            texto: Texto da página
            
        Returns:
            True se é página PROCESSAMENTO
        """
        texto_upper = texto.upper()
        
        # Verificar keywords principais
        tem_titulo = "PROCESSAMENTO" in texto_upper
        tem_depre = "DEPRE" in texto_upper or "DIRETORIA DE EXECUÇÕES" in texto_upper
        tem_numero_ordem = "Nº DE ORDEM" in texto_upper or "NÚMERO DO PRECATÓRIO" in texto_upper
        
        # Precisa ter pelo menos título + um dos outros
        return tem_titulo and (tem_depre or tem_numero_ordem)
    
    def eh_oficio_rejeitado(self, texto: str) -> bool:
        """
        Verifica se o texto indica que o ofício foi rejeitado.
        
        Args:
            texto: Texto da página
            
        Returns:
            True se é ofício rejeitado
        """
        texto_upper = texto.upper()
        
        for keyword in self.keywords_rejeicao:
            if keyword.upper() in texto_upper:
                return True
        
        return False
    
    def extrair_motivo_rejeicao(self, texto: str) -> Optional[str]:
        """
        Extrai o motivo da rejeição do ofício.
        
        Args:
            texto: Texto da página de rejeição
            
        Returns:
            Motivo da rejeição ou None
        """
        try:
            # Buscar padrão: "tendo em vista que..."
            import re
            
            padrao = re.compile(
                r'tendo em vista que[,:]?\s*(.+?)(?:\.|São Paulo)',
                re.IGNORECASE | re.DOTALL
            )
            
            match = padrao.search(texto)
            if match:
                motivo = match.group(1).strip()
                # Limitar tamanho
                if len(motivo) > 500:
                    motivo = motivo[:497] + "..."
                return motivo
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair motivo de rejeição: {e}")
            return None
    
    def extrair_numero_ordem_do_titulo(self, texto_oficio: str) -> Optional[str]:
        """
        Extrai número de ordem do TÍTULO do ofício (PDFs antigos).
        
        Busca padrão: "OFÍCIO REQUISITÓRIO Nº 644/2015"
        
        Args:
            texto_oficio: Texto do ofício (primeiras páginas)
            
        Returns:
            Número de ordem (ex: "644/2015") ou None
            
        Example:
            >>> detector = DetectorProcessamento()
            >>> texto = "OFÍCIO REQUISITÓRIO Nº 644/2015\\n..."
            >>> numero = detector.extrair_numero_ordem_do_titulo(texto)
            >>> print(numero)
            "644/2015"
        """
        try:
            # Buscar no título do ofício
            match = self.padrao_titulo_oficio.search(texto_oficio)
            
            if match:
                numero = match.group(1)
                logger.info(f"✅ Número de ordem encontrado no TÍTULO: {numero}")
                return numero
            
            logger.debug("Número de ordem não encontrado no título")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao extrair número do título: {e}")
            return None
    
    def extrair_numero_ordem(self, texto: str) -> Optional[str]:
        """
        Extrai número de ordem/precatório do texto da página PROCESSAMENTO.
        
        Args:
            texto: Texto da página PROCESSAMENTO
            
        Returns:
            Número de ordem no formato "XXX/YYYY" ou None se não encontrado
            
        Example:
            >>> texto = "Nº de Ordem: 822/2026"
            >>> detector.extrair_numero_ordem(texto)
            '822/2026'
        """
        # Tentar padrão completo primeiro (com label)
        match = self.padrao_numero_ordem.search(texto)
        if match:
            numero = match.group(1)
            logger.info(f"✅ Número de ordem extraído: {numero}")
            return numero
        
        # Tentar padrão simples (buscar XXX/YYYY isolado)
        # Procurar próximo ao texto "Nº de Ordem" ou "Número do Precatório"
        linhas = texto.split('\n')
        for i, linha in enumerate(linhas):
            if 'Nº de Ordem' in linha or 'Número do Precatório' in linha:
                # Buscar nas próximas 3 linhas
                for j in range(i, min(i + 3, len(linhas))):
                    match = self.padrao_numero_simples.search(linhas[j])
                    if match:
                        numero = match.group(1)
                        logger.info(f"✅ Número de ordem extraído (padrão alternativo): {numero}")
                        return numero
        
        logger.warning("⚠️ Número de ordem não encontrado no texto")
        return None
    
    def validar_numero_ordem(self, numero_ordem: str) -> bool:
        """
        Valida formato do número de ordem.
        
        Args:
            numero_ordem: String a validar
            
        Returns:
            True se formato válido (XXX/YYYY)
            
        Example:
            >>> detector.validar_numero_ordem("822/2026")
            True
            >>> detector.validar_numero_ordem("invalid")
            False
        """
        if not numero_ordem:
            return False
        
        # Verificar padrão XXX/YYYY
        match = re.match(r'^\d{1,5}/\d{4}$', numero_ordem)
        
        if match:
            # Validar ano (deve ser razoável)
            partes = numero_ordem.split('/')
            ano = int(partes[1])
            
            if 2000 <= ano <= 2030:  # Anos válidos
                return True
            else:
                logger.warning(f"⚠️ Ano inválido no número de ordem: {ano}")
                return False
        
        return False
