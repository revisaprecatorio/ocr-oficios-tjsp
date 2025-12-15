"""
DetectorProcessamento - Localiza página PROCESSAMENTO e extrai número de ordem/precatório
Versão 2.7.5 - Fix: Regra rigorosa PROCESSAMENTO (todos campos) + validação imediata numero_ordem
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
        limite: Optional[int] = None
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Detecta página com PROCESSAMENTO ou CERTIDÃO DE PUBLICAÇÃO após o ofício/ANEXO II.

        V2.7.3 FIX: Limite padrão removido (None = busca todo PDF)

        Args:
            pdf_path: Caminho para o arquivo PDF
            inicio: Página para começar busca (0-indexed)
            limite: Máximo de páginas para buscar após início (None = buscar até o final)

        Returns:
            Tupla (numero_pagina, texto_pagina) ou (None, None) se não encontrado

        Example:
            >>> detector = DetectorProcessamento()
            >>> pagina, texto = detector.detectar_processamento("oficio.pdf", inicio=20)
            >>> if pagina:
            ...     numero_ordem = detector.extrair_numero_ordem(texto)
        """
        try:
            logger.info(f"Buscando PROCESSAMENTO/CERTIDÃO a partir da página {inicio + 1}")

            doc = pymupdf.open(pdf_path)
            total_paginas = len(doc)

            # Limitar busca (None = buscar até o final)
            fim = min(inicio + limite, total_paginas) if limite else total_paginas
            
            for page_num in range(inicio, fim):
                page = doc.load_page(page_num)
                texto = page.get_text()

                # Verificar se tem "PROCESSAMENTO" no texto
                if self._eh_pagina_processamento(texto):
                    # V2.7.5 FIX 2: Validar que numero_ordem pode ser extraído
                    numero_ordem = self.extrair_numero_ordem(texto)
                    if numero_ordem:
                        logger.info(f"✅ PROCESSAMENTO detectado na página {page_num + 1} com numero_ordem: {numero_ordem}")
                        doc.close()
                        return (page_num + 1, texto)  # 1-indexed
                    else:
                        logger.warning(f"⚠️ V2.7.5: Página {page_num + 1} passou teste mas sem numero_ordem extraível - continuando busca...")
                        # Continua buscando próxima página
            
            doc.close()
            logger.warning(f"⚠️ PROCESSAMENTO não encontrado (buscou {fim - inicio} páginas)")
            return (None, None)
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar PROCESSAMENTO: {e}")
            return (None, None)

    def detectar_rejeicao(
        self,
        pdf_path: str,
        inicio: int = 0,
        limite: Optional[int] = None
    ) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        V3.0.2: Detecta página com NOTA DE REJEIÇÃO usando REGEX.

        PRIORIDADE: Esta função deve ser chamada ANTES de detectar_processamento()
        para garantir que rejeições não sejam confundidas com PROCESSAMENTO.

        Args:
            pdf_path: Caminho para o arquivo PDF
            inicio: Página para começar busca (0-indexed)
            limite: Máximo de páginas para buscar após início (None = buscar até o final)

        Returns:
            Tupla (numero_pagina, texto_pagina, motivo_rejeicao) ou (None, None, None) se não encontrado

        Example:
            >>> detector = DetectorProcessamento()
            >>> pagina, texto, motivo = detector.detectar_rejeicao("oficio.pdf", inicio=20)
            >>> if pagina:
            ...     print(f"Ofício rejeitado na página {pagina}: {motivo[:100]}")
        """
        try:
            logger.info(f"🔍 V3.0.2: Buscando NOTA DE REJEIÇÃO a partir da página {inicio + 1}")

            doc = pymupdf.open(pdf_path)
            total_paginas = len(doc)

            # Limitar busca (None = buscar até o final)
            fim = min(inicio + limite, total_paginas) if limite else total_paginas

            for page_num in range(inicio, fim):
                page = doc.load_page(page_num)
                texto = page.get_text()
                texto_upper = texto.upper()

                # Verificar keywords de rejeição
                if "NOTA DE REJEIÇÃO" in texto_upper or "NOTA DE REJEICAO" in texto_upper:
                    # Confirmar que é realmente rejeição (não falso positivo)
                    if "DEPRE" in texto_upper or "DIRETORIA DE EXECUÇÕES" in texto_upper:
                        # Extrair motivo
                        motivo = self.extrair_motivo_rejeicao(texto)

                        logger.warning(f"⚠️ NOTA DE REJEIÇÃO detectada na página {page_num + 1}")
                        if motivo:
                            logger.info(f"   Motivo: {motivo[:100]}...")
                        else:
                            logger.warning(f"   ⚠️ Motivo não extraído")

                        doc.close()
                        return (page_num + 1, texto, motivo)  # 1-indexed

            doc.close()
            logger.info(f"✅ NOTA DE REJEIÇÃO não encontrada (buscou {fim - inicio} páginas)")
            return (None, None, None)

        except Exception as e:
            logger.error(f"❌ Erro ao detectar REJEIÇÃO: {e}")
            return (None, None, None)

    def _eh_pagina_processamento(self, texto: str) -> bool:
        """
        Verifica se texto contém indicadores de página PROCESSAMENTO ou CERTIDÃO DE PUBLICAÇÃO.

        V3.0.2 FIX: Rejeitar NOTA DE REJEIÇÃO (prioridade máxima)
        V2.7.3 FIX: Detecta também CERTIDÃO DE PUBLICAÇÃO que contém numero_ordem
        V2.7.5 FIX: Exige TODOS os 3 campos (PROCESSAMENTO + DEPRE + numero_ordem)

        Args:
            texto: Texto da página

        Returns:
            True se é página PROCESSAMENTO ou CERTIDÃO com numero_ordem
        """
        texto_upper = texto.upper()

        # V3.0.2 FIX: PRIORIDADE MÁXIMA - Rejeitar NOTA DE REJEIÇÃO
        if "NOTA DE REJEIÇÃO" in texto_upper or "NOTA DE REJEICAO" in texto_upper:
            logger.debug("❌ Rejeitado: NOTA DE REJEIÇÃO (não é PROCESSAMENTO)")
            return False

        # V2.7.5 FIX 3: Rejeitar APROVAÇÃO DE REQUISITÓRIO (não é PROCESSAMENTO)
        if "APROVAÇÃO DE REQUISITÓRIO" in texto_upper or "APROVACAO DE REQUISITORIO" in texto_upper:
            logger.debug("❌ Rejeitado: APROVAÇÃO DE REQUISITÓRIO (não é PROCESSAMENTO)")
            return False

        # Verificar PROCESSAMENTO (padrão original)
        tem_titulo = "PROCESSAMENTO" in texto_upper
        tem_depre = "DEPRE" in texto_upper or "DIRETORIA DE EXECUÇÕES" in texto_upper
        tem_numero_ordem = "Nº DE ORDEM" in texto_upper or "NÚMERO DO PRECATÓRIO" in texto_upper

        # V2.7.3 FIX: Verificar CERTIDÃO DE PUBLICAÇÃO
        tem_certidao = "CERTIDÃO DE PUBLICAÇÃO" in texto_upper or "CERTIDAO DE PUBLICACAO" in texto_upper
        tem_numero_ordem_certidao = "NÚMERO DE ORDEM" in texto_upper

        # V2.7.5 FIX 1: Aceitar se TODOS os 3 campos presentes:
        # 1. PROCESSAMENTO + DEPRE + numero_ordem (TODOS obrigatórios)
        # 2. CERTIDÃO + numero_ordem
        if tem_titulo and tem_depre and tem_numero_ordem:
            logger.debug("✅ PROCESSAMENTO válido: título + DEPRE + numero_ordem")
            return True

        if tem_certidao and tem_numero_ordem_certidao:
            logger.info("✅ CERTIDÃO DE PUBLICAÇÃO detectada com numero_ordem")
            return True

        return False
    
    def eh_oficio_rejeitado(self, texto: str) -> bool:
        """
        Verifica se o texto indica que o ofício foi rejeitado.
        
        IMPORTANTE: "PROCESSAMENTO COM INFORMAÇÃO" NÃO é rejeição!
        Ofícios com número de ordem foram ACEITOS pelo DEPRE.
        
        Args:
            texto: Texto da página
            
        Returns:
            True se é ofício rejeitado
        """
        texto_upper = texto.upper()
        
        # 🔴 REGRA CRÍTICA: Se tem "PROCESSAMENTO COM INFORMAÇÃO" → NÃO é rejeitado
        if "PROCESSAMENTO COM INFORMAÇÃO" in texto_upper or "PROCESSAMENTO COM INFORMACAO" in texto_upper:
            logger.info("✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO (não rejeitado)")
            return False
        
        # 🔴 REGRA CRÍTICA: Se tem número de ordem → NÃO é rejeitado
        if self.extrair_numero_ordem(texto):
            logger.info("✅ Número de ordem detectado → Ofício ACEITO (não rejeitado)")
            return False
        
        # Verificar keywords de rejeição
        for keyword in self.keywords_rejeicao:
            if keyword.upper() in texto_upper:
                logger.warning(f"⚠️ Keyword de rejeição encontrada: {keyword}")
                return True
        
        return False
    
    def extrair_motivo_rejeicao(self, texto: str) -> Optional[str]:
        """
        Extrai o motivo da rejeição do ofício usando REGEX robusto.

        V3.0.2: REGEX melhorado com múltiplos padrões + truncamento garantido

        Args:
            texto: Texto da página de rejeição

        Returns:
            Motivo da rejeição ou None (máximo 500 chars)
        """
        try:
            motivo = None

            # Padrão 1: "tendo em vista que..." (mais comum)
            padrao1 = re.compile(
                r'tendo em vista\s+que[,:]?\s*(.+?)(?:\.[\s\n]*(?:São Paulo|Cumpre-nos|De outra|Ressaltamos))',
                re.IGNORECASE | re.DOTALL
            )

            match = padrao1.search(texto)
            if match:
                motivo = match.group(1).strip()
                # Limpar quebras de linha e espaços múltiplos
                motivo = re.sub(r'\s+', ' ', motivo)
                logger.info(f"✅ Motivo extraído (Padrão 1): {motivo[:100]}...")

            # Padrão 2: "irregularidade(s) passível(eis) de REJEIÇÃO..."
            if not motivo:
                padrao2 = re.compile(
                    r'irregularidade\(s\)\s+passível\(eis\)\s+de\s+REJEIÇÃO[^,]*,\s+tendo\s+em\s+vista\s+que[,:]?\s*(.+?)(?:\.[\s\n]*(?:São Paulo|Cumpre-nos|De outra|Ressaltamos))',
                    re.IGNORECASE | re.DOTALL
                )

                match = padrao2.search(texto)
                if match:
                    motivo = match.group(1).strip()
                    motivo = re.sub(r'\s+', ' ', motivo)
                    logger.info(f"✅ Motivo extraído (Padrão 2): {motivo[:100]}...")

            # Padrão 3: Fallback - texto completo após "NOTA DE REJEIÇÃO"
            if not motivo and "NOTA DE REJEIÇÃO" in texto.upper():
                # Extrair parágrafo após "NOTA DE REJEIÇÃO"
                padrao3 = re.compile(
                    r'NOTA DE REJEIÇÃO.+?(?:Processo DEPRE|O ofício).+?(?:irregularidade.+?)(?:\.[\s\n]*(?:São Paulo|Cumpre-nos))',
                    re.IGNORECASE | re.DOTALL
                )
                match = padrao3.search(texto)
                if match:
                    motivo = match.group(0).strip()
                    motivo = re.sub(r'\s+', ' ', motivo)
                    # Remover cabeçalho da nota
                    motivo = re.sub(r'^NOTA DE REJEIÇÃO.*?irregularidade\(s\)[^:]+:\s*', '', motivo, flags=re.IGNORECASE)
                    logger.warning(f"⚠️ Motivo extraído (Fallback): {motivo[:100]}...")

            # GARANTIA: Truncar em 500 chars SEMPRE (schema Pydantic)
            if motivo:
                if len(motivo) > 500:
                    motivo = motivo[:497] + "..."
                    logger.warning(f"⚠️ Motivo truncado para 500 chars (era {len(match.group(1))} chars)")
                return motivo
            else:
                logger.warning("⚠️ Motivo de rejeição não extraído (nenhum padrão match)")
                return None

        except Exception as e:
            logger.error(f"❌ Erro ao extrair motivo de rejeição: {e}")
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

    def _limpar_quebras_linha_numero_ordem(self, texto: str) -> str:
        """
        Remove quebras de linha indesejadas em números de ordem.

        Problema: PDF pode quebrar "19053/2025" em duas linhas:
        Linha 1: "Nº de Ordem: 19053/202"
        Linha 2: "5"

        Solução: Juntar quando detectar padrão XXX/YYY seguido de dígito isolado.

        Args:
            texto: Texto da seção PROCESSAMENTO

        Returns:
            Texto com números de ordem corrigidos

        Example:
            >>> texto = "Nº de Ordem: 19053/202\\n5\\nData: 21/02/2024"
            >>> detector._limpar_quebras_linha_numero_ordem(texto)
            "Nº de Ordem: 19053/2025\\nData: 21/02/2024"
        """
        linhas = texto.split('\n')
        texto_limpo = []

        i = 0
        while i < len(linhas):
            linha_atual = linhas[i].strip()

            # Padrão: número/ano-truncado (3 dígitos) no final da linha
            # Ex: "Nº de Ordem: 19053/202" ou apenas "19053/202"
            match = re.search(r'(\d{1,6}/\d{3})$', linha_atual)

            if match and i + 1 < len(linhas):
                proxima_linha = linhas[i + 1].strip()

                # Próxima linha é apenas um dígito isolado?
                if re.match(r'^\d$', proxima_linha):
                    # JUNTAR! 19053/202 + 5 = 19053/2025
                    linha_atual = linha_atual.replace(
                        match.group(1),
                        match.group(1) + proxima_linha
                    )
                    logger.info(f"🔧 Corrigido quebra de linha: {match.group(1)} + {proxima_linha} = {match.group(1) + proxima_linha}")
                    texto_limpo.append(linha_atual)
                    i += 2  # Pular próxima linha (já processada)
                    continue

            texto_limpo.append(linha_atual)
            i += 1

        return '\n'.join(texto_limpo)

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

    def buscar_numero_ordem_global(self, pdf_path: str) -> Optional[str]:
        """
        V2.7.3 FIX: Fallback global - busca numero_ordem em TODO o PDF usando REGEX.

        Usado quando detectar_processamento() falha.
        Busca padrões:
        - "Nº de Ordem: XXXXX/YYYY"
        - "Número de ordem: XXXXX/YYYY"
        - "Número do Precatório: XXXXX/YYYY"

        Args:
            pdf_path: Caminho do PDF

        Returns:
            Primeiro numero_ordem válido encontrado ou None

        Example:
            >>> detector = DetectorProcessamento()
            >>> numero = detector.buscar_numero_ordem_global("oficio.pdf")
            >>> print(numero)  # "50228/2025"
        """
        try:
            logger.info("🔍 V2.7.3: Iniciando busca GLOBAL de numero_ordem em todo PDF...")

            doc = pymupdf.open(pdf_path)
            total_paginas = len(doc)

            # Padrões para buscar
            padroes = [
                re.compile(r'Nº de Ordem:\s*(\d{1,5}/\d{4})', re.IGNORECASE),
                re.compile(r'Número de ordem:\s*(\d{1,5}/\d{4})', re.IGNORECASE),
                re.compile(r'Número do Precatório:\s*(\d{1,5}/\d{4})', re.IGNORECASE),
            ]

            # Buscar em TODAS as páginas
            for page_num in range(total_paginas):
                page = doc.load_page(page_num)
                texto = page.get_text()

                # Tentar todos os padrões
                for padrao in padroes:
                    match = padrao.search(texto)
                    if match:
                        numero = match.group(1)

                        # Validar
                        if self.validar_numero_ordem(numero):
                            logger.info(f"✅ V2.7.3 GLOBAL: numero_ordem encontrado na página {page_num + 1}: {numero}")
                            doc.close()
                            return numero

            doc.close()
            logger.warning("⚠️ V2.7.3 GLOBAL: numero_ordem NÃO encontrado em nenhuma página")
            return None

        except Exception as e:
            logger.error(f"❌ Erro na busca global de numero_ordem: {e}")
            return None
