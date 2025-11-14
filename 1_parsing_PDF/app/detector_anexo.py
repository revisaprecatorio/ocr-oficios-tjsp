"""
DetectorAnexoII - Localiza páginas com ANEXO II em PDFs.
Compatível com Windows Server 2022.
"""

import re
import logging
from pathlib import Path
from typing import List, Tuple
import pymupdf


logger = logging.getLogger(__name__)


class DetectorAnexoII:
    """
    Detector de ANEXO II em PDFs de ofícios requisitórios.

    ANEXO II contém dados bancários e financeiros detalhados:
    - Nome do credor
    - CPF/CNPJ
    - Banco, Agência, Conta
    - Valores detalhados (principal, juros, contribuições)
    - Data base de atualização
    """

    def __init__(self):
        # Marcadores principais do ANEXO II
        self.marcadores_anexo = [
            r"ANEXO\s+II",
            r"ANEXO\s+2",
            r"ANEXO\s+DOIS"
        ]

        # Campos esperados no ANEXO II (para validação)
        self.campos_esperados = [
            r"NOME:",
            r"CPF/CNPJ/RNE:",
            r"BANCO:",
            r"AG[ÊE]NCIA:",
            r"CONTA:",
            r"VALOR\s+REQUISITADO:",
            r"TOTAL\s+DESTE\s+REQUERENTE:"
        ]

        # Padrão para detectar estrutura tabular do ANEXO II
        self.padrao_credor = re.compile(r"CREDOR\s+N[ºO]\.?:\s*\d+", re.I)

    def detectar_anexo_ii(self, pdf_path: str, inicio: int = 0) -> Tuple[List[int], str, int]:
        """
        Detecta páginas contendo ANEXO II no PDF.
        
        V2.5.0: Retorna também a página do TÍTULO do ANEXO II.
        FIX v2.4.2: Adiciona parâmetro 'inicio' para buscar ANEXO II após o ofício selecionado.

        Args:
            pdf_path: Caminho para o arquivo PDF (compatível com Windows)
            inicio: Página inicial para busca (0-indexed). Default: 0 (início do PDF)

        Returns:
            Tupla contendo:
            - Lista das páginas do ANEXO II (1-indexed)
            - Texto completo do ANEXO II extraído
            - Página do TÍTULO do ANEXO II (0-indexed) - V2.5.0

        Raises:
            Exception: Se houver erro na abertura/leitura do PDF
        """
        try:
            # Normalizar path para compatibilidade Windows/Unix
            pdf_path = str(Path(pdf_path).resolve())
            logger.info(f"Iniciando detecção de ANEXO II em: {pdf_path} (a partir da página {inicio + 1})")

            doc = pymupdf.open(pdf_path)
            paginas_anexo = []
            pagina_titulo = None

            # V2.5.1: Buscar título do ANEXO II começando algumas páginas ANTES do início
            # Isso garante que não pulamos o título se ele estiver logo antes do início
            inicio_busca_titulo = max(0, inicio - 5)  # Buscar até 5 páginas antes
            
            # Primeiro, buscar apenas o TÍTULO do ANEXO II
            for page_num in range(inicio_busca_titulo, len(doc)):
                page = doc.load_page(page_num)
                texto_pagina = page.get_text()

                # V2.5.0: Detectar página do TÍTULO (primeira ocorrência)
                if pagina_titulo is None and self._eh_titulo_anexo_ii(texto_pagina):
                    pagina_titulo = page_num  # 0-indexed
                    logger.info(f"📌 TÍTULO do ANEXO II detectado na página {page_num + 1}")
                    break  # Parar após encontrar o título

            # Depois, buscar todas as páginas do ANEXO II a partir do título (ou início)
            inicio_anexo = pagina_titulo if pagina_titulo is not None else inicio
            for page_num in range(inicio_anexo, len(doc)):
                page = doc.load_page(page_num)
                texto_pagina = page.get_text()

                # Verificar marcadores do ANEXO II (todas as páginas)
                if self._eh_pagina_anexo_ii(texto_pagina):
                    paginas_anexo.append(page_num + 1)  # 1-indexed
                    logger.info(f"ANEXO II detectado na página {page_num + 1}")

            doc.close()

            if not paginas_anexo:
                logger.info(f"Nenhum ANEXO II detectado em {Path(pdf_path).name}")
                return [], "", -1

            # Extrair texto completo das páginas do ANEXO II
            texto_completo = self._extrair_texto_anexo(pdf_path, paginas_anexo)

            # Se não encontrou título específico, usar primeira página do ANEXO II
            if pagina_titulo is None:
                pagina_titulo = paginas_anexo[0] - 1  # Converter para 0-indexed
                logger.warning(f"⚠️ Título do ANEXO II não detectado, usando primeira página: {paginas_anexo[0]}")

            logger.info(f"ANEXO II encontrado em {len(paginas_anexo)} página(s): {paginas_anexo}")
            logger.info(f"📌 Página do título: {pagina_titulo + 1} (0-indexed: {pagina_titulo})")
            return paginas_anexo, texto_completo, pagina_titulo

        except Exception as e:
            logger.error(f"Erro ao detectar ANEXO II em {pdf_path}: {e}")
            raise

    def _eh_titulo_anexo_ii(self, texto: str) -> bool:
        """
        Verifica se a página contém o TÍTULO "ANEXO II".
        
        V2.5.0: Detecta apenas a página com o TÍTULO do ANEXO II,
        não páginas subsequentes com dados de credores.
        
        Critérios:
        1. Deve ter "ANEXO II" em destaque (sozinho na linha ou em caixa)
        2. Logo em seguida deve começar "Credor nº: 1" ou "Credor n°.: 1"
        3. Não deve ser apenas uma menção ao ANEXO II
        
        Args:
            texto: Texto da página
        
        Returns:
            True se é a página do TÍTULO do ANEXO II
        """
        texto_upper = texto.upper()
        
        # 1. Deve conter "ANEXO II"
        tem_anexo_ii = False
        for marcador in self.marcadores_anexo:
            if re.search(marcador, texto_upper):
                tem_anexo_ii = True
                break
        
        if not tem_anexo_ii:
            return False
        
        # 2. Deve ter "Credor nº: 1" ou "Credor n°.: 1" (primeiro credor)
        # Aceita variações: "Credor nº.: 1", "Credor n°: 1", "Credor nº: 1"
        tem_primeiro_credor = bool(re.search(
            r'Credor\s+n[°º]\.?:\s*1\b',
            texto,
            re.IGNORECASE
        ))
        
        # 3. Não deve ser apenas menção (deve ter estrutura de dados)
        tem_estrutura = (
            'NOME:' in texto_upper or
            'CPF/CNPJ' in texto_upper or
            'DATA DO NASCIMENTO' in texto_upper
        )
        
        return tem_anexo_ii and tem_primeiro_credor and tem_estrutura
    
    def _eh_pagina_anexo_ii(self, texto: str) -> bool:
        """
        Verifica se a página contém ANEXO II com dados bancários REAIS.
        
        NOVA VERSÃO (FINDING 05): Detecta apenas ANEXO II com dados bancários,
        evitando falsos positivos (páginas de decisão e índices).

        Args:
            texto: Texto da página

        Returns:
            True se a página contém ANEXO II bancário real
        """
        texto_upper = texto.upper()

        # PRÉ-REQUISITO: Deve conter "ANEXO II"
        marcador_encontrado = False
        for marcador in self.marcadores_anexo:
            if re.search(marcador, texto_upper):
                marcador_encontrado = True
                break

        if not marcador_encontrado:
            return False

        # === VERIFICAR PRESENÇA DE DADOS BANCÁRIOS REAIS ===
        
        # 1. CPF formatado (XXX.XXX.XXX-XX)
        padrao_cpf = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
        tem_cpf = bool(padrao_cpf.search(texto))
        
        # 2. Estrutura de credor
        tem_credor = bool(self.padrao_credor.search(texto)) or (
            'NOME:' in texto_upper and 'CPF' in texto_upper
        )
        
        # 3. Valor monetário (aceita variantes: "Valor:", "R$", etc.)
        tem_valor = (
            'VALOR TOTAL' in texto_upper or 
            'VALOR REQUISITADO' in texto_upper or
            'TOTAL DESTE REQUERENTE' in texto_upper or
            ('VALOR' in texto_upper and 'R$' in texto_upper)  # Variante simples
        )
        
        # === EXCLUIR FALSOS POSITIVOS CONHECIDOS ===
        
        # Falso positivo 1: Páginas de DECISÃO judicial
        eh_decisao = (
            'PROCESSO DIGITAL' in texto_upper or
            'DECISÃO' in texto_upper
        ) and (
            'JUIZ' in texto_upper or
            'DESEMBARGADOR' in texto_upper
        )
        
        # Falso positivo 2: Índices de documentos
        eh_indice = (
            'ÍNDICE' in texto_upper or 
            'SUMÁRIO' in texto_upper
        ) and (
            'CAPÍTULO' in texto_upper or
            texto.count('\n') < 30  # Índices são compactos
        )
        
        # Falso positivo 3: Menções ao ANEXO II sem dados
        # (ex: "...observando-se também a Portaria [...] seja instruído com planilha...")
        menciona_portaria = (
            'PORTARIA' in texto_upper and 
            'INSTRUÍDO' in texto_upper
        )
        
        # === DECISÃO FINAL ===
        
        # Deve ter dados bancários reais E não ser falso positivo
        tem_dados_reais = tem_cpf and tem_credor and tem_valor
        eh_falso_positivo = eh_decisao or eh_indice or (menciona_portaria and not tem_cpf)
        
        if tem_dados_reais and not eh_falso_positivo:
            logger.info(f"✅ ANEXO II bancário confirmado (CPF: {tem_cpf}, Credor: {tem_credor}, Valor: {tem_valor})")
            return True
        elif marcador_encontrado and not tem_dados_reais:
            # Log de falso positivo rejeitado
            motivo = []
            if eh_decisao:
                motivo.append("página de DECISÃO judicial")
            if eh_indice:
                motivo.append("ÍNDICE de documento")
            if menciona_portaria:
                motivo.append("apenas menção à Portaria")
            if not tem_cpf:
                motivo.append("sem CPF formatado")
            if not tem_credor:
                motivo.append("sem estrutura de credor")
            if not tem_valor:
                motivo.append("sem valores monetários")
            
            logger.debug(f"⚠️ ANEXO II rejeitado (falso positivo): {', '.join(motivo)}")
            return False
        
        return False

    def _extrair_texto_anexo(self, pdf_path: str, paginas: List[int]) -> str:
        """
        Extrai texto completo das páginas identificadas como ANEXO II.

        Args:
            pdf_path: Caminho para o arquivo PDF
            paginas: Lista de páginas (1-indexed) que contêm ANEXO II

        Returns:
            Texto completo do ANEXO II
        """
        try:
            pdf_path = str(Path(pdf_path).resolve())
            doc = pymupdf.open(pdf_path)
            texto_completo = ""

            for page_num in paginas:
                page = doc.load_page(page_num - 1)  # Converter para 0-indexed
                texto_pagina = page.get_text()

                # Adicionar separador entre páginas
                if texto_completo:
                    texto_completo += f"\n\n--- PÁGINA {page_num} ---\n\n"

                texto_completo += texto_pagina

            doc.close()

            logger.debug(f"Texto ANEXO II extraído: {len(texto_completo)} caracteres")
            return texto_completo

        except Exception as e:
            logger.error(f"Erro ao extrair texto do ANEXO II: {e}")
            return ""

    def validar_pdf(self, pdf_path: str) -> bool:
        """
        Valida se o arquivo PDF pode ser processado.
        Compatível com Windows Server.

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            True se o PDF é válido e pode ser processado
        """
        try:
            pdf_path = Path(pdf_path).resolve()

            if not pdf_path.exists():
                logger.error(f"Arquivo não encontrado: {pdf_path}")
                return False

            if pdf_path.suffix.lower() != '.pdf':
                logger.error(f"Arquivo não é PDF: {pdf_path}")
                return False

            # Testar abertura do PDF
            doc = pymupdf.open(str(pdf_path))
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
        Retorna estatísticas detalhadas da detecção de ANEXO II.

        Args:
            pdf_path: Caminho para o arquivo PDF

        Returns:
            Dicionário com estatísticas da detecção
        """
        stats = {
            "total_paginas": 0,
            "paginas_com_marcador": [],
            "paginas_com_campos": [],
            "paginas_detectadas": [],
            "campos_por_pagina": {}
        }

        try:
            pdf_path = str(Path(pdf_path).resolve())
            doc = pymupdf.open(pdf_path)
            stats["total_paginas"] = len(doc)

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto = page.get_text()
                texto_upper = texto.upper()

                # Verificar marcador
                for marcador in self.marcadores_anexo:
                    if re.search(marcador, texto_upper):
                        stats["paginas_com_marcador"].append(page_num + 1)
                        break

                # Contar campos encontrados
                campos_encontrados = []
                for campo in self.campos_esperados:
                    if re.search(campo, texto_upper):
                        campos_encontrados.append(campo)

                if campos_encontrados:
                    stats["paginas_com_campos"].append(page_num + 1)
                    stats["campos_por_pagina"][page_num + 1] = campos_encontrados

                # Verificar se atende critério de detecção
                if self._eh_pagina_anexo_ii(texto):
                    stats["paginas_detectadas"].append(page_num + 1)

            doc.close()

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de {pdf_path}: {e}")

        return stats
    
    def extrair_secao_credor_no_anexo(self, pdf_path: str, pagina_credor: int, cpf_formatado: str) -> str:
        """
        Extrai APENAS a seção do credor específico dentro do ANEXO II.
        
        V2.5.0: Nova estratégia usando página do credor
        - Extrai texto da página do credor
        - Identifica início ("Credor nº: X") e fim (próximo "Credor nº:" ou fim da página)
        - Reduz texto enviado ao LLM em 99%
        - Elimina confusão com dados de outros credores
        
        Estratégia:
        1. Extrai texto da página do credor
        2. Encontra posição do CPF
        3. Volta até encontrar "Credor nº:" anterior
        4. Avança até encontrar próximo "Credor nº:" (ou fim)
        5. Retorna apenas esse trecho
        
        Args:
            pdf_path: Caminho do PDF
            pagina_credor: Página do credor (0-indexed)
            cpf_formatado: CPF do credor (XXX.XXX.XXX-XX)
        
        Returns:
            Seção do credor ou texto completo da página (fallback)
        """
        try:
            logger.info(f"🎯 Extraindo seção focada do credor (página {pagina_credor + 1}, CPF: {cpf_formatado})")
            
            # Extrair texto da página do credor
            doc = pymupdf.open(pdf_path)
            page = doc.load_page(pagina_credor)
            texto_pagina = page.get_text()
            doc.close()
            
            # Encontrar posição do CPF
            pos_cpf = texto_pagina.find(cpf_formatado)
            if pos_cpf == -1:
                logger.warning(f"⚠️ CPF não encontrado na página {pagina_credor + 1}")
                return texto_pagina
            
            # Encontrar "Credor nº:" ANTES do CPF
            # Buscar todos os "Credor nº:" na página
            matches = list(re.finditer(r'Credor\s+n[°º]\.?:\s*\d+', texto_pagina, re.IGNORECASE))
            
            if not matches:
                logger.warning(f"⚠️ 'Credor nº:' não encontrado na página")
                return texto_pagina
            
            # Encontrar o "Credor nº:" que precede o CPF
            inicio = 0
            for match in matches:
                if match.start() < pos_cpf:
                    inicio = match.start()
                else:
                    break
            
            # Encontrar próximo "Credor nº:" APÓS o CPF (ou fim da página)
            fim = len(texto_pagina)
            for match in matches:
                if match.start() > pos_cpf:
                    fim = match.start()
                    break
            
            # Extrair seção
            secao = texto_pagina[inicio:fim].strip()
            
            logger.info(f"✅ Seção do credor extraída")
            logger.info(f"   Tamanho: {len(secao)} chars (vs {len(texto_pagina)} total)")
            logger.info(f"   Redução: {100 * (1 - len(secao)/len(texto_pagina)):.1f}%")
            
            return secao
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair seção do credor: {e}")
            logger.warning(f"   Fallback: usando página completa")
            try:
                doc = pymupdf.open(pdf_path)
                page = doc.load_page(pagina_credor)
                texto = page.get_text()
                doc.close()
                return texto
            except:
                return ""
    
    def pre_extrair_dados_com_regex(self, texto_secao: str) -> dict:
        """
        Pré-extrai dados usando regex antes de enviar ao LLM.
        
        V2.5.0: Extração híbrida (regex + LLM)
        - Regex para campos estruturados (CPF, data, banco)
        - LLM para campos complexos (nome, valores)
        - Maior precisão e menor dependência do LLM
        
        Args:
            texto_secao: Texto da seção do credor
        
        Returns:
            Dict com campos extraídos via regex
        """
        dados = {}
        
        try:
            logger.info("📋 Pré-extraindo dados com regex...")
            
            # CPF/CNPJ
            cpf_match = re.search(r'CPF/CNPJ(?:/RNE)?:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})', texto_secao, re.IGNORECASE)
            if cpf_match:
                dados['credor_cpf_cnpj'] = cpf_match.group(1)
                logger.info(f"   ✅ CPF: {dados['credor_cpf_cnpj']}")
            
            # Data de nascimento
            data_match = re.search(r'Data\s+(?:do\s+)?nascimento:\s*(\d{2}/\d{2}/\d{4})', texto_secao, re.IGNORECASE)
            if data_match:
                # Converter DD/MM/YYYY para YYYY-MM-DD
                dia, mes, ano = data_match.group(1).split('/')
                dados['data_nascimento'] = f"{ano}-{mes}-{dia}"
                logger.info(f"   ✅ Data Nasc: {dados['data_nascimento']}")
            
            # Banco
            banco_match = re.search(r'Banco:\s*(\d+)\s*-?\s*([^\n]+)', texto_secao, re.IGNORECASE)
            if banco_match:
                dados['banco'] = f"{banco_match.group(1)} - {banco_match.group(2).strip()}"
                logger.info(f"   ✅ Banco: {dados['banco']}")
            
            # Agência
            agencia_match = re.search(r'Ag[êe]ncia:\s*([\d-]+)', texto_secao, re.IGNORECASE)
            if agencia_match:
                dados['agencia'] = agencia_match.group(1).strip()
                logger.info(f"   ✅ Agência: {dados['agencia']}")
            
            # Conta
            conta_match = re.search(r'Conta:\s*([\d-]+)', texto_secao, re.IGNORECASE)
            if conta_match:
                dados['conta'] = conta_match.group(1).strip()
                logger.info(f"   ✅ Conta: {dados['conta']}")
            
            # Valor requisitado (múltiplos padrões)
            valor_patterns = [
                r'Valor\s+requisitado:\s*R\$\s*([\d.,]+)',
                r'Total\s+deste\s+requerente:\s*R\$\s*([\d.,]+)',
                r'Valor\s+total:\s*R\$\s*([\d.,]+)'
            ]
            
            for pattern in valor_patterns:
                valor_match = re.search(pattern, texto_secao, re.IGNORECASE)
                if valor_match:
                    valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                    try:
                        dados['valor_total_requisitado'] = float(valor_str)
                        logger.info(f"   ✅ Valor: R$ {dados['valor_total_requisitado']:.2f}")
                        break
                    except ValueError:
                        pass
            
            # Doença grave
            doenca_match = re.search(r'Portador\s+de\s+doen[çc]a\s+grave:\s*(Sim|N[ãa]o)', texto_secao, re.IGNORECASE)
            if doenca_match:
                dados['doenca_grave'] = doenca_match.group(1).upper() == 'SIM'
                logger.info(f"   ✅ Doença grave: {dados['doenca_grave']}")
            
            logger.info(f"📋 Pré-extraídos {len(dados)} campos com regex")
            
        except Exception as e:
            logger.error(f"❌ Erro ao pré-extrair dados: {e}")
        
        return dados
