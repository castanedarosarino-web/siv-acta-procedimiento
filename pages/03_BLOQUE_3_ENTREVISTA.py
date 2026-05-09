import streamlit as st
import json
import io
import os
import base64
import tempfile
from datetime import datetime, date
from fpdf import FPDF

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_OK = True
except Exception:
    CANVAS_OK = False

try:
    from PIL import Image
    PIL_OK = True
except Exception:
    PIL_OK = False

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_GLOBAL_OK = True
except Exception:
    GUARDADO_GLOBAL_OK = False

st.set_page_config(page_title="S.I.V.A.P. - Bloque 3 Entrevista", layout="wide")

BLOQUE_ID = "BLOQUE_3_ENTREVISTA"
LEMA = "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora."

if GUARDADO_GLOBAL_OK:
    try:
        iniciar_guardado_seguro(BLOQUE_ID)
        panel_guardado_seguro(BLOQUE_ID)
    except Exception:
        pass

# ============================================================
# ESTADO / GUARDADO SEGURO LOCAL DEL BLOQUE
# ============================================================

def set_default(k, v=""):
    if k not in st.session_state:
        st.session_state[k] = v


def init_bloque3():
    iniciales = {
        # Datos administrativos / entrevista
        "b3_lugar_entrevista": "Rosario",
        "b3_fecha_entrevista": str(date.today()),
        "b3_hora_entrevista": datetime.now().strftime("%H:%M"),
        "b3_dependencia_acta": "",
        "b3_personal_actuante": "",
        # Identificacion victima
        "b3_condicion": "Víctima/Damnificado",
        "b3_apellido": "",
        "b3_nombre": "",
        "b3_dni": "",
        "b3_edad": "",
        "b3_fecha_nacimiento": "",
        "b3_nacionalidad": "ARGENTINA",
        "b3_estado_civil": "",
        "b3_profesion": "",
        "b3_domicilio": "",
        "b3_telefono": "",
        "b3_celular": "",
        "b3_correo": "",
        # Relato
        "b3_relato_crudo": "",
        # Analisis
        "b3_situaciones_confirmadas": [],
        "b3_situacion_otro": "",
        # Autor / aprehendido
        "b3_autor_descripcion": "",
        "b3_autor_vestimenta": "",
        "b3_autor_contextura": "",
        "b3_autor_edad_aprox": "",
        "b3_autor_rasgos": "",
        "b3_autor_arma_elemento": "",
        "b3_autor_direccion_fuga": "",
        "b3_autor_lo_vio_bien": "",
        "b3_autor_lo_conoce": "",
        "b3_autor_podria_reconocerlo": "",
        "b3_autor_aprehendido_mismo": "",
        # Amenazas
        "b3_amenaza_frase_textual": "",
        "b3_amenaza_amedrentamiento": "",
        "b3_amenaza_temor_integridad": "",
        "b3_amenaza_contexto": "",
        "b3_amenaza_medio": "",
        "b3_amenaza_vinculo": "",
        # Lesiones
        "b3_lesiones_como": "",
        "b3_lesiones_zona": "",
        "b3_lesiones_asistencia": "",
        "b3_lesiones_instancia": "",
        # Robo / hurto
        "b3_robo_elementos": "",
        "b3_robo_modo": "",
        "b3_robo_arma": "",
        "b3_robo_recupero": "",
        # Genericas / evidencia
        "b3_testigos_camaras": "",
        "b3_evidencia_digital": "",
        "b3_preguntas_genericas": "",
        # Resguardo testimonio
        "b3_resguardo_opciones": [],
        "b3_resguardo_otro": "",
        "b3_resguardo_constancia_editable": "",
        # Productos
        "b3_relato_final": "",
        "b3_noticia_criminis": "",
        # Derechos victima
        "b3_derechos_victima_notificada": "SI",
        "b3_derechos_victima_domicilio_notificaciones": "",
        "b3_derechos_victima_telefono_notificaciones": "",
        "b3_derechos_victima_correo_notificaciones": "",
        "b3_derechos_victima_observaciones": "",
        # Firma
        "b3_modo_firma": "Sin firma digital",
        "b3_firma_base64": "",
        "b3_firma_subida_base64": "",
        "b3_firma_subida_nombre": "",
    }
    for k, v in iniciales.items():
        set_default(k, v)


init_bloque3()


def val(k, default=""):
    return st.session_state.get(k, default)


def limpiar_pdf(txt):
    txt = "" if txt is None else str(txt)
    repl = {
        "—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N"
    }
    for a, b in repl.items():
        txt = txt.replace(a, b)
    return txt


