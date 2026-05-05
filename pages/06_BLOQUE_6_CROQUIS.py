import streamlit as st
import json
from fpdf import FPDF

# =====================================================
# AUTOGUARDADO EN MEMORIA ENTRE BLOQUES
# Evita que Streamlit borre datos al navegar entre paginas.
# =====================================================
for _k in list(st.session_state.keys()):
    st.session_state[_k] = st.session_state[_k]


# =====================================================
# BLOQUE 6 - CROQUIS / RECEPCIÓN E IMPRESIÓN
# =====================================================

# --- FUNCIÓN PARA GENERAR EL PDF ---
def crear_pdf_final(imagen_croquis):
    """Genera el PDF con el encabezado solicitado y el croquis."""
    pdf = FPDF()
    pdf.add_page()

    # Título institucional solicitado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "CROQUIS DEL LUGAR DEL HECHO", ln=True, align='C')

    # Inserción de la imagen del croquis
    if imagen_croquis:
        # Se ajusta al ancho de la página (190mm)
        pdf.image(imagen_croquis, x=10, y=30, w=190)

    # Retorno binario directo para evitar errores en Python 3.14 (Render)
    return pdf.output()

# --- INTERFAZ PRINCIPAL ---
st.title("Módulo de Recepción e Impresión - SVI")

# 1. CARGA DEL ARCHIVO JSON (Generado por la IA con la inteligencia del hecho)
archivo_json = st.file_uploader("Cargar JSON del hecho", type=['json'])

if archivo_json:
    try:
        # Cargar datos del JSON para el flujo del programa
        datos_hecho = json.load(archivo_json)
        st.success("✅ Datos del hecho cargados correctamente.")

        # Muestra una breve referencia del archivo para el actante
        st.info(f"Referencia: {archivo_json.name}")

        # 2. CARGA DEL CROQUIS (La imagen generada por la IA)
        archivo_imagen = st.file_uploader("Cargar imagen del croquis (AI)", type=['png', 'jpg', 'jpeg'])

        if archivo_imagen:
            # Vista previa del croquis para verificación del actante
            st.image(archivo_imagen, caption="Vista previa para el acta")

            st.markdown("---")
            # Disposición de botones independientes
            col1, col2 = st.columns(2)

            # BOTÓN A: VIAJAR AL ACTANTE (Integración interna del sistema)
            with col1:
                if st.button("🚀 Viajar al Actante"):
                    # Almacena los datos en el estado de sesión para el resto del sumario
                    st.session_state['actante_data'] = datos_hecho
                    st.toast("Información enviada al bloque del Actante")

            # BOTÓN B: DESCARGA PDF (Para impresión física del anexo)
            with col2:
                # Generación de bytes del PDF
                pdf_bytes = crear_pdf_final(archivo_imagen)
                st.download_button(
                    label="📥 Descargar PDF para Impresión",
                    data=pdf_bytes,
                    file_name="CROQUIS_LUGAR_DEL_HECHO.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Error al procesar los archivos: {e}")

else:
    st.info("A la espera del archivo JSON del hecho para iniciar el bloque.")
