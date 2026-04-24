"""
ProcessadorOficio V3.0 - Production Ready (Schema Cleanup + V2.7.x fixes)

V3.0 = SCHEMA CLEANUP + PRODUCTION READY:
1. ✅ Schema simplificado: 50 → 35 colunas (-30%)
2. ✅ 15 campos vazios removidos (0% preenchimento)
3. ✅ Fix bug process_calculo (não existe no schema)
4. ✅ Projeto reorganizado (historico_arquivado/)
5. ✅ Baseline estável V2.7.6 mantido

Histórico V2.7.x (Stable):
- V2.7.6: FIX doenca_grave - validação de resposta Sim/Não
- V2.7.5: Detecção PROCESSAMENTO rigorosa (3 campos obrigatórios)
- V2.7.4: Prompts LLM atualizados (requerente_caps removido)
- V2.7.3: Fix data quality (numero_ordem + cpf_sucessor)
- V2.7.2: Remove requerente_caps field
- V2.7.1: Fix critical bugs (numero_ordem + data contamination)

Histórico V2.5.x:
- V2.5.3: Detecção de habilitação de herdeiros, óbito, doença grave
- V2.5.2: Detecção de saldo final

Meta: Taxa de sucesso ≥98% (vs 96.1% em V2.5.1)
Performance: +20-30% em queries (schema reduzido)
"""

import os
import json
import logging
import time
import re
from pathlib import Path
import psycopg2
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

import pymupdf
from openai import OpenAI

