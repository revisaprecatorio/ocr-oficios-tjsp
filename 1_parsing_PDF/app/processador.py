"""
ProcessadorOficio V2 - Pipeline otimizado com validação de CPF e extração seletiva.
Versão 2.0 - Processa apenas páginas relevantes, valida CPF, extrai número de ordem
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import pymupdf
from openai import OpenAI

from .detector import DetectorOficio
from .detector_anexo import DetectorAnexoII
from .detector_processamento import DetectorProcessamento
from .schemas import OficioRequisitorio

logger = logging.getLogger(__name__)


class ProcessadorOficio:
    """
    Pipeline V2 para processamento de Ofícios Requisitórios:
    1. Buscar TODOS os ofícios no PDF
    2. Validar CPF em cada ofício
    3. Processar apenas o ofício correto
    4. Detectar ANEXO II e PROCESSAMENTO
    5. Extrair dados estruturados (GPT-4o-mini) - APENAS páginas relevantes
    6. Validar dados (Pydantic)
    7. Salvar no PostgreSQL (upsert)
    """
    
    def __init__(self, openai_api_key: str, db_config: Dict[str, Any]):
        """
        Inicializa o processador V2.
        
        Args:
            openai_api_key: Chave da API OpenAI
            db_config: Configurações do banco PostgreSQL
        """
        # Inicializar OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        self.modelo_gpt = "gpt-4o-mini"
        
        # Configurações do banco
        self.db_config = db_config
        
        # Inicializar detectores V2
        self.detector = DetectorOficio()
        self.detector_anexo = DetectorAnexoII()
        self.detector_proc = DetectorProcessamento()  # NOVO!

        logger.info("ProcessadorOficio V2 inicializado")
    
    def processar_arquivo(self, pdf_path: str, cpf_numerico: str) -> Dict[str, Any]:
        """
        Processa um único arquivo PDF com validação de CPF.
        
        V2: Busca todos os ofícios, valida CPF, processa apenas o correto.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            cpf_numerico: CPF esperado (apenas números)
            
        Returns:
            Dict com resultado do processamento
        """
        inicio = time.time()
        
        try:
            logger.info(f"🔄 Iniciando processamento V2: {pdf_path}")
            
            # Validar arquivo PDF
            if not self.detector.validar_pdf(pdf_path):
                logger.error(f"❌ PDF inválido: {pdf_path}")
                return None
            
            # 1. Extrair CPF da pasta
            cpf_numerico = self._extrair_cpf_pasta(pdf_path)
            if not cpf_numerico:
                logger.error(f"❌ CPF inválido na pasta: {Path(pdf_path).parent.name}")
                return None
            
            cpf_formatado = self._formatar_cpf(cpf_numerico)
            logger.info(f"📋 CPF esperado: {cpf_formatado}")
            
            # 2. Buscar TODOS os ofícios no PDF
            todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
            
            if not todos_oficios:
                logger.warning("⚠️ Nenhum ofício encontrado no PDF")
                return self._criar_resultado_erro(
                    cpf_numerico, 
                    pdf_path, 
                    "Nenhum ofício detectado"
                )
            
            logger.info(f"📄 Encontrados {len(todos_oficios)} ofício(s) no PDF")
            
            # 3. Encontrar ofício com CPF correto
            oficio_correto = None
            for idx, oficio in enumerate(todos_oficios, 1):
                logger.info(f"🔍 Verificando ofício {idx}/{len(todos_oficios)} (páginas {oficio['paginas']})")
                
                if self.detector.validar_cpf_no_oficio(oficio['texto'], cpf_formatado):
                    logger.info(f"✅ CPF encontrado no ofício {idx}!")
                    oficio_correto = oficio
                    break
                else:
                    logger.info(f"❌ CPF não encontrado no ofício {idx}")
            
            if not oficio_correto:
                logger.warning(f"⚠️ CPF {cpf_formatado} não encontrado em nenhum ofício")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    f"CPF {cpf_formatado} não encontrado (PDF tem {len(todos_oficios)} ofício(s))"
                )
            
            # 4. Detectar ANEXO II (após ofício correto)
            ultima_pag_oficio = oficio_correto['paginas'][-1]
            paginas_anexo, texto_anexo = self.detector_anexo.detectar_anexo_ii(pdf_path)
            
            # 5. Tentar extrair número de ordem do TÍTULO do ofício (PDFs antigos)
            numero_ordem_titulo = self.detector_proc.extrair_numero_ordem_do_titulo(
                oficio_correto['texto']
            )
            
            # 6. Detectar PROCESSAMENTO (PDFs novos) - buscar em mais páginas
            inicio_proc = paginas_anexo[-1] - 1 if paginas_anexo else ultima_pag_oficio - 1
            pagina_proc, texto_proc = self.detector_proc.detectar_processamento(
                pdf_path,
                inicio=inicio_proc,
                limite=100  # Aumentar limite de busca
            )
            
            # 6.1. Verificar se ofício foi REJEITADO (ANTES de validar!)
            # 🔴 REGRA CRÍTICA: Verificar ACEITAÇÃO primeiro (prioridade máxima)
            oficio_rejeitado = False
            motivo_rejeicao = None
            tem_processamento_com_informacao = False
            tem_numero_ordem = False
            
            # Verificar se tem PROCESSAMENTO COM INFORMAÇÃO ou número de ordem
            if texto_proc:
                texto_upper = texto_proc.upper()
                if "PROCESSAMENTO COM INFORMAÇÃO" in texto_upper or "PROCESSAMENTO COM INFORMACAO" in texto_upper:
                    tem_processamento_com_informacao = True
                    logger.info("✅ PROCESSAMENTO COM INFORMAÇÃO detectado → Ofício ACEITO")
                
                if self.detector_proc.extrair_numero_ordem(texto_proc):
                    tem_numero_ordem = True
                    logger.info("✅ Número de ordem detectado → Ofício ACEITO")
            
            # 🔴 PRIORIDADE: Se tem PROCESSAMENTO COM INFORMAÇÃO ou número de ordem → NÃO é rejeitado
            if tem_processamento_com_informacao or tem_numero_ordem:
                oficio_rejeitado = False
                logger.info("✅ Ofício ACEITO (tem PROCESSAMENTO COM INFORMAÇÃO ou número de ordem)")
            else:
                # Só verificar rejeição se NÃO tem indicadores de aceitação
                # Buscar rejeição no texto do PROCESSAMENTO ou em páginas próximas
                if texto_proc and self.detector_proc.eh_oficio_rejeitado(texto_proc):
                    oficio_rejeitado = True
                    motivo_rejeicao = self.detector_proc.extrair_motivo_rejeicao(texto_proc)
                    logger.warning(f"⚠️ OFÍCIO REJEITADO detectado na página {pagina_proc}!")
                    if motivo_rejeicao:
                        logger.info(f"   Motivo: {motivo_rejeicao[:100]}...")
                else:
                    # Buscar rejeição em páginas próximas ao ofício
                    logger.debug("Buscando NOTA DE REJEIÇÃO em páginas próximas...")
                    for pag_offset in range(0, 50):
                        pag_busca = ultima_pag_oficio + pag_offset
                        try:
                            doc = pymupdf.open(pdf_path)
                            if pag_busca < len(doc):
                                texto_busca = doc.load_page(pag_busca).get_text()
                                if self.detector_proc.eh_oficio_rejeitado(texto_busca):
                                    oficio_rejeitado = True
                                    motivo_rejeicao = self.detector_proc.extrair_motivo_rejeicao(texto_busca)
                                    logger.warning(f"⚠️ OFÍCIO REJEITADO detectado na página {pag_busca + 1}!")
                                    if motivo_rejeicao:
                                        logger.info(f"   Motivo: {motivo_rejeicao[:100]}...")
                                    # Usar esse texto como PROCESSAMENTO
                                    if not texto_proc:
                                        texto_proc = texto_busca
                                        pagina_proc = pag_busca
                                    break
                            doc.close()
                        except Exception as e:
                            logger.debug(f"Erro ao buscar rejeição na página {pag_busca}: {e}")
                        break
            
            # 7. Montar texto relevante (APENAS páginas necessárias!)
            # CHUNKING: Se ofício muito grande SEM ANEXO II/PROCESSAMENTO, reduzir
            paginas_oficio = oficio_correto['paginas']
            num_paginas = len(paginas_oficio)
            
            if num_paginas > 100 and not texto_anexo and not texto_proc:
                logger.warning(f"⚠️ Ofício muito grande ({num_paginas} páginas) sem ANEXO II/PROCESSAMENTO")
                logger.info(f"🔧 Aplicando CHUNKING: primeiras 50 + últimas 50 páginas")
                
                # Extrair apenas primeiras 50 + últimas 50 páginas
                paginas_chunk = paginas_oficio[:50] + paginas_oficio[-50:]
                
                # Re-extrair texto apenas dessas páginas
                doc = pymupdf.open(pdf_path)
                texto_chunk = ""
                for pag in paginas_chunk:
                    texto_chunk += doc.load_page(pag).get_text() + "\n"
                doc.close()
                
                texto_relevante = texto_chunk
                logger.info(f"📄 Texto reduzido: {len(texto_relevante):,} chars (100 páginas)")
            else:
                texto_relevante = oficio_correto['texto']
            
            if texto_anexo:
                logger.info(f"📋 ANEXO II encontrado em {len(paginas_anexo)} página(s)")
                texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
            else:
                logger.warning("⚠️ ANEXO II não encontrado")
            
            if texto_proc:
                if oficio_rejeitado:
                    logger.info(f"📋 NOTA DE REJEIÇÃO encontrada na página {pagina_proc}")
                    texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_proc}"
                else:
                    logger.info(f"📋 PROCESSAMENTO encontrado na página {pagina_proc}")
                    texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
            elif numero_ordem_titulo:
                logger.info(f"📋 Número de ordem extraído do TÍTULO: {numero_ordem_titulo}")
            else:
                logger.warning("⚠️ PROCESSAMENTO não encontrado e número não está no título")
            
            # 8. Verificar tamanho e aplicar chunking adicional se necessário
            # Estimativa conservadora: 1 token ≈ 2 chars (português), limite 128k tokens ≈ 256k chars
            # Deixar margem de segurança: 200k chars
            MAX_CHARS = 200_000
            
            if len(texto_relevante) > MAX_CHARS:
                logger.warning(f"⚠️ Texto muito grande ({len(texto_relevante):,} chars > {MAX_CHARS:,})")
                logger.info(f"🔧 Aplicando CHUNKING AGRESSIVO: primeiras 30 + últimas 30 páginas do ofício")
                
                # Re-extrair com chunking mais agressivo
                paginas_chunk = paginas_oficio[:30] + paginas_oficio[-30:]
                
                doc = pymupdf.open(pdf_path)
                texto_chunk = ""
                for pag in paginas_chunk:
                    texto_chunk += doc.load_page(pag).get_text() + "\n"
                doc.close()
                
                texto_relevante = texto_chunk
                
                # Re-adicionar ANEXO II e PROCESSAMENTO (se houver)
                if texto_anexo:
                    texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
                if texto_proc:
                    if oficio_rejeitado:
                        texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_proc}"
                    else:
                        texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
                
                logger.info(f"📄 Texto reduzido: {len(texto_relevante):,} chars (60 páginas + anexos)")
            
            # 9. Enviar ao LLM com Modo Híbrido (Gemini + OpenAI fallback)
            logger.info(f"🤖 Enviando {len(texto_relevante):,} chars para LLM (modo híbrido)")
            logger.info(f"   Páginas enviadas: Ofício {oficio_correto['paginas']} + ANEXO II {paginas_anexo} + PROC {[pagina_proc] if pagina_proc else []}")
            
            dados_oficio = self._extrair_dados_llm_hibrido(
                texto_relevante, 
                tem_anexo_ii=bool(texto_anexo),
                tem_processamento=bool(texto_proc),
                numero_ordem_titulo=numero_ordem_titulo,
                oficio_rejeitado=oficio_rejeitado,
                motivo_rejeicao=motivo_rejeicao
            )
            
            if not dados_oficio:
                logger.error("❌ Falha na extração LLM")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    "Falha na extração LLM"
                )
            
            # 8. Validar com Pydantic
            try:
                oficio_validado = OficioRequisitorio(**dados_oficio)
                logger.info("✅ Dados validados com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro na validação Pydantic: {e}")
                return {
                    "cpf": cpf_numerico,
                    "pdf": Path(pdf_path).name,
                    "sucesso": False,
                    "cpf_validado": True,
                    "erro": f"Validação falhou: {e}",
                    "tempo_processamento": time.time() - inicio,
                    "num_oficios": len(todos_oficios)
                }
            
            # 8.1. Calcular flag IDOSO automaticamente
            if oficio_validado.data_nascimento:
                from datetime import date
                hoje = date.today()
                idade = hoje.year - oficio_validado.data_nascimento.year
                
                # Ajustar se ainda não fez aniversário este ano
                if (hoje.month, hoje.day) < (oficio_validado.data_nascimento.month, oficio_validado.data_nascimento.day):
                    idade -= 1
                
                # Atualizar flag idoso
                oficio_validado.idoso = (idade >= 60)
                logger.info(f"🎂 Idade calculada: {idade} anos → idoso={oficio_validado.idoso}")
            else:
                logger.debug("⚠️ data_nascimento não disponível, flag idoso não calculada")
            
            # 9. Retornar resultado de sucesso
            logger.info("✅ Processamento V2 concluído com sucesso!")
            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": True,
                "cpf_validado": True,
                "dados": oficio_validado.model_dump(),
                "tempo_processamento": time.time() - inicio,
                "num_oficios": len(todos_oficios)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento V2: {e}")
            import traceback
            traceback.print_exc()
            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": False,
                "cpf_validado": False,
                "erro": str(e),
                "tempo_processamento": time.time() - inicio,
                "num_oficios": 0
            }
    
    def _extrair_cpf_pasta(self, pdf_path: str) -> Optional[str]:
        """
        Extrai CPF do nome da pasta.
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            CPF (11 dígitos) ou None se inválido
        """
        try:
            cpf = Path(pdf_path).parent.name
            
            if not cpf.isdigit() or len(cpf) != 11:
                logger.error(f"CPF inválido: {cpf} (deve ter 11 dígitos)")
                return None
            
            return cpf
            
        except Exception as e:
            logger.error(f"Erro ao extrair CPF: {e}")
            return None
    
    def _formatar_cpf(self, cpf_numerico: str) -> str:
        """
        Formata CPF: 11671377877 → 116.713.778-77
        
        Args:
            cpf_numerico: CPF com 11 dígitos
            
        Returns:
            CPF formatado
        """
        if len(cpf_numerico) != 11:
            return cpf_numerico
        
        return f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:]}"
    
    def _criar_resultado_erro(
        self, 
        cpf: str, 
        pdf_path: str, 
        erro: str
    ) -> Dict[str, Any]:
        """
        Cria resultado de erro para análise manual.
        
        Args:
            cpf: CPF do processo
            pdf_path: Caminho para o PDF
            erro: Mensagem de erro
            
        Returns:
            Dict com resultado do erro
        """
        return {
            "cpf": cpf,
            "pdf": Path(pdf_path).name,
            "sucesso": False,
            "cpf_validado": False,
            "erro": erro,
            "tempo_processamento": 0,
            "num_oficios": 0
        }
    
    def _extrair_dados_llm_hibrido(
        self, 
        texto_oficio: str, 
        tem_anexo_ii: bool = False,
        tem_processamento: bool = False,
        numero_ordem_titulo: Optional[str] = None,
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extração híbrida: Gemini 2.5 Flash (primeiro) com fallback para GPT-4o-mini.
        
        NOVA em FINDING 08: Combina qualidade do Gemini (13 campos, grátis) 
        com confiabilidade do OpenAI (12 campos, 100% sucesso).
        
        Args:
            texto_oficio: Texto relevante (ofício + ANEXO II + PROCESSAMENTO)
            tem_anexo_ii: Se ANEXO II está presente
            tem_processamento: Se PROCESSAMENTO está presente
            numero_ordem_titulo: Número de ordem extraído do título (PDFs antigos)
            oficio_rejeitado: Se o ofício foi rejeitado
            motivo_rejeicao: Motivo da rejeição (se houver)
            
        Returns:
            Dicionário com dados extraídos ou None
        """
        # Criar LLM adapter se não existir
        if not hasattr(self, 'llm_adapter'):
            try:
                from .llm_adapter import LLMAdapter, LLMProvider
                gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                
                if gemini_key:
                    self.llm_adapter = LLMAdapter(
                        openai_api_key=self.openai_api_key,
                        gemini_api_key=gemini_key
                    )
                    self.llm_provider_enum = LLMProvider
                    logger.info("✅ LLM Adapter híbrido configurado (Gemini + OpenAI)")
                else:
                    logger.warning("⚠️ GOOGLE_API_KEY não encontrada, usando apenas OpenAI")
                    self.llm_adapter = None
            except Exception as e:
                logger.warning(f"⚠️ Erro ao configurar LLM Adapter: {e}, usando apenas OpenAI")
                self.llm_adapter = None
        
        # Se adapter não disponível, usar método legado
        if not self.llm_adapter:
            return self._extrair_dados_llm(
                texto_oficio, tem_anexo_ii, tem_processamento,
                numero_ordem_titulo, oficio_rejeitado, motivo_rejeicao
            )
        
        # Construir prompt (mesmo prompt para ambos LLMs)
        prompt = self._construir_prompt_llm(
            texto_oficio, tem_anexo_ii, tem_processamento,
            numero_ordem_titulo, oficio_rejeitado, motivo_rejeicao
        )
        
        # TENTATIVA 1: Gemini 2.5 Flash (mais completo, grátis)
        try:
            logger.info("🔄 Tentando extração com Gemini 2.5 Flash...")
            dados = self.llm_adapter.extract_structured_data(
                prompt,
                provider=self.llm_provider_enum.GEMINI
            )
            logger.info("✅ Gemini: Extração bem-sucedida!")
            return dados
        
        except Exception as e:
            erro_msg = str(e)
            logger.warning(f"⚠️ Gemini falhou: {erro_msg[:100]}")
            
            # Log do motivo específico
            if "finish_reason" in erro_msg:
                logger.warning("   Motivo: Bloqueio de conteúdo (safety filter)")
            elif "quota" in erro_msg.lower() or "429" in erro_msg:
                logger.warning("   Motivo: Quota excedida")
            else:
                logger.warning(f"   Motivo: {erro_msg[:80]}")
            
            logger.info("🔄 Usando fallback para OpenAI...")
        
        # FALLBACK: OpenAI GPT-4o-mini (mais confiável, pago)
        try:
            dados = self.llm_adapter.extract_structured_data(
                prompt,
                provider=self.llm_provider_enum.OPENAI
            )
            logger.info("✅ OpenAI: Extração bem-sucedida (fallback)!")
            return dados
        
        except Exception as e:
            logger.error(f"❌ Ambos LLMs falharam! Último erro (OpenAI): {e}")
            return None
    
    def _construir_prompt_llm(
        self,
        texto_oficio: str,
        tem_anexo_ii: bool = False,
        tem_processamento: bool = False,
        numero_ordem_titulo: Optional[str] = None,
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None
    ) -> str:
        """
        Constrói prompt para extração LLM (usado por ambos OpenAI e Gemini).
        
        Returns:
            String com prompt completo
        """
        # Ajustar prompt se ofício rejeitado
        nota_rejeicao = ""
        if oficio_rejeitado:
            nota_rejeicao = f"""
⚠️ ATENÇÃO: Este ofício foi REJEITADO pelo DEPRE!
- Extraia apenas os dados disponíveis no documento
- Campos que não estiverem disponíveis devem ser null
- Não invente valores
- Marque rejeitado=true
"""
        
        # Adicionar nota sobre anomalias
        nota_anomalia = ""
        if len(texto_oficio) < 500:
            nota_anomalia = """
⚠️ ATENÇÃO: Documento muito curto ou com formato anômalo!
- Se o documento não seguir o padrão esperado, marque anomalia=true
- Descreva o problema encontrado em descricao_anomalia
- Extraia o que for possível
"""
        
        # Prompt completo
        return f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

