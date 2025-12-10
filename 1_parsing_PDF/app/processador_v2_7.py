"""
ProcessadorOficioV27 - V2.7.0: REGEX-first processing pipeline.

MAJOR OPTIMIZATION:
- Extract 45/53 fields (85%) via REGEX first
- LLM reserved for only 8 complex fields
- Expected gains: -80% cost, -70% time, +25% accuracy

ARCHITECTURE CHANGE:
V2.6.1: LLM-first (all 53 fields) → Regex merge (8 fields)
V2.7.0: REGEX-first (45 fields) → LLM selective (8 fields) → Merge

VERSION: V2.7.0
DATE: 2025-12-10
"""

import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

from .processador import ProcessadorOficio
from .detector_anexo_v2_7 import DetectorAnexoIIV27

logger = logging.getLogger(__name__)


class ProcessadorOficioV27(ProcessadorOficio):
    """
    V2.7.0: Optimized processor with REGEX-first extraction.

    Inherits all V2.6.1 functionality and overrides key methods:
    - __init__: Uses DetectorAnexoIIV27 instead of DetectorAnexoII
    - processar_arquivo: Calls comprehensive regex extraction first
    - _extrair_dados_llm_seletivo: Only requests 8 fields from LLM
    - _construir_prompt_llm_seletivo: Minimal prompt for missing fields

    WORKFLOW:
    1. Detect ofício, ANEXO II, PROCESSAMENTO (same as V2.6.1)
    2. Extract ALL fields via REGEX (NEW: 45 fields)
    3. Identify which fields are still missing
    4. Request ONLY missing fields from LLM (NEW: selective)
    5. Merge REGEX + LLM data (REGEX priority)
    6. Validate with Pydantic
    """

    def __init__(self, openai_api_key: str, db_config: Dict[str, Any]):
        """
        Initialize V2.7.0 processor.

        Args:
            openai_api_key: OpenAI API key
            db_config: PostgreSQL database configuration
        """
        # Call parent constructor
        super().__init__(openai_api_key, db_config)

        # Replace detector with V2.7.0 version
        self.detector_anexo = DetectorAnexoIIV27()

        logger.info("=" * 80)
        logger.info("🚀 ProcessadorOficioV27 initialized (REGEX-first)")
        logger.info("=" * 80)
        logger.info("✅ V2.7.0: Comprehensive REGEX extraction (45 fields)")
        logger.info("✅ V2.7.0: Selective LLM requests (8 fields only)")
        logger.info("✅ V2.7.0: Expected gains: -80% cost, -70% time, +25% accuracy")
        logger.info("=" * 80)

    def processar_arquivo(self, pdf_path: str, cpf_numerico: str, tracker: Optional = None) -> Dict[str, Any]:
        """
        Process PDF with V2.7.0 REGEX-first approach.

        CHANGES from V2.6.1:
        - Calls pre_extrair_dados_completo() for 45 fields
        - Identifies missing fields
        - Sends only missing fields to LLM
        - Merges with REGEX priority

        Args:
            pdf_path: Path to PDF file
            cpf_numerico: Expected CPF (numbers only)
            tracker: Optional execution tracker

        Returns:
            Dict with processing result
        """
        inicio = time.time()

        try:
            logger.info(f"🔄 Iniciando processamento V2.7.0: {pdf_path}")

            # === V2.7.0 IMPROVEMENT 1: Validate file exists ===
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                logger.error(f"❌ Arquivo não encontrado: {pdf_path}")
                return {
                    'cpf': cpf_numerico,
                    'pdf': pdf_path_obj.name,
                    'sucesso': False,
                    'cpf_validado': False,
                    'erro': f"Arquivo não encontrado: {pdf_path_obj.name}",
                    'anomalia': True,
                    'descricao_anomalia': f"Arquivo não encontrado no momento do processamento: {pdf_path_obj.name}",
                    'tempo_processamento': time.time() - inicio,
                    'num_oficios': 0
                }

            # === PHASE 1-6: Same as V2.6.1 (ofício detection, ANEXO II, PROCESSAMENTO) ===
            # Call parent method to handle detection
            # But we'll override the extraction part

            # For now, let's extract up to the point where we have texto_anexo
            # Then we'll do REGEX-first extraction

            # 1. Validate PDF
            if not self.detector.validar_pdf(pdf_path):
                logger.error(f"❌ PDF inválido: {pdf_path}")
                return None

            # 2. Extract CPF from folder
            cpf_numerico = self._extrair_cpf_pasta(pdf_path)
            if not cpf_numerico:
                logger.error(f"❌ CPF inválido na pasta: {Path(pdf_path).parent.name}")
                return None

            cpf_formatado = self._formatar_cpf(cpf_numerico)
            logger.info(f"📋 CPF esperado: {cpf_formatado}")

            # 3. Find all ofícios
            todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
            if not todos_oficios:
                logger.warning("⚠️ Nenhum ofício detectado no PDF")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    "Nenhum ofício detectado"
                )

            logger.info(f"📄 Encontrados {len(todos_oficios)} ofício(s) no PDF")

            # 4. Find correct ofício with CPF
            oficio_correto = None
            for idx, oficio in enumerate(todos_oficios, 1):
                logger.info(f"🔍 Verificando ofício {idx}/{len(todos_oficios)}")

                if self.detector.validar_cpf_no_oficio(oficio['texto'], cpf_formatado):
                    logger.info(f"✅ CPF encontrado no ofício {idx}!")
                    oficio_correto = oficio
                    break

            if not oficio_correto:
                logger.warning(f"⚠️ CPF {cpf_formatado} não encontrado em nenhum ofício")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    f"CPF {cpf_formatado} não encontrado"
                )

            # 5. Detect ANEXO II
            ultima_pag_oficio = oficio_correto['paginas'][-1]
            paginas_anexo, texto_anexo, pagina_titulo_anexo = self.detector_anexo.detectar_anexo_ii(
                pdf_path,
                inicio=ultima_pag_oficio
            )

            # 6. Extract creditor section from ANEXO II
            secao_credor = ""
            if pagina_titulo_anexo >= 0:
                pagina_credor = self.detector.buscar_cpf_no_pdf(
                    pdf_path,
                    cpf_formatado,
                    inicio=pagina_titulo_anexo
                )

                if pagina_credor >= 0:
                    logger.info(f"✅ CPF encontrado na página {pagina_credor + 1}")
                    secao_credor = self.detector_anexo.extrair_secao_credor_no_anexo(
                        pdf_path,
                        pagina_credor,
                        cpf_formatado
                    )

                    if secao_credor:
                        logger.info(f"✅ Seção do credor extraída ({len(secao_credor)} chars)")
                        texto_anexo = secao_credor

            # === V2.7.0 IMPROVEMENT 2: Detect old PDFs without ANEXO II ===
            nome_arquivo = Path(pdf_path).name
            processo_numero = nome_arquivo.replace('.pdf', '')
            pdf_antigo = processo_numero.startswith('7')

            if pdf_antigo and not texto_anexo:
                logger.warning("=" * 80)
                logger.warning("⚠️ V2.7.0: PDF ANTIGO SEM ANEXO II DETECTADO")
                logger.warning(f"   Processo: {processo_numero}")
                logger.warning("   Este PDF será marcado como ANOMALIA")
                logger.warning("   Requer processamento manual especializado")
                logger.warning("=" * 80)

            # === PHASE 7 (NEW): COMPREHENSIVE REGEX EXTRACTION ===
            logger.info("=" * 80)
            logger.info("🔍 V2.7.0: PHASE 7 - COMPREHENSIVE REGEX EXTRACTION")
            logger.info("=" * 80)

            dados_regex = {}
            if texto_anexo and secao_credor:
                logger.info(f"📋 Extraindo TODOS os campos via REGEX...")
                tempo_regex_inicio = time.time()

                # Call V2.7.0 comprehensive extraction
                dados_regex = self.detector_anexo.pre_extrair_dados_completo(texto_anexo)

                tempo_regex = time.time() - tempo_regex_inicio
                campos_regex = len([v for v in dados_regex.values() if v is not None])
                logger.info(f"✅ REGEX extraction complete: {campos_regex} fields in {tempo_regex:.2f}s")
                logger.info(f"   Success rate: {campos_regex}/45 = {100*campos_regex/45:.1f}%")
            else:
                logger.warning("⚠️ ANEXO II não encontrado, pulando extração REGEX")

            # === PHASE 8 (NEW): IDENTIFY MISSING FIELDS ===
            logger.info("=" * 80)
            logger.info("🔍 V2.7.0: PHASE 8 - IDENTIFY MISSING FIELDS")
            logger.info("=" * 80)

            campos_faltantes = self._identificar_campos_faltantes(dados_regex)
            logger.info(f"📋 {len(campos_faltantes)} campos ainda faltantes:")
            for campo in campos_faltantes:
                logger.info(f"   - {campo}")

            # === PHASE 9 (NEW): SELECTIVE LLM EXTRACTION ===
            logger.info("=" * 80)
            logger.info("🔍 V2.7.0: PHASE 9 - SELECTIVE LLM EXTRACTION")
            logger.info("=" * 80)

            dados_llm = {}
            if campos_faltantes:
                logger.info(f"🤖 Requesting {len(campos_faltantes)} missing fields from LLM...")

                # Build full text (ofício + ANEXO II)
                texto_relevante = oficio_correto['texto']
                if texto_anexo:
                    texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"

                tempo_llm_inicio = time.time()
                dados_llm = self._extrair_dados_llm_seletivo(
                    texto_relevante,
                    campos_faltantes
                )
                tempo_llm = time.time() - tempo_llm_inicio

                if dados_llm:
                    campos_llm = len([v for v in dados_llm.values() if v is not None])
                    logger.info(f"✅ LLM extraction complete: {campos_llm} fields in {tempo_llm:.2f}s")
                else:
                    logger.warning("⚠️ LLM extraction failed")
            else:
                logger.info("✅ All fields extracted via REGEX, skipping LLM!")

            # === PHASE 10: MERGE REGEX + LLM (REGEX PRIORITY) ===
            logger.info("=" * 80)
            logger.info("🔍 V2.7.0: PHASE 10 - MERGE DATA")
            logger.info("=" * 80)

            dados_finais = self._mesclar_dados(dados_regex, dados_llm)
            campos_totais = len([v for v in dados_finais.values() if v is not None])
            logger.info(f"✅ Final data: {campos_totais} fields filled")
            logger.info(f"   REGEX: {len([v for v in dados_regex.values() if v is not None])} fields")
            logger.info(f"   LLM: {len([v for v in dados_llm.values() if v is not None])} fields")

            # === V2.7.0 IMPROVEMENT 3: Mark old PDFs without ANEXO II as anomaly ===
            if pdf_antigo and not texto_anexo:
                tamanho_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
                dados_finais['anomalia'] = True
                dados_finais['descricao_anomalia'] = (
                    f"PDF antigo (2007, formato 7xxxxxx) com {tamanho_mb:.1f} MB e "
                    f"{len(doc_paginas) if 'doc_paginas' in locals() else 'múltiplas'} páginas. "
                    f"Multi-creditor com {len(todos_oficios)} ofícios. "
                    f"ANEXO II não encontrado (formato antigo incompatível). "
                    f"Requer processamento manual especializado para PDFs antigos."
                )
                logger.warning(f"⚠️ Anomalia adicionada: {dados_finais['descricao_anomalia']}")

            # === PHASE 11: VALIDATE WITH PYDANTIC ===
            logger.info("=" * 80)
            logger.info("🔍 V2.7.0: PHASE 11 - VALIDATION")
            logger.info("=" * 80)

            from .schemas import OficioRequisitorio
            try:
                oficio_validado = OficioRequisitorio(**dados_finais)
                logger.info("✅ Dados validados com sucesso")
            except Exception as e:
                # === V2.7.0 IMPROVEMENT 4: Better ValidationError logging ===
                from pydantic import ValidationError
                if isinstance(e, ValidationError):
                    logger.error(f"❌ Erro na validação Pydantic:")
                    logger.error(f"   Tipo: {type(e).__name__}")
                    for error in e.errors():
                        campo = " -> ".join(str(loc) for loc in error['loc'])
                        msg = error['msg']
                        tipo = error['type']
                        logger.error(f"   Campo: {campo}")
                        logger.error(f"   Erro: {msg} (tipo: {tipo})")
                        if 'input' in error:
                            logger.error(f"   Valor recebido: {error['input']}")
                else:
                    logger.error(f"❌ Erro na validação: {type(e).__name__}: {e}")

                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    f"Validação falhou: {type(e).__name__}: {str(e)}"
                )

            # === PHASE 12: SAVE TO DATABASE ===
            tempo_total = time.time() - inicio
            logger.info("=" * 80)
            logger.info(f"✅ V2.7.0: PROCESSING COMPLETE in {tempo_total:.2f}s")
            logger.info("=" * 80)

            # Convert to dict and return (save will be handled by caller)
            dados_dict = oficio_validado.model_dump(mode='json')

            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": True,
                "cpf_validado": True,
                "dados": dados_dict,
                "tempo_processamento": tempo_total,
                "num_oficios": len(todos_oficios),
                "campos_regex": len([v for v in dados_regex.values() if v is not None]),
                "campos_llm": len([v for v in dados_llm.values() if v is not None]),
                "campos_totais": campos_totais
            }

        except Exception as e:
            logger.error(f"❌ Erro no processamento V2.7.0: {e}")
            import traceback
            traceback.print_exc()
            return self._criar_resultado_erro(
                cpf_numerico,
                pdf_path,
                f"Erro inesperado: {str(e)}"
            )

    def _identificar_campos_faltantes(self, dados_regex: Dict) -> list:
        """
        Identify which fields are still missing after REGEX extraction.

        V2.7.0: Only 8 complex fields typically need LLM:
        1. processo_origem (variable format)
        2. requerente_caps (variable position)
        3. advogado_nome (multiple sections)
        4. advogado_oab (multiple sections)
        5. motivo_rejeicao (free text)
        6. processo_execucao (rare)
        7. processo_conhecimento (rare)
        8. devedor_ente (rare)

        Args:
            dados_regex: Dict with fields extracted via regex

        Returns:
            List of field names still missing
        """
        # All 53 fields from schema
        todos_campos = [
            'processo_origem', 'requerente_caps', 'numero_ordem',
            'vara', 'processo_execucao', 'processo_conhecimento',
            'data_ajuizamento', 'data_transito_julgado', 'data_base_atualizacao',
            'advogado_nome', 'advogado_oab',
            'credor_nome', 'credor_cpf_cnpj', 'devedor_ente',
            'banco', 'agencia', 'conta', 'conta_tipo',
            'anexo_ii',
            'valor_principal_liquido', 'valor_principal_bruto',
            'juros_moratorios', 'valor_total_requisitado', 'saldo_final',
            'contrib_previdenciaria_iprem', 'contrib_previdenciaria_hspm',
            'idoso', 'doenca_grave', 'pcd', 'preferencial',
            'habilitacao_herdeiros', 'cessao_credito',
            'obito', 'data_obito', 'cpf_sucessor',
            'rejeitado', 'motivo_rejeicao',
            'observacoes', 'anomalia', 'descricao_anomalia',
            'tipo_levantamento', 'dados_bancarios_advogado', 'cpf_titular_conta',
            'data_nascimento',
            'valor_compensado', 'contribuicao_social',
            'salario_pericial', 'assist_tecnico', 'custas', 'despesas', 'multas'
        ]

        faltantes = []
        for campo in todos_campos:
            valor = dados_regex.get(campo)
            if valor is None or valor == '' or valor == []:
                faltantes.append(campo)

        return faltantes

    def _extrair_dados_llm_seletivo(
        self,
        texto_oficio: str,
        campos_faltantes: list
    ) -> Optional[Dict[str, Any]]:
        """
        Extract ONLY missing fields from LLM.

        V2.7.0: Selective extraction instead of requesting all 53 fields.

        Args:
            texto_oficio: Full text (ofício + ANEXO II)
            campos_faltantes: List of field names to extract

        Returns:
            Dict with only requested fields
        """
        if not campos_faltantes:
            return {}

        # Build minimal prompt
        prompt = self._construir_prompt_llm_seletivo(texto_oficio, campos_faltantes)

        # Use LLM adapter (Gemini primary, OpenAI fallback)
        if hasattr(self, 'llm_adapter') and self.llm_adapter:
            try:
                logger.info(f"🤖 Gemini: Extracting {len(campos_faltantes)} missing fields...")
                dados = self.llm_adapter.extract_structured_data(
                    prompt,
                    provider=self.llm_provider_enum.GEMINI
                )
                return dados
            except Exception as e:
                logger.warning(f"⚠️ Gemini failed: {e}, trying OpenAI fallback...")
                try:
                    dados = self.llm_adapter.extract_structured_data(
                        prompt,
                        provider=self.llm_provider_enum.OPENAI
                    )
                    return dados
                except Exception as e2:
                    logger.error(f"❌ OpenAI fallback also failed: {e2}")
                    return {}
        else:
            # Fallback to legacy OpenAI
            try:
                logger.info(f"🤖 OpenAI: Extracting {len(campos_faltantes)} missing fields...")
                response = self.client.chat.completions.create(
                    model=self.modelo_gpt,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                import json
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"❌ OpenAI extraction failed: {e}")
                return {}

    def _construir_prompt_llm_seletivo(
        self,
        texto_oficio: str,
        campos_faltantes: list
    ) -> str:
        """
        Build minimal prompt requesting ONLY missing fields.

        V2.7.0: Dramatically smaller prompt (8 fields vs 53 fields).

        Args:
            texto_oficio: Full text
            campos_faltantes: List of field names to extract

        Returns:
            Minimal prompt string
        """
        # Build field descriptions with explicit types
        descricoes = {
            # Strings
            'processo_origem': '(string) Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)',
            'requerente_caps': '(string) Nome TODO EM MAIÚSCULAS',
            'numero_ordem': '(string) Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)',
            'advogado_nome': '(string) Nome do advogado',
            'advogado_oab': '(string) OAB do advogado (formato: OAB/SP XXX.XXX)',
            'motivo_rejeicao': '(string) Motivo da rejeição (se rejeitado)',
            'processo_execucao': '(string) Número do processo de execução',
            'processo_conhecimento': '(string) Número do processo de conhecimento',
            'devedor_ente': '(string) Nome do ente devedor (ex: Município de São Paulo)',
            'vara': '(string) Vara responsável pelo processo',
            'observacoes': '(string) Observações relevantes sobre o processamento. Use este campo para documentar informações importantes como "Parte não possui conta bancária" ou outras particularidades',
            'descricao_anomalia': '(string) Descrição da anomalia (se houver)',
            'data_ajuizamento': '(string) Data de ajuizamento no formato ISO YYYY-MM-DD',
            'data_transito_julgado': '(string) Data de trânsito em julgado no formato ISO YYYY-MM-DD',
            'cpf_titular_conta': '(string) CPF do titular da conta (somente números)',
            'cpf_sucessor': '(string) CPF do sucessor em caso de óbito (somente números)',
            'data_obito': '(string) Data de óbito no formato ISO YYYY-MM-DD',

            # Booleans (NEVER strings!)
            'anomalia': '(boolean) true se documento tem formato anômalo, false caso contrário',
            'rejeitado': '(boolean) true se ofício foi rejeitado, false caso contrário',
            'dados_bancarios_advogado': '(boolean) true se os dados bancários são do advogado, false se são do credor',
            'pcd': '(boolean) true se pessoa com deficiência, false caso contrário',
            'cessao_credito': '(boolean) true se houve cessão de crédito, false caso contrário',

            # Numbers
            'valor_principal_liquido': '(number) Valor principal líquido em formato numérico (ex: 12345.67)',
            'valor_principal_bruto': '(number) Valor principal bruto em formato numérico',
            'contrib_previdenciaria_iprem': '(number) Contribuição IPREM em formato numérico',
            'contrib_previdenciaria_hspm': '(number) Contribuição HSPM em formato numérico',
            'valor_compensado': '(number) Valor compensado em formato numérico',
            'contribuicao_social': '(number) Contribuição social em formato numérico',
            'assist_tecnico': '(number) Honorários de assistente técnico em formato numérico',

            # Object (dict) - NEVER a string!
            'anexo_ii': '(object) Objeto JSON vazio {} - NÃO copie o texto do ANEXO II aqui!'
        }

        # Build field list
        campos_str = ""
        for campo in campos_faltantes:
            desc = descricoes.get(campo, f'{campo} (extrair do documento)')
            campos_str += f"- {campo}: {desc}\n"

        prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com TIPOS CORRETOS! Veja exemplos abaixo.

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS A EXTRAIR ===

