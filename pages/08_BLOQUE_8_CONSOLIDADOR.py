import streamlit as st
import json
import re
from datetime import datetime, date
from fpdf import FPDF

# =====================================================
# S.I.V.A.P. - BLOQUE 8
# CONSOLIDADOR SIMPLE DEL ACTA DE PROCEDIMIENTO
#
# Objetivo único:
#   Recolectar JSON enviados por colaboradores,
#   ordenar la información importante,
#   generar el ACTA DE PROCEDIMIENTO.
#
# No incluye diligencias posteriores de comisaría.
# No reemplaza los bloques individuales.
# =====================================================

try:
    from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque
    GUARDADO_GLOBAL = True
except Exception:
    GUARDADO_GLOBAL = False

BLOQUE_ID = "BLOQUE_8_CONSOLIDADOR_ACTA_PROCEDIMIENTO"

if GUARDADO_GLOBAL:
    iniciar_guardado_seguro(BLOQUE_ID)

st.set_page_config(
    page_title="S.I.V.A.P. - Bloque 8 Consolidador",
    page_icon="🚓",
    layout="wide"
)

# =====================================================
# ESTADO
# =====================================================

if "b8_actuacion" not in st.session_state:
    st.session_state.b8_actuacion = {
        "numero_acta": "",
        "fecha": str(date.today()),
        "hora_inicio": "",
        "hora_cierre": "",
        "dependencia": "",
        "unidad_regional": "UNIDAD REGIONAL II",
        "localidad": "Rosario",
        "movil": "",
        "personal_actuante": "",
        "incidencia": "",
        "lugar_hecho": "",
        "lugar_aprehension": "",
        "mesa_enlace_fiscalia": "",
        "disposicion_fiscal": ""
    }

if "b8_jsons" not in st.session_state:
    st.session_state.b8_jsons = []

if "b8_consolidado" not in st.session_state:
    st.session_state.b8_consolidado = {}

if "b8_acta_texto" not in st.session_state:
    st.session_state.b8_acta_texto = ""




# =====================================================
# HELPERS DE WIDGETS / SESSION_STATE
# Evitan advertencias de Streamlit por usar value= junto con key.
# Primero se inicializa la key en session_state y luego el widget se crea solo con key.
# =====================================================

def _to_date_safe(valor):
    try:
        if isinstance(valor, date):
            return valor
        if isinstance(valor, str) and re.match(r"\d{4}-\d{2}-\d{2}", valor):
            return date.fromisoformat(valor[:10])
    except Exception:
        pass
    return date.today()


def _preparar_key_texto(key, valor=""):
    if key not in st.session_state or (not norm(st.session_state.get(key)) and norm(valor)):
        st.session_state[key] = str(valor or "")


def _preparar_key_fecha(key, valor=None):
    if key not in st.session_state:
        st.session_state[key] = _to_date_safe(valor)


def preparar_widgets_actuacion():
    act = st.session_state.b8_actuacion
    _preparar_key_texto("b8_numero_acta", act.get("numero_acta", ""))
    _preparar_key_fecha("b8_fecha", act.get("fecha", str(date.today())))
    _preparar_key_texto("b8_hora_inicio", act.get("hora_inicio", ""))
    _preparar_key_texto("b8_hora_cierre", act.get("hora_cierre", ""))
    _preparar_key_texto("b8_unidad", act.get("unidad_regional", "UNIDAD REGIONAL II"))
    _preparar_key_texto("b8_dependencia", act.get("dependencia", ""))
    _preparar_key_texto("b8_localidad", act.get("localidad", "Rosario"))
    _preparar_key_texto("b8_movil", act.get("movil", ""))
    _preparar_key_texto("b8_incidencia", act.get("incidencia", ""))
    _preparar_key_texto("b8_lugar_hecho", act.get("lugar_hecho", ""))
    _preparar_key_texto("b8_lugar_aprehension", act.get("lugar_aprehension", ""))
    _preparar_key_texto("b8_personal", act.get("personal_actuante", ""))
    _preparar_key_texto("b8_fiscalia", act.get("mesa_enlace_fiscalia", ""))
    _preparar_key_texto("b8_disposicion", act.get("disposicion_fiscal", ""))


def sincronizar_actuacion_desde_widgets():
    act = st.session_state.b8_actuacion
    act["numero_acta"] = st.session_state.get("b8_numero_acta", "")
    act["fecha"] = str(st.session_state.get("b8_fecha", date.today()))
    act["hora_inicio"] = st.session_state.get("b8_hora_inicio", "")
    act["hora_cierre"] = st.session_state.get("b8_hora_cierre", "")
    act["unidad_regional"] = st.session_state.get("b8_unidad", "")
    act["dependencia"] = st.session_state.get("b8_dependencia", "")
    act["localidad"] = st.session_state.get("b8_localidad", "")
    act["movil"] = st.session_state.get("b8_movil", "")
    act["incidencia"] = st.session_state.get("b8_incidencia", "")
    act["lugar_hecho"] = st.session_state.get("b8_lugar_hecho", "")
    act["lugar_aprehension"] = st.session_state.get("b8_lugar_aprehension", "")
    act["personal_actuante"] = st.session_state.get("b8_personal", "")
    act["mesa_enlace_fiscalia"] = st.session_state.get("b8_fiscalia", "")
    act["disposicion_fiscal"] = st.session_state.get("b8_disposicion", "")


