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
        # V2.6.0: Lista de rejeição explícita (documentos que NÃO são ofícios)
        self.termos_rejeicao = [
            "PETIÇÃO",
            "PROCURAÇÃO",
            "DECISÃO",
            "DESPACHO",
            "CERTIDÃO",
            "TERMO DE DECLARAÇÃO",
            "DADOS DO ADVOGADO",
            "SENTENÇA",
            "ACÓRDÃO",
            "RECURSO",
            "AGRAVO",
            "APELAÇÃO",
            "EMBARGOS",
            "CONTESTAÇÃO",
            "MANIFESTAÇÃO"
        ]
        
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
        
        # V2.4.4: Padrões de CPF para busca direta
        self.cpf_patterns = [
            r'CPF/CNPJ:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            r'CPF/CNPJ/RNE:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
            r'CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})',
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
        
        V2.6.0: Adiciona rejeição explícita de documentos não-ofício
        
        Args:
            texto: Texto da página a ser analisada
            
        Returns:
            Número de critérios atendidos (0-3)
        """
        criterios_atendidos = 0
        texto_upper = texto.upper()
        
        # V2.6.0: REJEIÇÃO EXPLÍCITA - Se página contém termo de rejeição, retornar 0
        for termo in self.termos_rejeicao:
            if termo in texto_upper:
                logger.debug(f"   ❌ Página rejeitada: contém '{termo}'")
                return 0  # Não é ofício
        
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
        
        # 1E: V2.6.0: Indicadores adicionais de ofício requisitório (peso 2)
        if "CREDOR(S):" in texto_upper or "CREDORES:" in texto_upper:
            score_criterio1 += 2
        
        # V2.6.0: Critério 1 atendido se score >= 6 (threshold aumentado)
        # Garante que apenas documentos com múltiplos elementos essenciais sejam aceitos
        if score_criterio1 >= 6:
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
            logger.error(f"Erro ao validar PDF: {str(e)}")
            return False
    
    def buscar_cpf_no_pdf(self, pdf_path: str, cpf_formatado: str, inicio: int = 0) -> int:
        """
        Busca CPF no PDF APÓS a página do ANEXO II.
        Prioriza página com "Credor nº:" + CPF.
        
        V2.5.0: Mudanças importantes:
        - Busca APENAS após página do ANEXO II (parâmetro inicio)
        - Prioriza página com "Credor nº:" + CPF
        - Retorna APENAS a página do credor (não lista)
        - Valida que CPF é o mesmo da pasta (não aceita CPF diferente)
        
        Args:
            pdf_path: Caminho do PDF
            cpf_formatado: CPF formatado (XXX.XXX.XXX-XX)
            inicio: Página do TÍTULO do ANEXO II (0-indexed)
        
        Returns:
            Página do credor (0-indexed) ou -1 se não encontrado
        """
        logger.info(f"🔍 Buscando CPF {cpf_formatado} após ANEXO II (página {inicio + 1})...")
        
        try:
            doc = pymupdf.open(pdf_path)
            paginas_encontradas = []
            
            # Buscar APENAS após página do ANEXO II
            for num_pagina in range(inicio, len(doc)):
                page = doc.load_page(num_pagina)
                texto = page.get_text()
                
                # Buscar CPF formatado
                if cpf_formatado in texto:
                    paginas_encontradas.append(num_pagina)
                    logger.info(f"   ✅ CPF encontrado na página {num_pagina + 1}")
                
                # Para PDFs muito grandes, mostrar progresso
                if len(doc) > 500 and (num_pagina + 1) % 100 == 0:
                    logger.info(f"   📄 Processadas {num_pagina + 1}/{len(doc)} páginas...")
            
            if not paginas_encontradas:
                logger.warning(f"⚠️ CPF {cpf_formatado} NÃO encontrado após ANEXO II")
                doc.close()
                return -1
            
            logger.info(f"✅ CPF encontrado em {len(paginas_encontradas)} página(s): {[p+1 for p in paginas_encontradas]}")
            
            # Priorizar página com "Credor nº:" + CPF
            pagina_credor = None
            for num_pag in paginas_encontradas:
                page = doc.load_page(num_pag)
                texto = page.get_text()
                
                # Verificar se tem "Credor nº:" ou "Credor n°.:"
                if re.search(r'Credor\s+n[°º]\.?:\s*\d+', texto, re.IGNORECASE):
                    logger.info(f"   🎯 Página {num_pag + 1} tem 'Credor nº:' + CPF - SELECIONADA!")
                    pagina_credor = num_pag
                    break
            
            # Se não encontrou com "Credor nº:", usar primeira ocorrência
            if pagina_credor is None:
                pagina_credor = paginas_encontradas[0]
                logger.warning(f"   ⚠️ Nenhuma página com 'Credor nº:', usando primeira: {pagina_credor + 1}")
            
            doc.close()
            return pagina_credor
        
        except Exception as e:
            logger.error(f"❌ Erro ao buscar CPF: {str(e)}")
            return -1
    
    def extrair_oficio_por_cpf(self, pdf_path: str, cpf_formatado: str, contexto_paginas: int = 2) -> Dict[str, Any]:
        """
        Extrai ofício buscando diretamente pelo CPF (para PDFs muito grandes).
        
        V2.4.4: Estratégia alternativa para PDFs com 100+ credores:
        1. Buscar CPF diretamente em todas as páginas
        2. Priorizar páginas com "Nome:" + CPF (ofício completo)
        3. Extrair página do CPF + contexto (páginas antes/depois)
        4. Retornar como "ofício" para processamento normal
        
        Args:
            pdf_path: Caminho do PDF
            cpf_formatado: CPF formatado (XXX.XXX.XXX-XX)
            contexto_paginas: Número de páginas antes/depois para incluir (padrão: 2)
        
        Returns:
            Dict com 'paginas' e 'texto' do ofício, ou None se não encontrado
        """
        logger.info(f"🎯 Extraindo ofício por busca direta de CPF (PDF grande)")
        
        # Buscar páginas com o CPF
        paginas_cpf = self.buscar_cpf_no_pdf(pdf_path, cpf_formatado)
        
        if not paginas_cpf:
            logger.error(f"❌ CPF não encontrado no PDF")
            return None
        
        # V2.4.4: Priorizar páginas com "Nome:" + CPF (ofício completo)
        doc = pymupdf.open(pdf_path)
        pagina_principal = paginas_cpf[0]  # Default: primeira ocorrência
        
        for num_pag in paginas_cpf:
            page = doc.load_page(num_pag)
            texto = page.get_text()
            
            # Procurar por padrões de ofício completo
            if re.search(r'Nome:\s*[^\n]+', texto, re.IGNORECASE) and cpf_formatado in texto:
                logger.info(f"   ✅ Página {num_pag + 1} tem 'Nome:' + CPF - usando esta!")
                pagina_principal = num_pag
                break
            elif re.search(r'Credor\s+n[°º]\.?:\s*\d+', texto, re.IGNORECASE) and cpf_formatado in texto:
                logger.info(f"   ✅ Página {num_pag + 1} tem 'Credor nº:' + CPF - usando esta!")
                pagina_principal = num_pag
                break
        
        doc.close()
        
        # Definir range de páginas (página principal + contexto)
        doc = pymupdf.open(pdf_path)
        inicio = max(0, pagina_principal - contexto_paginas)
        fim = min(len(doc) - 1, pagina_principal + contexto_paginas)
        
        paginas_oficio = list(range(inicio, fim + 1))
        
        logger.info(f"📄 Extraindo páginas {inicio + 1} a {fim + 1} (contexto de {contexto_paginas} páginas)")
        
        # Extrair texto das páginas
        texto_completo = ""
        for num_pagina in paginas_oficio:
            page = doc.load_page(num_pagina)
            texto_completo += f"\n\n=== PÁGINA {num_pagina + 1} ===\n\n"
            texto_completo += page.get_text()
        
        doc.close()
        
        resultado = {
            'paginas': paginas_oficio,
            'texto': texto_completo,
            'metodo': 'busca_direta_cpf',
            'pagina_cpf': pagina_principal + 1
        }
        
        logger.info(f"✅ Ofício extraído: {len(paginas_oficio)} páginas (método: busca direta CPF)")
        
        return resultado
