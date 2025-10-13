# sheets_reader.py
import pandas as pd
import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials
import json

# ==========================================================
# 🔐 Função para ler credenciais corretamente
# ==========================================================
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


# ==========================================================
# 📊 Leitura e tratamento da planilha
# ==========================================================
def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Carrega o DataFrame de palpites processados do Google Sheets."""
    st.session_state["sheets_error"] = None

    try:
        creds_dict = _get_sheets_client()
        if not creds_dict:
            st.session_state["sheets_error"] = (
                "⚠️ Credenciais inválidas. Verifique o formato de 'gcp_service_account' "
                "ou 'GCP_SERVICE_ACCOUNT' nas Secrets do Streamlit."
            )
            return pd.DataFrame()

        # Autenticação
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)

        # Abre a planilha e aba
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=0).dropna(how="all")

        if df.empty:
            st.session_state["sheets_error"] = (
                f"⚠️ A aba '{sheet_name}' está vazia ou sem dados."
            )
            return pd.DataFrame()

        # ==========================================================
        # 🧹 Limpeza e normalização de colunas
        # ==========================================================
        df.columns = df.columns.astype(str).str.strip()

        renames = {
            'Data/Hora': 'Data_Hora',
            'Odd Sugerida': 'Odd_Sugerida',
            'Confiança': 'Confianca',
            'Liga': 'Liga',
            'Jogo': 'Jogo',
            'Palpite': 'Palpite'
        }
        df = df.rename(columns={k: v for k, v in renames.items() if k in df.columns})

        # ==========================================================
        # 🕒 Conversões e formatações
        # ==========================================================
        if 'Data_Hora' in df.columns:
            df['Data_Hora'] = pd.to_datetime(df['Data_Hora'], errors='coerce')

        # --- Converte Confiança ---
        if 'Confianca' in df.columns:
            df['Confianca'] = (
                df['Confianca']
                .astype(str)
                .str.replace(',', '.', regex=False)
                .str.replace(r'[^\d\.]', '', regex=True)
            )
            df['Confianca'] = pd.to_numeric(df['Confianca'], errors='coerce')
        else:
            df['Confianca'] = None

        # --- Converte Odd Sugerida ---
        if 'Odd_Sugerida' in df.columns:
            df['Odd_Sugerida'] = (
                df['Odd_Sugerida']
                .astype(str)
                .str.replace(',', '.', regex=False)
                .str.replace(r'[^\d\.]', '', regex=True)
            )
            df['Odd_Sugerida'] = pd.to_numeric(df['Odd_Sugerida'], errors='coerce')
        else:
            df['Odd_Sugerida'] = None

        # ==========================================================
        # ✨ Colunas formatadas para exibição
        # ==========================================================
        df['Confianca_display'] = df['Confianca'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D"
        )
        df['Odd_display'] = df['Odd_Sugerida'].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "N/D"
        )

        # ==========================================================
        # 🚫 Remove linhas inválidas
        # ==========================================================
        if 'Jogo' in df.columns and 'Palpite' in df.columns:
            df = df.dropna(subset=['Jogo', 'Palpite']).reset_index(drop=True)
        else:
            st.session_state["sheets_error"] = (
                "⚠️ Colunas essenciais ('Jogo' e 'Palpite') não encontradas."
            )
            return pd.DataFrame()

        return df

    except Exception as e:
        st.session_state["sheets_error"] = f"❌ Erro ao conectar/ler Sheets: {type(e).__name__}: {str(e)}"
        return pd.DataFrame()
