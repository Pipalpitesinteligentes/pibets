import os
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
import traceback
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials # Importada no topo

# --- CONFIGURAÇÃO E CONSTANTES ---
TZ = timezone(timedelta(hours=-3)) # America/Sao_Paulo
SHEET_NAME = os.environ.get("MEMBERS_SHEET_NAME", "members")      # nome da planilha
WORKSHEET = os.environ.get("MEMBERS_WORKSHEET_NAME", "usuarios")  # aba

# --- CONSTANTES DE COR BASEADAS NA LOGO ---
LOGO_CYAN = "#00FFFF" 
LOGO_DARK_BLUE = "#1a1d33"

# --- UTILITÁRIOS ---
def _now():
    """Retorna o datetime atual no fuso horário configurado."""
    return datetime.now(TZ)

def sha256_hex(x: str) -> str:
    """Calcula o hash SHA256 de uma string."""
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def constant_time_equal(a: str, b: str) -> bool:
    """Compara duas strings em tempo constante para segurança."""
    return hmac.compare_digest(a, b)

# --------------------------------------------------------------------------------
# CÓDIGO CSS CUSTOMIZADO PARA O LAYOUT DE LOGIN (NOVO)
# --------------------------------------------------------------------------------
def _apply_login_style():
    """Injeta CSS simples, usando as cores da logo para o estilo do botão e cards."""
    # As variáveis LOGO_CYAN e LOGO_DARK_BLUE DEVEM estar definidas fora desta função
    st.markdown(f"""
        <style>
        /* Estilo do botão de ação principal (Entrar) */
        .stButton>button.primary {{
            /* Cor do botão: O ciano/verde-água vibrante da logo */
            background-color: {LOGO_CYAN}; 
            color: #000000; 
            font-weight: bold;
        }}
        .stButton>button.primary:hover {{
            /* Sombra ou tom levemente diferente para hover */
            background-color: #00E0E0; 
        }}
        
        /* Estilo do "card" de benefícios */
        .benefit-card {{
            /* Fundo dos cards: Um azul escuro sutil que combina com o fundo do app */
            background-color: {LOGO_DARK_BLUE}; 
            padding: 10px 15px; 
            margin-bottom: 15px; 
            border-radius: 8px; 
            display: flex; 
            align-items: center;
        }}
        
        /* Cor dos ícones dentro dos cards */
        .benefit-icon {{
            font-size: 1.5em; 
            /* Cor dos ícones: Ciano vibrante */
            color: {LOGO_CYAN}; 
            margin-right: 15px;
        }}
        
        /* Estilo para links/textos de apoio */
        a {{
            color: {LOGO_CYAN}; /* Torna links (como 'Fale com o Suporte') ciano */
        }}
        </style>
    """, unsafe_allow_html=True)

