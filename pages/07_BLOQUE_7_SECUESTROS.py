import streamlit as st
import json
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import datetime
import tempfile
import os

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

# =====================================================
# BLOQUE 7 - SECUESTROS
# Version mejorada:
# - Lista de elementos secuestrados.
# - Agrupacion de elementos por acta.
# - Cada acta exige testigo, lugar, hora y firma.
# - Exporta JSON completo para BLOQUE 8.
# =====================================================

st.set_page_config(page_title="S.I.V. - Bloque 7 Secuestros", layout="wide", page_icon="📦")

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
    texto = str(texto or "").lower()
    return any(palabra in texto for palabra in ELEMENTOS_NO_MANIPULAR)


def limpiar_pdf(texto):
    if texto is None:
        return ""
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.", "–": "-", "—": "-",
        "“": '"', "”": '"', "’": "'", "✅": "", "⚠️": "", "🚨": ""
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


def convertir_firma_temp(canvas_result):
    if canvas_result is None or canvas_result.image_data is None:
        return None

    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
    blanco = Image.new("RGB", img.size, (255, 255, 255))
    blanco.paste(img, mask=img.split()[3])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    blanco.save(tmp.name, format="JPEG")
    return tmp.name


def elemento_label(e, idx=None):
    pref = f"{idx}. " if idx is not None else ""
    tipo = e.get("tipo_elemento", "Elemento")
    desc = e.get("descripcion", "")
    if tipo == "Automóvil":
        detalle = f"{e.get('auto_marca_modelo','')} dominio {e.get('auto_dominio','')}".strip()
    elif tipo == "Motocicleta":
        detalle = f"{e.get('moto_tipo_marca','')} dominio {e.get('moto_dominio','')}".strip()
    elif tipo == "Celular":
        detalle = f"{e.get('celular_marca','')} {e.get('celular_modelo','')} - {e.get('propietario','')}".strip()
    elif tipo == "Arma de fuego":
        detalle = f"{e.get('arma_tipo','')} {e.get('arma_calibre','')} - Nro. {e.get('arma_numeracion','')}".strip()
    else:
        detalle = desc[:80]
    return f"{pref}{tipo}: {detalle or desc or 'Sin descripción'}"


def es_elemento_comun(e):
    """
    Elementos que pueden ir en la plantilla típica de levantamiento y secuestro de elementos.
    Vehículos y armas quedan separados porque requieren actas/tratamiento específico.
    """
    tipo = e.get("tipo_elemento", "")
    return tipo not in ["Automóvil", "Motocicleta", "Arma de fuego"]



def descripcion_elemento_acta(e):
    tipo = e.get("tipo_elemento", "Elemento general")
    partes = [f"Tipo: {tipo}"]

    if tipo == "Automóvil":
        partes.extend([
            f"Marca/modelo: {e.get('auto_marca_modelo','S/D')}",
            f"Color: {e.get('auto_color','S/D')}",
            f"Dominio: {e.get('auto_dominio','S/D')}",
            f"Motor: {e.get('auto_motor','S/D')}",
            f"Chasis: {e.get('auto_chasis','S/D')}",
            f"Observaciones: {e.get('auto_observaciones','')}"
        ])
    elif tipo == "Motocicleta":
        partes.extend([
            f"Tipo/marca: {e.get('moto_tipo_marca','S/D')}",
            f"Color: {e.get('moto_color','S/D')}",
            f"Dominio: {e.get('moto_dominio','S/D')}",
            f"Cilindrada: {e.get('moto_cilindrada','S/D')}",
            f"Motor: {e.get('moto_motor','S/D')}",
            f"Chasis: {e.get('moto_chasis','S/D')}",
            f"Observaciones: {e.get('moto_observaciones','')}"
        ])
    elif tipo == "Celular":
        partes.extend([
            f"Marca: {e.get('celular_marca','S/D')}",
            f"Modelo: {e.get('celular_modelo','S/D')}",
            f"Color: {e.get('celular_color','S/D')}",
            f"IMEI: {e.get('celular_imei','S/D')}",
            f"Línea: {e.get('celular_linea','S/D')}",
            f"Propietario: {e.get('propietario','S/D')}",
            f"Condición: {e.get('celular_condicion','S/D')}"
        ])
    elif tipo == "Arma de fuego":
        partes.extend([
            f"Tipo de arma: {e.get('arma_tipo','S/D')}",
            f"Marca: {e.get('arma_marca','S/D')}",
            f"Calibre: {e.get('arma_calibre','S/D')}",
            f"Numeración visible: {e.get('arma_numeracion','S/D')}",
            f"Cartuchos/vainas: {e.get('arma_cartuchos','S/D')}",
            f"Intervención especializada: {e.get('intervencion_especializada','S/D')}"
        ])
    else:
        partes.append(f"Descripción: {e.get('descripcion','S/D')}")

    partes.extend([
        f"Estado: {e.get('estado','S/D')}",
        f"Lugar de hallazgo: {e.get('lugar_hallazgo','S/D')}",
        f"Ubicación precisa: {e.get('ubicacion_exacta','S/D')}",
        f"Destino / depósito: {e.get('destino','S/D')}",
        f"Observaciones: {e.get('observaciones','')}"
    ])

    if e.get("alerta_no_manipular") == "SÍ":
        partes.append("ALERTA: elemento con posible tratamiento especial. Preservar y evitar manipulación innecesaria.")

    return "\n".join([p for p in partes if p and not p.endswith(": ")])



