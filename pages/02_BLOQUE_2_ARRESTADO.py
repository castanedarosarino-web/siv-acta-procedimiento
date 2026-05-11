import streamlit as st
import json
import io
import base64
from datetime import datetime, date

try:
    from fpdf import FPDF
except Exception:
    FPDF = None

st.set_page_config(page_title="SIVAP - Bloque 2 Arrestado", layout="wide")

# ============================================================
# GUARDADO SEGURO - COMPATIBLE CON APP PRINCIPAL
# ============================================================
try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
except Exception:
    def iniciar_guardado_seguro(bloque_id):
        pass
    def panel_guardado_seguro(bloque_id):
        pass
    def autoguardar_bloque(bloque_id):
        pass

BLOQUE_ID = "BLOQUE_2_ARRESTADO"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

# ============================================================
# FUNCIONES BASE
# ============================================================
def calcular_edad(fecha):
    if not fecha:
        return ""
    hoy = date.today()
    return hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))


def fecha_desde_texto(valor, defecto=date(2000, 1, 1)):
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str) and valor:
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except Exception:
            return defecto
    return defecto


def indice_opcion(opciones, valor, defecto=0):
    try:
        return opciones.index(valor)
    except Exception:
        return defecto


def nuevo_arrestado():
    return {
        "dni": "",
        "apellido": "",
        "nombre": "",
        "apodo": "",
        "papa": "",
        "mama": "",
        "ciudad": "ROSARIO",
        "provincia": "SANTA FE",
        "pais": "ARGENTINA",
        "nacionalidad": "ARGENTINA",
        "fecha_nac": "",
        "edad": "",
        "estado_civil": "SOLTERO/A",
        "profesion": "",
        "lee": "SI",
        "escribe": "SI",
        "domicilio": "",
        "posee_dni": "NO",
        "consulta_911": "SI",
        "operador": "",
        "resultado_911": "NO POSEE PEDIDO DE CAPTURA",
        "cuij": "",
        "caratula": "",
        "autoridad": "",
        "delito": "",
        "lesiones": "NO",
        "detalle_lesiones": "",
        "origen_lesiones": "",
        "atencion": "NO REQUIRIÓ",
        "movil_policial": "",
        "dotacion": "",
        "hospital": "",
        "medico": "",
        "diagnostico": "",
        "resultado": "",
        "certificado": "NO",
        "derechos": "SI",
        "constancia_derechos": "",
        "comunicacion": "NO",
        "familiar": "",
        "telefono": "",
        "resultado_comunicacion": "",
        "secuestro": "NO",
        "detalle_sec": "",
        "deposito": "NO",
        "detalle_dep": ""
    }


def nuevo_testigo_aprehension():
    return {
        "nombre_apellido": "",
        "dni": "",
        "domicilio": "",
        "telefono": "",
        "firma_texto": "",
        "firma_imagen_base64": ""
    }


def asegurar_arrestado(a):
    base = nuevo_arrestado()
    if isinstance(a, dict):
        base.update(a)
    return base


def limpiar_widget_keys_bloque_2():
    prefijos = [
        "dni", "ape", "nom", "apo", "pa", "ma", "ciu", "prov", "pais", "nac",
        "fn", "dom", "ec", "pro", "lee", "esc", "pdni", "c911", "op", "res",
        "cuij", "car", "aut", "del", "les", "dles", "oles", "aten", "mov",
        "dot", "hos", "med", "diag", "resu", "cert", "der", "cder", "com",
        "fam", "tel", "rcom", "sec", "dsec", "dep", "ddep"
    ]
    borrar = []
    for key in st.session_state.keys():
        if any(str(key).startswith(p) for p in prefijos):
            borrar.append(key)
    for key in borrar:
        try:
            del st.session_state[key]
        except Exception:
            pass


def normalizar_arrestados_importados(datos):
    arrestados = datos.get("arrestados", []) if isinstance(datos, dict) else []
    if not isinstance(arrestados, list):
        arrestados = []
    return [asegurar_arrestado(a) for a in arrestados]


