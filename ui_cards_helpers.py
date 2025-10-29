# ui_cards_helpers.py – helpers do layout em cards
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

# ================= CSS =================
CARD_CSS = """
<style>
/* ======= NEON FUTURISTA THEME ======= */
:root {
  --bg-app: #050914;
  --text: #e6f6ff;
  --muted: #9fb4c8;

  --neon-cyan: #00f5ff;
  --neon-pink: #ff2d95;
  --neon-violet: #9a6bff;
  --neon-lime: #b6ff00;

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

/* Fundo geral do app (pode sobrepor o HIDE_TOOLBAR do app.py) */
.stApp { background: radial-gradient(1200px 600px at 20% -10%, rgba(0,245,255,0.06), transparent 50%),
                         radial-gradient(900px 500px at 120% 10%, rgba(255,45,149,0.05), transparent 55%),
                         var(--bg-app) !important; }
h1, h2, h3, p, .stMarkdown { color: var(--text); }

/* ======= Card ======= */
.card {
  background:
    linear-gradient(180deg, var(--card-grad-a), var(--card-grad-b)),
    var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: var(--shadow-card);
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
  height: 100%;
  position: relative;
  overflow: hidden;
}
.card::after {
  content: "";
  position: absolute; inset: -1px;
  border-radius: 18px;
  pointer-events: none;
  box-shadow: inset 0 0 22px rgba(0,245,255,0.08);
}
.card:hover {
  transform: translateY(-2px);
  border-color: rgba(255,45,149,0.45);
  box-shadow: var(--shadow-card), 0 0 22px rgba(0,245,255,0.18);
}

/* ======= Header do card ======= */
.card-header { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.badge {
  font-size:12px; padding:4px 10px; border-radius:999px;
  border:1px solid var(--chip-border);
  background: linear-gradient(90deg, rgba(0,245,255,0.10), rgba(154,107,255,0.08));
  color: var(--text);
  text-shadow: 0 0 6px rgba(0,245,255,0.35);
}
.kickoff { font-size:12px; color: var(--muted); }

/* ======= Times ======= */
.teams { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:8px 0 12px; }
.team { display:flex; align-items:center; gap:10px; min-width:0; }
.logo {
  width:30px; height:30px; border-radius:50%;
  background: radial-gradient(circle at 30% 30%, rgba(0,245,255,0.25), rgba(0,0,0,0.35));
  border:1px solid rgba(0,245,255,0.35);
  display:flex; align-items:center; justify-content:center;
  font-size:12px; color:#dffcff; letter-spacing:.5px;
  box-shadow: var(--glow-soft);
}
.team-name { font-weight:700; color: var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }

/* ======= Chips / métricas ======= */
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.chip {
  background: var(--chip-bg);
  color: var(--text);
  border: 1px solid var(--chip-border);
  border-radius: 12px;
  padding: 5px 10px;
  font-size: 12px;
  backdrop-filter: blur(6px);
  box-shadow: 0 0 0 0 rgba(0,0,0,0);
  transition: box-shadow .15s ease, transform .12s ease;
}
.chip strong { color: var(--neon-cyan); text-shadow: 0 0 8px rgba(0,245,255,0.6); }
.chip:hover { transform: translateY(-1px); box-shadow: var(--glow-soft); }

/* ======= Barras de probabilidade ======= */
.pred { margin-top:8px; }
.pred-row{ display:flex; align-items:center; justify-content:space-between; font-size:12px; color: var(--text); }
.progress{
  width:100%; height:8px; background:rgba(0,245,255,0.08);
  border-radius:999px; overflow:hidden; margin:6px 0 2px;
  border:1px solid rgba(0,245,255,0.25);
}
.bar{
  height:100%;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-violet), var(--neon-pink));
  box-shadow: 0 0 18px rgba(0,245,255,0.55);
}

/* ======= Rodapé / botão ======= */
.footer{ display:flex; justify-content:space-between; align-items:center; margin-top:14px; }
.action{
  font-size:12px; color:#0b1020; font-weight:800; letter-spacing:.2px;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-pink));
  border:none; padding:9px 12px; border-radius:12px; cursor:pointer;
  box-shadow: var(--glow-strong);
  transition: transform .1s ease, filter .15s ease, box-shadow .15s ease;
}
.action:hover{ transform: translateY(-1px); filter:brightness(1.05); box-shadow: var(--glow-strong), 0 0 30px rgba(154,107,255,0.25); }

/* ======= Ajustes gerais ======= */
.block-container{ padding-top: 1.2rem; }
</style>
"""

# ============= Adaptadores de dados =============
TEAM_SPLIT_TOKENS = [" x ", " X ", " vs ", " VS ", " x", " vs"]

def _split_teams(jogo: str) -> tuple[str, str]:
    if not isinstance(jogo, str): return ("Time A", "Time B")
    for tok in TEAM_SPLIT_TOKENS:
        if tok in jogo:
            a, b = jogo.split(tok, 1)
            return a.strip(), b.strip()
    parts = jogo.split(); mid = len(parts)//2 or 1
    return (" ".join(parts[:mid]) or "Time A", " ".join(parts[mid:]) or "Time B")

