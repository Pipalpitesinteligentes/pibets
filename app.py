# app_merged.py
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

# app_merged.py
# ... (TOPO ROBUSTO e imports)

# Agora sim importamos o resto do guard_gsheet para a UI
from guard_gsheet import require_login, issue_token
# Importe pandas explicitamente aqui, pois é usado em funções de conteúdo
import pandas as pd
from PIL import Image
import re 
# Os outros imports do final do script, como gspread, requests, datetime, etc., 
# devem ser movidos para o TOPO do script (onde estão os imports) para evitar NameError

# =================================================================
# 1️⃣ Definições das Funções de Conteúdo (Agora com a lógica dentro)
# =================================================================

def mostrar_palpites():
    # LOGO E TÍTULO
    logo = Image.open("logo_pi.png")
    st.image(logo, width=200)
    st.title("π - Palpites Inteligentes 🇧🇷⚽")

    # RESTANTE DO CONTEÚDO DA PÁGINA DE PALPITES (QUE ESTAVA NO FINAL DO SCRIPT)
    st.markdown("Escolha um confronto abaixo e veja as previsões estatísticas para o jogo.")
    
    # ATENÇÃO: Verifique se df e logos_times estão disponíveis globalmente ou mova a lógica do Google Sheets para o topo.
    # Vou assumir que eles estão disponíveis globalmente como você os definiu no final.
    
    rodadas_disponiveis = sorted(df["Rodada"].dropna().unique())
    rodada_escolhida = st.selectbox("📆 Selecione a rodada:", rodadas_disponiveis)

    df_rodada = df[df["Rodada"] == rodada_escolhida]
    confrontos_disponiveis = df_rodada.apply(lambda x: f"{x['Mandante']} x {x['Visitante']}", axis=1).tolist()
    confronto = st.selectbox("⚽ Escolha o confronto:", confrontos_disponiveis)
    
    # ... (O restante da lógica de Palpites - from if confronto: até o final daquela seção)
    # ... (Este bloco está muito longo para incluir aqui, mas coloque todo o conteúdo)
    # Exemplo de como começa o restante:
    if confronto:
        mandante, visitante = [t.strip() for t in confronto.split("x")]
        jogo = df[(df["Mandante"] == mandante) & (df["Visitante"] == visitante)]
        # ... (todo o bloco `if not jogo.empty: ...`)

def mostrar_banca():
    # CONTEÚDO DA GESTÃO DE BANCA (QUE ESTAVA NO SCRIPT PRINCIPAL)
    st.markdown("## 📈 Gestão de Banca")

    banca_inicial = st.number_input("💰 Informe sua Banca Inicial (R$):", min_value=0.0, step=10.0, format="%.2f", key="banca_input")

    st.markdown("""
    <style>
    /* ... (seu CSS aqui) ... */
    </style>
    """, unsafe_allow_html=True)
    
    # Se você não definiu 'dias' e 'df' globalmente, você precisa importá-los ou criá-los aqui.
    # Vou assumir que pd é importado globalmente.
    dias = list(range(1, 31))
    df_banca = pd.DataFrame({
        "Dia": dias,
        "Resultado do Dia (R$)": [0.0] * len(dias),
        "Resultado em %": ["0%"] * len(dias),
        "Saque (R$)": [0.0] * len(dias)
    })
    
    # ATENÇÃO: Evite usar 'df' dentro de uma função se ele for um DataFrame global do Google Sheets, 
    # use um nome diferente (como `df_banca`) para evitar confusão.
    
    df_editado = st.data_editor(
        df_banca,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        key="gestao_banca"
    )

    # ... (O restante da lógica de Gestão de Banca, incluindo recalcular e exibir os resultados)
    # ... (Seu CSS .resultado-container também deve ser incluído aqui ou no topo)


def mostrar_proximos_jogos():
    # CONTEÚDO DA API-FOOTBALL (QUE ESTAVA NO SCRIPT PRINCIPAL)
    st.header("🔎 Próximos jogos (API-Football)")
    # ... (todo o bloco `if menu == "🔎 Próximos jogos (API-Football)": ...`)
    # ATENÇÃO: Certifique-se de que `API_KEY`, `api_get`, `find_league_id_by_name`, etc. 
    # estejam acessíveis (definidos globalmente no topo do script).

def logout():
    # LÓGICA DE SAÍDA (QUE ESTAVA NO SCRIPT PRINCIPAL)
    if 'logado' in st.session_state:
        st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()


# =================================================================
# 2️⃣ Lógica Principal (Mais limpa e correta)
# =================================================================

# Login primeiro (já estava ok)
user_email = require_login(app_name="Palpite Inteligente")

# 2️⃣ Sidebar (agora definida ANTES do bloco de renderização)
with st.sidebar:
    st.markdown("## 👋 Bem-vindo" + (f", {user_email}" if user_email else "!"))
    menu = st.radio(
        "Escolha uma opção:",
        ["📊 Palpites", "📈 Gestão de Banca", "🔎 Próximos jogos (API-Football)", "🚪 Sair"],
        key="main_menu_radio"
    )

# 3️⃣ Segurança (garantia)
if "menu" not in locals():
    menu = "📊 Palpites"

# 4️⃣ Renderiza conteúdo de acordo com o menu (Apenas chamadas de função)
if menu == "📊 Palpites":
    mostrar_palpites()
elif menu == "📈 Gestão de Banca":
    mostrar_banca()
elif menu == "🔎 Próximos jogos (API-Football)":
    mostrar_proximos_jogos()