def generar_resumen_acta(arrestados):
    if not arrestados:
        return ""
    textos = []
    for idx, a in enumerate(arrestados, start=1):
        nombre = f"{a.get('apellido', '')}, {a.get('nombre', '')}".strip(" ,") or "persona no identificada"
        dni = f", DNI {a.get('dni')}" if a.get("dni") else ""
        domicilio = f", domiciliada en {a.get('domicilio')}" if a.get("domicilio") else ""
        consulta = ""
        if a.get("consulta_911") == "SI":
            consulta = f" Consultado el sistema 911, se informó: {a.get('resultado_911', '')}."
        lesiones = ""
        if a.get("lesiones") == "SI":
            lesiones = f" Presentaba/refirió lesiones: {a.get('detalle_lesiones', '')}."
        elif a.get("lesiones") == "NO":
            lesiones = " No presentaba lesiones visibles al momento de la carga."
        derechos = " Fue impuesto de los derechos que le asisten." if a.get("derechos") == "SI" else ""
        textos.append(f"Se individualizó al aprehendido N° {idx} como {nombre}{dni}{domicilio}.{consulta}{lesiones}{derechos}")
    return " ".join(textos)


def construir_json_sivap():
    numero_acta = st.session_state.get("actuacion_numero_acta", "")
    return {
        "sistema": "S.I.V.A.P.",
        "tipo_archivo": "colaboracion_json",
        "bloque": BLOQUE_ID,
        "autor_carga": {
            "ni": st.session_state.get("autor_ni", ""),
            "nombre_apellido": st.session_state.get("autor_nombre_apellido", ""),
            "jerarquia": st.session_state.get("autor_jerarquia", ""),
            "dependencia": st.session_state.get("autor_dependencia", ""),
            "rol_operativo": st.session_state.get("autor_rol_operativo", ""),
            "dispositivo": "Celular validado"
        },
        "actuacion": {
            "numero_acta": numero_acta,
            "fecha": st.session_state.get("actuacion_fecha", ""),
            "hora": st.session_state.get("actuacion_hora", ""),
            "dependencia": st.session_state.get("actuacion_dependencia", ""),
            "lugar": st.session_state.get("actuacion_lugar", "")
        },
        "arrestados": st.session_state.get("arrestados", []),
        "acta_aprehension": {
            "testigo_aprehension": st.session_state.get("testigo_aprehension", nuevo_testigo_aprehension()),
            "observaciones": st.session_state.get("observaciones_aprehension", "")
        },
        "resumen_para_acta_procedimiento": {
            "tipo": "arrestado_aprehendido",
            "texto_para_acta": generar_resumen_acta(st.session_state.get("arrestados", [])),
            "incorporar": True
        },
        "fecha_exportacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def nombre_archivo_json():
    numero = st.session_state.get("actuacion_numero_acta", "SIN_ACTA") or "SIN_ACTA"
    ni = st.session_state.get("autor_ni", "SIN_NI") or "SIN_NI"
    numero = str(numero).replace("/", "-").replace(" ", "_")
    ni = str(ni).replace(".", "").replace(" ", "_")
    return f"SIVAP_ACTA_{numero}_BLOQUE_2_ARRESTADO_NI_{ni}.json"


def pdf_texto_seguro(valor):
    return str(valor or "").replace("—", "-").replace("“", '"').replace("”", '"').replace("’", "'")


def generar_pdf_bloque_2(data):
    if FPDF is None:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "ACTA DE APREHENSION - BLOQUE 2 ARRESTADO/APREHENDIDO", ln=True, align="C")
    pdf.ln(4)

    actuacion = data.get("actuacion", {})
    autor = data.get("autor_carga", {})
    testigo = data.get("acta_aprehension", {}).get("testigo_aprehension", {})

    def mc(txt):
        pdf.multi_cell(0, 6, pdf_texto_seguro(txt))

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DATOS DE LA ACTUACION", ln=True)
    pdf.set_font("Arial", "", 10)
    mc(f"Acta N°: {actuacion.get('numero_acta', '')}    Fecha: {actuacion.get('fecha', '')}    Hora: {actuacion.get('hora', '')}")
    mc(f"Dependencia: {actuacion.get('dependencia', '')}")
    mc(f"Lugar: {actuacion.get('lugar', '')}")
    pdf.ln(2)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "PERSONAL INTERVINIENTE / CARGA", ln=True)
    pdf.set_font("Arial", "", 10)
    mc(f"NI: {autor.get('ni', '')} - {autor.get('jerarquia', '')} {autor.get('nombre_apellido', '')}")
    mc(f"Dependencia: {autor.get('dependencia', '')}    Rol: {autor.get('rol_operativo', '')}")
    pdf.ln(2)

    arrestados = data.get("arrestados", [])
    for idx, a in enumerate(arrestados, start=1):
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, f"ARRESTADO / APREHENDIDO N° {idx}", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(f"Apellido y nombre: {a.get('apellido', '')}, {a.get('nombre', '')}")
        mc(f"DNI: {a.get('dni', '')}    Apodo: {a.get('apodo', '')}    Edad: {a.get('edad', '')}")
        mc(f"Padre: {a.get('papa', '')}    Madre: {a.get('mama', '')}")
        mc(f"Nacimiento: {a.get('fecha_nac', '')}    Nacionalidad: {a.get('nacionalidad', '')}")
        mc(f"Domicilio: {a.get('domicilio', '')}")
        mc(f"Estado civil: {a.get('estado_civil', '')}    Profesión: {a.get('profesion', '')}    Lee: {a.get('lee', '')}    Escribe: {a.get('escribe', '')}")
        mc(f"Posee DNI físico: {a.get('posee_dni', '')}")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "Consulta 911", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(f"Consulta realizada: {a.get('consulta_911', '')}    Operador: {a.get('operador', '')}")
        mc(f"Resultado: {a.get('resultado_911', '')}")
        if a.get("resultado_911") == "POSEE PEDIDO DE CAPTURA":
            mc(f"CUIJ: {a.get('cuij', '')}    Carátula: {a.get('caratula', '')}")
            mc(f"Autoridad: {a.get('autoridad', '')}    Delito: {a.get('delito', '')}")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "Lesiones y asistencia médica", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(f"Presenta lesiones: {a.get('lesiones', '')}")
        if a.get("lesiones") == "SI":
            mc(f"Detalle: {a.get('detalle_lesiones', '')}")
            mc(f"Origen referido: {a.get('origen_lesiones', '')}")
            mc(f"Atención médica: {a.get('atencion', '')}")
            mc(f"Móvil policial: {a.get('movil_policial', '')}    Dotación: {a.get('dotacion', '')}")
            mc(f"Hospital: {a.get('hospital', '')}    Médico: {a.get('medico', '')}")
            mc(f"Diagnóstico: {a.get('diagnostico', '')}    Resultado: {a.get('resultado', '')}")
            mc(f"Certificado médico: {a.get('certificado', '')}")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "Derechos y comunicación", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(f"Lectura de derechos: {a.get('derechos', '')}")
        if a.get("constancia_derechos"):
            mc(f"Constancia: {a.get('constancia_derechos', '')}")
        mc(f"Comunicación familiar: {a.get('comunicacion', '')}")
        if a.get("comunicacion") == "SI":
            mc(f"Familiar: {a.get('familiar', '')}    Teléfono: {a.get('telefono', '')}")
            mc(f"Resultado: {a.get('resultado_comunicacion', '')}")
        pdf.ln(1)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "Secuestro relacionado", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(f"Secuestro causa: {a.get('secuestro', '')}")
        if a.get("secuestro") == "SI":
            mc(f"Detalle: {a.get('detalle_sec', '')}")
        mc(f"Depósito: {a.get('deposito', '')}")
        if a.get("deposito") == "SI":
            mc(f"Detalle depósito: {a.get('detalle_dep', '')}")
        pdf.ln(4)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "TESTIGO DE ACTUACION / APREHENSION", ln=True)
    pdf.set_font("Arial", "", 10)
    mc(f"Nombre y apellido: {testigo.get('nombre_apellido', '')}")
    mc(f"DNI: {testigo.get('dni', '')}")
    mc(f"Domicilio: {testigo.get('domicilio', '')}")
    mc(f"Teléfono: {testigo.get('telefono', '')}")
    if testigo.get("firma_texto"):
        mc(f"Firma digital registrada: {testigo.get('firma_texto', '')}")

    observaciones = data.get("acta_aprehension", {}).get("observaciones", "")
    if observaciones:
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "OBSERVACIONES DEL ACTA DE APREHENSION", ln=True)
        pdf.set_font("Arial", "", 10)
        mc(observaciones)

    pdf.ln(10)
    pdf.cell(0, 7, "______________________________        ______________________________", ln=True, align="C")
    pdf.cell(0, 7, "Firma personal interviniente                Firma testigo actuación", ln=True, align="C")

    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1")
    return bytes(salida)