from .detector import DetectorOficio
from .detector_anexo import DetectorAnexoII
from .detector_processamento import DetectorProcessamento
from .detector_termos_juridicos import DetectorTermosJuridicos
from .detector_saldo_final import DetectorSaldoFinal  # V2.5.2: Novo detector
from .detector_habilitacao_herdeiros import DetectorHabilitacaoHerdeiros  # V2.5.3: Novo detector
from .tracker_execucao import TrackerExecucao  # V2.5.3: Tracking completo
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
        self.openai_api_key = openai_api_key  # Armazenar para LLM adapter
        self.client = OpenAI(api_key=openai_api_key)
        self.modelo_gpt = "gpt-4o-mini"
        
        # Configurações do banco
        self.db_config = db_config
        
        # Inicializar detectores V2
        self.detector = DetectorOficio()
        self.detector_anexo = DetectorAnexoII()
        self.detector_proc = DetectorProcessamento()
        self.detector_termos = DetectorTermosJuridicos()  # V2.4.0
        self.detector_saldo = DetectorSaldoFinal()  # V2.5.2: Novo detector
        self.detector_habilitacao = DetectorHabilitacaoHerdeiros()  # V2.5.3: Novo detector

        logger.info("=" * 80)
        logger.info("🚀 ProcessadorOficio V3.0 - PRODUCTION READY")
        logger.info("=" * 80)
        logger.info("✅ V3.0: Schema cleanup (50→35 cols, -30%)")
        logger.info("✅ V2.7.6: FIX doenca_grave - validação resposta Sim/Não")
        logger.info("✅ V2.7.5: Detecção PROCESSAMENTO rigorosa (3 campos)")
        logger.info("✅ V2.7.4: Prompts LLM atualizados")
        logger.info("✅ V2.5.3: Habilitação herdeiros + Óbito + Doença grave")
        logger.info("✅ V2.5.2: Saldo final")
        logger.info("=" * 80)

    def _gravar_log_banco(self, cpf: str, descricao: str, processo: str = 'OCR'):
        """Grava na tabela public.logs com processo fixo OCR."""
        query = "INSERT INTO public.logs (cpf, descricao, processo) VALUES (%s, %s, %s)"
        conn = None
        try:
            cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))[:11]
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(query, (cpf_limpo, descricao, processo))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"❌ Erro ao gravar log: {e}")
        finally:
            if conn: conn.close()

    def _atualizar_estado_consulta_esaj(self, cpf: str, numero_processo: str, estado: str):
        """Atualiza current_state em consultas_esaj para o CPF/processo informado.
        
        processos é JSONB com formato: {"lista": [{"numero": "0024354-44.2023.8.26.0500", ...}]}
        Filtra pelo numero_processo dentro da lista para atualizar apenas o registro correto.
        """
        cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))[:11]
        cpf_fmt = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}" if len(cpf_limpo) == 11 else cpf_limpo
        query = """
            UPDATE consultas_esaj
            SET current_state = %s
            WHERE cpf = %s
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(processos->'lista') AS p
                WHERE p->>'numero' = %s
              )
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(query, (estado, cpf_limpo, numero_processo))
            rows = cur.rowcount
            conn.commit()
            cur.close()
            if rows > 0:
                logger.info(f"✅ consultas_esaj atualizado: CPF={cpf_fmt}, processo={numero_processo}, state={estado} ({rows} linha(s))")
            else:
                logger.warning(f"⚠️ consultas_esaj: nenhuma linha atualizada (CPF={cpf_fmt}, processo={numero_processo})")
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar consultas_esaj: {e}")
        finally:
            if conn: conn.close()

    def _registrar_ocr_no_tracking(self, cpf: str, numero_processo: str, erro_msg: str):
        """Insere evento OCR_ERRO em process_tracking seguindo o padrão de event log do sistema.
        
        Busca o consulta_id em consultas_esaj pelo CPF + número do processo (JSONB),
        depois insere linha em process_tracking com etapa='OCR', evento='OCR_ERRO'.
        """
        cpf_limpo = ''.join(filter(str.isdigit, str(cpf)))[:11]
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            # Buscar consulta_id vinculado ao processo
            cur.execute("""
                SELECT id, whatsapp_phone_number FROM consultas_esaj
                WHERE cpf = %s
                  AND EXISTS (
                    SELECT 1 FROM jsonb_array_elements(processos->'lista') AS p
                    WHERE p->>'numero' = %s
                  )
                ORDER BY created_at DESC LIMIT 1
            """, (cpf_limpo, numero_processo))
            row = cur.fetchone()
            consulta_id = row[0] if row else None
            whatsapp = row[1] if row else None

            detalhes = json.dumps({
                "processo": numero_processo,
                "node": "OCR Pipeline",
                "workflow": "processar_pipeline"
            })

            cur.execute("""
                INSERT INTO process_tracking
                    (consulta_id, cpf, whatsapp_phone_number, etapa, evento,
                     retries, concluido, erro, mensagem_erro, detalhes, timestamp_evento)
                VALUES (%s, %s, %s, 'OCR', 'OCR_ERRO', 0, false, true, %s, %s, NOW())
            """, (consulta_id, cpf_limpo, whatsapp, erro_msg[:500], detalhes))

            conn.commit()
            cur.close()
            logger.info(f"✅ process_tracking: OCR_ERRO registrado (CPF={cpf_limpo}, processo={numero_processo}, consulta_id={consulta_id})")
        except Exception as e:
            logger.error(f"❌ Erro ao registrar OCR_ERRO em process_tracking: {e}")
        finally:
            if conn: conn.close()

    def processar_arquivo(self, pdf_path: str, cpf_numerico: str, tracker: Optional[TrackerExecucao] = None) -> Dict[str, Any]:
        """
        Processa um único arquivo PDF com validação de CPF.

        V2: Busca todos os ofícios, valida CPF, processa apenas o correto.
        V2.5.3: Aceita tracker opcional para logging detalhado

        Args:
            pdf_path: Caminho para o arquivo PDF
            cpf_numerico: CPF esperado (apenas números)
            tracker: Tracker de execução opcional para logs em Markdown

        Returns:
            Dict com resultado do processamento
        """
        inicio = time.time()
        pdf_nome = Path(pdf_path).name
        
        try:
            logger.info(f"🔄 Iniciando processamento V2: {pdf_path}")

            # Validar arquivo PDF
            if not self.detector.validar_pdf(pdf_path):
                logger.error(f"❌ PDF inválido: {pdf_path}")
                if tracker:
                    tracker.adicionar_erro("PDF inválido ou corrompido")
                return None

            # 1. Extrair CPF da pasta (ou usar CPF passado como parâmetro)
            # V2.6.0: Se CPF foi passado como parâmetro, usar ele (para testes)
            # Caso contrário, extrair da estrutura de pastas (produção)
            if not cpf_numerico:
                cpf_numerico = self._extrair_cpf_pasta(pdf_path)
                if not cpf_numerico:
                    logger.error(f"❌ CPF inválido na pasta: {Path(pdf_path).parent.name}")
                    if tracker:
                        tracker.adicionar_erro(f"CPF inválido: {Path(pdf_path).parent.name}")
                    return None

            cpf_formatado = self._formatar_cpf(cpf_numerico)
            logger.info(f"📋 CPF esperado: {cpf_formatado}")

            # Tracker: Inicialização
            if tracker:
                tamanho_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
                tracker.iniciar(pdf_path, tamanho_mb)
            
            # 1.1. V2.5.1: Detectar PDF antigo (formato 7xxxxxx-xx.20xx)
            nome_arquivo = Path(pdf_path).name
            processo_numero = nome_arquivo.replace('.pdf', '')
            pdf_antigo = processo_numero.startswith('7')
            
            if pdf_antigo:
                logger.warning(f"⚠️ PDF ANTIGO detectado: {processo_numero} (formato 7xxxxxx)")
                logger.warning(f"⚠️ PDFs antigos podem ter estrutura diferente e menor taxa de sucesso")
            
            # 1.5. V2.6.0: NOVA ESTRATÉGIA - Indexar ANEXOS II por CPF ANTES de buscar ofícios
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 1.5. Indexação de ANEXOS II por CPF V2.6.0")
                tracker.adicionar_item("Indexando todos os ANEXOS II do PDF...", nivel=0, emoji="🔍")
            
            logger.info("🔍 V2.6.0: Indexando ANEXOS II por CPF...")
            anexos_indexados = self.detector_anexo.indexar_anexos_por_cpf(pdf_path)
            
            if tracker:
                tracker.adicionar_detalhes("Total de credores", len(anexos_indexados), nivel=1)
                if anexos_indexados:
                    tracker.adicionar_subsecao("CPFs indexados:", nivel=1)
                    for cpf_limpo, dados in list(anexos_indexados.items())[:5]:  # Mostrar até 5
                        tracker.adicionar_item(f"{dados['cpf_formatado']} - {dados['credor_nome'] or '(sem nome)'}", nivel=2)
                    if len(anexos_indexados) > 5:
                        tracker.adicionar_item(f"... e mais {len(anexos_indexados) - 5} credor(es)", nivel=2)
            
            # V2.6.0: Validar se CPF esperado está no índice
            if cpf_numerico not in anexos_indexados:
                logger.error(f"❌ V2.6.0: CPF {cpf_formatado} NÃO encontrado em nenhum ANEXO II!")
                logger.error(f"   CPF esperado: {cpf_formatado} ({cpf_numerico})")
                
                if anexos_indexados:
                    logger.error(f"   CPF(s) encontrado(s) em ANEXO II:")
                    for cpf_limpo, dados in anexos_indexados.items():
                        logger.error(f"      • {dados['cpf_formatado']} - {dados['credor_nome'] or '(sem nome)'}")
                    
                    msg = f"ANEXO II encontrado no PDF, mas nenhum pertence ao CPF esperado.\n"
                    msg += f"CPF esperado: {cpf_formatado}.\n"
                    msg += f"CPF(s) encontrado(s): {', '.join([d['cpf_formatado'] for d in anexos_indexados.values()])}"
                else:
                    msg = f"Nenhum ANEXO II detectado no PDF para qualquer CPF"
                
                self._gravar_log_banco(cpf_numerico, msg)
                
                if tracker:
                    tracker.adicionar_erro(msg)
                
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    msg
                )
            
            # V2.6.0: CPF encontrado no índice - usar dados do índice
            dados_anexo_indexado = anexos_indexados[cpf_numerico]
            logger.info(f"✅ V2.6.0: CPF {cpf_formatado} encontrado no ANEXO II!")
            logger.info(f"   Página: {dados_anexo_indexado['pagina'] + 1}")
            logger.info(f"   Credor: {dados_anexo_indexado['credor_nome'] or '(não extraído)'}")
            logger.info(f"   Tipo: {dados_anexo_indexado['tipo']}")
            
            if tracker:
                tracker.adicionar_resultado(f"✅ CPF encontrado no ANEXO II (página {dados_anexo_indexado['pagina'] + 1})", sucesso=True, nivel=1)
                if dados_anexo_indexado['credor_nome']:
                    tracker.adicionar_detalhes("Credor", dados_anexo_indexado['credor_nome'], nivel=2)
            
            # 2. Buscar todos os ofícios no PDF
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 2. Detecção de Ofícios")
                tracker.adicionar_item("Buscando todos os ofícios no PDF...", nivel=0, emoji="🔍")

            todos_oficios = self.detector.buscar_todos_oficios(pdf_path)

            if not todos_oficios:
                logger.warning("⚠️ Nenhum ofício detectado no PDF")
                if tracker:
                    tracker.adicionar_erro("Nenhum ofício detectado no PDF")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    "Nenhum ofício detectado"
                )

            logger.info(f"📄 Encontrados {len(todos_oficios)} ofício(s) no PDF")
            if tracker:
                for idx, oficio in enumerate(todos_oficios, 1):
                    paginas_str = f"[{oficio['paginas'][0]}-{oficio['paginas'][-1]}]" if len(oficio['paginas']) > 1 else f"[{oficio['paginas'][0]}]"
                    tracker.adicionar_resultado(f"Ofício {idx}: páginas {paginas_str}", sucesso=True, nivel=1)
                tracker.adicionar_detalhes("Total", len(todos_oficios), nivel=0)
                tracker.adicionar_linha_vazia()

            # 3. Encontrar ofício com CPF correto (método tradicional)
            if tracker:
                tracker.adicionar_secao("## 3. Validação de CPF")
                tracker.adicionar_item(f"Buscando CPF `{cpf_formatado}` em cada ofício...", nivel=0, emoji="🔍")

            oficio_correto = None
            for idx, oficio in enumerate(todos_oficios, 1):
                logger.info(f"🔍 Verificando ofício {idx}/{len(todos_oficios)} (páginas {oficio['paginas']})")

                if self.detector.validar_cpf_no_oficio(oficio['texto'], cpf_formatado):
                    logger.info(f"✅ CPF encontrado no ofício {idx}!")
                    if tracker:
                        tracker.adicionar_resultado(f"Ofício {idx}: **CPF ENCONTRADO!**", sucesso=True, nivel=1)
                    oficio_correto = oficio
                    break
                else:
                    logger.info(f"❌ CPF não encontrado no ofício {idx}")
                    if tracker:
                        tracker.adicionar_resultado(f"Ofício {idx}: CPF não encontrado", sucesso=False, nivel=1)
            
            # V2.4.4: FALLBACK - Se não encontrou CPF em nenhum ofício E PDF tem 100+ credores
            # Tentar busca direta por CPF (para casos onde ofício não foi detectado corretamente)
            if not oficio_correto and len(todos_oficios) >= 100:
                logger.warning(f"⚠️ CPF não encontrado nos {len(todos_oficios)} ofícios detectados")
                logger.warning(f"⚠️ Tentando FALLBACK: busca direta por CPF no PDF...")
                
                oficio_por_cpf = self.detector.extrair_oficio_por_cpf(pdf_path, cpf_formatado, contexto_paginas=3)
                
                if oficio_por_cpf:
                    logger.info(f"✅ FALLBACK bem-sucedido! Ofício encontrado na página {oficio_por_cpf['pagina_cpf']}")
                    oficio_correto = oficio_por_cpf
                else:
                    logger.error(f"❌ FALLBACK falhou - CPF não encontrado mesmo com busca direta")
            
            # V2.6.2: FALLBACK multi-credor
            # CPF confirmado no ANEXO II mas não mencionado no corpo do ofício.
            # Ocorre em precatórios com N credores: cada CPF fica apenas no ANEXO II,
            # não no ofício principal. Usar o ofício imediatamente anterior ao ANEXO II.
            if not oficio_correto and cpf_numerico in anexos_indexados and todos_oficios:
                pagina_anexo = dados_anexo_indexado['pagina'] + 1  # 0-indexed → 1-indexed
                candidatos = [o for o in todos_oficios if max(o['paginas']) < pagina_anexo]
                oficio_correto = candidatos[-1] if candidatos else todos_oficios[0]
                logger.warning(
                    f"⚠️ FALLBACK multi-credor: CPF só no ANEXO II (pág {pagina_anexo}), "
                    f"usando ofício páginas {oficio_correto['paginas']}"
                )
                if tracker:
                    tracker.adicionar_resultado(
                        f"⚠️ FALLBACK multi-credor: CPF confirmado no ANEXO II (pág {pagina_anexo}), "
                        f"ofício páginas {oficio_correto['paginas']}",
                        sucesso=True, nivel=1
                    )

            if not oficio_correto:
                logger.warning(f"⚠️ CPF {cpf_formatado} não encontrado em nenhum ofício")
                msg=f"CPF {cpf_formatado} não encontrado em nenhum ofício"
                self._gravar_log_banco(cpf_numerico,msg)
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    f"CPF {cpf_formatado} não encontrado (PDF tem {len(todos_oficios)} ofício(s))"
                )
            
            # 3.1. Detectar termos jurídicos no texto completo do PDF (V2.4.0)
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 4. Detecção de Termos Jurídicos V2.5.2")
                tracker.adicionar_item("Buscando termos no texto completo do PDF...", nivel=0, emoji="🔍")

            logger.info("🔍 Detectando termos jurídicos no PDF completo...")

            # Extrair texto completo do PDF para detecção de termos
            doc = pymupdf.open(pdf_path)
            texto_completo_pdf = ""
            for pagina in doc:
                texto_completo_pdf += pagina.get_text() + "\n"
            doc.close()
             
            # --- INÍCIO DA CORREÇÃO VARA ---
            vara_detectada = None
            try:
                # Busca nos primeiros 3000 caracteres do PDF bruto
                match_vara = re.search(
                    r'(?i)(\d+[ªºa]?\s*Vara\s*(?:da|de|do)?\s*(?:Fazenda|Juizado|Cível|Acidentes|Execuções)[^\n]*)', 
                    texto_completo_pdf[:3000] 
                )
                if match_vara:
                    vara_detectada = match_vara.group(1).strip().replace('\n', ' ')
                    logger.info(f"🏛️ Vara detectada via REGEX: {vara_detectada}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao tentar detectar vara via regex: {e}")
                self._gravar_log_banco(cpf_numerico,"Erro ao tentar detectar vara via regex")

            # Detectar termos jurídicos (V2.5.3: inclui doença grave)
            termos_juridicos = self.detector_termos.detectar_termos(texto_completo_pdf, cpf_formatado)
            logger.info(f"📋 Termos encontrados: {termos_juridicos}")

            if tracker:
                tracker.adicionar_subsecao("Resultados:", nivel=0)
                tracker.adicionar_detalhes("Preferencial", termos_juridicos['preferencial'], nivel=1)
                tracker.adicionar_detalhes("Habilitação Herdeiros", termos_juridicos['habilitacao_herdeiros'], nivel=1)
                tracker.adicionar_detalhes("Cessão Crédito", termos_juridicos['cessao_credito'], nivel=1)
                tracker.adicionar_detalhes("Doença Grave", termos_juridicos.get('doenca_grave', False), nivel=1)
                tracker.adicionar_item("(Cessão de Crédito: DESATIVADO em v2.5.2)", nivel=1)
                tracker.adicionar_linha_vazia()

            # 3.2. Detecção avançada de Habilitação de Herdeiros (V2.5.3)
            # Usa detector especializado com código 9270 + estrutura "Dados da Sucessão"
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 4.5. Detecção Avançada de Habilitação de Herdeiros V2.5.3")
                tracker.adicionar_item("Buscando código 9270 e estrutura 'Dados da Sucessão'...", nivel=0, emoji="🔍")

            resultado_habilitacao = self.detector_habilitacao.detectar(texto_completo_pdf)
            logger.info(f"📋 Habilitação detectada: {resultado_habilitacao}")

            # Se detector especializado encontrou com alta/média confiança, sobrescrever
            if resultado_habilitacao['nivel_confianca'] in ['ALTA', 'MÉDIA']:
                logger.info(f"✅ Sobrescrevendo habilitacao_herdeiros com resultado do detector especializado (confiança: {resultado_habilitacao['nivel_confianca']})")
                termos_juridicos['habilitacao_herdeiros'] = resultado_habilitacao['habilitacao_herdeiros']
                # Armazenar dados extras para adicionar ao JSON final
                dados_obito = {
                    'obito': resultado_habilitacao['obito'],
                    'data_obito': resultado_habilitacao['data_obito'],
                    'cpf_sucessor': resultado_habilitacao['cpf_sucessor']
                }
            else:
                # Detector especializado não encontrou nada ou baixa confiança
                dados_obito = {'obito': False, 'data_obito': None, 'cpf_sucessor': None}

            if tracker:
                tracker.adicionar_subsecao("Resultados:", nivel=0)
                tracker.adicionar_detalhes("Nível Confiança", resultado_habilitacao['nivel_confianca'] or 'N/A', nivel=1)
                tracker.adicionar_detalhes("Habilitação Confirmada", resultado_habilitacao['habilitacao_herdeiros'], nivel=1)
                tracker.adicionar_detalhes("Óbito Detectado", resultado_habilitacao['obito'], nivel=1)
                if resultado_habilitacao['data_obito']:
                    tracker.adicionar_detalhes("Data Óbito", resultado_habilitacao['data_obito'], nivel=1)
                if resultado_habilitacao['cpf_sucessor']:
                    tracker.adicionar_detalhes("CPF Sucessor", resultado_habilitacao['cpf_sucessor'], nivel=1)
                tracker.adicionar_linha_vazia()

            # 4. Detectar ANEXO II (após ofício correto) - MANTIDO PARA COMPATIBILIDADE
            # V2.6.0: Indexação já foi feita no início (linha 172), dados em dados_anexo_indexado
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 5. Detecção ANEXO II (Método Tradicional)")
                tracker.adicionar_item("Buscando ANEXO II a partir do fim do ofício...", nivel=0, emoji="🔍")

            # V2.5.0: Retorna também página do TÍTULO do ANEXO II
            # FIX v2.4.2: Buscar ANEXO II a partir da última página do ofício selecionado
            ultima_pag_oficio = oficio_correto['paginas'][-1]
            paginas_anexo, texto_anexo, pagina_titulo_anexo = self.detector_anexo.detectar_anexo_ii(
                pdf_path,
                inicio=ultima_pag_oficio  # Buscar a partir do fim do ofício (0-indexed)
            )

            logger.info(f"📌 Página do TÍTULO ANEXO II: {pagina_titulo_anexo + 1 if pagina_titulo_anexo >= 0 else 'N/A'}")

            if pagina_titulo_anexo >= 0:
                if tracker:
                    tracker.adicionar_resultado(f"Título ANEXO II: página {pagina_titulo_anexo + 1}", sucesso=True, nivel=1)
            else:
                if tracker:
                    tracker.adicionar_resultado("ANEXO II não encontrado", sucesso=False, nivel=1)

            # 4.1. V2.6.0: Usar página do ANEXO II indexado (mais confiável)
            pagina_credor = dados_anexo_indexado['pagina']  # Já temos do índice!
            secao_credor = ""
            
            logger.info(f"🔍 V2.6.0: Usando página do ANEXO II indexado: {pagina_credor + 1}")
            if tracker:
                tracker.adicionar_item(f"Extraindo seção do credor (página {pagina_credor + 1})...", nivel=1, emoji="🔍")

            # Extrair seção focada do credor
            secao_credor = self.detector_anexo.extrair_secao_credor_no_anexo(
                pdf_path,
                pagina_credor,
                cpf_formatado
            )

            if secao_credor:
                logger.info(f"✅ Seção do credor extraída ({len(secao_credor)} chars)")
                if tracker:
                    tracker.adicionar_resultado(f"Seção extraída: {len(secao_credor)} caracteres", sucesso=True, nivel=2)
                # Usar seção focada como texto do ANEXO II
                texto_anexo = secao_credor
            else:
                logger.warning(f"⚠️ Não conseguiu extrair seção, usando texto completo da página")
                self._gravar_log_banco(cpf_numerico,"Não conseguiu extrair seção, usando texto completo da página")
                if tracker:
                    tracker.adicionar_item("Usando texto completo da página (seção não extraída)", nivel=2, emoji="⚠️")
                # Fallback: usar texto da página indexada
                texto_anexo = dados_anexo_indexado['texto']

            if tracker:
                tracker.adicionar_linha_vazia()
            
            # 5. Tentar extrair número de ordem do TÍTULO do ofício (PDFs antigos)
            numero_ordem_titulo = self.detector_proc.extrair_numero_ordem_do_titulo(
                oficio_correto['texto']
            )
            
            # 6. Detectar PROCESSAMENTO (PDFs novos) - buscar em mais páginas
            # V3.0.2: PRIORIDADE 1 - Detectar REJEIÇÃO ANTES de PROCESSAMENTO
            if tracker:
                tracker.adicionar_secao("## 6. Detecção REJEIÇÃO / PROCESSAMENTO")
                tracker.adicionar_item("V3.0.2: Buscando NOTA DE REJEIÇÃO...", nivel=0, emoji="🔍")

            inicio_busca = paginas_anexo[-1] - 1 if paginas_anexo else ultima_pag_oficio - 1

            # V3.0.2: Nova função - detectar_rejeicao() retorna (pagina, texto, motivo)
            pagina_rejeicao, texto_rejeicao, motivo_rejeicao = self.detector_proc.detectar_rejeicao(
                pdf_path,
                inicio=inicio_busca,
                limite=None  # Buscar até o final do PDF
            )

            oficio_rejeitado = False
            if pagina_rejeicao:
                oficio_rejeitado = True
                logger.warning(f"⚠️ V3.0.2: OFÍCIO REJEITADO detectado na página {pagina_rejeicao}")
                self._gravar_log_banco(cpf_numerico,f"⚠️ V3.0.2: OFÍCIO REJEITADO detectado na página {pagina_rejeicao}")
                if motivo_rejeicao:
                    logger.info(f"   📝 Motivo: {motivo_rejeicao[:150]}...")
                if tracker:
                    tracker.adicionar_resultado(f"⚠️ NOTA DE REJEIÇÃO: página {pagina_rejeicao}", sucesso=True, nivel=1)
                    if motivo_rejeicao:
                        tracker.adicionar_detalhes("Motivo", motivo_rejeicao[:200] + "..." if len(motivo_rejeicao) > 200 else motivo_rejeicao, nivel=2)
            else:
                if tracker:
                    tracker.adicionar_resultado("✅ Ofício NÃO rejeitado", sucesso=True, nivel=1)

            # 6.1. Se NÃO rejeitado → Detectar PROCESSAMENTO (ou CERTIDÃO) com número de ordem
            pagina_proc = None
            texto_proc = None
            numero_ordem_global = None

            if not oficio_rejeitado:
                if tracker:
                    tracker.adicionar_item("Buscando PROCESSAMENTO...", nivel=0, emoji="🔍")

                pagina_proc, texto_proc = self.detector_proc.detectar_processamento(
                    pdf_path,
                    inicio=inicio_busca,
                    limite=None  # V2.7.3: Buscar até o final do PDF (sem limite)
                )

                if pagina_proc:
                    # 🔧 CORREÇÃO: Limpar quebras de linha em números de ordem ANTES de processar
                    texto_proc = self.detector_proc._limpar_quebras_linha_numero_ordem(texto_proc)
                    logger.info(f"✅ PROCESSAMENTO detectado na página {pagina_proc}")
                    if tracker:
                        tracker.adicionar_resultado(f"PROCESSAMENTO: página {pagina_proc}", sucesso=True, nivel=1)
                else:
                    if tracker:
                        tracker.adicionar_resultado("PROCESSAMENTO não encontrado", sucesso=False, nivel=1)

                    # V2.7.3 FIX: Fallback global - buscar numero_ordem em TODO o PDF
                    logger.info("🔍 V2.7.5: Tentando busca GLOBAL de numero_ordem (fallback)...")
                    numero_ordem_global = self.detector_proc.buscar_numero_ordem_global(pdf_path)
                    if numero_ordem_global:
                        logger.info(f"✅ V2.7.5: numero_ordem encontrado via busca global: {numero_ordem_global}")
                        if tracker:
                            tracker.adicionar_resultado(f"V2.7.5 GLOBAL: numero_ordem = {numero_ordem_global}", sucesso=True, nivel=1)
                    else:
                        logger.warning("⚠️ V2.7.5: numero_ordem NÃO encontrado mesmo com busca global")
                        self._gravar_log_banco(cpf_numerico,"V2.7.5: numero_ordem NÃO encontrado mesmo com busca global")
                        if tracker:
                            tracker.adicionar_resultado("V2.7.5 GLOBAL: numero_ordem não encontrado", sucesso=False, nivel=1)
            
            # 7. Montar texto relevante (APENAS páginas necessárias!)
            # CHUNKING: Se ofício muito grande SEM ANEXO II/PROCESSAMENTO, reduzir
            # FINDING 08: Desabilitar chunking se Gemini disponível (contexto 1M tokens)
            paginas_oficio = oficio_correto['paginas']
            num_paginas = len(paginas_oficio)
            
            # Verificar se Gemini está disponível
            gemini_disponivel = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            
            if num_paginas > 100 and not texto_anexo and not texto_proc and not gemini_disponivel:
                logger.warning(f"⚠️ Ofício muito grande ({num_paginas} páginas) sem ANEXO II/PROCESSAMENTO")
                self._gravar_log_banco(cpf_numerico,f" Ofício muito grande ({num_paginas} páginas) sem ANEXO II/PROCESSAMENTO")
                logger.info(f"🔧 Aplicando CHUNKING: primeiras 50 + últimas 50 páginas")
                
                # Extrair apenas primeiras 50 + últimas 50 páginas
                paginas_chunk = paginas_oficio[:50] + paginas_oficio[-50:]
                
                # Re-extrair texto apenas dessas páginas
                doc = pymupdf.open(pdf_path)
                texto_chunk = ""
                for pag in paginas_chunk:
                    if 0 <= pag - 1 < len(doc):  # FIX: paginas são 1-indexed, load_page espera 0-indexed
                        texto_chunk += doc.load_page(pag - 1).get_text() + "\n"
                doc.close()
                
                texto_relevante = texto_chunk
                logger.info(f"📄 Texto reduzido: {len(texto_relevante):,} chars (100 páginas)")
            else:
                texto_relevante = oficio_correto['texto']
            
            # V2.5.0: Pré-extrair dados com regex (se temos seção focada)
            dados_regex = {}
            if texto_anexo and secao_credor:
                logger.info(f"📋 Pré-extraindo dados com regex da seção focada...")
                dados_regex = self.detector_anexo.pre_extrair_dados_com_regex(texto_anexo)
                logger.info(f"✅ Pré-extraídos {len(dados_regex)} campos com regex")
            
            # Adicionar ANEXO II ao texto relevante
            if texto_anexo:
                texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
            else:
                logger.warning("⚠️ ANEXO II não encontrado")
                self._gravar_log_banco(cpf_numerico,"ANEXO II não encontrado")

            # V3.0.2: Adicionar NOTA DE REJEIÇÃO ou PROCESSAMENTO ao texto relevante
            if oficio_rejeitado and texto_rejeicao:
                logger.info(f"📋 NOTA DE REJEIÇÃO encontrada na página {pagina_rejeicao}")
                texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_rejeicao}"
            elif texto_proc:
                # FIX v2.4.3: Filtrar campo "Requerente" do PROCESSAMENTO em PDFs multi-creditor
                texto_proc_filtrado = self._filtrar_requerente_processamento(texto_proc)
                logger.info(f"📋 PROCESSAMENTO encontrado na página {pagina_proc}")
                texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc_filtrado}"
            elif numero_ordem_titulo:
                logger.info(f"📋 Número de ordem extraído do TÍTULO: {numero_ordem_titulo}")
            else:
                logger.warning("⚠️ PROCESSAMENTO não encontrado e número não está no título")
            
            # 8. Verificar tamanho e aplicar chunking adicional se necessário
            # Estimativa conservadora: 1 token ≈ 2 chars (português), limite 128k tokens ≈ 256k chars
            # Deixar margem de segurança: 200k chars
            MAX_CHARS = 200_000
            
            if len(texto_relevante) > MAX_CHARS and not gemini_disponivel:
                logger.warning(f"⚠️ Texto muito grande ({len(texto_relevante):,} chars > {MAX_CHARS:,})")
                logger.info(f"🔧 Aplicando CHUNKING AGRESSIVO: primeiras 30 + últimas 30 páginas do ofício")
                
                # Re-extrair com chunking mais agressivo
                paginas_chunk = paginas_oficio[:30] + paginas_oficio[-30:]
                
                doc = pymupdf.open(pdf_path)
                texto_chunk = ""
                for pag in paginas_chunk:
                    if 0 <= pag - 1 < len(doc):  # FIX: paginas são 1-indexed, load_page espera 0-indexed
                        texto_chunk += doc.load_page(pag - 1).get_text() + "\n"
                doc.close()
                
                texto_relevante = texto_chunk
                
                # Re-adicionar ANEXO II e PROCESSAMENTO/REJEIÇÃO (se houver)
                if texto_anexo:
                    texto_relevante += f"\n\n{'='*60}\n=== ANEXO II ===\n{'='*60}\n\n{texto_anexo}"
                # V3.0.2: Adicionar texto de rejeição ou processamento
                if oficio_rejeitado and texto_rejeicao:
                    texto_relevante += f"\n\n{'='*60}\n=== NOTA DE REJEIÇÃO ===\n{'='*60}\n\n{texto_rejeicao}"
                elif texto_proc:
                    texto_relevante += f"\n\n{'='*60}\n=== PROCESSAMENTO ===\n{'='*60}\n\n{texto_proc}"
                
                logger.info(f"📄 Texto reduzido: {len(texto_relevante):,} chars (60 páginas + anexos)")
            
            # 8.5. Normalizar valores brasileiros ANTES de enviar ao LLM (BUG FIX)
            logger.info("🔢 Normalizando valores monetários brasileiros...")
            texto_normalizado = self._normalizar_valores_brasileiros(texto_relevante)
            valores_encontrados = len(re.findall(r'R\$\s*\d+\.?\d*', texto_normalizado))
            logger.info(f"   ✅ {valores_encontrados} valores normalizados (R$ XX.XXX,XX → R$ XXXXX.XX)")
            
            # 9. Enviar ao LLM com Modo Híbrido (Gemini + OpenAI fallback)
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 7. Extração LLM (GPT-4o-mini)")
                tracker.adicionar_item(f"Enviando {len(texto_normalizado):,} caracteres para LLM...", nivel=0, emoji="🤖")
                paginas_str = f"Ofício {oficio_correto['paginas'][:3]}...{oficio_correto['paginas'][-3:]} ({len(oficio_correto['paginas'])} págs)"
                tracker.adicionar_detalhes("Páginas incluídas", paginas_str, nivel=1)
                if paginas_anexo:
                    tracker.adicionar_detalhes("+ ANEXO II", f"páginas {paginas_anexo}", nivel=1)
                if pagina_proc:
                    tracker.adicionar_detalhes("+ PROCESSAMENTO", f"página {pagina_proc}", nivel=1)

            logger.info(f"🤖 Enviando {len(texto_normalizado):,} chars para LLM (modo híbrido)")
            logger.info(f"   Páginas enviadas: Ofício {oficio_correto['paginas']} + ANEXO II {paginas_anexo} + PROC {[pagina_proc] if pagina_proc else []}")

            tempo_llm_inicio = time.time()
            dados_oficio = self._extrair_dados_llm_hibrido(
                texto_normalizado,  # Usar texto normalizado
                tem_anexo_ii=bool(texto_anexo),
                tem_processamento=bool(texto_proc),
                numero_ordem_titulo=numero_ordem_titulo,
                numero_ordem_global=numero_ordem_global,  # V2.7.3
                oficio_rejeitado=oficio_rejeitado,
                motivo_rejeicao=motivo_rejeicao
            )
            tempo_llm = time.time() - tempo_llm_inicio

            if dados_oficio and tracker:
                tracker.adicionar_resultado(f"Resposta recebida ({tempo_llm:.1f}s)", sucesso=True, nivel=1)
            
            if not dados_oficio:
                logger.error("❌ Falha na extração LLM")
                self._gravar_log_banco(cpf_numerico,"Falha na extração LLM")
                return self._criar_resultado_erro(
                    cpf_numerico,
                    pdf_path,
                    "Falha na extração LLM"
                )
            
            # V2.5.0: Mesclar dados regex com dados LLM (priorizar regex)
            if dados_regex:
                logger.info(f"🔀 Mesclando dados regex com dados LLM...")
                dados_antes = len([k for k, v in dados_oficio.items() if v])
                
                # Dados regex sobrescrevem dados LLM (mais confiáveis)
                for campo, valor in dados_regex.items():
                    if valor:  # Só sobrescrever se regex encontrou valor
                        dados_oficio[campo] = valor
                        logger.info(f"   ✅ {campo}: usando valor regex")
                
                dados_depois = len([k for k, v in dados_oficio.items() if v])
                logger.info(f"📊 Campos preenchidos: {dados_antes} → {dados_depois}")
            
            # --- INSERIR ESTE BLOCO AQUI ---
            if vara_detectada:
                vara_llm = dados_oficio.get('vara')
                if not vara_llm or len(str(vara_llm)) < 3 or "informado" in str(vara_llm).lower():
                    dados_oficio['vara'] = vara_detectada
                    logger.info(f"✅ Vara injetada via Regex: {vara_detectada}")
            # ------------------------------

            # 8. Validar CPF extraído vs CPF esperado (FIX v2.4.3)
            cpf_extraido = dados_oficio.get('credor_cpf_cnpj', '')
            if cpf_extraido:
                # Normalizar ambos CPFs para comparação (remover formatação)
                cpf_extraido_limpo = cpf_extraido.replace('.', '').replace('-', '')
                cpf_esperado_limpo = cpf_numerico
                
                if cpf_extraido_limpo != cpf_esperado_limpo:
                    logger.error(f"❌ CPF MISMATCH! LLM extraiu dados do credor ERRADO!")
                    logger.error(f"   CPF esperado (pasta): {cpf_formatado} ({cpf_esperado_limpo})")
                    logger.error(f"   CPF extraído (LLM): {cpf_extraido} ({cpf_extraido_limpo})")
                    logger.error(f"   Nome extraído: {dados_oficio.get('requerente_caps', 'N/A')}")
                    logger.warning("⚠️ Possível PDF multi-creditor com dados conflitantes")
                    self._gravar_log_banco(cpf_numerico,f" CPF MISMATCH! LLM extraiu dados do credor ERRADO!")
                    
                    # Marcar como erro crítico
                    return self._criar_resultado_erro(
                        cpf_numerico,
                        pdf_path,
                        f"CPF mismatch: extraído {cpf_extraido} mas esperado {cpf_formatado} (PDF multi-creditor)"
                    )
                else:
                    logger.info(f"✅ CPF validado: {cpf_extraido} corresponde ao esperado")
            else:
                logger.warning("⚠️ CPF não extraído pelo LLM (campo credor_cpf_cnpj vazio)")

            # 8.5. V2.6.0: Validação de sanidade de valores
            alertas_sanidade = self._validar_sanidade_valores(
                dados_oficio,
                cpf_formatado,
                dados_oficio.get('processo_origem', '')
            )

            if alertas_sanidade:
                logger.warning("=" * 80)
                logger.warning("🚨 ALERTAS DE SANIDADE DETECTADOS (V2.6.0):")
                for alerta in alertas_sanidade:
                    logger.warning(f"   {alerta}")
                logger.warning("=" * 80)

                if tracker:
                    tracker.adicionar_linha_vazia()
                    tracker.adicionar_secao("## 8. Alertas de Sanidade (V2.6.0)")
                    for alerta in alertas_sanidade:
                        tracker.adicionar_item(alerta, nivel=0, emoji="⚠️")

            # 9. Validar com Pydantic (com fallback se necessário)
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 9. Validação Pydantic")
                tracker.adicionar_item("Validando dados extraídos...", nivel=0, emoji="🔍")

            try:
                logger.info("🔍 V2.7.4: Iniciando validação Pydantic...")
                oficio_validado = OficioRequisitorio(**dados_oficio)
                logger.info("✅ V2.7.4: Dados validados com sucesso (sem erros de campo inexistente)")
                if tracker:
                    tracker.adicionar_resultado("Dados validados com sucesso", sucesso=True, nivel=1)
                    campos_preenchidos = len([k for k, v in dados_oficio.items() if v])
                    tracker.adicionar_detalhes("Campos preenchidos", campos_preenchidos, nivel=1)
            except Exception as e:
                # FINDING 08: Se validação falhar, tentar fallback para OpenAI
                from pydantic import ValidationError

                # V2.7.4: Log completo do erro
                logger.error(f"❌ V2.7.4: Erro na validação Pydantic:")
                self._gravar_log_banco(cpf_numerico,"V2.7.4: Erro na validação Pydantic:")
                logger.error(f"   Tipo: {type(e).__name__}")
                logger.error(f"   Mensagem: {str(e)}")
                logger.error(f"   Dados tentados: {list(dados_oficio.keys())[:10]}...")  # V2.7.4: Log campos
                
                # Se temos LLM adapter e não tentamos OpenAI ainda, fazer fallback
                if hasattr(self, 'llm_adapter') and self.llm_adapter:
                    logger.warning("⚠️ Tentando fallback para OpenAI devido a erro de validação...")
                    
                    try:
                        # Construir prompt novamente
                        prompt = self._construir_prompt_llm(
                            texto_relevante,
                            tem_anexo_ii=bool(texto_anexo),
                            tem_processamento=bool(texto_proc),
                            numero_ordem_titulo=numero_ordem_titulo,
                            numero_ordem_global=numero_ordem_global,  # V2.7.3
                            oficio_rejeitado=oficio_rejeitado,
                            motivo_rejeicao=motivo_rejeicao
                        )
                        
                        # Tentar com OpenAI
                        logger.info("🔄 Extraindo com OpenAI (fallback por erro de validação)...")
                        dados_oficio = self.llm_adapter.extract_structured_data(
                            prompt,
                            provider=self.llm_provider_enum.OPENAI
                        )
                        
                        # Tentar validar novamente
                        oficio_validado = OficioRequisitorio(**dados_oficio)
                        logger.info("✅ Dados validados com sucesso (OpenAI fallback)!")
                        
                    except Exception as e2:
                        logger.error(f"❌ Fallback OpenAI também falhou: {e2}")
                        self._gravar_log_banco(cpf_numerico,f"Fallback OpenAI também falhou: {e2}")
                        return {
                            "cpf": cpf_numerico,
                            "pdf": Path(pdf_path).name,
                            "sucesso": False,
                            "cpf_validado": True,
                            "erro": f"Validação falhou (Gemini e OpenAI): {e} | {e2}",
                            "tempo_processamento": time.time() - inicio,
                            "num_oficios": len(todos_oficios)
                        }
                else:
                    # Sem LLM adapter, retornar erro
                    return {
                        "cpf": cpf_numerico,
                        "pdf": Path(pdf_path).name,
                        "sucesso": False,
                        "cpf_validado": True,
                        "erro": f"Validação falhou: {type(e).__name__}: {str(e)}",
                        "tempo_processamento": time.time() - inicio,
                        "num_oficios": len(todos_oficios)
                    }
            
            # 8.1. Calcular flag IDOSO automaticamente
            if tracker:
                tracker.adicionar_linha_vazia()
                tracker.adicionar_secao("## 9. Cálculos V2.5.2")

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
                if tracker:
                    tracker.adicionar_detalhes("Idade", f"{idade} anos", nivel=0)
                    tracker.adicionar_detalhes("Idoso (≥60)", oficio_validado.idoso, nivel=0)
            else:
                logger.debug("⚠️ data_nascimento não disponível, flag idoso não calculada")
                if tracker:
                    tracker.adicionar_item("Data nascimento indisponível, flag idoso não calculada", nivel=0, emoji="⚠️")

            # 8.2. Adicionar termos jurídicos detectados (V2.4.0 / V2.5.3)
            oficio_validado.preferencial = termos_juridicos['preferencial']
            oficio_validado.habilitacao_herdeiros = termos_juridicos['habilitacao_herdeiros']
            # V2.7.2: cessao_credito REMOVIDO do schema
            # oficio_validado.cessao_credito = termos_juridicos['cessao_credito']
            oficio_validado.doenca_grave = termos_juridicos.get('doenca_grave', False)  # V2.5.3: Novo campo
            logger.info(f"📜 Termos jurídicos adicionados aos dados validados")

            # 8.2.1. V2.5.3: Adicionar dados de óbito e sucessão
            oficio_validado.obito = dados_obito['obito']
            oficio_validado.cpf_sucessor = dados_obito['cpf_sucessor']

            # Converter data_obito de DD/MM/YYYY para date object (ISO)
            if dados_obito['data_obito']:
                try:
                    from datetime import datetime
                    data_obito_str = dados_obito['data_obito']
                    data_obj = datetime.strptime(data_obito_str, '%d/%m/%Y').date()
                    oficio_validado.data_obito = data_obj
                    logger.info(f"📅 Data de óbito convertida: {data_obito_str} → {data_obj}")
                except ValueError as e:
                    logger.warning(f"⚠️ Erro ao converter data de óbito '{data_obito_str}': {e}")
                    oficio_validado.data_obito = None
            else:
                oficio_validado.data_obito = None

            # V2.7.3 FIX: Validar cpf_sucessor != credor_cpf_cnpj
            if oficio_validado.cpf_sucessor and oficio_validado.credor_cpf_cnpj:
                # Normalizar CPFs para comparação (remover formatação)
                cpf_sucessor_limpo = ''.join(filter(str.isdigit, oficio_validado.cpf_sucessor))
                credor_cpf_limpo = ''.join(filter(str.isdigit, oficio_validado.credor_cpf_cnpj))

                if cpf_sucessor_limpo == credor_cpf_limpo:
                    logger.warning(f"⚠️ V2.7.3: cpf_sucessor ({oficio_validado.cpf_sucessor}) "
                                 f"é IGUAL a credor_cpf_cnpj ({oficio_validado.credor_cpf_cnpj}) → Zeran do!")
                    oficio_validado.cpf_sucessor = None
                    oficio_validado.habilitacao_herdeiros = False
                    logger.info("✅ V2.7.3: cpf_sucessor zerado (mesmo CPF do credor)")

            logger.info(f"✅ Campos V2.5.3 adicionados: obito={oficio_validado.obito}, "
                       f"doenca_grave={oficio_validado.doenca_grave}, "
                       f"data_obito={oficio_validado.data_obito}, "
                       f"cpf_sucessor={oficio_validado.cpf_sucessor}")

            if tracker:
                tracker.adicionar_subsecao("Campos V2.5.3:", nivel=0)
                tracker.adicionar_detalhes("Doença Grave", oficio_validado.doenca_grave, nivel=1)
                tracker.adicionar_detalhes("Óbito", oficio_validado.obito, nivel=1)
                tracker.adicionar_detalhes("Data Óbito", oficio_validado.data_obito or "N/A", nivel=1)
                tracker.adicionar_detalhes("CPF Sucessor", oficio_validado.cpf_sucessor or "N/A", nivel=1)

            # 8.2.1. V2.5.2: Detectar saldo final com fallback
            if not oficio_validado.saldo_final:
                # Tentar detectar saldo final via regex no texto completo
                saldo_detectado = self.detector_saldo.extrair_saldo_final(texto_completo_pdf)
                if saldo_detectado:
                    oficio_validado.saldo_final = saldo_detectado
                    logger.info(f"💰 Saldo Final detectado via regex: R$ {saldo_detectado:,.2f}")
                    if tracker:
                        tracker.adicionar_detalhes("Saldo Final", saldo_detectado, nivel=0)
                        tracker.adicionar_item("(detectado via regex)", nivel=1)
                elif oficio_validado.valor_total_requisitado:
                    # Fallback: usar valor_total_requisitado
                    oficio_validado.saldo_final = oficio_validado.valor_total_requisitado
                    logger.info(f"📊 Saldo Final (fallback): R$ {oficio_validado.saldo_final:,.2f} (= valor_total_requisitado)")
                    if tracker:
                        tracker.adicionar_detalhes("Saldo Final (fallback)", oficio_validado.saldo_final, nivel=0)
                        tracker.adicionar_item("(= valor_total_requisitado)", nivel=1)
                else:
                    logger.warning("⚠️ Saldo Final não detectado e valor_total_requisitado ausente")
                    if tracker:
                        tracker.adicionar_item("Saldo Final não detectado", nivel=0, emoji="⚠️")
            
            # 8.3. V2.5.1: Preencher observações e campos vazios com "ERRO"
            observacoes_lista = []
            campos_erro = []
            
            # Detectar PDF antigo
            if pdf_antigo:
                observacoes_lista.append("PDF antigo (formato 7xxxxxx) - estrutura diferente")
            
            # Detectar CPF não encontrado
            if not oficio_validado.credor_cpf_cnpj:
                campos_erro.append("credor_cpf_cnpj")
                oficio_validado.credor_cpf_cnpj = "ERRO"
            
            # Detectar campos importantes vazios
            # V2.7.2: requerente_caps REMOVIDO do schema
            campos_importantes = {
                # 'requerente_caps': 'Nome do credor',  # V2.7.2: REMOVIDO
                'valor_total_requisitado': 'Valor total',
                'data_nascimento': 'Data de nascimento',
                'banco': 'Banco',
                'agencia': 'Agência',
                'conta': 'Conta'
            }

            for campo, descricao in campos_importantes.items():
                valor = getattr(oficio_validado, campo, None)
                if valor is None or valor == '' or valor == 0:
                    campos_erro.append(campo)
                    # Preencher com "ERRO" apenas campos de texto
                    if campo in ['banco', 'agencia', 'conta']:  # V2.7.2: requerente_caps removido
                        setattr(oficio_validado, campo, "ERRO")
            
            # Montar mensagem de observações
            if campos_erro:
                observacoes_lista.append(f"Campos não extraídos: {', '.join(campos_erro)}")
            
            if observacoes_lista:
                oficio_validado.observacoes = " | ".join(observacoes_lista)
                logger.warning(f"⚠️ Observações: {oficio_validado.observacoes}")
            
            # 9. Retornar resultado de sucesso
            logger.info("✅ Processamento V2 concluído com sucesso!")

            # Tracker: Finalizar com conclusão V2.5.2
            tempo_total = time.time() - inicio
            if tracker:
                tracker.finalizar(
                    sucesso=True,
                    tempo_total=tempo_total,
                    dados=oficio_validado.model_dump()
                )

            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": True,
                "cpf_validado": True,
                "dados": oficio_validado.model_dump(),
                "tempo_processamento": tempo_total,
                "num_oficios": len(todos_oficios)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento V2: {e}")
            self._gravar_log_banco(cpf_numerico,f" Erro no processamento V2: {e}")
            import traceback
            traceback.print_exc()

            # Tracker: Finalizar com erro
            tempo_total = time.time() - inicio
            if tracker:
                tracker.adicionar_erro(str(e))
                tracker.finalizar(sucesso=False, tempo_total=tempo_total)

            return {
                "cpf": cpf_numerico,
                "pdf": Path(pdf_path).name,
                "sucesso": False,
                "cpf_validado": False,
                "erro": str(e),
                "tempo_processamento": tempo_total,
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
                self._gravar_log_banco(cpf,f"CPF inválido: {cpf} (deve ter 11 dígitos)")
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
        numero_processo = Path(pdf_path).stem
        self._atualizar_estado_consulta_esaj(cpf, numero_processo, 'MANUAL_PROCESS')
        self._registrar_ocr_no_tracking(cpf, numero_processo, erro)

        return {
            "cpf": cpf,
            "pdf": Path(pdf_path).name,
            "sucesso": False,
            "cpf_validado": False,
            "erro": erro,
            "tempo_processamento": 0,
            "num_oficios": 0
        }
    
    def _normalizar_valores_brasileiros(self, texto: str) -> str:
        """
        Normaliza valores monetários brasileiros para formato que LLM entende.
        
        Converte: R$ 62.606,38 → R$ 62606.38
        
        PROBLEMA: LLMs interpretam ponto (.) como decimal (formato americano)
        SOLUÇÃO: Remover pontos de milhares e converter vírgula para ponto
        
        Args:
            texto: Texto com valores no formato brasileiro
            
        Returns:
            Texto com valores normalizados (formato americano)
            
        Exemplos:
            "R$ 62.606,38" → "R$ 62606.38"
            "R$ 1.234.567,89" → "R$ 1234567.89"
            "R$ 73.431,66" → "R$ 73431.66"
        """
        # Pattern: R$ + espaços opcionais + número com pontos/vírgulas
        # Captura: 1-3 dígitos, seguido de grupos de .XXX, terminando com ,XX
        pattern = r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)'
        
        def converter_match(match):
            valor_br = match.group(1)
            # Remove pontos (separador de milhares)
            valor_sem_pontos = valor_br.replace('.', '')
            # Substitui vírgula por ponto (separador decimal)
            valor_normalizado = valor_sem_pontos.replace(',', '.')
            return f"R$ {valor_normalizado}"
        
        texto_normalizado = re.sub(pattern, converter_match, texto)
        return texto_normalizado
    
    def _filtrar_requerente_processamento(self, texto_processamento: str) -> str:
        """
        Filtra o campo "Requerente" do texto de PROCESSAMENTO para evitar confusão em PDFs multi-creditor.
        
        FIX v2.4.3: Em PDFs com múltiplos credores, o PROCESSAMENTO lista o "Requerente" GERAL
        (ex: "Maria das Dores e outros"), que é diferente do credor específico do ofício
        (ex: "Roberto Pereira da Cruz"). Isso causa confusão no LLM, que prioriza o campo
        "Requerente" sobre o campo "Nome" do ofício.
        
        Args:
            texto_processamento: Texto original do PROCESSAMENTO
            
        Returns:
            Texto filtrado com campo "Requerente" substituído
        """
        # Padrões para detectar linha com "Requerente"
        # Exemplos:
        # "Requerente\nMaria das Dores Coutinho Silva e outros"
        # "Requerente: Maria das Dores Coutinho Silva e outros"
        # "Requerente Maria das Dores Coutinho Silva e outros"
        
        # Substituir linha completa do requerente
        texto_filtrado = re.sub(
            r'Requerente[:\s]*\n?[^\n]+',
            'Requerente: [VIDE OFÍCIO PARA CREDOR ESPECÍFICO]',
            texto_processamento,
            flags=re.IGNORECASE
        )
        
        logger.debug("🔧 Filtro aplicado: Campo 'Requerente' do PROCESSAMENTO substituído")
        return texto_filtrado
    
    def _extrair_dados_llm_hibrido(
        self,
        texto_oficio: str,
        tem_anexo_ii: bool = False,
        tem_processamento: bool = False,
        numero_ordem_titulo: Optional[str] = None,
        numero_ordem_global: Optional[str] = None,  # V2.7.3
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extração híbrida: Gemini 2.5 Flash (primeiro) com fallback para GPT-4o-mini.

        V2.7.3: Aceita numero_ordem_global para hint ao LLM
        NOVA em FINDING 08: Combina qualidade do Gemini (13 campos, grátis)
        com confiabilidade do OpenAI (12 campos, 100% sucesso).

        Args:
            texto_oficio: Texto relevante (ofício + ANEXO II + PROCESSAMENTO)
            tem_anexo_ii: Se ANEXO II está presente
            tem_processamento: Se PROCESSAMENTO está presente
            numero_ordem_titulo: Número de ordem extraído do título (PDFs antigos)
            numero_ordem_global: Número de ordem encontrado via busca global (V2.7.3)
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
                numero_ordem_titulo, numero_ordem_global, oficio_rejeitado, motivo_rejeicao
            )

        # Construir prompt (mesmo prompt para ambos LLMs)
        prompt = self._construir_prompt_llm(
            texto_oficio, tem_anexo_ii, tem_processamento,
            numero_ordem_titulo, numero_ordem_global, oficio_rejeitado, motivo_rejeicao
        )
        
        # TENTATIVA 1: Gemini 2.5 Flash (mais completo, grátis)
        try:
            logger.info("🔄 Tentando extração com Gemini 2.5 Flash...")
            dados = self.llm_adapter.extract_structured_data(
                prompt,
                provider=self.llm_provider_enum.GEMINI
            )
            logger.info("✅ Gemini: Extração bem-sucedida!")

            # V2.6.0: Aplicar verificação de tipos
            dados = self._verificar_e_corrigir_tipos(dados)

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

            # V2.6.0: Aplicar verificação de tipos
            dados = self._verificar_e_corrigir_tipos(dados)

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
        numero_ordem_global: Optional[str] = None,  # V2.7.3
        oficio_rejeitado: bool = False,
        motivo_rejeicao: Optional[str] = None
    ) -> str:
        """
        Constrói prompt para extração LLM (usado por ambos OpenAI e Gemini).

        V2.7.3: Adiciona numero_ordem_global como hint quando busca global encontra

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

        # V2.7.3: Adicionar hint sobre numero_ordem se encontrado
        nota_numero_ordem = ""
        if numero_ordem_titulo:
            nota_numero_ordem = f"""
✅ NÚMERO DE ORDEM JÁ DETECTADO NO TÍTULO: {numero_ordem_titulo}
- Use este valor para o campo numero_ordem
"""
        elif numero_ordem_global:
            nota_numero_ordem = f"""
✅ NÚMERO DE ORDEM DETECTADO VIA BUSCA GLOBAL: {numero_ordem_global}
- Use este valor para o campo numero_ordem
- Foi encontrado em CERTIDÃO DE PUBLICAÇÃO ou outra seção do PDF
"""

        # Prompt completo
        return f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

