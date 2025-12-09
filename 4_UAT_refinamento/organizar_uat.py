#!/usr/bin/env python3
"""
Script para organizar PDFs em pastas de UAT (User Acceptance Testing)
Baseado em condições específicas do CSV de export.

Autor: Cascade AI + Persival Balleste
Data: 14/11/2025
Versão: 1.0.0
"""

import pandas as pd
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrganizadorUAT:
    """Organiza PDFs em pastas de UAT baseado em condições do CSV"""
    
    def __init__(self, csv_path: str, data_dir: str, output_dir: str):
        """
        Inicializa o organizador
        
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
        
        # Converter booleanos
        bool_cols = ['anomalia', 'cessao_credito', 'habilitacao_herdeiros', 
                     'preferencial', 'rejeitado', 'idoso', 'doenca_grave', 'pcd']
        for col in bool_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(False).astype(bool)
        
        # Estatísticas
        self.stats = {
            '1_anomalia_formato': [],
            '2_cessao_credito': [],
            '3_herdeiros_nao_rejeitados': [],
            '4_preferencial': [],
            '5_rejeitados': [],
            '6_valores_altos': [],
            '7_dados_bancarios_incompletos': [],
            '8_multiplos_credores': [],
            '9_sem_juros_moratorios': [],
            '10_amostra_baseline': [],
            '11_processos_ok_100': []
        }
    
    def criar_estrutura_pastas(self):
        """Cria estrutura de pastas do UAT"""
        logger.info(f"Criando estrutura em: {self.output_dir}")
        
        pastas = [
            '1_anomalia_formato',
            '2_cessao_credito',
            '3_herdeiros_nao_rejeitados',
            '4_preferencial',
            '5_rejeitados',
            '6_valores_altos',
            '7_dados_bancarios_incompletos',
            '8_multiplos_credores',
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
            
            # Caminho origem (caminho_pdf já contém "data/consultas/...")
            # Precisamos remover o prefixo "data/consultas" do caminho_pdf
            # pois self.data_dir já aponta para "../data/consultas"
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
        """Aplica regras de categorização e copia PDFs"""
        
        logger.info("\n" + "="*80)
        logger.info("APLICANDO REGRAS DE CATEGORIZAÇÃO")
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
        
        # REGRA 2: Cessão de Crédito (excluindo anomalias)
        logger.info("📋 REGRA 2: Cessão de Crédito")
        regra2 = self.df[
            (self.df['cessao_credito'] == True) & 
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra2)}")
        
        for idx, row in regra2.iterrows():
            if self.copiar_pdf(row, '2_cessao_credito'):
                self.stats['2_cessao_credito'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)
        
        logger.info(f"   ✓ Copiados: {len(self.stats['2_cessao_credito'])}\n")
        
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
        
        # REGRA 5: Rejeitados
        logger.info("📋 REGRA 5: Rejeitados")
        regra5 = self.df[self.df['rejeitado'] == True]
        logger.info(f"   Processos encontrados: {len(regra5)}")
        
        for idx, row in regra5.iterrows():
            if self.copiar_pdf(row, '5_rejeitados'):
                self.stats['5_rejeitados'].append(row['numero_processo_cnj'])
                # Não adiciona a ja_categorizados pois pode estar em outras
        
        logger.info(f"   ✓ Copiados: {len(self.stats['5_rejeitados'])}\n")
        
        # REGRA 6: Valores Altos (> R$ 500k) - SUGESTÃO
        logger.info("📋 REGRA 6: Valores Altos (> R$ 500.000)")
        
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
        
        self.df['valor_total_float'] = self.df['valor_total_requisitado'].apply(parse_valor)
        
        regra6 = self.df[
            (self.df['valor_total_float'] > 500000) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra6)}")
        
        for idx, row in regra6.iterrows():
            if self.copiar_pdf(row, '6_valores_altos'):
                self.stats['6_valores_altos'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)
        
        logger.info(f"   ✓ Copiados: {len(self.stats['6_valores_altos'])}\n")
        
        # REGRA 7: Dados Bancários Incompletos - SUGESTÃO
        logger.info("📋 REGRA 7: Dados Bancários Incompletos")
        regra7 = self.df[
            (
                (self.df['banco'] == 'ERRO') | 
                (self.df['agencia'] == 'ERRO') | 
                (self.df['conta'] == 'ERRO') |
                (self.df['banco'].isna()) |
                (self.df['banco'] == 'null')
            ) &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra7)}")
        
        for idx, row in regra7.iterrows():
            if self.copiar_pdf(row, '7_dados_bancarios_incompletos'):
                self.stats['7_dados_bancarios_incompletos'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)
        
        logger.info(f"   ✓ Copiados: {len(self.stats['7_dados_bancarios_incompletos'])}\n")
        
        # REGRA 8: Múltiplos Credores - SUGESTÃO
        logger.info("📋 REGRA 8: Múltiplos Credores")
        regra8 = self.df[
            (self.df['credor_nome'] != self.df['requerente_caps']) &
            (self.df['cessao_credito'] != True) &
            (self.df['credor_nome'].notna()) &
            (self.df['credor_nome'] != 'ERRO') &
            (~self.df.index.isin(ja_categorizados))
        ]
        logger.info(f"   Processos encontrados: {len(regra8)}")
        
        for idx, row in regra8.iterrows():
            if self.copiar_pdf(row, '8_multiplos_credores'):
                self.stats['8_multiplos_credores'].append(row['numero_processo_cnj'])
                ja_categorizados.add(idx)
        
        logger.info(f"   ✓ Copiados: {len(self.stats['8_multiplos_credores'])}\n")
        
        # REGRA 9: Sem Juros Moratórios - SUGESTÃO
        logger.info("📋 REGRA 9: Sem Juros Moratórios")
        regra9 = self.df[
            (
                (self.df['juros_moratorios'] == 0) |
                (self.df['juros_moratorios'].isna())
            ) &
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
        regra10 = processos_normais.sample(n=min(n_amostras, len(processos_normais)), random_state=42)
        logger.info(f"   Selecionando {len(regra10)} amostras aleatórias")
        
        for idx, row in regra10.iterrows():
            if self.copiar_pdf(row, '10_amostra_baseline'):
                self.stats['10_amostra_baseline'].append(row['numero_processo_cnj'])
        
        logger.info(f"   ✓ Copiados: {len(self.stats['10_amostra_baseline'])}\n")
        
        # REGRA 11: Processos OK 100% (sem problemas)
        logger.info("📋 REGRA 11: Processos OK 100% (Sem Problemas)")
        
        # Processos OK = não rejeitados, sem anomalia, sem dados bancários incompletos
        processos_ok = self.df[
            (self.df['rejeitado'] != True) &
            (self.df['anomalia'] != True) &
            (self.df['banco'] != 'ERRO') &
            (self.df['agencia'] != 'ERRO') &
            (self.df['conta'] != 'ERRO') &
            (self.df['banco'].notna()) &
            (self.df['banco'] != 'null') &
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
        """Gera relatório de estatísticas"""
        logger.info("\n" + "="*80)
        logger.info("RELATÓRIO DE ORGANIZAÇÃO UAT")
        logger.info("="*80 + "\n")
        
        total_copiados = sum(len(v) for v in self.stats.values())
        
        print(f"📊 Total de processos no CSV: {len(self.df)}")
        print(f"📦 Total de PDFs copiados: {total_copiados}\n")
        
        print("📁 Distribuição por categoria:\n")
        
        categorias = {
            '1_anomalia_formato': 'Anomalia de Formato (ALTA)',
            '2_cessao_credito': 'Cessão de Crédito (MÉDIA)',
            '3_herdeiros_nao_rejeitados': 'Herdeiros Não Rejeitados (MÉDIA)',
            '4_preferencial': 'Preferencial (BAIXA)',
            '5_rejeitados': 'Rejeitados (ALTA)',
            '6_valores_altos': 'Valores Altos > R$ 500k (SUGESTÃO)',
            '7_dados_bancarios_incompletos': 'Dados Bancários Incompletos (SUGESTÃO)',
            '8_multiplos_credores': 'Múltiplos Credores (SUGESTÃO)',
            '9_sem_juros_moratorios': 'Sem Juros Moratórios (SUGESTÃO)',
            '10_amostra_baseline': 'Amostra Baseline (SUGESTÃO)',
            '11_processos_ok_100': 'Processos OK 100% (BASELINE)'
        }
        
        for pasta, descricao in categorias.items():
            count = len(self.stats[pasta])
            print(f"  {pasta:35} → {count:3} PDFs - {descricao}")
        
        print("\n" + "="*80)
        print(f"✅ Organização concluída! PDFs em: {self.output_dir}")
        print("="*80 + "\n")
    
    def gerar_readme(self):
        """Gera README.md com documentação do UAT"""
        readme_path = self.output_dir / 'README_UAT.md'
        
        content = f"""# 📋 UAT - User Acceptance Testing

