import streamlit as st
import json
import re
from datetime import datetime, date
from fpdf import FPDF

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_OK = True
except Exception:
    GUARDADO_OK = False

BLOQUE_ID = "BLOQUE_8_CONSOLIDADOR_ACTA_PROCEDIMIENTO"

st.set_page_config(
    page_title="S.I.V.A.P. - Bloque 8 Consolidador",
    page_icon="🚓",
    layout="wide"
)

if GUARDADO_OK:
    try:
        iniciar_guardado_seguro(BLOQUE_ID)
        panel_guardado_seguro(BLOQUE_ID)
    except Exception:
        pass

SISTEMA = "S.I.V.A.P. — Sistema Integrado de Validación de Actuaciones Policiales"
LEMA = "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora."

# ============================================================
# ESTADO
# ============================================================

def init_state():
    defaults = {
        "b8_numero_acta": "",
        "b8_fecha": date.today(),
        "b8_hora": datetime.now().strftime("%H:%M"),
        "b8_dependencia": "",
        "b8_reparticion": "",
        "b8_movil": "",
        "b8_personal_actante": "",
        "b8_lugar_hecho": "",
        "b8_lugar_aprehension": "",
        "b8_incidencia": "",
        "b8_intervencion_fiscal": "",
        "b8_hora_cierre": "",
        "b8_acta_texto_editable": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "b8_jsons" not in st.session_state:
        st.session_state.b8_jsons = []
    if "b8_consolidado" not in st.session_state:
        st.session_state.b8_consolidado = crear_consolidado_vacio()


def crear_consolidado_vacio():
    return {
        "json_cargados": [],
        "bloques_recibidos": [],
        "victimas": [],
        "arrestados": [],
        "testigos": [],
        "elementos": [],
        "inspecciones": [],
        "camaras": [],
        "noticias_criminis": [],
        "relatos_base": [],
        "observaciones": [],
    }

init_state()

# ============================================================
# UTILIDADES
# ============================================================

def limpiar_pdf(texto):
    if texto is None:
        return ""
    texto = str(texto)
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-", "•": "-",
        "🚓": "", "📥": "", "📦": "", "✅": "", "⚠️": ""
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return texto.encode("latin-1", "replace").decode("latin-1")


def texto_json(data):
    try:
        return json.dumps(data, ensure_ascii=False).lower()
    except Exception:
        return str(data).lower()


def buscar_recursivo(data, claves):
    resultados = []
    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if any(c in kl for c in claves) and not isinstance(v, (dict, list)):
                if str(v).strip():
                    resultados.append(str(v).strip())
            elif isinstance(v, (dict, list)):
                resultados.extend(buscar_recursivo(v, claves))
    elif isinstance(data, list):
        for item in data:
            resultados.extend(buscar_recursivo(item, claves))
    return resultados


def obtener_path(data, path, default=None):
    ref = data
    for p in path:
        if isinstance(ref, dict) and p in ref:
            ref = ref[p]
        else:
            return default
    return ref


def normalizar_nombre_archivo(txt):
    txt = str(txt or "SIVAP").upper()
    txt = re.sub(r"[^A-Z0-9]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt or "SIVAP"


def etiqueta_persona(p):
    if not isinstance(p, dict):
        return str(p)
    partes = []
    ape = p.get("apellido") or p.get("apellidos") or ""
    nom = p.get("nombre") or p.get("nombres") or p.get("nombre_apellido") or p.get("nombre_completo") or ""
    nombre = f"{ape}, {nom}".strip(", ").strip()
    if nombre:
        partes.append(nombre)
    dni = p.get("dni") or p.get("documento") or ""
    if dni:
        partes.append(f"DNI {dni}")
    dom = p.get("domicilio") or ""
    if dom:
        partes.append(f"domicilio {dom}")
    return " - ".join(partes) if partes else str(p)

# ============================================================
# DETECCION DE BLOQUES
# ============================================================

def detectar_bloque(data):
    """
    Detecta primero por estructura y campos declarados.
    No clasifica BLOQUE 3 como BLOQUE 2 solo porque el relato diga 'aprehendido'.
    """
    if not isinstance(data, (dict, list)):
        return "JSON EXTERNO"

    t = texto_json(data)

    # 1) Campos estructurales explícitos
    declarados = []
    if isinstance(data, dict):
        for k in ["bloque", "modulo", "módulo", "tipo_archivo", "version", "versión"]:
            if k in data:
                declarados.append(str(data.get(k, "")).lower())
        db = data.get("datos_bloque")
        if isinstance(db, dict):
            for k in ["bloque", "modulo", "módulo"]:
                if k in db:
                    declarados.append(str(db.get(k, "")).lower())

    declarados_txt = " ".join(declarados)

    if "bloque_3" in declarados_txt or "bloque 3" in declarados_txt:
        return "BLOQUE 3 — Víctima/Damnificado"
    if "bloque_2" in declarados_txt or "bloque 2" in declarados_txt:
        return "BLOQUE 2 — Arrestado/Aprehendido"
    if "bloque_4" in declarados_txt or "bloque 4" in declarados_txt:
        return "BLOQUE 4 — Testigo"
    if "bloque_6" in declarados_txt or "bloque 6" in declarados_txt:
        return "BLOQUE 6 — Inspección ocular"
    if "bloque_7" in declarados_txt or "bloque 7" in declarados_txt:
        return "BLOQUE 7 — Secuestros"
    if "bloque_1" in declarados_txt or "bloque 1" in declarados_txt:
        return "BLOQUE 1 — Datos base"

    # 2) Estructuras propias de cada bloque
    if isinstance(data, dict):
        if "datos_bloque" in data and isinstance(data["datos_bloque"], dict):
            db = data["datos_bloque"]
            if any(k in db for k in ["identificacion_victima", "noticia_criminis", "relato_final", "derechos_victima"]):
                return "BLOQUE 3 — Víctima/Damnificado"
            if any(k in db for k in ["arrestados", "arrestado", "aprehendidos"]):
                return "BLOQUE 2 — Arrestado/Aprehendido"

        if isinstance(data.get("arrestados"), list):
            return "BLOQUE 2 — Arrestado/Aprehendido"
        if any(k in data for k in ["identificacion_victima", "victima", "víctima", "noticia_criminis", "relato_final", "derechos_victima"]):
            return "BLOQUE 3 — Víctima/Damnificado"
        if any(k in data for k in ["testigos", "testigo"]):
            return "BLOQUE 4 — Testigo"
        if any(k in data for k in ["secuestros", "elementos_secuestrados", "elementos"]):
            return "BLOQUE 7 — Secuestros"
        if any(k in data for k in ["inspeccion", "inspección", "camaras", "cámaras", "relato_inspeccion"]):
            return "BLOQUE 6 — Inspección ocular"

    # 3) Fallback por texto, con prioridad víctima antes de arrestado
    if "identificacion_victima" in t or "noticia_criminis" in t or "derechos_victima" in t:
        return "BLOQUE 3 — Víctima/Damnificado"
    if "victima" in t or "víctima" in t or "damnificado" in t:
        return "BLOQUE 3 — Víctima/Damnificado"
    if "arrestados" in t or "bloque_2_arrestado" in t:
        return "BLOQUE 2 — Arrestado/Aprehendido"
    if "testigo" in t:
        return "BLOQUE 4 — Testigo"
    if "secuestro" in t:
        return "BLOQUE 7 — Secuestros"
    if "inspeccion" in t or "inspección" in t or "camara" in t or "cámara" in t:
        return "BLOQUE 6 — Inspección ocular"

    return "JSON EXTERNO"

# ============================================================
# EXTRACCION
# ============================================================

def extraer_de_json(data, bloque_confirmado, nombre_archivo=""):
    aporte = {
        "archivo": nombre_archivo,
        "bloque": bloque_confirmado,
        "victimas": [],
        "arrestados": [],
        "testigos": [],
        "elementos": [],
        "inspecciones": [],
        "camaras": [],
        "noticias_criminis": [],
        "relatos_base": [],
        "observaciones": [],
        "raw": data,
    }

    b = bloque_confirmado.lower()
    db = data.get("datos_bloque", data) if isinstance(data, dict) else data

    # Autor / actuacion si vinieren en JSON
    if isinstance(data, dict):
        autor = data.get("autor_carga") or data.get("autor") or {}
        act = data.get("actuacion") or {}
        if autor:
            aporte["observaciones"].append(f"Autor carga: {autor}")
        if act:
            aporte["observaciones"].append(f"Actuación declarada en JSON: {act}")

    # BLOQUE 2
    if "bloque 2" in b or "arrestado" in b or "aprehendido" in b:
        arrestados = []
        if isinstance(db, dict):
            arrestados = db.get("arrestados") or db.get("aprehendidos") or []
            if not arrestados and isinstance(db.get("arrestado"), dict):
                arrestados = [db.get("arrestado")]
        if isinstance(arrestados, list):
            aporte["arrestados"].extend(arrestados)
        return aporte

    # BLOQUE 3
    if "bloque 3" in b or "víctima" in b or "victima" in b or "damnificado" in b:
        vict = None
        if isinstance(db, dict):
            vict = db.get("identificacion_victima") or db.get("victima") or db.get("víctima")
            if isinstance(vict, dict):
                aporte["victimas"].append(vict)

            noticia = db.get("noticia_criminis") or db.get("super_resumen") or db.get("resumen")
            relato_final = db.get("relato_final")
            relato_crudo = db.get("relato_crudo")
            if noticia:
                aporte["noticias_criminis"].append(str(noticia))
            if relato_final:
                aporte["relatos_base"].append(str(relato_final))
            elif relato_crudo:
                aporte["relatos_base"].append(str(relato_crudo))
        return aporte

    # BLOQUE 4
    if "bloque 4" in b or "testigo" in b:
        testigos = []
        if isinstance(db, dict):
            testigos = db.get("testigos") or []
            if not testigos and isinstance(db.get("testigo"), dict):
                testigos = [db.get("testigo")]
        if isinstance(testigos, list):
            aporte["testigos"].extend(testigos)
        return aporte

    # BLOQUE 6
    if "bloque 6" in b or "inspección" in b or "inspeccion" in b:
        if isinstance(db, dict):
            datos = db.get("datos") if isinstance(db.get("datos"), dict) else db
            resumen = (
                datos.get("resumen_para_acta_procedimiento") or
                db.get("resumen_para_acta_procedimiento") or
                datos.get("relato_inspeccion") or
                datos.get("relato") or
                db.get("relato_inspeccion") or
                db.get("inspeccion") or
                ""
            )
            if resumen:
                aporte["inspecciones"].append(str(resumen))
            cams = db.get("camaras") or datos.get("camaras") or db.get("resumen_camaras") or []
            if isinstance(cams, list):
                aporte["camaras"].extend(cams)
            elif cams:
                aporte["camaras"].append(str(cams))
        return aporte

    # BLOQUE 7
    if "bloque 7" in b or "secuestro" in b:
        elementos = []
        if isinstance(db, dict):
            elementos = db.get("elementos") or db.get("secuestros") or db.get("elementos_secuestrados") or []
            if not elementos:
                descs = buscar_recursivo(db, ["descripcion", "descripción", "elemento", "secuestro"])
                elementos = [{"descripcion": d} for d in descs[:10]]
        if isinstance(elementos, list):
            aporte["elementos"].extend(elementos)
        return aporte

    # JSON externo: guardar texto relevante
    if isinstance(data, dict):
        rels = buscar_recursivo(data, ["relato", "resumen", "descripcion", "descripción"])
        if rels:
            aporte["relatos_base"].append(rels[0])
    return aporte


def reconstruir_consolidado():
    consolidado = crear_consolidado_vacio()
    for item in st.session_state.b8_jsons:
        aporte = extraer_de_json(item["data"], item["bloque_confirmado"], item.get("archivo", ""))
        consolidado["json_cargados"].append(item.get("archivo", "JSON"))
        if aporte["bloque"] not in consolidado["bloques_recibidos"]:
            consolidado["bloques_recibidos"].append(aporte["bloque"])
        for k in ["victimas", "arrestados", "testigos", "elementos", "inspecciones", "camaras", "noticias_criminis", "relatos_base", "observaciones"]:
            consolidado[k].extend(aporte.get(k, []))
    st.session_state.b8_consolidado = consolidado
    return consolidado

# ============================================================
# ACTA
# ============================================================

def lista_texto(items, titulo=None):
    if not items:
        return ""
    lineas = []
    if titulo:
        lineas.append(titulo)
    for i, item in enumerate(items, start=1):
        if isinstance(item, dict):
            desc = item.get("descripcion") or item.get("descripción") or item.get("detalle") or item.get("elemento") or etiqueta_persona(item)
        else:
            desc = str(item)
        lineas.append(f"{i}. {desc}")
    return "\n".join(lineas)


def construir_acta_procedimiento():
    cons = reconstruir_consolidado()
    fecha = st.session_state.get("b8_fecha")
    if isinstance(fecha, date):
        fecha_txt = fecha.strftime("%d/%m/%Y")
    else:
        fecha_txt = str(fecha)

    hora = st.session_state.get("b8_hora", "")
    dep = st.session_state.get("b8_dependencia", "")
    rep = st.session_state.get("b8_reparticion", "")
    nro = st.session_state.get("b8_numero_acta", "")
    movil = st.session_state.get("b8_movil", "")
    personal = st.session_state.get("b8_personal_actante", "")
    lugar = st.session_state.get("b8_lugar_hecho", "")
    lugar_apre = st.session_state.get("b8_lugar_aprehension", "")
    incidencia = st.session_state.get("b8_incidencia", "")
    fiscal = st.session_state.get("b8_intervencion_fiscal", "")
    cierre = st.session_state.get("b8_hora_cierre", "") or hora

    partes = []
    partes.append("ACTA DE PROCEDIMIENTO")
    partes.append("")
    intro = (
        f"En la ciudad de Rosario, Departamento homónimo, Provincia de Santa Fe, en fecha {fecha_txt}, "
        f"siendo aproximadamente las {hora} horas, personal policial de {dep or rep or 'la dependencia interviniente'}"
    )
    if movil:
        intro += f", móvil {movil}"
    if personal:
        intro += f", integrado por {personal}"
    intro += ", en cumplimiento de sus funciones específicas, procede a labrar la presente acta de procedimiento."
    partes.append(intro)

    if nro or incidencia:
        partes.append(f"Actuación/Acta Nro.: {nro or 'S/D'}. Incidencia: {incidencia or 'S/D'}.")
    if lugar:
        partes.append(f"Lugar del hecho: {lugar}.")
    if lugar_apre:
        partes.append(f"Lugar de aprehensión: {lugar_apre}.")

    # Relato central: priorizar noticia criminis de víctima y relatos base
    relato_central = []
    if cons["noticias_criminis"]:
        relato_central.extend(cons["noticias_criminis"])
    elif cons["relatos_base"]:
        relato_central.extend(cons["relatos_base"][:2])

    if relato_central:
        partes.append("\nRELATO CIRCUNSTANCIADO:")
        for r in relato_central:
            partes.append(str(r).strip())
    else:
        partes.append("\nRELATO CIRCUNSTANCIADO:\nSe deberá completar el relato circunstanciado del procedimiento con los datos recolectados en el lugar.")

    if cons["victimas"]:
        partes.append("\nVÍCTIMA / DAMNIFICADO:")
        for v in cons["victimas"]:
            partes.append(f"- {etiqueta_persona(v)}.")

    if cons["arrestados"]:
        partes.append("\nAPREHENDIDO / ARRESTADO:")
        for a in cons["arrestados"]:
            partes.append(f"- {etiqueta_persona(a)}.")
            if isinstance(a, dict):
                if a.get("resultado_911"):
                    partes.append(f"  Consulta 911: {a.get('resultado_911')}.")
                if a.get("lesiones"):
                    partes.append(f"  Lesiones visibles: {a.get('lesiones')}. {a.get('detalle_lesiones','')}")
                if a.get("diagnostico") or a.get("hospital"):
                    partes.append(f"  Asistencia médica: {a.get('hospital','')} {a.get('medico','')} {a.get('diagnostico','')} {a.get('resultado','')}.")

    if cons["elementos"]:
        partes.append("\nSECUESTROS / ELEMENTOS DE INTERÉS:")
        for e in cons["elementos"]:
            if isinstance(e, dict):
                desc = e.get("descripcion") or e.get("detalle") or e.get("tipo") or str(e)
                dep_el = e.get("deposito") or e.get("depósito") or ""
                hall = e.get("lugar_hallazgo") or e.get("hallazgo") or ""
                linea = f"- {desc}"
                if hall:
                    linea += f", hallado en {hall}"
                if dep_el:
                    linea += f", quedando en depósito/resguardo en {dep_el}"
                linea += "."
                partes.append(linea)
            else:
                partes.append(f"- {e}.")

    if cons["inspecciones"] or cons["camaras"]:
        partes.append("\nINSPECCIÓN OCULAR / CÁMARAS:")
        if cons["inspecciones"]:
            partes.append(str(cons["inspecciones"][0]).strip())
        else:
            partes.append("Se deja constancia que se realizó inspección ocular y relevamiento de circunstancias de interés en el lugar del hecho.")
        if cons["camaras"]:
            partes.append(f"Asimismo, se relevaron cámaras vinculadas al lugar del hecho, conforme anexo respectivo.")

    if cons["testigos"]:
        partes.append("\nTESTIGOS / ENTREVISTAS:")
        for t in cons["testigos"]:
            partes.append(f"- {etiqueta_persona(t)}.")
        partes.append("Las entrevistas completas se agregan como anexos cuando corresponda.")

    if fiscal:
        partes.append("\nINTERVENCIÓN FISCAL / MESA DE ENLACE:")
        partes.append(fiscal)

    partes.append("\nANEXOS:")
    anexos = []
    if cons["victimas"]:
        anexos.append("Acta de Entrevista a Víctima/Damnificado y Derechos de la Víctima, si correspondiere.")
    if cons["arrestados"]:
        anexos.append("Acta de Aprehensión/Arrestado y constancias médicas/derechos del imputado, si correspondiere.")
    if cons["inspecciones"] or cons["camaras"]:
        anexos.append("Acta de Inspección Ocular, relevamiento de cámaras y anexos fotográficos.")
    if cons["elementos"]:
        anexos.append("Actas de Secuestro y constancias de depósito/resguardo.")
    if not anexos:
        anexos.append("Sin anexos importados al momento de confeccionar la presente.")
    for a in anexos:
        partes.append(f"- {a}")

    partes.append(
        f"\nNo siendo para más, siendo las {cierre} horas, se da por finalizada la presente, "
        "previa lectura y ratificación de su contenido, firmando al pie el personal actuante para constancia."
    )

    return "\n".join(partes)


def generar_pdf_acta(texto):
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, limpiar_pdf("POLICÍA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, limpiar_pdf("ACTA DE PROCEDIMIENTO"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)

    for parrafo in limpiar_pdf(texto).split("\n"):
        if not parrafo.strip():
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 6, parrafo)

    pdf.ln(15)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma personal actuante", ln=False, align="C")
    pdf.cell(85, 6, "Firma y aclaracion", ln=True, align="C")

    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", "replace")
    return bytes(salida)

# ============================================================
# INTERFAZ
# ============================================================

st.title("🚓 BLOQUE 8 — Consolidador del Acta de Procedimiento")
st.caption(LEMA)

# Recalcular consolidado al inicio de cada corrida
reconstruir_consolidado()

tabs = st.tabs([
    "Actuación",
    "Importar JSON",
    "Datos recibidos",
    "Acta de Procedimiento",
    "Descargar"
])

# ------------------------------------------------------------
# ACTUACION
# ------------------------------------------------------------
with tabs[0]:
    st.subheader("Actuación activa")
    st.info("Complete los datos mínimos del procedimiento. Luego importe los JSON recibidos por WhatsApp.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Número de acta / actuación", key="b8_numero_acta")
        st.date_input("Fecha", key="b8_fecha")
        st.text_input("Hora de inicio/intervención", key="b8_hora")
    with c2:
        st.text_input("Repartición / Unidad", key="b8_reparticion")
        st.text_input("Dependencia", key="b8_dependencia")
        st.text_input("Móvil", key="b8_movil")
    with c3:
        st.text_area("Personal actante/interviniente", key="b8_personal_actante", height=95)
        st.text_input("Incidencia", key="b8_incidencia")

    st.text_input("Lugar del hecho", key="b8_lugar_hecho")
    st.text_input("Lugar de aprehensión", key="b8_lugar_aprehension")
    st.text_area("Intervención fiscal / Mesa de Enlace / Directivas", key="b8_intervencion_fiscal", height=110)
    st.text_input("Hora de cierre del acta", key="b8_hora_cierre")

# ------------------------------------------------------------
# IMPORTAR JSON
# ------------------------------------------------------------
with tabs[1]:
    st.subheader("📥 Importar JSON recibidos por WhatsApp")
    st.info("Suba uno o varios archivos JSON enviados por colaboradores. Revise el bloque detectado antes de incorporarlos.")

    archivos = st.file_uploader(
        "Cargar JSON de colaboración",
        type=["json"],
        accept_multiple_files=True,
        key="b8_uploader_json"
    )

    pendientes = []
    if archivos:
        for idx, archivo in enumerate(archivos):
            try:
                data = json.loads(archivo.getvalue().decode("utf-8"))
            except Exception:
                try:
                    data = json.loads(archivo.getvalue().decode("latin-1"))
                except Exception as e:
                    st.error(f"No se pudo leer {archivo.name}: {e}")
                    continue

            detectado = detectar_bloque(data)
            st.markdown(f"### {archivo.name}")
            st.success(f"Detectado automáticamente: {detectado}")

            opciones = [
                "BLOQUE 1 — Datos base",
                "BLOQUE 2 — Arrestado/Aprehendido",
                "BLOQUE 3 — Víctima/Damnificado",
                "BLOQUE 4 — Testigo",
                "BLOQUE 6 — Inspección ocular",
                "BLOQUE 7 — Secuestros",
                "JSON EXTERNO"
            ]
            if detectado not in opciones:
                opciones.append(detectado)
            default_idx = opciones.index(detectado) if detectado in opciones else 0
            confirmado = st.selectbox(
                "Confirmar/corregir bloque antes de importar",
                opciones,
                index=default_idx,
                key=f"b8_tipo_{archivo.name}_{idx}"
            )

            with st.expander("Ver contenido JSON"):
                st.json(data)

            pendientes.append({"archivo": archivo.name, "data": data, "bloque_confirmado": confirmado})

        if st.button("✅ Incorporar JSON seleccionados al Acta", type="primary"):
            existentes = {(x.get("archivo"), x.get("bloque_confirmado")) for x in st.session_state.b8_jsons}
            agregados = 0
            for p in pendientes:
                ident = (p["archivo"], p["bloque_confirmado"])
                if ident not in existentes:
                    st.session_state.b8_jsons.append(p)
                    agregados += 1
            reconstruir_consolidado()
            st.success(f"Se incorporaron {agregados} JSON. Revise la pestaña 'Datos recibidos'.")
            st.rerun()

    st.divider()
    if st.session_state.b8_jsons:
        st.markdown("### JSON ya incorporados")
        for i, item in enumerate(st.session_state.b8_jsons, start=1):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write(f"{i}. **{item.get('archivo')}** — {item.get('bloque_confirmado')}")
            with col_b:
                if st.button("Eliminar", key=f"b8_del_json_{i}"):
                    st.session_state.b8_jsons.pop(i - 1)
                    reconstruir_consolidado()
                    st.rerun()
    else:
        st.warning("Todavía no hay JSON incorporados.")

# ------------------------------------------------------------
# DATOS RECIBIDOS
# ------------------------------------------------------------
with tabs[2]:
    cons = reconstruir_consolidado()
    st.subheader("Datos importantes recibidos")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("JSON cargados", len(cons["json_cargados"]))
    m2.metric("Víctimas", len(cons["victimas"]))
    m3.metric("Arrestados", len(cons["arrestados"]))
    m4.metric("Elementos", len(cons["elementos"]))

    st.markdown("### Bloques recibidos")
    if cons["bloques_recibidos"]:
        for b in cons["bloques_recibidos"]:
            st.success(b)
    else:
        st.info("No hay bloques recibidos todavía.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Víctimas")
        if cons["victimas"]:
            for v in cons["victimas"]:
                st.write("- " + etiqueta_persona(v))
        else:
            st.info("Sin víctimas importadas.")

        st.markdown("### Arrestados")
        if cons["arrestados"]:
            for a in cons["arrestados"]:
                st.write("- " + etiqueta_persona(a))
        else:
            st.info("Sin arrestados importados.")

    with col2:
        st.markdown("### Elementos / Secuestros")
        if cons["elementos"]:
            for e in cons["elementos"]:
                if isinstance(e, dict):
                    st.write("- " + str(e.get("descripcion") or e.get("detalle") or e))
                else:
                    st.write("- " + str(e))
        else:
            st.info("Sin elementos importados.")

        st.markdown("### Inspección / Cámaras")
        if cons["inspecciones"] or cons["camaras"]:
            for ins in cons["inspecciones"][:3]:
                st.write("- " + str(ins)[:500])
            if cons["camaras"]:
                st.write(f"Cámaras relevadas: {len(cons['camaras'])}")
        else:
            st.info("Sin inspección/cámaras importadas.")

    with st.expander("Ver consolidado técnico"):
        st.json(cons)

# ------------------------------------------------------------
# ACTA
# ------------------------------------------------------------
with tabs[3]:
    st.subheader("Acta de Procedimiento")
    st.info("Genere el borrador, revise y edite antes de descargar.")

    if st.button("🚓 Generar / actualizar Acta de Procedimiento", type="primary"):
        st.session_state.b8_acta_texto_editable = construir_acta_procedimiento()
        st.success("Acta generada. Puede editar el texto antes de descargar.")

    st.text_area(
        "Texto editable del Acta de Procedimiento",
        key="b8_acta_texto_editable",
        height=520
    )

# ------------------------------------------------------------
# DESCARGAR
# ------------------------------------------------------------
with tabs[4]:
    st.subheader("Descargar actuación final")

    texto_final = st.session_state.get("b8_acta_texto_editable", "")
    if not texto_final.strip():
        st.warning("Primero genere el Acta de Procedimiento en la pestaña anterior.")
    else:
        pdf_data = generar_pdf_acta(texto_final)
        fecha = st.session_state.get("b8_fecha")
        fecha_txt = fecha.strftime("%Y%m%d") if isinstance(fecha, date) else normalizar_nombre_archivo(fecha)
        base = normalizar_nombre_archivo(f"SIVAP_ACTA_{st.session_state.get('b8_numero_acta','')}_{fecha_txt}")

        consolidado_final = {
            "sistema": SISTEMA,
            "tipo_archivo": "acta_procedimiento_consolidada",
            "actuacion": {
                "numero_acta": st.session_state.get("b8_numero_acta", ""),
                "fecha": str(st.session_state.get("b8_fecha", "")),
                "hora": st.session_state.get("b8_hora", ""),
                "dependencia": st.session_state.get("b8_dependencia", ""),
                "reparticion": st.session_state.get("b8_reparticion", ""),
                "movil": st.session_state.get("b8_movil", ""),
                "personal_actante": st.session_state.get("b8_personal_actante", ""),
                "lugar_hecho": st.session_state.get("b8_lugar_hecho", ""),
                "lugar_aprehension": st.session_state.get("b8_lugar_aprehension", ""),
                "incidencia": st.session_state.get("b8_incidencia", ""),
            },
            "datos_consolidados": reconstruir_consolidado(),
            "acta_procedimiento": texto_final,
            "fecha_exportacion": datetime.now().isoformat()
        }

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "📄 Descargar PDF Acta",
                data=pdf_data,
                file_name=f"{base}.pdf",
                mime="application/pdf"
            )
        with c2:
            st.download_button(
                "📝 Descargar TXT Acta",
                data=texto_final,
                file_name=f"{base}.txt",
                mime="text/plain"
            )
        with c3:
            st.download_button(
                "📦 Descargar JSON Consolidado",
                data=json.dumps(consolidado_final, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=f"{base}_CONSOLIDADO.json",
                mime="application/json"
            )

# Guardado automático del bloque al finalizar la corrida
if GUARDADO_OK:
    try:
        autoguardar_bloque(BLOQUE_ID)
    except Exception:
        pass
