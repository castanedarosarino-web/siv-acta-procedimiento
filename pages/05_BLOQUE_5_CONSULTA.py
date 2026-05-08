import streamlit as st

from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

BLOQUE_ID = "BLOQUE_5_CONSULTA"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

# =====================================================
# BLOQUE 5 - CONSULTA
# BLOQUE INFORMATIVO / NUTRE A LOS DEMÁS BLOQUES
# NO GENERA PDF
# =====================================================

delitos_criticos = [
    "muerte", "cadáver", "cadaver", "cráneo", "craneo",
    "restos", "homicidio", "bala", "disparo",
    "fallecido", "abuso", "sexual"
]


def validar_competencia(texto, autoridad):
    texto = texto.lower()
    es_critico = any(w in texto for w in delitos_criticos)

    if es_critico and autoridad == "Flagrancia (0800-MPA)":
        return False

    return True


st.title("🛡️ BLOQUE 5 - CONSULTA")
st.subheader("Auditor de Protocolo y Competencia Judicial")

resena = st.text_area(
    "📝 Reseña del Hecho:",
    height=150,
    placeholder="Ej: Personal comisionado arriba al lugar, constatando...",
    key="b5_resena"
)

st.divider()

st.write("### 📞 Registro de Comunicación")

autoridad_interviniente = st.selectbox(
    "¿Quién dio las directivas telefónicas?",
    [
        "Mesa de Enlace (Solo registro)",
        "Flagrancia (0800-MPA)",
        "Fiscalía de Homicidios",
        "Fiscalía de Género / Integridad Sexual",
        "Justicia de Menores"
    ],
    key="b5_autoridad_interviniente"
)

nombre_secretario = st.text_input(
    "Nombre del Secretario/Fiscal que atendió:",
    key="b5_nombre_secretario"
)

directivas = st.text_area(
    "Directivas impartidas:",
    height=120,
    placeholder="Ej: dispone consulta con fiscalía correspondiente, intervención de gabinete...",
    key="b5_directivas"
)

competencia_correcta = True
hecho_critico = False

if resena:
    texto = resena.lower()
    hecho_critico = any(w in texto for w in delitos_criticos)
    competencia_correcta = validar_competencia(resena, autoridad_interviniente)

    if not competencia_correcta:
        st.error(f"""
🚨 ERROR DE COMPETENCIA DETECTADO

Se detectan términos compatibles con hecho crítico, pero se registran directivas de:

{autoridad_interviniente}

ACCIÓN SUGERIDA:
- Verificar intervención de la fiscalía competente.
- Dejar constancia expresa de lo informado.
- Registrar nombre de quien impartió directivas.
""")

    if hecho_critico:
        st.error("🆘 PROCEDIMIENTO DE EXCEPCIÓN: requiere preservación estricta, comunicación inmediata y posible intervención de Gabinete Criminalístico.")

    elif "robo" in texto or "hurto" in texto:
        st.warning("⚠️ PROCEDIMIENTO DE FLAGRANCIA: verificar testigos, cámaras, damnificado y elementos sustraídos.")

st.divider()

if st.button("📄 FINALIZAR Y GENERAR BORRADOR"):
    if not resena:
        st.error("⚠️ Falta cargar la reseña del hecho.")

    elif not nombre_secretario:
        st.error("⚠️ Falta cargar quién atendió la consulta.")

    elif not directivas:
        st.error("⚠️ Falta cargar las directivas impartidas.")

    elif not competencia_correcta:
        st.error("🚨 BLOQUEO PREVENTIVO: posible error de competencia. Verifique antes de finalizar.")

    else:
        st.success("✅ Consulta validada correctamente.")

        datos_consulta = {
            "bloque": 5,
            "resena": resena,
            "autoridad_interviniente": autoridad_interviniente,
            "nombre_secretario_fiscal": nombre_secretario,
            "directivas": directivas,
            "hecho_critico": "SÍ" if hecho_critico else "NO",
            "competencia_validada": "SÍ"
        }

        st.json(datos_consulta)


# Guardado automático del bloque al finalizar la corrida
try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
