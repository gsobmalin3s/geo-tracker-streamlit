# Final corrected version with fully valid f-string for client info block
final_file_cleaned = "/mnt/data/geo_tracker_app_FINAL_STRING_CLEAN.py"

fixed_code_final = """\
import streamlit as st
import openai
import pandas as pd
import datetime
import plotly.express as px

st.set_page_config(page_title="GEO Tracker PRO", layout="wide")

# --- ESTILOS ---
st.markdown(\"\"\"
    <style>
        html, body {
            background-color: #0f1117;
            color: #f0f2f6;
            font-family: 'Segoe UI', sans-serif;
        }
        .stButton>button {
            background-color: #4e8cff;
            color: white;
            padding: 0.4rem 1.2rem;
            border: none;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        input, textarea {
            background-color: #1c1f26 !important;
            color: white !important;
        }
    </style>
\"\"\", unsafe_allow_html=True)

# --- GESTIÓN DE CLIENTES ---
st.sidebar.image("assets/logo-lin3s.jpg", width=160)
st.sidebar.markdown("### 👥 Cliente")

if "clients" not in st.session_state:
    st.session_state.clients = {}

client_options = list(st.session_state.clients.keys())
selected_client = st.sidebar.selectbox("Selecciona cliente", client_options + ["➕ Crear nuevo"], index=0 if client_options else len(client_options))

if selected_client == "➕ Crear nuevo":
    new_name = st.sidebar.text_input("Nombre de la marca")
    new_domain = st.sidebar.text_input("Dominio")
    new_sector = st.sidebar.text_input("Sector")
    new_desc = st.sidebar.text_area("Descripción breve")
    new_api = st.sidebar.text_input("🔑 API Key OpenAI", type="password")
    if st.sidebar.button("Crear cliente") and new_name:
        favicon_url = f"https://www.google.com/s2/favicons?domain={new_domain}"
        st.session_state.clients[new_name] = {
            "brand": new_name,
            "domain": new_domain,
            "sector": new_sector,
            "description": new_desc,
            "api_key": new_api,
            "favicon": favicon_url,
            "prompts": ["" for _ in range(10)],
            "results": []
        }
        selected_client = new_name

if selected_client not in st.session_state.clients:
    st.stop()

client = st.session_state.clients[selected_client]

# --- PERFIL DEL CLIENTE ---
st.markdown(f"**Dominio:** {client['domain']}\\n\\n**Sector:** {client['sector']}\\n\\n**Descripción:** {client['description']}")
"""

with open(final_file_cleaned, "w") as f:
    f.write(fixed_code_final)

final_file_cleaned
