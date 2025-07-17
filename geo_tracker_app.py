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

# --- DASHBOARD PRINCIPAL ---
def geo_tracker_dashboard():
    users = load_users()
    user = st.session_state.username

    if user not in users:
        st.error("Este usuario ya no existe. Por favor, cierra sesión.")
        if st.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.session_state.username = None
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
    client["brand"] = st.sidebar.text_input("Marca", value=client.get("brand", ""))
    client["domain"] = st.sidebar.text_input("Dominio", value=client.get("domain", ""))
    if client.get("domain"):
        domain_clean = client["domain"].replace("https://", "").replace("http://", "").split("/")[0]
        favicon_url = f"https://www.google.com/s2/favicons?sz=64&domain={domain_clean}"
        st.sidebar.image(favicon_url, width=32)

    st.sidebar.markdown("### 🔑 API Keys por cliente")
    client["apis"]["openai"] = st.sidebar.text_input("OpenAI API Key", value=client["apis"].get("openai", ""), type="password")
    st.sidebar.text_input("Gemini API (próximamente)", disabled=True)
    st.sidebar.text_input("Perplexity API (próximamente)", disabled=True)
    api_key = client["apis"]["openai"]
    model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
    run = st.sidebar.button("🚀 Consultar IA")
    save_users(users)

    st.markdown("### 🔑 Palabras clave principales")
    keywords_str = st.text_area("Palabras clave (una por línea):", "\n".join(client.get("keywords", [])))
    client["keywords"] = [kw.strip() for kw in keywords_str.splitlines() if kw.strip()]
    save_users(users)

    st.markdown("### 📥 Importar palabras clave desde Search Console")
    uploaded_file = st.file_uploader("Sube un CSV exportado desde GSC", type=["csv"])
    if uploaded_file is not None:
        try:
            df_keywords = pd.read_csv(uploaded_file)
            if "Consulta" in df_keywords.columns:
                new_keywords = df_keywords["Consulta"].dropna().unique().tolist()
                client["keywords"].extend([kw for kw in new_keywords if kw not in client["keywords"]])
                client["keywords"] = sorted(set(client["keywords"]))
                st.success(f"{len(new_keywords)} palabras clave añadidas.")
                save_users(users)
            else:
                st.error("El archivo no tiene una columna 'Consulta'.")
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")

    st.markdown("### ✍️ Prompts personalizados")
    if st.button("➕ Añadir nuevo prompt"):
        client["prompts"].append("")
        save_users(users)

    cols = st.columns(2)
    for i in range(len(client["prompts"])):
        with cols[i % 2]:
            value = st.text_area(f"Prompt #{i+1}", client["prompts"][i], height=80, key=f"prompt_{i}")
            client["prompts"][i] = value
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
            f"Este es un análisis SEO para IA. Prompt original: '{prompt}'. "
            f"Marca: '{brand}'. Respuesta de la IA: '{response[:1000]}'. "
            f"¿Qué debería mejorar esta marca para aparecer mejor posicionada en esta respuesta de IA? "
            f"Da recomendaciones claras."
        )
        try:
            openai_client = openai.OpenAI(api_key=api_key)
            rec_response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.7
            )
            return rec_response.choices[0].message.content
        except Exception as e:
            st.warning("No se pudo generar la recomendación.")
            return "No disponible"

    if run:
        valid_prompts = [p for p in client["prompts"] if p.strip()]
        if not api_key:
            st.warning("⚠️ Debes introducir una API Key válida de OpenAI.")
        elif not client["brand"]:
            st.warning("⚠️ Debes introducir una marca.")
        elif not valid_prompts:
            st.warning("⚠️ No hay prompts válidos para procesar.")
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

        # --- Gráfico Índice Visibilidad GEO ---
        df['score'] = df.apply(lambda row: (1 if row['mention'] else 0) + (1 if row['link'] else 0), axis=1)
        df['score'] += df['position'].apply(lambda x: max(0, 3 - int(x)) if pd.notnull(x) else 0)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df_sorted = df.sort_values("timestamp")
        visibilidad_geo = df_sorted.groupby(df_sorted["timestamp"].dt.date)["score"].sum().reset_index()
        visibilidad_geo.columns = ["Fecha", "Índice de Visibilidad GEO"]

        fig = px.line(visibilidad_geo, x="Fecha", y="Índice de Visibilidad GEO", markers=True,
                      title="📈 Índice de Visibilidad GEO (evolución diaria)")

        st.plotly_chart(fig, use_container_width=True)

        # Mostrar tabla
        st.markdown("### 📊 Resultados")
        st.dataframe(df)

# --- INICIO ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    geo_tracker_dashboard()
else:
    login_screen()
