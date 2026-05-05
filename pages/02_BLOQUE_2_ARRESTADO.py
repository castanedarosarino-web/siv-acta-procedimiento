import streamlit as st
import json
from datetime import datetime, date

st.set_page_config(page_title="SVI - Bloque 2 Arrestado", layout="wide")

# =====================================================
# AUTOGUARDADO EN MEMORIA ENTRE BLOQUES
# Evita que Streamlit borre datos al navegar entre paginas.
# =====================================================
for _k in list(st.session_state.keys()):
    st.session_state[_k] = st.session_state[_k]


# =========================
# ESTADO
# =========================
if "arrestados" not in st.session_state:
    st.session_state.arrestados = []

if "cantidad" not in st.session_state:
    st.session_state.cantidad = 1

# =========================
# FUNCIONES
# =========================
def calcular_edad(fecha):
    hoy = date.today()
    return hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))

def nuevo():
    return {
        "dni": "",
        "apellido": "",
        "nombre": "",
        "apodo": "",
        "papa": "",
        "mama": "",
        "ciudad": "ROSARIO",
        "provincia": "SANTA FE",
        "pais": "ARGENTINA",
        "nacionalidad": "ARGENTINA",
        "fecha_nac": "",
        "edad": "",
        "estado_civil": "SOLTERO/A",
        "profesion": "",
        "lee": "SI",
        "escribe": "SI",
        "domicilio": "",

        "posee_dni": "NO",

        "consulta_911": "SI",
        "operador": "",
        "resultado_911": "NO POSEE PEDIDO DE CAPTURA",
        "cuij": "",
        "caratula": "",
        "autoridad": "",
        "delito": "",

        "lesiones": "NO",
        "detalle_lesiones": "",
        "atencion": "NO REQUIRIÓ",
        "movil_policial": "",
        "dotacion": "",
        "hospital": "",
        "medico": "",
        "diagnostico": "",
        "resultado": "",
        "certificado": "NO",

        "derechos": "SI",
        "comunicacion": "NO",
        "familiar": "",
        "telefono": "",

        "secuestro": "NO",
        "detalle_sec": "",
        "deposito": "NO",
        "detalle_dep": ""
    }

# =========================
# CABECERA
# =========================
st.title("👤 BLOQUE 2 - ARRESTADO")

cant = st.number_input("Cantidad de arrestados", 1, 10, st.session_state.cantidad)
st.session_state.cantidad = cant

while len(st.session_state.arrestados) < cant:
    st.session_state.arrestados.append(nuevo())

while len(st.session_state.arrestados) > cant:
    st.session_state.arrestados.pop()

