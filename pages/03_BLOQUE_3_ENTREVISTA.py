import streamlit as st
import sqlite3
import json
import re
import os
import tempfile
from datetime import datetime, date
from fpdf import FPDF

try:
    from PIL import Image
except Exception:
    Image = None

try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_DISPONIBLE = True
except Exception:
    st_canvas = None
    CANVAS_DISPONIBLE = False

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    USA_GUARDADO_GLOBAL = True
except Exception:
    USA_GUARDADO_GLOBAL = False

# =====================================================
# S.I.V.A.P. - BLOQUE 3
# ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO
#
# Version corregida definitiva de trabajo:
# - Conserva metodologia de Identificacion y Relato.
# - Analisis S.I.V.A.P. funciona como guia interna, no como acta.
# - Delitos/situaciones manuales activan preguntas reales.
# - Descripcion de autor y conexion con aprehendido en campos separados.
# - Amenazas: NO pide instancia penal; si temor/amedrentamiento.
# - Lesiones: pregunta instancia penal por lesiones.
# - Robo con arma + lesiones: robo como hecho principal, instancia solo por lesiones.
# - Relato final y noticia criminis separados, sin pisarse.
# - PDF Acta de Entrevista sin noticia criminis interna.
# - Derechos de la victima como PDF independiente.
# - Guardado local + autoguardado global S.I.V.A.P. si esta disponible.
# =====================================================

BLOQUE_ID = "BLOQUE_3_ENTREVISTA"
DB_B3 = "sivap_bloque3_borrador.db"


# =====================================================
# GUARDADO BLINDADO LOCAL
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
    excluir = ["canvas", "download", "file_uploader", "uploaded", "button"]
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
        # Pestaña 1 - Identificacion
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

        # Pestaña 2 - Relato
        "b3_relato_inicial": "",
        "b3_resguardo_opciones": [],
        "b3_resguardo_otro": "",
        "b3_resguardo_constancia": "",

        # Pestaña 3 - Analisis / seleccion
        "b3_delitos_manual": [],
        "b3_delito_manual_otro": "",

        # Autor / aprehendido - campos fijos separados
        "b3_resp_autor_descripcion": "",
        "b3_resp_autor_vestimenta": "",
        "b3_resp_autor_contextura": "",
        "b3_resp_autor_edad_aprox": "",
        "b3_resp_autor_rasgos": "",
        "b3_resp_autor_arma_elemento": "",
        "b3_resp_autor_direccion_fuga": "",
        "b3_resp_autor_lo_vio_bien": "",
        "b3_resp_autor_lo_conoce": "",
        "b3_resp_autor_podria_reconocerlo": "",
        "b3_resp_autor_conexion_aprehendido": "",

        # Amenazas
        "b3_resp_amenaza_frase": "",
        "b3_resp_amenaza_amedrentamiento": "",
        "b3_resp_amenaza_temor_integridad": "",
        "b3_resp_amenaza_vinculo": "",
        "b3_resp_amenaza_medio_prueba": "",

        # Lesiones
        "b3_resp_lesion_mecanismo": "",
        "b3_resp_lesion_zona": "",
        "b3_resp_lesion_asistencia": "",
        "b3_resp_lesion_instancia": "NO DEFINIDO",

        # Robo / arma / hurto / daño / prueba
        "b3_resp_robo_objeto": "",
        "b3_resp_robo_modo": "",
        "b3_resp_robo_recupero": "",
        "b3_resp_hurto_detalle": "",
        "b3_resp_arma_descripcion": "",
        "b3_resp_arma_uso": "",
        "b3_resp_danio_detalle": "",
        "b3_resp_prueba_detalle": "",
        "b3_resp_genero_contexto": "",
        "b3_resp_genero_riesgo": "",
        "b3_resp_otro_detalle": "",

        # Pestaña 4
        "b3_relato_final": "",
        "b3_noticia_criminis": "",

        # Pestaña 5
        "b3_lugar_entrevista": "Rosario",
        "b3_fecha_entrevista": date.today(),
        "b3_hora_entrevista": datetime.now().strftime("%H:%M"),
        "b3_personal_actuante": "",
        "b3_dependencia_acta": "",

        # Derechos de la victima
        "b3_derechos_victima_notificada": "SI",
        "b3_derechos_victima_domicilio_notificaciones": "",
        "b3_derechos_victima_telefono_notificaciones": "",
        "b3_derechos_victima_correo_notificaciones": "",
        "b3_derechos_victima_observaciones": ""
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
        "“": '"', "”": '"', "’": "'", "‘": "'",
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
            salida.append(" ".join(token[i:i + max_len] for i in range(0, len(token), max_len)))
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


def texto_corto(texto, limite=1200):
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
        return f"{f.day:02d} dias del mes de {meses[f.month - 1]} de {f.year}"
    except Exception:
        return str(fecha_iso)


def val(key, defecto=""):
    return st.session_state.get(key, defecto)


def texto_limpio(texto):
    return re.sub(r"\s+", " ", str(texto or "")).strip()


# =====================================================
# DETECTOR Y SELECCION MANUAL
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
    "me di cuenta que no tenía", "me di cuenta que no tenia", "me sustrajeron sin violencia"
]
PAL_ARMA = [
    "arma", "arma de fuego", "pistola", "revólver", "revolver", "escopeta",
    "cuchillo", "arma blanca", "culata", "me apuntó", "me apunto", "me exhibió",
    "me exhibio", "disparó", "disparo"
]
PAL_DANIO = ["rompió", "rompio", "dañó", "daño", "danio", "forzó", "forzo", "vidrio", "ventana", "puerta", "cerradura", "candado"]
PAL_GENERO = ["mi pareja", "mi ex pareja", "ex pareja", "mi marido", "mi mujer", "conviviente", "convivimos", "hijo en común", "hijo en comun", "violencia de género", "violencia de genero", "violencia familiar", "perimetral", "restricción", "restriccion"]
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
    return d


