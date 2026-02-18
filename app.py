# app.py (corrigido)
# - Corrige try/except de query params (indentação)
# - Corrige string HIDE_TOOLBAR (fecha """)
# - Integra layout em cards (ui_cards.main) na aba de Palpites
# - Mantém login, Sheets e gestão de banca

import os, traceback
import streamlit as st
import pandas as pd
import gspread
import requests
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from typing import Optional
from sheets_reader import read_palpites_from_sheets
import guard_gsheet as guard
from guard_gsheet import require_login, issue_token
import ui_cards

# ======================== Globais ========================
LOGO_CYAN = "#00FFFF"
LOGO_DARK_BLUE = "#1a1d33"

os.environ["MEMBERS_FILE"] = "secure/members.json"
APP_INTERNAL_KEY = "pi-internal-123"

API_KEY = st.secrets.get("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}
st.session_state.API_KEY = API_KEY

SPREADSHEET_ID = "1H-Sy49f5tBV1YCAjd1UX6IKRNRrqr3wzoVSKVWChU00"
SHEET_NAME_PALPITES = "nova-tentativa"

# ======================== Query params utils ========================
try:
    _qp = st.query_params
    getp = _qp.get
except Exception:
    _qp = st.experimental_get_query_params()
    getp = lambda k, d=None: (_qp.get(k, [d]) or [d])[0]

# Healthcheck/endpoint util
if getp("health") == "1":
    st.write("ok")
    st.stop()

if getp("key") == APP_INTERNAL_KEY:
    cmd  = (getp("cmd", "") or "").lower()
    email = (getp("email", "") or "").strip().lower()
    try:
        from guard_gsheet import issue_token, revoke_user
        if cmd == "issue" and email:
            tok = issue_token(email, days=30)
            st.write(f"issued:{email}:{tok}")
        elif cmd == "revoke" and email:
            revoke_user(email)
            st.write(f"revoked:{email}")
        else:
            st.write("bad_command")
    except Exception as e:
        st.write("app_exception:", repr(e))
        st.write("trace:", traceback.format_exc())
    st.stop()

# ======================== Config visual / CSS ========================
st.set_page_config(page_title="Palpite Inteligente", page_icon="⚽", layout="wide")
HIDE_TOOLBAR = """
<style>
/* Toolbar e rodapé */
div[data-testid="stToolbar"] { display: none !important; }
a[data-testid="toolbar-github-icon"], a[aria-label="Open GitHub Repo"], a[href*="github.com"][target="_blank"] { display: none !important; }
footer { visibility: hidden; }

/* Fundo e tipografia */
.stApp { background-color: #0A0A23; }
h1, h2, h3, p, .stMarkdown { color: white; }

/* Cards de resultado (banca) */
.resultado-container { display:flex; justify-content:space-around; margin-top:40px; gap:40px; flex-wrap:wrap; }
.box { background:#1a1b2e; padding:20px; border-radius:12px; width:220px; text-align:center; box-shadow:0 0 10px #00FF88; }
.emoji { font-size:28px; margin-bottom:10px; }
.titulo { font-size:18px; font-weight:bold; color:#00FF88; }
.valor { font-size:24px; font-weight:bold; color:#fff; margin-top:5px; }

@media (max-width: 600px) {
  .resultado-container { gap:20px; flex-direction:column; align-items:center; }
  .box { width:90%; max-width:300px; padding:15px; }
  .valor { font-size:20px; }
  .titulo { font-size:16px; }
}
</style>
"""
st.markdown(HIDE_TOOLBAR, unsafe_allow_html=True)

# ======================== Logos (se usar) ========================
logos_times = {
    "CR Flamengo": "https://logodetimes.com/times/flamengo/logo-flamengo-256.png",
    "SE Palmeiras": "https://logodetimes.com/times/palmeiras/logo-palmeiras-256.png",
    "RB Bragantino": "https://logodetimes.com/times/red-bull-bragantino/logo-red-bull-bragantino-256.png",
    "Cruzeiro EC": "https://logodetimes.com/times/cruzeiro/logo-cruzeiro-256.png",
    "Fluminense FC": "https://logodetimes.com/times/fluminense/logo-fluminense-256.png",
    "SC Internacional": "https://logodetimes.com/times/internacional/logo-internacional-256.png",
    "EC Bahia": "https://logodetimes.com/times/bahia/logo-bahia-256.png",
    "Botafogo FR": "https://logodetimes.com/times/botafogo/logo-botafogo-256.png",
    "Ceará SC": "https://logodetimes.com/times/ceara/logo-ceara-256.png",
    "São Paulo FC": "https://logodetimes.com/times/sao-paulo/logo-sao-paulo-256.png",
    "CR Vasco da Gama": "https://logodetimes.com/times/vasco/logo-vasco-256.png",
    "SC Corinthians Paulista": "https://logodetimes.com/times/corinthians/logo-corinthians-256.png",
    "EC Juventude": "https://logodetimes.com/times/juventude/logo-juventude-256.png",
    "Mirassol FC": "https://logodetimes.com/times/mirassol/logo-mirassol-256.png",
    "Fortaleza EC": "https://logodetimes.com/times/fortaleza/logo-fortaleza-256.png",
    "EC Vitória": "https://logodetimes.com/times/vitoria/logo-vitoria-256.png",
    "CA Mineiro": "https://logodetimes.com/times/atletico-mineiro/logo-atletico-mineiro-256.png",
    "Grêmio FBPA": "https://logodetimes.com/times/gremio/logo-gremio-256.png",
    "Santos FC": "https://logodetimes.com/times/santos/logo-santos-256.png",
    "SC Recife": "https://logodetimes.com/times/sport-recife/logo-sport-recife-256.png"
}

# ======================== API-Football (opcional) ========================
@st.cache_data(ttl=60)
def api_get(path, params=None):
    url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
    if not API_KEY:
        raise ConnectionError("API_FOOTBALL_KEY não configurada.")
    resp = requests.get(url, headers={"x-apisports-key": API_KEY}, params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60*60)
def find_league_id_by_name(country_name=None, league_name=None):
    try:
        params = {}
        if country_name:
            params["country"] = country_name
        data = api_get("/leagues", params=params)
        for item in data.get("response", []):
            league = item.get("league", {})
            if league_name and league_name.lower() in league.get("name", "").lower():
                return league.get("id")
    except Exception:
        return None
    return None

@st.cache_data(ttl=30)
def get_upcoming_fixtures(league_id: int | None = None, days: int = 7, season: int | None = None):
    if not API_KEY:
        raise RuntimeError("Coloque sua API_FOOTBALL_KEY em st.secrets ou como variável de ambiente API_FOOTBALL_KEY.")
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    if season is None:
        season = now.year
    from_date = now.date().isoformat()
    to_date = (now + timedelta(days=days)).date().isoformat()
    params = {"from": from_date, "to": to_date, "timezone": "America/Sao_Paulo", "status": "NS", "season": str(season)}
    if league_id:
        params["league"] = league_id
    data = api_get("/fixtures", params=params)
    fixtures = []
    for item in data.get("response", []):
        f = item.get("fixture", {}); league = item.get("league", {}); teams = item.get("teams", {})
        fixture_dt_iso = f.get("date")
        try:
            dt = datetime.fromisoformat(fixture_dt_iso.replace("Z", "+00:00")).astimezone(tz)
        except Exception:
            continue
        if dt <= now:
            continue
        fixtures.append({
            "fixture_id": f.get("id"),
            "kickoff_iso": fixture_dt_iso,
            "kickoff_local": dt,
            "status": f.get("status", {}).get("short"),
            "home_team": teams.get("home", {}).get("name"),
            "away_team": teams.get("away", {}).get("name"),
            "league_id": league.get("id"),
            "league_name": league.get("name"),
        })
    fixtures.sort(key=lambda x: x["kickoff_local"])
    return fixtures

# ======================== Funções auxiliares do app ========================

def mostrar_banca():
    st.markdown("## 🧮 Calculadora de Risco (Stake)")
    st.markdown("Use esta ferramenta para determinar a entrada ideal (Stake) com base na sua banca total e na confiança do palpite.")
    st.markdown("---")
    banca_total = st.number_input("💰 1. Sua Banca Total (R$):", min_value=10.0, step=50.0, format="%.2f", value=st.session_state.get('banca_total_stake', 1000.0), key="banca_total_input")
    st.session_state['banca_total_stake'] = banca_total
    confianca_palpite = st.slider("📈 2. Confiança do Palpite (em %):", min_value=50, max_value=100, step=1, value=85)
    risco_max_percent = st.slider("⚠️ 3. Risco Máximo por Aposta (Unidade) - % da Banca:", min_value=0.5, max_value=5.0, step=0.5, value=2.0, format="%.1f%%")
    valor_max_risco = banca_total * (risco_max_percent / 100.0)
    confianca_normalizada = (confianca_palpite - 50) / 50.0
    stake_recomendado = valor_max_risco * confianca_normalizada
    st.markdown("---")
    col_stake, col_risco_max = st.columns(2)
    with col_risco_max:
        st.metric(label=f"Valor Máximo da Unidade ({risco_max_percent:.1f}%)", value=f"R$ {valor_max_risco:,.2f}")
    if stake_recomendado <= 0:
        with col_stake:
            st.metric(label="Entrada (Stake) Recomendada", value="R$ 0,00", delta="Confiança muito baixa!", delta_color="inverse")
        st.warning("A confiança do palpite é inferior a 50%. Aconselhamos a não fazer a entrada.")
    else:
        with col_stake:
            st.metric(label="Entrada (Stake) Recomendada", value=f"R$ {stake_recomendado:,.2f}", delta_color="off")
    st.markdown("---")
    st.info(f"Assume risco máximo de {risco_max_percent:.1f}% da banca (R$ {valor_max_risco:,.2f}). Stake varia com a confiança (50% a 100%).")


def logout():
    if 'logado' in st.session_state:
        st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()

# ======================== Fluxo principal ========================

# (Opcional) bloquear sem API_KEY. Se quiser ver somente cards do DF, você pode mover
# essa checagem para perto do uso da API-Football. Mantive como no original.
if not API_KEY:
    st.title("π - Palpites Inteligentes BR ⚽")
    st.error("Chave da API-Football não configurada. Configure `API_FOOTBALL_KEY` em secrets ou env.")
    st.stop()

user_email = require_login(app_name="Palpite Inteligente")

if 'df_palpites' not in st.session_state:
    st.session_state.df_palpites = pd.DataFrame()
if 'sheets_error_message' not in st.session_state:
    st.session_state.sheets_error_message = None

if st.session_state.df_palpites.empty:
    try:
        df_lido = read_palpites_from_sheets(SPREADSHEET_ID, SHEET_NAME_PALPITES)
        st.session_state.df_palpites = df_lido
        st.session_state.sheets_error_message = st.session_state.get("sheets_error")
        if not df_lido.empty:
            st.session_state.sheets_error_message = None
    except Exception as e:
        st.session_state.sheets_error_message = f"Erro geral ao carregar Sheets: {e}"

# Estado do bilhete (oculto por padrão)
if "show_ticket" not in st.session_state:
    st.session_state.show_ticket = False

# Abas
_tab_jogos, _tab_banca, _tab_sair = st.tabs(["⚽ Palpites Prontos", "📈 Gestão de Banca", "🚪 Sair"])

with _tab_jogos:
    st.markdown("## ⚽ Palpites Prontos")

    # Envia o estado pro layout
    ui_cards.main(show_ticket=st.session_state.show_ticket)

with _tab_banca:
    mostrar_banca()

with _tab_sair:
    st.warning("Clique no botão abaixo para sair da sua sessão.")
    if st.button("Confirmar Saída"):
        logout()

# Rodapé admin
st.caption(f"Usuário autenticado: {user_email or 'N/D'}")
ADMINS = {"felipesouzacontatoo@gmail.com"}
is_admin = (user_email or "").strip().lower() in ADMINS
st.caption(f"Admin? {'sim' if is_admin else 'não'}")
if is_admin:
    with st.expander("🔧 Gerar token (ADMIN)"):
        alvo = st.text_input("E-mail do assinante", key="admin_user_email")
        dias = st.number_input("Dias de validade", 1, 365, 30, key="admin_days")
        if st.button("Gerar token para este e-mail", key="admin_issue_token_btn"):
            tok = issue_token(alvo, days=int(dias))
            st.success(f"Token gerado para {alvo}: {tok}")
            st.info("Envie este código ao assinante.")

# ======================== FIM ========================








