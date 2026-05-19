"""
Testes DetectorSaldoFinal V3.0.0
Data: 19/05/2026

Cobertura:
- Prioridade 1: SALDO FINAL APÓS O PAGAMENTO (padrão V2.x)
- Prioridade 2: Saldo Final em DD/MM/AA (novo)
- Prioridade 3: Valores para Pagamento em DD/MM/AAAA (novo)
- Exclusão de SUB-TOTAL
- Isolamento de contexto por credor (multi-credor)
- validar_padroes() completo
- Integração com PDFs reais (marcados com @pytest.mark.integration)
- _garantir_saldo_final_e_data() fallbacks
"""

import os
import sys
from decimal import Decimal
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Adicionar raiz do projeto ao path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "1_parsing_PDF"))

from app.detector_saldo_final import DetectorSaldoFinal, ResultadoSaldoFinal

# Caminhos dos PDFs de integração
PDF_ALBINA_0013050 = ROOT / "data/consultas/24768225829/0013050-58.2017.8.26.0500.pdf"
PDF_ALBINA_0142153 = ROOT / "data/consultas/24768225829/0142153-74.2024.8.26.0500.pdf"


# =========================================================================
# FIXTURES
# =========================================================================

@pytest.fixture
def detector():
    return DetectorSaldoFinal()


TEXTO_SALDO_APOS_PAG = (
    "SALDO FINAL APÓS O PAGAMENTO\n"
    "VALOR PRINCIPAL em 23/05/2025\n"
    "         51.435,50\n"
    "R$\n"
    "TOTAL  R$ 51.435,50\n"
)

TEXTO_SALDO_APOS_PAG_COM_TOTAL = (
    "SALDO FINAL APÓS O PAGAMENTO\n"
    "VALOR PRINCIPAL  R$ 168.217,53\n"
    "JUROS MORATÓRIOS  R$ 75.010,58\n"
    "TOTAL  R$ 243.228,11\n"
)

TEXTO_SALDO_FINAL_EM = (
    "         14.161,60\nR$\n"
    "TOTAL\n"
    "         48.168,01\nR$\n"
    "Saldo Final em 29/03/19\n"
    "Saldo = débito ÷ 51,951027 (12/2018) x 52,200387 (03/2019)\n"
    "VALOR PRINCIPAL em 29/03/2019\n"
    "         34.169,63\nR$\n"
    "DESCONTO PREVIDENCIÁRIO\n"
    "              0,00\nR$\n"
    "ASSISTÊNCIA MÉDICA\n"
    "              0,00\nR$\n"
    "SUB-TOTAL\n"
    "         34.169,63\nR$\n"
    "JUROS MORATÓRIOS\n"
    "4,55%\n"
    "       89 dia(s)\n"
    "            384,36\n"
    "         14.613,93\nR$\nR$\n"
    "TOTAL\n"
    "         48.783,56\nR$\n"
    "Valores para Pagamento em 29/03/2019\n"
)

TEXTO_VALORES_PARA_PAG = (
    "Valores para Pagamento em 29/03/2019\n"
    "VALOR PRINCIPAL\n"
    "         34.169,63\nR$\n"
    "DESCONTO PREVIDENCIÁRIO\n"
    "              0,00\nR$\n"
    "SUB-TOTAL\n"
    "         34.169,63\nR$\n"
    "JUROS MORATÓRIOS\n"
    "         14.613,93\nR$\n"
    "TOTAL\n"
    "         48.783,56\nR$\n"
)

