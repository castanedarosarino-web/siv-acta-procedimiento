import streamlit as st
import json
from fpdf import FPDF
import io
import tempfile
import os
from datetime import date, datetime

try:
    from streamlit_drawable_canvas import st_canvas
    from PIL import Image
    CANVAS_OK = True
except Exception:
    CANVAS_OK = False

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_OK = True
except Exception:
    GUARDADO_OK = False

# =====================================================
# BLOQUE 6 - INSPECCION OCULAR Y RELEVAMIENTO DE CAMARAS
# =====================================================

st.set_page_config(
    page_title="S.I.V.A.P. - Bloque 6 Inspección Ocular",
    layout="wide",
    page_icon="🔎"
)

BLOQUE_ID = "BLOQUE_6_INSPECCION_OCULAR"

if GUARDADO_OK:
    iniciar_guardado_seguro(BLOQUE_ID)
    panel_guardado_seguro(BLOQUE_ID)


# =====================================================
# UTILIDADES
# =====================================================

def limpiar_pdf(texto):
    if texto is None:
        return ""
    texto = str(texto)
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.",
        "–": "-", "—": "-",
        "“": '"', "”": '"', "’": "'",
        "🔎": "", "📷": "", "🎥": "", "📥": "", "📦": "", "➕": "", "🗑️": ""
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def guardar_temp(bytes_img, suffix=".png"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(bytes_img)
    tmp.close()
    return tmp.name


def firma_canvas_a_bytes(canvas_result):
    if not CANVAS_OK:
        return None
    if canvas_result is None or canvas_result.image_data is None:
        return None
    try:
        img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[3])
        buffer = io.BytesIO()
        fondo.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None


def pdf_texto(pdf, texto, alto=6):
    pdf.set_x(pdf.l_margin)
    ancho = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(ancho, alto, limpiar_pdf(texto))


def imagen_en_pdf(pdf, bytes_img, titulo="Imagen", max_w=170):
    if not bytes_img:
        return
    path = guardar_temp(bytes_img, ".jpg")
    try:
        pdf.set_font("Arial", "B", 10)
        pdf_texto(pdf, titulo, alto=5)
        y_actual = pdf.get_y()
        if y_actual > 220:
            pdf.add_page()
            y_actual = 20
        pdf.image(path, x=20, y=y_actual + 2, w=max_w)
        pdf.ln(95)
    except Exception:
        pdf_texto(pdf, "No se pudo insertar la imagen en el PDF.")
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def generar_pdf_acta(datos, camaras, fotos_bytes, anexos_bytes):
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "UNIDAD REGIONAL II - ROSARIO", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 9, "ACTA DE INSPECCION OCULAR Y RELEVAMIENTO DE CAMARAS", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "1. DATOS GENERALES", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_texto(pdf,
        f"Fecha: {datos.get('fecha','')} - Hora: {datos.get('hora','')}\n"
        f"Lugar inspeccionado: {datos.get('lugar','')}\n"
        f"Dependencia: {datos.get('dependencia','')}\n"
        f"Personal actuante: {datos.get('personal','')}\n"
        f"Movil policial: {datos.get('movil','')}"
    )
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "2. PRESERVACION DEL LUGAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_texto(pdf,
        f"Lugar preservado: {datos.get('preservado','')}\n"
        f"Personal que preserva: {datos.get('personal_preserva','')}\n"
        f"Observaciones: {datos.get('obs_preservacion','')}"
    )
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "3. CARACTERISTICAS DEL LUGAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_texto(pdf,
        f"Estado del lugar: {datos.get('estado_lugar','')}\n"
        f"Iluminacion: {datos.get('iluminacion','')}\n"
        f"Transito vehicular/peatonal: {datos.get('transito','')}\n"
        f"Condiciones climaticas: {datos.get('clima','')}\n"
        f"Observaciones del entorno: {datos.get('entorno','')}"
    )
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "4. RELATO DE INSPECCION OCULAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_texto(pdf, datos.get("relato_inspeccion", ""), alto=7)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "5. ELEMENTOS OBSERVADOS / DATOS DE INTERES", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_texto(pdf, datos.get("elementos_interes", ""), alto=7)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "6. RELEVAMIENTO DE CAMARAS", ln=True)
    pdf.set_font("Arial", "", 10)

    if camaras:
        for i, cam in enumerate(camaras, start=1):
            pdf.set_font("Arial", "B", 10)
            pdf_texto(pdf, f"Camara Nro. {i}", alto=6)
            pdf.set_font("Arial", "", 10)
            pdf_texto(pdf,
                f"Tipo: {cam.get('tipo','')}\n"
                f"Ubicacion: {cam.get('ubicacion','')}\n"
                f"Orientacion / sector que capta: {cam.get('orientacion','')}\n"
                f"Responsable / propietario: {cam.get('duenio','')} - DNI: {cam.get('dni_duenio','')} - Telefono: {cam.get('telefono_duenio','')}\n"
                f"Conformidad / informacion obtenida: {cam.get('conformidad','')}\n"
                f"Observaciones: {cam.get('observaciones','')}",
                alto=6
            )

            firma_bytes = cam.get("firma_duenio_bytes")
            if cam.get("tipo") == "Privada" and firma_bytes:
                try:
                    path_firma = guardar_temp(firma_bytes, ".png")
                    pdf.set_font("Arial", "B", 9)
                    pdf_texto(pdf, "Firma digital del responsable:", alto=5)
                    pdf.image(path_firma, x=25, w=70)
                    pdf.ln(7)
                    os.unlink(path_firma)
                except Exception:
                    pass

            if cam.get("tipo") == "Privada":
                pdf.ln(4)
                pdf.cell(85, 7, "____________________________", ln=False, align="C")
                pdf.cell(85, 7, "____________________________", ln=True, align="C")
                pdf.cell(85, 6, "Firma responsable", ln=False, align="C")
                pdf.cell(85, 6, "Firma personal actuante", ln=True, align="C")
                pdf.ln(4)
    else:
        pdf_texto(pdf, "No se registraron camaras en el presente relevamiento.")

    if fotos_bytes:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "ANEXO FOTOGRAFICO DEL LUGAR", ln=True, align="C")
        pdf.ln(4)
        for idx, foto in enumerate(fotos_bytes[:6], start=1):
            imagen_en_pdf(pdf, foto, titulo=f"Foto Nro. {idx}", max_w=150)

    if anexos_bytes:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "ANEXOS DE INSPECCION", ln=True, align="C")
        pdf.ln(4)
        for idx, anexo in enumerate(anexos_bytes[:6], start=1):
            imagen_en_pdf(pdf, anexo, titulo=f"Anexo Nro. {idx}", max_w=150)

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "Creado por S.I.V.A.P. - Sistema Integrado de Validacion de Actuaciones Policiales", align="R")
    return pdf_bytes(pdf)