{nota_rejeicao}{nota_anomalia}{nota_numero_ordem}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
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

⚠️⚠️⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Em português brasileiro, o PONTO (.) é separador de MILHARES e a VÍRGULA (,) é separador de DECIMAIS!

EXEMPLOS CORRETOS - SIGA EXATAMENTE ESTE PADRÃO:

NO PDF:              RETORNE COMO:
"R$ 73.431,66"    →  73431.66  (NUMBER, não string!)
"R$ 88.994,41"    →  88994.41  (NUMBER, não string!)
"R$ 1.234.567,89" →  1234567.89 (NUMBER, não string!)
"R$ 190.221,42"   →  190221.42  (NUMBER, não string!)
"R$ 177.969,22"   →  177969.22  (NUMBER, não string!)

❌❌❌ EXEMPLOS ERRADOS (NÃO FAÇA ISTO): ❌❌❌

"R$ 73.431,66"    →  73.43     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 88.994,41"    →  88.99     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 73.431,66"    →  "73431.66" ❌ ERRADO! (é string, deve ser NUMBER)
"R$ 177.969,22"   →  17796     ❌ ERRADO! (esqueceu decimais)

VERIFICAÇÃO OBRIGATÓRIA:
1. Todos valores monetários são NÚMEROS (type: number), NÃO strings
2. Valores realistas: R$ 1.000 a R$ 10.000.000 (se < R$ 100, REVISE!)
3. Líquido ≤ Bruto (se líquido > bruto, INVERTEU OS CAMPOS!)

