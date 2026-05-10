import streamlit as st
import json
import base64
import io
import os
import re
import tempfile
from datetime import datetime, date
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_OK = True
except Exception:
    CANVAS_OK = False

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_OK = True
except Exception:
    GUARDADO_OK = False

# =====================================================
# S.I.V.A.P. - BLOQUE 3
# ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO
# Version corregida:
# - Importar JSON dentro del mismo BLOQUE 3
# - Guia dinamica por delito/situacion
# - Sin resguardo/no contaminacion del testimonio
# - Sin campos visibles de derechos de la victima
# - PDF unico: hoja 1 Acta de Entrevista, hoja 2 Derechos de la Victima
# - Relato final en primera persona / dichos de la entrevistada
# =====================================================

st.set_page_config(page_title="S.I.V.A.P. - BLOQUE 3 Entrevista", layout="wide", page_icon="🗣️")

BLOQUE_ID = "BLOQUE_3_ENTREVISTA"
if GUARDADO_OK:
    try:
        iniciar_guardado_seguro(BLOQUE_ID)
        panel_guardado_seguro(BLOQUE_ID)
    except Exception:
        pass

LEMA = "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora."

# =====================================================
# ESTADO
# =====================================================

DEFAULTS = {
    # actuacion / contexto
    "b3_numero_acta": "",
    "b3_fecha_entrevista": date.today(),
    "b3_hora_entrevista": datetime.now().strftime("%H:%M"),
    "b3_lugar_entrevista": "Rosario",
    "b3_dependencia_acta": "",
    "b3_personal_actuante": "",

    # identidad policial si no viene de app
    "b3_ni_policial": "",
    "b3_nombre_policial": "",
    "b3_jerarquia": "",
    "b3_dependencia_policial": "",
    "b3_rol_operativo": "Actante",

    # identificacion victima
    "b3_condicion": "Víctima/Damnificado",
    "b3_apellido": "",
    "b3_nombre": "",
    "b3_dni": "",
    "b3_edad": "",
    "b3_fecha_nacimiento": "",
    "b3_nacionalidad": "Argentina",
    "b3_estado_civil": "",
    "b3_profesion": "",
    "b3_domicilio": "",
    "b3_telefono": "",
    "b3_celular": "",
    "b3_correo": "",

    # relato
    "b3_relato_crudo": "",
    "b3_situaciones_confirmadas": [],
    "b3_situacion_otro": "",

    # guia dinamica - amenazas
    "b3_amenaza_frase": "",
    "b3_amenaza_medio": "",
    "b3_amenaza_temor": "",
    "b3_amenaza_vinculo": "",
    "b3_amenaza_evidencia": "",

    # lesiones
    "b3_lesion_mecanica": "",
    "b3_lesion_zona": "",
    "b3_lesion_asistencia": "",
    "b3_lesion_certificado": "",
    "b3_lesion_instancia": "",

    # robo / hurto
    "b3_robo_elementos": "",
    "b3_robo_modo": "",
    "b3_robo_arma": "",
    "b3_robo_intimidacion": "",
    "b3_robo_recupero": "",
    "b3_robo_elemento_reconocido": "",

    # descripcion objetiva del autor / aprehension vinculada
    "b3_autor_descripcion": "",
    "b3_autor_vestimenta_rasgos": "",
    "b3_autor_direccion": "",
    "b3_autor_conoce": "",
    "b3_autor_individualizacion": "",

    # daño / violencia / evidencia / otro
    "b3_danio_detalle": "",
    "b3_violencia_contexto": "",
    "b3_evidencia_detalle": "",
    "b3_otro_detalle": "",

    # productos
    "b3_relato_final": "",
    "b3_noticia_criminis": "",

    # firma digital directa en pantalla
    "b3_modo_firma": "Firma digital en pantalla",
    "b3_firma_canvas_b64": "",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# UTILIDADES
# =====================================================

def val(k, default=""):
    return st.session_state.get(k, default)


def setv(k, v):
    st.session_state[k] = v


def limpiar_pdf(txt):
    if txt is None:
        return ""
    txt = str(txt)
    rep = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "°": "Nro.",
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-", "•": "-", "…": "...",
        "✅": "", "⚠️": "", "🚓": "", "📄": "", "📥": "", "📤": ""
    }
    for a, b in rep.items():
        txt = txt.replace(a, b)
    return txt.encode("latin-1", "replace").decode("latin-1")


def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1", errors="replace")
    return bytes(out)


def pdf_multi(pdf, texto, alto=6):
    pdf.set_x(pdf.l_margin)
    ancho = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(ancho, alto, limpiar_pdf(texto), align="J")
    pdf.set_x(pdf.l_margin)


def normalizar_texto(t):
    t = (t or "").lower()
    return t


def detectar_situaciones(relato):
    t = normalizar_texto(relato)
    detectadas = []

    if any(x in t for x in ["amenaz", "te voy a matar", "muerte", "intimid", "amedrent"]):
        detectadas.append("Amenazas")
    if any(x in t for x in ["golpe", "lesion", "lesión", "herida", "sangre", "escori", "hospital", "medico", "médico", "certificado", "politraumat"]):
        detectadas.append("Lesiones")
    if any(x in t for x in ["robo", "robó", "robar", "sustra", "arrebat", "celular", "cuchillo", "arma", "pistola", "revolver", "revólver"]):
        if any(x in t for x in ["cuchillo", "arma", "pistola", "revolver", "revólver"]):
            detectadas.append("Robo con arma")
        else:
            detectadas.append("Robo / sustracción")
    if any(x in t for x in ["hurto", "faltante", "sin ejercer violencia"]):
        detectadas.append("Hurto")
    if any(x in t for x in ["daño", "dano", "romp", "rotura", "vidrio", "puerta"]):
        detectadas.append("Daño")
    if any(x in t for x in ["pareja", "ex pareja", "familia", "violencia de genero", "violencia de género", "conviviente"]):
        detectadas.append("Violencia familiar / contexto familiar")
    if any(x in t for x in ["aprehendid", "arrestad", "retenid", "reducid", "demorad", "transeunte", "transeúnte"]):
        detectadas.append("Aprehensión / retención vinculada")
    if any(x in t for x in ["camara", "cámara", "testigo", "captura", "video", "filmacion", "filmación"]):
        detectadas.append("Cámaras / testigos / evidencia")

    return list(dict.fromkeys(detectadas))


OPCIONES_SITUACIONES = [
    "Amenazas",
    "Lesiones",
    "Robo con arma",
    "Robo / sustracción",
    "Hurto",
    "Daño",
    "Violencia familiar / contexto familiar",
    "Aprehensión / retención vinculada",
    "Cámaras / testigos / evidencia",
    "Otro",
]


def normalizar_situacion(s):
    """Convierte etiquetas viejas o importadas a las opciones actuales del multiselect."""
    if s is None:
        return ""
    original = str(s).strip()
    t = original.lower()

    # Compatibilidad con versiones anteriores del BLOQUE 3.
    if t in ["robo / robo con arma", "robo con arma / robo", "robo agravado"]:
        return "Robo con arma"
    if "robo" in t and "arma" in t:
        return "Robo con arma"
    if "robo" in t or "sustra" in t or "arrebato" in t:
        return "Robo / sustracción"
    if "hurto" in t:
        return "Hurto"
    if "amenaz" in t:
        return "Amenazas"
    if "lesion" in t or "lesión" in t:
        return "Lesiones"
    if "dañ" in t or "dano" in t:
        return "Daño"
    if "violencia" in t or "familiar" in t or "genero" in t or "género" in t:
        return "Violencia familiar / contexto familiar"
    if "apreh" in t or "reten" in t or "arrest" in t or "demor" in t or "reduc" in t:
        return "Aprehensión / retención vinculada"
    if "camara" in t or "cámara" in t or "testigo" in t or "video" in t or "film" in t or "captura" in t:
        return "Cámaras / testigos / evidencia"
    if "otro" in t:
        return "Otro"

    return original if original in OPCIONES_SITUACIONES else "Otro"


