import streamlit as st

# Rota interna para API (antes do login/UI)
if "cmd" in st.experimental_get_query_params():
    from guard_gsheet import issue_token, revoke_user
    import traceback

    params = st.experimental_get_query_params()
    cmd   = (params.get("cmd", [""])[0]).lower()
    email = (params.get("email", [""])[0]).strip().lower()
    key   = (params.get("key", [""])[0])

    APP_INTERNAL_KEY = "pi-internal-123"  # mesmo que está no Worker

    if key != APP_INTERNAL_KEY:
        st.write("unauthorized")
        st.stop()

    try:
        if cmd == "issue" and email:
            tok = issue_token(email, days=30)
            st.write(f"issued:{email}:{tok}")
            st.stop()
        elif cmd == "revoke" and email:
            revoke_user(email)
            st.write(f"revoked:{email}")
            st.stop()
        else:
            st.write("bad_command")
            st.stop()
    except Exception as e:
        st.write("app_exception:", repr(e))
        st.write("trace:", traceback.format_exc())
        st.stop()

# ==== TOPO ROBUSTO (guard_gsheet + worker) ====
import os, traceback
import streamlit as st

os.environ["MEMBERS_FILE"] = "secure/members.json"

APP_INTERNAL_KEY = "pi-internal-123"  # <-- MESMO valor do Worker

# Ler query params (compatível com versões diferentes)
try:
    _qp = st.query_params
    getp = _qp.get
except Exception:
    _qp = st.experimental_get_query_params()
    getp = lambda k, d=None: (_qp.get(k, [d]) or [d])[0]

# Healthcheck
if getp("health") == "1":
    st.write("ok")
    st.stop()

# Endpoint interno (antes de qualquer UI/login)
if getp("key") == APP_INTERNAL_KEY:
    cmd   = (getp("cmd", "") or "").lower()
    email = (getp("email", "") or "").strip().lower()
    try:
        from guard_gsheet import issue_token, revoke_user  # importa só aqui
        if cmd == "issue" and email:
            tok = issue_token(email, days=30)
            st.write(f"issued:{email}:{tok}")
            st.stop()
        elif cmd == "revoke" and email:
            revoke_user(email)
            st.write(f"revoked:{email}")
            st.stop()
        else:
            st.write("bad_command")
            st.stop()
    except Exception as e:
        st.write("app_exception:", repr(e))
        st.write("trace:", traceback.format_exc())
        st.stop()
# ==== FIM do TOPO ROBUSTO ====

# Config da página deve vir antes de qualquer componente visual
st.set_page_config(page_title="Palpite Inteligente", page_icon="⚽", layout="wide")

# Agora sim importamos o resto do guard_gsheet para a UI
from guard_gsheet import require_login, issue_token

# Login primeiro
user_email = require_login(app_name="Palpite Inteligente")

# Debugs úteis
st.caption(f"Usuário autenticado: {user_email or 'N/D'}")

# Admins sempre em minúsculas
ADMINS = {"felipesouzacontatoo@gmail.com"}  # coloque aqui os emails admin
is_admin = (user_email or "").strip().lower() in ADMINS
st.caption(f"Admin? {'sim' if is_admin else 'não'}")

# (opcional) ver session_state se quiser diagnosticar
# st.json(st.session_state)

# Só admins veem o gerador
if is_admin:
    with st.expander("🔧 Gerar token (ADMIN)"):
        alvo = st.text_input("E-mail do assinante", key="admin_user_email")
        dias = st.number_input("Dias de validade", 1, 365, 30, key="admin_days")
        if st.button("Gerar token para este e-mail", key="admin_issue_token_btn"):
            tok = issue_token(alvo, days=int(dias))
            st.success(f"Token gerado para {alvo}: {tok}")
            st.info("Envie este código ao assinante.")

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from PIL import Image
import requests
import re
import json

# ----------------- (A partir daqui, vem sua lógica normal do app) -----------------
# Mantém sua conexão com Google Sheets via st.secrets
# Certifique-se de ter GCP_SERVICE_ACCOUNT em Secrets (JSON da service account)
creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# ========= CONTEÚDO LIBERADO APÓS LOGIN =========