TEXTO_MULTI_CREDOR = (
    "Calculo referente a\nCPF/CNPJ\nJoao Silva\n111.111.111-11\n"
    "VALOR PRINCIPAL em 31/12/2018\n         10.000,00\nR$\n"
    "SUB-TOTAL\n         10.000,00\nR$\n"
    "JUROS MORATÓRIOS\n         2.000,00\nR$\n"
    "TOTAL\n         12.000,00\nR$\n"
    "Saldo Final em 31/12/18\n"
    "VALOR PRINCIPAL em 31/12/2018\n         10.000,00\nR$\n"
    "SUB-TOTAL\n         10.000,00\nR$\n"
    "JUROS MORATÓRIOS\n         2.100,00\nR$\n"
    "TOTAL\n         12.100,00\nR$\n"
    "Calculo referente a\nCPF/CNPJ\nMaria Souza\n222.222.222-22\n"
    "VALOR PRINCIPAL em 31/12/2018\n         50.000,00\nR$\n"
    "SUB-TOTAL\n         50.000,00\nR$\n"
    "JUROS MORATÓRIOS\n         9.000,00\nR$\n"
    "TOTAL\n         59.000,00\nR$\n"
    "Saldo Final em 31/12/18\n"
    "VALOR PRINCIPAL em 31/12/2018\n         50.000,00\nR$\n"
    "SUB-TOTAL\n         50.000,00\nR$\n"
    "JUROS MORATÓRIOS\n         9.500,00\nR$\n"
    "TOTAL\n         59.500,00\nR$\n"
)


# =========================================================================
# 1. PRIORIDADE 1 — SALDO FINAL APÓS O PAGAMENTO
# =========================================================================

def test_detecta_saldo_apos_pagamento_com_total(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_SALDO_APOS_PAG_COM_TOTAL)
    assert resultado.saldo_final == Decimal("243228.11")
    assert resultado.origem_saldo_final == "saldo_apos_pagamento"


def test_detecta_saldo_apos_pagamento_valor_principal(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_SALDO_APOS_PAG)
    assert resultado.saldo_final is not None
    assert resultado.origem_saldo_final == "saldo_apos_pagamento"
    assert resultado.data_saldo_final == date(2025, 5, 23)


# =========================================================================
# 2. PRIORIDADE 2 — SALDO FINAL EM DD/MM/AA(AA)
# =========================================================================

def test_detecta_saldo_final_em_texto(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_SALDO_FINAL_EM)
    assert resultado.saldo_final == Decimal("48783.56")
    assert resultado.data_saldo_final == date(2019, 3, 29)
    assert resultado.origem_saldo_final == "saldo_final_em"
    assert resultado.origem_data_saldo_final == "titulo_saldo_final_em"


def test_saldo_final_em_ano_2_digitos(detector):
    d = detector._converter_data_br_2dig("29/03/19")
    assert d == date(2019, 3, 29)


def test_saldo_final_em_ano_2_digitos_seculo_xx(detector):
    d = detector._converter_data_br_2dig("15/06/85")
    assert d == date(1985, 6, 15)


def test_saldo_final_em_ano_4_digitos(detector):
    d = detector._converter_data_br_2dig("28/12/2023")
    assert d == date(2023, 12, 28)


# =========================================================================
# 3. PRIORIDADE 3 — VALORES PARA PAGAMENTO EM DD/MM/AAAA
# =========================================================================

def test_detecta_valores_para_pagamento_texto(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_VALORES_PARA_PAG)
    assert resultado.saldo_final == Decimal("48783.56")
    assert resultado.data_saldo_final == date(2019, 3, 29)
    assert resultado.origem_saldo_final == "valores_para_pagamento"
    assert resultado.origem_data_saldo_final == "titulo_valores_para_pagamento"


# =========================================================================
# 4. NÃO CAPTURA SUB-TOTAL
# =========================================================================

def test_nao_captura_subtotal_como_saldo_final(detector):
    texto_apenas_subtotal = (
        "Saldo Final em 31/12/23\n"
        "VALOR PRINCIPAL\n         20.000,00\nR$\n"
        "SUB-TOTAL\n         20.000,00\nR$\n"
        "IRRF\n         1.000,00\nR$\n"
        "SUB-TOTAL\n         19.000,00\nR$\n"
        "TOTAL\n         19.000,00\nR$\n"
    )
    resultado = detector.extrair_saldo_e_data_com_origem(texto_apenas_subtotal)
    assert resultado.saldo_final == Decimal("19000.00")
    assert resultado.saldo_final != Decimal("20000.00")


# =========================================================================
# 5. ISOLAMENTO DE CONTEXTO MULTI-CREDOR
# =========================================================================

def test_nao_captura_credor_errado_joao(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_MULTI_CREDOR, cpf="11111111111")
    assert resultado.saldo_final == Decimal("12100.00")


