import pandas as pd
import streamlit as st
import gspread
from gspread_dataframe import get_as_dataframe
from google.oauth2.service_account import Credentials

ddef read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    # ...
    json_str = st.secrets.get("GCP_SERVICE_ACCOUNT")
    
    if not isinstance(json_str, str) or not json_str.strip().startswith("{"):
         st.session_state["sheets_error"] = "Chave 'GCP_SERVICE_ACCOUNT' não encontrada ou formatada incorretamente (esperado string JSON)."
         return pd.DataFrame()

    import json
    try:
         creds_dict = json.loads(json_str)
    except json.JSONDecodeError as e:
         st.session_state["sheets_error"] = f"Erro ao decodificar JSON do GCP_SERVICE_ACCOUNT: {e}"
         return pd.DataFrame()
    
    # O resto da autenticação continua igual
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    gc = gspread.authorize(creds)
        # 3. Abre a planilha e a aba
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # 4. Converte para DataFrame
        # Passar 'header=1' garante que a primeira linha (cabeçalho) seja usada.
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=1).dropna(how="all")
        
        if df.empty:
            st.session_state["sheets_error"] = f"Planilha lida, mas a aba '{sheet_name}' está vazia ou sem dados."
            return pd.DataFrame()
        
        # 5. Limpeza e Conversão (Exemplo)
        if 'Data/Hora' in df.columns:
            # Garante que a coluna de data é tratada corretamente
            df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        
        # Filtra linhas sem dados essenciais
        return df.dropna(subset=['Jogo', 'Palpite']).reset_index(drop=True)

    except Exception as e:
        # Erros como permissão negada, ID errado, ou credenciais inválidas.
        st.session_state["sheets_error"] = f"Erro ao conectar/ler Sheets: {type(e).__name__}: {str(e)}"
        return pd.DataFrame()
