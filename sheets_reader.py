# sheets_reader.py
import pandas as pd
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe

# ⚠️ Usamos o cache para evitar chamadas repetitivas à API do Sheets
@st.cache_data(ttl=60)
def read_palpites_from_sheets(spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """Carrega o DataFrame de palpites processados do Google Sheets."""
    
    # Limpa o erro anterior antes de tentar novamente
    st.session_state["sheets_error"] = None 
    
    try:
        # 1. ACESSO CORRETO: Busca o dicionário de credenciais 'gcp_service_account'
        # Se a chave for complexa, st.secrets pode retornar um dicionário.
        # Se você está usando o método Service Account, ele deve estar sob essa chave.
        creds_dict = st.secrets.get("gcp_service_account")
        
        if not creds_dict or not isinstance(creds_dict, dict):
             # Define o erro para ser capturado no app_merged.py
             st.session_state["sheets_error"] = "Chave 'gcp_service_account' não encontrada ou formatada incorretamente nas Streamlit Secrets."
             return pd.DataFrame()
        
        # 2. Autenticação (usando o método gspread/oauth2client)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Usa o dicionário LIDO da Secret para autenticar
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
