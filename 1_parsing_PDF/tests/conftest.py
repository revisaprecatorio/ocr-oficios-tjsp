"""
Pytest fixtures compartilhados para testes do Pipeline OCR V2.5.3
"""

import pytest
from pathlib import Path
import sys

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


@pytest.fixture
def sample_text_habilitacao_herdeiros():
    """Texto de exemplo com código 9270 e estrutura completa."""
    return """
    TERMO DE DECLARAÇÃO

    Tipo de petição: 9270 - Habilitação de Herdeiro de Precatório

    Dados da Sucessão

    Requerente Falecido: JOÃO DA SILVA
    CPF: 576.290.808-91
    Data de óbito: 15/03/2023

    Sucessor:
    Nome: MARIA DA SILVA
    CPF: 123.456.789-00

    Solicito a habilitação do herdeiro conforme documentos anexos.
    """


@pytest.fixture
def sample_text_doenca_grave():
    """Texto de exemplo com menção a doença grave."""
    return """
    LAUDO MÉDICO

    Atesto para os devidos fins que o paciente JOSÉ SANTOS, portador do CPF 137.250.048-03,
    é portador de doença grave (neoplasia maligna) conforme CID-10 C61.

    Solicito preferência no pagamento do precatório nos termos do artigo 100, §2º da CF.

    Data: 10/01/2024
    Dr. Pedro Oliveira - CRM 12345
    """


@pytest.fixture
def sample_text_preferencial():
    """Texto de exemplo com pedido de preferência."""
    return """
    PETIÇÃO

    Venho requerer a PREFERÊNCIA no pagamento do precatório,
    tendo em vista que o requerente possui mais de 60 anos de idade.

    Data de Nascimento: 20/05/1950
    CPF: 037.368.708-76
    """


@pytest.fixture
def sample_text_sem_termos():
    """Texto sem termos jurídicos especiais."""
    return """
    OFÍCIO REQUISITÓRIO TJSP

    Processo: 0137444-93.2024.8.26.0500
    Requerente: ANTÔNIO PEREIRA
    CPF: 999.888.777-66

    Valor requisitado: R$ 50.000,00
    Banco: 001 - Bradesco
    Agência: 1234
    Conta: 56789-0
    """


@pytest.fixture
def mock_pdf_path(tmp_path):
    """Cria um arquivo PDF temporário para testes."""
    pdf_file = tmp_path / "test_oficio.pdf"
    pdf_file.write_text("Mock PDF content")
    return str(pdf_file)


@pytest.fixture
def sample_cpf_formatado():
    """CPF formatado padrão para testes."""
    return "576.290.808-91"


@pytest.fixture
def sample_cpf_numerico():
    """CPF apenas números para testes."""
    return "57629080891"


@pytest.fixture
def sample_data_obito():
    """Data de óbito em formato brasileiro."""
    return "15/03/2023"


@pytest.fixture
def sample_data_obito_iso():
    """Data de óbito em formato ISO."""
    from datetime import date
    return date(2023, 3, 15)
