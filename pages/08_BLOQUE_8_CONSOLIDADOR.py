import streamlit as st
import json
from datetime import datetime, date
from fpdf import FPDF

# =====================================================
# BLOQUE 8 - CONSTRUCTOR INTELIGENTE DE ACTAS
#
# Version mejorada:
# - Reemplaza al viejo "Consolidador Final".
# - Importa JSON de bloques.
# - Crea base comun del procedimiento.
# - Genera distintas actas desde la misma informacion.
# - Lee mejor:
#   BLOQUE 3: entrevista a victima/damnificado, noticia criminis.
#   BLOQUE 4: entrevista a testigo, no declaracion testimonial.
#   BLOQUE 6: inspeccion ocular, croquis, camaras, firma dueno camara.
#   BLOQUE 7: secuestros por lista, actas firmables y anexos.
#
# Regla madre:
# CARGO DATOS UNA VEZ.
# EL SISTEMA LOS ORDENA.
# EL SISTEMA GENERA LAS ACTAS QUE NECESITO.
#
# Regla documental:
# ACTA PRINCIPAL = RESUMEN.
# PDF DE CADA BLOQUE = ANEXO.
# =====================================================

st.set_page_config(
    page_title="S.I.V. - Bloque 8 Constructor Inteligente",
    layout="wide",
    page_icon="🧠"
)

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

BLOQUE_ID = "BLOQUE_8_CONSTRUCTOR_INTELIGENTE"
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
        "✅": "", "⚠️": "", "🚨": "", "📌": "", "🧠": ""
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


def generar_pdf_texto(titulo, cuerpo):
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "S.I.V. - Sistema Integral de Vigilancia y Procedimientos", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 8, limpiar_pdf(titulo), align="C")
    pdf.ln(5)

    pdf.set_font("Arial", "", 10)
    for parrafo in str(cuerpo).split("\n"):
        if parrafo.strip():
            pdf.multi_cell(0, 7, limpiar_pdf(parrafo), align="J")
        else:
            pdf.ln(3)

    pdf.ln(15)
    pdf.cell(90, 8, "____________________________", ln=False, align="C")
    pdf.cell(90, 8, "____________________________", ln=True, align="C")
    pdf.cell(90, 6, "Firma personal actuante", ln=False, align="C")
    pdf.cell(90, 6, "Firma autoridad / actante", ln=True, align="C")

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "Creado por Sub-Comisario Castaneda Juan - S.I.V.", align="R")

    return pdf_bytes(pdf)


def leer_json_upload(archivo):
    try:
        return json.loads(archivo.getvalue().decode("utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(archivo.getvalue().decode("latin-1"))
        except Exception:
            return None
    except Exception:
        return None


def texto_corto(texto, limite=500):
    texto = " ".join(str(texto or "").split())
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "..."


def asegurar_base():
    if "b8_importados" not in st.session_state:
        st.session_state.b8_importados = []

    if "b8_base_comun" not in st.session_state:
        st.session_state.b8_base_comun = {
            "datos_base": {},
            "victimas": [],
            "testigos_entrevista": [],
            "entrevistas_testigos_formula": "",
            "inspeccion": {},
            "secuestros": {
                "elementos": [],
                "actas": [],
                "resumen": ""
            },
            "diligencias": [],
            "campos_manual": {},
            "anexos": []
        }

    if "b8_actas_generadas" not in st.session_state:
        st.session_state.b8_actas_generadas = []

    if "b8_auditoria" not in st.session_state:
        st.session_state.b8_auditoria = []


def auditar(texto):
    st.session_state.b8_auditoria.append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "accion": texto
    })


