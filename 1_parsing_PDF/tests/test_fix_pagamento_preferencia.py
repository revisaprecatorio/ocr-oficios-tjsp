"""
Testes de regressão — Fix: Pagamento de Preferência (caso Benedita CPF 23990295691)

Cobre dois bugs:
  Bug 1 — prompt LLM deve conter aviso para ignorar "Pagamento de Preferência"
  Bug 2 — janela de isolamento deve ser >= 100k chars (alcança SALDO FINAL em PDFs grandes)

Estratégia para evitar SIGBUS (Python 3.14 + google-generativeai):
  - Testes de prompt: lêem processador.py como texto puro (sem import)
  - Testes de saldo: importam apenas DetectorSaldoFinal (sem google SDK)
"""

import sys
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "1_parsing_PDF"))

PROCESSADOR_PATH = ROOT / "1_parsing_PDF/app/processador.py"
DETECTOR_SALDO_PATH = ROOT / "1_parsing_PDF/app/detector_saldo_final.py"

from app.detector_saldo_final import DetectorSaldoFinal


# =========================================================================
# FIXTURES — textos sintéticos que replicam a estrutura dos PDFs da Benedita
# =========================================================================

def _texto_benedita_p1_janela_grande(distancia_chars: int = 12000) -> str:
    """
    Replica a estrutura do Processo 1 (CPF 23990295691):
      - Início: ANEXO II com CPF e Valor requisitado
      - Meio: padding de 'distancia_chars' (simula páginas entre ANEXO II e PROCESSAMENTO)
      - Fim: seção PROCESSAMENTO com SALDO FINAL APÓS O PAGAMENTO = 12.120,45
    """
    cabecalho = (
        "ANEXO II\n"
        "Credor nº 1\n"
        "Nome: BENEDITA SEBASTIANA PINTO RODRIGUES\n"
        "CPF/CNPJ: 239.902.956-91\n"
        "Data do nascimento: 10/02/1940\n"
        "Valor total da condenação: R$ 55.973,39\n"
        "Valor compensado: R$ 0,00\n"
        "Valor requisitado: R$ 55.973,39\n"
        "Banco: 001 - Banco do Brasil\n"
        "Agência: 0001-9\n"
        "Conta: 00012345-6\n"
    )
    padding = "X" * distancia_chars
    processamento = (
        "\nCERTIDÃO DE PROCESSAMENTO\n"
        "Número de ordem: 00001/2021\n\n"
        "Valores para Pagamento em 30/06/2021\n"
        "VALOR PRINCIPAL\n"
        "R$\n"
        "       24.067,73\n"
        "JUROS MORATÓRIOS\n"
        "R$\n"
        "       52.081,97\n"
        "TOTAL\n"
        "R$\n"
        "       76.149,70\n\n"
        "Pagamento de Preferência (Até 5 OPVs)\n"
        "5 * R$ 12.805,85 = R$ 64.029,25\n"
        "VALOR PRINCIPAL\n"
        "R$\n"
        "       20.236,96\n"
        "JUROS MORATÓRIOS\n"
        "R$\n"
        "       43.792,29\n"
        "TOTAL\n"
        "R$\n"
        "       64.029,25\n\n"
        "SALDO FINAL APÓS O PAGAMENTO\n"
        "VALOR PRINCIPAL em 30/06/2021\n"
        "R$\n"
        "        3.830,77\n"
        "JUROS MORATÓRIOS\n"
        "R$\n"
        "        8.289,68\n"
        "TOTAL\n"
        "R$\n"
        "       12.120,45\n"
    )
    return cabecalho + padding + processamento


def _texto_benedita_p2_janela_grande(distancia_chars: int = 12000) -> str:
    """Replica a estrutura do Processo 2: SALDO FINAL = 166.375,94."""
    cabecalho = (
        "ANEXO II\n"
        "Credor nº 1\n"
        "Nome: BENEDITA SEBASTIANA PINTO RODRIGUES\n"
        "CPF/CNPJ: 239.902.956-91\n"
        "Data do nascimento: 10/02/1940\n"
        "Valor total da condenação: R$ 182.333,02\n"
        "Valor compensado: R$ 0,00\n"
        "Valor requisitado: R$ 182.333,02\n"
        "Banco: 001 - Banco do Brasil\n"
        "Agência: 0001-9\n"
        "Conta: 00012345-6\n"
    )
    padding = "Y" * distancia_chars
    processamento = (
        "\nCERTIDÃO DE PROCESSAMENTO\n"
        "Número de ordem: 00001/2021\n\n"
        "Pagamento de Preferência (Até 5 OPVs)\n"
        "5 * R$ 12.805,85 = R$ 64.029,25\n"
        "VALOR PRINCIPAL\n"
        "R$\n"
        "       15.957,08\n"
        "JUROS MORATÓRIOS\n"
        "R$\n"
        "       48.072,16\n"
        "TOTAL\n"
        "R$\n"
        "       64.029,25\n\n"
        "SALDO FINAL APÓS O PAGAMENTO\n"
        "VALOR PRINCIPAL em 30/06/2021\n"
        "R$\n"
        "      118.375,94\n"
        "JUROS MORATÓRIOS\n"
        "R$\n"
        "       48.000,00\n"
        "TOTAL\n"
        "R$\n"
        "      166.375,94\n"
    )
    return cabecalho + padding + processamento


