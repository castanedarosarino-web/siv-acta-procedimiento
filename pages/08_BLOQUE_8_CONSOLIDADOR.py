import streamlit as st
import json
import re
from datetime import datetime, date
from fpdf import FPDF

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_DISPONIBLE = True
except Exception:
    GUARDADO_DISPONIBLE = False

# =====================================================
# S.I.V.A.P. - BLOQUE 8
# CONSOLIDADOR SIMPLE DEL ACTA DE PROCEDIMIENTO
#
# Objetivo unico:
# - Importar JSON recibidos por WhatsApp.
# - Extraer datos importantes.
# - Rellenar campos editables.
# - Permitir correccion del actante.
# - Generar ACTA DE PROCEDIMIENTO.
# =====================================================

st.set_page_config(
    page_title="S.I.V.A.P. - Bloque 8 Consolidador",
    page_icon="🚓",
    layout="wide"
)

BLOQUE_ID = "BLOQUE_8_CONSOLIDADOR_SIMPLE"
if GUARDADO_DISPONIBLE:
    try:
        iniciar_guardado_seguro(BLOQUE_ID)
        panel_guardado_seguro(BLOQUE_ID)
    except Exception:
        pass

# =====================================================
# ESTADO
# =====================================================

def init_state():
    defaults = {
        "b8_numero_acta": "",
        "b8_fecha": date.today(),
        "b8_hora_inicio": datetime.now().strftime("%H:%M"),
        "b8_hora_cierre": "",
        "b8_dependencia": "",
        "b8_unidad_regional": "UR II - ROSARIO",
        "b8_movil": "",
        "b8_personal_actante": "",
        "b8_personal_interviniente": "",
        "b8_lugar_hecho": "",
        "b8_lugar_aprehension": "",
        "b8_incidencia": "",
        "b8_intervencion_fiscal": "",
        "b8_disposiciones": "",
        "b8_observaciones_cierre": "",
        "b8_relato_base": "",
        "b8_relato_final_acta": "",
        "b8_json_importados": [],
        "b8_bloques_recibidos": [],
        "b8_victimas": [],
        "b8_arrestados": [],
        "b8_elementos": [],
        "b8_inspeccion": {},
        "b8_camaras": [],
        "b8_notas_importadas": [],
        "b8_pdf_generado": b"",
        "b8_json_consolidado": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

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
        "–": "-", "—": "-", "“": '"', "”": '"', "’": "'", "‘": "'",
        "✅": "", "⚠️": "", "🚓": "", "📥": "", "📄": "", "📦": ""
    }
    for a, b in reemplazos.items():
        texto = texto.replace(a, b)
    return texto.encode("latin-1", "replace").decode("latin-1")


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def compactar_espacios(txt):
    return re.sub(r"\s+", " ", str(txt or "")).strip()


def deep_get(data, paths, default=""):
    for path in paths:
        ref = data
        ok = True
        for part in path:
            if isinstance(ref, dict) and part in ref:
                ref = ref[part]
            else:
                ok = False
                break
        if ok and ref not in (None, "", [], {}):
            return ref
    return default


def buscar_valores(data, nombres):
    resultados = []
    nombres = [n.lower() for n in nombres]
    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if any(n in kl for n in nombres) and not isinstance(v, (dict, list)):
                if str(v).strip():
                    resultados.append(str(v).strip())
            elif isinstance(v, (dict, list)):
                resultados.extend(buscar_valores(v, nombres))
    elif isinstance(data, list):
        for item in data:
            resultados.extend(buscar_valores(item, nombres))
    return resultados


def lista_unica(lista):
    salida = []
    vistos = set()
    for item in lista:
        txt = compactar_espacios(item)
        if txt and txt.lower() not in vistos:
            salida.append(txt)
            vistos.add(txt.lower())
    return salida


def normalizar_nombre_archivo(txt):
    txt = limpiar_pdf(txt or "SIVAP")
    txt = re.sub(r"[^A-Za-z0-9_-]+", "_", txt)
    return txt.strip("_")[:80] or "SIVAP"


def agregar_bloque_recibido(nombre):
    if nombre and nombre not in st.session_state.b8_bloques_recibidos:
        st.session_state.b8_bloques_recibidos.append(nombre)