def detectar_bloque(data):
    if not isinstance(data, dict):
        return "DESCONOCIDO"

    modulo = str(data.get("modulo", "")).upper()
    bloque = str(data.get("bloque", "")).upper()

    if data.get("bloque") == 3 or "BLOQUE_3" in modulo or "ENTREVISTA_VICTIMA" in modulo:
        return "BLOQUE_3_VICTIMA"

    if data.get("bloque") == 4 or "BLOQUE_4" in modulo or "TESTIGO" in modulo:
        return "BLOQUE_4_TESTIGO"

    if data.get("bloque") == 6 or "BLOQUE_6" in modulo or "INSPECCION" in modulo or "CROQUIS" in modulo:
        return "BLOQUE_6_INSPECCION"

    if data.get("bloque") == 7 or "BLOQUE_7" in modulo or "SECUESTROS" in modulo:
        return "BLOQUE_7_SECUESTROS"

    if data.get("bloque") == 1 or "BLOQUE_1" in modulo:
        return "BLOQUE_1_CORAZON"

    if data.get("bloque") == 2 or "BLOQUE_2" in modulo or "ARRESTADO" in modulo:
        return "BLOQUE_2_ARRESTADO"

    if data.get("bloque") == 5 or "BLOQUE_5" in modulo or "CONSULTA" in modulo:
        return "BLOQUE_5_CONSULTA"

    return "DESCONOCIDO"


def importar_a_base(data, nombre_archivo="archivo.json"):
    base = st.session_state.b8_base_comun
    tipo = detectar_bloque(data)

    registro = {
        "archivo": nombre_archivo,
        "tipo_detectado": tipo,
        "fecha_importacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "json": data
    }
    st.session_state.b8_importados.append(registro)

    # BLOQUE 1 - Datos base / corazon
    if tipo == "BLOQUE_1_CORAZON":
        base["datos_base"]["bloque_1"] = data
        for k in ["nro_acta", "incidencia", "dependencia", "movil", "l_hecho", "l_apre", "relato"]:
            if isinstance(data, dict) and k in data:
                base["datos_base"][k] = data.get(k)
        auditar(f"Importado BLOQUE 1 desde {nombre_archivo}")

    # BLOQUE 2 - Arrestado
    elif tipo == "BLOQUE_2_ARRESTADO":
        base["diligencias"].append({
            "tipo": "ARRESTADO/APREHENDIDO",
            "resumen": texto_corto(json.dumps(data, ensure_ascii=False), 700),
            "origen": "BLOQUE 2"
        })
        auditar(f"Importado BLOQUE 2 desde {nombre_archivo}")

    # BLOQUE 3 - Victima / damnificado
    elif tipo == "BLOQUE_3_VICTIMA":
        filiacion = data.get("filiacion", {}) if isinstance(data, dict) else {}
        victima = {
            "nombre": filiacion.get("nombre") or data.get("nombre") or "Víctima/Damnificado",
            "dni": filiacion.get("dni") or data.get("dni", ""),
            "domicilio": filiacion.get("domicilio") or data.get("domicilio", ""),
            "celular": filiacion.get("celular") or data.get("celular", ""),
            "correo": filiacion.get("correo") or data.get("correo", ""),
            "relato": data.get("relato_primera_persona") or data.get("contenido") or data.get("relato") or "",
            "noticia_criminis": data.get("noticia_criminis") or data.get("resumen_para_acta_procedimiento") or "",
            "fundamento_aprehension": data.get("fundamento_aprehension") or "",
            "instancia_penal": data.get("instancia_penal", ""),
            "analisis_siv": data.get("analisis_siv", {})
        }
        base["victimas"].append(victima)
        base["anexos"].append("Acta de entrevista a víctima/damnificado - BLOQUE 3")
        auditar(f"Importado BLOQUE 3 desde {nombre_archivo}")

    # BLOQUE 4 - Testigo
    elif tipo == "BLOQUE_4_TESTIGO":
        # Santa Fe: no usar declaracion testimonial. Usar acta de entrevista.
        filiacion = data.get("filiacion", {}) if isinstance(data, dict) else {}
        testigo = {
            "nombre": filiacion.get("nombre") or data.get("nombre") or "Testigo",
            "dni": filiacion.get("dni") or data.get("dni", ""),
            "domicilio": filiacion.get("domicilio") or data.get("domicilio", ""),
            "celular": filiacion.get("celular") or data.get("telefono") or "",
            "relato": data.get("contenido") or data.get("relato") or data.get("entrevista") or ""
        }
        base["testigos_entrevista"].append(testigo)
        base["entrevistas_testigos_formula"] = (
            "Se deja constancia que se individualizaron testigos presenciales del hecho, "
            "a quienes se les recibió entrevista policial, labrándose las correspondientes "
            "actas de entrevista, las cuales se agregan como anexo."
        )
        base["anexos"].append("Acta de entrevista a testigo - BLOQUE 4")
        auditar(f"Importado BLOQUE 4 como Acta de Entrevista desde {nombre_archivo}")

    # BLOQUE 6 - Inspeccion/croquis/camaras
    elif tipo == "BLOQUE_6_INSPECCION":
        base["inspeccion"] = {
            "datos": data.get("datos", {}),
            "puntos_croquis": data.get("puntos_croquis", []),
            "camaras": data.get("camaras", []),
            "resumen_camaras": data.get("resumen_camaras", []),
            "resumen_para_acta": data.get("resumen_para_acta_procedimiento", ""),
            "cantidad_fotos": data.get("cantidad_fotos", "")
        }
        base["anexos"].append("Acta de inspección ocular, croquis y relevamiento de cámaras - BLOQUE 6")
        auditar(f"Importado BLOQUE 6 integral desde {nombre_archivo}")

    # BLOQUE 7 - Secuestros
    elif tipo == "BLOQUE_7_SECUESTROS":
        elementos = data.get("elementos", [])
        actas = data.get("actas_secuestro", [])
        resumen = data.get("resumen_para_acta_procedimiento", "")

        base["secuestros"]["elementos"].extend(elementos if isinstance(elementos, list) else [])
        base["secuestros"]["actas"].extend(actas if isinstance(actas, list) else [])
        if resumen:
            if base["secuestros"]["resumen"]:
                base["secuestros"]["resumen"] += "\n" + resumen
            else:
                base["secuestros"]["resumen"] = resumen

        base["anexos"].append("Acta/s de secuestro y listado de elementos - BLOQUE 7")
        auditar(f"Importado BLOQUE 7 con {len(elementos) if isinstance(elementos, list) else 0} elemento/s desde {nombre_archivo}")

    # Otros
    else:
        base["diligencias"].append({
            "tipo": "DATO_IMPORTADO",
            "resumen": texto_corto(json.dumps(data, ensure_ascii=False), 700),
            "origen": nombre_archivo
        })
        auditar(f"Importado JSON no clasificado desde {nombre_archivo}")


