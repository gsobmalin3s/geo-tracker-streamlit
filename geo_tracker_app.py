# Guardar el archivo geo_tracker_app.py corregido, sin triple comillas ni asignaciones
clean_code = """
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
    return [kw for kw in keywords if re.search(rf'\\b{re.escape(kw.lower())}\\b', text)]

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
        pdf.multi_cell(0, 6, f"Prompt: {row['prompt']}\\n"
                             f"Mención: {'Sí' if row['mention'] else 'No'}\\n"
                             f"Enlace: {'Sí' if row['link'] else 'No'}\\n"
                             f"Palabras clave: {', '.join(row['matched_keywords'])}\\n"
                             f"Posición: {row['position'] or '—'}\\n"
                             f"Recomendación: {row['recommendation']}\\n"
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

# --- DASHBOARD SIMULADO ---
def geo_tracker_dashboard():
    users = load_users()
    user = st.session_state.username

    if user not in users:
        st.error("Este usuario ya no existe. Cierra sesión e inicia de nuevo.")
        return

    clients = users[user]["clients"]
    st.sidebar.markdown(f"👤 Usuario: `{user}`")
    selected_client = st.sidebar.selectbox("Cliente", list(clients.keys()) + ["➕ Crear nuevo"])
    if selected_client == "➕ Crear nuevo":
        new_name = st.sidebar.text_input("Nuevo nombre de cliente")
        if st.sidebar.button("Crear cliente") and new_name:
            clients[new_name] = {
                "brand": "",
                "domain": "",
                "prompts": [],
                "results": [],
                "keywords": [],
                "apis": {"openai": "", "gemini": "", "perplexity": ""}
            }
            save_users(users)
            st.rerun()

    if selected_client not in clients:
        return

    client = clients[selected_client]
    menu = st.radio("📂 Menú", ["Dashboard", "Palabras clave", "Importar CSV", "Prompts a trackear", "Índice de Visibilidad"])
    model = "gpt-3.5-turbo"

    if menu == "Dashboard":
        st.markdown("## 📊 Dashboard")
        if st.button("🔁 Ejecutar simulación diaria"):
            client["results"] = []
            for p in client["prompts"]:
                response = simulate_ai_response(p, "ChatGPT")
                matched = get_keyword_matches(response, client["keywords"])
                mention = client["brand"].lower() in response.lower()
                link = "http" in response
                position = None
                for i, line in enumerate(response.splitlines()):
                    if client["brand"].lower() in line.lower():
                        position = i + 1
                        break
                recommendation = simulate_recommendation(response, client["brand"])
                client["results"].append({
                    "prompt": p,
                    "mention": mention,
                    "link": link,
                    "matched_keywords": matched,
                    "position": position,
                    "response": response,
                    "recommendation": recommendation
                })
            save_users(users)

        if client["results"]:
            df = pd.DataFrame(client["results"])
            st.dataframe(df[["prompt", "mention", "link", "matched_keywords", "position"]])
            if st.button("📄 Generar informe PDF"):
                pdf = generar_pdf_informe(df, client["brand"], "Presencia aceptable, pero se puede mejorar.")
                st.download_button("⬇️ Descargar informe PDF", data=pdf, file_name="informe.pdf", mime="application/pdf")

    elif menu == "Palabras clave":
        st.markdown("## 🔑 Palabras clave")
        kws = st.text_area("Introduce palabras clave:", "\\n".join(client["keywords"]))
        client["keywords"] = [k.strip() for k in kws.splitlines() if k.strip()]
        save_users(users)

    elif menu == "Importar CSV":
        st.markdown("## 📥 Importar desde CSV")
        file = st.file_uploader("Sube tu CSV (columna 'Consulta')", type=["csv"])
        if file:
            df = pd.read_csv(file)
            if "Consulta" in df.columns:
                nuevos = df["Consulta"].dropna().unique().tolist()
                client["keywords"].extend([k for k in nuevos if k not in client["keywords"]])
                client["keywords"] = sorted(set(client["keywords"]))
                save_users(users)
                st.success(f"{len(nuevos)} palabras clave añadidas.")
            else:
                st.error("CSV inválido: falta columna 'Consulta'.")

    elif menu == "Prompts a trackear":
        st.markdown("## ✍️ Prompts personalizados")
        if st.button("➕ Añadir prompt"):
            client["prompts"].append("")
        for i, p in enumerate(client["prompts"]):
            client["prompts"][i] = st.text_input(f"Prompt {i+1}", value=p, key=f"prompt_{i}")
        sector = st.selectbox("Sector", ["educación", "salud", "legal", "ecommerce"])
        sugerencias = sugerir_prompts(client["prompts"], sector)
        st.markdown("### Sugerencias")
        for s in sugerencias:
            if st.button(f"Añadir: {s}"):
                client["prompts"].append(s)
        save_users(users)

    elif menu == "Índice de Visibilidad":
        st.markdown("## 🌐 Índice de Visibilidad")
        if client["results"]:
            df = pd.DataFrame(client["results"])
            index = 0.5 * df["mention"].mean() + 0.3 * df["link"].mean() + 0.2 * df["position"].notna().mean()
            dominan = [kw for kw in client["keywords"] if df["response"].str.contains(kw, case=False).any()]
            st.metric("Dominan tus keywords", f"{len(dominan)} / {len(client['keywords'])}")
            st.metric("Índice de visibilidad (0-1)", f"{index:.2f}")
            st.metric("Menciones", f"{df['mention'].sum()} / {len(df)}")
        else:
            st.info("Ejecuta primero la simulación diaria.")