ATENÇÃO - LÍQUIDO vs BRUTO:
- Valor Principal LÍQUIDO = APÓS descontos (sempre ≤ bruto)
- Valor Principal BRUTO = ANTES de descontos (sempre ≥ líquido)

⚠️⚠️⚠️ ATENÇÃO CRÍTICA: PDFs MULTI-CREDITOR ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Este PDF pode conter MÚLTIPLOS CREDORES (até 52 credores em um único processo).

🔴 PRIORIDADE MÁXIMA - IDENTIFICAÇÃO DO CREDOR CORRETO:

1. O campo "Requerente" no PROCESSAMENTO refere-se ao REQUERENTE GERAL (todos os credores juntos)
   Exemplo: "Requerente: Maria das Dores e outros" = Maria + 51 outros credores

2. O campo "Nome:" no OFÍCIO refere-se ao CREDOR ESPECÍFICO que você deve extrair
   Exemplo: "Nome: Roberto Pereira da Cruz" = credor #26 de 52

3. V2.7.4: Campo requerente_caps REMOVIDO (usamos apenas credor_nome)
   NUNCA use o campo "Requerente:" do PROCESSAMENTO

4. Se encontrar "Credor n°: XX" ou "Credor nº: XX", esse é o credor específico

EXEMPLO DE CONFUSÃO (NÃO FAÇA ISTO):
```
❌ ERRADO:
Ofício: "Credor nº: 26, Nome: Roberto Pereira da Cruz"
PROCESSAMENTO: "Requerente: Maria das Dores e outros"
→ V2.7.4: requerente_caps REMOVIDO

✅ CORRETO:
Ofício: "Credor nº: 26, Nome: Roberto Pereira da Cruz"
PROCESSAMENTO: "Requerente: [VIDE OFÍCIO PARA CREDOR ESPECÍFICO]"
→ V2.7.4: requerente_caps REMOVIDO
```