# =====================================================
# UTILIDADES GENERALES
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
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto.encode("latin-1", "replace").decode("latin-1")


def pdf_bytes(pdf):
    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1", errors="replace")
    return bytes(salida)


def norm(s):
    return str(s or "").strip()


def upper_clean(s):
    return norm(s).upper()


def first_non_empty(*vals):
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
        if v not in [None, "", [], {}] and not isinstance(v, str):
            return v
    return ""


def compactar(texto, limite=900):
    texto = re.sub(r"\s+", " ", norm(texto))
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "..."


def buscar_valores(data, claves):
    """Busca valores por nombres de clave dentro de JSON de estructura variable."""
    resultados = []
    claves = [c.lower() for c in claves]

    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if any(c in kl for c in claves) and not isinstance(v, (dict, list)):
                if norm(v):
                    resultados.append(norm(v))
            if isinstance(v, (dict, list)):
                resultados.extend(buscar_valores(v, claves))
    elif isinstance(data, list):
        for item in data:
            resultados.extend(buscar_valores(item, claves))

    return resultados


def buscar_listas_por_clave(data, claves):
    resultados = []
    claves = [c.lower() for c in claves]
    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if any(c in kl for c in claves) and isinstance(v, list):
                resultados.extend(v)
            elif isinstance(v, (dict, list)):
                resultados.extend(buscar_listas_por_clave(v, claves))
    elif isinstance(data, list):
        for item in data:
            resultados.extend(buscar_listas_por_clave(item, claves))
    return resultados


def detectar_bloque(data):
    texto = json.dumps(data, ensure_ascii=False).lower()
    modulo = str(data.get("modulo", "") if isinstance(data, dict) else "").lower()
    bloque = str(data.get("bloque", "") if isinstance(data, dict) else "").lower()
    combo = f"{modulo} {bloque} {texto}"

    if "bloque_1" in combo or "bloque 1" in combo or "acta de procedimiento" in combo or "corazon" in combo:
        return "BLOQUE 1 — Datos base"
    if "bloque_2" in combo or "arrestado" in combo or "aprehendido" in combo or "detenido" in combo:
        return "BLOQUE 2 — Arrestado/Aprehendido"
    if "bloque_3" in combo or "victima" in combo or "víctima" in combo or "damnificado" in combo or "noticia_criminis" in combo:
        return "BLOQUE 3 — Víctima/Damnificado"
    if "bloque_4" in combo or "testigo" in combo or "entrevista a testigo" in combo:
        return "BLOQUE 4 — Testigo"
    if "bloque_5" in combo or "consulta" in combo:
        return "BLOQUE 5 — Consulta"
    if "bloque_6" in combo or "inspeccion" in combo or "inspección" in combo or "camaras" in combo or "cámaras" in combo:
        return "BLOQUE 6 — Inspección ocular"
    if "bloque_7" in combo or "secuestro" in combo or "elemento" in combo:
        return "BLOQUE 7 — Secuestros"
    return "JSON externo / no identificado"


def extraer_autor(data):
    if not isinstance(data, dict):
        return {}
    for k in ["autor_carga", "identidad_policial", "usuario", "policia"]:
        if isinstance(data.get(k), dict):
            return data.get(k)
    vals = {}
    for key in ["ni", "nombre_apellido", "jerarquia", "dependencia", "rol_operativo"]:
        found = buscar_valores(data, [key])
        if found:
            vals[key] = found[0]
    return vals


def extraer_actuacion(data):
    if not isinstance(data, dict):
        return {}
    for k in ["actuacion", "datos_actuacion", "procedimiento"]:
        if isinstance(data.get(k), dict):
            return data.get(k)
    return {}


def nombre_persona(d):
    if not isinstance(d, dict):
        return norm(d)
    apellido = first_non_empty(d.get("apellido"), d.get("apellidos"))
    nombre = first_non_empty(d.get("nombre"), d.get("nombres"), d.get("nombre_apellido"), d.get("nombre_completo"))
    if apellido and nombre and apellido.lower() not in nombre.lower():
        return f"{apellido}, {nombre}"
    return first_non_empty(nombre, apellido, d.get("detalle"), d.get("filiacion"))


def formatear_persona(d):
    if not isinstance(d, dict):
        return norm(d)
    nombre = nombre_persona(d)
    dni = first_non_empty(d.get("dni"), d.get("documento"))
    domicilio = first_non_empty(d.get("domicilio"), d.get("direccion"), d.get("dirección"))
    partes = []
    if nombre:
        partes.append(nombre)
    if dni:
        partes.append(f"DNI Nro. {dni}")
    if domicilio:
        partes.append(f"domicilio {domicilio}")
    return ", ".join(partes)


