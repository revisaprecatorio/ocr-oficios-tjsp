"""
Schemas Pydantic para validação de dados dos Ofícios Requisitórios TJSP.
Conforme especificações do AGENTS.md.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class OficioRequisitorio(BaseModel):
    """
    Schema principal para validação de dados extraídos de Ofícios Requisitórios.
    
    Campos obrigatórios conforme AGENTS.md:
    - processo_origem: Número CNJ (formato: 0000000-00.0000.0.00.0000)
    - requerente_caps: Nome TODO EM MAIÚSCULAS
    """
    
    # ===== CAMPOS OBRIGATÓRIOS =====
    processo_origem: str = Field(
        ..., 
        description="Número CNJ do processo de origem",
        min_length=20,
        max_length=30
    )
    
    requerente_caps: str = Field(
        ..., 
        description="Nome do requerente em MAIÚSCULAS",
        min_length=3,
        max_length=200
    )
    
    # ===== CAMPOS OPCIONAIS - OFÍCIO =====
    vara: Optional[str] = Field(
        None, 
        description="Vara responsável pelo ofício",
        max_length=100
    )
    
    processo_execucao: Optional[str] = Field(
        None, 
        description="Número do processo de execução",
        max_length=30
    )
    
    processo_conhecimento: Optional[str] = Field(
        None, 
        description="Número do processo de conhecimento",
        max_length=30
    )
    
    # ===== CAMPOS OPCIONAIS - DATAS =====
    data_ajuizamento: Optional[date] = Field(
        None, 
        description="Data de ajuizamento do processo (formato ISO: YYYY-MM-DD)"
    )
    
    data_transito_julgado: Optional[date] = Field(
        None, 
        description="Data do trânsito em julgado (formato ISO: YYYY-MM-DD)"
    )
    
    data_base_atualizacao: Optional[date] = Field(
        None, 
        description="Data base para atualização monetária (formato ISO: YYYY-MM-DD)"
    )
    
    # ===== CAMPOS OPCIONAIS - PARTES =====
    advogado_nome: Optional[str] = Field(
        None,
        description="Nome do advogado",
        max_length=200
    )

    advogado_oab: Optional[str] = Field(
        None,
        description="Número da OAB do advogado (formato: OAB/UF 000.000)",
        max_length=20
    )

    credor_nome: Optional[str] = Field(
        None,
        description="Nome do credor",
        max_length=200
    )

    credor_cpf_cnpj: Optional[str] = Field(
        None,
        description="CPF ou CNPJ do credor",
        max_length=18
    )

    devedor_ente: Optional[str] = Field(
        None,
        description="Ente devedor (município, estado, etc.)",
        max_length=200
    )

    # ===== CAMPOS OPCIONAIS - DADOS BANCÁRIOS (ANEXO II) =====
    banco: Optional[str] = Field(
        None,
        description="Código do banco (ex: 001, 341)",
        max_length=10
    )

    agencia: Optional[str] = Field(
        None,
        description="Número da agência bancária",
        max_length=20
    )

    conta: Optional[str] = Field(
        None,
        description="Número da conta bancária (com dígito)",
        max_length=30
    )

    conta_tipo: Optional[str] = Field(
        None,
        description="Tipo de conta (corrente, poupança, etc.)",
        max_length=20
    )
    
    # ===== CAMPOS OPCIONAIS - FINANCEIRO =====
    # Valores armazenados como Decimal para precisão monetária
    valor_principal_liquido: Optional[Decimal] = Field(
        None, 
        description="Valor principal líquido (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    valor_principal_bruto: Optional[Decimal] = Field(
        None, 
        description="Valor principal bruto (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    juros_moratorios: Optional[Decimal] = Field(
        None, 
        description="Juros moratórios (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    contrib_previdenciaria_iprem: Optional[Decimal] = Field(
        None, 
        description="Contribuição previdenciária IPREM (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    contrib_previdenciaria_hspm: Optional[Decimal] = Field(
        None, 
        description="Contribuição previdenciária HSPM (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    valor_total_requisitado: Optional[Decimal] = Field(
        None, 
        description="Valor total requisitado (sem R$, sem pontos de milhar)",
        ge=0,
        decimal_places=2
    )
    
    # ===== CAMPOS OPCIONAIS - PREFERÊNCIAS =====
    idoso: Optional[bool] = Field(
        None, 
        description="Indica se o beneficiário é idoso (≥60 anos)"
    )
    
    doenca_grave: Optional[bool] = Field(
        None, 
        description="Indica se há doença grave"
    )
    
    pcd: Optional[bool] = Field(
        None, 
        description="Indica se há pessoa com deficiência"
    )

    # ===== VALIDADORES =====
    
    @field_validator('processo_origem')
    @classmethod
    def validar_processo_cnj(cls, v: str) -> str:
        """Valida formato do processo CNJ: 0000000-00.0000.0.00.0000 (com possível sufixo)"""
        if not v:
            raise ValueError("Processo de origem é obrigatório")
        
        # Remover possível sufixo após barra (ex: /35, /0579)
        processo_limpo = v.split('/')[0]
        
        # Pattern CNJ conforme AGENTS.md
        pattern = r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
        if not re.match(pattern, processo_limpo):
            raise ValueError(f"Formato de processo CNJ inválido: {processo_limpo}. Esperado: 0000000-00.0000.0.00.0000")
        
        # Retornar apenas o número principal (sem sufixo)
        return processo_limpo
    
    @field_validator('requerente_caps')
    @classmethod
    def validar_requerente_maiusculo(cls, v: str) -> str:
        """Valida que o requerente está em MAIÚSCULAS"""
        if not v:
            raise ValueError("Nome do requerente é obrigatório")
        
        if v != v.upper():
            raise ValueError(f"Nome do requerente deve estar em MAIÚSCULAS: {v}")
        
        return v
    
    @field_validator('advogado_oab')
    @classmethod
    def validar_oab(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato OAB: OAB/UF 000.000"""
        if v is None:
            return v
        
        # Pattern básico para OAB
        pattern = r'^OAB/[A-Z]{2}\s+\d{1,6}\.?\d{3}$'
        if not re.match(pattern, v.upper()):
            # Tentar normalizar formato comum
            if re.match(r'^\d+/[A-Z]{2}$', v.upper()):
                return f"OAB/{v.split('/')[1]} {v.split('/')[0]}"
        
        return v
    
    @field_validator('credor_cpf_cnpj')
    @classmethod
    def validar_cpf_cnpj(cls, v: Optional[str]) -> Optional[str]:
        """Valida formato básico de CPF/CNPJ"""
        if v is None:
            return v
        
        # Remove formatação
        numeros = re.sub(r'[^\d]', '', v)
        
        if len(numeros) == 11:
            # CPF: 000.000.000-00
            return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
        elif len(numeros) == 14:
            # CNPJ: 00.000.000/0000-00
            return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
        else:
            raise ValueError(f"CPF/CNPJ deve ter 11 ou 14 dígitos: {v}")
    
    @model_validator(mode='after')
    def calcular_preferencias(self):
        """Calcula preferências baseadas em dados disponíveis"""
        # Calcular idade se data de nascimento estiver disponível
        # Por enquanto, vamos deixar manual conforme AGENTS.md
        return self


