"""
Schemas Pydantic para validação de dados dos Ofícios Requisitórios TJSP.
Conforme especificações do AGENTS.md.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
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
    
    # V2: NOVO CAMPO (opcional pois pode não existir em ofícios rejeitados)
    numero_ordem: Optional[str] = Field(
        None,
        description="Número de ordem/precatório (formato: XXX/YYYY)",
        pattern=r'^\d{1,5}/\d{4}$'
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
    # Aceita tanto estrutura aninhada quanto campos diretos
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
    
    # Estrutura aninhada do ANEXO II (alternativa)
    anexo_ii: Optional[Dict[str, Any]] = Field(
        None,
        description="Dados bancários do ANEXO II em estrutura aninhada"
    )
    
    # ===== CAMPOS FINANCEIROS - OPCIONAIS (V2) =====
    # Valores armazenados como Decimal para precisão monetária
    # Opcionais para permitir ofícios rejeitados ou PDFs antigos
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
    
    valor_total_requisitado: Optional[Decimal] = Field(
        None,
        description="Valor total requisitado (sem R$, sem pontos de milhar)",
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
    
    valor_total_requisitado: Decimal = Field(
        ...,  # V2: Obrigatório!
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
    
    # ===== CONTROLE DE PROCESSAMENTO (V2) =====
    rejeitado: Optional[bool] = Field(
        None,
        description="Indica se o ofício foi rejeitado pelo DEPRE"
    )
    
    motivo_rejeicao: Optional[str] = Field(
        None,
        description="Motivo da rejeição do ofício",
        max_length=500
    )
    
    observacoes: Optional[str] = Field(
        None,
        description="Observações sobre campos não encontrados ou anomalias",
        max_length=500
    )
    
    anomalia: Optional[bool] = Field(
        None,
        description="Indica se o PDF tem formato anômalo ou não segue padrão esperado"
    )
    
    descricao_anomalia: Optional[str] = Field(
        None,
        description="Descrição da anomalia encontrada",
        max_length=500
    )
    
    # ===== CAMPOS ADICIONAIS DO ANEXO II (V2) =====
    tipo_levantamento: Optional[str] = Field(
        None,
        description="Tipo de levantamento (ex: Crédito em contas para outros bancos)",
        max_length=200
    )
    
    dados_bancarios_advogado: Optional[bool] = Field(
        None,
        description="Se os dados bancários informados são do advogado"
    )
    
    cpf_titular_conta: Optional[str] = Field(
        None,
        description="CPF do titular da conta bancária indicada",
        max_length=18
    )
    
    data_nascimento: Optional[date] = Field(
        None,
        description="Data de nascimento do credor"
    )
    
    valor_compensado: Optional[Decimal] = Field(
        None,
        description="Valor compensado (Art. 100)",
        ge=0,
        decimal_places=2
    )
    
    # Valores trabalhistas (se houver)
    contribuicao_social: Optional[Decimal] = Field(
        None,
        description="Contribuição social",
        ge=0,
        decimal_places=2
    )
    
    salario_pericial: Optional[Decimal] = Field(
        None,
        description="Salário pericial",
        ge=0,
        decimal_places=2
    )
    
    assist_tecnico: Optional[Decimal] = Field(
        None,
        description="Assistente técnico",
        ge=0,
        decimal_places=2
    )
    
    custas: Optional[Decimal] = Field(
        None,
        description="Custas processuais",
        ge=0,
        decimal_places=2
    )
    
    despesas: Optional[Decimal] = Field(
        None,
        description="Despesas",
        ge=0,
        decimal_places=2
    )
    
    multas: Optional[Decimal] = Field(
        None,
        description="Multas",
        ge=0,
        decimal_places=2
    )

    # ===== VALIDADORES =====
    
    @field_validator(
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
        'multas',
        mode='before'
    )
    @classmethod
    def arredondar_decimais(cls, v):
        """
        Limpa e normaliza valores monetários antes da validação.
        
        Remove: R$, espaços, pontos de milhar
        Converte: vírgula em ponto decimal
        Aceita: int, float, str, Decimal
        """
        if v is None:
            return v
        
        # Converter para Decimal e arredondar
        from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
        
        try:
            # Tentar converter diferentes tipos
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            elif isinstance(v, str):
                # Limpar string: remover R$, espaços, pontos de milhar
                v = v.strip()
                v = v.replace('R$', '').replace('R$ ', '')
                v = v.replace(' ', '')
                
                # Se estiver vazio ou for "null", retornar None
                if not v or v.lower() in ('null', 'none', 'n/a', '-'):
                    return None
                
                # Remover pontos de milhar (mas manter ponto decimal se houver)
                # Lógica: se tem vírgula, é separador decimal brasileiro
                if ',' in v:
                    # Formato brasileiro: 1.234.567,89
                    v = v.replace('.', '')  # Remove pontos de milhar
                    v = v.replace(',', '.')  # Converte vírgula em ponto
                elif v.count('.') > 1:
                    # Múltiplos pontos = pontos de milhar (ex: 1.234.567)
                    # Remove todos exceto o último
                    partes = v.split('.')
                    v = ''.join(partes[:-1]) + '.' + partes[-1]
                
                v = Decimal(v)
            elif isinstance(v, Decimal):
                pass  # Já é Decimal
            else:
                # Tipo não suportado, retornar None
                return None
            
            # Validar se é positivo
            if v < 0:
                return None
            
            # Arredondar para 2 casas decimais
            return v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
        except (ValueError, InvalidOperation, AttributeError):
            # Se não conseguir converter, retornar None
            return None
    
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
    def normalizar_dados_bancarios(self):
        """Normaliza dados bancários de estrutura aninhada para campos diretos"""
        # Se anexo_ii existe e campos diretos estão vazios, copiar
        if self.anexo_ii and isinstance(self.anexo_ii, dict):
            if not self.banco and 'banco' in self.anexo_ii:
                self.banco = self.anexo_ii['banco']
            if not self.agencia and 'agencia' in self.anexo_ii:
                self.agencia = self.anexo_ii['agencia']
            if not self.conta and 'conta' in self.anexo_ii:
                self.conta = self.anexo_ii['conta']
            if not self.conta_tipo and 'conta_tipo' in self.anexo_ii:
                self.conta_tipo = self.anexo_ii['conta_tipo']
        
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
