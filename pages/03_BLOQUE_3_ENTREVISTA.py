
import streamlit as st
import json, re, os, tempfile
from datetime import datetime
from fpdf import FPDF
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from siv_guardado import iniciar_guardado_seguro, panel_guardado_seguro, autoguardar_bloque

# =====================================================
# BLOQUE 3 - ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO
# Entrevista en primera persona + detector orientativo por tipo penal/accion penal.
# =====================================================

st.set_page_config(page_title="S.I.V. - Bloque 3 Entrevista", layout="wide", page_icon="🗣️")
BLOQUE_ID = "BLOQUE_3_ENTREVISTA_VICTIMA"
iniciar_guardado_seguro(BLOQUE_ID)
panel_guardado_seguro(BLOQUE_ID)

# --------------------------- utilidades ---------------------------

def limpiar_pdf(t):
    if t is None: return ""
    repl = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","ñ":"n","Ñ":"N","°":"Nro.","–":"-","—":"-","“":"\"","”":"\"","’":"'","⚠️":"","🚨":"","✅":""}
    t = str(t)
    for k,v in repl.items(): t = t.replace(k,v)
    return t

def pdf_bytes(pdf):
    out = pdf.output(dest="S")
    return out.encode("latin-1", errors="replace") if isinstance(out, str) else bytes(out)

def firma_a_path(canvas):
    if canvas is None or canvas.image_data is None: return None
    img = Image.fromarray(canvas.image_data.astype("uint8"), "RGBA")
    bg = Image.new("RGB", img.size, (255,255,255))
    bg.paste(img, mask=img.split()[3])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    bg.save(tmp.name, format="JPEG")
    return tmp.name

def contiene(texto, palabras):
    texto = str(texto or "").lower()
    return any(p in texto for p in palabras)

def resumen_corto(t, n=430):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "..."

# --------------------------- detector SIV ---------------------------

PAL_LESIONES = ["me pego","me pegó","me golpeo","me golpeó","me empujo","me empujó","me corto","me cortó","me lastimo","me lastimó","cachetada","trompada","patada","culata","dolor","hematoma","hinchado","inflamacion","inflamación","sangre","corte","hospital","sies","ambulancia","certificado medico","certificado médico"]
PAL_AMENAZAS = ["me amenazo","me amenazó","amenaza","amenazas","te voy a matar","me va a matar","me dijo que me iba a matar","te voy a prender fuego","me amedrento","me amedrentó","temo por mi integridad","me siento amedrentada"]
PAL_ROBO = ["me robo","me robó","me sustrajo","me saco","me sacó","me arrebato","me arrebató","me quito","me quitó","me llevo","me llevó","me exigio","me exigió","dame todo","entregue","entregué","se dio a la fuga","para darse a la fuga"]
PAL_HURTO = ["me falto","me faltó","no estaba","desaparecio","desapareció","sin ejercer violencia"]
PAL_ARMA = ["arma","arma de fuego","pistola","revolver","revólver","escopeta","cuchillo","arma blanca","culata","me apunto","me apuntó","me exhibio","me exhibió","disparo","disparó"]
PAL_DANIO = ["rompio","rompió","daño","danio","dañó","forzo","forzó","vidrio","ventana","puerta","cerradura","candado"]
PAL_GENERO = ["mi pareja","mi ex pareja","ex pareja","mi marido","conviviente","convivimos","hijo en comun","hijo en común","violencia de genero","violencia de género","violencia familiar","perimetral","medida de restriccion","medida de restricción"]
PAL_SEXUAL = ["abuso","abusó","me toco","me tocó","sin consentimiento","sexual","violacion","violación","manoseo"]
PAL_PRIVADA = ["me insulto","me insultó","insulto","injuria","injurias","calumnia","calumnias","publico que soy","publicó que soy"]
PAL_CAM = ["camara","cámara","filmacion","filmación","testigo","vecino vio","captura","whatsapp","mensaje","audio"]