def generar_pdf_elementos_comunes(datos_generales, acta, elementos, firma_path=None):
    """
    Plantilla predeterminada basada en:
    Acta de levantamiento y secuestro de elementos.
    Para billetera, documentación, dinero, celular común, prendas, mochila, etc.
    No reemplaza plantillas especiales de auto/moto/arma.
    """
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=16)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Policia de la Provincia de Santa Fe", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Unidad Regional II - Perez-Zavalla-Soldini", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Acta de levantamiento y secuestro de elementos", ln=True, align="C")
    pdf.ln(4)

    fecha_txt = acta.get("fecha_acta", "S/D")
    hora_txt = acta.get("hora_acta", "S/D")
    ciudad = datos_generales.get("ciudad", "S/D")
    departamento = datos_generales.get("departamento", "S/D")
    personal = datos_generales.get("personal_actuante", "S/D")
    movil = datos_generales.get("movil", "S/D")
    dependencia = datos_generales.get("dependencia", "S/D")
    lugar = acta.get("lugar_acta", "S/D")

    testigo_1 = (
        f"{acta.get('testigo_nombre','S/D')}, DNI Nro. {acta.get('testigo_dni','S/D')}, "
        f"domicilio {acta.get('testigo_domicilio','S/D')}, telefono {acta.get('testigo_telefono','S/D')}"
    )

    testigo_2_nombre = acta.get("testigo2_nombre", "")
    if testigo_2_nombre:
        testigo_2 = (
            f" y el/la llamado/a {testigo_2_nombre}, DNI Nro. {acta.get('testigo2_dni','S/D')}, "
            f"domicilio {acta.get('testigo2_domicilio','S/D')}, telefono {acta.get('testigo2_telefono','S/D')}"
        )
    else:
        testigo_2 = ""

    elementos_txt = []
    for idx, e in enumerate(elementos, start=1):
        elementos_txt.append(f"{idx}) {descripcion_elemento_acta(e)}")

    cuerpo = f"""
En la ciudad de {ciudad}, departamento {departamento}, Provincia de Santa Fe, en fecha {fecha_txt}, siendo las {hora_txt} horas, el funcionario policial actuante quien suscribe {personal}, encargado/a del movil policial Nro. {movil}, numerario/s de {dependencia}, a los fines legales que diere a lugar y en las circunstancias y comprobaciones que se detallan, confecciona la presente acta donde HACE CONSTAR:

Que en la fecha y hora indicada, constituido el personal actuante en {lugar}, se solicito la presencia de ciudadano/a que oficie de TESTIGO habil, haciendose presente y acreditando identidad el/la llamado/a {testigo_1}{testigo_2}.

Que de acuerdo a las circunstancias constatadas, y en presencia del/de los testigo/s, se procede al LEVANTAMIENTO Y SECUESTRO de los siguientes elementos:

{chr(10).join(elementos_txt)}

Observaciones:
{acta.get('observaciones_acta','')}

Por lo que no siendo para mas, se da por finalizada la presente y de concluido el acto, que previa lectura de su contenido en forma individual, firman los testigos y el personal actuante para debida constancia.
"""

    pdf.set_font("Arial", "", 10)
    for parrafo in limpiar_pdf(cuerpo).split("\n"):
        if not parrafo.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, parrafo, align="J")

    if firma_path:
        try:
            pdf.ln(4)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 7, "Firma digital del testigo", ln=True)
            pdf.image(firma_path, x=25, w=70)
        except Exception:
            pass

    pdf.ln(16)
    pdf.cell(60, 8, "____________________", ln=False, align="C")
    pdf.cell(60, 8, "____________________", ln=False, align="C")
    pdf.cell(60, 8, "____________________", ln=True, align="C")
    pdf.cell(60, 6, "Firma Testigo", ln=False, align="C")
    pdf.cell(60, 6, "Firma Testigo", ln=False, align="C")
    pdf.cell(60, 6, "Firma Personal Actuante", ln=True, align="C")

    return pdf_bytes(pdf)