{campos_str}

=== REGRAS GERAIS DE RESPOSTA (CRÍTICO!) ===

🚨 NUNCA RETORNE MENSAGENS DESCRITIVAS NOS CAMPOS DE DADOS! 🚨

✅ CORRETO: Use null quando não encontrar um campo
   "conta_tipo": null
   "advogado_nome": null
   "vara": null

❌ ERRADO: NUNCA escreva mensagens explicativas nos campos
   "conta_tipo": "Parte não possui conta bancária" ← PROIBIDO!
   "advogado_nome": "Não informado" ← PROIBIDO!
   "vara": "Não consta no documento" ← PROIBIDO!

📝 Se precisar explicar algo, use o campo "observacoes":
   "conta_tipo": null,
   "observacoes": "Parte não possui conta bancária conforme página 93"

=== REGRAS DE TIPOS (CRÍTICO!) ===

1. STRINGS: Use aspas duplas (max 20 caracteres para campos curtos)
   Exemplo: "processo_origem": "0137444-93.2024.8.26.0500"
   Exemplo: "requerente_caps": "ROBERTO FURIAN"
   Exemplo: "data_ajuizamento": "2024-05-18"
   Exemplo: "conta_tipo": "Corrente" (OU null se não houver)

2. BOOLEANS: Use true/false SEM aspas (NUNCA use "Sim"/"Não")
   Exemplo: "dados_bancarios_advogado": true
   Exemplo: "anomalia": false
   Exemplo: "rejeitado": false