⚠️⚠️⚠️ ATENÇÃO: DADOS BANCÁRIOS INLINE (SEM ANEXO II SEPARADO) ⚠️⚠️⚠️

IMPORTANTE: Alguns ofícios contêm dados bancários INLINE (na mesma página do ofício),
NÃO em ANEXO II separado. Isso é comum em PDFs multi-creditor.

PROCURE POR ESTES PADRÕES NO TEXTO DO OFÍCIO:

PADRÃO INLINE TÍPICO (PROCURE NO OFÍCIO):
- "Credor n°: XX" ou "Credor nº: XX"
- "Nome: [NOME COMPLETO]" ← Extrair para credor_nome
- "CPF/CNPJ: XXX.XXX.XXX-XX" ← EXTRAIA PARA credor_cpf_cnpj
- "Data do nascimento: DD/MM/AAAA" ← EXTRAIA PARA data_nascimento (converta para AAAA-MM-DD)
- "Banco: XXX" ou "Banco: [NOME DO BANCO]"
- "Agência: XXXX" ou "Ag.: XXXX"
- "Conta: XXXXX-X" ou "C/C: XXXXX-X"
- "Valor requisitado: R$ X.XXX,XX"
- "Valor total da condenação: R$ X.XXX,XX"

🔴 ATENÇÃO ESPECIAL - CPF E DATA DE NASCIMENTO:
Estes campos aparecem logo após "Nome:" no formato:
```
Nome: Roberto Pereira da Cruz
CPF/CNPJ: 037.304.618-93
Data do nascimento: 30/07/1960
```