def pdf_multi(pdf, txt, alto=6):
    """
    Wrapper seguro para FPDF.
    Evita el error: Not enough horizontal space to render a single character,
    que aparece cuando multi_cell se ejecuta con el cursor X corrido hacia la derecha
    despues de un cell() anterior.
    """
    texto = limpiar_pdf(txt)
    try:
        pdf.set_x(pdf.l_margin)
        ancho = pdf.w - pdf.l_margin - pdf.r_margin
        if ancho <= 20:
            ancho = 170
        pdf.multi_cell(ancho, alto, texto)
        pdf.set_x(pdf.l_margin)
    except Exception:
        # Ultimo respaldo: cortar lineas largas y escribirlas como celdas simples
        pdf.set_x(pdf.l_margin)
        ancho = pdf.w - pdf.l_margin - pdf.r_margin
        max_chars = 95
        for linea in str(texto).split("\n"):
            while len(linea) > max_chars:
                corte = linea.rfind(" ", 0, max_chars)
                if corte <= 0:
                    corte = max_chars
                pdf.cell(ancho, alto, linea[:corte], ln=True)
                linea = linea[corte:].lstrip()
            pdf.cell(ancho, alto, linea, ln=True)
        pdf.set_x(pdf.l_margin)


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="ignore")
    return bytes(salida)


# ============================================================
# DETECCION / SITUACIONES
# ============================================================

def detectar_situaciones(relato):
    t = (relato or "").lower()
    detectadas = []

    def add(x):
        if x not in detectadas:
            detectadas.append(x)

    if any(p in t for p in ["amenaz", "te voy a matar", "te voy a prender", "amedrent", "intimid"]):
        add("Amenazas")
    if any(p in t for p in ["golp", "lesion", "lesión", "herid", "sangre", "hematoma", "dolor", "certificado", "hospital"]):
        add("Lesiones")
    if any(p in t for p in ["robo", "robó", "robar", "sustra", "arrebat", "apoder", "cuchillo", "arma", "pistola", "revólver", "revolver"]):
        add("Robo / Robo con arma")
    if any(p in t for p in ["hurto", "faltante", "sin violencia", "me sacaron"]):
        add("Hurto / Sustracción")
    if any(p in t for p in ["daño", "romp", "rotura", "vidrio"]):
        add("Daño")
    if any(p in t for p in ["pareja", "ex pareja", "violencia familiar", "conviviente", "exconviviente", "género", "genero"]):
        add("Violencia familiar / contexto familiar")
    if any(p in t for p in ["cámara", "camara", "filmación", "filmacion", "video", "whatsapp", "captura", "testigo"]):
        add("Cámaras / testigos / evidencia digital")
    return detectadas


def situaciones_trabajadas():
    s = list(val("b3_situaciones_confirmadas", []))
    otro = val("b3_situacion_otro", "").strip()
    if otro and otro not in s:
        s.append(otro)
    return s


def hay(cat):
    s = " | ".join(situaciones_trabajadas()).lower()
    cat = cat.lower()
    if cat == "amenazas":
        return "amenaza" in s
    if cat == "lesiones":
        return "lesion" in s or "lesión" in s
    if cat == "robo":
        return "robo" in s or "arma" in s
    if cat == "hurto":
        return "hurto" in s or "sustracción" in s or "sustraccion" in s
    if cat == "evidencia":
        return "cámara" in s or "camara" in s or "testigo" in s or "evidencia" in s
    return cat in s


# ============================================================
# TEXTO / RELATO / NOTICIA
# ============================================================

def nombre_victima():
    nombre = f"{val('b3_apellido').strip()}, {val('b3_nombre').strip()}".strip(", ").strip()
    return nombre or "la persona entrevistada"


def construir_constancia_resguardo():
    opciones = val("b3_resguardo_opciones", []) or []
    otro = val("b3_resguardo_otro", "").strip()
    partes = []
    if opciones:
        partes.append("Se deja constancia que " + "; ".join(opciones).lower() + ".")
    if otro:
        partes.append(otro)
    return " ".join(partes).strip()


