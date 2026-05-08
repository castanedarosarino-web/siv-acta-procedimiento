import streamlit as st
import json
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io
import tempfile
import os
from datetime import datetime, date
from streamlit_drawable_canvas import st_canvas

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

# =====================================================
# BLOQUE 6 - INSPECCION OCULAR / CROQUIS / CAMARAS
#
# Version reconstruida integral:
# - Preservacion del lugar
# - Relato de inspeccion ocular
# - Relevamiento de camaras publicas y privadas
# - Firma digital del dueño/responsable de camara privada
# - Carga de fotos del lugar
# - Croquis demostrativo policial guiado, orientado al norte
# - PDF propio para imprimir/anexar
# - JSON para BLOQUE 8
#
# Regla:
# El croquis NO debe inventar. El policia carga puntos relevantes.
# El sistema dibuja un esquema simple, claro y util para el fiscal.
# =====================================================

st.set_page_config(
    page_title="S.I.V. - Bloque 6 Inspección Ocular y Croquis",
    layout="wide",
    page_icon="🗺️"
)

BLOQUE_ID = "BLOQUE_6_INSPECCION_CROQUIS"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)


# =====================================================
# UTILIDADES
# =====================================================

def limpiar_pdf(texto):
    if texto is None:
        return ""
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.",
        "–": "-", "—": "-",
        "“": '"', "”": '"', "’": "'",
        "✅": "", "⚠️": "", "🚨": "", "📍": "", "🧭": "", "🗺️": ""
    }
    texto = str(texto)
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def guardar_temp_imagen(bytes_img, suffix=".png"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(bytes_img)
    tmp.close()
    return tmp.name


def firma_canvas_a_bytes(canvas_result):
    if canvas_result is None or canvas_result.image_data is None:
        return None
    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
    # Si el canvas está vacío, igual puede traer fondo blanco. Se acepta como firma visual si el operador decide agregarla.
    fondo = Image.new("RGB", img.size, (255, 255, 255))
    fondo.paste(img, mask=img.split()[3])
    buffer = io.BytesIO()
    fondo.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def color_por_tipo(tipo):
    colores = {
        "Víctima / persona": (220, 40, 40),
        "Arrestado / sospechoso": (40, 80, 220),
        "Vehículo": (30, 130, 80),
        "Elemento secuestrado": (180, 100, 20),
        "Arma / indicio especial": (160, 40, 160),
        "Vaina / munición": (180, 80, 20),
        "Mancha / rastro": (150, 20, 20),
        "Cámara pública": (30, 120, 180),
        "Cámara privada": (20, 150, 150),
        "Ingreso / egreso": (80, 80, 80),
        "Referencia": (0, 0, 0),
        "Otro": (70, 70, 70),
    }
    return colores.get(tipo, (0, 0, 0))


def crear_croquis_guiado(datos, puntos):
    """
    Genera croquis demostrativo simple.
    No intenta adivinar desde fotos. Usa datos cargados por el policia.
    Coordenadas x/y expresadas de 0 a 100.
    """
    ancho, alto = 1100, 800
    margen = 70

    img = Image.new("RGB", (ancho, alto), "white")
    d = ImageDraw.Draw(img)

    try:
        font_titulo = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
        font_sub = ImageFont.truetype("DejaVuSans.ttf", 18)
        font = ImageFont.truetype("DejaVuSans.ttf", 16)
        font_chico = ImageFont.truetype("DejaVuSans.ttf", 14)
        font_num = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except Exception:
        font_titulo = font_sub = font = font_chico = font_num = None

    # Marco principal
    d.rectangle([30, 30, ancho - 30, alto - 30], outline=(0, 0, 0), width=3)
    d.text((50, 45), "CROQUIS DEMOSTRATIVO DEL LUGAR DEL HECHO", fill=(0, 0, 0), font=font_titulo)

    # Norte
    norte = datos.get("orientacion_norte", "Norte hacia arriba")
    cx, cy = ancho - 135, 120
    d.ellipse([cx - 38, cy - 38, cx + 38, cy + 38], outline=(0, 0, 0), width=2)

    if norte == "Norte hacia arriba":
        d.line([cx, cy + 30, cx, cy - 25], fill=(0, 0, 0), width=3)
        d.polygon([(cx, cy - 32), (cx - 10, cy - 5), (cx + 10, cy - 5)], fill=(0, 0, 0))
        d.text((cx - 8, cy - 65), "N", fill=(0, 0, 0), font=font_num)
    elif norte == "Norte hacia abajo":
        d.line([cx, cy - 30, cx, cy + 25], fill=(0, 0, 0), width=3)
        d.polygon([(cx, cy + 32), (cx - 10, cy + 5), (cx + 10, cy + 5)], fill=(0, 0, 0))
        d.text((cx - 8, cy + 45), "N", fill=(0, 0, 0), font=font_num)
    elif norte == "Norte hacia la derecha":
        d.line([cx - 30, cy, cx + 25, cy], fill=(0, 0, 0), width=3)
        d.polygon([(cx + 32, cy), (cx + 5, cy - 10), (cx + 5, cy + 10)], fill=(0, 0, 0))
        d.text((cx + 45, cy - 10), "N", fill=(0, 0, 0), font=font_num)
    else:
        d.line([cx + 30, cy, cx - 25, cy], fill=(0, 0, 0), width=3)
        d.polygon([(cx - 32, cy), (cx - 5, cy - 10), (cx - 5, cy + 10)], fill=(0, 0, 0))
        d.text((cx - 60, cy - 10), "N", fill=(0, 0, 0), font=font_num)

    d.text((ancho - 210, 170), norte, fill=(0, 0, 0), font=font_chico)

    # Área de dibujo
    area = [margen, 160, ancho - margen, 610]
    d.rectangle(area, outline=(0, 0, 0), width=2)

    # Calles / referencias principales
    calle_principal = datos.get("calle_principal", "")
    calle_transversal = datos.get("calle_transversal", "")
    referencia = datos.get("referencia_lugar", "")

    if calle_principal:
        d.line([area[0] + 20, (area[1] + area[3]) // 2, area[2] - 20, (area[1] + area[3]) // 2], fill=(160, 160, 160), width=18)
        d.text((area[0] + 30, (area[1] + area[3]) // 2 - 35), calle_principal, fill=(0, 0, 0), font=font)
    if calle_transversal:
        d.line([(area[0] + area[2]) // 2, area[1] + 20, (area[0] + area[2]) // 2, area[3] - 20], fill=(180, 180, 180), width=16)
        d.text(((area[0] + area[2]) // 2 + 12, area[1] + 25), calle_transversal, fill=(0, 0, 0), font=font)

    if referencia:
        d.text((area[0] + 20, area[3] - 35), f"Referencia: {referencia}", fill=(0, 0, 0), font=font_chico)

    # Puntos relevantes
    leyenda = []
    for i, p in enumerate(puntos, start=1):
        try:
            x_pct = float(p.get("x", 50))
            y_pct = float(p.get("y", 50))
        except Exception:
            x_pct, y_pct = 50, 50

        x_pct = max(0, min(100, x_pct))
        y_pct = max(0, min(100, y_pct))

        x = area[0] + int((area[2] - area[0]) * x_pct / 100)
        y = area[1] + int((area[3] - area[1]) * y_pct / 100)

        tipo = p.get("tipo", "Otro")
        etiqueta = p.get("etiqueta", f"Punto {i}")
        detalle = p.get("detalle", "")
        color = color_por_tipo(tipo)

        d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=color, outline=(0, 0, 0), width=2)
        d.text((x - 5, y - 10), str(i), fill=(255, 255, 255), font=font_num)
        d.text((x + 16, y - 10), etiqueta[:28], fill=(0, 0, 0), font=font_chico)

        leyenda.append(f"{i}. {tipo}: {etiqueta}" + (f" - {detalle}" if detalle else ""))

    # Leyenda
    d.text((50, 630), "LEYENDA / PUNTOS RELEVANTES:", fill=(0, 0, 0), font=font_sub)
    y = 660
    for item in leyenda[:8]:
        d.text((60, y), item[:120], fill=(0, 0, 0), font=font_chico)
        y += 22
    if len(leyenda) > 8:
        d.text((60, y), f"... y {len(leyenda) - 8} punto/s mas detallados en acta.", fill=(0, 0, 0), font=font_chico)

    # Pie
    d.text((50, alto - 55), "Croquis demostrativo generado por S.I.V. - Debe ser revisado por el personal actuante.", fill=(0, 0, 0), font=font_chico)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf_integral(datos, puntos, camaras, fotos_bytes, croquis_bytes):
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "UNIDAD REGIONAL II", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "ACTA DE INSPECCION OCULAR, CROQUIS Y RELEVAMIENTO", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. DATOS DEL LUGAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(
        f"Fecha: {datos.get('fecha','S/D')} - Hora: {datos.get('hora','S/D')}\n"
        f"Lugar inspeccionado: {datos.get('lugar','S/D')}\n"
        f"Dependencia: {datos.get('dependencia','S/D')}\n"
        f"Personal actuante: {datos.get('personal','S/D')}\n"
        f"Movil: {datos.get('movil','S/D')}"
    ))
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. PRESERVACION DEL LUGAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(
        f"Lugar preservado: {datos.get('preservado','S/D')}\n"
        f"Personal que preserva: {datos.get('personal_preserva','S/D')}\n"
        f"Observaciones de preservacion: {datos.get('obs_preservacion','')}"
    ))
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "3. RELATO DE INSPECCION OCULAR", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(datos.get("relato_inspeccion", "")), align="J")
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "4. PUNTOS RELEVANTES PARA CROQUIS", ln=True)
    pdf.set_font("Arial", "", 10)
    if puntos:
        for i, p in enumerate(puntos, start=1):
            pdf.multi_cell(0, 7, limpiar_pdf(f"{i}. {p.get('tipo','S/D')}: {p.get('etiqueta','S/D')} - {p.get('detalle','')} - Ubicacion x:{p.get('x')} y:{p.get('y')}"))
    else:
        pdf.multi_cell(0, 7, "No se cargaron puntos relevantes.")
    pdf.ln(2)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "5. RELEVAMIENTO DE CAMARAS", ln=True)
    pdf.set_font("Arial", "", 10)
    if camaras:
        for i, cam in enumerate(camaras, start=1):
            pdf.multi_cell(0, 7, limpiar_pdf(
                f"Camara Nro. {i} - Tipo: {cam.get('tipo','S/D')}\n"
                f"Ubicacion: {cam.get('ubicacion','S/D')}\n"
                f"Orientacion/cobertura: {cam.get('orientacion','S/D')}\n"
                f"Responsable/dueno: {cam.get('duenio','S/D')} - DNI: {cam.get('dni_duenio','S/D')} - Telefono: {cam.get('telefono_duenio','S/D')}\n"
                f"Conformidad/informacion: {cam.get('conformidad','S/D')}\n"
                f"Observaciones: {cam.get('observaciones','')}"
            ))

            # Firma digital del dueño/responsable de cámara privada
            firma_bytes = cam.get("firma_duenio_bytes")
            if cam.get("tipo") == "Privada" and firma_bytes:
                try:
                    path_firma = guardar_temp_imagen(firma_bytes, ".png")
                    pdf.set_font("Arial", "B", 10)
                    pdf.cell(0, 7, "Firma digital del dueno/responsable de camara privada:", ln=True)
                    pdf.image(path_firma, x=25, w=70)
                    try:
                        os.unlink(path_firma)
                    except Exception:
                        pass
                except Exception:
                    pass

            if cam.get("tipo") == "Privada":
                pdf.ln(4)
                pdf.cell(90, 7, "____________________________", ln=False, align="C")
                pdf.cell(90, 7, "____________________________", ln=True, align="C")
                pdf.cell(90, 6, "Firma dueno/responsable camara", ln=False, align="C")
                pdf.cell(90, 6, "Firma personal actuante", ln=True, align="C")
                pdf.ln(4)
    else:
        pdf.multi_cell(0, 7, "No se registraron camaras.")
    pdf.ln(2)

    # Croquis
    if croquis_bytes:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "CROQUIS DEMOSTRATIVO", ln=True, align="C")
        path_croquis = guardar_temp_imagen(croquis_bytes, ".png")
        try:
            pdf.image(path_croquis, x=10, y=25, w=190)
        finally:
            try:
                os.unlink(path_croquis)
            except Exception:
                pass

    # Fotos
    if fotos_bytes:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "ANEXO FOTOGRAFICO DEL LUGAR", ln=True, align="C")
        y = 25
        for idx, foto in enumerate(fotos_bytes[:4], start=1):
            path_foto = guardar_temp_imagen(foto, ".jpg")
            try:
                if y > 210:
                    pdf.add_page()
                    y = 20
                pdf.set_font("Arial", "B", 10)
                pdf.text(15, y, limpiar_pdf(f"Foto Nro. {idx}"))
                pdf.image(path_foto, x=15, y=y + 5, w=85)
                y += 75
            except Exception:
                pass
            finally:
                try:
                    os.unlink(path_foto)
                except Exception:
                    pass

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "Creado por Sub-Comisario Castaneda Juan - S.I.V.", align="R")
    return pdf_bytes(pdf)


