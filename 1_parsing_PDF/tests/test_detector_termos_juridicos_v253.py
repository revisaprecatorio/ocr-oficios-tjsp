"""
Testes para DetectorTermosJuridicos - V2.5.3
Foca na nova funcionalidade de detecção de doença grave
"""

import pytest
from app.detector_termos_juridicos import DetectorTermosJuridicos


class TestDetectorTermosJuridicosV253:
    """Testes das funcionalidades V2.5.3"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup executado antes de cada teste"""
        self.detector = DetectorTermosJuridicos()

    # ==================== TESTES DOENÇA GRAVE (V2.5.3) ====================

    @pytest.mark.v253
    @pytest.mark.detector
    def test_detectar_doenca_grave_termo_completo(self, sample_text_doenca_grave):
        """Deve detectar 'doença grave' no texto"""
        resultado = self.detector.detectar_termos(sample_text_doenca_grave)

        assert resultado['doenca_grave'] is True

    @pytest.mark.v253
    def test_detectar_doenca_grave_variacao_acento(self):
        """Deve detectar 'doença grave' com ou sem acento"""
        textos = [
            "O requerente possui doença grave",
            "O requerente possui doenca grave",
            "DOENÇA GRAVE confirmada",
            "doEnÇa GrAvE",
        ]

        for texto in textos:
            resultado = self.detector.detectar_termos(texto)
            assert resultado['doenca_grave'] is True, f"Falhou para: {texto}"

    @pytest.mark.v253
    def test_detectar_molestia_grave(self):
        """Deve detectar variação 'moléstia grave'"""
        textos = [
            "portador de moléstia grave",
            "portador de molestia grave",
            "MOLÉSTIA GRAVE",
        ]

        for texto in textos:
            resultado = self.detector.detectar_termos(texto)
            assert resultado['doenca_grave'] is True

    @pytest.mark.v253
    def test_detectar_laudo_medico(self):
        """Deve detectar 'laudo médico' como indicador de doença grave"""
        textos = [
            "conforme laudo médico anexo",
            "laudo medico comprovando",
            "LAUDO MÉDICO atesta",
        ]

        for texto in textos:
            resultado = self.detector.detectar_termos(texto)
            assert resultado['doenca_grave'] is True

    @pytest.mark.v253
    def test_detectar_atestado_medico(self):
        """Deve detectar 'atestado médico' como indicador"""
        texto = "atestado médico comprovando a condição"

        resultado = self.detector.detectar_termos(texto)
        assert resultado['doenca_grave'] is True

    @pytest.mark.v253
    def test_detectar_portador_doenca_grave(self):
        """Deve detectar 'portador de doença grave'"""
        texto = "O autor é portador de doença grave conforme CID-10"

        resultado = self.detector.detectar_termos(texto)
        assert resultado['doenca_grave'] is True

    # ==================== CASOS NEGATIVOS ====================

    @pytest.mark.v253
    def test_nao_detectar_doenca_sem_grave(self):
        """Não deve detectar 'doença' sem 'grave'"""
        texto = "O requerente possui uma doença crônica"

        resultado = self.detector.detectar_termos(texto)
        assert resultado['doenca_grave'] is False

    @pytest.mark.v253
    def test_nao_detectar_grave_sem_doenca(self):
        """Não deve detectar 'grave' isolado"""
        texto = "A situação é grave mas não há doença"

        resultado = self.detector.detectar_termos(texto)
        assert resultado['doenca_grave'] is False

    @pytest.mark.v253
    def test_nao_detectar_em_texto_limpo(self, sample_text_sem_termos):
        """Não deve detectar em texto sem indicadores"""
        resultado = self.detector.detectar_termos(sample_text_sem_termos)

        assert resultado['doenca_grave'] is False

    # ==================== TESTES INTEGRADOS (4 CAMPOS) ====================

    @pytest.mark.v253
    def test_retornar_4_campos_v253(self, sample_text_preferencial):
        """Deve retornar 4 campos: preferencial, habilitacao, cessao, doenca_grave"""
        resultado = self.detector.detectar_termos(sample_text_preferencial)

        assert 'preferencial' in resultado
        assert 'habilitacao_herdeiros' in resultado
        assert 'cessao_credito' in resultado
        assert 'doenca_grave' in resultado

    @pytest.mark.v253
    def test_detectar_multiplos_termos_simultaneos(self):
        """Deve detectar múltiplos termos no mesmo texto"""
        texto = """
        PETIÇÃO

        O requerente possui preferência por ser idoso (70 anos)
        e é portador de doença grave (neoplasia maligna) conforme
        laudo médico anexo.

        Solicito preferência no pagamento.
        """

        resultado = self.detector.detectar_termos(texto)

        assert resultado['preferencial'] is True
        assert resultado['doenca_grave'] is True
        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['cessao_credito'] is False  # Sempre False em v2.0+

    # ==================== TESTES DE COMPATIBILIDADE ====================

    @pytest.mark.v253
    def test_cessao_credito_sempre_false(self, sample_text_doenca_grave):
        """Cessão de crédito deve sempre retornar False (desativado v2.0)"""
        resultado = self.detector.detectar_termos(sample_text_doenca_grave)

        assert resultado['cessao_credito'] is False

    @pytest.mark.v253
    def test_preferencial_ainda_funciona(self, sample_text_preferencial):
        """Detecção de preferencial deve continuar funcionando"""
        resultado = self.detector.detectar_termos(sample_text_preferencial)

        assert resultado['preferencial'] is True

    # ==================== TESTES COM CONTEXTO ====================

    @pytest.mark.v253
    def test_detectar_com_contexto_doenca_grave(self, sample_text_doenca_grave):
        """Método com contexto deve funcionar para doença grave"""
        resultado = self.detector.detectar_com_contexto(sample_text_doenca_grave)

        assert resultado['preferencial'] is False
        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['cessao_credito'] is False
        # Contexto não implementado para doença grave ainda
        assert 'contexto_doenca_grave' not in resultado