def normalizar_manual(opciones, otro=""):
    opciones = opciones if isinstance(opciones, list) else []
    out = set()
    for op in opciones:
        s = str(op).lower()
        if "robo con arma" in s:
            out.update(["robo", "arma"])
        elif "robo" in s:
            out.add("robo")
        elif "amenaza" in s:
            out.add("amenazas")
        elif "lesion" in s:
            out.add("lesiones")
        elif "hurto" in s:
            out.add("hurto")
        elif "daño" in s or "dano" in s:
            out.add("danio")
        elif "género" in s or "genero" in s or "familiar" in s:
            out.add("genero")
        elif "arma" in s:
            out.add("arma")
        elif "cámara" in s or "camara" in s or "testigo" in s or "evidencia" in s:
            out.add("prueba")
        elif "privada" in s:
            out.add("privada")
        elif "sexual" in s:
            out.add("sexual")
        elif "otro" in s:
            out.add("otro")
    if str(otro or "").strip():
        out.add("otro")
    return out


def situaciones_activas(relato):
    d = analizar_relato_interno(relato)
    manual = normalizar_manual(val("b3_delitos_manual", []), val("b3_delito_manual_otro", ""))
    activos = {k for k, v in d.items() if v}
    activos.update(manual)
    if "robo" in activos and "arma" in activos:
        activos.add("robo_con_arma")
    if "robo" in activos and "lesiones" in activos:
        activos.add("robo_con_lesiones")
    return d, activos


def etiquetas_situaciones(activos):
    etiquetas = []
    if "robo_con_arma" in activos and "lesiones" in activos:
        etiquetas.append("Robo con arma y lesiones asociadas")
    elif "robo_con_arma" in activos:
        etiquetas.append("Robo con arma / elemento de peligrosidad")
    elif "robo" in activos:
        etiquetas.append("Robo / arrebato / sustracción con violencia o intimidación")
    if "hurto" in activos:
        etiquetas.append("Hurto / sustracción sin violencia")
    if "amenazas" in activos:
        etiquetas.append("Amenazas")
    if "lesiones" in activos:
        etiquetas.append("Lesiones")
    if "arma" in activos and "robo_con_arma" not in activos:
        etiquetas.append("Uso o exhibición de arma / elemento de peligrosidad")
    if "danio" in activos:
        etiquetas.append("Daño")
    if "genero" in activos:
        etiquetas.append("Contexto de violencia familiar / género")
    if "sexual" in activos:
        etiquetas.append("Situación contra la integridad sexual")
    if "privada" in activos:
        etiquetas.append("Posible acción privada")
    if "prueba" in activos:
        etiquetas.append("Testigos / cámaras / evidencia digital")
    if "otro" in activos:
        etiquetas.append("Otra situación agregada manualmente")
    return etiquetas


def requiere_autor(activos, relato):
    menciona_autor = contiene(relato, ["sujeto", "masculino", "persona", "autor", "aprehendido", "retenido", "agarraron", "lo corrieron", "lo atraparon", "lo detuvieron"])
    return bool(activos.intersection({"robo", "amenazas", "lesiones", "arma", "danio", "genero", "sexual", "otro"}) or menciona_autor)


# =====================================================
# DATOS ACTUALES
# =====================================================

def filiacion_actual():
    return {
        "condicion": val("b3_condicion"),
        "nombre": val("b3_nombre"),
        "dni": val("b3_dni"),
        "edad": val("b3_edad"),
        "fecha_nac": val("b3_fecha_nac"),
        "nacionalidad": val("b3_nacionalidad"),
        "estado_civil": val("b3_estado_civil"),
        "profesion": val("b3_profesion"),
        "domicilio": val("b3_domicilio"),
        "telefono_fijo": val("b3_telefono_fijo"),
        "celular": val("b3_celular"),
        "correo": val("b3_correo")
    }


def identidad_y_actuacion():
    return {
        "autor_carga": st.session_state.get("identidad_policial", {}),
        "actuacion": st.session_state.get("actuacion", {})
    }


def respuestas_guia_actuales():
    keys = [k for k in st.session_state.keys() if k.startswith("b3_resp_")]
    return {k.replace("b3_resp_", ""): st.session_state.get(k, "") for k in sorted(keys)}


def construir_constancia_resguardo():
    opciones = val("b3_resguardo_opciones", [])
    otro = texto_limpio(val("b3_resguardo_otro", ""))
    partes = []
    if opciones:
        partes.append("Se deja constancia que " + "; ".join(opciones).lower() + ".")
    if otro:
        partes.append(otro)
    constancia = " ".join(partes).strip()
    st.session_state["b3_resguardo_constancia"] = constancia
    return constancia


def derechos_victima_actual():
    return {
        "notificada": val("b3_derechos_victima_notificada", "SI"),
        "domicilio_notificaciones": val("b3_derechos_victima_domicilio_notificaciones"),
        "telefono_notificaciones": val("b3_derechos_victima_telefono_notificaciones"),
        "correo_notificaciones": val("b3_derechos_victima_correo_notificaciones"),
        "observaciones": val("b3_derechos_victima_observaciones")
    }


# =====================================================
# CONSTRUCCION DE RELATO Y NOTICIA
# =====================================================

def agregar_frase(partes, texto):
    texto = texto_limpio(texto)
    if texto:
        partes.append(texto.rstrip(".") + ".")