# =====================================================
# SESSION STATE
# =====================================================

if "b6_puntos" not in st.session_state:
    st.session_state.b6_puntos = []

if "b6_camaras" not in st.session_state:
    st.session_state.b6_camaras = []

if "b6_firmas_camaras" not in st.session_state:
    st.session_state.b6_firmas_camaras = {}


# =====================================================
# INTERFAZ
# =====================================================

st.title("🗺️ BLOQUE 6 — INSPECCIÓN OCULAR, CROQUIS Y CÁMARAS")
st.subheader("Croquis policial guiado con sentido al norte, fotos, relato y relevamiento de cámaras")
st.warning("El croquis es demostrativo y guiado: el sistema no inventa. El personal carga puntos relevantes y revisa el resultado.")

tabs = st.tabs([
    "1. Datos y preservación",
    "2. Relato inspección",
    "3. Cámaras",
    "4. Croquis guiado",
    "5. Fotos",
    "6. PDF / JSON"
])

# =====================================================
# 1. DATOS Y PRESERVACION
# =====================================================
with tabs[0]:
    st.subheader("Datos generales del lugar")

    c1, c2 = st.columns(2)
    with c1:
        fecha = st.date_input("Fecha", value=date.today(), key="b6_fecha")
        hora = st.time_input("Hora", key="b6_hora")
        lugar = st.text_area("Lugar inspeccionado", key="b6_lugar")
        dependencia = st.text_input("Dependencia", key="b6_dependencia")
    with c2:
        personal = st.text_area("Personal actuante", key="b6_personal")
        movil = st.text_input("Móvil policial", key="b6_movil")
        preservado = st.radio("¿Lugar preservado?", ["SI", "NO", "PARCIAL"], horizontal=True, key="b6_preservado")
        personal_preserva = st.text_input("Personal que preserva", key="b6_personal_preserva")

    obs_preservacion = st.text_area("Observaciones sobre preservación del lugar", key="b6_obs_preservacion")

