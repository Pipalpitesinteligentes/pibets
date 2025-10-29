# app_merged_cards.py – versão com layout em CARDS integrado
# ==================================================================================
# Mantém sua estrutura atual e troca o layout antigo (selectbox) pelo ui_cards.main()
# Requisitos: colocar os arquivos ui_cards.py e ui_cards_helpers.py na mesma pasta.
# ==================================================================================


import os, traceback
import streamlit as st
import pandas as pd
import gspread
import requests
import re
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from PIL import Image
from typing import Optional
from sheets_reader import read_palpites_from_sheets
import hmac
import hashlib
import guard_gsheet as guard


# ⬇️ novo: importa o layout de cards
import ui_cards


# ----------------------------------------------------------------------------------
# Globais de estilo/cores
LOGO_CYAN = "#00FFFF"
LOGO_DARK_BLUE = "#1a1d33"


# Config ambiente
os.environ["MEMBERS_FILE"] = "secure/members.json"
APP_INTERNAL_KEY = "pi-internal-123"


# Credenciais API-Football
API_KEY = st.secrets.get("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}
st.session_state.API_KEY = API_KEY


# Sheets (confirmado pelo usuário)
SPREADSHEET_ID = "1H-Sy49f5tBV1YCAjd1UX6IKRNRrqr3wzoVSKVWChU00"
SHEET_NAME_PALPITES = "nova-tentativa"


# ----------------------------------------------------------------------------------
# Topo robusto / endpoints utilitários
try:
    _qp = st.query_params
    getp = _qp.get
except Exception:
    _qp = st.experimental_get_query_params()
    getp = lambda k, d=None: (_qp.get(k, [d]) or [d])[0]


if getp("health") == "1":
st.write("ok"); st.stop()


if getp("key") == APP_INTERNAL_KEY:
cmd = (getp("cmd", "") or "").lower()
email = (getp("email", "") or "").strip().lower()
try:
from guard_gsheet import issue_token, revoke_user
if cmd == "issue" and email:
tok = issue_token(email, days=30); st.write(f"issued:{email}:{tok}"); st.stop()
elif cmd == "revoke" and email:
revoke_user(email); st.write(f"revoked:{email}"); st.stop()
else:
st.write("bad_command"); st.stop()
except Exception as e:
st.write("app_exception:", repr(e)); st.write("trace:", traceback.format_exc()); st.stop()


# ----------------------------------------------------------------------------------
# Config visual
st.set_page_config(page_title="Palpite Inteligente", page_icon="⚽", layout="wide")
HIDE_TOOLBAR = """
<style>
div[data-testid="stToolbar"] { display: none !important; }
a[data-testid="toolbar-github-icon"], a[aria-label="Open GitHub Repo"], a[href*="github.com"][target="_blank"] { display: none !important; }
footer { visibility: hidden; }
.stApp { background-color: #0A0A23; }
h1, h2, h3, p, .stMarkdown { color: white; }
.resultado-container { display:flex; justify-content:space-around; margin-top:40px; gap:40px; flex-wrap:wrap; }
.box { background:#1a1b2e; padding:20px; border-radius:12px; width:220px; text-align:center; box-shadow:0 0 10px #00FF88; }
.emoji { font-size:28px; margin-bottom:10px; }
.titulo { font-size:18px; font-weight:bold; color:#00FF88; }
.valor { font-size:24px; font-weight:bold; color:#fff; margin-top:5px; }
@media (max-width: 600px) {
.resultado-container { gap:20px; flex-direction:column; align-items:center; }
.box { width:90%; max-width:300px; padding:15px; }
.valor { font-size:20px; } .titulo { font-size:16px; }
}
"""
# ================================== FIM ================================== #