{nota_rejeicao}{nota_anomalia}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)
  ⚠️ ATENÇÃO - DIFERENÇA CRÍTICA:
  * CORRETO: "644/2015", "2913/2023", "12345/2024" (formato: números/ano)
  * ERRADO: "0181657-92.2021.8.26.0500" (isso é número do PROCESSO, não número de ordem!)
  * Buscar no TÍTULO: "OFÍCIO REQUISITÓRIO Nº XXX/YYYY"
  * OU na seção "PROCESSAMENTO": "Nº de Ordem: XXX/YYYY" ou "Ordem: XXX/YYYY"
  * Se NÃO encontrar o número de ordem, retorne null (não invente!)
- valor_principal_liquido: Valor principal líquido (número decimal)
- valor_principal_bruto: Valor principal bruto (número decimal)
- juros_moratorios: Juros moratórios (número decimal)
- valor_total_requisitado: Valor total requisitado (número decimal)

=== CAMPOS OPCIONAIS (nível raiz do JSON) ===

DADOS BANCÁRIOS (ANEXO II):
- banco: Código do banco (apenas números, ex: 341)
- agencia: Número da agência
- conta: Número da conta (com dígito)
- conta_tipo: Tipo de conta (corrente/poupança)
- dados_bancarios_advogado: Se dados são do advogado (true/false)
- cpf_titular_conta: CPF do titular da conta