SEMPRE extraia estes campos quando presentes no ofício!
- CPF/CNPJ → campo credor_cpf_cnpj (mantenha formatação: XXX.XXX.XXX-XX)
- Data do nascimento → campo data_nascimento (converta DD/MM/AAAA para AAAA-MM-DD)

REGRAS PARA DADOS INLINE:
1. Se há ANEXO II separado → use dados do ANEXO II (prioridade)
2. Se NÃO há ANEXO II → procure dados inline no ofício
3. V2.7.4: Campo requerente_caps REMOVIDO (usamos apenas credor_nome)
4. SEMPRE extraia CPF/CNPJ e Data do nascimento se presentes no ofício
5. Extraia TODOS os campos disponíveis (banco, agência, conta, valores)
6. Se encontrar "Credor n°: XX", extraia os dados desse credor específico

EXEMPLO DE EXTRAÇÃO INLINE:
```
Texto: "Credor n°: 26
Nome: Roberto Pereira da Cruz
CPF/CNPJ: 037.304.618-93
Banco: 001 - Banco do Brasil
Agência: 1234-5
Conta: 98765-4
Valor requisitado: R$ 52.228,43"

→ Extrair:
{{
  // V2.7.4: requerente_caps REMOVIDO
  "credor_nome": "ROBERTO PEREIRA DA CRUZ",
  "credor_cpf_cnpj": "037.304.618-93",
  "banco": "001",
  "agencia": "1234-5",
  "conta": "98765-4",
  "valor_total_requisitado": 52228.43
}}
```

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
- vara: Vara responsável (Busque no CABEÇALHO/Endereçamento: "Excelentíssimo... da X Vara...", "Juízo da X Vara...")
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
        numero_ordem_global: Optional[str] = None,  # V2.7.3
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
            
            # 🔍 DEBUG: Log do texto enviado ao LLM
            logger.info(f"📝 Texto enviado ao LLM: {len(texto_oficio)} caracteres")
            logger.info(f"   📋 Primeiros 300 chars: {texto_oficio[:300]}")
            logger.info(f"   📋 Últimos 300 chars: {texto_oficio[-300:]}")

            # V2.7.3: Adicionar hint sobre numero_ordem se encontrado
            nota_numero_ordem = ""
            if numero_ordem_titulo:
                nota_numero_ordem = f"""
✅ NÚMERO DE ORDEM JÁ DETECTADO NO TÍTULO: {numero_ordem_titulo}
- Use este valor para o campo numero_ordem
"""
            elif numero_ordem_global:
                nota_numero_ordem = f"""
✅ NÚMERO DE ORDEM DETECTADO VIA BUSCA GLOBAL: {numero_ordem_global}
- Use este valor para o campo numero_ordem
- Foi encontrado em CERTIDÃO DE PUBLICAÇÃO ou outra seção do PDF
"""

            # Prompt V2 otimizado
            prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

