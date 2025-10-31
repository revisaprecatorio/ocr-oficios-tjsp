#!/usr/bin/env python3
"""
Script de Teste Isolado - Bug de Parsing de Valores

Processa o PDF problemático localmente sem gravar no banco de dados.
Gera outputs detalhados em cada etapa para diagnóstico.

Processo: 0015796-15.2025.8.26.0500
CPF: 27308157830 (273.081.578-30)
PDF: Precatório-RAF.pdf

Autor: Sistema OCR Debug
Data: 31/10/2025
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Adicionar path do sistema OCR
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "3_OCR" / "1_parsing_PDF"))

from dotenv import load_dotenv

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent.parent / "3_OCR" / ".env"
load_dotenv(env_path)

# Importar componentes do sistema OCR
from app.detector import DetectorOficio
from app.detector_anexo import DetectorAnexoII
from app.detector_processamento import DetectorProcessamento
from app.processador import ProcessadorOficio
from app.schemas import OficioRequisitorio

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestProcessadorLocal:
    """Processador de teste que salva outputs em cada etapa"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "test_outputs"
        self.output_dir.mkdir(exist_ok=True)
        
        # Configurações
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.db_config = {}  # Não vamos usar banco
        
        # Inicializar detectores
        self.detector = DetectorOficio()
        self.detector_anexo = DetectorAnexoII()
        self.detector_proc = DetectorProcessamento()
        
        # Inicializar processador
        self.processador = ProcessadorOficio(
            openai_api_key=self.openai_api_key,
            db_config=self.db_config
        )
        
        logger.info("✅ TestProcessadorLocal inicializado")
        logger.info(f"📁 Outputs serão salvos em: {self.output_dir}")
    
    def salvar_output(self, nome_arquivo: str, conteudo: str):
        """Salva output em arquivo"""
        arquivo = self.output_dir / nome_arquivo
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        logger.info(f"💾 Salvo: {nome_arquivo}")
    
    def processar_pdf_debug(self, pdf_path: str, cpf: str):
        """
        Processa PDF com debug completo em cada etapa
        
        Args:
            pdf_path: Caminho para o PDF
            cpf: CPF numérico (11 dígitos)
        """
        logger.info("="*80)
        logger.info("🔍 INICIANDO TESTE DE PROCESSAMENTO")
        logger.info("="*80)
        logger.info(f"📄 PDF: {Path(pdf_path).name}")
        logger.info(f"👤 CPF: {cpf}")
        logger.info("")
        
        # ETAPA 1: Extrair texto bruto do PDF
        logger.info("📖 ETAPA 1: Extração de texto do PDF com PyMuPDF")
        logger.info("-" * 80)
        
        import pymupdf
        doc = pymupdf.open(pdf_path)
        texto_completo = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            texto_pagina = page.get_text()
            texto_completo += f"\n--- PÁGINA {page_num + 1} ---\n{texto_pagina}"
        doc.close()
        
        self.salvar_output("1_texto_extraido.txt", texto_completo)
        logger.info(f"✅ Texto extraído: {len(texto_completo):,} caracteres")
        
        # Buscar valor no texto para confirmar
        if "88.994,41" in texto_completo:
            logger.info("✅ Valor correto '88.994,41' ENCONTRADO no texto bruto")
        else:
            logger.warning("⚠️  Valor '88.994,41' NÃO encontrado no texto bruto")
        
        logger.info("")
        
        # ETAPA 2: Detectar ofício e ANEXO II
        logger.info("🔍 ETAPA 2: Detecção de ofício e ANEXO II")
        logger.info("-" * 80)
        
        cpf_formatado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        
        # Buscar todos os ofícios
        todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
        logger.info(f"📄 Ofícios encontrados: {len(todos_oficios)}")
        
        # Encontrar ofício com CPF correto
        oficio_correto = None
        for idx, oficio in enumerate(todos_oficios, 1):
            if self.detector.validar_cpf_no_oficio(oficio['texto'], cpf_formatado):
                logger.info(f"✅ CPF encontrado no ofício {idx}")
                oficio_correto = oficio
                break
        
        if not oficio_correto:
            logger.error("❌ CPF não encontrado em nenhum ofício")
            return
        
        # Detectar ANEXO II
        paginas_anexo, texto_anexo = self.detector_anexo.detectar_anexo_ii(pdf_path)
        if texto_anexo:
            logger.info(f"📋 ANEXO II encontrado em {len(paginas_anexo)} página(s)")
        else:
            logger.warning("⚠️  ANEXO II não encontrado")
        
        # Detectar PROCESSAMENTO
        ultima_pag_oficio = oficio_correto['paginas'][-1]
        inicio_proc = paginas_anexo[-1] - 1 if paginas_anexo else ultima_pag_oficio - 1
        pagina_proc, texto_proc = self.detector_proc.detectar_processamento(
            pdf_path,
            inicio=inicio_proc,
            limite=100
        )
        
        if texto_proc:
            logger.info(f"📋 PROCESSAMENTO encontrado na página {pagina_proc}")
        
        # Montar texto relevante
        texto_relevante = oficio_correto['texto']
        if texto_anexo:
            texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
        if texto_proc:
            texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
        
        self.salvar_output("1a_texto_relevante.txt", texto_relevante)
        logger.info(f"✅ Texto relevante: {len(texto_relevante):,} caracteres")
        logger.info("")
        
        # ETAPA 3: Montar prompt para LLM
        logger.info("💬 ETAPA 3: Montagem do prompt para GPT-4o-mini")
        logger.info("-" * 80)
        
        prompt = self._criar_prompt(texto_relevante, tem_anexo_ii=bool(texto_anexo))
        self.salvar_output("2_prompt_llm.txt", prompt)
        logger.info(f"✅ Prompt criado: {len(prompt):,} caracteres")
        logger.info("")
        
        # ETAPA 4: Chamar LLM (GPT-4o-mini)
        logger.info("🤖 ETAPA 4: Chamada ao GPT-4o-mini")
        logger.info("-" * 80)
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key)
        
        logger.info("⏳ Aguardando resposta do GPT-4o-mini...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em extração de dados estruturados de documentos jurídicos. Retorne apenas JSON válido."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        json_resposta = response.choices[0].message.content
        self.salvar_output("3_resposta_llm.json", json_resposta)
        
        # Parse e exibir valores extraídos pelo LLM
        dados_llm = json.loads(json_resposta)
        logger.info("✅ Resposta recebida do LLM")
        logger.info("")
        logger.info("💰 VALORES EXTRAÍDOS PELO LLM:")
        logger.info(f"   valor_principal_liquido: {dados_llm.get('valor_principal_liquido')}")
        logger.info(f"   valor_principal_bruto: {dados_llm.get('valor_principal_bruto')}")
        logger.info(f"   juros_moratorios: {dados_llm.get('juros_moratorios')}")
        logger.info(f"   valor_total_requisitado: {dados_llm.get('valor_total_requisitado')}")
        logger.info("")
        
        # ETAPA 5: Validação Pydantic
        logger.info("✅ ETAPA 5: Validação com Pydantic")
        logger.info("-" * 80)
        
        try:
            oficio_validado = OficioRequisitorio(**dados_llm)
            logger.info("✅ Validação Pydantic: SUCESSO")
            
            dados_validados = oficio_validado.model_dump()
            self.salvar_output(
                "4_dados_validados.json",
                json.dumps(dados_validados, indent=2, ensure_ascii=False, default=str)
            )
            
            logger.info("")
            logger.info("💰 VALORES APÓS VALIDAÇÃO PYDANTIC:")
            logger.info(f"   valor_principal_liquido: {oficio_validado.valor_principal_liquido}")
            logger.info(f"   valor_principal_bruto: {oficio_validado.valor_principal_bruto}")
            logger.info(f"   juros_moratorios: {oficio_validado.juros_moratorios}")
            logger.info(f"   valor_total_requisitado: {oficio_validado.valor_total_requisitado}")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Erro na validação Pydantic: {e}")
            return
        
        # ETAPA 6: Gerar SQL statement (sem executar)
        logger.info("📝 ETAPA 6: Geração de SQL statement")
        logger.info("-" * 80)
        
        sql = self._gerar_sql(cpf, oficio_validado)
        self.salvar_output("5_sql_statement.sql", sql)
        logger.info("✅ SQL statement gerado")
        logger.info("")
        
        # ETAPA 7: Comparação com valores corretos
        logger.info("📊 ETAPA 7: Comparação com valores corretos")
        logger.info("-" * 80)
        
        comparacao = self._gerar_comparacao(oficio_validado)
        self.salvar_output("6_tabela_comparacao.txt", comparacao)
        logger.info(comparacao)
        
        logger.info("")
        logger.info("="*80)
        logger.info("✅ TESTE COMPLETO! Verifique os arquivos em test_outputs/")
        logger.info("="*80)
    
    def _criar_prompt(self, texto_oficio: str, tem_anexo_ii: bool) -> str:
        """Cria prompt para LLM (mesmo do sistema original)"""
        prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)