def analizar_relato(relato):
    t = str(relato or "").lower()
    hay_les = contiene(t, PAL_LESIONES); hay_ame = contiene(t, PAL_AMENAZAS)
    hay_rob = contiene(t, PAL_ROBO); hay_hur = contiene(t, PAL_HURTO)
    hay_arm = contiene(t, PAL_ARMA); hay_dan = contiene(t, PAL_DANIO)
    hay_gen = contiene(t, PAL_GENERO); hay_sex = contiene(t, PAL_SEXUAL)
    hay_priv = contiene(t, PAL_PRIVADA); hay_cam = contiene(t, PAL_CAM)
    tipo, accion, alertas, guia = [], [], [], []
    
    if hay_rob and (hay_arm or hay_les):
        tipo += ["Posible robo calificado / robo con arma o violencia"]
        accion += ["Acción pública por el hecho principal"]
        alertas += ["Posible ROBO con arma/violencia. No tratar como simple sustracción."]
        guia += ["Precisar tipo de arma, color, tamaño y si la víctima la vio claramente.","Precisar si apuntó, exhibió o golpeó con el arma.","Precisar objeto sustraído: marca, modelo, color y propiedad.","Precisar descripción del autor, dirección de fuga, cámaras y testigos."]
        if hay_les:
            accion += ["Posible lesión leve asociada dependiente de instancia privada"]
            alertas += ["Además se detectan posibles LESIONES. Documentar asistencia médica/certificado.","Consultar si desea instar acción penal por las lesiones sufridas, sin perder de vista el robo como acción pública."]
            guia += ["Integrar en primera persona: En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas."]
    elif hay_rob:
        tipo += ["Posible robo / arrebato / sustracción"]
        accion += ["Acción pública orientativa"]
        alertas += ["Posible ROBO/ARREBATO. Verificar violencia, intimidación o fuerza."]
        guia += ["Precisar si hubo fuerza, violencia, amenaza o intimidación.","Precisar objeto sustraído, autor, fuga, testigos y cámaras."]
    elif hay_hur:
        tipo += ["Posible hurto"]
        accion += ["Acción pública orientativa"]
        alertas += ["Posible HURTO. Verificar ausencia de violencia o fuerza."]
        guia += ["Precisar dónde estaba el objeto y cuándo advirtió la faltante."]
    
    if hay_ame:
        tipo += ["Posible amenazas"]
        accion += ["Acción pública orientativa"]
        alertas += ["Posible AMENAZAS. No pedir instancia penal como en lesiones leves."]
        guia += ["Precisar frase textual de la amenaza.","Precisar si se sintió amedrentada/intimidada y si teme por su integridad física.","Precisar medio utilizado, vínculo con autor, antecedentes, capturas, cámaras o testigos."]
    if hay_les and not (hay_rob and (hay_arm or hay_les)):
        tipo += ["Posible lesiones leves"]
        accion += ["Dependiente de instancia privada orientativa"]
        alertas += ["Posible LESIONES LEVES. Consultar si desea instar la acción penal."]
        guia += ["Precisar mecanismo de agresión, zona lesionada, dolor, lesión visible, asistencia médica y certificado.","Integrar en primera persona: En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas."]
    if hay_arm and not hay_rob:
        tipo += ["Posible arma / elemento de peligrosidad"]
        accion += ["Requiere consulta/intervención según contexto"]
        alertas += ["Se menciona arma o elemento de peligrosidad."]
        guia += ["Precisar tipo, color, tamaño, mano en que la llevaba, si apuntó, exhibió o disparó."]
    if hay_dan:
        tipo += ["Posible daño"]
        accion += ["Acción pública orientativa según contexto"]
        alertas += ["Posible DAÑO. Precisar objeto dañado y mecanismo."]
        guia += ["Precisar qué fue dañado, cómo, fotos, titularidad y testigos."]
    if hay_gen:
        tipo += ["Posible violencia de género/familiar"]
        accion += ["Consulta/intervención especial"]
        alertas += ["Posible VIOLENCIA DE GÉNERO/FAMILIAR. Activar resguardos y consulta correspondiente."]
        guia += ["Precisar vínculo, convivencia, hijos, antecedentes, medidas vigentes, riesgo actual y domicilio seguro."]
    if hay_sex:
        tipo += ["Posible delito contra la integridad sexual"]
        accion += ["Alerta sensible / posible instancia privada con excepciones"]
        alertas += ["Posible DELITO SEXUAL. Trato reservado, evitar revictimización y consultar autoridad competente."]
        guia += ["No exponer innecesariamente a la víctima. Preservar prueba y consultar protocolo/autoridad competente."]
    if hay_priv:
        tipo += ["Posible acción privada: calumnias/injurias"]
        accion += ["Acción privada orientativa"]
        alertas += ["Posible ACCIÓN PRIVADA. No tratar automáticamente como flagrancia común."]
        guia += ["Dejar constancia, preservar capturas/mensajes y consultar superior/autoridad competente si hay duda."]
    if hay_cam:
        alertas += ["Se mencionan cámaras, testigos o evidencia digital."]
        guia += ["Precisar ubicación de cámara, dueño/responsable, orientación y contacto del testigo."]
    if not alertas:
        alertas = ["No se detectaron alertas fuertes. Verificar modo, tiempo, lugar, autor, daño y prueba."]
        guia = ["Asegurar que el relato tenga modo, tiempo, lugar, daño, autor, reconocimiento, testigos/cámaras y elementos relevantes."]
    def sd(xs):
        out=[]
        for x in xs:
            if x not in out: out.append(x)
        return out
    return {"tipo_orientativo":sd(tipo),"naturaleza_accion_orientativa":sd(accion),"alertas":sd(alertas),"guia_interna":sd(guia)}

