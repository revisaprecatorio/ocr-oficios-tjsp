#!/usr/bin/env python3
"""
Script para organizar PDFs em pastas de UAT (User Acceptance Testing) - V3.0.2
Adaptado do v2.5.1 para novo schema V3.0 (35 colunas)

Changelog V3.0:
- REMOVIDO: cessao_credito, requerente_caps (campos não existem mais)
- ADICIONADO: obito, cpf_sucessor, data_obito (novos campos)
- ATUALIZADO: credor_nome (vs requerente_caps), data_base_atualizacao (vs data_ajuizamento)
- Schema: 50→35 colunas

Autor: Claude Code + Persival Balleste
Data Criação Original: 14/11/2025
Data Adaptação V3.0: 14/12/2025
Versão: 3.0.2
"""

import pandas as pd
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrganizadorUAT_V3:
    """Organiza PDFs em pastas de UAT baseado em schema V3.0 (35 colunas)"""

    def __init__(self, csv_path: str, data_dir: str, output_dir: str):
        """
        Inicializa o organizador V3.0

        Args:
            csv_path: Caminho para o CSV de export
            data_dir: Diretório com os PDFs originais (data/consultas)
            output_dir: Diretório de saída (4_UAT_refinamento)
        """
        self.csv_path = Path(csv_path)
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)

        # Carregar CSV
        logger.info(f"Carregando CSV: {self.csv_path}")
        self.df = pd.read_csv(self.csv_path)
        logger.info(f"Total de processos no CSV: {len(self.df)}")

        # Converter booleanos (V3.0: sem cessao_credito)
        bool_cols = ['anomalia', 'habilitacao_herdeiros',
                     'preferencial', 'rejeitado', 'idoso', 'doenca_grave', 'pcd',
                     'obito']  # V3.0: novo campo
        for col in bool_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(False).astype(bool)

        # Estatísticas (V3.0: categorias atualizadas)
        self.stats = {
            '1_anomalia_formato': [],
            '3_herdeiros_nao_rejeitados': [],
            '4_preferencial': [],
            '5_rejeitados': [],
            '6_obito_sucessao': [],  # V3.0: NOVO
            '7_dados_bancarios_incompletos': [],
            '9_sem_juros_moratorios': [],
            '10_amostra_baseline': [],
            '11_processos_ok_100': []
        }

    def criar_estrutura_pastas(self):
        """Cria estrutura de pastas do UAT V3.0"""
        logger.info(f"Criando estrutura V3.0 em: {self.output_dir}")

        pastas = [
            '1_anomalia_formato',
            '3_herdeiros_nao_rejeitados',
            '4_preferencial',
            '5_rejeitados',
            '6_obito_sucessao',  # V3.0: NOVO
            '7_dados_bancarios_incompletos',
            '9_sem_juros_moratorios',
            '10_amostra_baseline',
            '11_processos_ok_100'
        ]

        for pasta in pastas:
            pasta_path = self.output_dir / pasta
            pasta_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"  ✓ {pasta}/")

    def copiar_pdf(self, row: pd.Series, destino_pasta: str) -> bool:
        """
        Copia PDF para pasta de destino mantendo estrutura cpf/processo.pdf

        Args:
            row: Linha do DataFrame
            destino_pasta: Nome da pasta de destino

        Returns:
            True se copiou com sucesso, False caso contrário
        """
        try:
            # Extrair informações
            cpf = str(row['cpf'])
            caminho_pdf = row['caminho_pdf']

            # Caminho origem
            caminho_relativo = caminho_pdf.replace('data/consultas/', '')
            origem = self.data_dir / caminho_relativo

            if not origem.exists():
                logger.warning(f"PDF não encontrado: {origem}")
                return False

            # Caminho destino (mantém estrutura cpf/processo.pdf)
            destino_dir = self.output_dir / destino_pasta / cpf
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino = destino_dir / origem.name

            # Copiar
            shutil.copy2(origem, destino)
            logger.debug(f"  ✓ Copiado: {origem.name} → {destino_pasta}/{cpf}/")

            return True

        except Exception as e:
            logger.error(f"Erro ao copiar {row.get('numero_processo_cnj', 'N/A')}: {e}")
            return False

    def aplicar_regras(self):
        """Aplica regras de categorização V3.0 e copia PDFs"""

        logger.info("\n" + "="*80)
        logger.info("APLICANDO REGRAS DE CATEGORIZAÇÃO V3.0")
        logger.info("="*80 + "\n")

        # Conjunto para rastrear PDFs já categorizados
        ja_categorizados = set()

        # REGRA 1: Anomalia de Formato (PRIORIDADE ALTA)
        logger.info("📋 REGRA 1: Anomalia de Formato")
        regra1 = self.df[self.df['anomalia'] == True]
        logger.info(f"   Processos encontrados: {len(regra1)}")

        for idx, row in regra1.iterrows():
            if self.copiar_pdf(row, '1_anomalia_formato'):
                self.stats['1_anomalia_formato'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['1_anomalia_formato'])}\n")

        # REGRA 2: V3.0 - REMOVIDA (cessao_credito não existe mais)
        logger.info("📋 REGRA 2: Cessão de Crédito - REMOVIDA (V3.0)")
        logger.info("   Campo 'cessao_credito' não existe mais no schema V3.0\n")

        # REGRA 3: Herdeiros Não Rejeitados (excluindo anteriores)
        logger.info("📋 REGRA 3: Herdeiros Não Rejeitados")
        regra3 = self.df[
            (self.df['habilitacao_herdeiros'] == True) &
            (self.df['rejeitado'] != True) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra3)}")

        for idx, row in regra3.iterrows():
            if self.copiar_pdf(row, '3_herdeiros_nao_rejeitados'):
                self.stats['3_herdeiros_nao_rejeitados'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['3_herdeiros_nao_rejeitados'])}\n")

        # REGRA 4: Preferencial (excluindo anteriores)
        logger.info("📋 REGRA 4: Preferencial")
        regra4 = self.df[
            (self.df['preferencial'] == True) &
            (self.df['rejeitado'] != True) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra4)}")

        for idx, row in regra4.iterrows():
            if self.copiar_pdf(row, '4_preferencial'):
                self.stats['4_preferencial'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['4_preferencial'])}\n")

        # REGRA 5: Rejeitados (V3.0.2: Agora detectados corretamente!)
        logger.info("📋 REGRA 5: Rejeitados (V3.0.2: Detecção REGEX-first)")
        regra5 = self.df[self.df['rejeitado'] == True]
        logger.info(f"   Processos encontrados: {len(regra5)}")

        for idx, row in regra5.iterrows():
            if self.copiar_pdf(row, '5_rejeitados'):
                self.stats['5_rejeitados'].append(row['numero_processo_cnj'])
                # Não adiciona a ja_categorizados pois pode estar em outras

        logger.info(f"   ✓ Copiados: {len(self.stats['5_rejeitados'])}\n")

        # REGRA 6: V3.0 - NOVO - Óbito e Sucessão
        logger.info("📋 REGRA 6: Óbito e Sucessão (V3.0: NOVO)")
        regra6 = self.df[
            (self.df['obito'] == True) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra6)}")

        for idx, row in regra6.iterrows():
            if self.copiar_pdf(row, '6_obito_sucessao'):
                self.stats['6_obito_sucessao'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['6_obito_sucessao'])}\n")

        # REGRA 7: Dados Bancários Incompletos - SUGESTÃO
        logger.info("📋 REGRA 7: Dados Bancários Incompletos")
        regra7 = self.df[
            (
                (self.df['banco'].isna()) |
                (self.df['banco'] == 'null') |
                (self.df['agencia'].isna()) |
                (self.df['conta'].isna())
            ) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra7)}")

        for idx, row in regra7.iterrows():
            if self.copiar_pdf(row, '7_dados_bancarios_incompletos'):
                self.stats['7_dados_bancarios_incompletos'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['7_dados_bancarios_incompletos'])}\n")

        # REGRA 8: V3.0 - REMOVIDA (dependia de requerente_caps)
        logger.info("📋 REGRA 8: Múltiplos Credores - REMOVIDA (V3.0)")
        logger.info("   Campo 'requerente_caps' foi removido do schema V3.0\n")

        # REGRA 9: Sem Juros Moratórios - SUGESTÃO
        logger.info("📋 REGRA 9: Sem Juros Moratórios")

        # Converter valores para float
        def parse_valor(v):
            if pd.isna(v) or v == '-':
                return 0.0
            if isinstance(v, str):
                v = v.replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(v)
            except:
                return 0.0

        self.df['juros_float'] = self.df['juros_moratorios'].apply(parse_valor)

        regra9 = self.df[
            (self.df['juros_float'] == 0) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra9)}")

        # Limitar a 10 amostras
        regra9_sample = regra9.head(10)

        for idx, row in regra9_sample.iterrows():
            if self.copiar_pdf(row, '9_sem_juros_moratorios'):
                self.stats['9_sem_juros_moratorios'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)

        logger.info(f"   ✓ Copiados: {len(self.stats['9_sem_juros_moratorios'])} (limitado a 10)\n")

        # REGRA 10: Amostra Baseline (10% dos normais) - SUGESTÃO
        logger.info("📋 REGRA 10: Amostra Baseline (Processos Normais)")
        processos_normais = self.df[~self.df.index.isin(ja_categorizados)]
        logger.info(f"   Processos normais disponíveis: {len(processos_normais)}")

        # 10% ou mínimo 5
        n_amostras = max(5, int(len(processos_normais) * 0.1))
        regra10 = processos_normais.sample(n=min(n_amostras, len(processos_normais)), random_state=42) if len(processos_normais) > 0 else pd.DataFrame()
        logger.info(f"   Selecionando {len(regra10)} amostras aleatórias")

        for idx, row in regra10.iterrows():
            if self.copiar_pdf(row, '10_amostra_baseline'):
                self.stats['10_amostra_baseline'].append(row['numero_processo_cnj'])

        logger.info(f"   ✓ Copiados: {len(self.stats['10_amostra_baseline'])}\n")

        # REGRA 11: Processos OK 100% (sem problemas)
        logger.info("📋 REGRA 11: Processos OK 100% (Sem Problemas)")

        # V3.0: Processos OK = não rejeitados, sem anomalia, sem dados bancários incompletos, sem óbito
        processos_ok = self.df[
            (self.df['rejeitado'] != True) &
            (self.df['anomalia'] != True) &
            (self.df['obito'] != True) &  # V3.0: NOVO critério
            (self.df['banco'].notna()) &
            (self.df['banco'] != 'null') &
            (self.df['agencia'].notna()) &
            (self.df['conta'].notna()) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos OK disponíveis: {len(processos_ok)}")

        # Selecionar até 10 amostras aleatórias
        n_amostras_ok = min(10, len(processos_ok))
        regra11 = processos_ok.sample(n=n_amostras_ok, random_state=42) if len(processos_ok) > 0 else pd.DataFrame()
        logger.info(f"   Selecionando {len(regra11)} amostras de processos OK")

        for idx, row in regra11.iterrows():
            if self.copiar_pdf(row, '11_processos_ok_100'):
                self.stats['11_processos_ok_100'].append(row['numero_processo_cnj'])

        logger.info(f"   ✓ Copiados: {len(self.stats['11_processos_ok_100'])}\n")

    def gerar_relatorio(self):
        """Gera relatório de estatísticas V3.0"""
        logger.info("\n" + "="*80)
        logger.info("RELATÓRIO DE ORGANIZAÇÃO UAT V3.0")
        logger.info("="*80 + "\n")

        total_copiados = sum(len(v) for v in self.stats.values())

        print(f"📊 Total de processos no CSV: {len(self.df)}")
        print(f"📦 Total de PDFs copiados: {total_copiados}\n")

        print("📁 Distribuição por categoria (V3.0):\n")

        categorias = {
            '1_anomalia_formato': 'Anomalia de Formato (ALTA)',
            '3_herdeiros_nao_rejeitados': 'Herdeiros Não Rejeitados (MÉDIA)',
            '4_preferencial': 'Preferencial (MÉDIA)',
            '5_rejeitados': 'Rejeitados (ALTA - V3.0.2: REGEX-first)',
            '6_obito_sucessao': 'Óbito e Sucessão (MÉDIA - V3.0: NOVO)',
            '7_dados_bancarios_incompletos': 'Dados Bancários Incompletos (SUGESTÃO)',
            '9_sem_juros_moratorios': 'Sem Juros Moratórios (SUGESTÃO)',
            '10_amostra_baseline': 'Amostra Baseline (SUGESTÃO)',
            '11_processos_ok_100': 'Processos OK 100% (BASELINE)'
        }

        for pasta, descricao in categorias.items():
            count = len(self.stats[pasta])
            print(f"  {pasta:35} → {count:3} PDFs - {descricao}")

        print("\n" + "="*80)
        print("📝 V3.0 MUDANÇAS:")
        print("  ✅ ADICIONADO: 6_obito_sucessao (novos campos V3.0)")
        print("  ❌ REMOVIDO: 2_cessao_credito (campo não existe mais)")
        print("  ❌ REMOVIDO: 8_multiplos_credores (dependia de requerente_caps)")
        print("  🔧 Schema: 50→35 colunas")
        print("="*80 + "\n")
        print(f"✅ Organização V3.0 concluída! PDFs em: {self.output_dir}")
        print("="*80 + "\n")

    def gerar_readme(self):
        """Gera README.md com documentação do UAT V3.0"""
        readme_path = self.output_dir / 'README_UAT_V3.md'

        hoje = datetime.now().strftime("%d/%m/%Y")

        content = f"""# 📋 UAT V3.0 - User Acceptance Testing

**Data de Criação:** {hoje}
**Versão Sistema:** V3.0.2
**Schema:** 35 colunas (reduzido de 50 em v2.5.1)
**Total de Processos:** {len(self.df)}
**Total de PDFs para Validação:** {sum(len(v) for v in self.stats.values())}
**Taxa de Captura:** {len(self.df)}/{len(self.df)} (100%)

---

## 🆕 Mudanças V3.0

### ✅ Campos Adicionados
- `obito` (boolean) - Indica se credor faleceu
- `data_obito` (date) - Data do óbito do credor
- `cpf_sucessor` (string) - CPF do sucessor/herdeiro

### ❌ Campos Removidos (15 colunas)
- `cessao_credito` - Não rastreamos mais cessões de crédito
- `requerente_caps` - Substituído por `credor_nome`
- `data_ajuizamento` - Substituído por `data_base_atualizacao`
- +12 outros campos não utilizados

### 🔧 Schema
- **v2.5.1:** 50 colunas
- **V3.0:** 35 colunas (-30%)

---

## 🎯 Objetivo

Esta estrutura organiza PDFs de Ofícios Requisitórios em categorias específicas para facilitar o **User Acceptance Testing (UAT)** e validação de qualidade da extração de dados usando o novo schema V3.0.

---

## 📁 Estrutura de Pastas V3.0

### 🔴 **PRIORIDADE ALTA - Validação Imediata**

#### **1. Anomalia de Formato**
**Pasta:** `1_anomalia_formato/`
**Quantidade:** {len(self.stats['1_anomalia_formato'])} PDFs
**Descrição:** PDFs com formato antigo (7xxxxxx) ou estrutura diferente do padrão atual.
**Ação:** ⚠️ Validar se dados foram extraídos corretamente apesar da estrutura diferente.
**Tempo Estimado:** ~30 minutos

#### **5. Rejeitados**
**Pasta:** `5_rejeitados/`
**Quantidade:** {len(self.stats['5_rejeitados'])} PDFs
**Descrição:** ✅ Processos rejeitados pelo DEPRE - **V3.0.2: Detecção REGEX-first implementada!**
**Ação:** Confirmar que campo `motivo_rejeicao` foi capturado corretamente.
**Tempo Estimado:** ~15 minutos
**Nota:** Rejeição é um **sucesso** - sistema identificou status corretamente.

---

### 🟡 **PRIORIDADE MÉDIA - Validação Importante**

#### **3. Herdeiros Não Rejeitados**
**Pasta:** `3_herdeiros_nao_rejeitados/`
**Quantidade:** {len(self.stats['3_herdeiros_nao_rejeitados'])} PDFs
**Descrição:** Processos com habilitação de herdeiros aprovados.
**Ação:** Validar múltiplos credores e distribuição de valores.
**Tempo Estimado:** ~1 hora

#### **4. Preferencial**
**Pasta:** `4_preferencial/`
**Quantidade:** {len(self.stats['4_preferencial'])} PDFs
**Descrição:** Processos com preferência (idoso ≥60 anos, doença grave, PCD).
**Ação:** Validar marcadores de preferência e dados do credor.
**Tempo Estimado:** ~30 minutos

#### **6. Óbito e Sucessão** (V3.0: NOVO)
**Pasta:** `6_obito_sucessao/`
**Quantidade:** {len(self.stats['6_obito_sucessao'])} PDFs
**Descrição:** ⚰️ Processos onde o credor faleceu e há sucessor.
**Ação:** Validar `obito=true`, `data_obito`, `cpf_sucessor`, e `habilitacao_herdeiros`.
**Tempo Estimado:** ~30 minutos
**Nota:** V3.0 adiciona rastreamento de óbito e sucessão.

---

### 🔵 **SUGESTÕES - Validação Complementar**

#### **7. Dados Bancários Incompletos**
**Pasta:** `7_dados_bancarios_incompletos/`
**Quantidade:** {len(self.stats['7_dados_bancarios_incompletos'])} PDFs
**Descrição:** Processos com banco, agência ou conta vazios.
**Ação:** Validar se dados bancários estão realmente ausentes no PDF ou se houve erro de extração.
**Tempo Estimado:** ~5 minutos

#### **9. Sem Juros Moratórios**
**Pasta:** `9_sem_juros_moratorios/`
**Quantidade:** {len(self.stats['9_sem_juros_moratorios'])} PDFs (limitado a 10)
**Descrição:** Processos sem juros moratórios ou com valor zero.
**Ação:** Validar se realmente não há juros ou se houve erro de extração.
**Tempo Estimado:** ~30 minutos

#### **10. Amostra Baseline**
**Pasta:** `10_amostra_baseline/`
**Quantidade:** {len(self.stats['10_amostra_baseline'])} PDFs
**Descrição:** Amostra aleatória de processos "normais" (10% dos não categorizados).
**Ação:** Validação de qualidade geral da extração.
**Tempo Estimado:** ~30 minutos

#### **11. Processos OK 100%**
**Pasta:** `11_processos_ok_100/`
**Quantidade:** {len(self.stats['11_processos_ok_100'])} PDFs
**Descrição:** Processos sem problemas (não rejeitados, sem anomalia, dados bancários completos, sem óbito).
**Ação:** Validação de qualidade baseline - estes devem estar 100% corretos.
**Tempo Estimado:** ~15 minutos

---

### ❌ **CATEGORIAS REMOVIDAS (v2.5.1 → V3.0)**

#### ~~**2. Cessão de Crédito**~~ (REMOVIDA)
**Motivo:** Campo `cessao_credito` foi removido do schema V3.0
**Alternativa:** Não rastreamos mais cessões de crédito

#### ~~**8. Múltiplos Credores**~~ (REMOVIDA)
**Motivo:** Dependia de `requerente_caps` (removido em V3.0)
**Alternativa:** Usar `credor_nome` para identificação

---

## 📊 Estatísticas Detalhadas

### **Resumo por Prioridade**

| Prioridade | Quantidade | % do Total | Tempo Estimado | Ação |
|------------|------------|------------|----------------|------|
| 🔴 **ALTA** | {len(self.stats['1_anomalia_formato']) + len(self.stats['5_rejeitados'])} | - | ~45 min | Validação imediata |
| 🟡 **MÉDIA** | {len(self.stats['3_herdeiros_nao_rejeitados']) + len(self.stats['4_preferencial']) + len(self.stats['6_obito_sucessao'])} | - | ~2 horas | Validação importante |
| 🔵 **SUGESTÕES** | {len(self.stats['7_dados_bancarios_incompletos']) + len(self.stats['9_sem_juros_moratorios']) + len(self.stats['10_amostra_baseline']) + len(self.stats['11_processos_ok_100'])} | - | ~1 hora | Validação complementar |
| **TOTAL PDFs** | **{sum(len(v) for v in self.stats.values())}** | **100%** | **~3-4 horas** | - |

### **Distribuição por Categoria**

| # | Categoria | PDFs | Prioridade | Status |
|---|-----------|------|------------|--------|
| 1 | Anomalia de Formato | {len(self.stats['1_anomalia_formato'])} | 🔴 ALTA | ⚠️ Requer atenção |
| 3 | Herdeiros Não Rejeitados | {len(self.stats['3_herdeiros_nao_rejeitados'])} | 🟡 MÉDIA | 📋 Validar credores |
| 4 | Preferencial | {len(self.stats['4_preferencial'])} | 🟡 MÉDIA | 📋 Validar marcadores |
| 5 | Rejeitados | {len(self.stats['5_rejeitados'])} | 🔴 ALTA | ✅ V3.0.2: REGEX-first |
| 6 | Óbito e Sucessão | {len(self.stats['6_obito_sucessao'])} | 🟡 MÉDIA | 🆕 V3.0: NOVO |
| 7 | Dados Bancários Incompletos | {len(self.stats['7_dados_bancarios_incompletos'])} | 🔵 SUGESTÃO | 🔍 Verificar |
| 9 | Sem Juros Moratórios | {len(self.stats['9_sem_juros_moratorios'])} | 🔵 SUGESTÃO | 🔍 Verificar |
| 10 | Amostra Baseline | {len(self.stats['10_amostra_baseline'])} | 🔵 SUGESTÃO | 🔍 Qualidade |
| 11 | Processos OK 100% | {len(self.stats['11_processos_ok_100'])} | 🔵 BASELINE | ✅ Referência |

---

## ✅ Checklist de Validação V3.0

Para cada PDF, validar:

### **Campos Básicos (35 colunas)**
- [ ] **CPF** e **numero_processo_cnj**
- [ ] **processo_origem**
- [ ] **numero_ordem** (null se rejeitado)
- [ ] **vara**

### **Datas**
- [ ] **data_base_atualizacao** (V3.0: substitui data_ajuizamento)
- [ ] **data_nascimento**
- [ ] **data_obito** (V3.0: NOVO - se aplicável)

### **Partes**
- [ ] **credor_nome** (V3.0: substitui requerente_caps)
- [ ] **credor_cpf_cnpj**
- [ ] **devedor_ente**
- [ ] **cpf_sucessor** (V3.0: NOVO - se aplicável)

### **Dados Bancários**
- [ ] **banco** (3 dígitos)
- [ ] **agencia**
- [ ] **conta**

### **Valores Financeiros**
- [ ] **valor_principal_liquido**
- [ ] **valor_principal_bruto**
- [ ] **juros_moratorios**
- [ ] **valor_total_requisitado**
- [ ] **saldo_final**

### **Preferências**
- [ ] **idoso** (≥60 anos)
- [ ] **doenca_grave**
- [ ] **pcd**
- [ ] **preferencial**
- [ ] **habilitacao_herdeiros**
- [ ] **obito** (V3.0: NOVO)

### **Controle**
- [ ] **rejeitado**
- [ ] **motivo_rejeicao** (V3.0.2: REGEX-first)
- [ ] **observacoes**
- [ ] **anomalia**
- [ ] **descricao_anomalia**

---

## 🔧 Plano de Validação Recomendado

### **Fase 1: ALTA Prioridade** ⏱️ ~45 minutos
```bash
# 1. Anomalias de Formato (~30 min)
cd 1_anomalia_formato/
# Validar estrutura antiga (7xxxxxx)

# 2. Rejeitados (~15 min)
cd ../5_rejeitados/
# V3.0.2: Confirmar detecção REGEX de motivo_rejeicao
```

### **Fase 2: MÉDIA Prioridade** ⏱️ ~2 horas
```bash
# 3. Herdeiros (~1 hora)
cd ../3_herdeiros_nao_rejeitados/

# 4. Preferencial (~30 min)
cd ../4_preferencial/

# 6. Óbito e Sucessão - V3.0: NOVO (~30 min)
cd ../6_obito_sucessao/
# Validar: obito=true, data_obito, cpf_sucessor
```

### **Fase 3: SUGESTÕES (Opcional)** ⏱️ ~1 hora
```bash
cd ../7_dados_bancarios_incompletos/  # ~5 min
cd ../9_sem_juros_moratorios/         # ~30 min
cd ../10_amostra_baseline/            # ~30 min
cd ../11_processos_ok_100/            # ~15 min
```

---

## 📝 Relatório de Validação

Criar planilha com colunas:

| CPF | Processo | Categoria | Status | Campos V3.0 OK | Observações |
|-----|----------|-----------|--------|----------------|-------------|
| ... | ... | ... | ✅/❌ | obito, cpf_sucessor | ... |

---

## 🚀 Próximos Passos

Após UAT V3.0:
1. Consolidar erros encontrados
2. Ajustar detecção REGEX se necessário (V3.0.2: rejeição já otimizada)
3. Reprocessar PDFs com erros
4. Atualizar banco PostgreSQL
5. Deploy V3.1.0

---

## 🔗 Referências

- **Schema V3.0:** `1_parsing_PDF/app/schemas.py`
- **Ingestão V3.0:** `2_ingestao/scripts/ingest_v3_0.py`
- **CHANGELOG:** `CHANGELOG.md` (V3.0.2)
- **Script Organização:** `organizar_uat_v3.py`

---

## 📄 Informações do Documento

**Gerado automaticamente por:** `organizar_uat_v3.py`
**Data de Criação:** {hoje}
**Versão do Sistema:** V3.0.2
**Schema:** 35 colunas (reduzido de 50 em v2.5.1)
**Autor:** Claude Code + Persival Balleste

---

**Status:** ✅ **Estrutura UAT V3.0 completa e pronta para validação!**

**Tempo Total Estimado:** ~3-4 horas
**Prioridade Imediata:** Anomalias + Rejeitados (~45 minutos)

---

## 📌 Migração v2.5.1 → V3.0

### Mudanças no Script
- ✅ Adicionada categoria `6_obito_sucessao`
- ❌ Removida categoria `2_cessao_credito`
- ❌ Removida categoria `8_multiplos_credores`
- 🔧 Atualizada lógica para 35 colunas

### Campos Substituídos
- `requerente_caps` → `credor_nome`
- `data_ajuizamento` → `data_base_atualizacao`

### Novos Campos V3.0
- `obito` (boolean)
- `data_obito` (date)
- `cpf_sucessor` (string)

**UAT anterior (v2.5.1):** Arquivado em `2_ingestao/historico_evolucao_anteriores/4_UAT_refinamento_v2.5.1_LEGACY/`
"""

        readme_path.write_text(content, encoding='utf-8')
        logger.info(f"✓ README V3.0 gerado: {readme_path}")


def main():
    """Função principal V3.0"""

    print("="*80)
    print("📥 UAT ORGANIZER V3.0.2")
    print("="*80)
    print("\n🔧 Mudanças em relação a v2.5.1:")
    print("  ✅ ADICIONADO: Categoria 6_obito_sucessao (novos campos V3.0)")
    print("  ❌ REMOVIDO: Categoria 2_cessao_credito (campo não existe)")
    print("  ❌ REMOVIDO: Categoria 8_multiplos_credores (dependia de requerente_caps)")
    print("  🔧 Schema: 50→35 colunas\n")
    print("="*80 + "\n")

    # Configurações (caminhos relativos ao root do projeto)
    CSV_PATH = "../tests/LATEST_export.csv"  # Atualizar para CSV mais recente
    DATA_DIR = "../data/consultas"
    OUTPUT_DIR = "."  # Já estamos dentro de 4_UAT_refinamento

    # Criar organizador V3.0
    organizador = OrganizadorUAT_V3(
        csv_path=CSV_PATH,
        data_dir=DATA_DIR,
        output_dir=OUTPUT_DIR
    )

    # Executar
    organizador.criar_estrutura_pastas()
    organizador.aplicar_regras()
    organizador.gerar_relatorio()
    organizador.gerar_readme()

    logger.info("\n✅ Processo V3.0 concluído com sucesso!")


if __name__ == "__main__":
    main()
