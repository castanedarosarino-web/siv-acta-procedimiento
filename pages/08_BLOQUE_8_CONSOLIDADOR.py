import streamlit as st
import sqlite3
import json
import re
import os
import uuid
from datetime import datetime, date
from fpdf import FPDF
from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

# =====================================================
# S.I.V. - BLOQUE 8
# CONSTRUCTOR INTELIGENTE DE ACTAS
# Version experimental segura
#
# Idea rectora:
# CARGO DATOS UNA VEZ
# EL SISTEMA LOS ORDENA
# EL SISTEMA GENERA LAS ACTAS QUE NECESITO
#
# Esta version:
# - No reemplaza bloques anteriores.
# - Recibe JSON de bloques.
# - Permite cargar datos comunes.
# - Tiene checklist/catalogo de actas.
# - Autocompleta campos desde la base comun.
# - Permite campos manuales y campos de decision.
# - Guarda los datos nuevos para reutilizarlos.
# - Permite tomar foto/PDF como plantilla inicial.
# =====================================================

st.set_page_config(
    page_title="S.I.V. - Bloque 8 Constructor",
    page_icon="🚔",
    layout="wide"
)

# =====================================================
# GUARDADO SEGURO DEL BLOQUE 8
# Va después de st.set_page_config para evitar error de Streamlit.
# =====================================================
BLOQUE_ID = "BLOQUE_8_CONSTRUCTOR_INTELIGENTE"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

DB = "siv_bloque8_constructor.db"
UPLOAD_DIR = "plantillas_subidas"
os.makedirs(UPLOAD_DIR, exist_ok=True)

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()


# =====================================================
# BASE DE DATOS
# =====================================================

def crear_tablas():
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        clave TEXT,
        rol TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS procedimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE,
        fecha TEXT,
        dependencia TEXT,
        lugar_hecho TEXT,
        lugar_aprehension TEXT,
        incidencia TEXT,
        movil TEXT,
        personal TEXT,
        relato_base TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS datos_comunes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento TEXT,
        categoria TEXT,
        clave TEXT,
        valor TEXT,
        origen TEXT,
        actualizado_en TEXT,
        UNIQUE(procedimiento, categoria, clave)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS entidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento TEXT,
        tipo TEXT,
        nombre TEXT,
        dni TEXT,
        domicilio TEXT,
        telefono TEXT,
        detalle TEXT,
        origen TEXT,
        creado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS elementos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento TEXT,
        tipo TEXT,
        descripcion TEXT,
        lugar_hallazgo TEXT,
        deposito TEXT,
        detalle TEXT,
        origen TEXT,
        creado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS diligencias_importadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento TEXT,
        bloque_origen TEXT,
        tipo TEXT,
        resumen TEXT,
        contenido TEXT,
        datos_json TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS plantillas_actas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        categoria TEXT,
        descripcion TEXT,
        campos_json TEXT,
        plantilla_texto TEXT,
        origen TEXT,
        archivo_origen TEXT,
        activa INTEGER DEFAULT 1,
        creado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS actas_generadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento TEXT,
        plantilla_id INTEGER,
        nombre_acta TEXT,
        datos_usados_json TEXT,
        texto_final TEXT,
        pdf_path TEXT,
        generado_por TEXT,
        generado_en TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        accion TEXT,
        detalle TEXT,
        fecha TEXT
    )
    """)

    conn.commit()


def crear_usuarios_demo():
    usuarios = [
        ("actante", "1234", "ACTANTE"),
        ("gomez", "1234", "COLABORADOR"),
        ("ruiz", "1234", "COLABORADOR"),
        ("supervisor", "1234", "SUPERVISOR")
    ]
    for usuario, clave, rol in usuarios:
        c.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO usuarios (usuario, clave, rol) VALUES (?, ?, ?)",
                (usuario, clave, rol)
            )
    conn.commit()


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def auditar(accion, detalle):
    usuario = st.session_state.get("usuario", "sistema")
    c.execute(
        "INSERT INTO auditoria (usuario, accion, detalle, fecha) VALUES (?, ?, ?, ?)",
        (usuario, accion, detalle, ahora())
    )
    conn.commit()


def seed_plantillas():
    c.execute("SELECT COUNT(*) FROM plantillas_actas")
    if c.fetchone()[0] > 0:
        return

    plantillas = [
        {
            "nombre": "Acta de Procedimiento",
            "categoria": "Principal",
            "descripcion": "Cuerpo principal del procedimiento.",
            "campos": [
                {"clave": "numero_acta", "label": "Nro. de Acta", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "incidencia", "label": "Incidencia", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "dependencia", "label": "Dependencia", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "movil", "label": "Movil", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "personal_interviniente", "label": "Personal interviniente", "tipo": "decision", "opciones": "personal"},
                {"clave": "fecha", "label": "Fecha", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "hora_cierre", "label": "Hora de cierre", "tipo": "manual", "categoria": "cierre"},
                {"clave": "lugar_hecho", "label": "Lugar del hecho", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "relato_circunstanciado", "label": "Relato circunstanciado", "tipo": "manual_largo", "categoria": "relato"},
                {"clave": "funcionario_firma", "label": "Funcionario que firma", "tipo": "decision", "opciones": "personal"}
            ],
            "texto": """ACTA DE PROCEDIMIENTO UR II (S.I.V.)

En la fecha {fecha}, personal de {dependencia}, movil {movil}, en relacion a la incidencia {incidencia}, deja constancia del procedimiento identificado como Nro. {numero_acta}.

Lugar del hecho: {lugar_hecho}.

Personal interviniente: {personal_interviniente}.

Relato circunstanciado:
{relato_circunstanciado}