def datos_manual_actual():
    return {
        "nro_acta": st.session_state.get("b8_nro_acta", ""),
        "incidencia": st.session_state.get("b8_incidencia", ""),
        "dependencia": st.session_state.get("b8_dependencia", ""),
        "movil": st.session_state.get("b8_movil", ""),
        "fecha": str(st.session_state.get("b8_fecha", date.today())),
        "hora": str(st.session_state.get("b8_hora", "")),
        "lugar_hecho": st.session_state.get("b8_lugar_hecho", ""),
        "lugar_aprehension": st.session_state.get("b8_lugar_aprehension", ""),
        "personal_actuante": st.session_state.get("b8_personal_actuante", ""),
        "actante": st.session_state.get("b8_actante", ""),
        "fiscalia": st.session_state.get("b8_fiscalia", ""),
        "observaciones": st.session_state.get("b8_observaciones", "")
    }


def fusionar_datos_base():
    base = st.session_state.b8_base_comun
    manual = datos_manual_actual()
    for k, v in manual.items():
        if v not in ("", None):
            base["datos_base"][k] = v


def obtener(k, default=""):
    base = st.session_state.b8_base_comun
    return base.get("datos_base", {}).get(k, default)


def resumen_victimas():
    victimas = st.session_state.b8_base_comun.get("victimas", [])
    if not victimas:
        return "No se importaron entrevistas de víctima/damnificado."
    partes = []
    for idx, v in enumerate(victimas, start=1):
        partes.append(
            f"{idx}) {v.get('nombre','Víctima/Damnificado')}: "
            f"{texto_corto(v.get('noticia_criminis') or v.get('relato'), 600)}"
        )
    return "\n".join(partes)