def construir_relato_final(relato_crudo, activos):
    partes = []
    relato = texto_limpio(relato_crudo)
    if relato:
        # Conserva lo que dijo la victima. Si ya esta en primera persona, no lo deforma.
        agregar_frase(partes, relato)

    # Autor / conexion con aprehendido, en orden logico
    if requiere_autor(activos, relato_crudo):
        desc = val("b3_resp_autor_descripcion")
        vest = val("b3_resp_autor_vestimenta")
        cont = val("b3_resp_autor_contextura")
        edad = val("b3_resp_autor_edad_aprox")
        rasgos = val("b3_resp_autor_rasgos")
        arma_elem = val("b3_resp_autor_arma_elemento")
        fuga = val("b3_resp_autor_direccion_fuga")
        vio = val("b3_resp_autor_lo_vio_bien")
        conoce = val("b3_resp_autor_lo_conoce")
        reconoce = val("b3_resp_autor_podria_reconocerlo")
        conexion = val("b3_resp_autor_conexion_aprehendido")

        datos_autor = []
        if desc:
            datos_autor.append(f"era {desc}")
        if cont:
            datos_autor.append(f"de contextura {cont}")
        if edad:
            datos_autor.append(f"de aproximadamente {edad} años de edad")
        if vest:
            datos_autor.append(f"vestía {vest}")
        if rasgos:
            datos_autor.append(f"presentaba como rasgos o señas particulares {rasgos}")
        if datos_autor:
            agregar_frase(partes, "Asimismo manifiesto que la persona que cometió el hecho " + ", ".join(datos_autor))
        if arma_elem:
            agregar_frase(partes, f"Manifiesto que dicha persona utilizó o llevaba consigo {arma_elem}")
        if fuga:
            agregar_frase(partes, f"Luego del hecho observé que se dio a la fuga o se retiró en dirección hacia {fuga}")
        if vio:
            agregar_frase(partes, f"Manifiesto que respecto de si pude verlo correctamente: {vio}")
        if conoce:
            agregar_frase(partes, f"Respecto de si conozco al autor, manifiesto que {conoce}")
        if reconoce:
            agregar_frase(partes, f"Consultada sobre si podría reconocerlo nuevamente, manifiesto que {reconoce}")
        if conexion:
            agregar_frase(partes, f"Respecto de la persona retenida o aprehendida, manifiesto que {conexion}")

    if "amenazas" in activos:
        frase = val("b3_resp_amenaza_frase")
        amed = val("b3_resp_amenaza_amedrentamiento")
        temor = val("b3_resp_amenaza_temor_integridad")
        vinc = val("b3_resp_amenaza_vinculo")
        medio = val("b3_resp_amenaza_medio_prueba")
        if frase:
            agregar_frase(partes, f"Manifiesto que la amenaza recibida fue textual: '{frase}'")
        if amed:
            agregar_frase(partes, f"Ante dicha expresión, manifiesto que {amed}")
        if temor:
            agregar_frase(partes, f"Asimismo manifiesto que {temor}")
        if vinc:
            agregar_frase(partes, f"En cuanto al vínculo con el autor y el motivo de mi temor, manifiesto que {vinc}")
        if medio:
            agregar_frase(partes, f"Sobre el medio utilizado y posibles pruebas, manifiesto que {medio}")

    if "robo" in activos:
        obj = val("b3_resp_robo_objeto")
        modo = val("b3_resp_robo_modo")
        rec = val("b3_resp_robo_recupero")
        if obj:
            agregar_frase(partes, f"Manifiesto que el elemento sustraído o que intentaron sustraerme fue {obj}")
        if modo:
            agregar_frase(partes, f"Respecto de la forma en que se produjo la sustracción, manifiesto que {modo}")
        if rec:
            agregar_frase(partes, f"En cuanto al recupero o secuestro de elementos, manifiesto que {rec}")

    if "hurto" in activos:
        hurto = val("b3_resp_hurto_detalle")
        if hurto:
            agregar_frase(partes, f"Respecto de la sustracción sin violencia, manifiesto que {hurto}")

    if "arma" in activos:
        arma = val("b3_resp_arma_descripcion")
        uso = val("b3_resp_arma_uso")
        if arma:
            agregar_frase(partes, f"Sobre el arma o elemento observado, manifiesto que se trataba de {arma}")
        if uso:
            agregar_frase(partes, f"En relación al uso de dicho elemento, manifiesto que {uso}")

    if "lesiones" in activos:
        mecanismo = val("b3_resp_lesion_mecanismo")
        zona = val("b3_resp_lesion_zona")
        asistencia = val("b3_resp_lesion_asistencia")
        instancia = val("b3_resp_lesion_instancia")
        if mecanismo:
            agregar_frase(partes, f"Manifiesto que las lesiones se produjeron de la siguiente manera: {mecanismo}")
        if zona:
            agregar_frase(partes, f"Manifiesto que resultó afectada la siguiente zona del cuerpo o presento la siguiente lesión/dolor: {zona}")
        if asistencia:
            agregar_frase(partes, f"Respecto de la asistencia médica, manifiesto que {asistencia}")
        if instancia == "SÍ":
            agregar_frase(partes, "En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas")
        elif instancia == "NO":
            agregar_frase(partes, "En este acto manifiesto que no es mi deseo instar la acción penal por las lesiones sufridas")
        elif instancia == "DESEA PENSARLO / NO RESPONDE":
            agregar_frase(partes, "Consultada respecto de la instancia penal por las lesiones sufridas, manifiesto que deseo pensarlo o no respondo en este acto")

    if "danio" in activos and val("b3_resp_danio_detalle"):
        agregar_frase(partes, f"Respecto de los daños, manifiesto que {val('b3_resp_danio_detalle')}")

    if "genero" in activos:
        if val("b3_resp_genero_contexto"):
            agregar_frase(partes, f"En cuanto al vínculo o contexto familiar, manifiesto que {val('b3_resp_genero_contexto')}")
        if val("b3_resp_genero_riesgo"):
            agregar_frase(partes, f"Respecto de mi situación actual de riesgo o temor, manifiesto que {val('b3_resp_genero_riesgo')}")

    if "prueba" in activos and val("b3_resp_prueba_detalle"):
        agregar_frase(partes, f"En relación a testigos, cámaras, mensajes, audios, capturas u otros elementos de prueba, manifiesto que {val('b3_resp_prueba_detalle')}")

    if "otro" in activos and val("b3_resp_otro_detalle"):
        agregar_frase(partes, f"Asimismo manifiesto como dato de interés para la actuación que {val('b3_resp_otro_detalle')}")

    constancia = construir_constancia_resguardo()
    if constancia:
        agregar_frase(partes, constancia)

    texto = "\n\n".join(partes).strip()
    texto = re.sub(r"[ ]+", " ", texto).replace("..", ".")
    return texto