with st.sidebar:
    st.markdown("## 👋 Bem-vindo, felipesouza!")
    menu = st.radio("Escolha uma opção:", ["📊 Palpites", "📈 Gestão de Banca", "🚪 Sair"])

# ========== EXIBIR CONTEÚDO CONFORME O MENU ==========
if menu == "📊 Palpites":
    st.title(" ")
    # Coloque aqui o conteúdo dos palpites

elif menu == "🚪 Sair":
    st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()    

elif menu == "📈 Gestão de Banca":
    st.markdown("## 📈 Gestão de Banca")

    banca_inicial = st.number_input("💰 Informe sua Banca Inicial (R$):", min_value=0.0, step=10.0, format="%.2f")

    st.markdown("""
    <style>
    .stDataFrame, .st-emotion-cache-1uixxvy {
        background-color: #13141f !important;
        color: #ffffff !important;
    }
    .st-emotion-cache-1v0mbdj p {
        color: #00ff99;
        font-size: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    dias = list(range(1, 31))
    df = pd.DataFrame({
        "Dia": dias,
        "Resultado do Dia (R$)": [0.0] * len(dias),
        "Resultado em %": ["0%"] * len(dias),
        "Saque (R$)": [0.0] * len(dias)
    })

    df_editado = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        key="gestao_banca"
    )

    # Recalcular a coluna 'Resultado em %'
    df_editado["Resultado em %"] = df_editado["Resultado do Dia (R$)"].apply(
        lambda x: f"{(x / banca_inicial * 100):.2f}%" if banca_inicial > 0 else "0%"
    )

    # Calcular lucro/prejuízo e saque total
    lucro_total = sum(df_editado["Resultado do Dia (R$)"])
    saques_total = sum(df_editado["Saque (R$)"])
    banca_final = banca_inicial + lucro_total - saques_total

    st.markdown(f"""
<div class='resultado-container'>
    <div class='box'>
        <div class='emoji'>💰</div>
        <div class='titulo'>Lucro/Prejuízo</div>
        <div class='valor'>R$ {lucro_total:,.2f}</div>
    </div>
    <div class='box'>
        <div class='emoji'>🏧</div>
        <div class='titulo'>Saques Totais</div>
        <div class='valor'>R$ {saques_total:,.2f}</div>
    </div>
    <div class='box'>
        <div class='emoji'>💼</div>
        <div class='titulo'>Banca Final</div>
        <div class='valor'>R$ {banca_final:,.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.resultado-container {
    display: flex;
    justify-content: space-around;
    margin-top: 40px;
    gap: 40px;
    flex-wrap: wrap;
}

.box {
    background-color: #1a1b2e;
    padding: 20px;
    border-radius: 12px;
    width: 220px;
    text-align: center;
    box-shadow: 0 0 10px #00FF88;
}

.emoji {
    font-size: 28px;
    margin-bottom: 10px;
}

.titulo {
    font-size: 18px;
    font-weight: bold;
    color: #00FF88;
}

.valor {
    font-size: 24px;
    font-weight: bold;
    color: white;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)

  
# ========= ESTILO VISUAL =========
st.markdown("""
    <style>
    .stApp {
        background-color: #0A0A23;
    }
    h1, h2, h3, p, .stMarkdown {
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ========= LOGO E TÍTULO =========
logo = Image.open("logo_pi.png")
st.image(logo, width=200)
st.title("π - Palpites Inteligentes 🇧🇷⚽")

# ========= ACESSO À PLANILHA =========
import json
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from gspread_dataframe import get_as_dataframe

# Acesso à planilha
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
gc = gspread.authorize(creds)
sheet = gc.open("nova_tentativa_01").sheet1
df = get_as_dataframe(sheet).dropna(how="all")

# ========= MAPA DE LOGOS =========
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

# ========= INTERFACE DE PALPITES =========
st.markdown("Escolha um confronto abaixo e veja as previsões estatísticas para o jogo.")

rodadas_disponiveis = sorted(df["Rodada"].dropna().unique())
rodada_escolhida = st.selectbox("📆 Selecione a rodada:", rodadas_disponiveis)

df_rodada = df[df["Rodada"] == rodada_escolhida]
confrontos_disponiveis = df_rodada.apply(lambda x: f"{x['Mandante']} x {x['Visitante']}", axis=1).tolist()
confronto = st.selectbox("⚽ Escolha o confronto:", confrontos_disponiveis)

if confronto:
    mandante, visitante = [t.strip() for t in confronto.split("x")]
    jogo = df[(df["Mandante"] == mandante) & (df["Visitante"] == visitante)]

    if not jogo.empty:
        dados = jogo.iloc[0]
        st.success("✅ Palpite gerado com sucesso!")

        col1, col2, col3 = st.columns(3)
        with col1:
                st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="{logos_times.get(mandante)}" width="120"/>
            <p style="color:white; font-weight: bold;">{mandante}</p>
        </div>
        """,
        unsafe_allow_html=True
    )  
                
        with col2:
                st.markdown("<div style='text-align:center;font-size:36px;'>⚔️</div>", unsafe_allow_html=True)
    
        with col3:
             st.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="{logos_times.get(visitante)}" width="120"/>
            <p style="color:white; font-weight: bold;">{visitante}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
        st.markdown("---")
        st.markdown(f"### 📅 **Data do jogo:** <span style='color:#3DFB86'>{dados['Data']}</span>", unsafe_allow_html=True)
        st.markdown("### 🧠 **Melhor Palpite:**")
        st.success(f"**{dados['Melhor Palpite']}**")

        st.markdown("### 📊 **Estatísticas do confronto:**")
        st.markdown(f"""
        - 🔥 **+1.5 Gols:** `{dados['+1.5 Gols']}`
        - 🔥 **+2.5 Gols:** `{dados['+2.5 Gols']}`
        - 🥅 **Ambas Marcam:** `{dados['Ambas Marcam']}`
        - 🚩 **Escanteios Estimado:** `{dados['Escanteios Estimado']}`
        """)

        gols_mandante = dados['Gols Mandante']
        gols_visitante = dados['Gols Visitante']
        resultado_real = f"{gols_mandante} x {gols_visitante}"
        st.markdown(f"### 📊 Resultado Real: `{resultado_real}`")

        total_gols = gols_mandante + gols_visitante
        ambas_marcam = gols_mandante > 0 and gols_visitante > 0

        palpite = dados['Melhor Palpite'].strip().lower()
        acertou = False
        if "1.5" in palpite and total_gols > 1.5:
            acertou = True
        elif "2.5" in palpite and total_gols > 2.5:
            acertou = True
        elif "ambas" in palpite and ambas_marcam:
            acertou = True
        elif f"{gols_mandante} x {gols_visitante}" in palpite:
            acertou = True

        escanteios_mandante = dados['Escanteios Mandante']
        escanteios_visitante = dados['Escanteios Visitante']
        escanteios_estimado = dados['Escanteios Estimado']
        escanteios_reais = escanteios_mandante + escanteios_visitante

        acertou_escanteios = False
        if "escanteio" in palpite:
            match = re.search(r"(\d+)\+", palpite)
            if match:
                minimo = int(match.group(1))
                if escanteios_reais >= minimo:
                    acertou_escanteios = True

        st.markdown(f"**🟡 Escanteios Reais:** `{escanteios_reais}`")
        st.markdown(f"**📌 Escanteios Estimado:** `{escanteios_estimado}`")

        if pd.isna(gols_mandante) or pd.isna(gols_visitante):
            st.info("⏳ Aguardando resultado do jogo...")
        else:
            if acertou:
                st.success("✅ Palpite de gols correto!")
            else:
                st.error("❌ Palpite de gols incorreto.")

            if "escanteio" in palpite:
                if acertou_escanteios:
                    st.success("✅ Palpite de escanteios correto!")
                else:
                    st.error("❌ Palpite de escanteios incorreto!")