class ProcessoMetadata(BaseModel):
    """Metadados do processo extraídos dos nomes de pastas e arquivos"""
    
    cpf: str = Field(
        ..., 
        description="CPF extraído do nome da pasta (apenas números)",
        pattern=r'^\d{11}$'
    )
    
    numero_processo: str = Field(
        ..., 
        description="Número do processo extraído do nome do arquivo",
        min_length=20,
        max_length=30
    )
    
    texto_completo_oficio: str = Field(
        ..., 
        description="Texto completo extraído das páginas do ofício"
    )
    
    paginas_oficio: list[int] = Field(
        ..., 
        description="Lista das páginas onde o ofício foi detectado"
    )
    
    timestamp_processamento: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp do processamento"
    )
    
    processado: bool = Field(
        default=False,
        description="Indica se o processamento foi concluído com sucesso"
    )


class OficioCompleto(BaseModel):
    """Schema completo combinando dados do ofício e metadados"""
    
    # Metadados
    metadata: ProcessoMetadata
    
    # Dados estruturados do ofício (None se não foi processado com sucesso)
    oficio: Optional[OficioRequisitorio]
    
    # Data de envio (opcional)
    data_envio: Optional[date] = Field(
        None,
        description="Data de envio do ofício"
    )

    class Config:
        """Configuração do modelo"""
        # Permite campos extras para flexibilidade
        extra = "forbid"
        # Valida na atribuição
        validate_assignment = True
        # Usa Enum por valor
        use_enum_values = True
