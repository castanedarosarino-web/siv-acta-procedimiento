import streamlit as st
import json
from datetime import datetime

st.set_page_config(page_title="SVI - Acta de Procedimiento", layout="wide", page_icon="🚔")

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

BLOQUE_ID = "BLOQUE_1_CORAZON"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTextInput { margin-top: -15px; }
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# =====================================================
# DATOS BASE - BLOQUE 1 PROTEGIDO
# =====================================================
if "data_operativa" not in st.session_state:
    st.session_state.data_operativa = {
        "nro_acta": "",
        "incidencia": "",
        "dependencia": "CRE PÉREZ",
        "dependencia_otra": "",
        "movil": "",
        "refuerzo": "",
        "l_hecho": "",
        "l_apre": "",
        "relato": "",
        "personal": "Sub Comisario CASTAÑEDA Juan",
        "colaboraciones": []
    }

if "relato_usuario" not in st.session_state:
    st.session_state.relato_usuario = st.session_state.data_operativa.get("relato", "")

if "importacion_ok" not in st.session_state:
    st.session_state.importacion_ok = False


# =====================================================
# FUNCIONES
# =====================================================
def sincronizar_relato():
    st.session_state.data_operativa["relato"] = st.session_state.get("relato_usuario", "")


def preparar_exportacion_manual():
    data_exportar = dict(st.session_state.data_operativa)

    # FORZADO FINAL: toma el relato directo del widget visible
    data_exportar["relato"] = st.session_state.get("relato_usuario", "")

    return json.dumps(
        data_exportar,
        indent=4,
        ensure_ascii=False
    )


def aplicar_importacion_controlada(
    datos,
    importar_bloque1=False,
    sumar_relato=True,
    importar_refuerzo=True
):
    campos_bloque1_protegido = [
        "nro_acta",
        "incidencia",
        "dependencia",
        "dependencia_otra",
        "movil",
        "personal",
        "l_hecho",
        "l_apre"
    ]

    if importar_bloque1:
        for campo in campos_bloque1_protegido:
            if datos.get(campo):
                st.session_state.data_operativa[campo] = datos[campo]

    if importar_refuerzo:
        if datos.get("refuerzo"):
            if st.session_state.data_operativa.get("refuerzo"):
                st.session_state.data_operativa["refuerzo"] += f" / {datos['refuerzo']}"
            else:
                st.session_state.data_operativa["refuerzo"] = datos["refuerzo"]

    relato_nuevo = datos.get("relato", "")

    if sumar_relato and relato_nuevo:
        origen = datos.get("personal", "Colaborador")
        movil_origen = datos.get("movil", "S/D")

        marca = f"\n\n--- APORTE DE COLABORACIÓN: {origen} | Móvil: {movil_origen} ---\n"

        if st.session_state.data_operativa.get("relato"):
            st.session_state.data_operativa["relato"] += marca + relato_nuevo
        else:
            st.session_state.data_operativa["relato"] = marca.strip() + "\n" + relato_nuevo

        st.session_state.relato_usuario = st.session_state.data_operativa["relato"]

    st.session_state.data_operativa["colaboraciones"].append({
        "fecha_importacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "personal": datos.get("personal", "N/C"),
        "movil": datos.get("movil", "S/D"),
        "incluyo_relato": bool(relato_nuevo),
        "bloque1_importado": importar_bloque1
    })


# =====================================================
# SIDEBAR
# =====================================================
with st.sidebar:
    st.title("📂 Central de Recepción")
    st.markdown("### **Creado por Sub Comisario CASTAÑEDA Juan**")

    if st.session_state.importacion_ok:
        st.success("✅ Colaboración incorporada con control del operador.")
        st.session_state.importacion_ok = False

    st.divider()

    modo = st.radio(
        "Modo de trabajo",
        ["Colaborador", "Central / Actero"]
    )

    st.divider()

    if modo == "Central / Actero":
        st.subheader("📥 Importar Colaboración")

        archivo_colab = st.file_uploader(
            "Subir colaboración JSON",
            type=["json"],
            key="importar_colaboracion"
        )

        if archivo_colab is not None:
            try:
                datos_colab = json.loads(archivo_colab.getvalue().decode("utf-8"))

                st.warning("⚠️ Revise antes de importar. El Bloque 1 está protegido por defecto.")

                with st.expander("👁️ Ver contenido recibido", expanded=True):
                    st.write("**Personal:**", datos_colab.get("personal", "N/C"))
                    st.write("**Móvil:**", datos_colab.get("movil", "S/D"))
                    st.write("**Lugar del hecho:**", datos_colab.get("l_hecho", ""))
                    st.write("**Lugar de aprehensión:**", datos_colab.get("l_apre", ""))
                    st.write("**Relato recibido:**")
                    st.text_area(
                        "Vista previa del relato",
                        value=datos_colab.get("relato", ""),
                        height=160,
                        disabled=True
                    )

                importar_relato = st.checkbox("✅ Sumar relato al acta", value=True)
                importar_refuerzo = st.checkbox("✅ Incorporar refuerzo si corresponde", value=True)
                importar_bloque1 = st.checkbox("⚠️ Permitir modificar datos del Bloque 1", value=False)

                if st.button("📥 CONFIRMAR IMPORTACIÓN", use_container_width=True):
                    aplicar_importacion_controlada(
                        datos_colab,
                        importar_bloque1=importar_bloque1,
                        sumar_relato=importar_relato,
                        importar_refuerzo=importar_refuerzo
                    )

                    st.session_state.importacion_ok = True
                    st.rerun()

            except Exception as e:
                st.error(f"Error al importar colaboración: {e}")

    else:
        st.subheader("👮 Modo Colaborador")
        st.info("Complete el Bloque 1 y exporte su colaboración al final del relato.")