# =====================================================
# ESTADO
# =====================================================

if "b6_camaras" not in st.session_state:
    st.session_state.b6_camaras = []


# =====================================================
# INTERFAZ
# =====================================================

st.title("🔎 BLOQUE 6 — INSPECCIÓN OCULAR")
st.subheader("Preservación del lugar, relato técnico, relevamiento de cámaras, fotos y anexos")

st.info("Este bloque registra la inspección ocular y genera el acta/anexos correspondientes para el actante y el consolidado final.")

tabs = st.tabs([
    "1. Datos y preservación",
    "2. Relato de inspección",
    "3. Cámaras",
    "4. Fotos y anexos",
    "5. PDF / JSON"
])

# =====================================================
# 1. DATOS Y PRESERVACION
# =====================================================
with tabs[0]:
    st.subheader("Datos generales del lugar")

    c1, c2 = st.columns(2)
    with c1:
        st.date_input("Fecha", value=date.today(), key="b6_fecha")
        st.time_input("Hora", key="b6_hora")
        st.text_area("Lugar inspeccionado", key="b6_lugar")
        st.text_input("Dependencia", key="b6_dependencia")
        st.text_input("Móvil policial", key="b6_movil")
    with c2:
        st.text_area("Personal actuante", key="b6_personal")
        st.radio("¿Lugar preservado?", ["SI", "NO", "PARCIAL"], horizontal=True, key="b6_preservado")
        st.text_input("Personal que preserva", key="b6_personal_preserva")
        st.text_area("Observaciones sobre preservación", key="b6_obs_preservacion")

    st.divider()
    st.subheader("Características generales")

    c3, c4 = st.columns(2)
    with c3:
        st.selectbox("Estado del lugar", ["", "Sin alteraciones visibles", "Alterado parcialmente", "Alterado", "No se puede determinar"], key="b6_estado_lugar")
        st.selectbox("Iluminación", ["", "Natural", "Artificial", "Escasa", "Sin iluminación", "No corresponde"], key="b6_iluminacion")
    with c4:
        st.selectbox("Tránsito vehicular / peatonal", ["", "Escaso", "Moderado", "Intenso", "Sin circulación al momento"], key="b6_transito")
        st.text_input("Condiciones climáticas", key="b6_clima")

    st.text_area("Observaciones del entorno", key="b6_entorno")