def detectar_bloque(data):
    # Primero datos estructurales, despues texto libre.
    bloque_raw = " ".join([
        str(data.get("bloque", "")) if isinstance(data, dict) else "",
        str(data.get("modulo", "")) if isinstance(data, dict) else "",
        str(data.get("tipo_archivo", "")) if isinstance(data, dict) else "",
        str(data.get("version", "")) if isinstance(data, dict) else ""
    ]).lower()

    datos_bloque = data.get("datos_bloque", {}) if isinstance(data, dict) else {}
    if isinstance(datos_bloque, dict):
        claves_bloque = " ".join(datos_bloque.keys()).lower()
    else:
        claves_bloque = ""

    estructural = bloque_raw + " " + claves_bloque

    if "bloque_3" in estructural or "bloque 3" in estructural or "victima" in estructural or "víctima" in estructural or "damnificado" in estructural or "entrevista" in estructural:
        if "identificacion_victima" in estructural or "noticia_criminis" in estructural or "relato_final" in estructural or "derechos_victima" in estructural or "victima" in estructural or "damnificado" in estructural:
            return "BLOQUE 3 — Víctima/Damnificado"

    if "bloque_2" in estructural or "bloque 2" in estructural or "arrestado" in estructural or "aprehendido" in estructural or "detenido" in estructural:
        if "arrestados" in estructural or "arrestado" in bloque_raw or "aprehendido" in bloque_raw:
            return "BLOQUE 2 — Arrestado/Aprehendido"

    if "bloque_6" in estructural or "bloque 6" in estructural or "inspeccion" in estructural or "inspección" in estructural or "camara" in estructural or "cámara" in estructural:
        return "BLOQUE 6 — Inspección Ocular"

    if "bloque_7" in estructural or "bloque 7" in estructural or "secuestro" in estructural or "elementos" in estructural:
        return "BLOQUE 7 — Secuestros"

    if "bloque_1" in estructural or "bloque 1" in estructural or "acta de procedimiento" in estructural:
        return "BLOQUE 1 — Datos Base"

    texto = json.dumps(data, ensure_ascii=False).lower()
    # En texto libre, priorizar victima antes que aprehendido, porque B3 puede mencionar al aprehendido.
    if any(x in texto for x in ["identificacion_victima", "noticia_criminis", "derechos_victima", "victima", "víctima", "damnificado"]):
        return "BLOQUE 3 — Víctima/Damnificado"
    if any(x in texto for x in ["arrestados", "bloque_2_arrestado", "consulta_911"]):
        return "BLOQUE 2 — Arrestado/Aprehendido"
    if any(x in texto for x in ["inspeccion", "inspección", "camaras", "cámaras"]):
        return "BLOQUE 6 — Inspección Ocular"
    if any(x in texto for x in ["secuestro", "elementos_secuestrados", "deposito"]):
        return "BLOQUE 7 — Secuestros"
    return "JSON externo / no identificado"


def autodetectar_o_corregir_bloque(data, sugerido, widget_key):
    opciones = [
        "BLOQUE 1 — Datos Base",
        "BLOQUE 2 — Arrestado/Aprehendido",
        "BLOQUE 3 — Víctima/Damnificado",
        "BLOQUE 4 — Testigo",
        "BLOQUE 6 — Inspección Ocular",
        "BLOQUE 7 — Secuestros",
        "JSON externo / no identificado"
    ]
    idx = opciones.index(sugerido) if sugerido in opciones else len(opciones) - 1
    return st.selectbox("Bloque correcto", opciones, index=idx, key=widget_key)

# =====================================================
# EXTRACTORES POR BLOQUE
# =====================================================

def extraer_autor_y_actuacion(data):
    autor = data.get("autor_carga", {}) if isinstance(data, dict) else {}
    actuacion = data.get("actuacion", {}) if isinstance(data, dict) else {}

    # Completar actuacion global si viene del JSON y aun esta vacia.
    if isinstance(actuacion, dict):
        mapa = {
            "numero_acta": "b8_numero_acta",
            "nro_acta": "b8_numero_acta",
            "fecha": "b8_fecha",
            "dependencia": "b8_dependencia",
            "reparticion": "b8_unidad_regional",
            "movil": "b8_movil",
            "móvil": "b8_movil",
            "lugar_hecho": "b8_lugar_hecho",
            "lugar": "b8_lugar_hecho",
            "lugar_aprehension": "b8_lugar_aprehension",
            "incidencia": "b8_incidencia"
        }
        for k, dest in mapa.items():
            if k in actuacion and actuacion[k] not in (None, ""):
                if dest == "b8_fecha":
                    try:
                        if not st.session_state.get(dest):
                            st.session_state[dest] = date.fromisoformat(str(actuacion[k])[:10])
                    except Exception:
                        pass
                elif not st.session_state.get(dest):
                    st.session_state[dest] = str(actuacion[k])

    if isinstance(autor, dict):
        nombre = autor.get("nombre_apellido") or autor.get("nombre") or ""
        jerarquia = autor.get("jerarquia") or ""
        if nombre and not st.session_state.get("b8_personal_actante"):
            st.session_state.b8_personal_actante = compactar_espacios(f"{jerarquia} {nombre}")


def importar_bloque1(data):
    extraer_autor_y_actuacion(data)
    agregar_bloque_recibido("BLOQUE 1 — Datos Base")

    posibles = data
    if isinstance(data, dict):
        posibles = data.get("datos_bloque") or data.get("data_operativa") or data

    pares = [
        ("nro_acta", "b8_numero_acta"),
        ("numero_acta", "b8_numero_acta"),
        ("incidencia", "b8_incidencia"),
        ("dependencia", "b8_dependencia"),
        ("movil", "b8_movil"),
        ("móvil", "b8_movil"),
        ("personal", "b8_personal_interviniente"),
        ("l_hecho", "b8_lugar_hecho"),
        ("lugar_hecho", "b8_lugar_hecho"),
        ("l_apre", "b8_lugar_aprehension"),
        ("lugar_aprehension", "b8_lugar_aprehension"),
        ("relato", "b8_relato_base"),
        ("relato_circunstanciado", "b8_relato_base")
    ]
    if isinstance(posibles, dict):
        for origen, dest in pares:
            if origen in posibles and posibles[origen] not in (None, "") and not st.session_state.get(dest):
                st.session_state[dest] = str(posibles[origen])