# ============================================================
# ESTADO INICIAL
# ============================================================
if "arrestados" not in st.session_state:
    st.session_state.arrestados = [nuevo_arrestado()]

if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1

if "testigo_aprehension" not in st.session_state:
    st.session_state.testigo_aprehension = nuevo_testigo_aprehension()

if "observaciones_aprehension" not in st.session_state:
    st.session_state.observaciones_aprehension = ""

for key in [
    "autor_ni", "autor_nombre_apellido", "autor_jerarquia", "autor_dependencia", "autor_rol_operativo",
    "actuacion_numero_acta", "actuacion_fecha", "actuacion_hora", "actuacion_dependencia", "actuacion_lugar"
]:
    if key not in st.session_state:
        st.session_state[key] = ""

# ============================================================
# CABECERA
# ============================================================
st.title("👤 BLOQUE 2 - ARRESTADO / APREHENDIDO")
st.caption("Carga modular del arrestado/aprehendido. Exporta JSON para WhatsApp, importa colaboración recibida y genera PDF propio del bloque.")

# ============================================================
# CAPA 0 - IMPORTAR JSON RECIBIDO POR WHATSAPP
# Debe ejecutarse antes de crear widgets de arrestados.
# ============================================================
with st.expander("📥 Importar JSON recibido por WhatsApp", expanded=False):
    archivo_json = st.file_uploader("Seleccionar archivo JSON de BLOQUE 2", type=["json"], key="importador_bloque_2_json")
    if archivo_json is not None:
        try:
            datos_importados = json.load(archivo_json)
            bloque_importado = datos_importados.get("bloque") or datos_importados.get("modulo")
            if bloque_importado != BLOQUE_ID:
                st.warning("El archivo no parece corresponder a BLOQUE 2 ARRESTADO. Revise antes de incorporar.")
            st.success("JSON leído correctamente. Revise e incorpore si corresponde.")

            if st.button("✅ Incorporar datos al BLOQUE 2", key="btn_incorporar_json_bloque_2"):
                arrestados_importados = normalizar_arrestados_importados(datos_importados)
                if not arrestados_importados:
                    arrestados_importados = [nuevo_arrestado()]
                st.session_state.arrestados = arrestados_importados
                st.session_state.cantidad = len(arrestados_importados)

                if isinstance(datos_importados.get("autor_carga"), dict):
                    autor = datos_importados.get("autor_carga", {})
                    st.session_state.autor_ni = autor.get("ni", "")
                    st.session_state.autor_nombre_apellido = autor.get("nombre_apellido", "")
                    st.session_state.autor_jerarquia = autor.get("jerarquia", "")
                    st.session_state.autor_dependencia = autor.get("dependencia", "")
                    st.session_state.autor_rol_operativo = autor.get("rol_operativo", "")

                if isinstance(datos_importados.get("actuacion"), dict):
                    act = datos_importados.get("actuacion", {})
                    st.session_state.actuacion_numero_acta = act.get("numero_acta", "")
                    st.session_state.actuacion_fecha = act.get("fecha", "")
                    st.session_state.actuacion_hora = act.get("hora", "")
                    st.session_state.actuacion_dependencia = act.get("dependencia", "")
                    st.session_state.actuacion_lugar = act.get("lugar", "")

                acta_aprehension = datos_importados.get("acta_aprehension", {})
                if isinstance(acta_aprehension, dict):
                    testigo = acta_aprehension.get("testigo_aprehension", {})
                    if isinstance(testigo, dict):
                        nuevo_t = nuevo_testigo_aprehension()
                        nuevo_t.update(testigo)
                        st.session_state.testigo_aprehension = nuevo_t
                    st.session_state.observaciones_aprehension = acta_aprehension.get("observaciones", "")

                limpiar_widget_keys_bloque_2()
                st.success("Datos incorporados al BLOQUE 2.")
                st.rerun()
        except Exception as e:
            st.error(f"No se pudo leer el JSON: {e}")