def _benefit_card(icon, text):
    """Função auxiliar para criar os 'cards' de benefício em HTML puro."""
    st.markdown(f"""
        <div class="benefit-card">
            <span class="benefit-icon">{icon}</span>
            <span style="color: #DDDDDD;">{text}</span>
        </div>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS AUTHENTICATION ---
# Cria e mantém o client em cache (Streamlit >= 1.12)
@st.cache_resource
def _create_gspread_client():
    sa = st.secrets.get("GCP_SERVICE_ACCOUNT")
    creds_dict = None

    if isinstance(sa, dict):
        creds_dict = sa
    elif isinstance(sa, str):
        s = sa.strip()
        if s.startswith("{"):
            try:
                creds_dict = json.loads(s)
            except Exception as e:
                st.error("JSON em GCP_SERVICE_ACCOUNT está mal formado.")
                st.exception(e)
                st.stop()
        else:
            try:
                creds_dict = json.loads(s)
            except Exception as e:
                st.error("Formato desconhecido em GCP_SERVICE_ACCOUNT. Verifique o segredo.")
                st.exception(e)
                st.stop()
    else:
        st.error("Erro Crítico de Secret: Chave GCP_SERVICE_ACCOUNT não encontrada.")
        st.stop()

    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error("Falha ao autenticar no Google Sheets. Verifique credenciais e permissões.")
        st.exception(e)
        st.stop()

# Wrapper compatível com chamadas antigas no código
def _client():
    return _create_gspread_client()

# Abre a worksheet com tratamento de erro
def _ws():
    try:
        c = _client()
        sh = c.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET)
        return ws
    except gspread.SpreadsheetNotFound:
        st.error(f"Planilha '{SHEET_NAME}' não encontrada (verifique nome).")
        st.stop()
    except gspread.WorksheetNotFound:
        st.error(f"Aba '{WORKSHEET}' não encontrada na planilha '{SHEET_NAME}'.")
        st.stop()
    except Exception as e:
        st.error("Erro ao abrir a worksheet.")
        st.exception(e)
        st.stop()

# --- (RESTO DAS FUNÇÕES DE BUSCA E VALIDAÇÃO) ---

def _rows() -> List[List[str]]:
    """Busca todas as linhas da aba de usuários."""
    ws = _ws()
    # header (linha 1): email | status | plan | exp | token_sha256 | updated_at
    return ws.get_all_values()

def _find_row_index(email: str) -> Optional[int]:
    """Encontra o índice da linha do usuário (base 1)."""
    vals = _rows()
    for idx, row in enumerate(vals[1:], start=2):
        if len(row) > 0 and row[0].strip().lower() == email.strip().lower():
            return idx
    return None
    
def _client():
    return _create_gspread_client()
    
def get_user(email: str) -> Optional[Dict]:
    """Retorna os dados do usuário como um dicionário."""
    vals = _rows()
    for row in vals[1:]:
        if len(row) < 1:
            continue
        if row[0].strip().lower() == email.strip().lower():
            def col(i): return row[i].strip() if i < len(row) else ""
            return {
                "email": col(0),
                "status": col(1),
                "plan": col(2),
                "exp": col(3),
                "token_sha256": col(4),
                "updated_at": col(5),
            }
    return None

def is_active(email: str) -> bool:
    """Verifica se o usuário está ativo e com a assinatura válida."""
    u = get_user(email)
    if not u or u.get("status") != "active":
        return False
    exp = u.get("exp")
    if not exp:
        return False
    
    # Conversão da data de expiração
    try:
        dt = datetime.fromisoformat(exp).replace(tzinfo=TZ)
    except Exception:
        try:
            dt = datetime.strptime(exp, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZ)
        except Exception:
            return False
            
    return _now() <= dt

def _upsert(email: str, status: str, plan: str, exp_iso: str, token_sha256: str):
    """Insere ou atualiza a linha de um usuário."""
    ws = _ws()
    row_idx = _find_row_index(email)
    payload = [email.lower(), status, plan, exp_iso, token_sha256, _now().isoformat()]
    if row_idx:
        ws.update(f"A{row_idx}:F{row_idx}", [payload])
    else:
        ws.append_row(payload, value_input_option="USER_ENTERED")

def issue_token(email: str, days: int = 30, plan: str = "mensal") -> str:
    """Gera, salva e retorna um novo token para o usuário."""
    token_raw = sha256_hex(f"{email}-{time.time()}")[:16]
    token_hash = sha256_hex(token_raw)
    exp_dt = (_now() + timedelta(days=days)).replace(microsecond=0)
    _upsert(email=email, status="active", plan=plan, exp_iso=exp_dt.isoformat(), token_sha256=token_hash)
    return token_raw

def revoke_user(email: str):
    """Revoga o acesso do usuário."""
    u = get_user(email)
    if not u:
        return
    _upsert(
        email=email,
        status="inactive",
        plan=u.get("plan", "mensal"),
        exp_iso=u.get("exp", ""),
        token_sha256=u.get("token_sha256", ""),
    )

def validate_email_token(email: str, token_plain: str) -> bool:
    """Valida o e-mail e o token do usuário."""
    u = get_user(email)
    if not u or u.get("status") != "active" or not token_plain or not u.get("token_sha256") or not is_active(email):
        return False
        
    return constant_time_equal(sha256_hex(token_plain), u["token_sha256"])

# ---------- UI (st_login MODIFICADO) ----------
def st_login(app_name: str = "Painel", show_logo: bool = True):
    
    # 1. Aplica o CSS customizado e limpa o padding da página
    _apply_login_style() 

    # já autenticado?
    if "auth_email" in st.session_state and is_active(st.session_state["auth_email"]):
        return st.session_state["auth_email"]
    
    # 2. ESTRUTURA DE DUAS COLUNAS 50/50
    # O Streamlit só deve criar DUAS colunas aqui: col_info e col_login
    col_info, col_login = st.columns([5, 5], gap="large") 

    # ==========================================================
    # 1. COLUNA DA ESQUERDA (Informações / Benefícios)
    # ==========================================================
    with col_info:
        with col_info:
    
    # 🛑 NOVO: INÍCIO DA EXIBIÇÃO DA LOGO 🛑
    # Usamos 3 colunas para centralizar a logo dentro desta coluna maior
    # [1] = Espaço esquerdo, [2] = Logo, [1] = Espaço direito (ajuste a proporção se precisar)
    logo_col1, logo_col2, logo_col3 = st.columns([1, 2, 1])
    with logo_col2:
        # Caminho da sua logo que você enviou
        try:
            st.image(
                "logo_pi.png", 
                width=150, # Tamanho ajustado para a coluna
            )
        except Exception:
             # Fallback: Se a logo não carregar (problema de caminho), exibe um texto
             st.markdown("<h1 style='color: #00FFFF;'>π</h1>", unsafe_allow_html=True)
             
    # Adiciona um pequeno espaço para separar a logo do título
    st.markdown("<br>", unsafe_allow_html=True) 
    # 🛑 FIM DA EXIBIÇÃO DA LOGO 🛑
    
        # A. Logo e Título principal
        st.markdown(f'<h1 style="color: #FFFFFF;">π - Palpites Inteligentes</h1>', unsafe_allow_html=True)
        
        # B. Subtítulo
        st.markdown(f"""
            <p class='text-login-info'>
            Acesse as melhores análises e maximize seus resultados no mercado esportivo.
            </p>
        """, unsafe_allow_html=True)

        st.markdown("---") # Divisor sutil

        # C. Lista de Benefícios
        st.markdown("<h4>O que oferecemos:</h4>", unsafe_allow_html=True)
        _benefit_card("⚽", "Palpites inteligentes") # Ajustado
        _benefit_card("📈", "Análises em tempo real")
        _benefit_card("🛡️", "100% Seguro e Confiável")
        _benefit_card("🏆", "Estratégias otimizadas para alta performance")


    # ==========================================================
    # 2. COLUNA DA DIREITA (Formulário de Login)
    # ==========================================================
    with col_login:
        # Título do Formulário
        st.title("Acesso Restrito")
        st.subheader("Entre com suas credenciais")
        
        # ... (O restante da lógica do Formulário de Login com st.form) ...
        # (Seu código de formulário antigo deve ser mantido aqui)
        
        with st.form("login_form"):
            st.markdown("E-MAIL")
            email = st.text_input(
                label="E-mail",
                key="guard_email_input",
                label_visibility="collapsed",
                placeholder="seuemail@exemplo.com"
            )
            
            st.markdown("TOKEN")
            token = st.text_input(
                label="Seu código de acesso",
                key="guard_token_input",
                label_visibility="collapsed",
                type="password", 
                placeholder="Cole o código recebido"
            )
            
            if email:
                email = email.strip().lower()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submitted = st.form_submit_button(
                "Entrar na plataforma →", 
                type="primary", 
                use_container_width=True
            )

        # Divisor e Link Secundário
        st.markdown("""
            <div style="text-align: center; color: #555555; margin-top: 10px; margin-bottom: 10px;">
            <hr style="border: 0.5px solid #222;">
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown(
            "Não tem acesso? **[Fale com o Suporte](https://seusite.com/suporte)**", 
            unsafe_allow_html=True
        )

        # Lógica de Submissão
        if submitted:
            # ... (Sua lógica de validação aqui) ...
            if not email:
                st.error("Digite seu e-mail.")
            elif not token:
                st.error("Digite seu código de acesso.")
            else:
                try:
                    ok = validate_email_token(email, token)
                except Exception as e:
                    st.error("Erro interno ao validar token. Veja detalhes abaixo:")
                    st.exception(e)
                    ok = False

                if ok:
                    st.session_state["auth_email"] = email
                    st.success("Login realizado!")
                    st.rerun()
                else:
                    st.error("E-mail ou código inválido/expirado.")
                    
    return None
def require_login(app_name: str = "Painel", show_logo: bool = True) -> str:
    """Função principal que exige login antes de prosseguir."""
    user = st_login(app_name=app_name, show_logo=show_logo)
    if not user:
        st.stop()
    return user

def _ws():
    try:
        c = _client()
        sh = c.open(SHEET_NAME)
        ws = sh.worksheet(WORKSHEET)
        return ws
    except gspread.SpreadsheetNotFound:
        st.error(f"Planilha '{SHEET_NAME}' não encontrada (verifique nome).")
        st.stop()
    except gspread.WorksheetNotFound:
        st.error(f"Aba '{WORKSHEET}' não encontrada na planilha '{SHEET_NAME}'.")
        st.stop()
    except Exception as e:
        st.error("Erro ao abrir a worksheet.")
        st.exception(e)
        st.stop()
