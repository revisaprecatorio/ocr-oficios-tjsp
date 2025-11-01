"""
Adaptador unificado para múltiplos LLMs.
Suporta: OpenAI (GPT-4o-mini) e Google (Gemini 2.5 Pro).

Implementado para FINDING 06 - Testes A/B entre LLMs.
"""

import json
import logging
import os
from typing import Dict, Any, Optional
from enum import Enum

# OpenAI
from openai import OpenAI

# Google Gemini
import google.generativeai as genai


logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Provedores de LLM suportados."""
    OPENAI = "openai"
    GEMINI = "gemini"


class LLMAdapter:
    """
    Adaptador unificado para extrair dados estruturados via LLMs.
    
    Suporta:
    - OpenAI: gpt-4o-mini (baseline atual)
    - Google: gemini-2.5-pro, gemini-2.5-flash
    
    Interface unificada:
    - extract_structured_data(prompt, provider) -> dict
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None
    ):
        """
        Inicializa adaptador com múltiplos provedores.
        
        Args:
            openai_api_key: API key OpenAI (opcional)
            gemini_api_key: API key Google Gemini (opcional)
        """
        self.providers_available = {}
        
        # Configurar OpenAI
        if openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.providers_available[LLMProvider.OPENAI] = {
                    "model": "gpt-4o-mini",
                    "max_tokens": 16384,
                    "temperature": 0
                }
                logger.info("✅ OpenAI configurado: gpt-4o-mini")
            except Exception as e:
                logger.error(f"❌ Erro ao configurar OpenAI: {e}")
        
        # Configurar Gemini
        if gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                self.gemini_model = genai.GenerativeModel("gemini-2.5-pro")
                self.providers_available[LLMProvider.GEMINI] = {
                    "model": "gemini-2.5-pro",
                    "max_tokens": 1048576,  # 1M input tokens
                    "temperature": 0
                }
                logger.info("✅ Gemini configurado: gemini-2.5-pro")
            except Exception as e:
                logger.error(f"❌ Erro ao configurar Gemini: {e}")
    
    def extract_structured_data(
        self,
        prompt: str,
        provider: LLMProvider = LLMProvider.OPENAI,
        model_override: Optional[str] = None,
        temperature: float = 0
    ) -> Dict[str, Any]:
        """
        Extrai dados estruturados (JSON) de um prompt usando LLM.
        
        Args:
            prompt: Prompt completo com contexto e schema
            provider: Provedor de LLM (openai ou gemini)
            model_override: Modelo específico (sobrescreve padrão)
            temperature: Temperatura (0 = determinístico)
            
        Returns:
            Dicionário com dados estruturados extraídos
            
        Raises:
            ValueError: Se provedor não está configurado
            Exception: Se extração falhar
        """
        if provider not in self.providers_available:
            raise ValueError(
                f"Provedor '{provider}' não configurado. "
                f"Disponíveis: {list(self.providers_available.keys())}"
            )
        
        logger.info(f"🤖 Extraindo dados com {provider.upper()}")
        
        if provider == LLMProvider.OPENAI:
            return self._extract_openai(prompt, model_override, temperature)
        elif provider == LLMProvider.GEMINI:
            return self._extract_gemini(prompt, model_override, temperature)
        else:
            raise ValueError(f"Provedor desconhecido: {provider}")
    
    def _extract_openai(
        self,
        prompt: str,
        model_override: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        """
        Extração via OpenAI (GPT-4o-mini).
        
        Características:
        - Resposta: JSON Mode (garantido JSON válido)
        - Tokens: ~16k input
        - Custo: $0.150/1M input, $0.600/1M output
        """
        try:
            model = model_override or self.providers_available[LLMProvider.OPENAI]["model"]
            
            logger.info(f"   Modelo: {model}")
            logger.info(f"   Prompt: {len(prompt):,} chars")
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente especializado em extração de dados "
                            "estruturados de documentos jurídicos. Retorne apenas JSON válido."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                response_format={"type": "json_object"}  # Force JSON
            )
            
            # Extrair JSON
            json_str = response.choices[0].message.content
            
            # Parse JSON
            dados = json.loads(json_str)
            
            logger.info(f"   ✅ Extração OK: {len(dados)} campos")
            return dados
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON inválido do OpenAI: {e}")
            logger.error(f"   Resposta: {json_str[:500]}...")
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao extrair com OpenAI: {e}")
            raise
    
    def _extract_gemini(
        self,
        prompt: str,
        model_override: Optional[str],
        temperature: float
    ) -> Dict[str, Any]:
        """
        Extração via Google Gemini (2.5 Pro).
        
        Características:
        - Resposta: Text (precisa fazer parse manual)
        - Tokens: ~1M input (contexto 60x maior!)
        - Custo: Grátis até limite, depois mais barato que OpenAI
        """
        try:
            model_name = model_override or "gemini-2.5-pro"
            
            # Criar modelo se override
            if model_override:
                model = genai.GenerativeModel(model_name)
            else:
                model = self.gemini_model
            
            logger.info(f"   Modelo: {model_name}")
            logger.info(f"   Prompt: {len(prompt):,} chars")
            
            # Configurar geração
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": 8192,
                "response_mime_type": "application/json"  # Request JSON
            }
            
            # Gerar resposta
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extrair texto
            json_str = response.text.strip()
            
            # Limpar markdown se presente
            if json_str.startswith("```json"):
                json_str = json_str.replace("```json", "").replace("```", "").strip()
            elif json_str.startswith("```"):
                json_str = json_str.replace("```", "").strip()
            
            # Parse JSON
            dados = json.loads(json_str)
            
            logger.info(f"   ✅ Extração OK: {len(dados)} campos")
            return dados
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON inválido do Gemini: {e}")
            logger.error(f"   Resposta: {json_str[:500]}...")
            # Tentar recuperar JSON dentro da resposta
            try:
                # Buscar por { ... } no texto
                import re
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    json_str_clean = json_match.group(0)
                    dados = json.loads(json_str_clean)
                    logger.warning("⚠️ JSON recuperado de resposta mal formatada")
                    return dados
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"❌ Erro ao extrair com Gemini: {e}")
            raise
    
    def compare_providers(
        self,
        prompt: str,
        providers: list[LLMProvider] = None
    ) -> Dict[LLMProvider, Dict[str, Any]]:
        """
        Executa extração com múltiplos provedores e compara resultados.
        
        Útil para testes A/B.
        
        Args:
            prompt: Prompt para extrair dados
            providers: Lista de provedores (padrão: todos disponíveis)
            
        Returns:
            Dict com resultados de cada provedor:
            {
                LLMProvider.OPENAI: {...dados...},
                LLMProvider.GEMINI: {...dados...}
            }
        """
        if providers is None:
            providers = list(self.providers_available.keys())
        
        resultados = {}
        
        for provider in providers:
            if provider not in self.providers_available:
                logger.warning(f"⚠️ Provedor {provider} não disponível, pulando")
                continue
            
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Testando: {provider.upper()}")
                logger.info(f"{'='*60}")
                
                dados = self.extract_structured_data(prompt, provider)
                resultados[provider] = {
                    "success": True,
                    "data": dados,
                    "error": None
                }
                
            except Exception as e:
                logger.error(f"❌ Falha com {provider}: {e}")
                resultados[provider] = {
                    "success": False,
                    "data": None,
                    "error": str(e)
                }
        
        return resultados
    
    def get_available_providers(self) -> list[LLMProvider]:
        """Retorna lista de provedores configurados e disponíveis."""
        return list(self.providers_available.keys())
    
    def get_provider_info(self, provider: LLMProvider) -> Dict[str, Any]:
        """Retorna informações sobre um provedor específico."""
        if provider not in self.providers_available:
            raise ValueError(f"Provedor {provider} não configurado")
        return self.providers_available[provider]


# ===== FUNÇÕES AUXILIARES =====

def criar_adapter_from_env() -> LLMAdapter:
    """
    Cria adaptador usando API keys do ambiente.
    
    Lê variáveis:
    - OPENAI_API_KEY
    - GOOGLE_API_KEY (ou GEMINI_API_KEY)
    
    Returns:
        LLMAdapter configurado com provedores disponíveis
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not openai_key and not gemini_key:
        raise ValueError(
            "Nenhuma API key configurada! "
            "Configure OPENAI_API_KEY ou GOOGLE_API_KEY"
        )
    
    return LLMAdapter(
        openai_api_key=openai_key,
        gemini_api_key=gemini_key
    )

