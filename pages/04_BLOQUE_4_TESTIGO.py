import streamlit as st
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import json
import tempfile
import os
import base64
from datetime import datetime, date

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_DISPONIBLE = True
except Exception:
    GUARDADO_DISPONIBLE = False

# =====================================================
# S.I.V.A.P. - BLOQUE 4 TESTIGO
# Acta de Entrevista a Testigo
#
# Correccion aplicada:
# - Mantiene firma digital simple con st_canvas, como la version que funcionaba.
# - Genera copia interna de firma en base64 real.
# - La firma viaja en el JSON por WhatsApp.
# - El actante puede importar JSON dentro del mismo BLOQUE 4.
# - Al importar, se completan los campos y se visualiza la firma recibida.
# - El PDF usa la firma actual o importada.
# =====================================================

st.set_page_config(page_title="S.I.V.A.P. - Bloque 4 Testigo", layout="wide")

BLOQUE_ID = "BLOQUE_4_TESTIGO"
if GUARDADO_DISPONIBLE:
    iniciar_guardado_seguro(BLOQUE_ID)
    panel_guardado_seguro(BLOQUE_ID)

SISTEMA = "S.I.V.A.P. - Sistema Integrado de Validacion de Actuaciones Policiales"
LEMA = "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora."

# =====================================================
# ESTADO / UTILIDADES
# =====================================================

