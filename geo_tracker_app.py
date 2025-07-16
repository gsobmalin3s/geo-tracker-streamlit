# geo_tracker_app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import hashlib
import json
import os
import re
from fpdf import FPDF
from io import BytesIO

# --- CONFIG GLOBAL ---
st.set_page_config(page_title="GEO Tracker PRO", layout="wide")
USER_DB = "data/users.json"
os.makedirs("data", exist_ok=True)

# --- UTILIDADES ---
def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def get_keyword_matches(text, keywords):
    text = text.lower()
    return [kw for kw in keywords if re.search(rf'\b{re.escape(kw.lower())}\b', text)]

def simulate_ai_response(prompt, model_name):
    examples = {
        "ChatGPT": f"Claro, aquí tienes una lista de los mejores servicios para {prompt}: 1. MarcaX 2. OtroServicio 3. Recomendado.net",
        "Gemini": f"Según nuestra base de datos, {prompt} se puede resolver con plataformas como MarcaX y otras opciones del mercado.",
        "Claude": f"Para {prompt}, se recomienda explorar alternativas como MarcaX. Estas ofrecen buena cobertura y experiencia."
    }
    return examples.get(model_name, f"Respuesta genérica para: {prompt}")

def simulate_recommendation(response, brand):
    if brand.lower() not in response.lower():
        return "❌ No apareces. Refuerza autoridad de marca y enlaces relevantes."
    elif "http" not in response:
        return "✅ Apareces sin enlace. Añade contenido con URLs claras en tu web."
    else:
        return "✅ Apareces con enlace. Continúa mejorando contenido útil e informacional."

def sugerir_prompts(ya_existentes, sector="educación"):
    base = {
        "educación": ["mejores universidades en línea", "cursos online gratuitos", "educación IA personalizada"],
        "salud": ["apps salud mental", "seguros de salud digitales", "terapias IA en salud"],
        "legal": ["abogados digitales", "consultas legales gratis", "servicios legales IA"],
        "ecommerce": ["mejores tiendas de electrónica", "alternativas Amazon", "comprar sin registro"]
    }
    todos = base.get(sector.lower(), [])
    return [p for p in todos if p not in ya_existentes][:5]

def generar_pdf_informe(df, brand, conclusion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title(f"Informe IA – {brand}")
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, txt=f"Informe de Visibilidad – {brand}", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.ln(10)
    for i, row in df.iterrows():
        pdf.multi_cell(0, 6, f"Prompt: {row['prompt']}\n"
                             f"Mención: {'Sí' if row['mention'] else 'No'}\n"
                             f"Enlace: {'Sí' if row['link'] else 'No'}\n"
                             f"Palabras clave: {', '.join(row['matched_keywords'])}\n"
                             f"Posición: {row['position'] or '—'}\n"
                             f"Recomendación: {row['recommendation']}\n"
                             f"{'-'*50}")
    pdf.ln(8)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 10, "Conclusión general:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, conclusion)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# --- AUTENTICACIÓN ---
def login_screen():
    st.title("🔐 GEO Tracker PRO")
    tab_login, tab_register = st.tabs(["Iniciar sesión", "Registrarse"])
    users = load_users()

    with tab_login:
        username = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            if username in users and verify_password(password, users[username]["password"]):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"¡Bienvenido, {username}!")
                st.experimental_set_query_params(page="dashboard")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    with tab_register:
        new_user = st.text_input("Email de registro")
        new_pass = st.text_input("Nueva contraseña", type="password")
        if st.button("Crear cuenta"):
            if new_user in users:
                st.warning("Ese usuario ya existe.")
            elif not new_user or not new_pass:
                st.warning("Rellena ambos campos.")
            else:
                users[new_user] = {
                    "password": hash_password(new_pass),
                    "clients": {}
                }
                save_users(users)
                st.success("Usuario creado. Ahora puedes iniciar sesión.")

# --- INICIO ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

query_params = st.experimental_get_query_params()

if st.session_state.authenticated and query_params.get("page") == ["dashboard"]:
    import dashboard
    dashboard.run()
else:
    login_screen()