def importar_bloque3(data):
    extraer_autor_y_actuacion(data)
    agregar_bloque_recibido("BLOQUE 3 — Víctima/Damnificado")

    db = data.get("datos_bloque", {}) if isinstance(data, dict) else {}
    if not isinstance(db, dict):
        db = {}

    ident = db.get("identificacion_victima") or data.get("identificacion_victima", {}) if isinstance(data, dict) else {}
    if not isinstance(ident, dict):
        ident = {}

    apellido = ident.get("apellido", "")
    nombre = ident.get("nombre", "") or ident.get("nombres", "")
    nombre_completo = ident.get("nombre_completo", "") or compactar_espacios(f"{apellido} {nombre}")
    dni = ident.get("dni", "") or ident.get("documento", "")
    domicilio = ident.get("domicilio", "")
    telefono = ident.get("telefono", "") or ident.get("celular", "")

    noticia = db.get("noticia_criminis", "") or data.get("noticia_criminis", "") if isinstance(data, dict) else ""
    relato_final = db.get("relato_final", "") or data.get("relato_final", "") if isinstance(data, dict) else ""
    relato_crudo = db.get("relato_crudo", "") or data.get("relato_crudo", "") if isinstance(data, dict) else ""

    if not noticia:
        noticia = " ".join(buscar_valores(data, ["noticia_criminis", "super_resumen"])[:1])
    if not relato_final:
        relato_final = " ".join(buscar_valores(data, ["relato_final"])[:1])
    if not relato_crudo:
        relato_crudo = " ".join(buscar_valores(data, ["relato_crudo", "relato"])[:1])

    if nombre_completo or noticia or relato_final or relato_crudo:
        item = {
            "nombre": nombre_completo,
            "dni": dni,
            "domicilio": domicilio,
            "telefono": telefono,
            "noticia_criminis": noticia,
            "relato_final": relato_final,
            "relato_crudo": relato_crudo,
            "incorporar": True,
            "origen": "BLOQUE 3"
        }
        st.session_state.b8_victimas.append(item)


def importar_bloque2(data):
    extraer_autor_y_actuacion(data)
    agregar_bloque_recibido("BLOQUE 2 — Arrestado/Aprehendido")

    arrestados = []
    if isinstance(data, dict):
        if isinstance(data.get("arrestados"), list):
            arrestados = data.get("arrestados")
        elif isinstance(data.get("datos_bloque"), dict) and isinstance(data["datos_bloque"].get("arrestados"), list):
            arrestados = data["datos_bloque"].get("arrestados")
        elif isinstance(data.get("datos_bloque"), dict):
            db = data["datos_bloque"]
            if db.get("identificacion_arrestado"):
                arrestados = [db.get("identificacion_arrestado")]

    if not arrestados:
        nombres = buscar_valores(data, ["nombre"])
        apellidos = buscar_valores(data, ["apellido"])
        dnis = buscar_valores(data, ["dni"])
        if nombres or apellidos or dnis:
            arrestados = [{"nombre": nombres[0] if nombres else "", "apellido": apellidos[0] if apellidos else "", "dni": dnis[0] if dnis else ""}]

    for a in arrestados:
        if not isinstance(a, dict):
            continue
        nombre = compactar_espacios(f"{a.get('apellido','')} {a.get('nombre','')}") or a.get("nombre_completo", "")
        item = {
            "nombre": nombre,
            "dni": a.get("dni", ""),
            "domicilio": a.get("domicilio", ""),
            "consulta_911": a.get("resultado_911", "") or a.get("consulta_911", ""),
            "cuij": a.get("cuij", ""),
            "caratula": a.get("caratula", ""),
            "autoridad": a.get("autoridad", ""),
            "lesiones": a.get("lesiones", ""),
            "detalle_lesiones": a.get("detalle_lesiones", ""),
            "atencion": a.get("atencion", ""),
            "hospital": a.get("hospital", ""),
            "medico": a.get("medico", ""),
            "diagnostico": a.get("diagnostico", ""),
            "resultado_medico": a.get("resultado", ""),
            "derechos": a.get("derechos", ""),
            "comunicacion": a.get("comunicacion", ""),
            "incorporar": True,
            "origen": "BLOQUE 2"
        }
        st.session_state.b8_arrestados.append(item)


