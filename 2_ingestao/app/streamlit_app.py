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


@st.cache_resource
def get_db_connection():
    """Cria conexão com PostgreSQL (cached)"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def executar_query(query: str, params=None) -> pd.DataFrame:
    """Executa query e retorna DataFrame"""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Erro ao executar query: {e}")
        return pd.DataFrame()


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
    
    # Header
    st.markdown('<div class="main-header">⚖️ Ofícios Requisitórios TJSP</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar - Filtros
    st.sidebar.header("🔍 Filtros")
    
    # Filtro: CPF
    cpf_filter = st.sidebar.text_input("CPF (apenas números)", "")
    
    # Filtro: Processo
    processo_filter = st.sidebar.text_input("Número do Processo", "")
    
    # Filtro: Vara
    varas_query = "SELECT DISTINCT vara FROM esaj_detalhe_processos WHERE vara IS NOT NULL ORDER BY vara;"
    varas_df = executar_query(varas_query)
    varas_options = ["Todas"] + varas_df['vara'].tolist() if not varas_df.empty else ["Todas"]
    vara_filter = st.sidebar.selectbox("Vara", varas_options)
    
    # Filtro: Status
    st.sidebar.subheader("Status")
    rejeitado_filter = st.sidebar.checkbox("Apenas Rejeitados", value=False)
    aprovado_filter = st.sidebar.checkbox("Apenas Aprovados", value=False)
    
    # Filtro: Preferências
    st.sidebar.subheader("Preferências")
    idoso_filter = st.sidebar.checkbox("Idoso", value=False)
    doenca_grave_filter = st.sidebar.checkbox("Doença Grave", value=False)
    pcd_filter = st.sidebar.checkbox("PCD", value=False)
    
    # Filtro: Valores
    st.sidebar.subheader("Valores")
    valor_min = st.sidebar.number_input("Valor Mínimo (R$)", min_value=0.0, value=0.0, step=1000.0)
    valor_max = st.sidebar.number_input("Valor Máximo (R$)", min_value=0.0, value=1000000.0, step=1000.0)
    
    # Filtro: Datas
    st.sidebar.subheader("Datas")
    data_inicio = st.sidebar.date_input("Data Ajuizamento - Início", value=None)
    data_fim = st.sidebar.date_input("Data Ajuizamento - Fim", value=None)
    
    # Construir query com filtros
    query = """
        SELECT 
            id, cpf, numero_processo_cnj, processo_origem, requerente_caps,
            vara, rejeitado, idoso, doenca_grave, pcd,
            valor_total_requisitado, data_ajuizamento,
            motivo_rejeicao, observacoes
        FROM esaj_detalhe_processos
        WHERE 1=1
    """
    params = {}
    
    if cpf_filter:
        query += " AND cpf = %(cpf)s"
        params['cpf'] = cpf_filter
    
    if processo_filter:
        query += " AND numero_processo_cnj LIKE %(processo)s"
        params['processo'] = f"%{processo_filter}%"
    
    if vara_filter != "Todas":
        query += " AND vara = %(vara)s"
        params['vara'] = vara_filter
    
    if rejeitado_filter:
        query += " AND rejeitado = true"
    
    if aprovado_filter:
        query += " AND (rejeitado = false OR rejeitado IS NULL)"
    
    if idoso_filter:
        query += " AND idoso = true"
    
    if doenca_grave_filter:
        query += " AND doenca_grave = true"
    
    if pcd_filter:
        query += " AND pcd = true"
    
    if valor_min > 0:
        query += " AND valor_total_requisitado >= %(valor_min)s"
        params['valor_min'] = valor_min
    
    if valor_max < 1000000:
        query += " AND valor_total_requisitado <= %(valor_max)s"
        params['valor_max'] = valor_max
    
    if data_inicio:
        query += " AND data_ajuizamento >= %(data_inicio)s"
        params['data_inicio'] = data_inicio
    
    if data_fim:
        query += " AND data_ajuizamento <= %(data_fim)s"
        params['data_fim'] = data_fim
    
    query += " ORDER BY timestamp_ingestao DESC;"
    
    # Executar query
    df = executar_query(query, params)
    
    # Estatísticas
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
                use_container_width=True,
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
