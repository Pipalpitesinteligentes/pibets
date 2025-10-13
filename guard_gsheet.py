import os
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials # Importada no topo

# --- CONFIGURAÇÃO E CONSTANTES ---
TZ = timezone(timedelta(hours=-3)) # America/Sao_Paulo
SHEET_NAME = os.environ.get("MEMBERS_SHEET_NAME", "members")      # nome da planilha
WORKSHEET = os.environ.get("MEMBERS_WORKSHEET_NAME", "usuarios")  # aba

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

# --- GOOGLE SHEETS AUTHENTICATION ---
def _get_creds_dict():
    """Tenta obter o dicionário de credenciais em vários formatos."""
    
    # 1. Tenta o formato padrão TOML: [gcp_service_account]
    creds_dict = st.secrets.get("gcp_service_account")
    
    # 2. Se não for um dicionário válido, tenta a string simples (GCP_SERVICE_ACCOUNT)
    if not isinstance(creds_dict, dict) or not creds_dict:
        json_str = st.secrets.get("GCP_SERVICE_ACCOUNT")
        if isinstance(json_str, str) and json_str.strip().startswith("{"):
            try:
                # Decodifica a string JSON
                creds_dict = json.loads(json_str)
            except Exception:
                # Falha silenciosa no JSON, prossegue para o erro abaixo
                pass 
    
    # Retorna o dicionário se for válido
    return creds_dict if isinstance(creds_dict, dict) and creds_dict else None


def _client():
    """Autentica com o Google Sheets e retorna o cliente gspread."""
    creds_dict = _get_creds_dict()
    
    if not creds_dict:
        st.error("Erro Crítico de Secret: Chave GCP de Login não encontrada. Verifique as Secrets.")
        st.stop()
        
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Usa as credenciais importadas no topo
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope) 
        return gspread.authorize(creds)
    except Exception as e:
        # Erros de permissão, chave inválida, etc.
        st.error(f"Erro Crítico de Conexão: Não foi possível acessar o Google Sheets. {type(e).__name__}: {str(e)}")
        st.stop()
        
def _ws():
    """Retorna a aba 'usuarios' da planilha de membros."""
    c = _client()
    sh = c.open(SHEET_NAME)
    return sh.worksheet(WORKSHEET)

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

# ---------- UI ----------
def st_login(app_name: str = "Painel", show_logo: bool = True):
    """Exibe o formulário de login e verifica a sessão."""
    # já autenticado?
    if "auth_email" in st.session_state and is_active(st.session_state["auth_email"]):
        return st.session_state["auth_email"]

    with st.container():
        if show_logo:
            st.markdown("### 🔐 Acesso ao " + app_name)
        email = st.text_input("E-mail", key="guard_email", placeholder="seuemail@exemplo.com").strip().lower()
        token = st.text_input("Seu código de acesso", key="guard_token", type="password", placeholder="Cole o código recebido")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Entrar", key="guard_btn_enter"):
                if validate_email_token(email, token):
                    st.session_state["auth_email"] = email
                    st.success("Login realizado! Recarregando...")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                else:
                    st.error("E-mail ou código inválido/expirado.")
        with col2:
            if st.button("Esqueci meu código", key="guard_btn_forgot"):
                st.info("Fale com o suporte para receber um novo código.")
    return None

def require_login(app_name: str = "Painel", show_logo: bool = True) -> str:
    """Função principal que exige login antes de prosseguir."""
    user = st_login(app_name=app_name, show_logo=show_logo)
    if not user:
        st.stop()
    return user