Cierre:
Siendo las {hora_cierre} horas, se da por finalizada la presente, firmando al pie {funcionario_firma} para constancia."""
        },
        {
            "nombre": "Acta de Aprehension",
            "categoria": "Personas",
            "descripcion": "Acta vinculada a arrestado/aprehendido.",
            "campos": [
                {"clave": "aprehendido", "label": "Aprehendido", "tipo": "decision", "opciones": "arrestados"},
                {"clave": "dni_aprehendido", "label": "DNI aprehendido", "tipo": "auto", "categoria": "arrestado"},
                {"clave": "lugar_aprehension", "label": "Lugar de aprehension", "tipo": "auto", "categoria": "procedimiento"},
                {"clave": "hora_aprehension", "label": "Hora de aprehension", "tipo": "manual", "categoria": "aprehension"},
                {"clave": "motivo_aprehension", "label": "Motivo/circunstancias", "tipo": "manual_largo", "categoria": "aprehension"},
                {"clave": "personal_firma", "label": "Policia que firma", "tipo": "decision", "opciones": "personal"},
                {"clave": "testigo_actuacion", "label": "Testigo de actuacion", "tipo": "decision", "opciones": "testigos"}
            ],
            "texto": """ACTA DE APREHENSION

En relacion al procedimiento de referencia, se deja constancia que siendo las {hora_aprehension} horas, en {lugar_aprehension}, se procedio a la aprehension de {aprehendido}, DNI {dni_aprehendido}.

Circunstancias:
{motivo_aprehension}

Firma como funcionario interviniente: {personal_firma}.
Testigo de actuacion: {testigo_actuacion}."""
        },
        {
            "nombre": "Acta de Secuestro",
            "categoria": "Elementos",
            "descripcion": "Acta para documentar elementos secuestrados.",
            "campos": [
                {"clave": "elementos_secuestrados", "label": "Elementos a incluir", "tipo": "decision_multi", "opciones": "elementos"},
                {"clave": "lugar_hallazgo", "label": "Lugar de hallazgo", "tipo": "manual", "categoria": "secuestro"},
                {"clave": "deposito", "label": "Lugar de deposito/resguardo", "tipo": "manual", "categoria": "secuestro"},
                {"clave": "testigo_actuacion", "label": "Testigo de actuacion", "tipo": "decision", "opciones": "testigos"},
                {"clave": "personal_firma", "label": "Funcionario que firma", "tipo": "decision", "opciones": "personal"},
                {"clave": "observaciones", "label": "Observaciones", "tipo": "manual_largo", "categoria": "secuestro"}
            ],
            "texto": """ACTA DE SECUESTRO

En el marco del presente procedimiento, se procede al formal secuestro de los siguientes elementos:
{elementos_secuestrados}

Lugar de hallazgo: {lugar_hallazgo}.
Lugar de deposito/resguardo: {deposito}.

Observaciones:
{observaciones}

Firma funcionario: {personal_firma}.
Testigo de actuacion: {testigo_actuacion}."""
        },
        {
            "nombre": "Acta de Entrega de Detenido",
            "categoria": "Detenidos",
            "descripcion": "Acta de entrega/recepcion de detenido.",
            "campos": [
                {"clave": "detenido", "label": "Detenido", "tipo": "decision", "opciones": "arrestados"},
                {"clave": "lugar_entrega", "label": "Lugar de entrega", "tipo": "manual", "categoria": "entrega_detenido"},
                {"clave": "hora_entrega", "label": "Hora de entrega", "tipo": "manual", "categoria": "entrega_detenido"},
                {"clave": "personal_entrega", "label": "Personal que entrega", "tipo": "decision", "opciones": "personal"},
                {"clave": "personal_recibe", "label": "Personal que recibe", "tipo": "manual", "categoria": "entrega_detenido"},
                {"clave": "estado_fisico", "label": "Estado fisico visible", "tipo": "manual", "categoria": "entrega_detenido"},
                {"clave": "observaciones", "label": "Observaciones", "tipo": "manual_largo", "categoria": "entrega_detenido"}
            ],
            "texto": """ACTA DE ENTREGA DE DETENIDO

Se deja constancia que siendo las {hora_entrega} horas, en {lugar_entrega}, personal policial procede a hacer entrega de {detenido}.

Entrega: {personal_entrega}.
Recibe: {personal_recibe}.
Estado fisico visible: {estado_fisico}.

Observaciones:
{observaciones}"""
        },
        {
            "nombre": "Acta de Entrevista Victima",
            "categoria": "Entrevistas",
            "descripcion": "Acta o constancia de entrevista a victima.",
            "campos": [
                {"clave": "victima", "label": "Victima", "tipo": "decision", "opciones": "victimas"},
                {"clave": "personal_entrevista", "label": "Personal que entrevista", "tipo": "decision", "opciones": "personal"},
                {"clave": "relato_victima", "label": "Relato de la victima", "tipo": "manual_largo", "categoria": "victima"},
                {"clave": "observaciones", "label": "Observaciones", "tipo": "manual_largo", "categoria": "victima"}
            ],
            "texto": """ACTA DE ENTREVISTA A VICTIMA

Comparece/Se entrevista a {victima}, ante personal policial {personal_entrevista}.

La misma manifiesta:
{relato_victima}

Observaciones:
{observaciones}"""
        },
        {
            "nombre": "Acta de Entrevista Testigo",
            "categoria": "Entrevistas",
            "descripcion": "Acta o constancia de entrevista testimonial.",
            "campos": [
                {"clave": "testigo", "label": "Testigo", "tipo": "decision", "opciones": "testigos"},
                {"clave": "personal_entrevista", "label": "Personal que entrevista", "tipo": "decision", "opciones": "personal"},
                {"clave": "relato_testigo", "label": "Relato del testigo", "tipo": "manual_largo", "categoria": "testigo"},
                {"clave": "observaciones", "label": "Observaciones", "tipo": "manual_largo", "categoria": "testigo"}
            ],
            "texto": """ACTA DE ENTREVISTA A TESTIGO

Se recibe entrevista a {testigo}, ante personal policial {personal_entrevista}.

El mismo manifiesta:
{relato_testigo}