def fragmentos_modelo(analisis):
    j = " ".join(analisis.get("tipo_orientativo", []) + analisis.get("alertas", [])).lower()
    fr=[]
    if "amenaza" in j:
        fr.append("Cuando mi vecino me dijo textualmente “te voy a matar”, sentí mucho temor, me sentí amedrentada y desde ese momento temo por mi integridad física, ya que lo conozco del barrio y vive cerca de mi domicilio.")
    if "lesiones" in j:
        fr.append("En este acto manifiesto que es mi deseo instar la acción penal por las lesiones sufridas.")
    if "robo" in j:
        fr.append("El sujeto utilizó la violencia para sustraerme mis pertenencias, motivo por el cual sentí temor por mi integridad física y no pude resistirme.")
    if "arma" in j:
        fr.append("Con respecto al arma, recuerdo que era del tipo pistola, color negra metálica, y que la llevaba en una de sus manos mientras me intimidaba.")
    return fr

def noticia_criminis(fil, relato, analisis, instancia):
    nom = fil.get("nombre") or "la víctima/damnificado"
    cond = fil.get("condicion") or "víctima/damnificado"
    tipo = ", ".join(analisis.get("tipo_orientativo", [])) or "hecho delictivo a determinar"
    acc = ", ".join(analisis.get("naturaleza_accion_orientativa", [])) or "naturaleza a determinar"
    txt = f"De la entrevista policial recibida a {nom}, en carácter de {cond}, surge una noticia criminis compatible orientativamente con {tipo}. La persona entrevistada aportó relato en primera persona con circunstancias de modo, tiempo y lugar, datos de interés para la investigación y eventual intervención policial."
    if instancia == "SI": txt += " Asimismo, manifestó expresamente su deseo de instar la acción penal por las lesiones sufridas."
    if instancia == "NO": txt += " Asimismo, manifestó que no es su deseo instar la acción penal por el momento."
    if relato: txt += f" Síntesis: {resumen_corto(relato)}"
    txt += f" Naturaleza orientativa detectada: {acc}."
    return txt

def fundamento(relato, analisis):
    j = " ".join(analisis.get("tipo_orientativo", [])).lower()
    ps=[]
    if "robo" in j: ps.append("La víctima aportó relato directo sobre la sustracción, violencia/intimidación y datos del autor o fuga.")
    if "arma" in j: ps.append("Surge uso o exhibición de arma o elemento de peligrosidad, relevante para intervención inmediata.")
    if "lesiones" in j: ps.append("Surgen lesiones o dolor, debiendo documentarse asistencia médica/certificado.")
    if "amenaza" in j: ps.append("Surge amenaza textual o intimidación, con temor manifestado por la víctima.")
    return " ".join(ps) or "El relato aporta datos iniciales de interés para orientar la intervención policial y la consulta a la autoridad competente."

