# app.py (corrigido)
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


# Abas
_tab_jogos, _tab_banca, _tab_sair = st.tabs(["⚽ Palpites Prontos", "📈 Gestão de Banca", "🚪 Sair"])


with _tab_jogos:
# 👉 Novo layout em cards
ui_cards.main()


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