CONTRIBUIÇÕES:
- contrib_previdenciaria_iprem: INST.PREV. ou IPREMSAOPAULO (número)
- contrib_previdenciaria_hspm: ASSIST.MÉD. ou HSPMSAOPAULO (número)

DATAS (formato YYYY-MM-DD):
- data_nascimento: Data de nascimento do credor
- data_base_atualizacao: Data base para atualização
- data_ajuizamento: Data de ajuizamento
- data_transito_julgado: Data do trânsito em julgado

PREFERÊNCIAS (true/false):
- idoso: Credor com mais de 60 anos
- doenca_grave: Portador de doença grave
- pcd: Pessoa com deficiência

OUTROS VALORES:
- tipo_levantamento: Tipo de levantamento
- valor_compensado: Valor compensado (número)
- contribuicao_social: Contribuição social (número)
- salario_pericial: Salário pericial (número)
- assist_tecnico: Assistente técnico (número)
- custas: Custas (número)
- despesas: Despesas (número)
- multas: Multas (número)

OUTRAS INFORMAÇÕES:
- vara: Vara responsável
- credor_nome: Nome do credor
- credor_cpf_cnpj: CPF/CNPJ do credor
- devedor_ente: Ente devedor
- advogado_nome: Nome do advogado
- advogado_oab: OAB do advogado

