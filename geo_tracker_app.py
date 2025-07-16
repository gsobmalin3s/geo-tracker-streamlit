import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import hashlib
import json
import os
import openai
import re
import time

# --- RUTAS ---
USER_DB = "data/users.json"
os.makedirs("data", exist_ok=True)

# --- CSS para loader ---
st.markdown("""
    <style>
        #loader-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .lin3s-loader {
            width: 40px;
            height: 30px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .bar {
            height: 6px;
            background-color: white;
            animation: pulse 1.2s infinite ease-in-out;
        }
        .bar:nth-child(2) {
            animation-delay: 0.2s;
        }
        .bar:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
    </style>
    <div id="loader-container">
        <div class="lin3s-loader">
            <div class="bar"></div>
            <div class="bar"></div>
            <div class="bar"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

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

def call_openai_cached(prompt, api_key, model):
    if "openai_cache" not in st.session_state:
        st.session_state.openai_cache = {}
    key = (prompt, model)
    if key in st.session_state.openai_cache:
        return st.session_state.openai_cache[key]
    try:
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response['choices'][0]['message']['content']
        st.session_state.openai_cache[key] = content
        return content
    except Exception as e:
        st.error(f"Error al consultar OpenAI: {e}")
        return None
