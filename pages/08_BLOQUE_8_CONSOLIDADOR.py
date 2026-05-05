import streamlit as st
import json
from datetime import datetime
from fpdf import FPDF

# =====================================================
# BLOQUE 8 - CONSOLIDADOR FINAL
# ÚNICO BLOQUE NUEVO
# NO MODIFICA BLOQUES 1 A 7
# =====================================================

st.set_page_config(page_title="SVI - Bloque 8 Consolidador", layout="wide", page_icon="📑")


def safe(v, default="S/D"):
    if v is None:
        return default
    if isinstance(v, str) and not v.strip():
        return default
    return str(v)


def normalizar_texto_pdf(texto):
    if texto is None:
        return ""
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.", "–": "-", "—": "-",
        "“": '"', "”": '"', "’": "'"
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


def detectar_bloque(datos):
    """Detecta el bloque por estructura, sin exigir que los JSON sean idénticos."""
    if not isinstance(datos, dict):
        return "DESCONOCIDO"

    modulo = str(datos.get("modulo", "")).upper()
    bloque = datos.get("bloque")

    if modulo == "BLOQUE_2_ARRESTADO" or "arrestados" in datos:
        return "BLOQUE_2"
    if bloque == 5 or "autoridad_interviniente" in datos or "directivas" in datos:
        return "BLOQUE_5"
    if bloque == 7 or "tipo_secuestro" in datos or "descripcion" in datos and "destino" in datos:
        return "BLOQUE_7"
    if "nro_acta" in datos or "data_operativa" in datos or "relato" in datos and "personal" in datos:
        return "BLOQUE_1"
    if "filiacion" in datos and "contenido" in datos:
        nombre_archivo = str(datos.get("_nombre_archivo", "")).lower()
        if "testigo" in nombre_archivo:
            return "BLOQUE_4"
        if "entrevista" in nombre_archivo or "victima" in nombre_archivo or "damnificado" in nombre_archivo:
            return "BLOQUE_3"
        return "BLOQUE_3_O_4"
    if "inspeccion" in datos or "croquis" in datos or "preservado" in datos or "actante_data" in datos:
        return "BLOQUE_6"

    return "DESCONOCIDO"


def agregar_json(diccionario, bloque, datos):
    if bloque == "BLOQUE_3_O_4":
        diccionario.setdefault("BLOQUE_3_O_4", []).append(datos)
    elif bloque in ["BLOQUE_3", "BLOQUE_4", "BLOQUE_7"]:
        diccionario.setdefault(bloque, []).append(datos)
    else:
        diccionario[bloque] = datos