def init_b4():
    defaults = {
        "b4_ni": "",
        "b4_nombre_policial": "",
        "b4_jerarquia": "",
        "b4_dependencia_policial": "",
        "b4_rol_operativo": "Actante",
        "b4_numero_acta": "",
        "b4_fecha_actuacion": str(date.today()),
        "b4_hora_actuacion": datetime.now().strftime("%H:%M"),
        "b4_lugar_entrevista": "Rosario",
        "b4_dependencia_acta": "",
        "b4_testigo_nombre": "",
        "b4_testigo_dni": "",
        "b4_testigo_telefono": "",
        "b4_testigo_correo": "",
        "b4_testigo_fecha_nac": "",
        "b4_testigo_domicilio": "",
        "b4_relato": "",
        "b4_firma_base64": "",
        "b4_firma_origen": "",
        "b4_importacion_info": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def aplicar_importacion_pendiente():
    """Aplica importacion antes de instanciar widgets para evitar errores de session_state."""
    pendiente = st.session_state.get("b4_importacion_pendiente")
    if not pendiente:
        return

    data = pendiente
    entrevista = data.get("entrevista_testigo") or data.get("datos_testigo") or data.get("datos_bloque") or data
    filiacion = entrevista.get("filiacion") or entrevista.get("testigo") or {}
    actuacion = data.get("actuacion", {})
    autor = data.get("autor_carga", {})
    firma = entrevista.get("firma", data.get("firma", {}))

    # Actuacion / autor
    st.session_state["b4_ni"] = autor.get("ni", st.session_state.get("b4_ni", ""))
    st.session_state["b4_nombre_policial"] = autor.get("nombre_apellido", st.session_state.get("b4_nombre_policial", ""))
    st.session_state["b4_jerarquia"] = autor.get("jerarquia", st.session_state.get("b4_jerarquia", ""))
    st.session_state["b4_dependencia_policial"] = autor.get("dependencia", st.session_state.get("b4_dependencia_policial", ""))
    st.session_state["b4_rol_operativo"] = autor.get("rol_operativo", st.session_state.get("b4_rol_operativo", "Actante"))

    st.session_state["b4_numero_acta"] = actuacion.get("numero_acta", st.session_state.get("b4_numero_acta", ""))
    st.session_state["b4_fecha_actuacion"] = actuacion.get("fecha", st.session_state.get("b4_fecha_actuacion", str(date.today())))
    st.session_state["b4_hora_actuacion"] = actuacion.get("hora", st.session_state.get("b4_hora_actuacion", datetime.now().strftime("%H:%M")))
    st.session_state["b4_lugar_entrevista"] = actuacion.get("lugar_entrevista", st.session_state.get("b4_lugar_entrevista", "Rosario"))
    st.session_state["b4_dependencia_acta"] = actuacion.get("dependencia", st.session_state.get("b4_dependencia_acta", ""))

    # Filiacion
    st.session_state["b4_testigo_nombre"] = filiacion.get("nombre", filiacion.get("nombre_completo", st.session_state.get("b4_testigo_nombre", "")))
    st.session_state["b4_testigo_dni"] = filiacion.get("dni", st.session_state.get("b4_testigo_dni", ""))
    st.session_state["b4_testigo_telefono"] = filiacion.get("telefono", st.session_state.get("b4_testigo_telefono", ""))
    st.session_state["b4_testigo_correo"] = filiacion.get("correo", st.session_state.get("b4_testigo_correo", ""))
    st.session_state["b4_testigo_fecha_nac"] = filiacion.get("fecha_nac", filiacion.get("fecha_nacimiento", st.session_state.get("b4_testigo_fecha_nac", "")))
    st.session_state["b4_testigo_domicilio"] = filiacion.get("domicilio", st.session_state.get("b4_testigo_domicilio", ""))

    st.session_state["b4_relato"] = entrevista.get("contenido", entrevista.get("relato", st.session_state.get("b4_relato", "")))

    firma_b64 = firma.get("firma_base64") or firma.get("firma_canvas_base64") or ""
    if firma_b64 and firma_b64 != "[firma digital guardada]":
        st.session_state["b4_firma_base64"] = firma_b64
        st.session_state["b4_firma_origen"] = "importada_json"

    st.session_state["b4_importacion_info"] = "JSON de BLOQUE 4 incorporado correctamente. Revise y corrija los campos antes de generar PDF/JSON."
    st.session_state.pop("b4_importacion_pendiente", None)


def limpiar_pdf(texto):
    if texto is None:
        return ""
    reemplazos = {
        "ñ": "n", "Ñ": "N", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "°": "Nro.",
        "“": '"', "”": '"', "’": "'", "–": "-", "—": "-"
    }
    texto = str(texto)
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto


def canvas_a_base64(canvas_result):
    if canvas_result is None or canvas_result.image_data is None:
        return ""
    try:
        img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
        # Detectar si hay trazo: pixeles no blancos/no transparentes suficientes
        alpha = img.split()[3]
        bbox = alpha.getbbox()
        if not bbox:
            return ""
        blanco = Image.new("RGB", img.size, (255, 255, 255))
        blanco.paste(img, mask=alpha)
        buffer = io.BytesIO()
        blanco.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return ""


def base64_a_tempfile(firma_b64):
    if not firma_b64:
        return None
    try:
        raw = base64.b64decode(firma_b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(raw)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def datos_actuales():
    return {
        "filiacion": {
            "nombre": st.session_state.get("b4_testigo_nombre", ""),
            "dni": st.session_state.get("b4_testigo_dni", ""),
            "telefono": st.session_state.get("b4_testigo_telefono", ""),
            "correo": st.session_state.get("b4_testigo_correo", ""),
            "fecha_nac": st.session_state.get("b4_testigo_fecha_nac", ""),
            "domicilio": st.session_state.get("b4_testigo_domicilio", ""),
        },
        "contenido": st.session_state.get("b4_relato", ""),
        "firma": {
            "tipo": "firma_digital_canvas",
            "firma_base64": st.session_state.get("b4_firma_base64", ""),
            "origen": st.session_state.get("b4_firma_origen", "")
        }
    }


def armar_json_exportacion():
    nro = st.session_state.get("b4_numero_acta", "")
    ni = st.session_state.get("b4_ni", "")
    datos = datos_actuales()

    return {
        "sistema": SISTEMA,
        "tipo_archivo": "colaboracion_json",
        "bloque": "BLOQUE_4_ENTREVISTA_TESTIGO",
        "autor_carga": {
            "ni": ni,
            "nombre_apellido": st.session_state.get("b4_nombre_policial", ""),
            "jerarquia": st.session_state.get("b4_jerarquia", ""),
            "dependencia": st.session_state.get("b4_dependencia_policial", ""),
            "rol_operativo": st.session_state.get("b4_rol_operativo", ""),
            "dispositivo": "Celular validado"
        },
        "actuacion": {
            "numero_acta": nro,
            "fecha": st.session_state.get("b4_fecha_actuacion", ""),
            "hora": st.session_state.get("b4_hora_actuacion", ""),
            "dependencia": st.session_state.get("b4_dependencia_acta", ""),
            "lugar_entrevista": st.session_state.get("b4_lugar_entrevista", "")
        },
        "entrevista_testigo": datos,
        "resumen_para_acta_procedimiento": {
            "tipo": "testigo",
            "nombre": datos["filiacion"].get("nombre", ""),
            "dni": datos["filiacion"].get("dni", ""),
            "texto_para_acta": "Se individualizo testigo de interes, a quien se recibio entrevista policial, labrandose acta respectiva que se agrega como anexo.",
            "incorporar": True
        },
        "fecha_exportacion": datetime.now().isoformat()
    }


def generar_pdf_testigo(datos, firma_b64):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=20, top=15, right=15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    dependencia = st.session_state.get("b4_dependencia_acta") or st.session_state.get("b4_dependencia_policial", "")
    lugar = st.session_state.get("b4_lugar_entrevista", "Rosario")
    fecha = st.session_state.get("b4_fecha_actuacion", str(date.today()))
    hora = st.session_state.get("b4_hora_actuacion", datetime.now().strftime("%H:%M"))

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, limpiar_pdf("POLICIA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
    if dependencia:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpiar_pdf(dependencia.upper()), ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, limpiar_pdf("ACTA DE ENTREVISTA A TESTIGO"), ln=True, align="C")
    pdf.ln(5)

    f = datos["filiacion"]
    nombre = f.get("nombre", "")
    dni = f.get("dni", "")
    domicilio = f.get("domicilio", "")
    telefono = f.get("telefono", "")
    correo = f.get("correo", "")
    fecha_nac = f.get("fecha_nac", "")

    apertura = (
        f"En la ciudad de {lugar}, a fecha {fecha}, siendo las {hora} horas, "
        f"se procede a recibir entrevista a quien dijo llamarse {nombre}, DNI Nro. {dni}, "
        f"fecha de nacimiento {fecha_nac}, domiciliado/a en {domicilio}, "
        f"telefono/correo {telefono} / {correo}, en relacion a las presentes actuaciones."
    )
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(apertura), align="J")
    pdf.ln(3)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, limpiar_pdf("RELATO"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(datos.get("contenido", "")), align="J")

    pdf.ln(8)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, limpiar_pdf("CIERRE"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf("No siendo para mas, previa lectura y ratificacion de su contenido, se da por finalizado el presente acto, firmando al pie para constancia."), align="J")

    pdf.ln(16)
    y_pos = pdf.get_y()
    path_firma = base64_a_tempfile(firma_b64)
    if path_firma:
        try:
            pdf.image(path_firma, x=28, y=y_pos - 13, w=58)
        except Exception:
            pass
        finally:
            try:
                os.unlink(path_firma)
            except Exception:
                pass

    pdf.cell(85, 8, "____________________________", 0, 0, "C")
    pdf.cell(85, 8, "____________________________", 0, 1, "C")
    pdf.cell(85, 5, limpiar_pdf("Firma testigo"), 0, 0, "C")
    pdf.cell(85, 5, limpiar_pdf("Firma personal policial"), 0, 1, "C")

    pdf.ln(8)
    personal = f"{st.session_state.get('b4_jerarquia', '')} {st.session_state.get('b4_nombre_policial', '')}".strip()
    if personal:
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, limpiar_pdf(f"Personal actuante: {personal}"))

    pdf.set_y(-22)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, limpiar_pdf(LEMA), align="R")

    return pdf_bytes(pdf)