def normalizar_json_importado(data, nombre_archivo=""):
    bloque = detectar_bloque(data)
    autor = extraer_autor(data)
    actuacion = extraer_actuacion(data)

    resumen = {
        "archivo": nombre_archivo,
        "bloque": bloque,
        "autor": autor,
        "actuacion": actuacion,
        "data": data
    }
    return resumen


# =====================================================
# EXTRACCIÓN PARA ACTA
# =====================================================

def consolidar_jsons():
    consolidado = {
        "bloques_recibidos": [],
        "autores": [],
        "victimas": [],
        "arrestados": [],
        "testigos": [],
        "elementos": [],
        "inspeccion": [],
        "camaras": [],
        "relatos": [],
        "noticias_criminis": [],
        "diligencias": [],
        "advertencias": []
    }

    for item in st.session_state.b8_jsons:
        data = item.get("data", {})
        bloque = item.get("bloque", "JSON")
        consolidado["bloques_recibidos"].append(bloque)

        autor = item.get("autor", {})
        if autor:
            consolidado["autores"].append({"bloque": bloque, **autor})

        # Actuación: si viene en JSON y falta en la actuación activa, se sugiere
        act = item.get("actuacion", {})
        if isinstance(act, dict):
            for origen_key, destino_key in [
                ("numero_acta", "numero_acta"), ("nro_acta", "numero_acta"),
                ("fecha", "fecha"), ("dependencia", "dependencia"),
                ("reparticion", "unidad_regional"), ("movil", "movil"), ("móvil", "movil"),
                ("incidencia", "incidencia"), ("lugar_hecho", "lugar_hecho"),
                ("lugar", "lugar_hecho"), ("lugar_aprehension", "lugar_aprehension")
            ]:
                if norm(act.get(origen_key)) and not norm(st.session_state.b8_actuacion.get(destino_key)):
                    st.session_state.b8_actuacion[destino_key] = norm(act.get(origen_key))

        texto_json = json.dumps(data, ensure_ascii=False).lower()

        # BLOQUE 2: arrestados
        arrestados = []
        if isinstance(data, dict):
            if isinstance(data.get("arrestados"), list):
                arrestados.extend(data.get("arrestados"))
            arrestados.extend(buscar_listas_por_clave(data, ["arrestados", "aprehendidos", "detenidos"]))
        for a in arrestados:
            if isinstance(a, dict) and a not in consolidado["arrestados"]:
                consolidado["arrestados"].append(a)

        # BLOQUE 3: víctima
        victima_candidates = []
        if isinstance(data, dict):
            for key in ["identificacion_victima", "victima", "víctima", "damnificado", "filiacion"]:
                v = data.get(key)
                if isinstance(v, dict):
                    victima_candidates.append(v)
            victima_candidates.extend(buscar_listas_por_clave(data, ["victimas", "víctimas", "damnificados"]))
        for v in victima_candidates:
            if isinstance(v, dict) and v not in consolidado["victimas"]:
                consolidado["victimas"].append(v)

        # Testigos
        testigos = buscar_listas_por_clave(data, ["testigos"])
        for t in testigos:
            if isinstance(t, dict) and t not in consolidado["testigos"]:
                consolidado["testigos"].append(t)

        # Elementos / secuestros
        elementos = []
        if isinstance(data, dict):
            for key in ["elementos", "secuestros", "elementos_secuestrados", "lista_elementos"]:
                if isinstance(data.get(key), list):
                    elementos.extend(data.get(key))
            elementos.extend(buscar_listas_por_clave(data, ["elementos", "secuestros"]))
        for e in elementos:
            if e not in consolidado["elementos"]:
                consolidado["elementos"].append(e)

        # Relatos y resumenes importantes
        for clave in [
            "noticia_criminis", "resumen_para_acta_procedimiento", "resumen_para_acta", "relato_circunstanciado",
            "relato_final", "relato_crudo", "relato_inspeccion", "resumen_inspeccion", "resumen"
        ]:
            vals = buscar_valores(data, [clave])
            for val in vals[:3]:
                if len(val) > 15:
                    if clave == "noticia_criminis":
                        consolidado["noticias_criminis"].append({"bloque": bloque, "texto": val})
                    else:
                        consolidado["relatos"].append({"bloque": bloque, "clave": clave, "texto": val})

        # Inspección ocular / cámaras
        if "inspeccion" in texto_json or "inspección" in texto_json or "camara" in texto_json or "cámara" in texto_json:
            resumen_ins = first_non_empty(
                *buscar_valores(data, ["resumen_para_acta_procedimiento"]),
                *buscar_valores(data, ["resumen_inspeccion"]),
                *buscar_valores(data, ["relato_inspeccion"]),
                *buscar_valores(data, ["relato"])
            )
            if resumen_ins:
                consolidado["inspeccion"].append({"bloque": bloque, "texto": resumen_ins})
            camaras = buscar_listas_por_clave(data, ["camaras", "cámaras"])
            for cam in camaras:
                consolidado["camaras"].append(cam)
            cam_txt = buscar_valores(data, ["resumen_camaras", "camaras", "cámaras"])
            for ct in cam_txt:
                if ct:
                    consolidado["camaras"].append(ct)

        # Diligencias genéricas
        if "medico" in texto_json or "hospital" in texto_json or "911" in texto_json or "fiscal" in texto_json or "mesa" in texto_json:
            vals = []
            for cl in ["consulta_911", "resultado_911", "hospital", "medico", "médico", "diagnostico", "diagnóstico", "fiscal", "mesa"]:
                vals.extend(buscar_valores(data, [cl]))
            if vals:
                consolidado["diligencias"].append({"bloque": bloque, "texto": "; ".join(vals[:8])})

    # Limpieza simple de duplicados en textos
    for key in ["relatos", "noticias_criminis", "inspeccion", "diligencias"]:
        vistos = set()
        nuevos = []
        for x in consolidado[key]:
            firma = json.dumps(x, ensure_ascii=False)[:300]
            if firma not in vistos:
                nuevos.append(x)
                vistos.add(firma)
        consolidado[key] = nuevos

    st.session_state.b8_consolidado = consolidado
    return consolidado