def generar_pdf_acta_secuestro(datos_generales, acta, elementos, firma_path=None):
    pdf = FPDF()
    pdf.set_margins(18, 15, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "BLOQUE 7: ACTA DE SECUESTRO", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. DATOS GENERALES", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(
        f"Ciudad: {datos_generales.get('ciudad','S/D')} - Departamento: {datos_generales.get('departamento','S/D')}\n"
        f"Fecha: {acta.get('fecha_acta','S/D')} - Hora: {acta.get('hora_acta','S/D')}\n"
        f"Personal actuante: {datos_generales.get('personal_actuante','S/D')}\n"
        f"Dependencia: {datos_generales.get('dependencia','S/D')} - Movil: {datos_generales.get('movil','S/D')}\n"
        f"Lugar del acto de secuestro: {acta.get('lugar_acta','S/D')}"
    ))
    pdf.ln(3)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. TESTIGO DE ACTUACION", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, limpiar_pdf(
        f"Nombre y apellido: {acta.get('testigo_nombre','S/D')}\n"
        f"DNI: {acta.get('testigo_dni','S/D')}\n"
        f"Domicilio: {acta.get('testigo_domicilio','S/D')}\n"
        f"Telefono: {acta.get('testigo_telefono','S/D')}\n"
        f"Correo: {acta.get('testigo_correo','S/D')}"
    ))
    pdf.ln(3)

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "3. ELEMENTOS INCLUIDOS EN ESTA ACTA", ln=True)
    pdf.set_font("Arial", "", 10)

    for idx, e in enumerate(elementos, start=1):
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 7, limpiar_pdf(f"Elemento Nro. {idx}: {elemento_label(e)}"))
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, limpiar_pdf(descripcion_elemento_acta(e)))
        pdf.ln(3)

    if acta.get("observaciones_acta"):
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "4. OBSERVACIONES DEL ACTA", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, limpiar_pdf(acta.get("observaciones_acta", "")))
        pdf.ln(3)

    if any(e.get("alerta_no_manipular") == "SÍ" for e in elementos):
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "5. CONSTANCIA DE PRESERVACION", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, limpiar_pdf(
            "Se deja constancia que uno o mas elementos incluidos en la presente acta presentan posible tratamiento especial, "
            "por lo que se recomienda preservar, evitar manipulacion innecesaria y dar intervencion a la autoridad o gabinete especializado cuando corresponda."
        ))
        pdf.ln(3)

    if firma_path:
        try:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "FIRMA DIGITAL DEL TESTIGO", ln=True)
            pdf.image(firma_path, x=25, w=70)
            pdf.ln(8)
        except Exception:
            pass

    pdf.ln(15)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 8, "Firma Testigo", ln=False, align="C")
    pdf.cell(85, 8, "Firma Personal Actuante", ln=True, align="C")

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "Creado por Sub-Comisario Castaneda Juan - S.I.V.", align="R")

    return pdf_bytes(pdf)


# =====================================================
# SESSION STATE
# =====================================================
if "b7_elementos" not in st.session_state:
    st.session_state.b7_elementos = []