def construir_fragmento_autor():
    frases = []
    if val("b3_autor_descripcion").strip():
        frases.append(f"Manifiesto que la persona que cometió el hecho era {val('b3_autor_descripcion').strip()}.")
    if val("b3_autor_vestimenta").strip():
        frases.append(f"Vestía {val('b3_autor_vestimenta').strip()}.")
    if val("b3_autor_contextura").strip():
        frases.append(f"Su contextura física era {val('b3_autor_contextura').strip()}.")
    if val("b3_autor_edad_aprox").strip():
        frases.append(f"Estimo que tendría aproximadamente {val('b3_autor_edad_aprox').strip()} años de edad.")
    if val("b3_autor_rasgos").strip():
        frases.append(f"Como rasgos o señas particulares indico: {val('b3_autor_rasgos').strip()}.")
    if val("b3_autor_arma_elemento").strip():
        frases.append(f"Utilizó o exhibió {val('b3_autor_arma_elemento').strip()}.")
    if val("b3_autor_direccion_fuga").strip():
        frases.append(f"Luego del hecho se retiró o fugó en dirección hacia {val('b3_autor_direccion_fuga').strip()}.")
    if val("b3_autor_lo_vio_bien").strip():
        frases.append(f"Respecto de si pude observarlo correctamente, manifiesto que {val('b3_autor_lo_vio_bien').strip()}.")
    if val("b3_autor_lo_conoce").strip():
        frases.append(f"En cuanto a si lo conozco, manifiesto que {val('b3_autor_lo_conoce').strip()}.")
    if val("b3_autor_podria_reconocerlo").strip():
        frases.append(f"Consultado/a si podría reconocerlo, manifiesto que {val('b3_autor_podria_reconocerlo').strip()}.")
    if val("b3_autor_aprehendido_mismo").strip():
        frases.append(f"Respecto de la persona retenida/aprehendida, manifiesto que {val('b3_autor_aprehendido_mismo').strip()}.")
    return " ".join(frases)


def construir_fragmento_amenazas():
    frases = []
    if val("b3_amenaza_frase_textual").strip():
        frases.append(f"Manifiesto que la amenaza recibida fue textualmente: '{val('b3_amenaza_frase_textual').strip()}'.")
    if val("b3_amenaza_amedrentamiento").strip():
        frases.append(f"Ante dicha expresión, {val('b3_amenaza_amedrentamiento').strip()}.")
    if val("b3_amenaza_temor_integridad").strip():
        frases.append(f"Asimismo manifiesto que {val('b3_amenaza_temor_integridad').strip()}.")
    if val("b3_amenaza_contexto").strip():
        frases.append(f"La amenaza ocurrió en el siguiente contexto: {val('b3_amenaza_contexto').strip()}.")
    if val("b3_amenaza_medio").strip():
        frases.append(f"El medio utilizado fue: {val('b3_amenaza_medio').strip()}.")
    if val("b3_amenaza_vinculo").strip():
        frases.append(f"Respecto del vínculo con el autor, manifiesto que {val('b3_amenaza_vinculo').strip()}.")
    return " ".join(frases)


def construir_fragmento_lesiones():
    frases = []
    if val("b3_lesiones_como").strip():
        frases.append(f"Manifiesto que las lesiones se produjeron de la siguiente manera: {val('b3_lesiones_como').strip()}.")
    if val("b3_lesiones_zona").strip():
        frases.append(f"Las zonas del cuerpo afectadas fueron: {val('b3_lesiones_zona').strip()}.")
    if val("b3_lesiones_asistencia").strip():
        frases.append(f"Respecto de la asistencia médica, manifiesto que {val('b3_lesiones_asistencia').strip()}.")
    inst = val("b3_lesiones_instancia", "").strip()
    if inst == "Sí":
        frases.append("En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas.")
    elif inst == "No":
        frases.append("En este acto manifiesto que no es mi deseo instar la acción penal por las lesiones sufridas.")
    elif inst == "Desea pensarlo / no responde":
        frases.append("Consultado/a respecto de la instancia penal por las lesiones sufridas, manifiesto que deseo pensarlo o no respondo en este acto.")
    return " ".join(frases)


def construir_fragmento_robo():
    frases = []
    if val("b3_robo_elementos").strip():
        frases.append(f"Manifiesto que me sustrajeron o intentaron sustraer: {val('b3_robo_elementos').strip()}.")
    if val("b3_robo_modo").strip():
        frases.append(f"Respecto de la forma en que ocurrió el hecho, manifiesto que {val('b3_robo_modo').strip()}.")
    if val("b3_robo_arma").strip():
        frases.append(f"El arma o elemento utilizado fue: {val('b3_robo_arma').strip()}.")
    if val("b3_robo_recupero").strip():
        frases.append(f"En cuanto al recupero de elementos, manifiesto que {val('b3_robo_recupero').strip()}.")
    return " ".join(frases)


def construir_fragmento_evidencia():
    frases = []
    if val("b3_testigos_camaras").strip():
        frases.append(f"Sobre testigos, cámaras o filmaciones, manifiesto que {val('b3_testigos_camaras').strip()}.")
    if val("b3_evidencia_digital").strip():
        frases.append(f"Respecto de evidencia digital, capturas o mensajes, manifiesto que {val('b3_evidencia_digital').strip()}.")
    if val("b3_preguntas_genericas").strip():
        frases.append(val("b3_preguntas_genericas").strip())
    return " ".join(frases)


def construir_relato_final_sin_guardar():
    partes = []
    relato = val("b3_relato_crudo", "").strip()
    if relato:
        partes.append(relato)
    for frag in [
        construir_fragmento_autor(),
        construir_fragmento_robo(),
        construir_fragmento_amenazas(),
        construir_fragmento_lesiones(),
        construir_fragmento_evidencia(),
        val("b3_resguardo_constancia_editable", "").strip() or construir_constancia_resguardo(),
    ]:
        if frag and frag.strip():
            partes.append(frag.strip())
    return "\n\n".join(partes).strip()


