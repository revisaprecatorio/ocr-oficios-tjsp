"""
DetectorOficio V2 - Localiza ofícios requisitórios dentro de PDFs com validação por CPF.
Versão 2.0 - Otimizado para buscar múltiplos ofícios e validar CPF
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
import pymupdf

logger = logging.getLogger(__name__)


class DetectorOficio:
    """
    Detector de Ofícios Requisitórios em PDFs usando 3 critérios:
    1. Keywords: "OFÍCIO REQUISITÓRIO", "OFICIO REQUISITORIO", "VARA DA FAZENDA PÚBLICA"
    2. Padrão CNJ: \\d{7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}
    3. Estrutura: "AO JUÍZO DA ... VARA"
    
    Mínimo 2/3 critérios para detectar início do ofício.
    
    V2: Adiciona busca de múltiplos ofícios e validação por CPF
    """
    
    def __init__(self):
        # Critério 1A: Títulos específicos de ofícios requisitórios
        self.keywords_titulo = [
            "OFÍCIO REQUISITÓRIO Nº",
            "OFICIO REQUISITORIO Nº", 
            "OFÍCIO REQUISITÓRIO N°",
            "OFICIO REQUISITORIO N°",
            "OFÍCIO REQUISITÓRIO NÚMERO",
            "OFICIO REQUISITORIO NUMERO",
            "OFÍCIO REQUISITÓRIO",
            "OFICIO REQUISITORIO"
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
            "DOCUMENTO ASSINADO DIGITALMENTE",
            "Dr(a).",
            "Juiz(a) de Direito"
        ]
        
        self.tamanho_minimo_pagina = 500  # chars
    
    def buscar_todos_oficios(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Busca TODOS os ofícios requisitórios no PDF.
        
        V2: Novo método para suportar PDFs com múltiplos ofícios.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Lista de dicionários, cada um contendo:
            {
                'pagina_inicio': int (1-indexed),
                'paginas': List[int] (1-indexed),
                'texto': str
            }
            
        Example:
            >>> detector = DetectorOficio()
            >>> oficios = detector.buscar_todos_oficios("processo.pdf")
            >>> print(f"Encontrados {len(oficios)} ofício(s)")
        """
        try:
            logger.info(f"Buscando todos ofícios em: {pdf_path}")
            
            doc = pymupdf.open(pdf_path)
            oficios = []
            
            paginas_oficio_atual = []
            texto_oficio_atual = ""
            em_oficio = False
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto_pagina = page.get_text()
                
                criterios = self._avaliar_criterios(texto_pagina)
                
                # Detectou início de NOVO ofício
                if criterios >= 2:
                    # Se já estava em um ofício, salvar o anterior
                    if em_oficio and paginas_oficio_atual:
                        oficios.append({
                            'pagina_inicio': paginas_oficio_atual[0],
                            'paginas': paginas_oficio_atual.copy(),
                            'texto': texto_oficio_atual
                        })
                        logger.info(f"Ofício completo: páginas {paginas_oficio_atual}")
                    
                    # Iniciar novo ofício
                    em_oficio = True
                    paginas_oficio_atual = [page_num + 1]
                    texto_oficio_atual = texto_pagina
                    logger.info(f"Ofício iniciado na página {page_num + 1} ({criterios}/3 critérios)")
                
                # Continuação do ofício atual
                elif em_oficio:
                    # Verificar se é fim do ofício
                    if self._eh_fim_oficio(texto_pagina):
                        # Adicionar página final e salvar ofício
                        paginas_oficio_atual.append(page_num + 1)
                        texto_oficio_atual += f"\n\n--- PÁGINA {page_num + 1} ---\n\n{texto_pagina}"
                        
                        oficios.append({
                            'pagina_inicio': paginas_oficio_atual[0],
                            'paginas': paginas_oficio_atual.copy(),
                            'texto': texto_oficio_atual
                        })
                        logger.info(f"Ofício finalizado: páginas {paginas_oficio_atual}")
                        
                        # Resetar
                        em_oficio = False
                        paginas_oficio_atual = []
                        texto_oficio_atual = ""
                    else:
                        # Continua no ofício
                        paginas_oficio_atual.append(page_num + 1)
                        texto_oficio_atual += f"\n\n--- PÁGINA {page_num + 1} ---\n\n{texto_pagina}"
            
            # Se ainda estava em ofício ao final do PDF
            if em_oficio and paginas_oficio_atual:
                oficios.append({
                    'pagina_inicio': paginas_oficio_atual[0],
                    'paginas': paginas_oficio_atual,
                    'texto': texto_oficio_atual
                })
                logger.info(f"Ofício final: páginas {paginas_oficio_atual}")
            
            doc.close()
            logger.info(f"✅ Total de ofícios encontrados: {len(oficios)}")
            return oficios
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar ofícios: {e}")
            return []
    
    def validar_cpf_no_oficio(self, texto_oficio: str, cpf_formatado: str) -> bool:
        """
        Verifica se CPF está presente no texto do ofício.
        
        V2: Novo método para validação de CPF.
        
        Args:
            texto_oficio: Texto extraído do ofício
            cpf_formatado: CPF no formato 999.999.999-99
            
        Returns:
            True se CPF encontrado, False caso contrário
            
        Example:
            >>> detector.validar_cpf_no_oficio(texto, "116.713.778-77")
            True
        """
        # Buscar CPF formatado (com pontos e traço)
        if cpf_formatado in texto_oficio:
            logger.info(f"✅ CPF {cpf_formatado} encontrado no ofício")
            return True
        
        # Buscar também sem formatação (backup)
        cpf_numerico = cpf_formatado.replace(".", "").replace("-", "")
        if cpf_numerico in texto_oficio:
            logger.info(f"✅ CPF {cpf_numerico} (sem formatação) encontrado no ofício")
            return True
        
        logger.debug(f"❌ CPF {cpf_formatado} NÃO encontrado neste ofício")
        return False
    
    def detectar_oficio(self, pdf_path: str) -> Tuple[List[int], str]:
        """
        Método legado para compatibilidade com V1.
        Detecta o PRIMEIRO ofício no PDF.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Tupla contendo:
            - Lista das páginas do ofício (1-indexed)
            - Texto completo do ofício extraído
        """
        oficios = self.buscar_todos_oficios(pdf_path)
        
        if not oficios:
            logger.warning(f"Nenhum ofício detectado em {pdf_path}")
            return [], ""
        
        # Retornar primeiro ofício
        primeiro_oficio = oficios[0]
        return primeiro_oficio['paginas'], primeiro_oficio['texto']
    
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
        
        # 1B: Cabeçalho oficial obrigatório (peso 3)
        cabecalho_encontrado = any(cabecalho.upper() in texto_upper for cabecalho in self.keywords_cabecalho)
        if cabecalho_encontrado:
            score_criterio1 += 3
        
        # 1C: Vara de fazenda pública (peso 2)
        vara_encontrada = any(vara.upper() in texto_upper for vara in self.keywords_vara)
        if vara_encontrada:
            score_criterio1 += 2
        
        # 1D: Contexto específico de requisição (peso 1)
        if "VALOR GLOBAL DA REQUISIÇÃO" in texto_upper or "REQUERENTE:" in texto_upper:
            score_criterio1 += 1
        
        # Critério 1 atendido se score >= 5 (garantindo elementos essenciais)
        if score_criterio1 >= 5:
            criterios_atendidos += 1
        
        # Critério 2: Padrão CNJ
        if self.padrao_cnj.search(texto):
            criterios_atendidos += 1
        
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
                break
        
        return criterios_atendidos
    
    def _eh_fim_oficio(self, texto: str) -> bool:
        """
        Detecta se a página representa o fim do ofício usando heurísticas.
        
        Args:
            texto: Texto da página
            
        Returns:
            True se for provavelmente o fim do ofício
        """
        texto_upper = texto.upper()
        
        # Buscar indicadores de assinatura
        tem_assinatura = any(
            indicador.upper() in texto_upper 
            for indicador in self.indicadores_fim
        )
        
        # Página muito curta pode indicar fim
        pagina_curta = len(texto) < self.tamanho_minimo_pagina
        
        # Fim do ofício = assinatura + página curta
        return tem_assinatura and pagina_curta
    
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
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar PDF {pdf_path}: {e}")
            return False
