# sheets_reader.py
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe

def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Carrega o DataFrame de palpites processados do Google Sheets (Modo Inverso)."""
    
    st.session_state["sheets_error"] = None 
    
    try:
        # 1. ACESSO INVERSO: Busca a string JSON da chave simples
        json_str = st.secrets.get("gcp_service_account")
        
        if not json_str or not isinstance(json_str, str):
             # Se a chave não for encontrada como string, assume que a Secret está incorreta
             st.session_state["sheets_error"] = "Chave 'gcp_service_accountT' não encontrada ou não é uma string JSON. Verifique suas Secrets."
             return pd.DataFrame()

        # 2. Decodifica a string JSON
        import json
        try:
            creds_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            st.session_state["sheets_error"] = f"Erro ao decodificar JSON do GCP_SERVICE_ACCOUNT: {e}"
            return pd.DataFrame()

        # 3. Autenticação (continua igual)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
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
