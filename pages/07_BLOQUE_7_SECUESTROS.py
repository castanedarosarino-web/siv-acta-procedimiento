import streamlit as st
import json
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import datetime

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

BLOQUE_ID = "BLOQUE_7_SECUESTROS"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)


ELEMENTOS_NO_MANIPULAR = [
    "arma", "pistola", "revólver", "revolver", "escopeta",
    "vaina", "cartucho", "munición", "municion", "bala",
    "explosivo", "granada",
    "sangre", "mancha hemática", "mancha hematica",
    "restos biológicos", "restos biologicos",
    "estupefaciente", "droga", "sustancia",
    "celular", "teléfono", "telefono", "notebook", "computadora",
    "cuchillo con sangre", "arma blanca con sangre"
]


def detectar_no_manipular(texto):
    texto = texto.lower()
    return any(palabra in texto for palabra in ELEMENTOS_NO_MANIPULAR)


def convertir_firma_a_bytes(canvas_result):
    if canvas_result.image_data is not None:
        img = Image.fromarray(canvas_result.image_data.astype("uint8"))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    return None


def generar_pdf_bloque_7(datos, firma_testigo=None):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "BLOQUE 7: ACTA DE SECUESTRO", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. DATOS GENERALES:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Ciudad: {datos['ciudad']} - Departamento: {datos['departamento']}", ln=True)
    pdf.cell(0, 7, f"Fecha y hora: {datos['fecha']} {datos['hora']}", ln=True)
    pdf.cell(0, 7, f"Personal actuante: {datos['personal_actuante']}", ln=True)
    pdf.cell(0, 7, f"Dependencia: {datos['dependencia']} - Móvil: {datos['movil']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. TIPO DE SECUESTRO:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Tipo: {datos['tipo_secuestro']}", ln=True)
    pdf.cell(0, 7, f"Formulario: {datos['formulario']}", ln=True)
    pdf.cell(0, 7, f"Código interno: {datos['codigo']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "3. TESTIGO DE ACTUACIÓN:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Nombre y apellido: {datos['testigo_nombre']}", ln=True)
    pdf.cell(0, 7, f"DNI: {datos['testigo_dni']}", ln=True)
    pdf.cell(0, 7, f"Domicilio: {datos['testigo_domicilio']}", ln=True)
    pdf.cell(0, 7, f"Teléfono: {datos['testigo_telefono']}", ln=True)
    pdf.cell(0, 7, f"Correo: {datos['testigo_correo']}", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "4. LUGAR, MOTIVO Y UBICACIÓN DEL SECUESTRO:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, f"Lugar exacto: {datos['lugar_secuestro']}")
    pdf.multi_cell(0, 7, f"Ubicación precisa del elemento: {datos['ubicacion_exacta']}")
    pdf.multi_cell(0, 7, f"Motivo: {datos['motivo']}")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "5. DESCRIPCIÓN DEL ELEMENTO SECUESTRADO:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, datos["descripcion"])
    pdf.cell(0, 7, f"Estado general: {datos['estado']}", ln=True)
    pdf.cell(0, 7, f"Destino / depósito: {datos['destino']}", ln=True)
    pdf.ln(4)

    if datos["formulario"] == "Automóvil":
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "6. DATOS DEL AUTOMÓVIL:", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 7, f"Marca/Modelo: {datos['auto_marca_modelo']}", ln=True)
        pdf.cell(0, 7, f"Color: {datos['auto_color']}", ln=True)
        pdf.cell(0, 7, f"Dominio: {datos['auto_dominio']}", ln=True)
        pdf.cell(0, 7, f"Motor: {datos['auto_motor']}", ln=True)
        pdf.cell(0, 7, f"Chasis: {datos['auto_chasis']}", ln=True)
        pdf.multi_cell(0, 7, f"Faltantes / observaciones: {datos['auto_observaciones']}")
        pdf.ln(4)

    if datos["formulario"] == "Motocicleta":
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "6. DATOS DE LA MOTOCICLETA:", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 7, f"Tipo/Marca: {datos['moto_tipo_marca']}", ln=True)
        pdf.cell(0, 7, f"Color: {datos['moto_color']}", ln=True)
        pdf.cell(0, 7, f"Dominio: {datos['moto_dominio']}", ln=True)
        pdf.cell(0, 7, f"Cilindrada: {datos['moto_cilindrada']}", ln=True)
        pdf.cell(0, 7, f"Motor: {datos['moto_motor']}", ln=True)
        pdf.cell(0, 7, f"Chasis: {datos['moto_chasis']}", ln=True)
        pdf.multi_cell(0, 7, f"Estado / observaciones: {datos['moto_observaciones']}")
        pdf.ln(4)

    if datos["observaciones"]:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "7. OBSERVACIONES:", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, datos["observaciones"])
        pdf.ln(4)

    if firma_testigo:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "8. FIRMA DIGITAL DEL TESTIGO:", ln=True)
        pdf.image(firma_testigo, x=20, w=80)

    pdf.ln(15)
    pdf.cell(90, 8, "____________________________", ln=False, align="C")
    pdf.cell(90, 8, "____________________________", ln=True, align="C")
    pdf.cell(90, 8, "Firma Testigo", ln=False, align="C")
    pdf.cell(90, 8, "Firma Personal Actuante", ln=True, align="C")

    pdf.set_y(-30)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 10, "Creado por Sub-Comisario Castaneda Juan - S.I.V.", align="R")

    return bytes(pdf.output())


