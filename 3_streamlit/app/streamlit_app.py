#!/usr/bin/env python3
"""
Interface Streamlit - Consulta de Ofícios Requisitórios TJSP
Permite filtrar, visualizar e exportar dados do PostgreSQL
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import psycopg2
import base64

# Carregar variáveis de ambiente
env_path = Path(__file__).parent.parent / ".env"
print(f"🔍 DEBUG: Looking for .env at: {env_path.absolute()}")
print(f"🔍 DEBUG: .env exists: {env_path.exists()}")

# Force load with override=True to ensure env vars are set
load_dotenv(env_path, override=True)

print(f"🔍 DEBUG: DB_HOST = {os.getenv('DB_HOST')}")
print(f"🔍 DEBUG: DB_PORT = {os.getenv('DB_PORT')}")
print(f"🔍 DEBUG: DB_NAME = {os.getenv('DB_NAME')}")
print(f"🔍 DEBUG: DB_USER = {os.getenv('DB_USER')}")

# Configuração da página
st.set_page_config(
    page_title="Ofícios Requisitórios TJSP",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0 0.5rem 0;
        margin-top: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stDataFrame {
        font-size: 0.9rem;
    }
    /* Espaçamento superior para não cortar o título */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_todos_dados():
    """
    Carrega TODOS os dados do PostgreSQL em memória (cached)
    Executado apenas uma vez na inicialização
    """
    with st.spinner("🔄 Aguarde, organizando e indexando os dados..."):
        try:
            # Explicit connection parameters (fallback to hardcoded if env not loaded)
            db_host = os.getenv("DB_HOST", "72.60.62.124")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "n8n")
            db_user = os.getenv("DB_USER", "admin")
            db_password = os.getenv("DB_PASSWORD", "BetaAgent2024SecureDB")
            
            print(f"🔌 Connecting to: {db_host}:{db_port}/{db_name} as {db_user}")
            
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            
            # Query para buscar TODOS os dados de uma vez
            query = """
                SELECT 
                    id, cpf, numero_processo_cnj, processo_origem, requerente_caps,
                    numero_ordem, vara, processo_execucao, processo_conhecimento,
                    data_ajuizamento, data_transito_julgado, data_base_atualizacao, data_nascimento,
                    advogado_nome, advogado_oab, credor_nome, credor_cpf_cnpj, devedor_ente,
                    banco, agencia, conta, conta_tipo, tipo_levantamento, 
                    dados_bancarios_advogado, cpf_titular_conta,
                    valor_principal_liquido, valor_principal_bruto, juros_moratorios,
                    valor_total_requisitado, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
                    valor_compensado, contribuicao_social, salario_pericial, 
                    assist_tecnico, custas, despesas, multas,
                    idoso, doenca_grave, pcd,
                    preferencial, habilitacao_herdeiros, cessao_credito,
                    rejeitado, motivo_rejeicao, observacoes, anomalia, descricao_anomalia,
                    process_diagnostico, caminho_pdf, timestamp_ingestao
                FROM esaj_detalhe_processos
                ORDER BY timestamp_ingestao DESC;
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Converter tipos para otimizar memória (sem warnings)
            if 'rejeitado' in df.columns:
                df['rejeitado'] = df['rejeitado'].astype('boolean')
            if 'idoso' in df.columns:
                df['idoso'] = df['idoso'].astype('boolean')
            if 'doenca_grave' in df.columns:
                df['doenca_grave'] = df['doenca_grave'].astype('boolean')
            if 'pcd' in df.columns:
                df['pcd'] = df['pcd'].astype('boolean')
            if 'preferencial' in df.columns:
                df['preferencial'] = df['preferencial'].astype('boolean')
            if 'habilitacao_herdeiros' in df.columns:
                df['habilitacao_herdeiros'] = df['habilitacao_herdeiros'].astype('boolean')
            if 'cessao_credito' in df.columns:
                df['cessao_credito'] = df['cessao_credito'].astype('boolean')
            if 'process_diagnostico' in df.columns:
                df['process_diagnostico'] = df['process_diagnostico'].astype('boolean')
            
            return df
            
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {e}")
            return pd.DataFrame()


