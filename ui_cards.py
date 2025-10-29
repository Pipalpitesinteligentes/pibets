import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

def main():

# ======================== CONFIG BÁSICA ========================
st.set_page_config(page_title="Palpites – Cards", layout="wide")


# ======================== ESTILOS (CSS) ========================
CARD_CSS = """
<style>
:root {
--card-bg: #0e1117; /* fundo escuro padrão Streamlit */
--card-border: #1f2937;
--chip-bg: #111827;
--chip-txt: #e5e7eb;
--ok: #22c55e; /* verde */
--warn: #f59e0b; /* amarelo */
--bad: #ef4444; /* vermelho */
--brand: #fde047; /* amarelo destaque */
}


.card {
background: var(--card-bg);
border: 1px solid var(--card-border);
border-radius: 16px;
padding: 16px;
box-shadow: 0 6px 18px rgba(0,0,0,0.25);
transition: transform .12s ease, box-shadow .12s ease;
height: 100%;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(0,0,0,0.35); }


.card-header{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.badge{ font-size:12px; padding:4px 8px; border-radius:999px; border:1px solid #374151; background:#111827; color:#e5e7eb; }
.kickoff{ font-size:12px; color:#9ca3af; }
.teams{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin:6px 0 10px; }
.team { display:flex; align-items:center; gap:8px; min-width:0; }
.logo { width:28px; height:28px; border-radius:50%; background:#1f2937; display:flex; align-items:center; justify-content:center; font-size:12px; color:#e5e7eb; border:1px solid #374151; }
.team-name { font-weight:600; color:#e5e7eb; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }


.pred { margin-top:6px; }
.pred-row{ display:flex; align-items:center; justify-content:space-between; font-size:12px; color:#e5e7eb; }
.progress{ width:100%; height:7px; background:#111827; border-radius:999px; overflow:hidden; margin:6px 0 2px; border:1px solid #1f2937; }
.bar{ height:100%; background:linear-gradient(90deg, #fde047, #22c55e); }


.chips{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
.chip { background:var(--chip-bg); color:var(--chip-txt); border:1px solid #374151; border-radius:12px; padding:4px 8px; font-size:12px; }
.chip strong { color:#fde047; }


.footer{ display:flex; justify-content:space-between; align-items:center; margin-top:12px; }
.action{ font-size:12px; color:#111827; background:var(--brand); border:none; padding:8px 10px; border-radius:10px; cursor:pointer; font-weight:700; }
.action:hover{ filter:brightness(0.95); }


/* fix spacing inside columns */
.block-container{ padding-top: 1.5rem; }
</style>
"""


st.markdown(CARD_CSS, unsafe_allow_html=True)


# ======================== MOCK / ADAPTADOR ========================
# Você pode usar **um** dos dois adaptadores abaixo:
# A) `build_records_from_df(df_palpites)` – quando você já tem um DataFrame vindo do Sheets/API
# B) `fetch_matches_api_football()` – quando quiser puxar direto da API-Football (fixtures futuros)
# Escolha e use **um** na seção "APLICA FILTROS".


from zoneinfo import ZoneInfo


TEAM_SPLIT_TOKENS = [" x ", " X ", " vs ", " VS ", " x", " vs"]

pass

