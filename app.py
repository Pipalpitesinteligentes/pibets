# app_merged.py - CÓDIGO FINAL COM FLUXO WORKER/SHEETS
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
from PIL import Image
from typing import Optional
from sheets_reader import read_palpites_from_sheets
import hmac
import hashlib
import guard_gsheet as guard

# Coloque essas linhas no escopo global do app.py, antes de qualquer função.
LOGO_CYAN = "#00FFFF" 
LOGO_DARK_BLUE = "#1a1d33" 

# Configuração de Ambiente
os.environ["MEMBERS_FILE"] = "secure/members.json"
APP_INTERNAL_KEY = "pi-internal-123"

# Credenciais e Chaves API
# ⚠️ CORREÇÃO 1: Garante que a API Key é buscada corretamente
API_KEY = st.secrets.get("API_FOOTBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY} if API_KEY else {}
st.session_state.API_KEY = API_KEY

# ID da Planilha de Palpites Prontos (O SEU LINK)
# ⚠️ VALORES CONFIRMADOS PELO USUÁRIO. NÃO ALTERAR.
SPREADSHEET_ID = "1H-Sy49f5tBV1YCAjd1UX6IKRNRrqr3wzoVSKVWChU00" 
SHEET_NAME_PALPITES = "nova-tentativa" 

# ====================================================================
# ==== TOPO ROBUSTO (guard_gsheet + worker) - SEM ALTERAÇÕES ESSENCIAIS
# ====================================================================

# ... (CÓDIGO DO TOPO ROBUSTO INALTERADO) ...

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
    cmd     = (getp("cmd", "") or "").lower()
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
        st.stop()
    except Exception as e:
        st.write("app_exception:", repr(e))
        st.write("trace:", traceback.format_exc())
        st.stop()
        
# ====================================================================
# ==== CONFIGURAÇÃO E CSS (Ajuste do MainMenu corrigido) ====
# ====================================================================

st.set_page_config(page_title="Palpite Inteligente", page_icon="⚽", layout="wide")
HIDE_TOOLBAR = """
<style>
/* ... (CSS INALTERADO) ... */
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

# Mapa de Logos (também global)
logos_times = {
    # ... (MAPA DE LOGOS INALTERADO) ...
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
# ==== API-FOOTBALL: funções de integração (APENAS PARA TESTE) ====
# ====================================================================
# OBS: O conteúdo dessas funções permanece o mesmo da correção anterior.
@st.cache_data(ttl=60)
def api_get(path, params=None):
    # ... (CÓDIGO INALTERADO) ...
    url = API_BASE.rstrip("/") + "/" + path.lstrip("/")
    if not API_KEY:
        raise ConnectionError("API_FOOTBALL_KEY não configurada.")
        
    resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=15)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=60*60)
def find_league_id_by_name(country_name=None, league_name=None):
    # ... (CÓDIGO INALTERADO) ...
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
    # ... (CÓDIGO INALTERADO) ...
    if not API_KEY:
        raise RuntimeError("Coloque sua API_FOOTBALL_KEY em st.secrets ou como variável de ambiente API_FOOTBALL_KEY.")

    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    
    if season is None:
        season = now.year 

    from_date = now.date().isoformat()
    to_date = (now + timedelta(days=days)).date().isoformat()

    params = {
        "from": from_date, 
        "to": to_date, 
        "timezone": "America/Sao_Paulo",
        "status": "NS",
        "season": str(season)
    }
    
    if league_id:
        params["league"] = league_id

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
            # ⚠️ CORREÇÃO DE SYNTAX ERROR: Adicionei esta linha para fechar a função
            "venue": f.get("venue", {}).get("name") 
        })
        # FIM DA CORREÇÃO DO SYNTAX ERROR (o erro geralmente era uma falta de fechar um dict ou list)
    
    fixtures.sort(key=lambda x: x["kickoff_local"])
    return fixtures

# ====================================================================
# ==== 1. FUNÇÕES DE CONTEÚDO (Implementando a lógica dentro) ====
# ====================================================================

# ====================================================================
# ==== 1. FUNÇÕES DE CONTEÚDO (Implementando a lógica dentro) ====
# ====================================================================

# ... (Mantenha as funções api_get, find_league_id_by_name, get_upcoming_fixtures) ...
# ... (Mantenha a função mostrar_banca/mostrar_calculadora_stake) ...

# Certifique-se de que logos_times está definido globalmente (que já está!)

def mostrar_jogos_e_palpites():
    
    st.title("π - Palpites Inteligentes⚽")
    st.markdown("---") 
    
    # Função segura para formatar os itens (mantida)
    def _format_item_safe(row):
        dt = row.get('Data/Hora') or row.get('Data_Hora') or row.get('DataHora') or row.get('data_hora')
        jogo = row.get('Jogo') or row.get('jogo') or row.get('Partida') or "Jogo sem nome"

        if pd.notna(dt):
            try:
                dt_str = pd.to_datetime(dt).strftime("%d/%m %H:%M")
                return f"{jogo} ({dt_str})"
            except Exception:
                return f"{jogo} (Data inválida)"
        else:
            return f"{jogo}"

    # 🛑 Pega df do session_state
    df_palpites = st.session_state.df_palpites
    sheets_error_message = st.session_state.sheets_error_message

    # Mostra mensagem de erro do Sheets, se houver
    if sheets_error_message:
        st.error(f"Erro na Conexão com Google Sheets: {sheets_error_message}")
        st.warning("Verifique sua Service Account e permissões.")
        return

    if df_palpites.empty:
        st.info("Nenhum palpite disponível no momento.")
        return
        
    st.subheader(f"Selecione um Palpite (Total: {len(df_palpites)})")

    # Lista de jogos para selectbox
    jogos_disponiveis = [_format_item_safe(r) for _, r in df_palpites.iterrows()]

    # Caixa de seleção (mantida na coluna principal)
    jogo_escolhido_str = st.selectbox(
        "⚽ Escolha o confronto para visualizar o palpite:", 
        jogos_disponiveis, 
        label_visibility="collapsed" # Esconde o label para ficar mais limpo
    )

    if jogo_escolhido_str:
        nome_jogo = jogo_escolhido_str.split('(')[0].strip()
        
        # Encontra o palpite selecionado (robusto)
        if 'Jogo' in df_palpites.columns:
            palpite_selecionado = df_palpites[df_palpites['Jogo'] == nome_jogo].iloc[0]
        else:
            palpite_selecionado = df_palpites.iloc[0] # Pega o primeiro se não conseguir filtrar
        
        # Extrai os nomes dos times (simplificado: assume "Casa vs Visitante")
        try:
            time_casa, time_fora = [t.strip() for t in nome_jogo.split("vs")]
        except ValueError:
             time_casa = nome_jogo
             time_fora = "Visitante"
        
        # ====================================================================
        # ==== NOVO LAYOUT DE DUAS COLUNAS PARA O DESTAQUE DO PALPITE ====
        # ====================================================================
        st.markdown("---")
        
        col_jogo, col_metricas = st.columns([5, 3], gap="large") # Colunas 5/3

        # ------------------------------------------------------------------
        # COLUNA ESQUERDA (JOGO E LOGOS)
        # ------------------------------------------------------------------
        with col_jogo:
            st.markdown(f"### Confronto Analisado: {nome_jogo}")
            
            # --- CARD DE DESTAQUE DO JOGO (COM NOVO CSS) ---
            st.markdown("<div class='confronto-card'>", unsafe_allow_html=True)
            
            # Divide o card em 3 colunas (3-1-3 para mais espaço)
            col_logo_casa, col_vs, col_logo_fora = st.columns([3, 1, 3])
            
            # Logo Casa
            logo_casa_url = logos_times.get(time_casa, None)
            with col_logo_casa:
                if logo_casa_url:
                    st.image(logo_casa_url, width=100) # Removemos o caption
                else:
                    st.markdown(f"#### {time_casa}")
                # Nome do Time
                st.markdown(f"<div class='time-nome'>{time_casa}</div>", unsafe_allow_html=True)


            # VS
            with col_vs:
                # Usando o novo CSS para alinhar o VS
                st.markdown("<div class='vs-text'>VS</div>", unsafe_allow_html=True)

            # Logo Fora
            logo_fora_url = logos_times.get(time_fora, None)
            with col_logo_fora:
                if logo_fora_url:
                    st.image(logo_fora_url, width=100) # Removemos o caption
                else:
                    st.markdown(f"#### {time_fora}")
                # Nome do Time
                st.markdown(f"<div class='time-nome'>{time_fora}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True) # Fecha o card

            # Data/Hora (Abaixo do card)
            data_col = palpite_selecionado.get('Data/Hora') or palpite_selecionado.get('Data_Hora')
            if pd.notna(data_col):
                try:
                    dt_formatado = pd.to_datetime(data_col).strftime('%d/%m/%Y às %H:%M')
                    st.markdown(f"🗓️ **Kickoff:** {dt_formatado}")
                except Exception:
                    st.markdown("🗓️ **Kickoff:** Data inválida")
        
        # ------------------------------------------------------------------
        # COLUNA DIREITA (PALPITE E MÉTRICAS)
        # ------------------------------------------------------------------
        with col_metricas:
            
            # 1️⃣ Predição IA (Destaque Principal)
            palpite_final = palpite_selecionado.get('Palpite', 'N/D')
            
            st.markdown(f"### 🎯 Palpite Recomendado")
            
            # Contêiner para envolver o palpite em um Box de Destaque
            st.markdown(f"""
                <div style='background-color: #1a1d33; padding: 20px; border-radius: 10px; text-align: center;'>
                    <h1 style='color: {LOGO_CYAN}; margin: 0; padding: 0;'>{palpite_final}</h1>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---") # Separador para métricas
            
            # Exibe métricas em linha
            col_c, col_o = st.columns(2)

            # 2️⃣ Confiança (robusto)
            conf_val, conf_display = _get_confidence_display(palpite_selecionado)
            with col_c:
                st.metric(label="📈 Confiança", value=conf_display)

            # 3️⃣ Odd Sugerida (robusto)
            odd_val, odd_display = _get_odd_display(palpite_selecionado)
            with col_o:
                st.metric(label="📊 Odd Recomendada", value=odd_display)

            # Botão para aplicar palpite
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"Aplicar Stake com este Palpite →", type="primary", use_container_width=True):
                st.success(f"Palpite '{palpite_final}' do jogo '{nome_jogo}' considerado para sua estratégia.")
                # st.rerun() # Opcional: para forçar re-render se houver mudança de estado