**Data de Criação:** 14/11/2025  
**Versão:** v2.5.1  
**Total de Processos:** {len(self.df)}  
**Total de PDFs para Validação:** {sum(len(v) for v in self.stats.values())}

---

## 🎯 Objetivo

Esta estrutura organiza PDFs de Ofícios Requisitórios em categorias específicas para facilitar o **User Acceptance Testing (UAT)** e validação de qualidade da extração de dados.

---

## 📁 Estrutura de Pastas

### **1. Anomalia de Formato** (PRIORIDADE ALTA)
**Pasta:** `1_anomalia_formato/`  
**Quantidade:** {len(self.stats['1_anomalia_formato'])} PDFs  
**Descrição:** PDFs com formato antigo (7xxxxxx) ou estrutura diferente do padrão atual.  
**Ação:** Validar se dados foram extraídos corretamente apesar da estrutura diferente.

### **2. Cessão de Crédito** (PRIORIDADE MÉDIA)
**Pasta:** `2_cessao_credito/`  
**Quantidade:** {len(self.stats['2_cessao_credito'])} PDFs  
**Descrição:** Processos onde o crédito foi cedido a terceiros.  
**Ação:** Validar dados bancários do cessionário e informações de cessão.

### **3. Herdeiros Não Rejeitados** (PRIORIDADE MÉDIA)
**Pasta:** `3_herdeiros_nao_rejeitados/`  
**Quantidade:** {len(self.stats['3_herdeiros_nao_rejeitados'])} PDFs  
**Descrição:** Processos com habilitação de herdeiros aprovados.  
**Ação:** Validar múltiplos credores e distribuição de valores.

