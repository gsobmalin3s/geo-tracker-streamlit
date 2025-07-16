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

# --- Utilidades ---
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

def login_screen():
    st.title("🔐 GEO Tracker PRO")
    tab_login, tab_register = st.tabs(["Iniciar sesión", "Registrarse"])
    users = load_users()

    with tab_login:
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            if username in users and verify_password(password, users[username]["password"]):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"¡Bienvenido, {username}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    with tab_register:
        new_user = st.text_input("Nuevo usuario")
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

def geo_tracker_dashboard():
    st.set_page_config(page_title="GEO Tracker PRO", layout="wide")
    users = load_users()
    user = st.session_state.username

    if user not in users:
        st.error("Este usuario ya no existe. Por favor, cierra sesión y vuelve a entrar.")
        if st.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()
        st.stop()

    clients = users[user]["clients"]

    logo_path = "assets/logo-lin3s.jpg"
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, width=160)
    else:
        st.sidebar.markdown("### GEO Tracker PRO")

    st.sidebar.markdown(f"👤 Usuario: `{user}`")
    st.sidebar.markdown("### 👥 Cliente")

    client_options = list(clients.keys())
    selected_client = st.sidebar.selectbox(
        "Selecciona cliente",
        client_options + ["➕ Crear nuevo"],
        index=0 if client_options else len(client_options)
    )

    if selected_client == "➕ Crear nuevo":
        new_name = st.sidebar.text_input("Nombre del nuevo cliente")
        if st.sidebar.button("Crear cliente") and new_name:
            clients[new_name] = {
                "brand": "",
                "domain": "",
                "prompts": ["" for _ in range(4)],
                "results": [],
                "apis": {"openai": ""},
                "keywords": []
            }
            save_users(users)
            st.rerun()

    if selected_client not in clients:
        st.stop()

    # (el resto del código sigue igual...)