def generar_pdf(fil, relato, noticia, fundamento_txt, analisis, firma_path):
    pdf = FPDF(); pdf.set_margins(18,12,18); pdf.set_auto_page_break(auto=True, margin=16); pdf.add_page()
    pdf.set_font("Arial","B",12); pdf.cell(0,8,"POLICIA DE LA PROVINCIA DE SANTA FE", ln=True, align="C")
    pdf.set_font("Arial","",10); pdf.cell(0,6,"UNIDAD REGIONAL II", ln=True, align="C")
    pdf.set_font("Arial","B",14); pdf.cell(0,10,"ACTA DE ENTREVISTA A VICTIMA / DAMNIFICADO", ln=True, align="C"); pdf.ln(4)
    pdf.set_font("Arial","B",11); pdf.cell(0,8,"1. DATOS DE LA PERSONA ENTREVISTADA", ln=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,limpiar_pdf(f"Condicion: {fil.get('condicion','S/D')}\nApellido y nombres: {fil.get('nombre','S/D')}\nDNI: {fil.get('dni','S/D')} - Edad: {fil.get('edad','S/D')}\nFecha de nacimiento: {fil.get('fecha_nac','S/D')}\nDomicilio: {fil.get('domicilio','S/D')}\nTelefono fijo: {fil.get('telefono_fijo','S/D')} - Celular: {fil.get('celular','S/D')}\nCorreo: {fil.get('correo','S/D')}")); pdf.ln(2)
    pdf.set_font("Arial","B",11); pdf.cell(0,8,"2. RELATO EN PRIMERA PERSONA", ln=True)
    pdf.set_font("Arial","",10); pdf.multi_cell(0,7,limpiar_pdf(relato), align="J"); pdf.ln(2)
    pdf.set_font("Arial","B",11); pdf.cell(0,8,"3. ORIENTACION INTERNA S.I.V.", ln=True)
    pdf.set_font("Arial","",10); pdf.multi_cell(0,7,limpiar_pdf(f"Tipo orientativo: {', '.join(analisis.get('tipo_orientativo', [])) or 'S/D'}\nNaturaleza orientativa: {', '.join(analisis.get('naturaleza_accion_orientativa', [])) or 'S/D'}")); pdf.ln(2)
    pdf.set_font("Arial","B",11); pdf.cell(0,8,"4. NOTICIA CRIMINIS / RESUMEN PARA ACTA", ln=True)
    pdf.set_font("Arial","",10); pdf.multi_cell(0,7,limpiar_pdf(noticia), align="J"); pdf.ln(2)
    pdf.set_font("Arial","B",11); pdf.cell(0,8,"5. FUNDAMENTO ORIENTATIVO DE INTERVENCION/APREHENSION", ln=True)
    pdf.set_font("Arial","",10); pdf.multi_cell(0,7,limpiar_pdf(fundamento_txt), align="J"); pdf.ln(4)
    if firma_path:
        try:
            pdf.set_font("Arial","B",10); pdf.cell(0,7,"Firma digital de la persona entrevistada:", ln=True); pdf.image(firma_path, x=25, w=70); pdf.ln(6)
        except Exception: pass
    pdf.ln(12); pdf.cell(85,8,"____________________________", ln=False, align="C"); pdf.cell(85,8,"____________________________", ln=True, align="C")
    pdf.cell(85,6,"Firma persona entrevistada", ln=False, align="C"); pdf.cell(85,6,"Firma personal actuante", ln=True, align="C")
    pdf.set_y(-25); pdf.set_font("Arial","I",8); pdf.cell(0,8,"Creado por Sub-Comisario Castaneda Juan - S.I.V.", align="R")
    return pdf_bytes(pdf)

# --------------------------- interfaz ---------------------------