# ==================== TESTES DE INTEGRAÇÃO V2.5.3 ====================

class TestIntegracaoTermosJuridicosV253:
    """Testes de integração para V2.5.3"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.detector = DetectorTermosJuridicos()

    @pytest.mark.v253
    @pytest.mark.integration
    def test_caso_real_cpf_137250048_03_doenca_grave(self):
        """Teste com caso real: CPF 137.250.048-03 (esperado: doença grave)"""
        texto = """
        LAUDO MÉDICO

        Atesto que JOSÉ SANTOS, CPF 137.250.048-03, é portador de
        doença grave (CID C61 - neoplasia maligna da próstata).

        Solicito preferência no pagamento do precatório conforme
        artigo 100, §2º da Constituição Federal.
        """

        resultado = self.detector.detectar_termos(texto)

        assert resultado['doenca_grave'] is True
        assert resultado['preferencial'] is True

    @pytest.mark.v253
    @pytest.mark.integration
    def test_caso_real_idoso_preferencial_sem_doenca(self):
        """Teste com caso real: apenas idoso + preferencial"""
        texto = """
        PETIÇÃO

        Requerente: CLEBER ROBERTO
        CPF: 037.368.708-76
        Data Nascimento: 22/06/1956 (68 anos)

        Solicito PREFERÊNCIA por idade superior a 60 anos.
        """

        resultado = self.detector.detectar_termos(texto)

        assert resultado['preferencial'] is True
        assert resultado['doenca_grave'] is False
        assert resultado['habilitacao_herdeiros'] is False

    @pytest.mark.v253
    @pytest.mark.integration
    def test_compatibilidade_v252_v253(self):
        """Deve manter compatibilidade com detecções V2.5.2"""
        # Texto que funcionava em V2.5.2
        texto_v252 = "Reconheço a preferência para o credor idoso."

        resultado = self.detector.detectar_termos(texto_v252)

        # Campos V2.5.2 devem continuar funcionando
        assert resultado['preferencial'] is True
        assert resultado['habilitacao_herdeiros'] is False
        assert resultado['cessao_credito'] is False

        # Novo campo V2.5.3 deve estar presente
        assert 'doenca_grave' in resultado
        assert resultado['doenca_grave'] is False
