"""Info ExpeDJ: tablero para que las ULE sigan el estado de sus expedientes con DJ.

Prototipo con datos FICTICIOS.  Correr con:  uv run streamlit run app/app.py
"""
import hmac

import streamlit as st

from datos import cargar_datos
from vistas import vista_ingreso, vista_resultados

st.set_page_config(page_title="Información sobre expedientes con DJ", page_icon=":material/folder_shared:", layout="wide")

AVISO = ("Prototipo personal con datos ficticios. No contiene información real "
         "ni representa la posición del MIDIS-OFIS.")


def iniciar_sesion():
    """Pide usuario y contraseña. Los usuarios están en .streamlit/secrets.toml."""
    with st.container(width=420):
        st.title("Información sobre expedientes con DJ")
        st.caption("Estado de los expedientes con DJ que envían las ULE")
        with st.form("ingreso"):
            usuario = st.text_input("Usuario", key="campo_usuario")
            clave = st.text_input("Contraseña", type="password", key="campo_clave")
            entrar = st.form_submit_button("Ingresar", type="primary", icon=":material/login:",
                                           width="stretch")
        if entrar:
            datos = st.secrets.get("usuarios", {}).get(usuario)
            if datos and hmac.compare_digest(clave, datos["clave"]):
                st.session_state.usuario = dict(datos)
                st.rerun()
            st.error("Usuario o contraseña incorrectos.", icon=":material/error:")
        st.caption(AVISO)


if "usuario" not in st.session_state:
    iniciar_sesion()
    st.stop()

usuario = st.session_state.usuario
expedientes, observaciones, origen, hora = cargar_datos()

with st.sidebar:
    st.markdown(f"**{usuario['etiqueta']}**")
    st.caption("Perfil: ULE" if usuario["perfil"] == "ULE" else "Perfil: coordinación territorial")
    if st.button("Actualizar datos", icon=":material/refresh:", width="stretch"):
        cargar_datos.clear()
        st.rerun()
    st.caption(f"Datos leídos de {origen} el {hora}.")
    if st.button("Cerrar sesión", icon=":material/logout:", width="stretch"):
        del st.session_state.usuario
        st.rerun()
    st.caption(AVISO)

st.title("Información sobre expedientes con DJ")
if usuario["perfil"] == "ULE":
    # La ULE solo ve la primera pestaña y solo sus expedientes
    vista_resultados(expedientes, observaciones, perfil="ULE", ubigeo=usuario["ubigeo"])
else:
    resultados, ingreso = st.tabs([":material/fact_check: Resultado de la evaluación",
                                   ":material/map: Ingreso de expedientes"])
    with resultados:
        vista_resultados(expedientes, observaciones, perfil="CT")
    with ingreso:
        vista_ingreso(expedientes, observaciones)