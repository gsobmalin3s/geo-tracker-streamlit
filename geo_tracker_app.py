import streamlit as st
import openai
import pandas as pd
import datetime
import plotly.express as px

st.set_page_config(page_title="GEO Tracker", layout="wide")

# Style and Logo
st.markdown("""
    <style>
        html, body {
            background-color: #0f1117;
            color: #f0f2f6;
            font-family: 'Segoe UI', sans-serif;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        input, textarea {
            background-color: #1c1f26 !important;
            color: white !important;
        }
        .stButton>button {
            background-color: #4e8cff;
            color: white;
            padding: 0.5rem 1.5rem;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar config
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/6/69/LIN3S_logo.svg", width=160)
st.sidebar.markdown("### 🧠 GEO Tracker Configuración")

# Client switching
if "clients" not in st.session_state:
    st.session_state.clients = {}
client_name = st.sidebar.text_input("👤 Cliente (marca única)", value="Cliente 1")
if client_name not in st.session_state.clients:
    st.session_state.clients[client_name] = {"brand": "", "domain": "", "prompts": [], "results": []}
selected = st.session_state.clients[client_name]

# OpenAI + marca
api_key = st.sidebar.text_input("🔑 Clave API OpenAI", type="password")
selected["brand"] = st.sidebar.text_input("🏷️ Marca", value=selected["brand"])
selected["domain"] = st.sidebar.text_input("🌐 Dominio", value=selected["domain"])
model = st.sidebar.selectbox("🤖 Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
run = st.sidebar.button("🚀 Consultar IA")

# Alias helper
alias_list = [selected["brand"], selected["brand"].lower()]
if selected["brand"].lower() == "uoc":
    alias_list.append("universitat oberta de catalunya")

# Prompts input
st.markdown("### ✍️ Prompts personalizados")
columns = st.columns(5)
selected["prompts"] = selected["prompts"] if selected["prompts"] else ["" for _ in range(25)]
prompts = []
for i in range(25):
    with columns[i % 5]:
        value = st.text_area(f"Prompt #{i+1}", selected["prompts"][i], height=80, key=f"p_{i}")
        prompts.append(value)
selected["prompts"] = prompts

# Function GPT call
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
        return f"ERROR: {e}"

# Consultar IA
if run and api_key and selected["brand"]:
    selected["results"] = []
    for p in selected["prompts"]:
        if not p.strip(): continue
        response = call_openai(p)
        mention = any(alias.lower() in response.lower() for alias in alias_list)
        link = "http" in response
        position = None
        lines = response.splitlines()
        for i, line in enumerate(lines):
            if any(alias.lower() in line.lower() for alias in alias_list) and line.strip().startswith(f"{i+1}"):
                position = i + 1
                break
        selected["results"].append({
            "prompt": p,
            "mention": mention,
            "link": link,
            "position": position,
            "timestamp": datetime.datetime.now(),
            "response": response
        })

# Mostrar dashboard
if selected["results"]:
    df = pd.DataFrame(selected["results"])
    st.markdown("### 📊 Resultados")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ % de menciones", f"{(df['mention'].sum() / len(df) * 100):.1f}%")
    with col2:
        st.metric("🔗 % con enlace", f"{(df['link'].sum() / len(df) * 100):.1f}%")
    with col3:
        pos_media = df['position'].dropna()
        st.metric("📌 Posición media", f"{pos_media.mean():.1f}" if not pos_media.empty else "—")

    st.dataframe(df[["prompt", "mention", "link", "position", "timestamp"]])

    st.download_button("⬇️ Exportar CSV", data=df.to_csv(index=False), file_name=f"resultados_{client_name}.csv")

    st.markdown("### 📈 Apariciones por Prompt")
    chart_df = df.copy()
    chart_df["mención"] = chart_df["mention"].apply(lambda x: "✅ Sí" if x else "❌ No")
    fig = px.bar(chart_df, x="prompt", color="mención", title="Menciones por prompt", height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🧠 Respuestas completas")
    for i, row in df.iterrows():
        with st.expander(f"📝 Prompt #{i+1}: {row['prompt'][:50]}..."):
            st.markdown(row["response"])
