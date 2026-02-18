# ui_cards_helpers.py
from __future__ import annotations

import hashlib
from typing import Any, Dict, List

import pandas as pd
import streamlit as st


# ================= CSS =================
CARD_CSS = """
<style>
:root {
  --bg-app: #050914;
  --text: #e6f6ff;
  --muted: #9fb4c8;

  --neon-cyan: #00f5ff;
  --neon-pink: #ff2d95;
  --neon-violet: #9a6bff;

  --card-bg: #0b1020;
  --card-grad-a: rgba(0,245,255,0.08);
  --card-grad-b: rgba(154,107,255,0.06);
  --card-border: rgba(0,245,255,0.25);

  --chip-bg: rgba(10, 14, 30, 0.75);
  --chip-border: rgba(0,245,255,0.25);

  --glow-strong: 0 0 16px rgba(0,245,255,0.55), 0 0 42px rgba(255,45,149,0.25);
  --glow-soft:  0 0 12px rgba(154,107,255,0.35);
  --shadow-card: 0 10px 30px rgba(0,0,0,0.45);
}

.stApp {
  background:
    radial-gradient(1200px 600px at 20% -10%, rgba(0,245,255,0.06), transparent 50%),
    radial-gradient(900px 500px at 120% 10%, rgba(255,45,149,0.05), transparent 55%),
    var(--bg-app) !important;
}
h1, h2, h3, p, .stMarkdown { color: var(--text); }

/* ======= Card ======= */
.card{
  background:
    linear-gradient(180deg, var(--card-grad-a), var(--card-grad-b)),
    var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: var(--shadow-card);
  height: 100%;
  position: relative;
  overflow: hidden;
}
.card:hover{
  border-color: rgba(255,45,149,0.45);
  box-shadow: var(--shadow-card), 0 0 22px rgba(0,245,255,0.18);
}

.card-header{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.badge{
  font-size:12px; padding:4px 10px; border-radius:999px;
  border:1px solid var(--chip-border);
  background: linear-gradient(90deg, rgba(0,245,255,0.10), rgba(154,107,255,0.08));
  color: var(--text);
}
.kickoff{ font-size:12px; color: var(--muted); }

.teams{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin:8px 0 12px; }
.team{ display:flex; align-items:center; gap:10px; min-width:0; }
.logo{
  width:30px; height:30px; border-radius:50%;
  background: radial-gradient(circle at 30% 30%, rgba(0,245,255,0.25), rgba(0,0,0,0.35));
  border:1px solid rgba(0,245,255,0.35);
  display:flex; align-items:center; justify-content:center;
  font-size:12px; color:#dffcff;
  box-shadow: var(--glow-soft);
}
.team-name{ font-weight:700; color: var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

.chips{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.chip{
  background: var(--chip-bg);
  color: var(--text);
  border: 1px solid var(--chip-border);
  border-radius: 12px;
  padding: 5px 10px;
  font-size: 12px;
  backdrop-filter: blur(6px);
}
.chip strong{ color: var(--neon-cyan); }

.footer{ display:flex; justify-content:space-between; align-items:center; margin-top:14px; }

.action, .action:link, .action:visited{
  font-size:12px;
  color:#003355 !important;
  font-weight:800;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-pink));
  padding:9px 12px;
  border-radius:12px;
  box-shadow: var(--glow-strong);
  text-decoration:none;
}

/* ===== Botão do bilhete (somente ele) ===== */
.ticket-btn-wrap div.stButton > button{
  width: auto !important;
  padding: 6px 12px !important;
  border-radius: 999px !important;
  border: 1px solid rgba(0,245,255,0.35) !important;
  background: rgba(10, 14, 30, 0.55) !important;
  color: var(--text) !important;
  font-size: 12px !important;
  box-shadow: 0 0 10px rgba(0,245,255,0.15) !important;
}
.ticket-btn-wrap div.stButton > button:hover{
  border-color: rgba(255,45,149,0.45) !important;
  box-shadow: 0 0 18px rgba(0,245,255,0.25) !important;
}
</style>
"""