def generar_noticia_criminis(filiacion, relato_final, activos):
    nombre = texto_limpio(filiacion.get("nombre", "")) or "S/D"
    dni = texto_limpio(filiacion.get("dni", ""))

    intro = f"Seguidamente se entrevista a quien dijo llamarse {nombre}"
    if dni:
        intro += f", DNI Nro. {dni}"
    intro += ", quien manifestó que "

    partes = []
    relato = texto_limpio(relato_final or val("b3_relato_inicial", ""))
    if relato:
        partes.append(texto_corto(relato, 420).rstrip("."))

    obj = val("b3_resp_robo_objeto")
    modo = val("b3_resp_robo_modo")
    arma = val("b3_resp_arma_descripcion") or val("b3_resp_autor_arma_elemento")
    vest = val("b3_resp_autor_vestimenta")
    desc = val("b3_resp_autor_descripcion")
    cont = val("b3_resp_autor_contextura")
    rasgos = val("b3_resp_autor_rasgos")
    fuga = val("b3_resp_autor_direccion_fuga")
    conexion = val("b3_resp_autor_conexion_aprehendido")
    lesiones = val("b3_resp_lesion_zona")
    amenaza = val("b3_resp_amenaza_frase")

    extras = []
    if obj:
        extras.append(f"manifestó que el elemento sustraído o que intentaron sustraerle fue {obj}")
    if modo:
        extras.append(f"manifestó que la modalidad del hecho fue {modo}")
    if arma:
        extras.append(f"manifestó que el autor utilizó o exhibió {arma}")
    datos_autor = []
    if desc:
        datos_autor.append(desc)
    if cont:
        datos_autor.append(f"contextura {cont}")
    if vest:
        datos_autor.append(f"vestía {vest}")
    if rasgos:
        datos_autor.append(f"rasgos/señas: {rasgos}")
    if datos_autor:
        extras.append("manifestó que el autor era " + ", ".join(datos_autor))
    if amenaza:
        extras.append(f"manifestó que fue amenazado/a con la expresión textual '{amenaza}'")
    if lesiones:
        extras.append(f"manifestó que resultó lesionado/a o dolorido/a en {lesiones}")
    if fuga:
        extras.append(f"manifestó que el autor se retiró o fugó hacia {fuga}")
    if conexion:
        extras.append(f"manifestó respecto de la persona retenida/aprehendida que {conexion}")

    # Evita duplicar demasiado si el relato ya es suficientemente completo.
    if extras:
        partes.append("Asimismo, " + "; asimismo, ".join(extras[:6]))

    cuerpo = ". ".join([p for p in partes if p]).strip()
    if not cuerpo:
        cuerpo = "aportó datos vinculados al hecho que motiva la intervención policial"

    noticia = intro + cuerpo.rstrip(".") + "."
    noticia = re.sub(r"\s+", " ", noticia).replace("..", ".").strip()
    return texto_corto(noticia, 1400)


# =====================================================
# FIRMA
# =====================================================

def firma_canvas_a_path(canvas_result):
    if not CANVAS_DISPONIBLE or Image is None:
        return None
    if canvas_result is None or getattr(canvas_result, "image_data", None) is None:
        return None
    try:
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
    except Exception:
        return None


def firma_upload_a_path(uploaded_file):
    if uploaded_file is None or Image is None:
        return None
    try:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "LA"):
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[-1])
            img = fondo
        else:
            img = img.convert("RGB")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        img.save(tmp.name, format="JPEG")
        return tmp.name
    except Exception:
        return None


# =====================================================
# PDF ACTA DE ENTREVISTA
# =====================================================

