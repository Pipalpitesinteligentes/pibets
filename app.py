# app_merged.py
# ====================================================================
# ==== 0. IMPORTS, VARIÁVEIS DE AMBIENTE E BIBLIOTECAS UNIFICADAS ====
# ====================================================================
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
from oauth2client.service_account import ServiceAccountCredentials # Para compatibilidade gspread/oauth2client
from gspread_dataframe import get_as_dataframe
from PIL import Image
from typing import Optional

# Configuração de Ambiente
os.environ["MEMBERS_FILE"] = "secure/members.json"
APP_INTERNAL_KEY = "pi-internal-123" # <-- MESMO valor do Worker

# Credenciais e Chaves API (Busca da API-Football deve vir antes das funções que a usam)
API_KEY = st.secrets.get("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}

# ====================================================================
# ==== TOPO ROBUSTO (guard_gsheet + worker) - SEM ALTERAÇÕES ESSENCIAIS
# ====================================================================

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
        from guard_gsheet import issue_token, revoke_user # importa só aqui
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

# ====================================================================
# ==== CONFIGURAÇÃO E CSS (Ajuste do MainMenu corrigido) ====
# ====================================================================

st.set_page_config(page_title="Palpite Inteligente", page_icon="⚽", layout="wide")
# ↓ Ajuste: O MainMenu (hambúrguer) não é mais escondido.
HIDE_TOOLBAR = """
<style>
/* toolbar inteiro (inclui GitHub/Fork) */
div[data-testid="stToolbar"] { display: none !important; }

/* alguns temas/versões colocam link do GitHub como âncora separada */
a[data-testid="toolbar-github-icon"],
a[aria-label="Open GitHub Repo"],
a[href*="github.com"][target="_blank"] { display: none !important; }

/* rodapé padrão */
footer { visibility: hidden; }

/* Estilo geral de fundo */
.stApp { background-color: #0A0A23; }
h1, h2, h3, p, .stMarkdown { color: white; }

/* Estilos para o resultado da Banca */
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
.emoji { font-size: 28px; margin-bottom: 10px; }
.titulo { font-size: 18px; font-weight: bold; color: #00FF88; }
.valor { font-size: 24px; font-weight: bold; color: white; margin-top: 5px; }

/* Estilo para dataframes em Gestão de Banca */
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
"""
st.markdown(HIDE_TOOLBAR, unsafe_allow_html=True)


# Agora sim importamos o resto do guard_gsheet para a UI
from guard_gsheet import require_login, issue_token

# ====================================================================
# ==== CONEXÕES E VARIÁVEIS GLOBAIS (ANTES DAS FUNÇÕES) ====
# ====================================================================

@st.cache_resource(ttl=3600)
def load_gsheet_data():
    "Carrega o DataFrame da planilha do Google Sheets."""
    try:
        # Tenta o método ServiceAccountCredentials (mais antigo/compatível)
        service_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        gc = gspread.authorize(creds)
        sheet = gc.open("nova_tentativa_01").sheet1
        df_sheet = get_as_dataframe(sheet).dropna(how="all")
        return df_sheet
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets. Verifique 'nova_tentativa_01' e 'GCP_SERVICE_ACCOUNT' nos secrets. Erro: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de falha

# Carrega o DataFrame principal (disponível globalmente)
df = load_gsheet_data()

# Mapa de Logos (também global)
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

# ====================================================================
# ==== API-FOOTBALL: funções de integração (Manteve-se global) ====
# ====================================================================

@st.cache_data(ttl=60)
def api_get(path, params=None):
    url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
    resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60*60)
def find_league_id_by_name(country_name=None, league_name=None):
    # Lógica da busca de liga... (sem alterações)
    try:
        params = {}
        if country_name:
            params["country"] = country_name
        data = api_get("/leagues", params=params)
        for item in data.get("response", []):
            league = item.get("league", {})
            country = item.get("country", {})
            if league_name and league_name.lower() in league.get("name", "").lower():
                return league.get("id")
            if country_name and country_name.lower() in country.get("name", "").lower():
                return league.get("id")
    except Exception:
        return None
    return None

