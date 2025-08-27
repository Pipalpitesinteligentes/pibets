# guard_gsheet.py — usa Google Sheets como storage
import os, time, hashlib, hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

TZ = timezone(timedelta(hours=-3))  # America/Sao_Paulo
SHEET_NAME = os.environ.get("MEMBERS_SHEET_NAME", "members")       # nome da planilha
WORKSHEET = os.environ.get("MEMBERS_WORKSHEET_NAME", "usuarios")   # aba

def _now():
    return datetime.now(TZ)

def sha256_hex(x: str) -> str:
    import hashlib
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

def _client():
    creds_dict = st.secrets["GCP_SERVICE_ACCOUNT"]
    if isinstance(creds_dict, str):
        import json
        creds_dict = json.loads(creds_dict)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def _ws():
    c = _client()
    sh = c.open(SHEET_NAME)
    return sh.worksheet(WORKSHEET)

def _rows() -> List[List[str]]:
    ws = _ws()
    # header na linha 1: email | status | plan | exp | token_sha256 | updated_at
    vals = ws.get_all_values()
    return vals

def _find_row_index(email: str) -> Optional[int]:
    vals = _rows()
    for idx, row in enumerate(vals[1:], start=2):
        if len(row) > 0 and row[0].strip().lower() == email.strip().lower():
            return idx
    return None

def get_user(email: str) -> Optional[Dict]:
    vals = _rows()
    for row in vals[1:]:
        if len(row) < 1:
            continue
        if row[0].strip().lower() == email.strip().lower():
            # mapeia colunas
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
    u = get_user(email)
    if not u: return False
    if u.get("status") != "active": return False
    exp = u.get("exp")
    if not exp: return False
    try:
        dt = datetime.fromisoformat(exp)
    except Exception:
        try:
            dt = datetime.strptime(exp, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=TZ)
        except Exception:
            return False
    return _now() <= dt

def _upsert(email: str, status: str, plan: str, exp_iso: str, token_sha256: str):
    ws = _ws()
    row_idx = _find_row_index(email)
    payload = [email.lower(), status, plan, exp_iso, token_sha256, _now().isoformat()]
    if row_idx:
        ws.update(f"A{row_idx}:F{row_idx}", [payload])
    else:
        ws.append_row(payload, value_input_option="USER_ENTERED")

def issue_token(email: str, days: int = 30, plan: str = "mensal") -> str:
    token_raw = sha256_hex(f"{email}-{time.time()}")[:16]
    token_hash = sha256_hex(token_raw)
    exp_dt = (_now() + timedelta(days=days)).replace(microsecond=0)
    _upsert(email=email, status="active", plan=plan, exp_iso=exp_dt.isoformat(), token_sha256=token_hash)
    return token_raw

def revoke_user(email: str):
    u = get_user(email)
    if not u: return
    _upsert(email=email, status="inactive", plan=u.get("plan","mensal"), exp_iso=u.get("exp",""), token_sha256=u.get("token_sha256",""))

def validate_email_token(email: str, token_plain: str) -> bool:
    u = get_user(email)
    if not u: return False
    if u.get("status") != "active": return False
    if not token_plain or not u.get("token_sha256"): return False
    if not is_active(email): return False
    return constant_time_equal(sha256_hex(token_plain), u["token_sha256"])

# ---------- UI (igual ao guard anterior) ----------
def st_login(app_name: str = "Painel", show_logo: bool = True):
    if "auth_email" in st.session_state and is_active(st.
