import streamlit as st
import sqlite3
import json
import datetime
import hashlib

# =====================================================
# S.I.V.A.P. - MOTOR GENÉRICO DE GUARDADO / PERSISTENCIA
#
# Este archivo reemplaza al viejo siv_guardado.py.
#
# Objetivo:
# - Un solo motor de guardado para todo el programa.
# - Guardar por ACTUACIÓN + BLOQUE.
# - Evitar que se borre información al cambiar pestaña, bloque o recargar.
# - No guardar widgets peligrosos de Streamlit:
#   st.button, st.download_button, st.file_uploader, canvas/firma, objetos binarios.
#
# Compatible con los bloques que ya usan:
# - iniciar_guardado_seguro(BLOQUE_ID)
# - panel_guardado_seguro(BLOQUE_ID)
# - autoguardar_bloque(BLOQUE_ID)
#
# Regla S.I.V.A.P.:
# Si el dato se cargó, no se pierde.
# =====================================================

DB_BORRADORES = "sivap_borradores_global.db"


# =====================================================
# BASE DE DATOS
# =====================================================

def _conn():
    conn = sqlite3.connect(DB_BORRADORES, check_same_thread=False)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS borradores_sivap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento_id TEXT,
        bloque TEXT,
        datos_json TEXT,
        actualizado_en TEXT,
        UNIQUE(procedimiento_id, bloque)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS eventos_guardado_sivap (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        procedimiento_id TEXT,
        bloque TEXT,
        accion TEXT,
        detalle TEXT,
        fecha_hora TEXT
    )
    """)

    conn.commit()
    return conn


def _ahora():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _auditar(procedimiento_id, bloque, accion, detalle=""):
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute("""
        INSERT INTO eventos_guardado_sivap
        (procedimiento_id, bloque, accion, detalle, fecha_hora)
        VALUES (?, ?, ?, ?, ?)
        """, (procedimiento_id, bloque, accion, detalle, _ahora()))
        conn.commit()
        conn.close()
    except Exception:
        pass


# =====================================================
# IDENTIDAD DE ACTUACIÓN
# =====================================================

def _procedimiento_id_actual():
    """
    Prioridad:
    1. st.session_state['actuacion']['procedimiento_id']
    2. numero_acta + fecha + reparticion
    3. SIN_ACTUACION_ACTIVA
    """
    actuacion = st.session_state.get("actuacion", {})

    if isinstance(actuacion, dict):
        pid = actuacion.get("procedimiento_id")
        if pid:
            return str(pid)

        numero = actuacion.get("numero_acta", "")
        fecha = actuacion.get("fecha", "")
        rep = actuacion.get("reparticion_dependencia", "")
        if numero or fecha or rep:
            base = f"{rep}-{fecha}-{numero}"
            return _normalizar_id(base)

    return "SIN_ACTUACION_ACTIVA"


def _normalizar_id(texto):
    texto = str(texto or "").upper()
    salida = []
    for c in texto:
        if c.isalnum():
            salida.append(c)
        elif c in [" ", "-", "_", "/", "."]:
            salida.append("-")
    res = "".join(salida)
    while "--" in res:
        res = res.replace("--", "-")
    res = res.strip("-")
    return res or "SIN_ACTUACION_ACTIVA"


# =====================================================
# FILTRO DE CLAVES
# =====================================================

def _prefijos_por_bloque(bloque):
    b = str(bloque or "").upper()

    if "BLOQUE_1" in b or "BLOQUE 1" in b:
        return ["b1_", "bloque1_", "relato_usuario", "data_operativa", "datos_operativos"]

    if "BLOQUE_2" in b or "BLOQUE 2" in b or "ARRESTADO" in b:
        return ["b2_", "arrestado_", "arrestados_"]

    if "BLOQUE_3" in b or "BLOQUE 3" in b or "ENTREVISTA" in b or "VICTIMA" in b or "VÍCTIMA" in b:
        return ["b3_"]

    if "BLOQUE_4" in b or "BLOQUE 4" in b or "TESTIGO" in b:
        return ["b4_"]

    if "BLOQUE_5" in b or "BLOQUE 5" in b or "CONSULTA" in b:
        return ["b5_"]

    if "BLOQUE_6" in b or "BLOQUE 6" in b or "CROQUIS" in b or "INSPECCION" in b or "INSPECCIÓN" in b:
        return ["b6_"]

    if "BLOQUE_7" in b or "BLOQUE 7" in b or "SECUESTRO" in b:
        return ["b7_"]

    if "BLOQUE_8" in b or "BLOQUE 8" in b or "CONSTRUCTOR" in b or "CONSOLIDADOR" in b:
        return ["b8_"]

    # Fallback: no bloquear todo el sistema por un nombre raro,
    # pero guardar solo claves sivap_ o del bloque si existen.
    return ["sivap_"]


def _clave_excluida(k):
    k = str(k)
    kl = k.lower()

    prefijos_excluidos = [
        "_",
        "guardar_borrador_",
        "borrar_borrador_",
        "borrar_todos_borradores_",
        "recuperar_borrador_",
        "download_",
        "descargar_",
        "file_uploader_",
        "button_",
    ]

    contiene_excluidos = [
        "canvas",
        "firma_canvas",
        "st_canvas",
        "uploaded_file",
        "file_uploader",
        "download_button",
        "archivo",
        "uploaded",
        "image_data",
        "bytes",
    ]

    if any(k.startswith(p) for p in prefijos_excluidos):
        return True

    if any(p in kl for p in contiene_excluidos):
        return True

    return False


def _clave_guardable_para_bloque(k, bloque):
    if _clave_excluida(k):
        return False

    # No guardar identidad/actuación dentro de cada bloque: app.py los maneja.
    # Pero sí se usan para construir la clave de guardado.
    if k in ["identidad_policial", "actuacion"]:
        return False

    prefijos = _prefijos_por_bloque(bloque)

    for p in prefijos:
        if str(k).startswith(p):
            return True

    # Algunos bloques viejos usan listas/datos sin prefijo claro.
    # Se permite si el nombre contiene el número de bloque.
    b = str(bloque or "").upper()
    if "BLOQUE_1" in b and k in ["relato_usuario", "data_operativa", "datos_operativos"]:
        return True

    return False


# =====================================================
# SERIALIZACIÓN SEGURA
# =====================================================

def _serializar(v):
    if isinstance(v, datetime.datetime):
        return {"__tipo__": "datetime", "valor": v.isoformat()}
    if isinstance(v, datetime.date):
        return {"__tipo__": "date", "valor": v.isoformat()}
    if isinstance(v, datetime.time):
        return {"__tipo__": "time", "valor": v.isoformat()}

    if isinstance(v, (str, int, float, bool)) or v is None:
        return v

    if isinstance(v, list):
        salida = []
        for x in v:
            sx = _serializar(x)
            if sx is not None:
                salida.append(sx)
        return salida

    if isinstance(v, dict):
        salida = {}
        for k, x in v.items():
            sx = _serializar(x)
            if sx is not None:
                salida[str(k)] = sx
        return salida

    # Evita guardar objetos Streamlit, UploadedFile, Canvas, imágenes, etc.
    return None


def _deserializar(v):
    if isinstance(v, dict) and "__tipo__" in v:
        try:
            if v["__tipo__"] == "date":
                return datetime.date.fromisoformat(v["valor"])
            if v["__tipo__"] == "time":
                return datetime.time.fromisoformat(v["valor"])
            if v["__tipo__"] == "datetime":
                return datetime.datetime.fromisoformat(v["valor"])
        except Exception:
            return v.get("valor", "")

    if isinstance(v, list):
        return [_deserializar(x) for x in v]

    if isinstance(v, dict):
        return {k: _deserializar(x) for k, x in v.items()}

    return v


# =====================================================
# FUNCIONES PRINCIPALES
# =====================================================

def guardar_borrador_bloque(bloque):
    procedimiento_id = _procedimiento_id_actual()
    datos = {}

    for k, v in st.session_state.items():
        if not _clave_guardable_para_bloque(k, bloque):
            continue

        sv = _serializar(v)
        if sv is not None:
            datos[str(k)] = sv

    conn = _conn()
    c = conn.cursor()

    c.execute("""
    INSERT INTO borradores_sivap (procedimiento_id, bloque, datos_json, actualizado_en)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(procedimiento_id, bloque)
    DO UPDATE SET datos_json=excluded.datos_json, actualizado_en=excluded.actualizado_en
    """, (
        procedimiento_id,
        str(bloque),
        json.dumps(datos, ensure_ascii=False, indent=2),
        _ahora()
    ))

    conn.commit()
    conn.close()

    st.session_state[f"_sivap_ultimo_guardado_{bloque}"] = _ahora()
    _auditar(procedimiento_id, bloque, "GUARDAR", f"{len(datos)} campos guardados")


def cargar_borrador_bloque(bloque, sobrescribir=False):
    procedimiento_id = _procedimiento_id_actual()

    conn = _conn()
    c = conn.cursor()
    c.execute("""
    SELECT datos_json, actualizado_en
    FROM borradores_sivap
    WHERE procedimiento_id=? AND bloque=?
    """, (procedimiento_id, str(bloque)))
    row = c.fetchone()
    conn.close()

    if not row:
        return False, ""

    try:
        datos = json.loads(row[0])

        for k, v in datos.items():
            if not _clave_guardable_para_bloque(k, bloque):
                continue

            # Carga inicial: no pisa lo que ya está.
            # Recuperación manual: sobrescribir=True permite restaurar.
            if sobrescribir or k not in st.session_state:
                st.session_state[k] = _deserializar(v)

        st.session_state[f"_sivap_borrador_fecha_{bloque}"] = row[1]
        _auditar(procedimiento_id, bloque, "CARGAR", f"sobrescribir={sobrescribir}")
        return True, row[1]

    except Exception as e:
        _auditar(procedimiento_id, bloque, "ERROR_CARGAR", str(e))
        return False, row[1]


def borrar_borrador_bloque(bloque):
    procedimiento_id = _procedimiento_id_actual()

    conn = _conn()
    c = conn.cursor()
    c.execute("""
    DELETE FROM borradores_sivap
    WHERE procedimiento_id=? AND bloque=?
    """, (procedimiento_id, str(bloque)))
    conn.commit()
    conn.close()

    _auditar(procedimiento_id, bloque, "BORRAR", "Borrador del bloque borrado")


def borrar_borradores_actuacion_actual():
    procedimiento_id = _procedimiento_id_actual()

    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM borradores_sivap WHERE procedimiento_id=?", (procedimiento_id,))
    conn.commit()
    conn.close()

    _auditar(procedimiento_id, "TODOS", "BORRAR_ACTUACION", "Se borraron todos los borradores de la actuación")


def listar_borradores_actuacion():
    procedimiento_id = _procedimiento_id_actual()

    conn = _conn()
    c = conn.cursor()
    c.execute("""
    SELECT bloque, actualizado_en
    FROM borradores_sivap
    WHERE procedimiento_id=?
    ORDER BY actualizado_en DESC
    """, (procedimiento_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# =====================================================
# API COMPATIBLE CON BLOQUES EXISTENTES
# =====================================================

def iniciar_guardado_seguro(bloque):
    marca = f"_sivap_borrador_cargado_{bloque}"

    if marca not in st.session_state:
        ok, fecha = cargar_borrador_bloque(bloque, sobrescribir=False)
        st.session_state[marca] = True
        st.session_state[f"_sivap_borrador_fecha_{bloque}"] = fecha if ok else ""


def panel_guardado_seguro(bloque):
    procedimiento_id = _procedimiento_id_actual()
    fecha = st.session_state.get(f"_sivap_borrador_fecha_{bloque}", "")
    ultimo = st.session_state.get(f"_sivap_ultimo_guardado_{bloque}", "")

    st.sidebar.divider()
    st.sidebar.markdown("### 💾 Guardado S.I.V.A.P.")
    st.sidebar.caption(f"Actuación: {procedimiento_id}")
    st.sidebar.caption(f"Bloque: {bloque}")

    if ultimo:
        st.sidebar.success(f"Autoguardado: {ultimo}")
    elif fecha:
        st.sidebar.success(f"Borrador cargado: {fecha}")
    else:
        st.sidebar.info("Sin borrador previo")

    c1, c2 = st.sidebar.columns(2)

    with c1:
        if st.button("💾 Guardar", key=f"guardar_borrador_{bloque}", use_container_width=True):
            guardar_borrador_bloque(bloque)
            st.success("Borrador guardado.")

    with c2:
        if st.button("↩️ Recuperar", key=f"recuperar_borrador_{bloque}", use_container_width=True):
            ok, fecha_rec = cargar_borrador_bloque(bloque, sobrescribir=True)
            if ok:
                st.success("Borrador recuperado.")
                st.rerun()
            else:
                st.warning("No hay borrador para recuperar.")

    with st.sidebar.expander("Mantenimiento del bloque"):
        st.caption("Usar con cuidado. No borra otros bloques.")
        if st.button("🧹 Borrar este borrador", key=f"borrar_borrador_{bloque}", use_container_width=True):
            borrar_borrador_bloque(bloque)
            st.success("Borrador del bloque borrado.")
            st.rerun()

    with st.sidebar.expander("Borradores de esta actuación"):
        rows = listar_borradores_actuacion()
        if rows:
            for b, f in rows:
                st.caption(f"{b} — {f}")
        else:
            st.caption("No hay borradores para esta actuación.")

        st.warning("Esto borra todos los borradores de la actuación activa.")
        if st.button("🧨 Borrar actuación completa", key=f"borrar_todos_borradores_{bloque}", use_container_width=True):
            borrar_borradores_actuacion_actual()
            st.success("Borradores de la actuación borrados.")
            st.rerun()


def autoguardar_bloque(bloque):
    """
    Autoguardado silencioso.
    Si algo falla, no debe romper el bloque.
    """
    try:
        guardar_borrador_bloque(bloque)
    except Exception:
        pass


# Alias por si en el futuro se quiere usar nombres más claros.
iniciar_bloque = iniciar_guardado_seguro
panel_guardado = panel_guardado_seguro
autoguardar = autoguardar_bloque