elif menu == "🚪 Sair":
    logout()
# ... (o restante do script, como Debugs úteis e a seção ADMIN)

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
# ==== fim do bloco substituto ====

# ----------------- imports gerais que usaremos -----------------
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe
from PIL import Image
import requests
import re
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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

# ================= API-FOOTBALL: funções de integração =================
# ATENÇÃO: coloque sua chave em st.secrets["API_FOOTBALL_KEY"] ou variavel de ambiente API_FOOTBALL_KEY
API_KEY = st.secrets.get("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}

@st.cache_data(ttl=60)
def api_get(path, params=None):
    url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
    resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60*60)  # cache por 1h as ligas (não mudam tanto)
def find_league_id_by_name(country_name=None, league_name=None):
    """
    Busca na API leagues e tenta encontrar o league_id baseado em country_name e/ou league_name.
    Se não achar, retorna None.
    """
    try:
        params = {}
        # podemos filtrar por country ou procurar geral
        if country_name:
            params["country"] = country_name
        data = api_get("/leagues", params=params)
        for item in data.get("response", []):
            league = item.get("league", {})
            country = item.get("country", {})
            if league_name and league_name.lower() in league.get("name", "").lower():
                return league.get("id")
            if country_name and country_name.lower() in country.get("name", "").lower():
                # se passou só country e há correspondência, pode retornar o primeiro
                return league.get("id")
    except Exception:
        return None
    return None

@st.cache_data(ttl=30)  # resultados próximos: cache curto
def get_upcoming_fixtures(league_id: int | None = None, days: int = 7, n: int | None = None):
    """
    Retorna fixtures futuros filtrados por data > now.
    - league_id: se informar, filtra por liga
    - days: busca de hoje até hoje+days (usa from/to)
    - n: se informado e league_id presente, pode usar o endpoint /fixtures?league=..&next=n (API também possui /fixtures?league=..&next=..)
    """
    if not API_KEY:
        raise RuntimeError("Coloque sua API_FOOTBALL_KEY em st.secrets ou como variável de ambiente API_FOOTBALL_KEY.")

    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    from_date = now.date().isoformat()
    to_date = (now + timedelta(days=days)).date().isoformat()

    params = {"from": from_date, "to": to_date, "timezone": "America/Sao_Paulo"}
    if league_id:
        params["league"] = league_id
    # se n informado e league_id presente, podemos usar param next (muitos exemplos usam /fixtures?league=...&next=5)
    if n and league_id:
        params["next"] = n

    data = api_get("/fixtures", params=params)
    fixtures = []
    for item in data.get("response", []):
        f = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        # parse date
        fixture_dt_iso = f.get("date")
        try:
            dt = datetime.fromisoformat(fixture_dt_iso.replace("Z", "+00:00")).astimezone(tz)
        except Exception:
            # pulo parsing inválido
            continue
        # só futuros
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
            "venue": f.get("venue", {}).get("name")
        })
    fixtures.sort(key=lambda x: x["kickoff_local"])
    return fixtures

# ================= END API-FOOTBALL =================

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

# ========== Nova seção: Próximos jogos via API-Football ==========
if menu == "🔎 Próximos jogos (API-Football)":
    st.header("🔎 Próximos jogos (API-Football)")
    st.markdown("Use essa seção para visualizar os próximos jogos de uma liga. Se não souber o `league_id`, digite país ou parte do nome da liga que eu tento resolver automaticamente.")

    if not API_KEY:
        st.warning("Chave da API-Football não encontrada. Adicione `API_FOOTBALL_KEY` em `st.secrets` ou variável de ambiente `API_FOOTBALL_KEY`.")
    else:
        col1, col2 = st.columns([2,1])
        with col1:
            league_input = st.text_input("Insira league_id ou nome da liga / país (ex: '39' ou 'Premier League' ou 'England')", value="39")
            days = st.number_input("Buscar próximos (dias)", min_value=1, max_value=30, value=7)
            n = st.number_input("Se preferir próximos N jogos (opcional, deixa 0 para ignorar)", min_value=0, max_value=0, value=0)
        with col2:
            if st.button("Buscar próximos jogos"):
                try:
                    league_id = None
                    # tenta interpretar como inteiro
                    if str(league_input).strip().isdigit():
                        league_id = int(str(league_input).strip())
                    else:
                        # tenta lookup por nome/pais
                        league_id = find_league_id_by_name(country_name=league_input, league_name=league_input)
                        if not league_id:
                            st.info("Não encontrei a liga automaticamente. Tente com o league_id (ex: 39 para Premier League) ou nome exato.")
                    fixtures = get_upcoming_fixtures(league_id=league_id, days=int(days), n=(int(n) if int(n)>0 else None))
                    if not fixtures:
                        st.info("Nenhum jogo futuro encontrado no período selecionado.")
                    else:
                        # tabela resumida
                        table = []
                        for f in fixtures:
                            table.append({
                                "Data (local)": f["kickoff_local"].strftime("%Y-%m-%d %H:%M"),
                                "Liga": f["league_name"],
                                "Mandante": f["home_team"],
                                "Visitante": f["away_team"],
                                "Local": f["venue"]
                            })
                        st.table(table)
                        # opcional: permitir clicar e importar jogo p/ seu fluxo de palpites
                        st.success(f"{len(table)} jogos futuros listados.")
                except Exception as e:
                    st.error(f"Erro: {e}")

# ===========================================================
# FIM do app_merged.py
# ===========================================================