def generar_pdf_acta_entrevista(filiacion, relato_final, firma_path=None):
    identidad = st.session_state.get("identidad_policial", {})
    actuacion = st.session_state.get("actuacion", {})

    dependencia = (
        val("b3_dependencia_acta")
        or actuacion.get("dependencia")
        or actuacion.get("reparticion_dependencia")
        or identidad.get("dependencia")
        or "DEPENDENCIA POLICIAL"
    )
    lugar = val("b3_lugar_entrevista", "Rosario")
    fecha_ent = val("b3_fecha_entrevista", date.today())
    hora_ent = val("b3_hora_entrevista", "")
    personal = val("b3_personal_actuante") or identidad.get("nombre_apellido") or identidad.get("nombre") or "personal policial actuante"

    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

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

    apertura = (
        f"En la ciudad de {lugar}, a los {fecha_larga(fecha_ent)}, siendo las {hora_ent or '____'} horas, "
        f"el funcionario policial actuante {personal}, con prestacion de servicio en {dependencia}, "
        f"procede a entrevistar a una persona consultada sobre sus datos personales y sobre los hechos que motivan la presente actuacion."
    )
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, apertura)
    pdf.ln(3)

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

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "RELATO", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, relato_final or "S/D")
    pdf.ln(3)

    cierre = (
        "No siendo para mas, previa lectura integra y ratificacion de su contenido, "
        "se da por finalizado el presente acto, firmando la persona entrevistada junto al personal policial actuante, "
        "para debida constancia."
    )
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, cierre)
    pdf.ln(5)

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
# PDF DERECHOS DE LA VICTIMA
# =====================================================

def generar_pdf_derechos_victima(filiacion, firma_path=None):
    identidad = st.session_state.get("identidad_policial", {})
    actuacion = st.session_state.get("actuacion", {})

    dependencia = (
        val("b3_dependencia_acta")
        or actuacion.get("dependencia")
        or actuacion.get("reparticion_dependencia")
        or identidad.get("dependencia")
        or "DEPENDENCIA POLICIAL"
    )
    lugar = val("b3_lugar_entrevista", "Rosario")
    fecha_ent = val("b3_fecha_entrevista", date.today())
    hora_ent = val("b3_hora_entrevista", "")
    personal = val("b3_personal_actuante") or identidad.get("nombre_apellido") or identidad.get("nombre") or "personal policial actuante"

    derechos = derechos_victima_actual()
    domicilio_notif = derechos.get("domicilio_notificaciones") or filiacion.get("domicilio", "")
    telefono_notif = derechos.get("telefono_notificaciones") or filiacion.get("celular", "") or filiacion.get("telefono_fijo", "")
    correo_notif = derechos.get("correo_notificaciones") or filiacion.get("correo", "")

    pdf = FPDF()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, "POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "UNIDAD REGIONAL II - ROSARIO", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, limpiar_pdf(str(dependencia).upper()), ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 9, "NOTIFICACION DE DERECHOS DE LA VICTIMA", ln=True, align="C")
    pdf.ln(5)

    apertura = (
        f"En la ciudad de {lugar}, a los {fecha_larga(fecha_ent)}, siendo las {hora_ent or '____'} horas, "
        f"personal policial actuante {personal}, con prestacion de servicio en {dependencia}, procede a notificar "
        f"a quien dijo llamarse {filiacion.get('nombre','S/D')}, DNI Nro. {filiacion.get('dni','S/D')}, "
        f"domiciliado/a en {filiacion.get('domicilio','S/D')}, respecto de los derechos que le asisten en su caracter "
        f"de victima/damnificado/a en las presentes actuaciones."
    )
    pdf.set_font("Arial", "", 10)
    pdf_multi(pdf, apertura)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DERECHOS INFORMADOS", ln=True)
    pdf.set_font("Arial", "", 9)
    items = [
        "A recibir un trato digno y respetuoso por parte de las autoridades intervinientes.",
        "A ser informada sobre el estado del procedimiento y las medidas que pudieren corresponder.",
        "A aportar informacion, documentacion, testigos, imagenes, videos, audios u otros elementos utiles para la investigacion.",
        "A solicitar medidas de proteccion o resguardo cuando existieren circunstancias que lo justifiquen.",
        "A ser informada sobre organismos de asistencia, contencion y orientacion a victimas.",
        "A designar domicilio, telefono o medio electronico para recibir notificaciones vinculadas al procedimiento.",
        "A solicitar restitucion de efectos propios cuando correspondiere y conforme disposicion de autoridad competente.",
        "A ampliar su entrevista, denuncia o aporte de datos ante la autoridad competente cuando resultare necesario."
    ]
    for item in items:
        pdf_multi(pdf, f"- {item}", alto=5)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DOMICILIO Y MEDIOS PARA NOTIFICACIONES", ln=True)
    pdf.set_font("Arial", "", 10)
    medios = (
        f"Domicilio denunciado para notificaciones: {domicilio_notif or 'S/D'}.\n"
        f"Telefono: {telefono_notif or 'S/D'}.\n"
        f"Correo electronico: {correo_notif or 'S/D'}."
    )
    pdf_multi(pdf, medios)

    obs = texto_limpio(derechos.get("observaciones", ""))
    if obs:
        pdf.ln(2)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "OBSERVACIONES", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf_multi(pdf, obs)

    pdf.ln(4)
    cierre = (
        "Leida que le fuera la presente, la persona notificada manifiesta quedar debidamente anoticiada "
        "de los derechos precedentemente informados, firmando al pie para debida constancia."
    )
    pdf_multi(pdf, cierre)
    pdf.ln(7)

    if firma_path:
        try:
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 6, "Firma digital de la persona notificada:", ln=True)
            pdf.image(firma_path, x=25, w=75)
            pdf.ln(7)
        except Exception:
            pass

    pdf.ln(10)
    pdf.cell(85, 8, "____________________________", ln=False, align="C")
    pdf.cell(85, 8, "____________________________", ln=True, align="C")
    pdf.cell(85, 6, "Firma y aclaracion de la victima", ln=False, align="C")
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
fecha_b = val("b3_borrador_fecha", "")
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
        st.selectbox("Condición", ["Víctima", "Damnificado/a", "Representante legal", "Progenitor/a", "Otro"], key="b3_condicion")
        st.text_input("Apellido y nombres", key="b3_nombre")
        st.text_input("DNI", key="b3_dni")
        st.text_input("Edad", key="b3_edad")
        st.text_input("Fecha de nacimiento", key="b3_fecha_nac")
        st.text_input("Nacionalidad", key="b3_nacionalidad")
    with c2:
        st.text_input("Estado civil", key="b3_estado_civil")
        st.text_input("Profesión / ocupación", key="b3_profesion")
        st.text_area("Domicilio", key="b3_domicilio", height=80)
        st.text_input("Teléfono fijo", key="b3_telefono_fijo")
        st.text_input("Celular", key="b3_celular")
        st.text_input("Correo electrónico", key="b3_correo")