# =====================================================
# CUERPO PRINCIPAL - BLOQUE 1
# =====================================================
st.title("🚔 ACTA DE PROCEDIMIENTO UR II _(S.I.V.)")
st.subheader("Creado por Sub Comisario CASTAÑEDA Juan")

# Las pestañas internas fueron retiradas porque los bloques ya funcionan
# como páginas independientes en el menú lateral.
with st.container():
    st.subheader("🛡️ Identificación Administrativa y Operativa")

    c1, c2, c3, c4 = st.columns(4)

    n_acta = c1.text_input(
        "Nro. de Acta",
        value=st.session_state.data_operativa["nro_acta"]
    )

    n_incidencia = c2.text_input(
        "Nro. Incidencia (911)",
        value=st.session_state.data_operativa["incidencia"]
    )

    dep_opciones = ["CRE PÉREZ", "CRE FUNES", "CRE ROSARIO", "B.O.U.", "G.T.M.", "OTRO"]
    dep_actual = st.session_state.data_operativa.get("dependencia", "CRE PÉREZ")
    idx_dep = dep_opciones.index(dep_actual) if dep_actual in dep_opciones else 0

    dep = c3.selectbox(
        "Dependencia",
        dep_opciones,
        index=idx_dep
    )

    if dep == "OTRO":
        dep_otra = c4.text_input(
            "Especifique Dependencia",
            value=st.session_state.data_operativa.get("dependencia_otra", "")
        )
        n_movil = st.text_input(
            "Nro. de Móvil",
            value=st.session_state.data_operativa.get("movil", "")
        )
    else:
        n_movil = c4.text_input(
            "Nro. de Móvil",
            value=st.session_state.data_operativa.get("movil", "")
        )
        dep_otra = ""

    personal_actuante = st.text_input(
        "Personal Actuante",
        value=st.session_state.data_operativa.get("personal", "Sub Comisario CASTAÑEDA Juan")
    )

    refuerzos = st.text_input(
        "Refuerzo (Móviles/Personal de apoyo)",
        value=st.session_state.data_operativa.get("refuerzo", "")
    )

    c5, c6 = st.columns(2)

    fecha_proc = c5.date_input(
        "Fecha",
        value=datetime.now()
    )

    hora_proc = c6.time_input(
        "Hora",
        value=datetime.now()
    )

    lugar_hecho = st.text_input(
        "📍 Lugar del Hecho",
        value=st.session_state.data_operativa.get("l_hecho", "")
    )

    lugar_apre = st.text_input(
        "👤 Lugar de Aprehensión",
        value=st.session_state.data_operativa.get("l_apre", "")
    )

    st.divider()

    st.subheader("📝 Relato Circunstanciado")

    relato_usuario = st.text_area(
        "Narración de los hechos:",
        key="relato_usuario",
        height=200,
        on_change=sincronizar_relato
    )

    st.session_state.data_operativa.update({
        "nro_acta": n_acta,
        "incidencia": n_incidencia,
        "dependencia": dep,
        "dependencia_otra": dep_otra,
        "movil": n_movil,
        "relato": st.session_state.get("relato_usuario", ""),
        "personal": personal_actuante,
        "refuerzo": refuerzos,
        "l_hecho": lugar_hecho,
        "l_apre": lugar_apre
    })

    if st.button("🚀 COPIAR Y LISTO PARA PEGAR EN IA"):
        st.components.v1.html(
            f"<script>navigator.clipboard.writeText({json.dumps(st.session_state.get('relato_usuario', ''), ensure_ascii=False)});</script>",
            height=0
        )
        st.success("✅ Copiado al portapapeles.")

    st.divider()

    nombre_base = st.session_state.data_operativa.get("nro_acta", "SVI") or "SVI"
    movil_base = st.session_state.data_operativa.get("movil", "MOVIL") or "MOVIL"

    if modo == "Colaborador":
        st.download_button(
            label="💾 EXPORTAR COLABORACIÓN",
            data=preparar_exportacion_manual(),
            file_name=f"colaboracion_{nombre_base}_{movil_base}.json",
            mime="application/json",
            use_container_width=True
        )

    else:
        st.download_button(
            label="💾 GUARDAR ACTA FINAL",
            data=preparar_exportacion_manual(),
            file_name=f"acta_final_{nombre_base}.json",
            mime="application/json",
            use_container_width=True
        )

# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