st.title("📦 BLOQUE 7 — SECUESTROS")
st.subheader("Secuestro de la causa / Secuestro por depósito")
st.write("---")

col1, col2 = st.columns(2)

with col1:
    ciudad = st.text_input("Ciudad", key="b7_ciudad")
    departamento = st.text_input("Departamento", key="b7_departamento")
    fecha = st.date_input("Fecha", datetime.date.today(), key="b7_fecha")
    hora = st.time_input("Hora", key="b7_hora")

with col2:
    personal_actuante = st.text_area("Personal actuante", key="b7_personal_actuante")
    dependencia = st.text_input("Dependencia", key="b7_dependencia")
    movil = st.text_input("Móvil policial", key="b7_movil")

st.write("---")

tipo_secuestro = st.radio(
    "Tipo de secuestro",
    ["Secuestro de la causa", "Secuestro por depósito"],
    horizontal=True,
    key="b7_tipo_secuestro"
)

formulario = st.selectbox(
    "Formulario a utilizar",
    ["Elemento general", "Automóvil", "Motocicleta"],
    key="b7_formulario"
)

codigo = st.text_input("Código interno del secuestro", value=st.session_state.get("b7_codigo", "SEC-01"), key="b7_codigo")

st.write("---")
st.subheader("👤 Testigo de actuación")

tc1, tc2 = st.columns(2)

with tc1:
    testigo_nombre = st.text_input("Nombre y apellido del testigo", key="b7_testigo_nombre")
    testigo_dni = st.text_input("DNI del testigo", key="b7_testigo_dni")
    testigo_correo = st.text_input("Correo electrónico del testigo", key="b7_testigo_correo")

with tc2:
    testigo_domicilio = st.text_input("Domicilio del testigo", key="b7_testigo_domicilio")
    testigo_telefono = st.text_input("Teléfono del testigo", key="b7_testigo_telefono")

st.write("---")
st.subheader("📍 Lugar y motivo del secuestro")

lugar_secuestro = st.text_area("Lugar exacto del secuestro", key="b7_lugar_secuestro")
ubicacion_exacta = st.text_area(
    "Ubicación precisa del elemento",
    placeholder="Ej: sobre mesa del comedor, debajo de cama, interior de baúl...",
    key="b7_ubicacion_exacta"
)
motivo = st.text_area("Motivo del secuestro", key="b7_motivo")