# =========================
# FORMULARIOS
# =========================
for i in range(cant):
    a = st.session_state.arrestados[i]

    with st.expander(f"ARRESTADO {i+1}", True):

        st.subheader("📌 Identificación")

        c1, c2, c3 = st.columns(3)
        a["dni"] = c1.text_input("DNI", a["dni"], key=f"dni{i}")
        a["apellido"] = c2.text_input("Apellido", a["apellido"], key=f"ape{i}").upper()
        a["nombre"] = c3.text_input("Nombre", a["nombre"], key=f"nom{i}").upper()

        a["apodo"] = st.text_input("Apodo", a["apodo"], key=f"apo{i}").upper()

        st.subheader("👪 Filiación")
        c4, c5 = st.columns(2)
        a["papa"] = c4.text_input("Padre", a["papa"], key=f"pa{i}")
        a["mama"] = c5.text_input("Madre", a["mama"], key=f"ma{i}")

        st.subheader("🌎 Nacimiento")

        fecha = st.date_input("Fecha nacimiento", date(2000,1,1), key=f"fn{i}")
        a["fecha_nac"] = str(fecha)
        a["edad"] = calcular_edad(fecha)

        st.write(f"Edad: {a['edad']}")

        st.subheader("🏠 Datos personales")

        a["domicilio"] = st.text_input("Domicilio", a["domicilio"], key=f"dom{i}")

        a["estado_civil"] = st.selectbox(
            "Estado civil",
            ["SOLTERO/A","CASADO/A","CONCUBINO/A","DIVORCIADO/A","VIUDO/A"],
            key=f"ec{i}"
        )

        a["profesion"] = st.text_input("Profesión", a["profesion"], key=f"pro{i}")

        # =========================
        # 911
        # =========================
        st.subheader("📡 Consulta 911")

        a["consulta_911"] = st.radio("Consulta 911", ["SI","NO"], key=f"c911{i}")

        if a["consulta_911"] == "SI":
            a["operador"] = st.text_input("Operador", a["operador"], key=f"op{i}")
            a["resultado_911"] = st.selectbox(
                "Resultado",
                ["NO POSEE PEDIDO DE CAPTURA","POSEE PEDIDO DE CAPTURA"],
                key=f"res{i}"
            )
            a["cuij"] = st.text_input("CUIJ", a["cuij"], key=f"cuij{i}")
            a["caratula"] = st.text_input("Carátula", a["caratula"], key=f"car{i}")
            a["autoridad"] = st.text_input("Autoridad", a["autoridad"], key=f"aut{i}")
            a["delito"] = st.text_input("Delito", a["delito"], key=f"del{i}")

        # =========================
        # LESIONES
        # =========================
        st.subheader("🩺 Lesiones")

        a["lesiones"] = st.radio("¿Presenta lesiones?", ["NO","SI"], key=f"les{i}")

        if a["lesiones"] == "SI":
            a["detalle_lesiones"] = st.text_area("Detalle lesiones", key=f"dles{i}")

            a["atencion"] = st.selectbox(
                "Atención médica",
                ["NO REQUIRIÓ","AMBULANCIA","MOVIL POLICIAL"],
                key=f"aten{i}"
            )

            if a["atencion"] == "MOVIL POLICIAL":
                a["movil_policial"] = st.text_input("Móvil", key=f"mov{i}")
                a["dotacion"] = st.text_input("Dotación", key=f"dot{i}")

            a["hospital"] = st.text_input("Hospital", key=f"hos{i}")
            a["medico"] = st.text_input("Médico", key=f"med{i}")
            a["diagnostico"] = st.text_input("Diagnóstico", key=f"diag{i}")

            a["resultado"] = st.selectbox(
                "Resultado",
                ["DADO DE ALTA","INTERNADO","OBSERVACION"],
                key=f"resu{i}"
            )

            a["certificado"] = st.radio("Certificado médico", ["SI","NO"], key=f"cert{i}")

        # =========================
        # DERECHOS
        # =========================
        st.subheader("⚖️ Derechos")

        a["derechos"] = st.radio("Lectura de derechos", ["SI","NO"], key=f"der{i}")

        # =========================
        # COMUNICACIÓN
        # =========================
        st.subheader("📞 Comunicación")

        a["comunicacion"] = st.radio("¿Comunicar a familiar?", ["NO","SI"], key=f"com{i}")

        if a["comunicacion"] == "SI":
            a["familiar"] = st.text_input("Familiar", key=f"fam{i}")
            a["telefono"] = st.text_input("Teléfono", key=f"tel{i}")

        # =========================
        # SECUESTRO
        # =========================
        st.subheader("📦 Secuestro")

        a["secuestro"] = st.radio("Secuestro causa", ["NO","SI"], key=f"sec{i}")

        if a["secuestro"] == "SI":
            a["detalle_sec"] = st.text_area("Detalle secuestro", key=f"dsec{i}")

        a["deposito"] = st.radio("Depósito", ["NO","SI"], key=f"dep{i}")

        if a["deposito"] == "SI":
            a["detalle_dep"] = st.text_area("Detalle depósito", key=f"ddep{i}")

# =========================
# EXPORTAR
# =========================
st.divider()

data = {
    "modulo": "BLOQUE_2_ARRESTADO",
    "cantidad": len(st.session_state.arrestados),
    "arrestados": st.session_state.arrestados
}

json_data = json.dumps(data, indent=4, ensure_ascii=False)

st.download_button(
    "💾 EXPORTAR COLABORACIÓN",
    json_data,
    file_name="bloque2_arrestados.json"
)

with st.expander("Ver JSON"):
    st.code(json_data)