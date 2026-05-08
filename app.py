import streamlit as st
import sqlite3
import json
from datetime import date, datetime

# =====================================================
# S.I.V. - APP PRINCIPAL / VALIDACIÓN
#
# 1. Validación policial autoresponsable por NI.
# 2. ACTUACIONES: número de acta, fecha y repartición.
# 3. Bloques de trabajo.
# =====================================================

st.set_page_config(
    page_title="S.I.V. - Acta de Procedimiento",
    layout="wide",
    page_icon="🚔"
)

DB_APP = "siv_identidad_actuaciones.db"


def conn_db():
    conn = sqlite3.connect(DB_APP, check_same_thread=False)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS identidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ni TEXT,
        nombre TEXT,
        jerarquia TEXT,
        dependencia TEXT,
        rol_operativo TEXT,
        dispositivo TEXT,
        creado_en TEXT,
        ultimo_ingreso TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS actuaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ni TEXT,
        numero_acta TEXT,
        fecha TEXT,
        reparticion_dependencia TEXT,
        procedimiento_id TEXT,
        creado_en TEXT
    )
    """)

    conn.commit()
    return conn


def normalizar_ni(ni):
    return str(ni or "").replace(".", "").replace("-", "").replace(" ", "").strip()


def crear_procedimiento_id(numero_acta, fecha, reparticion):
    base = f"{reparticion}-{fecha}-{numero_acta}".upper()
    salida = []
    for c in base:
        if c.isalnum():
            salida.append(c)
        elif c in [" ", "-", "_", "/", "."]:
            salida.append("-")
    proc = "".join(salida)
    while "--" in proc:
        proc = proc.replace("--", "-")
    return proc.strip("-")


def guardar_identidad(identidad):
    conn = conn_db()
    c = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
    INSERT INTO identidades
    (ni, nombre, jerarquia, dependencia, rol_operativo, dispositivo, creado_en, ultimo_ingreso)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        identidad.get("ni", ""),
        identidad.get("nombre", ""),
        identidad.get("jerarquia", ""),
        identidad.get("dependencia", ""),
        identidad.get("rol_operativo", ""),
        identidad.get("dispositivo", "celular validado"),
        ahora,
        ahora
    ))
    conn.commit()
    conn.close()


def guardar_actuacion(ni, actuacion):
    conn = conn_db()
    c = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
    INSERT INTO actuaciones
    (ni, numero_acta, fecha, reparticion_dependencia, procedimiento_id, creado_en)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        ni,
        actuacion.get("numero_acta", ""),
        actuacion.get("fecha", ""),
        actuacion.get("reparticion_dependencia", ""),
        actuacion.get("procedimiento_id", ""),
        ahora
    ))
    conn.commit()
    conn.close()


def mostrar_estado_sidebar():
    st.sidebar.markdown("## 🚔 S.I.V.")

    identidad = st.session_state.get("identidad_policial")
    actuacion = st.session_state.get("actuacion")

    if identidad:
        st.sidebar.success("Identidad validada")
        st.sidebar.write(f"**NI:** {identidad.get('ni_formateado', identidad.get('ni', ''))}")
        st.sidebar.write(f"**Nombre:** {identidad.get('nombre', '')}")
        st.sidebar.write(f"**Rol:** {identidad.get('rol_operativo', '')}")
    else:
        st.sidebar.warning("Identidad pendiente")

    if actuacion:
        st.sidebar.success("Actuación activa")
        st.sidebar.write(f"**Acta:** {actuacion.get('numero_acta', '')}")
        st.sidebar.write(f"**Fecha:** {actuacion.get('fecha', '')}")
        st.sidebar.write(f"**Repartición:** {actuacion.get('reparticion_dependencia', '')}")
    else:
        st.sidebar.warning("Actuación pendiente")

    st.sidebar.divider()

    if st.sidebar.button("🔄 Cambiar identidad / actuación", use_container_width=True):
        for k in ["identidad_policial", "actuacion"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()


# =====================================================
# INICIO
# =====================================================

mostrar_estado_sidebar()

st.title("🚔 S.I.V. - ACTA DE PROCEDIMIENTO")
st.subheader("Sistema modular de actas policiales - Policía de Santa Fe")

# =====================================================
# 1. IDENTIDAD POLICIAL
# =====================================================

if "identidad_policial" not in st.session_state:
    st.markdown("## 1. IDENTIDAD POLICIAL")
    st.info("Validación autoresponsable: el NI funciona como PIN e identidad funcional del policía.")

    with st.form("form_identidad_policial"):
        c1, c2 = st.columns(2)

        with c1:
            ni_ingresado = st.text_input("NI / PIN policial", placeholder="Ej: 561.908")
            nombre = st.text_input("Nombre y apellido", placeholder="Ej: CASTAÑEDA JUAN")
            jerarquia = st.text_input("Jerarquía", placeholder="Ej: Subcomisario")

        with c2:
            dependencia = st.text_input("Dependencia", placeholder="Ej: SUB COMISARIA 18 - UR II")
            rol_operativo = st.selectbox(
                "Rol operativo en este procedimiento",
                ["Actante", "Colaborador", "Ambos"]
            )
            st.text_input("Dispositivo", value="celular validado", disabled=True)

        aceptar = st.checkbox(
            "Declaro bajo responsabilidad funcional que los datos ingresados corresponden a mi identidad policial."
        )

        submit = st.form_submit_button("✅ Validar identidad policial", use_container_width=True)

        if submit:
            ni_normalizado = normalizar_ni(ni_ingresado)

            if not ni_normalizado or not nombre or not jerarquia or not dependencia:
                st.error("Debe completar NI, nombre, jerarquía y dependencia.")
            elif not aceptar:
                st.error("Debe aceptar la validación autoresponsable.")
            else:
                identidad = {
                    "ni": ni_normalizado,
                    "ni_formateado": ni_ingresado,
                    "nombre": nombre.upper().strip(),
                    "jerarquia": jerarquia.strip(),
                    "dependencia": dependencia.upper().strip(),
                    "rol_operativo": rol_operativo,
                    "dispositivo": "celular validado",
                    "fecha_hora_validacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                st.session_state["identidad_policial"] = identidad
                guardar_identidad(identidad)
                st.success("Identidad policial validada.")
                st.rerun()

    st.stop()


identidad = st.session_state["identidad_policial"]

st.success(
    f"Identidad validada: NI {identidad.get('ni_formateado', identidad.get('ni'))} - "
    f"{identidad.get('nombre')} - {identidad.get('jerarquia')} - "
    f"{identidad.get('dependencia')} - Rol: {identidad.get('rol_operativo')}"
)

# =====================================================
# 2. ACTUACIONES
# =====================================================

if "actuacion" not in st.session_state:
    st.markdown("## 2. ACTUACIONES")
    st.warning("Antes de trabajar en los bloques, cargue los datos de la actuación. Todo JSON generado debe pertenecer a este procedimiento.")

    with st.form("form_actuaciones"):
        st.markdown("### ACTUACIONES")

        c1, c2, c3 = st.columns(3)

        with c1:
            numero_acta = st.text_input("Número de acta", placeholder="Ej: 123/26")

        with c2:
            fecha_acta = st.date_input("Fecha", value=date.today())

        with c3:
            reparticion = st.text_input(
                "Repartición / Dependencia",
                value=identidad.get("dependencia", ""),
                placeholder="Ej: SUB COMISARIA 18 - UR II"
            )

        submit_actuacion = st.form_submit_button("✅ Iniciar actuación", use_container_width=True)

        if submit_actuacion:
            if not numero_acta or not reparticion:
                st.error("Debe completar número de acta y repartición/dependencia.")
            else:
                procedimiento_id = crear_procedimiento_id(numero_acta, str(fecha_acta), reparticion)

                actuacion = {
                    "numero_acta": numero_acta.strip(),
                    "fecha": str(fecha_acta),
                    "reparticion_dependencia": reparticion.upper().strip(),
                    "procedimiento_id": procedimiento_id,
                    "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                st.session_state["actuacion"] = actuacion
                guardar_actuacion(identidad.get("ni", ""), actuacion)
                st.success("Actuación iniciada.")
                st.rerun()

    st.stop()


actuacion = st.session_state["actuacion"]

st.markdown("## 2. ACTUACIÓN ACTIVA")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Número de acta", actuacion.get("numero_acta", ""))
with c2:
    st.metric("Fecha", actuacion.get("fecha", ""))
with c3:
    st.metric("Repartición / Dependencia", actuacion.get("reparticion_dependencia", ""))

st.info("Todo lo que se cargue en los bloques debe quedar asociado a esta identidad policial y a esta actuación.")

# =====================================================
# 3. BLOQUES
# =====================================================

st.markdown("## 3. BLOQUES DE TRABAJO")

st.markdown("""
Seleccione el bloque correspondiente desde el menú lateral:

1. **BLOQUE 1 CORAZÓN** — datos base y relato del procedimiento.  
2. **BLOQUE 2 ARRESTADO** — aprehendido/arrestado.  
3. **BLOQUE 3 ENTREVISTA** — víctima/damnificado, noticia criminis y entrevista en primera persona.  
4. **BLOQUE 4 TESTIGO** — acta de entrevista a testigo.  
5. **BLOQUE 5 CONSULTA** — consultas y diligencias.  
6. **BLOQUE 6 CROQUIS** — inspección ocular, croquis, cámaras y fotos.  
7. **BLOQUE 7 SECUESTROS** — elementos, actas de secuestro y anexos.  
8. **BLOQUE 8 CONSOLIDADOR / CONSTRUCTOR** — acta principal y documentos finales.
""")

with st.expander("Ver datos técnicos que deben acompañar cada JSON"):
    st.json({
        "autor_carga": identidad,
        "actuacion": actuacion
    })

st.success("Sistema listo para trabajar. Ingrese al bloque que corresponda desde el menú lateral.")
