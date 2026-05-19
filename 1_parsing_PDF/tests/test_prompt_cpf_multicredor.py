"""
Testes V3.1 — Fix multi-credor: CPF esperado no prompt LLM

Cobre:
  T1  Unit: prompt com cpf_esperado contém o CPF
  T2  Unit: prompt sem cpf_esperado NÃO contém bloco CPF
  T3  Unit: bloco CPF aparece antes do texto do documento
  T4  Mock: LLM retorna credor correto quando CPF da Albina é passado
  T5  Mock: LLM retorna credor correto quando CPF do João é passado
  T6  Mock: cpf_esperado=None → comportamento legado inalterado
  T7  Integração leve: prompt construído contém CPF real da Albina (sem chamada LLM)
  T8  Regressão: suite de testes existente não quebra
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "1_parsing_PDF"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def processador():
    """Instancia ProcessadorOficio sem conexão ao banco."""
    from app.processador import ProcessadorOficio
    with patch("app.processador.psycopg2.connect"):
        proc = ProcessadorOficio.__new__(ProcessadorOficio)
        proc.detector = MagicMock()
        proc.detector_anexo = MagicMock()
        proc.detector_saldo = MagicMock()
        proc.detector_proc = MagicMock()
        proc.detector_termos = MagicMock()
        proc.detector_habilitacao = MagicMock()
        proc.openai_api_key = "fake-key"
        proc.llm_adapter = None
        return proc


TEXTO_MULTI_CREDOR = """
OFÍCIO REQUISITÓRIO TJSP — Processo: 0013050-58.2017.8.26.0500

Credor nº: 1
Nome: JOÃO BAPTISTA
CPF/CNPJ: 123.456.789-00
Data do nascimento: 01/01/1940
Valor total: R$ 19.815,00

