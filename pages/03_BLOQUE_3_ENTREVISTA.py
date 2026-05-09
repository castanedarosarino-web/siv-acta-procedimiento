import streamlit as st
import json
import base64
import io
import os
import re
from datetime import datetime, date
from fpdf import FPDF
from PIL import Image

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

    # firma
    "b3_modo_firma": "Firma digital en pantalla",
    "b3_firma_canvas_b64": "",
    "b3_firma_subida_b64": "",
    "b3_firma_subida_nombre": "",
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
        ["datos_bloque"],
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

    analisis = primer_dict_existente(datos_bloque, [["analisis_sivap"], ["analisis"]])
    if analisis:
        sit = analisis.get("situaciones_confirmadas") or analisis.get("situaciones_detectadas") or []
        if isinstance(sit, str):
            sit = [sit]
        setv("b3_situaciones_confirmadas", sit)

    resp = primer_dict_existente(datos_bloque, [["respuestas_guia"], ["guia"], ["respuestas"]])
    if resp:
        # Importa respuestas si existen con nombres conocidos.
        amenazas = resp.get("amenazas", {}) if isinstance(resp.get("amenazas", {}), dict) else {}
        lesiones = resp.get("lesiones", {}) if isinstance(resp.get("lesiones", {}), dict) else {}
        robo = resp.get("robo", {}) if isinstance(resp.get("robo", {}), dict) else {}
        autor = resp.get("descripcion_autor", {}) if isinstance(resp.get("descripcion_autor", {}), dict) else {}

        setv("b3_amenaza_frase", amenazas.get("frase_textual") or amenazas.get("frase") or val("b3_amenaza_frase"))
        setv("b3_amenaza_temor", amenazas.get("amedrentamiento") or amenazas.get("temor_integridad") or val("b3_amenaza_temor"))
        setv("b3_amenaza_vinculo", amenazas.get("vinculo_autor") or val("b3_amenaza_vinculo"))

        setv("b3_lesion_mecanica", lesiones.get("mecanica") or lesiones.get("descripcion_lesiones") or val("b3_lesion_mecanica"))
        setv("b3_lesion_asistencia", lesiones.get("asistencia_medica") or val("b3_lesion_asistencia"))
        setv("b3_lesion_instancia", lesiones.get("insta_accion_penal") or val("b3_lesion_instancia"))

        setv("b3_robo_elementos", robo.get("elementos_sustraidos") or val("b3_robo_elementos"))
        setv("b3_robo_modo", robo.get("modo_comision") or val("b3_robo_modo"))
        setv("b3_robo_arma", robo.get("arma_utilizada") or val("b3_robo_arma"))
        setv("b3_robo_recupero", robo.get("recupero_elementos") or val("b3_robo_recupero"))

        setv("b3_autor_descripcion", autor.get("descripcion_general") or val("b3_autor_descripcion"))
        combo = " ".join([str(autor.get("vestimenta", "")), str(autor.get("contextura", "")), str(autor.get("edad_aproximada", "")), str(autor.get("rasgos", ""))]).strip()
        if combo:
            setv("b3_autor_vestimenta_rasgos", combo)
        setv("b3_autor_direccion", autor.get("direccion_fuga") or val("b3_autor_direccion"))
        setv("b3_autor_conoce", autor.get("lo_conoce") or val("b3_autor_conoce"))

    # Si no trajo situaciones, detectarlas del relato.
    if not val("b3_situaciones_confirmadas"):
        setv("b3_situaciones_confirmadas", detectar_situaciones(val("b3_relato_crudo")))


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


def construir_relato_final():
    partes = []
    crudo = val("b3_relato_crudo").strip()
    if crudo:
        partes.append(crudo)
    partes.extend(construir_fragmentos_guia())
    final = "\n\n".join(partes).strip()
    setv("b3_relato_final", final)
    return final