Observaciones:
{observaciones}"""
        },
        {
            "nombre": "Acta de Inspeccion Ocular - Resumen",
            "categoria": "Inspeccion",
            "descripcion": "Resumen para incorporar al sumario; croquis/anexos se conservan por bloque propio.",
            "campos": [
                {"clave": "lugar_inspeccion", "label": "Lugar inspeccionado", "tipo": "auto", "categoria": "inspeccion"},
                {"clave": "resumen_inspeccion", "label": "Resumen inspeccion ocular", "tipo": "manual_largo", "categoria": "inspeccion"},
                {"clave": "camaras", "label": "Camaras relevadas", "tipo": "manual_largo", "categoria": "inspeccion"},
                {"clave": "personal_firma", "label": "Funcionario que firma", "tipo": "decision", "opciones": "personal"}
            ],
            "texto": """ACTA / RESUMEN DE INSPECCION OCULAR

Se deja constancia que se realizo inspeccion ocular en {lugar_inspeccion}.

Resumen:
{resumen_inspeccion}

Camaras/relevamiento:
{camaras}

El acta completa, croquis, fotos y anexos deberan conservarse junto al bloque de inspeccion ocular.

Firma funcionario: {personal_firma}."""
        }
    ]

    for p in plantillas:
        c.execute("""
        INSERT INTO plantillas_actas (nombre, categoria, descripcion, campos_json, plantilla_texto, origen, archivo_origen, activa, creado_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["nombre"],
            p["categoria"],
            p["descripcion"],
            json.dumps(p["campos"], ensure_ascii=False, indent=2),
            p["texto"],
            "SISTEMA",
            "",
            1,
            ahora()
        ))

    conn.commit()


crear_tablas()
crear_usuarios_demo()
seed_plantillas()


# =====================================================
# FUNCIONES DE DATOS
# =====================================================

def guardar_dato(procedimiento, categoria, clave, valor, origen="manual"):
    if valor is None:
        return
    if isinstance(valor, list):
        valor = "\n".join([str(v) for v in valor if str(v).strip()])
    valor = str(valor).strip()
    if not valor:
        return

    c.execute("""
    INSERT INTO datos_comunes (procedimiento, categoria, clave, valor, origen, actualizado_en)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(procedimiento, categoria, clave)
    DO UPDATE SET valor=excluded.valor, origen=excluded.origen, actualizado_en=excluded.actualizado_en
    """, (procedimiento, categoria, clave, valor, origen, ahora()))
    conn.commit()


def obtener_dato(procedimiento, categoria, clave):
    c.execute("""
    SELECT valor FROM datos_comunes
    WHERE procedimiento=? AND categoria=? AND clave=?
    """, (procedimiento, categoria, clave))
    row = c.fetchone()
    return row[0] if row else ""


def obtener_todos_datos(procedimiento):
    c.execute("""
    SELECT categoria, clave, valor, origen, actualizado_en
    FROM datos_comunes
    WHERE procedimiento=?
    ORDER BY categoria, clave
    """, (procedimiento,))
    return c.fetchall()


def obtener_procedimientos():
    c.execute("""
    SELECT numero, fecha, dependencia, lugar_hecho, lugar_aprehension, incidencia, movil, personal, relato_base, estado
    FROM procedimientos
    ORDER BY id DESC
    """)
    return c.fetchall()


def obtener_procedimiento(numero):
    c.execute("""
    SELECT numero, fecha, dependencia, lugar_hecho, lugar_aprehension, incidencia, movil, personal, relato_base, estado
    FROM procedimientos
    WHERE numero=?
    """, (numero,))
    return c.fetchone()


def obtener_plantillas():
    c.execute("""
    SELECT id, nombre, categoria, descripcion, campos_json, plantilla_texto, origen, archivo_origen
    FROM plantillas_actas
    WHERE activa=1
    ORDER BY categoria, nombre
    """)
    return c.fetchall()


def obtener_plantilla(pid):
    c.execute("""
    SELECT id, nombre, categoria, descripcion, campos_json, plantilla_texto, origen, archivo_origen
    FROM plantillas_actas
    WHERE id=?
    """, (pid,))
    return c.fetchone()


def listar_entidades(procedimiento, tipo):
    c.execute("""
    SELECT id, nombre, dni, domicilio, telefono, detalle
    FROM entidades
    WHERE procedimiento=? AND tipo=?
    ORDER BY id
    """, (procedimiento, tipo))
    rows = c.fetchall()
    opciones = []
    for r in rows:
        id_, nombre, dni, domicilio, telefono, detalle = r
        label = nombre or detalle or f"{tipo} #{id_}"
        if dni:
            label += f" - DNI {dni}"
        opciones.append(label)
    return opciones


def listar_personal(procedimiento):
    opciones = listar_entidades(procedimiento, "personal")
    proc = obtener_procedimiento(procedimiento)
    if proc and proc[7]:
        for item in dividir_lista_texto(proc[7]):
            if item not in opciones:
                opciones.append(item)
    return opciones


def listar_elementos(procedimiento):
    c.execute("""
    SELECT id, tipo, descripcion, lugar_hallazgo, deposito
    FROM elementos
    WHERE procedimiento=?
    ORDER BY id
    """, (procedimiento,))
    rows = c.fetchall()
    opciones = []
    for id_, tipo, descripcion, lugar, deposito in rows:
        label = descripcion or tipo or f"Elemento #{id_}"
        if lugar:
            label += f" - Hallazgo: {lugar}"
        opciones.append(label)
    return opciones


def opciones_para(procedimiento, nombre_opcion):
    if nombre_opcion == "personal":
        return listar_personal(procedimiento)
    if nombre_opcion == "testigos":
        return listar_entidades(procedimiento, "testigo")
    if nombre_opcion == "victimas":
        return listar_entidades(procedimiento, "victima")
    if nombre_opcion == "arrestados":
        return listar_entidades(procedimiento, "arrestado")
    if nombre_opcion == "elementos":
        return listar_elementos(procedimiento)
    return []


def dividir_lista_texto(texto):
    if not texto:
        return []
    partes = re.split(r"[\n;,]+", texto)
    return [p.strip() for p in partes if p.strip()]


# =====================================================
# IMPORTACION Y DETECCION SIMPLE
# =====================================================

