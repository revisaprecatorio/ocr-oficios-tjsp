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
load_dotenv(env_path)

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
        padding: 1rem 0;
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
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            
            # Query para buscar TODOS os dados de uma vez
            query = """
                SELECT 
                    id, cpf, numero_processo_cnj, processo_origem, requerente_caps,
                    numero_ordem, vara, processo_execucao, processo_conhecimento,
                    data_ajuizamento, data_transito_julgado, data_base_atualizacao,
                    advogado_nome, advogado_oab, credor_nome, credor_cpf_cnpj, devedor_ente,
                    banco, agencia, conta, conta_tipo,
                    valor_principal_liquido, valor_principal_bruto, juros_moratorios,
                    valor_total_requisitado, contrib_previdenciaria_iprem, contrib_previdenciaria_hspm,
                    idoso, doenca_grave, pcd,
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
    
    # Filtro: Preferências
    if filtros.get('idoso'):
        df_filtrado = df_filtrado[df_filtrado['idoso'] == True]
    
    if filtros.get('doenca_grave'):
        df_filtrado = df_filtrado[df_filtrado['doenca_grave'] == True]
    
    if filtros.get('pcd'):
        df_filtrado = df_filtrado[df_filtrado['pcd'] == True]
    
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


def display_pdf(pdf_path: Path):
    """Exibe PDF inline"""
    if not pdf_path.exists():
        st.warning(f"PDF não encontrado: {pdf_path}")
        return
    
    with open(pdf_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def main():
    """Função principal"""
    
    # Inicializar session_state para filtros (persistente entre reruns)
    if 'idoso' not in st.session_state:
        st.session_state.idoso = False
    if 'doenca_grave' not in st.session_state:
        st.session_state.doenca_grave = False
    if 'pcd' not in st.session_state:
        st.session_state.pcd = False
    if 'cpf_filter' not in st.session_state:
        st.session_state.cpf_filter = ""
    if 'processo_filter' not in st.session_state:
        st.session_state.processo_filter = ""
    
    # Header
    st.markdown('<div class="main-header">⚖️ Ofícios Requisitórios TJSP</div>', unsafe_allow_html=True)
    
    # Carregar dados em memória (cached - executado apenas 1x)
    df_completo = carregar_todos_dados()
    
    if df_completo.empty:
        st.error("❌ Nenhum dado disponível no banco de dados.")
        return
    
    # Mostrar info de cache
    st.info(f"✅ {len(df_completo)} processos carregados em memória | Filtros são instantâneos!")
    st.markdown("---")
    
    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros")
    
    # Dicionário de filtros
    filtros = {}
    
    # Filtro: CPF (com session_state)
    st.session_state.cpf_filter = st.sidebar.text_input(
        "CPF (apenas números)", 
        value=st.session_state.cpf_filter,
        key="txt_cpf"
    )
    filtros['cpf'] = st.session_state.cpf_filter
    
    # Filtro: Processo (com session_state)
    st.session_state.processo_filter = st.sidebar.text_input(
        "Número do Processo", 
        value=st.session_state.processo_filter,
        key="txt_processo"
    )
    filtros['processo'] = st.session_state.processo_filter
    
    # Filtro: Vara (extrair opções do DataFrame em memória)
    varas_unicas = sorted(df_completo['vara'].dropna().unique().tolist())
    varas_options = ["Todas"] + varas_unicas
    filtros['vara'] = st.sidebar.selectbox("Vara", varas_options)
    
    # Filtro: Status
    st.sidebar.subheader("Status")
    status_option = st.sidebar.radio(
        "Selecione o status:",
        ["Todos", "Apenas Rejeitados", "Apenas Aprovados"],
        index=0
    )
    
    if status_option == "Apenas Rejeitados":
        filtros['rejeitado'] = True
    elif status_option == "Apenas Aprovados":
        filtros['rejeitado'] = False
    else:
        filtros['rejeitado'] = None
    
    # Filtro: Preferências (usando session_state diretamente para feedback instantâneo)
    st.sidebar.subheader("Preferências")
    
    # Checkboxes com valor direto do session_state (INSTANTÂNEO!)
    st.session_state.idoso = st.sidebar.checkbox(
        "👴 Idoso", 
        value=st.session_state.idoso,
        key="cb_idoso"
    )
    
    st.session_state.doenca_grave = st.sidebar.checkbox(
        "🏥 Doença Grave", 
        value=st.session_state.doenca_grave,
        key="cb_doenca"
    )
    
    st.session_state.pcd = st.sidebar.checkbox(
        "♿ PCD", 
        value=st.session_state.pcd,
        key="cb_pcd"
    )
    
    # Usar valores do session_state
    filtros['idoso'] = st.session_state.idoso
    filtros['doenca_grave'] = st.session_state.doenca_grave
    filtros['pcd'] = st.session_state.pcd
    
    # Filtro: Valores
    st.sidebar.subheader("Valores")
    filtros['valor_min'] = st.sidebar.number_input("Valor Mínimo (R$)", min_value=0.0, value=0.0, step=1000.0)
    filtros['valor_max'] = st.sidebar.number_input("Valor Máximo (R$)", min_value=0.0, value=1000000.0, step=1000.0)
    
    # Filtro: Datas
    st.sidebar.subheader("Datas")
    filtros['data_inicio'] = st.sidebar.date_input("Data Ajuizamento - Início", value=None)
    filtros['data_fim'] = st.sidebar.date_input("Data Ajuizamento - Fim", value=None)
    
    # Aplicar filtros no DataFrame em memória (INSTANTÂNEO!)
    # Sem cache - permite UI responsiva
    with st.spinner("🔄 Filtrando..."):
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
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Dados", "📊 Gráficos", "📄 Visualizar PDF"])
    
    with tab1:
        st.subheader("Resultados da Consulta")
        
        if not df.empty:
            # Formatar valores
            if 'valor_total_requisitado' in df.columns:
                df['valor_total_requisitado'] = df['valor_total_requisitado'].apply(
                    lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "-"
                )
            
            # Exibir tabela
            st.dataframe(
                df,
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
                
                st.write(f"**Requerente:** {selected_row['requerente_caps']}")
                st.write(f"**CPF:** {cpf}")
                st.write(f"**Processo:** {numero_processo}")
                
                pdf_path = get_pdf_path(cpf, numero_processo)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    if pdf_path.exists():
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📥 Download PDF",
                                data=f,
                                file_name=f"{numero_processo}.pdf",
                                mime="application/pdf"
                            )
                
                st.markdown("---")
                display_pdf(pdf_path)
        else:
            st.info("Nenhum processo para visualizar.")


if __name__ == "__main__":
    main()
