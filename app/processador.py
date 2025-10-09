"""
ProcessadorOficio - Pipeline completo para extração de dados de Ofícios Requisitórios.
Implementação conforme AGENTS.md: detectar → extract (LLM) → validar → salvar.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI

from .detector import DetectorOficio
from .detector_anexo import DetectorAnexoII
from .schemas import OficioRequisitorio, ProcessoMetadata, OficioCompleto


logger = logging.getLogger(__name__)


class ProcessadorOficio:
    """
    Pipeline completo para processamento de Ofícios Requisitórios:
    1. Detectar ofício no PDF (DetectorOficio)
    2. Extrair dados estruturados (GPT-5 Nano)
    3. Validar dados (Pydantic)
    4. Salvar no PostgreSQL (upsert)
    """
    
    def __init__(self, openai_api_key: str, db_config: Dict[str, Any]):
        """
        Inicializa o processador com configurações necessárias.
        
        Args:
            openai_api_key: Chave da API OpenAI
            db_config: Configurações do banco PostgreSQL
        """
        # Inicializar OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        self.modelo_gpt = "gpt-5-nano-2025-08-07"  # Conforme AGENTS.md
        
        # Configurações do banco
        self.db_config = db_config
        
        # Inicializar detectores
        self.detector = DetectorOficio()
        self.detector_anexo = DetectorAnexoII()

        logger.info("ProcessadorOficio inicializado com suporte a ANEXO II")
    
    def processar_arquivo(self, pdf_path: str) -> Optional[OficioCompleto]:
        """
        Processa um único arquivo PDF extraindo dados do ofício requisitório.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            OficioCompleto se processamento bem-sucedido, None caso contrário
        """
        try:
            logger.info(f"Iniciando processamento de: {pdf_path}")
            
            # Validar arquivo PDF
            if not self.detector.validar_pdf(pdf_path):
                logger.error(f"PDF inválido: {pdf_path}")
                return None
            
            # Extrair metadados do caminho
            metadata = self._extrair_metadata_arquivo(pdf_path)
            if not metadata:
                logger.error(f"Erro ao extrair metadados: {pdf_path}")
                return None
            
            # Detectar ofício no PDF
            paginas_oficio, texto_oficio = self.detector.detectar_oficio(pdf_path)
            
            if not paginas_oficio:
                logger.warning(f"Nenhum ofício detectado em: {pdf_path}")
                # Registrar erro mas continuar processamento
                metadata.paginas_oficio = []
                metadata.texto_completo_oficio = ""
                metadata.processado = False
                return OficioCompleto(
                    metadata=metadata,
                    oficio=None
                )
            
            # Atualizar metadata com dados detectados
            metadata.paginas_oficio = paginas_oficio
            metadata.texto_completo_oficio = texto_oficio

            # Detectar ANEXO II (opcional - nem todos os processos têm)
            paginas_anexo, texto_anexo = self.detector_anexo.detectar_anexo_ii(pdf_path)

            # Combinar textos para extração completa
            texto_completo = texto_oficio
            if texto_anexo:
                logger.info(f"ANEXO II encontrado em {len(paginas_anexo)} página(s)")
                texto_completo += f"\n\n=== ANEXO II ===\n\n{texto_anexo}"

            # Extrair dados estruturados com LLM
            logger.info(f"Enviando {len(texto_completo)} chars para GPT-5 Nano")
            dados_oficio = self._extrair_dados_llm(texto_completo, tem_anexo_ii=bool(texto_anexo))
            
            if not dados_oficio:
                logger.error(f"Falha na extração LLM: {pdf_path}")
                metadata.processado = False
                return OficioCompleto(
                    metadata=metadata,
                    oficio=None
                )
            
            # Validar dados com Pydantic
            try:
                oficio_validado = OficioRequisitorio(**dados_oficio)
                logger.info("Dados validados com sucesso")
            except Exception as e:
                logger.error(f"Erro na validação Pydantic: {e}")
                metadata.processado = False
                return OficioCompleto(
                    metadata=metadata,
                    oficio=None
                )
            
            # Criar objeto completo
            metadata.processado = True
            oficio_completo = OficioCompleto(
                metadata=metadata,
                oficio=oficio_validado
            )
            
            logger.info(f"Processamento concluído com sucesso: {pdf_path}")
            return oficio_completo
            
        except Exception as e:
            logger.error(f"Erro no processamento de {pdf_path}: {e}")
            return None
    
    def _extrair_metadata_arquivo(self, pdf_path: str) -> Optional[ProcessoMetadata]:
        """
        Extrai metadados do arquivo conforme estrutura definida:
        ./Processos/{cpf_numerico}/{numero_processo_cnj}.pdf
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            ProcessoMetadata ou None se extração falhar
        """
        try:
            path = Path(pdf_path)
            
            # Extrair CPF da pasta (apenas números)
            cpf = path.parent.name
            if not cpf.isdigit() or len(cpf) != 11:
                logger.error(f"CPF inválido na pasta: {cpf}")
                return None
            
            # Extrair número do processo do arquivo
            numero_processo = path.stem
            
            # Criar metadata
            metadata = ProcessoMetadata(
                cpf=cpf,
                numero_processo=numero_processo,
                texto_completo_oficio="",  # Será preenchido após detecção
                paginas_oficio=[],  # Será preenchido após detecção
                processado=False
            )
            
            logger.debug(f"Metadata extraída - CPF: {cpf}, Processo: {numero_processo}")
            return metadata
            
        except Exception as e:
            logger.error(f"Erro ao extrair metadata de {pdf_path}: {e}")
            return None
    
    def _extrair_dados_llm(self, texto_oficio: str, tem_anexo_ii: bool = False) -> Optional[Dict[str, Any]]:
        """
        Extrai dados estruturados do texto do ofício usando GPT-5 Nano.
        Conforme template do AGENTS.md + dados bancários do ANEXO II.

        Args:
            texto_oficio: Texto completo do ofício (pode incluir ANEXO II)
            tem_anexo_ii: Indica se o texto contém ANEXO II

        Returns:
            Dicionário com dados extraídos ou None se falhar
        """
        try:
            # Adicionar campos bancários se ANEXO II presente
            campos_bancarios = ""
            if tem_anexo_ii:
                campos_bancarios = """
