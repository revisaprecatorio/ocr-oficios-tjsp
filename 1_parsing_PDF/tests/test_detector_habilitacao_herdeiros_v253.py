"""
Testes para DetectorHabilitacaoHerdeiros - V2.5.3
Testa detecção de código 9270, extração de CPF sucessor e data de óbito
"""

import pytest
from app.detector_habilitacao_herdeiros import DetectorHabilitacaoHerdeiros


class TestDetectorHabilitacaoHerdeiros:
    """Testes do detector de habilitação de herdeiros"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup executado antes de cada teste"""
        self.detector = DetectorHabilitacaoHerdeiros()

    # ==================== TESTES DE ALTA CONFIANÇA ====================

    @pytest.mark.v253
    @pytest.mark.detector
    def test_detectar_codigo_9270_alta_confianca(self, sample_text_habilitacao_herdeiros, sample_cpf_formatado):
        """Deve detectar código 9270 com alta confiança"""
        resultado = self.detector.detectar(sample_text_habilitacao_herdeiros)

        assert resultado['habilitacao_herdeiros'] is True
        assert resultado['obito'] is True
        assert resultado['nivel_confianca'] == 'ALTA'

    @pytest.mark.v253
    def test_extrair_data_obito_formato_brasileiro(self, sample_text_habilitacao_herdeiros):
        """Deve extrair data de óbito no formato DD/MM/YYYY"""
        resultado = self.detector.detectar(sample_text_habilitacao_herdeiros)

        assert resultado['data_obito'] == '15/03/2023'

    @pytest.mark.v253
    def test_extrair_cpf_sucessor(self, sample_text_habilitacao_herdeiros):
        """Deve extrair CPF do sucessor (herdeiro)"""
        resultado = self.detector.detectar(sample_text_habilitacao_herdeiros)

        assert resultado['cpf_sucessor'] == '123.456.789-00'

    # ==================== TESTES DE MÉDIA CONFIANÇA ====================

    @pytest.mark.v253
    def test_detectar_media_confianca_sem_codigo_9270(self):
        """Deve detectar com média confiança quando há estrutura mas sem código 9270"""
        texto = """
        Habilitação de Herdeiro

        Dados da Sucessão

        Requerente falecido: JOÃO SILVA
        Data de óbito: 10/02/2022

        Sucessor:
        Nome: MARIA SILVA
        """

        resultado = self.detector.detectar(texto)

        assert resultado['habilitacao_herdeiros'] is True
        assert resultado['obito'] is True
        assert resultado['nivel_confianca'] == 'MÉDIA'

    # ==================== TESTES DE BAIXA CONFIANÇA ====================

    @pytest.mark.v253
    def test_detectar_baixa_confianca_so_obito(self):
        """Deve detectar baixa confiança quando há apenas menção a óbito"""
        texto = """
        O autor faleceu em 01/01/2020.
        Não há menção a herdeiros habilitados.
        """

        resultado = self.detector.detectar(texto)

        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['obito'] is True
        assert resultado['nivel_confianca'] == 'BAIXA'

    # ==================== TESTES DE CASOS NEGATIVOS ====================

    @pytest.mark.v253
    def test_nao_detectar_sem_indicadores(self, sample_text_sem_termos):
        """Não deve detectar quando não há nenhum indicador"""
        resultado = self.detector.detectar(sample_text_sem_termos)

        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['obito'] is False
        assert resultado['nivel_confianca'] is None
        assert resultado['data_obito'] is None
        assert resultado['cpf_sucessor'] is None

    @pytest.mark.v253
    def test_texto_vazio(self):
        """Deve retornar valores padrão para texto vazio"""
        resultado = self.detector.detectar("")

        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['obito'] is False
        assert resultado['nivel_confianca'] is None

    # ==================== TESTES DE EXTRAÇÃO ====================

    @pytest.mark.v253
    def test_extrair_data_obito_formatos_validos(self):
        """Deve aceitar diferentes formatos válidos de data"""
        textos = [
            "Data de óbito: 15/03/2023",
            "Óbito em 20/12/2022",
            "Falecimento em 01/01/2021",
        ]

        for texto in textos:
            data = self.detector._extrair_data_obito(texto)
            assert data is not None
            assert len(data) == 10  # DD/MM/YYYY

    @pytest.mark.v253
    def test_extrair_cpf_sucessor_diferentes_formatos(self):
        """Deve extrair CPF em diferentes posições"""
        texto = """
        Sucessor: MARIA DA SILVA
        CPF: 123.456.789-00
        RG: 12.345.678-9
        """

        resultado = self.detector._extrair_cpf_sucessor(texto)
        assert resultado == '123.456.789-00'

    # ==================== TESTES DE VALIDAÇÃO ====================

    @pytest.mark.v253
    def test_validar_padroes_regex(self):
        """Deve validar que os padrões regex funcionam corretamente"""
        testes = self.detector.validar_padroes()

        assert testes['preferencial'] is False  # Não deve detectar preferencial
        assert testes['habilitacao_codigo_9270'] is True
        assert testes['habilitacao_cpf_validado'] is True
        assert testes['cessao'] is False  # Sempre False em v2.0+

    @pytest.mark.v253
    def test_detectar_simples_alta_confianca(self, sample_text_habilitacao_herdeiros):
        """Método simplificado deve retornar True para alta confiança"""
        resultado = self.detector.detectar_simples(sample_text_habilitacao_herdeiros)
        assert resultado is True

    @pytest.mark.v253
    def test_detectar_simples_baixa_confianca(self):
        """Método simplificado deve retornar False para baixa confiança"""
        texto = "O autor faleceu mas não há herdeiros habilitados."
        resultado = self.detector.detectar_simples(texto)
        assert resultado is False

    # ==================== TESTES DE EDGE CASES ====================

    @pytest.mark.v253
    def test_codigo_9270_com_espacos_variados(self):
        """Deve detectar código 9270 mesmo com espaçamento irregular"""
        textos = [
            "9270-Habilitação de Herdeiro",
            "9270 - Habilitação de Herdeiro",
            "9270  -  Habilitação de Herdeiro",
            "9270.Habilitação de Herdeiro",
        ]

        for texto in textos:
            resultado = self.detector.detectar(texto)
            assert resultado['nivel_confianca'] == 'ALTA', f"Falhou para: {texto}"

    @pytest.mark.v253
    def test_data_obito_invalida_nao_retorna_nada(self):
        """Deve ignorar datas inválidas"""
        texto = "Data de óbito: 32/13/2023"  # Data inválida

        resultado = self.detector._extrair_data_obito(texto)
        assert resultado is None

    @pytest.mark.v253
    def test_multiplos_cpfs_retorna_primeiro_sucessor(self):
        """Quando há múltiplos CPFs, deve priorizar o do sucessor"""
        texto = """
        Requerente: João Silva - CPF: 111.111.111-11

        Sucessor: Maria Silva
        CPF: 222.222.222-22

        Advogado: José Santos - CPF: 333.333.333-33
        """

        resultado = self.detector._extrair_cpf_sucessor(texto)
        assert resultado == '222.222.222-22'