CONTROLE:
- rejeitado: Se o ofício foi rejeitado (true/false)
- motivo_rejeicao: Motivo da rejeição (se houver)
- anomalia: Se o PDF tem formato anômalo (true/false)
- descricao_anomalia: Descrição do problema encontrado (se houver)

=== REGRAS CRÍTICAS ===

1. ESTRUTURA: JSON FLAT (todos os campos no nível raiz, SEM objetos aninhados)
2. Campos não encontrados = null
3. Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
4. Datas: formato YYYY-MM-DD
5. Requerente: SEMPRE em MAIÚSCULAS
6. Booleanos: true ou false (minúsculas)
7. Número de ordem: buscar na seção "PROCESSAMENTO" (formato: XXX/YYYY)

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido:"""
    
    def _extrair_dados_llm(
        self, 
        texto_oficio: str, 
        tem_anexo_ii: bool = False,
        tem_processamento: bool = False,
        numero_ordem_titulo: Optional[str] = None,
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai dados estruturados usando GPT-4o-mini APENAS (método legado).
        
        V2: Prompt atualizado com número de ordem e ANEXO II completo.
        NOTA: Prefer usar _extrair_dados_llm_hibrido() para modo híbrido.
        
        Args:
            texto_oficio: Texto relevante (ofício + ANEXO II + PROCESSAMENTO)
            tem_anexo_ii: Se ANEXO II está presente
            tem_processamento: Se PROCESSAMENTO está presente
            numero_ordem_titulo: Número de ordem extraído do título (PDFs antigos)
            oficio_rejeitado: Se o ofício foi rejeitado
            motivo_rejeicao: Motivo da rejeição (se houver)
            
        Returns:
            Dicionário com dados extraídos ou None
        """
        try:
            # Ajustar prompt se ofício rejeitado
            nota_rejeicao = ""
            if oficio_rejeitado:
                nota_rejeicao = f"""
⚠️ ATENÇÃO: Este ofício foi REJEITADO pelo DEPRE!
- Extraia apenas os dados disponíveis no documento
- Campos que não estiverem disponíveis devem ser null
- Não invente valores
- Marque rejeitado=true
"""
            
            # Adicionar nota sobre anomalias
            nota_anomalia = ""
            if len(texto_oficio) < 500:
                nota_anomalia = """
⚠️ ATENÇÃO: Documento muito curto ou com formato anômalo!
- Se o documento não seguir o padrão esperado, marque anomalia=true
- Descreva o problema encontrado em descricao_anomalia
- Extraia o que for possível
"""
            
            # Prompt V2 otimizado
            prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

