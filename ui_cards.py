# ui_cards.py – versão corrigida (com main() e filtros inline/sidebar)
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from ui_cards_helpers import (
    build_records_from_df,
    fetch_matches_api_football,
    to_df,
    render_grid,
    CARD_CSS,
    # get_upcoming_fixtures,  # use se quiser mesclar fixtures da API
)

# -------------------- Bloco dos filtros (inline OU sidebar) --------------------
def _filters_block(df: pd.DataFrame):
    if "filters_place" not in st.session_state:
        st.session_state["filters_place"] = "inline"  # "inline" | "sidebar"

    # Barra de controle: onde exibir
    top_left, top_right = st.columns([1, 1])
    with top_right:
        place = st.radio(
            "Exibir filtros em:",
            options=["inline", "sidebar"],
            index=0 if st.session_state["filters_place"] == "inline" else 1,
            horizontal=True,
            format_func=lambda x: "Aqui na página" if x == "inline" else "Menu lateral",
        )
        st.session_state["filters_place"] = place

    # Defaults
    if not df.empty:
        min_date, max_date = df["date"].min(), df["date"].max()
        leagues = sorted(df["league"].dropna().unique())
        rounds = sorted([r for r in df["round"].dropna().unique()])
        statuses = sorted(df["status"].dropna().unique())
    else:
        from datetime import date
        min_date = max_date = date.today()
        leagues, rounds, statuses = [], [], []

    def _render_controls(container):
        with container:
            if st.session_state["filters_place"] == "sidebar":
                st.header("Filtros")

            c1, c2 = st.columns(2)
            with c1:
                date_from = st.date_input("De", value=min_date, key="flt_date_from")
            with c2:
                date_to = st.date_input("Até", value=max_date, key="flt_date_to")

            selected_leagues = st.multiselect("Competições", leagues, default=leagues, key="flt_leagues")
            selected_round = st.selectbox("Rodada", ["Todas"] + [str(x) for x in rounds], key="flt_round")
            selected_status = st.multiselect("Status", statuses, default=statuses, key="flt_status")
            query = st.text_input("Buscar (time/mercado)", key="flt_query")
            cols_grid = st.slider("# de colunas", 2, 4, 3, key="flt_cols")

            return date_from, date_to, selected_leagues, selected_round, selected_status, query, cols_grid

    if st.session_state["filters_place"] == "sidebar":
        date_from, date_to, selected_leagues, selected_round, selected_status, query, cols_grid = _render_controls(st.sidebar)
    else:
        with st.expander("🔎 Filtros", expanded=True):
            date_from, date_to, selected_leagues, selected_round, selected_status, query, cols_grid = _render_controls(st.container())

    return date_from, date_to, selected_leagues, selected_round, selected_status, query, cols_grid

# -------------------- Função principal --------------------
def main():
    # CSS Neon
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    # ====== Dados → records → df ======
    records: List[Dict[str, Any]] = []
    if 'df_palpites' in st.session_state and isinstance(st.session_state.df_palpites, pd.DataFrame):
        records = build_records_from_df(st.session_state.df_palpites)

    # Opcional: mesclar fixtures da API-Football
    # fixtures = get_upcoming_fixtures(league_id=None, days=7)
    # records += fetch_matches_api_football(fixtures)

    df = to_df(records)

    # ====== Título ======
    st.markdown("""
    <h2 style="
        color:#00f5ff;
        text-shadow: 0 0 10px rgba(0,245,255,0.8), 0 0 25px rgba(255,45,149,0.4);
        font-weight:800; letter-spacing:0.5px; margin-top:-10px;
    ">
        ⚡ I.A Palpites em Tempo Real
    </h2>
    """, unsafe_allow_html=True)

    # ====== Filtros (inline ou sidebar) ======
    (date_from, date_to, selected_leagues, selected_round,
     selected_status, query, cols_grid) = _filters_block(df)

    # ====== Aplicação dos filtros ======
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

    # ====== Métricas ======
    #c1, c2, c3 = st.columns(3)
    #with c1:
        #st.caption("Jogos listados")
        #st.markdown(f"<h3 style='margin:0'>{len(df_view)}</h3>", unsafe_allow_html=True)
    #with c2:
        #st.caption("Confiança média")
        #avg_conf = (df_view["confidence"].mean() * 100) if not df_view.empty and df_view["confidence"].notna().any() else 0
        #st.markdown(f"<h3 style='margin:0'>{avg_conf:.0f}%</h3>", unsafe_allow_html=True)
    #with c3:
        #st.caption("Competições")
        #st.markdown(f"<h3 style='margin:0'>{len(set(df_view['league'])) if not df_view.empty else 0}</h3>", unsafe_allow_html=True)

    #st.divider()

    # ====== Grid de cards ======
    render_grid(df_view.reset_index(drop=True), cols=cols_grid)