def importar_bloque6(data):
    extraer_autor_y_actuacion(data)
    agregar_bloque_recibido("BLOQUE 6 — Inspección Ocular")

    datos = data.get("datos", {}) if isinstance(data, dict) else {}
    db = data.get("datos_bloque", {}) if isinstance(data, dict) else {}
    if not isinstance(datos, dict):
        datos = {}
    if not isinstance(db, dict):
        db = {}

    resumen = data.get("resumen_para_acta_procedimiento", "") if isinstance(data, dict) else ""
    relato = datos.get("relato_inspeccion", "") or db.get("relato", "") or db.get("relato_inspeccion", "")
    lugar = datos.get("lugar", "") or db.get("lugar", "") or db.get("lugar_inspeccion", "")
    preservado = datos.get("preservado", "") or db.get("preservado", "")
    camaras = data.get("camaras", []) if isinstance(data, dict) else []
    resumen_camaras = data.get("resumen_camaras", []) if isinstance(data, dict) else []

    if not resumen:
        resumen = relato
    if not resumen:
        vals = buscar_valores(data, ["resumen", "relato", "inspeccion", "inspección"])
        resumen = vals[0] if vals else ""

    st.session_state.b8_inspeccion = {
        "lugar": lugar,
        "preservado": preservado,
        "resumen": resumen,
        "relato": relato,
        "incorporar": True,
        "origen": "BLOQUE 6"
    }

    if isinstance(camaras, list):
        for cam in camaras:
            if isinstance(cam, dict):
                st.session_state.b8_camaras.append({
                    "tipo": cam.get("tipo", ""),
                    "ubicacion": cam.get("ubicacion", ""),
                    "orientacion": cam.get("orientacion", ""),
                    "observaciones": cam.get("observaciones", ""),
                    "incorporar": True
                })
    elif isinstance(resumen_camaras, list):
        for txt in resumen_camaras:
            st.session_state.b8_camaras.append({"tipo": "", "ubicacion": str(txt), "orientacion": "", "observaciones": "", "incorporar": True})


def importar_bloque7(data):
    extraer_autor_y_actuacion(data)
    agregar_bloque_recibido("BLOQUE 7 — Secuestros")

    elementos = []
    if isinstance(data, dict):
        for clave in ["elementos", "elementos_secuestrados", "secuestros"]:
            if isinstance(data.get(clave), list):
                elementos = data.get(clave)
                break
        if not elementos and isinstance(data.get("datos_bloque"), dict):
            db = data["datos_bloque"]
            for clave in ["elementos", "elementos_secuestrados", "secuestros"]:
                if isinstance(db.get(clave), list):
                    elementos = db.get(clave)
                    break

    if not elementos:
        vals = buscar_valores(data, ["descripcion", "descripción", "elemento", "secuestro"])
        elementos = [{"descripcion": v} for v in lista_unica(vals[:10])]

    for e in elementos:
        if isinstance(e, dict):
            desc = e.get("descripcion", "") or e.get("detalle", "") or e.get("elemento", "") or str(e)
            item = {
                "descripcion": desc,
                "lugar_hallazgo": e.get("lugar_hallazgo", "") or e.get("hallazgo", ""),
                "deposito": e.get("deposito", "") or e.get("depósito", "") or e.get("resguardo", ""),
                "testigo": e.get("testigo", ""),
                "incorporar": True,
                "origen": "BLOQUE 7"
            }
        else:
            item = {"descripcion": str(e), "lugar_hallazgo": "", "deposito": "", "testigo": "", "incorporar": True, "origen": "BLOQUE 7"}
        if compactar_espacios(item["descripcion"]):
            st.session_state.b8_elementos.append(item)


def importar_json(data, bloque):
    st.session_state.b8_json_importados.append({
        "bloque": bloque,
        "fecha_importacion": datetime.now().isoformat(),
        "data": data
    })

    if bloque.startswith("BLOQUE 1"):
        importar_bloque1(data)
    elif bloque.startswith("BLOQUE 2"):
        importar_bloque2(data)
    elif bloque.startswith("BLOQUE 3"):
        importar_bloque3(data)
    elif bloque.startswith("BLOQUE 6"):
        importar_bloque6(data)
    elif bloque.startswith("BLOQUE 7"):
        importar_bloque7(data)
    else:
        agregar_bloque_recibido(bloque)
        vals = buscar_valores(data, ["resumen", "relato", "descripcion", "descripción"])
        st.session_state.b8_notas_importadas.append(vals[0] if vals else json.dumps(data, ensure_ascii=False)[:500])

# =====================================================
# FORMULARIOS EDITABLES
# =====================================================

def input_key_default(key, default=""):
    if key not in st.session_state:
        st.session_state[key] = default