# ====================================================================
# NOVAS FUNÇÕES AUXILIARES NECESSÁRIAS
# ====================================================================

# Adicione estas funções auxiliares no seu app.py (próximo das funções mostrar_*)

def _get_confidence_display(palpite_selecionado):
    """Função auxiliar para padronizar o display da Confiança."""
    conf_names = ['Confiança', 'Confiança (%)', 'Confianca', 'confidence']
    confianca_val = None
    for name in conf_names:
        if name in palpite_selecionado:
            confianca_val = palpite_selecionado[name]
            break
            
    if pd.isna(confianca_val) or confianca_val is None:
        return None, 'N/D'
    elif isinstance(confianca_val, (int, float)):
        # Multiplica por 100 se valor <= 1 (decimais)
        if confianca_val <= 1:
            confianca_val = confianca_val * 100
        return confianca_val, f"{confianca_val:.1f}%"
    return None, str(confianca_val)

def _get_odd_display(palpite_selecionado):
    """Função auxiliar para padronizar o display da Odd."""
    odd_names = ['Odd Sugerida', 'Odd', 'odd', 'Odd_Sugerida']
    odd_val = None
    for name in odd_names:
        if name in palpite_selecionado:
            odd_val = palpite_selecionado[name]
            break
            
    if pd.isna(odd_val) or odd_val is None:
        return None, 'N/D'
    elif isinstance(odd_val, (int, float)):
        return odd_val, f"{odd_val:.2f}"
    return None, str(odd_val)
    