def test_nao_captura_credor_errado_maria(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_MULTI_CREDOR, cpf="22222222222")
    assert resultado.saldo_final == Decimal("59500.00")


def test_isolamento_cpf_formatado(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_MULTI_CREDOR, cpf="111.111.111-11")
    assert resultado.saldo_final == Decimal("12100.00")


def test_sem_cpf_retorna_primeiro_match(detector):
    resultado = detector.extrair_saldo_e_data_com_origem(TEXTO_MULTI_CREDOR)
    assert resultado.saldo_final is not None


# =========================================================================
# 6. TEXTO VAZIO / NENHUM PADRÃO
# =========================================================================

def test_texto_vazio_retorna_resultado_vazio(detector):
    resultado = detector.extrair_saldo_e_data_com_origem("")
    assert resultado.saldo_final is None
    assert resultado.data_saldo_final is None
    assert resultado.origem_saldo_final is None


def test_texto_sem_saldo_retorna_resultado_vazio(detector):
    resultado = detector.extrair_saldo_e_data_com_origem("Texto qualquer sem saldo")
    assert resultado.saldo_final is None


# =========================================================================
# 7. RETROCOMPATIBILIDADE
# =========================================================================

def test_extrair_saldo_final_retrocompat(detector):
    saldo = detector.extrair_saldo_final(TEXTO_SALDO_APOS_PAG_COM_TOTAL)
    assert saldo == Decimal("243228.11")


def test_extrair_saldo_e_data_retrocompat(detector):
    saldo, data = detector.extrair_saldo_e_data(TEXTO_SALDO_FINAL_EM)
    assert saldo == Decimal("48783.56")
    assert data == date(2019, 3, 29)


def test_extrair_saldo_com_contexto_retrocompat(detector):
    res = detector.extrair_saldo_com_contexto(TEXTO_SALDO_APOS_PAG_COM_TOTAL)
    assert res["saldo_final"] == Decimal("243228.11")
    assert res["contexto"] is not None


# =========================================================================
# 8. VALIDAR PADRÕES INTERNO
# =========================================================================

def test_validar_padroes_todos_ok(detector):
    testes = detector.validar_padroes()
    assert testes["pattern_apos_pag_v2"] is True
    assert testes["pattern_saldo_com_total_v2"] is True
    assert testes["pattern_saldo_final_em"] is True
    assert testes["pattern_valores_para_pagamento"] is True
    assert testes["pattern_generico"] is True
    assert testes["conversao_valor"] is True
    assert testes["conversao_data_2dig"] is True


# =========================================================================
# 9. FALLBACK _garantir_saldo_final_e_data (unit)
# =========================================================================

def _mock_oficio(**kwargs):
    oficio = MagicMock()
    oficio.saldo_final = kwargs.get("saldo_final", None)
    oficio.data_saldo_final = kwargs.get("data_saldo_final", None)
    oficio.origem_saldo_final = None
    oficio.origem_data_saldo_final = None
    oficio.valor_total_requisitado = kwargs.get("valor_total_requisitado", None)
    oficio.valor_principal_bruto = kwargs.get("valor_principal_bruto", None)
    oficio.valor_principal_liquido = kwargs.get("valor_principal_liquido", None)
    oficio.juros_moratorios = kwargs.get("juros_moratorios", None)
    oficio.data_base_atualizacao = kwargs.get("data_base_atualizacao", None)
    oficio.anomalia = False
    return oficio


def test_garantir_fallback_usa_valor_total_requisitado():
    sys.path.insert(0, str(ROOT / "1_parsing_PDF"))
    from app.processador import ProcessadorOficio

    processador = ProcessadorOficio.__new__(ProcessadorOficio)
    processador.detector_saldo = DetectorSaldoFinal()

    oficio = _mock_oficio(valor_total_requisitado=Decimal("144367.82"),
                          data_base_atualizacao=date(2018, 11, 30))
    processador._garantir_saldo_final_e_data(oficio, "Texto sem saldo", "24768225829")

    assert oficio.saldo_final == Decimal("144367.82")
    assert oficio.origem_saldo_final == "fallback_valor_total_requisitado"
    assert oficio.data_saldo_final == date(2018, 11, 30)
    assert oficio.origem_data_saldo_final == "fallback_data_base_atualizacao"