def normalizar_lista_situaciones(situaciones):
    if not situaciones:
        return []
    if isinstance(situaciones, str):
        situaciones = [situaciones]
    salida = []
    for s in situaciones:
        ns = normalizar_situacion(s)
        if ns in OPCIONES_SITUACIONES and ns not in salida:
            salida.append(ns)
    return salida


def es_json_bloque3(data):
    txt = json.dumps(data, ensure_ascii=False).lower()
    estructural = " ".join([
        str(data.get("bloque", "")) if isinstance(data, dict) else "",
        str(data.get("modulo", "")) if isinstance(data, dict) else "",
        str(data.get("tipo_archivo", "")) if isinstance(data, dict) else "",
    ]).lower()
    if "bloque_3" in estructural or "bloque 3" in estructural or "entrevista" in estructural or "victima" in estructural or "víctima" in estructural:
        return True
    return any(x in txt for x in ["identificacion_victima", "noticia_criminis", "relato_final", "derechos_victima"])


def get_nested(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def primer_dict_existente(data, rutas):
    for ruta in rutas:
        v = get_nested(data, ruta, None)
        if isinstance(v, dict):
            return v
    return {}


def primer_valor(data, rutas, default=""):
    for ruta in rutas:
        v = get_nested(data, ruta, None)
        if v not in [None, "", [], {}]:
            return v
    return default


def importar_json_bloque3(data):
    # Soporta versiones anteriores y nuevas.
    datos_bloque = primer_dict_existente(data, [
        ["entrevista"],          # formato simple actual
        ["datos_bloque"],        # compatibilidad con versiones anteriores
        ["datos_entrevista"],    # compatibilidad con versiones anteriores reales exportadas
        ["datos_completos_bloque"],
        ["bloque3"],
        ["datos"],
    ])
    if not datos_bloque and isinstance(data, dict):
        datos_bloque = data

    identidad = primer_dict_existente(data, [["autor_carga"], ["identidad_policial"]])
    actuacion = primer_dict_existente(data, [["actuacion"]])

    victima = primer_dict_existente(datos_bloque, [
        ["identificacion_victima"],
        ["victima"],
        ["filiacion"],
        ["identificacion"],
    ])

    # Actuacion / autor
    if actuacion:
        setv("b3_numero_acta", actuacion.get("numero_acta") or actuacion.get("nro_acta") or val("b3_numero_acta"))
        setv("b3_dependencia_acta", actuacion.get("dependencia") or actuacion.get("reparticion") or val("b3_dependencia_acta"))
        if actuacion.get("fecha"):
            try:
                setv("b3_fecha_entrevista", datetime.fromisoformat(str(actuacion.get("fecha"))).date())
            except Exception:
                pass
    if identidad:
        setv("b3_ni_policial", identidad.get("ni") or identidad.get("NI") or val("b3_ni_policial"))
        setv("b3_nombre_policial", identidad.get("nombre_apellido") or identidad.get("nombre") or val("b3_nombre_policial"))
        setv("b3_jerarquia", identidad.get("jerarquia") or val("b3_jerarquia"))
        setv("b3_dependencia_policial", identidad.get("dependencia") or val("b3_dependencia_policial"))
        setv("b3_rol_operativo", identidad.get("rol_operativo") or val("b3_rol_operativo"))

    # Victima
    if victima:
        setv("b3_condicion", victima.get("condicion") or victima.get("vinculo_hecho") or val("b3_condicion"))
        setv("b3_apellido", victima.get("apellido") or victima.get("apellidos") or val("b3_apellido"))
        setv("b3_nombre", victima.get("nombre") or victima.get("nombres") or val("b3_nombre"))
        # Si viene nombre completo en una sola clave
        completo = victima.get("nombre_completo") or victima.get("nombre_apellido") or ""
        if completo and not (val("b3_apellido") or val("b3_nombre")):
            setv("b3_nombre", completo)
        setv("b3_dni", victima.get("dni") or victima.get("documento") or val("b3_dni"))
        setv("b3_edad", str(victima.get("edad") or val("b3_edad")))
        setv("b3_fecha_nacimiento", victima.get("fecha_nacimiento") or victima.get("nacimiento") or val("b3_fecha_nacimiento"))
        setv("b3_nacionalidad", victima.get("nacionalidad") or val("b3_nacionalidad"))
        setv("b3_estado_civil", victima.get("estado_civil") or val("b3_estado_civil"))
        setv("b3_profesion", victima.get("profesion") or victima.get("ocupacion") or val("b3_profesion"))
        setv("b3_domicilio", victima.get("domicilio") or val("b3_domicilio"))
        setv("b3_telefono", victima.get("telefono") or val("b3_telefono"))
        setv("b3_celular", victima.get("celular") or val("b3_celular"))
        setv("b3_correo", victima.get("correo") or victima.get("email") or val("b3_correo"))

    # Relatos / productos
    setv("b3_relato_crudo", primer_valor(datos_bloque, [["relato_crudo"], ["relato"], ["relato_inicial"]], val("b3_relato_crudo")))
    setv("b3_relato_final", primer_valor(datos_bloque, [["relato_final"], ["texto_final"]], val("b3_relato_final")))
    setv("b3_noticia_criminis", primer_valor(datos_bloque, [["noticia_criminis"], ["resumen_para_acta"], ["resumen_para_acta_procedimiento", "texto_para_acta"]], val("b3_noticia_criminis")))

    # Situaciones: soporta el formato nuevo y el formato anterior real que exportaba datos_entrevista
    analisis = primer_dict_existente(datos_bloque, [["analisis_sivap"], ["analisis"]])
    sit = []
    if analisis:
        sit = analisis.get("situaciones_confirmadas") or analisis.get("situaciones_detectadas") or []
    if not sit:
        sit = datos_bloque.get("situaciones_confirmadas") or datos_bloque.get("situaciones_detectadas") or []
    if isinstance(sit, str):
        sit = [sit]
    if sit:
        setv("b3_situaciones_confirmadas", normalizar_lista_situaciones(sit))

    resp = primer_dict_existente(datos_bloque, [["respuestas_guia"], ["guia"], ["respuestas"]])
    if resp:
        # Importa respuestas si existen con nombres conocidos, incluyendo versiones anteriores.
        amenazas = resp.get("amenazas", {}) if isinstance(resp.get("amenazas", {}), dict) else {}
        lesiones = resp.get("lesiones", {}) if isinstance(resp.get("lesiones", {}), dict) else {}
        robo = resp.get("robo", {}) if isinstance(resp.get("robo", {}), dict) else {}
        autor = {}
        if isinstance(resp.get("persona_sindicada", {}), dict):
            autor = resp.get("persona_sindicada", {})
        elif isinstance(resp.get("descripcion_autor", {}), dict):
            autor = resp.get("descripcion_autor", {})

        setv("b3_amenaza_frase", amenazas.get("frase_textual") or amenazas.get("frase") or val("b3_amenaza_frase"))
        setv("b3_amenaza_medio", amenazas.get("medio") or val("b3_amenaza_medio"))
        setv("b3_amenaza_temor", amenazas.get("amedrentamiento") or amenazas.get("temor_integridad") or amenazas.get("temor") or val("b3_amenaza_temor"))
        setv("b3_amenaza_vinculo", amenazas.get("vinculo_autor") or amenazas.get("vinculo") or val("b3_amenaza_vinculo"))
        setv("b3_amenaza_evidencia", amenazas.get("evidencia") or val("b3_amenaza_evidencia"))

        setv("b3_lesion_mecanica", lesiones.get("mecanica") or lesiones.get("como") or lesiones.get("descripcion_lesiones") or val("b3_lesion_mecanica"))
        setv("b3_lesion_zona", lesiones.get("zona") or val("b3_lesion_zona"))
        setv("b3_lesion_asistencia", lesiones.get("asistencia") or lesiones.get("asistencia_medica") or val("b3_lesion_asistencia"))
        setv("b3_lesion_certificado", lesiones.get("certificado") or val("b3_lesion_certificado"))
        setv("b3_lesion_instancia", lesiones.get("instancia_penal") or lesiones.get("insta_accion_penal") or val("b3_lesion_instancia"))

        setv("b3_robo_elementos", robo.get("elementos") or robo.get("elementos_sustraidos") or val("b3_robo_elementos"))
        setv("b3_robo_modo", robo.get("modo") or robo.get("modo_comision") or val("b3_robo_modo"))
        setv("b3_robo_arma", robo.get("arma") or robo.get("arma_utilizada") or val("b3_robo_arma"))
        setv("b3_robo_intimidacion", robo.get("intimidacion") or val("b3_robo_intimidacion"))
        setv("b3_robo_recupero", robo.get("recupero") or robo.get("recupero_elementos") or val("b3_robo_recupero"))
        setv("b3_robo_elemento_reconocido", robo.get("elemento_reconocido") or val("b3_robo_elemento_reconocido"))

        desc = autor.get("descripcion") or autor.get("descripcion_general") or val("b3_autor_descripcion")
        vest = autor.get("vestimenta_rasgos") or autor.get("vestimenta") or ""
        contextura = autor.get("contextura") or ""
        edad = autor.get("edad_aproximada") or ""
        rasgos = autor.get("rasgos") or ""
        detalles_autor = "; ".join([x for x in [vest, contextura, f"edad aproximada {edad}" if edad else "", rasgos] if str(x).strip()])
        setv("b3_autor_descripcion", desc)
        setv("b3_autor_vestimenta_rasgos", detalles_autor or val("b3_autor_vestimenta_rasgos"))
        setv("b3_autor_direccion", autor.get("direccion_retiro") or autor.get("direccion_fuga") or val("b3_autor_direccion"))
        setv("b3_autor_conoce", autor.get("conocimiento_previo") or autor.get("lo_conoce") or val("b3_autor_conoce"))
        setv("b3_autor_individualizacion", autor.get("datos_individualizacion") or val("b3_autor_individualizacion"))
        combo = " ".join([str(autor.get("vestimenta", "")), str(autor.get("contextura", "")), str(autor.get("edad_aproximada", "")), str(autor.get("rasgos", ""))]).strip()
        if combo:
            setv("b3_autor_vestimenta_rasgos", combo)
        setv("b3_autor_direccion", autor.get("direccion_fuga") or val("b3_autor_direccion"))
        setv("b3_autor_conoce", autor.get("lo_conoce") or val("b3_autor_conoce"))

    # Firma digital recibida en el JSON.
    firma = primer_dict_existente(datos_bloque, [["firma"]])
    if firma:
        canvas_b64 = firma.get("firma_canvas_base64") or firma.get("firma_base64") or ""
        if firma_base64_valida(canvas_b64):
            setv("b3_firma_canvas_b64", canvas_b64)
            setv("b3_modo_firma", "Firma digital en pantalla")

    # Si no trajo situaciones, detectarlas del relato.
    if not val("b3_situaciones_confirmadas"):
        setv("b3_situaciones_confirmadas", normalizar_lista_situaciones(detectar_situaciones(val("b3_relato_crudo"))))
    else:
        setv("b3_situaciones_confirmadas", normalizar_lista_situaciones(val("b3_situaciones_confirmadas")))


def nombre_victima():
    partes = []
    if val("b3_apellido"):
        partes.append(val("b3_apellido"))
    if val("b3_nombre"):
        partes.append(val("b3_nombre"))
    return ", ".join(partes).strip(", ").strip()


def filiacion_victima():
    return {
        "condicion": val("b3_condicion"),
        "apellido": val("b3_apellido"),
        "nombre": val("b3_nombre"),
        "nombre_completo": nombre_victima(),
        "dni": val("b3_dni"),
        "edad": val("b3_edad"),
        "fecha_nacimiento": val("b3_fecha_nacimiento"),
        "nacionalidad": val("b3_nacionalidad"),
        "estado_civil": val("b3_estado_civil"),
        "profesion": val("b3_profesion"),
        "domicilio": val("b3_domicilio"),
        "telefono": val("b3_telefono"),
        "celular": val("b3_celular"),
        "correo": val("b3_correo"),
    }


def limpiar_espacios_texto(texto):
    texto = str(texto or "").replace("\r", " ").replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    # Correcciones menores frecuentes de dictado sin pretender reescribir todo.
    reemplazos = {
        " hiba ": " iba ",
        " relizar ": " realizar ",
        " delagado ": " delgado ",
        " En.ma ": " En mi ",
        " me.suele ": " me duele ",
        " le.diera ": " le diera ",
        " me.pegab ": " me pegaba ",
        " aun tirosi": " un tiro",
        " me.rode": " me robe",
    }
    tmp = f" {texto} "
    for a, b in reemplazos.items():
        tmp = tmp.replace(a, b)
    texto = tmp.strip()
    texto = re.sub(r"\s+([,.])", r"\1", texto)
    texto = re.sub(r"\.{2,}", ".", texto)
    return texto


def limpiar_fin_punto(texto):
    texto = limpiar_espacios_texto(texto)
    return texto.rstrip(" .")


def frase_si(texto, final="."):
    texto = limpiar_fin_punto(texto)
    if not texto:
        return ""
    return texto + final


def hora_relato_desde_crudo():
    crudo = val("b3_relato_crudo") or ""
    m = re.search(r"(\d{1,2})[:.]?(\d{2})?", crudo)
    if m:
        hh = m.group(1)
        mm = m.group(2) or "00"
        return f"{int(hh):02d}:{mm} hs"
    return ""


def identidad_en_parrafo():
    f = filiacion_victima()
    nom = nombre_victima() or "la persona entrevistada"
    partes = [f"se procede a recibir entrevista a quien dijo llamarse {nom}"]
    if f.get("dni"):
        partes.append(f"DNI Nro. {f.get('dni')}")
    if f.get("edad"):
        partes.append(f"de {f.get('edad')} años de edad")
    if f.get("fecha_nacimiento"):
        partes.append(f"nacido/a el {f.get('fecha_nacimiento')}")
    if f.get("nacionalidad"):
        partes.append(f"de nacionalidad {f.get('nacionalidad')}")
    if f.get("estado_civil"):
        partes.append(f"estado civil {f.get('estado_civil')}")
    if f.get("profesion"):
        partes.append(f"de profesión/ocupación {f.get('profesion')}")
    if f.get("domicilio"):
        partes.append(f"domiciliado/a en {f.get('domicilio')}")
    tel = " / ".join([x for x in [f.get("telefono"), f.get("celular")] if str(x).strip()])
    if tel:
        partes.append(f"teléfono/celular {tel}")
    if f.get("condicion"):
        partes.append(f"en carácter de {f.get('condicion')}")
    return ", ".join(partes) + ", en relación a las presentes actuaciones."




def fondo_canvas_firma(ancho=850, alto=220):
    """Fondo visible para que el espacio de firma no quede blanco/invisible."""
    img = Image.new("RGB", (ancho, alto), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, ancho - 3, alto - 3], outline=(0, 0, 0), width=3)
    d.line([45, alto - 55, ancho - 45, alto - 55], fill=(160, 160, 160), width=2)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 18)
    except Exception:
        f = None
    d.text((55, alto - 48), "Firma digital de la persona entrevistada", fill=(90, 90, 90), font=f)
    return img

