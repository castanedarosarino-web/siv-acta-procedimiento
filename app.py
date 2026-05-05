import streamlit as st

st.set_page_config(page_title="S.I.V. - Acta de Procedimiento", layout="wide", page_icon="🚔")

st.title("🚔 S.I.V. - ACTA DE PROCEDIMIENTO")
st.subheader("Sistema modular de actas policiales - Policía de Santa Fe")

st.info("""
Este programa está organizado por bloques independientes. Cada bloque conserva su propia vida:
interfaz, campos, botones, PDF, JSON y lógica interna. El Bloque 8 solo importa JSON y consolida.
""")

st.markdown("""
### Orden de trabajo recomendado

1. Completar los Bloques 1 a 7 según corresponda.
2. Descargar el JSON propio de cada bloque.
3. Ingresar al **Bloque 8 - Consolidador Final**.
4. Importar los JSON generados.
5. Revisar la vista previa editable.
6. Descargar el acta final y el remito de entrega.

### Regla de oro

**Los Bloques 1 a 7 no se modifican desde el Bloque 8.**
""")