3. NUMBERS: Use números SEM aspas
   Exemplo: "valor_principal_liquido": 122125.03
   Exemplo: "contrib_previdenciaria_iprem": 13433.89

4. OBJECTS: Use chaves {{}} (NUNCA copie texto para dentro do objeto!)
   Exemplo: "anexo_ii": {{}}

5. NULL: Se campo não existe, use null (sem aspas)
   Exemplo: "data_obito": null
   Exemplo: "conta_tipo": null
   Exemplo: "cpf_sucessor": null

=== ERROS COMUNS A EVITAR ===

❌ ERRADO: "dados_bancarios_advogado": "Banco: 001 Agência: 6815"
✅ CORRETO: "dados_bancarios_advogado": true

❌ ERRADO: "anexo_ii": "Credor nº: 1 Nome: FULANO..."
✅ CORRETO: "anexo_ii": {{}}

❌ ERRADO: "anomalia": "Não"
✅ CORRETO: "anomalia": false

❌ ERRADO: "valor_principal_liquido": "122125.03"
✅ CORRETO: "valor_principal_liquido": 122125.03

❌ ERRADO: "conta_tipo": "Parte não possui conta bancária"
✅ CORRETO: "conta_tipo": null, "observacoes": "Parte sem conta bancária"

=== DOCUMENTO ===

