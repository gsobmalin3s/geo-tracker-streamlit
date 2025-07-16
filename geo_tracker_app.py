# Generar el código Python completo de más de 200 líneas incluyendo:
# - Registro de usuarios
# - Login
# - Consulta a OpenAI
# - Uso de spinner
# - Visualización opcional
# - Comentarios y estructura profesional

# Comenzamos armando la estructura como string
python_code = """
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import hashlib
import json
import os
import openai
import re

# --- RUTAS ---
USER_DB = "data/users.json"
os.makedirs("data", exist_ok=True)

# --- Utilidades de usuario ---
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

# --- Coincidencia de palabras clave (si se usa más adelante) ---
def get_keyword_matches(text, keywords):
    text = text.lower()
    return [kw for kw in keywords if re.search(rf'\\\\b{re.escape(kw.lower())}\\\\b', text)]

# --- Llamada a OpenAI con caché ---
def call_openai_cached(prompt, api_key, model):
    if "openai_cache" not in st.session_state:
        st.session_state.openai_cache = {}
    key = (prompt, model)
    if key in st.session_state.openai_cache:
        return st.session_state.openai_cache[key]
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response['choices'][0]['message']['content']
        st.session_state.openai_cache[key] = content
        return content
    except Exception as e:
        st.error(f"Error al consultar OpenAI: {e}")
        return None

# --- Configuración de página ---
st.set_page_config(page_title="App OpenAI Segura", layout="centered")
st.title("🔐 Sistema con Login + OpenAI")

# --- Manejo de sesión ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# --- Interfaz principal ---
menu = st.sidebar.radio("Menú", ["Iniciar sesión", "Registrar", "OpenAI", "Cerrar sesión"])

users = load_users()

# --- Registro de usuario ---
if menu == "Registrar":
    st.subheader("📝 Registro de nuevo usuario")
    new_user = st.text_input("Nuevo usuario")
    new_pass = st.text_input("Nueva contraseña", type="password")
    if st.button("Registrar"):
        if new_user in users:
            st.warning("El usuario ya existe.")
        else:
            users[new_user] = hash_password(new_pass)
            save_users(users)
            st.success("Usuario registrado correctamente.")

# --- Inicio de sesión ---
elif menu == "Iniciar sesión":
    st.subheader("🔑 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    api_key = st.text_input("API Key de OpenAI", type="password")

    if st.button("Entrar"):
        if username in users and verify_password(password, users[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.api_key = api_key
            st.success(f"Bienvenido, {username}")
        else:
            st.error("Usuario o contraseña incorrectos.")

# --- Cerrar sesión ---
elif menu == "Cerrar sesión":
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.api_key = ""
    st.success("Sesión cerrada.")

# --- Consulta a OpenAI ---
elif menu == "OpenAI":
    if not st.session_state.logged_in:
        st.warning("Debes iniciar sesión primero.")
    else:
        st.subheader(f"👋 Hola, {st.session_state.username}")
        st.write("Consulta segura a OpenAI")

        prompt = st.text_area("🧠 Prompt")
        model = st.selectbox("Modelo", ["gpt-3.5-turbo", "gpt-4"])

        if st.button("Enviar"):
            if not prompt.strip():
                st.warning("El prompt está vacío.")
            else:
                with st.spinner("Consultando a OpenAI..."):
                    result = call_openai_cached(prompt, st.session_state.api_key, model)
                    if result:
                        st.success("Respuesta de OpenAI:")
                        st.markdown(result)
                    else:
                        st.error("No se obtuvo respuesta.")
        
        # Opcional: Historial
        if "openai_cache" in st.session_state:
            st.subheader("📜 Historial (caché)")
            for key, val in list(st.session_state.openai_cache.items())[-5:][::-1]:
                st.markdown(f"**Prompt:** `{key[0][:30]}...`  \n**Modelo:** {key[1]}  \n> {val[:300]}...")

# --- Footer ---
st.markdown("---")
st.markdown("📦 Proyecto de ejemplo con Streamlit + OpenAI")
"""

with open("/mnt/data/app_openai_login.py", "w", encoding="utf-8") as f:
    f.write(python_code)

"/mnt/data/app_openai_login.py"