CAMPOS ANEXO II (dados bancários - se presentes):
- banco: Código do banco (apenas números, ex: 341, 001)
- agencia: Número da agência (sem dígito)
- conta: Número da conta com dígito (ex: 12345-6)
- conta_tipo: Tipo da conta (corrente, poupança)"""

            # Template do prompt conforme AGENTS.md
            prompt = f"""Você é um assistente especializado em extrair dados de Ofícios Requisitórios do TJSP.

DOCUMENTO: Ofício Requisitório do Tribunal de Justiça de São Paulo {' + ANEXO II' if tem_anexo_ii else ''}
FORMATO: JSON válido

CAMPOS OBRIGATÓRIOS:
- processo_origem: Número CNJ (0000000-00.0000.0.00.0000)
- requerente_caps: Nome TODO EM MAIÚSCULAS

CAMPOS OPCIONAIS:
- vara, processo_execucao, processo_conhecimento
- datas (YYYY-MM-DD): data_ajuizamento, data_transito_julgado, data_base_atualizacao
- partes: advogado_nome, advogado_oab (OAB/UF 000.000), credor_nome, credor_cpf_cnpj, devedor_ente
- financeiro (números puros): valor_principal_liquido, valor_principal_bruto, juros_moratorios, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm, valor_total_requisitado
- preferências (bool): idoso, doenca_grave, pcd{campos_bancarios}

REGRAS:
- Campos não encontrados = null
- Valores numéricos sem R$, sem pontos de milhar, sem vírgulas (usar ponto decimal)
- Requerente SEMPRE em MAIÚSCULAS
- Dados bancários extrair do ANEXO II se disponível

DOCUMENTO:
{texto_oficio}