if "b7_actas_secuestro" not in st.session_state:
    st.session_state.b7_actas_secuestro = []


# =====================================================
# INTERFAZ
# =====================================================
st.title("📦 BLOQUE 7 — SECUESTROS")
st.subheader("Lista de elementos secuestrados y actas firmables por testigo")
st.warning("Regla: cada acta debe agrupar solo los elementos secuestrados en el mismo acto, ante el testigo que firma.")
st.info("Plantilla predeterminada: si los elementos seleccionados son comunes, el PDF sale como Acta de levantamiento y secuestro de elementos. Si incluye automóvil, motocicleta o arma, usa acta especial separada.")

st.write("---")
st.subheader("1. Datos generales del procedimiento")

g1, g2 = st.columns(2)

with g1:
    ciudad = st.text_input("Ciudad", key="b7_ciudad")
    departamento = st.text_input("Departamento", key="b7_departamento")
    fecha_general = st.date_input("Fecha general", datetime.date.today(), key="b7_fecha_general")
    hora_general = st.time_input("Hora general", key="b7_hora_general")

with g2:
    personal_actuante = st.text_area("Personal actuante", key="b7_personal_actuante")
    dependencia = st.text_input("Dependencia", key="b7_dependencia")
    movil = st.text_input("Móvil policial", key="b7_movil")

datos_generales = {
    "ciudad": ciudad,
    "departamento": departamento,
    "fecha_general": str(fecha_general),
    "hora_general": str(hora_general),
    "personal_actuante": personal_actuante,
    "dependencia": dependencia,
    "movil": movil
}

st.write("---")
st.subheader("2. Cargar elemento secuestrado")

tipo_elemento = st.selectbox(
    "Tipo de elemento",
    [
        "Elemento general",
        "Automóvil",
        "Motocicleta",
        "Celular",
        "Arma de fuego",
        "Efectos personales",
        "Dinero",
        "Documentación",
        "Prenda de vestir",
        "Sustancia / estupefaciente",
        "Otro"
    ],
    key="b7_tipo_elemento"
)

descripcion = st.text_area("Descripción general del elemento", height=120, key="b7_descripcion")
estado = st.selectbox(
    "Estado general",
    ["Bueno", "Regular", "Dañado", "Inutilizado", "Restos/Fragmentos", "No determinado"],
    key="b7_estado"
)

c_lugar1, c_lugar2 = st.columns(2)
with c_lugar1:
    lugar_hallazgo = st.text_area("Lugar de hallazgo", key="b7_lugar_hallazgo")
    ubicacion_exacta = st.text_area("Ubicación precisa", key="b7_ubicacion_exacta")
with c_lugar2:
    destino = st.text_input("Destino / depósito / resguardo", key="b7_destino")
    propietario = st.text_input("Propietario o vinculación", placeholder="Ej: víctima, arrestado, desconocido", key="b7_propietario")
    observaciones = st.text_area("Observaciones del elemento", key="b7_observaciones_elemento")

auto_marca_modelo = auto_color = auto_dominio = auto_motor = auto_chasis = auto_observaciones = ""
moto_tipo_marca = moto_color = moto_dominio = moto_cilindrada = moto_motor = moto_chasis = moto_observaciones = ""
celular_marca = celular_modelo = celular_color = celular_imei = celular_linea = celular_condicion = ""
arma_tipo = arma_marca = arma_calibre = arma_numeracion = arma_cartuchos = intervencion_especializada = ""

if tipo_elemento == "Automóvil":
    st.markdown("#### 🚗 Datos especiales de automóvil")
    a1, a2, a3 = st.columns(3)
    with a1:
        auto_marca_modelo = st.text_input("Marca / modelo", key="b7_auto_marca_modelo")
        auto_color = st.text_input("Color", key="b7_auto_color")
    with a2:
        auto_dominio = st.text_input("Dominio / patente", key="b7_auto_dominio")
        auto_motor = st.text_input("Nro. motor", key="b7_auto_motor")
    with a3:
        auto_chasis = st.text_input("Nro. chasis", key="b7_auto_chasis")
    auto_observaciones = st.text_area("Faltantes / estado / observaciones del automóvil", key="b7_auto_observaciones")

