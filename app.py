import streamlit as st
import sqlite3
import os
import base64

# Configuración de la página
st.set_page_config(page_title="Consulta de NSS - Metepec II", layout="wide")
st.title("🗂️ Sistema de Consulta de Número de Seguridad Social (NSS)")
st.subheader("CECYTEM Plantel Metepec II")

# --- CONEXIÓN Y CONFIGURACIÓN DE BASE DE DATOS ---
DB_NAME = "buscar_documentos.db"
CARPETA_ANEXOS = "archivos_escaneados"

def conectar_db():
    return sqlite3.connect(DB_NAME)

def inicializar_db_dinamica():
    """Crea la tabla con los nuevos campos de búsqueda y carga los alumnos de prueba."""
    if not os.path.exists(CARPETA_ANEXOS):
        os.makedirs(CARPETA_ANEXOS)
        
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS documentos")
    
    cursor.execute("""
        CREATE TABLE documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_control TEXT UNIQUE,
            alumno_nombre TEXT,
            nss TEXT,
            categoria TEXT,
            fecha_registro DATE,
            archivo_nombre TEXT
        )
    """)
    
    datos_alumnos = [
        ('23215060110001', 'Juan Pérez López', '12345678901', 'Seguridad Social', '2026-06-09', 'doc_001.pdf'),
        ('23215060110002', 'María Rodríguez García', '98765432102', 'Seguridad Social', '2026-06-09', 'doc_002.pdf')
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO documentos (num_control, alumno_nombre, nss, categoria, fecha_registro, archivo_nombre)
        VALUES (?, ?, ?, ?, ?, ?)
    """, datos_alumnos)
        
    conn.commit()
    conn.close()

# Inicializar base de datos
inicializar_db_dinamica()

# --- FUNCIONES DE VISUALIZACIÓN ---
def mostrar_pdf_estable(ruta_pdf):
    """Muestra el PDF usando flujos binarios optimizados."""
    if os.path.exists(ruta_pdf):
        nombre_archivo = os.path.basename(ruta_pdf)
        
        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()
        
        st.download_button(
            label=f"📥 Abrir / Descargar {nombre_archivo} en pestaña nueva",
            data=pdf_bytes,
            file_name=nombre_archivo,
            mime="application/pdf"
        )
        
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="750px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.error(f"⚠️ El archivo físico '{os.path.basename(ruta_pdf)}' no se encuentra.")


# --- CONTROL DE ACCESO (SISTEMA DE SEGURIDAD SEGURO) ---

PASSWORD_CORRECTO = "MetepecII_2026"

# Inicializar estado de autenticación
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# Callback para procesar el login de forma nativa sin usar st.rerun
def verificar_password():
    if st.session_state["password_input"] == PASSWORD_CORRECTO:
        st.session_state["autenticado"] = True
    else:
        st.session_state["autenticado"] = False
        st.sidebar.error("❌ Contraseña incorrecta.")

# Si no está autenticado, bloquea la pantalla completa
if not st.session_state["autenticado"]:
    st.markdown("### 🔐 Acceso Restringido")
    st.info("Por favor, introduce las credenciales asignadas por la administración del plantel para consultar los números de seguridad social.")
    
    # El parámetro on_change ejecuta la verificación de manera limpia en el backend de Streamlit
    st.text_input(
        "Introduce la contraseña del sistema:", 
        type="password", 
        key="password_input", 
        on_change=verificar_password
    )
            
else:
    # --- INTERFAZ DEL SISTEMA (SOLO VISIBLE SI ESTÁ AUTENTICADO) ---
    
    # Opción sencilla para cerrar sesión reiniciando el estado completo
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state["autenticado"] = False
        st.write('<meta http-equiv="refresh" content="0">', unsafe_allow_html=True) # Alternativa limpia para refrescar

    st.sidebar.header("🔍 Filtros de Búsqueda")
    busqueda_texto = st.sidebar.text_input("Buscar por Nombre, Archivo, NSS o No. Control:")

    # Consulta SQL Dinámica
    query = """
        SELECT id, num_control, alumno_nombre, nss, categoria, fecha_registro, archivo_nombre 
        FROM documentos 
        WHERE 1=1
    """
    parametros = []

    if busqueda_texto:
        query += """ 
            AND (alumno_nombre LIKE ? 
            OR archivo_nombre LIKE ? 
            OR nss LIKE ? 
            OR num_control LIKE ?)
        """
        termino = f"%{busqueda_texto}%"
        parametros.extend([termino, termino, termino, termino])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(query, parametros)
    resultados = cursor.fetchall()
    conn.close()

    col_lista, col_visor = st.columns([1, 1])

    with col_lista:
        st.subheader("📋 Expedientes Encontrados")
        if resultados:
            opciones_docs = {}
            
            for doc in resultados:
                id_doc, num_control, alumno, nss, categoria, fecha, archivo = doc
                opciones_docs[f"{alumno} ({num_control})"] = archivo
                
                with st.container():
                    st.markdown(f"### 👨‍🎓 Alumno: {alumno}")
                    st.text(
                        f"No. Control: {num_control}\n"
                        f"NSS: {nss}\n"
                        f"Archivo Físico: {archivo}\n"
                        f"Fecha de Registro: {fecha}"
                    )
                    st.markdown("---")
            
            seleccion = st.radio(
                "Seleccione el alumno para visualizar su NSS:",
                options=list(opciones_docs.keys()),
                key="selector_alumnos"
            )
            st.session_state['archivo_seleccionado'] = opciones_docs[seleccion]
        else:
            st.info("No se encontraron coincidencias con los datos ingresados.")
            st.session_state['archivo_seleccionado'] = None

    with col_visor:
        st.subheader("📄 Visor de Expediente PDF")
        if 'archivo_seleccionado' in st.session_state and st.session_state['archivo_seleccionado']:
            archivo_a_cargar = st.session_state['archivo_seleccionado']
            ruta_completa = os.path.join(CARPETA_ANEXOS, archivo_a_cargar)
            mostrar_pdf_estable(ruta_completa)
        else:
            st.info("Seleccione un registro de la izquierda para previsualizar.")