def formatear_arrestado(a):
    if not isinstance(a, dict):
        return norm(a)
    nombre = formatear_persona(a)
    partes = [nombre] if nombre else []
    apodo = a.get("apodo")
    if apodo:
        partes.append(f"apodado {apodo}")
    domicilio = a.get("domicilio")
    if domicilio and "domicilio" not in " ".join(partes).lower():
        partes.append(f"domiciliado en {domicilio}")
    return ", ".join([p for p in partes if p])


def formatear_elemento(e):
    if isinstance(e, dict):
        desc = first_non_empty(e.get("descripcion"), e.get("descripción"), e.get("detalle"), e.get("elemento"), e.get("tipo"))
        lugar = first_non_empty(e.get("lugar_hallazgo"), e.get("hallazgo"), e.get("lugar"))
        deposito = first_non_empty(e.get("deposito"), e.get("depósito"), e.get("resguardo"))
        partes = [desc] if desc else []
        if lugar:
            partes.append(f"hallado en {lugar}")
        if deposito:
            partes.append(f"con depósito/resguardo en {deposito}")
        return ", ".join(partes)
    return norm(e)


def construir_relato_base(consolidado):
    # Preferencia: noticia criminis del Bloque 3, luego relato de Bloque 1, luego relatos relevantes.
    if consolidado.get("noticias_criminis"):
        return consolidado["noticias_criminis"][0]["texto"]

    for r in consolidado.get("relatos", []):
        if "BLOQUE 1" in r.get("bloque", "") or "relato_circunstanciado" in r.get("clave", ""):
            return r.get("texto", "")

    if consolidado.get("relatos"):
        return consolidado["relatos"][0].get("texto", "")

    return ""