elif tipo_elemento == "Motocicleta":
    st.markdown("#### 🏍️ Datos especiales de motocicleta")
    m1, m2, m3 = st.columns(3)
    with m1:
        moto_tipo_marca = st.text_input("Tipo / marca", key="b7_moto_tipo_marca")
        moto_color = st.text_input("Color", key="b7_moto_color")
    with m2:
        moto_dominio = st.text_input("Dominio", key="b7_moto_dominio")
        moto_cilindrada = st.text_input("Cilindrada", key="b7_moto_cilindrada")
    with m3:
        moto_motor = st.text_input("Nro. motor", key="b7_moto_motor")
        moto_chasis = st.text_input("Nro. chasis", key="b7_moto_chasis")
    moto_observaciones = st.text_area("Estado actual / observaciones de la motocicleta", key="b7_moto_observaciones")

elif tipo_elemento == "Celular":
    st.markdown("#### 📱 Datos especiales de celular")
    cel1, cel2, cel3 = st.columns(3)
    with cel1:
        celular_marca = st.text_input("Marca", key="b7_celular_marca")
        celular_modelo = st.text_input("Modelo", key="b7_celular_modelo")
    with cel2:
        celular_color = st.text_input("Color", key="b7_celular_color")
        celular_imei = st.text_input("IMEI si se conoce", key="b7_celular_imei")
    with cel3:
        celular_linea = st.text_input("Número de línea si se conoce", key="b7_celular_linea")
        celular_condicion = st.selectbox("Condición", ["No determinada", "Encendido", "Apagado", "Bloqueado", "Roto"], key="b7_celular_condicion")

elif tipo_elemento == "Arma de fuego":
    st.markdown("#### ⚠️ Datos especiales de arma de fuego")
    ar1, ar2, ar3 = st.columns(3)
    with ar1:
        arma_tipo = st.text_input("Tipo de arma", placeholder="Pistola, revólver, escopeta...", key="b7_arma_tipo")
        arma_marca = st.text_input("Marca", key="b7_arma_marca")
    with ar2:
        arma_calibre = st.text_input("Calibre", key="b7_arma_calibre")
        arma_numeracion = st.text_input("Numeración visible", key="b7_arma_numeracion")
    with ar3:
        arma_cartuchos = st.text_input("Cartuchos / vainas / municiones", key="b7_arma_cartuchos")
        intervencion_especializada = st.text_input("Intervención especializada / autoridad", key="b7_intervencion_especializada")

texto_alerta = " ".join([
    tipo_elemento, descripcion, lugar_hallazgo, ubicacion_exacta, destino, propietario,
    celular_marca, celular_modelo, arma_tipo, arma_calibre, arma_cartuchos
])

alerta = detectar_no_manipular(texto_alerta)

if alerta:
    st.error("""
🚨 ALERTA DE NO MANIPULACIÓN / PRESERVACIÓN

El elemento informado podría requerir tratamiento especial.
NO manipular innecesariamente. Preservar. Dar intervención a autoridad o gabinete especializado cuando corresponda.
""")

if st.button("➕ Agregar elemento a la lista", use_container_width=True):
    if not descripcion and tipo_elemento not in ["Automóvil", "Motocicleta", "Celular", "Arma de fuego"]:
        st.error("Debe cargar una descripción del elemento.")
    else:
        elemento = {
            "id_elemento": len(st.session_state.b7_elementos) + 1,
            "tipo_elemento": tipo_elemento,
            "descripcion": descripcion,
            "estado": estado,
            "lugar_hallazgo": lugar_hallazgo,
            "ubicacion_exacta": ubicacion_exacta,
            "destino": destino,
            "propietario": propietario,
            "observaciones": observaciones,
            "alerta_no_manipular": "SÍ" if alerta else "NO",
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
            "moto_observaciones": moto_observaciones,
            "celular_marca": celular_marca,
            "celular_modelo": celular_modelo,
            "celular_color": celular_color,
            "celular_imei": celular_imei,
            "celular_linea": celular_linea,
            "celular_condicion": celular_condicion,
            "arma_tipo": arma_tipo,
            "arma_marca": arma_marca,
            "arma_calibre": arma_calibre,
            "arma_numeracion": arma_numeracion,
            "arma_cartuchos": arma_cartuchos,
            "intervencion_especializada": intervencion_especializada
        }
        st.session_state.b7_elementos.append(elemento)
        st.success("Elemento agregado a la lista de secuestros.")
        autoguardar_bloque(BLOQUE_ID)