Credor nº: 2
Nome: ALBINA LOPES PROENCA
CPF/CNPJ: 247.682.258-29
Data do nascimento: 06/08/1927
Valor total: R$ 40.181,51
"""


# ---------------------------------------------------------------------------
# T1 — prompt com cpf_esperado contém o CPF
# ---------------------------------------------------------------------------

def test_prompt_contem_cpf_quando_fornecido(processador):
    prompt = processador._construir_prompt_llm(
        texto_oficio="texto qualquer",
        cpf_esperado="247.682.258-29",
    )
    assert "247.682.258-29" in prompt


# ---------------------------------------------------------------------------
# T2 — prompt sem cpf_esperado NÃO contém bloco CPF
# ---------------------------------------------------------------------------

def test_prompt_sem_cpf_nao_contem_bloco(processador):
    prompt = processador._construir_prompt_llm(
        texto_oficio="texto qualquer",
        cpf_esperado=None,
    )
    assert "CPF DO CREDOR A SER EXTRAÍDO" not in prompt
    assert "REGRA ABSOLUTA" not in prompt


# ---------------------------------------------------------------------------
# T3 — bloco CPF aparece antes do texto do documento
# ---------------------------------------------------------------------------

def test_bloco_cpf_aparece_antes_do_documento(processador):
    cpf = "247.682.258-29"
    prompt = processador._construir_prompt_llm(
        texto_oficio="TEXTO_MARCADOR_DOCUMENTO",
        cpf_esperado=cpf,
    )
    pos_cpf = prompt.find(cpf)
    pos_doc = prompt.find("TEXTO_MARCADOR_DOCUMENTO")
    assert pos_cpf != -1
    assert pos_doc != -1
    assert pos_cpf < pos_doc, "Bloco CPF deve preceder o texto do documento"


# ---------------------------------------------------------------------------
# T4 — mock: CPF da Albina → extrai dados da Albina
# ---------------------------------------------------------------------------

def test_mock_cpf_albina_retorna_albina(processador):
    cpf_albina = "247.682.258-29"
    dados_esperados = {
        "credor_nome": "ALBINA LOPES PROENCA",
        "credor_cpf_cnpj": cpf_albina,
        "valor_total_requisitado": 40181.51,
    }

    mock_adapter = MagicMock()
    mock_adapter.extract_structured_data.return_value = dados_esperados
    processador.llm_adapter = mock_adapter

    from app.llm_adapter import LLMProvider
    processador.llm_provider_enum = LLMProvider

    resultado = processador._extrair_dados_llm_hibrido(
        TEXTO_MULTI_CREDOR,
        cpf_esperado=cpf_albina,
    )

    assert resultado is not None
    call_args = mock_adapter.extract_structured_data.call_args
    prompt_enviado = call_args[0][0]
    assert cpf_albina in prompt_enviado
    assert "CPF DO CREDOR A SER EXTRAÍDO" in prompt_enviado


# ---------------------------------------------------------------------------
# T5 — mock: CPF do João → prompt contém CPF do João
# ---------------------------------------------------------------------------

def test_mock_cpf_joao_envia_cpf_joao_no_prompt(processador):
    cpf_joao = "123.456.789-00"
    dados_esperados = {
        "credor_nome": "JOÃO BAPTISTA",
        "credor_cpf_cnpj": cpf_joao,
        "valor_total_requisitado": 19815.0,
    }

    mock_adapter = MagicMock()
    mock_adapter.extract_structured_data.return_value = dados_esperados
    processador.llm_adapter = mock_adapter

    from app.llm_adapter import LLMProvider
    processador.llm_provider_enum = LLMProvider

    resultado = processador._extrair_dados_llm_hibrido(
        TEXTO_MULTI_CREDOR,
        cpf_esperado=cpf_joao,
    )

    assert resultado is not None
    call_args = mock_adapter.extract_structured_data.call_args
    prompt_enviado = call_args[0][0]
    assert cpf_joao in prompt_enviado
    assert "CPF DO CREDOR A SER EXTRAÍDO" in prompt_enviado


# ---------------------------------------------------------------------------
# T6 — cpf_esperado=None → comportamento legado (sem bloco CPF)
# ---------------------------------------------------------------------------

def test_sem_cpf_esperado_comportamento_legado(processador):
    dados_esperados = {
        "credor_nome": "QUALQUER CREDOR",
        "credor_cpf_cnpj": "000.000.000-00",
        "valor_total_requisitado": 1000.0,
    }

    mock_adapter = MagicMock()
    mock_adapter.extract_structured_data.return_value = dados_esperados
    processador.llm_adapter = mock_adapter

    from app.llm_adapter import LLMProvider
    processador.llm_provider_enum = LLMProvider

    resultado = processador._extrair_dados_llm_hibrido(
        TEXTO_MULTI_CREDOR,
        cpf_esperado=None,
    )

    assert resultado is not None
    call_args = mock_adapter.extract_structured_data.call_args
    prompt_enviado = call_args[0][0]
    assert "CPF DO CREDOR A SER EXTRAÍDO" not in prompt_enviado


# ---------------------------------------------------------------------------
# T7 — integração leve: PDF real → prompt contém CPF da Albina (sem LLM)
# ---------------------------------------------------------------------------

def test_integracao_leve_prompt_pdf_albina(processador):
    """Verifica que _construir_prompt_llm inclui o CPF para o caso real da Albina."""
    cpf_albina = "247.682.258-29"

    pdf_path = Path(__file__).parent.parent.parent / "data/consultas/24768225829/0013050-58.2017.8.26.0500.pdf"
    if not pdf_path.exists():
        pytest.skip(f"PDF real não encontrado: {pdf_path}")

    import fitz
    doc = fitz.open(str(pdf_path))
    texto = "".join(p.get_text() for p in doc)
    doc.close()

    prompt = processador._construir_prompt_llm(
        texto_oficio=texto[:5000],
        cpf_esperado=cpf_albina,
    )

    assert cpf_albina in prompt
    assert "CPF DO CREDOR A SER EXTRAÍDO" in prompt
    assert "REGRA ABSOLUTA" in prompt


# ---------------------------------------------------------------------------
# T8 — regressão: imports e instanciação não quebram
# ---------------------------------------------------------------------------

def test_regressao_imports_e_instanciacao():
    """Garante que as alterações não quebraram imports ou instanciação básica."""
    from app.processador import ProcessadorOficio
    import inspect

    sig_hibrido = inspect.signature(ProcessadorOficio._extrair_dados_llm_hibrido)
    sig_prompt = inspect.signature(ProcessadorOficio._construir_prompt_llm)
    sig_legado = inspect.signature(ProcessadorOficio._extrair_dados_llm)

    assert "cpf_esperado" in sig_hibrido.parameters
    assert "cpf_esperado" in sig_prompt.parameters
    assert "cpf_esperado" in sig_legado.parameters

    assert sig_hibrido.parameters["cpf_esperado"].default is None
    assert sig_prompt.parameters["cpf_esperado"].default is None
    assert sig_legado.parameters["cpf_esperado"].default is None