def editar_victimas():
    st.markdown("### Víctimas / damnificados importados")
    if not st.session_state.b8_victimas:
        st.info("Sin víctimas importadas.")
        return
    nuevas = []
    for i, v in enumerate(st.session_state.b8_victimas):
        with st.expander(f"Víctima {i+1}: {v.get('nombre','Sin nombre')}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre y apellido", value=v.get("nombre", ""), key=f"b8_vic_{i}_nombre")
                dni = st.text_input("DNI", value=v.get("dni", ""), key=f"b8_vic_{i}_dni")
                domicilio = st.text_input("Domicilio", value=v.get("domicilio", ""), key=f"b8_vic_{i}_dom")
                telefono = st.text_input("Teléfono", value=v.get("telefono", ""), key=f"b8_vic_{i}_tel")
            with c2:
                incorporar = st.checkbox("Incorporar al Acta de Procedimiento", value=v.get("incorporar", True), key=f"b8_vic_{i}_inc")
                noticia = st.text_area("Noticia criminis / resumen para acta", value=v.get("noticia_criminis", ""), height=160, key=f"b8_vic_{i}_noticia")
                relato = st.text_area("Relato final / referencia", value=v.get("relato_final", "") or v.get("relato_crudo", ""), height=120, key=f"b8_vic_{i}_relato")
            nuevas.append({"nombre": nombre, "dni": dni, "domicilio": domicilio, "telefono": telefono, "noticia_criminis": noticia, "relato_final": relato, "relato_crudo": v.get("relato_crudo", ""), "incorporar": incorporar, "origen": v.get("origen", "BLOQUE 3")})
    st.session_state.b8_victimas = nuevas


