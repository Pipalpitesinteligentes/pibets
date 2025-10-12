# sheets_reader.py
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe

# Note: As credenciais (st.secrets) serão lidas do app_merged.py
# O cache foi removido como você testou, para evitar conflitos de nomes.

def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Carrega o DataFrame de palpites processados do Google Sheets."""
    
    try:
        # Reconstroi o dicionário de credenciais usando as chaves de nível superior
        credentials_info = {
            "type": st.secrets.get("type"),
            "project_id": st.secrets.get("project_id"),
            "private_key": st.secrets.get("private_key"), 
            "client_email": st.secrets.get("client_email"),
            "token_uri": st.secrets.get("token_uri")
        }
        
        if not credentials_info.get("client_email"):
            # st.error já estará no app, aqui apenas retorna o vazio
            return pd.DataFrame() 
            
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)
        gc = gspread.authorize(creds)
        
        # 3. Abre a planilha
        sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # 4. Converte para DataFrame
        df = get_as_dataframe(sheet, evaluate_formulas=True, header=1).dropna(how="all")
        
        # Adicione uma verificação de colunas para garantir que o DataFrame está OK
        if df.empty:
            return pd.DataFrame()
            
        # Limpezas/conversões que você faz (se houver)
        # Ex: df['Data/Hora'] = pd.to_datetime(df['Data/Hora'])
        
        return df

    except Exception as e:
        # A exceção será capturada no app_merged.py para exibir o erro
        st.session_state["sheets_error"] = str(e)
        return pd.DataFrame()