- valor_principal_liquido: Valor principal líquido (número decimal)
- valor_principal_bruto: Valor principal bruto (número decimal)
- juros_moratorios: Juros moratórios (número decimal)
- valor_total_requisitado: Valor total requisitado (número decimal)

=== REGRAS CRÍTICAS ===

1. ESTRUTURA: JSON FLAT (todos os campos no nível raiz)
2. Campos não encontrados = null
3. Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
4. Datas: formato YYYY-MM-DD
5. Requerente: SEMPRE em MAIÚSCULAS
6. Booleanos: true ou false (minúsculas)

⚠️ IMPORTANTE: Para valores monetários, retorne apenas números com ponto como decimal.
Exemplo: "R$ 88.994,41" deve ser retornado como 88994.41

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido:"""
        
        return prompt
    
    def _gerar_sql(self, cpf: str, oficio: OficioRequisitorio) -> str:
        """Gera SQL statement formatado"""
        # Extrair número do processo do nome do arquivo
        numero_processo = "0015796-15.2025.8.26.0500"
        
        sql = f"""-- SQL Statement para INSERT/UPDATE
-- Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- ⚠️ ESTE SQL NÃO FOI EXECUTADO (modo debug)

INSERT INTO lista_processos (
    cpf,
    numero_processo,
    processo_origem,
    requerente_caps,
    numero_ordem,
    vara,
    valor_principal_liquido,
    valor_principal_bruto,
    juros_moratorios,
    valor_total_requisitado,
    contrib_previdenciaria_iprem,
    contrib_previdenciaria_hspm,
    banco,
    agencia,
    conta,
    conta_tipo,
    data_nascimento,
    idoso,
    doenca_grave,
    pcd,
    timestamp_processamento
) VALUES (
    '{cpf}',
    '{numero_processo}',
    '{oficio.processo_origem}',
    '{oficio.requerente_caps}',
    {f"'{oficio.numero_ordem}'" if oficio.numero_ordem else "NULL"},
    {f"'{oficio.vara}'" if oficio.vara else "NULL"},
    {oficio.valor_principal_liquido if oficio.valor_principal_liquido else "NULL"},
    {oficio.valor_principal_bruto if oficio.valor_principal_bruto else "NULL"},
    {oficio.juros_moratorios if oficio.juros_moratorios else "NULL"},
    {oficio.valor_total_requisitado if oficio.valor_total_requisitado else "NULL"},
    {oficio.contrib_previdenciaria_iprem if oficio.contrib_previdenciaria_iprem else "NULL"},
    {oficio.contrib_previdenciaria_hspm if oficio.contrib_previdenciaria_hspm else "NULL"},
    {f"'{oficio.banco}'" if oficio.banco else "NULL"},
    {f"'{oficio.agencia}'" if oficio.agencia else "NULL"},
    {f"'{oficio.conta}'" if oficio.conta else "NULL"},
    {f"'{oficio.conta_tipo}'" if oficio.conta_tipo else "NULL"},
    {f"'{oficio.data_nascimento}'" if oficio.data_nascimento else "NULL"},
    {oficio.idoso if oficio.idoso is not None else "NULL"},
    {oficio.doenca_grave if oficio.doenca_grave is not None else "NULL"},
    {oficio.pcd if oficio.pcd is not None else "NULL"},
    CURRENT_TIMESTAMP
)
ON CONFLICT (cpf, numero_processo) DO UPDATE SET
    valor_principal_liquido = EXCLUDED.valor_principal_liquido,
    valor_principal_bruto = EXCLUDED.valor_principal_bruto,
    juros_moratorios = EXCLUDED.juros_moratorios,
    valor_total_requisitado = EXCLUDED.valor_total_requisitado,
    timestamp_processamento = CURRENT_TIMESTAMP;