def construir_noticia_criminis():
    # Esta no es el relato de entrevista: es resumen policial para Acta de Procedimiento.
    nom = nombre_victima() or "la persona entrevistada"
    dni = val("b3_dni")
    intro = f"Seguidamente se entrevista a quien dijo llamarse {nom}"
    if dni:
        intro += f", DNI Nro. {dni}"
    intro += ", quien manifestó que "

    texto_base = val("b3_relato_final").strip() or construir_relato_final() or val("b3_relato_crudo").strip()
    texto_base = " ".join(texto_base.split())
    if len(texto_base) > 900:
        texto_base = texto_base[:900].rsplit(" ", 1)[0] + "..."
    noticia = intro + (texto_base if texto_base else "aportó datos vinculados al hecho investigado")
    if not noticia.endswith("."):
        noticia += "."
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
    if not val("b3_relato_final").strip():
        construir_relato_final()

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
        f"se procede a recibir entrevista a la persona que se individualiza a continuacion, "
        f"en relacion a las presentes actuaciones."
    )
    pdf_multi(pdf, apertura)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DATOS DE IDENTIDAD", ln=True)
    pdf.set_font("Arial", "", 10)
    f = filiacion_victima()
    datos = (
        f"Condicion: {f.get('condicion','')}\n"
        f"Apellido y nombre: {f.get('apellido','')}, {f.get('nombre','')}\n"
        f"DNI: {f.get('dni','')}\n"
        f"Edad: {f.get('edad','')}\n"
        f"Fecha de nacimiento: {f.get('fecha_nacimiento','')}\n"
        f"Nacionalidad: {f.get('nacionalidad','')}\n"
        f"Estado civil: {f.get('estado_civil','')}\n"
        f"Profesion/Ocupacion: {f.get('profesion','')}\n"
        f"Domicilio: {f.get('domicilio','')}\n"
        f"Telefono/Celular: {f.get('telefono','')} {f.get('celular','')}"
    )
    pdf_multi(pdf, datos)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "FACULTAD DE ABSTENCION", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "Se hace saber a la persona entrevistada la facultad legal de abstenerse de declarar cuando correspondiere por vinculo familiar u otra situacion legalmente contemplada, manifestando quedar debidamente anoticiada.")
    pdf.ln(3)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "RELATO", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, val("b3_relato_final"), alto=7)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "CIERRE", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "No siendo para mas, previa integra lectura y ratificacion de su contenido, se da por finalizado el presente acto, firmando al pie para constancia.")
    pdf.ln(15)
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

    # Hoja 2 - Derechos de la Victima
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
    pdf.ln(15)
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
    if not val("b3_relato_final").strip():
        construir_relato_final()
    if not val("b3_noticia_criminis").strip():
        construir_noticia_criminis()

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
            "situaciones_detectadas": detectar_situaciones(val("b3_relato_crudo")),
            "situaciones_confirmadas": val("b3_situaciones_confirmadas", []),
            "situacion_otro": val("b3_situacion_otro"),
        },
        "respuestas_guia": respuestas_guia,
        "relato_final": val("b3_relato_final"),
        "noticia_criminis": val("b3_noticia_criminis"),
        "derechos_victima": {
            "notificada": "SI",
            "documento_generado": "SI",
            "incluido_en_pdf_completo": "SI"
        },
        "firma": {
            "tipo": val("b3_modo_firma"),
            "firma_canvas_base64": "[firma digital guardada]" if val("b3_firma_canvas_b64") else "",
            "firma_subida_nombre": val("b3_firma_subida_nombre"),
            "firma_subida_base64": "[firma subida guardada]" if val("b3_firma_subida_b64") else "",
        }
    }

    return {
        "sistema": "S.I.V.A.P. — Sistema Integrado de Validación de Actuaciones Policiales",
        "tipo_archivo": "colaboracion_json",
        "bloque": "BLOQUE_3_ENTREVISTA_VICTIMA",
        "autor_carga": autor_carga,
        "actuacion": actuacion,
        "datos_bloque": datos_bloque,
        "datos_completos_bloque": datos_bloque,
        "resumen_para_acta_procedimiento": {
            "tipo": "victima_damnificado",
            "nombre": nombre_victima(),
            "dni": val("b3_dni"),
            "domicilio": val("b3_domicilio"),
            "texto_para_acta": val("b3_noticia_criminis"),
            "incorporar": True
        },
        "fecha_exportacion": datetime.now().isoformat()
    }


def nombre_archivo_json():
    nro = re.sub(r"[^A-Za-z0-9_-]+", "_", val("b3_numero_acta") or "SIN_ACTA")
    ni = re.sub(r"[^A-Za-z0-9_-]+", "", val("b3_ni_policial") or "SIN_NI")
    return f"SIVAP_ACTA_{nro}_BLOQUE_3_VICTIMA_NI_{ni}.json"

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
                    importar_json_bloque3(data)
                    st.success("Datos incorporados. Revise las pestañas siguientes y corrija lo necesario.")
                    if GUARDADO_OK:
                        try:
                            autoguardar_bloque(BLOQUE_ID)
                        except Exception:
                            pass
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

    opciones = [
        "Amenazas",
        "Lesiones",
        "Robo con arma",
        "Robo / sustracción",
        "Hurto",
        "Daño",
        "Violencia familiar / contexto familiar",
        "Aprehensión / retención vinculada",
        "Cámaras / testigos / evidencia",
        "Otro"
    ]
    if not val("b3_situaciones_confirmadas") and detectadas:
        st.session_state["b3_situaciones_confirmadas"] = detectadas

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
            construir_relato_final()
            st.success("Relato final actualizado.")
    with c2:
        if st.button("🚓 Generar / actualizar noticia criminis", use_container_width=True):
            construir_noticia_criminis()
            st.success("Noticia criminis actualizada.")

    st.text_area("Relato final de entrevista", key="b3_relato_final", height=360)
    st.text_area("Súper resumen / noticia criminis para Acta de Procedimiento", key="b3_noticia_criminis", height=180)

# 5 Firma / PDF / JSON
with tabs[5]:
    st.subheader("Firma, PDF completo y JSON")
    st.info("El PDF completo genera Hoja 1: Acta de Entrevista y Hoja 2: Derechos de la Víctima. No requiere cargar campos adicionales de derechos.")

    st.selectbox("Modo de firma", ["Firma digital en pantalla", "Subir foto de firma", "Sin firma digital"], key="b3_modo_firma")

    if val("b3_modo_firma") == "Firma digital en pantalla":
        if CANVAS_OK:
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 1)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=160,
                width=500,
                drawing_mode="freedraw",
                key="b3_canvas_firma"
            )
            if canvas_result is not None and canvas_result.image_data is not None:
                try:
                    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
                    fondo = Image.new("RGB", img.size, (255, 255, 255))
                    fondo.paste(img, mask=img.split()[3])
                    buf = io.BytesIO()
                    fondo.save(buf, format="PNG")
                    setv("b3_firma_canvas_b64", base64.b64encode(buf.getvalue()).decode("utf-8"))
                except Exception:
                    pass
        else:
            st.warning("Canvas no disponible. Use la opción 'Subir foto de firma'.")

    if val("b3_modo_firma") == "Subir foto de firma":
        firma_file = st.file_uploader("Subir foto de firma", type=["jpg", "jpeg", "png"], key="b3_upload_firma")
        if firma_file:
            b = firma_file.getvalue()
            setv("b3_firma_subida_nombre", firma_file.name)
            setv("b3_firma_subida_b64", base64.b64encode(b).decode("utf-8"))
            st.image(b, caption="Firma subida", width=300)

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
