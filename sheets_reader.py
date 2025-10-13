# sheets_reader.py (TOPO)
import pandas as pd
import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import json
import unicodedata
# Adicione/cole no topo do sheets_reader.py
import json
import re
from json.decoder import JSONDecodeError

def _get_sheets_client():
    """
    Retorna um dict com as credenciais do service account em vários formatos possíveis.
    Tenta corrigir automaticamente strings JSON onde a private_key contém quebras de linha reais.
    """
    # Tenta as duas chaves comuns que você tem usado
    creds_raw = st.secrets.get("gcp_service_account") or st.secrets.get("GCP_SERVICE_ACCOUNT")

    # Se já é dict, devolve diretamente
    if isinstance(creds_raw, dict):
        return creds_raw if creds_raw else None

    # Se for None ou vazio
    if not creds_raw:
        return None

    # Se for string, tenter decodificar direto
    if isinstance(creds_raw, str):
        s = creds_raw.strip()

        # 1) Tentativa direta
        try:
            return json.loads(s)
        except JSONDecodeError as e:
            # 2) Tenta escapar quebras de linha reais (substitui linhas reais por \\n)
            try:
                s_fix = s.replace('\r\n', '\\n').replace('\n', '\\n')
                return json.loads(s_fix)
            except JSONDecodeError:
                pass

            # 3) Se ainda falhar, tenta extrair a chave privada e escapar apenas ela
            #    procura por "private_key": " ... "
            try:
                # tenta localizar trecho "private_key": " ... "
                m = re.search(r'"private_key"\s*:\s*"(.+?)"\s*(,|\})', s, flags=re.DOTALL)
                if m:
                    pk_raw = m.group(1)  # conteúdo entre aspas (pode ter quebras reais)
                    # Se tiver quebras de linha reais, substitui só elas
                    if '\n' in pk_raw or '\r' in pk_raw:
                        pk_fixed = pk_raw.replace('\r\n', '\\n').replace('\n', '\\n')
                        s2 = s[:m.start(1)] + pk_fixed + s[m.end(1):]
                        return json.loads(s2)
            except Exception:
                pass

    # Se nada funcionou, devolve None
    return None

def _get_sheets_client():
    """Tenta obter o dicionário de credenciais em vários formatos."""
    creds_dict = st.secrets.get("gcp_service_account")

    if not isinstance(creds_dict, dict) or not creds_dict:
        json_str = st.secrets.get("GCP_SERVICE_ACCOUNT")
        if isinstance(json_str, str) and json_str.strip().startswith("{"):
            try:
                creds_dict = json.loads(json_str)
            except Exception:
                return None

    return creds_dict if isinstance(creds_dict, dict) and creds_dict else None


def _normalize_columns(cols):
    """Retorna lista de colunas normalizadas (sem espaços/acentos e em lower)."""
    out = []
    for c in cols:
        if not isinstance(c, str):
            out.append("")  # mantém posição, evita erros
            continue
        s = c.strip()
        s = s.replace('\u200b', '')  # remove zero-width spaces se houver
        # remove acentos
        s = unicodedata.normalize('NFKD', s)
        s = s.encode('ascii', errors='ignore').decode('ascii')
        out.append(s.lower())
    return out


def _find_best_column(df, candidates):
    """
    Recebe df e uma lista de possíveis nomes (ex ['jogo','partida','match'])
    Retorna o nome real da coluna no df ou None.
    """
    norm = _normalize_columns(df.columns.tolist())
    for cand in candidates:
        cand_norm = unicodedata.normalize('NFKD', cand).encode('ascii', errors='ignore').decode('ascii').strip().lower()
        if cand_norm in norm:
            idx = norm.index(cand_norm)
            return df.columns[idx]  # devolve o nome original encontrado
    return None


def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """
    Carrega o DataFrame de palpites processados do Google Sheets.
    Substitua SPREADSHEET_ID e sheet_name ao chamar a função no app.
    """
    st.session_state["sheets_error"] = None

    try:
        creds_dict = _get_sheets_client()
        if not creds_dict:
            st.session_state["sheets_error"] = "Chave 'gcp_service_account' não encontrada ou formatada incorretamente nas Streamlit Secrets."
            return pd.DataFrame()

        # Autenticação
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)

        # Abre a planilha e a aba
        sh = gc.open_by_key(spreadsheet_id)
        sheet = sh.worksheet(sheet_name)

        # Converte para DataFrame
        # header=0 assume que a primeira linha da aba é o cabeçalho.
        # Se na sua planilha o cabeçalho estiver na segunda linha, troque para header=1.
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=0).dropna(how="all")

        # DEBUG: mostra o que veio
        st.write("Shape do df lido:", df.shape)
        st.write("Colunas originais encontradas:", df.columns.tolist())
        st.dataframe(df.head(8))

        if df.empty:
            st.session_state["sheets_error"] = f"Planilha lida, mas a aba '{sheet_name}' está vazia ou sem dados."
            return pd.DataFrame()

        # Normaliza nomes de coluna (irá usar para busca)
        # Não alteramos os nomes originais ainda, apenas usamos para procurar.
        # Procura por colunas equivalentes para 'Jogo' e 'Palpite'
        col_jogo = _find_best_column(df, ["Jogo", "jogo", "Partida", "Match", "Jogo/Time", "time"])
        col_palpite = _find_best_column(df, ["Palpite", "palpites", "Suggestion", "Suggestion", "PalpiteFinal"])

        if col_jogo is None or col_palpite is None:
            st.warning(f"Não foi possível mapear automaticamente 'Jogo' e/ou 'Palpite'. Colunas encontradas: {df.columns.tolist()}")
            # mostra sugestões simples de cols que mais se parecem
            st.info("Se as colunas existirem em outra linha de cabeçalho, tente ajustar `header=` em get_as_dataframe (0 ou 1).")
            st.session_state["sheets_error"] = "Colunas esperadas não encontradas ('Jogo' e 'Palpite')."
            return pd.DataFrame()

        # Renomeia para nomes padrão que o resto do app espera
        df = df.rename(columns={col_jogo: "Jogo", col_palpite: "Palpite"})

        # Conversões opcionais
        if 'Data/Hora' in df.columns:
            df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')

        # Filtra linhas sem dados essenciais e reseta index
        df = df.dropna(subset=['Jogo', 'Palpite']).reset_index(drop=True)

        return df

    except Exception as e:
        st.session_state["sheets_error"] = f"Erro ao conectar/ler Sheets: {type(e).__name__}: {str(e)}"
        st.error(st.session_state["sheets_error"])
        return pd.DataFrame()
