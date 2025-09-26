"""
DetectorOficio - Localiza ofícios requisitórios dentro de PDFs.
Implementação conforme AGENTS.md usando 3 critérios de detecção.
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple
import pymupdf


logger = logging.getLogger(__name__)


class DetectorOficio:
    """
    Detector de Ofícios Requisitórios em PDFs usando 3 critérios:
    1. Keywords: "OFÍCIO REQUISITÓRIO", "OFICIO REQUISITORIO", "VARA DA FAZENDA PÚBLICA"
    2. Padrão CNJ: \\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}
    3. Estrutura: "AO JUÍZO DA ... VARA"
    
    Mínimo 2/3 critérios para detectar início do ofício.
    """
    
    def __init__(self):
        # Critério 1A: Títulos específicos de ofícios requisitórios
        self.keywords_titulo = [
            "OFÍCIO REQUISITÓRIO Nº",
            "OFICIO REQUISITORIO Nº", 
            "OFÍCIO REQUISITÓRIO N°",
            "OFICIO REQUISITORIO N°",
            "OFÍCIO REQUISITÓRIO NÚMERO",
            "OFICIO REQUISITORIO NUMERO"
        ]
        
        # Critério 1B: Cabeçalho oficial obrigatório
        self.keywords_cabecalho = [
            "TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO",
            "TRIBUNAL DE JUSTICA DO ESTADO DE SAO PAULO"
        ]
        
        # Critério 1C: Vara específica de fazenda pública
        self.keywords_vara = [
            "VARA DE FAZENDA PÚBLICA",
            "VARA DA FAZENDA PÚBLICA"
        ]
        
        # Critério 2: Padrão CNJ conforme especificação
        self.padrao_cnj = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')
        
        # Critério 3: Estrutura de endereçamento
        self.estrutura_vara = "AO JUÍZO DA"
        
        # Heurística para fim do ofício: assinatura + página curta
        self.indicadores_fim = [
            "ASSINADO ELETRONICAMENTE",
            "ASSINATURA ELETRÔNICA",
            "CERTIFICADO DIGITAL",
            "Dr(a).",
            "Juiz(a) de Direito"
        ]
        
        self.tamanho_minimo_pagina = 500  # chars
    
    def detectar_oficio(self, pdf_path: str) -> Tuple[List[int], str]:
        """
        Método principal para detectar ofício em PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Tupla contendo:
            - Lista das páginas do ofício (1-indexed)
            - Texto completo do ofício extraído
            
        Raises:
            Exception: Se houver erro na abertura/leitura do PDF
        """
        try:
            logger.info(f"Iniciando detecção de ofício em: {pdf_path}")
            
            doc = pymupdf.open(pdf_path)
            paginas_oficio = []
            texto_completo = ""
            
            # Analisar cada página
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto_pagina = page.get_text()
                
                logger.debug(f"Analisando página {page_num + 1}: {len(texto_pagina)} chars")
                
                # Aplicar os 3 critérios de detecção
                criterios_atendidos = self._avaliar_criterios(texto_pagina)
                
                # Segundo AGENTS.md: mínimo 2/3 critérios
                if criterios_atendidos >= 2:
                    paginas_oficio.append(page_num + 1)  # 1-indexed
                    logger.info(f"Página {page_num + 1} identificada como ofício ({criterios_atendidos}/3 critérios)")
            
            doc.close()
            
            if not paginas_oficio:
                logger.warning(f"Nenhum ofício detectado em {pdf_path}")
                return [], ""
            
            # Extrair texto completo das páginas identificadas
            texto_completo = self._extrair_texto_oficio(pdf_path, paginas_oficio)
            
            logger.info(f"Ofício detectado em {len(paginas_oficio)} páginas: {paginas_oficio}")
            return paginas_oficio, texto_completo
            
        except Exception as e:
            logger.error(f"Erro ao detectar ofício em {pdf_path}: {e}")
            raise
    
    def _avaliar_criterios(self, texto: str) -> int:
        """
        Avalia quantos critérios de detecção são atendidos pelo texto.
        
        Args:
            texto: Texto da página a ser analisada
            
        Returns:
            Número de critérios atendidos (0-3)
        """
        criterios_atendidos = 0
        texto_upper = texto.upper()
        
        # Critério 1: Validação hierárquica de ofício requisitório
        score_criterio1 = 0
        
        # 1A: Título específico do ofício (peso 3)
        titulo_encontrado = any(titulo.upper() in texto_upper for titulo in self.keywords_titulo)
        if titulo_encontrado:
            score_criterio1 += 3
            logger.debug("Critério 1A - Título de ofício requisitório encontrado")
        
        # 1B: Cabeçalho oficial obrigatório (peso 3)
        cabecalho_encontrado = any(cabecalho.upper() in texto_upper for cabecalho in self.keywords_cabecalho)
        if cabecalho_encontrado:
            score_criterio1 += 3
            logger.debug("Critério 1B - Cabeçalho oficial TJSP encontrado")
        
        # 1C: Vara de fazenda pública (peso 2)
        vara_encontrada = any(vara.upper() in texto_upper for vara in self.keywords_vara)
        if vara_encontrada:
            score_criterio1 += 2
            logger.debug("Critério 1C - Vara de Fazenda Pública encontrada")
        
        # 1D: Contexto específico de requisição (peso 1)
        if "VALOR GLOBAL DA REQUISIÇÃO" in texto_upper or "REQUERENTE:" in texto_upper:
            score_criterio1 += 1
            logger.debug("Critério 1D - Contexto de requisição encontrado")
        
        # Critério 1 atendido se score >= 5 (garantindo elementos essenciais)
        if score_criterio1 >= 5:
            criterios_atendidos += 1
            logger.debug(f"Critério 1 ATENDIDO - Score: {score_criterio1}/9")
        
        # Critério 2: Padrão CNJ
        if self.padrao_cnj.search(texto):
            criterios_atendidos += 1
            matches = self.padrao_cnj.findall(texto)
            logger.debug(f"Critério 2 atendido - Padrões CNJ encontrados: {matches}")
        
        # Critério 3: Estrutura vara específica para ofícios requisitórios
        estruturas_validas = [
            "AO EXCELENTÍSSIMO SENHOR",
            "AO EXMO. SR.",
            "AO EXMO. SENHOR",
            "AO JUÍZO DA",
            "À EXCELENTÍSSIMA SENHORA",
            "À EXMA. SRA."
        ]
        
        for estrutura in estruturas_validas:
            if estrutura.upper() in texto_upper:
                criterios_atendidos += 1
                logger.debug(f"Critério 3 atendido - Estrutura encontrada: {estrutura}")
                break
        
        return criterios_atendidos
    
    def _extrair_texto_oficio(self, pdf_path: str, paginas: List[int]) -> str:
        """
        Extrai texto completo das páginas identificadas como ofício.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            paginas: Lista de páginas (1-indexed) que contêm o ofício
            
        Returns:
            Texto completo do ofício
        """
        try:
            doc = pymupdf.open(pdf_path)
            texto_completo = ""
            
            for page_num in paginas:
                page = doc.load_page(page_num - 1)  # Converter para 0-indexed
                texto_pagina = page.get_text()
                
                # Adicionar separador entre páginas
                if texto_completo:
                    texto_completo += "\n\n--- PÁGINA {} ---\n\n".format(page_num)
                
                texto_completo += texto_pagina
            
            doc.close()
            
            logger.debug(f"Texto completo extraído: {len(texto_completo)} caracteres")
            return texto_completo
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto do ofício: {e}")
            return ""
    
    def _detectar_fim_oficio(self, texto: str) -> bool:
        """
        Detecta se a página representa o fim do ofício usando heurísticas.
        Conforme AGENTS.md: assinatura + página curta (<500 chars).
        
        Args:
            texto: Texto da página
            
        Returns:
            True se for provavelmente o fim do ofício
        """
        # Página muito curta pode indicar fim
        if len(texto) < self.tamanho_minimo_pagina:
            return True
        
        # Buscar indicadores de assinatura
        texto_upper = texto.upper()
        for indicador in self.indicadores_fim:
            if indicador.upper() in texto_upper:
                logger.debug(f"Indicador de fim encontrado: {indicador}")
                return True
        
        return False
    
    def validar_pdf(self, pdf_path: str) -> bool:
        """
        Valida se o arquivo PDF pode ser processado.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            True se o PDF é válido e pode ser processado
        """
        try:
            if not Path(pdf_path).exists():
                logger.error(f"Arquivo não encontrado: {pdf_path}")
                return False
            
            if not pdf_path.lower().endswith('.pdf'):
                logger.error(f"Arquivo não é PDF: {pdf_path}")
                return False
            
            # Testar abertura do PDF
            doc = pymupdf.open(pdf_path)
            if len(doc) == 0:
                logger.error(f"PDF vazio: {pdf_path}")
                doc.close()
                return False
            
            doc.close()
            logger.debug(f"PDF válido: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar PDF {pdf_path}: {e}")
            return False
    
    def obter_estatisticas_deteccao(self, pdf_path: str) -> dict:
        """
        Retorna estatísticas detalhadas da detecção para debug.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Dicionário com estatísticas da detecção
        """
        stats = {
            "total_paginas": 0,
            "paginas_com_keywords": [],
            "paginas_com_cnj": [],
            "paginas_com_estrutura": [],
            "paginas_detectadas": []
        }
        
        try:
            doc = pymupdf.open(pdf_path)
            stats["total_paginas"] = len(doc)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto = page.get_text()
                texto_upper = texto.upper()
                
                # Verificar cada critério individualmente
                for keyword in self.keywords_oficio:
                    if keyword.upper() in texto_upper:
                        stats["paginas_com_keywords"].append(page_num + 1)
                        break
                
                if self.padrao_cnj.search(texto):
                    stats["paginas_com_cnj"].append(page_num + 1)
                
                if self.estrutura_vara.upper() in texto_upper:
                    stats["paginas_com_estrutura"].append(page_num + 1)
                
                # Verificar se atende critério mínimo
                if self._avaliar_criterios(texto) >= 2:
                    stats["paginas_detectadas"].append(page_num + 1)
            
            doc.close()
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de {pdf_path}: {e}")
        
        return stats