# ============= Adaptadores de dados =============
TEAM_SPLIT_TOKENS = [" x ", " X ", " vs ", " VS ", " x", " vs"]


def _split_teams(jogo: str) -> tuple[str, str]:
    if not isinstance(jogo, str):
        return ("Time A", "Time B")
    for tok in TEAM_SPLIT_TOKENS:
        if tok in jogo:
            a, b = jogo.split(tok, 1)
            return a.strip(), b.strip()
    parts = jogo.split()
    mid = len(parts) // 2 or 1
    return (" ".join(parts[:mid]) or "Time A", " ".join(parts[mid:]) or "Time B")


def _safe_float(x) -> float | None:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/d"):
        return None
    s = s.replace("%", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def _ensure_dict(x) -> Dict[str, Any]:
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    if isinstance(x, (list, tuple)):
        try:
            return dict(x)
        except Exception:
            return {}
    return {"Odd": x}


def build_records_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []

    recs: List[Dict[str, Any]] = []
    for i, r in df.reset_index(drop=True).iterrows():
        jogo = r.get("Jogo") or r.get("Partida") or "Jogo sem nome"
        home, away = _split_teams(str(jogo))

        dt_raw = r.get("Data/Hora") or r.get("Data_Hora") or r.get("DataHora") or r.get("data_hora")
        kickoff_iso = ""
        if pd.notna(dt_raw):
            try:
                dt = pd.to_datetime(dt_raw)
                kickoff_iso = dt.isoformat()
            except Exception:
                kickoff_iso = ""

        conf = None
        for k in ["Confiança", "Confiança (%)", "Confianca", "confidence"]:
            if k in r and pd.notna(r[k]):
                conf = _safe_float(r[k])
                if conf is not None and conf <= 1.0:
                    conf = conf * 100.0
                break

        odd = None
        for k in ["Odd Sugerida", "Odd", "odd", "Odd_Sugerida"]:
            if k in r and pd.notna(r[k]):
                odd = _safe_float(r[k])
                if odd is None:
                    odd = str(r[k])
                break

        league = r.get("Liga") or r.get("Competição") or "—"
        rodada = r.get("Rodada") if "Rodada" in df.columns else None

        recs.append(
            {
                "id": f"df-{i}",
                "league": league,
                "round": int(rodada) if str(rodada).isdigit() else None,
                "kickoff": kickoff_iso,
                "home": home,
                "away": away,
                "pred_label": r.get("Palpite", "—"),
                "pred_probs": {},
                "odds": {"Odd": odd} if odd not in (None, "") else {},
                "status": "Agendado",
                "best_bet": r.get("Melhor Palpite", r.get("Palpite", "")),
                "confidence": (conf / 100.0) if conf is not None else None,  # 0-1
            }
        )

    return recs


def fetch_matches_api_football(api_fixtures: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    if not api_fixtures:
        return []
    recs: List[Dict[str, Any]] = []
    for f in api_fixtures:
        try:
            dt_iso = f.get("kickoff_iso") or pd.to_datetime(f.get("kickoff_local")).isoformat()
        except Exception:
            dt_iso = ""
        recs.append(
            {
                "id": f"fx-{f.get('fixture_id')}",
                "league": f.get("league_name", "—"),
                "round": f.get("round"),
                "kickoff": dt_iso,
                "home": f.get("home_team", "Time A"),
                "away": f.get("away_team", "Time B"),
                "pred_label": "—",
                "pred_probs": {},
                "odds": {},
                "status": f.get("status", "NS"),
                "best_bet": "",
                "confidence": None,
            }
        )
    return recs


def to_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if not df.empty:
        df["kickoff_dt"] = pd.to_datetime(df["kickoff"], errors="coerce")
        df["date"] = df["kickoff_dt"].dt.date
        df["time"] = df["kickoff_dt"].dt.strftime("%H:%M")
        for col, default in [("confidence", None), ("status", "Agendado"), ("league", "—"), ("round", None)]:
            if col not in df.columns:
                df[col] = default
    return df


def _logo_block(name: str) -> str:
    initials = "".join([w[0] for w in str(name).split()][:2]).upper() or "?"
    return f'<div class="logo" title="{name}">{initials}</div>'


def _card_html(row: pd.Series, show_ticket: bool = False) -> str:
    kickoff_dt = row.get("kickoff_dt")
    kickoff_fmt = kickoff_dt.strftime("%d/%m/%Y %H:%M") if pd.notna(kickoff_dt) else "-"

    if show_ticket:
        palpite_txt = row.get("pred_label", "-")

        conf_float = _safe_float(row.get("confidence"))
        if conf_float is None:
            conf_txt = "--"
        else:
            conf_pct = int(round(conf_float * 100)) if conf_float <= 1.0 else int(round(conf_float))
            conf_txt = f"{conf_pct}%"

        odds_dict = _ensure_dict(row.get("odds"))
        odds_dict = {k: v for k, v in odds_dict.items() if v not in (None, "", "—", "-", "nan")}
        chips_odds = ""
        if odds_dict:
            chips_odds = "".join([f'<span class="chip"><strong>{k}</strong> {v}</span>' for k, v in odds_dict.items()])

        best_bet_txt = row.get("best_bet") or row.get("pred_label") or "N/D"
        action_html = '<a href="https://pinbet.bet/cadastro?ref=_jetbet_Lsesportes&c=ia1" target="_blank" class="action">Bilhete</a>'
    else:
        palpite_txt = "🔒 Oculto"
        conf_txt = "🔒"
        chips_odds = '<span class="chip"><strong>Odd</strong> 🔒</span>'
        best_bet_txt = "🔒 Oculto"
        action_html = ""

    return f"""
      <div class="card">
        <div class="card-header">
          <span class="badge">{row.get('league','-')}</span>
          <span class="badge">Rodada {row.get('round','-') if pd.notna(row.get('round')) else '-'}</span>
          <span class="kickoff">{kickoff_fmt}</span>
        </div>

        <div class="teams">
          <div class="team">{_logo_block(row.get('home',''))}<span class="team-name">{row.get('home','')}</span></div>
          <span>vs</span>
          <div class="team">{_logo_block(row.get('away',''))}<span class="team-name">{row.get('away','')}</span></div>
        </div>

        <div class="chips">
          <span class="chip"><strong>Palpite</strong> {palpite_txt}</span>
          <span class="chip"><strong>Confiança</strong> {conf_txt}</span>
          <span class="chip"><strong>Status</strong> {row.get('status','-')}</span>
        </div>

        <div class="chips">{chips_odds}</div>

        <div class="footer">
          <small class="kickoff">Melhor aposta: <strong>{best_bet_txt}</strong></small>
          {action_html}
        </div>
      </div>
    """


def _make_card_id(row: pd.Series) -> str:
    base = (
        str(row.get("id") or "")
        + "|"
        + str(row.get("date") or "")
        + "|"
        + str(row.get("home") or "")
        + "|"
        + str(row.get("away") or "")
    )
    return hashlib.md5(base.encode("utf-8")).hexdigest()[:12]


def render_grid(df: pd.DataFrame, cols: int = 3) -> None:
    if df is None or df.empty:
        st.info("Nenhum jogo encontrado com os filtros.")
        return

    if "ticket_open" not in st.session_state:
        st.session_state.ticket_open = {}

    rows = [df.iloc[i : i + cols] for i in range(0, len(df), cols)]
    for chunk in rows:
        columns = st.columns(len(chunk))
        for col, (_, row) in zip(columns, chunk.iterrows()):
            card_id = _make_card_id(row)
            is_open = st.session_state.ticket_open.get(card_id, False)

            with col:
                st.markdown(_card_html(row, show_ticket=is_open), unsafe_allow_html=True)

                # botão pequeno, alinhado à direita
                left, right = st.columns([3, 1])
                with right:
                    st.markdown('<div class="ticket-btn-wrap">', unsafe_allow_html=True)
                    label = "🙈 Ocultar" if is_open else "👁️ Ver bilhete"
                    if st.button(label, key=f"toggle_{card_id}"):
                        st.session_state.ticket_open[card_id] = not is_open
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