def generar_acta_procedimiento(consolidado, datos_manual):
    a = st.session_state.b8_actuacion

    fecha = first_non_empty(a.get("fecha"), str(date.today()))
    hora_inicio = a.get("hora_inicio") or "____"
    hora_cierre = a.get("hora_cierre") or "____"
    localidad = a.get("localidad") or "Rosario"
    dependencia = a.get("dependencia") or "dependencia interviniente"
    movil = a.get("movil") or "móvil policial"
    personal = a.get("personal_actuante") or "personal policial actuante"
    incidencia = a.get("incidencia") or "incidencia de referencia"
    nro_acta = a.get("numero_acta") or "S/N"
    lugar_hecho = a.get("lugar_hecho") or "lugar del hecho no consignado"
    lugar_aprehension = a.get("lugar_aprehension") or lugar_hecho

    partes = []
    partes.append("ACTA DE PROCEDIMIENTO")
    partes.append("")
    partes.append(
        f"En la ciudad de {localidad}, Departamento homónimo, Provincia de Santa Fe, "
        f"a fecha {fecha}, siendo aproximadamente las {hora_inicio} horas, personal policial de {dependencia}, "
        f"a bordo del móvil {movil}, integrado por {personal}, en relación a la incidencia {incidencia}, "
        f"deja constancia del procedimiento identificado bajo Acta Nro. {nro_acta}."
    )

    relato = datos_manual.get("relato_principal") or construir_relato_base(consolidado)
    if relato:
        partes.append("")
        partes.append("RELATO CIRCUNSTANCIADO")
        partes.append(compactar(relato, 2200))
    else:
        partes.append("")
        partes.append("RELATO CIRCUNSTANCIADO")
        partes.append("Se deja constancia que el relato circunstanciado deberá ser completado por el personal actante con los datos del procedimiento.")

    # Víctimas
    victimas = consolidado.get("victimas", [])
    if victimas:
        partes.append("")
        partes.append("VÍCTIMA / DAMNIFICADO")
        for idx, v in enumerate(victimas, start=1):
            partes.append(f"{idx}. Se individualiza a {formatear_persona(v)}.")
        if consolidado.get("noticias_criminis"):
            partes.append("Se deja constancia que se recibió entrevista policial a la víctima/damnificado, cuya acta se agrega como anexo, incorporándose al presente solo su noticia criminis o resumen operativo.")

    # Arrestados
    arrestados = consolidado.get("arrestados", [])
    if arrestados:
        partes.append("")
        partes.append("APREHENDIDO / ARRESTADO")
        for idx, ar in enumerate(arrestados, start=1):
            partes.append(f"{idx}. Se procede a la identificación y aprehensión de {formatear_arrestado(ar)}.")
            if isinstance(ar, dict):
                consulta = first_non_empty(ar.get("consulta_911"), ar.get("resultado_911"))
                resultado = ar.get("resultado_911")
                if consulta or resultado:
                    partes.append(f"   Consulta 911 / antecedentes: {first_non_empty(resultado, consulta)}.")
                lesiones = ar.get("lesiones")
                detalle_les = ar.get("detalle_lesiones")
                diagnostico = ar.get("diagnostico")
                hospital = ar.get("hospital")
                medico = ar.get("medico")
                if lesiones == "SI" or detalle_les or diagnostico or hospital:
                    partes.append(
                        f"   Se deja constancia de atención médica/lesiones: {compactar(' '.join([norm(detalle_les), norm(hospital), norm(medico), norm(diagnostico)]), 500)}."
                    )
                derechos = ar.get("derechos")
                if derechos:
                    partes.append(f"   Lectura/notificación de derechos: {derechos}.")
    elif datos_manual.get("aprehension_manual"):
        partes.append("")
        partes.append("APREHENDIDO / ARRESTADO")
        partes.append(datos_manual.get("aprehension_manual"))

    # Secuestros
    elementos = consolidado.get("elementos", [])
    secuestro_manual = datos_manual.get("secuestro_manual")
    if elementos or secuestro_manual:
        partes.append("")
        partes.append("SECUESTROS / ELEMENTOS DE INTERÉS")
        if elementos:
            for idx, e in enumerate(elementos, start=1):
                texto_e = formatear_elemento(e)
                if texto_e:
                    partes.append(f"{idx}. {texto_e}.")
        if secuestro_manual:
            partes.append(secuestro_manual)
        partes.append("Los elementos secuestrados quedan documentados en las actas y anexos correspondientes.")

    # Inspección ocular
    inspecciones = consolidado.get("inspeccion", [])
    camaras = consolidado.get("camaras", [])
    if inspecciones or camaras or datos_manual.get("inspeccion_manual"):
        partes.append("")
        partes.append("INSPECCIÓN OCULAR Y RELEVAMIENTO")
        if datos_manual.get("inspeccion_manual"):
            partes.append(datos_manual.get("inspeccion_manual"))
        elif inspecciones:
            partes.append(compactar(inspecciones[0].get("texto", ""), 900))
        else:
            partes.append("Se deja constancia que se realizó inspección ocular y relevamiento del lugar conforme acta anexa.")
        if camaras:
            partes.append(f"Asimismo, se relevaron cámaras públicas y/o privadas vinculadas al lugar, registrándose {len(camaras)} referencia/s de cámara en los datos importados.")
        partes.append("El acta completa de inspección ocular y sus anexos quedan reservados como actuación complementaria.")

    # Diligencias
    diligencias_texto = []
    for d in consolidado.get("diligencias", []):
        if d.get("texto"):
            diligencias_texto.append(d.get("texto"))
    if datos_manual.get("diligencias_manual"):
        diligencias_texto.append(datos_manual.get("diligencias_manual"))
    if diligencias_texto:
        partes.append("")
        partes.append("DILIGENCIAS REALIZADAS")
        partes.append(compactar(" ".join(diligencias_texto), 1200))

    # Fiscalía / Mesa de enlace
    fiscalia = first_non_empty(a.get("mesa_enlace_fiscalia"), datos_manual.get("fiscalia_manual"))
    disposicion = first_non_empty(a.get("disposicion_fiscal"), datos_manual.get("disposicion_manual"))
    if fiscalia or disposicion:
        partes.append("")
        partes.append("INTERVENCIÓN FISCAL / MESA DE ENLACE")
        if fiscalia:
            partes.append(f"Se dio conocimiento a {fiscalia}.")
        if disposicion:
            partes.append(f"Disposición recibida: {disposicion}.")

    # Anexos
    partes.append("")
    partes.append("ANEXOS")
    anexos = []
    bloques = " | ".join(consolidado.get("bloques_recibidos", []))
    if "BLOQUE 2" in bloques:
        anexos.append("Acta / constancia de arrestado-aprehendido")
    if "BLOQUE 3" in bloques:
        anexos.append("Acta de entrevista a víctima/damnificado y derechos de la víctima")
    if "BLOQUE 4" in bloques:
        anexos.append("Actas de entrevista a testigos")
    if "BLOQUE 6" in bloques:
        anexos.append("Acta de inspección ocular, relevamiento y anexos fotográficos")
    if "BLOQUE 7" in bloques:
        anexos.append("Actas de secuestro / elementos")
    if anexos:
        for an in anexos:
            partes.append(f"- {an}.")
    else:
        partes.append("- Se agregan las constancias y anexos que correspondan al procedimiento.")

    partes.append("")
    partes.append("CIERRE")
    partes.append(
        f"No siendo para más, siendo las {hora_cierre} horas, se da por finalizada la presente actuación, "
        f"firmando al pie el personal interviniente para constancia."
    )

    return "\n\n".join(partes).strip()


