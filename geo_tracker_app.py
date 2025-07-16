import streamlit as st
import openai
import pandas as pd
import datetime
import plotly.express as px
import os

st.set_page_config(page_title="GEO Tracker PRO", layout="wide")

# --- ESTILOS ---
st.markdown("""
    <style>
        html, body {
            background-color: #0f1117;
            color: #f0f2f6;
            font-family: 'Segoe UI', sans-serif;
        }
        .stButton>button {
            background-color: #4e8cff;
            color: white;
            padding: 0.4rem 1.2rem;
            border: none;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        input, textarea {
            background-color: #1c1f26 !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE CLIENTES ---
logo_path = "assets/logo-lin3s.jpg"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width=160)
else:
    st.sidebar.markdown("### GEO Tracker PRO")

st.sidebar.markdown("### 👥 Cliente")

if "clients" not in st.session_state:
    st.session_state.clients = {}

if "selected_client" not in st.session_state:
    st.session_state.selected_client = None

client_options = list(st.session_state.clients.keys())
selected_client = st.sidebar.selectbox(
    "Selecciona cliente",
    client_options + ["➕ Crear nuevo"],
    index=client_options.index(st.session_state.selected_client)
    if st.session_state.selected_client in client_options else len(client_options)
)

if selected_client == "➕ Crear nuevo":
    new_name = st.sidebar.text_input("Nombre del nuevo cliente")
    if st.sidebar.button("Crear cliente") and new_name:
        st.session_state.clients[new_name] = {
            "brand": "",
            "domain": "",
            "prompts": ["" for _ in range(4)],
            "results": [],
            "apis": {
                "openai": "",
                "gemini": None,
                "claude": None
            }
        }
        st.session_state.selected_client = new_name
        st.experimental_rerun()
else:
    st.session_state.selected_client = selected_client

if selected_client not in st.session_state.clients:
    st.stop()

client = st.session_state.clients[selected_client]

# --- CONFIGURACIÓN ---
st.sidebar.markdown("### ⚙️ Configuración")
client["brand"] = st.sidebar.text_input("Marca", value=client.get("brand", ""))
client["domain"] = st.sidebar.text_input("Dominio", value=client.get("domain", ""))

# --- Imagen de perfil desde favicon ---
if client.get("domain"):
    domain_clean = client["domain"].replace("https://", "").replace("http://", "").split("/")[0]
    favicon_url = f"https://www.google.com/s2/favicons?sz=64&domain={domain_clean}"
    st.sidebar.image(favicon_url, width=32)

# --- API por cliente ---
st.sidebar.markdown("### 🔑 API Keys por cliente")
client["apis"]["openai"] = st.sidebar.text_input("OpenAI API Key", value=client["apis"].get("openai", ""), type="password")
st.sidebar.text_input("Gemini API Key (próximamente)", disabled=True)
st.sidebar.text_input("Claude API Key (próximamente)", disabled=True)

api_key = client["apis"]["openai"]
model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
run = st.sidebar.button("🚀 Consultar IA")

aliases = [client["brand"], client["brand"].lower()]
if client["brand"].lower() == "uoc":
    aliases.append("universitat oberta de catalunya")

# --- PROMPTS PERSONALIZADOS ---
st.markdown("### ✍️ Prompts personalizados")

if st.button("➕ Añadir nuevo prompt"):
    client["prompts"].append("")

cols = st.columns(2)
for i in range(len(client["prompts"])):
    with cols[i % 2]:
        value = st.text_area(f"Prompt #{i+1}", client["prompts"][i], height=80, key=f"prompt_{i}")
        client["prompts"][i] = value

# --- FUNCIONES GPT ---
def call_openai(prompt):
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Error al consultar OpenAI: {e}")
        return None

def generate_recommendation(prompt, brand, response):
    analysis_prompt = f"""Este es un análisis SEO para IA. Prompt original: "{prompt}". Marca: "{brand}". Respuesta de la IA: "{response[:1000]}". ¿Qué debería mejorar esta marca para aparecer mejor posicionada en esta respuesta de IA? Da recomendaciones claras."""
    try:
        rec_response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.7
        )
        return rec_response['choices'][0]['message']['content']
    except Exception as e:
        st.warning("No se pudo generar la recomendación.")
        return "No disponible"

# --- CONSULTA GPT ---
valid_prompts = [p for p in client["prompts"] if p.strip()]
if run:
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
            mention = any(alias.lower() in response.lower() for alias in aliases)
            link = "http" in response
            position = None
            for i, line in enumerate(response.splitlines()):
                if any(alias.lower() in line.lower() for alias in aliases) and line.strip().split(" ")[0].isdigit():
                    position = i + 1
                    break
            recommendation = generate_recommendation(p, client["brand"], response)
            client["results"].append({
                "prompt": p,
                "mention": mention,
                "link": link,
                "position": position,
                "timestamp": datetime.datetime.now(),
                "response": response,
                "recommendation": recommendation
            })

# --- DASHBOARD ---
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

    st.dataframe(df[["prompt", "mention", "link", "position", "timestamp"]])

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