# =====================================================
# 2. RELATO
# =====================================================
with tabs[1]:
    st.subheader("Relato técnico / policial de la inspección ocular")

    st.text_area(
        "Relato de inspección ocular",
        height=300,
        placeholder="Ej: Constituido el personal actuante en el lugar, se observa...",
        key="b6_relato_inspeccion"
    )

    st.text_area(
        "Elementos observados / datos de interés para la investigación",
        height=180,
        placeholder="Ej: ubicación de víctima, vehículo, arma, vainas, manchas, cámaras, ingresos/egresos, daños visibles, rastros, referencias...",
        key="b6_elementos_interes"
    )

# =====================================================
# 3. CAMARAS
# =====================================================
with tabs[2]:
    st.subheader("Relevamiento de cámaras públicas y privadas")

    cam1, cam2 = st.columns(2)

    with cam1:
        tipo_camara = st.selectbox("Tipo de cámara", ["Pública", "Privada"], key="b6_tipo_camara")
        ubicacion_camara = st.text_area("Ubicación de la cámara", key="b6_ubicacion_camara")
        orientacion_camara = st.text_area("Orientación / sector que capta", key="b6_orientacion_camara")
        conformidad = st.selectbox(
            "Conformidad / información obtenida",
            ["No corresponde", "Autoriza visualización", "Autoriza entrega de copia", "No autoriza", "No se pudo contactar"],
            key="b6_conformidad_camara"
        )

    with cam2:
        duenio = st.text_input("Dueño / responsable", key="b6_duenio_camara")
        dni_duenio = st.text_input("DNI dueño / responsable", key="b6_dni_duenio_camara")
        telefono_duenio = st.text_input("Teléfono dueño / responsable", key="b6_telefono_duenio_camara")
        observaciones_camara = st.text_area("Observaciones", key="b6_observaciones_camara")

    firma_duenio_bytes = None
    if tipo_camara == "Privada":
        st.markdown("#### Firma digital del dueño/responsable")
        if CANVAS_OK:
            canvas_firma = st_canvas(
                fill_color="rgba(255, 255, 255, 1)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=150,
                width=500,
                drawing_mode="freedraw",
                key="b6_firma_duenio_camara_canvas"
            )
            firma_duenio_bytes = firma_canvas_a_bytes(canvas_firma)
        else:
            st.warning("Firma en pantalla no disponible. Puede dejar constancia en observaciones.")

    if st.button("➕ Agregar cámara relevada"):
        if not ubicacion_camara:
            st.error("Debe cargar ubicación de la cámara.")
        else:
            camara = {
                "id_camara": len(st.session_state.b6_camaras) + 1,
                "tipo": tipo_camara,
                "ubicacion": ubicacion_camara,
                "orientacion": orientacion_camara,
                "duenio": duenio,
                "dni_duenio": dni_duenio,
                "telefono_duenio": telefono_duenio,
                "conformidad": conformidad,
                "observaciones": observaciones_camara,
                "firma_duenio": "SI" if firma_duenio_bytes else "NO",
                "firma_duenio_bytes": firma_duenio_bytes
            }
            st.session_state.b6_camaras.append(camara)
            if GUARDADO_OK:
                autoguardar_bloque(BLOQUE_ID)
            st.success("Cámara agregada al relevamiento.")

    st.markdown("### Cámaras cargadas")
    if st.session_state.b6_camaras:
        for idx, cam in enumerate(st.session_state.b6_camaras, start=1):
            with st.expander(f"Cámara {idx} - {cam.get('tipo')} - {cam.get('ubicacion','')[:50]}"):
                st.write(f"**Ubicación:** {cam.get('ubicacion')}")
                st.write(f"**Orientación:** {cam.get('orientacion')}")
                st.write(f"**Dueño/responsable:** {cam.get('duenio')}")
                st.write(f"**Firma digital:** {cam.get('firma_duenio')}")
                if st.button(f"🗑️ Eliminar cámara {idx}", key=f"b6_eliminar_camara_{idx}"):
                    st.session_state.b6_camaras.pop(idx - 1)
                    for j, item in enumerate(st.session_state.b6_camaras, start=1):
                        item["id_camara"] = j
                    if GUARDADO_OK:
                        autoguardar_bloque(BLOQUE_ID)
                    st.rerun()
    else:
        st.info("Todavía no hay cámaras cargadas.")

# =====================================================
# 4. FOTOS Y ANEXOS
# =====================================================
with tabs[3]:
    st.subheader("Fotos y anexos de inspección")

    fotos = st.file_uploader(
        "Cargar fotos del lugar",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="b6_fotos_lugar"
    )

    if fotos:
        for f in fotos:
            data = f.getvalue()
            st.image(data, caption=f.name, width=320)
    else:
        st.info("No hay fotos cargadas.")

    st.divider()

    anexos = st.file_uploader(
        "Cargar otros anexos de inspección en imagen",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="b6_anexos_inspeccion"
    )

    if anexos:
        for f in anexos:
            data = f.getvalue()
            st.image(data, caption=f.name, width=320)
    else:
        st.info("No hay anexos cargados.")