st.write("---")
st.subheader("🔍 Descripción del elemento")

descripcion = st.text_area(
    "Descripción policial del elemento secuestrado",
    height=150,
    placeholder="Ej: Se procede al secuestro de...",
    key="b7_descripcion"
)

estado = st.selectbox(
    "Estado general",
    ["Bueno", "Regular", "Dañado", "Inutilizado", "Restos/Fragmentos", "No determinado"],
    key="b7_estado"
)

destino = st.text_input("Destino / depósito", placeholder="Ej: Depósito Judicial / Seccional / Fiscalía", key="b7_destino")

texto_alerta = f"{descripcion} {formulario} {motivo} {ubicacion_exacta}"

if detectar_no_manipular(texto_alerta):
    st.error("""
🚨 ALERTA DE NO MANIPULACIÓN

El elemento informado podría requerir tratamiento especial.

NO manipular.
NO trasladar sin autorización.
Preservar el lugar.
Dar intervención a autoridad correspondiente / gabinete especializado.
Dejar constancia en acta.
""")

st.write("---")

auto_marca_modelo = ""
auto_color = ""
auto_dominio = ""
auto_motor = ""
auto_chasis = ""
auto_observaciones = ""

moto_tipo_marca = ""
moto_color = ""
moto_dominio = ""
moto_cilindrada = ""
moto_motor = ""
moto_chasis = ""
moto_observaciones = ""

if formulario == "Automóvil":
    st.subheader("🚗 Formulario especial: Automóvil")

    a1, a2, a3 = st.columns(3)

    with a1:
        auto_marca_modelo = st.text_input("Marca / Modelo", key="b7_auto_marca_modelo")
        auto_color = st.text_input("Color", key="b7_auto_color")

    with a2:
        auto_dominio = st.text_input("Dominio / Patente", key="b7_auto_dominio")
        auto_motor = st.text_input("Nro. Motor", key="b7_auto_motor")

    with a3:
        auto_chasis = st.text_input("Nro. Chasis", key="b7_auto_chasis")

    auto_observaciones = st.text_area("Faltantes / estado / observaciones del automóvil", key="b7_auto_observaciones")

if formulario == "Motocicleta":
    st.subheader("🏍️ Formulario especial: Motocicleta")

    m1, m2, m3 = st.columns(3)

    with m1:
        moto_tipo_marca = st.text_input("Tipo / Marca", key="b7_moto_tipo_marca")
        moto_color = st.text_input("Color", key="b7_moto_color")

    with m2:
        moto_dominio = st.text_input("Dominio", key="b7_moto_dominio")
        moto_cilindrada = st.text_input("Cilindrada", key="b7_moto_cilindrada")

    with m3:
        moto_motor = st.text_input("Nro. Motor", key="b7_moto_motor")
        moto_chasis = st.text_input("Nro. Chasis", key="b7_moto_chasis")

    moto_observaciones = st.text_area("Estado actual / observaciones de la motocicleta", key="b7_moto_observaciones")

st.write("---")
st.subheader("📝 Observaciones finales")

observaciones = st.text_area("Observaciones generales", key="b7_observaciones")

st.write("---")
st.subheader("✍️ Firma digital del testigo")

canvas_result = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=2,
    stroke_color="#000000",
    background_color="#FFFFFF",
    height=180,
    width=500,
    drawing_mode="freedraw",
    key="firma_testigo_canvas"
)

firma_testigo = convertir_firma_a_bytes(canvas_result)

st.write("---")