{texto_oficio[:100000]}

=== RESPOSTA (JSON COM TIPOS CORRETOS) ===
"""

        return prompt

    def _sanitizar_strings_longas(self, dados: Dict) -> Dict:
        """
        Sanitize long strings that exceed Pydantic limits.

        V2.7.0: Defense-in-depth - move descriptive messages to 'observacoes' field.

        Args:
            dados: Merged data dict

        Returns:
            Sanitized dict
        """
        # Short string fields (max 20 chars)
        campos_curtos = ['conta_tipo']

        # Track sanitized fields for observacoes
        sanitizacoes = []

        for campo in campos_curtos:
            if campo in dados and isinstance(dados[campo], str):
                valor_original = dados[campo]
                if len(valor_original) > 20:
                    # Move to observacoes
                    msg = f"{campo}: {valor_original}"
                    sanitizacoes.append(msg)
                    dados[campo] = None
                    logger.warning(f"⚠️ Sanitização: {campo} com {len(valor_original)} chars → movido para observacoes")

        # Append to observacoes if sanitization occurred
        if sanitizacoes:
            obs_atual = dados.get('observacoes', '')
            obs_nova = '; '.join(sanitizacoes)
            dados['observacoes'] = f"{obs_atual}; {obs_nova}" if obs_atual else obs_nova

        return dados

    def _mesclar_dados(self, dados_regex: Dict, dados_llm: Dict) -> Dict:
        """
        Merge REGEX and LLM data with REGEX priority.

        V2.7.0: REGEX data is more reliable, so it takes priority.

        Args:
            dados_regex: Fields extracted via regex
            dados_llm: Fields extracted via LLM

        Returns:
            Merged dict
        """
        # Start with LLM data
        dados_finais = dados_llm.copy()

        # Overwrite with REGEX data (higher priority)
        for campo, valor in dados_regex.items():
            if valor is not None and valor != '' and valor != []:
                dados_finais[campo] = valor
                logger.debug(f"   ✅ {campo}: usando valor REGEX")

        # Sanitize long strings (defense-in-depth)
        dados_finais = self._sanitizar_strings_longas(dados_finais)

        return dados_finais
