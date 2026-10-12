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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cargar_reservas(): return cargar_json(RESERVAS_FILE, [])
def guardar_reservas(reservas): guardar_json(RESERVAS_FILE, reservas)
def cargar_socios(): return cargar_json(SOCIOS_FILE, [])
def guardar_socios(socios): guardar_json(SOCIOS_FILE, socios)

def cargar_config():
    return cargar_json(CONFIG_FILE, {
        "smtp_host": "", "smtp_port": 587, "smtp_user": "",
        "smtp_pass": "", "email_from": "", "whatsapp_numero_club": ""
    })

def guardar_config(cfg): guardar_json(CONFIG_FILE, cfg)

# ============================================================
# SOCIOS / LOGIN
# ============================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def inicializar_socios_demo():
    socios = cargar_socios()
    if not socios:
        socios = [
            {"id": "S001", "nombre": "Juan Pérez", "email": "juan@email.com", "telefono": "11 5555-0001", "password": hash_password("1234"), "activo": True},
            {"id": "S002", "nombre": "María Gómez", "email": "maria@email.com", "telefono": "11 5555-0002", "password": hash_password("1234"), "activo": True},
            {"id": "S003", "nombre": "Carlos López", "email": "carlos@email.com", "telefono": "11 5555-0003", "password": hash_password("1234"), "activo": True},
        ]
        guardar_socios(socios)
    return socios

def autenticar(socio_id: str, password: str):
    for s in cargar_socios():
        if s["id"].upper() == socio_id.upper() and s["password"] == hash_password(password) and s.get("activo", True):
            return s
    return None

def registrar_socio(nombre, email, telefono, password):
    socios = cargar_socios()
    nums = [int(s["id"][1:]) for s in socios if s["id"].startswith("S") and s["id"][1:].isdigit()]
    nuevo_id = f"S{max(nums, default=0) + 1:03d}"

    if any(s["email"].lower() == email.lower() for s in socios):
        return None, "Ese email ya está registrado."

    nuevo = {
        "id": nuevo_id, "nombre": nombre.strip(), "email": email.strip().lower(),
        "telefono": telefono.strip(), "password": hash_password(password), "activo": True
    }
    socios.append(nuevo)
    guardar_socios(socios)
    return nuevo, f"Socio registrado. Tu ID es **{nuevo_id}**."

def actualizar_socio(socio_id, nombre, email, telefono, password_nueva=None, activo=True):
    socios = cargar_socios()
    for s in socios:
        if s["id"] == socio_id:
            s["nombre"] = nombre.strip()
            s["email"] = email.strip().lower()
            s["telefono"] = telefono.strip()
            s["activo"] = activo
            if password_nueva and len(password_nueva.strip()) > 0:
                s["password"] = hash_password(password_nueva.strip())
            guardar_socios(socios)
            return True, "Socio actualizado correctamente."
    return False, "No se encontró el socio."

def eliminar_socio(socio_id):
    socios = cargar_socios()
    socios_filtrados = [s for s in socios if s["id"] != socio_id]
    if len(socios_filtrados) < len(socios):
        guardar_socios(socios_filtrados)
        return True, "Socio eliminado permanentemente."
    return False, "No se pudo encontrar al socio."

# ============================================================
# RESERVAS
# ============================================================

def obtener_reservas_dia(fecha_str):
    return [r for r in cargar_reservas() if r["fecha"] == fecha_str]

def esta_ocupada(fecha_str, cancha, horario):
    return any(r["cancha"] == cancha and r["horario"] == horario for r in obtener_reservas_dia(fecha_str))