def construir_noticia_criminis_sin_guardar():
    nombre = nombre_victima()
    dni = val("b3_dni", "").strip()
    intro = f"Seguidamente se entrevista a quien dijo llamarse {nombre}"
    if dni:
        intro += f", DNI N° {dni}"
    intro += ", quien manifestó que "

    hechos = []
    relato = val("b3_relato_crudo", "").strip()
    if relato:
        hechos.append(relato)
    if val("b3_robo_elementos").strip():
        hechos.append(f"le sustrajeron o intentaron sustraer {val('b3_robo_elementos').strip()}")
    if val("b3_robo_arma").strip() or val("b3_autor_arma_elemento").strip():
        arma = val("b3_robo_arma", "").strip() or val("b3_autor_arma_elemento", "").strip()
        hechos.append(f"el autor utilizó o exhibió {arma}")
    desc = []
    for k in ["b3_autor_descripcion", "b3_autor_vestimenta", "b3_autor_contextura", "b3_autor_rasgos"]:
        if val(k).strip():
            desc.append(val(k).strip())
    if desc:
        hechos.append("describe al autor como " + ", ".join(desc))
    if val("b3_lesiones_zona").strip() or val("b3_lesiones_como").strip():
        hechos.append("resultó lesionado/a " + (val("b3_lesiones_zona").strip() or val("b3_lesiones_como").strip()))
    if val("b3_autor_aprehendido_mismo").strip():
        hechos.append(f"respecto de la persona retenida/aprehendida manifestó que {val('b3_autor_aprehendido_mismo').strip()}")
    if val("b3_robo_recupero").strip():
        hechos.append(f"en relación al elemento recuperado manifestó que {val('b3_robo_recupero').strip()}")

    cuerpo = "; asimismo, ".join([h.strip().rstrip(".") for h in hechos if h.strip()]) or "aportó datos de interés para las presentes actuaciones"
    return (intro + cuerpo + ".").replace("..", ".")


# ============================================================
# PDF
# ============================================================

def encabezado_pdf(pdf, titulo):
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "UNIDAD REGIONAL II - ROSARIO", ln=True, align="C")
    dep = val("b3_dependencia_acta") or st.session_state.get("dependencia", "")
    if dep:
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, limpiar_pdf(dep).upper(), ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, limpiar_pdf(titulo), ln=True, align="C")
    pdf.ln(4)


def obtener_firma_temp():
    b64 = val("b3_firma_base64") or val("b3_firma_subida_base64")
    if not b64:
        return None
    try:
        data = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception:
        return None


def insertar_firma(pdf, firma_path):
    if firma_path and os.path.exists(firma_path):
        try:
            pdf.image(firma_path, x=25, w=70)
            pdf.ln(6)
        except Exception:
            pass


def generar_pdf_acta_entrevista(relato_final=None):
    relato_final = relato_final or val("b3_relato_final") or construir_relato_final_sin_guardar()
    firma_path = obtener_firma_temp()
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    encabezado_pdf(pdf, "ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO")
    pdf.set_font("Arial", "", 10)
    apertura = (
        f"En la ciudad de {val('b3_lugar_entrevista')}, a fecha {val('b3_fecha_entrevista')}, siendo las {val('b3_hora_entrevista')} horas, "
        f"personal policial actuante procede a entrevistar a una persona en caracter de {val('b3_condicion')}, en relacion a las presentes actuaciones."
    )
    pdf_multi(pdf, apertura)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DATOS DE IDENTIDAD", ln=True)
    pdf.set_font("Arial", "", 10)
    datos = (
        f"Apellido y nombres: {val('b3_apellido')}, {val('b3_nombre')}\n"
        f"DNI: {val('b3_dni')}\nEdad: {val('b3_edad')}\nFecha de nacimiento: {val('b3_fecha_nacimiento')}\n"
        f"Nacionalidad: {val('b3_nacionalidad')}\nEstado civil: {val('b3_estado_civil')}\nProfesion/Ocupacion: {val('b3_profesion')}\n"
        f"Domicilio: {val('b3_domicilio')}\nTelefono/Celular: {val('b3_telefono')} / {val('b3_celular')}\nCorreo: {val('b3_correo')}"
    )
    pdf_multi(pdf, datos)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "FACULTAD DE ABSTENCION", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "Previo al acto, se hace saber a la persona entrevistada la facultad de abstenerse de declarar cuando correspondiere por vinculo familiar u otra situacion legalmente contemplada, manifestando quedar debidamente anoticiada.")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "RELATO", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, relato_final)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "CIERRE", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, "No siendo para mas, previa integra lectura y ratificacion de su contenido, se da por finalizado el presente acto, firmando al pie para constancia.")
    pdf.ln(8)
    if firma_path:
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, "Firma digital incorporada:", ln=True)
        insertar_firma(pdf, firma_path)
    pdf.ln(8)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion entrevistado/a", ln=False, align="C")
    pdf.cell(85, 6, "Firma personal policial", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 9)
    pdf_multi(pdf, f"Personal actuante: {val('b3_personal_actuante')}", alto=5)
    return pdf_bytes(pdf)