def texto_desde_json(data, nivel=0):
    sangria = "  " * nivel
    lineas = []

    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lineas.append(f"{sangria}{k}:")
                lineas.append(texto_desde_json(v, nivel + 1))
            else:
                lineas.append(f"{sangria}{k}: {v}")
    elif isinstance(data, list):
        for i, item in enumerate(data, start=1):
            lineas.append(f"{sangria}- Item {i}:")
            lineas.append(texto_desde_json(item, nivel + 1))
    else:
        lineas.append(f"{sangria}{data}")

    return "\n".join(lineas)


def detectar_bloque(data):
    texto = json.dumps(data, ensure_ascii=False).lower()
    if "arrestado" in texto or "aprehendido" in texto or "detenido" in texto:
        return "BLOQUE 2 - ARRESTADO"
    if "victima" in texto or "víctima" in texto:
        return "VICTIMA"
    if "testigo" in texto:
        return "TESTIGOS"
    if "inspeccion" in texto or "inspección" in texto or "croquis" in texto:
        return "BLOQUE 6 - INSPECCION OCULAR"
    if "secuestro" in texto or "elemento" in texto:
        return "SECUESTROS"
    return "JSON EXTERNO"


def buscar_valores_por_claves(data, claves):
    resultados = []
    if isinstance(data, dict):
        for k, v in data.items():
            kl = str(k).lower()
            if any(cl in kl for cl in claves) and not isinstance(v, (dict, list)):
                if str(v).strip():
                    resultados.append(str(v).strip())
            elif isinstance(v, (dict, list)):
                resultados.extend(buscar_valores_por_claves(v, claves))
    elif isinstance(data, list):
        for item in data:
            resultados.extend(buscar_valores_por_claves(item, claves))
    return resultados


def importar_datos_minimos_desde_json(procedimiento, data, bloque):
    """
    Importa datos utiles sin destruir estructura.
    Deteccion simple y conservadora.
    """
    texto = texto_desde_json(data)
    resumenes = buscar_valores_por_claves(data, ["resumen", "relato", "descripcion", "diagnostico", "resultado", "hecho"])
    resumen = resumenes[0] if resumenes else f"Informacion importada desde {bloque}"

    c.execute("""
    INSERT INTO diligencias_importadas (procedimiento, bloque_origen, tipo, resumen, contenido, datos_json, estado, creado_por, creado_en)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        procedimiento,
        bloque,
        "DATO_IMPORTADO",
        resumen[:500],
        texto,
        json.dumps(data, ensure_ascii=False, indent=2),
        "IMPORTADO",
        st.session_state.usuario,
        ahora()
    ))

    # Datos generales
    for clave in ["dependencia", "incidencia", "movil", "móvil", "lugar", "hora", "fecha"]:
        vals = buscar_valores_por_claves(data, [clave])
        if vals:
            guardar_dato(procedimiento, "importado", clave.replace("ó", "o"), vals[0], bloque)

    # Personas
    texto_l = json.dumps(data, ensure_ascii=False).lower()
    nombres = buscar_valores_por_claves(data, ["nombre", "apellido"])
    dnis = buscar_valores_por_claves(data, ["dni", "documento"])

    tipo_entidad = None
    if "arrestado" in texto_l or "aprehendido" in texto_l or "detenido" in texto_l:
        tipo_entidad = "arrestado"
    elif "victima" in texto_l or "víctima" in texto_l:
        tipo_entidad = "victima"
    elif "testigo" in texto_l:
        tipo_entidad = "testigo"

    if tipo_entidad and nombres:
        nombre = " ".join(nombres[:2]) if len(nombres) >= 2 else nombres[0]
        dni = dnis[0] if dnis else ""
        c.execute("""
        INSERT INTO entidades (procedimiento, tipo, nombre, dni, domicilio, telefono, detalle, origen, creado_en)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (procedimiento, tipo_entidad, nombre, dni, "", "", resumen[:300], bloque, ahora()))

    # Elementos
    if "secuestro" in texto_l or "elemento" in texto_l:
        elementos = buscar_valores_por_claves(data, ["elemento", "descripcion", "descripción"])
        if elementos:
            c.execute("""
            INSERT INTO elementos (procedimiento, tipo, descripcion, lugar_hallazgo, deposito, detalle, origen, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                procedimiento,
                "secuestro",
                elementos[0],
                "",
                "",
                resumen[:300],
                bloque,
                ahora()
            ))

    # Inspeccion
    if "inspeccion" in texto_l or "inspección" in texto_l:
        guardar_dato(procedimiento, "inspeccion", "resumen_inspeccion", resumen, bloque)
        lugares = buscar_valores_por_claves(data, ["lugar", "direccion", "dirección"])
        if lugares:
            guardar_dato(procedimiento, "inspeccion", "lugar_inspeccion", lugares[0], bloque)
        camaras = buscar_valores_por_claves(data, ["camara", "cámara", "camaras", "cámaras"])
        if camaras:
            guardar_dato(procedimiento, "inspeccion", "camaras", "\n".join(camaras[:5]), bloque)

    conn.commit()


# =====================================================
# PLANTILLAS Y PDF
# =====================================================

def detectar_campos_en_texto(texto):
    """
    Detecta placeholders tipo {campo}.
    Tambien sugiere campos por lineas con ':'.
    """
    campos = []
    vistos = set()

    for m in re.findall(r"\{([a-zA-Z0-9_]+)\}", texto):
        if m not in vistos:
            campos.append(m)
            vistos.add(m)

    for line in texto.splitlines():
        if ":" in line and len(line) < 90:
            posible = line.split(":")[0].strip().lower()
            posible = re.sub(r"[^a-z0-9áéíóúñ_ ]", "", posible)
            posible = posible.replace(" ", "_")
            posible = posible.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
            if posible and posible not in vistos and len(posible) > 2:
                campos.append(posible)
                vistos.add(posible)

    return campos


def renderizar_plantilla(texto, datos):
    salida = texto
    for k, v in datos.items():
        salida = salida.replace("{" + k + "}", str(v))
    # Deja vacios los placeholders no completados
    salida = re.sub(r"\{[a-zA-Z0-9_]+\}", "________________", salida)
    return salida


def limpiar_pdf_texto(s):
    if s is None:
        return ""
    s = str(s)
    # fpdf clasico trabaja mejor con latin-1.
    reemplazos = {
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-", "•": "-", "…": "...",
    }
    for a, b in reemplazos.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class PDFActa(FPDF):
    def header(self):
        self.set_font("Arial", "B", 11)
        self.cell(0, 8, limpiar_pdf_texto("POLICIA DE LA PROVINCIA DE SANTA FE"), 0, 1, "C")
        self.set_font("Arial", "", 9)
        self.cell(0, 6, limpiar_pdf_texto("S.I.V. - Sistema Integral de Vigilancia y Procedimientos"), 0, 1, "C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, limpiar_pdf_texto(f"Pagina {self.page_no()}"), 0, 0, "C")


def generar_pdf(texto, nombre_base):
    pdf = PDFActa()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Arial", "", 11)

    for parrafo in limpiar_pdf_texto(texto).split("\n"):
        if parrafo.strip() == "":
            pdf.ln(4)
        else:
            pdf.multi_cell(0, 7, parrafo)

    filename = f"{nombre_base}_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(UPLOAD_DIR, filename)
    pdf.output(path)
    return path


def guardar_acta_generada(procedimiento, plantilla_id, nombre_acta, datos, texto_final, pdf_path):
    c.execute("""
    INSERT INTO actas_generadas (procedimiento, plantilla_id, nombre_acta, datos_usados_json, texto_final, pdf_path, generado_por, generado_en)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        procedimiento,
        plantilla_id,
        nombre_acta,
        json.dumps(datos, ensure_ascii=False, indent=2),
        texto_final,
        pdf_path,
        st.session_state.usuario,
        ahora()
    ))
    conn.commit()