def resumen_testigos():
    formula = st.session_state.b8_base_comun.get("entrevistas_testigos_formula", "")
    cantidad = len(st.session_state.b8_base_comun.get("testigos_entrevista", []))
    if cantidad:
        return formula + f" Cantidad de actas de entrevista a testigo importadas: {cantidad}."
    return "No se importaron actas de entrevista a testigo."


def resumen_inspeccion():
    insp = st.session_state.b8_base_comun.get("inspeccion", {})
    if not insp:
        return "No se importó BLOQUE 6."
    resumen = insp.get("resumen_para_acta", "")
    camaras = insp.get("camaras", [])
    puntos = insp.get("puntos_croquis", [])
    extra = f" Se relevaron {len(camaras)} cámara/s y {len(puntos)} punto/s relevantes para croquis."
    return (resumen or "Se realizó inspección ocular, croquis y relevamiento de cámaras conforme acta anexa.") + extra


def resumen_secuestros():
    sec = st.session_state.b8_base_comun.get("secuestros", {})
    elementos = sec.get("elementos", [])
    actas = sec.get("actas", [])
    resumen = sec.get("resumen", "")

    if not elementos and not resumen:
        return "No se importaron secuestros."

    partes = []
    if resumen:
        partes.append(resumen)

    if elementos:
        partes.append("Elementos secuestrados registrados:")
        for idx, e in enumerate(elementos, start=1):
            tipo = e.get("tipo_elemento", "Elemento")
            desc = e.get("descripcion", "")
            destino = e.get("destino", "")
            if tipo == "Automóvil":
                desc = f"{e.get('auto_marca_modelo','')} dominio {e.get('auto_dominio','')}"
            elif tipo == "Motocicleta":
                desc = f"{e.get('moto_tipo_marca','')} dominio {e.get('moto_dominio','')}"
            elif tipo == "Celular":
                desc = f"Celular {e.get('celular_marca','')} {e.get('celular_modelo','')} - {e.get('propietario','')}"
            elif tipo == "Arma de fuego":
                desc = f"Arma de fuego {e.get('arma_tipo','')} calibre {e.get('arma_calibre','')}"

            partes.append(f"{idx}) {tipo}: {desc}. Destino: {destino or 'S/D'}.")

    if actas:
        partes.append("Actas de secuestro generadas:")
        for a in actas:
            partes.append(
                f"- Acta {a.get('id_acta','S/D')}: testigo {a.get('testigo_nombre','S/D')}, "
                f"elementos {len(a.get('elementos_ids', []))}, lugar {a.get('lugar_acta','S/D')}."
            )

    return "\n".join(partes)


def anexos_texto():
    anexos = st.session_state.b8_base_comun.get("anexos", [])
    if not anexos:
        return "Sin anexos importados."
    vistos = []
    for a in anexos:
        if a not in vistos:
            vistos.append(a)
    return "\n".join([f"- {a}" for a in vistos])