Retorne APENAS JSON válido:"""

            # Fazer chamada para GPT-5 Nano
            response = self.client.chat.completions.create(
                model=self.modelo_gpt,
                messages=[{"role": "user", "content": prompt}]
                # GPT-5 Nano usa temperatura padrão (1), não suporta temperature=0
            )
            
            # Extrair resposta
            json_response = response.choices[0].message.content
            
            # Strip markdown code blocks conforme AGENTS.md
            json_response = json_response.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            dados = json.loads(json_response)
            
            logger.debug(f"Dados extraídos pelo LLM: {len(dados)} campos")
            return dados
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON do LLM: {e}")
            logger.debug(f"Resposta do LLM: {json_response}")
            return None
        except Exception as e:
            logger.error(f"Erro na chamada LLM: {e}")
            return None
    
    def salvar_postgres(self, oficio: OficioCompleto) -> bool:
        """
        Salva dados no PostgreSQL usando upsert conforme AGENTS.md.
        Primary key: (cpf, numero_processo)
        
        Args:
            oficio: Dados completos do ofício para salvar
            
        Returns:
            True se salvamento bem-sucedido
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # SQL de upsert conforme AGENTS.md
            sql = """
            INSERT INTO lista_processos (
                cpf, numero_processo, vara, processo_execucao, processo_conhecimento,
                data_ajuizamento, data_transito_julgado, requerente_caps, advogado_nome,
                advogado_oab, valor_principal_liquido, valor_principal_bruto,
                juros_moratorios, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
                valor_total_requisitado, data_base_atualizacao, idoso, doenca_grave,
                pcd, texto_completo_oficio, timestamp_processamento, data_envio, processado
            ) VALUES (
                %(cpf)s, %(numero_processo)s, %(vara)s, %(processo_execucao)s, %(processo_conhecimento)s,
                %(data_ajuizamento)s, %(data_transito_julgado)s, %(requerente_caps)s, %(advogado_nome)s,
                %(advogado_oab)s, %(valor_principal_liquido)s, %(valor_principal_bruto)s,
                %(juros_moratorios)s, %(contrib_previdenciaria_iprem)s, %(contrib_previdenciaria_hspm)s,
                %(valor_total_requisitado)s, %(data_base_atualizacao)s, %(idoso)s, %(doenca_grave)s,
                %(pcd)s, %(texto_completo_oficio)s, %(timestamp_processamento)s, %(data_envio)s, %(processado)s
            )
            ON CONFLICT (cpf, numero_processo) DO UPDATE SET
                vara = EXCLUDED.vara,
                processo_execucao = EXCLUDED.processo_execucao,
                processo_conhecimento = EXCLUDED.processo_conhecimento,
                data_ajuizamento = EXCLUDED.data_ajuizamento,
                data_transito_julgado = EXCLUDED.data_transito_julgado,
                requerente_caps = EXCLUDED.requerente_caps,
                advogado_nome = EXCLUDED.advogado_nome,
                advogado_oab = EXCLUDED.advogado_oab,
                valor_principal_liquido = EXCLUDED.valor_principal_liquido,
                valor_principal_bruto = EXCLUDED.valor_principal_bruto,
                juros_moratorios = EXCLUDED.juros_moratorios,
                contrib_previdenciaria_iprem = EXCLUDED.contrib_previdenciaria_iprem,
                contrib_previdenciaria_hspm = EXCLUDED.contrib_previdenciaria_hspm,
                valor_total_requisitado = EXCLUDED.valor_total_requisitado,
                data_base_atualizacao = EXCLUDED.data_base_atualizacao,
                idoso = EXCLUDED.idoso,
                doenca_grave = EXCLUDED.doenca_grave,
                pcd = EXCLUDED.pcd,
                texto_completo_oficio = EXCLUDED.texto_completo_oficio,
                timestamp_processamento = EXCLUDED.timestamp_processamento,
                data_envio = EXCLUDED.data_envio,
                processado = EXCLUDED.processado
            """
            
            # Preparar dados para inserção
            dados = {
                'cpf': oficio.metadata.cpf,
                'numero_processo': oficio.metadata.numero_processo,
                'texto_completo_oficio': oficio.metadata.texto_completo_oficio,
                'timestamp_processamento': oficio.metadata.timestamp_processamento,
                'processado': oficio.metadata.processado,
                'data_envio': oficio.data_envio
            }
            
            # Adicionar dados do ofício se processamento foi bem-sucedido
            if oficio.oficio:
                dados.update({
                    'vara': oficio.oficio.vara,
                    'processo_execucao': oficio.oficio.processo_execucao,
                    'processo_conhecimento': oficio.oficio.processo_conhecimento,
                    'data_ajuizamento': oficio.oficio.data_ajuizamento,
                    'data_transito_julgado': oficio.oficio.data_transito_julgado,
                    'requerente_caps': oficio.oficio.requerente_caps,
                    'advogado_nome': oficio.oficio.advogado_nome,
                    'advogado_oab': oficio.oficio.advogado_oab,
                    'valor_principal_liquido': oficio.oficio.valor_principal_liquido,
                    'valor_principal_bruto': oficio.oficio.valor_principal_bruto,
                    'juros_moratorios': oficio.oficio.juros_moratorios,
                    'contrib_previdenciaria_iprem': oficio.oficio.contrib_previdenciaria_iprem,
                    'contrib_previdenciaria_hspm': oficio.oficio.contrib_previdenciaria_hspm,
                    'valor_total_requisitado': oficio.oficio.valor_total_requisitado,
                    'data_base_atualizacao': oficio.oficio.data_base_atualizacao,
                    'idoso': oficio.oficio.idoso,
                    'doenca_grave': oficio.oficio.doenca_grave,
                    'pcd': oficio.oficio.pcd
                })
            else:
                # Preencher com None se processamento falhou
                campos_oficio = [
                    'vara', 'processo_execucao', 'processo_conhecimento',
                    'data_ajuizamento', 'data_transito_julgado', 'requerente_caps',
                    'advogado_nome', 'advogado_oab', 'valor_principal_liquido',
                    'valor_principal_bruto', 'juros_moratorios',
                    'contrib_previdenciaria_iprem', 'contrib_previdenciaria_hspm',
                    'valor_total_requisitado', 'data_base_atualizacao',
                    'idoso', 'doenca_grave', 'pcd'
                ]
                for campo in campos_oficio:
                    dados[campo] = None
            
            # Executar upsert
            cursor.execute(sql, dados)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Dados salvos no PostgreSQL: CPF {oficio.metadata.cpf}, Processo {oficio.metadata.numero_processo}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar no PostgreSQL: {e}")
            return False
    
    def processar_pasta(self, pasta_base: str = "./Processos") -> Dict[str, Any]:
        """
        Processa todos os PDFs na pasta base conforme estrutura do projeto.
        
        Args:
            pasta_base: Pasta contendo as pastas de CPF com PDFs
            
        Returns:
            Estatísticas do processamento
        """
        stats = {
            "total_arquivos": 0,
            "processados_sucesso": 0,
            "processados_erro": 0,
            "oficios_detectados": 0,
            "oficios_salvos": 0
        }
        
        try:
            pasta_path = Path(pasta_base)
            if not pasta_path.exists():
                logger.error(f"Pasta base não encontrada: {pasta_base}")
                return stats
            
            # Buscar todos os PDFs na estrutura {cpf}/{processo}.pdf
            pdf_files = list(pasta_path.rglob("*.pdf"))
            stats["total_arquivos"] = len(pdf_files)
            
            logger.info(f"Encontrados {len(pdf_files)} PDFs para processar")
            
            for pdf_file in pdf_files:
                try:
                    # Processar arquivo
                    resultado = self.processar_arquivo(str(pdf_file))
                    
                    if resultado:
                        stats["processados_sucesso"] += 1
                        
                        if resultado.oficio:
                            stats["oficios_detectados"] += 1
                            
                            # Salvar no banco
                            if self.salvar_postgres(resultado):
                                stats["oficios_salvos"] += 1
                    else:
                        stats["processados_erro"] += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao processar {pdf_file}: {e}")
                    stats["processados_erro"] += 1
            
            logger.info(f"Processamento concluído: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erro no processamento da pasta: {e}")
            return stats