{nota_rejeicao}{nota_anomalia}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)
  ⚠️ ATENÇÃO - DIFERENÇA CRÍTICA:
  * CORRETO: "644/2015", "2913/2023", "12345/2024" (formato: números/ano)
  * ERRADO: "0181657-92.2021.8.26.0500" (isso é número do PROCESSO, não número de ordem!)
  * Buscar no TÍTULO: "OFÍCIO REQUISITÓRIO Nº XXX/YYYY"
  * OU na seção "PROCESSAMENTO": "Nº de Ordem: XXX/YYYY" ou "Ordem: XXX/YYYY"
  * Se NÃO encontrar o número de ordem, retorne null (não invente!)
- valor_principal_liquido: Valor principal líquido (número decimal)
- valor_principal_bruto: Valor principal bruto (número decimal)
- juros_moratorios: Juros moratórios (número decimal)
- valor_total_requisitado: Valor total requisitado (número decimal)

=== CAMPOS OPCIONAIS (nível raiz do JSON) ===

DADOS BANCÁRIOS (ANEXO II):
- banco: Código do banco (apenas números, ex: 341)
- agencia: Número da agência
- conta: Número da conta (com dígito)
- conta_tipo: Tipo de conta (corrente/poupança)
- dados_bancarios_advogado: Se dados são do advogado (true/false)
- cpf_titular_conta: CPF do titular da conta