with tabs[1]:
    st.subheader("Relato inicial")
    st.caption("Cargar el relato crudo de la víctima/damnificado. Se conserva y luego se ordena en el relato final.")
    st.text_area("Relato inicial de la víctima / damnificado", key="b3_relato_inicial", height=350)

    st.divider()
    st.subheader("Observación sobre resguardo / no contaminación del testimonio")
    opciones_resguardo = [
        "Víctima entrevistada separada del aprehendido",
        "No hubo contacto visual ni verbal previo",
        "No había aprehendido presente",
        "Entrevista recibida en lugar reservado",
        "Se evitó presencia de familiares/terceros que pudieran influir",
        "No fue posible evitar contacto previo, pero luego se entrevistó por separado",
        "No corresponde"
    ]
    st.multiselect("Seleccione las constancias que correspondan", opciones_resguardo, key="b3_resguardo_opciones")
    st.text_area("Otro / ampliar observación", key="b3_resguardo_otro", height=80)
    if st.button("Generar / actualizar constancia de resguardo", key="b3_button_constancia_resguardo"):
        construir_constancia_resguardo()
        guardar_borrador_b3()
    st.text_area("Constancia breve editable", key="b3_resguardo_constancia", height=90)


with tabs[2]:
    st.subheader("Análisis S.I.V.A.P. — guía interna")
    relato = val("b3_relato_inicial", "")
    _, activos = situaciones_activas(relato)
    etiquetas = etiquetas_situaciones(activos)
    if etiquetas:
        st.success("Del relato se observan posibles delitos/situaciones: " + ", ".join(etiquetas))
    else:
        st.warning("Del relato no se detectaron con claridad delitos/situaciones. Puede agregar manualmente una opción para activar preguntas clave.")

    st.markdown("### Agregar manualmente delito/situación no detectado")
    st.multiselect(
        "Seleccione una o más opciones para activar preguntas clave",
        [
            "robo",
            "robo con arma",
            "amenazas",
            "lesiones",
            "hurto",
            "daño",
            "violencia familiar/género",
            "arma",
            "cámaras/testigos/evidencia digital",
            "acción privada",
            "integridad sexual",
            "otro"
        ],
        key="b3_delitos_manual"
    )
    if "otro" in val("b3_delitos_manual", []):
        st.text_input("Otro delito/situación a tener en cuenta", key="b3_delito_manual_otro")

    _, activos = situaciones_activas(relato)
    st.caption("Estas preguntas son internas. No salen como cuestionario en el PDF. Las respuestas se integran al relato final como dichos de la víctima.")

    if requiere_autor(activos, relato):
        st.divider()
        st.markdown("### Descripción del autor y conexión con aprehendido")
        st.info("Estos campos son clave para justificar que la persona retenida/aprehendida es la misma señalada por la víctima.")
        ca1, ca2 = st.columns(2)
        with ca1:
            st.text_area("¿Cómo era la persona que cometió el hecho?", key="b3_resp_autor_descripcion", height=80)
            st.text_input("Vestimenta", key="b3_resp_autor_vestimenta")
            st.text_input("Contextura", key="b3_resp_autor_contextura")
            st.text_input("Edad aproximada", key="b3_resp_autor_edad_aprox")
            st.text_area("Rasgos / señas particulares", key="b3_resp_autor_rasgos", height=80)
        with ca2:
            st.text_input("Arma o elemento usado / exhibido", key="b3_resp_autor_arma_elemento")
            st.text_input("Dirección de fuga", key="b3_resp_autor_direccion_fuga")
            st.text_input("¿Lo vio bien?", key="b3_resp_autor_lo_vio_bien")
            st.text_input("¿Lo conoce? ¿De dónde?", key="b3_resp_autor_lo_conoce")
            st.text_input("¿Podría reconocerlo?", key="b3_resp_autor_podria_reconocerlo")
            st.text_area("¿La persona retenida/aprehendida es la misma que robó, amenazó o lesionó?", key="b3_resp_autor_conexion_aprehendido", height=90)

    if "amenazas" in activos:
        st.divider()
        st.markdown("### Guía interna — Amenazas")
        st.warning("Amenazas: no se pide instancia penal. Se debe precisar frase textual, amedrentamiento/intimidación y temor por integridad física.")
        st.text_input("Frase textual de la amenaza", key="b3_resp_amenaza_frase")
        st.text_area("¿Se sintió amedrentada/intimidada?", key="b3_resp_amenaza_amedrentamiento", height=80, placeholder="Ej: sentí mucho temor y me sentí amedrentada...")
        st.text_area("¿Teme por su integridad física?", key="b3_resp_amenaza_temor_integridad", height=80, placeholder="Ej: desde ese momento temo por mi integridad física...")
        st.text_area("¿Conoce al autor? ¿Qué vínculo tiene y por qué le genera temor?", key="b3_resp_amenaza_vinculo", height=80)
        st.text_area("Medio utilizado / testigos / cámaras / capturas", key="b3_resp_amenaza_medio_prueba", height=80)
        st.caption("Modelo: Cuando mi vecino me dijo textualmente 'te voy a matar', sentí mucho temor, me sentí amedrentada y desde ese momento temo por mi integridad física...")

    if "lesiones" in activos:
        st.divider()
        st.markdown("### Guía interna — Lesiones")
        if "robo" in activos:
            st.info("Robo con lesiones: el robo se mantiene como hecho principal; la instancia se pregunta únicamente por las lesiones asociadas.")
        st.text_area("¿Cómo se produjo la lesión?", key="b3_resp_lesion_mecanismo", height=80)
        st.text_area("¿Qué zona del cuerpo resultó afectada y qué lesión/dolor presenta?", key="b3_resp_lesion_zona", height=80)
        st.text_area("¿Recibió asistencia médica, ambulancia, hospital o certificado médico?", key="b3_resp_lesion_asistencia", height=80)
        st.selectbox("¿Es su deseo instar la acción penal por las lesiones sufridas?", ["NO DEFINIDO", "SÍ", "NO", "DESEA PENSARLO / NO RESPONDE"], key="b3_resp_lesion_instancia")

    if "robo" in activos:
        st.divider()
        st.markdown("### Guía interna — Robo / sustracción con violencia o intimidación")
        st.text_area("¿Qué elemento le sustrajeron o intentaron sustraer? Marca, modelo, color y características.", key="b3_resp_robo_objeto", height=80)
        st.text_area("¿Cómo fue la sustracción?", key="b3_resp_robo_modo", height=80)
        st.text_area("¿Hubo recupero, secuestro o reconocimiento de elementos?", key="b3_resp_robo_recupero", height=80)

    if "hurto" in activos:
        st.divider()
        st.markdown("### Guía interna — Hurto / sustracción sin violencia")
        st.text_area("Detalle de la sustracción sin violencia", key="b3_resp_hurto_detalle", height=80)

    if "arma" in activos:
        st.divider()
        st.markdown("### Guía interna — Arma / elemento de peligrosidad")
        st.text_input("Tipo de arma o elemento observado", key="b3_resp_arma_descripcion")
        st.text_area("¿Cómo fue utilizado?", key="b3_resp_arma_uso", height=80)

    if "danio" in activos:
        st.divider()
        st.markdown("### Guía interna — Daño")
        st.text_area("¿Qué cosa fue dañada y cómo se produjo el daño?", key="b3_resp_danio_detalle", height=90)

    if "genero" in activos:
        st.divider()
        st.markdown("### Guía interna — Contexto familiar / género")
        st.text_area("Vínculo, antecedentes o medidas vigentes", key="b3_resp_genero_contexto", height=90)
        st.text_area("Riesgo actual o temor de nuevos hechos", key="b3_resp_genero_riesgo", height=90)

    if "prueba" in activos:
        st.divider()
        st.markdown("### Guía interna — Testigos / cámaras / evidencia digital")
        st.text_area("Testigos, cámaras, mensajes, audios, capturas u otros elementos", key="b3_resp_prueba_detalle", height=90)

    if "otro" in activos:
        st.divider()
        st.markdown("### Guía interna — Otra situación")
        st.text_area("Detalle adicional para incorporar al relato", key="b3_resp_otro_detalle", height=90)

    if st.button("💾 Guardar respuestas de guía", use_container_width=True, key="b3_button_guardar_guia"):
        guardar_borrador_b3()
        st.success("Respuestas guardadas.")