# ============================================================
# CAPA 1 - IDENTIDAD POLICIAL Y ACTUACION
# ============================================================
with st.expander("🪪 Identidad policial y actuación", expanded=False):
    st.subheader("Identidad policial")
    c1, c2, c3 = st.columns(3)
    st.session_state.autor_ni = c1.text_input("NI policial / PIN", value=st.session_state.autor_ni, key="widget_autor_ni")
    st.session_state.autor_nombre_apellido = c2.text_input("Nombre y apellido", value=st.session_state.autor_nombre_apellido, key="widget_autor_nombre")
    st.session_state.autor_jerarquia = c3.text_input("Jerarquía", value=st.session_state.autor_jerarquia, key="widget_autor_jerarquia")

    c4, c5 = st.columns(2)
    st.session_state.autor_dependencia = c4.text_input("Dependencia", value=st.session_state.autor_dependencia, key="widget_autor_dependencia")
    roles = ["Actante", "Colaborador", "Ambos", ""]
    st.session_state.autor_rol_operativo = c5.selectbox(
        "Rol operativo",
        roles,
        index=indice_opcion(roles, st.session_state.autor_rol_operativo, 0),
        key="widget_autor_rol"
    )
    st.info("Dispositivo: celular validado")

    st.subheader("Actuación")
    c6, c7, c8 = st.columns(3)
    st.session_state.actuacion_numero_acta = c6.text_input("Número de acta", value=st.session_state.actuacion_numero_acta, key="widget_acta_numero")
    st.session_state.actuacion_fecha = c7.text_input("Fecha", value=st.session_state.actuacion_fecha, placeholder="AAAA-MM-DD", key="widget_acta_fecha")
    st.session_state.actuacion_hora = c8.text_input("Hora", value=st.session_state.actuacion_hora, placeholder="HH:MM", key="widget_acta_hora")
    c9, c10 = st.columns(2)
    st.session_state.actuacion_dependencia = c9.text_input("Dependencia / repartición", value=st.session_state.actuacion_dependencia, key="widget_acta_dependencia")
    st.session_state.actuacion_lugar = c10.text_input("Lugar", value=st.session_state.actuacion_lugar, key="widget_acta_lugar")