CONTRIBUIÇÕES:
- contrib_previdenciaria_iprem: INST.PREV. ou IPREMSAOPAULO (número)
- contrib_previdenciaria_hspm: ASSIST.MÉD. ou HSPMSAOPAULO (número)

DATAS (formato YYYY-MM-DD):
- data_nascimento: Data de nascimento do credor
- data_base_atualizacao: Data base para atualização
- data_ajuizamento: Data de ajuizamento
- data_transito_julgado: Data do trânsito em julgado

PREFERÊNCIAS (true/false):
- idoso: Credor com mais de 60 anos
- doenca_grave: Portador de doença grave
- pcd: Pessoa com deficiência

OUTROS VALORES:
- tipo_levantamento: Tipo de levantamento
- valor_compensado: Valor compensado (número)
- contribuicao_social: Contribuição social (número)
- salario_pericial: Salário pericial (número)
- assist_tecnico: Assistente técnico (número)
- custas: Custas (número)
- despesas: Despesas (número)
- multas: Multas (número)

OUTRAS INFORMAÇÕES:
- vara: Vara responsável
- credor_nome: Nome do credor
- credor_cpf_cnpj: CPF/CNPJ do credor
- devedor_ente: Ente devedor
- advogado_nome: Nome do advogado
- advogado_oab: OAB do advogado