def filtrar_dataframe(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """
    Aplica filtros no DataFrame em memória (RÁPIDO!)
    SEM cache para permitir atualização instantânea da UI
    """
    df_filtrado = df.copy()
    
    # Filtro: CPF
    if filtros.get('cpf'):
        df_filtrado = df_filtrado[df_filtrado['cpf'] == filtros['cpf']]
    
    # Filtro: Processo
    if filtros.get('processo'):
        df_filtrado = df_filtrado[
            df_filtrado['numero_processo_cnj'].str.contains(filtros['processo'], case=False, na=False)
        ]
    
    # Filtro: Vara
    if filtros.get('vara') and filtros['vara'] != "Todas":
        df_filtrado = df_filtrado[df_filtrado['vara'] == filtros['vara']]
    
    # Filtro: Status
    if filtros.get('rejeitado') is not None:
        df_filtrado = df_filtrado[df_filtrado['rejeitado'] == filtros['rejeitado']]
    
    # Filtro: Preferências (com suporte a None = "Todos")
    if filtros.get('idoso') is not None:
        df_filtrado = df_filtrado[df_filtrado['idoso'] == filtros['idoso']]
    
    if filtros.get('doenca_grave') is not None:
        df_filtrado = df_filtrado[df_filtrado['doenca_grave'] == filtros['doenca_grave']]
    
    if filtros.get('pcd') is not None:
        df_filtrado = df_filtrado[df_filtrado['pcd'] == filtros['pcd']]
    
    # Filtro: Termos Jurídicos (v2.4.0)
    if filtros.get('preferencial') is not None:
        df_filtrado = df_filtrado[df_filtrado['preferencial'] == filtros['preferencial']]
    
    if filtros.get('habilitacao_herdeiros') is not None:
        df_filtrado = df_filtrado[df_filtrado['habilitacao_herdeiros'] == filtros['habilitacao_herdeiros']]
    
    if filtros.get('cessao_credito') is not None:
        df_filtrado = df_filtrado[df_filtrado['cessao_credito'] == filtros['cessao_credito']]
    
    # Filtro: Valores
    if filtros.get('valor_min', 0) > 0:
        df_filtrado = df_filtrado[df_filtrado['valor_total_requisitado'] >= filtros['valor_min']]
    
    if filtros.get('valor_max', 1000000) < 1000000:
        df_filtrado = df_filtrado[df_filtrado['valor_total_requisitado'] <= filtros['valor_max']]
    
    # Filtro: Datas
    if filtros.get('data_inicio'):
        df_filtrado = df_filtrado[df_filtrado['data_ajuizamento'] >= pd.to_datetime(filtros['data_inicio'])]
    
    if filtros.get('data_fim'):
        df_filtrado = df_filtrado[df_filtrado['data_ajuizamento'] <= pd.to_datetime(filtros['data_fim'])]
    
    return df_filtrado


def get_pdf_path(cpf: str, numero_processo: str) -> Path:
    """Retorna path do PDF"""
    pdf_dir = Path(os.getenv("PDF_DIR", "../data/consultas"))
    pdf_dir = Path(__file__).parent.parent / pdf_dir
    return pdf_dir / cpf / f"{numero_processo}.pdf"


def display_pdf_info(pdf_path: Path):
    """
    Exibe informações sobre o PDF (apenas download, sem visualização inline)
    """
    if not pdf_path.exists():
        st.warning(f"PDF não encontrado: {pdf_path}")
        return
    
    # Verificar tamanho do arquivo
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    
    # Mensagem informativa
    st.success(f"✅ PDF disponível para download ({file_size_mb:.1f} MB)")
    st.info("💡 **Dica:** Clique no botão 'Download PDF' acima para abrir o arquivo no seu navegador ou aplicativo de PDF preferido.")


def main():
    """Função principal"""
    
    # ========================================================================
    # PRIORIDADE 1: SIDEBAR COM RADIO BUTTONS (RENDERIZAÇÃO RÁPIDA!)
    # ========================================================================
    st.sidebar.header("🔍 Filtros")
    
    # Inicializar session_state
    if 'cpf_filter' not in st.session_state:
        st.session_state.cpf_filter = ""
    if 'processo_filter' not in st.session_state:
        st.session_state.processo_filter = ""
    
    # Dicionário de filtros
    filtros = {}
    
    # Filtro: CPF (renderiza instantaneamente)
    st.session_state.cpf_filter = st.sidebar.text_input(
        "CPF (apenas números)", 
        value=st.session_state.cpf_filter,
        key="txt_cpf"
    )
    filtros['cpf'] = st.session_state.cpf_filter
    
    # Filtro: Processo (renderiza instantaneamente)
    st.session_state.processo_filter = st.sidebar.text_input(
        "Número do Processo", 
        value=st.session_state.processo_filter,
        key="txt_processo"
    )
    filtros['processo'] = st.session_state.processo_filter
    
    # Filtro: Preferências com SELECTBOX (renderiza instantaneamente + compacto!)
    st.sidebar.subheader("Preferências")
    
    # Selectbox para Idoso
    idoso_option = st.sidebar.selectbox(
        "👴 Idoso",
        ["Todos", "Apenas Idosos", "Não Idosos"],
        index=0,
        key="select_idoso"
    )
    if idoso_option == "Apenas Idosos":
        filtros['idoso'] = True
    elif idoso_option == "Não Idosos":
        filtros['idoso'] = False
    else:
        filtros['idoso'] = None
    
    # Selectbox para Doença Grave
    doenca_option = st.sidebar.selectbox(
        "🏥 Doença Grave",
        ["Todos", "Apenas com Doença Grave", "Sem Doença Grave"],
        index=0,
        key="select_doenca"
    )
    if doenca_option == "Apenas com Doença Grave":
        filtros['doenca_grave'] = True
    elif doenca_option == "Sem Doença Grave":
        filtros['doenca_grave'] = False
    else:
        filtros['doenca_grave'] = None
    
    # Selectbox para PCD
    pcd_option = st.sidebar.selectbox(
        "♿ PCD",
        ["Todos", "Apenas PCD", "Não PCD"],
        index=0,
        key="select_pcd"
    )
    if pcd_option == "Apenas PCD":
        filtros['pcd'] = True
    elif pcd_option == "Não PCD":
        filtros['pcd'] = False
    else:
        filtros['pcd'] = None
    
    # ========================================================================
    # TERMOS JURÍDICOS (v2.4.0)
    # ========================================================================
    st.sidebar.subheader("📜 Termos Jurídicos")
    
    # Selectbox para Preferencial
    preferencial_option = st.sidebar.selectbox(
        "⭐ Preferência",
        ["Todos", "Com Preferência", "Sem Preferência"],
        index=0,
        key="select_preferencial"
    )
    if preferencial_option == "Com Preferência":
        filtros['preferencial'] = True
    elif preferencial_option == "Sem Preferência":
        filtros['preferencial'] = False
    else:
        filtros['preferencial'] = None
    
    # Selectbox para Habilitação de Herdeiros
    habilitacao_option = st.sidebar.selectbox(
        "👨‍👩‍👧‍👦 Habilitação de Herdeiros",
        ["Todos", "Com Habilitação", "Sem Habilitação"],
        index=0,
        key="select_habilitacao"
    )
    if habilitacao_option == "Com Habilitação":
        filtros['habilitacao_herdeiros'] = True
    elif habilitacao_option == "Sem Habilitação":
        filtros['habilitacao_herdeiros'] = False
    else:
        filtros['habilitacao_herdeiros'] = None
    
    # Selectbox para Cessão de Crédito
    cessao_option = st.sidebar.selectbox(
        "📄 Cessão de Crédito",
        ["Todos", "Com Cessão", "Sem Cessão"],
        index=0,
        key="select_cessao"
    )
    if cessao_option == "Com Cessão":
        filtros['cessao_credito'] = True
    elif cessao_option == "Sem Cessão":
        filtros['cessao_credito'] = False
    else:
        filtros['cessao_credito'] = None
    
    # ========================================================================
    # CARREGAR DADOS (após renderizar controles rápidos)
    # ========================================================================
    
    # Carregar dados em memória (cached - executado apenas 1x)
    df_completo = carregar_todos_dados()
    
    if df_completo.empty:
        st.error("❌ Nenhum dado disponível no banco de dados.")
        return
    
    # Filtro: Vara (precisa dos dados)
    varas_unicas = sorted(df_completo['vara'].dropna().unique().tolist())
    varas_options = ["Todas"] + varas_unicas
    filtros['vara'] = st.sidebar.selectbox("Vara", varas_options)
    
    # Filtro: Status
    st.sidebar.subheader("Status")
    status_option = st.sidebar.radio(
        "Selecione o status:",
        ["Todos", "Apenas Rejeitados", "Apenas Aprovados"],
        index=0,
        key="radio_status"
    )
    
    if status_option == "Apenas Rejeitados":
        filtros['rejeitado'] = True
    elif status_option == "Apenas Aprovados":
        filtros['rejeitado'] = False
    else:
        filtros['rejeitado'] = None
    
    # Filtro: Valores
    st.sidebar.subheader("Valores")
    filtros['valor_min'] = st.sidebar.number_input("Valor Mínimo (R$)", min_value=0.0, value=0.0, step=1000.0)
    filtros['valor_max'] = st.sidebar.number_input("Valor Máximo (R$)", min_value=0.0, value=1000000.0, step=1000.0)
    
    # Filtro: Datas
    st.sidebar.subheader("Datas")
    filtros['data_inicio'] = st.sidebar.date_input("Data Ajuizamento - Início", value=None)
    filtros['data_fim'] = st.sidebar.date_input("Data Ajuizamento - Fim", value=None)
    
    # ========================================================================
    # CONTEÚDO PRINCIPAL
    # ========================================================================
    
    # Header
    st.markdown('<div class="main-header">⚖️ Ofícios Requisitórios TJSP</div>', unsafe_allow_html=True)
    
    # Nota: Removida mensagem de info para economizar espaço vertical
    # {len(df_completo)} processos carregados em cache, filtros processados em memória
    
    st.markdown("---")
    
    # Aplicar filtros no DataFrame em memória (INSTANTÂNEO!)
    df = filtrar_dataframe(df_completo, filtros)
    
    # Estatísticas (calculadas em memória)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total de Processos", len(df))
    
    with col2:
        rejeitados = df['rejeitado'].sum() if 'rejeitado' in df.columns else 0
        st.metric("❌ Rejeitados", int(rejeitados))
    
    with col3:
        valor_total = df['valor_total_requisitado'].sum() if 'valor_total_requisitado' in df.columns else 0
        st.metric("💰 Valor Total", f"R$ {valor_total:,.2f}")
    
    with col4:
        idosos = df['idoso'].sum() if 'idoso' in df.columns else 0
        st.metric("👴 Idosos", int(idosos))
    
    # Estatísticas de Termos Jurídicos (v2.4.0)
    st.markdown("### 📜 Termos Jurídicos Detectados")
    col5, col6, col7 = st.columns(3)
    
    with col5:
        preferencial_count = df['preferencial'].sum() if 'preferencial' in df.columns else 0
        preferencial_pct = (preferencial_count / len(df) * 100) if len(df) > 0 else 0
        st.metric("⭐ Preferência", f"{int(preferencial_count)} ({preferencial_pct:.1f}%)")
    
    with col6:
        habilitacao_count = df['habilitacao_herdeiros'].sum() if 'habilitacao_herdeiros' in df.columns else 0
        habilitacao_pct = (habilitacao_count / len(df) * 100) if len(df) > 0 else 0
        st.metric("👨‍👩‍👧‍👦 Habilitação Herdeiros", f"{int(habilitacao_count)} ({habilitacao_pct:.1f}%)")
    
    with col7:
        cessao_count = df['cessao_credito'].sum() if 'cessao_credito' in df.columns else 0
        cessao_pct = (cessao_count / len(df) * 100) if len(df) > 0 else 0
        st.metric("📄 Cessão de Crédito", f"{int(cessao_count)} ({cessao_pct:.1f}%)")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Dados", "📊 Gráficos", "📄 Visualizar PDF"])
    
    with tab1:
        st.subheader("Resultados da Consulta")
        
        if not df.empty:
            # Criar cópia do DataFrame para exibição
            df_display = df.copy()
            
            # Formatar valores monetários
            if 'valor_total_requisitado' in df_display.columns:
                df_display['valor_total_requisitado'] = df_display['valor_total_requisitado'].apply(
                    lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
                )
            if 'valor_principal_liquido' in df_display.columns:
                df_display['valor_principal_liquido'] = df_display['valor_principal_liquido'].apply(
                    lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
                )
            if 'valor_principal_bruto' in df_display.columns:
                df_display['valor_principal_bruto'] = df_display['valor_principal_bruto'].apply(
                    lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
                )
            
            # Exibir TODAS as colunas
            st.dataframe(
                df_display,
                width='stretch',
                height=400
            )
            
            # Botão de download CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"oficios_tjsp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            
            # Seção de visualização rápida de PDF
            st.subheader("🔍 Visualização Rápida de PDF")
            st.info("💡 Selecione um processo na lista abaixo para visualizar o PDF")
            
            # Criar lista de processos com informações resumidas
            processo_options = []
            for idx, row in df.iterrows():
                requerente = row['requerente_caps'][:40] if len(row['requerente_caps']) > 40 else row['requerente_caps']
                rejeitado = row.get('rejeitado', False)
                status = "❌ Rejeitado" if pd.notna(rejeitado) and rejeitado else "✅ Aprovado"
                processo_options.append(f"{row['numero_processo_cnj']} | {requerente} | {status}")
            
            # Selectbox para escolher processo
            selected_option = st.selectbox(
                "Escolha um processo para visualizar:",
                options=range(len(processo_options)),
                format_func=lambda x: processo_options[x],
                key="pdf_viewer_tab1"
            )
            
            if selected_option is not None:
                selected_row = df.iloc[selected_option]
                cpf = selected_row['cpf']
                numero_processo = selected_row['numero_processo_cnj']
                
                # Informações do processo
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**CPF:** {cpf}")
                with col2:
                    st.write(f"**Processo:** {numero_processo}")
                with col3:
                    valor = selected_row.get('valor_total_requisitado', '-')
                    st.write(f"**Valor:** {valor}")
                
                # Botão de download e visualização
                pdf_path = get_pdf_path(cpf, numero_processo)
                
                if pdf_path.exists():
                    # Verificar tamanho do arquivo
                    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                    
                    st.markdown("---")
                    
                    # Botão de download destacado
                    col1, col2, col3 = st.columns([2, 2, 2])
                    with col2:
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Download PDF ({file_size_mb:.1f} MB)",
                                data=f,
                                file_name=f"{numero_processo}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary",
                                key=f"download_tab1_{numero_processo}"
                            )
                    
                    # Informações do PDF
                    display_pdf_info(pdf_path)
                else:
                    st.error(f"❌ PDF não encontrado: {pdf_path}")
        else:
            st.info("Nenhum resultado encontrado com os filtros aplicados.")
    
    with tab2:
        st.subheader("Visualizações")
        
        if not df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Gráfico: Distribuição por Status
                status_counts = df['rejeitado'].value_counts()
                fig1 = px.pie(
                    values=status_counts.values,
                    names=['Aprovado' if not x else 'Rejeitado' for x in status_counts.index],
                    title="Distribuição por Status"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Gráfico: Top 5 Varas
                if 'vara' in df.columns:
                    vara_counts = df['vara'].value_counts().head(5)
                    fig2 = px.bar(
                        x=vara_counts.values,
                        y=vara_counts.index,
                        orientation='h',
                        title="Top 5 Varas",
                        labels={'x': 'Quantidade', 'y': 'Vara'}
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Gráfico: Termos Jurídicos (v2.4.0)
            st.markdown("### 📜 Distribuição de Termos Jurídicos")
            
            # Preparar dados para o gráfico
            termos_data = {
                'Termo': ['Preferência', 'Habilitação de Herdeiros', 'Cessão de Crédito'],
                'Quantidade': [
                    int(df['preferencial'].sum()) if 'preferencial' in df.columns else 0,
                    int(df['habilitacao_herdeiros'].sum()) if 'habilitacao_herdeiros' in df.columns else 0,
                    int(df['cessao_credito'].sum()) if 'cessao_credito' in df.columns else 0
                ]
            }
            
            termos_df = pd.DataFrame(termos_data)
            
            # Gráfico de barras horizontal
            fig3 = px.bar(
                termos_df,
                x='Quantidade',
                y='Termo',
                orientation='h',
                title="Termos Jurídicos Detectados",
                labels={'Quantidade': 'Número de Processos', 'Termo': 'Termo Jurídico'},
                color='Quantidade',
                color_continuous_scale='Blues'
            )
            fig3.update_layout(showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
            
        else:
            st.info("Nenhum dado para visualizar.")
    
    with tab3:
        st.subheader("Visualizar PDF")
        
        if not df.empty:
            # Seletor de processo
            processo_options = df.apply(
                lambda row: f"{row['cpf']} - {row['numero_processo_cnj']} - {row['requerente_caps'][:30]}",
                axis=1
            ).tolist()
            
            selected_idx = st.selectbox("Selecione um processo:", range(len(processo_options)), format_func=lambda x: processo_options[x])
            
            if selected_idx is not None:
                selected_row = df.iloc[selected_idx]
                cpf = selected_row['cpf']
                numero_processo = selected_row['numero_processo_cnj']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Requerente:** {selected_row['requerente_caps'][:40]}")
                with col2:
                    st.write(f"**CPF:** {cpf}")
                with col3:
                    st.write(f"**Processo:** {numero_processo}")
                
                pdf_path = get_pdf_path(cpf, numero_processo)
                
                if pdf_path.exists():
                    # Verificar tamanho do arquivo
                    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
                    
                    st.markdown("---")
                    
                    # Botão de download destacado e centralizado
                    col1, col2, col3 = st.columns([2, 2, 2])
                    with col2:
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label=f"📥 Download PDF ({file_size_mb:.1f} MB)",
                                data=f,
                                file_name=f"{numero_processo}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary",
                                key=f"download_tab3_{numero_processo}"
                            )
                    
                    # Informações do PDF
                    display_pdf_info(pdf_path)
                else:
                    st.error(f"❌ PDF não encontrado: {pdf_path}")
        else:
            st.info("Nenhum processo para visualizar.")


if __name__ == "__main__":
    main()
