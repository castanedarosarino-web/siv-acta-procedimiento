import streamlit as st
import sqlite3
import json
import datetime

DB_BORRADORES = "siv_borradores.db"

# =====================================================
# S.I.V. - GUARDADO SEGURO
#
# Correccion:
# No guarda claves internas de widgets problematicos:
# - st.button
# - st.download_button
# - st.file_uploader
# - canvas/firma
#
# Esto evita el error:
# values for st.button ... cannot be set using st.session_state
# =====================================================

def _ahora():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _conn():
    conn = sqlite3.connect(DB_BORRADORES, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS borradores_siv (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bloque TEXT UNIQUE,
        datos_json TEXT,
        actualizado_en TEXT
    )
    """)
    conn.commit()
    return conn


def _clave_excluida(k):
    k = str(k)

    prefijos_excluidos = [
        "_",
        "guardar_borrador_",
        "borrar_borrador_",
        "borrar_todos_borradores_",
        "download_",
        "descargar_",
        "file_uploader_",
    ]

    contiene_excluidos = [
        "canvas",
        "firma_canvas",
        "st_canvas",
        "uploaded_file",
        "file_uploader",
        "download_button",
    ]

    if any(k.startswith(p) for p in prefijos_excluidos):
        return True

    if any(p in k.lower() for p in contiene_excluidos):
        return True

    return False


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
        return [_serializar(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _serializar(x) for k, x in v.items()}
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


def guardar_borrador_bloque(bloque):
    conn = _conn()
    c = conn.cursor()

    datos = {}
    for k, v in st.session_state.items():
        if _clave_excluida(k):
            continue

        sv = _serializar(v)
        if sv is not None:
            datos[str(k)] = sv

    c.execute("""
    INSERT INTO borradores_siv (bloque, datos_json, actualizado_en)
    VALUES (?, ?, ?)
    ON CONFLICT(bloque)
    DO UPDATE SET datos_json=excluded.datos_json, actualizado_en=excluded.actualizado_en
    """, (bloque, json.dumps(datos, ensure_ascii=False, indent=2), _ahora()))

    conn.commit()
    conn.close()


def cargar_borrador_bloque(bloque):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT datos_json, actualizado_en FROM borradores_siv WHERE bloque=?", (bloque,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False, ""

    try:
        datos = json.loads(row[0])
        for k, v in datos.items():
            if _clave_excluida(k):
                continue
            if k not in st.session_state:
                st.session_state[k] = _deserializar(v)
        return True, row[1]
    except Exception:
        return False, row[1]


def borrar_borrador_bloque(bloque):
    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM borradores_siv WHERE bloque=?", (bloque,))
    conn.commit()
    conn.close()


def borrar_todos_los_borradores():
    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM borradores_siv")
    conn.commit()
    conn.close()


def iniciar_guardado_seguro(bloque):
    marca = f"_borrador_cargado_{bloque}"
    if marca not in st.session_state:
        ok, fecha = cargar_borrador_bloque(bloque)
        st.session_state[marca] = True
        st.session_state[f"_borrador_fecha_{bloque}"] = fecha if ok else ""


def panel_guardado_seguro(bloque):
    st.sidebar.divider()
    st.sidebar.markdown("### 💾 Borrador")

    fecha = st.session_state.get(f"_borrador_fecha_{bloque}", "")
    if fecha:
        st.sidebar.success(f"Cargado: {fecha}")
    else:
        st.sidebar.info("Sin borrador previo")

    c1, c2 = st.sidebar.columns(2)

    with c1:
        if st.button("💾 Guardar", key=f"guardar_borrador_{bloque}", use_container_width=True):
            guardar_borrador_bloque(bloque)
            st.success("Borrador guardado correctamente.")

    with c2:
        if st.button("🧹 Borrar", key=f"borrar_borrador_{bloque}", use_container_width=True):
            borrar_borrador_bloque(bloque)
            st.success("Borrador borrado.")
            st.rerun()

    with st.sidebar.expander("Mantenimiento"):
        st.caption("Usar solo si quedó un borrador viejo generando errores.")
        if st.button("🧨 Borrar TODOS los borradores", key=f"borrar_todos_borradores_{bloque}", use_container_width=True):
            borrar_todos_los_borradores()
            st.success("Todos los borradores fueron borrados.")
            st.rerun()


def autoguardar_bloque(bloque):
    try:
        guardar_borrador_bloque(bloque)
    except Exception:
        pass