@st.cache_data(ttl=30)
def get_upcoming_fixtures(league_id: int | None = None, days: int = 7, n: int | None = None):
    # Lógica da busca de jogos... (sem alterações)
    if not API_KEY:
        raise RuntimeError("Coloque sua API_FOOTBALL_KEY em st.secrets ou como variável de ambiente API_FOOTBALL_KEY.")

    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    from_date = now.date().isoformat()
    to_date = (now + timedelta(days=days)).date().isoformat()

    params = {"from": from_date, "to": to_date, "timezone": "America/Sao_Paulo"}
    if league_id:
        params["league"] = league_id
    if n and league_id:
        params["next"] = n

    data = api_get("/fixtures", params=params)
    fixtures = []
    for item in data.get("response", []):
        f = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
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
            "venue": f.get("venue", {}).get("name")
        })
    fixtures.sort(key=lambda x: x["kickoff_local"])
    return fixtures


# ====================================================================
# ==== 1. FUNÇÕES DE CONTEÚDO (Implementando a lógica dentro) ====
# ====================================================================

def mostrar_jogos_e_palpites():
    # LOGO E TÍTULO
    from PIL import Image
    try:
        logo = Image.open("logo_pi.png")
        st.image(logo, width=200)
    except FileNotFoundError:
        st.header("Logo não encontrada")
        
    st.title("π - Palpites Inteligentes 🇧🇷⚽")
    st.markdown("Selecione a fonte de dados e o jogo para ver as previsões.")

    # Opção 1: Selecionar a fonte dos jogos (Palpites do Sheets ou Jogos da API)
    origem = st.radio(
        "Selecione a fonte dos dados:",
        ["Palpites da Rodada (Sheets)", "Próximos Jogos (API-Football)"],
        horizontal=True
    )
    
    st.markdown("---") 

    if origem == "Palpites da Rodada (Sheets)":
        # Lógica para os dados do Sheets
        if df.empty:
            st.warning("Não há dados de palpites para exibir.")
            return

        # 1. Caixa: Campeonato
        campeonatos = sorted(df["Campeonato"].dropna().unique())
        campeonato_escolhido = st.selectbox("🏆 Selecione o Campeonato:", campeonatos)
        
        df_campeonato = df[df["Campeonato"] == campeonato_escolhido]

        # 2. Caixa: Rodada
        rodadas_disponiveis = sorted(df_campeonato["Rodada"].dropna().unique())
        rodada_escolhida = st.selectbox("📆 Selecione a rodada:", rodadas_disponiveis)

        df_rodada = df_campeonato[df_campeonato["Rodada"] == rodada_escolhida]
        
        # 3. Caixa: Confronto
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
                        
                    else: # origem == "Próximos Jogos (API-Football)"
        # Lógica para os dados da API
        if not API_KEY:
            st.error("Chave da API-Football não configurada.")
            return
            
        st.info("Buscar jogos futuros para gerar palpites em tempo real.")
        
        # 1. Caixa: Liga/Campeonato (Para a API, usamos o ID ou nome)
        league_input = st.text_input("Insira league_id ou nome da liga / país (ex: '39' ou 'Brasil')", value="71")
        
        # Tenta resolver o ID na hora
        try:
            league_id = None
            if str(league_input).strip().isdigit():
                league_id = int(str(league_input).strip())
            else:
                league_id = find_league_id_by_name(country_name=league_input, league_name=league_input)
                if not league_id:
                    st.warning("Liga não encontrada. Tente um ID exato (ex: 71 para Brasil Série A).")

            if league_id:
                # 2. Caixa: Período (Substitui Rodada)
                days = st.number_input("Buscar próximos (dias)", min_value=1, max_value=30, value=7)
                
                # Botão para buscar (pois é uma chamada de API)
                if st.button(f"Buscar {days} dias de jogos (Liga ID: {league_id})"):
                    fixtures = get_upcoming_fixtures(league_id=league_id, days=int(days))
                    
                    if fixtures:
                        # 3. Caixa: Confronto (Opção de Jogo)
                        jogos_api = [
                            f"{f['home_team']} x {f['away_team']} ({f['kickoff_local'].strftime('%d/%m %H:%M')})"
                            for f in fixtures
                        ]
                        jogo_escolhido = st.selectbox("⚽ Escolha o jogo (API):", jogos_api)
                        
                        st.info(f"Detalhes: {jogo_escolhido} (Você pode adicionar a lógica de geração de palpite aqui)")
                    else:
                        st.info("Nenhum jogo futuro encontrado no período selecionado.")

        except Exception as e:
            st.error(f"Erro na busca da API: {e}")