def obtener_firma_base64():
    # Firma digital directa en pantalla. No se usa foto/archivo de firma.
    return val("b3_firma_canvas_b64") or ""


def firma_base64_valida(b64):
    if not b64 or not isinstance(b64, str):
        return False
    if b64.startswith("["):
        return False
    try:
        raw = base64.b64decode(b64, validate=True)
        return len(raw) > 50
    except Exception:
        return False

def canvas_tiene_trazo(image_data):
    """Devuelve True solo si el canvas tiene trazos oscuros reales. Evita guardar fondos blancos vacios como firma."""
    if image_data is None:
        return False
    try:
        img = Image.fromarray(image_data.astype("uint8"), "RGBA")
        # Detecta pixeles oscuros con alfa visible. La firma se dibuja en negro.
        pix = img.getdata()
        oscuros = 0
        for r, g, b, a in pix:
            if a > 20 and r < 180 and g < 180 and b < 180:
                oscuros += 1
                if oscuros > 40:
                    return True
        return False
    except Exception:
        return False


def canvas_a_base64(image_data):
    if image_data is None:
        return ""
    try:
        img = Image.fromarray(image_data.astype("uint8"), "RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[3])
        buf = io.BytesIO()
        fondo.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return ""


def guardar_firma_temp_desde_base64():
    b64 = obtener_firma_base64()
    if not firma_base64_valida(b64):
        return ""
    try:
        raw = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(raw)
        tmp.close()
        return tmp.name
    except Exception:
        return ""


def insertar_firma_pdf(pdf, titulo="Firma digital de la persona entrevistada"):
    path = guardar_firma_temp_desde_base64()
    if not path:
        return False
    try:
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, limpiar_pdf(titulo), ln=True)
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.image(path, x=x + 5, y=y, w=70)
        pdf.ln(28)
        return True
    except Exception:
        return False
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass

