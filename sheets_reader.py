# sheets_reader.py (TOPO)
import pandas as pd
import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
# Importe o módulo correto do Google:
from google.oauth2.service_account import Credentials 
# Use o import do JSON (se for usar o formato string)
import json 

# sheets_reader.py (NOVA FUNÇÃO COMPLETA)

def _get_sheets_client():
    """Tenta obter o dicionário de credenciais em vários formatos."""
    
    # 1. Tenta o formato padrão do Streamlit (seção [gcp_service_account])
    creds_dict = st.secrets.get("gcp_service_account")
    
    # 2. Se não for dicionário ou estiver vazio, tenta a string JSON simples
    if not isinstance(creds_dict, dict) or not creds_dict:
        json_str = st.secrets.get("GCP_SERVICE_ACCOUNT")
        
        if isinstance(json_str, str) and json_str.strip().startswith("{"):
            try:
                # Tenta decodificar a string JSON
                creds_dict = json.loads(json_str)
            except Exception:
                return None # Falha na decodificação

    # Retorna o dicionário, se for válido
    return creds_dict if isinstance(creds_dict, dict) and creds_dict else None


def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Carrega o DataFrame de palpites processados do Google Sheets."""
    
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
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # Converte para DataFrame
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=1).dropna(how="all")

        if df.empty:
             st.session_state["sheets_error"] = f"Planilha lida, mas a aba '{sheet_name}' está vazia ou sem dados."
             return pd.DataFrame()
        
        # Limpeza e Conversão
        if 'Data/Hora' in df.columns:
             df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        
        # Filtra linhas sem dados essenciais
        return df.dropna(subset=['Jogo', 'Palpite']).reset_index(drop=True)

    except Exception as e:
        # Erros como permissão negada, ID errado, ou credenciais inválidas.
        st.session_state["sheets_error"] = f"Erro ao conectar/ler Sheets: {type(e).__name__}: {str(e)}"
        return pd.DataFrame()
        
        # Abre a planilha e a aba
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # Converte para DataFrame
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=1).dropna(how="all")
        
        if df.empty:
             st.session_state["sheets_error"] = f"Planilha lida, mas a aba '{sheet_name}' está vazia ou sem dados."
             return pd.DataFrame()
        
        # Limpeza e Conversão
        if 'Data/Hora' in df.columns:
             df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        
        # Filtra linhas sem dados essenciais
        return df.dropna(subset=['Jogo', 'Palpite']).reset_index(drop=True)

    except Exception as e:
        # Erros como permissão negada, ID errado, ou credenciais inválidas.
        st.session_state["sheets_error"] = f"Erro ao conectar/ler Sheets: {type(e).__name__}: {str(e)}"
        return pd.DataFrame()