def generar_pdf_derechos_victima():
    firma_path = obtener_firma_temp()
    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    encabezado_pdf(pdf, "NOTIFICACION DE DERECHOS DE LA VICTIMA")
    pdf.set_font("Arial", "", 10)
    apertura = (
        f"En la ciudad de {val('b3_lugar_entrevista')}, a fecha {val('b3_fecha_entrevista')}, siendo las {val('b3_hora_entrevista')} horas, "
        f"personal policial actuante procede a notificar a {nombre_victima()}, DNI Nro. {val('b3_dni')}, domiciliado/a en {val('b3_domicilio')}, "
        "respecto de los derechos que le asisten en su caracter de victima/damnificado/a en las presentes actuaciones."
    )
    pdf_multi(pdf, apertura)
    pdf.ln(3)
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
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DOMICILIO / MEDIOS PARA NOTIFICACIONES", ln=True)
    pdf.set_font("Arial", "", 10)
    medios = f"Domicilio: {val('b3_derechos_victima_domicilio_notificaciones')}\nTelefono: {val('b3_derechos_victima_telefono_notificaciones')}\nCorreo electronico: {val('b3_derechos_victima_correo_notificaciones')}"
    pdf_multi(pdf, medios)
    if val("b3_derechos_victima_observaciones").strip():
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "OBSERVACIONES", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf_multi(pdf, val("b3_derechos_victima_observaciones"))
    pdf.ln(5)
    pdf_multi(pdf, "Leida que le fuera la presente, la persona notificada manifiesta quedar debidamente anoticiada de los derechos precedentemente informados, firmando al pie para constancia.")
    pdf.ln(8)
    if firma_path:
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, "Firma digital incorporada:", ln=True)
        insertar_firma(pdf, firma_path)
    pdf.ln(8)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion de la victima", ln=False, align="C")
    pdf.cell(85, 6, "Firma personal policial", ln=True, align="C")
    return pdf_bytes(pdf)


def armar_json_exportacion():
    identidad = st.session_state.get("identidad_policial", {})
    actuacion = st.session_state.get("actuacion", {})
    return {
        "sistema": "S.I.V.A.P. - Sistema Integrado de Validacion de Actuaciones Policiales",
        "lema": LEMA,
        "modulo": BLOQUE_ID,
        "autor_carga": identidad,
        "actuacion": actuacion,
        "datos_entrevista": {
            "lugar": val("b3_lugar_entrevista"),
            "fecha": val("b3_fecha_entrevista"),
            "hora": val("b3_hora_entrevista"),
            "dependencia": val("b3_dependencia_acta"),
            "personal_actuante": val("b3_personal_actuante"),
            "victima": {k.replace("b3_", ""): val(k) for k in ["b3_condicion", "b3_apellido", "b3_nombre", "b3_dni", "b3_edad", "b3_fecha_nacimiento", "b3_nacionalidad", "b3_estado_civil", "b3_profesion", "b3_domicilio", "b3_telefono", "b3_celular", "b3_correo"]},
            "relato_crudo": val("b3_relato_crudo"),
            "situaciones_detectadas": detectar_situaciones(val("b3_relato_crudo")),
            "situaciones_confirmadas": situaciones_trabajadas(),
            "respuestas_guia": {
                "descripcion_autor": {"descripcion": val("b3_autor_descripcion"), "vestimenta": val("b3_autor_vestimenta"), "contextura": val("b3_autor_contextura"), "edad_aproximada": val("b3_autor_edad_aprox"), "rasgos": val("b3_autor_rasgos"), "arma_elemento": val("b3_autor_arma_elemento"), "direccion_fuga": val("b3_autor_direccion_fuga"), "lo_vio_bien": val("b3_autor_lo_vio_bien"), "lo_conoce": val("b3_autor_lo_conoce"), "podria_reconocerlo": val("b3_autor_podria_reconocerlo"), "aprehendido_es_mismo": val("b3_autor_aprehendido_mismo")},
                "amenazas": {"frase_textual": val("b3_amenaza_frase_textual"), "amedrentamiento": val("b3_amenaza_amedrentamiento"), "temor_integridad": val("b3_amenaza_temor_integridad"), "contexto": val("b3_amenaza_contexto"), "medio": val("b3_amenaza_medio"), "vinculo": val("b3_amenaza_vinculo")},
                "lesiones": {"como": val("b3_lesiones_como"), "zona": val("b3_lesiones_zona"), "asistencia": val("b3_lesiones_asistencia"), "instancia_penal": val("b3_lesiones_instancia")},
                "robo": {"elementos": val("b3_robo_elementos"), "modo": val("b3_robo_modo"), "arma": val("b3_robo_arma"), "recupero": val("b3_robo_recupero")},
                "resguardo_testimonio": {"opciones": val("b3_resguardo_opciones", []), "otro": val("b3_resguardo_otro"), "constancia": val("b3_resguardo_constancia_editable")},
            },
            "relato_final": val("b3_relato_final"),
            "noticia_criminis": val("b3_noticia_criminis"),
            "derechos_victima": {"notificada": val("b3_derechos_victima_notificada"), "domicilio_notificaciones": val("b3_derechos_victima_domicilio_notificaciones"), "telefono_notificaciones": val("b3_derechos_victima_telefono_notificaciones"), "correo_notificaciones": val("b3_derechos_victima_correo_notificaciones"), "observaciones": val("b3_derechos_victima_observaciones")},
        },
        "fecha_exportacion": datetime.now().isoformat()
    }