# =====================================================
# CONSTRUCCION DE TEXTOS
# =====================================================

def construir_fragmentos_guia():
    situaciones = val("b3_situaciones_confirmadas", []) or []
    partes = []

    # Robo / hurto / sustraccion
    if any(s in situaciones for s in ["Robo con arma", "Robo / sustracción", "Hurto"]):
        fr = []
        if val("b3_robo_elementos"):
            fr.append(f"Manifiesto que me sustrajeron {val('b3_robo_elementos')}.")
        if val("b3_robo_modo"):
            fr.append(f"Respecto de la forma en que ocurrió el hecho, puedo decir que {val('b3_robo_modo')}.")
        if val("b3_robo_arma"):
            fr.append(f"Recuerdo que el sujeto utilizó o exhibió {val('b3_robo_arma')}.")
        if val("b3_robo_intimidacion"):
            fr.append(f"En ese momento me intimidó de la siguiente manera: {val('b3_robo_intimidacion')}.")
        if val("b3_robo_recupero"):
            fr.append(f"Sobre el recupero de lo sustraído, manifiesto que {val('b3_robo_recupero')}.")
        if val("b3_robo_elemento_reconocido"):
            fr.append(f"En cuanto al elemento exhibido o secuestrado, manifiesto que {val('b3_robo_elemento_reconocido')}.")
        if fr:
            partes.append(" ".join(fr))

    # Amenazas
    if "Amenazas" in situaciones:
        fr = []
        frase = val("b3_amenaza_frase")
        if frase:
            fr.append(f"Cuando me amenazó, me dijo textualmente: '{frase}'.")
        if val("b3_amenaza_medio"):
            fr.append(f"La amenaza fue realizada por {val('b3_amenaza_medio')}.")
        if val("b3_amenaza_temor"):
            fr.append(f"A raíz de ello sentí temor, me sentí amedrentada/intimidada y manifiesto que {val('b3_amenaza_temor')}.")
        if val("b3_amenaza_vinculo"):
            fr.append(f"Respecto de esa persona, manifiesto que {val('b3_amenaza_vinculo')}.")
        if val("b3_amenaza_evidencia"):
            fr.append(f"También puedo aportar o señalar lo siguiente: {val('b3_amenaza_evidencia')}.")
        if fr:
            partes.append(" ".join(fr))

    # Lesiones
    if "Lesiones" in situaciones:
        fr = []
        if val("b3_lesion_mecanica"):
            fr.append(f"Sobre las lesiones sufridas, manifiesto que {val('b3_lesion_mecanica')}.")
        if val("b3_lesion_zona"):
            fr.append(f"Las zonas de mi cuerpo afectadas fueron: {val('b3_lesion_zona')}.")
        if val("b3_lesion_asistencia"):
            fr.append(f"Respecto de la asistencia médica, manifiesto que {val('b3_lesion_asistencia')}.")
        if val("b3_lesion_certificado"):
            fr.append(f"En cuanto al certificado médico, manifiesto que {val('b3_lesion_certificado')}.")
        if val("b3_lesion_instancia") == "Sí":
            fr.append("En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas.")
        elif val("b3_lesion_instancia") == "No":
            fr.append("En este acto manifiesto que no es mi deseo instar la acción penal por las lesiones sufridas.")
        elif val("b3_lesion_instancia") == "Desea pensarlo / no responde":
            fr.append("Consultada respecto de la instancia penal por las lesiones sufridas, manifiesto que deseo pensarlo o no respondo en este acto.")
        if fr:
            partes.append(" ".join(fr))

    # Aprehension / persona sindicada: sin reconocimiento, sin confrontacion.
    if "Aprehensión / retención vinculada" in situaciones:
        fr = []
        if val("b3_autor_descripcion"):
            fr.append(f"Recuerdo que la persona que cometió el hecho era {val('b3_autor_descripcion')}.")
        if val("b3_autor_vestimenta_rasgos"):
            fr.append(f"Puedo decir que vestía o presentaba los siguientes rasgos visibles: {val('b3_autor_vestimenta_rasgos')}.")
        if val("b3_autor_direccion"):
            fr.append(f"Luego del hecho observé que se retiró en dirección hacia {val('b3_autor_direccion')}.")
        if val("b3_autor_conoce"):
            fr.append(f"Respecto de si lo conozco previamente, manifiesto que {val('b3_autor_conoce')}.")
        if val("b3_autor_individualizacion"):
            fr.append(f"Asimismo puedo aportar como datos de individualización: {val('b3_autor_individualizacion')}.")
        if fr:
            partes.append(" ".join(fr))

    # Daño
    if "Daño" in situaciones and val("b3_danio_detalle"):
        partes.append(f"Respecto de los daños observados o sufridos, manifiesto que {val('b3_danio_detalle')}.")

    # Violencia familiar / contexto
    if "Violencia familiar / contexto familiar" in situaciones and val("b3_violencia_contexto"):
        partes.append(f"Sobre el contexto o vínculo con la persona mencionada, manifiesto que {val('b3_violencia_contexto')}.")

    # Evidencia
    if "Cámaras / testigos / evidencia" in situaciones and val("b3_evidencia_detalle"):
        partes.append(f"En relación a posibles testigos, cámaras, capturas o evidencia, manifiesto que {val('b3_evidencia_detalle')}.")

    # Otro
    if "Otro" in situaciones and val("b3_otro_detalle"):
        partes.append(val("b3_otro_detalle"))

    return [p.strip() for p in partes if p and p.strip()]