CONTROLE:
- rejeitado: Se o ofício foi rejeitado (true/false)
- motivo_rejeicao: Motivo da rejeição (se houver)
- anomalia: Se o PDF tem formato anômalo (true/false)
- descricao_anomalia: Descrição do problema encontrado (se houver)

=== REGRAS CRÍTICAS ===

1. ESTRUTURA: JSON FLAT (todos os campos no nível raiz, SEM objetos aninhados)
2. Campos não encontrados = null
3. Valores numéricos: SEM R$, SEM pontos de milhar, vírgula = ponto decimal
4. Datas: formato YYYY-MM-DD
5. Requerente: SEMPRE em MAIÚSCULAS
6. Booleanos: true ou false (minúsculas)
7. Número de ordem: buscar na seção "PROCESSAMENTO" (formato: XXX/YYYY)

EXEMPLO DE ESTRUTURA CORRETA:
{{
  "processo_origem": "0035938-67.2018.8.26.0053",
  "requerente_caps": "REGINA APARECIDA NARDES GARCIA DIAS",
  "numero_ordem": "2913/2023",
  "valor_principal_liquido": 17753.80,
  "valor_principal_bruto": 37993.13,
  "juros_moratorios": 20239.33,
  "valor_total_requisitado": 37993.13,
  "banco": "341",
  "agencia": "3740",
  "conta": "00000001341-6",
  "vara": "1ª VARA DE FAZENDA PÚBLICA",
  "data_base_atualizacao": "2020-02-29",
  "idoso": false
}}

