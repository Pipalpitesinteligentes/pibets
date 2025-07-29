import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe
from PIL import Image
import requests
import re
import json
import os
import gspread

# Salva o conteúdo do secrets em um arquivo temporário
cred_json = st.secrets["GCP_SERVICE_ACCOUNT"]
with open("/tmp/credentials.json", "w") as f:
    f.write(cred_json)  # se der erro, use: json.dump(cred_json, f)

# 2. Conecta ao Google Sheets com escopo apropriado
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("/tmp/credentials.json", scope)
client = gspread.authorize(credentials)

# 3. Acessa a aba de usuários da planilha
planilha = client.open("usuarios_app")
sheet = planilha.worksheet("usuarios")
dados = sheet.get_all_records()

# 4. Gera o config dinamicamente com base no conteúdo da planilha
config = {
    'credentials': {
        'usernames': {
            linha['usuario']: {
                'email': linha['email'],
                'name': linha['nome'],
                'password': stauth.Hasher([str(linha['senha'])]).generate()[0]
            }
            for linha in dados
        }
    },
    'cookie': {
        'name': 'meu_cookie_login',
        'key': 'chave_supersecreta_123',  # troque por algo único
        'expiry_days': 7
    }
}

# 5. Inicializa o autentificador
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 6. Executa a tela de login
name, authentication_status, username = authenticator.login("🔐 Login", "main")

# 7. Resultado do login
if authentication_status:
    st.sidebar.success(f"✅ Bem-vindo, {name}!")
    menu = st.sidebar.selectbox("Menu", ["📊 Palpites", "📈 Gestão de Banca", "🚪 Sair"])

    if menu == "📊 Palpites":
        st.title("📊 Palpites do Dia")
        st.markdown("Conteúdo aqui...")

    elif menu == "📈 Gestão de Banca":
        st.title("📈 Gestão de Banca")
        st.markdown("Outro conteúdo aqui...")

    authenticator.logout("🚪 Sair", "sidebar")

elif authentication_status is False:
    st.error("❌ Usuário ou senha incorretos")

elif authentication_status is None:
    st.warning("🔐 Digite seu usuário e senha para continuar")

# ========= CONTEÚDO LIBERADO APÓS LOGIN =========

with st.sidebar:
    st.markdown("## 👋 Bem-vindo, felipesouza!")
    menu = st.radio("Escolha uma opção:", ["📊 Palpitações", "📈 Gestão de Banca", "🚪 Sair"])

# ========== EXIBIR CONTEÚDO CONFORME O MENU ==========
if menu == "📊 Palpites":
    st.title(" ")
    # Coloque aqui o conteúdo dos palpites

elif menu == "📈 Gestão de Banca":
    st.markdown("## 📈 Gestão de Banca")

    # Entrada da Banca Inicial
    banca_inicial = st.number_input("💰 Informe sua Banca Inicial (R$):", min_value=0.0, step=10.0, format="%.2f")

    # Estilo escuro personalizado
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

elif menu == "🚪 Sair":
    st.session_state.logado = False
    st.success("Você saiu com sucesso.")
    st.rerun()    
    
    # Criando tabela de 30 dias
    dias = list(range(1, 31))
    df = pd.DataFrame({
        "Dia": dias,
        "Resultado do Dia (R$)": [0.0] * len(dias),
        "Resultado em %": ["0%"] * len(dias),
        "Saque (R$)": [0.0] * len(dias)
    })

    # Editor interativo
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

# Exibe os resultados finais
st.markdown(f"""
<div class='banca-final'>
    💰 <strong>Lucro/Prejuízo Total:</strong> R$ {lucro_total:,.2f}  
    🏧 <strong>Saques Totais:</strong> R$ {saques_total:,.2f}  
    💼 <strong>Banca Final:</strong> R$ {banca_final:,.2f}
</div>
""", unsafe_allow_html=True)

# Estilo verde personalizado da Banca Final
st.markdown("""
<style>
.banca-final {
    margin-top: 30px;
    font-size: 22px;
    font-weight: bold;
    color: #00FF88;
    display: flex;
    align-items: center;
    gap: 10px;
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