def construir_acta(datos):
    b1 = datos.get("BLOQUE_1", {})
    b2 = datos.get("BLOQUE_2", {})
    b5 = datos.get("BLOQUE_5", {})
    b6 = datos.get("BLOQUE_6", {})
    b7_lista = datos.get("BLOQUE_7", [])
    entrevistas = datos.get("BLOQUE_3", []) + datos.get("BLOQUE_3_O_4", [])
    testigos = datos.get("BLOQUE_4", [])

    ciudad = safe(b7_lista[0].get("ciudad"), "") if b7_lista else ""
    departamento = safe(b7_lista[0].get("departamento"), "") if b7_lista else ""
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    hora_hoy = datetime.now().strftime("%H:%M")

    nro_acta = safe(b1.get("nro_acta"), "S/N")
    incidencia = safe(b1.get("incidencia"), "S/D")
    dependencia = safe(b1.get("dependencia_otra") if b1.get("dependencia") == "OTRO" else b1.get("dependencia"), "S/D")
    movil = safe(b1.get("movil"), "S/D")
    personal = safe(b1.get("personal"), "S/D")
    refuerzo = safe(b1.get("refuerzo"), "S/D")
    lugar_hecho = safe(b1.get("l_hecho"), "S/D")
    lugar_apre = safe(b1.get("l_apre"), "S/D")
    relato = safe(b1.get("relato"), "")

    partes = []
    partes.append("POLICIA DE LA PROVINCIA DE SANTA FE")
    partes.append("UNIDAD REGIONAL II")
    partes.append("ACTA DE PROCEDIMIENTO")
    partes.append("")
    partes.append(f"Acta Nro.: {nro_acta}    Incidencia 911: {incidencia}")
    partes.append(f"Fecha de confeccion: {fecha_hoy}    Hora: {hora_hoy}")
    if ciudad or departamento:
        partes.append(f"Ciudad: {ciudad or 'S/D'}    Departamento: {departamento or 'S/D'}    Provincia: Santa Fe")
    partes.append(f"Dependencia: {dependencia}    Movil: {movil}")
    partes.append(f"Personal actuante: {personal}")
    if refuerzo != "S/D":
        partes.append(f"Refuerzo / apoyo: {refuerzo}")
    partes.append("")

    partes.append("I. DATOS DEL PROCEDIMIENTO")
    partes.append(f"Lugar del hecho: {lugar_hecho}.")
    partes.append(f"Lugar de aprehension: {lugar_apre}.")
    partes.append("")

    partes.append("II. RELATO CIRCUNSTANCIADO")
    if relato:
        partes.append(relato)
    else:
        partes.append("[Completar relato circunstanciado del Bloque 1].")
    partes.append("")

    if b2.get("arrestados"):
        partes.append("III. PERSONAS APREHENDIDAS / ARRESTADAS")
        for idx, a in enumerate(b2.get("arrestados", []), start=1):
            nombre = f"{safe(a.get('apellido'), '')} {safe(a.get('nombre'), '')}".strip()
            partes.append(
                f"Arrestado Nro. {idx}: {nombre or 'S/D'}, DNI {safe(a.get('dni'))}, "
                f"alias/apodo {safe(a.get('apodo'))}, edad {safe(a.get('edad'))}, domicilio {safe(a.get('domicilio'))}. "
                f"Consulta 911: {safe(a.get('consulta_911'))}; resultado: {safe(a.get('resultado_911'))}. "
                f"Lectura de derechos: {safe(a.get('derechos'))}. Comunicación familiar: {safe(a.get('comunicacion'))}."
            )
            if a.get("lesiones") == "SI":
                partes.append(
                    f"Respecto de lesiones/asistencia: {safe(a.get('detalle_lesiones'))}. "
                    f"Atencion: {safe(a.get('atencion'))}; hospital: {safe(a.get('hospital'))}; "
                    f"medico: {safe(a.get('medico'))}; diagnostico: {safe(a.get('diagnostico'))}."
                )
        partes.append("")

    if entrevistas:
        partes.append("IV. ENTREVISTAS / VICTIMAS / DAMNIFICADOS")
        for idx, e in enumerate(entrevistas, start=1):
            f = e.get("filiacion", {})
            partes.append(
                f"Entrevistado Nro. {idx}: {safe(f.get('nombre'))}, DNI {safe(f.get('dni'))}, "
                f"domicilio {safe(f.get('domicilio'))}, telefono {safe(f.get('telefono'))}, correo {safe(f.get('correo'))}. "
                f"Sintesis: {safe(e.get('contenido'), '[Completar sintesis]')}"
            )
        partes.append("Se deja constancia que las actas de entrevista completas, con sus firmas, se agregan como anexo cuando corresponda.")
        partes.append("")

    if testigos:
        partes.append("V. TESTIGOS")
        for idx, t in enumerate(testigos, start=1):
            f = t.get("filiacion", {})
            partes.append(
                f"Testigo Nro. {idx}: {safe(f.get('nombre'))}, DNI {safe(f.get('dni'))}, "
                f"domicilio {safe(f.get('domicilio'))}, telefono {safe(f.get('telefono'))}, correo {safe(f.get('correo'))}. "
                f"Sintesis testimonial: {safe(t.get('contenido'), '[Completar sintesis]')}"
            )
        partes.append("Se deja constancia que las declaraciones testimoniales completas, con sus firmas, se agregan como anexo cuando corresponda.")
        partes.append("")

    if b5:
        partes.append("VI. CONSULTA JUDICIAL / DIRECTIVAS")
        partes.append(
            f"Se mantuvo comunicacion con {safe(b5.get('autoridad_interviniente'))}, siendo atendida por "
            f"{safe(b5.get('nombre_secretario_fiscal'))}, quien impartio las siguientes directivas: "
            f"{safe(b5.get('directivas'))}. Competencia validada: {safe(b5.get('competencia_validada'))}. "
            f"Hecho critico: {safe(b5.get('hecho_critico'))}."
        )
        if b5.get("resena"):
            partes.append(f"Resena de consulta: {b5.get('resena')}")
        partes.append("")

    if b6:
        partes.append("VII. INSPECCION / CROQUIS")
        partes.append("Se deja constancia de la incorporacion de datos de inspeccion/croquis generados por el Bloque 6. El croquis y/o acta grafica se agrega como anexo independiente cuando corresponda.")
        if b6.get("inspeccion"):
            partes.append(f"Resumen de inspeccion: {safe(b6.get('inspeccion'))}")
        partes.append("")

    if b7_lista:
        partes.append("VIII. SECUESTROS / DEPOSITOS")
        for idx, s in enumerate(b7_lista, start=1):
            partes.append(
                f"Secuestro Nro. {idx}: tipo {safe(s.get('tipo_secuestro'))}, formulario {safe(s.get('formulario'))}, "
                f"codigo {safe(s.get('codigo'))}. Lugar: {safe(s.get('lugar_secuestro'))}. "
                f"Ubicacion precisa: {safe(s.get('ubicacion_exacta'))}. Motivo: {safe(s.get('motivo'))}. "
                f"Descripcion: {safe(s.get('descripcion'))}. Estado: {safe(s.get('estado'))}. Destino/deposito: {safe(s.get('destino'))}."
            )
            if s.get("alerta_no_manipular") == "SÍ":
                partes.append("Se deja constancia que el elemento fue preservado sin manipulacion innecesaria por posible tratamiento especial.")
        partes.append("Las actas de secuestro completas se agregan como anexo independiente cuando corresponda.")
        partes.append("")

    partes.append("IX. ANEXOS MENCIONADOS")
    anexos = []
    if entrevistas:
        anexos.append("Acta/s de entrevista")
    if testigos:
        anexos.append("Acta/s de declaracion testimonial")
    if b6:
        anexos.append("Croquis / inspeccion ocular")
    if b7_lista:
        anexos.append("Acta/s de secuestro y deposito")
    if b2.get("arrestados"):
        anexos.append("Planilla / JSON de arrestados")
    if anexos:
        for anexo in anexos:
            partes.append(f"- {anexo}")
    else:
        partes.append("No se registran anexos importados al momento.")
    partes.append("")

    partes.append("X. CIERRE")
    partes.append(
        "No siendo para mas, se da por finalizada la presente acta de procedimiento, previa lectura y ratificacion "
        "de su contenido, firmando al pie el personal actuante para debida constancia."
    )
    partes.append("")
    partes.append("Firma personal actuante: ______________________________")
    partes.append("Aclaracion: __________________________________________")

    return "\n".join(partes)