# =====================================================
# PDF
# =====================================================

class PDFActa(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 7, limpiar_pdf("POLICÍA DE LA PROVINCIA DE SANTA FE"), ln=True, align="C")
        self.set_font("Arial", "B", 10)
        self.cell(0, 6, limpiar_pdf("S.I.V.A.P. — Sistema Integrado de Validación de Actuaciones Policiales"), ln=True, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 8, limpiar_pdf(f"Página {self.page_no()}"), align="C")


def generar_pdf_acta(texto):
    pdf = PDFActa()
    pdf.set_margins(18, 12, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Arial", "", 11)

    for parrafo in limpiar_pdf(texto).split("\n"):
        if parrafo.strip() == "":
            pdf.ln(3)
        elif parrafo.strip().isupper() and len(parrafo.strip()) < 60:
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 7, parrafo.strip())
            pdf.set_font("Arial", "", 11)
        else:
            pdf.multi_cell(0, 7, parrafo.strip(), align="J")

    return pdf_bytes(pdf)


# =====================================================
# INTERFAZ
# =====================================================

st.title("🚓 BLOQUE 8 — CONSOLIDADOR DEL ACTA DE PROCEDIMIENTO")
st.caption("S.I.V.A.P. no inventa el procedimiento policial. Lo ordena, lo valida y lo mejora.")

if GUARDADO_GLOBAL:
    with st.sidebar:
        panel_guardado_seguro(BLOQUE_ID)

st.sidebar.info("Flujo simple: crear actuación → importar JSON → generar acta.")

# Pestañas simples

tab_act, tab_json, tab_datos, tab_acta, tab_descarga = st.tabs([
    "1. Actuación",
    "2. Importar JSON",
    "3. Datos recibidos",
    "4. Acta de Procedimiento",
    "5. Descargar"
])

# =====================================================
# 1. ACTUACION
# =====================================================
with tab_act:
    st.subheader("Actuación activa")
    st.info("Complete los datos mínimos del procedimiento. Si los JSON traen datos de actuación, el sistema puede sugerirlos automáticamente.")

    preparar_widgets_actuacion()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Nro. de acta / procedimiento", key="b8_numero_acta")
        st.date_input("Fecha", key="b8_fecha")
        st.text_input("Hora inicio / intervención", key="b8_hora_inicio")
        st.text_input("Hora cierre", key="b8_hora_cierre")
    with c2:
        st.text_input("Unidad Regional", key="b8_unidad")
        st.text_input("Dependencia", key="b8_dependencia")
        st.text_input("Localidad", key="b8_localidad")
        st.text_input("Móvil", key="b8_movil")
    with c3:
        st.text_input("Incidencia / comisión 911", key="b8_incidencia")
        st.text_area("Lugar del hecho", height=80, key="b8_lugar_hecho")
        st.text_area("Lugar de aprehensión", height=80, key="b8_lugar_aprehension")

    st.text_area("Personal actante / interviniente", height=100, key="b8_personal")

    colf1, colf2 = st.columns(2)
    with colf1:
        st.text_input("Mesa de Enlace / Fiscalía", key="b8_fiscalia")
    with colf2:
        st.text_input("Disposición fiscal / indicación recibida", key="b8_disposicion")

    sincronizar_actuacion_desde_widgets()

    st.success("Actuación cargada. Continúe en 'Importar JSON'.")


