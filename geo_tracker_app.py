
# Este archivo usa el cliente OpenAI >= 1.0.0 con client.chat.completions.create()

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import hashlib
import json
import os
from openai import OpenAI
import re
from fpdf import FPDF
from io import BytesIO

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

    for _, row in df.iterrows():
        content = (
            f"Prompt: {row.get('prompt', '—')}
"
            f"Mención: {'Sí' if row.get('mention') else 'No'}
"
            f"Enlace: {'Sí' if row.get('link') else 'No'}
"
            f"Palabras clave: {', '.join(row.get('matched_keywords', [])) or '—'}
"
            f"Posición: {row.get('position') or '—'}
"
            f"Recomendación: {row.get('recommendation', 'No disponible')}
"
            f"{'-'*50}"
        )
        pdf.multi_cell(0, 6, content)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)

# --- DASHBOARD ---
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

def geo_tracker_dashboard():
    users = load_users()
    user = st.session_state.username
    if user not in users:
        st.error("Usuario no encontrado.")
        return

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
        return

    client = clients[selected_client]
    st.sidebar.text_input("Dominio", value=client.get("domain", ""), key="dominio", help="Dominio web del cliente")
    client["brand"] = st.sidebar.text_input("Marca", value=client.get("brand", ""))
    client["apis"]["openai"] = st.sidebar.text_input("OpenAI API Key", value=client["apis"].get("openai", ""), type="password")
    model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
    run = st.sidebar.button("🚀 Consultar IA")
    save_users(users)

    keywords_str = st.text_area("Palabras clave", "
".join(client.get("keywords", [])))
    client["keywords"] = [kw.strip() for kw in keywords_str.splitlines() if kw.strip()]
    save_users(users)

    if st.button("➕ Añadir nuevo prompt"):
        client["prompts"].append("")
        save_users(users)

    cols = st.columns(2)
    for i, prompt in enumerate(client["prompts"]):
        with cols[i % 2]:
            val = st.text_area(f"Prompt #{i+1}", prompt, key=f"prompt_{i}")
            client["prompts"][i] = val
    save_users(users)

    def call_openai(prompt):
        try:
            client_ai = OpenAI(api_key=client["apis"]["openai"])
            response = client_ai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error al consultar OpenAI: {e}")
            return None

    def generate_inline_recommendation(prompt, brand, response):
        if brand.lower() not in response.lower():
            return "La marca no fue mencionada. Mejorar autoridad o relevancia."
        if "http" not in response:
            return "Considera incluir enlaces relevantes o mejorar presencia digital."
        return "Presencia adecuada. Reforzar con más contenido relevante."

    if run:
        results = []
        for p in [p for p in client["prompts"] if p.strip()]:
            resp = call_openai(p)
            if not resp:
                continue
            matched = get_keyword_matches(resp, client["keywords"])
            results.append({
                "prompt": p,
                "mention": bool(matched),
                "matched_keywords": matched,
                "link": "http" in resp,
                "position": None,
                "timestamp": datetime.datetime.now().isoformat(),
                "response": resp,
                "recommendation": generate_inline_recommendation(p, client["brand"], resp)
            })
        client["results"] = results
        save_users(users)

    if client.get("results"):
        df = pd.DataFrame(client["results"])
        mostrar_dashboard_final(df, client, selected_client)

def mostrar_dashboard_final(df, client, selected_client):
    st.markdown("## 📊 Resultados")
    df["matched_keywords"] = df["matched_keywords"].apply(lambda x: ", ".join(x))
    st.dataframe(df[["prompt", "mention", "link", "matched_keywords", "recommendation"]])

    st.markdown("### 📄 Descargar PDF")
    if st.button("📥 Generar PDF"):
        pdf = generar_pdf_informe(df, client["brand"])
        st.download_button("Descargar", data=pdf, file_name=f"{client['brand']}_informe.pdf")

    st.markdown("### 🌍 Índice de visibilidad GEO")

    def calcular_indice(row):
        score = 0
        if row.get("mention"): score += 1
        if row.get("link"): score += 1
        if isinstance(row.get("position"), int): score += max(0, 5 - row["position"]) * 0.5
        score += len(row.get("matched_keywords", "").split(", ")) * 0.3
        return round(score, 2)

    df["visibilidad_geo"] = df.apply(calcular_indice, axis=1)
    fig = px.bar(df, x="prompt", y="visibilidad_geo", text="visibilidad_geo", color="visibilidad_geo",
                 labels={"visibilidad_geo": "Índice GEO"}, title="Índice de Visibilidad por Prompt")
    st.plotly_chart(fig, use_container_width=True)

# --- INICIO ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    geo_tracker_dashboard()
else:
    login_screen()
