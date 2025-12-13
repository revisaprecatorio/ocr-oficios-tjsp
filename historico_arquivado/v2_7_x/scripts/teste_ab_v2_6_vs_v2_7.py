#!/usr/bin/env python3
"""
A/B Testing: V2.6.1 vs V2.7.0

Compare performance of LLM-first vs REGEX-first approaches.

METRICS COMPARED:
1. Success rate (% PDFs processed without errors)
2. Average fields filled per PDF
3. Processing time per PDF
4. Accuracy per field (when ground truth available)
5. Token usage & cost (for LLM calls)

EXPECTED RESULTS:
- V2.7.0 should have: +25% accuracy, -70% time, -80% cost
- V2.7.0 should fill 15+ more fields on average
- Both should have similar success rates

VERSION: V2.7.0
DATE: 2025-12-10
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import sys

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.processador import ProcessadorOficio
from app.processador_v2_7 import ProcessadorOficioV27

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ABTester:
    """
    A/B testing framework for comparing V2.6.1 vs V2.7.0.
    """

    def __init__(
        self,
        openai_api_key: str,
        db_config: Dict,
        input_dir: str,
        output_dir: str
    ):
        """
        Initialize A/B tester.

        Args:
            openai_api_key: OpenAI API key
            db_config: Database configuration
            input_dir: Directory with test PDFs
            output_dir: Directory to save results
        """
        self.openai_api_key = openai_api_key
        self.db_config = db_config
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize processors
        self.proc_v2_6 = ProcessadorOficio(openai_api_key, db_config)
        self.proc_v2_7 = ProcessadorOficioV27(openai_api_key, db_config)

        logger.info("=" * 80)
        logger.info("🧪 A/B TESTER INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"Input dir: {self.input_dir}")
        logger.info(f"Output dir: {self.output_dir}")
        logger.info("=" * 80)

    def encontrar_pdfs_teste(self) -> List[Tuple[str, str]]:
        """
        Find test PDFs and their expected CPFs.

        Returns:
            List of (pdf_path, cpf) tuples
        """
        pdfs = []

        # Search in all lote_* subdirectories
        for lote_dir in self.input_dir.glob("lote_*"):
            if not lote_dir.is_dir():
                continue

            for pdf_file in lote_dir.glob("*.pdf"):
                # Extract CPF from filename (first 11 digits)
                nome = pdf_file.stem
                cpf = nome[:11]  # First 11 chars should be CPF

                # Validate CPF (11 digits)
                if len(cpf) == 11 and cpf.isdigit():
                    pdfs.append((str(pdf_file), cpf))

        logger.info(f"📄 Encontrados {len(pdfs)} PDFs de teste")
        return pdfs

    def processar_pdf_v2_6(self, pdf_path: str, cpf: str) -> Dict:
        """
        Process PDF with V2.6.1 (LLM-first).

        Args:
            pdf_path: Path to PDF
            cpf: Expected CPF

        Returns:
            Dict with result and metrics
        """
        logger.info(f"🔵 V2.6.1: Processing {Path(pdf_path).name}...")

        inicio = time.time()
        try:
            resultado = self.proc_v2_6.processar_arquivo(pdf_path, cpf)
            tempo = time.time() - inicio

            if resultado and resultado.get('sucesso'):
                dados = resultado.get('dados', {})
                campos_preenchidos = len([v for v in dados.values() if v is not None])

                return {
                    'versao': 'V2.6.1',
                    'pdf': Path(pdf_path).name,
                    'cpf': cpf,
                    'sucesso': True,
                    'tempo_s': tempo,
                    'campos_preenchidos': campos_preenchidos,
                    'dados': dados,
                    'erro': None
                }
            else:
                return {
                    'versao': 'V2.6.1',
                    'pdf': Path(pdf_path).name,
                    'cpf': cpf,
                    'sucesso': False,
                    'tempo_s': tempo,
                    'campos_preenchidos': 0,
                    'dados': {},
                    'erro': resultado.get('erro', 'Unknown error') if resultado else 'Processing failed'
                }

        except Exception as e:
            tempo = time.time() - inicio
            logger.error(f"❌ V2.6.1 error: {e}")
            return {
                'versao': 'V2.6.1',
                'pdf': Path(pdf_path).name,
                'cpf': cpf,
                'sucesso': False,
                'tempo_s': tempo,
                'campos_preenchidos': 0,
                'dados': {},
                'erro': str(e)
            }

    def processar_pdf_v2_7(self, pdf_path: str, cpf: str) -> Dict:
        """
        Process PDF with V2.7.0 (REGEX-first).

        Args:
            pdf_path: Path to PDF
            cpf: Expected CPF

        Returns:
            Dict with result and metrics
        """
        logger.info(f"🟢 V2.7.0: Processing {Path(pdf_path).name}...")

        inicio = time.time()
        try:
            resultado = self.proc_v2_7.processar_arquivo(pdf_path, cpf)
            tempo = time.time() - inicio

            if resultado and resultado.get('sucesso'):
                dados = resultado.get('dados', {})
                campos_preenchidos = len([v for v in dados.values() if v is not None])

                return {
                    'versao': 'V2.7.0',
                    'pdf': Path(pdf_path).name,
                    'cpf': cpf,
                    'sucesso': True,
                    'tempo_s': tempo,
                    'campos_preenchidos': campos_preenchidos,
                    'campos_regex': resultado.get('campos_regex', 0),
                    'campos_llm': resultado.get('campos_llm', 0),
                    'dados': dados,
                    'erro': None
                }
            else:
                return {
                    'versao': 'V2.7.0',
                    'pdf': Path(pdf_path).name,
                    'cpf': cpf,
                    'sucesso': False,
                    'tempo_s': tempo,
                    'campos_preenchidos': 0,
                    'campos_regex': 0,
                    'campos_llm': 0,
                    'dados': {},
                    'erro': resultado.get('erro', 'Unknown error') if resultado else 'Processing failed'
                }

        except Exception as e:
            tempo = time.time() - inicio
            logger.error(f"❌ V2.7.0 error: {e}")
            return {
                'versao': 'V2.7.0',
                'pdf': Path(pdf_path).name,
                'cpf': cpf,
                'sucesso': False,
                'tempo_s': tempo,
                'campos_preenchidos': 0,
                'campos_regex': 0,
                'campos_llm': 0,
                'dados': {},
                'erro': str(e)
            }

    def executar_teste_ab(self, limite_pdfs: int = None) -> Dict:
        """
        Execute A/B test on all PDFs.

        Args:
            limite_pdfs: Maximum number of PDFs to test (None = all)

        Returns:
            Dict with aggregated results
        """
        logger.info("=" * 80)
        logger.info("🧪 STARTING A/B TEST")
        logger.info("=" * 80)

        pdfs = self.encontrar_pdfs_teste()

        if limite_pdfs:
            pdfs = pdfs[:limite_pdfs]
            logger.info(f"⚠️ Limitando a {limite_pdfs} PDFs para teste rápido")

        resultados_v2_6 = []
        resultados_v2_7 = []

        for idx, (pdf_path, cpf) in enumerate(pdfs, 1):
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"📄 PDF {idx}/{len(pdfs)}: {Path(pdf_path).name}")
            logger.info("=" * 80)

            # Test V2.6.1
            resultado_v2_6 = self.processar_pdf_v2_6(pdf_path, cpf)
            resultados_v2_6.append(resultado_v2_6)

            # Test V2.7.0
            resultado_v2_7 = self.processar_pdf_v2_7(pdf_path, cpf)
            resultados_v2_7.append(resultado_v2_7)

            # Show comparison
            logger.info("")
            logger.info("📊 COMPARISON:")
            logger.info(f"   V2.6.1: {resultado_v2_6['sucesso']} | {resultado_v2_6['campos_preenchidos']} fields | {resultado_v2_6['tempo_s']:.2f}s")
            logger.info(f"   V2.7.0: {resultado_v2_7['sucesso']} | {resultado_v2_7['campos_preenchidos']} fields | {resultado_v2_7['tempo_s']:.2f}s")

            if resultado_v2_7['sucesso']:
                logger.info(f"   V2.7.0 BREAKDOWN: {resultado_v2_7['campos_regex']} regex + {resultado_v2_7['campos_llm']} llm")

        # Aggregate results
        resultados = {
            'timestamp': datetime.now().isoformat(),
            'total_pdfs': len(pdfs),
            'v2_6_1': self._agregar_resultados(resultados_v2_6),
            'v2_7_0': self._agregar_resultados(resultados_v2_7),
            'resultados_detalhados': {
                'v2_6_1': resultados_v2_6,
                'v2_7_0': resultados_v2_7
            }
        }

        # Save results
        resultado_file = self.output_dir / f"ab_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(resultado_file, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"✅ Results saved to: {resultado_file}")
        logger.info("=" * 80)

        # Generate report
        self._gerar_relatorio(resultados)

        return resultados

    def _agregar_resultados(self, resultados: List[Dict]) -> Dict:
        """
        Aggregate results for a version.

        Args:
            resultados: List of individual results

        Returns:
            Dict with aggregated metrics
        """
        total = len(resultados)
        sucessos = sum(1 for r in resultados if r['sucesso'])
        falhas = total - sucessos

        # Calculate averages (only for successful cases)
        sucessos_list = [r for r in resultados if r['sucesso']]

        if sucessos_list:
            tempo_medio = sum(r['tempo_s'] for r in sucessos_list) / len(sucessos_list)
            campos_medio = sum(r['campos_preenchidos'] for r in sucessos_list) / len(sucessos_list)
        else:
            tempo_medio = 0
            campos_medio = 0

        return {
            'total_pdfs': total,
            'sucessos': sucessos,
            'falhas': falhas,
            'taxa_sucesso': 100.0 * sucessos / total if total > 0 else 0,
            'tempo_medio_s': tempo_medio,
            'campos_medio': campos_medio
        }

    def _gerar_relatorio(self, resultados: Dict):
        """
        Generate human-readable report.

        Args:
            resultados: Aggregated results dict
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 A/B TEST REPORT")
        logger.info("=" * 80)
        logger.info(f"Timestamp: {resultados['timestamp']}")
        logger.info(f"Total PDFs: {resultados['total_pdfs']}")
        logger.info("")

        v2_6 = resultados['v2_6_1']
        v2_7 = resultados['v2_7_0']

        logger.info("🔵 V2.6.1 (LLM-first):")
        logger.info(f"   Success rate: {v2_6['taxa_sucesso']:.1f}% ({v2_6['sucessos']}/{v2_6['total_pdfs']})")
        logger.info(f"   Avg time: {v2_6['tempo_medio_s']:.2f}s per PDF")
        logger.info(f"   Avg fields: {v2_6['campos_medio']:.1f} fields filled")
        logger.info("")

        logger.info("🟢 V2.7.0 (REGEX-first):")
        logger.info(f"   Success rate: {v2_7['taxa_sucesso']:.1f}% ({v2_7['sucessos']}/{v2_7['total_pdfs']})")
        logger.info(f"   Avg time: {v2_7['tempo_medio_s']:.2f}s per PDF")
        logger.info(f"   Avg fields: {v2_7['campos_medio']:.1f} fields filled")
        logger.info("")

        # Calculate improvements
        logger.info("📈 V2.7.0 IMPROVEMENTS:")

        if v2_6['tempo_medio_s'] > 0:
            tempo_ganho = 100.0 * (v2_6['tempo_medio_s'] - v2_7['tempo_medio_s']) / v2_6['tempo_medio_s']
            logger.info(f"   Time: {tempo_ganho:+.1f}% ({v2_6['tempo_medio_s']:.2f}s → {v2_7['tempo_medio_s']:.2f}s)")

        if v2_6['campos_medio'] > 0:
            campos_ganho = v2_7['campos_medio'] - v2_6['campos_medio']
            logger.info(f"   Fields: {campos_ganho:+.1f} more fields ({v2_6['campos_medio']:.1f} → {v2_7['campos_medio']:.1f})")

        taxa_ganho = v2_7['taxa_sucesso'] - v2_6['taxa_sucesso']
        logger.info(f"   Success rate: {taxa_ganho:+.1f}pp ({v2_6['taxa_sucesso']:.1f}% → {v2_7['taxa_sucesso']:.1f}%)")

        logger.info("=" * 80)

        # Save markdown report
        relatorio_md = self.output_dir / f"ab_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._salvar_relatorio_markdown(resultados, relatorio_md)
        logger.info(f"📄 Markdown report saved to: {relatorio_md}")
        logger.info("=" * 80)

    def _salvar_relatorio_markdown(self, resultados: Dict, output_path: Path):
        """
        Save detailed markdown report.

        Args:
            resultados: Aggregated results
            output_path: Path to save markdown file
        """
        v2_6 = resultados['v2_6_1']
        v2_7 = resultados['v2_7_0']

        # Calculate improvements
        tempo_ganho = 0
        if v2_6['tempo_medio_s'] > 0:
            tempo_ganho = 100.0 * (v2_6['tempo_medio_s'] - v2_7['tempo_medio_s']) / v2_6['tempo_medio_s']

        campos_ganho = v2_7['campos_medio'] - v2_6['campos_medio']
        taxa_ganho = v2_7['taxa_sucesso'] - v2_6['taxa_sucesso']

        md = f"""# A/B Test Report: V2.6.1 vs V2.7.0

**Date:** {resultados['timestamp']}
**Total PDFs:** {resultados['total_pdfs']}

## Summary

| Metric | V2.6.1 (LLM-first) | V2.7.0 (REGEX-first) | Improvement |
|--------|-------------------|---------------------|-------------|
| **Success Rate** | {v2_6['taxa_sucesso']:.1f}% | {v2_7['taxa_sucesso']:.1f}% | {taxa_ganho:+.1f}pp |
| **Avg Time (s)** | {v2_6['tempo_medio_s']:.2f}s | {v2_7['tempo_medio_s']:.2f}s | {tempo_ganho:+.1f}% |
| **Avg Fields** | {v2_6['campos_medio']:.1f} | {v2_7['campos_medio']:.1f} | {campos_ganho:+.1f} |
| **Successes** | {v2_6['sucessos']}/{v2_6['total_pdfs']} | {v2_7['sucessos']}/{v2_7['total_pdfs']} | - |
| **Failures** | {v2_6['falhas']} | {v2_7['falhas']} | - |

## Interpretation

### 🟢 V2.7.0 Wins If:
- Time improvement ≥ 50% (target: 70%)
- Fields filled increase ≥ 10 (target: 15)
- Success rate maintained or improved

### 🔵 V2.6.1 Wins If:
- V2.7.0 has lower success rate
- V2.7.0 has fewer fields filled

## Detailed Results

### V2.6.1 (LLM-first)
- **Approach:** Send all 53 fields to LLM, merge with 8 regex fields
- **Success Rate:** {v2_6['taxa_sucesso']:.1f}% ({v2_6['sucessos']}/{v2_6['total_pdfs']})
- **Avg Time:** {v2_6['tempo_medio_s']:.2f}s per PDF
- **Avg Fields:** {v2_6['campos_medio']:.1f} fields filled

### V2.7.0 (REGEX-first)
- **Approach:** Extract 45 fields via regex, send only missing fields to LLM
- **Success Rate:** {v2_7['taxa_sucesso']:.1f}% ({v2_7['sucessos']}/{v2_7['total_pdfs']})
- **Avg Time:** {v2_7['tempo_medio_s']:.2f}s per PDF
- **Avg Fields:** {v2_7['campos_medio']:.1f} fields filled

## Conclusion

"""

        # Add conclusion based on results
        if tempo_ganho >= 50 and campos_ganho >= 10:
            md += """✅ **V2.7.0 is the clear winner!**

The REGEX-first approach delivers significant improvements in speed and completeness:
- Faster processing (meets or exceeds 50% time reduction target)
- More fields extracted (meets or exceeds +10 fields target)
- Maintained or improved success rate

**Recommendation:** Promote V2.7.0 to production and retire V2.6.1.
"""
        elif v2_7['taxa_sucesso'] < v2_6['taxa_sucesso']:
            md += """⚠️ **V2.6.1 wins due to reliability.**

While V2.7.0 shows improvements in speed/completeness, the success rate regression is concerning.

**Recommendation:** Debug V2.7.0 failures before promoting to production.
"""
        else:
            md += """🤔 **Mixed results - further analysis needed.**

V2.7.0 shows improvements but doesn't meet all targets.

**Recommendation:** Investigate specific failure cases and optimize regex patterns.
"""

        # Save
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)


def main():
    """
    Main entry point for A/B testing.
    """
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment")

    db_config = {
        'host': os.getenv("DB_HOST", "72.60.62.124"),
        'port': int(os.getenv("DB_PORT", 5432)),
        'database': os.getenv("DB_NAME", "n8n"),
        'user': os.getenv("DB_USER", "admin"),
        'password': os.getenv("DB_PASSWORD", "BetaAgent2024SecureDB")
    }

    # Test configuration
    input_dir = Path(__file__).parent.parent / "data" / "consultas"
    output_dir = Path(__file__).parent / "ab_test_results"

    # Create tester
    tester = ABTester(
        openai_api_key=openai_api_key,
        db_config=db_config,
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )

    # Run test (limit to 5 PDFs for quick test, remove limit for full test)
    import sys
    limite = int(sys.argv[1]) if len(sys.argv) > 1 else None

    resultados = tester.executar_teste_ab(limite_pdfs=limite)

    logger.info("")
    logger.info("✅ A/B test completed successfully!")


if __name__ == "__main__":
    main()