def mostrar_banca():
    st.markdown("## 🧮 Calculadora de Risco (Stake)")
    st.markdown("Use esta ferramenta para determinar a entrada ideal (Stake) com base na sua banca total e na confiança do palpite.")
    st.markdown("---")

    # 1. ENTRADA DA BANCA TOTAL (Persistência básica via st.session_state)
    banca_total = st.number_input(
        "💰 1. Sua Banca Total (R$):", 
        min_value=10.0, 
        step=50.0, 
        format="%.2f",
        value=st.session_state.get('banca_total_stake', 1000.0), # Valor padrão 1000
        key="banca_total_input"
    )
    # Garante que o valor preenchido persista
    st.session_state['banca_total_stake'] = banca_total


    # 2. ENTRADA DA CONFIANÇA
    confianca_palpite = st.slider(
        "📈 2. Confiança do Palpite (em %):",
        min_value=50, 
        max_value=100, 
        step=1, 
        value=85
    )

    # 3. ENTRADA DO RISCO MÁXIMO (A porcentagem máxima que você arrisca em 1 unidade)
    risco_max_percent = st.slider(
        "⚠️ 3. Risco Máximo por Aposta (Unidade) - % da Banca:",
        min_value=0.5, 
        max_value=5.0, 
        step=0.5, 
        value=2.0, # Padrão: 2% de risco máximo por aposta
        format="%.1f%%"
    )
    
    # --- LÓGICA DE CÁLCULO (Stake Variável) ---
    
    # 1. Calcula o valor máximo de risco (100% da sua unidade, ex: 2% de R$ 1000 = R$ 20)
    valor_max_risco = banca_total * (risco_max_percent / 100.0)

    # 2. Normaliza a Confiança (50% a 100% vira 0 a 1)
    # 50% = 0 (Stake 0), 100% = 1 (Stake Máximo)
    # (Confiança - Mínima) / (Máxima - Mínima)
    confianca_normalizada = (confianca_palpite - 50) / 50.0
    
    # 3. Stake Calculado
    # Ex: Se a confiança for 85%, confianca_normalizada = 0.7
    # Stake = R$ 20.00 * 0.7 = R$ 14.00
    stake_recomendado = valor_max_risco * confianca_normalizada

    st.markdown("---")
    
    # --- EXIBIÇÃO DO RESULTADO ---
    
    col_stake, col_risco_max = st.columns(2)
    
    with col_risco_max:
        st.metric(
            label=f"Valor Máximo da Unidade ({risco_max_percent:.1f}%)",
            value=f"R$ {valor_max_risco:,.2f}"
        )

    if stake_recomendado <= 0:
        with col_stake:
            st.metric(
                label="Entrada (Stake) Recomendada",
                value="R$ 0,00",
                delta="Confiança muito baixa!",
                delta_color="inverse"
            )
        st.warning("A confiança do palpite é inferior a 50%. Aconselhamos a não fazer a entrada.")
    else:
        with col_stake:
            st.metric(
                label="Entrada (Stake) Recomendada",
                value=f"R$ {stake_recomendado:,.2f}",
                delta_color="off"
            )

    st.markdown("---")
    st.info(f"O cálculo assume que: o risco máximo que você tolera é de {risco_max_percent:.1f}% da sua banca (R$ {valor_max_risco:,.2f}). O valor de entrada (stake) é ajustado proporcionalmente à confiança do palpite (entre 50% e 100%).")