# ============================================================
# CAPA 2 - DATOS DEL ARRESTADO / APREHENDIDO
# ============================================================
st.subheader("📌 Datos del arrestado/aprehendido")

cant = st.number_input("Cantidad de arrestados", 1, 10, int(st.session_state.cantidad), key="cantidad_arrestados_widget")
st.session_state.cantidad = int(cant)

while len(st.session_state.arrestados) < st.session_state.cantidad:
    st.session_state.arrestados.append(nuevo_arrestado())

while len(st.session_state.arrestados) > st.session_state.cantidad:
    st.session_state.arrestados.pop()

for i in range(st.session_state.cantidad):
    st.session_state.arrestados[i] = asegurar_arrestado(st.session_state.arrestados[i])
    a = st.session_state.arrestados[i]

    with st.expander(f"ARRESTADO / APREHENDIDO {i + 1}", expanded=True):
        st.subheader("📌 Identificación")
        c1, c2, c3 = st.columns(3)
        a["dni"] = c1.text_input("DNI", value=a["dni"], key=f"dni{i}")
        a["apellido"] = c2.text_input("Apellido", value=a["apellido"], key=f"ape{i}").upper()
        a["nombre"] = c3.text_input("Nombre", value=a["nombre"], key=f"nom{i}").upper()
        a["apodo"] = st.text_input("Apodo", value=a["apodo"], key=f"apo{i}").upper()

        st.subheader("👪 Filiación")
        c4, c5 = st.columns(2)
        a["papa"] = c4.text_input("Padre", value=a["papa"], key=f"pa{i}")
        a["mama"] = c5.text_input("Madre", value=a["mama"], key=f"ma{i}")

        st.subheader("🌎 Nacimiento y datos personales")
        c6, c7, c8 = st.columns(3)
        fecha = c6.date_input("Fecha nacimiento", value=fecha_desde_texto(a["fecha_nac"]), key=f"fn{i}")
        a["fecha_nac"] = str(fecha)
        a["edad"] = calcular_edad(fecha)
        c7.write("Edad")
        c7.info(str(a["edad"]))
        a["nacionalidad"] = c8.text_input("Nacionalidad", value=a["nacionalidad"], key=f"nac{i}").upper()

        c9, c10, c11 = st.columns(3)
        a["ciudad"] = c9.text_input("Ciudad", value=a["ciudad"], key=f"ciu{i}").upper()
        a["provincia"] = c10.text_input("Provincia", value=a["provincia"], key=f"prov{i}").upper()
        a["pais"] = c11.text_input("País", value=a["pais"], key=f"pais{i}").upper()

        a["domicilio"] = st.text_input("Domicilio", value=a["domicilio"], key=f"dom{i}")

        c12, c13, c14, c15 = st.columns(4)
        estados = ["SOLTERO/A", "CASADO/A", "CONCUBINO/A", "DIVORCIADO/A", "VIUDO/A"]
        a["estado_civil"] = c12.selectbox("Estado civil", estados, index=indice_opcion(estados, a["estado_civil"]), key=f"ec{i}")
        a["profesion"] = c13.text_input("Profesión", value=a["profesion"], key=f"pro{i}")
        a["lee"] = c14.radio("Lee", ["SI", "NO"], index=indice_opcion(["SI", "NO"], a["lee"]), horizontal=True, key=f"lee{i}")
        a["escribe"] = c15.radio("Escribe", ["SI", "NO"], index=indice_opcion(["SI", "NO"], a["escribe"]), horizontal=True, key=f"esc{i}")

        a["posee_dni"] = st.radio("Posee DNI físico", ["NO", "SI"], index=indice_opcion(["NO", "SI"], a["posee_dni"]), horizontal=True, key=f"pdni{i}")

        st.subheader("📡 Consulta 911")
        a["consulta_911"] = st.radio("Consulta 911", ["SI", "NO"], index=indice_opcion(["SI", "NO"], a["consulta_911"]), horizontal=True, key=f"c911{i}")
        if a["consulta_911"] == "SI":
            a["operador"] = st.text_input("Operador", value=a["operador"], key=f"op{i}")
            resultados_911 = ["NO POSEE PEDIDO DE CAPTURA", "POSEE PEDIDO DE CAPTURA"]
            a["resultado_911"] = st.selectbox("Resultado", resultados_911, index=indice_opcion(resultados_911, a["resultado_911"]), key=f"res{i}")
            if a["resultado_911"] == "POSEE PEDIDO DE CAPTURA":
                c16, c17 = st.columns(2)
                a["cuij"] = c16.text_input("CUIJ", value=a["cuij"], key=f"cuij{i}")
                a["caratula"] = c17.text_input("Carátula", value=a["caratula"], key=f"car{i}")
                c18, c19 = st.columns(2)
                a["autoridad"] = c18.text_input("Autoridad", value=a["autoridad"], key=f"aut{i}")
                a["delito"] = c19.text_input("Delito", value=a["delito"], key=f"del{i}")

        st.subheader("🩺 Lesiones y asistencia médica")
        a["lesiones"] = st.radio("¿Presenta lesiones?", ["NO", "SI"], index=indice_opcion(["NO", "SI"], a["lesiones"]), horizontal=True, key=f"les{i}")
        if a["lesiones"] == "SI":
            a["detalle_lesiones"] = st.text_area("Detalle lesiones", value=a["detalle_lesiones"], key=f"dles{i}")
            a["origen_lesiones"] = st.text_area("Origen referido de las lesiones", value=a["origen_lesiones"], key=f"oles{i}")
            atenciones = ["NO REQUIRIÓ", "AMBULANCIA", "SIES", "MOVIL POLICIAL"]
            a["atencion"] = st.selectbox("Atención médica", atenciones, index=indice_opcion(atenciones, a["atencion"]), key=f"aten{i}")
            if a["atencion"] == "MOVIL POLICIAL":
                c20, c21 = st.columns(2)
                a["movil_policial"] = c20.text_input("Móvil", value=a["movil_policial"], key=f"mov{i}")
                a["dotacion"] = c21.text_input("Dotación", value=a["dotacion"], key=f"dot{i}")
            c22, c23 = st.columns(2)
            a["hospital"] = c22.text_input("Hospital", value=a["hospital"], key=f"hos{i}")
            a["medico"] = c23.text_input("Médico", value=a["medico"], key=f"med{i}")
            a["diagnostico"] = st.text_input("Diagnóstico", value=a["diagnostico"], key=f"diag{i}")
            resultados_medicos = ["", "DADO DE ALTA", "INTERNADO", "OBSERVACION"]
            a["resultado"] = st.selectbox("Resultado", resultados_medicos, index=indice_opcion(resultados_medicos, a["resultado"]), key=f"resu{i}")
            a["certificado"] = st.radio("Certificado médico", ["SI", "NO"], index=indice_opcion(["SI", "NO"], a["certificado"], 1), horizontal=True, key=f"cert{i}")

        st.subheader("⚖️ Derechos")
        a["derechos"] = st.radio("Lectura de derechos", ["SI", "NO"], index=indice_opcion(["SI", "NO"], a["derechos"]), horizontal=True, key=f"der{i}")
        a["constancia_derechos"] = st.text_area("Constancia breve", value=a["constancia_derechos"], key=f"cder{i}")

        st.subheader("📞 Comunicación")
        a["comunicacion"] = st.radio("¿Comunicar a familiar?", ["NO", "SI"], index=indice_opcion(["NO", "SI"], a["comunicacion"]), horizontal=True, key=f"com{i}")
        if a["comunicacion"] == "SI":
            c24, c25 = st.columns(2)
            a["familiar"] = c24.text_input("Familiar", value=a["familiar"], key=f"fam{i}")
            a["telefono"] = c25.text_input("Teléfono", value=a["telefono"], key=f"tel{i}")
            a["resultado_comunicacion"] = st.text_input("Resultado comunicación", value=a["resultado_comunicacion"], key=f"rcom{i}")

        st.subheader("📦 Secuestro relacionado")
        a["secuestro"] = st.radio("Secuestro causa", ["NO", "SI"], index=indice_opcion(["NO", "SI"], a["secuestro"]), horizontal=True, key=f"sec{i}")
        if a["secuestro"] == "SI":
            a["detalle_sec"] = st.text_area("Detalle secuestro", value=a["detalle_sec"], key=f"dsec{i}")
        a["deposito"] = st.radio("Depósito", ["NO", "SI"], index=indice_opcion(["NO", "SI"], a["deposito"]), horizontal=True, key=f"dep{i}")
        if a["deposito"] == "SI":
            a["detalle_dep"] = st.text_area("Detalle depósito", value=a["detalle_dep"], key=f"ddep{i}")

