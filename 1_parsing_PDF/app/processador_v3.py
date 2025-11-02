"""
ProcessadorOficio V3 DEFINITIVA - Pipeline com melhorias críticas para alta acurácia

V3 = V2.5.1 + 3 Melhorias Críticas:
1. ✅ Exemplos explícitos no prompt (valores brasileiros)
2. ✅ Validação de sanidade de valores
3. ✅ Verificação de tipos

Meta: Taxa de sucesso ≥98% (vs 96.1% em V2.5.1)

Data: 01/11/2025
Status: EM DESENVOLVIMENTO
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .processador import ProcessadorOficio

logger = logging.getLogger(__name__)


class ProcessadorOficioV3(ProcessadorOficio):
    """
    V3 Definitiva: Herda de ProcessadorOficio (V2.5.1) e adiciona melhorias críticas.
    
    Melhorias implementadas:
    1. Prompt otimizado com exemplos explícitos de valores brasileiros
    2. Validação de sanidade para detectar parsing incorreto
    3. Verificação rigorosa de tipos de dados
    
    Casos alvo:
    - Ponto decimal interpretado incorretamente (73.431,66 → 73,43)
    - Inversão líquido/bruto
    - Parsing de valores truncados
    """
    
    def __init__(self, openai_api_key: str, db_config: Dict[str, Any], modo_teste: bool = False):
        """
        Inicializa o processador V3.
        
        Args:
            openai_api_key: Chave da API OpenAI
            db_config: Configurações do banco PostgreSQL
            modo_teste: Se True, não grava no banco (apenas retorna resultados)
        """
        super().__init__(openai_api_key, db_config)
        self.modo_teste = modo_teste
        
        logger.info("=" * 80)
        logger.info("🚀 ProcessadorOficio V3 DEFINITIVA inicializado")
        logger.info("=" * 80)
        logger.info("✅ Melhoria #1: Prompt com exemplos de valores brasileiros")
        logger.info("✅ Melhoria #2: Validação de sanidade de valores")
        logger.info("✅ Melhoria #3: Verificação rigorosa de tipos")
        if modo_teste:
            logger.info("⚠️  MODO TESTE: Não gravará no banco de dados")
        logger.info("=" * 80)
    
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
        V3: Sobrescreve método híbrido para adicionar melhorias críticas.
        
        Melhorias:
        1. Adiciona exemplos explícitos de valores brasileiros no prompt
        2. Verifica e corrige tipos (strings → numbers)
        3. Valida sanidade dos valores extraídos
        """
        # Chamar método da classe pai para obter prompt base
        # Mas vamos interceptar para adicionar nossos exemplos
        from .llm_adapter import LLMAdapter, LLMProvider
        import os
        
        # Criar LLM adapter se não existir
        if not hasattr(self, 'llm_adapter'):
            try:
                gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                self.llm_adapter = LLMAdapter(
                    openai_api_key=self.openai_api_key,
                    gemini_api_key=gemini_key
                )
                self.tem_gemini = gemini_key is not None
            except Exception as e:
                logger.warning(f"⚠️ Erro ao criar LLM adapter: {e}")
                self.llm_adapter = None
                self.tem_gemini = False
        
        # Construir prompt (usando método da classe pai)
        nota_rejeicao = ""
        if oficio_rejeitado:
            nota_rejeicao = f"""
⚠️ ATENÇÃO: Este ofício possui NOTA DE REJEIÇÃO!
Motivo: {motivo_rejeicao if motivo_rejeicao else 'Não especificado'}
Ainda assim, extraia TODOS os campos solicitados.
"""
        
        nota_anomalia = ""
        if numero_ordem_titulo:
            nota_anomalia = f"""
📋 INFORMAÇÃO ADICIONAL:
Número de ordem identificado no título: {numero_ordem_titulo}
Use este número se não encontrar no campo PROCESSAMENTO.
"""
        
        # 🚀 MELHORIA #1: Adicionar exemplos explícitos de valores brasileiros
        exemplos_valores = """

⚠️⚠️⚠️ ATENÇÃO CRÍTICA: VALORES MONETÁRIOS NO FORMATO BRASILEIRO ⚠️⚠️⚠️

REGRA FUNDAMENTAL: Em português brasileiro, o PONTO (.) é separador de MILHARES e a VÍRGULA (,) é separador de DECIMAIS!

EXEMPLOS CORRETOS - VOCÊ DEVE SEGUIR EXATAMENTE ESTE PADRÃO:

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

VERIFICAÇÃO OBRIGATÓRIA ANTES DE RETORNAR:
1. Todos os valores monetários são NÚMEROS (type: number), NÃO strings
2. Valores realistas: R$ 1.000 a R$ 10.000.000 (se menor que R$ 100, REVISE!)
3. Líquido ≤ Bruto (se líquido > bruto, VOCÊ INVERTEU!)

ATENÇÃO ESPECIAL - LÍQUIDO vs BRUTO:

- Valor Principal LÍQUIDO: Valor APÓS descontos (sempre MENOR ou igual ao bruto)
- Valor Principal BRUTO: Valor ANTES de descontos (sempre MAIOR ou igual ao líquido)

Exemplo:
  Valor Bruto: R$ 311.369,53
  Descontos: R$ 121.148,11
  Valor Líquido: R$ 190.221,42 (bruto - descontos)

Se você encontrar líquido > bruto, VOCÊ INVERTEU OS CAMPOS! Corrija antes de retornar.

"""
        
        # Construir prompt V3 com exemplos
        prompt_v3 = nota_rejeicao + nota_anomalia + exemplos_valores + "\n\n[DOCUMENTO]\n" + texto_oficio + "\n\n[FIM DO DOCUMENTO]"
        
        # Tentar extração com Gemini primeiro (se disponível)
        dados = None
        if self.tem_gemini and self.llm_adapter:
            try:
                logger.info("🔄 Tentando extração com Gemini 2.5 Flash (V3)...")
                dados = self.llm_adapter.extract_structured_data(
                    prompt=prompt_v3,
                    provider=LLMProvider.GEMINI
                )
                
                if dados:
                    logger.info("✅ Extração com Gemini bem-sucedida")
            except Exception as e:
                logger.warning(f"⚠️ Gemini falhou: {e}")
        
        # Se Gemini falhou ou não disponível, usar OpenAI
        if not dados:
            logger.info("🔄 Usando OpenAI GPT-4o-mini (V3)...")
            dados = self.llm_adapter.extract_structured_data(
                prompt=prompt_v3,
                provider=LLMProvider.OPENAI
            )
        
        if not dados:
            logger.error("❌ Falha na extração com ambos LLMs")
            return None
        
        # 🚀 MELHORIA #3: Verificação rigorosa de tipos
        dados = self._verificar_e_corrigir_tipos(dados)
        
        # 🚀 MELHORIA #2: Validação de sanidade de valores
        # (vamos fazer isso no processar_arquivo para ter acesso a CPF e processo)
        dados['_v3_validacao_pendente'] = True
        
        return dados
    
    def _verificar_e_corrigir_tipos(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        MELHORIA #3: Verifica e corrige tipos de dados (especialmente valores monetários).
        
        Garante que:
        - Valores monetários são numbers (não strings)
        - Strings numéricas são convertidas para float
        - Valores None/null são preservados
        """
        campos_monetarios = [
            'valor_principal_liquido',
            'valor_principal_bruto',
            'juros_moratorios',
            'valor_total_requisitado',
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
                    logger.warning(f"🔧 V3: {campo} retornado como STRING: '{valor}' - convertendo...")
                    
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
        MELHORIA #2: Validação de sanidade para detectar parsing incorreto.
        
        Verifica:
        1. Valores muito baixos (< R$ 100 ou < R$ 1.000)
        2. Inversão líquido/bruto
        3. Inconsistência entre total declarado e calculado
        4. Valores zerados em campos obrigatórios
        
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
    
    def _salvar_no_banco(self, dados: Dict[str, Any], texto_completo: str) -> bool:
        """
        Salva dados no PostgreSQL.
        
        V3: Respeita modo_teste (não grava se modo_teste=True).
        """
        if self.modo_teste:
            logger.info("⚠️  MODO TESTE: Simulando gravação no banco (não gravando de fato)")
            logger.info(f"   CPF: {dados.get('cpf')}")
            logger.info(f"   Processo: {dados.get('numero_processo')}")
            logger.info(f"   Valor Total: R$ {dados.get('valor_total_requisitado', 0):,.2f}")
            return True  # Simular sucesso
        
        # Se não estiver em modo teste, usar método da classe pai
        return super()._salvar_no_banco(dados, texto_completo)
    
    def processar_arquivo(self, pdf_path: str, cpf_numerico: str, salvar_db: bool = True) -> Dict[str, Any]:
        """
        Processa um único arquivo PDF.
        
        V3: Adiciona parâmetro salvar_db e validação de sanidade.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            cpf_numerico: CPF esperado (apenas números)
            salvar_db: Se False, não grava no banco (sobrescreve modo_teste)
            
        Returns:
            Dict com resultado completo do processamento
        """
        # Se salvar_db=False, forçar modo teste temporariamente
        modo_teste_original = self.modo_teste
        if not salvar_db:
            self.modo_teste = True
        
        try:
            # Processar usando método da classe pai (V2.5.1)
            resultado = super().processar_arquivo(pdf_path, cpf_numerico)
            
            # Adicionar informação de versão ao resultado
            if resultado:
                resultado['_versao_processador'] = 'V3_DEFINITIVA'
                
                # 🚀 MELHORIA #2: Validação de sanidade (se pendente)
                if resultado.get('dados') and resultado['dados'].get('_v3_validacao_pendente'):
                    # Remover flag
                    del resultado['dados']['_v3_validacao_pendente']
                    
                    # Validar sanidade
                    cpf_formatado = self._formatar_cpf(cpf_numerico)
                    numero_processo = resultado['dados'].get('processo_origem', '')
                    
                    alertas = self._validar_sanidade_valores(
                        resultado['dados'],
                        cpf_formatado,
                        numero_processo
                    )
                    
                    if alertas:
                        resultado['_alertas_sanidade'] = alertas
                        # Também adicionar aos logs
                        logger.warning("=" * 80)
                        logger.warning("🚨 ALERTAS DE SANIDADE DETECTADOS (V3):")
                        for alerta in alertas:
                            logger.warning(f"   {alerta}")
                        logger.warning("=" * 80)
            
            return resultado
            
        finally:
            # Restaurar modo teste original
            self.modo_teste = modo_teste_original


# Função auxiliar para criar instância V3
def criar_processador_v3(
    openai_api_key: str,
    db_config: Dict[str, Any],
    modo_teste: bool = False
) -> ProcessadorOficioV3:
    """
    Factory function para criar ProcessadorOficio V3.
    
    Args:
        openai_api_key: Chave da API OpenAI
        db_config: Configurações do banco PostgreSQL
        modo_teste: Se True, não grava no banco
        
    Returns:
        ProcessadorOficioV3 inicializado
    """
    return ProcessadorOficioV3(
        openai_api_key=openai_api_key,
        db_config=db_config,
        modo_teste=modo_teste
    )

