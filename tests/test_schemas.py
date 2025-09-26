"""
Testes para Schemas Pydantic.
Conforme AGENTS.md - validação de campos obrigatórios e formatos.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from pydantic import ValidationError

from app.schemas import OficioRequisitorio, ProcessoMetadata, OficioCompleto


class TestOficioRequisitorio:
    """Testes do schema OficioRequisitorio"""
    
    def test_campos_obrigatorios_validos(self):
        """Teste com campos obrigatórios válidos"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "FERNANDO SANTOS ERNESTO"
        }
        
        oficio = OficioRequisitorio(**data)
        
        assert oficio.processo_origem == "0035938-67.2018.8.26.0053"
        assert oficio.requerente_caps == "FERNANDO SANTOS ERNESTO"
    
    def test_processo_origem_obrigatorio(self):
        """Teste processo_origem obrigatório"""
        data = {
            "requerente_caps": "FERNANDO SANTOS ERNESTO"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OficioRequisitorio(**data)
        
        assert "processo_origem" in str(exc_info.value)
    
    def test_requerente_caps_obrigatorio(self):
        """Teste requerente_caps obrigatório"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            OficioRequisitorio(**data)
        
        assert "requerente_caps" in str(exc_info.value)
    
    def test_processo_cnj_formato_valido(self):
        """Teste validação formato CNJ válido"""
        processos_validos = [
            "0035938-67.2018.8.26.0053",
            "0176505-63.2021.8.26.0500",
            "0221031-18.2021.8.26.0500",
            "1234567-89.2023.1.01.1234"
        ]
        
        for processo in processos_validos:
            data = {
                "processo_origem": processo,
                "requerente_caps": "TESTE"
            }
            
            oficio = OficioRequisitorio(**data)
            assert oficio.processo_origem == processo
    
    def test_processo_cnj_formato_invalido(self):
        """Teste validação formato CNJ inválido"""
        processos_invalidos = [
            "123456",
            "123456-78.2021",
            "0035938-67.2018.8.26",
            "035938-67.2018.8.26.0053",  # Faltam dígitos
            "12345678-67.2018.8.26.0053",  # Muitos dígitos
            "0035938.67.2018.8.26.0053"  # Formato errado
        ]
        
        for processo in processos_invalidos:
            data = {
                "processo_origem": processo,
                "requerente_caps": "TESTE"
            }
            
            with pytest.raises(ValidationError):
                OficioRequisitorio(**data)
    
    def test_requerente_maiusculo_valido(self):
        """Teste requerente em maiúsculas (válido)"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "FERNANDO SANTOS ERNESTO"
        }
        
        oficio = OficioRequisitorio(**data)
        assert oficio.requerente_caps == "FERNANDO SANTOS ERNESTO"
    
    def test_requerente_maiusculo_invalido(self):
        """Teste requerente não em maiúsculas (inválido)"""
        nomes_invalidos = [
            "Fernando Santos Ernesto",
            "FERNANDO santos ERNESTO",
            "fernando santos ernesto"
        ]
        
        for nome in nomes_invalidos:
            data = {
                "processo_origem": "0035938-67.2018.8.26.0053",
                "requerente_caps": nome
            }
            
            with pytest.raises(ValidationError) as exc_info:
                OficioRequisitorio(**data)
            
            assert "MAIÚSCULAS" in str(exc_info.value)
    
    def test_valores_monetarios_validos(self):
        """Teste valores monetários válidos"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE",
            "valor_principal_liquido": Decimal("15000.50"),
            "valor_principal_bruto": Decimal("18000.75"),
            "valor_total_requisitado": Decimal("20000.00")
        }
        
        oficio = OficioRequisitorio(**data)
        
        assert oficio.valor_principal_liquido == Decimal("15000.50")
        assert oficio.valor_principal_bruto == Decimal("18000.75")
        assert oficio.valor_total_requisitado == Decimal("20000.00")
    
    def test_valores_monetarios_negativos(self):
        """Teste valores monetários negativos (inválidos)"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE",
            "valor_principal_liquido": Decimal("-1000.00")
        }
        
        with pytest.raises(ValidationError):
            OficioRequisitorio(**data)
    
    def test_datas_formato_iso(self):
        """Teste datas em formato ISO"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE",
            "data_ajuizamento": date(2018, 12, 15),
            "data_transito_julgado": date(2021, 6, 30),
            "data_base_atualizacao": date(2024, 1, 1)
        }
        
        oficio = OficioRequisitorio(**data)
        
        assert oficio.data_ajuizamento == date(2018, 12, 15)
        assert oficio.data_transito_julgado == date(2021, 6, 30)
        assert oficio.data_base_atualizacao == date(2024, 1, 1)
    
    def test_preferencias_boolean(self):
        """Teste campos de preferências (boolean)"""
        data = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE",
            "idoso": True,
            "doenca_grave": False,
            "pcd": True
        }
        
        oficio = OficioRequisitorio(**data)
        
        assert oficio.idoso is True
        assert oficio.doenca_grave is False
        assert oficio.pcd is True
    
    def test_validacao_oab_formato(self):
        """Teste validação formato OAB"""
        data_base = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE"
        }
        
        # Formato válido
        data_base["advogado_oab"] = "OAB/SP 123.456"
        oficio = OficioRequisitorio(**data_base)
        assert oficio.advogado_oab == "OAB/SP 123.456"
        
        # Formato que será normalizado
        data_base["advogado_oab"] = "123456/SP"
        oficio = OficioRequisitorio(**data_base)
        assert oficio.advogado_oab == "OAB/SP 123456"
    
    def test_validacao_cpf_cnpj(self):
        """Teste validação CPF/CNPJ"""
        data_base = {
            "processo_origem": "0035938-67.2018.8.26.0053",
            "requerente_caps": "TESTE"
        }
        
        # CPF válido
        data_base["credor_cpf_cnpj"] = "12345678901"
        oficio = OficioRequisitorio(**data_base)
        assert oficio.credor_cpf_cnpj == "123.456.789-01"
        
        # CNPJ válido
        data_base["credor_cpf_cnpj"] = "12345678000195"
        oficio = OficioRequisitorio(**data_base)
        assert oficio.credor_cpf_cnpj == "12.345.678/0001-95"
        
        # Formato inválido
        data_base["credor_cpf_cnpj"] = "123456"
        with pytest.raises(ValidationError):
            OficioRequisitorio(**data_base)


class TestProcessoMetadata:
    """Testes do schema ProcessoMetadata"""
    
    def test_metadata_valida(self):
        """Teste metadata válida"""
        data = {
            "cpf": "02174781824",
            "numero_processo": "0176505-63.2021.8.26.0500",
            "texto_completo_oficio": "Texto do ofício",
            "paginas_oficio": [1, 2, 3]
        }
        
        metadata = ProcessoMetadata(**data)
        
        assert metadata.cpf == "02174781824"
        assert metadata.numero_processo == "0176505-63.2021.8.26.0500"
        assert metadata.paginas_oficio == [1, 2, 3]
        assert isinstance(metadata.timestamp_processamento, datetime)
        assert metadata.processado is False
    
    def test_cpf_formato_invalido(self):
        """Teste CPF com formato inválido"""
        data = {
            "cpf": "123456789",  # Menos de 11 dígitos
            "numero_processo": "0176505-63.2021.8.26.0500",
            "texto_completo_oficio": "Texto",
            "paginas_oficio": [1]
        }
        
        with pytest.raises(ValidationError):
            ProcessoMetadata(**data)
    
    def test_cpf_nao_numerico(self):
        """Teste CPF não numérico"""
        data = {
            "cpf": "abc12345678",
            "numero_processo": "0176505-63.2021.8.26.0500",
            "texto_completo_oficio": "Texto",
            "paginas_oficio": [1]
        }
        
        with pytest.raises(ValidationError):
            ProcessoMetadata(**data)


class TestOficioCompleto:
    """Testes do schema OficioCompleto"""
    
    def test_oficio_completo_valido(self):
        """Teste ofício completo válido"""
        metadata = ProcessoMetadata(
            cpf="02174781824",
            numero_processo="0176505-63.2021.8.26.0500",
            texto_completo_oficio="Texto do ofício",
            paginas_oficio=[1, 2]
        )
        
        oficio = OficioRequisitorio(
            processo_origem="0035938-67.2018.8.26.0053",
            requerente_caps="FERNANDO SANTOS ERNESTO"
        )
        
        oficio_completo = OficioCompleto(
            metadata=metadata,
            oficio=oficio,
            data_envio=date(2024, 1, 15)
        )
        
        assert oficio_completo.metadata.cpf == "02174781824"
        assert oficio_completo.oficio.processo_origem == "0035938-67.2018.8.26.0053"
        assert oficio_completo.data_envio == date(2024, 1, 15)
    
    def test_oficio_completo_sem_oficio(self):
        """Teste ofício completo sem dados do ofício (erro no processamento)"""
        metadata = ProcessoMetadata(
            cpf="02174781824",
            numero_processo="0176505-63.2021.8.26.0500",
            texto_completo_oficio="",
            paginas_oficio=[],
            processado=False
        )
        
        oficio_completo = OficioCompleto(
            metadata=metadata,
            oficio=None
        )
        
        assert oficio_completo.metadata.processado is False
        assert oficio_completo.oficio is None
