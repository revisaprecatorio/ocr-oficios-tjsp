#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Compatibilidade Windows Server 2022

Verifica:
- Encoding UTF-8
- Paths com Path() (cross-platform)
- Imports do projeto
- PyMuPDF
- Pydantic
"""

import sys
import os
from pathlib import Path


def teste_encoding():
    """Testa encoding UTF-8"""
    print("=" * 60)
    print("TESTE 1: Encoding UTF-8")
    print("=" * 60)

    textos_acentuados = [
        "OFÍCIO REQUISITÓRIO",
        "AGÊNCIA BANCÁRIA",
        "CONTRIBUIÇÃO PREVIDENCIÁRIA",
        "TRÂNSITO EM JULGADO"
    ]

    for texto in textos_acentuados:
        try:
            # Tentar encode/decode
            encoded = texto.encode('utf-8')
            decoded = encoded.decode('utf-8')
            assert decoded == texto
            print(f"✓ {texto}")
        except Exception as e:
            print(f"✗ Erro com '{texto}': {e}")
            return False

    print("✓ Encoding UTF-8 OK\n")
    return True


def teste_paths():
    """Testa manipulação de paths cross-platform"""
    print("=" * 60)
    print("TESTE 2: Paths Cross-Platform")
    print("=" * 60)

    try:
        # Teste com Path()
        base = Path(__file__).parent
        print(f"✓ Diretório atual: {base}")

        # Testar paths relativos
        test_path = base / "data" / "consultas"
        print(f"✓ Path relativo: {test_path}")

        # Testar resolve()
        resolved = test_path.resolve()
        print(f"✓ Path absoluto: {resolved}")

        # Testar rglob
        if test_path.exists():
            pdfs = list(test_path.rglob("*.pdf"))
            print(f"✓ rglob funciona: {len(pdfs)} PDFs encontrados")
        else:
            print(f"⚠️  Pasta de teste não existe: {test_path}")

        print("✓ Paths cross-platform OK\n")
        return True
    except Exception as e:
        print(f"✗ Erro: {e}\n")
        return False


def teste_imports():
    """Testa imports do projeto"""
    print("=" * 60)
    print("TESTE 3: Imports do Projeto")
    print("=" * 60)

    modulos = [
        ("pymupdf", "PyMuPDF"),
        ("pydantic", "Pydantic"),
        ("psycopg2", "PostgreSQL Driver"),
        ("openai", "OpenAI"),
        ("dotenv", "Python-dotenv")
    ]

    sucesso = True
    for modulo, nome in modulos:
        try:
            __import__(modulo)
            print(f"✓ {nome}")
        except ImportError as e:
            print(f"✗ {nome} não instalado: {e}")
            sucesso = False

    # Testar imports do app
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from app.detector import DetectorOficio
        from app.detector_anexo import DetectorAnexoII
        from app.schemas import OficioRequisitorio
        print(f"✓ Módulos do app")
    except Exception as e:
        print(f"✗ Erro ao importar módulos do app: {e}")
        sucesso = False

    if sucesso:
        print("✓ Todos os imports OK\n")
    else:
        print("✗ Alguns imports falharam\n")

    return sucesso


def teste_pymupdf():
    """Testa leitura de PDF com PyMuPDF"""
    print("=" * 60)
    print("TESTE 4: PyMuPDF (Leitura de PDF)")
    print("=" * 60)

    try:
        import pymupdf

        # Buscar primeiro PDF de teste
        base = Path(__file__).parent / "data" / "consultas"
        if not base.exists():
            print("⚠️  Pasta de teste não existe, pulando teste de PDF")
            return True

        pdfs = list(base.rglob("*.pdf"))
        if not pdfs:
            print("⚠️  Nenhum PDF encontrado, pulando teste")
            return True

        # Testar primeiro PDF
        pdf_path = pdfs[0]
        print(f"Testando: {pdf_path.name}")

        doc = pymupdf.open(str(pdf_path))
        num_pages = len(doc)
        print(f"✓ PDF aberto: {num_pages} páginas")

        # Testar extração de texto
        page = doc[0]
        text = page.get_text()
        print(f"✓ Texto extraído: {len(text)} caracteres")

        doc.close()
        print("✓ PyMuPDF OK\n")
        return True

    except Exception as e:
        print(f"✗ Erro: {e}\n")
        return False


def teste_pydantic():
    """Testa validação Pydantic"""
    print("=" * 60)
    print("TESTE 5: Pydantic (Validação)")
    print("=" * 60)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from app.schemas import OficioRequisitorio

        # Testar validação básica
        dados_validos = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "JOÃO DA SILVA",
            "banco": "341",
            "agencia": "1234",
            "conta": "12345-6"
        }

        oficio = OficioRequisitorio(**dados_validos)
        print(f"✓ Validação básica OK")
        print(f"  - Processo: {oficio.processo_origem}")
        print(f"  - Requerente: {oficio.requerente_caps}")
        print(f"  - Banco: {oficio.banco}")
        print(f"  - Conta: {oficio.conta}")

        # Testar validação de erro (requerente não maiúsculo)
        try:
            dados_invalidos = {
                "processo_origem": "0035938-67.2018.8.26.0053",
                "requerente_caps": "João da Silva"  # minúsculas
            }
            oficio_invalido = OficioRequisitorio(**dados_invalidos)
            print("✗ Validação deveria ter falhado (nome não maiúsculo)")
            return False
        except Exception:
            print("✓ Validação de erro OK (rejeita nome não maiúsculo)")

        print("✓ Pydantic OK\n")
        return True

    except Exception as e:
        print(f"✗ Erro: {e}\n")
        return False


def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "TESTE DE COMPATIBILIDADE WINDOWS SERVER" + " " * 9 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    resultados = []

    # Executar testes
    resultados.append(("Encoding UTF-8", teste_encoding()))
    resultados.append(("Paths Cross-Platform", teste_paths()))
    resultados.append(("Imports", teste_imports()))
    resultados.append(("PyMuPDF", teste_pymupdf()))
    resultados.append(("Pydantic", teste_pydantic()))

    # Resumo
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)

    total = len(resultados)
    sucesso = sum(1 for _, ok in resultados if ok)

    for nome, ok in resultados:
        status = "✓ PASSOU" if ok else "✗ FALHOU"
        print(f"{nome:30s} {status}")

    print()
    print(f"Total: {sucesso}/{total} testes passaram")

    if sucesso == total:
        print("\n✓ COMPATIBILIDADE OK PARA WINDOWS SERVER 2022\n")
        return 0
    else:
        print(f"\n✗ {total - sucesso} TESTE(S) FALHARAM\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
