import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import json
import os
import hashlib
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Club de Tenis · Reservas",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

RESERVAS_FILE = "reservas_tennis.json"
SOCIOS_FILE = "socios_tennis.json"
CONFIG_FILE = "config_tennis.json"

# Horarios de 60 minutos: de 08:00 a 21:00
HORARIOS = [
    "08:00", "09:00", "10:00", "11:00", "12:00", 
    "13:00", "14:00", "15:00", "16:00", "17:00", 
    "18:00", "19:00", "20:00", "21:00"
]

CANCHAS = [f"Cancha {i}" for i in range(1, 7)]

# Precios (ARS) según aranceles vigentes desde 01/10/26
PRECIO_SOCIO = 8500      # Tarifa base socio diario / referencia hora
PRECIO_NO_SOCIO = 22000  # Invitados mayores de 11 años
ADICIONAL_LUZ = 3200     # Adicional luz por hora

def get_precio(es_socio: bool, con_luz: bool) -> int:
    base = PRECIO_SOCIO if es_socio else PRECIO_NO_SOCIO
    return base + (ADICIONAL_LUZ if con_luz else 0)

def format_precio(monto: int) -> str:
    return f"$ {monto:,}".replace(",", ".")

# ============================================================
# TEMA VISUAL (MODO CLARO / OSCURO & CSS MEJORADO)
# ============================================================

def aplicar_tema():
    st.markdown("""
    <style>
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-card: #1E293B;
                --text-main: #F8FAFC;
                --border-color: #334155;
                --metric-bg: #0F172A;
                --primary-brand: #22C55E;
            }
        }
        @media (prefers-color-scheme: light) {
            :root {
                --bg-card: #FFFFFF;
                --text-main: #1E293B;
                --border-color: #E2E8F0;
                --metric-bg: #F0FDF4;
                --primary-brand: #16A34A;
            }
        }

        .club-header {
            background: linear-gradient(135deg, #15803D 0%, #166534 100%);
            color: white;
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1.2rem;
            box-shadow: 0 4px 20px rgba(22, 101, 52, 0.15);
        }
        .club-header h1 {
            color: white !important;
            margin: 0;
            font-size: 1.8rem;
            font-weight: 700;
        }
        .club-header p {
            margin: 0;
            opacity: 0.9;
            font-size: 1rem;
        }
        .logo-circle {
            width: 60px;
            height: 60px;
            background: #FACC15;
            color: #1E293B;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        .precio-badge {
            display: inline-block;
            background: #FEF08A;
            color: #854D0E;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.95rem;
        }
        .pago-ok { color: #16A34A; font-weight: 600; }
        .pago-pendiente { color: #D97706; font-weight: 600; }
        
        .footer {
            text-align: center;
            opacity: 0.6;
            font-size: 0.85rem;
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }
    </style>
    """, unsafe_allow_html=True)

def header_club(subtitulo: str = ""):
    st.markdown(f"""
    <div class="club-header">
        <div class="logo-circle">🎾</div>
        <div>
            <h1>Club de Tenis</h1>
            <p>{subtitulo or "Sistema de reservas de canchas"}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PERSISTENCIA
# ============================================================

def cargar_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default

def guardar_json(path, data):
    with open(path, "w",