# =====================================================
# 2. IMPORTAR JSON
# =====================================================
with tab_json:
    st.subheader("Importar colaboraciones JSON recibidas por WhatsApp")

    st.markdown("""
    **Uso operativo:** el colaborador descarga su JSON, lo envía por WhatsApp al actante, y el actante lo carga aquí.  
    Puede subir **varios JSON a la vez**.
    """)

    archivos = st.file_uploader(
        "Cargar JSON recibidos por WhatsApp",
        type=["json"],
        accept_multiple_files=True,
        key="b8_uploader_jsons"
    )

    if archivos:
        if st.button("📥 Leer JSON cargados", use_container_width=True):
            nuevos = 0
            errores = []
            for archivo in archivos:
                try:
                    data = json.load(archivo)
                    item = normalizar_json_importado(data, archivo.name)

                    # Evita duplicados por nombre + contenido
                    firma = archivo.name + json.dumps(data, ensure_ascii=False)[:500]
                    ya = False
                    for existente in st.session_state.b8_jsons:
                        firma_exist = existente.get("archivo", "") + json.dumps(existente.get("data", {}), ensure_ascii=False)[:500]
                        if firma == firma_exist:
                            ya = True
                            break
                    if not ya:
                        st.session_state.b8_jsons.append(item)
                        nuevos += 1
                except Exception as e:
                    errores.append(f"{archivo.name}: {e}")

            consolidar_jsons()
            if nuevos:
                st.success(f"Se incorporaron {nuevos} JSON al tablero de recepción.")
            if errores:
                st.error("No se pudieron leer algunos archivos:\n" + "\n".join(errores))

    st.divider()
    st.markdown("### Tablero de recepción")

    if not st.session_state.b8_jsons:
        st.warning("Todavía no hay JSON cargados.")
    else:
        for idx, item in enumerate(st.session_state.b8_jsons, start=1):
            autor = item.get("autor", {}) or {}
            act = item.get("actuacion", {}) or {}
            with st.expander(f"✅ {idx}. {item.get('bloque')} — {item.get('archivo')}", expanded=False):
                st.write(f"**Archivo:** {item.get('archivo')}")
                st.write(f"**Bloque detectado:** {item.get('bloque')}")
                if autor:
                    st.write(f"**Autor carga:** {autor.get('jerarquia','')} {autor.get('nombre_apellido', autor.get('nombre',''))} — NI {autor.get('ni','')}")
                if act:
                    st.write(f"**Actuación informada:** {act}")
                if st.button(f"Eliminar JSON {idx}", key=f"b8_eliminar_json_{idx}"):
                    st.session_state.b8_jsons.pop(idx - 1)
                    consolidar_jsons()
                    st.rerun()

        if st.button("🔄 Reconsolidar datos recibidos", use_container_width=True):
            consolidar_jsons()
            st.success("Datos reconsolidados.")


# =====================================================
# 3. DATOS RECIBIDOS
# =====================================================
with tab_datos:
    st.subheader("Datos importantes recibidos")

    consolidado = consolidar_jsons()

    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("JSON cargados", len(st.session_state.b8_jsons))
    colm2.metric("Víctimas", len(consolidado.get("victimas", [])))
    colm3.metric("Arrestados", len(consolidado.get("arrestados", [])))
    colm4.metric("Elementos", len(consolidado.get("elementos", [])))

    st.markdown("### Bloques recibidos")
    if consolidado.get("bloques_recibidos"):
        for b in consolidado.get("bloques_recibidos"):
            st.success(b)
    else:
        st.warning("No hay bloques recibidos todavía.")

    t1, t2, t3, t4 = st.tabs(["Personas", "Relatos", "Secuestros", "Inspección / Cámaras"])

    with t1:
        st.markdown("#### Víctimas / Damnificados")
        if consolidado.get("victimas"):
            for v in consolidado["victimas"]:
                st.write("- " + formatear_persona(v))
        else:
            st.info("No se detectaron víctimas.")

        st.markdown("#### Arrestados / Aprehendidos")
        if consolidado.get("arrestados"):
            for a in consolidado["arrestados"]:
                st.write("- " + formatear_arrestado(a))
        else:
            st.info("No se detectaron arrestados.")

        st.markdown("#### Testigos")
        if consolidado.get("testigos"):
            for t in consolidado["testigos"]:
                st.write("- " + formatear_persona(t))
        else:
            st.info("No se detectaron testigos.")

    with t2:
        st.markdown("#### Noticias criminis")
        if consolidado.get("noticias_criminis"):
            for r in consolidado["noticias_criminis"]:
                st.text_area(r.get("bloque", "Noticia"), r.get("texto", ""), height=140)
        else:
            st.info("No se detectó noticia criminis específica.")

        st.markdown("#### Otros relatos/resúmenes")
        if consolidado.get("relatos"):
            for idx, r in enumerate(consolidado["relatos"], start=1):
                st.text_area(f"{idx}. {r.get('bloque')} — {r.get('clave')}", r.get("texto", ""), height=120)
        else:
            st.info("No se detectaron relatos/resúmenes.")

    with t3:
        if consolidado.get("elementos"):
            for e in consolidado["elementos"]:
                st.write("- " + formatear_elemento(e))
        else:
            st.info("No se detectaron secuestros o elementos.")

    with t4:
        st.markdown("#### Inspección ocular")
        if consolidado.get("inspeccion"):
            for i in consolidado["inspeccion"]:
                st.write("- " + compactar(i.get("texto", ""), 500))
        else:
            st.info("No se detectó inspección ocular.")

        st.markdown("#### Cámaras")
        if consolidado.get("camaras"):
            for cam in consolidado["camaras"][:20]:
                if isinstance(cam, dict):
                    st.write("- " + compactar(json.dumps(cam, ensure_ascii=False), 300))
                else:
                    st.write("- " + compactar(cam, 300))
        else:
            st.info("No se detectaron cámaras.")