def construir_acta(tipo_acta, campos_extra):
    fusionar_datos_base()

    encabezado = (
        f"En fecha {obtener('fecha', date.today())}, siendo las {obtener('hora','S/D')} horas, "
        f"personal de {obtener('dependencia','S/D')}, móvil {obtener('movil','S/D')}, "
        f"interviene en relación a hecho ocurrido en {obtener('lugar_hecho','S/D')}."
    )

    if tipo_acta == "Acta de Procedimiento":
        cuerpo = f"""{encabezado}

NOTICIA CRIMINIS / ENTREVISTA A VÍCTIMA-DAMNIFICADO:
{resumen_victimas()}

TESTIGOS:
{resumen_testigos()}

INSPECCIÓN OCULAR / CROQUIS / CÁMARAS:
{resumen_inspeccion()}

SECUESTROS:
{resumen_secuestros()}

CONSULTA / OBSERVACIONES:
{campos_extra.get('consulta_observaciones','')}

ANEXOS:
{anexos_texto()}

CIERRE:
Se deja constancia que el acta principal contiene un resumen ordenado de la intervención, quedando las actas completas generadas por cada bloque como anexos independientes.
"""
        return "ACTA DE PROCEDIMIENTO", cuerpo

    if tipo_acta == "Resumen para Fiscalía":
        cuerpo = f"""RESUMEN OPERATIVO PARA FISCALÍA

DATOS BASE:
Dependencia: {obtener('dependencia','S/D')}
Incidencia: {obtener('incidencia','S/D')}
Lugar del hecho: {obtener('lugar_hecho','S/D')}
Personal actuante: {obtener('personal_actuante','S/D')}

NOTICIA CRIMINIS:
{resumen_victimas()}

FUNDAMENTO DE INTERVENCIÓN / APREHENSIÓN:
{campos_extra.get('fundamento_aprehension','')}

INSPECCIÓN Y CÁMARAS:
{resumen_inspeccion()}

SECUESTROS:
{resumen_secuestros()}

ANEXOS:
{anexos_texto()}
"""
        return "RESUMEN OPERATIVO PARA FISCALÍA", cuerpo

    if tipo_acta == "Acta de Secuestros - Resumen":
        cuerpo = f"""ACTA / RESUMEN DE SECUESTROS

{encabezado}

ELEMENTOS Y ACTAS IMPORTADAS DESDE BLOQUE 7:
{resumen_secuestros()}

OBSERVACIONES:
{campos_extra.get('observaciones_secuestro','')}

ANEXOS:
Se agregan las actas de secuestro específicas generadas en BLOQUE 7, firmadas por el testigo correspondiente cuando corresponda.
"""
        return "ACTA / RESUMEN DE SECUESTROS", cuerpo

    if tipo_acta == "Acta de Inspección - Resumen":
        cuerpo = f"""ACTA / RESUMEN DE INSPECCIÓN OCULAR

{encabezado}

INSPECCIÓN OCULAR, CROQUIS Y CÁMARAS:
{resumen_inspeccion()}

OBSERVACIONES:
{campos_extra.get('observaciones_inspeccion','')}

ANEXOS:
Se agrega el PDF integral de inspección ocular, croquis demostrativo, fotos y relevamiento de cámaras generado por BLOQUE 6.
"""
        return "ACTA / RESUMEN DE INSPECCIÓN OCULAR", cuerpo

    if tipo_acta == "Plantilla personalizada":
        plantilla = campos_extra.get("plantilla_texto", "")
        reemplazos = {
            "{fecha}": obtener("fecha", ""),
            "{hora}": obtener("hora", ""),
            "{dependencia}": obtener("dependencia", ""),
            "{movil}": obtener("movil", ""),
            "{lugar_hecho}": obtener("lugar_hecho", ""),
            "{personal_actuante}": obtener("personal_actuante", ""),
            "{victima_resumen}": resumen_victimas(),
            "{testigos_resumen}": resumen_testigos(),
            "{inspeccion_resumen}": resumen_inspeccion(),
            "{secuestros_resumen}": resumen_secuestros(),
            "{anexos}": anexos_texto(),
        }
        cuerpo = plantilla
        for k, v in reemplazos.items():
            cuerpo = cuerpo.replace(k, str(v))
        return "ACTA DESDE PLANTILLA PERSONALIZADA", cuerpo

    return "ACTA", "Sin contenido."


# =====================================================
# INICIO
# =====================================================

asegurar_base()

st.title("🧠 BLOQUE 8 — CONSTRUCTOR INTELIGENTE DE ACTAS")
st.subheader("Carga una vez, ordena la información y genera las actas necesarias")

st.info("""
Este bloque NO reemplaza a los bloques 1 a 7. Los lee, ordena la información y genera documentos.
Acta principal = resumen. PDFs propios de cada bloque = anexos.
""")