IMPORTANTE: Retorne JSON com estrutura FLAT (campos no nível raiz), NÃO use objetos aninhados!

{nota_rejeicao}{nota_anomalia}{nota_numero_ordem}

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo

=== CAMPOS OBRIGATÓRIOS (nível raiz do JSON) ===

- processo_origem: Número CNJ do processo (formato: 0000000-00.0000.0.00.0000)
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

⚠️⚠️⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Em português brasileiro, o PONTO (.) é separador de MILHARES e a VÍRGULA (,) é separador de DECIMAIS!

EXEMPLOS CORRETOS - SIGA EXATAMENTE ESTE PADRÃO:

NO PDF:              RETORNE COMO:
"R$ 73.431,66"    →  73431.66  (NUMBER, não string!)
"R$ 88.994,41"    →  88994.41  (NUMBER, não string!)
"R$ 1.234.567,89" →  1234567.89 (NUMBER, não string!)
"R$ 190.221,42"   →  190221.42  (NUMBER, não string!)
"R$ 177.969,22"   →  177969.22  (NUMBER, não string!)

❌❌❌ EXEMPLOS ERRADOS (NÃO FAÇA ISTO): ❌❌❌

"R$ 73.431,66"    →  73.43     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 88.994,41"    →  88.99     ❌ ERRADO! (truncou, interpretou ponto como decimal)
"R$ 73.431,66"    →  "73431.66" ❌ ERRADO! (é string, deve ser NUMBER)
"R$ 177.969,22"   →  17796     ❌ ERRADO! (esqueceu decimais)

VERIFICAÇÃO OBRIGATÓRIA:
1. Todos valores monetários são NÚMEROS (type: number), NÃO strings
2. Valores realistas: R$ 1.000 a R$ 10.000.000 (se < R$ 100, REVISE!)
3. Líquido ≤ Bruto (se líquido > bruto, INVERTEU OS CAMPOS!)

ATENÇÃO - LÍQUIDO vs BRUTO:
- Valor Principal LÍQUIDO = APÓS descontos (sempre ≤ bruto)
- Valor Principal BRUTO = ANTES de descontos (sempre ≥ líquido)

⚠️⚠️⚠️ ATENÇÃO CRÍTICA: PDFs MULTI-CREDITOR ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Este PDF pode conter MÚLTIPLOS CREDORES (até 52 credores em um único processo).

🔴 PRIORIDADE MÁXIMA - IDENTIFICAÇÃO DO CREDOR CORRETO:

1. O campo "Requerente" no PROCESSAMENTO refere-se ao REQUERENTE GERAL (todos os credores juntos)
   Exemplo: "Requerente: Maria das Dores e outros" = Maria + 51 outros credores

2. O campo "Nome:" no OFÍCIO refere-se ao CREDOR ESPECÍFICO que você deve extrair
   Exemplo: "Nome: Roberto Pereira da Cruz" = credor #26 de 52

3. V2.7.4: Campo requerente_caps REMOVIDO (usamos apenas credor_nome)
   NUNCA use o campo "Requerente:" do PROCESSAMENTO

