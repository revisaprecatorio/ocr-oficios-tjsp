"""
Teste A/B EXPANDIDO: Gemini 2.5 Pro vs GPT-4o-mini
Agora sem limites de quota! 🚀
"""

import sys
import os
from pathlib import Path
import json
import logging
from datetime import datetime

# Configurar paths
sys.path.insert(0, str(Path(__file__).parent.parent / "1_parsing_PDF"))

# Configurar logging
logging.basicConfig(level=logging.WARNING)  # Menos verbose

from test_ab_gemini_vs_gpt import ABTestRunner

print("\n" + "="*80)
print("🧪 TESTE A/B EXPANDIDO: Gemini 2.5 Pro vs GPT-4o-mini")
print("="*80 + "\n")

# Configurar API keys
openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = "AIzaSyDaPekNGH_d1ywT2_ZojhHYGLQcNeLEUYM"

if not openai_key:
    print("❌ OPENAI_API_KEY não configurada!")
    exit(1)

# Criar runner
runner = ABTestRunner(openai_key, gemini_key)

# Buscar PDFs
base_dir = Path(__file__).parent.parent / "data" / "consultas"
pdfs = sorted(list(base_dir.rglob("*.pdf")))[:10]  # 10 PDFs para teste robusto

if not pdfs:
    print("❌ Nenhum PDF encontrado")
    exit(1)

print(f"📁 Processando {len(pdfs)} PDFs...")
print(f"🕐 Início: {datetime.now().strftime('%H:%M:%S')}\n")

# Executar testes
for idx, pdf_path in enumerate(pdfs, 1):
    print(f"[{idx:2d}/{len(pdfs)}] {pdf_path.name[:50]:50s} ... ", end='', flush=True)
    try:
        runner.comparar_extracao(str(pdf_path))
        print("✅")
    except Exception as e:
        print(f"❌ {str(e)[:30]}")

# Gerar relatório
print("\n" + runner.gerar_relatorio())

# Salvar resultados
output_file = Path(__file__).parent / "ab_test_expandido_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(runner.resultados, f, indent=2, ensure_ascii=False)

print(f"\n💾 Resultados salvos: {output_file.name}")
print(f"🕐 Fim: {datetime.now().strftime('%H:%M:%S')}")
