#!/usr/bin/env python3
"""
Script de teste rápido para validar detecção de termos jurídicos
Testa o detector antes de processar todos os PDFs
"""

import sys
from pathlib import Path

# Adicionar path do app
sys.path.insert(0, str(Path(__file__).parent / "1_parsing_PDF"))

from app.detector_termos_juridicos import DetectorTermosJuridicos

def test_detector():
    """Testa o detector com textos de exemplo"""
    
    print("=" * 60)
    print("🧪 TESTE DO DETECTOR DE TERMOS JURÍDICOS")
    print("=" * 60)
    
    detector = DetectorTermosJuridicos()
    
    # Teste 1: Preferência
    print("\n📋 Teste 1: Preferência")
    texto1 = "Reconheço a preferência para o credor Cleber Roberto da Silva."
    resultado1 = detector.detectar_termos(texto1)
    print(f"   Texto: {texto1[:60]}...")
    print(f"   Resultado: {resultado1}")
    assert resultado1['preferencial'] == True, "❌ Falhou: preferencial deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 2: Habilitação de Herdeiros
    print("\n📋 Teste 2: Habilitação de Herdeiros")
    texto2 = "Defiro a habilitação dos herdeiros de JOSÉ ANGELO FERRACIN"
    resultado2 = detector.detectar_termos(texto2)
    print(f"   Texto: {texto2[:60]}...")
    print(f"   Resultado: {resultado2}")
    assert resultado2['habilitacao_herdeiros'] == True, "❌ Falhou: habilitacao_herdeiros deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 3: Cessão de Crédito
    print("\n📋 Teste 3: Cessão de Crédito")
    texto3 = "conforme instrumento particular de cessão de crédito"
    resultado3 = detector.detectar_termos(texto3)
    print(f"   Texto: {texto3[:60]}...")
    print(f"   Resultado: {resultado3}")
    assert resultado3['cessao_credito'] == True, "❌ Falhou: cessao_credito deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 4: Cessão de Direitos Creditórios
    print("\n📋 Teste 4: Cessão de Direitos Creditórios")
    texto4 = "Escritura Pública de Cessão de Direitos Creditórios"
    resultado4 = detector.detectar_termos(texto4)
    print(f"   Texto: {texto4[:60]}...")
    print(f"   Resultado: {resultado4}")
    assert resultado4['cessao_credito'] == True, "❌ Falhou: cessao_credito deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 5: Múltiplos termos
    print("\n📋 Teste 5: Múltiplos Termos")
    texto5 = """
    Reconheço a preferência para o credor.
    Defiro a habilitação dos herdeiros.
    Conforme cessão de crédito anexa.
    """
    resultado5 = detector.detectar_termos(texto5)
    print(f"   Resultado: {resultado5}")
    assert resultado5['preferencial'] == True, "❌ Falhou: preferencial deveria ser True"
    assert resultado5['habilitacao_herdeiros'] == True, "❌ Falhou: habilitacao_herdeiros deveria ser True"
    assert resultado5['cessao_credito'] == True, "❌ Falhou: cessao_credito deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 6: Nenhum termo
    print("\n📋 Teste 6: Nenhum Termo Encontrado")
    texto6 = "Este é um texto sem nenhum termo jurídico relevante."
    resultado6 = detector.detectar_termos(texto6)
    print(f"   Texto: {texto6[:60]}...")
    print(f"   Resultado: {resultado6}")
    assert resultado6['preferencial'] == False, "❌ Falhou: preferencial deveria ser False"
    assert resultado6['habilitacao_herdeiros'] == False, "❌ Falhou: habilitacao_herdeiros deveria ser False"
    assert resultado6['cessao_credito'] == False, "❌ Falhou: cessao_credito deveria ser False"
    print("   ✅ PASSOU")
    
    # Teste 7: Case Insensitive
    print("\n📋 Teste 7: Case Insensitive")
    texto7 = "PREFERÊNCIA em MAIÚSCULAS"
    resultado7 = detector.detectar_termos(texto7)
    print(f"   Texto: {texto7}")
    print(f"   Resultado: {resultado7}")
    assert resultado7['preferencial'] == True, "❌ Falhou: preferencial deveria ser True"
    print("   ✅ PASSOU")
    
    # Teste 8: Detecção com contexto
    print("\n📋 Teste 8: Detecção com Contexto")
    texto8 = "Reconheço a preferência para o credor Cleber Roberto da Silva."
    resultado8 = detector.detectar_com_contexto(texto8)
    print(f"   Texto: {texto8[:60]}...")
    print(f"   Preferencial: {resultado8['preferencial']}")
    print(f"   Contexto: {resultado8['contexto_preferencial']}")
    assert resultado8['preferencial'] == True, "❌ Falhou: preferencial deveria ser True"
    assert resultado8['contexto_preferencial'] is not None, "❌ Falhou: contexto deveria existir"
    print("   ✅ PASSOU")
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\n🚀 Detector está funcionando corretamente!")
    print("   Pronto para processar PDFs reais.\n")

if __name__ == "__main__":
    try:
        test_detector()
    except AssertionError as e:
        print(f"\n❌ TESTE FALHOU: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