# =========================================================================
# BUG 1 — Prompt LLM deve conter aviso sobre "Pagamento de Preferência"
# Estratégia: ler processador.py como texto puro (sem import → sem SIGBUS)
# =========================================================================

class TestPromptAvisoPagamentoPreferencia:

    def test_processador_py_existe(self):
        assert PROCESSADOR_PATH.exists(), f"processador.py não encontrado: {PROCESSADOR_PATH}"

    def test_prompt_contem_aviso_pagamento_preferencia(self):
        """Após Fix 1: processador.py deve conter instrução explícita."""
        conteudo = PROCESSADOR_PATH.read_text(encoding="utf-8")
        assert "Pagamento de Prefer" in conteudo, (
            "Fix 1 não aplicado: aviso sobre 'Pagamento de Preferência' ausente no processador.py"
        )

    def test_prompt_instrui_ignorar_total_pagamento_preferencia(self):
        """Após Fix 1: instrução deve orientar a NÃO usar o TOTAL do Pagamento de Preferência."""
        conteudo = PROCESSADOR_PATH.read_text(encoding="utf-8")
        assert "valor_principal_bruto" in conteudo, "Campo valor_principal_bruto deve existir no prompt"
        instrucao_presente = (
            "NÃO" in conteudo and "Pagamento de Prefer" in conteudo
        ) or (
            "NAO" in conteudo and "Pagamento de Prefer" in conteudo
        ) or (
            "nao usar" in conteudo.lower() and "prefer" in conteudo.lower()
        ) or (
            "ignore" in conteudo.lower() and "prefer" in conteudo.lower()
        )
        assert instrucao_presente, (
            "Fix 1 não aplicado: instrução para ignorar Pagamento de Preferência não encontrada"
        )

    def test_detector_saldo_janela_e_100k(self):
        """Após Fix 2: detector_saldo_final.py deve usar janela de 100000, não 10000."""
        import re
        conteudo = DETECTOR_SALDO_PATH.read_text(encoding="utf-8")
        assert "pos + 100000" in conteudo, (
            "Fix 2 não aplicado: janela de isolamento deve ser 100000 chars em detector_saldo_final.py"
        )
        assert not re.search(r'pos \+ 10000(?!0)', conteudo), (
            "Fix 2 incompleto: janela antiga 'pos + 10000' (sem sexto zero) ainda presente"
        )


# =========================================================================
# BUG 2 — Janela de isolamento deve alcançar SALDO FINAL em PDFs grandes
# =========================================================================

