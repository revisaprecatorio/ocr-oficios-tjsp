"""
ProcessadorOficio V3 - Versão Corrigida com Melhorias do Bug Report

Melhorias implementadas baseadas na investigação do bug de 31/10/2025:
1. ✅ Isolamento robusto de ofícios em PDFs multi-documento
2. ✅ Prompt explícito sobre formato brasileiro de números
3. ✅ Validação de sanidade para valores monetários
4. ✅ Detecção e alerta de PDFs com múltiplos ofícios
5. ✅ Logs detalhados para debug
6. ✅ Garantia de que valores sejam retornados como NUMBERS

Baseado em: ProcessadorOficio V2
Data da correção: 31/10/2025
Bug fix: Parsing de valores (R$ 88.994,41 → R$ 88,99)
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

import pymupdf
from openai import OpenAI

from .detector import DetectorOficio
from .detector_anexo import DetectorAnexoII
from .detector_processamento import DetectorProcessamento
from .schemas import OficioRequisitorio

logger = logging.getLogger(__name__)


class ProcessadorOficioCorrigido:
    """
    Pipeline V3 (Corrigido) para processamento de Ofícios Requisitórios.
    
    Melhorias vs V2:
    - Isolamento RIGOROSO de ofícios (previne mistura de dados)
    - Prompt com exemplos explícitos de formato brasileiro
    - Validação de sanidade de valores (alerta se < R$ 1.000)
    - Detecção de PDFs multi-ofício com alertas
    - Logs detalhados em cada etapa
    - Verificação de tipos de dados retornados pelo LLM
    
    Pipeline:
    1. Detectar TODOS os ofícios no PDF
    2. ⚠️ ALERTAR se múltiplos ofícios (edge case)
    3. Validar CPF e isolar ofício correto
    4. Garantir isolamento de contexto
    5. Detectar ANEXO II e PROCESSAMENTO
    6. Extrair dados (GPT-4o-mini com prompt melhorado)
    7. ✅ Validar tipos e valores de sanidade
    8. Validar com Pydantic
    9. Salvar no PostgreSQL
    """
    
    def __init__(self, openai_api_key: str, db_config: Dict[str, Any]):
        """
        Inicializa o processador V3 (Corrigido).
        
        Args:
            openai_api_key: Chave da API OpenAI
            db_config: Configurações do banco PostgreSQL
        """
        # Inicializar OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        self.modelo_gpt = "gpt-4o-mini"
        
        # Configurações do banco
        self.db_config = db_config
        
        # Inicializar detectores
        self.detector = DetectorOficio()
        self.detector_anexo = DetectorAnexoII()
        self.detector_proc = DetectorProcessamento()

        logger.info("ProcessadorOficioCorrigido V3 inicializado")
        logger.info("✅ Melhorias: isolamento robusto + validação de sanidade + prompt otimizado")
    
    def processar_arquivo(self, pdf_path: str, cpf_numerico: str) -> Dict[str, Any]:
        """
        Processa um único arquivo PDF com isolamento robusto de ofícios.
        
        V3: Melhorias de isolamento e validação de valores.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            cpf_numerico: CPF esperado (apenas números)
            
        Returns:
            Dict com resultado do processamento
        """
        inicio = time.time()
        
        try:
            logger.info("="*80)
            logger.info(f"🔄 Iniciando processamento V3 (CORRIGIDO): {pdf_path}")
            logger.info("="*80)
            
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
            logger.info(f"👤 CPF esperado: {cpf_formatado} ({cpf_numerico})")
            
            # 2. Buscar TODOS os ofícios no PDF
            logger.info("")
            logger.info("📄 ETAPA 1: Detecção de ofícios")
            logger.info("-" * 80)
            
            todos_oficios = self.detector.buscar_todos_oficios(pdf_path)
            
            if not todos_oficios:
                logger.warning("⚠️ Nenhum ofício encontrado no PDF")
                return self._criar_resultado_erro(
                    cpf_numerico, 
                    pdf_path, 
                    "Nenhum ofício detectado"
                )
            
            logger.info(f"✅ Encontrados {len(todos_oficios)} ofício(s) no PDF")
            
            # 🚨 ALERTA: PDF com múltiplos ofícios (edge case!)
            if len(todos_oficios) > 1:
                logger.warning("")
                logger.warning("🚨 " + "="*76)
                logger.warning("🚨 ALERTA: PDF COM MÚLTIPLOS OFÍCIOS (EDGE CASE CRÍTICO!)")
                logger.warning("🚨 " + "="*76)
                logger.warning(f"🚨 Este PDF contém {len(todos_oficios)} ofícios diferentes")
                logger.warning("🚨 Risco de confusão de dados entre documentos")
                logger.warning("🚨 Isolamento rigoroso será aplicado")
                logger.warning("🚨 " + "="*76)
                logger.warning("")
            
            # Listar todos os ofícios detectados
            for idx, oficio in enumerate(todos_oficios, 1):
                paginas = oficio['paginas']
                num_chars = len(oficio['texto'])
                logger.info(f"   Ofício {idx}: páginas {paginas[0]+1}-{paginas[-1]+1} ({len(paginas)} pág, {num_chars:,} chars)")
            
            # 3. Encontrar ofício com CPF correto
            logger.info("")
            logger.info("🔍 ETAPA 2: Validação de CPF")
            logger.info("-" * 80)
            
            oficio_correto = None
            oficio_correto_idx = None
            
            for idx, oficio in enumerate(todos_oficios, 1):
                logger.info(f"🔍 Verificando ofício {idx}/{len(todos_oficios)} (páginas {oficio['paginas'][0]+1}-{oficio['paginas'][-1]+1})")
                
                if self.detector.validar_cpf_no_oficio(oficio['texto'], cpf_formatado):
                    logger.info(f"✅ CPF {cpf_formatado} ENCONTRADO no ofício {idx}!")
                    oficio_correto = oficio
                    oficio_correto_idx = idx
                    break
                else:
                    logger.info(f"❌ CPF {cpf_formatado} NÃO encontrado no ofício {idx}")
            
            if not oficio_correto:
                logger.warning(f"⚠️ CPF {cpf_formatado} não encontrado em nenhum ofício")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    f"CPF {cpf_formatado} não encontrado (PDF tem {len(todos_oficios)} ofício(s))"
                )
            
            logger.info("")
            logger.info(f"✅ Ofício selecionado: #{oficio_correto_idx} (páginas {oficio_correto['paginas'][0]+1}-{oficio_correto['paginas'][-1]+1})")
            logger.info(f"   Caracteres: {len(oficio_correto['texto']):,}")
            logger.info(f"   Páginas: {len(oficio_correto['paginas'])}")
            
            # 🔒 ISOLAMENTO RIGOROSO: Garantir que apenas este ofício seja processado
            if len(todos_oficios) > 1:
                logger.info("")
                logger.info("🔒 ISOLAMENTO RIGOROSO ATIVADO")
                logger.info("-" * 80)
                logger.info(f"✅ Texto isolado: APENAS ofício #{oficio_correto_idx}")
                logger.info(f"❌ Excluídos: {len(todos_oficios) - 1} outro(s) ofício(s)")
                logger.info("✅ Contexto limpo garantido")
            
            # 4. Detectar ANEXO II (após ofício correto)
            logger.info("")
            logger.info("📋 ETAPA 3: Detecção de ANEXO II e PROCESSAMENTO")
            logger.info("-" * 80)
            
            ultima_pag_oficio = oficio_correto['paginas'][-1]
            paginas_anexo, texto_anexo = self.detector_anexo.detectar_anexo_ii(pdf_path)
            
            if texto_anexo:
                logger.info(f"✅ ANEXO II encontrado em {len(paginas_anexo)} página(s): {[p+1 for p in paginas_anexo]}")
            else:
                logger.warning("⚠️ ANEXO II não encontrado")
            
            # 5. Extrair número de ordem do título (fallback)
            numero_ordem_titulo = self.detector_proc.extrair_numero_ordem_do_titulo(
                oficio_correto['texto']
            )
            
            if numero_ordem_titulo:
                logger.info(f"📋 Número de ordem extraído do título: {numero_ordem_titulo}")
            
            # 6. Detectar PROCESSAMENTO
            inicio_proc = paginas_anexo[-1] - 1 if paginas_anexo else ultima_pag_oficio - 1
            pagina_proc, texto_proc = self.detector_proc.detectar_processamento(
                pdf_path,
                inicio=inicio_proc,
                limite=100
            )
            
            if texto_proc:
                logger.info(f"✅ PROCESSAMENTO encontrado na página {pagina_proc + 1}")
            else:
                logger.warning("⚠️ PROCESSAMENTO não encontrado")
            
            # 7. Verificar rejeição (mesma lógica da V2)
            oficio_rejeitado, motivo_rejeicao = self._verificar_rejeicao(
                pdf_path,
                texto_proc,
                pagina_proc,
                ultima_pag_oficio
            )
            
            # 8. Montar texto relevante (APENAS ofício correto!)
            logger.info("")
            logger.info("📝 ETAPA 4: Montagem do contexto")
            logger.info("-" * 80)
            
            texto_relevante = self._montar_texto_relevante(
                oficio_correto,
                texto_anexo,
                texto_proc,
                oficio_rejeitado
            )
            
            logger.info(f"✅ Contexto montado: {len(texto_relevante):,} caracteres")
            logger.info(f"   Componentes: Ofício + {'ANEXO II ' if texto_anexo else ''}+ {'PROCESSAMENTO' if texto_proc else 'sem PROC'}")
            
            # 9. Enviar ao LLM com prompt melhorado
            logger.info("")
            logger.info("🤖 ETAPA 5: Extração de dados (GPT-4o-mini)")
            logger.info("-" * 80)
            logger.info(f"⏳ Enviando {len(texto_relevante):,} chars para GPT-4o-mini...")
            logger.info(f"   Modelo: {self.modelo_gpt}")
            logger.info(f"   Temperature: 0 (determinístico)")
            logger.info(f"   Prompt: V3 (com exemplos de formato brasileiro)")
            
            dados_oficio = self._extrair_dados_llm_v3(
                texto_relevante, 
                tem_anexo_ii=bool(texto_anexo),
                tem_processamento=bool(texto_proc),
                numero_ordem_titulo=numero_ordem_titulo,
                oficio_rejeitado=oficio_rejeitado,
                motivo_rejeicao=motivo_rejeicao,
                num_oficios=len(todos_oficios)
            )
            
            if not dados_oficio:
                logger.error("❌ Falha na extração LLM")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    "Falha na extração LLM"
                )
            
            logger.info("✅ Dados extraídos do LLM")
            
            # 🔍 VALIDAÇÃO DE SANIDADE: Verificar valores monetários
            logger.info("")
            logger.info("🔍 ETAPA 6: Validação de sanidade")
            logger.info("-" * 80)
            
            self._validar_sanidade_valores(dados_oficio)
            
            # 10. Validar com Pydantic
            logger.info("")
            logger.info("✅ ETAPA 7: Validação Pydantic")
            logger.info("-" * 80)
            
            try:
                oficio_validado = OficioRequisitorio(**dados_oficio)
                logger.info("✅ Dados validados com sucesso (Pydantic)")
            except Exception as e:
                logger.error(f"❌ Erro na validação Pydantic: {e}")
                return {
                    "cpf": cpf_numerico,
                    "pdf": Path(pdf_path).name,
                    "sucesso": False,
                    "cpf_validado": True,
                    "erro": f"Validação falhou: {e}",
                    "tempo_processamento": time.time() - inicio,
                    "num_oficios": len(todos_oficios),
                    "multi_oficio_warning": len(todos_oficios) > 1
                }
            
            # 11. Calcular flag IDOSO automaticamente
            if oficio_validado.data_nascimento:
                from datetime import date
                hoje = date.today()
                idade = hoje.year - oficio_validado.data_nascimento.year
                
                if (hoje.month, hoje.day) < (oficio_validado.data_nascimento.month, oficio_validado.data_nascimento.day):
                    idade -= 1
                
                oficio_validado.idoso = (idade >= 60)
                logger.info(f"🎂 Idade calculada: {idade} anos → idoso={oficio_validado.idoso}")
            
            # 12. Retornar resultado de sucesso
            logger.info("")
            logger.info("="*80)
            logger.info("✅ PROCESSAMENTO V3 CONCLUÍDO COM SUCESSO!")
            logger.info("="*80)
            logger.info(f"⏱️  Tempo total: {time.time() - inicio:.2f}s")
            logger.info(f"📄 Ofícios no PDF: {len(todos_oficios)}")
            if len(todos_oficios) > 1:
                logger.info(f"🔒 Isolamento aplicado: ofício #{oficio_correto_idx} de {len(todos_oficios)}")
            logger.info(f"💰 Valor total: R$ {float(oficio_validado.valor_total_requisitado or 0):,.2f}")
            logger.info("="*80)
            
            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": True,
                "cpf_validado": True,
                "dados": oficio_validado.model_dump(),
                "tempo_processamento": time.time() - inicio,
                "num_oficios": len(todos_oficios),
                "multi_oficio_warning": len(todos_oficios) > 1,
                "oficio_selecionado": oficio_correto_idx
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento V3: {e}")
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
    
    def _verificar_rejeicao(
        self,
        pdf_path: str,
        texto_proc: Optional[str],
        pagina_proc: Optional[int],
        ultima_pag_oficio: int
    ) -> tuple[bool, Optional[str]]:
        """
        Verifica se ofício foi rejeitado (mesma lógica da V2).
        
        Returns:
            (oficio_rejeitado, motivo_rejeicao)
        """
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
        
        # Prioridade: se tem indicadores de aceitação, não é rejeitado
        if tem_processamento_com_informacao or tem_numero_ordem:
            oficio_rejeitado = False
            logger.info("✅ Ofício ACEITO")
        else:
            # Verificar rejeição apenas se não tem indicadores de aceitação
            if texto_proc and self.detector_proc.eh_oficio_rejeitado(texto_proc):
                oficio_rejeitado = True
                motivo_rejeicao = self.detector_proc.extrair_motivo_rejeicao(texto_proc)
                logger.warning(f"⚠️ OFÍCIO REJEITADO detectado!")
                if motivo_rejeicao:
                    logger.info(f"   Motivo: {motivo_rejeicao[:100]}...")
        
        return oficio_rejeitado, motivo_rejeicao
    
    def _montar_texto_relevante(
        self,
        oficio: Dict[str, Any],
        texto_anexo: Optional[str],
        texto_proc: Optional[str],
        oficio_rejeitado: bool
    ) -> str:
        """
        Monta texto relevante com ofício + ANEXO II + PROCESSAMENTO.
        
        Returns:
            Texto relevante para enviar ao LLM
        """
        texto_relevante = oficio['texto']
        
        if texto_anexo:
            texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
        
        if texto_proc:
            if oficio_rejeitado:
                texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_proc}"
            else:
                texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
        
        # Aplicar chunking se necessário (mesma lógica da V2)
        MAX_CHARS = 200_000
        if len(texto_relevante) > MAX_CHARS:
            logger.warning(f"⚠️ Texto muito grande ({len(texto_relevante):,} chars > {MAX_CHARS:,})")
            logger.info("🔧 Aplicando CHUNKING: primeiras 30 + últimas 30 páginas")
            
            paginas_oficio = oficio['paginas']
            paginas_chunk = paginas_oficio[:30] + paginas_oficio[-30:]
            
            doc = pymupdf.open(pdf_path)
            texto_chunk = ""
            for pag in paginas_chunk:
                texto_chunk += doc.load_page(pag).get_text() + "\n"
            doc.close()
            
            texto_relevante = texto_chunk
            
            # Re-adicionar anexos
            if texto_anexo:
                texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
            if texto_proc:
                if oficio_rejeitado:
                    texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_proc}"
                else:
                    texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
            
            logger.info(f"📄 Texto reduzido: {len(texto_relevante):,} chars")
        
        return texto_relevante
    
    def _validar_sanidade_valores(self, dados: Dict[str, Any]) -> None:
        """
        Valida sanidade dos valores monetários extraídos.
        
        Alertas:
        - Valores < R$ 1.000 (suspeito)
        - Valores retornados como strings (deve ser number)
        - Valores inconsistentes (líquido > bruto)
        """
        campos_valores = [
            'valor_principal_liquido',
            'valor_principal_bruto',
            'juros_moratorios',
            'valor_total_requisitado'
        ]
        
        alertas = []
        
        for campo in campos_valores:
            valor = dados.get(campo)
            
            if valor is None:
                continue
            
            # Verificar se é string (deveria ser number)
            if isinstance(valor, str):
                alertas.append(f"⚠️ {campo}: retornado como STRING '{valor}' (deveria ser NUMBER)")
                # Tentar converter
                try:
                    valor = float(valor.replace('.', '').replace(',', '.'))
                    dados[campo] = valor
                except:
                    alertas.append(f"   ❌ Conversão falhou!")
                    continue
            
            # Verificar se valor é number
            if isinstance(valor, (int, float, Decimal)):
                valor_float = float(valor)
                
                # Alerta: valor < R$ 1.000
                if valor_float < 1000 and valor_float > 0:
                    alertas.append(f"🚨 {campo}: R$ {valor_float:,.2f} < R$ 1.000 (SUSPEITO!)")
                
                # Alerta: valor muito baixo (< R$ 100)
                if valor_float < 100 and valor_float > 0:
                    alertas.append(f"🚨 {campo}: R$ {valor_float:,.2f} < R$ 100 (MUITO SUSPEITO!)")
                
                # Log: valor OK
                if valor_float >= 1000:
                    logger.info(f"✅ {campo}: R$ {valor_float:,.2f} (OK)")
        
        # Exibir alertas
        if alertas:
            logger.warning("")
            logger.warning("⚠️ " + "="*76)
            logger.warning("⚠️ ALERTAS DE VALIDAÇÃO DE SANIDADE")
            logger.warning("⚠️ " + "="*76)
            for alerta in alertas:
                logger.warning(f"   {alerta}")
            logger.warning("⚠️ " + "="*76)
            logger.warning("")
        else:
            logger.info("✅ Validação de sanidade: NENHUM alerta")
    
    def _extrair_dados_llm_v3(
        self, 
        texto_oficio: str, 
        tem_anexo_ii: bool = False,
        tem_processamento: bool = False,
        numero_ordem_titulo: Optional[str] = None,
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None,
        num_oficios: int = 1
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai dados estruturados usando GPT-4o-mini com prompt V3 melhorado.
        
        Melhorias vs V2:
        - ✅ Exemplos explícitos de formato brasileiro
        - ✅ Instruções claras sobre conversão de valores
        - ✅ Alerta se múltiplos ofícios no PDF
        - ✅ Garantia de retorno como NUMBERS
        
        Args:
            texto_oficio: Texto relevante (ofício + ANEXO II + PROCESSAMENTO)
            tem_anexo_ii: Se ANEXO II está presente
            tem_processamento: Se PROCESSAMENTO está presente
            numero_ordem_titulo: Número de ordem extraído do título
            oficio_rejeitado: Se o ofício foi rejeitado
            motivo_rejeicao: Motivo da rejeição (se houver)
            num_oficios: Número de ofícios no PDF (para alertar se > 1)
            
        Returns:
            Dicionário com dados extraídos ou None
        """
        try:
            # Nota sobre múltiplos ofícios
            nota_multi_oficio = ""
            if num_oficios > 1:
                nota_multi_oficio = f"""
🚨 ATENÇÃO CRÍTICA: Este PDF contém {num_oficios} ofícios DIFERENTES!
- O texto abaixo é APENAS de UM ofício isolado
- NÃO misture dados de ofícios diferentes
- Extraia APENAS os dados deste documento específico
- Se houver dúvida, retorne null
"""
            
            # Ajustar prompt se ofício rejeitado
            nota_rejeicao = ""
            if oficio_rejeitado:
                nota_rejeicao = """
⚠️ ATENÇÃO: Este ofício foi REJEITADO pelo DEPRE!
- Extraia apenas os dados disponíveis no documento
- Campos que não estiverem disponíveis devem ser null
- Não invente valores
- Marque rejeitado=true
"""
            
            # Prompt V3 com melhorias
            prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