tabs = st.tabs([
    "1. Datos Base",
    "2. Importar JSON",
    "3. Base Común",
    "4. Constructor de Actas",
    "5. Tomar Foto/PDF como Plantilla",
    "6. Actas Generadas",
    "7. Auditoría"
])

# =====================================================
# 1. DATOS BASE
# =====================================================
with tabs[0]:
    st.subheader("Datos base del procedimiento")

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Nro. de acta", key="b8_nro_acta")
        st.text_input("Incidencia / carta 911", key="b8_incidencia")
        st.text_input("Dependencia", key="b8_dependencia")
        st.text_input("Móvil", key="b8_movil")
        st.date_input("Fecha", value=date.today(), key="b8_fecha")
        st.text_input("Hora", key="b8_hora")
    with c2:
        st.text_area("Lugar del hecho", key="b8_lugar_hecho")
        st.text_area("Lugar de aprehensión", key="b8_lugar_aprehension")
        st.text_area("Personal actuante", key="b8_personal_actuante")
        st.text_input("Actante / funcionario que redacta", key="b8_actante")
        st.text_input("Fiscalía / autoridad", key="b8_fiscalia")
        st.text_area("Observaciones generales", key="b8_observaciones")

    if st.button("💾 Incorporar datos base a la base común", use_container_width=True):
        fusionar_datos_base()
        auditar("Datos base incorporados manualmente a la base común.")
        autoguardar_bloque(BLOQUE_ID)
        st.success("Datos base incorporados.")

# =====================================================
# 2. IMPORTAR JSON
# =====================================================
with tabs[1]:
    st.subheader("Importar JSON generados por los bloques")

    archivos = st.file_uploader(
        "Subir JSON de Bloques 1 a 7",
        type=["json"],
        accept_multiple_files=True,
        key="file_uploader_b8_jsons"
    )

    if archivos:
        if st.button("📥 Importar JSON seleccionados", use_container_width=True):
            cantidad = 0
            for archivo in archivos:
                data = leer_json_upload(archivo)
                if data is None:
                    st.error(f"No se pudo leer: {archivo.name}")
                    continue
                importar_a_base(data, archivo.name)
                cantidad += 1

            autoguardar_bloque(BLOQUE_ID)
            st.success(f"Se importaron {cantidad} archivo/s JSON.")

    st.markdown("### JSON importados")
    if st.session_state.b8_importados:
        for idx, reg in enumerate(st.session_state.b8_importados, start=1):
            with st.expander(f"{idx}. {reg.get('archivo')} — {reg.get('tipo_detectado')}"):
                st.json({
                    "archivo": reg.get("archivo"),
                    "tipo_detectado": reg.get("tipo_detectado"),
                    "fecha_importacion": reg.get("fecha_importacion")
                })
    else:
        st.info("Aún no hay JSON importados.")

# =====================================================
# 3. BASE COMUN
# =====================================================
with tabs[2]:
    st.subheader("Base común del procedimiento")

    st.markdown("### Víctimas / damnificados")
    st.json(st.session_state.b8_base_comun.get("victimas", []))

    st.markdown("### Testigos con acta de entrevista")
    st.write(resumen_testigos())
    with st.expander("Ver testigos importados"):
        st.json(st.session_state.b8_base_comun.get("testigos_entrevista", []))

    st.markdown("### Inspección ocular / croquis / cámaras")
    st.write(resumen_inspeccion())

    st.markdown("### Secuestros")
    st.write(resumen_secuestros())

    st.markdown("### Anexos")
    st.text(anexos_texto())

    st.markdown("### Datos manuales que se agregan a la base común")
    c1, c2 = st.columns(2)
    with c1:
        clave_manual = st.text_input("Nombre del dato", key="b8_clave_manual", placeholder="Ej: persona_que_recibe")
    with c2:
        valor_manual = st.text_input("Valor", key="b8_valor_manual", placeholder="Ej: Juan Pérez DNI...")
    if st.button("➕ Agregar dato manual reutilizable", use_container_width=True):
        if clave_manual and valor_manual:
            st.session_state.b8_base_comun["campos_manual"][clave_manual] = valor_manual
            auditar(f"Dato manual agregado a base común: {clave_manual}")
            autoguardar_bloque(BLOQUE_ID)
            st.success("Dato agregado.")
        else:
            st.error("Debe completar nombre y valor.")

    with st.expander("Ver base común completa"):
        st.json(st.session_state.b8_base_comun)