# ============================================================
# CAPA 3 - ACTA DE APREHENSION / TESTIGO SIMPLE
# ============================================================
st.divider()
st.subheader("📝 Acta de aprehensión")

with st.expander("👤 Testigo de actuación / aprehensión", expanded=True):
    testigo = st.session_state.testigo_aprehension
    c1, c2 = st.columns(2)
    testigo["nombre_apellido"] = c1.text_input("Nombre y apellido", value=testigo.get("nombre_apellido", ""), key="testigo_aprehension_nombre")
    testigo["dni"] = c2.text_input("DNI", value=testigo.get("dni", ""), key="testigo_aprehension_dni")
    c3, c4 = st.columns(2)
    testigo["domicilio"] = c3.text_input("Domicilio", value=testigo.get("domicilio", ""), key="testigo_aprehension_domicilio")
    testigo["telefono"] = c4.text_input("Teléfono", value=testigo.get("telefono", ""), key="testigo_aprehension_telefono")
    testigo["firma_texto"] = st.text_input("Firma digital / aclaración", value=testigo.get("firma_texto", ""), key="testigo_aprehension_firma_texto")

    firma_archivo = st.file_uploader("Adjuntar imagen de firma digital, si corresponde", type=["png", "jpg", "jpeg"], key="testigo_aprehension_firma_img")
    if firma_archivo is not None:
        testigo["firma_imagen_base64"] = base64.b64encode(firma_archivo.read()).decode("utf-8")
        st.success("Firma digital adjuntada.")

    st.session_state.testigo_aprehension = testigo

