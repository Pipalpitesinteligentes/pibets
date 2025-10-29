# ui_cards_helpers.py – helpers do layout em cards
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

# ================= CSS =================
CARD_CSS = """
<style>
:root { --card-bg:#0e1117; --card-border:#1f2937; --chip-bg:#111827; --chip-txt:#e5e7eb; --brand:#fde047; }
.card{background:var(--card-bg);border:1px solid var(--card-border);border-radius:16px;padding:16px;
      box-shadow:0 6px 18px rgba(0,0,0,.25);transition:transform .12s, box-shadow .12s;height:100%}
.card:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(0,0,0,.35)}
.card-header{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.badge{font-size:12px;padding:4px 8px;border-radius:999px;border:1px solid #374151;background:#111827;color:#e5e7eb}
.kickoff{font-size:12px;color:#9ca3af}
.teams{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:6px 0 10px}
.team{display:flex;align-items:center;gap:8px;min-width:0}
.logo{width:28px;height:28px;border-radius:50%;background:#1f2937;display:flex;align-items:center;justify-content:center;
      font-size:12px;color:#e5e7eb;border:1px solid #374151}
.team-name{font-weight:600;color:#e5e7eb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pred{margin-top:6px}
.pred-row{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#e5e7eb}
.progress{width:100%;height:7px;background:#111827;border-radius:999px;overflow:hidden;margin:6px 0 2px;border:1px solid #1f2937}
.bar{height:100%;background:linear-gradient(90deg,#fde047,#22c55e)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{background:var(--chip-bg);color:var(--chip-txt);border:1px solid #374151;border-radius:12px;padding:4px 8px;font-size:12px}
.chip strong{color:#fde047}
.footer{display:flex;justify-content:space-between;align-items:center;margin-top:12px}
.action{font-size:12px;color:#111827;background:var(--brand);border:none;padding:8px 10px;border-radius:10px;cursor:pointer;font-weight:700}
.action:hover{filter:brightness(.95)}
.block-container{padding-top:1.5rem}
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