st.title("🗣️ BLOQUE 3 — ACTA DE ENTREVISTA A VÍCTIMA / DAMNIFICADO")
st.subheader("Relato en primera persona, detector orientativo y noticia criminis para el actante")
st.warning("El acta NO debe quedar como cuestionario. El sistema alerta; el policía pregunta; la víctima relata en primera persona.")

tabs = st.tabs(["1. Identificación", "2. Relato", "3. Análisis S.I.V.", "4. Relato final / resumen", "5. Firma / PDF / JSON"])

with tabs[0]:
    st.subheader("Datos de la víctima / damnificado")
    c1,c2 = st.columns(2)
    with c1:
        condicion = st.selectbox("Condición", ["Víctima","Damnificado","Denunciante","Representante legal","Otro"], key="b3_condicion")
        nombre = st.text_input("Apellido y nombres", key="b3_nombre")
        dni = st.text_input("DNI", key="b3_dni")
        edad = st.text_input("Edad", key="b3_edad")
        fecha_nac = st.text_input("Fecha de nacimiento", key="b3_fecha_nac")
    with c2:
        domicilio = st.text_area("Domicilio", key="b3_domicilio")
        telefono_fijo = st.text_input("Teléfono fijo", key="b3_telefono_fijo")
        celular = st.text_input("Celular", key="b3_celular")
        correo = st.text_input("Correo electrónico", key="b3_correo")
    st.info("Base protocolo: individualizar víctima/testigos y registrar datos de contacto.")

with tabs[1]:
    st.subheader("Relato inicial en primera persona")
    st.markdown("Escribir como habla la víctima: **Yo estaba... vi... sentí... me golpeó... me sustrajo... temo...**")
    relato_inicial = st.text_area("Relato inicial", height=370, placeholder="Yo estaba en la parada del colectivo cuando...", key="b3_relato_inicial")
    evito = st.radio("¿Se evitó contacto entre víctima/testigo e imputado/aprehendido?", ["SI","NO","NO CORRESPONDE"], horizontal=True, key="b3_evito_contacto")
    obs_contacto = st.text_area("Observación sobre resguardo/no contaminación del testimonio", key="b3_obs_contacto")

with tabs[2]:
    st.subheader("Análisis orientativo S.I.V.")
    analisis = analizar_relato(st.session_state.get("b3_relato_inicial", ""))
    st.markdown("### Alertas")
    for a in analisis["alertas"]: st.warning(a)
    st.markdown("### Naturaleza de acción orientativa")
    for n in analisis["naturaleza_accion_orientativa"] or ["Sin naturaleza orientativa definida"]: st.info(n)
    st.markdown("### Guía interna para el policía")
    for g in analisis["guia_interna"]: st.write(f"- {g}")
    st.markdown("### Fragmentos modelo para integrar al relato")
    fr = fragmentos_modelo(analisis)
    if fr:
        for x in fr: st.code(x)
    else: st.info("Sin fragmentos modelo específicos.")
    requiere = any("instancia" in x.lower() or "lesiones" in x.lower() for x in analisis["alertas"] + analisis["naturaleza_accion_orientativa"])
    if requiere: st.error("⚠️ Verificar si corresponde consultar deseo de instar acción penal, especialmente por lesiones leves.")
    instancia_penal = st.selectbox("Deseo de instar acción penal, si corresponde", ["NO_DEFINIDO","SI","NO","NO_CORRESPONDE"] if requiere else ["NO_CORRESPONDE","NO_DEFINIDO","SI","NO"], key="b3_instancia_penal")