st.session_state.observaciones_aprehension = st.text_area(
    "Observaciones del acta de aprehensión",
    value=st.session_state.observaciones_aprehension,
    key="observaciones_acta_aprehension"
)

# ============================================================
# CAPA 4 - RESUMEN PARA ACTA DE PROCEDIMIENTO
# ============================================================
st.divider()
st.subheader("🧾 Resumen para Acta de Procedimiento")
resumen = generar_resumen_acta(st.session_state.arrestados)
st.text_area("Texto que podrá tomar BLOQUE 8", value=resumen, height=140, disabled=True, key="resumen_bloque_2_vista")

# ============================================================
# CAPA 5 - EXPORTACION JSON Y PDF
# ============================================================
st.divider()
st.subheader("📤 Exportación y documentos")

data_sivap = construir_json_sivap()
json_data = json.dumps(data_sivap, indent=4, ensure_ascii=False)

c1, c2 = st.columns(2)

with c1:
    st.download_button(
        "📤 Descargar JSON para WhatsApp",
        json_data,
        file_name=nombre_archivo_json(),
        mime="application/json"
    )

with c2:
    if FPDF is None:
        st.warning("Para generar PDF falta instalar fpdf2. Agregue fpdf2 al requirements.txt.")
    else:
        pdf_bytes = generar_pdf_bloque_2(data_sivap)
        st.download_button(
            "📄 Descargar PDF BLOQUE 2",
            pdf_bytes,
            file_name="BLOQUE_2_ACTA_APREHENSION.pdf",
            mime="application/pdf"
        )

with st.expander("Modo técnico: ver JSON", expanded=False):
    st.code(json_data, language="json")

# ============================================================
# CAPA 6 - VALIDACION SIMPLE DEL BLOQUE
# ============================================================
st.divider()
if st.button("✅ Validar BLOQUE 2", key="validar_bloque_2"):
    st.session_state["bloque_2_validado"] = True
    st.session_state["bloque_2_fecha_validacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.success("BLOQUE 2 validado. Queda listo para consolidación posterior.")

if st.session_state.get("bloque_2_validado"):
    st.info(f"BLOQUE 2 validado el {st.session_state.get('bloque_2_fecha_validacion', '')}")

# ============================================================
# AUTOGUARDADO FINAL
# ============================================================
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