# =====================================================
# LOGIN
# =====================================================

if "login" not in st.session_state:
    st.session_state.login = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "rol" not in st.session_state:
    st.session_state.rol = ""

if not st.session_state.login:
    st.title("🚔 S.I.V. - BLOQUE 8")
    st.subheader("Constructor Inteligente de Actas")

    col1, col2 = st.columns([1, 1])

    with col1:
        usuario = st.text_input("Usuario")
        clave = st.text_input("Clave", type="password")

        if st.button("Ingresar", use_container_width=True):
            c.execute("SELECT usuario, rol FROM usuarios WHERE usuario=? AND clave=?", (usuario, clave))
            row = c.fetchone()
            if row:
                st.session_state.login = True
                st.session_state.usuario = row[0]
                st.session_state.rol = row[1]
                auditar("LOGIN", "Ingreso al sistema")
                st.rerun()
            else:
                st.error("Usuario o clave incorrectos")

    with col2:
        st.info("""
        Usuarios demo:

        - actante / 1234
        - gomez / 1234
        - supervisor / 1234
        """)

    st.stop()


# =====================================================
# CABECERA Y MENU
# =====================================================

st.title("🚔 S.I.V. - BLOQUE 8: Constructor Inteligente de Actas")

h1, h2, h3, h4 = st.columns(4)
h1.success(f"Usuario: {st.session_state.usuario}")
h2.info(f"Rol: {st.session_state.rol}")
h3.warning(datetime.now().strftime("%d/%m/%Y %H:%M"))

with h4:
    if st.button("Cerrar sesion", use_container_width=True):
        auditar("LOGOUT", "Cierre de sesion")
        st.session_state.login = False
        st.session_state.usuario = ""
        st.session_state.rol = ""
        st.rerun()

menu = st.sidebar.radio(
    "Menu",
    [
        "Inicio",
        "1. Datos Base",
        "2. Importar JSON de Bloques",
        "3. Base Comun del Procedimiento",
        "4. Constructor de Actas",
        "5. Tomar Foto/PDF como Plantilla",
        "6. Actas Generadas",
        "7. Auditoria"
    ]
)


def seleccionar_procedimiento(abiertos=False):
    procedimientos = obtener_procedimientos()
    if abiertos:
        procedimientos = [p for p in procedimientos if p[9] == "ABIERTO"]
    lista = [p[0] for p in procedimientos]
    if not lista:
        st.warning("No hay procedimientos cargados.")
        st.stop()
    return st.selectbox("Seleccionar procedimiento", lista)


# =====================================================
# INICIO
# =====================================================

