# ui_cards.py – (REESCRITO e COMPATÍVEL com toggle por card no helpers)
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Tuple

from ui_cards_helpers import (
    build_records_from_df,
    fetch_matches_api_football,
    to_df,
    render_grid,
    CARD_CSS,
)

# -------------------- Bloco dos filtros (inline OU sidebar) --------------------
def _filters_block(df: pd.DataFrame) -> Tuple:
    if "filters_place" not in st.session_state:
        st.session_state["filters_place"] = "inline"  # "inline" | "sidebar"

    # Barra de controle: onde exibir
    _l, _r = st.columns([1, 1])
    with _r:
        place = st.radio(
            "Exibir filtros em:",
            options=["inline", "sidebar"],
            index=0 if st.session_state["filters_place"] == "inline" else 1,
            horizontal=True,
            format_func=lambda x: "Aqui na página" if x == "inline" else "Menu lateral",
        )
        st.session_state["filters_place"] = place

    # Defaults
    if not df.empty and "date" in df.columns:
        min_date, max_date = df["date"].min(), df["date"].max()
        leagues = sorted(df["league"].dropna().unique()) if "league" in df.columns else []
        rounds = sorted([r for r in df["round"].dropna().unique()]) if "round" in df.columns else []
        statuses = sorted(df["status"].dropna().unique()) if "status" in df.columns else []
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
        return _render_controls(st.sidebar)
    else:
        with st.expander("🔎 Filtros", expanded=True):
            return _render_controls(st.container())


# -------------------- Função principal --------------------
def main():
    # CSS Neon
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    # ====== Dados → records → df ======
    records: List[Dict[str, Any]] = []
    try:
        if "df_palpites" in st.session_state and isinstance(st.session_state.df_palpites, pd.DataFrame):
            records = build_records_from_df(st.session_state.df_palpites)
    except Exception as e:
        st.error(f"Erro ao montar records do DF: {e}")
        records = []

    # Opcional: mesclar fixtures da API-Football (se você usar)
    # Ex.: records += fetch_matches_api_football(fixtures)
    # (mantive aqui para você ativar depois)
    # try:
    #     fixtures = get_upcoming_fixtures(league_id=None, days=7)
    #     records += fetch_matches_api_football(fixtures)
    # except Exception:
    #     pass

    df = to_df(records)

    # ====== Título ======
    st.markdown(
        """
        <h2 style="
            color:#00f5ff;
            text-shadow: 0 0 10px rgba(0,245,255,0.8), 0 0 25px rgba(255,45,149,0.4);
            font-weight:800; letter-spacing:0.5px; margin-top:-10px;
        ">
            ⚡ I.A Palpites em Tempo Real
        </h2>
        """,
        unsafe_allow_html=True,
    )

    # ====== Filtros ======
    (date_from, date_to, selected_leagues, selected_round,
     selected_status, query, cols_grid) = _filters_block(df)

    # ====== Aplicação dos filtros ======
    df_view = df
    if not df.empty:
        try:
            mask = pd.Series([True] * len(df), index=df.index)

            # datas
            if "date" in df.columns:
                mask &= (df["date"] >= date_from) & (df["date"] <= date_to)

            # competição
            if selected_leagues and "league" in df.columns:
                mask &= df["league"].isin(selected_leagues)

            # rodada
            if selected_round != "Todas" and "round" in df.columns:
                mask &= df["round"].astype(str) == str(selected_round)

            # status
            if selected_status and "status" in df.columns:
                mask &= df["status"].isin(selected_status)

            # busca
            if query:
                q = query.lower()
                mask &= df.apply(lambda r: q in str(r.to_dict()).lower(), axis=1)

            df_view = df[mask]
        except Exception as e:
            st.warning(f"Falha ao aplicar filtros (mostrando tudo): {e}")
            df_view = df

    # ====== Renderização ======
    # IMPORTANTE:
    # NÃO existe show_ticket aqui.
    # O "Ver bilhete / Ocultar" é por card e está dentro do render_grid (helpers).
    df_grid = df_view.reset_index(drop=True)
    render_grid(df_grid, cols=int(cols_grid))