def construir_relato_final(guardar=False):
    """Construye un relato final fluido.
    No pega respuestas como cuestionario: integra relato crudo + guía en primera persona.
    Solo escribe en st.session_state si guardar=True.
    """
    crudo = limpiar_espacios_texto(val("b3_relato_crudo"))
    situaciones = val("b3_situaciones_confirmadas", []) or []
    partes = []

    # Apertura temporal. Si el relato ya empieza bien, no se fuerza demasiado.
    hora = hora_relato_desde_crudo()
    if hora and not crudo.lower().startswith(("hoy", "siendo", "en fecha")):
        partes.append(f"Hoy, siendo aproximadamente las {hora},")
    elif crudo:
        # Toma el relato crudo como base, pero luego lo mejora con datos estructurados.
        partes.append(crudo.rstrip("."))

    # Robo / sustracción: se arma como secuencia narrativa.
    if any(s in situaciones for s in ["Robo con arma", "Robo / sustracción", "Hurto"]):
        if not partes:
            partes.append("Hoy")
        if val("b3_robo_arma"):
            partes.append(f"se me acercó un sujeto masculino, quien exhibiendo {limpiar_fin_punto(val('b3_robo_arma'))}")
        if val("b3_robo_intimidacion"):
            partes.append(f"me dijo \"{limpiar_fin_punto(val('b3_robo_intimidacion'))}\"")
        if val("b3_robo_modo"):
            partes.append(f"Ante esa situación {limpiar_fin_punto(val('b3_robo_modo'))}")
        if val("b3_lesion_mecanica"):
            partes.append(f"momento en el cual {limpiar_fin_punto(val('b3_lesion_mecanica'))}")
        if val("b3_robo_elementos"):
            partes.append(f"Luego de ello logró sustraerme {limpiar_fin_punto(val('b3_robo_elementos'))}")
        if val("b3_autor_direccion"):
            partes.append(f"y se dio a la fuga hacia {limpiar_fin_punto(val('b3_autor_direccion'))}")
        elif "Aprehensión / retención vinculada" in situaciones:
            partes.append("y se dio a la fuga a pie")
        if val("b3_robo_recupero"):
            partes.append(f"Posteriormente {limpiar_fin_punto(val('b3_robo_recupero'))}")
        if val("b3_robo_elemento_reconocido"):
            partes.append(f"reconociendo dicho elemento como de mi propiedad, por cuanto {limpiar_fin_punto(val('b3_robo_elemento_reconocido'))}")

    # Amenazas puras o asociadas.
    if "Amenazas" in situaciones:
        if val("b3_amenaza_frase"):
            partes.append(f"Recuerdo que la amenaza fue textual: \"{limpiar_fin_punto(val('b3_amenaza_frase'))}\"")
        if val("b3_amenaza_temor"):
            partes.append(f"Ante ello {limpiar_fin_punto(val('b3_amenaza_temor'))}")
        if val("b3_amenaza_vinculo"):
            partes.append(f"Respecto de esa persona, manifiesto que {limpiar_fin_punto(val('b3_amenaza_vinculo'))}")
        if val("b3_amenaza_evidencia"):
            partes.append(f"También puedo aportar como evidencia o referencia: {limpiar_fin_punto(val('b3_amenaza_evidencia'))}")

    # Persona sindicada: solo datos recordados, sin reconocimiento/confrontación.
    if "Aprehensión / retención vinculada" in situaciones:
        descs = []
        if val("b3_autor_descripcion"):
            descs.append(limpiar_fin_punto(val("b3_autor_descripcion")))
        if val("b3_autor_vestimenta_rasgos"):
            descs.append(limpiar_fin_punto(val("b3_autor_vestimenta_rasgos")))
        if descs:
            partes.append("Recuerdo que el sujeto era " + ", ".join(descs))
        if val("b3_autor_conoce"):
            partes.append(f"Respecto de si lo conozco previamente, manifiesto que {limpiar_fin_punto(val('b3_autor_conoce'))}")
        if val("b3_autor_individualizacion"):
            partes.append(f"Asimismo puedo aportar como datos de individualización: {limpiar_fin_punto(val('b3_autor_individualizacion'))}")

    # Lesiones: cierre específico.
    if "Lesiones" in situaciones:
        les = []
        if val("b3_lesion_zona"):
            les.append(f"Respecto a las lesiones sufridas, manifiesto que me resultó afectada la zona de {limpiar_fin_punto(val('b3_lesion_zona'))}")
        elif val("b3_lesion_mecanica"):
            les.append(f"Respecto a las lesiones sufridas, manifiesto que {limpiar_fin_punto(val('b3_lesion_mecanica'))}")
        if val("b3_lesion_asistencia"):
            les.append(f"no habiendo sido asistido por personal médico hasta el momento" if "no" in val("b3_lesion_asistencia").lower() else f"habiendo recibido asistencia médica: {limpiar_fin_punto(val('b3_lesion_asistencia'))}")
        if val("b3_lesion_certificado"):
            les.append(f"y {('no poseyendo certificado médico' if 'no' in val('b3_lesion_certificado').lower() else 'poseyendo certificado médico/diagnóstico: ' + limpiar_fin_punto(val('b3_lesion_certificado')))}")
        if val("b3_lesion_instancia") == "Sí":
            les.append("Asimismo, es mi deseo instar la acción penal por las lesiones sufridas")
        elif val("b3_lesion_instancia") == "No":
            les.append("Asimismo, manifiesto que no es mi deseo instar la acción penal por las lesiones sufridas")
        elif val("b3_lesion_instancia") == "Desea pensarlo / no responde":
            les.append("Consultado/a al respecto, manifiesto que deseo pensarlo o no respondo en este acto")
        if les:
            partes.append(", ".join(les))

    if "Cámaras / testigos / evidencia" in situaciones and val("b3_evidencia_detalle"):
        partes.append(f"En relación a posibles testigos, cámaras, capturas o evidencia, manifiesto que {limpiar_fin_punto(val('b3_evidencia_detalle'))}")
    if "Daño" in situaciones and val("b3_danio_detalle"):
        partes.append(f"Respecto de los daños observados o sufridos, manifiesto que {limpiar_fin_punto(val('b3_danio_detalle'))}")
    if "Violencia familiar / contexto familiar" in situaciones and val("b3_violencia_contexto"):
        partes.append(f"Sobre el contexto o vínculo con la persona mencionada, manifiesto que {limpiar_fin_punto(val('b3_violencia_contexto'))}")
    if "Otro" in situaciones and val("b3_otro_detalle"):
        partes.append(limpiar_fin_punto(val("b3_otro_detalle")))

    # Si no hubo guía útil, conserva el relato crudo limpio.
    if not partes and crudo:
        partes = [crudo]

    texto = " ".join([p.strip().rstrip(".") for p in partes if p and p.strip()])
    texto = limpiar_espacios_texto(texto)
    if texto and not texto.endswith("."):
        texto += "."
    if guardar:
        setv("b3_relato_final", texto)
    return texto


def construir_noticia_criminis(guardar=False):
    # Esta no es el relato de entrevista: es resumen policial para Acta de Procedimiento.
    nom = nombre_victima() or "la persona entrevistada"
    dni = val("b3_dni")
    intro = f"Seguidamente se entrevista a quien dijo llamarse {nom}"
    if dni:
        intro += f", DNI Nro. {dni}"
    intro += ", quien manifestó que "

    texto_base = val("b3_relato_final").strip() or construir_relato_final(guardar=False) or val("b3_relato_crudo").strip()
    texto_base = " ".join(texto_base.split())
    if len(texto_base) > 900:
        texto_base = texto_base[:900].rsplit(" ", 1)[0] + "..."
    noticia = intro + (texto_base if texto_base else "aportó datos vinculados al hecho investigado")
    if not noticia.endswith("."):
        noticia += "."
    if guardar:
        setv("b3_noticia_criminis", noticia)
    return noticia

# =====================================================
# PDF
# =====================================================