if menu == "Inicio":
    st.subheader("Idea rectora")

    st.code("""CARGO DATOS UNA VEZ
        ↓
EL SISTEMA LOS ORDENA
        ↓
EL SISTEMA GENERA LAS ACTAS QUE NECESITO""")

    st.markdown("""
    Este BLOQUE 8 no reemplaza los bloques individuales.  
    Cada bloque puede generar su PDF propio para firmar/imprimir y tambien exportar JSON.

    El BLOQUE 8 toma esa informacion y permite construir distintas actas:
    - con campos automaticos;
    - con campos de decision;
    - con campos manuales faltantes;
    - guardando lo nuevo para futuras actas.
    """)

    procs = obtener_procedimientos()
    c.execute("SELECT COUNT(*) FROM datos_comunes")
    datos_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM plantillas_actas WHERE activa=1")
    plant_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM actas_generadas")
    actas_count = c.fetchone()[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Procedimientos", len(procs))
    m2.metric("Datos comunes", datos_count)
    m3.metric("Plantillas", plant_count)
    m4.metric("Actas generadas", actas_count)


# =====================================================
# DATOS BASE
# =====================================================

if menu == "1. Datos Base":
    st.subheader("1. Datos Base del Procedimiento")

    tab1, tab2 = st.tabs(["Crear procedimiento", "Agregar personas/elementos"])

    with tab1:
        with st.form("crear_proc"):
            numero = st.text_input("Nro. de acta / procedimiento")
            fecha = st.date_input("Fecha", value=date.today())
            dependencia = st.text_input("Dependencia")
            incidencia = st.text_input("Incidencia")
            movil = st.text_input("Movil")
            personal = st.text_area("Personal interviniente (uno por linea o separado por coma)")
            lugar_hecho = st.text_input("Lugar del hecho")
            lugar_aprehension = st.text_input("Lugar de aprehension")
            relato_base = st.text_area("Relato base / circunstanciado inicial", height=200)

            crear = st.form_submit_button("Crear / guardar procedimiento", use_container_width=True)

        if crear:
            if not numero:
                st.error("Debe indicar nro. de acta/procedimiento.")
            else:
                try:
                    c.execute("""
                    INSERT INTO procedimientos (numero, fecha, dependencia, lugar_hecho, lugar_aprehension, incidencia, movil, personal, relato_base, estado, creado_por, creado_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        numero, str(fecha), dependencia, lugar_hecho, lugar_aprehension,
                        incidencia, movil, personal, relato_base, "ABIERTO",
                        st.session_state.usuario, ahora()
                    ))
                    conn.commit()

                    # Base comun
                    guardar_dato(numero, "procedimiento", "numero_acta", numero, "datos_base")
                    guardar_dato(numero, "procedimiento", "fecha", str(fecha), "datos_base")
                    guardar_dato(numero, "procedimiento", "dependencia", dependencia, "datos_base")
                    guardar_dato(numero, "procedimiento", "incidencia", incidencia, "datos_base")
                    guardar_dato(numero, "procedimiento", "movil", movil, "datos_base")
                    guardar_dato(numero, "procedimiento", "lugar_hecho", lugar_hecho, "datos_base")
                    guardar_dato(numero, "procedimiento", "lugar_aprehension", lugar_aprehension, "datos_base")
                    guardar_dato(numero, "relato", "relato_circunstanciado", relato_base, "datos_base")

                    for p in dividir_lista_texto(personal):
                        c.execute("""
                        INSERT INTO entidades (procedimiento, tipo, nombre, dni, domicilio, telefono, detalle, origen, creado_en)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (numero, "personal", p, "", "", "", "", "datos_base", ahora()))
                    conn.commit()

                    auditar("CREAR_PROCEDIMIENTO", numero)
                    st.success("Procedimiento creado y datos incorporados a la base comun.")
                except sqlite3.IntegrityError:
                    st.error("Ya existe un procedimiento con ese numero.")

    with tab2:
        procedimiento = seleccionar_procedimiento(abiertos=True)

        st.markdown("### Agregar persona")
        colp1, colp2 = st.columns(2)
        with colp1:
            tipo = st.selectbox("Tipo", ["personal", "arrestado", "victima", "testigo", "familiar", "medico", "fiscal", "otro"])
            nombre = st.text_input("Nombre completo")
            dni = st.text_input("DNI")
        with colp2:
            domicilio = st.text_input("Domicilio")
            telefono = st.text_input("Telefono")
            detalle = st.text_area("Detalle / rol / observaciones", height=100)

        if st.button("Agregar persona", use_container_width=True):
            if nombre or detalle:
                c.execute("""
                INSERT INTO entidades (procedimiento, tipo, nombre, dni, domicilio, telefono, detalle, origen, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (procedimiento, tipo, nombre, dni, domicilio, telefono, detalle, "manual", ahora()))
                conn.commit()
                auditar("AGREGAR_PERSONA", f"{tipo} - {nombre}")
                st.success("Persona agregada.")
            else:
                st.error("Debe cargar al menos nombre o detalle.")

        st.divider()
        st.markdown("### Agregar elemento / secuestro")
        cole1, cole2 = st.columns(2)
        with cole1:
            tipo_el = st.text_input("Tipo de elemento", value="secuestro")
            descripcion = st.text_area("Descripcion del elemento", height=100)
        with cole2:
            lugar_hallazgo = st.text_input("Lugar de hallazgo")
            deposito = st.text_input("Deposito / resguardo")
            detalle_el = st.text_area("Detalle adicional", height=100)

        if st.button("Agregar elemento", use_container_width=True):
            if descripcion:
                c.execute("""
                INSERT INTO elementos (procedimiento, tipo, descripcion, lugar_hallazgo, deposito, detalle, origen, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (procedimiento, tipo_el, descripcion, lugar_hallazgo, deposito, detalle_el, "manual", ahora()))
                conn.commit()
                auditar("AGREGAR_ELEMENTO", descripcion[:100])
                st.success("Elemento agregado.")
            else:
                st.error("Debe cargar descripcion.")


# =====================================================
# IMPORTAR JSON
# =====================================================

if menu == "2. Importar JSON de Bloques":
    st.subheader("2. Importar JSON de Bloques Independientes")

    procedimiento = seleccionar_procedimiento(abiertos=True)

    st.info("El JSON alimenta la base comun. El PDF propio de cada bloque sigue siendo valido para firmar/imprimir.")

    archivo = st.file_uploader("Cargar JSON", type=["json"])

    if archivo is not None:
        try:
            data = json.load(archivo)
            bloque = detectar_bloque(data)
            st.success(f"JSON leido. Bloque detectado: {bloque}")

            with st.expander("Vista previa del JSON convertido a texto"):
                st.text_area("Contenido", texto_desde_json(data), height=350)

            bloque_edit = st.text_input("Bloque origen", value=bloque)

            if st.button("Importar a la base comun", use_container_width=True):
                importar_datos_minimos_desde_json(procedimiento, data, bloque_edit)
                auditar("IMPORTAR_JSON", f"{procedimiento} - {bloque_edit}")
                st.success("JSON importado. Los datos utiles ya pueden ser usados por el constructor de actas.")

        except Exception as e:
            st.error(f"No se pudo leer el JSON: {e}")


# =====================================================
# BASE COMUN
# =====================================================

if menu == "3. Base Comun del Procedimiento":
    st.subheader("3. Base Comun del Procedimiento")

    procedimiento = seleccionar_procedimiento()

    tab1, tab2, tab3 = st.tabs(["Datos comunes", "Personas", "Elementos"])

    with tab1:
        datos = obtener_todos_datos(procedimiento)
        if datos:
            st.dataframe(
                [{"Categoria": d[0], "Clave": d[1], "Valor": d[2], "Origen": d[3], "Actualizado": d[4]} for d in datos],
                use_container_width=True
            )
        else:
            st.info("No hay datos comunes cargados.")

        st.markdown("### Agregar dato manual reutilizable")
        col1, col2 = st.columns(2)
        with col1:
            categoria = st.text_input("Categoria", value="manual")
            clave = st.text_input("Clave", placeholder="ej: hora_entrega")
        with col2:
            valor = st.text_area("Valor", height=100)

        if st.button("Guardar dato comun", use_container_width=True):
            guardar_dato(procedimiento, categoria, clave, valor, "manual")
            auditar("GUARDAR_DATO_COMUN", f"{categoria}.{clave}")
            st.success("Dato guardado para reutilizar en otras actas.")

    with tab2:
        c.execute("""
        SELECT tipo, nombre, dni, domicilio, telefono, detalle, origen
        FROM entidades
        WHERE procedimiento=?
        ORDER BY tipo, id
        """, (procedimiento,))
        rows = c.fetchall()
        if rows:
            st.dataframe(
                [{"Tipo": r[0], "Nombre": r[1], "DNI": r[2], "Domicilio": r[3], "Telefono": r[4], "Detalle": r[5], "Origen": r[6]} for r in rows],
                use_container_width=True
            )
        else:
            st.info("No hay personas cargadas.")

    with tab3:
        c.execute("""
        SELECT tipo, descripcion, lugar_hallazgo, deposito, detalle, origen
        FROM elementos
        WHERE procedimiento=?
        ORDER BY id
        """, (procedimiento,))
        rows = c.fetchall()
        if rows:
            st.dataframe(
                [{"Tipo": r[0], "Descripcion": r[1], "Hallazgo": r[2], "Deposito": r[3], "Detalle": r[4], "Origen": r[5]} for r in rows],
                use_container_width=True
            )
        else:
            st.info("No hay elementos cargados.")


# =====================================================
# CONSTRUCTOR DE ACTAS
# =====================================================

if menu == "4. Constructor de Actas":
    st.subheader("4. Constructor de Actas")

    procedimiento = seleccionar_procedimiento()
    plantillas = obtener_plantillas()

    if not plantillas:
        st.warning("No hay plantillas cargadas.")
        st.stop()

    st.markdown("### Checklist de actas disponibles")

    plantilla_labels = {
        f"{p[1]} [{p[2]}]": p[0]
        for p in plantillas
    }

    seleccionadas = st.multiselect(
        "Elegir actas a generar",
        list(plantilla_labels.keys())
    )

    if not seleccionadas:
        st.info("Seleccione una o mas actas.")
        st.stop()

    guardar_reutilizable = st.checkbox(
        "Guardar datos nuevos y decisiones en el S.I.V. para proximas actas",
        value=True
    )

    st.divider()

    for label in seleccionadas:
        pid = plantilla_labels[label]
        plantilla = obtener_plantilla(pid)
        pid, nombre, categoria, descripcion, campos_json, plantilla_texto, origen, archivo_origen = plantilla
        campos = json.loads(campos_json)

        st.markdown(f"## {nombre}")
        st.caption(descripcion)

        datos_acta = {}

        st.markdown("#### Datos automaticos, decisiones y faltantes")

        for campo in campos:
            clave = campo.get("clave")
            etiqueta = campo.get("label", clave)
            tipo = campo.get("tipo", "manual")
            categoria_campo = campo.get("categoria", "manual")

            if tipo == "auto":
                valor = obtener_dato(procedimiento, categoria_campo, clave)

                # Fallbacks desde procedimiento
                proc = obtener_procedimiento(procedimiento)
                if proc:
                    mapa_proc = {
                        "numero_acta": proc[0],
                        "fecha": proc[1],
                        "dependencia": proc[2],
                        "lugar_hecho": proc[3],
                        "lugar_aprehension": proc[4],
                        "incidencia": proc[5],
                        "movil": proc[6],
                        "personal_interviniente": proc[7],
                        "relato_circunstanciado": proc[8]
                    }
                    valor = valor or mapa_proc.get(clave, "")

                datos_acta[clave] = st.text_input(f"✅ {etiqueta}", value=valor, key=f"{pid}_{clave}_auto")

            elif tipo == "manual":
                valor_existente = obtener_dato(procedimiento, categoria_campo, clave)
                datos_acta[clave] = st.text_input(f"⬜ {etiqueta}", value=valor_existente, key=f"{pid}_{clave}_manual")

            elif tipo == "manual_largo":
                valor_existente = obtener_dato(procedimiento, categoria_campo, clave)
                datos_acta[clave] = st.text_area(f"⬜ {etiqueta}", value=valor_existente, height=140, key=f"{pid}_{clave}_long")

            elif tipo == "decision":
                opciones = opciones_para(procedimiento, campo.get("opciones", ""))
                opciones_final = [""] + opciones + ["AGREGAR MANUALMENTE"]
                elegido = st.selectbox(f"🔽 {etiqueta}", opciones_final, key=f"{pid}_{clave}_dec")
                if elegido == "AGREGAR MANUALMENTE":
                    elegido = st.text_input(f"Escribir {etiqueta}", key=f"{pid}_{clave}_dec_manual")
                datos_acta[clave] = elegido

            elif tipo == "decision_multi":
                opciones = opciones_para(procedimiento, campo.get("opciones", ""))
                elegidos = st.multiselect(f"🔽 {etiqueta}", opciones, key=f"{pid}_{clave}_multi")
                extra = st.text_area(f"Agregar manualmente a {etiqueta} (opcional)", height=80, key=f"{pid}_{clave}_multi_extra")
                valores = elegidos[:]
                if extra.strip():
                    valores.extend(dividir_lista_texto(extra))
                datos_acta[clave] = "\n".join(valores)

            else:
                datos_acta[clave] = st.text_input(etiqueta, key=f"{pid}_{clave}_otro")

        texto_final = renderizar_plantilla(plantilla_texto, datos_acta)

        with st.expander(f"Vista previa - {nombre}", expanded=True):
            texto_editado = st.text_area("Texto final editable antes de PDF", value=texto_final, height=360, key=f"texto_final_{pid}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"📄 Generar PDF - {nombre}", key=f"pdf_{pid}", use_container_width=True):
                if guardar_reutilizable:
                    for campo in campos:
                        clave = campo.get("clave")
                        categoria_campo = campo.get("categoria", f"acta_{nombre.lower().replace(' ', '_')}")
                        valor = datos_acta.get(clave, "")
                        guardar_dato(
                            procedimiento,
                            categoria_campo,
                            clave,
                            valor,
                            f"acta_generada:{nombre}"
                        )

                pdf_path = generar_pdf(texto_editado, nombre.replace(" ", "_"))
                guardar_acta_generada(procedimiento, pid, nombre, datos_acta, texto_editado, pdf_path)
                auditar("GENERAR_ACTA", f"{procedimiento} - {nombre}")

                with open(pdf_path, "rb") as f:
                    st.download_button(
                        f"⬇️ Descargar PDF - {nombre}",
                        f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )

                st.success("Acta generada. Los datos nuevos/decisiones fueron guardados si la opcion estaba marcada.")

        with col2:
            st.download_button(
                f"⬇️ Descargar TXT - {nombre}",
                texto_editado,
                file_name=f"{nombre.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        st.divider()


# =====================================================
# TOMAR FOTO/PDF COMO PLANTILLA
# =====================================================

if menu == "5. Tomar Foto/PDF como Plantilla":
    st.subheader("5. Tomar Foto/PDF como Plantilla")

    st.warning("""
    Fase practica inicial:
    el sistema permite subir la foto/PDF del acta real y crear una plantilla editable.
    La lectura automatica completa por OCR puede agregarse como capa posterior.
    En esta version, el usuario pega o transcribe el texto base y marca campos con {campo}.
    """)

    archivo = st.file_uploader("Subir foto, imagen escaneada o PDF del formulario/acta", type=["jpg", "jpeg", "png", "pdf"])

    archivo_guardado = ""

    if archivo is not None:
        ext = archivo.name.split(".")[-1].lower()
        nombre_archivo = f"plantilla_{uuid.uuid4().hex[:8]}.{ext}"
        archivo_guardado = os.path.join(UPLOAD_DIR, nombre_archivo)
        with open(archivo_guardado, "wb") as f:
            f.write(archivo.getbuffer())

        st.success("Archivo guardado como referencia de plantilla.")

        if ext in ["jpg", "jpeg", "png"]:
            st.image(archivo_guardado, caption="Referencia visual de la plantilla", use_container_width=True)
        else:
            st.info("PDF cargado. Queda guardado como referencia.")

    st.markdown("### Crear plantilla desde el formulario real")

    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre de la nueva acta", placeholder="Ej: Acta de entrega de menor")
        categoria = st.text_input("Categoria", value="Plantilla tomada de foto/PDF")
    with col2:
        descripcion = st.text_area("Descripcion / uso", height=100)

    st.markdown("""
    Pegue o transcriba el texto base del acta.  
    Use llaves para marcar campos variables: `{fecha}`, `{menor_nombre}`, `{testigo}`, `{observaciones}`.
    """)

    texto_base = st.text_area(
        "Texto base de la plantilla",
        height=320,
        placeholder="ACTA DE ...\nEn la ciudad de ..., siendo las {hora}, comparece {persona} ..."
    )

    campos_detectados = detectar_campos_en_texto(texto_base) if texto_base else []

    if campos_detectados:
        st.markdown("### Campos detectados")
        st.write(", ".join(campos_detectados))

        st.info("Por defecto los campos se crean como manuales. Luego podra editarlos desde el codigo o mejorar el catalogo.")

    if st.button("💾 Guardar nueva plantilla", use_container_width=True):
        if not nombre or not texto_base:
            st.error("Debe completar nombre y texto base.")
        else:
            campos = []
            for campo in campos_detectados:
                campos.append({
                    "clave": campo,
                    "label": campo.replace("_", " ").title(),
                    "tipo": "manual_largo" if campo in ["relato", "observaciones", "descripcion"] else "manual",
                    "categoria": "plantilla_personalizada"
                })

            try:
                c.execute("""
                INSERT INTO plantillas_actas (nombre, categoria, descripcion, campos_json, plantilla_texto, origen, archivo_origen, activa, creado_en)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nombre,
                    categoria,
                    descripcion,
                    json.dumps(campos, ensure_ascii=False, indent=2),
                    texto_base,
                    "FOTO_PDF",
                    archivo_guardado,
                    1,
                    ahora()
                ))
                conn.commit()
                auditar("CREAR_PLANTILLA_FOTO_PDF", nombre)
                st.success("Plantilla guardada. Ya aparece en el Constructor de Actas.")
            except sqlite3.IntegrityError:
                st.error("Ya existe una plantilla con ese nombre.")


# =====================================================
# ACTAS GENERADAS
# =====================================================

if menu == "6. Actas Generadas":
    st.subheader("6. Actas Generadas")

    procedimiento = seleccionar_procedimiento()

    c.execute("""
    SELECT id, nombre_acta, pdf_path, generado_por, generado_en, texto_final
    FROM actas_generadas
    WHERE procedimiento=?
    ORDER BY id DESC
    """, (procedimiento,))
    rows = c.fetchall()

    if not rows:
        st.info("No hay actas generadas para este procedimiento.")
        st.stop()

    for id_, nombre, pdf_path, generado_por, generado_en, texto_final in rows:
        with st.expander(f"{nombre} - {generado_en} - {generado_por}"):
            st.text_area("Texto generado", texto_final, height=250, key=f"acta_txt_{id_}")

            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Descargar PDF",
                        f.read(),
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        key=f"down_pdf_{id_}"
                    )


# =====================================================
# AUDITORIA
# =====================================================

if menu == "7. Auditoria":
    st.subheader("7. Auditoria")

    if st.session_state.rol != "SUPERVISOR":
        st.warning("Solo supervisor puede ver auditoria.")
        st.stop()

    c.execute("""
    SELECT usuario, accion, detalle, fecha
    FROM auditoria
    ORDER BY id DESC
    """)
    rows = c.fetchall()

    st.dataframe(
        [{"Usuario": r[0], "Accion": r[1], "Detalle": r[2], "Fecha": r[3]} for r in rows],
        use_container_width=True
    )

# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