if st.button("📄 GENERAR ACTA DE SECUESTRO COMPLETA"):
    campos_faltantes = []

    if not ciudad:
        campos_faltantes.append("Ciudad")
    if not departamento:
        campos_faltantes.append("Departamento")
    if not personal_actuante:
        campos_faltantes.append("Personal actuante")
    if not dependencia:
        campos_faltantes.append("Dependencia")
    if not movil:
        campos_faltantes.append("Móvil policial")
    if not testigo_nombre:
        campos_faltantes.append("Nombre del testigo")
    if not testigo_dni:
        campos_faltantes.append("DNI del testigo")
    if not testigo_telefono:
        campos_faltantes.append("Teléfono del testigo")
    if not testigo_correo:
        campos_faltantes.append("Correo electrónico del testigo")
    if not testigo_domicilio:
        campos_faltantes.append("Domicilio del testigo")
    if not lugar_secuestro:
        campos_faltantes.append("Lugar exacto del secuestro")
    if not ubicacion_exacta:
        campos_faltantes.append("Ubicación precisa del elemento")
    if not motivo:
        campos_faltantes.append("Motivo del secuestro")
    if not descripcion:
        campos_faltantes.append("Descripción del elemento")
    if not destino:
        campos_faltantes.append("Destino / depósito")
    if firma_testigo is None:
        campos_faltantes.append("Firma digital del testigo")

    if formulario == "Automóvil":
        if not auto_marca_modelo:
            campos_faltantes.append("Marca / modelo del automóvil")
        if not auto_dominio:
            campos_faltantes.append("Dominio del automóvil")

    if formulario == "Motocicleta":
        if not moto_tipo_marca:
            campos_faltantes.append("Tipo / marca de motocicleta")
        if not moto_dominio:
            campos_faltantes.append("Dominio de motocicleta")

    if campos_faltantes:
        st.error("⚠️ No se puede generar el acta. Faltan campos obligatorios:")
        for campo in campos_faltantes:
            st.write(f"- {campo}")

    else:
        datos_b7 = {
            "bloque": 7,
            "ciudad": ciudad,
            "departamento": departamento,
            "fecha": str(fecha),
            "hora": str(hora),
            "personal_actuante": personal_actuante,
            "dependencia": dependencia,
            "movil": movil,
            "tipo_secuestro": tipo_secuestro,
            "formulario": formulario,
            "codigo": codigo,
            "testigo_nombre": testigo_nombre,
            "testigo_dni": testigo_dni,
            "testigo_domicilio": testigo_domicilio,
            "testigo_telefono": testigo_telefono,
            "testigo_correo": testigo_correo,
            "lugar_secuestro": lugar_secuestro,
            "ubicacion_exacta": ubicacion_exacta,
            "motivo": motivo,
            "descripcion": descripcion,
            "estado": estado,
            "destino": destino,
            "observaciones": observaciones,
            "alerta_no_manipular": "SÍ" if detectar_no_manipular(texto_alerta) else "NO",
            "auto_marca_modelo": auto_marca_modelo,
            "auto_color": auto_color,
            "auto_dominio": auto_dominio,
            "auto_motor": auto_motor,
            "auto_chasis": auto_chasis,
            "auto_observaciones": auto_observaciones,
            "moto_tipo_marca": moto_tipo_marca,
            "moto_color": moto_color,
            "moto_dominio": moto_dominio,
            "moto_cilindrada": moto_cilindrada,
            "moto_motor": moto_motor,
            "moto_chasis": moto_chasis,
            "moto_observaciones": moto_observaciones
        }

        pdf_b7 = generar_pdf_bloque_7(datos_b7, firma_testigo)
        json_b7 = json.dumps(datos_b7, indent=4, ensure_ascii=False)

        st.success("✅ Acta de secuestro generada correctamente.")

        c1, c2 = st.columns(2)

        with c1:
            st.download_button(
                "📥 Descargar PDF Bloque 7",
                data=pdf_b7,
                file_name="Bloque_7_Secuestro.pdf",
                mime="application/pdf"
            )

        with c2:
            st.download_button(
                "📥 Descargar JSON Bloque 7",
                data=json_b7,
                file_name="bloque_7.json",
                mime="application/json"
            )

# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
