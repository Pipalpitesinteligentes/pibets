# login_gcp.py - Versão Mínima de Autenticação e Login

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import hmac

# --- CONFIGURAÇÃO ---
SHEET_NAME = os.environ.get("MEMBERS_SHEET_NAME", "members") 
WORKSHEET = os.environ.get("MEMBERS_WORKSHEET_NAME", "usuarios") 

def _get_creds_dict():
    """Tenta obter o dicionário de credenciais de ambos os formatos (TOML ou String)."""
    
    # 1. Tenta o formato padrão TOML: [gcp_service_account] (Deve falhar, mas é um bom fallback)
    creds_dict = st.secrets.get("gcp_service_account")
    
   # 2. Tenta a string simples (GCP_SERVICE_ACCOUNT) <--- FOCO AQUI
    if not isinstance(creds_dict, dict) or not creds_dict:
        json_str = st.secrets.get("GCP_SERVICE_ACCOUNT")
        if isinstance(json_str, str) and json_str.strip().startswith("{"):
            import json # Certifique-se de que o import json está no topo!
            try:
                creds_dict = json.loads(json_str)
            except Exception:
                return None 

    # Retorna o dicionário, se for válido
    return creds_dict if isinstance(creds_dict, dict) and creds_dict else None

def _get_worksheet():
    """Autentica e retorna a aba 'usuarios'."""
    
    creds_dict = _get_creds_dict()
    
    if not creds_dict:
        st.error("Erro Crítico de Secret: Chave GCP de Login não encontrada. Verifique as Secrets.")
        st.stop()
        
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope) 
        gc = gspread.authorize(creds)
        
        sh = gc.open(SHEET_NAME)
        return sh.worksheet(WORKSHEET)

    except Exception as e:
        # Erro de permissão ou chave inválida
        st.error(f"Erro Crítico de Conexão: Não foi possível acessar o Google Sheets. {type(e).__name__}: {str(e)}")
        st.stop()


def validate_email_token(email: str, token_plain: str) -> bool:
    """Validação básica simulada (apenas para teste de conexão)."""
    try:
        ws = _get_worksheet()
        # Assume que a coluna 1 (índice 0) é o email, e a coluna 5 (índice 4) é o hash do token
        records = ws.get_all_records()
        
        for record in records:
            if record.get('email', '').strip().lower() == email.strip().lower():
                # Hash simples para demonstração
                stored_hash = record.get('token_sha256', '') 
                
                # Simula a verificação de hash para evitar timing attacks
                expected_hash = hashlib.sha256(token_plain.encode("utf-8")).hexdigest()
                return hmac.compare_digest(expected_hash, stored_hash)

        return False

    except Exception as e:
        st.error(f"Erro durante a validação de token: {e}")
        return False

# --- FUNÇÃO DE ENTRADA DO STREAMLIT ---
def require_login(app_name: str = "Painel", show_logo: bool = True) -> str:
    # 1. Tenta se já está logado na session state (SIMULADO)
    if "auth_email" in st.session_state:
         # OBS: O is_active() não está aqui, então confiaremos na session_state
         return st.session_state["auth_email"] 

    # 2. Mostra o formulário de login
    with st.container():
        if show_logo:
            st.markdown("### 🔐 Acesso ao " + app_name)
        
        email = st.text_input("E-mail", key="new_guard_email", placeholder="seuemail@exemplo.com").strip().lower()
        token = st.text_input("Seu código de acesso", key="new_guard_token", type="password", placeholder="Cole o código recebido")
        
        if st.button("Entrar", key="new_guard_btn_enter"):
            if validate_email_token(email, token):
                st.session_state["auth_email"] = email
                st.success("Login realizado! Por favor, recarregue a página.")
                st.rerun()
            else:
                st.error("E-mail ou código inválido/expirado.")
                
    st.stop()
