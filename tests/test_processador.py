"""
Testes para ProcessadorOficio.
Conforme AGENTS.md - testes do pipeline completo e integração.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from decimal import Decimal

from app.processador import ProcessadorOficio
from app.schemas import OficioRequisitorio, ProcessoMetadata, OficioCompleto


class TestProcessadorOficio:
    """Testes do ProcessadorOficio"""
    
    def setup_method(self):
        """Setup para cada teste"""
        self.api_key = "sk-test-key"
        self.db_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }
        
        with patch('app.processador.OpenAI'):
            self.processador = ProcessadorOficio(self.api_key, self.db_config)
    
    def test_extrair_metadata_arquivo_valido(self):
        """Teste extração de metadata de arquivo válido"""
        pdf_path = "./Processos/02174781824/0176505-63.2021.8.26.0500.pdf"
        
        metadata = self.processador._extrair_metadata_arquivo(pdf_path)
        
        assert metadata is not None
        assert metadata.cpf == "02174781824"
        assert metadata.numero_processo == "0176505-63.2021.8.26.0500"
        assert metadata.processado is False
        assert isinstance(metadata.timestamp_processamento, datetime)
    
    def test_extrair_metadata_arquivo_cpf_invalido(self):
        """Teste com CPF inválido"""
        pdf_path = "./Processos/123456789/0176505-63.2021.8.26.0500.pdf"
        
        metadata = self.processador._extrair_metadata_arquivo(pdf_path)
        
        assert metadata is None
    
    def test_extrair_metadata_arquivo_cpf_nao_numerico(self):
        """Teste com CPF não numérico"""
        pdf_path = "./Processos/abc12345678/0176505-63.2021.8.26.0500.pdf"
        
        metadata = self.processador._extrair_metadata_arquivo(pdf_path)
        
        assert metadata is None
    
    @patch('app.processador.OpenAI')
    def test_extrair_dados_llm_sucesso(self, mock_openai_class):
        """Teste extração LLM bem-sucedida"""
        # Mock da resposta da OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "FERNANDO SANTOS ERNESTO",
            "vara": "1ª VARA DE FAZENDA PÚBLICA",
            "valor_total_requisitado": "15000.50"
        }'''
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Reinicializar processador com mock
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        texto_oficio = "OFÍCIO REQUISITÓRIO teste"
        resultado = processador._extrair_dados_llm(texto_oficio)
        
        assert resultado is not None
        assert resultado["processo_origem"] == "0035938-67.2018.8.26.0053"
        assert resultado["requerente_caps"] == "FERNANDO SANTOS ERNESTO"
        assert resultado["vara"] == "1ª VARA DE FAZENDA PÚBLICA"
    
    @patch('app.processador.OpenAI')
    def test_extrair_dados_llm_json_invalido(self, mock_openai_class):
        """Teste com resposta JSON inválida da LLM"""
        # Mock da resposta inválida
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "JSON inválido { malformed"
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Reinicializar processador com mock
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        resultado = processador._extrair_dados_llm("texto teste")
        
        assert resultado is None
    
    @patch('app.processador.OpenAI')
    def test_extrair_dados_llm_com_markdown(self, mock_openai_class):
        """Teste extração removendo markdown code blocks"""
        # Mock com resposta em markdown
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
        {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE"
        }
        ```'''
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        # Reinicializar processador com mock
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        resultado = processador._extrair_dados_llm("texto teste")
        
        assert resultado is not None
        assert resultado["processo_origem"] == "0035938-67.2018.8.26.0053"
    
    @patch('psycopg2.connect')
    def test_salvar_postgres_sucesso(self, mock_connect):
        """Teste salvamento PostgreSQL bem-sucedido"""
        # Mock da conexão e cursor
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Criar dados de teste
        metadata = ProcessoMetadata(
            cpf="02174781824",
            numero_processo="0176505-63.2021.8.26.0500",
            texto_completo_oficio="Texto do ofício",
            paginas_oficio=[1, 2],
            processado=True
        )
        
        oficio = OficioRequisitorio(
            processo_origem="0035938-67.2018.8.26.0053",
            requerente_caps="FERNANDO SANTOS ERNESTO",
            vara="1ª VARA DE FAZENDA PÚBLICA"
        )
        
        oficio_completo = OficioCompleto(
            metadata=metadata,
            oficio=oficio
        )
        
        # Executar salvamento
        resultado = self.processador.salvar_postgres(oficio_completo)
        
        # Verificar chamadas
        assert resultado is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_salvar_postgres_erro(self, mock_connect):
        """Teste erro no salvamento PostgreSQL"""
        # Mock que gera exceção
        mock_connect.side_effect = Exception("Erro de conexão")
        
        # Criar dados mínimos
        metadata = ProcessoMetadata(
            cpf="02174781824",
            numero_processo="0176505-63.2021.8.26.0500",
            texto_completo_oficio="Texto",
            paginas_oficio=[1]
        )
        
        oficio_completo = OficioCompleto(
            metadata=metadata,
            oficio=None
        )
        
        # Executar salvamento
        resultado = self.processador.salvar_postgres(oficio_completo)
        
        assert resultado is False
    
    @patch('app.processador.ProcessadorOficio.salvar_postgres')
    @patch('app.processador.DetectorOficio')
    @patch('app.processador.OpenAI')
    def test_processar_arquivo_completo_sucesso(self, mock_openai, mock_detector_class, mock_salvar):
        """Teste processamento completo bem-sucedido"""
        # Mock do detector
        mock_detector = Mock()
        mock_detector.validar_pdf.return_value = True
        mock_detector.detectar_oficio.return_value = ([1, 2], "Texto do ofício")
        mock_detector_class.return_value = mock_detector
        
        # Mock da resposta LLM
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "FERNANDO SANTOS ERNESTO"
        }'''
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Reinicializar processador
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        # Executar processamento
        pdf_path = "./Processos/02174781824/0176505-63.2021.8.26.0500.pdf"
        resultado = processador.processar_arquivo(pdf_path)
        
        # Verificar resultado
        assert resultado is not None
        assert resultado.metadata.processado is True
        assert resultado.oficio is not None
        assert resultado.oficio.processo_origem == "0035938-67.2018.8.26.0053"
    
    @patch('app.processador.DetectorOficio')
    def test_processar_arquivo_pdf_invalido(self, mock_detector_class):
        """Teste com PDF inválido"""
        # Mock do detector retornando inválido
        mock_detector = Mock()
        mock_detector.validar_pdf.return_value = False
        mock_detector_class.return_value = mock_detector
        
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        resultado = processador.processar_arquivo("arquivo_invalido.pdf")
        
        assert resultado is None
    
    @patch('app.processador.DetectorOficio')
    def test_processar_arquivo_oficio_nao_detectado(self, mock_detector_class):
        """Teste quando ofício não é detectado"""
        # Mock do detector não encontrando ofício
        mock_detector = Mock()
        mock_detector.validar_pdf.return_value = True
        mock_detector.detectar_oficio.return_value = ([], "")
        mock_detector_class.return_value = mock_detector
        
        processador = ProcessadorOficio(self.api_key, self.db_config)
        
        pdf_path = "./Processos/02174781824/0176505-63.2021.8.26.0500.pdf"
        resultado = processador.processar_arquivo(pdf_path)
        
        # Deve retornar resultado mas sem ofício processado
        assert resultado is not None
        assert resultado.metadata.processado is False
        assert resultado.oficio is None
        assert resultado.metadata.paginas_oficio == []
    
    @patch('pathlib.Path.rglob')
    @patch('pathlib.Path.exists')
    def test_processar_pasta_estatisticas(self, mock_exists, mock_rglob):
        """Teste geração de estatísticas do processamento da pasta"""
        # Mock da estrutura de arquivos
        mock_exists.return_value = True
        mock_files = [
            Mock(spec=str, __str__=lambda x: "file1.pdf"),
            Mock(spec=str, __str__=lambda x: "file2.pdf")
        ]
        mock_rglob.return_value = mock_files
        
        # Mock do processamento
        with patch.object(self.processador, 'processar_arquivo') as mock_processar:
            with patch.object(self.processador, 'salvar_postgres') as mock_salvar:
                # Simular resultados diferentes
                resultado1 = Mock()
                resultado1.oficio = Mock()  # Sucesso com ofício
                
                resultado2 = None  # Erro no processamento
                
                mock_processar.side_effect = [resultado1, resultado2]
                mock_salvar.return_value = True
                
                # Executar processamento
                stats = self.processador.processar_pasta("./test_dir")
                
                # Verificar estatísticas
                assert stats["total_arquivos"] == 2
                assert stats["processados_sucesso"] == 1
                assert stats["processados_erro"] == 1
                assert stats["oficios_detectados"] == 1
                assert stats["oficios_salvos"] == 1
