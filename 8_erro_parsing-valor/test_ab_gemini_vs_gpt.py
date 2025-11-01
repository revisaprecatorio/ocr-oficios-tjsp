"""
Teste A/B: Gemini 2.5 Pro vs GPT-4o-mini
Compara precisão de extração em casos problemáticos identificados.

Implementado para FINDING 06 - Testes com Gemini 2.5 Pro
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "1_parsing_PDF"))

from app.llm_adapter import LLMAdapter, LLMProvider
from app.detector_anexo import DetectorAnexoII
from app.schemas import OficioRequisitorio
import pymupdf

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ABTestRunner:
    """Executa testes A/B entre LLMs diferentes."""
    
    def __init__(self, openai_key: str, gemini_key: str):
        """
        Inicializa runner de testes A/B.
        
        Args:
            openai_key: API key OpenAI
            gemini_key: API key Gemini
        """
        self.adapter = LLMAdapter(
            openai_api_key=openai_key,
            gemini_api_key=gemini_key
        )
        self.detector_anexo = DetectorAnexoII()
        
        self.resultados = []
    
    def criar_prompt_extracao(self, texto_oficio: str) -> str:
        """
        Cria prompt otimizado para extração estruturada.
        Baseado no prompt usado no processador.py atual.
        """
        prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

-- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
-- requerente_caps: Nome TODO EM MAIÚSCULAS

=== CAMPOS OPCIONAIS (nível raiz do JSON) ===

DADOS BANCÁRIOS:
-- banco: Código do banco (apenas números)
-- agencia: Número da agência
-- conta: Número da conta (com dígito)

VALORES MONETÁRIOS (números decimais, SEM R$, SEM pontos de milhar):
-- valor_principal_liquido: Valor principal líquido
-- valor_principal_bruto: Valor principal bruto  
-- juros_moratorios: Juros moratórios
-- valor_total_requisitado: Valor total requisitado

DATAS (formato YYYY-MM-DD):
-- data_nascimento: Data de nascimento do credor
-- data_base_atualizacao: Data base para atualização

OUTROS:
-- idoso: true se idade >= 60 anos, false caso contrário, null se sem data nascimento
-- doenca_grave: true/false/null
-- cpf_credor: CPF do credor (apenas números)

=== REGRAS CRÍTICAS ===

1. JSON FLAT: Todos os campos no nível raiz, SEM objetos aninhados
2. Campos não encontrados: usar null
3. Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
   Exemplos: "R$ 1.234,56" → 1234.56 | "R$ 50.000,00" → 50000.00
4. Datas: sempre YYYY-MM-DD | Exemplos: 31/12/2020 → "2020-12-31"
5. Requerente: SEMPRE em MAIÚSCULAS
6. CPF: apenas números (sem pontos/traços)

EXEMPLO DE ESTRUTURA CORRETA:
{{
  "processo_origem": "0035938-67.2018.8.26.0053",
  "requerente_caps": "JOÃO SILVA SANTOS",
  "valor_total_requisitado": 50000.00,
  "cpf_credor": "12345678900",
  "data_nascimento": "1963-04-15",
  "idoso": true,
  "banco": "001",
  "agencia": "1234",
  "conta": "567890-1"
}}

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido:"""
        
        return prompt
    
    def extrair_texto_relevante(self, pdf_path: str) -> str:
        """
        Extrai texto relevante do PDF (ofício + ANEXO II).
        Simula o que o processador.py faz.
        """
        try:
            doc = pymupdf.open(pdf_path)
            
            # Para simplificar, pegar primeiras 50 páginas
            texto_completo = ""
            for i in range(min(50, len(doc))):
                texto_completo += doc[i].get_text() + "\n"
            
            doc.close()
            
            # Detectar ANEXO II
            paginas_anexo, texto_anexo = self.detector_anexo.detectar_anexo_ii(pdf_path)
            
            if texto_anexo:
                texto_completo += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
            
            return texto_completo
            
        except Exception as e:
            logger.error(f"Erro ao extrair texto de {pdf_path}: {e}")
            return ""
    
    def validar_com_pydantic(self, dados: Dict[str, Any]) -> tuple[bool, str]:
        """
        Valida dados extraídos com Pydantic.
        
        Returns:
            (sucesso, mensagem_erro)
        """
        try:
            oficio = OficioRequisitorio(**dados)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def comparar_extracao(
        self,
        pdf_path: str,
        esperado: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Compara extração de ambos LLMs em um PDF.
        
        Args:
            pdf_path: Caminho para PDF
            esperado: Valores esperados (ground truth) se disponível
            
        Returns:
            Resultado da comparação com métricas
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"📄 Testando: {Path(pdf_path).name}")
        logger.info(f"{'='*80}\n")
        
        # Extrair texto
        texto = self.extrair_texto_relevante(pdf_path)
        logger.info(f"📝 Texto extraído: {len(texto):,} caracteres\n")
        
        # Criar prompt
        prompt = self.criar_prompt_extracao(texto)
        
        # Testar com ambos provedores
        resultados_llm = self.adapter.compare_providers(prompt)
        
        # Analisar resultados
        resultado = {
            "pdf": Path(pdf_path).name,
            "timestamp": datetime.now().isoformat(),
            "texto_chars": len(texto),
            "llms": {}
        }
        
        for provider, res in resultados_llm.items():
            provider_name = provider.value
            
            if not res["success"]:
                resultado["llms"][provider_name] = {
                    "success": False,
                    "error": res["error"]
                }
                continue
            
            dados = res["data"]
            
            # Validar com Pydantic
            valido, erro_validacao = self.validar_com_pydantic(dados)
            
            # Contar campos extraídos
            campos_extraidos = sum(1 for v in dados.values() if v is not None)
            
            resultado["llms"][provider_name] = {
                "success": True,
                "data": dados,
                "validation": {
                    "passed": valido,
                    "error": erro_validacao
                },
                "metrics": {
                    "campos_extraidos": campos_extraidos,
                    "campos_totais": len(dados)
                }
            }
            
            # Comparar com esperado se disponível
            if esperado:
                diferencas = self._comparar_com_esperado(dados, esperado)
                resultado["llms"][provider_name]["diferencas"] = diferencas
        
        self.resultados.append(resultado)
        return resultado
    
    def _comparar_com_esperado(
        self,
        extraido: Dict[str, Any],
        esperado: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compara valores extraídos com esperados."""
        diferencas = []
        
        for campo, valor_esperado in esperado.items():
            valor_extraido = extraido.get(campo)
            
            if valor_extraido != valor_esperado:
                diferencas.append({
                    "campo": campo,
                    "esperado": valor_esperado,
                    "extraido": valor_extraido,
                    "correto": False
                })
        
        return diferencas
    
    def gerar_relatorio(self) -> str:
        """Gera relatório consolidado dos testes."""
        if not self.resultados:
            return "Nenhum teste executado."
        
        relatorio = []
        relatorio.append("\n" + "="*80)
        relatorio.append("📊 RELATÓRIO A/B: Gemini 2.5 Pro vs GPT-4o-mini")
        relatorio.append("="*80 + "\n")
        
        # Estatísticas gerais
        total_testes = len(self.resultados)
        relatorio.append(f"Total de testes: {total_testes}\n")
        
        # Comparar provedores
        stats_providers = {
            "openai": {"sucessos": 0, "validacoes_ok": 0, "campos_medio": 0},
            "gemini": {"sucessos": 0, "validacoes_ok": 0, "campos_medio": 0}
        }
        
        for res in self.resultados:
            for provider, dados in res["llms"].items():
                if dados["success"]:
                    stats_providers[provider]["sucessos"] += 1
                    if dados["validation"]["passed"]:
                        stats_providers[provider]["validacoes_ok"] += 1
                    stats_providers[provider]["campos_medio"] += dados["metrics"]["campos_extraidos"]
        
        # Médias
        for provider in stats_providers:
            if stats_providers[provider]["sucessos"] > 0:
                stats_providers[provider]["campos_medio"] /= stats_providers[provider]["sucessos"]
        
        # Tabela comparativa
        relatorio.append("┌" + "─"*78 + "┐")
        relatorio.append(f"│ {'Provedor':<20} │ {'Sucessos':<12} │ {'Validações OK':<16} │ {'Campos/doc':<12} │")
        relatorio.append("├" + "─"*78 + "┤")
        
        for provider, stats in stats_providers.items():
            relatorio.append(
                f"│ {provider.upper():<20} │ {stats['sucessos']:>4}/{total_testes:<6} │ "
                f"{stats['validacoes_ok']:>4}/{stats['sucessos']:<10} │ {stats['campos_medio']:>6.1f}{'':>5} │"
            )
        
        relatorio.append("└" + "─"*78 + "┘\n")
        
        # Detalhes por PDF
        relatorio.append("\n📋 Detalhes por PDF:\n")
        
        for idx, res in enumerate(self.resultados, 1):
            relatorio.append(f"\n{idx}. {res['pdf']}")
            relatorio.append(f"   Texto: {res['texto_chars']:,} chars\n")
            
            for provider, dados in res["llms"].items():
                if dados["success"]:
                    validacao = "✅ OK" if dados["validation"]["passed"] else "❌ FALHOU"
                    campos = dados["metrics"]["campos_extraidos"]
                    relatorio.append(f"   {provider.upper():<10} {validacao}  ({campos} campos)")
                else:
                    relatorio.append(f"   {provider.upper():<10} ❌ ERRO: {dados['error'][:50]}")
        
        return "\n".join(relatorio)


# ===== MAIN =====

def main():
    """Executa teste A/B em casos problemáticos."""
    
    print("\n🧪 TESTE A/B: Gemini 2.5 Pro vs GPT-4o-mini")
    print("="*80 + "\n")
    
    # Configurar API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = "AIzaSyDaPekNGH_d1ywT2_ZojhHYGLQcNeLEUYM"
    
    if not openai_key:
        print("❌ OPENAI_API_KEY não configurada!")
        print("   Configure: export OPENAI_API_KEY=sk-...")
        return
    
    # Criar runner
    runner = ABTestRunner(openai_key, gemini_key)
    
    # Buscar PDFs de teste
    base_dir = Path(__file__).parent.parent / "data" / "consultas"
    pdfs = sorted(list(base_dir.rglob("*.pdf")))[:3]  # Primeiros 3 PDFs
    
    if not pdfs:
        print("❌ Nenhum PDF encontrado em data/consultas/")
        return
    
    print(f"📁 Encontrados {len(pdfs)} PDFs para teste\n")
    
    # Executar testes
    for pdf_path in pdfs:
        try:
            runner.comparar_extracao(str(pdf_path))
        except Exception as e:
            logger.error(f"Erro ao testar {pdf_path.name}: {e}")
    
    # Gerar e exibir relatório
    relatorio = runner.gerar_relatorio()
    print(relatorio)
    
    # Salvar resultados
    output_file = Path(__file__).parent / "ab_test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(runner.resultados, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados salvos em: {output_file}")


if __name__ == "__main__":
    main()