# ============================================================
# INTERFAZ
# ============================================================

st.title("🚓 BLOQUE 3 - ENTREVISTA A VÍCTIMA / DAMNIFICADO")
st.caption(LEMA)

# Botones que modifican estado ANTES de instanciar widgets dependientes
# Se ubican dentro de cada pestaña antes de sus text_area correspondientes.

tabs = st.tabs(["1. Identificación", "2. Relato", "3. Análisis S.I.V.A.P.", "4. Relato final / Noticia criminis", "5. Firma / PDF / JSON"])

with tabs[0]:
    st.subheader("Identificación de víctima / damnificado")
    c0, c1, c2 = st.columns(3)
    with c0:
        st.text_input("Lugar de entrevista", key="b3_lugar_entrevista")
        st.text_input("Fecha", key="b3_fecha_entrevista")
        st.text_input("Hora", key="b3_hora_entrevista")
    with c1:
        st.text_input("Dependencia", key="b3_dependencia_acta")
        st.text_input("Personal policial actuante", key="b3_personal_actuante")
    with c2:
        st.selectbox("Condición", ["Víctima/Damnificado", "Representante legal", "Progenitor/a", "Otro"], key="b3_condicion")

    st.divider()
    a, b = st.columns(2)
    with a:
        st.text_input("Apellido", key="b3_apellido")
        st.text_input("Nombre", key="b3_nombre")
        st.text_input("DNI", key="b3_dni")
        st.text_input("Edad", key="b3_edad")
        st.text_input("Fecha de nacimiento", key="b3_fecha_nacimiento")
        st.text_input("Nacionalidad", key="b3_nacionalidad")
    with b:
        st.text_input("Estado civil", key="b3_estado_civil")
        st.text_input("Profesión / Ocupación", key="b3_profesion")
        st.text_area("Domicilio", key="b3_domicilio", height=80)
        st.text_input("Teléfono fijo", key="b3_telefono")
        st.text_input("Celular", key="b3_celular")
        st.text_input("Correo electrónico", key="b3_correo")

with tabs[1]:
    st.subheader("Relato inicial")
    st.info("Esta pestaña conserva el relato crudo de la víctima/damnificado. Luego S.I.V.A.P. lo ordena con las respuestas de guía.")
    st.text_area("Relato inicial de la víctima / damnificado", key="b3_relato_crudo", height=360)

