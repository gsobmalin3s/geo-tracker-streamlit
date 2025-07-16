import streamlit as st
import openai
import pandas as pd
import datetime
import plotly.express as px

st.set_page_config(page_title="GEO Tracker", layout="wide")

# Custom CSS styling
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
        .css-1aumxhk {
            padding: 1rem;
            border-radius: 10px;
            background-color: #1c1f26;
        }
        .css-ffhzg2 {  /* for sidebar */
            background-color: #1c1f26 !important;
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

# App title
st.markdown("## 🔍 GEO Tracker – Monitor de Prompts IA para tu Marca")

# Sidebar
with st.sidebar:
    st.image("https://www.lin3s.com/apple-touch-icon.png", width=100)
    st.markdown("### ⚙️ Configuración")
    api_key = st.text_input("🔑 Clave API de OpenAI", type="password")
    brand = st.text_input("🏷️ Nombre de la marca")
    domain = st.text_input("🌐 Dominio (ej. midominio.com)")
    model = st.selectbox("🧠 Modelo GPT", ["gpt-4", "gpt-3.5-turbo"])
    run = st.button("🚀 Consultar GPT")

# Prompts input
st.markdown("### ✍️ Introduce tus Prompts")
default_prompts = ["" for _ in range(25)]
prompts = []
cols = st.columns(5)
for i in range(25):
    with cols[i % 5]:
        p = st.text_area(f"Prompt #{i+1}", default_prompts[i], height=50, key=f"prompt_{i}")
        if p.strip():
            prompts.append(p.strip())

# Results store
if "results" not in st.session_state:
    st.session_state["results"] = []

# GPT Call function
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

# On run
if run and api_key and brand:
    st.session_state["results"] = []
    for p in prompts:
        content = call_openai(p)
        mention = brand.lower() in content.lower()
        link = "http" in content
        position = None
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if brand.lower() in line.lower() and line.strip().startswith(str(i+1)):
                position = i + 1
                break
        st.session_state["results"].append({
            "prompt": p,
            "response": content,
            "mention": mention,
            "link": link,
            "position": position,
            "timestamp": datetime.datetime.now()
        })

# Show dashboard
if st.session_state["results"]:
    df = pd.DataFrame(st.session_state["results"])
    st.markdown("### 📊 Resultados del Análisis")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ % de menciones", f"{(df['mention'].sum() / len(df) * 100):.1f}%")
    with col2:
        st.metric("🔗 % con enlace", f"{(df['link'].sum() / len(df) * 100):.1f}%")
    with col3:
        st.metric("📌 Posición media", f"{df['position'].dropna().mean():.1f}" if not df['position'].dropna().empty else "—")

    st.dataframe(df[["prompt", "mention", "link", "position", "timestamp"]])

    st.download_button("⬇️ Exportar CSV", data=df.to_csv(index=False), file_name="geo_results.csv", mime="text/csv")

    # Gráfico
    st.markdown("### 📈 Evolución de Menciones")
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    fig = px.bar(df, x="prompt", y="mention", color="mention", title="Aparición de marca por prompt")
    st.plotly_chart(fig, use_container_width=True)