4. Se encontrar "Credor n°: XX" ou "Credor nº: XX", esse é o credor específico

EXEMPLO DE CONFUSÃO (NÃO FAÇA ISTO):
```
❌ ERRADO:
Ofício: "Credor nº: 26, Nome: Roberto Pereira da Cruz"
PROCESSAMENTO: "Requerente: Maria das Dores e outros"
→ V2.7.4: requerente_caps REMOVIDO

✅ CORRETO:
Ofício: "Credor nº: 26, Nome: Roberto Pereira da Cruz"
PROCESSAMENTO: "Requerente: [VIDE OFÍCIO PARA CREDOR ESPECÍFICO]"
→ V2.7.4: requerente_caps REMOVIDO
```

⚠️⚠️⚠️ ATENÇÃO: DADOS BANCÁRIOS INLINE (SEM ANEXO II SEPARADO) ⚠️⚠️⚠️

IMPORTANTE: Alguns ofícios contêm dados bancários INLINE (na mesma página do ofício),
NÃO em ANEXO II separado. Isso é comum em PDFs multi-creditor.

PROCURE POR ESTES PADRÕES NO TEXTO DO OFÍCIO:

PADRÃO INLINE TÍPICO (PROCURE NO OFÍCIO):
- "Credor n°: XX" ou "Credor nº: XX"
- "Nome: [NOME COMPLETO]" ← Extrair para credor_nome
- "CPF/CNPJ: XXX.XXX.XXX-XX" ← EXTRAIA PARA credor_cpf_cnpj
- "Data do nascimento: DD/MM/AAAA" ← EXTRAIA PARA data_nascimento (converta para AAAA-MM-DD)
- "Banco: XXX" ou "Banco: [NOME DO BANCO]"
- "Agência: XXXX" ou "Ag.: XXXX"
- "Conta: XXXXX-X" ou "C/C: XXXXX-X"
- "Valor requisitado: R$ X.XXX,XX"
- "Valor total da condenação: R$ X.XXX,XX"

🔴 ATENÇÃO ESPECIAL - CPF E DATA DE NASCIMENTO:
Estes campos aparecem logo após "Nome:" no formato:
```
Nome: Roberto Pereira da Cruz
CPF/CNPJ: 037.304.618-93
Data do nascimento: 30/07/1960
```

SEMPRE extraia estes campos quando presentes no ofício!
- CPF/CNPJ → campo credor_cpf_cnpj (mantenha formatação: XXX.XXX.XXX-XX)
- Data do nascimento → campo data_nascimento (converta DD/MM/AAAA para AAAA-MM-DD)

REGRAS PARA DADOS INLINE:
1. Se há ANEXO II separado → use dados do ANEXO II (prioridade)
2. Se NÃO há ANEXO II → procure dados inline no ofício
3. V2.7.4: Campo requerente_caps REMOVIDO (usamos apenas credor_nome)
4. SEMPRE extraia CPF/CNPJ e Data do nascimento se presentes no ofício
5. Extraia TODOS os campos disponíveis (banco, agência, conta, valores)
6. Se encontrar "Credor n°: XX", extraia os dados desse credor específico

EXEMPLO DE EXTRAÇÃO INLINE:
```
Texto: "Credor n°: 26
Nome: Roberto Pereira da Cruz
CPF/CNPJ: 037.304.618-93
Banco: 001 - Banco do Brasil
Agência: 1234-5
Conta: 98765-4
Valor requisitado: R$ 52.228,43"

→ Extrair:
{{
  // V2.7.4: requerente_caps REMOVIDO
  "credor_nome": "ROBERTO PEREIRA DA CRUZ",
  "credor_cpf_cnpj": "037.304.618-93",
  "banco": "001",
  "agencia": "1234-5",
  "conta": "98765-4",
  "valor_total_requisitado": 52228.43
}}
```

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
  // V2.7.4: requerente_caps REMOVIDO
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
            
            # V3.0.2: Adicionar flag de rejeição + motivo (truncado para 500 chars)
            if oficio_rejeitado:
                dados['rejeitado'] = True
                # Usar motivo extraído por regex se LLM não retornou
                if motivo_rejeicao and not dados.get('motivo_rejeicao'):
                    dados['motivo_rejeicao'] = motivo_rejeicao
                # V3.0.2: GARANTIR truncamento em 500 chars (LLM pode retornar texto longo)
                if dados.get('motivo_rejeicao') and len(dados['motivo_rejeicao']) > 500:
                    dados['motivo_rejeicao'] = dados['motivo_rejeicao'][:497] + "..."
                    logger.warning(f"⚠️ V3.0.2: motivo_rejeicao truncado para 500 chars (Pydantic limit)")
            
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

    def _verificar_e_corrigir_tipos(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        V2.6.0 - MELHORIA #2: Verifica e corrige tipos de dados (especialmente valores monetários).

        Garante que:
        - Valores monetários são numbers (não strings)
        - Strings numéricas são convertidas para float
        - Valores None/null são preservados

        Args:
            dados: Dicionário com dados extraídos do LLM

        Returns:
            Dados com tipos corrigidos
        """
        campos_monetarios = [
            'valor_principal_liquido',
            'valor_principal_bruto',
            'juros_moratorios',
            'valor_total_requisitado',
            'saldo_final',
            'contrib_previdenciaria_iprem',
            'contrib_previdenciaria_hspm',
            'valor_compensado',
            'contribuicao_social',
            'salario_pericial',
            'assist_tecnico',
            'custas',
            'despesas',
            'multas'
        ]

        for campo in campos_monetarios:
            if campo in dados and dados[campo] is not None:
                valor = dados[campo]

                # Se for string, tentar converter
                if isinstance(valor, str):
                    logger.warning(f"🔧 V2.6.0: {campo} retornado como STRING: '{valor}' - convertendo...")

                    try:
                        # Limpar e converter
                        valor_limpo = valor.replace('R$', '').replace(' ', '').strip()

                        # Formato brasileiro: trocar . por nada e , por .
                        if ',' in valor_limpo:
                            valor_limpo = valor_limpo.replace('.', '').replace(',', '.')

                        valor_convertido = float(valor_limpo)
                        dados[campo] = valor_convertido
                        logger.info(f"   ✅ Convertido para: {valor_convertido}")

                    except (ValueError, AttributeError) as e:
                        logger.error(f"   ❌ Erro ao converter '{valor}': {e}")
                        dados[campo] = None

                # Se for int, converter para float
                elif isinstance(valor, int):
                    dados[campo] = float(valor)

        return dados

    def _validar_sanidade_valores(
        self,
        dados: Dict[str, Any],
        cpf: str,
        processo: str
    ) -> List[str]:
        """
        V2.6.0 - MELHORIA #3: Validação de sanidade para detectar parsing incorreto.

        Verifica:
        1. Valores muito baixos (< R$ 100 ou < R$ 1.000)
        2. Inversão líquido/bruto
        3. Inconsistência entre total declarado e calculado
        4. Valores zerados em campos obrigatórios

        Args:
            dados: Dicionário com dados extraídos
            cpf: CPF do processo (para logging)
            processo: Número do processo (para logging)

        Returns:
            Lista de alertas de sanidade
        """
        alertas = []

        # Extrair valores
        liquido = dados.get('valor_principal_liquido') or 0
        bruto = dados.get('valor_principal_bruto') or 0
        juros = dados.get('juros_moratorios') or 0
        total = dados.get('valor_total_requisitado') or 0

        # 1. Verificar valores muito baixos (possível parsing incorreto)
        if liquido > 0 and liquido < 100:
            alertas.append(
                f"🚨 CRÍTICO: Valor líquido R$ {liquido:,.2f} < R$ 100 "
                f"(possível parsing incorreto! Ex: 73.431,66 → 73,43)"
            )
        elif liquido > 0 and liquido < 1000:
            alertas.append(
                f"⚠️  SUSPEITO: Valor líquido R$ {liquido:,.2f} < R$ 1.000 "
                f"(revisar se não foi truncado)"
            )

        if bruto > 0 and bruto < 100:
            alertas.append(
                f"🚨 CRÍTICO: Valor bruto R$ {bruto:,.2f} < R$ 100 "
                f"(possível parsing incorreto!)"
            )
        elif bruto > 0 and bruto < 1000:
            alertas.append(
                f"⚠️  SUSPEITO: Valor bruto R$ {bruto:,.2f} < R$ 1.000 "
                f"(revisar se não foi truncado)"
            )

        if total > 0 and total < 100:
            alertas.append(
                f"🚨 CRÍTICO: Valor total R$ {total:,.2f} < R$ 100 "
                f"(possível parsing incorreto!)"
            )
        elif total > 0 and total < 1000:
            alertas.append(
                f"⚠️  SUSPEITO: Valor total R$ {total:,.2f} < R$ 1.000"
            )

        # 2. Verificar inversão líquido/bruto
        if liquido > 0 and bruto > 0 and liquido > bruto:
            alertas.append(
                f"🚨 INVERSÃO DETECTADA: Líquido (R$ {liquido:,.2f}) > Bruto (R$ {bruto:,.2f}) "
                f"- CAMPOS INVERTIDOS!"
            )

        # 3. Verificar consistência de totais (com tolerância de R$ 500)
        if total > 0 and bruto > 0:
            total_calculado = bruto + juros
            diferenca = abs(total - total_calculado)

            if diferenca > 500:
                alertas.append(
                    f"⚠️  INCONSISTÊNCIA: Total declarado (R$ {total:,.2f}) vs "
                    f"calculado (R$ {total_calculado:,.2f}) - diferença: R$ {diferenca:,.2f}"
                )

        # 4. Verificar valores zerados em campos importantes
        if liquido == 0 and bruto == 0:
            alertas.append(
                f"🚨 CRÍTICO: Valores principal líquido e bruto ZERADOS "
                f"(possível falha na extração!)"
            )

        if total == 0:
            alertas.append(
                f"⚠️  ATENÇÃO: Valor total requisitado ZERADO"
            )

        return alertas

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