def archivo_nombre_json():
    nro = st.session_state.get("b4_numero_acta", "SIN_ACTA") or "SIN_ACTA"
    ni = st.session_state.get("b4_ni", "SIN_NI") or "SIN_NI"
    return f"SIVAP_ACTA_{nro}_BLOQUE_4_TESTIGO_NI_{ni}.json".replace("/", "-").replace(" ", "_")


# =====================================================
# APLICAR IMPORTACION ANTES DE WIDGETS
# =====================================================
init_b4()
aplicar_importacion_pendiente()

# =====================================================
# INTERFAZ
# =====================================================
st.title("🚓 BLOQUE 4 — Acta de Entrevista a Testigo")
st.caption(LEMA)

with st.sidebar:
    st.header("Identidad policial")
    st.text_input("NI / PIN policial", key="b4_ni")
    st.text_input("Nombre y apellido", key="b4_nombre_policial")
    st.text_input("Jerarquía", key="b4_jerarquia")
    st.text_input("Dependencia", key="b4_dependencia_policial")
    st.selectbox("Rol operativo", ["Actante", "Colaborador", "Ambos"], key="b4_rol_operativo")

    st.divider()
    st.header("Actuación")
    st.text_input("Número de acta", key="b4_numero_acta")
    st.text_input("Fecha", key="b4_fecha_actuacion")
    st.text_input("Hora", key="b4_hora_actuacion")
    st.text_input("Lugar entrevista", key="b4_lugar_entrevista")
    st.text_input("Dependencia del acta", key="b4_dependencia_acta")

seccion = st.radio(
    "Sección",
    ["Importar JSON", "Datos del testigo", "Relato", "Firma digital", "PDF / JSON"],
    horizontal=True,
    key="b4_seccion"
)

if st.session_state.get("b4_importacion_info"):
    st.success(st.session_state["b4_importacion_info"])

