import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from zoneinfo import ZoneInfo


# ================================================================
# ==== FUNÇÃO PRINCIPAL (main) – cards integrados ao app principal ====
# ================================================================


def main():
st.set_page_config(page_title="Palpites Inteligentes - Cards", layout="wide")


from ui_cards_helpers import (
build_records_from_df,
fetch_matches_api_football,
to_df,
render_grid,
CARD_CSS,
get_upcoming_fixtures,
)


st.markdown(CARD_CSS, unsafe_allow_html=True)


# ===================== FONTES DE DADOS =====================
records = []
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
today = datetime.today().date()
min_date = max_date = today


col1, col2 = st.columns(2)
with col1:
date_from = st.date_input("De", value=min_date)
with col2:
date_to = st.date_input("Até", value=max_date)


leagues = sorted(df["league"].dropna().unique()) if not df.empty else []
selected_leagues = st.multiselect("Competições", leagues, default=leagues)


rounds = sorted(df["round"].dropna().unique()) if not df.empty else []
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
st.markdown("# ⚽ Palpites Inteligentes – Grade de Jogos")
st.caption("Visual moderno em cards, integrando df_palpites e API-Football.")


c1, c2, c3 = st.columns(3)
with c1:
st.metric("Jogos listados", len(df_view))
main()
