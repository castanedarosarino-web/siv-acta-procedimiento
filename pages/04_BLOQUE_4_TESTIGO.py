import streamlit as st
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import json
import tempfile
import os
from datetime import datetime

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="S.I.V. - Bloque 4: DECLARACIÓN DE TESTIGO", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Oficial Interviniente")
    interviniente = st.text_input("Rango y Nombre", value="SUB COMISARIO CASTAÑEDA JUAN")
    dependencia = st.text_input("Dependencia", value="SUBCOMISARIA ZAVALLA - UR II")

def limpiar_texto(texto):
    if texto is None: return ""
    r = {"ñ": "n", "Ñ": "N", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "°": "Nro."}
    for k, v in r.items(): texto = str(texto).replace(k, v)
    return texto.upper()

def generar_pdf_testigo(datos, firma_img):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_margins(left=25, top=20, right=15)
    pdf.add_page()

    # ENCABEZADO
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "UR II ROSARIO - " + dependencia, ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ACTA DE DECLARACION DE TESTIGO", ln=True, align="C")
    pdf.ln(10)

    # CUADRO DE FILIACIÓN DEL TESTIGO
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "I. DATOS DEL TESTIGO:", ln=True)
    pdf.set_font("Arial", "", 11)
    
    f = datos["filiacion"]
    pdf.cell(50, 8, "Nombre y Apellido:", 1); pdf.cell(0, 8, limpiar_texto(f['nombre']), 1, 1)
    pdf.cell(50, 8, "D.N.I. / F. Nac:", 1); pdf.cell(0, 8, f"{f['dni']} | {f['fecha_nac']}", 1, 1)
    pdf.cell(50, 8, "Telefono / Correo:", 1); pdf.cell(0, 8, f"{f['telefono']} | {f['correo']}", 1, 1)
    pdf.multi_cell(0, 8, limpiar_texto(f"Domicilio: {f['domicilio']}"), 1)
    pdf.ln(10)

    # RELATO DEL TESTIGO
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "II. TESTIMONIO DE LOS HECHOS:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, limpiar_texto(datos["contenido"]), 0, 'J')

    # FIRMAS
    pdf.ln(25)
    y_pos = pdf.get_y()
    
    if firma_img is not None:
        img = Image.fromarray(firma_img.astype('uint8'), 'RGBA')
        blanco = Image.new("RGB", img.size, (255, 255, 255))
        blanco.paste(img, mask=img.split()[3])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            blanco.save(tmp.name, format="JPEG")
            pdf.image(tmp.name, x=30, y=y_pos - 15, w=50)
            os.unlink(tmp.name)

    pdf.cell(85, 8, "------------------------------------", 0, 0, "C")
    pdf.cell(85, 8, "------------------------------------", 0, 1, "C")
    pdf.cell(85, 5, "FIRMA TESTIGO", 0, 0, "C")
    pdf.cell(85, 5, "FIRMA INTERVINIENTE", 0, 1, "C")

    return pdf.output(dest="S").encode("latin-1", errors="replace")

def main():
    st.title("🚓 S.I.V. - Bloque 4: TESTIGO")
    
    with st.expander("👤 DATOS FILIATORIOS DEL TESTIGO", expanded=True):
        c1, c2 = st.columns([2, 1])
        nombre = c1.text_input("Apellido y Nombres").upper()
        dni = c2.text_input("DNI")
        
        c3, c4 = st.columns(2)
        telefono = c3.text_input("Teléfono de Contacto")
        correo = c4.text_input("Correo Electrónico")
        
        c5, c6 = st.columns([1, 2])
        fecha_nac = c5.text_input("Fecha de Nacimiento")
        domicilio = c6.text_input("Domicilio Real")

    st.subheader("✍️ Declaración Testimonial")
    relato = st.text_area("El testigo manifiesta que:", height=200)

    st.markdown("---")
    st.subheader("🖊️ FIRMA DEL TESTIGO")
    canvas_testigo = st_canvas(
        fill_color="rgba(255, 255, 255, 1)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        width=500,
        drawing_mode="freedraw",
        key="canvas_testigo",
    )

    datos_json = {
        "filiacion": {
            "nombre": nombre, "dni": dni, "telefono": telefono, 
            "correo": correo, "fecha_nac": fecha_nac, "domicilio": domicilio
        },
        "contenido": relato
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 EXPORTAR JSON PARA ACTANTE",
            data=json.dumps(datos_json, indent=4, ensure_ascii=False),
            file_name=f"testigo_{dni}.json",
            mime="application/json"
        )
    with col2:
        if st.button("💾 GENERAR PDF TESTIGO"):
            if canvas_testigo.image_data is not None and nombre:
                pdf_bytes = generar_pdf_testigo(datos_json, canvas_testigo.image_data)
                st.download_button(
                    label="📄 DESCARGAR ACTA TESTIGO",
                    data=pdf_bytes,
                    file_name=f"Acta_Testigo_{dni}.pdf",
                    mime="application/pdf"
                )
            else:
                st.warning("Se requiere firma y nombre del testigo.")

if __name__ == "__main__":
    main()