# =====================================================
# 4. ACTA DE PROCEDIMIENTO
# =====================================================
with tab_acta:
    st.subheader("Generar Acta de Procedimiento")
    consolidado = consolidar_jsons()

    st.info("Complete solo lo que falte o lo que quiera ajustar. El acta principal debe ser resumen ordenado; las actas completas quedan como anexos.")

    relato_sugerido = construir_relato_base(consolidado)

    if "b8_relato_principal_manual" not in st.session_state or not norm(st.session_state.get("b8_relato_principal_manual")):
        st.session_state["b8_relato_principal_manual"] = relato_sugerido

    relato_principal = st.text_area(
        "Relato principal para el Acta de Procedimiento",
        height=240,
        key="b8_relato_principal_manual"
    )

    c1, c2 = st.columns(2)
    with c1:
        aprehension_manual = st.text_area("Aprehensión / arrestado — completar si falta", height=120, key="b8_aprehension_manual")
        secuestro_manual = st.text_area("Secuestros — completar si falta", height=120, key="b8_secuestro_manual")
    with c2:
        inspeccion_manual = st.text_area("Inspección ocular / cámaras — completar si falta", height=120, key="b8_inspeccion_manual")
        diligencias_manual = st.text_area("Diligencias realizadas — médico, 911, fiscalía, etc.", height=120, key="b8_diligencias_manual")

    fiscalia_manual = st.text_input("Fiscalía / Mesa de Enlace — completar si falta", key="b8_fiscalia_manual")
    disposicion_manual = st.text_input("Disposición recibida — completar si falta", key="b8_disposicion_manual")

    datos_manual = {
        "relato_principal": relato_principal,
        "aprehension_manual": aprehension_manual,
        "secuestro_manual": secuestro_manual,
        "inspeccion_manual": inspeccion_manual,
        "diligencias_manual": diligencias_manual,
        "fiscalia_manual": fiscalia_manual,
        "disposicion_manual": disposicion_manual,
    }

    if st.button("🚓 GENERAR / ACTUALIZAR ACTA DE PROCEDIMIENTO", use_container_width=True):
        st.session_state.b8_acta_texto = generar_acta_procedimiento(consolidado, datos_manual)
        st.session_state["b8_acta_final_editable"] = st.session_state.b8_acta_texto
        st.success("Acta de Procedimiento generada. Revise y edite antes de descargar.")

    st.divider()
    st.markdown("### Vista editable del Acta de Procedimiento")

    if not st.session_state.b8_acta_texto:
        st.session_state.b8_acta_texto = generar_acta_procedimiento(consolidado, datos_manual)

    if "b8_acta_final_editable" not in st.session_state:
        st.session_state["b8_acta_final_editable"] = st.session_state.b8_acta_texto

    st.text_area(
        "Acta final editable",
        height=520,
        key="b8_acta_final_editable"
    )
    st.session_state.b8_acta_texto = st.session_state.get("b8_acta_final_editable", "")


# =====================================================
# 5. DESCARGAR
# =====================================================
with tab_descarga:
    st.subheader("Descargar actuación final")

    consolidado = consolidar_jsons()

    if not st.session_state.b8_acta_texto:
        st.warning("Primero genere el Acta de Procedimiento en la pestaña 4.")
    else:
        pdf_data = generar_pdf_acta(st.session_state.b8_acta_texto)
        json_consolidado = {
            "sistema": "S.I.V.A.P. — Sistema Integrado de Validación de Actuaciones Policiales",
            "tipo": "acta_procedimiento_consolidada",
            "actuacion": st.session_state.b8_actuacion,
            "jsons_importados": [
                {
                    "archivo": x.get("archivo"),
                    "bloque": x.get("bloque"),
                    "autor": x.get("autor"),
                    "actuacion": x.get("actuacion")
                }
                for x in st.session_state.b8_jsons
            ],
            "datos_consolidados": consolidado,
            "acta_texto": st.session_state.b8_acta_texto,
            "fecha_generacion": datetime.now().isoformat()
        }
        json_data = json.dumps(json_consolidado, ensure_ascii=False, indent=4)

        nombre_base = st.session_state.b8_actuacion.get("numero_acta", "SIN_ACTA") or "SIN_ACTA"
        nombre_base = re.sub(r"[^A-Za-z0-9_-]+", "_", nombre_base)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "📄 Descargar PDF Acta de Procedimiento",
                data=pdf_data,
                file_name=f"SIVAP_ACTA_PROCEDIMIENTO_{nombre_base}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with c2:
            st.download_button(
                "📦 Descargar JSON consolidado",
                data=json_data.encode("utf-8"),
                file_name=f"SIVAP_CONSOLIDADO_{nombre_base}.json",
                mime="application/json",
                use_container_width=True
            )
        with c3:
            st.download_button(
                "📝 Descargar TXT editable",
                data=st.session_state.b8_acta_texto.encode("utf-8"),
                file_name=f"SIVAP_ACTA_PROCEDIMIENTO_{nombre_base}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with st.expander("Ver JSON consolidado"):
            st.code(json_data, language="json")

# Guardado automático del bloque al finalizar la corrida
if GUARDADO_GLOBAL:
    try:
        autoguardar_bloque(BLOQUE_ID)
    except Exception:
        pass
