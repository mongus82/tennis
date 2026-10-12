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

# Horarios de 90 minutos: 08:00, 09:30, 11:00, 12:30, 14:00, 15:30, 17:00, 18:30, 20:00
HORARIOS = [
    "08:00", "09:30", "11:00", "12:30",
    "14:00", "15:30", "17:00", "18:30", "20:00"
]

CANCHAS = [f"Cancha {i}" for i in range(1, 7)]

# Precios (ARS) — pico = 17:00 en adelante
PRECIO_NORMAL = 8000
PRECIO_PICO = 12000
HORA_PICO = "17:00"

# Colores del club
COLOR_PRIMARIO = "#1B5E20"
COLOR_SECUNDARIO = "#4CAF50"
COLOR_ACENTO = "#FFC107"
COLOR_FONDO = "#F1F8E9"


def get_precio(horario: str) -> int:
    return PRECIO_PICO if horario >= HORA_PICO else PRECIO_NORMAL


def format_precio(monto: int) -> str:
    return f"$ {monto:,}".replace(",", ".")


# ============================================================
# TEMA VISUAL (CSS)
# ============================================================

def aplicar_tema():
    st.markdown(f"""
    <style>
        .stApp {{
            background: linear-gradient(180deg, {COLOR_FONDO} 0%, #ffffff 40%);
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {COLOR_PRIMARIO} 0%, #2E7D32 100%);
        }}
        [data-testid="stSidebar"] * {{
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            color: #ffffff !important;
        }}
        [data-testid="stSidebar"] hr {{
            border-color: rgba(255,255,255,0.3);
        }}
        h1, h2, h3 {{
            color: {COLOR_PRIMARIO} !important;
        }}
        .stButton > button[kind="primary"] {{
            background-color: {COLOR_SECUNDARIO} !important;
            border-color: {COLOR_SECUNDARIO} !important;
            color: white !important;
            font-weight: 600;
            border-radius: 8px;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: {COLOR_PRIMARIO} !important;
            border-color: {COLOR_PRIMARIO} !important;
        }}
        .stButton > button[kind="secondary"] {{
            border-radius: 8px;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 12px !important;
            border: 1px solid #C8E6C9 !important;
            background: #ffffff;
        }}
        [data-testid="stMetric"] {{
            background: #E8F5E9;
            border-radius: 10px;
            padding: 12px;
        }}
        .club-header {{
            background: linear-gradient(90deg, {COLOR_PRIMARIO}, {COLOR_SECUNDARIO});
            color: white;
            padding: 1.2rem 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .club-header h1 {{
            color: white !important;
            margin: 0;
            font-size: 1.8rem;
        }}
        .club-header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 0.95rem;
        }}
        .logo-circle {{
            width: 56px;
            height: 56px;
            background: {COLOR_ACENTO};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            flex-shrink: 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .precio-badge {{
            display: inline-block;
            background: {COLOR_ACENTO};
            color: #333;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.95rem;
        }}
        .precio-pico {{
            background: #FF5722;
            color: white;
        }}
        .pago-ok {{ color: #2E7D32; font-weight: 600; }}
        .pago-pendiente {{ color: #E65100; font-weight: 600; }}
        .footer {{
            text-align: center;
            color: #78909C;
            font-size: 0.85rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #E0E0E0;
        }}
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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_reservas():
    return cargar_json(RESERVAS_FILE, [])


def guardar_reservas(reservas):
    guardar_json(RESERVAS_FILE, reservas)


def cargar_socios():
    return cargar_json(SOCIOS_FILE, [])


def guardar_socios(socios):
    guardar_json(SOCIOS_FILE, socios)


def cargar_config():
    default = {
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "email_from": "",
        "whatsapp_numero_club": ""
    }
    return cargar_json(CONFIG_FILE, default)


def guardar_config(cfg):
    guardar_json(CONFIG_FILE, cfg)


# ============================================================
# SOCIOS / LOGIN
# ============================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def inicializar_socios_demo():
    socios = cargar_socios()
    if not socios:
        socios = [
            {
                "id": "S001",
                "nombre": "Juan Pérez",
                "email": "juan@email.com",
                "telefono": "11 5555-0001",
                "password": hash_password("1234"),
                "activo": True
            },
            {
                "id": "S002",
                "nombre": "María Gómez",
                "email": "maria@email.com",
                "telefono": "11 5555-0002",
                "password": hash_password("1234"),
                "activo": True
            },
            {
                "id": "S003",
                "nombre": "Carlos López",
                "email": "carlos@email.com",
                "telefono": "11 5555-0003",
                "password": hash_password("1234"),
                "activo": True
            },
        ]
        guardar_socios(socios)
    return socios


def autenticar(socio_id: str, password: str):
    socios = cargar_socios()
    for s in socios:
        if s["id"].upper() == socio_id.upper() and s["password"] == hash_password(password) and s.get("activo", True):
            return s
    return None


def registrar_socio(nombre, email, telefono, password):
    socios = cargar_socios()
    nums = [int(s["id"][1:]) for s in socios if s["id"].startswith("S") and s["id"][1:].isdigit()]
    next_num = max(nums, default=0) + 1
    nuevo_id = f"S{next_num:03d}"

    if any(s["email"].lower() == email.lower() for s in socios):
        return None, "Ese email ya está registrado."

    nuevo = {
        "id": nuevo_id,
        "nombre": nombre.strip(),
        "email": email.strip().lower(),
        "telefono": telefono.strip(),
        "password": hash_password(password),
        "activo": True
    }
    socios.append(nuevo)
    guardar_socios(socios)
    return nuevo, f"Socio registrado. Tu ID es **{nuevo_id}**."


# ============================================================
# RESERVAS
# ============================================================

def obtener_reservas_dia(fecha_str):
    return [r for r in cargar_reservas() if r["fecha"] == fecha_str]


def esta_ocupada(fecha_str, cancha, horario):
    return any(
        r["cancha"] == cancha and r["horario"] == horario
        for r in obtener_reservas_dia(fecha_str)
    )


def agregar_reserva(fecha_str, cancha, horario, socio, metodo_pago):
    if esta_ocupada(fecha_str, cancha, horario):
        return False, None, "Esa cancha ya está reservada en ese horario."

    precio = get_precio(horario)
    # Efectivo se paga en el club (pendiente). Transferencia y MP se consideran pagados.
    pagado = metodo_pago in ("Transferencia", "Mercado Pago (simulado)")

    reserva = {
        "id": f"{fecha_str}_{cancha}_{horario}_{datetime.now().timestamp()}",
        "fecha": fecha_str,
        "cancha": cancha,
        "horario": horario,
        "duracion": "90 min",
        "socio_id": socio["id"],
        "nombre": socio["nombre"],
        "email": socio["email"],
        "telefono": socio["telefono"],
        "precio": precio,
        "metodo_pago": metodo_pago,
        "pagado": pagado,
        "creada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    reservas = cargar_reservas()
    reservas.append(reserva)
    guardar_reservas(reservas)
    return True, reserva, "¡Reserva confirmada!"


def cancelar_reserva(reserva_id):
    reservas = cargar_reservas()
    nuevas = [r for r in reservas if r["id"] != reserva_id]
    if len(nuevas) == len(reservas):
        return False
    guardar_reservas(nuevas)
    return True


def marcar_pagado(reserva_id):
    reservas = cargar_reservas()
    for r in reservas:
        if r["id"] == reserva_id:
            r["pagado"] = True
            guardar_reservas(reservas)
            return True
    return False


def limpiar_reservas_antiguas():
    hoy = datetime.now().date()
    reservas = cargar_reservas()
    nuevas = [
        r for r in reservas
        if datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= hoy
    ]
    if len(nuevas) != len(reservas):
        guardar_reservas(nuevas)


# ============================================================
# CONFIRMACIONES (Email / WhatsApp)
# ============================================================

def mensaje_confirmacion(reserva: dict) -> str:
    estado_pago = "✅ Pagado" if reserva.get("pagado") else "⏳ Pendiente de pago"
    return (
        f"🎾 *Club de Tenis — Confirmación de Reserva*\n\n"
        f"Hola {reserva['nombre']},\n\n"
        f"Tu reserva quedó confirmada:\n"
        f"• *Cancha:* {reserva['cancha']}\n"
        f"• *Fecha:* {reserva['fecha']}\n"
        f"• *Horario:* {reserva['horario']} (90 min)\n"
        f"• *Precio:* {format_precio(reserva['precio'])}\n"
        f"• *Pago:* {reserva['metodo_pago']} — {estado_pago}\n\n"
        f"¡Te esperamos en la cancha!\n"
        f"Club de Tenis"
    )


def mensaje_email_html(reserva: dict) -> str:
    estado = "Pagado ✅" if reserva.get("pagado") else "Pendiente de pago ⏳"
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #1B5E20;">
        <div style="max-width: 500px; margin: 0 auto; border: 2px solid #4CAF50; border-radius: 12px; padding: 24px;">
            <h2 style="color: #1B5E20;">🎾 Club de Tenis</h2>
            <p>Hola <strong>{reserva['nombre']}</strong>,</p>
            <p>Tu reserva quedó confirmada:</p>
            <table style="width:100%; border-collapse: collapse;">
                <tr><td style="padding:6px 0;"><strong>Cancha</strong></td><td>{reserva['cancha']}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Fecha</strong></td><td>{reserva['fecha']}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Horario</strong></td><td>{reserva['horario']} (90 min)</td></tr>
                <tr><td style="padding:6px 0;"><strong>Precio</strong></td><td>{format_precio(reserva['precio'])}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Pago</strong></td><td>{reserva['metodo_pago']} — {estado}</td></tr>
            </table>
            <p style="margin-top: 20px;">¡Te esperamos en la cancha!</p>
            <p style="color:#78909C; font-size:0.85em;">Club de Tenis · Sistema de reservas</p>
        </div>
    </body>
    </html>
    """


def enviar_email(reserva: dict):
    cfg = cargar_config()
    if not cfg.get("smtp_host") or not cfg.get("smtp_user") or not cfg.get("smtp_pass"):
        return False, "Email no configurado. Andá a Administración → Notificaciones."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎾 Reserva confirmada — {reserva['cancha']} {reserva['fecha']} {reserva['horario']}"
        msg["From"] = cfg.get("email_from") or cfg["smtp_user"]
        msg["To"] = reserva["email"]
        msg.attach(MIMEText(mensaje_confirmacion(reserva), "plain"))
        msg.attach(MIMEText(mensaje_email_html(reserva), "html"))

        with smtplib.SMTP(cfg["smtp_host"], int(cfg.get("smtp_port", 587))) as server:
            server.starttls()
            server.login(cfg["smtp_user"], cfg["smtp_pass"])
            server.sendmail(msg["From"], [reserva["email"]], msg.as_string())
        return True, f"Email enviado a {reserva['email']}"
    except Exception as e:
        return False, f"Error al enviar email: {e}"


def link_whatsapp(reserva: dict) -> str:
    telefono = reserva.get("telefono", "").replace(" ", "").replace("-", "").replace("+", "")
    if telefono and not telefono.startswith("54") and len(telefono) <= 10:
        telefono = "54" + telefono.lstrip("0")
    texto = mensaje_confirmacion(reserva)
    encoded = urllib.parse.quote(texto)
    if telefono:
        return f"https://wa.me/{telefono}?text={encoded}"
    return f"https://wa.me/?text={encoded}"


# ============================================================
# INICIALIZACIÓN
# ============================================================

aplicar_tema()
inicializar_socios_demo()
limpiar_reservas_antiguas()

if "socio" not in st.session_state:
    st.session_state.socio = None


# ============================================================
# PANTALLA DE LOGIN / REGISTRO
# ============================================================

def pantalla_login():
    header_club("Ingresá con tu cuenta de socio")

    tab_login, tab_registro = st.tabs(["🔑 Iniciar sesión", "📝 Registrarme"])

    with tab_login:
        st.markdown("#### Ingresá tus datos")
        col1, col2 = st.columns(2)
        with col1:
            socio_id = st.text_input("ID de socio", placeholder="Ej: S001", key="login_id")
        with col2:
            password = st.text_input("Contraseña", type="password", placeholder="••••", key="login_pass")

        if st.button("Entrar", type="primary", use_container_width=True):
            if not socio_id or not password:
                st.error("Completá ID y contraseña.")
            else:
                socio = autenticar(socio_id.strip(), password)
                if socio:
                    st.session_state.socio = socio
                    st.rerun()
                else:
                    st.error("ID o contraseña incorrectos.")

        st.info("**Demo:** ID `S001` / `S002` / `S003` — contraseña `1234`")

    with tab_registro:
        st.markdown("#### Crear cuenta de socio")
        nombre = st.text_input("Nombre completo *", key="reg_nombre")
        email = st.text_input("Email *", key="reg_email")
        telefono = st.text_input("Teléfono / WhatsApp *", placeholder="11 1234-5678", key="reg_tel")
        pass1 = st.text_input("Contraseña *", type="password", key="reg_pass1")
        pass2 = st.text_input("Repetir contraseña *", type="password", key="reg_pass2")

        if st.button("Registrarme", type="primary", use_container_width=True):
            if not all([nombre, email, telefono, pass1, pass2]):
                st.error("Completá todos los campos.")
            elif pass1 != pass2:
                st.error("Las contraseñas no coinciden.")
            elif len(pass1) < 4:
                st.error("La contraseña debe tener al menos 4 caracteres.")
            else:
                socio, msg = registrar_socio(nombre, email, telefono, pass1)
                if socio:
                    st.success(msg)
                    st.balloons()
                    st.info("Ahora podés iniciar sesión con tu nuevo ID.")
                else:
                    st.error(msg)


# ============================================================
# APP PRINCIPAL (logueado)
# ============================================================

def pantalla_app():
    socio = st.session_state.socio

    with st.sidebar:
        st.markdown(f"### 👤 {socio['nombre']}")
        st.caption(f"ID: {socio['id']}")
        st.caption(f"📧 {socio['email']}")
        st.caption(f"📞 {socio['telefono']}")
        st.divider()

        pagina = st.radio(
            "Menú",
            [
                "Nueva Reserva",
                "Ver Disponibilidad",
                "Mis Reservas",
                "Precios",
                "Administración"
            ],
            label_visibility="collapsed"
        )

        st.divider()
        st.markdown("### Turnos")
        st.caption("Duración: **90 minutos**")
        st.caption("08:00 → 20:00")
        st.markdown("### Precios")
        st.caption(f"Normal: **{format_precio(PRECIO_NORMAL)}**")
        st.caption(f"Pico (≥17:00): **{format_precio(PRECIO_PICO)}**")

        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.socio = None
            st.rerun()

    # ---------- NUEVA RESERVA ----------
    if pagina == "Nueva Reserva":
        header_club("Nueva reserva · 90 minutos")

        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input(
                "Fecha",
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=30),
                value=datetime.now().date()
            )
            fecha_str = fecha.strftime("%Y-%m-%d")
        with col2:
            cancha = st.selectbox("Cancha", CANCHAS)

        st.markdown("#### Horarios disponibles")
        ocupados = {
            r["horario"] for r in obtener_reservas_dia(fecha_str)
            if r["cancha"] == cancha
        }
        libres = [h for h in HORARIOS if h not in ocupados]

        if fecha == datetime.now().date():
            ahora = datetime.now().time()
            libres = [h for h in libres if time.fromisoformat(h) > ahora]

        if not libres:
            st.warning("No hay horarios disponibles para esta cancha en esa fecha.")
        else:
            opciones = []
            for h in libres:
                p = get_precio(h)
                etiqueta = f"{h}  ·  {format_precio(p)}"
                if h >= HORA_PICO:
                    etiqueta += "  (pico)"
                opciones.append((h, etiqueta))

            labels = [o[1] for o in opciones]
            idx = st.selectbox(
                "Horario",
                range(len(labels)),
                format_func=lambda i: labels[i]
            )
            horario = opciones[idx][0]
            precio = get_precio(horario)

            badge_class = "precio-badge precio-pico" if horario >= HORA_PICO else "precio-badge"
            st.markdown(
                f'<span class="{badge_class}">{format_precio(precio)} · 90 min</span>',
                unsafe_allow_html=True
            )

            st.markdown("---")
            st.markdown("#### Pago")
            metodo = st.radio(
                "Método de pago",
                ["Efectivo (en club)", "Transferencia", "Mercado Pago (simulado)"],
                horizontal=True
            )

            if metodo == "Transferencia":
                st.info("Transferí a **CBU 0000003100010000000001** · Alias: **CLUB.TENIS** · Titular: Club de Tenis")
            elif metodo == "Mercado Pago (simulado)":
                st.info("En producción se abriría el checkout de Mercado Pago. Acá se marca como pagado al confirmar.")

            if st.button("✅ Confirmar Reserva", type="primary", use_container_width=True):
                ok, reserva, msg = agregar_reserva(fecha_str, cancha, horario, socio, metodo)
                if ok:
                    st.success(msg)
                    st.balloons()

                    with st.container(border=True):
                        estado = "✅ Pagado" if reserva["pagado"] else "⏳ Pendiente de pago"
                        st.markdown(
                            f"**{reserva['cancha']}** · {fecha.strftime('%d/%m/%Y')} · **{horario}** (90 min)  \n"
                            f"💰 {format_precio(reserva['precio'])} · {reserva['metodo_pago']} · {estado}"
                        )

                    st.markdown("#### Enviar confirmación")
                    c1, c2 = st.columns(2)
                    with c1:
                        wa_url = link_whatsapp(reserva)
                        st.link_button("📱 Abrir WhatsApp", wa_url, use_container_width=True)
                    with c2:
                        if st.button("✉️ Enviar Email", use_container_width=True):
                            ok_mail, msg_mail = enviar_email(reserva)
                            if ok_mail:
                                st.success(msg_mail)
                            else:
                                st.warning(msg_mail)

                    with st.expander("Ver mensaje de confirmación"):
                        st.code(mensaje_confirmacion(reserva), language=None)
                else:
                    st.error(msg)

    # ---------- DISPONIBILIDAD ----------
    elif pagina == "Ver Disponibilidad":
        header_club("Disponibilidad de canchas")

        fecha = st.date_input(
            "Fecha",
            min_value=datetime.now().date(),
            max_value=datetime.now().date() + timedelta(days=30),
            value=datetime.now().date(),
            key="disp_fecha"
        )
        fecha_str = fecha.strftime("%Y-%m-%d")
        reservas_dia = obtener_reservas_dia(fecha_str)

        datos = []
        for horario in HORARIOS:
            fila = {"Horario": f"{horario} (90')"}
            for cancha in CANCHAS:
                ocupada = any(
                    r["cancha"] == cancha and r["horario"] == horario
                    for r in reservas_dia
                )
                if ocupada:
                    r = next(x for x in reservas_dia if x["cancha"] == cancha and x["horario"] == horario)
                    fila[cancha] = f"🔴 {r['nombre']}"
                else:
                    p = get_precio(horario)
                    fila[cancha] = f"🟢 {format_precio(p)}"
            datos.append(fila)

        df = pd.DataFrame(datos)
        st.markdown(f"**{fecha.strftime('%A %d/%m/%Y').capitalize()}** · Turnos de 90 minutos")
        st.dataframe(df, use_container_width=True, hide_index=True, height=420)

        total = len(HORARIOS) * len(CANCHAS)
        ocupados_n = len(reservas_dia)
        c1, c2, c3 = st.columns(3)
        c1.metric("Turnos totales", total)
        c2.metric("Ocupados", ocupados_n)
        c3.metric("Libres", total - ocupados_n)

    # ---------- MIS RESERVAS ----------
    elif pagina == "Mis Reservas":
        header_club("Mis reservas")

        reservas = cargar_reservas()
        hoy = datetime.now().date()
        mias = [
            r for r in reservas
            if r.get("socio_id") == socio["id"]
            and datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= hoy
        ]
        mias = sorted(mias, key=lambda x: (x["fecha"], x["horario"]))

        if not mias:
            st.info("No tenés reservas próximas.")
        else:
            st.markdown(f"**{len(mias)} reserva(s)**")
            for r in mias:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        pago_txt = (
                            '<span class="pago-ok">✅ Pagado</span>'
                            if r.get("pagado")
                            else '<span class="pago-pendiente">⏳ Pendiente</span>'
                        )
                        st.markdown(
                            f"**{r['cancha']}** · {r['fecha']} · **{r['horario']}** (90 min)  \n"
                            f"💰 {format_precio(r['precio'])} · {r['metodo_pago']} · {pago_txt}",
                            unsafe_allow_html=True
                        )
                    with col2:
                        if not r.get("pagado"):
                            if st.button("💳 Marcar pago", key=f"pay_{r['id']}"):
                                marcar_pagado(r["id"])
                                st.rerun()
                    with col3:
                        if st.button("🗑️ Cancelar", key=f"cancel_{r['id']}"):
                            cancelar_reserva(r["id"])
                            st.success("Reserva cancelada.")
                            st.rerun()

                    with st.expander("Reenviar confirmación"):
                        wa = link_whatsapp(r)
                        st.link_button("📱 WhatsApp", wa)
                        if st.button("✉️ Email", key=f"mail_{r['id']}"):
                            ok_m, msg_m = enviar_email(r)
                            if ok_m:
                                st.success(msg_m)
                            else:
                                st.warning(msg_m)

    # ---------- PRECIOS ----------
    elif pagina == "Precios":
        header_club("Lista de precios")

        st.markdown(f"""
        | Tipo | Horario | Precio (90 min) |
        |------|---------|-----------------|
        | **Normal** | 08:00 – 15:30 | {format_precio(PRECIO_NORMAL)} |
        | **Pico** | 17:00 – 20:00 | {format_precio(PRECIO_PICO)} |
        """)

        st.markdown("#### Métodos de pago aceptados")
        st.markdown("""
        - 💵 **Efectivo** en el club (pagás al llegar)
        - 🏦 **Transferencia** bancaria (CBU / Alias)
        - 💙 **Mercado Pago** (simulado en esta demo)
        """)
        st.info("Los precios son por cancha y por turno de 90 minutos. Incluyen uso de red y vestuarios.")

    # ---------- ADMINISTRACIÓN ----------
    elif pagina == "Administración":
        header_club("Administración")

        tab_res, tab_soc, tab_cfg = st.tabs(["Reservas", "Socios", "Notificaciones"])

        with tab_res:
            reservas = cargar_reservas()
            hoy = datetime.now().date()
            proximas = [
                r for r in reservas
                if datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= hoy
            ]
            st.metric("Reservas próximas", len(proximas))

            if proximas:
                df = pd.DataFrame(proximas)
                cols = ["fecha", "horario", "cancha", "nombre", "precio", "metodo_pago", "pagado", "telefono"]
                cols = [c for c in cols if c in df.columns]
                df = df[cols].sort_values(["fecha", "horario"])
                st.dataframe(df, use_container_width=True, hide_index=True)

            if st.button("🧹 Limpiar reservas pasadas"):
                limpiar_reservas_antiguas()
                st.success("Listo.")
                st.rerun()

            if st.button("⚠️ Borrar TODAS las reservas", type="primary"):
                guardar_reservas([])
                st.warning("Todas eliminadas.")
                st.rerun()

        with tab_soc:
            socios = cargar_socios()
            df_s = pd.DataFrame([
                {
                    "ID": s["id"],
                    "Nombre": s["nombre"],
                    "Email": s["email"],
                    "Teléfono": s["telefono"],
                    "Activo": s.get("activo", True)
                }
                for s in socios
            ])
            st.dataframe(df_s, use_container_width=True, hide_index=True)
            st.caption(f"Total socios: {len(socios)}")

        with tab_cfg:
            st.markdown("#### Configuración de Email (SMTP)")
            st.caption("Para enviar confirmaciones reales por email. Dejá vacío para solo simular.")
            cfg = cargar_config()

            smtp_host = st.text_input("SMTP Host", value=cfg.get("smtp_host", ""), placeholder="smtp.gmail.com")
            smtp_port = st.number_input("Puerto", value=int(cfg.get("smtp_port", 587)), min_value=1, max_value=65535)
            smtp_user = st.text_input("Usuario SMTP", value=cfg.get("smtp_user", ""))
            smtp_pass = st.text_input("Contraseña / App Password", value=cfg.get("smtp_pass", ""), type="password")
            email_from = st.text_input("Email remitente", value=cfg.get("email_from", ""), placeholder="reservas@clubtenis.com")

            st.markdown("#### WhatsApp")
            st.caption("El botón de WhatsApp abre WhatsApp Web con el mensaje listo para el teléfono del socio.")
            wa_club = st.text_input(
                "Número del club (opcional)",
                value=cfg.get("whatsapp_numero_club", ""),
                placeholder="54911..."
            )

            if st.button("💾 Guardar configuración", type="primary"):
                guardar_config({
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port,
                    "smtp_user": smtp_user,
                    "smtp_pass": smtp_pass,
                    "email_from": email_from,
                    "whatsapp_numero_club": wa_club
                })
                st.success("Configuración guardada.")

    st.markdown(
        '<div class="footer">🎾 Club de Tenis · Reservas · Turnos de 90 min</div>',
        unsafe_allow_html=True
    )


# ============================================================
# ROUTER
# ============================================================

if st.session_state.socio is None:
    pantalla_login()
else:
    pantalla_app()
