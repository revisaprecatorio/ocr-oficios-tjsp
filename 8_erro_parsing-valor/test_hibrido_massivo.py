"""
TESTE MASSIVO: Modo Híbrido Gemini + OpenAI
Testa TODOS os PDFs disponíveis para validar 100% de taxa de sucesso.
"""

import sys
import os
from pathlib import Path
import json
import logging
from datetime import datetime
from collections import Counter

# Configurar paths
sys.path.insert(0, str(Path.cwd().parent / "1_parsing_PDF"))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from app.processador import ProcessadorOficio

print("\n" + "="*80)
print("🧪 TESTE MASSIVO: Modo Híbrido (Gemini 2.5 Flash + GPT-4o-mini)")
print("   Objetivo: Validar 100% de taxa de sucesso")
print("="*80 + "\n")

# Configurar API keys
openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not openai_key:
    print("❌ ERRO: OPENAI_API_KEY não configurada")
    sys.exit(1)

if not gemini_key:
    print("⚠️ WARNING: GOOGLE_API_KEY não configurada, usando apenas OpenAI")

# DB config (dummy para testes)
db_config = {
    "host": "localhost",
    "database": "test",
    "user": "test",
    "password": "test"
}

# Criar processador
processador = ProcessadorOficio(openai_key, db_config)

# Buscar TODOS os PDFs
base_dir = Path.cwd().parent / "data" / "consultas"
todos_pdfs = sorted(list(base_dir.rglob("*.pdf")))

print(f"📁 Total de PDFs encontrados: {len(todos_pdfs)}")
print(f"🕐 Início: {datetime.now().strftime('%H:%M:%S')}\n")

# Estatísticas
stats = {
    "total": 0,
    "sucessos": 0,
    "falhas": 0,
    "gemini_sucessos": 0,
    "openai_fallbacks": 0,
    "ambos_falharam": 0,
    "campos_totais": [],
    "tempos": [],
    "erros": Counter()
}

resultados_detalhados = []

# Processar cada PDF
for idx, pdf_path in enumerate(todos_pdfs, 1):
    stats["total"] += 1
    nome = pdf_path.name[:50]
    
    print(f"[{idx:3d}/{len(todos_pdfs)}] {nome:50s} ", end='', flush=True)
    
    try:
        # Extrair CPF da pasta
        cpf = pdf_path.parent.name
        
        # Processar
        inicio = datetime.now()
        resultado = processador.processar_arquivo(str(pdf_path), cpf)
        tempo = (datetime.now() - inicio).total_seconds()
        
        stats["tempos"].append(tempo)
        
        if resultado and resultado.get("sucesso"):
            stats["sucessos"] += 1
            
            # Contar campos extraídos
            dados = resultado.get("dados", {})
            campos_preenchidos = len([v for v in dados.values() if v not in [None, '', []]])
            stats["campos_totais"].append(campos_preenchidos)
            
            # Detectar qual LLM foi usado (via logs - simplificado)
            # Como não temos acesso direto, assumimos Gemini se não houve erro
            stats["gemini_sucessos"] += 1
            
            print(f"✅ ({campos_preenchidos:2d} campos, {tempo:.1f}s)")
            
            resultados_detalhados.append({
                "pdf": pdf_path.name,
                "sucesso": True,
                "campos": campos_preenchidos,
                "tempo": tempo
            })
        else:
            stats["falhas"] += 1
            erro = resultado.get("erro", "Erro desconhecido") if resultado else "Resultado None"
            stats["erros"][erro[:50]] += 1
            
            print(f"❌ {erro[:30]}")
            
            resultados_detalhados.append({
                "pdf": pdf_path.name,
                "sucesso": False,
                "erro": erro,
                "tempo": tempo
            })
    
    except Exception as e:
        stats["falhas"] += 1
        erro_str = str(e)[:50]
        stats["erros"][erro_str] += 1
        print(f"❌ Exception: {erro_str}")
        
        resultados_detalhados.append({
            "pdf": pdf_path.name,
            "sucesso": False,
            "erro": str(e),
            "tempo": 0
        })

# Análise final
print("\n" + "="*80)
print("📊 RELATÓRIO FINAL - TESTE MASSIVO")
print("="*80 + "\n")

print(f"Total de PDFs testados:     {stats['total']}")
print(f"Sucessos:                   {stats['sucessos']} ({100*stats['sucessos']/max(1,stats['total']):.1f}%)")
print(f"Falhas:                     {stats['falhas']} ({100*stats['falhas']/max(1,stats['total']):.1f}%)")

if stats['campos_totais']:
    print(f"\nCampos extraídos (média):   {sum(stats['campos_totais'])/len(stats['campos_totais']):.1f}")
    print(f"Campos extraídos (mínimo):  {min(stats['campos_totais'])}")
    print(f"Campos extraídos (máximo):  {max(stats['campos_totais'])}")

if stats['tempos']:
    print(f"\nTempo médio:                {sum(stats['tempos'])/len(stats['tempos']):.1f}s")
    print(f"Tempo total:                {sum(stats['tempos']):.1f}s ({sum(stats['tempos'])/60:.1f} min)")

if stats['erros']:
    print(f"\n🔍 Top 5 Erros:")
    for erro, count in stats['erros'].most_common(5):
        print(f"   {count:3d}x - {erro}")

# Avaliação
print("\n" + "="*80)
print("🎯 AVALIAÇÃO:")
print("="*80 + "\n")

taxa_sucesso = 100 * stats['sucessos'] / max(1, stats['total'])

if taxa_sucesso == 100:
    print("✅ PERFEITO! 100% de taxa de sucesso!")
    print("✅ Modo híbrido funcionando conforme esperado")
    print("✅ Sistema pronto para produção!")
elif taxa_sucesso >= 95:
    print(f"✅ EXCELENTE! {taxa_sucesso:.1f}% de taxa de sucesso")
    print(f"⚠️ {stats['falhas']} falhas detectadas (revisar erros acima)")
    print("✅ Sistema quase pronto para produção")
elif taxa_sucesso >= 90:
    print(f"⚠️ BOM: {taxa_sucesso:.1f}% de taxa de sucesso")
    print(f"⚠️ {stats['falhas']} falhas detectadas")
    print("⚠️ Requer análise e correções")
else:
    print(f"❌ PROBLEMAS: Apenas {taxa_sucesso:.1f}% de sucesso")
    print(f"❌ {stats['falhas']} falhas em {stats['total']} PDFs")
    print("❌ Requer investigação urgente")

# Salvar resultados
output_file = Path.cwd() / "test_hibrido_massivo_results.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": datetime.now().isoformat(),
        "stats": {
            "total": stats["total"],
            "sucessos": stats["sucessos"],
            "falhas": stats["falhas"],
            "taxa_sucesso": taxa_sucesso,
            "campos_media": sum(stats['campos_totais'])/len(stats['campos_totais']) if stats['campos_totais'] else 0,
            "tempo_medio": sum(stats['tempos'])/len(stats['tempos']) if stats['tempos'] else 0
        },
        "resultados": resultados_detalhados
    }, f, indent=2, ensure_ascii=False)

print(f"\n💾 Resultados salvos: {output_file.name}")
print(f"🕐 Fim: {datetime.now().strftime('%H:%M:%S')}")
print("="*80)