def generar_pdf_acta(texto):
    pdf = FPDF()
    pdf.set_margins(18, 15, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "ACTA DE PROCEDIMIENTO CONSOLIDADA", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "", 11)
    for linea in normalizar_texto_pdf(texto).split("\n"):
        if not linea.strip():
            pdf.ln(3)
        elif len(linea) < 60 and (linea.endswith(":") or linea[:3] in ["I. ", "II", "III", "IV.", "V. ", "VI.", "VII", "VIII", "IX.", "X. "]):
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 7, linea)
            pdf.set_font("Arial", "", 11)
        else:
            pdf.multi_cell(0, 7, linea, align="J")

    pdf.set_y(-22)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "Generado por S.I.V. - Bloque 8 Consolidador", align="R")
    return pdf_bytes(pdf)


def generar_remito(datos):
    b1 = datos.get("BLOQUE_1", {})
    b2 = datos.get("BLOQUE_2", {})
    b5 = datos.get("BLOQUE_5", {})
    b6 = datos.get("BLOQUE_6", {})
    b7_lista = datos.get("BLOQUE_7", [])
    entrevistas = datos.get("BLOQUE_3", []) + datos.get("BLOQUE_3_O_4", [])
    testigos = datos.get("BLOQUE_4", [])

    pdf = FPDF()
    pdf.set_margins(18, 15, 18)
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "REMITO DE ENTREGA DE ACTUACIONES", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Arial", "", 11)
    texto = (
        f"En fecha {datetime.now().strftime('%d/%m/%Y')} siendo las {datetime.now().strftime('%H:%M')} horas, "
        f"se deja constancia de la remision de actuaciones vinculadas al Acta Nro. {safe(b1.get('nro_acta'), 'S/N')} "
        f"/ Incidencia 911 {safe(b1.get('incidencia'), 'S/D')}."
    )
    pdf.multi_cell(0, 8, normalizar_texto_pdf(texto), align="J")
    pdf.ln(5)

    items = [
        "Acta de procedimiento consolidada",
        f"JSON Bloque 1 / datos base: {'SI' if b1 else 'NO'}",
        f"Arrestados informados: {len(b2.get('arrestados', []))}",
        f"Entrevistas / victimas / damnificados: {len(entrevistas)}",
        f"Testigos: {len(testigos)}",
        f"Consulta judicial / directivas: {'SI' if b5 else 'NO'}",
        f"Croquis / inspeccion ocular: {'SI' if b6 else 'NO'}",
        f"Actas de secuestro: {len(b7_lista)}",
    ]

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Documentacion remitida:", ln=True)
    pdf.set_font("Arial", "", 11)
    for item in items:
        pdf.cell(0, 7, normalizar_texto_pdf(f"- {item}"), ln=True)

    pdf.ln(18)
    pdf.cell(90, 8, "____________________________", ln=False, align="C")
    pdf.cell(90, 8, "____________________________", ln=True, align="C")
    pdf.cell(90, 8, "Entrega", ln=False, align="C")
    pdf.cell(90, 8, "Recibe", ln=True, align="C")

    return pdf_bytes(pdf)