with tabs[2]:
    st.subheader("Análisis S.I.V.A.P. - guía interna")
    detectadas = detectar_situaciones(val("b3_relato_crudo"))
    if detectadas:
        st.success("Del relato se observan posibles delitos/situaciones: " + ", ".join(detectadas))
    else:
        st.warning("Del relato no se detectaron automáticamente delitos/situaciones. Puede agregarse manualmente.")
    opciones = ["Amenazas", "Lesiones", "Robo / Robo con arma", "Hurto / Sustracción", "Daño", "Violencia familiar / contexto familiar", "Cámaras / testigos / evidencia digital", "Otro"]
    # Set default detected before widget instantiation, only if user never selected anything
    if not val("b3_situaciones_confirmadas", []) and detectadas:
        st.session_state["b3_situaciones_confirmadas"] = [d for d in detectadas if d in opciones]
    st.multiselect("Confirmar situaciones a trabajar", opciones, key="b3_situaciones_confirmadas")
    st.text_input("Agregar manualmente otro delito/situación no detectado", key="b3_situacion_otro")

    st.divider()
    st.subheader("Descripción del autor y conexión con aprehendido")
    st.caption("Estas preguntas son guía interna. No salen como cuestionario: alimentan el relato final como dichos de la víctima.")
    ca, cb = st.columns(2)
    with ca:
        st.text_area("¿Cómo era la persona que cometió el hecho?", key="b3_autor_descripcion", height=90)
        st.text_input("Vestimenta", key="b3_autor_vestimenta")
        st.text_input("Contextura física", key="b3_autor_contextura")
        st.text_input("Edad aproximada", key="b3_autor_edad_aprox")
        st.text_area("Rasgos / señas particulares", key="b3_autor_rasgos", height=80)
        st.text_input("Arma o elemento usado / exhibido", key="b3_autor_arma_elemento")
    with cb:
        st.text_input("Dirección de fuga", key="b3_autor_direccion_fuga")
        st.selectbox("¿Lo vio bien?", ["", "sí", "no", "parcialmente"], key="b3_autor_lo_vio_bien")
        st.text_input("¿Lo conoce? ¿De dónde?", key="b3_autor_lo_conoce")
        st.selectbox("¿Podría reconocerlo?", ["", "sí", "no", "cree que sí", "no está seguro/a"], key="b3_autor_podria_reconocerlo")
        st.text_area("¿La persona retenida/aprehendida es la misma que robó, amenazó o lesionó?", key="b3_autor_aprehendido_mismo", height=115)

    if hay("robo") or hay("hurto"):
        st.divider()
        st.subheader("Guía interna - Robo / Robo con arma / Sustracción")
        st.text_area("Elementos sustraídos o que intentaron sustraer", key="b3_robo_elementos", height=90)
        st.text_area("Modo de comisión del hecho", key="b3_robo_modo", height=90)
        st.text_input("Arma o elemento utilizado", key="b3_robo_arma")
        st.text_area("Recupero de elementos / secuestro vinculado", key="b3_robo_recupero", height=80)

    if hay("amenazas"):
        st.divider()
        st.subheader("Guía interna - Amenazas")
        st.text_input("Frase textual de la amenaza", key="b3_amenaza_frase_textual")
        st.text_area("¿Se sintió amedrentada/intimidada?", key="b3_amenaza_amedrentamiento", height=80, placeholder="Ej: sentí mucho temor y me sentí amedrentada...")
        st.text_area("¿Teme por su integridad física?", key="b3_amenaza_temor_integridad", height=80, placeholder="Ej: desde ese momento temo por mi integridad física...")
        st.text_area("Contexto de la amenaza", key="b3_amenaza_contexto", height=80)
        st.text_input("Medio utilizado", key="b3_amenaza_medio")
        st.text_input("Vínculo con el autor", key="b3_amenaza_vinculo")
        st.info("No se pregunta instancia penal en amenazas. Se precisa frase textual, temor, amedrentamiento, contexto, medio y vínculo.")

    if hay("lesiones") or hay("robo"):
        st.divider()
        st.subheader("Guía interna - Lesiones")
        st.text_area("¿Cómo se produjo la lesión?", key="b3_lesiones_como", height=85)
        st.text_area("Zona del cuerpo afectada / lesiones observadas", key="b3_lesiones_zona", height=85)
        st.text_area("Asistencia médica / SIES / hospital / certificado", key="b3_lesiones_asistencia", height=85)
        st.selectbox("¿Es su deseo instar la acción penal por las lesiones sufridas?", ["", "Sí", "No", "Desea pensarlo / no responde"], key="b3_lesiones_instancia")

    if hay("evidencia") or True:
        st.divider()
        st.subheader("Testigos, cámaras y evidencia")
        st.text_area("Testigos / cámaras / filmaciones posibles", key="b3_testigos_camaras", height=80)
        st.text_area("Evidencia digital / WhatsApp / capturas / redes", key="b3_evidencia_digital", height=80)
        st.text_area("Otra respuesta útil para integrar al relato", key="b3_preguntas_genericas", height=80)

    st.divider()
    st.subheader("Observación sobre resguardo / no contaminación del testimonio")
    opciones_resguardo = [
        "Víctima entrevistada separada del aprehendido",
        "No hubo contacto visual ni verbal previo",
        "No había aprehendido presente",
        "Entrevista recibida en lugar reservado",
        "Se evitó presencia de familiares/terceros que pudieran influir",
        "No fue posible evitar contacto previo, pero luego se entrevistó por separado",
        "No corresponde",
    ]
    st.multiselect("Seleccione las constancias que correspondan", opciones_resguardo, key="b3_resguardo_opciones")
    st.text_area("Otro / ampliar observación", key="b3_resguardo_otro", height=80)
    const_auto = construir_constancia_resguardo()
    st.caption("Constancia automática sugerida:")
    st.info(const_auto or "Sin constancia automática todavía.")
    if st.button("Usar / actualizar constancia editable de resguardo", key="b3_btn_actualizar_resguardo"):
        st.session_state["b3_resguardo_constancia_editable"] = const_auto
    st.text_area("Constancia breve editable", key="b3_resguardo_constancia_editable", height=100)