def agregar_reserva(fecha_str, cancha, horario, socio, con_luz, metodo_pago):
    if esta_ocupada(fecha_str, cancha, horario):
        return False, None, "Esa cancha ya está reservada en ese horario."

    es_socio = socio is not None
    precio = get_precio(es_socio, con_luz)
    pagado = metodo_pago in ("Transferencia", "Mercado Pago (simulado)")

    reserva = {
        "id": f"{fecha_str}_{cancha}_{horario}_{datetime.now().timestamp()}",
        "fecha": fecha_str, "cancha": cancha, "horario": horario,
        "duracion": "60 min", 
        "socio_id": socio["id"] if es_socio else "INVITADO", 
        "nombre": socio["nombre"] if es_socio else "No socio",
        "email": socio["email"] if es_socio else "", 
        "telefono": socio["telefono"] if es_socio else "", 
        "precio": precio,
        "con_luz": con_luz,
        "metodo_pago": metodo_pago, "pagado": pagado,
        "creada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    reservas = cargar_reservas()
    reservas.append(reserva)
    guardar_reservas(reservas)
    return True, reserva, "¡Reserva confirmada!"

def cancelar_reserva(reserva_id):
    reservas = cargar_reservas()
    nuevas = [r for r in reservas if r["id"] != reserva_id]
    if len(nuevas) == len(reservas): return False
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
    nuevas = [r for r in reservas if datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= hoy]
    if len(nuevas) != len(reservas): guardar_reservas(nuevas)

# ============================================================
# CONFIRMACIONES (Email / WhatsApp)
# ============================================================

def mensaje_confirmacion(reserva: dict) -> str:
    estado_pago = "✅ Pagado" if reserva.get("pagado") else "⏳ Pendiente de pago"
    luz_txt = "💡 Con luz (Adicional incl.)" if reserva.get("con_luz") else "☀️ Sin luz"
    return (
        f"🎾 *Club de Tenis — Confirmación de Reserva*\n\n"
        f"Hola {reserva['nombre']},\n\n"
        f"Tu reserva quedó confirmada:\n"
        f"• *Cancha:* {reserva['cancha']}\n"
        f"• *Fecha:* {reserva['fecha']}\n"
        f"• *Horario:* {reserva['horario']} (60 min)\n"
        f"• *Detalle:* {luz_txt}\n"
        f"• *Precio:* {format_precio(reserva['precio'])}\n"
        f"• *Pago:* {reserva['metodo_pago']} — {estado_pago}\n\n"
        f"¡Te esperamos en la cancha!\nClub de Tenis"
    )

def mensaje_email_html(reserva: dict) -> str:
    estado = "Pagado ✅" if reserva.get("pagado") else "Pendiente de pago ⏳"
    luz_txt = "💡 Con luz" if reserva.get("con_luz") else "☀️ Sin luz"
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #166534;">
        <div style="max-width: 500px; margin: 0 auto; border: 2px solid #22C55E; border-radius: 12px; padding: 24px;">
            <h2>🎾 Club de Tenis</h2>
            <p>Hola <strong>{reserva['nombre']}</strong>,</p>
            <p>Tu reserva quedó confirmada:</p>
            <table style="width:100%; border-collapse: collapse;">
                <tr><td style="padding:6px 0;"><strong>Cancha</strong></td><td>{reserva['cancha']}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Fecha</strong></td><td>{reserva['fecha']}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Horario</strong></td><td>{reserva['horario']} (60 min)</td></tr>
                <tr><td style="padding:6px 0;"><strong>Iluminación</strong></td><td>{luz_txt}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Precio</strong></td><td>{format_precio(reserva['precio'])}</td></tr>
                <tr><td style="padding:6px 0;"><strong>Pago</strong></td><td>{reserva['metodo_pago']} — {estado}</td></tr>
            </table>
            <p style="margin-top: 20px;">¡Te esperamos en la cancha!</p>
        </div>
    </body>
    </html>
    """

def enviar_email(reserva: dict):
    cfg = cargar_config()
    if not cfg.get("smtp_host") or not cfg.get("smtp_user") or not cfg.get("smtp_pass") or not reserva.get("email"):
        return False, "Email no configurado o destinatario sin correo."
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
    encoded = urllib.parse.quote(mensaje_confirmacion(reserva))
    return f"https://wa.me/{telefono}?text={encoded}" if telefono else f"https://wa.me/?text={encoded}"

# ============================================================
# INICIALIZACIÓN
# ============================================================

aplicar_tema()
inicializar_socios_demo()
limpiar_reservas_antiguas()

if "socio" not in st.session_state:
    st.session_state.socio = None

if "admin_autenticado" not in st.session_state:
    st.session_state.admin_autenticado = False

# ============================================================
# PANTALLA DE LOGIN / REGISTRO
# ============================================================

def pantalla_login():
    header_club("Ingresá con tu cuenta de socio")
    tab_login, tab_registro = st.tabs(["🔑 Iniciar sesión", "📝 Registrarme"])

    with tab_login:
        st.markdown("#### Ingresá tus datos")
        col1, col2 = st.columns(2)
        with col1: socio_id = st.text_input("ID de socio", placeholder="Ej: S001", key="login_id")
        with col2: password = st.text_input("Contraseña", type="password", placeholder="••••", key="login_pass")

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
                st.error("Mínimo 4 caracteres.")
            else:
                socio, msg = registrar_socio(nombre, email, telefono, pass1)
                if socio:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)

# ============================================================
# APP PRINCIPAL
# ============================================================

def pantalla_app():
    socio = st.session_state.socio

    with st.sidebar:
        st.markdown(f"### 👤 {socio['nombre']}")
        st.caption(f"ID: {socio['id']}")
        st.divider()

        pagina = st.radio(
            "Menú",
            ["Nueva Reserva", "Ver Disponibilidad", "Mis Reservas", "Precios", "Administración"],
            label_visibility="collapsed"
        )

        st.divider()
        st.markdown("### Turnos")
        st.caption("Duración: **60 minutos**")
        st.caption("08:00 → 21:00")
        st.markdown("### Tarifas Base")
        st.caption(f"Socio: **{format_precio(PRECIO_SOCIO)}**")
        st.caption(f"No socio: **{format_precio(PRECIO_NO_SOCIO)}**")
        st.caption(f"Adicional Luz: **{format_precio(ADICIONAL_LUZ)}**")

        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.socio = None
            st.session_state.admin_autenticado = False
            st.rerun()

    # ---------- NUEVA RESERVA ----------
    if pagina == "Nueva Reserva":
        header_club("Nueva reserva · 60 minutos")

        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", min_value=datetime.now().date(), max_value=datetime.now().date() + timedelta(days=30), value=datetime.now().date())
            fecha_str = fecha.strftime("%Y-%m-%d")
        with col2:
            cancha = st.selectbox("Cancha", CANCHAS)

        st.markdown("#### Horarios disponibles")
        ocupados = {r["horario"] for r in obtener_reservas_dia(fecha_str) if r["cancha"] == cancha}
        libres = [h for h in HORARIOS if h not in ocupados]

        if fecha == datetime.now().date():
            ahora = datetime.now().time()
            libres = [h for h in libres if time.fromisoformat(h) > ahora]

        if not libres:
            st.warning("No hay horarios disponibles para esta cancha en esa fecha.")
        else:
            opciones = [f"{h} hs" for h in libres]
            idx = st.selectbox("Horario", range(len(opciones)), format_func=lambda i: opciones[i])
            horario = libres[idx]

            con_luz = st.checkbox("💡 Incluir Adicional Luz (+ $ 3.200)")

            precio_total = get_precio(True, con_luz)
            st.markdown(f'<span class="precio-badge">Total: {format_precio(precio_total)} · 60 min</span>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### Pago")
            metodo = st.radio("Método de pago", ["Efectivo (en club)", "Transferencia", "Mercado Pago (simulado)"], horizontal=True)

            if metodo == "Transferencia":
                st.info("Transferí a **CBU 0000003100010000000001** · Alias: **CLUB.TENIS**")

            if st.button("✅ Confirmar Reserva", type="primary", use_container_width=True):
                ok, reserva, msg = agregar_reserva(fecha_str, cancha, horario, socio, con_luz, metodo)
                if ok:
                    st.success(msg)
                    st.balloons()
                    with st.container(border=True):
                        estado = "✅ Pagado" if reserva["pagado"] else "⏳ Pendiente"
                        luz_txt = "💡 Con luz" if reserva["con_luz"] else "☀️ Sin luz"
                        st.markdown(f"**{reserva['cancha']}** · {fecha.strftime('%d/%m/%Y')} · **{horario} hs** ({luz_txt}) \\\n💰 {format_precio(reserva['precio'])} · {estado}")
                    
                    c1, c2 = st.columns(2)
                    with c1: st.link_button("📱 WhatsApp", link_whatsapp(reserva), use_container_width=True)
                    with c2: 
                        if st.button("✉️ Enviar Email", use_container_width=True):
                            ok_m, msg_m = enviar_email(reserva)
                            (st.success(msg_m) if ok_m else st.warning(msg_m))
                else:
                    st.error(msg)

    # ---------- DISPONIBILIDAD ----------
    elif pagina == "Ver Disponibilidad":
        header_club("Disponibilidad de canchas")
        fecha = st.date_input("Fecha", min_value=datetime.now().date(), max_value=datetime.now().date() + timedelta(days=30), value=datetime.now().date(), key="disp_fecha")
        fecha_str = fecha.strftime("%Y-%m-%d")
        reservas_dia = obtener_reservas_dia(fecha_str)

        datos = []
        precio_base_str = format_precio(PRECIO_SOCIO)
        for horario in HORARIOS:
            fila = {"Horario": f"{horario} hs"}
            for cancha in CANCHAS:
                r = next((x for x in reservas_dia if x["cancha"] == cancha and x["horario"] == horario), None)
                fila[cancha] = f"🔴 {r['nombre']}" if r else f"🟢 {precio_base_str}"
            datos.append(fila)

        st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True)

    # ---------- MIS RESERVAS ----------
    elif pagina == "Mis Reservas":
        header_club("Mis reservas")
        hoy = datetime.now().date()
        mias = sorted([r for r in cargar_reservas() if r.get("socio_id") == socio["id"] and datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= hoy], key=lambda x: (x["fecha"], x["horario"]))

        if not mias:
            st.info("No tenés reservas próximas.")
        else:
            for r in mias:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        pago_txt = '<span class="pago-ok">✅ Pagado</span>' if r.get("pagado") else '<span class="pago-pendiente">⏳ Pendiente</span>'
                        luz_txt = "💡 Con luz" if r.get("con_luz") else "☀️ Sin luz"
                        st.markdown(f"**{r['cancha']}** · {r['fecha']} · **{r['horario']} hs** ({luz_txt}) \\\n💰 {format_precio(r['precio'])} · {pago_txt}", unsafe_allow_html=True)
                    with c2:
                        if not r.get("pagado") and st.button("💳 Pagar", key=f"pay_{r['id']}"):
                            marcar_pagado(r["id"])
                            st.rerun()
                    with c3:
                        if st.button("🗑️ Cancelar", key=f"cancel_{r['id']}"):
                            cancelar_reserva(r["id"])
                            st.rerun()

    # ---------- PRECIOS ----------
    elif pagina == "Precios":
        header_club("Aranceles de Tenis (Vigente a partir del 01/10/26)")
        st.markdown(f"""
        | Categoría / Concepto | Detalle | Precio |
        |---|---|---|
        | **Diario** | Socio Mayor de 11 Años | {format_precio(8500)} |
        | **Diario** | Socio Menor de 10 Años | {format_precio(7500)} |
        | **Mensual** | Socio Mayor 11 Años | {format_precio(29500)} |
        | **Mensual** | Socio Menor de 10 Años | {format_precio(18000)} |
        | **Trimestral** | Socio Mayor 11 Años | {format_precio(70000)} |
        | **Trimestral** | Socio Menor de 10 Años | {format_precio(35000)} |
        | **Invitados** | Mayores de 11 Años | {format_precio(22000)} |
        | **Invitados** | Menores de 10 Años | {format_precio(15000)} |
        | **Adicional Luz** | La hora | {format_precio(3200)} |
        | **Adicional Luz** | 1/2 hora | {format_precio(1600)} |
        """)

    # ---------- ADMINISTRACIÓN ----------
    elif pagina == "Administración":
        header_club("Panel de Administración")

        if not st.session_state.admin_autenticado:
            st.warning("⚠️ Esta sección requiere credenciales de Administrador.")
            with st.form("form_login_admin"):
                adm_user = st.text_input("Usuario administrador")
                adm_pass = st.text_input("Contraseña", type="password")
                btn_ingresar_adm = st.form_submit_button("Ingresar como Administrador", type="primary")

                if btn_ingresar_adm:
                    if adm_user == "admin" and adm_pass == "2345":
                        st.session_state.admin_autenticado = True
                        st.success("¡Acceso concedido!")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña de administrador incorrectos.")
        else:
            col_salir_adm, _ = st.columns([1, 4])
            with col_salir_adm:
                if st.button("🔒 Cerrar Sesión Admin"):
                    st.session_state.admin_autenticado = False
                    st.rerun()

            tab_res, tab_soc, tab_cfg = st.tabs(["Reservas", "Gestión de Socios", "Notificaciones"])

            with tab_res:
                proximas = [r for r in cargar_reservas() if datetime.strptime(r["fecha"], "%Y-%m-%d").date() >= datetime.now().date()]
                if proximas:
                    st.dataframe(pd.DataFrame(proximas)[["fecha", "horario", "cancha", "nombre", "precio", "con_luz", "metodo_pago", "pagado"]], use_container_width=True, hide_index=True)
                if st.button("⚠️ Borrar TODAS las reservas", type="primary"):
                    guardar_reservas([])
                    st.rerun()

            with tab_soc:
                st.markdown("### 👥 Administración de Usuarios / Socios")
                socios = cargar_socios()

                df_soc = pd.DataFrame(socios)
                if not df_soc.empty and "password" in df_soc.columns:
                    df_soc_view = df_soc.drop(columns=["password"])
                else:
                    df_soc_view = df_soc

                st.dataframe(df_soc_view, use_container_width=True, hide_index=True)

                st.divider()
                
                st.markdown("#### ✏️ Modificar o Eliminar un Socio")
                opciones_socios = {f"{s['id']} - {s['nombre']} ({s['email']})": s for s in socios}
                
                if opciones_socios:
                    socio_sel_key = st.selectbox("Seleccioná un socio a gestionar", list(opciones_socios.keys()))
                    s_sel = opciones_socios[socio_sel_key]

                    with st.form("form_edit_socio"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            edit_nombre = st.text_input("Nombre completo", value=s_sel["nombre"])
                            edit_email = st.text_input("Email", value=s_sel["email"])
                        with col_b:
                            edit_tel = st.text_input("Teléfono", value=s_sel["telefono"])
                            edit_pass = st.text_input("Nueva Contraseña (dejar en blanco para mantener)", type="password")
                        
                        edit_activo = st.checkbox("Cuenta Activa", value=s_sel.get("activo", True))

                        if st.form_submit_button("💾 Guardar Cambios"):
                            ok, msg = actualizar_socio(s_sel["id"], edit_nombre, edit_email, edit_tel, edit_pass, edit_activo)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                    st.markdown("##### 🗑️ Eliminar Socio")
                    confirmar_del = st.checkbox(f"Confirmar que deseas eliminar a **{s_sel['nombre']}** ({s_sel['id']})", key=f"del_chk_{s_sel['id']}")
                    if st.button("❌ Eliminar Socio Permanentemente", type="primary", key=f"btn_del_{s_sel['id']}"):
                        if confirmar_del:
                            ok_del, msg_del = eliminar_socio(s_sel["id"])
                            if ok_del:
                                if socio["id"] == s_sel["id"]:
                                    st.session_state.socio = None
                                st.success(msg_del)
                                st.rerun()
                            else:
                                st.error(msg_del)
                        else:
                            st.warning("Debes marcar la casilla de confirmación para eliminar al socio.")

                st.divider()
                st.markdown("#### ➕ Registrar Nuevo Socio Manualmente")
                with st.form("form_nuevo_socio"):
                    c1, c2 = st.columns(2)
                    with c1:
                        new_nombre = st.text_input("Nombre completo")
                        new_email = st.text_input("Email")
                    with c2:
                        new_tel = st.text_input("Teléfono")
                        new_pass = st.text_input("Contraseña", type="password")
                    
                    if st.form_submit_button("➕ Crear Socio"):
                        if not all([new_nombre, new_email, new_tel, new_pass]):
                            st.error("Completá todos los campos.")
                        else:
                            ns, msg = registrar_socio(new_nombre, new_email, new_tel, new_pass)
                            if ns:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

            with tab_cfg:
                cfg = cargar_config()
                smtp_host = st.text_input("SMTP Host", value=cfg.get("smtp_host", ""))
                smtp_port = st.number_input("Puerto", value=int(cfg.get("smtp_port", 587)))
                smtp_user = st.text_input("Usuario SMTP", value=cfg.get("smtp_user", ""))
                smtp_pass = st.text_input("Contraseña", value=cfg.get("smtp_pass", ""), type="password")
                email_from = st.text_input("Email remitente", value=cfg.get("email_from", ""))
                if st.button("💾 Guardar configuración", type="primary"):
                    guardar_config({"smtp_host": smtp_host, "smtp_port": smtp_port, "smtp_user": smtp_user, "smtp_pass": smtp_pass, "email_from": email_from})
                    st.success("Guardado.")

    st.markdown('<div class="footer">🎾 Club de Tenis · Turnos de 60 min</div>', unsafe_allow_html=True)

# ============================================================
# ROUTER
# ============================================================

if st.session_state.socio is None:
    pantalla_login()
else:
    pantalla_app()
