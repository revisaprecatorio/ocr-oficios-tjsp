"""
Testes para DetectorOficio.
Conforme AGENTS.md - teste crítico: detector deve encontrar ofício em qualquer posição.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import pymupdf

from app.detector import DetectorOficio


class TestDetectorOficio:
    """Testes do DetectorOficio"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.detector = DetectorOficio()
    
    def test_avaliar_criterios_todos_atendidos(self):
        """Teste com todos os 3 critérios atendidos"""
        texto = """
        TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO
        OFÍCIO REQUISITÓRIO Nº 123
        AO JUÍZO DA 1ª VARA DA FAZENDA PÚBLICA
        Processo: 0035938-67.2018.8.26.0053
        """
        
        criterios = self.detector._avaliar_criterios(texto)
        assert criterios == 3
    
    def test_avaliar_criterios_minimo_atendido(self):
        """Teste com 2/3 critérios (mínimo para detecção)"""
        texto = """
        OFÍCIO REQUISITÓRIO DO TJSP
        Processo nº: 0176505-63.2021.8.26.0500
        Requerente: FERNANDO SANTOS ERNESTO
        """
        
        criterios = self.detector._avaliar_criterios(texto)
        assert criterios == 2  # Keywords + CNJ
    
    def test_avaliar_criterios_insuficiente(self):
        """Teste com apenas 1 critério (insuficiente)"""
        texto = """
        Simples documento com processo
        Número: 0221031-18.2021.8.26.0500
        Sem outras características de ofício
        """
        
        criterios = self.detector._avaliar_criterios(texto)
        assert criterios == 1  # Apenas CNJ
    
    def test_avaliar_criterios_nenhum(self):
        """Teste sem nenhum critério"""
        texto = """
        Documento qualquer sem características
        de relatório judicial comum
        """
        
        criterios = self.detector._avaliar_criterios(texto)
        assert criterios == 0
    
    def test_detectar_fim_oficio_assinatura(self):
        """Teste detecção de fim por assinatura"""
        texto = """
        ASSINADO ELETRONICAMENTE
        Dr(a). João Silva
        Juiz(a) de Direito
        """
        
        resultado = self.detector._detectar_fim_oficio(texto)
        assert resultado is True
    
    def test_detectar_fim_oficio_pagina_curta(self):
        """Teste detecção de fim por página curta"""
        texto_curto = "Fim do documento"  # Menos de 500 chars
        
        resultado = self.detector._detectar_fim_oficio(texto_curto)
        assert resultado is True
    
    def test_detectar_fim_oficio_pagina_normal(self):
        """Teste página normal (não é fim)"""
        texto_longo = "A" * 1000  # Mais de 500 chars, sem indicadores
        
        resultado = self.detector._detectar_fim_oficio(texto_longo)
        assert resultado is False
    
    def test_validar_pdf_arquivo_inexistente(self):
        """Teste validação de arquivo inexistente"""
        resultado = self.detector.validar_pdf("/caminho/inexistente.pdf")
        assert resultado is False
    
    def test_validar_pdf_arquivo_nao_pdf(self):
        """Teste validação de arquivo não-PDF"""
        with patch('pathlib.Path.exists', return_value=True):
            resultado = self.detector.validar_pdf("documento.txt")
            assert resultado is False
    
    @patch('pymupdf.open')
    def test_validar_pdf_valido(self, mock_open):
        """Teste validação de PDF válido"""
        # Mock do documento PDF
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=5)  # 5 páginas
        mock_doc.close = Mock()
        mock_open.return_value = mock_doc
        
        with patch('pathlib.Path.exists', return_value=True):
            resultado = self.detector.validar_pdf("documento.pdf")
            assert resultado is True
            mock_doc.close.assert_called_once()
    
    @patch('pymupdf.open')
    def test_validar_pdf_vazio(self, mock_open):
        """Teste validação de PDF vazio"""
        # Mock do documento vazio
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=0)  # 0 páginas
        mock_doc.close = Mock()
        mock_open.return_value = mock_doc
        
        with patch('pathlib.Path.exists', return_value=True):
            resultado = self.detector.validar_pdf("vazio.pdf")
            assert resultado is False
            mock_doc.close.assert_called_once()
    
    @patch('pymupdf.open')
    def test_detectar_oficio_sucesso(self, mock_open):
        """Teste detecção bem-sucedida de ofício"""
        # Mock das páginas
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Documento comum sem características"
        
        mock_page2 = Mock()
        mock_page2.get_text.return_value = """
        OFÍCIO REQUISITÓRIO Nº 123
        Processo: 0035938-67.2018.8.26.0053
        AO JUÍZO DA 1ª VARA
        """
        
        mock_page3 = Mock()
        mock_page3.get_text.return_value = "Continuação do ofício com mais detalhes"
        
        # Mock do documento
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=3)
        mock_doc.load_page.side_effect = [mock_page1, mock_page2, mock_page3]
        mock_doc.close = Mock()
        mock_open.return_value = mock_doc
        
        # Executar detecção
        paginas, texto = self.detector.detectar_oficio("teste.pdf")
        
        # Verificar resultados
        assert paginas == [2]  # Apenas página 2 atende critérios
        assert len(texto) > 0  # Deve ter extraído algum texto
        assert "OFÍCIO REQUISITÓRIO" in texto or "0035938-67.2018.8.26.0053" in texto
        mock_doc.close.assert_called()
    
    @patch('pymupdf.open')
    def test_detectar_oficio_nao_encontrado(self, mock_open):
        """Teste quando nenhum ofício é detectado"""
        # Mock da página sem critérios suficientes
        mock_page = Mock()
        mock_page.get_text.return_value = "Documento comum sem ofício"
        
        # Mock do documento
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=1)
        mock_doc.load_page.return_value = mock_page
        mock_doc.close = Mock()
        mock_open.return_value = mock_doc
        
        # Executar detecção
        paginas, texto = self.detector.detectar_oficio("teste.pdf")
        
        # Verificar resultados
        assert paginas == []
        assert texto == ""
        mock_doc.close.assert_called()
    
    @patch('pymupdf.open')
    def test_obter_estatisticas_deteccao(self, mock_open):
        """Teste geração de estatísticas de detecção"""
        # Mock das páginas com diferentes características
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "OFÍCIO REQUISITÓRIO sem mais nada"
        
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Processo: 0035938-67.2018.8.26.0053"
        
        mock_page3 = Mock()
        mock_page3.get_text.return_value = "AO JUÍZO DA 1ª VARA"
        
        # Mock do documento
        mock_doc = Mock()
        mock_doc.__len__ = Mock(return_value=3)
        mock_doc.load_page.side_effect = [mock_page1, mock_page2, mock_page3]
        mock_doc.close = Mock()
        mock_open.return_value = mock_doc
        
        # Executar
        stats = self.detector.obter_estatisticas_deteccao("teste.pdf")
        
        # Verificar
        assert stats["total_paginas"] == 3
        assert 1 in stats["paginas_com_keywords"]
        assert 2 in stats["paginas_com_cnj"] 
        assert 3 in stats["paginas_com_estrutura"]
        mock_doc.close.assert_called()
    
    def test_keywords_case_insensitive(self):
        """Teste que keywords funcionam independente de case"""
        texto_lower = "ofício requisitório do tribunal"
        texto_mixed = "OFICIO REQUISITORIO Do TjSp"
        
        criterios1 = self.detector._avaliar_criterios(texto_lower)
        criterios2 = self.detector._avaliar_criterios(texto_mixed)
        
        assert criterios1 >= 1  # Deve encontrar keyword
        assert criterios2 >= 1  # Deve encontrar keyword
    
    def test_padrao_cnj_regex(self):
        """Teste específico do padrão CNJ"""
        textos_validos = [
            "Processo: 0035938-67.2018.8.26.0053",
            "N° 0176505-63.2021.8.26.0500 - Precatório",
            "CNJ: 0221031-18.2021.8.26.0500"
        ]
        
        textos_invalidos = [
            "Processo: 12345",
            "Número: 123456-78.2021",
            "CNJ incompleto: 0035938"
        ]
        
        for texto in textos_validos:
            matches = self.detector.padrao_cnj.findall(texto)
            assert len(matches) > 0, f"Deveria encontrar CNJ em: {texto}"
        
        for texto in textos_invalidos:
            matches = self.detector.padrao_cnj.findall(texto)
            assert len(matches) == 0, f"Não deveria encontrar CNJ em: {texto}"