if seccion == "Importar JSON":
    st.subheader("📥 Importar colaboración JSON de BLOQUE 4")
    st.info("Cargue aquí el JSON de BLOQUE 4 recibido por WhatsApp. El bloque se completará automáticamente para que el actante revise/corrija.")
    archivo = st.file_uploader("Seleccionar JSON de BLOQUE 4", type=["json"], key="b4_importador_json")

    if archivo is not None:
        try:
            data = json.load(archivo)
            bloque = str(data.get("bloque", "")).upper()
            if "BLOQUE_4" not in bloque and "TESTIGO" not in json.dumps(data, ensure_ascii=False).upper():
                st.error("Este archivo no parece corresponder a BLOQUE 4 - Testigo.")
            else:
                st.success("JSON de BLOQUE 4 detectado correctamente.")
                entrevista = data.get("entrevista_testigo") or data.get("datos_testigo") or data.get("datos_bloque") or data
                filiacion = entrevista.get("filiacion") or entrevista.get("testigo") or {}
                firma = entrevista.get("firma", data.get("firma", {}))
                st.write(f"**Testigo:** {filiacion.get('nombre','')}")
                st.write(f"**DNI:** {filiacion.get('dni','')}")
                st.write("**Firma incluida:**", "SÍ" if (firma.get("firma_base64") or firma.get("firma_canvas_base64")) else "NO")

                if st.button("✅ Incorporar datos al BLOQUE 4 del actante"):
                    st.session_state["b4_importacion_pendiente"] = data
                    st.rerun()
        except Exception as e:
            st.error(f"No se pudo leer el JSON: {e}")

elif seccion == "Datos del testigo":
    st.subheader("👤 Datos filiatorios del testigo")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.text_input("Apellido y nombres", key="b4_testigo_nombre")
    with c2:
        st.text_input("DNI", key="b4_testigo_dni")

    c3, c4 = st.columns(2)
    with c3:
        st.text_input("Teléfono", key="b4_testigo_telefono")
    with c4:
        st.text_input("Correo electrónico", key="b4_testigo_correo")

    c5, c6 = st.columns([1, 2])
    with c5:
        st.text_input("Fecha de nacimiento", key="b4_testigo_fecha_nac")
    with c6:
        st.text_input("Domicilio real", key="b4_testigo_domicilio")

elif seccion == "Relato":
    st.subheader("✍️ Entrevista / relato del testigo")
    st.text_area("El testigo manifiesta que:", height=280, key="b4_relato")

elif seccion == "Firma digital":
    st.subheader("🖊️ Firma digital del testigo")
    st.info("La firma se guarda internamente y viaja dentro del JSON para que el actante pueda importarla.")

    canvas_testigo = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        width=500,
        drawing_mode="freedraw",
        key="canvas_testigo",
    )

    firma_b64 = canvas_a_base64(canvas_testigo)
    if firma_b64:
        st.session_state["b4_firma_base64"] = firma_b64
        st.session_state["b4_firma_origen"] = "canvas_local"
        st.success("Firma digital capturada correctamente.")

    if st.session_state.get("b4_firma_base64"):
        st.markdown("### Vista previa de firma guardada/importada")
        try:
            st.image(base64.b64decode(st.session_state["b4_firma_base64"]), width=280)
        except Exception:
            st.info("Firma guardada internamente. Se incorporará al PDF y al JSON.")

elif seccion == "PDF / JSON":
    st.subheader("📄 PDF y JSON para WhatsApp")

    datos = datos_actuales()
    firma_b64 = st.session_state.get("b4_firma_base64", "")

    if not firma_b64:
        st.warning("Todavía no se capturó firma digital. Vaya a la sección 'Firma digital' y firme antes de exportar.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 Generar PDF Acta de Entrevista a Testigo"):
            if not datos["filiacion"].get("nombre"):
                st.error("Debe cargar nombre del testigo.")
            else:
                pdf_data = generar_pdf_testigo(datos, firma_b64)
                st.download_button(
                    "⬇️ Descargar PDF BLOQUE 4",
                    data=pdf_data,
                    file_name=f"BLOQUE_4_Acta_Entrevista_Testigo_{datos['filiacion'].get('dni','')}.pdf",
                    mime="application/pdf"
                )

    with col2:
        json_data = armar_json_exportacion()
        st.download_button(
            "📤 Descargar JSON para WhatsApp",
            data=json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=archivo_nombre_json(),
            mime="application/json"
        )

    with st.expander("Ver JSON que se enviará"):
        st.json(armar_json_exportacion())

# Guardado automatico del bloque al finalizar la corrida
try:
    if GUARDADO_DISPONIBLE:
        autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