ATENÇÃO: numero_ordem é diferente de processo_origem!
- processo_origem: 0035938-67.2018.8.26.0053 (número CNJ do processo)
- numero_ordem: 2913/2023 (número do ofício/precatório)

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido:"""

            # Chamar GPT-4o-mini
            response = self.client.chat.completions.create(
                model=self.modelo_gpt,
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
                temperature=0,  # Determinístico
                response_format={"type": "json_object"}
            )
            
            # Extrair JSON da resposta
            json_str = response.choices[0].message.content
            
            # Parse JSON
            dados = json.loads(json_str)
            
            # Se número de ordem foi extraído do título e LLM não encontrou, usar o do título
            if numero_ordem_titulo and not dados.get('numero_ordem'):
                logger.info(f"📋 Usando número de ordem do título: {numero_ordem_titulo}")
                dados['numero_ordem'] = numero_ordem_titulo
            
            # Adicionar flag de rejeição se detectada
            if oficio_rejeitado:
                dados['rejeitado'] = True
                if motivo_rejeicao and not dados.get('motivo_rejeicao'):
                    dados['motivo_rejeicao'] = motivo_rejeicao
            
            # Adicionar observações sobre campos não encontrados
            campos_ausentes = []
            campos_obrigatorios = [
                'valor_principal_liquido', 'valor_principal_bruto', 
                'juros_moratorios', 'valor_total_requisitado'
            ]
            
            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    campos_ausentes.append(campo)
            
            if campos_ausentes and not dados.get('observacoes'):
                obs = f"Campos não encontrados: {', '.join(campos_ausentes)}"
                dados['observacoes'] = obs
                logger.warning(f"⚠️ {obs}")
            
            # Detectar anomalias (formato não padrão)
            if dados.get('anomalia') and not dados.get('descricao_anomalia'):
                dados['descricao_anomalia'] = "PDF com formato anômalo detectado pelo LLM"
            
            logger.debug(f"Dados extraídos: {list(dados.keys())}")
            return dados
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}")
            logger.error(f"Resposta do LLM: {json_str[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Erro na chamada LLM: {e}")
            return None
    
    def salvar_postgres(self, resultado: Dict[str, Any]) -> bool:
        """
        Salva dados no PostgreSQL (upsert).
        
        Args:
            oficio_completo: Objeto completo para salvar
            
        Returns:
            True se salvou com sucesso
        """
        # TODO: Implementar quando necessário
        logger.warning("salvar_postgres() não implementado na V2")
        return False
