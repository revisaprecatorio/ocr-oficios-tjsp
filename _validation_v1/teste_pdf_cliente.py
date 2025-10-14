#!/usr/bin/env python
"""
Teste direto do PDF de exemplo do cliente
"""
import sys
import os
from pathlib import Path

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.detector import DetectorOficio
from app.detector_anexo import DetectorAnexoII
from app.processador import ProcessadorOficio
from dotenv import load_dotenv
import json

# Carregar .env
load_dotenv()

# Configurações
pdf_path = "_definition-e-specs/0158003-37.2025.8.26.0500.pdf"
openai_key = os.getenv("OPENAI_API_KEY")

print("="*60)
print("🧪 TESTE DO PDF DE EXEMPLO DO CLIENTE")
print("="*60)
print(f"📄 PDF: {pdf_path}")
print()

# 1. Detectar ofício
print("1️⃣ Detectando ofício...")
detector = DetectorOficio()
paginas_oficio, texto_oficio = detector.detectar_oficio(pdf_path)
print(f"   ✅ Ofício detectado em {len(paginas_oficio)} páginas: {paginas_oficio}")
print(f"   📝 Texto extraído: {len(texto_oficio)} caracteres")
print()

# 2. Detectar ANEXO II
print("2️⃣ Detectando ANEXO II...")
detector_anexo = DetectorAnexoII()
paginas_anexo, texto_anexo = detector_anexo.detectar_anexo_ii(pdf_path)
print(f"   ✅ ANEXO II detectado em {len(paginas_anexo)} páginas: {paginas_anexo}")
print(f"   📝 Texto ANEXO II: {len(texto_anexo)} caracteres")
print()

# Mostrar trecho do ANEXO II
if texto_anexo:
    print("📋 Trecho do ANEXO II:")
    print("-"*60)
    linhas = texto_anexo.split('\n')
    for i, linha in enumerate(linhas[:30], 1):
        if linha.strip():
            print(f"   {i:2d}. {linha.strip()}")
    print("-"*60)
    print()

# 3. Processar com LLM
print("3️⃣ Processando com LLM (GPT-4o-mini)...")
print("   ⏳ Aguarde...")

# Criar processador
db_config = {
    "host": "localhost",
    "port": 5432,
    "database": "oficios_tjsp",
    "user": "postgres",
    "password": "dummy"
}

processador = ProcessadorOficio(openai_key, db_config)

# Extrair dados
from app.processador import ProcessadorOficio
import pymupdf

# Simular extração
doc = pymupdf.open(pdf_path)
texto_completo = ""
for page in doc:
    texto_completo += page.get_text()
doc.close()

# Chamar LLM
dados = processador._extrair_dados_llm(texto_completo, tem_anexo_ii=len(paginas_anexo) > 0)

if dados:
    print("   ✅ Dados extraídos com sucesso!")
    print()
    
    # 4. Mostrar dados bancários
    print("="*60)
    print("💰 DADOS BANCÁRIOS EXTRAÍDOS")
    print("="*60)
    
    campos_bancarios = {
        "banco": dados.get("banco"),
        "agencia": dados.get("agencia"),
        "conta": dados.get("conta"),
        "conta_tipo": dados.get("conta_tipo")
    }
    
    for campo, valor in campos_bancarios.items():
        status = "✅" if valor else "❌"
        print(f"   {status} {campo}: {valor}")
    
    print()
    
    # 5. Mostrar outros dados importantes
    print("="*60)
    print("📊 OUTROS DADOS EXTRAÍDOS")
    print("="*60)
    
    campos_importantes = [
        "processo_origem",
        "requerente_caps",
        "valor_total_requisitado",
        "valor_principal_liquido",
        "juros_moratorios"
    ]
    
    for campo in campos_importantes:
        valor = dados.get(campo)
        status = "✅" if valor else "❌"
        print(f"   {status} {campo}: {valor}")
    
    print()
    
    # 6. Salvar JSON completo
    output_file = "_validation_v1/outputs/teste_exemplo_cliente_completo.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON completo salvo em: {output_file}")
    print()
    
    # 7. Conclusão
    print("="*60)
    print("📋 CONCLUSÃO")
    print("="*60)
    
    tem_dados_bancarios = all(campos_bancarios.values())
    
    if tem_dados_bancarios:
        print("   ✅ SUCESSO: Todos os dados bancários foram extraídos!")
    else:
        print("   ❌ PROBLEMA: Dados bancários NÃO foram extraídos!")
        print()
        print("   Campos faltando:")
        for campo, valor in campos_bancarios.items():
            if not valor:
                print(f"      - {campo}")
    
    print()

else:
    print("   ❌ Erro ao extrair dados com LLM")
    print()

print("="*60)
print("✅ TESTE CONCLUÍDO")
print("="*60)