# =====================================================
# 2. RELATO
# =====================================================
with tabs[1]:
    st.subheader("Relato de inspección ocular")

    relato_inspeccion = st.text_area(
        "Relato técnico / policial de la inspección ocular",
        height=260,
        placeholder="Ej: Constituido el personal en el lugar, se observa...",
        key="b6_relato_inspeccion"
    )

    elementos_interes = st.text_area(
        "Elementos de importancia para el fiscal",
        height=150,
        placeholder="Ej: ubicación de víctima, vehículo, arma, vainas, manchas, cámaras, ingreso/egreso...",
        key="b6_elementos_interes"
    )

# =====================================================
# 3. CAMARAS
# =====================================================
with tabs[2]:
    st.subheader("Relevamiento de cámaras públicas y privadas")

    st.info("Para cámaras privadas se carga el dueño/responsable y se puede incorporar firma digital.")

    cam1, cam2 = st.columns(2)

    with cam1:
        tipo_camara = st.selectbox("Tipo de cámara", ["Pública", "Privada"], key="b6_tipo_camara")
        ubicacion_camara = st.text_area("Ubicación de la cámara", key="b6_ubicacion_camara")
        orientacion_camara = st.text_area("Orientación / qué sector capta", key="b6_orientacion_camara")
        conformidad = st.selectbox(
            "Conformidad / información obtenida",
            ["No corresponde", "Autoriza visualización", "Autoriza entrega de copia", "No autoriza", "No se pudo contactar"],
            key="b6_conformidad_camara"
        )

    with cam2:
        duenio = st.text_input("Dueño / responsable", key="b6_duenio_camara")
        dni_duenio = st.text_input("DNI dueño / responsable", key="b6_dni_duenio_camara")
        telefono_duenio = st.text_input("Teléfono dueño / responsable", key="b6_telefono_duenio_camara")
        observaciones_camara = st.text_area("Observaciones de la cámara", key="b6_observaciones_camara")

    firma_duenio_bytes = None
    if tipo_camara == "Privada":
        st.markdown("#### Firma digital del dueño/responsable de cámara privada")
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

    if st.button("➕ Agregar cámara relevada", use_container_width=True):
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
                "firma_duenio": "SÍ" if firma_duenio_bytes else "NO",
                "firma_duenio_bytes": firma_duenio_bytes
            }
            st.session_state.b6_camaras.append(camara)
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
                if st.button(f"Eliminar cámara {idx}", key=f"b6_eliminar_camara_{idx}"):
                    st.session_state.b6_camaras.pop(idx - 1)
                    for j, item in enumerate(st.session_state.b6_camaras, start=1):
                        item["id_camara"] = j
                    autoguardar_bloque(BLOQUE_ID)
                    st.rerun()
    else:
        st.info("Todavía no hay cámaras cargadas.")