with tabs[3]:
    st.subheader("Relato final y noticia criminis")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📝 Generar / actualizar relato final", use_container_width=True, key="b3_btn_generar_relato"):
            st.session_state["b3_relato_final"] = construir_relato_final_sin_guardar()
            st.success("Relato final actualizado sin borrar la noticia criminis.")
    with c2:
        if st.button("🚓 Generar / actualizar noticia criminis", use_container_width=True, key="b3_btn_generar_noticia"):
            st.session_state["b3_noticia_criminis"] = construir_noticia_criminis_sin_guardar()
            st.success("Noticia criminis actualizada sin borrar el relato final.")
    st.text_area("Relato final ordenado", key="b3_relato_final", height=330)
    st.text_area("Súper resumen / noticia criminis para BLOQUE 1 / BLOQUE 8", key="b3_noticia_criminis", height=180)
    st.info("La noticia criminis no reemplaza el acta de entrevista completa. Es un resumen operativo para BLOQUE 1 / BLOQUE 8.")

with tabs[4]:
    st.subheader("Firma, PDF y JSON")
    st.markdown("### Firma")
    st.selectbox("Modo de firma", ["Sin firma digital", "Firma digital en pantalla", "Subir foto de firma"], key="b3_modo_firma")
    if val("b3_modo_firma") == "Firma digital en pantalla":
        if CANVAS_OK:
            st.caption("Firmar dentro del recuadro.")
            canvas = st_canvas(fill_color="rgba(255,255,255,0)", stroke_width=2, stroke_color="#000000", background_color="#FFFFFF", height=180, width=500, drawing_mode="freedraw", key="b3_canvas_firma")
            if canvas.image_data is not None and PIL_OK:
                try:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.session_state["b3_firma_base64"] = base64.b64encode(buf.getvalue()).decode("utf-8")
                    st.image(buf.getvalue(), caption="Vista previa de firma", width=260)
                except Exception:
                    st.warning("No se pudo procesar la firma digital.")
        else:
            st.warning("El canvas no está disponible en este celular/entorno. Puede subir foto de firma.")
    elif val("b3_modo_firma") == "Subir foto de firma":
        up = st.file_uploader("Subir foto de firma", type=["png", "jpg", "jpeg"], key="b3_upload_firma")
        if up is not None:
            data = up.read()
            st.session_state["b3_firma_subida_base64"] = base64.b64encode(data).decode("utf-8")
            st.session_state["b3_firma_subida_nombre"] = up.name
            st.image(data, caption="Vista previa de firma", width=260)
    else:
        st.warning("Todavía no se detecta firma digital. Puede generar el PDF igual, pero sin firma insertada.")

    st.divider()
    st.markdown("### Notificación de Derechos de la Víctima")
    st.radio("¿Se notificaron los derechos de la víctima/damnificado?", ["SI", "NO"], horizontal=True, key="b3_derechos_victima_notificada")
    st.text_area("Domicilio para recibir notificaciones", key="b3_derechos_victima_domicilio_notificaciones", height=70)
    d1, d2 = st.columns(2)
    with d1:
        st.text_input("Teléfono para notificaciones", key="b3_derechos_victima_telefono_notificaciones")
    with d2:
        st.text_input("Correo electrónico para notificaciones", key="b3_derechos_victima_correo_notificaciones")
    st.text_area("Observaciones sobre la notificación de derechos", key="b3_derechos_victima_observaciones", height=80)

    st.divider()
    st.markdown("### Descargas")
    cpdf1, cpdf2, cjson = st.columns(3)
    with cpdf1:
        st.download_button("📄 Descargar Acta de Entrevista", data=generar_pdf_acta_entrevista(), file_name="BLOQUE_3_Acta_Entrevista.pdf", mime="application/pdf", use_container_width=True, key="b3_download_acta")
    with cpdf2:
        st.download_button("📄 Descargar Derechos de la Víctima", data=generar_pdf_derechos_victima(), file_name="BLOQUE_3_Derechos_de_la_Victima.pdf", mime="application/pdf", use_container_width=True, key="b3_download_derechos")
    with cjson:
        json_data = json.dumps(armar_json_exportacion(), ensure_ascii=False, indent=2)
        st.download_button("💾 Descargar JSON BLOQUE 3", data=json_data, file_name="bloque_3_entrevista_victima.json", mime="application/json", use_container_width=True, key="b3_download_json")
    with st.expander("Ver JSON"):
        st.json(armar_json_exportacion())

# Guardado automatico al finalizar la corrida
try:
    if GUARDADO_GLOBAL_OK:
        autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