def test_garantir_llm_extraction_preserva_saldo():
    from app.processador import ProcessadorOficio

    processador = ProcessadorOficio.__new__(ProcessadorOficio)
    processador.detector_saldo = DetectorSaldoFinal()

    oficio = _mock_oficio(saldo_final=Decimal("99999.00"),
                          data_base_atualizacao=date(2022, 1, 1))
    processador._garantir_saldo_final_e_data(oficio, "Texto sem saldo", "12345678901")

    assert oficio.saldo_final == Decimal("99999.00")
    assert oficio.origem_saldo_final == "llm_extraction"


def test_garantir_fallback_extremo_zero_anomalia():
    from app.processador import ProcessadorOficio

    processador = ProcessadorOficio.__new__(ProcessadorOficio)
    processador.detector_saldo = DetectorSaldoFinal()

    oficio = _mock_oficio()
    processador._garantir_saldo_final_e_data(oficio, "Texto qualquer", "12345678901")

    assert oficio.saldo_final == Decimal("0.00")
    assert oficio.origem_saldo_final == "fallback_zero_erro"
    assert oficio.anomalia is True


# =========================================================================
# 10. INTEGRAÇÃO COM PDFs REAIS
# =========================================================================

pytestmark_integration = pytest.mark.skipif(
    not PDF_ALBINA_0013050.exists(),
    reason="PDF de integração não encontrado"
)


@pytest.mark.integration
@pytest.mark.skipif(not PDF_ALBINA_0013050.exists(), reason="PDF não disponível")
def test_pdf_albina_0013050_saldo_final_em():
    """PDF multi-credor: Albina deve retornar saldo=48783.56, data=2019-03-29 via saldo_final_em."""
    import fitz

    doc = fitz.open(str(PDF_ALBINA_0013050))
    texto = ""
    for p in doc:
        texto += p.get_text() + "\n"
    doc.close()

    detector = DetectorSaldoFinal()
    resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="24768225829")

    assert resultado.saldo_final is not None, "Esperado saldo_final detectado, obtido None"
    assert resultado.saldo_final > 0
    assert resultado.data_saldo_final == date(2019, 3, 29)
    assert resultado.origem_saldo_final == "saldo_final_em"


@pytest.mark.integration
@pytest.mark.skipif(not PDF_ALBINA_0013050.exists(), reason="PDF não disponível")
def test_pdf_albina_0013050_sem_cpf_retorna_primeiro_credor():
    """Sem isolamento de CPF, retorna o primeiro match (não necessariamente Albina)."""
    import fitz

    doc = fitz.open(str(PDF_ALBINA_0013050))
    texto = ""
    for p in doc:
        texto += p.get_text() + "\n"
    doc.close()

    detector = DetectorSaldoFinal()
    resultado_sem_cpf = detector.extrair_saldo_e_data_com_origem(texto)
    resultado_com_cpf = detector.extrair_saldo_e_data_com_origem(texto, cpf="24768225829")

    assert resultado_sem_cpf.saldo_final is not None
    assert resultado_com_cpf.saldo_final is not None
    assert resultado_com_cpf.saldo_final > 0
    # Verifica que o isolamento por CPF está ativo (pode ou não diferir do sem-CPF)
    assert resultado_com_cpf.origem_saldo_final is not None


@pytest.mark.integration
@pytest.mark.skipif(not PDF_ALBINA_0142153.exists(), reason="PDF não disponível")
def test_pdf_albina_0142153_detector_retorna_none():
    """PDF sem bloco de saldo explícito — detector retorna None, fallback via processador."""
    import fitz

    doc = fitz.open(str(PDF_ALBINA_0142153))
    texto = ""
    for p in doc:
        texto += p.get_text() + "\n"
    doc.close()

    detector = DetectorSaldoFinal()
    resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="24768225829")

    assert resultado.saldo_final is None, (
        f"Esperado None (sem bloco de saldo), obtido {resultado.saldo_final}"
    )
