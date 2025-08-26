# guard.py — versão estável
import json, os, time, hashlib, hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

# Tenta importar Streamlit; se não estiver disponível (teste/CLI), segue sem
try:
    import streamlit as st
except Exception:
    st = None  # permite executar funções não-UI sem Streamlit

MEMBERS_FILE = os.environ.get("MEMBERS_FILE", "secure/members.json")
TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo

# ---------- Utilidades ----------
def _now():
    return datetime.now(TZ)

def _read_db() -> Dict:
    if not os.path.exists(MEMBERS_FILE):
        return {"version": 1, "updated_at": _now().isoformat(), "users": {}}
    with open(MEMBERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_db(db: Dict):
    os.makedirs(os.path.dirname(MEMBERS_FILE), exist_ok=True)
    db["updated_at"] = _now().isoformat()
    tmp = MEMBERS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MEMBERS_FILE)

def sha256_hex(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

def _parse_exp(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        # fallback YYYY-MM-DD
        return datetime.strptime(dt_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZ)

# ---------- API de membros ----------
def get_user(email: str) -> Optional[Dict]:
    db = _read_db()
    return db.get("users", {}).get(email.lower())

def is_active(email: str) -> bool:
    u = get_user(email)
    if not u:
        return False
    if u.get("status") != "active":
        return False
    exp = u.get("exp")
    if not exp:
        return False
    return _now() <= _parse_exp(exp)

def issue_token(email: str, days: int = 30) -> str:
    """Gera token simples (16 hex), salva hash + exp em members.json e retorna o token em texto puro."""
    db = _read_db()
    email = email.lower()
    users = db.setdefault("users", {})
    token_raw = hashlib.sha256(f"{email}-{time.time()}".encode()).hexdigest()[:16]
    token_hash = sha256_hex(token_raw)
    exp_dt = (_now() + timedelta(days=days)).replace(microsecond=0)
    users[email] = users.get(email, {})
    users[email].update({
        "status": "active",
        "plan": users[email].get("plan", "mensal"),
        "exp": exp_dt.isoformat(),
        "token_sha256": token_hash
    })
    _write_db(db)
    return token_raw

def revoke_user(email: str):
    db = _read_db()
    email = email.lower()
    if email in db.get("users", {}):
        db["users"][email]["status"] = "inactive"
        _write_db(db)

def validate_email_token(email: str, token_plain: str) -> bool:
    u = get_user(email)
    if not u:
        return False
    if u.get("status") != "active":
        return False
    if not token_plain or not u.get("token_sha256"):
        return False
    if not is_active(email):
        return False
    return constant_time_equal(sha256_hex(token_plain), u["token_sha256"])

# ---------- Camada Streamlit ----------
def st_login(app_name: str = "Painel", show_logo: bool = True) -> Optional[str]:
    """
    Mostra o formulário de login (email + código) e retorna o email autenticado, ou None se falhar.
    Usa st.session_state["auth_email"] para manter sessão.
    """
    if st is None:
        return None

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
                    st.success("Login realizado!")
                    # força recarregar para esconder o formulário
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
    """Força autenticação. Se não logar, st.stop(). Retorna o email autenticado ao logar."""
    if st is None:
        raise RuntimeError("Streamlit não disponível para login.")
    user = st_login(app_name=app_name, show_logo=show_logo)
    if not user:
        st.stop()
    return user
