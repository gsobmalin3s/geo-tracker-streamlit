# dashboard.py

import streamlit as st
import pandas as pd
import datetime
import json
import re
import openai
from geo_tracker_app import (
    load_users, save_users, get_keyword_matches,
    simulate_ai_response, simulate_recommendation,
    sugerir_prompts, generar_pdf_informe
)

def run():
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
                "apis": {"openai": "", "gemini": "(próximamente)", "perplexity": "(próximamente)"}
            }
            save_users(users)
            st.rerun()

    if selected_client not in clients:
        return

    client = clients[selected_client]
    st.title(f"📍 GEO Tracker – {selected_client}")

    st.markdown("### ⚙️ Configuración")
    client["brand"] = st.text_input("Marca", value=client.get("brand", ""))
    client["domain"] = st.text_input("Dominio", value=client.get("domain", ""))
    client["apis"]["openai"] = st.text_input("OpenAI API Key", type="password", value=client["apis"].get("openai", ""))
    st.text_input("Gemini API Key", value="(próximamente)", disabled=True)
    st.text_input("Perplexity API Key", value="(próximamente)", disabled=True)
    save_users(users)

    st.divider()
    st.markdown("### 🔑 Palabras clave")
    kws = st.text_area("Introduce palabras clave (una por línea):", "\n".join(client["keywords"]))
    client["keywords"] = [k.strip() for k in kws.splitlines() if k.strip()]
    save_users(users)

    uploaded_file = st.file_uploader("📥 Importar CSV (columna 'Consulta')", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "Consulta" in df.columns:
            nuevos = df["Consulta"].dropna().unique().tolist()
            client["keywords"].extend([k for k in nuevos if k not in client["keywords"]])
            client["keywords"] = sorted(set(client["keywords"]))
            st.success(f"{len(nuevos)} palabras clave añadidas.")
            save_users(users)
        else:
            st.error("El archivo debe tener una columna 'Consulta'.")

    st.divider()
    st.markdown("### ✍️ Prompts a trackear")
    if st.button("➕ Añadir prompt"):
        client["prompts"].append("")
    for i, p in enumerate(client["prompts"]):
        client["prompts"][i] = st.text_input(f"Prompt {i+1}", value=p, key=f"prompt_{i}")

    sector = st.selectbox("🧭 Sector sugerido", ["educación", "salud", "legal", "ecommerce"])
    sugerencias = sugerir_prompts(client["prompts"], sector)
    for s in sugerencias:
        if st.button(f"➕ Añadir sugerido: {s}"):
            client["prompts"].append(s)
            save_users(users)
            st.rerun()

    st.divider()
    st.markdown("### 🚀 Ejecutar simulación con IA")
    if st.button("Ejecutar" ):
        client["results"] = []
        for prompt in client["prompts"]:
            response = simulate_ai_response(prompt, "openai", client["apis"]["openai"])
            matched = get_keyword_matches(response, client["keywords"])
            mention = client["brand"].lower() in response.lower()
            link = "http" in response
            position = None
            for i, line in enumerate(response.splitlines()):
                if client["brand"].lower() in line.lower():
                    position = i + 1
                    break
            recommendation = simulate_recommendation(response, client["brand"], client["apis"]["openai"])
            client["results"].append({
                "prompt": prompt,
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
        st.markdown("### 📊 Resultados")
        st.dataframe(df[["prompt", "mention", "link", "matched_keywords", "position"]])

        visibility = 0.5 * df["mention"].mean() + 0.3 * df["link"].mean() + 0.2 * df["position"].notna().mean()
        dominan = [kw for kw in client["keywords"] if df["response"].str.contains(kw, case=False).any()]
        st.metric("Índice de Visibilidad (0-1)", f"{visibility:.2f}")
        st.metric("Menciones", f"{df['mention'].sum()} / {len(df)}")
        st.metric("Keywords dominantes", f"{len(dominan)} / {len(client['keywords'])}")

        if st.button("📄 Generar informe PDF"):
            pdf = generar_pdf_informe(df, client["brand"], "Conclusión generada automáticamente.")
            st.download_button("⬇️ Descargar informe PDF", data=pdf, file_name="informe.pdf", mime="application/pdf")