def build_records_from_df(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty: return []
    recs: List[Dict[str, Any]] = []
    for i, r in df.reset_index(drop=True).iterrows():
        jogo = r.get('Jogo') or r.get('Partida') or 'Jogo sem nome'
        home, away = _split_teams(str(jogo))
        # data/hora
        dt_raw = r.get('Data/Hora') or r.get('Data_Hora') or r.get('DataHora') or r.get('data_hora')
        kickoff_iso = ''
        if pd.notna(dt_raw):
            try:
                dt = pd.to_datetime(dt_raw)
                kickoff_iso = dt.isoformat()
            except Exception:
                kickoff_iso = ''
        # confiança
        conf = None
        for k in ['Confiança', 'Confiança (%)', 'Confianca', 'confidence']:
            if k in r and pd.notna(r[k]):
                try:
                    v = float(r[k]); conf = v*100 if v <= 1 else v
                except Exception: pass
                break
        # odd
        odd = None
        for k in ['Odd Sugerida', 'Odd', 'odd', 'Odd_Sugerida']:
            if k in r and pd.notna(r[k]):
                try: odd = float(r[k])
                except Exception: odd = str(r[k])
                break
        league = r.get('Liga') or r.get('Competição') or '—'
        rodada = r.get('Rodada') if 'Rodada' in df.columns else None
        recs.append({
            'id': f'df-{i}',
            'league': league,
            'round': int(rodada) if str(rodada).isdigit() else None,
            'kickoff': kickoff_iso,
            'home': home, 'away': away,
            'pred_label': r.get('Palpite', '—'),
            'pred_probs': {},
            'odds': ({'Odd': odd} if odd else {}),
            'status': 'Agendado',
            'best_bet': r.get('Melhor Palpite', r.get('Palpite', '')),
            'confidence': (conf/100.0) if conf is not None else None,
        })
    return recs

def fetch_matches_api_football(api_fixtures: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    if not api_fixtures: return []
    recs: List[Dict[str, Any]] = []
    for f in api_fixtures:
        try: dt_iso = f.get('kickoff_iso') or pd.to_datetime(f.get('kickoff_local')).isoformat()
        except Exception: dt_iso = ''
        recs.append({
            'id': f"fx-{f.get('fixture_id')}",
            'league': f.get('league_name', '—'),
            'round': f.get('round'),
            'kickoff': dt_iso,
            'home': f.get('home_team', 'Time A'),
            'away': f.get('away_team', 'Time B'),
            'pred_label': '—',
            'pred_probs': {},
            'odds': {},
            'status': f.get('status', 'NS'),
            'best_bet': '',
            'confidence': None,
        })
    return recs

# ============= Renderização =============
def to_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if not df.empty:
        df["kickoff_dt"] = pd.to_datetime(df["kickoff"], errors="coerce")
        df["date"] = df["kickoff_dt"].dt.date
        df["time"] = df["kickoff_dt"].dt.strftime("%H:%M")
        for col, default in [("confidence", None), ("status", "Agendado"),
                             ("league", "—"), ("round", None)]:
            if col not in df.columns: df[col] = default
    return df

def _prob_bar_html(label: str, p: float) -> str:
    pct = int(round(float(p) * 100))
    return f"""
      <div class="pred">
        <div class="pred-row"><span>{label}</span><span>{pct}%</span></div>
        <div class="progress"><div class="bar" style="width:{pct}%;"></div></div>
      </div>
    """

def _logo_block(name: str) -> str:
    initials = "".join([w[0] for w in name.split()][:2]).upper() or "?"
    return f'<div class="logo" title="{name}">{initials}</div>'

def _card_html(row: pd.Series) -> str:
    kickoff_fmt = row["kickoff_dt"].strftime("%d/%m/%Y %H:%M") if pd.notna(row["kickoff_dt"]) else "-"
    conf_pct = int(round(float(row.get("confidence") or 0) * 100)) if row.get("confidence") is not None else 0
    probs_html = "".join(_prob_bar_html(k, float(v)) for k, v in (row.get("pred_probs") or {}).items())
    chips = "".join([f'<span class="chip"><strong>{k}</strong> {v}</span>' for k, v in (row.get("odds") or {}).items()])
    return f"""
      <div class="card">
        <div class="card-header">
          <span class="badge">{row.get('league','-')}</span>
          <span class="badge">Rodada {row.get('round','-') if pd.notna(row.get('round')) else '-'}</span>
          <span class="kickoff">{kickoff_fmt}</span>
        </div>
        <div class="teams">
          <div class="team">{_logo_block(row['home'])}<span class="team-name">{row['home']}</span></div>
          <span>vs</span>
          <div class="team">{_logo_block(row['away'])}<span class="team-name">{row['away']}</span></div>
        </div>
        <div class="chips">
          <span class="chip"><strong>Palpite</strong> {row.get('pred_label','-')}</span>
          <span class="chip"><strong>Confiança</strong> {conf_pct}%</span>
          <span class="chip"><strong>Status</strong> {row.get('status','-')}</span>
        </div>
        {probs_html}
        <div class="chips">{chips}</div>
        <div class="footer">
          <small class="kickoff">Melhor aposta: {row.get('best_bet','-')}</small>
          <button class="action" onclick="window.parent.postMessage({{type:'select_game', id:'{row.get('id','')}' }}, '*')">Detalhes</button>
        </div>
      </div>
    """

def render_grid(df: pd.DataFrame, cols: int = 3):
    if df.empty:
        st.info("Nenhum jogo encontrado com os filtros.")
        return
    rows = [df.iloc[i:i+cols] for i in range(0, len(df), cols)]
    for chunk in rows:
        columns = st.columns(len(chunk))
        for col, (_, row) in zip(columns, chunk.iterrows()):
            with col:
                st.markdown(_card_html(row), unsafe_allow_html=True)
