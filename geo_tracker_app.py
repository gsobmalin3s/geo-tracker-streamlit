# geo_tracker_pro.py
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
from tempfile import NamedTemporaryFile

# --- CONFIG ---
st.set_page_config(page_title="GEO Tracker PRO", layout="wide")
USER_DB = "data/users.json"
os.makedirs("data", exist_ok=True)

# --- UTILS ---
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

def generar_pdf_informe(df, brand, fig=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title(f"Informe de Visibilidad – {brand}")
    pdf.cell(200, 10, txt=f"Informe IA – {brand}", ln=True, align="C")
    pdf.ln(10)

    if fig:
        with NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            fig.write_image(tmpfile.name)
            pdf.image(tmpfile.name, x=10, y=30, w=180)
            pdf.ln(90)

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

# --- AUTENTICACIÓN ---
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
                users[new_user] = {"password": hash_password(new_pass), "clients": {}}
                save_users(users)
                st.success("Usuario creado. Ahora puedes iniciar sesión.")

# --- DASHBOARD ---
def geo_tracker_dashboard():
    users = load_users()
    user = st.session_state.username

    if user not in users:
        st.error("Este usuario ya no existe.")
        if st.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.rerun()
        st.stop()

    clients = users[user]["clients"]
    st.sidebar.markdown(f"👤 Usuario: {user}")
    selected_client = st.sidebar.selectbox("Selecciona cliente", list(clients.keys()) + ["➕ Crear nuevo"])

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

    client = clients[selected_client]
    st.sidebar.markdown("### ⚙️ Configuración")
    client["brand"] = st.sidebar.text_input("Marca", value=client.get("brand", ""), help="Nombre de la marca a analizar. Aparecerá en los prompts y en el informe.").strip()
    client["domain"] = st.sidebar.text_input("Dominio", value=client.get("domain", ""), help="Web principal del cliente. Se usa para mostrar favicon e identificar enlaces.").lower().strip()
    if client.get("domain"):
        favicon_url = f"https://www.google.com/s2/favicons?sz=64&domain={client['domain']}"
        st.sidebar.image(favicon_url, width=32)

    st.sidebar.markdown("### 🔑 API Keys")
    client["apis"]["openai"] = st.sidebar.text_input("OpenAI API Key", value=client["apis"].get("openai", ""), type="password", help="Clave secreta desde https://platform.openai.com")
    api_key = client["apis"]["openai"]
    model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
    run = st.sidebar.button("🚀 Consultar IA")
    save_users(users)

    st.markdown("### 🔑 Palabras clave principales")
    keywords_str = st.text_area("Palabras clave (una por línea):", "\n".join(client.get("keywords", [])), help="Introduce términos clave que quieres rastrear.")
    client["keywords"] = [kw.strip().lower() for kw in keywords_str.splitlines() if kw.strip()]
    save_users(users)

    st.markdown("### ✍️ Prompts personalizados")
    if st.button("➕ Añadir nuevo prompt"):
        client["prompts"].append("")
        save_users(users)

    cols = st.columns(2)
    for i in range(len(client["prompts"])):
        with cols[i % 2]:
            value = st.text_area(f"Prompt #{i+1}", client["prompts"][i], height=80, key=f"prompt_{i}", help="Consulta para la IA. Usa marca y palabras clave.")
            client["prompts"][i] = value.strip()
    save_users(users)

    def call_openai(prompt):
        try:
            openai_client = openai.OpenAI(api_key=api_key)
            response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error al consultar OpenAI: {e}")
            return None

    def generate_recommendation(prompt, brand, response):
        analysis_prompt = (
            f"Este es un análisis SEO para IA. Prompt: '{prompt.lower()}'. "
            f"Marca: '{brand.lower()}'. Respuesta IA: '{response[:1000].lower()}'. "
            f"¿Qué puede mejorar esta marca para mejorar su visibilidad?"
        )
        try:
            openai_client = openai.OpenAI(api_key=api_key)
            rec_response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.7
            )
            return rec_response.choices[0].message.content
        except Exception:
            return "No disponible"

    if run:
        valid_prompts = [p for p in client["prompts"] if p.strip()]
        if not api_key:
            st.warning("⚠️ Debes introducir una API Key válida.")
        elif not client["brand"]:
            st.warning("⚠️ Debes introducir una marca.")
        elif not valid_prompts:
            st.warning("⚠️ No hay prompts válidos.")
        else:
            client["results"] = []
            for p in valid_prompts:
                response = call_openai(p)
                if not response:
                    continue
                response_lower = response.lower()
                keyword_matches = get_keyword_matches(response_lower, client.get("keywords", []))
                mention = len(keyword_matches) > 0
                link = "http" in response_lower
                position = None
                for i, line in enumerate(response.splitlines()):
                    if any(kw in line.lower() for kw in keyword_matches) and line.strip().split(" ")[0].isdigit():
                        position = i + 1
                        break
                recommendation = generate_recommendation(p, client["brand"], response)
                client["results"].append({
                    "prompt": p,
                    "mention": mention,
                    "matched_keywords": keyword_matches,
                    "link": link,
                    "position": position,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "response": response,
                    "recommendation": recommendation
                })
            save_users(users)

    if client.get("results"):
        df = pd.DataFrame(client["results"])
        df['score'] = df.apply(lambda row: (1 if row['mention'] else 0) + (1 if row['link'] else 0), axis=1)
        df['sco]()