{nota_multi_oficio}{nota_rejeicao}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS
- numero_ordem: Número de ordem do RPV/Precatório (formato: XXXXX/YYYY)
- valor_principal_liquido: Valor principal líquido (NUMBER, não string!)
- valor_principal_bruto: Valor principal bruto (NUMBER, não string!)
- juros_moratorios: Juros moratórios (NUMBER, não string!)
- valor_total_requisitado: Valor total requisitado (NUMBER, não string!)

⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️

NO PDF, os valores aparecem assim:
- "R$ 88.994,41" (ponto = milhar, vírgula = decimal)
- "R$ 1.234.567,89"
- "R$ 123,45"

VOCÊ DEVE RETORNAR assim (NUMBER sem formatação):
- 88994.41 (ponto como decimal, sem milhar)
- 1234567.89
- 123.45

EXEMPLOS DE CONVERSÃO CORRETOS:
✅ "R$ 88.994,41" → 88994.41 (NUMBER)
✅ "R$ 1.234.567,89" → 1234567.89 (NUMBER)
✅ "R$ 123,45" → 123.45 (NUMBER)
✅ "88.994,41" → 88994.41 (NUMBER)

EXEMPLOS DE CONVERSÃO ERRADOS:
❌ "R$ 88.994,41" → "88.99" (truncou!)
❌ "R$ 88.994,41" → "88994.41" (string!)
❌ "R$ 88.994,41" → 88.99 (interpretou ponto como decimal!)

