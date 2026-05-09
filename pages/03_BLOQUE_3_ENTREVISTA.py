import streamlit as st
import sqlite3
import json
import re
import os
import tempfile
from datetime import datetime, date
from fpdf import FPDF
from PIL import Image
from streamlit_drawable_canvas import st_canvas

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    USA_GUARDADO_GLOBAL = True
except Exception:
    USA_GUARDADO_GLOBAL = False

# =====================================================
# S.I.V.A.P. - BLOQUE 3
# ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO
#
# Version corregida:
# - Conserva Identificacion y Relato.
# - Guia interna SIVAP con preguntas + campos.
# - Relato final editable y noticia criminis unica.
# - PDF con formato policial similar a acta real:
#   encabezado, fecha/hora, datos, facultad de abstencion,
#   RELATO, cierre y firmas.
# - Guardado blindado local para no perder informacion.
# =====================================================

BLOQUE_ID = "BLOQUE_3_ENTREVISTA_VICTIMA"
DB_B3 = "sivap_bloque3_borrador.db"


# =====================================================
# GUARDADO BLINDADO
# =====================================================

def _conn_b3():
    conn = sqlite3.connect(DB_B3, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS borrador_bloque3 (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        datos_json TEXT,
        actualizado_en TEXT
    )
    """)
    conn.commit()
    return conn


def _clave_b3_guardable(k):
    k = str(k)
    if not k.startswith("b3_"):
        return False
    excluir = ["canvas", "firma_canvas", "download", "file_uploader", "uploaded", "button"]
    return not any(x in k.lower() for x in excluir)


def _serializar(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, date):
        return {"__tipo__": "date", "valor": v.isoformat()}
    if isinstance(v, list):
        return [_serializar(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _serializar(x) for k, x in v.items()}
    return None


def _deserializar(v):
    if isinstance(v, dict) and v.get("__tipo__") == "date":
        try:
            return date.fromisoformat(v.get("valor"))
        except Exception:
            return v.get("valor", "")
    if isinstance(v, list):
        return [_deserializar(x) for x in v]
    if isinstance(v, dict):
        return {k: _deserializar(x) for k, x in v.items()}
    return v


def guardar_borrador_b3():
    datos = {}
    for k, v in st.session_state.items():
        if _clave_b3_guardable(k):
            sv = _serializar(v)
            if sv is not None:
                datos[k] = sv

    conn = _conn_b3()
    c = conn.cursor()
    c.execute("""
    INSERT INTO borrador_bloque3 (id, datos_json, actualizado_en)
    VALUES (1, ?, ?)
    ON CONFLICT(id)
    DO UPDATE SET datos_json=excluded.datos_json, actualizado_en=excluded.actualizado_en
    """, (
        json.dumps(datos, ensure_ascii=False, indent=2),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()


def cargar_borrador_b3():
    conn = _conn_b3()
    c = conn.cursor()
    c.execute("SELECT datos_json, actualizado_en FROM borrador_bloque3 WHERE id=1")
    row = c.fetchone()
    conn.close()

    if not row:
        return False, ""

    try:
        datos = json.loads(row[0])
        for k, v in datos.items():
            if _clave_b3_guardable(k) and k not in st.session_state:
                st.session_state[k] = _deserializar(v)
        return True, row[1]
    except Exception:
        return False, row[1]


def borrar_borrador_b3():
    conn = _conn_b3()
    c = conn.cursor()
    c.execute("DELETE FROM borrador_bloque3 WHERE id=1")
    conn.commit()
    conn.close()


def iniciar_bloque3():
    if "b3_borrador_cargado" not in st.session_state:
        ok, fecha = cargar_borrador_b3()
        st.session_state["b3_borrador_cargado"] = True
        st.session_state["b3_borrador_fecha"] = fecha if ok else ""

    iniciales = {
        "b3_condicion": "Víctima",
        "b3_nombre": "",
        "b3_dni": "",
        "b3_edad": "",
        "b3_fecha_nac": "",
        "b3_nacionalidad": "ARGENTINA",
        "b3_estado_civil": "",
        "b3_profesion": "",
        "b3_domicilio": "",
        "b3_telefono_fijo": "",
        "b3_celular": "",
        "b3_correo": "",
        "b3_relato_inicial": "",
        "b3_evito_contacto": "NO CORRESPONDE",
        "b3_obs_contacto": "",
        "b3_relato_final": "",
        "b3_noticia_criminis": "",
        "b3_lugar_entrevista": "Rosario",
        "b3_fecha_entrevista": date.today(),
        "b3_hora_entrevista": datetime.now().strftime("%H:%M"),
        "b3_personal_actuante": "",
        "b3_dependencia_acta": "",
        "b3_insta_accion_penal": "NO DEFINIDO"
    }
    for k, v in iniciales.items():
        if k not in st.session_state:
            st.session_state[k] = v


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
        "“": '"', "”": '"', "’": "'",
        "–": "-", "—": "-",
        "✅": "", "⚠️": "", "🚨": "", "📌": "", "🗣️": ""
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto


def partir_palabras_largas(texto, max_len=65):
    texto = str(texto or "")
    salida = []
    for token in texto.split(" "):
        if len(token) > max_len:
            salida.append(" ".join(token[i:i+max_len] for i in range(0, len(token), max_len)))
        else:
            salida.append(token)
    return " ".join(salida)


def pdf_multi(pdf, texto, alto=6, align="J"):
    texto = limpiar_pdf(partir_palabras_largas(texto))
    if not texto.strip():
        pdf.ln(3)
        return
    for linea in texto.split("\n"):
        linea = linea.strip()
        if linea:
            pdf.multi_cell(0, alto, limpiar_pdf(partir_palabras_largas(linea)), align=align)
        else:
            pdf.ln(3)


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def texto_corto(texto, limite=700):
    texto = " ".join(str(texto or "").split())
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "..."


def contiene(texto, palabras):
    t = str(texto or "").lower()
    return any(p in t for p in palabras)


def fecha_larga(fecha_iso):
    try:
        if isinstance(fecha_iso, date):
            f = fecha_iso
        else:
            f = date.fromisoformat(str(fecha_iso))
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        return f"{f.day:02d} dias del mes de {meses[f.month-1]} de {f.year}"
    except Exception:
        return str(fecha_iso)


# =====================================================
# DETECTOR Y GUIA
# =====================================================

PAL_LESIONES = [
    "me pegó", "me pego", "me golpeó", "me golpeo", "me empujó", "me empujo",
    "me cortó", "me corto", "me lastimó", "me lastimo", "me lesionó", "me lesiono",
    "cachetada", "trompada", "patada", "puñetazo", "dolor", "hematoma",
    "hinchado", "inflamación", "inflamacion", "sangre", "corte", "hospital",
    "sies", "ambulancia", "certificado médico", "certificado medico", "médico", "medico"
]
PAL_AMENAZAS = [
    "me amenazó", "me amenazo", "amenaza", "amenazas", "te voy a matar",
    "me iba a matar", "me va a matar", "te voy a prender fuego", "me amedrentó",
    "me amedrento", "me intimidó", "me intimido"
]
PAL_ROBO = [
    "me robó", "me robo", "me sustrajo", "me sacó", "me saco", "me arrebató",
    "me arrebato", "me quitó", "me quito", "me llevó", "me llevo", "me exigió",
    "me exigio", "dame todo", "entregué", "entregue"
]
PAL_HURTO = [
    "me faltó", "me falto", "no estaba", "desapareció", "desaparecio",
    "me di cuenta que no tenía", "me di cuenta que no tenia"
]
PAL_ARMA = [
    "arma", "arma de fuego", "pistola", "revólver", "revolver", "escopeta",
    "cuchillo", "arma blanca", "culata", "me apuntó", "me apunto", "me exhibió",
    "me exhibio", "disparó", "disparo"
]
PAL_DANIO = [
    "rompió", "rompio", "dañó", "daño", "danio", "forzó", "forzo",
    "vidrio", "ventana", "puerta", "cerradura", "candado"
]
PAL_GENERO = [
    "mi pareja", "mi ex pareja", "ex pareja", "mi marido", "mi mujer",
    "conviviente", "convivimos", "hijo en común", "hijo en comun",
    "violencia de género", "violencia de genero", "violencia familiar",
    "perimetral", "restricción", "restriccion"
]
PAL_SEXUAL = ["abuso", "abusó", "me tocó", "me toco", "sin consentimiento", "sexual", "violación", "violacion", "manoseo"]
PAL_PRIVADA = ["injuria", "injurias", "calumnia", "calumnias", "me insultó", "me insulto", "publicó que soy", "publico que soy"]
PAL_PRUEBA = ["cámara", "camara", "filmación", "filmacion", "testigo", "vecino vio", "captura", "whatsapp", "mensaje", "audio"]


def analizar_relato_interno(relato):
    t = str(relato or "").lower()
    d = {
        "lesiones": contiene(t, PAL_LESIONES),
        "amenazas": contiene(t, PAL_AMENAZAS),
        "robo": contiene(t, PAL_ROBO),
        "hurto": contiene(t, PAL_HURTO),
        "arma": contiene(t, PAL_ARMA),
        "danio": contiene(t, PAL_DANIO),
        "genero": contiene(t, PAL_GENERO),
        "sexual": contiene(t, PAL_SEXUAL),
        "privada": contiene(t, PAL_PRIVADA),
        "prueba": contiene(t, PAL_PRUEBA)
    }
    tipos = []
    if d["robo"] and (d["arma"] or d["lesiones"]):
        tipos.append("robo_arma_violencia_lesiones")
    elif d["robo"]:
        tipos.append("robo_arrebato")
    if d["hurto"]:
        tipos.append("hurto")
    if d["amenazas"]:
        tipos.append("amenazas")
    if d["lesiones"]:
        tipos.append("lesiones")
    if d["arma"] and not d["robo"]:
        tipos.append("arma")
    if d["danio"]:
        tipos.append("danio")
    if d["genero"]:
        tipos.append("genero_familiar")
    if d["sexual"]:
        tipos.append("sexual")
    if d["privada"]:
        tipos.append("accion_privada")
    if d["prueba"]:
        tipos.append("prueba_digital_testigos_camaras")
    return d, tipos


def pregunta(id_, texto, ayuda="", tipo="text_area", opciones=None):
    return {"id": id_, "texto": texto, "ayuda": ayuda, "tipo": tipo, "opciones": opciones or []}


def construir_preguntas_guia(relato):
    d, tipos = analizar_relato_interno(relato)
    preguntas = []

    if relato and len(relato.strip()) < 80:
        preguntas.append(pregunta("base_modo_tiempo_lugar", "Complete modo, tiempo y lugar del hecho.", "Dónde estaba, cuándo ocurrió y cómo comenzó."))

    if d["amenazas"]:
        preguntas.extend([
            pregunta("amenaza_frase", "¿Qué frase textual le dijo el autor de la amenaza?", "Debe quedar como: me dijo textualmente..."),
            pregunta("amenaza_amedrentamiento", "¿La víctima se sintió amedrentada/intimidada y teme por su integridad física?", "Clave para amenazas."),
            pregunta("amenaza_vinculo", "¿Conoce al autor? ¿Qué vínculo tiene y por qué le genera temor?", "Vecino, ex pareja, familiar, vive cerca, antecedentes."),
            pregunta("amenaza_medio_prueba", "¿La amenaza fue personal, por teléfono, WhatsApp o redes? ¿Hay testigos, cámaras o capturas?", "Registrar prueba si existe.")
        ])

    if d["lesiones"]:
        preguntas.extend([
            pregunta("lesion_mecanismo", "¿Cómo se produjo la lesión?", "Golpe de puño, patada, empujón, corte, objeto, caída, etc."),
            pregunta("lesion_zona", "¿Qué zona del cuerpo resultó afectada y qué lesión/dolor presenta?", "Rostro, cabeza, brazo, pierna, corte, hematoma, inflamación, dolor."),
            pregunta("lesion_asistencia", "¿Recibió asistencia médica, ambulancia, hospital o certificado médico?", "Indicar SIES, hospital, médico, diagnóstico o certificado."),
            pregunta("lesion_instancia", "¿Es su deseo instar la acción penal por las lesiones sufridas?", "Solo se incorpora al relato si corresponde.", tipo="select", opciones=["NO DEFINIDO", "SÍ", "NO"])
        ])

    if d["robo"]:
        preguntas.extend([
            pregunta("robo_objeto", "¿Qué elemento le sustrajeron? Describa marca, modelo, color y características.", "Ej: teléfono celular Samsung, color negro, funda transparente."),
            pregunta("robo_modo", "¿Cómo fue la sustracción?", "Arrebato, violencia, intimidación, fuerza, exigencia o entrega por temor."),
            pregunta("robo_autor_fuga", "¿Puede describir al autor y hacia dónde se dio a la fuga?", "Vestimenta, contextura, moto/auto/a pie, dirección de fuga."),
            pregunta("robo_reconocimiento", "¿Podría reconocer al autor si lo vuelve a ver?", "Debe quedar incorporado si pudo observarlo.")
        ])

    if d["arma"]:
        preguntas.extend([
            pregunta("arma_descripcion", "¿Qué tipo de arma o elemento de peligrosidad observó?", "Pistola, revólver, cuchillo, color, tamaño, estado."),
            pregunta("arma_uso", "¿Cómo usó el arma?", "Si apuntó, exhibió, golpeó con la culata, amenazó o disparó.")
        ])

    if d["danio"]:
        preguntas.append(pregunta("danio_detalle", "¿Qué cosa fue dañada y cómo se produjo el daño?", "Puerta, ventana, vidrio, vehículo, cerradura, fotos o titularidad."))

    if d["genero"]:
        preguntas.extend([
            pregunta("genero_contexto", "¿Qué vínculo tiene con el autor y si existen antecedentes o medidas vigentes?", "Pareja, ex pareja, convivencia, hijos, medidas."),
            pregunta("genero_riesgo", "¿Existe riesgo actual o temor de nuevos hechos?", "Domicilio seguro, armas, amenazas recientes, convivencia.")
        ])

    if d["sexual"]:
        preguntas.append(pregunta("sexual_resguardo", "Registrar situación con trato reservado y evitar revictimización.", "Consultar autoridad competente/protocolo específico."))

    if d["privada"]:
        preguntas.append(pregunta("privada_constancia", "Posible acción privada: deje constancia clara y consulte superior si corresponde.", "No tratar automáticamente como flagrancia común."))

    if d["prueba"]:
        preguntas.append(pregunta("prueba_detalle", "¿Qué testigos, cámaras, mensajes, audios o capturas existen?", "Nombre/contacto de testigos, ubicación de cámaras, capturas o teléfono."))

    if not preguntas and relato.strip():
        preguntas.extend([
            pregunta("base_autor", "¿Puede aportar datos del autor o describirlo?", "Nombre, apodo, vestimenta, contextura, domicilio, si lo conoce."),
            pregunta("base_prueba", "¿Hay testigos, cámaras u otra prueba inmediata?", "Nombre/contacto, ubicación de cámaras, fotos, mensajes.")
        ])

    vistos = set()
    filtradas = []
    for p in preguntas:
        if p["id"] not in vistos:
            filtradas.append(p)
            vistos.add(p["id"])
    return filtradas


def obtener_respuestas_guia():
    respuestas = {}
    for k, v in st.session_state.items():
        if k.startswith("b3_resp_") and isinstance(v, str) and v.strip():
            respuestas[k.replace("b3_resp_", "")] = v.strip()
    return respuestas


def frase_instancia_penal(valor):
    if valor == "SÍ":
        return "En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas."
    if valor == "NO":
        return "En este acto manifiesto que no es mi deseo instar la acción penal por las lesiones sufridas."
    return ""


def construir_relato_final(relato_crudo, respuestas):
    relato = " ".join(str(relato_crudo or "").split())
    partes = []
    if relato:
        partes.append(relato)

    orden = [
        "base_modo_tiempo_lugar", "amenaza_frase", "amenaza_amedrentamiento",
        "amenaza_vinculo", "amenaza_medio_prueba", "arma_descripcion", "arma_uso",
        "robo_objeto", "robo_modo", "robo_autor_fuga", "robo_reconocimiento",
        "lesion_mecanismo", "lesion_zona", "lesion_asistencia", "lesion_instancia",
        "danio_detalle", "genero_contexto", "genero_riesgo", "prueba_detalle",
        "base_autor", "base_prueba"
    ]

    for oid in orden:
        r = respuestas.get(oid, "")
        if not r:
            continue
        if oid == "amenaza_frase":
            partes.append(f"Con relación a la amenaza recibida, recuerdo que el autor me dijo textualmente: “{r}”.")
        elif oid == "amenaza_amedrentamiento":
            partes.append(f"Por las amenazas recibidas, {r}")
        elif oid == "lesion_instancia":
            f = frase_instancia_penal(r)
            if f:
                partes.append(f)
        elif oid == "arma_descripcion":
            partes.append(f"Con respecto al arma o elemento utilizado, recuerdo que {r}")
        elif oid == "arma_uso":
            partes.append(f"Respecto del modo en que utilizó el arma o elemento, manifiesto que {r}")
        elif oid == "robo_objeto":
            partes.append(f"El elemento que me sustrajeron fue {r}")
        elif oid == "robo_reconocimiento":
            partes.append(f"Respecto de la posibilidad de reconocer al autor, manifiesto que {r}")
        elif oid == "lesion_zona":
            partes.append(f"Como consecuencia del hecho, presento/sentí {r}")
        elif oid == "lesion_asistencia":
            partes.append(f"Con relación a la asistencia médica, manifiesto que {r}")
        elif oid == "prueba_detalle":
            partes.append(f"Con relación a testigos, cámaras o evidencia disponible, manifiesto que {r}")
        else:
            partes.append(r)

    texto = " ".join([p.strip() for p in partes if p.strip()])
    texto = re.sub(r"\s+", " ", texto).strip()
    if texto and texto[-1] not in ".!?":
        texto += "."
    return texto


def generar_noticia_criminis(filiacion, relato_final, respuestas):
    nombre = filiacion.get("nombre", "").strip() or "la víctima/damnificado"
    dni = filiacion.get("dni", "").strip()
    domicilio = filiacion.get("domicilio", "").strip()

    d, tipos = analizar_relato_interno(relato_final)
    intro = f"De la entrevista recibida a {nombre}"
    if dni:
        intro += f", DNI Nro. {dni}"
    if domicilio:
        intro += f", domiciliado/a en {domicilio}"
    intro += ", surge que "

    if d["robo"] and (d["arma"] or d["lesiones"]):
        hecho = "habría sido víctima de un hecho de sustracción mediante violencia y/o intimidación"
        if d["arma"]:
            hecho += ", con utilización de arma o elemento de peligrosidad"
        if d["lesiones"]:
            hecho += ", resultando además con lesiones"
    elif d["robo"]:
        hecho = "habría sido víctima de una sustracción de pertenencias"
    elif d["amenazas"]:
        hecho = "habría sido víctima de amenazas"
    elif d["lesiones"]:
        hecho = "habría sufrido lesiones"
    elif d["danio"]:
        hecho = "habría sufrido daños sobre bienes de su propiedad o a su cargo"
    elif d["hurto"]:
        hecho = "habría advertido la sustracción de pertenencias"
    else:
        hecho = "aportó información de interés vinculada al hecho investigado"

    datos = []
    if respuestas.get("amenaza_amedrentamiento"):
        datos.append("manifestando haberse sentido amedrentada/intimidada y temer por su integridad física")
    if respuestas.get("robo_autor_fuga"):
        datos.append("aportando datos sobre el autor y/o su fuga")
    if respuestas.get("robo_reconocimiento"):
        datos.append("indicando datos sobre la posibilidad de reconocimiento")
    if respuestas.get("lesion_asistencia") or respuestas.get("lesion_zona"):
        datos.append("dejándose constancia de las lesiones y/o asistencia médica referidas")
    if respuestas.get("lesion_instancia") == "SÍ":
        datos.append("manifestando su deseo de instar la acción penal por las lesiones sufridas")
    if respuestas.get("prueba_detalle") or respuestas.get("amenaza_medio_prueba"):
        datos.append("señalando testigos, cámaras o elementos de prueba a resguardar")

    texto = intro + hecho
    if datos:
        texto += ", " + ", ".join(datos)
    texto += ". Se labró acta de entrevista individual, la cual se agrega como anexo."
    return texto_corto(texto, 900)


def firma_canvas_a_path(canvas_result):
    if canvas_result is None or canvas_result.image_data is None:
        return None

    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
    pixels = img.getdata()
    tinta = 0
    for p in pixels:
        r, g, b, a = p
        if a > 0 and not (r > 245 and g > 245 and b > 245):
            tinta += 1
            if tinta > 30:
                break

    if tinta <= 30:
        return None

    fondo = Image.new("RGB", img.size, (255, 255, 255))
    fondo.paste(img, mask=img.split()[3])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    fondo.save(tmp.name, format="JPEG")
    return tmp.name


def filiacion_actual():
    return {
        "condicion": st.session_state.get("b3_condicion", ""),
        "nombre": st.session_state.get("b3_nombre", ""),
        "dni": st.session_state.get("b3_dni", ""),
        "edad": st.session_state.get("b3_edad", ""),
        "fecha_nac": st.session_state.get("b3_fecha_nac", ""),
        "nacionalidad": st.session_state.get("b3_nacionalidad", ""),
        "estado_civil": st.session_state.get("b3_estado_civil", ""),
        "profesion": st.session_state.get("b3_profesion", ""),
        "domicilio": st.session_state.get("b3_domicilio", ""),
        "telefono_fijo": st.session_state.get("b3_telefono_fijo", ""),
        "celular": st.session_state.get("b3_celular", ""),
        "correo": st.session_state.get("b3_correo", "")
    }


def identidad_y_actuacion():
    return {
        "autor_carga": st.session_state.get("identidad_policial", {}),
        "actuacion": st.session_state.get("actuacion", {})
    }


# =====================================================
# PDF ACTA DE ENTREVISTA - FORMATO POLICIAL
# =====================================================

def generar_pdf_acta_entrevista(filiacion, relato_final, noticia_criminis, firma_path=None):
    identidad = st.session_state.get("identidad_policial", {})
    actuacion = st.session_state.get("actuacion", {})

    dependencia = (
        st.session_state.get("b3_dependencia_acta")
        or actuacion.get("reparticion_dependencia")
        or identidad.get("dependencia")
        or "DEPENDENCIA POLICIAL"
    )

    lugar = st.session_state.get("b3_lugar_entrevista", "Rosario")
    fecha_ent = st.session_state.get("b3_fecha_entrevista", date.today())
    hora_ent = st.session_state.get("b3_hora_entrevista", "")
    personal = st.session_state.get("b3_personal_actuante", "") or identidad.get("nombre", "personal policial actuante")

    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Encabezado institucional
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "UNIDAD REGIONAL II - ROSARIO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, limpiar_pdf(str(dependencia).upper()), ln=True, align="C")
    pdf.ln(3)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 9, "ACTA DE ENTREVISTA", ln=True, align="C")
    pdf.ln(5)

    # Apertura
    apertura = (
        f"En la ciudad de {lugar}, a los {fecha_larga(fecha_ent)}, siendo las {hora_ent or '____'} horas, "
        f"el funcionario policial actuante {personal}, con prestación de servicio en {dependencia}, "
        f"procede a entrevistar a una persona consultada sobre sus datos personales y sobre los hechos que motivan la presente actuación."
    )
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, apertura)
    pdf.ln(3)

    # Datos de identidad
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DATOS DE IDENTIDAD DE LA PERSONA ENTREVISTADA", ln=True)
    pdf.set_font("Arial", "", 10)

    datos = (
        f"Condicion: {filiacion.get('condicion','S/D')}. "
        f"Apellido y nombre: {filiacion.get('nombre','S/D')}. "
        f"DNI: {filiacion.get('dni','S/D')}. "
        f"Edad: {filiacion.get('edad','S/D')}. "
        f"Fecha de nacimiento: {filiacion.get('fecha_nac','S/D')}. "
        f"Nacionalidad: {filiacion.get('nacionalidad','S/D')}. "
        f"Estado civil: {filiacion.get('estado_civil','S/D')}. "
        f"Profesion/ocupacion: {filiacion.get('profesion','S/D')}. "
        f"Domicilio: {filiacion.get('domicilio','S/D')}. "
        f"Telefono: {filiacion.get('telefono_fijo','S/D')} / Celular: {filiacion.get('celular','S/D')}. "
        f"Correo electronico: {filiacion.get('correo','S/D')}."
    )
    pdf_multi(pdf, datos)
    pdf.ln(2)

    # Facultad de abstención
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "FACULTAD DE ABSTENCION", ln=True)
    pdf.set_font("Arial", "", 9)
    abstencion = (
        "Acto seguido se le hace saber que no se encuentra obligado/a a declarar contra si mismo/a, "
        "ni contra su conyuge, ascendientes, descendientes, hermanos u otras personas comprendidas por la ley, "
        "pudiendo abstenerse de declarar en los supuestos legalmente previstos. Asimismo, se le hace saber que "
        "debera expresarse con verdad respecto de las circunstancias que manifieste conocer."
    )
    pdf_multi(pdf, abstencion, alto=5)
    pdf.ln(3)

    # Relato
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "RELATO", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, relato_final)
    pdf.ln(3)

    # Constancia opcional muy breve para acta, no análisis interno
    if noticia_criminis:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "RESUMEN OPERATIVO PARA ACTA DE PROCEDIMIENTO", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf_multi(pdf, noticia_criminis, alto=5)
        pdf.ln(3)

    # Cierre formal
    pdf.set_font("Arial", "", 10)
    cierre = (
        "No siendo para mas, previa lectura integra y ratificacion de su contenido, "
        "se da por finalizado el presente acto, firmando la persona entrevistada junto al personal policial actuante, "
        "para debida constancia."
    )
    pdf_multi(pdf, cierre)
    pdf.ln(5)

    # Firma digital si existe
    if firma_path:
        try:
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 6, "Firma digital de la persona entrevistada:", ln=True)
            pdf.image(firma_path, x=25, w=75)
            pdf.ln(7)
        except Exception:
            pass

    pdf.ln(10)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion del entrevistado", ln=False, align="C")
    pdf.cell(85, 6, "Firma personal policial", ln=True, align="C")

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, "S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora.", align="R")

    return pdf_bytes(pdf)


# =====================================================
# INTERFAZ
# =====================================================

iniciar_bloque3()

if USA_GUARDADO_GLOBAL:
    try:
        iniciar_guardado_seguro(BLOQUE_ID)
        panel_guardado_seguro(BLOQUE_ID)
    except Exception:
        pass

st.title("🗣️ BLOQUE 3 — ACTA DE ENTREVISTA A VÍCTIMA / DAMNIFICADO")
st.subheader("Formato policial de entrevista + guía interna S.I.V.A.P.")

st.sidebar.divider()
st.sidebar.markdown("### 🛡️ Guardado BLOQUE 3")
fecha_b = st.session_state.get("b3_borrador_fecha", "")
if fecha_b:
    st.sidebar.success(f"Borrador cargado: {fecha_b}")
else:
    st.sidebar.info("Sin borrador previo BLOQUE 3")

if st.sidebar.button("💾 Guardar entrevista BLOQUE 3", use_container_width=True, key="b3_button_guardar_manual"):
    guardar_borrador_b3()
    if USA_GUARDADO_GLOBAL:
        try:
            autoguardar_bloque(BLOQUE_ID)
        except Exception:
            pass
    st.success("Entrevista guardada.")

if st.sidebar.button("🧹 Limpiar SOLO BLOQUE 3", use_container_width=True, key="b3_button_limpiar_manual"):
    borrar_borrador_b3()
    for k in list(st.session_state.keys()):
        if k.startswith("b3_"):
            del st.session_state[k]
    st.rerun()

st.warning("La entrevista queda en borrador. El sistema no borra ni reemplaza lo escrito sin orden del policía.")

tabs = st.tabs([
    "1. Identificación",
    "2. Relato",
    "3. Análisis S.I.V.A.P.",
    "4. Relato final / noticia criminis",
    "5. Firma / PDF / JSON"
])


with tabs[0]:
    st.subheader("Identificación de víctima / damnificado")

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Condición", ["Víctima", "Damnificado", "Denunciante", "Representante legal", "Otro"], key="b3_condicion")
        st.text_input("Apellido y nombres", key="b3_nombre")
        st.text_input("DNI", key="b3_dni")
        st.text_input("Edad", key="b3_edad")
        st.text_input("Fecha de nacimiento", key="b3_fecha_nac")
        st.text_input("Nacionalidad", key="b3_nacionalidad")

    with c2:
        st.text_input("Estado civil", key="b3_estado_civil")
        st.text_input("Profesión / ocupación", key="b3_profesion")
        st.text_area("Domicilio", key="b3_domicilio")
        st.text_input("Teléfono fijo", key="b3_telefono_fijo")
        st.text_input("Celular", key="b3_celular")
        st.text_input("Correo electrónico", key="b3_correo")

    st.info("Estos datos alimentan el acta de entrevista y el resumen para BLOQUE 1/BLOQUE 8.")


with tabs[1]:
    st.subheader("Relato crudo en primera persona")

    st.markdown("El relato se escribe como dichos de la persona entrevistada: **Yo estaba... / vi... / sentí... / me golpeó... / me sustrajo...**")

    st.text_area(
        "Relato inicial de la víctima / damnificado",
        height=390,
        key="b3_relato_inicial",
        placeholder='Ej: Yo estaba en la parada del colectivo cuando un sujeto se me acercó con un arma de fuego...'
    )

    st.radio("¿Se evitó contacto entre víctima/testigo e imputado/aprehendido?", ["SI", "NO", "NO CORRESPONDE"], horizontal=True, key="b3_evito_contacto")
    st.text_area("Observación sobre resguardo / no contaminación del testimonio", key="b3_obs_contacto")


with tabs[2]:
    st.subheader("Guía interna para mejorar el relato")

    relato = st.session_state.get("b3_relato_inicial", "")
    preguntas = construir_preguntas_guia(relato)

    if not relato.strip():
        st.info("Primero cargue el relato en la pestaña 2. Luego S.I.V.A.P. mostrará las preguntas de guía necesarias.")
    else:
        st.success("S.I.V.A.P. analizó el relato y muestra solo preguntas útiles para reforzarlo.")
        st.caption("Estas preguntas son internas. No salen como cuestionario en el PDF.")

        for p in preguntas:
            st.markdown(f"**{p['texto']}**")
            if p.get("ayuda"):
                st.caption(p["ayuda"])

            key = f"b3_resp_{p['id']}"
            if p["tipo"] == "select":
                st.selectbox("Respuesta", p["opciones"], key=key)
            else:
                st.text_area("Respuesta para incorporar al relato", key=key, height=90)

        if st.button("💾 Guardar respuestas de guía", use_container_width=True, key="b3_button_guardar_guia"):
            guardar_borrador_b3()
            st.success("Respuestas guardadas.")

    st.info("La naturaleza de acción y la orientación jurídica quedan como análisis interno del sistema. No se imprimen como fundamento.")


with tabs[3]:
    st.subheader("Relato final y noticia criminis")

    respuestas = obtener_respuestas_guia()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧠 Generar / actualizar relato final desde guía", use_container_width=True, key="b3_button_generar_relato_final"):
            st.session_state["b3_relato_final"] = construir_relato_final(st.session_state.get("b3_relato_inicial", ""), respuestas)
            guardar_borrador_b3()
            st.success("Relato final generado. Revíselo y corríjalo si hace falta.")
            st.rerun()

    with c2:
        if st.button("📌 Generar súper resumen / noticia criminis", use_container_width=True, key="b3_button_generar_noticia"):
            st.session_state["b3_noticia_criminis"] = generar_noticia_criminis(
                filiacion_actual(),
                st.session_state.get("b3_relato_final", "") or st.session_state.get("b3_relato_inicial", ""),
                respuestas
            )
            guardar_borrador_b3()
            st.success("Noticia criminis generada.")
            st.rerun()

    st.markdown("### A. Relato final de entrevista")
    st.caption("Va al PDF. Debe quedar en primera persona. El policía puede corregirlo libremente.")
    st.text_area("Relato final en primera persona", height=360, key="b3_relato_final")

    st.markdown("### B. Súper resumen / noticia criminis")
    st.caption("Sirve para alimentar BLOQUE 1/BLOQUE 8. No reemplaza el relato completo.")
    st.text_area("Noticia criminis / resumen para acta de procedimiento", height=190, key="b3_noticia_criminis")


with tabs[4]:
    st.subheader("Firma digital, PDF y JSON")

    st.markdown("### Datos formales del acta")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Lugar de entrevista", key="b3_lugar_entrevista")
    with c2:
        st.date_input("Fecha de entrevista", key="b3_fecha_entrevista")
    with c3:
        st.text_input("Hora de entrevista", key="b3_hora_entrevista")

    c4, c5 = st.columns(2)
    with c4:
        st.text_input("Dependencia que labra el acta", key="b3_dependencia_acta")
    with c5:
        st.text_input("Personal policial actuante", key="b3_personal_actuante")

    st.markdown("### Firma digital de la persona entrevistada")
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=170,
        width=500,
        drawing_mode="freedraw",
        key="b3_firma_canvas"
    )

    firma_path = firma_canvas_a_path(canvas_result)
    if firma_path:
        st.success("Firma digital detectada.")
    else:
        st.warning("Todavía no se detecta firma digital. Puede generar el PDF igual, pero sin firma insertada.")

    filiacion = filiacion_actual()
    relato_final = st.session_state.get("b3_relato_final", "") or st.session_state.get("b3_relato_inicial", "")
    respuestas = obtener_respuestas_guia()
    noticia = st.session_state.get("b3_noticia_criminis", "")
    if not noticia:
        noticia = generar_noticia_criminis(filiacion, relato_final, respuestas)

    analisis_interno, tipos_internos = analizar_relato_interno(relato_final)
    datos_identidad = identidad_y_actuacion()

    datos_exportar = {
        "bloque": 3,
        "modulo": "BLOQUE_3_ENTREVISTA_VICTIMA_DAMNIFICADO",
        "version": "sivap_bloque3_formato_acta_entrevista_real",
        "autor_carga": datos_identidad.get("autor_carga", {}),
        "actuacion": datos_identidad.get("actuacion", {}),
        "filiacion": filiacion,
        "datos_formales_acta": {
            "lugar": st.session_state.get("b3_lugar_entrevista", ""),
            "fecha": str(st.session_state.get("b3_fecha_entrevista", "")),
            "hora": st.session_state.get("b3_hora_entrevista", ""),
            "dependencia": st.session_state.get("b3_dependencia_acta", ""),
            "personal_actuante": st.session_state.get("b3_personal_actuante", "")
        },
        "relato_primera_persona": relato_final,
        "respuestas_guia": respuestas,
        "noticia_criminis": noticia,
        "resumen_para_acta_procedimiento": noticia,
        "evito_contacto_imputado": st.session_state.get("b3_evito_contacto", ""),
        "observacion_no_contaminacion": st.session_state.get("b3_obs_contacto", ""),
        "analisis_interno_sivap": {
            "detectores": analisis_interno,
            "tipos_orientativos_internos": tipos_internos
        },
        "firma_digital": "SÍ" if firma_path else "NO",
        "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    json_exportar = json.dumps(datos_exportar, ensure_ascii=False, indent=4)
    pdf_data = generar_pdf_acta_entrevista(filiacion, relato_final, noticia, firma_path)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💾 Guardar entrevista completa", use_container_width=True, key="b3_button_guardar_completa"):
            guardar_borrador_b3()
            if USA_GUARDADO_GLOBAL:
                try:
                    autoguardar_bloque(BLOQUE_ID)
                except Exception:
                    pass
            st.success("Entrevista completa guardada.")
    with c2:
        st.download_button(
            "📄 Descargar PDF Acta de Entrevista",
            data=pdf_data,
            file_name="BLOQUE_3_Acta_Entrevista.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="b3_download_pdf"
        )
    with c3:
        st.download_button(
            "📦 Descargar JSON para BLOQUE 8",
            data=json_exportar,
            file_name="bloque_3_entrevista_victima.json",
            mime="application/json",
            use_container_width=True,
            key="b3_download_json"
        )

    with st.expander("Ver JSON que se enviará al actante / BLOQUE 8"):
        st.code(json_exportar, language="json")

    if firma_path and os.path.exists(firma_path):
        try:
            os.unlink(firma_path)
        except Exception:
            pass

try:
    guardar_borrador_b3()
except Exception:
    pass

if USA_GUARDADO_GLOBAL:
    try:
        autoguardar_bloque(BLOQUE_ID)
    except Exception:
        pass