def advertencias(datos):
    avisos = []
    if "BLOQUE_1" not in datos:
        avisos.append("Falta importar JSON del BLOQUE 1: datos base y relato central.")
    else:
        b1 = datos["BLOQUE_1"]
        for campo, nombre in [("nro_acta", "Nro. de acta"), ("incidencia", "Incidencia 911"), ("personal", "Personal actuante"), ("relato", "Relato circunstanciado")]:
            if not str(b1.get(campo, "")).strip():
                avisos.append(f"BLOQUE 1: llenar campo {nombre}.")
    return avisos


st.title("📑 BLOQUE 8 — CONSOLIDADOR FINAL")
st.subheader("Importa JSON de los bloques y genera el acta final")

st.warning("Regla de seguridad: este bloque NO modifica los Bloques 1 a 7. Solo lee archivos JSON exportados.")

if "bloque8_datos" not in st.session_state:
    st.session_state.bloque8_datos = {}
if "bloque8_texto" not in st.session_state:
    st.session_state.bloque8_texto = ""

archivos = st.file_uploader(
    "📥 Importar JSON generados por Bloques 1 a 7",
    type=["json"],
    accept_multiple_files=True
)

if archivos:
    datos_importados = {}
    errores = []
    for archivo in archivos:
        try:
            contenido = json.loads(archivo.getvalue().decode("utf-8"))
            if isinstance(contenido, dict):
                contenido["_nombre_archivo"] = archivo.name
            bloque = detectar_bloque(contenido)
            agregar_json(datos_importados, bloque, contenido)
        except Exception as e:
            errores.append(f"{archivo.name}: {e}")

    st.session_state.bloque8_datos = datos_importados

    if errores:
        st.error("Se detectaron errores al importar:")
        for e in errores:
            st.write(f"- {e}")

    st.success("JSON importados y clasificados.")

st.divider()

if st.session_state.bloque8_datos:
    st.write("### 📦 Bloques detectados")
    cols = st.columns(4)
    claves = list(st.session_state.bloque8_datos.keys())
    for i, clave in enumerate(claves):
        valor = st.session_state.bloque8_datos[clave]
        cantidad = len(valor) if isinstance(valor, list) else 1
        cols[i % 4].info(f"{clave}: {cantidad}")

    avisos = advertencias(st.session_state.bloque8_datos)
    if avisos:
        st.error("⚠️ Faltan datos para una consolidación completa:")
        for aviso in avisos:
            st.write(f"- {aviso}")

    if st.button("🧠 ARMAR BORRADOR DEL ACTA FINAL", use_container_width=True):
        st.session_state.bloque8_texto = construir_acta(st.session_state.bloque8_datos)

    st.write("### ✍️ Vista previa editable")
    texto_editado = st.text_area(
        "Revise, corrija o complete el acta antes de generar PDF:",
        value=st.session_state.bloque8_texto,
        height=520
    )
    st.session_state.bloque8_texto = texto_editado

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.session_state.bloque8_texto.strip():
            st.download_button(
                "📄 Descargar ACTA FINAL PDF",
                data=generar_pdf_acta(st.session_state.bloque8_texto),
                file_name="ACTA_PROCEDIMIENTO_CONSOLIDADA.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.info("Primero arme o escriba el borrador del acta.")

    with c2:
        st.download_button(
            "📦 Descargar JSON Consolidado",
            data=json.dumps(st.session_state.bloque8_datos, indent=4, ensure_ascii=False),
            file_name="bloque8_consolidado.json",
            mime="application/json",
            use_container_width=True
        )

    with c3:
        st.download_button(
            "📑 Descargar REMITO PDF",
            data=generar_remito(st.session_state.bloque8_datos),
            file_name="REMITO_ENTREGA_ACTUACIONES.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with st.expander("Ver JSON consolidado"):
        st.json(st.session_state.bloque8_datos)
else:
    st.info("Importe los JSON de los bloques para comenzar la consolidación.")