def editar_arrestados():
    st.markdown("### Arrestados / aprehendidos importados")
    if not st.session_state.b8_arrestados:
        st.info("Sin arrestados importados.")
        return
    nuevos = []
    for i, a in enumerate(st.session_state.b8_arrestados):
        with st.expander(f"Arrestado {i+1}: {a.get('nombre','Sin nombre')}", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre y apellido", value=a.get("nombre", ""), key=f"b8_arr_{i}_nombre")
                dni = st.text_input("DNI", value=a.get("dni", ""), key=f"b8_arr_{i}_dni")
                domicilio = st.text_input("Domicilio", value=a.get("domicilio", ""), key=f"b8_arr_{i}_dom")
                consulta = st.text_area("Consulta 911 / pedido de captura", value=a.get("consulta_911", ""), height=80, key=f"b8_arr_{i}_911")
                derechos = st.text_input("Lectura de derechos", value=a.get("derechos", ""), key=f"b8_arr_{i}_der")
            with c2:
                incorporar = st.checkbox("Incorporar al Acta de Procedimiento", value=a.get("incorporar", True), key=f"b8_arr_{i}_inc")
                lesiones = st.text_area("Lesiones visibles", value=a.get("detalle_lesiones", "") or a.get("lesiones", ""), height=90, key=f"b8_arr_{i}_les")
                atencion = st.text_area("Asistencia médica / hospital / diagnóstico", value=compactar_espacios(f"{a.get('atencion','')} {a.get('hospital','')} {a.get('medico','')} {a.get('diagnostico','')} {a.get('resultado_medico','')}"), height=90, key=f"b8_arr_{i}_aten")
            nuevos.append({"nombre": nombre, "dni": dni, "domicilio": domicilio, "consulta_911": consulta, "derechos": derechos, "detalle_lesiones": lesiones, "asistencia_medica": atencion, "incorporar": incorporar, "origen": a.get("origen", "BLOQUE 2")})
    st.session_state.b8_arrestados = nuevos


def editar_elementos():
    st.markdown("### Elementos / secuestros importados")
    if not st.session_state.b8_elementos:
        st.info("Sin elementos importados.")
        return
    nuevos = []
    for i, e in enumerate(st.session_state.b8_elementos):
        with st.expander(f"Elemento {i+1}: {e.get('descripcion','Sin descripción')[:60]}", expanded=True):
            descripcion = st.text_area("Descripción", value=e.get("descripcion", ""), height=90, key=f"b8_el_{i}_desc")
            c1, c2, c3 = st.columns(3)
            with c1:
                lugar = st.text_input("Lugar de hallazgo", value=e.get("lugar_hallazgo", ""), key=f"b8_el_{i}_lug")
            with c2:
                deposito = st.text_input("Depósito / resguardo", value=e.get("deposito", ""), key=f"b8_el_{i}_dep")
            with c3:
                incorporar = st.checkbox("Incorporar", value=e.get("incorporar", True), key=f"b8_el_{i}_inc")
            nuevos.append({"descripcion": descripcion, "lugar_hallazgo": lugar, "deposito": deposito, "testigo": e.get("testigo", ""), "incorporar": incorporar, "origen": e.get("origen", "BLOQUE 7")})
    st.session_state.b8_elementos = nuevos


def editar_inspeccion():
    st.markdown("### Inspección ocular / cámaras")
    ins = st.session_state.b8_inspeccion if isinstance(st.session_state.b8_inspeccion, dict) else {}
    if not ins and not st.session_state.b8_camaras:
        st.info("Sin inspección/cámaras importadas.")
        return
    c1, c2 = st.columns(2)
    with c1:
        lugar = st.text_input("Lugar inspeccionado", value=ins.get("lugar", ""), key="b8_ins_lugar")
        preservado = st.text_input("Preservación del lugar", value=ins.get("preservado", ""), key="b8_ins_pres")
        incorporar = st.checkbox("Incorporar resumen de inspección al acta", value=ins.get("incorporar", True), key="b8_ins_inc")
    with c2:
        resumen = st.text_area("Resumen de inspección ocular para acta", value=ins.get("resumen", "") or ins.get("relato", ""), height=170, key="b8_ins_resumen")
    st.session_state.b8_inspeccion = {"lugar": lugar, "preservado": preservado, "resumen": resumen, "incorporar": incorporar, "origen": ins.get("origen", "BLOQUE 6")}

    if st.session_state.b8_camaras:
        nuevas = []
        st.markdown("#### Cámaras relevadas")
        for i, cam in enumerate(st.session_state.b8_camaras):
            with st.expander(f"Cámara {i+1}: {cam.get('ubicacion','Sin ubicación')[:60]}"):
                ubicacion = st.text_input("Ubicación", value=cam.get("ubicacion", ""), key=f"b8_cam_{i}_ubi")
                orientacion = st.text_area("Orientación / cobertura", value=cam.get("orientacion", ""), height=80, key=f"b8_cam_{i}_ori")
                tipo = st.text_input("Tipo", value=cam.get("tipo", ""), key=f"b8_cam_{i}_tipo")
                incorporar_cam = st.checkbox("Incorporar", value=cam.get("incorporar", True), key=f"b8_cam_{i}_inc")
                nuevas.append({"tipo": tipo, "ubicacion": ubicacion, "orientacion": orientacion, "observaciones": cam.get("observaciones", ""), "incorporar": incorporar_cam})
        st.session_state.b8_camaras = nuevas

# =====================================================
# ACTA
# =====================================================

def construir_acta():
    fecha = st.session_state.b8_fecha
    if isinstance(fecha, date):
        fecha_txt = fecha.strftime("%d/%m/%Y")
    else:
        fecha_txt = str(fecha)

    partes = []
    encabezado = (
        f"En la ciudad de Rosario, Departamento homónimo, Provincia de Santa Fe, "
        f"siendo las {st.session_state.b8_hora_inicio} horas del día {fecha_txt}, "
        f"personal policial de {st.session_state.b8_dependencia or 'la dependencia interviniente'}, "
        f"móvil {st.session_state.b8_movil or 'S/D'}, en momentos en que se encontraba recorriendo la jurisdicción "
        f"en prevención de delitos y contravenciones, procede a labrar la presente Acta de Procedimiento."
    )
    if st.session_state.b8_numero_acta:
        encabezado += f" Actuaciones identificadas bajo Nro. {st.session_state.b8_numero_acta}."
    if st.session_state.b8_incidencia:
        encabezado += f" Incidencia: {st.session_state.b8_incidencia}."
    partes.append(encabezado)

    if st.session_state.b8_lugar_hecho:
        partes.append(f"Se deja constancia que el lugar del hecho/intervención se ubica en {st.session_state.b8_lugar_hecho}.")

    if st.session_state.b8_relato_base.strip():
        partes.append(st.session_state.b8_relato_base.strip())

    # Victimas / noticia criminis
    for v in st.session_state.b8_victimas:
        if not v.get("incorporar", True):
            continue
        noticia = compactar_espacios(v.get("noticia_criminis", ""))
        nombre = compactar_espacios(v.get("nombre", ""))
        dni = compactar_espacios(v.get("dni", ""))
        if noticia:
            partes.append(noticia)
        elif nombre:
            txt = f"Seguidamente se entrevista a quien dijo llamarse {nombre}"
            if dni:
                txt += f", DNI Nro. {dni}"
            relato = compactar_espacios(v.get("relato_final", "") or v.get("relato_crudo", ""))
            if relato:
                txt += f", quien manifestó que {relato}"
            txt += "."
            partes.append(txt)

    # Arrestados
    for a in st.session_state.b8_arrestados:
        if not a.get("incorporar", True):
            continue
        nombre = compactar_espacios(a.get("nombre", ""))
        dni = compactar_espacios(a.get("dni", ""))
        if nombre:
            txt = f"Acto seguido, se procede a la identificación y aprehensión de {nombre}"
            if dni:
                txt += f", DNI Nro. {dni}"
            if st.session_state.b8_lugar_aprehension:
                txt += f", en {st.session_state.b8_lugar_aprehension}"
            txt += "."
            partes.append(txt)
        if a.get("consulta_911"):
            partes.append(f"Consultado el sistema correspondiente, respecto del aprehendido se informa: {a.get('consulta_911')}.")
        if a.get("derechos"):
            partes.append(f"Se deja constancia de la lectura de derechos al aprehendido: {a.get('derechos')}.")
        lesiones = compactar_espacios(a.get("detalle_lesiones", ""))
        atencion = compactar_espacios(a.get("asistencia_medica", ""))
        if lesiones or atencion:
            partes.append(f"Asimismo, respecto del estado físico del aprehendido, se hace constar: {lesiones}. {atencion}".strip())

    # Secuestros
    elementos_txt = []
    for e in st.session_state.b8_elementos:
        if e.get("incorporar", True) and compactar_espacios(e.get("descripcion", "")):
            item = compactar_espacios(e.get("descripcion"))
            if e.get("lugar_hallazgo"):
                item += f" (hallado en {e.get('lugar_hallazgo')})"
            if e.get("deposito"):
                item += f" (depósito/resguardo: {e.get('deposito')})"
            elementos_txt.append(item)
    if elementos_txt:
        partes.append("Se procede al secuestro de los siguientes elementos: " + "; ".join(elementos_txt) + ".")

    # Inspeccion
    ins = st.session_state.b8_inspeccion if isinstance(st.session_state.b8_inspeccion, dict) else {}
    if ins.get("incorporar", True) and compactar_espacios(ins.get("resumen", "")):
        partes.append("Se realizó inspección ocular en el lugar, dejándose constancia de lo siguiente: " + compactar_espacios(ins.get("resumen")) + ".")
    if st.session_state.b8_camaras:
        cam_txt = []
        for cam in st.session_state.b8_camaras:
            if cam.get("incorporar", True):
                linea = compactar_espacios(f"{cam.get('tipo','')} ubicada en {cam.get('ubicacion','')}, orientada/captando {cam.get('orientacion','')}")
                if linea:
                    cam_txt.append(linea)
        if cam_txt:
            partes.append("Asimismo, se efectuó relevamiento de cámaras: " + "; ".join(cam_txt) + ".")

    # Fiscalia / cierre
    if st.session_state.b8_intervencion_fiscal or st.session_state.b8_disposiciones:
        partes.append(f"Se dio conocimiento a la autoridad competente/Mesa de Enlace, informándose: {st.session_state.b8_intervencion_fiscal}. Disposiciones: {st.session_state.b8_disposiciones}.")

    cierre = "No siendo para más, se da por finalizada la presente acta"
    if st.session_state.b8_hora_cierre:
        cierre += f", siendo las {st.session_state.b8_hora_cierre} horas"
    cierre += ", previa lectura y ratificación de su contenido, firmando al pie el personal actuante para constancia."
    if st.session_state.b8_observaciones_cierre:
        cierre += " Observaciones: " + st.session_state.b8_observaciones_cierre
    partes.append(cierre)

    return "\n\n".join([p for p in partes if compactar_espacios(p)])


class PDFActa(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 7, limpiar_pdf("POLICIA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
        self.set_font("Arial", "", 10)
        self.cell(0, 6, limpiar_pdf(st.session_state.get("b8_unidad_regional", "UR II - ROSARIO")), ln=True, align="C")
        self.set_font("Arial", "B", 13)
        self.cell(0, 9, limpiar_pdf("ACTA DE PROCEDIMIENTO"), ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 8, limpiar_pdf("S.I.V.A.P. - Sistema Integrado de Validacion de Actuaciones Policiales"), align="C")


def generar_pdf_acta(texto):
    pdf = PDFActa()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Arial", "", 11)

    for parrafo in limpiar_pdf(texto).split("\n"):
        if not parrafo.strip():
            pdf.ln(3)
        else:
            pdf.set_x(18)
            pdf.multi_cell(0, 7, parrafo, align="J")

    pdf.ln(18)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma personal actuante", ln=False, align="C")
    pdf.cell(85, 6, "Aclaracion / sello", ln=True, align="C")
    return pdf_bytes(pdf)


def armar_json_consolidado(acta_texto):
    data = {
        "sistema": "S.I.V.A.P.",
        "tipo_archivo": "acta_procedimiento_consolidada",
        "actuacion": {
            "numero_acta": st.session_state.b8_numero_acta,
            "fecha": str(st.session_state.b8_fecha),
            "hora_inicio": st.session_state.b8_hora_inicio,
            "hora_cierre": st.session_state.b8_hora_cierre,
            "dependencia": st.session_state.b8_dependencia,
            "unidad_regional": st.session_state.b8_unidad_regional,
            "movil": st.session_state.b8_movil,
            "personal_actante": st.session_state.b8_personal_actante,
            "personal_interviniente": st.session_state.b8_personal_interviniente,
            "lugar_hecho": st.session_state.b8_lugar_hecho,
            "lugar_aprehension": st.session_state.b8_lugar_aprehension,
            "incidencia": st.session_state.b8_incidencia
        },
        "bloques_recibidos": st.session_state.b8_bloques_recibidos,
        "victimas": st.session_state.b8_victimas,
        "arrestados": st.session_state.b8_arrestados,
        "elementos": st.session_state.b8_elementos,
        "inspeccion": st.session_state.b8_inspeccion,
        "camaras": st.session_state.b8_camaras,
        "acta_procedimiento": acta_texto,
        "fecha_consolidacion": datetime.now().isoformat()
    }
    return json.dumps(data, ensure_ascii=False, indent=4)

# =====================================================
# INTERFAZ
# =====================================================

st.title("🚓 BLOQUE 8 — Consolidador del Acta de Procedimiento")
st.caption("Subí los JSON recibidos por WhatsApp, corregí los datos de campo y generá el Acta de Procedimiento.")

tabs = st.tabs(["Actuación", "Importar JSON", "Datos recibidos", "Acta de Procedimiento", "Descargar"])

with tabs[0]:
    st.subheader("Actuación activa")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Nro. de acta / procedimiento", key="b8_numero_acta")
        st.date_input("Fecha", key="b8_fecha")
        st.text_input("Hora inicio", key="b8_hora_inicio")
        st.text_input("Hora cierre", key="b8_hora_cierre")
    with c2:
        st.text_input("Unidad Regional", key="b8_unidad_regional")
        st.text_input("Dependencia", key="b8_dependencia")
        st.text_input("Móvil", key="b8_movil")
        st.text_input("Incidencia", key="b8_incidencia")
    with c3:
        st.text_area("Personal actante", key="b8_personal_actante", height=80)
        st.text_area("Personal interviniente", key="b8_personal_interviniente", height=80)
    st.text_input("Lugar del hecho", key="b8_lugar_hecho")
    st.text_input("Lugar de aprehensión", key="b8_lugar_aprehension")
    st.text_area("Relato base / comisión inicial / circunstancias generales", key="b8_relato_base", height=180)
    st.text_area("Intervención fiscal / Mesa de Enlace", key="b8_intervencion_fiscal", height=80)
    st.text_area("Disposiciones recibidas", key="b8_disposiciones", height=80)
    st.text_area("Observaciones de cierre", key="b8_observaciones_cierre", height=80)

with tabs[1]:
    st.subheader("📥 Importar JSON recibidos por WhatsApp")
    st.info("Cargue uno o varios archivos JSON enviados por colaboradores. Antes de incorporarlos puede confirmar o corregir el bloque detectado.")
    archivos = st.file_uploader("Subir JSON", type=["json"], accept_multiple_files=True, key="b8_uploader_json")

    if archivos:
        st.markdown("### Archivos detectados")
        datos_pendientes = []
        for idx, archivo in enumerate(archivos):
            try:
                data = json.load(archivo)
                sugerido = detectar_bloque(data)
                st.success(f"{archivo.name}: leído correctamente. Sugerido: {sugerido}")
                bloque_confirmado = autodetectar_o_corregir_bloque(data, sugerido, f"b8_confirmar_bloque_{idx}_{archivo.name}")
                with st.expander(f"Vista previa {archivo.name}"):
                    st.json(data)
                datos_pendientes.append((data, bloque_confirmado, archivo.name))
            except Exception as e:
                st.error(f"No se pudo leer {archivo.name}: {e}")

        if datos_pendientes:
            if st.button("✅ Incorporar JSON a campos editables", use_container_width=True):
                for data, bloque, nombre_archivo in datos_pendientes:
                    importar_json(data, bloque)
                st.success("JSON incorporados. Revise la pestaña 'Datos recibidos' para corregir el trabajo de campo.")
                st.rerun()
    else:
        st.warning("Todavía no se cargaron JSON.")

with tabs[2]:
    st.subheader("Datos importantes recibidos y editables")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("JSON cargados", len(st.session_state.b8_json_importados))
    m2.metric("Víctimas", len(st.session_state.b8_victimas))
    m3.metric("Arrestados", len(st.session_state.b8_arrestados))
    m4.metric("Elementos", len(st.session_state.b8_elementos))

    st.markdown("### Bloques recibidos")
    if st.session_state.b8_bloques_recibidos:
        for b in st.session_state.b8_bloques_recibidos:
            st.success(b)
    else:
        st.info("Sin bloques recibidos.")

    st.divider()
    editar_victimas()
    st.divider()
    editar_arrestados()
    st.divider()
    editar_elementos()
    st.divider()
    editar_inspeccion()

with tabs[3]:
    st.subheader("Acta de Procedimiento")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚓 Generar / actualizar Acta de Procedimiento", use_container_width=True):
            st.session_state.b8_relato_final_acta = construir_acta()
            st.success("Acta generada con los datos consolidados y corregidos.")
    with c2:
        if st.button("🧹 Limpiar solo el texto del acta generada", use_container_width=True):
            st.session_state.b8_relato_final_acta = ""
            st.rerun()

    st.text_area("Texto final editable del Acta de Procedimiento", key="b8_relato_final_acta", height=520)

with tabs[4]:
    st.subheader("Descargar actuación final")
    acta = st.session_state.b8_relato_final_acta
    if not acta.strip():
        st.warning("Primero genere el Acta de Procedimiento en la pestaña anterior.")
    else:
        pdf_data = generar_pdf_acta(acta)
        json_data = armar_json_consolidado(acta)
        base = normalizar_nombre_archivo(f"SIVAP_ACTA_{st.session_state.b8_numero_acta or 'SIN_NUMERO'}")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("📄 Descargar PDF Acta de Procedimiento", data=pdf_data, file_name=f"{base}_ACTA_PROCEDIMIENTO.pdf", mime="application/pdf", use_container_width=True)
        with c2:
            st.download_button("📝 Descargar TXT editable", data=acta, file_name=f"{base}_ACTA_PROCEDIMIENTO.txt", mime="text/plain", use_container_width=True)
        with c3:
            st.download_button("📦 Descargar JSON consolidado", data=json_data, file_name=f"{base}_CONSOLIDADO.json", mime="application/json", use_container_width=True)

        with st.expander("Vista del JSON consolidado"):
            st.code(json_data, language="json")

try:
    if GUARDADO_DISPONIBLE:
        autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