### **4. Preferencial** (PRIORIDADE BAIXA)
**Pasta:** `4_preferencial/`  
**Quantidade:** {len(self.stats['4_preferencial'])} PDFs  
**Descrição:** Processos com preferência (idoso ≥60 anos, doença grave, PCD).  
**Ação:** Validar marcadores de preferência e dados do credor.

### **5. Rejeitados** (PRIORIDADE ALTA)
**Pasta:** `5_rejeitados/`  
**Quantidade:** {len(self.stats['5_rejeitados'])} PDFs  
**Descrição:** Processos rejeitados pelo DEPRE.  
**Ação:** Analisar motivo da rejeição e validar se dados foram extraídos corretamente.

### **6. Valores Altos** (SUGESTÃO)
**Pasta:** `6_valores_altos/`  
**Quantidade:** {len(self.stats['6_valores_altos'])} PDFs  
**Descrição:** Processos com valor total requisitado > R$ 500.000.  
**Ação:** Validação extra devido ao alto valor financeiro.

### **7. Dados Bancários Incompletos** (SUGESTÃO)
**Pasta:** `7_dados_bancarios_incompletos/`  
**Quantidade:** {len(self.stats['7_dados_bancarios_incompletos'])} PDFs  
**Descrição:** Processos com banco, agência ou conta marcados como "ERRO" ou vazios.  
**Ação:** Validar se dados bancários estão realmente ausentes no PDF ou se houve erro de extração.

### **8. Múltiplos Credores** (SUGESTÃO)
**Pasta:** `8_multiplos_credores/`  
**Quantidade:** {len(self.stats['8_multiplos_credores'])} PDFs  
**Descrição:** Processos onde credor_nome ≠ requerente_caps (exceto cessão de crédito).  
**Ação:** Validar se há múltiplos credores ou erro de extração.

### **9. Sem Juros Moratórios** (SUGESTÃO)
**Pasta:** `9_sem_juros_moratorios/`  
**Quantidade:** {len(self.stats['9_sem_juros_moratorios'])} PDFs (limitado a 10)  
**Descrição:** Processos sem juros moratórios ou com valor zero.  
**Ação:** Validar se realmente não há juros ou se houve erro de extração.

### **10. Amostra Baseline** (SUGESTÃO)
**Pasta:** `10_amostra_baseline/`  
**Quantidade:** {len(self.stats['10_amostra_baseline'])} PDFs  
**Descrição:** Amostra aleatória de processos "normais" (10% dos não categorizados).  
**Ação:** Validação de qualidade geral da extração.

### **11. Processos OK 100%** (BASELINE)
**Pasta:** `11_processos_ok_100/`  
**Quantidade:** {len(self.stats['11_processos_ok_100'])} PDFs  
**Descrição:** Processos sem problemas (não rejeitados, sem anomalia, dados bancários completos).  
**Ação:** Validação de qualidade baseline - estes devem estar 100% corretos.