class TestJanelaIsolamentoSaldoFinal:

    @pytest.fixture
    def detector(self):
        return DetectorSaldoFinal()

    # --- Regressão: casos existentes não devem ser afetados ---

    def test_saldo_dentro_janela_5k_continua_detectando(self, detector):
        """Garante que casos com SALDO FINAL próximo (< 5k chars) continuam funcionando."""
        texto = _texto_benedita_p1_janela_grande(distancia_chars=4000)
        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        assert resultado.saldo_final is not None, (
            "Regressão: saldo dentro de 5k chars não detectado"
        )
        assert resultado.saldo_final == Decimal("12120.45"), (
            f"Valor errado: esperado 12120.45, obtido {resultado.saldo_final}"
        )
        assert resultado.origem_saldo_final == "saldo_apos_pagamento"

    def test_saldo_sem_cpf_detecta_no_texto_completo(self, detector):
        """Sem CPF, detecta via texto completo (independe de janela)."""
        texto = _texto_benedita_p1_janela_grande(distancia_chars=500)
        resultado = detector.extrair_saldo_e_data_com_origem(texto)
        assert resultado.saldo_final is not None
        assert resultado.saldo_final == Decimal("12120.45")

    # --- Novos casos: SALDO FINAL além de 10k chars do CPF ---

    def test_saldo_benedita_p1_alem_10k_chars(self, detector):
        """Fix 2: SALDO FINAL APÓS O PAGAMENTO a 12k chars do CPF → deve detectar R$ 12.120,45."""
        texto = _texto_benedita_p1_janela_grande(distancia_chars=12000)
        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        assert resultado.saldo_final is not None, (
            "Fix 2 não aplicado: SALDO FINAL a 12k chars do CPF não foi detectado"
        )
        assert resultado.saldo_final == Decimal("12120.45"), (
            f"Valor errado: esperado 12120.45, obtido {resultado.saldo_final}"
        )
        assert resultado.origem_saldo_final == "saldo_apos_pagamento"

    def test_saldo_benedita_p2_alem_10k_chars(self, detector):
        """Fix 2: Processo 2 — SALDO FINAL a 12k chars → deve detectar R$ 166.375,94."""
        texto = _texto_benedita_p2_janela_grande(distancia_chars=12000)
        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        assert resultado.saldo_final is not None, (
            "Fix 2 não aplicado: SALDO FINAL (P2) a 12k chars do CPF não foi detectado"
        )
        assert resultado.saldo_final == Decimal("166375.94"), (
            f"Valor errado: esperado 166375.94, obtido {resultado.saldo_final}"
        )
        assert resultado.origem_saldo_final == "saldo_apos_pagamento"

    def test_nao_captura_total_pagamento_preferencia_como_saldo(self, detector):
        """
        O TOTAL do 'Pagamento de Preferência' (R$ 64.029,25) NÃO deve ser o saldo_final.
        O saldo correto é o TOTAL de 'SALDO FINAL APÓS O PAGAMENTO' = R$ 12.120,45.
        """
        texto = _texto_benedita_p1_janela_grande(distancia_chars=500)
        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        assert resultado.saldo_final != Decimal("64029.25"), (
            "Bug: detector capturou R$ 64.029,25 (Pagamento de Preferência) como saldo_final"
        )
        assert resultado.saldo_final == Decimal("12120.45"), (
            f"Esperado 12120.45, obtido {resultado.saldo_final}"
        )

    def test_saldo_em_bloco_calculo_referente_nao_consecutivo(self, detector):
        """
        Fix V3.0.1: CPF no bloco 0, SALDO FINAL no bloco 3 (blocos 1 e 2 sem CPF).
        O detector deve expandir o contexto para incluir o bloco com SALDO FINAL.
        """
        bloco0 = (
            "Calculo referente a 239.902.956-91 CPF/CNPJ Beneficiário\n"
            "Credor: BENEDITA SEBASTIANA PINTO RODRIGUES\n"
            "CPF: 239.902.956-91\n"
            "Valor: R$ 55.973,39\n"
        )
        bloco1 = "Calculo referente a Índices de Atualização\nIPCA jan/2021: 0,25%\n"
        bloco2 = "Calculo referente a Juros Moratórios\nTaxa: 0,5% a.m.\n"
        bloco3 = (
            "Calculo referente a Saldo\n"
            "SALDO FINAL APÓS O PAGAMENTO\n"
            "VALOR PRINCIPAL em 30/06/2021\n"
            "          3.830,77\nR$\n"
            "JUROS MORATÓRIOS\n"
            "          8.289,68\nR$\n"
            "TOTAL\n"
            "         12.120,45\nR$\n"
            "CPF: 239.902.956-91\n"
        )
        texto = bloco0 + bloco1 + bloco2 + bloco3

        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        assert resultado.saldo_final is not None, (
            "Fix V3.0.1 não aplicado: SALDO FINAL em bloco não-consecutivo ao bloco do CPF não detectado"
        )
        assert resultado.saldo_final == Decimal("12120.45"), (
            f"Valor errado: esperado 12120.45, obtido {resultado.saldo_final}"
        )

    def test_data_saldo_benedict_p1_detectada(self, detector):
        """Data do bloco SALDO FINAL (30/06/2021) deve ser retornada."""
        texto = _texto_benedita_p1_janela_grande(distancia_chars=500)
        resultado = detector.extrair_saldo_e_data_com_origem(texto, cpf="23990295691")
        if resultado.saldo_final is not None:
            assert resultado.data_saldo_final == date(2021, 6, 30), (
                f"Data incorreta: esperado 2021-06-30, obtido {resultado.data_saldo_final}"
            )