# =====================================================
# 5. PDF / JSON
# =====================================================
with tabs[4]:
    st.subheader("Generar PDF integral y JSON para BLOQUE 8")

    datos = {
        "fecha": str(st.session_state.get("b6_fecha", date.today())),
        "hora": str(st.session_state.get("b6_hora", "")),
        "lugar": st.session_state.get("b6_lugar", ""),
        "dependencia": st.session_state.get("b6_dependencia", ""),
        "personal": st.session_state.get("b6_personal", ""),
        "movil": st.session_state.get("b6_movil", ""),
        "preservado": st.session_state.get("b6_preservado", ""),
        "personal_preserva": st.session_state.get("b6_personal_preserva", ""),
        "obs_preservacion": st.session_state.get("b6_obs_preservacion", ""),
        "estado_lugar": st.session_state.get("b6_estado_lugar", ""),
        "iluminacion": st.session_state.get("b6_iluminacion", ""),
        "transito": st.session_state.get("b6_transito", ""),
        "clima": st.session_state.get("b6_clima", ""),
        "entorno": st.session_state.get("b6_entorno", ""),
        "relato_inspeccion": st.session_state.get("b6_relato_inspeccion", ""),
        "elementos_interes": st.session_state.get("b6_elementos_interes", "")
    }

    fotos_actuales = []
    if "b6_fotos_lugar" in st.session_state and st.session_state.b6_fotos_lugar:
        try:
            for f in st.session_state.b6_fotos_lugar:
                fotos_actuales.append(f.getvalue())
        except Exception:
            fotos_actuales = []

    anexos_actuales = []
    if "b6_anexos_inspeccion" in st.session_state and st.session_state.b6_anexos_inspeccion:
        try:
            for f in st.session_state.b6_anexos_inspeccion:
                anexos_actuales.append(f.getvalue())
        except Exception:
            anexos_actuales = []

    camaras_json = []
    for cam in st.session_state.b6_camaras:
        cj = dict(cam)
        if cj.get("firma_duenio_bytes"):
            cj["firma_duenio_bytes"] = "[firma digital incorporada al PDF]"
        camaras_json.append(cj)

    resumen_camaras = [
        f"{cam.get('tipo','S/D')} ubicada en {cam.get('ubicacion','S/D')}, orientada/captando {cam.get('orientacion','S/D')}"
        for cam in st.session_state.b6_camaras
    ]

    resumen_para_acta = (
        f"Se realizo inspeccion ocular en {datos.get('lugar','S/D')}. "
        f"Lugar preservado: {datos.get('preservado','S/D')}. "
        f"Se relevaron {len(st.session_state.b6_camaras)} camara/s. "
        f"Se incorporaron {len(fotos_actuales)} foto/s del lugar y {len(anexos_actuales)} anexo/s de inspeccion. "
        f"Resumen: {datos.get('relato_inspeccion','')[:500]}"
    )

    datos_exportar = {
        "bloque": 6,
        "modulo": "BLOQUE_6_INSPECCION_OCULAR",
        "version": "inspeccion_ocular_camaras_fotos_anexos",
        "datos": datos,
        "camaras": camaras_json,
        "cantidad_fotos": len(fotos_actuales),
        "cantidad_anexos": len(anexos_actuales),
        "resumen_camaras": resumen_camaras,
        "resumen_para_acta_procedimiento": resumen_para_acta,
        "fecha_exportacion": datetime.now().isoformat()
    }

    pdf_integral = generar_pdf_acta(
        datos,
        st.session_state.b6_camaras,
        fotos_actuales,
        anexos_actuales
    )

    json_b6 = json.dumps(datos_exportar, ensure_ascii=False, indent=4)

    c1, c2 = st.columns(2)

    with c1:
        st.download_button(
            "📥 Descargar PDF integral BLOQUE 6",
            data=pdf_integral,
            file_name="Bloque_6_Inspeccion_Ocular.pdf",
            mime="application/pdf"
        )

    with c2:
        st.download_button(
            "📦 Descargar JSON BLOQUE 6",
            data=json_b6,
            file_name="bloque_6_inspeccion_ocular.json",
            mime="application/json"
        )

    with st.expander("Ver JSON BLOQUE 6"):
        st.code(json_b6, language="json")

# Guardado automático del bloque al finalizar la corrida
try:
    if GUARDADO_OK:
        autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