st.write("---")
st.subheader("3. Lista de elementos secuestrados")

if not st.session_state.b7_elementos:
    st.info("Todavía no hay elementos secuestrados cargados.")
else:
    for idx, e in enumerate(st.session_state.b7_elementos, start=1):
        with st.expander(elemento_label(e, idx), expanded=False):
            st.json(e)
            if e.get("alerta_no_manipular") == "SÍ":
                st.warning("Elemento con alerta de preservación/no manipulación.")
            if st.button(f"🗑️ Eliminar elemento {idx}", key=f"b7_eliminar_{idx}"):
                st.session_state.b7_elementos.pop(idx - 1)
                for j, item in enumerate(st.session_state.b7_elementos, start=1):
                    item["id_elemento"] = j
                autoguardar_bloque(BLOQUE_ID)
                st.rerun()

st.write("---")
st.subheader("4. Generar acta de secuestro con elementos seleccionados")

if st.session_state.b7_elementos:
    st.info("Seleccione los elementos que fueron secuestrados en el mismo acto y ante el mismo testigo.")

    opciones = {
        elemento_label(e, idx): idx - 1
        for idx, e in enumerate(st.session_state.b7_elementos, start=1)
    }

    seleccion = st.multiselect(
        "Elementos que integran ESTA acta",
        list(opciones.keys()),
        key="b7_elementos_para_acta"
    )

    st.markdown("#### Testigo, lugar y firma de esta acta")
    t1, t2 = st.columns(2)
    with t1:
        testigo_nombre = st.text_input("Nombre y apellido del testigo", key="b7_testigo_nombre")
        testigo_dni = st.text_input("DNI del testigo", key="b7_testigo_dni")
        testigo_correo = st.text_input("Correo electrónico del testigo", key="b7_testigo_correo")
    with t2:
        testigo_domicilio = st.text_input("Domicilio del testigo", key="b7_testigo_domicilio")
        testigo_telefono = st.text_input("Teléfono del testigo", key="b7_testigo_telefono")

    with st.expander("Segundo testigo opcional para acta de elementos comunes"):
        t21, t22 = st.columns(2)
        with t21:
            testigo2_nombre = st.text_input("Nombre y apellido del segundo testigo", key="b7_testigo2_nombre")
            testigo2_dni = st.text_input("DNI del segundo testigo", key="b7_testigo2_dni")
        with t22:
            testigo2_domicilio = st.text_input("Domicilio del segundo testigo", key="b7_testigo2_domicilio")
            testigo2_telefono = st.text_input("Teléfono del segundo testigo", key="b7_testigo2_telefono")

    a1, a2, a3 = st.columns(3)
    with a1:
        fecha_acta = st.date_input("Fecha del acta", datetime.date.today(), key="b7_fecha_acta")
    with a2:
        hora_acta = st.time_input("Hora del acta", key="b7_hora_acta")
    with a3:
        lugar_acta = st.text_input("Lugar del acto de secuestro", key="b7_lugar_acta")

    observaciones_acta = st.text_area("Observaciones propias de esta acta", key="b7_observaciones_acta")

    st.markdown("#### Firma digital del testigo")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=180,
        width=500,
        drawing_mode="freedraw",
        key="b7_firma_testigo_canvas"
    )

    firma_path = convertir_firma_temp(canvas_result)

    if st.button("📄 GENERAR ACTA DE SECUESTRO PARA FIRMA", use_container_width=True):
        faltantes = []
        if not seleccion:
            faltantes.append("Seleccionar al menos un elemento")
        if not testigo_nombre:
            faltantes.append("Nombre del testigo")
        if not testigo_dni:
            faltantes.append("DNI del testigo")
        if not lugar_acta:
            faltantes.append("Lugar del acto de secuestro")
        if firma_path is None:
            faltantes.append("Firma digital del testigo")

        if faltantes:
            st.error("No se puede generar el acta. Faltan:")
            for f in faltantes:
                st.write(f"- {f}")
        else:
            indices = [opciones[x] for x in seleccion]
            elementos_acta = [st.session_state.b7_elementos[i] for i in indices]

            acta = {
                "id_acta": len(st.session_state.b7_actas_secuestro) + 1,
                "fecha_acta": str(fecha_acta),
                "hora_acta": str(hora_acta),
                "lugar_acta": lugar_acta,
                "testigo_nombre": testigo_nombre,
                "testigo_dni": testigo_dni,
                "testigo_domicilio": testigo_domicilio,
                "testigo_telefono": testigo_telefono,
                "testigo_correo": testigo_correo,
                "testigo2_nombre": testigo2_nombre,
                "testigo2_dni": testigo2_dni,
                "testigo2_domicilio": testigo2_domicilio,
                "testigo2_telefono": testigo2_telefono,
                "personal_actuante": personal_actuante,
                "elementos_ids": [e["id_elemento"] for e in elementos_acta],
                "elementos_resumen": [elemento_label(e) for e in elementos_acta],
                "observaciones_acta": observaciones_acta,
                "firmada": "SÍ"
            }

            if all(es_elemento_comun(e) for e in elementos_acta):
                pdf_acta = generar_pdf_elementos_comunes(datos_generales, acta, elementos_acta, firma_path)
                acta["plantilla_usada"] = "Acta de levantamiento y secuestro de elementos comunes"
            else:
                pdf_acta = generar_pdf_acta_secuestro(datos_generales, acta, elementos_acta, firma_path)
                acta["plantilla_usada"] = "Acta especial / vehículo / elemento con tratamiento diferenciado"

            st.session_state.b7_actas_secuestro.append(acta)
            autoguardar_bloque(BLOQUE_ID)

            st.success("Acta de secuestro generada y registrada en la lista de actas.")

            st.download_button(
                "📥 Descargar PDF de esta acta",
                data=pdf_acta,
                file_name=f"Acta_Secuestro_{acta['id_acta']}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            if firma_path and os.path.exists(firma_path):
                try:
                    os.unlink(firma_path)
                except Exception:
                    pass

st.write("---")
st.subheader("5. Actas de secuestro generadas")

if not st.session_state.b7_actas_secuestro:
    st.info("Todavía no hay actas de secuestro generadas.")
else:
    for acta in st.session_state.b7_actas_secuestro:
        with st.expander(f"Acta N° {acta.get('id_acta')} - Testigo: {acta.get('testigo_nombre')} - Elementos: {len(acta.get('elementos_ids', []))}"):
            st.json(acta)

st.write("---")
st.subheader("6. Exportar JSON para BLOQUE 8")

datos_b7 = {
    "bloque": 7,
    "modulo": "BLOQUE_7_SECUESTROS",
    "version": "lista_elementos_y_actas_firmables",
    "datos_generales": datos_generales,
    "elementos": st.session_state.b7_elementos,
    "actas_secuestro": st.session_state.b7_actas_secuestro,
    "resumen_para_acta_procedimiento": ""
}

# Resumen automatico para BLOQUE 8 / acta de procedimiento
if st.session_state.b7_elementos:
    resumenes = []
    for idx, e in enumerate(st.session_state.b7_elementos, start=1):
        alerta_txt = " con preservación especial" if e.get("alerta_no_manipular") == "SÍ" else ""
        resumenes.append(f"{idx}) {elemento_label(e)}; destino: {e.get('destino','S/D')}{alerta_txt}")
    datos_b7["resumen_para_acta_procedimiento"] = "Se registran los siguientes elementos secuestrados: " + " | ".join(resumenes)

json_b7 = json.dumps(datos_b7, indent=4, ensure_ascii=False)

st.download_button(
    "📥 Descargar JSON Bloque 7 completo",
    data=json_b7,
    file_name="bloque_7_secuestros.json",
    mime="application/json",
    use_container_width=True
)

with st.expander("Ver JSON Bloque 7"):
    st.code(json_b7, language="json")

# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