# =====================================================
# 4. CONSTRUCTOR
# =====================================================
with tabs[3]:
    st.subheader("Constructor de actas")

    tipo_acta = st.selectbox(
        "Acta a generar",
        [
            "Acta de Procedimiento",
            "Resumen para Fiscalía",
            "Acta de Secuestros - Resumen",
            "Acta de Inspección - Resumen",
            "Plantilla personalizada"
        ],
        key="b8_tipo_acta"
    )

    campos_extra = {}

    if tipo_acta == "Acta de Procedimiento":
        campos_extra["consulta_observaciones"] = st.text_area("Consulta / observaciones para incorporar", key="b8_consulta_obs")

    elif tipo_acta == "Resumen para Fiscalía":
        campos_extra["fundamento_aprehension"] = st.text_area(
            "Fundamento de intervención/aprehensión",
            value="\n".join([v.get("fundamento_aprehension","") for v in st.session_state.b8_base_comun.get("victimas", []) if v.get("fundamento_aprehension")]),
            key="b8_fundamento_fiscalia"
        )

    elif tipo_acta == "Acta de Secuestros - Resumen":
        campos_extra["observaciones_secuestro"] = st.text_area("Observaciones de secuestros", key="b8_obs_secuestro")

    elif tipo_acta == "Acta de Inspección - Resumen":
        campos_extra["observaciones_inspeccion"] = st.text_area("Observaciones de inspección", key="b8_obs_inspeccion")

    elif tipo_acta == "Plantilla personalizada":
        st.info("Pegue una plantilla y use campos como {fecha}, {hora}, {dependencia}, {victima_resumen}, {secuestros_resumen}, {inspeccion_resumen}, {anexos}.")
        campos_extra["plantilla_texto"] = st.text_area("Plantilla editable", height=330, key="b8_plantilla_texto")

    titulo, cuerpo = construir_acta(tipo_acta, campos_extra)

    st.markdown("### Vista previa editable")
    cuerpo_editable = st.text_area("Contenido del acta", value=cuerpo, height=520, key="b8_cuerpo_acta_editable")

    if st.button("📄 Generar acta y guardar en historial", use_container_width=True):
        acta = {
            "titulo": titulo,
            "tipo": tipo_acta,
            "contenido": cuerpo_editable,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        st.session_state.b8_actas_generadas.append(acta)
        auditar(f"Acta generada: {tipo_acta}")
        autoguardar_bloque(BLOQUE_ID)
        st.success("Acta guardada en historial.")

    pdf = generar_pdf_texto(titulo, cuerpo_editable)
    st.download_button(
        "📥 Descargar PDF del acta actual",
        data=pdf,
        file_name="BLOQUE_8_Acta_Generada.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# =====================================================
# 5. PLANTILLA FOTO/PDF
# =====================================================
with tabs[4]:
    st.subheader("Tomar Foto/PDF como Plantilla")

    st.warning("""
Fase práctica inicial: se permite subir foto/PDF del formulario real y transcribir/pegar su texto base.
La lectura OCR automática completa queda como capa posterior. El sistema ya permite convertirla en plantilla editable con {campos}.
""")

    plantilla_archivo = st.file_uploader(
        "Subir foto, imagen escaneada o PDF del acta/formulario",
        type=["jpg", "jpeg", "png", "pdf"],
        key="file_uploader_b8_plantilla"
    )

    if plantilla_archivo:
        st.success(f"Archivo recibido: {plantilla_archivo.name}")
        if plantilla_archivo.type.startswith("image"):
            st.image(plantilla_archivo.getvalue(), caption="Vista previa del formulario", use_container_width=True)
        else:
            st.info("PDF cargado. En esta fase, transcriba o pegue el texto base abajo.")

    st.markdown("### Crear plantilla editable")
    nombre_plantilla = st.text_input("Nombre de la nueva acta", key="b8_nombre_plantilla")
    texto_base_plantilla = st.text_area(
        "Texto base de la plantilla",
        height=360,
        placeholder="Pegue aquí el texto de la plantilla y reemplace partes por {campo}.",
        key="b8_texto_base_plantilla"
    )

    if st.button("💾 Guardar como plantilla personalizada", use_container_width=True):
        if nombre_plantilla and texto_base_plantilla:
            st.session_state.b8_base_comun.setdefault("plantillas_personalizadas", [])
            st.session_state.b8_base_comun["plantillas_personalizadas"].append({
                "nombre": nombre_plantilla,
                "texto": texto_base_plantilla,
                "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            auditar(f"Plantilla personalizada creada: {nombre_plantilla}")
            autoguardar_bloque(BLOQUE_ID)
            st.success("Plantilla guardada. Puede usarla desde Constructor de Actas copiando su texto.")
        else:
            st.error("Debe completar nombre y texto base.")

    with st.expander("Plantillas guardadas"):
        st.json(st.session_state.b8_base_comun.get("plantillas_personalizadas", []))

# =====================================================
# 6. ACTAS GENERADAS
# =====================================================
with tabs[5]:
    st.subheader("Actas generadas")

    if st.session_state.b8_actas_generadas:
        for idx, acta in enumerate(st.session_state.b8_actas_generadas, start=1):
            with st.expander(f"{idx}. {acta.get('tipo')} — {acta.get('fecha')}"):
                st.text_area("Contenido", acta.get("contenido", ""), height=260, key=f"b8_acta_hist_{idx}")
                pdf_hist = generar_pdf_texto(acta.get("titulo", "ACTA"), acta.get("contenido", ""))
                st.download_button(
                    "Descargar PDF",
                    data=pdf_hist,
                    file_name=f"Acta_Bloque8_{idx}.pdf",
                    mime="application/pdf",
                    key=f"download_b8_hist_{idx}",
                    use_container_width=True
                )
    else:
        st.info("Todavía no hay actas generadas.")

    json_consolidado = json.dumps({
        "bloque": 8,
        "modulo": "BLOQUE_8_CONSTRUCTOR_INTELIGENTE",
        "base_comun": st.session_state.b8_base_comun,
        "actas_generadas": st.session_state.b8_actas_generadas,
        "auditoria": st.session_state.b8_auditoria
    }, ensure_ascii=False, indent=4)

    st.download_button(
        "📦 Descargar JSON consolidado BLOQUE 8",
        data=json_consolidado,
        file_name="bloque_8_consolidado.json",
        mime="application/json",
        use_container_width=True
    )

# =====================================================
# 7. AUDITORIA
# =====================================================
with tabs[6]:
    st.subheader("Auditoría interna")

    if st.session_state.b8_auditoria:
        for item in reversed(st.session_state.b8_auditoria):
            st.write(f"**{item.get('fecha')}** — {item.get('accion')}")
    else:
        st.info("Sin movimientos registrados.")

    if st.button("🧹 Limpiar historial de BLOQUE 8", use_container_width=True):
        st.session_state.b8_importados = []
        st.session_state.b8_actas_generadas = []
        st.session_state.b8_auditoria = []
        st.session_state.b8_base_comun = {
            "datos_base": {},
            "victimas": [],
            "testigos_entrevista": [],
            "entrevistas_testigos_formula": "",
            "inspeccion": {},
            "secuestros": {
                "elementos": [],
                "actas": [],
                "resumen": ""
            },
            "diligencias": [],
            "campos_manual": {},
            "anexos": []
        }
        autoguardar_bloque(BLOQUE_ID)
        st.success("Historial de BLOQUE 8 limpiado.")
        st.rerun()

try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