with tabs[3]:
    st.subheader("Relato final y noticia criminis")
    _, activos = situaciones_activas(val("b3_relato_inicial", ""))

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🧠 Generar / actualizar relato final desde guía", use_container_width=True, key="b3_button_generar_relato_final"):
            st.session_state["b3_relato_final"] = construir_relato_final(val("b3_relato_inicial", ""), activos)
            guardar_borrador_b3()
            st.success("Relato final generado. Revíselo y corríjalo si hace falta. No se borró la noticia criminis.")
    with c2:
        if st.button("📌 Generar súper resumen / noticia criminis", use_container_width=True, key="b3_button_generar_noticia"):
            base_relato = val("b3_relato_final") or construir_relato_final(val("b3_relato_inicial", ""), activos)
            st.session_state["b3_noticia_criminis"] = generar_noticia_criminis(filiacion_actual(), base_relato, activos)
            guardar_borrador_b3()
            st.success("Noticia criminis generada. No se borró el relato final.")

    st.markdown("### A. Relato final de entrevista")
    st.caption("Va al PDF. Debe quedar en primera persona. El policía puede corregirlo libremente.")
    st.text_area("Relato final en primera persona", height=360, key="b3_relato_final")

    st.markdown("### B. Súper resumen / noticia criminis")
    st.caption("Sirve para incorporar al BLOQUE 1/BLOQUE 8. Es breve, policial y suficiente para justificar intervención o aprehensión. No reemplaza el relato completo.")
    st.info("Estilo esperado: Seguidamente se entrevista a quien dijo llamarse..., quien manifestó que...")
    st.text_area("Noticia criminis / resumen para acta de procedimiento", height=220, key="b3_noticia_criminis")


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

    st.divider()
    st.markdown("### Notificación de Derechos de la Víctima")
    st.radio("¿Se notificaron los derechos de la víctima/damnificado?", ["SI", "NO"], horizontal=True, key="b3_derechos_victima_notificada")
    st.text_area("Domicilio para recibir notificaciones", key="b3_derechos_victima_domicilio_notificaciones", placeholder="Si se deja vacío, el PDF tomará el domicilio cargado en Identificación.")
    cdv1, cdv2 = st.columns(2)
    with cdv1:
        st.text_input("Teléfono para notificaciones", key="b3_derechos_victima_telefono_notificaciones", placeholder="Si se deja vacío, tomará el celular/teléfono cargado.")
    with cdv2:
        st.text_input("Correo electrónico para notificaciones", key="b3_derechos_victima_correo_notificaciones", placeholder="Si se deja vacío, tomará el correo cargado.")
    st.text_area("Observaciones sobre la notificación de derechos", key="b3_derechos_victima_observaciones", placeholder="Ej: Se informa verbalmente en lenguaje claro y comprensible. La víctima manifiesta quedar debidamente notificada.", height=90)

    st.divider()
    st.markdown("### Firma digital de la persona entrevistada")
    st.info("La firma se realiza dentro del recuadro blanco. Si desde el celular no aparece el recuadro, use la opción alternativa: subir foto de firma.")
    firma_canvas_path = None
    if CANVAS_DISPONIBLE:
        with st.container(border=True):
            st.markdown("**Recuadro de firma:**")
            canvas_result = st_canvas(
                fill_color="rgba(255, 255, 255, 1)",
                stroke_width=4,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=220,
                width=700,
                drawing_mode="freedraw",
                key="b3_firma_canvas"
            )
        firma_canvas_path = firma_canvas_a_path(canvas_result)
    else:
        st.warning("El recuadro de firma no está disponible en este entorno. Use la opción de subir foto de firma.")

    st.markdown("### Firma alternativa")
    firma_upload = st.file_uploader("Si no puede firmar en pantalla, suba una foto/imagen de la firma", type=["jpg", "jpeg", "png"], key="b3_file_uploader_firma")
    firma_upload_path = firma_upload_a_path(firma_upload)
    firma_path = firma_canvas_path or firma_upload_path

    if firma_path:
        st.success("Firma digital detectada y lista para insertar en el PDF.")
    else:
        st.warning("Todavía no se detecta firma digital. Puede generar el PDF igual, pero sin firma insertada.")

    filiacion = filiacion_actual()
    _, activos = situaciones_activas(val("b3_relato_inicial", ""))
    relato_final = val("b3_relato_final") or construir_relato_final(val("b3_relato_inicial", ""), activos)
    noticia = val("b3_noticia_criminis") or generar_noticia_criminis(filiacion, relato_final, activos)
    analisis_interno = analizar_relato_interno(relato_final)
    datos_identidad = identidad_y_actuacion()

    datos_exportar = {
        "bloque": 3,
        "modulo": "BLOQUE_3_ENTREVISTA_VICTIMA_DAMNIFICADO",
        "version": "sivap_bloque3_corregido_metodologia_derechos_victima",
        "autor_carga": datos_identidad.get("autor_carga", {}),
        "actuacion": datos_identidad.get("actuacion", {}),
        "filiacion": filiacion,
        "datos_formales_acta": {
            "lugar": val("b3_lugar_entrevista"),
            "fecha": str(val("b3_fecha_entrevista")),
            "hora": val("b3_hora_entrevista"),
            "dependencia": val("b3_dependencia_acta"),
            "personal_actuante": val("b3_personal_actuante")
        },
        "relato_crudo": val("b3_relato_inicial"),
        "relato_primera_persona": relato_final,
        "respuestas_guia": respuestas_guia_actuales(),
        "delitos_detectados_sivap": etiquetas_situaciones({k for k, v in analisis_interno.items() if v}),
        "delitos_agregados_por_policia": val("b3_delitos_manual", []),
        "delito_manual_otro": val("b3_delito_manual_otro"),
        "noticia_criminis": noticia,
        "resumen_para_acta_procedimiento": noticia,
        "resguardo_testimonio": {
            "opciones": val("b3_resguardo_opciones", []),
            "otro": val("b3_resguardo_otro"),
            "constancia": construir_constancia_resguardo()
        },
        "derechos_victima": derechos_victima_actual(),
        "analisis_interno_sivap": {
            "detectores": analisis_interno,
            "situaciones_activas": sorted(list(activos))
        },
        "firma_digital": "SÍ" if firma_path else "NO",
        "creado_en": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    json_exportar = json.dumps(datos_exportar, ensure_ascii=False, indent=4)
    pdf_data = generar_pdf_acta_entrevista(filiacion, relato_final, firma_path)
    pdf_derechos_victima = generar_pdf_derechos_victima(filiacion, firma_path)

    c1, c2, c3, c4 = st.columns(4)
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
        st.download_button("📄 Descargar PDF Acta de Entrevista", data=pdf_data, file_name="BLOQUE_3_Acta_Entrevista.pdf", mime="application/pdf", use_container_width=True, key="b3_download_pdf")
    with c3:
        st.download_button("📥 Descargar JSON BLOQUE 3", data=json_exportar.encode("utf-8"), file_name="bloque3_entrevista_victima.json", mime="application/json", use_container_width=True, key="b3_download_json")
    with c4:
        st.download_button("📄 Descargar Derechos de la Víctima", data=pdf_derechos_victima, file_name="BLOQUE_3_Derechos_de_la_Victima.pdf", mime="application/pdf", use_container_width=True, key="b3_download_pdf_derechos_victima")

    with st.expander("Ver JSON BLOQUE 3"):
        st.code(json_exportar, language="json")


# Guardado automatico al final de la corrida
try:
    guardar_borrador_b3()
except Exception:
    pass

if USA_GUARDADO_GLOBAL:
    try:
        autoguardar_bloque(BLOQUE_ID)
    except Exception:
        pass
