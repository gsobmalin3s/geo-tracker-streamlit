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
    save_users(users)

    api_key = client["apis"]["openai"]
    model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
    run = st.sidebar.button("🚀 Consultar IA")

    # Palabras clave manuales
    st.markdown("### 🔑 Palabras clave principales")
    keywords_str = st.text_area("Palabras clave (una por línea):", "\n".join(client.get("keywords", [])))
    client["keywords"] = [kw.strip() for kw in keywords_str.splitlines() if kw.strip()]
    save_users(users)

    # NUEVO: importar keywords desde CSV de Search Console
    st.markdown("### 📥 Importar palabras clave desde Search Console")
    uploaded_file = st.file_uploader("Sube un CSV exportado desde GSC", type=["csv"])
    if uploaded_file is not None:
        try:
            df_keywords = pd.read_csv(uploaded_file)
            if "Consulta" in df_keywords.columns:
                new_keywords = df_keywords["Consulta"].dropna().unique().tolist()
                client["keywords"].extend([kw for kw in new_keywords if kw not in client["keywords"]])
                st.success(f"{len(new_keywords)} palabras clave añadidas.")
                save_users(users)
            else:
                st.error("El archivo no tiene una columna 'Consulta'. ¿Has exportado correctamente desde GSC?")
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
            client_oai = openai.OpenAI(api_key=api_key)
            response = client_oai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error al consultar OpenAI: {e}")
            return None

    def generate_recommendation(prompt, brand, response):
        analysis_prompt = f"Este es un análisis SEO para IA. Prompt original: '{prompt}'. Marca: '{brand}'. Respuesta de la IA: '{response[:1000]}'. ¿Qué debería mejorar esta marca para aparecer mejor posicionada en esta respuesta de IA? Da recomendaciones claras."
        try:
            client_oai = openai.OpenAI(api_key=api_key)
            rec_response = client_oai.chat.completions.create(
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
                    if any(re.search(rf'\b{re.escape(k)}\b', line.lower()) for k in keyword_matches) and line.strip().split(" ")[0].isdigit():
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

    if client["results"]:
        df = pd.DataFrame(client["results"])
        visibility = round(
            (df["mention"].sum() * 50 + df["link"].sum() * 25 + df["position"].notna().sum() * 25) / (len(df) * 100) * 100,
            1
        )

        st.markdown("### 📊 Dashboard de Visibilidad")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ % Mención", f"{(df['mention'].mean()*100):.1f}%")
        col2.metric("🔗 % con enlace", f"{(df['link'].mean()*100):.1f}%")
        col3.metric("📌 Posición media", f"{df['position'].dropna().mean():.1f}" if not df['position'].dropna().empty else "—")
        col4.metric("🌟 Índice Visibilidad", f"{visibility}/100")

        st.dataframe(df[["prompt", "mention", "matched_keywords", "link", "position", "timestamp"]])
        st.download_button("⬇️ Exportar CSV", data=df.to_csv(index=False), file_name=f"{selected_client}_resultados.csv")

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

# --- APP ENTRY POINT ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    geo_tracker_dashboard()
else:
    login_screen()