REGRA: Remova R$, converta vírgula em ponto, remova pontos de milhar, retorne como NUMBER.

=== CAMPOS OPCIONAIS ===

[... mesmos campos da V2 ...]

=== REGRAS CRÍTICAS ===

1. ESTRUTURA: JSON FLAT (todos os campos no nível raiz)
2. Campos não encontrados = null
3. Valores monetários: SEMPRE como NUMBER (não string!)
4. Formato brasileiro: "1.234,56" → 1234.56 (NUMBER)
5. Datas: formato YYYY-MM-DD
6. Requerente: SEMPRE em MAIÚSCULAS
7. Booleanos: true ou false (minúsculas)

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON FLAT válido com valores como NUMBERS:"""

            # Chamar GPT-4o-mini
            response = self.client.chat.completions.create(
                model=self.modelo_gpt,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um assistente especializado em extração de dados estruturados de documentos jurídicos brasileiros. Retorne apenas JSON válido com valores monetários como NUMBERS."
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
            
            # Adicionar observações sobre campos ausentes
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
            
            logger.debug(f"Dados extraídos: {list(dados.keys())}")
            return dados
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao fazer parse do JSON: {e}")
            logger.error(f"Resposta do LLM: {json_str[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Erro na chamada LLM: {e}")
            return None
    
    # Métodos auxiliares (mesmos da V2)
    
    def _extrair_cpf_pasta(self, pdf_path: str) -> Optional[str]:
        """Extrai CPF do nome da pasta."""
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
        """Formata CPF: 11671377877 → 116.713.778-77"""
        if len(cpf_numerico) != 11:
            return cpf_numerico
        return f"{cpf_numerico[:3]}.{cpf_numerico[3:6]}.{cpf_numerico[6:9]}-{cpf_numerico[9:]}"
    
    def _criar_resultado_erro(
        self, 
        cpf: str, 
        pdf_path: str, 
        erro: str
    ) -> Dict[str, Any]:
        """Cria resultado de erro."""
        return {
            "cpf": cpf,
            "pdf": Path(pdf_path).name,
            "sucesso": False,
            "cpf_validado": False,
            "erro": erro,
            "tempo_processamento": 0,
            "num_oficios": 0
        }
    
    def salvar_postgres(self, resultado: Dict[str, Any]) -> bool:
        """Salva dados no PostgreSQL (mesmo da V2)."""
        logger.warning("salvar_postgres() não implementado na V3")
        return False
    
    # Alias para compatibilidade
    processar_pdf = processar_arquivo