"""
        return sql
    
    def _gerar_comparacao(self, oficio: OficioRequisitorio) -> str:
        """Gera tabela de comparação com valores corretos"""
        
        # Valores corretos do PDF
        valores_corretos = {
            "valor_principal_liquido": Decimal("88994.41"),
            "valor_principal_bruto": Decimal("88994.41"),
            "juros_moratorios": Decimal("0.00"),
            "valor_total_requisitado": Decimal("88994.41"),
        }
        
        # Valores extraídos
        valores_extraidos = {
            "valor_principal_liquido": oficio.valor_principal_liquido,
            "valor_principal_bruto": oficio.valor_principal_bruto,
            "juros_moratorios": oficio.juros_moratorios,
            "valor_total_requisitado": oficio.valor_total_requisitado,
        }
        
        comparacao = "\n" + "="*100 + "\n"
        comparacao += "COMPARAÇÃO: Valores Corretos vs Valores Extraídos\n"
        comparacao += "="*100 + "\n\n"
        comparacao += f"{'Campo':<35} {'Correto (PDF)':<20} {'Extraído':<20} {'Status':<10}\n"
        comparacao += "-"*100 + "\n"
        
        for campo, valor_correto in valores_corretos.items():
            valor_extraido = valores_extraidos[campo]
            
            if valor_extraido is None:
                status = "❌ NULL"
                diferenca = ""
            elif valor_extraido == valor_correto:
                status = "✅ OK"
                diferenca = ""
            else:
                status = "❌ ERRO"
                diff = valor_extraido - valor_correto if valor_extraido else -valor_correto
                diferenca = f" (diff: {diff:+,.2f})"
            
            comparacao += f"{campo:<35} R$ {float(valor_correto):>15,.2f}  "
            comparacao += f"R$ {float(valor_extraido) if valor_extraido else 0:>15,.2f}  "
            comparacao += f"{status:<10}{diferenca}\n"
        
        comparacao += "="*100 + "\n"
        
        return comparacao


def main():
    """Função principal"""
    print("\n" + "="*80)
    print("🐛 TESTE DE DEBUG: Bug de Parsing de Valores")
    print("="*80 + "\n")
    
    # Configurar caminhos
    base_dir = Path(__file__).parent.parent
    pdf_path = base_dir / "test_data" / "Precatório-RAF.pdf"
    cpf = "27308157830"
    
    # Verificar se PDF existe
    if not pdf_path.exists():
        print(f"❌ ERRO: PDF não encontrado: {pdf_path}")
        return
    
    # Verificar API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERRO: OPENAI_API_KEY não configurada no .env")
        return
    
    # Inicializar e executar teste
    try:
        tester = TestProcessadorLocal()
        tester.processar_pdf_debug(str(pdf_path), cpf)
        
        print("\n✅ Teste concluído com sucesso!")
        print(f"📁 Verifique os outputs em: {base_dir / 'test_outputs'}")
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