# =====================================================
# 4. CROQUIS GUIADO
# =====================================================
with tabs[3]:
    st.subheader("Croquis demostrativo guiado")

    st.info("Cargue orientación norte, calles/referencias y puntos importantes. El sistema dibuja un esquema simple.")

    c1, c2 = st.columns(2)
    with c1:
        orientacion_norte = st.selectbox(
            "Sentido del norte en el croquis",
            ["Norte hacia arriba", "Norte hacia abajo", "Norte hacia la derecha", "Norte hacia la izquierda"],
            key="b6_orientacion_norte"
        )
        calle_principal = st.text_input("Calle / eje principal", key="b6_calle_principal")
        calle_transversal = st.text_input("Calle transversal / referencia secundaria", key="b6_calle_transversal")
    with c2:
        referencia_lugar = st.text_area("Referencia del lugar", key="b6_referencia_lugar")
        observacion_croquis = st.text_area("Observación para croquis", key="b6_observacion_croquis")

    st.markdown("### Agregar punto relevante al croquis")
    p1, p2, p3 = st.columns(3)
    with p1:
        tipo_punto = st.selectbox(
            "Tipo de punto",
            [
                "Víctima / persona",
                "Arrestado / sospechoso",
                "Vehículo",
                "Elemento secuestrado",
                "Arma / indicio especial",
                "Vaina / munición",
                "Mancha / rastro",
                "Cámara pública",
                "Cámara privada",
                "Ingreso / egreso",
                "Referencia",
                "Otro"
            ],
            key="b6_tipo_punto"
        )
        etiqueta_punto = st.text_input("Etiqueta corta", key="b6_etiqueta_punto")
    with p2:
        x_punto = st.slider("Ubicación horizontal X", 0, 100, 50, key="b6_x_punto")
        y_punto = st.slider("Ubicación vertical Y", 0, 100, 50, key="b6_y_punto")
    with p3:
        detalle_punto = st.text_area("Detalle", key="b6_detalle_punto")

    if st.button("➕ Agregar punto al croquis", use_container_width=True):
        if not etiqueta_punto:
            st.error("Debe cargar una etiqueta corta.")
        else:
            punto = {
                "id_punto": len(st.session_state.b6_puntos) + 1,
                "tipo": tipo_punto,
                "etiqueta": etiqueta_punto,
                "detalle": detalle_punto,
                "x": x_punto,
                "y": y_punto
            }
            st.session_state.b6_puntos.append(punto)
            autoguardar_bloque(BLOQUE_ID)
            st.success("Punto agregado al croquis.")

    st.markdown("### Puntos cargados")
    if st.session_state.b6_puntos:
        for idx, p in enumerate(st.session_state.b6_puntos, start=1):
            with st.expander(f"{idx}. {p.get('tipo')} - {p.get('etiqueta')}"):
                st.json(p)
                if st.button(f"Eliminar punto {idx}", key=f"b6_eliminar_punto_{idx}"):
                    st.session_state.b6_puntos.pop(idx - 1)
                    for j, item in enumerate(st.session_state.b6_puntos, start=1):
                        item["id_punto"] = j
                    autoguardar_bloque(BLOQUE_ID)
                    st.rerun()
    else:
        st.info("Todavía no hay puntos cargados.")

