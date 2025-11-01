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

    def detectar_anexo_ii(self, pdf_path: str) -> Tuple[List[int], str]:
        """
        Detecta páginas contendo ANEXO II no PDF.

        Args:
            pdf_path: Caminho para o arquivo PDF (compatível com Windows)

        Returns:
            Tupla contendo:
            - Lista das páginas do ANEXO II (1-indexed)
            - Texto completo do ANEXO II extraído

        Raises:
            Exception: Se houver erro na abertura/leitura do PDF
        """
        try:
            # Normalizar path para compatibilidade Windows/Unix
            pdf_path = str(Path(pdf_path).resolve())
            logger.info(f"Iniciando detecção de ANEXO II em: {pdf_path}")

            doc = pymupdf.open(pdf_path)
            paginas_anexo = []

            # Analisar cada página
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                texto_pagina = page.get_text()

                # Verificar marcadores do ANEXO II
                if self._eh_pagina_anexo_ii(texto_pagina):
                    paginas_anexo.append(page_num + 1)  # 1-indexed
                    logger.info(f"ANEXO II detectado na página {page_num + 1}")

            doc.close()

            if not paginas_anexo:
                logger.info(f"Nenhum ANEXO II detectado em {Path(pdf_path).name}")
                return [], ""

            # Extrair texto completo das páginas do ANEXO II
            texto_completo = self._extrair_texto_anexo(pdf_path, paginas_anexo)

            logger.info(f"ANEXO II encontrado em {len(paginas_anexo)} página(s): {paginas_anexo}")
            return paginas_anexo, texto_completo

        except Exception as e:
            logger.error(f"Erro ao detectar ANEXO II em {pdf_path}: {e}")
            raise

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
