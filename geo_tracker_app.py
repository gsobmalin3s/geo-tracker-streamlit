import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import hashlib
import json
import os
import openai
import re
from fpdf import FPDF
from io import BytesIO
from openai import OpenAI

# --- CONFIG GLOBAL ---
st.set_page_config(page_title="GEO Tracker PRO", layout="wide")

# --- RUTAS ---
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

def generar_pdf_informe(df, brand):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title(f"Informe de Visibilidad – {brand}")
    pdf.cell(200, 10, txt=f"Informe IA – {brand}", ln=True, align="C")
    pdf.ln(10)
    for i, row in df.iterrows():
        pdf.multi_cell(0, 6, f"Prompt: {row['prompt']}\n"
                                 f"Mención: {'Sí' if row['mention'] else 'No'}\n"
                                 f"Enlace: {'Sí' if row['link'] else 'No'}\n"
                                 f"Palabras clave: {', '.join(row['matched_keywords'])}\n"
                                 f"Posición: {row['position'] or '—'}\n"
                                 f"Recomendación: {row['recommendation']}\n"
                                 f"{'-'*50}")
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

def mostrar_dashboard_final(df, client, selected_client):
    st.dataframe(df[["prompt", "mention", "matched_keywords", "link", "position", "timestamp"]])
    st.download_button("⬇️ Exportar CSV", data=df.to_csv(index=False), file_name=f"{selected_client}_resultados.csv")

    if st.button("📄 Generar PDF del informe"):
        pdf_file = generar_pdf_informe(df, client["brand"])
        st.download_button("⬇️ Descargar informe PDF", data=pdf_file, file_name="informe_visibilidad.pdf", mime="application/pdf")

    m = df["mention"].mean()
    l = df["link"].mean()
    p = df["position"].notna().mean()
    k = len([kw for kw in client["keywords"] if any(kw.lower() in r.lower() for r in df["response"])]) / max(len(client["keywords"]), 1)
    visibility = round((m * 0.4 + l * 0.25 + p * 0.2 + k * 0.15) * 100, 1)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ % Mención", f"{m*100:.1f}%")
    col2.metric("🔗 % con enlace", f"{l*100:.1f}%")
    col3.metric("📌 Prompts con posición", f"{p*100:.1f}%")
    col4.metric("🌟 Índice Visibilidad", f"{visibility}/100", help="Basado en menciones, enlaces, posición y presencia de keywords relevantes.")

    st.markdown("### 📈 Menciones por Prompt")
    df["mención"] = df["mention"].apply(lambda x: "Sí" if x else "No")
    fig = px.bar(df, x="prompt", color="mención", title="Aparición de marca por prompt")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🧠 Recomendaciones SEO")
    for i, row in df.iterrows():
        with st.expander(f"Prompt {i+1}: {row['prompt'][:40]}..."):
            st.markdown(f"**Respuesta IA:**\n\n{row['response'][:1200]}")
            st.markdown("---")
            st.markdown(f"**Recomendación:**\n\n{row['recommendation']}")

# --- AUTENTICACIÓN ---
def login_screen():
    st.title("🔐 GEO Tracker PRO")
    tab_login, tab_register = st.tabs(["Iniciar sesión", "Registrarse"])
    users = load_users()

    with tab_login:
        username = st.text_input("Usuario", help="Tu nombre de usuario para iniciar sesión.")
        password = st.text_input("Contraseña", type="password", help="Introduce tu contraseña segura.")
        if st.button("Iniciar sesión"):
            if username in users and verify_password(password, users[username]["password"]):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"¡Bienvenido, {username}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    with tab_register:
        new_user = st.text_input("Nuevo usuario", help="Introduce tu correo o nombre de usuario para registrarte.")
        new_pass = st.text_input("Nueva contraseña", type="password", help="Crea una contraseña segura.")
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

if st.session_state.authenticated:
    st.write("Aquí iría el dashboard completo, incluyendo prompts, keywords, análisis y resultados.")
else:
    login_screen()
