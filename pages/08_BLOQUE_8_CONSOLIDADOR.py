import streamlit as st
import json
import io
import re
from datetime import date, datetime
from fpdf import FPDF

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
except Exception:
    def iniciar_guardado_seguro(*args, **kwargs):
        return None
    def panel_guardado_seguro(*args, **kwargs):
        return None
    def autoguardar_bloque(*args, **kwargs):
        return None

# =====================================================
# S.I.V.A.P. - BLOQUE 8
# CONSOLIDADOR SIMPLE DEL ACTA DE PROCEDIMIENTO
# Objetivo: importar JSON recibidos por WhatsApp, recolectar
# lo importante y generar el Acta de Procedimiento.
# =====================================================

st.set_page_config(page_title="S.I.V.A.P. - Bloque 8 Consolidador", layout="wide", page_icon="🚓")

BLOQUE_ID = "BLOQUE_8_CONSOLIDADOR_ACTA_PROCEDIMIENTO"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

LEMA = "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora."

# =====================================================
# ESTADO
# =====================================================

def init_state():
    defaults = {
        "b8_numero_acta": "",
        "b8_fecha": date.today(),
        "b8_hora": datetime.now().strftime("%H:%M"),
        "b8_dependencia": "",
        "b8_reparticion": "UNIDAD REGIONAL II - ROSARIO",
        "b8_movil": "",
        "b8_personal_actante": "",
        "b8_lugar_hecho": "",
        "b8_lugar_aprehension": "",
        "b8_relato_base": "",
        "b8_intervencion_fiscal": "",
        "b8_hora_cierre": "",
        "b8_acta_generada": "",
        "b8_jsons_importados": [],
        "b8_consolidado": {
            "bloques": [],
            "victimas": [],
            "arrestados": [],
            "elementos": [],
            "inspecciones": [],
            "testigos": [],
            "noticias_criminis": [],
            "relatos_victima": [],
            "camaras": [],
            "resumenes": []
        }
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# UTILIDADES GENERALES
# =====================================================

def normalizar_txt(s):
    if s is None:
        return ""
    return str(s).strip()


def limpiar_pdf_texto(s):
    if s is None:
        return ""
    s = str(s)
    reemplazos = {
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-", "•": "-", "…": "...",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.",
        "🚓": "", "📥": "", "📦": "", "📄": "", "✅": "", "⚠️": ""
    }
    for a, b in reemplazos.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def json_text(data):
    try:
        return json.dumps(data, ensure_ascii=False).lower()
    except Exception:
        return str(data).lower()


def obtener_por_ruta(data, rutas, default=None):
    for ruta in rutas:
        ref = data
        ok = True
        for parte in ruta:
            if isinstance(ref, dict) and parte in ref:
                ref = ref[parte]
            else:
                ok = False
                break
        if ok and ref not in [None, "", [], {}]:
            return ref
    return default


def buscar_clave_recursiva(data, nombres):
    nombres_norm = {n.lower() for n in nombres}
    hallazgos = []
    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if kl in nombres_norm and not isinstance(v, (dict, list)) and str(v).strip():
                hallazgos.append(str(v).strip())
            elif isinstance(v, (dict, list)):
                hallazgos.extend(buscar_clave_recursiva(v, nombres))
    elif isinstance(data, list):
        for item in data:
            hallazgos.extend(buscar_clave_recursiva(item, nombres))
    return hallazgos


def buscar_diccionario_con_clave(data, claves_objetivo):
    claves_objetivo = {c.lower() for c in claves_objetivo}
    encontrados = []
    if isinstance(data, dict):
        keys = {str(k).lower() for k in data.keys()}
        if keys.intersection(claves_objetivo):
            encontrados.append(data)
        for v in data.values():
            encontrados.extend(buscar_diccionario_con_clave(v, claves_objetivo))
    elif isinstance(data, list):
        for item in data:
            encontrados.extend(buscar_diccionario_con_clave(item, claves_objetivo))
    return encontrados


def unir_nombre(apellido="", nombre=""):
    apellido = normalizar_txt(apellido)
    nombre = normalizar_txt(nombre)
    if apellido and nombre:
        return f"{apellido}, {nombre}"
    return apellido or nombre

# =====================================================
# DETECCION DE BLOQUES
# =====================================================

def detectar_bloque(data):
    """
    Deteccion robusta: primero mira campos estructurales y estructuras propias.
    No clasifica un JSON de victima como BLOQUE 2 solo porque mencione aprehendido.
    """
    texto = json_text(data)
    meta = " ".join([
        str(data.get("bloque", "")) if isinstance(data, dict) else "",
        str(data.get("modulo", "")) if isinstance(data, dict) else "",
        str(data.get("tipo_archivo", "")) if isinstance(data, dict) else "",
        str(data.get("version", "")) if isinstance(data, dict) else "",
    ]).lower()

    # Prioridad por estructura especifica de BLOQUE 3
    if any(x in meta for x in ["bloque_3", "bloque 3", "victima", "víctima", "damnificado", "entrevista"]):
        return "BLOQUE 3 — Víctima/Damnificado"
    if any(x in texto for x in ["identificacion_victima", "noticia_criminis", "derechos_victima", "relato_final"]):
        return "BLOQUE 3 — Víctima/Damnificado"

    # BLOQUE 2 por estructura
    if any(x in meta for x in ["bloque_2", "bloque 2", "arrestado"]):
        return "BLOQUE 2 — Arrestado/Aprehendido"
    if '"arrestados"' in texto or '"cantidad"' in texto and "arrestado" in texto:
        return "BLOQUE 2 — Arrestado/Aprehendido"

    # BLOQUE 6 por estructura, ya sin croquis como criterio principal
    if any(x in meta for x in ["bloque_6", "bloque 6", "inspeccion", "inspección"]):
        return "BLOQUE 6 — Inspección ocular"
    if any(x in texto for x in ["relato_inspeccion", "inspeccion_ocular", "camaras", "cámaras", "preservado"]):
        return "BLOQUE 6 — Inspección ocular"

    # BLOQUE 7 por estructura
    if any(x in meta for x in ["bloque_7", "bloque 7", "secuestro"]):
        return "BLOQUE 7 — Secuestros"
    if '"elementos"' in texto or '"secuestros"' in texto:
        return "BLOQUE 7 — Secuestros"

    if "testigo" in texto:
        return "BLOQUE 4 — Testigo"

    return "JSON externo / no identificado"

# =====================================================
# EXTRACTORES
# =====================================================

def extraer_bloque3(data):
    victimas = []
    noticias = []
    relatos = []
    resumenes = []

    ident = obtener_por_ruta(data, [
        ["datos_bloque", "identificacion_victima"],
        ["datos_bloque", "identificacion"],
        ["identificacion_victima"],
        ["identificacion"],
        ["bloques", "bloque3", "identificacion_victima"],
    ], {})

    if isinstance(ident, dict) and ident:
        nombre = unir_nombre(
            ident.get("apellido", "") or ident.get("apellidos", ""),
            ident.get("nombre", "") or ident.get("nombres", "") or ident.get("nombre_apellido", "")
        )
        if not nombre:
            nombre = ident.get("nombre_completo", "") or ident.get("victima", "") or ident.get("damnificado", "")
        victima = {
            "nombre": normalizar_txt(nombre),
            "dni": normalizar_txt(ident.get("dni", "") or ident.get("documento", "")),
            "domicilio": normalizar_txt(ident.get("domicilio", "")),
            "telefono": normalizar_txt(ident.get("telefono", "") or ident.get("celular", "")),
            "detalle": normalizar_txt(ident.get("vinculo_hecho", "") or ident.get("condicion", "Víctima/Damnificado"))
        }
        if victima["nombre"] or victima["dni"]:
            victimas.append(victima)

    # Fallback para JSONs con otro formato: buscar diccionarios que parezcan víctima
    if not victimas:
        candidatos = buscar_diccionario_con_clave(data, ["dni", "apellido", "nombre", "domicilio", "telefono"])
        for cand in candidatos[:3]:
            if not isinstance(cand, dict):
                continue
            cand_txt = json.dumps(cand, ensure_ascii=False).lower()
            if any(x in cand_txt for x in ["victima", "víctima", "damnificado", "entrevista"]):
                nombre = unir_nombre(cand.get("apellido", ""), cand.get("nombre", "")) or cand.get("nombre_completo", "")
                if nombre or cand.get("dni"):
                    victimas.append({
                        "nombre": normalizar_txt(nombre),
                        "dni": normalizar_txt(cand.get("dni", "")),
                        "domicilio": normalizar_txt(cand.get("domicilio", "")),
                        "telefono": normalizar_txt(cand.get("telefono", "") or cand.get("celular", "")),
                        "detalle": "Víctima/Damnificado"
                    })
                    break

    noticia = obtener_por_ruta(data, [
        ["datos_bloque", "noticia_criminis"],
        ["noticia_criminis"],
        ["bloques", "bloque3", "noticia_criminis"],
    ], "")
    if noticia:
        noticias.append(str(noticia).strip())

    relato_final = obtener_por_ruta(data, [
        ["datos_bloque", "relato_final"],
        ["relato_final"],
        ["bloques", "bloque3", "relato_final"],
    ], "")
    relato_crudo = obtener_por_ruta(data, [
        ["datos_bloque", "relato_crudo"],
        ["relato_crudo"],
        ["bloques", "bloque3", "relato_crudo"],
    ], "")

    if relato_final:
        relatos.append(str(relato_final).strip())
    elif relato_crudo:
        relatos.append(str(relato_crudo).strip())

    if noticias:
        resumenes.extend(noticias)
    elif relatos:
        resumenes.append(relatos[0][:700])

    return {"victimas": victimas, "noticias_criminis": noticias, "relatos_victima": relatos, "resumenes": resumenes}


def extraer_bloque2(data):
    arrestados = []
    lista = obtener_por_ruta(data, [["arrestados"], ["datos_bloque", "arrestados"]], [])
    if isinstance(lista, dict):
        lista = [lista]
    if isinstance(lista, list):
        for a in lista:
            if not isinstance(a, dict):
                continue
            nombre = unir_nombre(a.get("apellido", ""), a.get("nombre", "")) or a.get("nombre_completo", "")
            arrestados.append({
                "nombre": normalizar_txt(nombre),
                "dni": normalizar_txt(a.get("dni", "")),
                "domicilio": normalizar_txt(a.get("domicilio", "")),
                "consulta_911": normalizar_txt(a.get("resultado_911", "") or a.get("consulta_911", "")),
                "lesiones": normalizar_txt(a.get("lesiones", "")),
                "diagnostico": normalizar_txt(a.get("diagnostico", "")),
                "derechos": normalizar_txt(a.get("derechos", "")),
                "detalle": normalizar_txt(a.get("detalle_lesiones", "") or a.get("resultado", ""))
            })
    return {"arrestados": arrestados}


def extraer_bloque6(data):
    inspecciones = []
    camaras = []
    datos = obtener_por_ruta(data, [["datos"], ["datos_bloque"], ["inspeccion"]], {})

    relato = ""
    if isinstance(datos, dict):
        relato = datos.get("relato_inspeccion", "") or datos.get("relato", "") or datos.get("resumen_inspeccion", "")
        lugar = datos.get("lugar", "") or datos.get("lugar_inspeccion", "") or datos.get("direccion", "")
        preservado = datos.get("preservado", "")
    else:
        lugar, preservado = "", ""

    resumen = obtener_por_ruta(data, [["resumen_para_acta_procedimiento"], ["resumen_inspeccion"], ["datos", "resumen_para_acta_procedimiento"]], "")
    if resumen or relato or lugar:
        inspecciones.append({
            "lugar": normalizar_txt(lugar),
            "preservado": normalizar_txt(preservado),
            "resumen": normalizar_txt(resumen or relato)
        })

    lista_camaras = obtener_por_ruta(data, [["camaras"], ["datos_bloque", "camaras"], ["datos", "camaras"]], [])
    if isinstance(lista_camaras, dict):
        lista_camaras = [lista_camaras]
    if isinstance(lista_camaras, list):
        for cam in lista_camaras:
            if isinstance(cam, dict):
                camaras.append({
                    "tipo": normalizar_txt(cam.get("tipo", "")),
                    "ubicacion": normalizar_txt(cam.get("ubicacion", "")),
                    "orientacion": normalizar_txt(cam.get("orientacion", "") or cam.get("cobertura", "")),
                    "observaciones": normalizar_txt(cam.get("observaciones", ""))
                })
    else:
        cams = buscar_clave_recursiva(data, ["camaras", "cámaras", "camara", "cámara"])
        for c in cams[:5]:
            camaras.append({"tipo": "", "ubicacion": c, "orientacion": "", "observaciones": ""})

    return {"inspecciones": inspecciones, "camaras": camaras}


def extraer_bloque7(data):
    elementos = []
    lista = obtener_por_ruta(data, [["elementos"], ["secuestros"], ["datos_bloque", "elementos"], ["datos_bloque", "secuestros"]], [])
    if isinstance(lista, dict):
        lista = [lista]
    if isinstance(lista, list):
        for e in lista:
            if isinstance(e, dict):
                elementos.append({
                    "descripcion": normalizar_txt(e.get("descripcion", "") or e.get("elemento", "") or e.get("detalle", "")),
                    "lugar_hallazgo": normalizar_txt(e.get("lugar_hallazgo", "") or e.get("hallazgo", "")),
                    "deposito": normalizar_txt(e.get("deposito", "") or e.get("resguardo", "")),
                    "testigo": normalizar_txt(e.get("testigo", ""))
                })
            elif str(e).strip():
                elementos.append({"descripcion": str(e).strip(), "lugar_hallazgo": "", "deposito": "", "testigo": ""})
    return {"elementos": elementos}


def extraer_testigos(data):
    testigos = []
    texto = json_text(data)
    if "testigo" not in texto:
        return {"testigos": []}
    candidatos = buscar_diccionario_con_clave(data, ["dni", "apellido", "nombre", "domicilio", "telefono"])
    for cand in candidatos:
        if isinstance(cand, dict):
            nombre = unir_nombre(cand.get("apellido", ""), cand.get("nombre", "")) or cand.get("nombre_completo", "")
            if nombre or cand.get("dni"):
                testigos.append({
                    "nombre": normalizar_txt(nombre),
                    "dni": normalizar_txt(cand.get("dni", "")),
                    "domicilio": normalizar_txt(cand.get("domicilio", "")),
                    "telefono": normalizar_txt(cand.get("telefono", ""))
                })
    return {"testigos": testigos[:5]}


def extraer_info(data, bloque):
    out = {"bloques": [bloque], "victimas": [], "arrestados": [], "elementos": [], "inspecciones": [], "testigos": [], "noticias_criminis": [], "relatos_victima": [], "camaras": [], "resumenes": []}
    if "BLOQUE 3" in bloque:
        out.update(extraer_bloque3(data))
    elif "BLOQUE 2" in bloque:
        out.update(extraer_bloque2(data))
    elif "BLOQUE 6" in bloque:
        out.update(extraer_bloque6(data))
    elif "BLOQUE 7" in bloque:
        out.update(extraer_bloque7(data))
    elif "BLOQUE 4" in bloque:
        out.update(extraer_testigos(data))
    else:
        # Intentos generales sin forzar clasificación errónea
        out.update(extraer_bloque3(data))
        b2 = extraer_bloque2(data)
        if b2.get("arrestados"):
            out.update(b2)
        b7 = extraer_bloque7(data)
        if b7.get("elementos"):
            out.update(b7)
        b6 = extraer_bloque6(data)
        if b6.get("inspecciones") or b6.get("camaras"):
            out.update(b6)
    return out


def consolidar_jsons():
    consolidado = {"bloques": [], "victimas": [], "arrestados": [], "elementos": [], "inspecciones": [], "testigos": [], "noticias_criminis": [], "relatos_victima": [], "camaras": [], "resumenes": []}
    for item in st.session_state.b8_jsons_importados:
        info = item.get("info_extraida", {})
        for k in consolidado.keys():
            vals = info.get(k, [])
            if isinstance(vals, list):
                consolidado[k].extend(vals)
    # deduplicar bloques conservando orden
    vistos = set()
    bloques = []
    for b in consolidado["bloques"]:
        if b not in vistos:
            bloques.append(b)
            vistos.add(b)
    consolidado["bloques"] = bloques
    st.session_state.b8_consolidado = consolidado
    return consolidado

# =====================================================
# ACTA Y PDF
# =====================================================

def linea_persona(p):
    partes = []
    if p.get("nombre"):
        partes.append(p["nombre"])
    if p.get("dni"):
        partes.append(f"DNI Nro. {p['dni']}")
    if p.get("domicilio"):
        partes.append(f"domicilio {p['domicilio']}")
    return ", ".join(partes)


def generar_texto_acta():
    c = st.session_state.b8_consolidado
    fecha = st.session_state.b8_fecha
    if isinstance(fecha, date):
        fecha_txt = fecha.strftime("%d/%m/%Y")
    else:
        fecha_txt = str(fecha)

    hora = st.session_state.b8_hora or "____"
    dependencia = st.session_state.b8_dependencia or "dependencia policial interviniente"
    movil = st.session_state.b8_movil or "móvil policial"
    personal = st.session_state.b8_personal_actante or "personal policial actuante"
    nro = st.session_state.b8_numero_acta or "____"
    lugar = st.session_state.b8_lugar_hecho or "lugar del hecho"
    lugar_apre = st.session_state.b8_lugar_aprehension

    partes = []
    partes.append("ACTA DE PROCEDIMIENTO")
    partes.append("")
    partes.append(
        f"En la ciudad de Rosario, Departamento homónimo, Provincia de Santa Fe, a fecha {fecha_txt}, siendo aproximadamente las {hora} horas, "
        f"personal de {dependencia}, a cargo/intervención de {personal}, móvil {movil}, en relación al Acta Nro. {nro}, procede a labrar la presente acta de procedimiento."
    )
    if lugar:
        partes.append(f"El procedimiento tuvo lugar en {lugar}.")

    if st.session_state.b8_relato_base.strip():
        partes.append("")
        partes.append("RELATO CIRCUNSTANCIADO:")
        partes.append(st.session_state.b8_relato_base.strip())

    # Víctima / noticia criminis
    if c.get("victimas") or c.get("noticias_criminis"):
        partes.append("")
        partes.append("ENTREVISTA INICIAL / VÍCTIMA:")
        if c.get("noticias_criminis"):
            partes.append(c["noticias_criminis"][0])
        elif c.get("victimas"):
            v = c["victimas"][0]
            partes.append(f"Seguidamente se entrevista a quien dijo llamarse {linea_persona(v)}, quien manifestó circunstancias vinculadas al hecho investigado, labrándose el acta de entrevista correspondiente como anexo.")

    # Arrestados
    if c.get("arrestados"):
        partes.append("")
        partes.append("APREHENDIDO/S:")
        for a in c["arrestados"]:
            texto = f"Se individualiza en carácter de aprehendido a {linea_persona(a)}."
            if a.get("consulta_911"):
                texto += f" Consulta/resultado 911: {a.get('consulta_911')}."
            if a.get("lesiones") and a.get("lesiones") != "NO":
                texto += f" Presenta/declara lesiones: {a.get('lesiones')}."
            if a.get("diagnostico"):
                texto += f" Diagnóstico/asistencia médica: {a.get('diagnostico')}."
            if a.get("derechos"):
                texto += f" Lectura de derechos: {a.get('derechos')}."
            partes.append(texto)
        if lugar_apre:
            partes.append(f"Lugar de aprehensión: {lugar_apre}.")

    # Secuestros
    if c.get("elementos"):
        partes.append("")
        partes.append("SECUESTROS / ELEMENTOS:")
        for e in c["elementos"]:
            texto = f"Se procede al secuestro de {e.get('descripcion','elemento sin descripción')}"
            if e.get("lugar_hallazgo"):
                texto += f", hallado en {e.get('lugar_hallazgo')}"
            if e.get("deposito"):
                texto += f", quedando depositado/resguardado en {e.get('deposito')}"
            texto += "."
            partes.append(texto)

    # Inspección / cámaras
    if c.get("inspecciones") or c.get("camaras"):
        partes.append("")
        partes.append("INSPECCIÓN OCULAR / CÁMARAS:")
        if c.get("inspecciones"):
            ins = c["inspecciones"][0]
            resumen = ins.get("resumen") or "se realizó inspección ocular en el lugar."
            partes.append(f"Se deja constancia que se realizó inspección ocular. {resumen}")
        if c.get("camaras"):
            partes.append(f"Asimismo, se efectuó relevamiento de cámaras, registrándose {len(c['camaras'])} cámara/s de interés para la investigación, quedando el detalle en el anexo respectivo.")

    # Testigos
    if c.get("testigos"):
        partes.append("")
        partes.append("TESTIGOS:")
        for t in c["testigos"]:
            partes.append(f"Se individualiza testigo: {linea_persona(t)}.")

    if st.session_state.b8_intervencion_fiscal.strip():
        partes.append("")
        partes.append("INTERVENCIÓN FISCAL / MESA DE ENLACE:")
        partes.append(st.session_state.b8_intervencion_fiscal.strip())

    partes.append("")
    cierre_hora = st.session_state.b8_hora_cierre or "____"
    partes.append(f"No siendo para más, siendo las {cierre_hora} horas, se da por finalizado el presente acto, firmando al pie el personal actuante para debida constancia.")

    return "\n\n".join(partes)


class PDFActa(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 7, limpiar_pdf_texto("POLICIA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
        self.set_font("Arial", "B", 10)
        self.cell(0, 6, limpiar_pdf_texto("S.I.V.A.P. - ACTA DE PROCEDIMIENTO"), ln=True, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 8, limpiar_pdf_texto(f"Página {self.page_no()} - {LEMA}"), align="C")


def generar_pdf_bytes(texto):
    pdf = PDFActa()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Arial", "", 10)
    for parrafo in limpiar_pdf_texto(texto).split("\n"):
        if not parrafo.strip():
            pdf.ln(3)
        else:
            pdf.set_x(18)
            pdf.multi_cell(174, 6.5, parrafo)
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)

# =====================================================
# INTERFAZ
# =====================================================

st.title("🚓 BLOQUE 8 — Consolidador del Acta de Procedimiento")
st.caption(LEMA)

tabs = st.tabs(["Actuación", "Importar JSON", "Datos recibidos", "Acta de Procedimiento", "Descargar"])

with tabs[0]:
    st.subheader("Actuación activa")
    st.info("Cargue los datos mínimos del procedimiento. Luego importe los JSON recibidos por WhatsApp.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Nro. de acta / procedimiento", key="b8_numero_acta")
        st.date_input("Fecha", key="b8_fecha")
        st.text_input("Hora de inicio / intervención", key="b8_hora")
    with c2:
        st.text_input("Repartición", key="b8_reparticion")
        st.text_input("Dependencia", key="b8_dependencia")
        st.text_input("Móvil", key="b8_movil")
    with c3:
        st.text_area("Personal actante / interviniente", key="b8_personal_actante", height=100)
        st.text_input("Lugar del hecho", key="b8_lugar_hecho")
        st.text_input("Lugar de aprehensión", key="b8_lugar_aprehension")
    st.text_area("Relato base inicial del actante", key="b8_relato_base", height=180)
    st.text_area("Intervención fiscal / Mesa de Enlace / directivas", key="b8_intervencion_fiscal", height=100)
    st.text_input("Hora de cierre del acta", key="b8_hora_cierre")

with tabs[1]:
    st.subheader("Importar JSON recibidos por WhatsApp")
    st.info("Suba uno o varios archivos JSON enviados por colaboradores. El sistema detecta el bloque y extrae lo importante para el Acta de Procedimiento.")
    archivos = st.file_uploader("Cargar JSON de colaboración", type=["json"], accept_multiple_files=True, key="b8_uploader_json")

    if archivos:
        temporales = []
        for idx, archivo in enumerate(archivos):
            try:
                data = json.load(archivo)
                bloque_auto = detectar_bloque(data)
                opciones = [
                    "BLOQUE 1 — Datos base",
                    "BLOQUE 2 — Arrestado/Aprehendido",
                    "BLOQUE 3 — Víctima/Damnificado",
                    "BLOQUE 4 — Testigo",
                    "BLOQUE 6 — Inspección ocular",
                    "BLOQUE 7 — Secuestros",
                    "JSON externo / no identificado",
                ]
                if bloque_auto not in opciones:
                    opciones.append(bloque_auto)
                st.markdown(f"### Archivo: {archivo.name}")
                bloque_final = st.selectbox("Bloque correcto", opciones, index=opciones.index(bloque_auto), key=f"b8_bloque_sel_{idx}_{archivo.name}")
                info = extraer_info(data, bloque_final)

                cols = st.columns(4)
                cols[0].metric("Víctimas", len(info.get("victimas", [])))
                cols[1].metric("Arrestados", len(info.get("arrestados", [])))
                cols[2].metric("Elementos", len(info.get("elementos", [])))
                cols[3].metric("Cámaras", len(info.get("camaras", [])))

                with st.expander("Vista previa extraída"):
                    st.json(info)

                temporales.append({"nombre_archivo": archivo.name, "bloque": bloque_final, "data": data, "info_extraida": info, "fecha_importacion": datetime.now().isoformat()})
            except Exception as e:
                st.error(f"No se pudo leer {archivo.name}: {e}")

        if temporales and st.button("📥 Incorporar JSON al procedimiento", use_container_width=True):
            # Evita duplicar por nombre de archivo y bloque; si se vuelve a subir, reemplaza.
            existentes = {(j.get("nombre_archivo"), j.get("bloque")) for j in st.session_state.b8_jsons_importados}
            for item in temporales:
                key = (item.get("nombre_archivo"), item.get("bloque"))
                if key not in existentes:
                    st.session_state.b8_jsons_importados.append(item)
            consolidar_jsons()
            autoguardar_bloque(BLOQUE_ID)
            st.success("JSON incorporados. Revise la pestaña 'Datos recibidos'.")

    if st.session_state.b8_jsons_importados:
        st.divider()
        if st.button("🧹 Limpiar JSON importados", use_container_width=True):
            st.session_state.b8_jsons_importados = []
            consolidar_jsons()
            st.rerun()

with tabs[2]:
    consolidado = consolidar_jsons()
    st.subheader("Datos importantes recibidos")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("JSON cargados", len(st.session_state.b8_jsons_importados))
    m2.metric("Víctimas", len(consolidado.get("victimas", [])))
    m3.metric("Arrestados", len(consolidado.get("arrestados", [])))
    m4.metric("Elementos", len(consolidado.get("elementos", [])))

    st.markdown("### Bloques recibidos")
    if consolidado.get("bloques"):
        for b in consolidado["bloques"]:
            st.success(b)
    else:
        st.warning("Todavía no hay bloques recibidos.")

    colv, cole = st.columns(2)
    with colv:
        st.markdown("### Víctimas")
        if consolidado.get("victimas"):
            for v in consolidado["victimas"]:
                st.write(f"- {linea_persona(v)}")
        else:
            st.info("Sin víctimas importadas.")

        st.markdown("### Arrestados")
        if consolidado.get("arrestados"):
            for a in consolidado["arrestados"]:
                st.write(f"- {linea_persona(a)}")
        else:
            st.info("Sin arrestados importados.")

    with cole:
        st.markdown("### Elementos / Secuestros")
        if consolidado.get("elementos"):
            for e in consolidado["elementos"]:
                st.write(f"- {e.get('descripcion','')}")
        else:
            st.info("Sin elementos importados.")

        st.markdown("### Inspección / Cámaras")
        if consolidado.get("inspecciones") or consolidado.get("camaras"):
            for ins in consolidado.get("inspecciones", []):
                st.write(f"- {ins.get('resumen','')}")
            if consolidado.get("camaras"):
                st.write(f"- Cámaras relevadas: {len(consolidado.get('camaras', []))}")
        else:
            st.info("Sin inspección/cámaras importadas.")

    with st.expander("Ver consolidado técnico"):
        st.json(consolidado)

with tabs[3]:
    consolidar_jsons()
    st.subheader("Acta de Procedimiento")
    if st.button("🚓 Generar / actualizar Acta de Procedimiento", use_container_width=True):
        st.session_state.b8_acta_generada = generar_texto_acta()
        autoguardar_bloque(BLOQUE_ID)
        st.success("Acta generada. Puede editarla antes de descargar.")

    if not st.session_state.b8_acta_generada:
        st.session_state.b8_acta_generada = generar_texto_acta()

    st.text_area("Texto final editable", key="b8_acta_generada", height=520)

with tabs[4]:
    consolidar_jsons()
    st.subheader("Descargar actuación final")
    texto = st.session_state.b8_acta_generada or generar_texto_acta()
    pdf_bytes = generar_pdf_bytes(texto)
    consolidado_final = {
        "sistema": "S.I.V.A.P.",
        "bloque": "BLOQUE 8 — Consolidador del Acta de Procedimiento",
        "actuacion": {
            "numero_acta": st.session_state.b8_numero_acta,
            "fecha": str(st.session_state.b8_fecha),
            "hora": st.session_state.b8_hora,
            "dependencia": st.session_state.b8_dependencia,
            "reparticion": st.session_state.b8_reparticion,
            "movil": st.session_state.b8_movil,
            "personal_actante": st.session_state.b8_personal_actante,
            "lugar_hecho": st.session_state.b8_lugar_hecho,
            "lugar_aprehension": st.session_state.b8_lugar_aprehension,
        },
        "datos_consolidados": st.session_state.b8_consolidado,
        "json_importados": [
            {"nombre_archivo": j.get("nombre_archivo"), "bloque": j.get("bloque"), "fecha_importacion": j.get("fecha_importacion")} for j in st.session_state.b8_jsons_importados
        ],
        "acta_procedimiento": texto,
        "fecha_exportacion": datetime.now().isoformat()
    }
    nombre_base = st.session_state.b8_numero_acta.replace("/", "-").replace(" ", "_") if st.session_state.b8_numero_acta else "SIN_NUMERO"
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📄 Descargar PDF Acta", data=pdf_bytes, file_name=f"SIVAP_ACTA_PROCEDIMIENTO_{nombre_base}.pdf", mime="application/pdf", use_container_width=True)
    with c2:
        st.download_button("📝 Descargar TXT Acta", data=texto, file_name=f"SIVAP_ACTA_PROCEDIMIENTO_{nombre_base}.txt", mime="text/plain", use_container_width=True)
    with c3:
        st.download_button("📦 Descargar JSON consolidado", data=json.dumps(consolidado_final, ensure_ascii=False, indent=2), file_name=f"SIVAP_CONSOLIDADO_{nombre_base}.json", mime="application/json", use_container_width=True)

try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
