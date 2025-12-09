"""
TrackerExecucao - Gerenciador de logs de execução em Markdown
Versão: 1.0.0
Data: 04/12/2025

Gera arquivos Markdown detalhados para cada CPF processado,
com estrutura hierárquica indentada mostrando todas as etapas.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from decimal import Decimal

logger = logging.getLogger(__name__)


class TrackerExecucao:
    """
    Rastreia e documenta toda a execução do pipeline OCR em formato Markdown.

    Uso:
        tracker = TrackerExecucao(cpf="03736870876", processo="0137444-93.2024.8.26.0500")
        tracker.iniciar(pdf_path="/path/to/file.pdf")
        tracker.adicionar_secao("1. Detecção de Ofícios")
        tracker.adicionar_item("Buscando ofícios...", nivel=1)
        tracker.adicionar_resultado("✅ Ofício 1 detectado", nivel=2)
        tracker.salvar("/path/to/logs/")
    """

    def __init__(self, cpf: str, processo: str):
        """
        Inicializa o tracker para um CPF/processo específico.

        Args:
            cpf: CPF sem formatação (ex: "03736870876")
            processo: Número do processo CNJ (ex: "0137444-93.2024.8.26.0500")
        """
        self.cpf = cpf
        self.processo = processo
        self.cpf_formatado = self._formatar_cpf(cpf)

        # Buffer do Markdown
        self.linhas = []

        # Controle de status
        self.status = "🔄 PROCESSANDO"
        self.data_inicio = datetime.now()
        self.data_fim = None

        # Estatísticas
        self.tempo_total = 0.0
        self.erros = []

        logger.debug(f"TrackerExecucao inicializado: CPF {self.cpf}, Processo {self.processo}")

    def _formatar_cpf(self, cpf: str) -> str:
        """Formata CPF: 03736870876 → 037.368.708-76"""
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf

    def iniciar(self, pdf_path: str, tamanho_mb: float = 0.0):
        """
        Adiciona cabeçalho do Markdown com informações iniciais.

        Args:
            pdf_path: Caminho completo do PDF
            tamanho_mb: Tamanho do arquivo em MB
        """
        self.linhas.append(f"# Execução: CPF {self.cpf} - Processo {self.processo}")
        self.linhas.append(f"**Data Início**: {self.data_inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        self.linhas.append(f"**Status**: {self.status}")
        self.linhas.append("")

        # Seção de inicialização
        self.linhas.append("## 📋 Inicialização")
        self.linhas.append(f"- 📁 **PDF**: `{pdf_path}`")
        self.linhas.append(f"- 👤 **CPF esperado**: `{self.cpf_formatado}`")
        if tamanho_mb > 0:
            self.linhas.append(f"- 📏 **Tamanho**: {tamanho_mb:.2f} MB")
        self.linhas.append("")

    def adicionar_secao(self, titulo: str):
        """
        Adiciona uma seção principal (##).

        Args:
            titulo: Título da seção (ex: "## 1. Detecção de Ofícios")
        """
        # Se não começar com ##, adicionar
        if not titulo.startswith("##"):
            titulo = f"## {titulo}"

        self.linhas.append(titulo)

    def adicionar_item(self, texto: str, nivel: int = 0, emoji: str = ""):
        """
        Adiciona um item com indentação opcional.

        Args:
            texto: Texto do item
            nivel: Nível de indentação (0=sem, 1=2 espaços, 2=4 espaços, etc.)
            emoji: Emoji opcional no início (ex: "🔍", "✅", "❌")
        """
        indent = "  " * nivel
        prefixo = f"{emoji} " if emoji else ""
        self.linhas.append(f"{indent}{prefixo}{texto}")

    def adicionar_resultado(self, texto: str, sucesso: bool = True, nivel: int = 1):
        """
        Adiciona um resultado com emoji automático (✅ ou ❌).

        Args:
            texto: Texto do resultado
            sucesso: True para ✅, False para ❌
            nivel: Nível de indentação
        """
        emoji = "✅" if sucesso else "❌"
        self.adicionar_item(texto, nivel=nivel, emoji=emoji)

    def adicionar_subsecao(self, titulo: str, nivel: int = 1):
        """
        Adiciona uma subseção com indentação e negrito.

        Args:
            titulo: Título da subseção
            nivel: Nível de indentação
        """
        indent = "  " * nivel
        self.linhas.append(f"{indent}**{titulo}**")

    def adicionar_detalhes(self, chave: str, valor: Any, nivel: int = 1):
        """
        Adiciona um par chave-valor formatado.

        Args:
            chave: Nome do campo
            valor: Valor do campo
            nivel: Nível de indentação
        """
        indent = "  " * nivel

        # Formatar valor
        if isinstance(valor, bool):
            valor_fmt = "✅ TRUE" if valor else "❌ FALSE"
        elif isinstance(valor, (int, float, Decimal)):
            if isinstance(valor, (float, Decimal)) and valor >= 100:
                valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                valor_fmt = str(valor)
        elif valor is None:
            valor_fmt = "❌ NULL"
        else:
            valor_fmt = str(valor)

        self.linhas.append(f"{indent}- **{chave}**: {valor_fmt}")

    def adicionar_lista(self, itens: list, nivel: int = 1, emoji: str = ""):
        """
        Adiciona uma lista de itens com marcadores.

        Args:
            itens: Lista de strings
            nivel: Nível de indentação
            emoji: Emoji opcional para cada item
        """
        for item in itens:
            self.adicionar_item(f"- {item}", nivel=nivel, emoji=emoji)

    def adicionar_divisor(self):
        """Adiciona uma linha divisória"""
        self.linhas.append("---")
        self.linhas.append("")

    def adicionar_linha_vazia(self):
        """Adiciona uma linha em branco"""
        self.linhas.append("")

    def finalizar(self, sucesso: bool, tempo_total: float = 0.0, dados: dict = None):
        """
        Finaliza o tracking com resumo e conclusão.

        Args:
            sucesso: True se processamento foi bem-sucedido
            tempo_total: Tempo total de processamento em segundos
            dados: Dicionário com dados extraídos (opcional)
        """
        self.data_fim = datetime.now()
        self.tempo_total = tempo_total
        self.status = "✅ SUCESSO" if sucesso else "❌ ERRO"

        # Adicionar divisor
        self.adicionar_divisor()

        # Seção de conclusão
        self.linhas.append("## 🏁 Conclusão")
        self.linhas.append(f"**Status Final**: {self.status}")
        self.linhas.append(f"**Data Fim**: {self.data_fim.strftime('%Y-%m-%d %H:%M:%S')}")

        if tempo_total > 0:
            self.linhas.append(f"**Tempo Total**: {tempo_total:.1f}s")

        # Se houver dados, adicionar resumo dos campos V2.5.2
        if dados and sucesso:
            self.adicionar_linha_vazia()
            self.linhas.append("### 📊 Resumo V2.5.2")

            # Campos principais
            if dados.get('cpf'):
                self.adicionar_detalhes("CPF", dados['cpf'], nivel=0)
            if dados.get('requerente_caps'):
                self.adicionar_detalhes("Requerente", dados['requerente_caps'], nivel=0)
            if dados.get('numero_ordem'):
                self.adicionar_detalhes("Nº Ordem", dados['numero_ordem'], nivel=0)
            if dados.get('valor_total_requisitado'):
                self.adicionar_detalhes("Valor Total", dados['valor_total_requisitado'], nivel=0)

            # Campos V2.5.2
            self.adicionar_linha_vazia()
            self.linhas.append("### 🆕 Campos V2.5.2")
            self.adicionar_detalhes("Saldo Final", dados.get('saldo_final', 'N/A'), nivel=0)
            self.adicionar_detalhes("Preferencial", dados.get('preferencial', False), nivel=0)
            self.adicionar_detalhes("Habilitação Herdeiros", dados.get('habilitacao_herdeiros', False), nivel=0)
            self.adicionar_detalhes("Cessão Crédito", dados.get('cessao_credito', False), nivel=0)

        # Adicionar erros se houver
        if self.erros:
            self.adicionar_linha_vazia()
            self.linhas.append("### ⚠️ Erros Encontrados")
            for i, erro in enumerate(self.erros, 1):
                self.linhas.append(f"{i}. {erro}")

    def adicionar_erro(self, mensagem: str):
        """
        Registra um erro ocorrido durante o processamento.

        Args:
            mensagem: Descrição do erro
        """
        self.erros.append(mensagem)
        self.adicionar_item(f"❌ ERRO: {mensagem}", nivel=1)
        logger.error(f"Tracker registrou erro: {mensagem}")

    def salvar(self, output_dir: str) -> Path:
        """
        Salva o Markdown no diretório especificado.

        Args:
            output_dir: Diretório onde salvar (ex: "outputs/logs")

        Returns:
            Path do arquivo salvo
        """
        # Criar diretório se não existir
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Nome do arquivo
        filename = f"{self.cpf}_{self.processo}_execution.md"
        filepath = output_path / filename

        # Atualizar status no cabeçalho
        if len(self.linhas) >= 3:
            self.linhas[2] = f"**Status**: {self.status}"

        # Escrever arquivo
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.linhas))

        logger.info(f"📄 Markdown salvo: {filepath}")
        return filepath

    def get_markdown(self) -> str:
        """
        Retorna o conteúdo Markdown como string.

        Returns:
            String com todo o conteúdo Markdown
        """
        return '\n'.join(self.linhas)

    def debug_print(self):
        """Imprime o Markdown atual no console (para debug)"""
        print("="*80)
        print(self.get_markdown())
        print("="*80)