def mostrar_proximos_jogos():
    # Conteúdo da API-Football (MANTIDO para teste de API)
    st.header("🔎 Próximos jogos (API-Football) - Debug")
    st.markdown("Use essa seção para *testar e depurar* as chamadas de API, confirmando que sua chave e filtros funcionam.")

    if not API_KEY:
        st.warning("Chave da API-Football não encontrada.")
        return

    # 🛑 ENVOLVENDO O LAYOUT EM UM CONTAINER EXCLUSIVO DA ABA
    with st.container(): 
        col1, col2, col3 = st.columns([2,1,1]) # ⬅️ AGORA ISOLADO
        with col1:
            league_input = st.text_input("Insira league_id ou nome da liga / país (ex: '39' ou 'Premier League')", value="39", key="search_league_input")
        with col2:
            days = st.number_input("Buscar próximos (dias)", min_value=1, max_value=30, value=7, key="search_days")
        with col3:
            season_input = st.number_input("Ano da Season", min_value=2000, max_value=datetime.now().year + 1, value=datetime.now().year, key="search_season")
        
        # ... (O restante da lógica da função continua aqui, fora do col1, col2, col3) ...
        n = 0 
        st.write(" ")
    
    if st.button("Buscar próximos jogos (API)"):
        try:
            league_id = None
            if str(league_input).strip().isdigit():
                league_id = int(str(league_input).strip())
            else:
                league_id = find_league_id_by_name(country_name=league_input, league_name=league_input)
                if not league_id:
                    st.info("Não encontrei a liga automaticamente. Tente com o league_id (ex: 39 para Premier League) ou nome exato.")
            
            fixtures = get_upcoming_fixtures(
                league_id=league_id, 
                days=int(days), 
                season=int(season_input) 
            )
            
            if not fixtures:
                st.info("Nenhum jogo futuro encontrado no período selecionado. Verifique o ID da Liga e o Ano da Season.")
            else:
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
            st.code(traceback.format_exc())