# ==================== TESTES DE INTEGRAÇÃO ====================

class TestIntegracaoDetectorHabilitacao:
    """Testes de integração do detector com casos reais"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = DetectorHabilitacaoHerdeiros()

    @pytest.mark.v253
    @pytest.mark.integration
    def test_caso_real_cpf_576290808_91(self):
        """Teste com caso real: CPF 576.290.808-91 (esperado: habilitação detectada)"""
        # Simulação do texto real do PDF
        texto = """
        9270 . Habilitação de Herdeiro de Precatório

        Dados da Sucessão

        Requerente (Falecido):
        Nome: ELIO RODRIGUES BARBOSA
        CPF: 576.290.808-91
        Data de óbito: 22/12/1948

        Sucessor:
        Nome: FULANO DE TAL
        CPF: 123.456.789-00
        """

        resultado = self.detector.detectar(texto)

        assert resultado['habilitacao_herdeiros'] is True
        assert resultado['obito'] is True
        assert resultado['nivel_confianca'] == 'ALTA'
        assert resultado['data_obito'] is not None
        assert resultado['cpf_sucessor'] == '123.456.789-00'

    @pytest.mark.v253
    @pytest.mark.integration
    def test_caso_real_sem_habilitacao(self):
        """Teste com caso real: CPF sem habilitação (controle negativo)"""
        texto = """
        OFÍCIO REQUISITÓRIO

        Requerente: JOSÉ DA SILVA
        CPF: 037.368.708-76
        Data Nascimento: 22/06/1956

        Valor requisitado: R$ 193.918,15
        """

        resultado = self.detector.detectar(texto)

        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['obito'] is False
        assert resultado['nivel_confianca'] is None