---

## 📊 Estatísticas

| Categoria | Quantidade | Prioridade |
|-----------|------------|------------|
| Anomalia de Formato | {len(self.stats['1_anomalia_formato'])} | ALTA |
| Cessão de Crédito | {len(self.stats['2_cessao_credito'])} | MÉDIA |
| Herdeiros Não Rejeitados | {len(self.stats['3_herdeiros_nao_rejeitados'])} | MÉDIA |
| Preferencial | {len(self.stats['4_preferencial'])} | BAIXA |
| Rejeitados | {len(self.stats['5_rejeitados'])} | ALTA |
| Valores Altos | {len(self.stats['6_valores_altos'])} | SUGESTÃO |
| Dados Bancários Incompletos | {len(self.stats['7_dados_bancarios_incompletos'])} | SUGESTÃO |
| Múltiplos Credores | {len(self.stats['8_multiplos_credores'])} | SUGESTÃO |
| Sem Juros Moratórios | {len(self.stats['9_sem_juros_moratorios'])} | SUGESTÃO |
| Amostra Baseline | {len(self.stats['10_amostra_baseline'])} | SUGESTÃO |
| Processos OK 100% | {len(self.stats['11_processos_ok_100'])} | BASELINE |
| **TOTAL** | **{sum(len(v) for v in self.stats.values())}** | - |

---

## ✅ Checklist de Validação

Para cada PDF, validar:

- [ ] **Dados do Requerente:** Nome em MAIÚSCULAS, CPF correto
- [ ] **Processo:** Número CNJ no formato correto
- [ ] **Valores Financeiros:** Principal, juros, total requisitado
- [ ] **Dados Bancários:** Banco (3 dígitos), agência, conta, tipo
- [ ] **Preferências:** Idoso, doença grave, PCD (se aplicável)
- [ ] **Datas:** Ajuizamento, trânsito julgado, base atualização
- [ ] **Advogado:** Nome e OAB (se presente)
- [ ] **Observações:** Motivo rejeição, anomalias

---

## 🔧 Como Usar

1. **Priorize as pastas ALTA:**
   - `1_anomalia_formato/`
   - `5_rejeitados/`

2. **Depois valide MÉDIA:**
   - `2_cessao_credito/`
   - `3_herdeiros_nao_rejeitados/`

3. **Por último BAIXA e SUGESTÕES:**
   - `4_preferencial/`
   - `6_valores_altos/`
   - `7_dados_bancarios_incompletos/`
   - `8_multiplos_credores/`
   - `9_sem_juros_moratorios/`
   - `10_amostra_baseline/`

4. **Para cada PDF:**
   - Abra o PDF original
   - Compare com dados extraídos no CSV
   - Anote discrepâncias em planilha de validação
   - Marque como ✅ (OK) ou ❌ (Erro)

---

## 📝 Relatório de Validação

Criar planilha com colunas:

| CPF | Processo | Categoria | Status | Observações |
|-----|----------|-----------|--------|-------------|
| ... | ... | ... | ✅/❌ | ... |

---

## 🚀 Próximos Passos

Após UAT:
1. Consolidar erros encontrados
2. Ajustar prompts LLM se necessário
3. Reprocessar PDFs com erros
4. Atualizar banco PostgreSQL
5. Deploy v2.6.0

---

**Gerado automaticamente por:** `organizar_uat.py`  
**Data:** 14/11/2025  
**Versão:** v2.5.1
"""
        
        readme_path.write_text(content, encoding='utf-8')
        logger.info(f"✓ README gerado: {readme_path}")


def main():
    """Função principal"""
    
    # Configurações (caminhos relativos ao root do projeto)
    CSV_PATH = "../tests/2025-11-14T18-08_export.csv"
    DATA_DIR = "../data/consultas"
    OUTPUT_DIR = "."  # Já estamos dentro de 4_UAT_refinamento
    
    # Criar organizador
    organizador = OrganizadorUAT(
        csv_path=CSV_PATH,
        data_dir=DATA_DIR,
        output_dir=OUTPUT_DIR
    )
    
    # Executar
    organizador.criar_estrutura_pastas()
    organizador.aplicar_regras()
    organizador.gerar_relatorio()
    organizador.gerar_readme()
    
    logger.info("\n✅ Processo concluído com sucesso!")


if __name__ == "__main__":
    main()
