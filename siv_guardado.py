import streamlit as st
import sqlite3
import json
import datetime

DB_BORRADORES = "siv_borradores.db"

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
        if str(k).startswith("_"):
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

def autoguardar_bloque(bloque):
    try:
        guardar_borrador_bloque(bloque)
    except Exception:
        pass