def mostrar_banca():
    # Conteúdo da Gestão de Banca
    st.markdown("## 📈 Gestão de Banca")

    banca_inicial = st.number_input("💰 Informe sua Banca Inicial (R$):", min_value=0.0, step=10.0, format="%.2f", key="banca_input")

    dias = list(range(1, 31))
    df_banca = pd.DataFrame({
        "Dia": dias,
        "Resultado do Dia (R$)": [0.0] * len(dias),
        "Resultado em %": ["0%"] * len(dias),
        "Saque (R$)": [0.0] * len(dias)
    })

    df_editado = st.data_editor(
        df_banca,
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

    # Exibição dos resultados (usa o CSS global)
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


def mostrar_proximos_jogos():
    # Conteúdo da API-Football
    st.header("🔎 Próximos jogos (API-Football)")
    st.markdown("Use essa seção para visualizar os próximos jogos de uma liga. Se não souber o `league_id`, digite país ou parte do nome da liga que eu tento resolver automaticamente.")

    if not API_KEY:
        st.warning("Chave da API-Football não encontrada. Adicione `API_FOOTBALL_KEY` em `st.secrets` ou variável de ambiente `API_FOOTBALL_KEY`.")
        return

    col1, col2 = st.columns([2,1])
    with col1:
        league_input = st.text_input("Insira league_id ou nome da liga / país (ex: '39' ou 'Premier League' ou 'England')", value="39")
        days = st.number_input("Buscar próximos (dias)", min_value=1, max_value=30, value=7)
        n = st.number_input("Se preferir próximos N jogos (opcional, deixa 0 para ignorar)", min_value=0, max_value=0, value=0)
    
    with col2:
        # Espaçador para alinhar o botão
        st.write(" ")
        st.write(" ")
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
                    st.success(f"{len(table)} jogos futuros listados.")
            except Exception as e:
                st.error(f"Erro ao buscar jogos: {e}")

def logout():
    # Lógica de deslogar
    if 'logado' in st.session_state:
        st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()

# ====================================================================
# ==== 2. FLUXO PRINCIPAL DO APP (APÓS LOGIN) ====
# ====================================================================

# Login primeiro
user_email = require_login(app_name="Palpite Inteligente")

# 1️⃣ Define os Tabs no topo da página (Menu Moderno)
tab_jogos, tab_banca, tab_sair = st.tabs([
    "⚽ Jogos e Palpites", 
    "📈 Gestão de Banca", 
    "🚪 Sair"
])

# 2️⃣ Renderiza o conteúdo dentro do bloco "with" da Tab correspondente
with tab_jogos:
    mostrar_jogos_e_palpites()
    
with tab_banca:
    mostrar_banca()

with tab_sair:
    st.warning("Clique no botão abaixo para sair da sua sessão.")
    if st.button("Confirmar Saída"):
        logout()

# Debugs úteis e Admin Panel
st.caption(f"Usuário autenticado: {user_email or 'N/D'}")

# Admins sempre em minúsculas
ADMINS = {"felipesouzacontatoo@gmail.com"}
is_admin = (user_email or "").strip().lower() in ADMINS
st.caption(f"Admin? {'sim' if is_admin else 'não'}")

# Só admins veem o gerador
if is_admin:
    with st.expander("🔧 Gerar token (ADMIN)"):
        alvo = st.text_input("E-mail do assinante", key="admin_user_email")
        dias = st.number_input("Dias de validade", 1, 365, 30, key="admin_days")
        if st.button("Gerar token para este e-mail", key="admin_issue_token_btn"):
            tok = issue_token(alvo, days=int(dias))
            st.success(f"Token gerado para {alvo}: {tok}")
            st.info("Envie este código ao assinante.")

# ====================================================================
# FIM do app_merged.py
# ====================================================================









