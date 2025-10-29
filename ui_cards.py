# ui_cards.py
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

# Importa os helpers (CSS, render e adaptadores)
from ui_cards_helpers import (
    build_records_from_df,
    fetch_matches_api_football,
    to_df,
    render_grid,
    CARD_CSS,
    # get_upcoming_fixtures,  # use se for mesclar fixtures da API-Football
)

def main():
    # NÃO chame st.set_page_config aqui (já é chamado no app.py)
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    # ===================== FONTES DE DADOS =====================
    records: List[Dict[str, Any]] = []

    # Pega do session_state (df_palpites) e adapta para cards
    if 'df_palpites' in st.session_state and isinstance(st.session_state.df_palpites, pd.DataFrame):
        records = build_records_from_df(st.session_state.df_palpites)

    # ⚙️ OPCIONAL: Mesclar jogos futuros via API-Football
    # fixtures = get_upcoming_fixtures(league_id=None, days=7)
    # records += fetch_matches_api_football(fixtures)

    df = to_df(records)

    # ===================== SIDEBAR =====================
    with st.sidebar:
        st.header("Filtros")
        if not df.empty:
            min_date, max_date = df["date"].min(), df["date"].max()
        else:
            from datetime import date
            today = date.today()
            min_date = max_date = today

        c1, c2 = st.columns(2)
        with c1:
            date_from = st.date_input("De", value=min_date)
        with c2:
            date_to = st.date_input("Até", value=max_date)

        leagues = sorted(df["league"].dropna().unique()) if not df.empty else []
        selected_leagues = st.multiselect("Competições", leagues, default=leagues)

        rounds = sorted([r for r in df["round"].dropna().unique()]) if not df.empty else []
        selected_round = st.selectbox("Rodada", ["Todas"] + [str(x) for x in rounds])

        status_opts = sorted(df["status"].dropna().unique()) if not df.empty else []
        selected_status = st.multiselect("Status", status_opts, default=status_opts)

        query = st.text_input("Buscar (time/mercado)")
        cols_grid = st.slider("# de colunas", 2, 4, 3)

    # ===================== FILTROS =====================
    if not df.empty:
        mask = (df["date"] >= date_from) & (df["date"] <= date_to)

        if selected_leagues:
            mask &= df["league"].isin(selected_leagues)
        if selected_round != "Todas":
            mask &= df["round"].astype(str) == str(selected_round)
        if selected_status:
            mask &= df["status"].isin(selected_status)
        if query:
            q = query.lower()
            mask &= df.apply(lambda r: q in str(r.to_dict()).lower(), axis=1)

        df_view = df[mask]
    else:
        df_view = df

    # ===================== CABEÇALHO =====================
    st.markdown("""
<h2 style="
    color:#00f5ff;
    text-shadow: 0 0 10px rgba(0,245,255,0.8), 0 0 25px rgba(255,45,149,0.4);
    font-weight:800;
    letter-spacing:0.5px;
    margin-top: -10px;
">
    ⚡ IA de Palpites em Tempo Real 
</h2>
""", unsafe_allow_html=True)
    #st.caption("Visual em cards integrando df_palpites (e opcionalmente fixtures da API-Football).")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Jogos listados", len(df_view))
    with c2:
        avg_conf = (df_view["confidence"].mean() * 100) if not df_view.empty and df_view["confidence"].notna().any() else 0
        st.metric("Confiança média", f"{avg_conf:.0f}%")
    with c3:
        st.metric("Competições", len(set(df_view["league"])) if not df_view.empty else 0)

    st.divider()

    # ===================== RENDERIZA CARDS =====================
    render_grid(df_view.reset_index(drop=True), cols=cols_grid)

    #with st.expander("Como integrar com sua API"):
        #st.markdown(
            #"""
            #1. O app lê `st.session_state.df_palpites`.
            #2. `build_records_from_df()` transforma o DF no formato dos cards.
            #3. Para adicionar fixtures futuros, use `fetch_matches_api_football()` após obter `get_upcoming_fixtures()`.
            #"""
        #)