with tabs[3]:
    st.subheader("Relato final y noticia criminis")
    if "b3_relato_final" not in st.session_state or not st.session_state.b3_relato_final:
        st.session_state.b3_relato_final = st.session_state.get("b3_relato_inicial", "")
    relato_final = st.text_area("Relato final en primera persona", height=380, key="b3_relato_final")
    fil_tmp = {"condicion":st.session_state.get("b3_condicion",""),"nombre":st.session_state.get("b3_nombre",""),"dni":st.session_state.get("b3_dni",""),"edad":st.session_state.get("b3_edad",""),"fecha_nac":st.session_state.get("b3_fecha_nac",""),"domicilio":st.session_state.get("b3_domicilio",""),"telefono_fijo":st.session_state.get("b3_telefono_fijo",""),"celular":st.session_state.get("b3_celular",""),"correo":st.session_state.get("b3_correo","")}
    an_fin = analizar_relato(relato_final)
    not_auto = noticia_criminis(fil_tmp, relato_final, an_fin, st.session_state.get("b3_instancia_penal", "NO_DEFINIDO"))
    fund_auto = fundamento(relato_final, an_fin)
    noticia = st.text_area("Súper resumen / noticia criminis para acta de procedimiento", value=st.session_state.get("b3_noticia_criminis", not_auto), height=180, key="b3_noticia_criminis")
    fund = st.text_area("Fundamento orientativo de intervención/aprehensión", value=st.session_state.get("b3_fundamento_aprehension", fund_auto), height=140, key="b3_fundamento_aprehension")
    if st.button("🔄 Regenerar resumen desde relato final", use_container_width=True):
        st.session_state.b3_noticia_criminis = not_auto
        st.session_state.b3_fundamento_aprehension = fund_auto
        st.rerun()

with tabs[4]:
    st.subheader("Firma digital, PDF y JSON")
    canvas = st_canvas(fill_color="rgba(255,255,255,1)", stroke_width=3, stroke_color="#000000", background_color="#FFFFFF", height=170, width=500, drawing_mode="freedraw", key="b3_firma_canvas")
    firma_path = firma_a_path(canvas)
    fil = {"condicion":st.session_state.get("b3_condicion",""),"nombre":st.session_state.get("b3_nombre",""),"dni":st.session_state.get("b3_dni",""),"edad":st.session_state.get("b3_edad",""),"fecha_nac":st.session_state.get("b3_fecha_nac",""),"domicilio":st.session_state.get("b3_domicilio",""),"telefono_fijo":st.session_state.get("b3_telefono_fijo",""),"celular":st.session_state.get("b3_celular",""),"correo":st.session_state.get("b3_correo","")}
    rel = st.session_state.get("b3_relato_final", st.session_state.get("b3_relato_inicial", ""))
    an = analizar_relato(rel)
    noti = st.session_state.get("b3_noticia_criminis", noticia_criminis(fil, rel, an, st.session_state.get("b3_instancia_penal", "NO_DEFINIDO")))
    fundi = st.session_state.get("b3_fundamento_aprehension", fundamento(rel, an))
    datos = {"bloque":3,"modulo":"BLOQUE_3_ENTREVISTA_VICTIMA","version":"primera_persona_detector_accion_penal","filiacion":fil,"contenido":rel,"relato_primera_persona":rel,"evito_contacto_imputado":st.session_state.get("b3_evito_contacto",""),"observacion_no_contaminacion":st.session_state.get("b3_obs_contacto",""),"analisis_siv":an,"instancia_penal":st.session_state.get("b3_instancia_penal","NO_DEFINIDO"),"noticia_criminis":noti,"fundamento_aprehension":fundi,"resumen_para_acta_procedimiento":noti,"firma_digital":"SÍ" if firma_path else "NO","creado_en":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    pdf = generar_pdf(fil, rel, noti, fundi, an, firma_path)
    c1,c2=st.columns(2)
    with c1: st.download_button("📄 Descargar PDF Acta de Entrevista", pdf, file_name="Bloque_3_Acta_Entrevista_Victima.pdf", mime="application/pdf", use_container_width=True)
    with c2: st.download_button("📦 Descargar JSON para actante / BLOQUE 8", json.dumps(datos, ensure_ascii=False, indent=4), file_name="bloque_3_entrevista_victima.json", mime="application/json", use_container_width=True)
    with st.expander("Ver JSON BLOQUE 3"): st.code(json.dumps(datos, ensure_ascii=False, indent=4), language="json")
    if firma_path and os.path.exists(firma_path):
        try: os.unlink(firma_path)
        except Exception: pass

try:
    autoguardar_bloque(BLOQUE_ID)
except Exception:
    pass