def logout():
    # Lógica de deslogar
    if 'logado' in st.session_state:
        st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()

# ====================================================================
# ==== 2. FLUXO PRINCIPAL DO APP (APÓS LOGIN) ====
# ====================================================================

# ⚠️ CORREÇÃO 3: Verificação da API Key
if not API_KEY:
    st.title("π - Palpites Inteligentes BR ⚽")
    st.error("Chave da API-Football não configurada. Configure a chave `API_FOOTBALL_KEY` no `.streamlit/secrets.toml`.")
    st.stop()


# Login primeiro
user_email = require_login(app_name="Palpite Inteligente")

# NOVO BLOCO: Carregamento Principal do DataFrame (RESOLVE NameError)
# -------------------------------------------------------------------
# 1. Inicializa o estado se não existir
if 'df_palpites' not in st.session_state:
    st.session_state.df_palpites = pd.DataFrame()
if 'sheets_error_message' not in st.session_state:
    st.session_state.sheets_error_message = None

# 2. Se o DataFrame estiver vazio, tenta carregar (ou sempre que quiser recarregar)
if st.session_state.df_palpites.empty:
    try:
        # Chama a função de leitura do Sheets
        df_lido = read_palpites_from_sheets(SPREADSHEET_ID, SHEET_NAME_PALPITES) 
        
        # Armazena o resultado no Session State
        st.session_state.df_palpites = df_lido
        st.session_state.sheets_error_message = st.session_state.get("sheets_error") # Pega o erro do sheets_reader
        
        # Se carregou, limpa o erro
        if not df_lido.empty:
            st.session_state.sheets_error_message = None 
            
    except Exception as e:
        # Captura erros gerais
        st.session_state.sheets_error_message = f"Erro geral ao carregar Sheets: {e}"

# 1️⃣ Define os Tabs no topo da página (Menu Moderno)
tab_jogos, tab_banca, tab_sair = st.tabs([
    "⚽ Palpites Prontos", # Nome da aba alterado
    "📈 Gestão de Banca", 
    "🚪 Sair"
])

# 2️⃣ Renderiza o conteúdo dentro do bloco "with" da Tab correspondente
with tab_jogos:
    mostrar_jogos_e_palpites() # Agora carrega do Sheets
    
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






























