class PDFB3(FPDF):
    def header(self):
        self.set_font("Arial", "B", 11)
        self.cell(0, 6, limpiar_pdf("POLICIA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
        self.set_font("Arial", "", 9)
        dep = val("b3_dependencia_acta") or val("b3_dependencia_policial") or "DEPENDENCIA POLICIAL"
        self.cell(0, 6, limpiar_pdf(str(dep).upper()), ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 8, limpiar_pdf(LEMA), align="R")


def datos_apertura_pdf():
    lugar = val("b3_lugar_entrevista") or "Rosario"
    fecha = val("b3_fecha_entrevista")
    hora = val("b3_hora_entrevista")
    if isinstance(fecha, date):
        fecha_txt = fecha.strftime("%d/%m/%Y")
    else:
        fecha_txt = str(fecha)
    return lugar, fecha_txt, hora


def generar_pdf_completo_b3():
    relato_pdf = val("b3_relato_final").strip() or construir_relato_final(guardar=False)

    pdf = PDFB3()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=18)

    # Hoja 1 - Entrevista
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, limpiar_pdf("ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO"), ln=True, align="C")
    pdf.ln(4)

    lugar, fecha_txt, hora = datos_apertura_pdf()
    pdf.set_font("Arial", "", 10)
    apertura = (
        f"En la ciudad de {lugar}, a fecha {fecha_txt}, siendo las {hora} horas, "
        f"{identidad_en_parrafo()}"
    )
    pdf_multi(pdf, apertura)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "RELATO", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, relato_pdf, alto=7)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "CIERRE", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "No siendo para mas, previa integra lectura y ratificacion de su contenido, se da por finalizado el presente acto, firmando al pie para constancia.")
    pdf.ln(8)
    insertar_firma_pdf(pdf, "Firma digital de la persona entrevistada:")
    pdf.ln(5)
    pdf.cell(85, 7, "____________________________", ln=False, align="C")
    pdf.cell(10, 7, "", ln=False)
    pdf.cell(85, 7, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion entrevistado/a", ln=False, align="C")
    pdf.cell(10, 6, "", ln=False)
    pdf.cell(85, 6, "Firma personal policial", ln=True, align="C")
    pdf.ln(6)
    personal = val("b3_personal_actuante") or val("b3_nombre_policial")
    pdf.set_font("Arial", "", 9)
    pdf_multi(pdf, f"Personal actuante: {personal}")

    # Hoja siguiente - Derechos de la Victima
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, limpiar_pdf("NOTIFICACION DE DERECHOS DE LA VICTIMA"), ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    nom = nombre_victima() or "la persona entrevistada"
    dni = val("b3_dni")
    texto = (
        f"En la ciudad de {lugar}, a fecha {fecha_txt}, siendo las {hora} horas, "
        f"se procede a notificar a {nom}"
    )
    if dni:
        texto += f", DNI Nro. {dni}"
    texto += ", respecto de los derechos que le asisten en su caracter de victima/damnificado/a en las presentes actuaciones."
    pdf_multi(pdf, texto)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DERECHOS INFORMADOS", ln=True)
    pdf.set_font("Arial", "", 9)
    derechos = [
        "Recibir trato digno y respetuoso por parte de las autoridades intervinientes.",
        "Ser informada sobre el estado del procedimiento y las medidas que pudieren corresponder.",
        "Aportar informacion, documentacion, testigos, imagenes, videos u otros elementos utiles para la investigacion.",
        "Solicitar medidas de proteccion cuando existieren circunstancias que lo justifiquen.",
        "Ser informada sobre organismos de asistencia, contencion y orientacion a victimas.",
        "Designar domicilio, telefono o medio electronico para recibir notificaciones vinculadas al procedimiento.",
        "Solicitar la restitucion de efectos propios cuando correspondiere y conforme disposicion de autoridad competente.",
        "Ser informada respecto de las vias institucionales disponibles para ampliar denuncia o aportar nuevos datos."
    ]
    for d in derechos:
        pdf_multi(pdf, f"- {d}", alto=5)
    pdf.ln(5)

    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "Leida que le fuera la presente, la persona notificada manifiesta quedar debidamente anoticiada de los derechos precedentemente informados, firmando al pie para constancia.")
    pdf.ln(8)
    insertar_firma_pdf(pdf, "Firma digital de la persona notificada:")
    pdf.ln(5)
    pdf.cell(85, 7, "____________________________", ln=False, align="C")
    pdf.cell(10, 7, "", ln=False)
    pdf.cell(85, 7, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion de la victima", ln=False, align="C")
    pdf.cell(10, 6, "", ln=False)
    pdf.cell(85, 6, "Firma personal policial", ln=True, align="C")

    return pdf_bytes(pdf)

# =====================================================
# EXPORTACION JSON
# =====================================================

def armar_json_exportacion():
    relato_final_export = val("b3_relato_final").strip() or construir_relato_final(guardar=False)
    noticia_export = val("b3_noticia_criminis").strip() or construir_noticia_criminis(guardar=False)

    autor_carga = {
        "ni": val("b3_ni_policial"),
        "nombre_apellido": val("b3_nombre_policial"),
        "jerarquia": val("b3_jerarquia"),
        "dependencia": val("b3_dependencia_policial"),
        "rol_operativo": val("b3_rol_operativo"),
        "dispositivo": "Celular validado"
    }
    actuacion = {
        "numero_acta": val("b3_numero_acta"),
        "fecha": str(val("b3_fecha_entrevista")),
        "hora": val("b3_hora_entrevista"),
        "dependencia": val("b3_dependencia_acta"),
        "lugar_entrevista": val("b3_lugar_entrevista"),
    }
    respuestas_guia = {
        "amenazas": {
            "frase_textual": val("b3_amenaza_frase"),
            "medio": val("b3_amenaza_medio"),
            "temor_amedrentamiento": val("b3_amenaza_temor"),
            "vinculo_autor": val("b3_amenaza_vinculo"),
            "evidencia": val("b3_amenaza_evidencia"),
        },
        "lesiones": {
            "mecanica": val("b3_lesion_mecanica"),
            "zona": val("b3_lesion_zona"),
            "asistencia_medica": val("b3_lesion_asistencia"),
            "certificado": val("b3_lesion_certificado"),
            "insta_accion_penal": val("b3_lesion_instancia"),
        },
        "robo": {
            "elementos_sustraidos": val("b3_robo_elementos"),
            "modo_comision": val("b3_robo_modo"),
            "arma_utilizada": val("b3_robo_arma"),
            "intimidacion": val("b3_robo_intimidacion"),
            "recupero_elementos": val("b3_robo_recupero"),
            "elemento_reconocido": val("b3_robo_elemento_reconocido"),
        },
        "persona_sindicada": {
            "descripcion": val("b3_autor_descripcion"),
            "vestimenta_rasgos": val("b3_autor_vestimenta_rasgos"),
            "direccion_retiro": val("b3_autor_direccion"),
            "conocimiento_previo": val("b3_autor_conoce"),
            "datos_individualizacion": val("b3_autor_individualizacion"),
        },
        "danio": val("b3_danio_detalle"),
        "violencia_contexto": val("b3_violencia_contexto"),
        "evidencia": val("b3_evidencia_detalle"),
        "otro": val("b3_otro_detalle"),
    }

    datos_bloque = {
        "identificacion_victima": filiacion_victima(),
        "relato_crudo": val("b3_relato_crudo"),
        "analisis_sivap": {
            "situaciones_detectadas": normalizar_lista_situaciones(detectar_situaciones(val("b3_relato_crudo"))),
            "situaciones_confirmadas": normalizar_lista_situaciones(val("b3_situaciones_confirmadas", [])),
            "situacion_otro": val("b3_situacion_otro"),
        },
        "respuestas_guia": respuestas_guia,
        "relato_final": relato_final_export,
        "noticia_criminis": noticia_export,
        "derechos_victima": {
            "notificada": "SI",
            "documento_generado": "SI",
            "incluido_en_pdf_completo": "SI"
        },
        "firma": {
            "tipo": "Firma digital en pantalla",
            "firma_canvas_base64": val("b3_firma_canvas_b64"),
        }
    }

    # Formato simple actual: una sola llave principal para la entrevista.
    # Se eliminaron datos_bloque/datos_entrevista/datos_completos_bloque duplicados
    # para que el importador no tenga que adivinar entre estructuras repetidas.
    return {
        "sistema": "S.I.V.A.P. — Sistema Integrado de Validación de Actuaciones Policiales",
        "tipo_archivo": "colaboracion_json",
        "bloque": "BLOQUE_3_ENTREVISTA_VICTIMA",
        "autor_carga": autor_carga,
        "actuacion": actuacion,
        "entrevista": datos_bloque,
        "resumen_para_acta_procedimiento": {
            "tipo": "victima_damnificado",
            "nombre": nombre_victima(),
            "dni": val("b3_dni"),
            "domicilio": val("b3_domicilio"),
            "texto_para_acta": noticia_export,
            "incorporar": True
        },
        "fecha_exportacion": datetime.now().isoformat()
    }


def nombre_archivo_json():
    nro = re.sub(r"[^A-Za-z0-9_-]+", "_", val("b3_numero_acta") or "SIN_ACTA")
    ni = re.sub(r"[^A-Za-z0-9_-]+", "", val("b3_ni_policial") or "SIN_NI")
    return f"SIVAP_ACTA_{nro}_BLOQUE_3_VICTIMA_NI_{ni}.json"


# =====================================================
# IMPORTACION PENDIENTE ANTES DE CREAR WIDGETS
# =====================================================

# Streamlit no permite modificar st.session_state de una key después de que
# el widget con esa key ya fue creado. Por eso, cuando el actante toca
# "Incorporar", se guarda el JSON como pendiente y se hace rerun.
# En la corrida siguiente se aplica acá, antes de dibujar sidebar/tabs/widgets.
if st.session_state.get("_b3_import_pendiente"):
    try:
        importar_json_bloque3(st.session_state["_b3_import_pendiente"])
        st.session_state["_b3_import_ok"] = True
    except Exception as e:
        st.session_state["_b3_import_error"] = str(e)
    finally:
        st.session_state["_b3_import_pendiente"] = None

# =====================================================
# INTERFAZ
# =====================================================

st.title("🗣️ BLOQUE 3 — Acta de Entrevista a Víctima/Damnificado")
st.caption(LEMA)

with st.sidebar:
    st.header("Identidad policial")
    st.text_input("NI / PIN policial", key="b3_ni_policial")
    st.text_input("Nombre y apellido", key="b3_nombre_policial")
    st.text_input("Jerarquía", key="b3_jerarquia")
    st.text_input("Dependencia", key="b3_dependencia_policial")
    st.selectbox("Rol operativo", ["Actante", "Colaborador", "Ambos"], key="b3_rol_operativo")
    st.success("Dispositivo: celular validado")

    st.divider()
    st.header("ACTUACIÓN")
    st.text_input("Número de acta", key="b3_numero_acta")
    st.date_input("Fecha", key="b3_fecha_entrevista")
    st.text_input("Hora", key="b3_hora_entrevista")
    st.text_input("Lugar", key="b3_lugar_entrevista")
    st.text_input("Dependencia acta", key="b3_dependencia_acta")
    st.text_area("Personal actuante", key="b3_personal_actuante", height=80)


tabs = st.tabs([
    "0. Importar JSON",
    "1. Identificación",
    "2. Relato",
    "3. Análisis S.I.V.A.P.",
    "4. Relato final / Noticia",
    "5. Firma / PDF / JSON"
])

# 0 Importar
with tabs[0]:
    st.subheader("📥 Importar colaboración JSON de BLOQUE 3")
    st.info("Use esta pestaña cuando un colaborador envía por WhatsApp un JSON de BLOQUE 3. El formulario se completa y el actante puede revisar/corregir antes de guardar o imprimir.")
    if st.session_state.pop("_b3_import_ok", False):
        st.success("Datos incorporados al BLOQUE 3. Revise Identificación, Relato, Análisis y Relato final antes de imprimir/exportar.")
    if st.session_state.get("_b3_import_error"):
        st.error("No se pudo incorporar el JSON: " + str(st.session_state.pop("_b3_import_error")))
    archivo = st.file_uploader("Subir JSON BLOQUE 3 recibido por WhatsApp", type=["json"], key="b3_import_json")
    if archivo is not None:
        try:
            data = json.load(archivo)
            if not es_json_bloque3(data):
                st.error("El archivo no parece corresponder a BLOQUE 3. Debe importarse en su bloque correspondiente.")
            else:
                st.success("JSON de BLOQUE 3 detectado correctamente.")
                with st.expander("Vista previa técnica"):
                    st.json(data)
                if st.button("📥 Incorporar datos al BLOQUE 3 del actante", use_container_width=True):
                    st.session_state["_b3_import_pendiente"] = data
                    st.rerun()
        except Exception as e:
            st.error(f"No se pudo leer el JSON: {e}")

# 1 Identificacion
with tabs[1]:
    st.subheader("Identificación de víctima / damnificado")
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Condición", ["Víctima/Damnificado", "Representante legal", "Progenitor/a", "Otro"], key="b3_condicion")
        st.text_input("Apellido", key="b3_apellido")
        st.text_input("Nombre", key="b3_nombre")
        st.text_input("DNI", key="b3_dni")
        st.text_input("Edad", key="b3_edad")
        st.text_input("Fecha de nacimiento", key="b3_fecha_nacimiento")
    with c2:
        st.text_input("Nacionalidad", key="b3_nacionalidad")
        st.text_input("Estado civil", key="b3_estado_civil")
        st.text_input("Profesión / ocupación", key="b3_profesion")
        st.text_area("Domicilio", key="b3_domicilio", height=90)
        st.text_input("Teléfono fijo", key="b3_telefono")
        st.text_input("Celular", key="b3_celular")
        st.text_input("Correo electrónico", key="b3_correo")

# 2 Relato
with tabs[2]:
    st.subheader("Relato inicial")
    st.text_area("Relato inicial de la víctima/damnificado", key="b3_relato_crudo", height=360)

# 3 Analisis dinamico
with tabs[3]:
    st.subheader("Análisis S.I.V.A.P. — guía dinámica")
    detectadas = detectar_situaciones(val("b3_relato_crudo"))
    if detectadas:
        st.success("Del relato se observan posibles delitos/situaciones: " + ", ".join(detectadas))
    else:
        st.warning("Del relato no se detectaron situaciones automáticamente. Puede agregarlas manualmente.")

    opciones = OPCIONES_SITUACIONES

    # Streamlit exige que todo valor actual del multiselect exista en options.
    # Por eso se normalizan etiquetas viejas/importadas antes de crear el widget.
    actuales = normalizar_lista_situaciones(val("b3_situaciones_confirmadas", []))
    if not actuales and detectadas:
        actuales = normalizar_lista_situaciones(detectadas)
    st.session_state["b3_situaciones_confirmadas"] = actuales

    st.multiselect("Confirmar situaciones a trabajar", opciones, key="b3_situaciones_confirmadas")
    if "Otro" in val("b3_situaciones_confirmadas", []):
        st.text_input("Otra situación no detectada", key="b3_situacion_otro")

    situaciones = val("b3_situaciones_confirmadas", []) or []
    st.divider()

    if any(s in situaciones for s in ["Robo con arma", "Robo / sustracción", "Hurto"]):
        with st.expander("Preguntas clave — Robo / sustracción", expanded=True):
            st.text_area("¿Qué elemento/s le sustrajeron o intentaron sustraer?", key="b3_robo_elementos", height=80)
            st.text_area("¿Cómo ocurrió el hecho?", key="b3_robo_modo", height=80)
            if "Robo con arma" in situaciones:
                st.text_input("Arma o elemento utilizado/exhibido", key="b3_robo_arma")
                st.text_area("¿Cómo fue intimidada o amenazada durante el hecho?", key="b3_robo_intimidacion", height=80)
            st.text_area("¿Hubo recupero de elementos?", key="b3_robo_recupero", height=70)
            st.text_area("¿Reconoce el elemento recuperado/secuestrado como propio?", key="b3_robo_elemento_reconocido", height=70)

    if "Amenazas" in situaciones:
        with st.expander("Preguntas clave — Amenazas", expanded=True):
            st.text_input("Frase textual de la amenaza", key="b3_amenaza_frase")
            st.selectbox("Medio utilizado", ["", "personalmente", "teléfono", "WhatsApp", "redes sociales", "por intermedio de otra persona", "otro"], key="b3_amenaza_medio")
            st.text_area("¿Se sintió amedrentada/intimidada? ¿Teme por su integridad física?", key="b3_amenaza_temor", height=90)
            st.text_area("¿Lo conoce previamente? ¿Qué vínculo tiene o de dónde lo conoce?", key="b3_amenaza_vinculo", height=80)
            st.text_area("¿Hay testigos, cámaras, capturas o mensajes?", key="b3_amenaza_evidencia", height=80)

    if "Lesiones" in situaciones:
        with st.expander("Preguntas clave — Lesiones", expanded=True):
            st.text_area("¿Cómo se produjeron las lesiones?", key="b3_lesion_mecanica", height=80)
            st.text_input("Zona/s del cuerpo afectada/s", key="b3_lesion_zona")
            st.text_area("Asistencia médica / SIES / hospital / médico", key="b3_lesion_asistencia", height=80)
            st.text_input("Certificado médico / diagnóstico", key="b3_lesion_certificado")
            st.selectbox("¿Desea instar acción penal por las lesiones sufridas?", ["", "Sí", "No", "Desea pensarlo / no responde"], key="b3_lesion_instancia")

    if "Aprehensión / retención vinculada" in situaciones:
        with st.expander("Preguntas clave — Persona sindicada / datos objetivos", expanded=True):
            st.info("No se pregunta reconocimiento ni confrontación con aprehendido. Solo datos objetivos recordados por la entrevistada.")
            st.text_area("¿Qué recuerda de la persona que cometió el hecho?", key="b3_autor_descripcion", height=80)
            st.text_area("Vestimenta, contextura, edad aproximada, rasgos visibles", key="b3_autor_vestimenta_rasgos", height=90)
            st.text_input("Dirección en la que se retiró o fugó", key="b3_autor_direccion")
            st.text_area("¿Lo conoce previamente?", key="b3_autor_conoce", height=70)
            st.text_area("Otros datos que permitan individualizarlo", key="b3_autor_individualizacion", height=80)

    if "Daño" in situaciones:
        with st.expander("Preguntas clave — Daño", expanded=True):
            st.text_area("Detalle de daño, elemento dañado y circunstancias", key="b3_danio_detalle", height=100)

    if "Violencia familiar / contexto familiar" in situaciones:
        with st.expander("Preguntas clave — Contexto familiar / vínculo", expanded=True):
            st.text_area("Contexto, vínculo, convivencia, antecedentes relevantes", key="b3_violencia_contexto", height=120)

    if "Cámaras / testigos / evidencia" in situaciones:
        with st.expander("Preguntas clave — Cámaras / testigos / evidencia", expanded=True):
            st.text_area("Testigos, cámaras, capturas, videos, mensajes u otra evidencia", key="b3_evidencia_detalle", height=120)

    if "Otro" in situaciones:
        with st.expander("Preguntas clave — Otro", expanded=True):
            st.text_area("Detalle adicional para integrar al relato", key="b3_otro_detalle", height=120)

# 4 Relato final
with tabs[4]:
    st.subheader("Relato final y noticia criminis")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📝 Generar / actualizar relato final", use_container_width=True):
            construir_relato_final(guardar=True)
            st.success("Relato final actualizado.")
    with c2:
        if st.button("🚓 Generar / actualizar noticia criminis", use_container_width=True):
            construir_noticia_criminis(guardar=True)
            st.success("Noticia criminis actualizada.")

    st.text_area("Relato final de entrevista", key="b3_relato_final", height=360)
    st.text_area("Súper resumen / noticia criminis para Acta de Procedimiento", key="b3_noticia_criminis", height=180)

# 5 Firma / PDF / JSON
with tabs[5]:
    st.subheader("Firma digital, PDF completo y JSON")
    st.info("El PDF completo genera Acta de Entrevista y Notificación de Derechos de la Víctima. La firma digital forma parte del flujo; si luego se firma en papel, queda como refuerzo.")

    if firma_base64_valida(obtener_firma_base64()):
        try:
            st.image(base64.b64decode(obtener_firma_base64()), caption="Firma digital cargada/importada", width=300)
        except Exception:
            st.success("Firma digital cargada/importada.")

    st.markdown("### Firma digital de la persona entrevistada")
    st.caption("Firme dentro del recuadro. La firma digital se guarda en el JSON y se inserta en el PDF.")

    if CANVAS_OK:
        # IMPORTANTE: el BLOQUE 4 funciona porque usa el canvas directo y simple.
        # En BLOQUE 3 se mantiene la misma logica, agregando solo una imagen de fondo
        # blanca con borde para que el recuadro no quede invisible dentro de st.tabs.
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            background_image=fondo_canvas_firma(500, 150),
            height=150,
            width=500,
            drawing_mode="freedraw",
            update_streamlit=True,
            display_toolbar=False,
            key="b3_canvas_firma_victima_simple",
        )

        if canvas_result is not None and canvas_result.image_data is not None:
            if canvas_tiene_trazo(canvas_result.image_data):
                b64_firma = canvas_a_base64(canvas_result.image_data)
                if b64_firma:
                    setv("b3_firma_canvas_b64", b64_firma)
                    setv("b3_modo_firma", "Firma digital en pantalla")
                    st.success("Firma digital capturada.")
            else:
                st.caption("Aún no se detectó trazo de firma en el recuadro.")
    else:
        st.error("No se pudo cargar el recuadro de firma digital. Verifique streamlit-drawable-canvas en requirements.txt o recargue la página.")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        pdf_data = generar_pdf_completo_b3()
        st.download_button(
            "📄 Descargar PDF completo BLOQUE 3",
            data=pdf_data,
            file_name="BLOQUE_3_Acta_Entrevista_y_Derechos_Victima.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="b3_down_pdf_completo"
        )

    with c2:
        data_json = armar_json_exportacion()
        json_bytes = json.dumps(data_json, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "📤 Descargar JSON para WhatsApp",
            data=json_bytes,
            file_name=nombre_archivo_json(),
            mime="application/json",
            use_container_width=True,
            key="b3_down_json_wsp"
        )

    msg = f"S.I.V.A.P. — Colaboración BLOQUE 3\nActa: {val('b3_numero_acta') or 'SIN ACTA'}\nVíctima: {nombre_victima() or 'SIN CARGAR'}\nArchivo: {nombre_archivo_json()}\nActante: importar este JSON dentro de BLOQUE 3."
    st.text_area("Mensaje sugerido para WhatsApp", value=msg, height=120, key="b3_msg_wsp")

    with st.expander("Vista técnica JSON"):
        st.json(armar_json_exportacion())

try:
    if GUARDADO_OK:
        autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