# =====================================================
# 5. FOTOS
# =====================================================
with tabs[4]:
    st.subheader("Fotos del lugar")

    fotos = st.file_uploader(
        "Cargar fotos del lugar",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="b6_fotos_lugar"
    )

    fotos_bytes = []
    if fotos:
        for f in fotos:
            data = f.getvalue()
            fotos_bytes.append(data)
            st.image(data, caption=f.name, width=320)
    else:
        st.info("No hay fotos cargadas.")

# =====================================================
# 6. PDF / JSON
# =====================================================
with tabs[5]:
    st.subheader("Generar croquis, PDF integral y JSON para BLOQUE 8")

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
        "relato_inspeccion": st.session_state.get("b6_relato_inspeccion", ""),
        "elementos_interes": st.session_state.get("b6_elementos_interes", ""),
        "orientacion_norte": st.session_state.get("b6_orientacion_norte", "Norte hacia arriba"),
        "calle_principal": st.session_state.get("b6_calle_principal", ""),
        "calle_transversal": st.session_state.get("b6_calle_transversal", ""),
        "referencia_lugar": st.session_state.get("b6_referencia_lugar", ""),
        "observacion_croquis": st.session_state.get("b6_observacion_croquis", "")
    }

    # Fotos actuales desde uploader si existen
    fotos_actuales = []
    if "b6_fotos_lugar" in st.session_state and st.session_state.b6_fotos_lugar:
        try:
            for f in st.session_state.b6_fotos_lugar:
                fotos_actuales.append(f.getvalue())
        except Exception:
            fotos_actuales = []

    croquis_bytes = crear_croquis_guiado(datos, st.session_state.b6_puntos)

    st.markdown("### Vista previa del croquis")
    st.image(croquis_bytes, caption="Croquis demostrativo generado por S.I.V.", use_container_width=True)

    # Para JSON no guardar bytes pesados de firmas, solo constancia
    camaras_json = []
    for cam in st.session_state.b6_camaras:
        cj = dict(cam)
        if cj.get("firma_duenio_bytes"):
            cj["firma_duenio_bytes"] = "[firma digital incorporada al PDF]"
        camaras_json.append(cj)

    resumen_camaras = []
    for cam in st.session_state.b6_camaras:
        resumen_camaras.append(
            f"{cam.get('tipo','S/D')} ubicada en {cam.get('ubicacion','S/D')}, orientada/captando {cam.get('orientacion','S/D')}"
        )

    resumen_para_acta = (
        f"Se realizó inspección ocular en {datos.get('lugar','S/D')}. "
        f"Lugar preservado: {datos.get('preservado','S/D')}. "
        f"Se relevaron {len(st.session_state.b6_camaras)} cámara/s. "
        f"Puntos relevantes para croquis: {len(st.session_state.b6_puntos)}. "
        f"Resumen: {datos.get('relato_inspeccion','')[:500]}"
    )

    datos_exportar = {
        "bloque": 6,
        "modulo": "BLOQUE_6_INSPECCION_CROQUIS",
        "version": "integral_croquis_camaras_firma_digital",
        "datos": datos,
        "puntos_croquis": st.session_state.b6_puntos,
        "camaras": camaras_json,
        "cantidad_fotos": len(fotos_actuales),
        "resumen_camaras": resumen_camaras,
        "resumen_para_acta_procedimiento": resumen_para_acta
    }

    pdf_integral = generar_pdf_integral(
        datos,
        st.session_state.b6_puntos,
        st.session_state.b6_camaras,
        fotos_actuales,
        croquis_bytes
    )

    json_b6 = json.dumps(datos_exportar, ensure_ascii=False, indent=4)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button(
            "📥 Descargar PDF integral BLOQUE 6",
            data=pdf_integral,
            file_name="Bloque_6_Inspeccion_Croquis_Camaras.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with c2:
        st.download_button(
            "🗺️ Descargar imagen del croquis",
            data=croquis_bytes,
            file_name="Croquis_Demostrativo.png",
            mime="image/png",
            use_container_width=True
        )

    with c3:
        st.download_button(
            "📦 Descargar JSON BLOQUE 6",
            data=json_b6,
            file_name="bloque_6_inspeccion_croquis.json",
            mime="application/json",
            use_container_width=True
        )

    with st.expander("Ver JSON BLOQUE 6"):
        st.code(json_b6, language="json")

# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
