import streamlit as st
import openai
import pandas as pd
import datetime
import plotly.express as px

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
st.sidebar.image("assets/logo-lin3s.jpg", width=160)
st.sidebar.markdown("### 👥 Cliente")

if "clients" not in st.session_state:
    st.session_state.clients = {}

client_options = list(st.session_state.clients.keys())
selected_client = st.sidebar.selectbox("Selecciona cliente", client_options + ["➕ Crear nuevo"], index=0 if client_options else len(client_options))

if selected_client == "➕ Crear nuevo":
    new_name = st.sidebar.text_input("Nombre de la marca")
    new_domain = st.sidebar.text_input("Dominio")
    new_sector = st.sidebar.text_input("Sector")
    new_desc = st.sidebar.text_area("Descripción breve")
    new_api = st.sidebar.text_input("🔑 API Key OpenAI", type="password")
    if st.sidebar.button("Crear cliente") and new_name:
        favicon_url = f"https://www.google.com/s2/favicons?domain={new_domain}"
        st.session_state.clients[new_name] = {
            "brand": new_name,
            "domain": new_domain,
            "sector": new_sector,
            "description": new_desc,
            "api_key": new_api,
            "favicon": favicon_url,
            "prompts": ["" for _ in range(10)],
            "results": []
        }
        selected_client = new_name

if selected_client not in st.session_state.clients:
    st.stop()

client = st.session_state.clients[selected_client]

# --- PERFIL DEL CLIENTE ---
st.markdown(f"**Dominio:** {client['domain']}  
**Sector:** {client['sector']}  
**Descripción:** {client['description']}")

# --- CONFIGURACIÓN ---
st.sidebar.markdown("### ⚙️ Configuración")
model = st.sidebar.selectbox("Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
run = st.sidebar.button("🚀 Consultar IA")

aliases = [client["brand"], client["brand"].lower()]
if client["brand"].lower() == "uoc":
    aliases.append("universitat oberta de catalunya")

# --- PROMPTS ---
st.markdown("### ✍️ Prompts personalizados")
cols = st.columns(2)
for i in range(len(client["prompts"])):
    with cols[i % 2]:
        value = st.text_area(f"Prompt #{i+1}", client["prompts"][i], height=80, key=f"prompt_{i}")
        client["prompts"][i] = value

# --- CONSULTA GPT ---
def call_openai(prompt, key):
    try:
        openai.api_key = key
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}"

def generate_recommendation(prompt, brand, response, key):
    analysis_prompt = f"Este es un análisis SEO para IA. Prompt original: '{prompt}'. Marca: '{brand}'. Respuesta de la IA: '{response[:1000]}'. ¿Qué debería mejorar esta marca para aparecer mejor posicionada en esta respuesta de IA? Da recomendaciones claras."
    try:
        openai.api_key = key
        rec_response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.7
        )
        return rec_response['choices'][0]['message']['content']
    except:
        return "No disponible"

if run and client["api_key"] and client["brand"]:
    client["results"] = []
    for p in client["prompts"]:
        if not p.strip():
            continue
        response = call_openai(p, client["api_key"])
        mention = any(alias.lower() in response.lower() for alias in aliases)
        link = "http" in response and client["domain"] in response
        position = None
        for i, line in enumerate(response.splitlines()):
            if any(alias.lower() in line.lower() for alias in aliases) and line.strip().startswith(str(i+1)):
                position = i + 1
                break
        recommendation = generate_recommendation(p, client["brand"], response, client["api_key"])
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
