# Volver a generar el archivo eliminando toda lógica relacionada con OpenAI,
# dejando solo el sistema de login, registro, cierre de sesión y estructura base

python_code_no_openai = """
import streamlit as st
import hashlib
import json
import os

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

# --- Configuración de página ---
st.set_page_config(page_title="Sistema de Login", layout="centered")
st.title("🔐 Sistema de Login Seguro")

# --- Manejo de sesión ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Interfaz principal ---
menu = st.sidebar.radio("Menú", ["Iniciar sesión", "Registrar", "Cerrar sesión"])

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

    if st.button("Entrar"):
        if username in users and verify_password(password, users[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bienvenido, {username}")
        else:
            st.error("Usuario o contraseña incorrectos.")

# --- Cerrar sesión ---
elif menu == "Cerrar sesión":
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.success("Sesión cerrada.")

# --- Área protegida ---
if st.session_state.logged_in:
    st.subheader("🎉 Bienvenido al área privada")
    st.markdown(f"Usuario: **{st.session_state.username}**")
else:
    st.info("Por favor, inicia sesión para acceder al contenido.")
"""

path_clean_login = "/mnt/data/app_login_solo.py"
with open(path_clean_login, "w", encoding="utf-8") as f:
    f.write(python_code_no_openai)

path_clean_login
