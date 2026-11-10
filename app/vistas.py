"""Las 2 pestañas del tablero: resultado de la evaluación e ingreso de expedientes."""
import json
import re
from pathlib import Path

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st

from datos import ESTADOS

MAPA = Path(__file__).parents[1] / "data" / "geo" / "peru_departamental_simple.geojson"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
AZULES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TIPOS = {"DETERMINACIÓN": "Determinación", "REEVALUACION": "Reevaluación", "MIXTO": "Mixto"}
ALTO = 420  # alto del mapa y del gráfico de observaciones, para que queden parejos

# Columnas de la tabla de expedientes: (columna de la matriz, título en la app)
COLUMNAS_ULE = {
    "EXPEDIENTE": "Expediente", "FECHA EXPEDIENTE": "Fecha de ingreso",
    "TIPO DE SOLICITUDES": "Tipo de solicitud", "ESTADO": "Estado",
    "¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?": "Cómo se comunicó",
    "DOCUMENTO": "Documento de atención", "OBSERVACIÓN": "Nota",
}
# Proceso interno: solo lo ve el coordinador territorial
COLUMNAS_CT = {
    "¿DÓNDE SE PROCESÓ?": "Dónde se procesó", "FECHA DERIVACIÓN": "Fecha de derivación",
    "FECHA DE ASIGNACIÓN PARA SU ATENCIÓN": "Fecha de asignación",
    "¿ADJUNTA DJ FIRMADAS DIGITALMENTE?": "¿Adjunta DJ firmadas digitalmente?",
}


def texto(valor):
    """Valor de la matriz para el recorrido: las celdas vacías o con "-" no aplican."""
    return "No aplica" if valor in ("", "-") else valor


# ---------- Pestaña 1: resultado de la evaluación ----------

def vista_resultados(expedientes, observaciones, perfil, ubigeo=None):
    if perfil == "CT":
        ubigeo = elegir_ule(expedientes)
        if ubigeo is None:
            st.info("Elige una ULE para ver el resultado de sus expedientes.", icon=":material/search:")
            return

    propios = expedientes[expedientes["UBIGEO"] == ubigeo].sort_values("f_ingreso", ascending=False)
    if propios.empty:
        st.info("Esta ULE todavía no tiene expedientes registrados.")
        return
    primera = propios.iloc[0]
    st.subheader(f"ULE de {primera['DISTRITO']}")
    st.caption(f"Provincia de {primera['PROVINCIA']}, departamento de {primera['DEPARTAMENTO']} · "
               f"Coordinación territorial: {primera['COORDINADOR TERRITORIAL']}")

    pendientes = propios[propios["ESTADO"] == "Observado: por subsanar"]
    if not pendientes.empty:
        quien = "Tienes" if perfil == "ULE" else "Esta ULE tiene"
        n = len(pendientes)
        st.warning(
            f"El más antiguo lleva {int(pendientes['dias_por_subsanar'].max())} días desde el correo "
            "de observación. Selecciónalo en la tabla para ver los pasos para subsanar.",
            title=f"{quien} {n} expediente{'s' if n > 1 else ''} observado{'s' if n > 1 else ''} por subsanar",
            icon=":material/warning:")

    with st.container(horizontal=True):
        st.metric("Expedientes enviados", len(propios), border=True)
        st.metric("Conformes", int((propios["ESTADO"] == "Conforme").sum()), border=True)
        st.metric("Por subsanar", len(pendientes), border=True)
        st.metric("En evaluación", int((propios["ESTADO"] == "En evaluación").sum()), border=True)

    columnas = COLUMNAS_ULE | (COLUMNAS_CT if perfil == "CT" else {})
    tabla = propios[list(columnas)].rename(columns=columnas)
    evento = st.dataframe(
        tabla, hide_index=True, on_select="rerun", selection_mode="single-row",
        key=f"tabla_{ubigeo}", alt=f"Expedientes de la ULE de {primera['DISTRITO']}")

    if not evento.selection.rows:
        st.caption(":material/touch_app: Selecciona un expediente en la tabla para ver su detalle.")
        return
    detalle_expediente(propios.iloc[evento.selection.rows[0]], observaciones, perfil)


def elegir_ule(expedientes):
    ules = (expedientes.drop_duplicates("UBIGEO").sort_values("ULE")
            .set_index("UBIGEO")["ULE"])
    return st.selectbox("ULE", ules.index, index=None, format_func=ules.get,
                        placeholder="Escribe el nombre del distrito…", key="ule_elegida")


def detalle_expediente(exp, observaciones, perfil):
    color, icono = ESTADOS[exp["ESTADO"]]
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.subheader(f"Expediente {exp['EXPEDIENTE']}")
            st.badge(exp["ESTADO"], color=color, icon=icono)

        pasos = {"Ingreso del expediente": exp["FECHA EXPEDIENTE"]}
        if perfil == "CT":
            pasos |= {"Derivación": exp["FECHA DERIVACIÓN"],
                      "Asignación para su atención": exp["FECHA DE ASIGNACIÓN PARA SU ATENCIÓN"],
                      "Dónde se procesó": exp["¿DÓNDE SE PROCESÓ?"]}
        pasos |= {
            "Resultado de la evaluación": exp["RESULTADO DE EVALUACIÓN"],
            "Correo de observación": exp["FECHA DE ENVÍO DE CORREO"],
            "Subsanación": exp["ESTADO DE SUBSANACIÓN"],
            "Fecha de subsanación": exp["FECHA DE SUBSANACIÓN"],
            "Cómo se comunicó el resultado": exp["¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?"],
            "Documento de atención": exp["DOCUMENTO"],
        }
        recorrido = pd.DataFrame({"Paso": list(pasos), "Fecha o estado": [texto(v) for v in pasos.values()]})
        st.table(recorrido, hide_index=True, alt="Recorrido del expediente paso a paso")

        if exp["OBSERVACIÓN"]:
            st.info(exp["OBSERVACIÓN"], title="Nota del expediente", icon=":material/sticky_note_2:")

        dj = observaciones[observaciones["EXPEDIENTE"] == exp["EXPEDIENTE"]]
        if dj.empty:
            return
        st.markdown(f"**DJ observadas: {dj['N° DJ'].nunique()}**")
        for criterio, grupo in dj.groupby("OBSERVACIÓN", sort=False):
            with st.container(border=True):
                st.markdown(f"**{criterio}** · DJ de {grupo['TIPO DE DJ'].iloc[0].lower()}: "
                            f"{', '.join(grupo['N° DJ'])}")
                st.markdown(grupo["DETALLE DE OBSERVACIÓN"].iloc[0])
                # "1. … 2. …" se muestra como lista, un paso por línea
                pasos = re.sub(r" (?=\d+\. )", "\n", grupo["PASOS PARA SUBSANAR OBSERVACIÓN"].iloc[0])
                st.success(pasos, title="Pasos para subsanar", icon=":material/checklist:")


# ---------- Pestaña 2: ingreso de expedientes ----------

def vista_ingreso(expedientes, observaciones):
    with st.container(horizontal=True, vertical_alignment="bottom"):
        deptos = st.multiselect("Departamento", sorted(expedientes["DEPARTAMENTO"].unique()),
                                placeholder="Todos")
        coords = st.multiselect("Coordinación territorial",
                                sorted(expedientes["COORDINADOR TERRITORIAL"].unique()),
                                placeholder="Todas")
        tipos = st.pills("Tipo de solicitud", list(TIPOS), format_func=TIPOS.get,
                         selection_mode="multi", default=list(TIPOS))

    df = expedientes
    if deptos:
        df = df[df["DEPARTAMENTO"].isin(deptos)]
    if coords:
        df = df[df["COORDINADOR TERRITORIAL"].isin(coords)]
    df = df[df["TIPO DE SOLICITUDES"].isin(tipos)]
    if df.empty:
        st.info("No hay expedientes con estos filtros.")
        return
    obs = observaciones[observaciones["EXPEDIENTE"].isin(df["EXPEDIENTE"])]

    evaluados = df["RESULTADO DE EVALUACIÓN"].isin(["CONFORME", "OBSERVADO"])
    observados = df["RESULTADO DE EVALUACIÓN"] == "OBSERVADO"
    with st.container(horizontal=True):
        st.metric("Expedientes recibidos", f"{len(df):,}", border=True)
        st.metric("Observados", f"{observados.sum() / max(evaluados.sum(), 1):.0%}", border=True,
                  help="Porcentaje de los expedientes evaluados que salieron observados.")
        st.metric("Por subsanar", int((df["ESTADO"] == "Observado: por subsanar").sum()), border=True)
        st.metric("Tiempo de atención", f"{df['dias_atencion'].mean():.1f} días", border=True,
                  help="Promedio de días hábiles entre el ingreso del expediente y el envío de la respuesta.")
        st.metric("En evaluación", int((df["ESTADO"] == "En evaluación").sum()), border=True)

    izquierda, derecha = st.columns([3, 2])
    with izquierda, st.container(border=True):
        mapa_departamentos(df)
    with derecha, st.container(border=True):
        observaciones_frecuentes(obs)

    with st.container(border=True):
        st.markdown("**Expedientes recibidos por mes**")
        por_mes = df.groupby(df["f_ingreso"].dt.to_period("M")).size().reset_index(name="Expedientes")
        por_mes["Mes"] = [MESES[p.month - 1] + f" {p.year}" for p in por_mes["f_ingreso"]]
        grafico = alt.Chart(por_mes).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Mes:N", sort=list(por_mes["Mes"]), title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Expedientes:Q", title="Expedientes"),
            tooltip=["Mes", "Expedientes"])
        st.altair_chart(grafico, alt="Expedientes recibidos por mes")

    with st.container(border=True):
        st.markdown("**ULE para priorizar la asistencia técnica**")
        st.caption("Ordenadas por expedientes por subsanar y por los días que llevan pendientes.")
        ranking_ule(df)


def mapa_departamentos(df):
    st.markdown("**Mapa por departamento**")
    medida = st.segmented_control(
        "Mostrar", ["Expedientes recibidos", "% observados", "Por subsanar"],
        default="Expedientes recibidos", required=True, label_visibility="collapsed")
    resumen = df.groupby("DEPARTAMENTO").agg(
        recibidos=("EXPEDIENTE", "size"),
        evaluados=("RESULTADO DE EVALUACIÓN", lambda r: r.isin(["CONFORME", "OBSERVADO"]).sum()),
        observados=("RESULTADO DE EVALUACIÓN", lambda r: (r == "OBSERVADO").sum()),
        por_subsanar=("ESTADO", lambda e: (e == "Observado: por subsanar").sum()),
    ).reset_index()
    resumen["Expedientes recibidos"] = resumen["recibidos"]
    resumen["% observados"] = (100 * resumen["observados"] / resumen["evaluados"].clip(lower=1)).round(1)
    resumen["Por subsanar"] = resumen["por_subsanar"]

    geo = json.loads(MAPA.read_text(encoding="utf-8"))
    figura = px.choropleth(
        resumen, geojson=geo, locations="DEPARTAMENTO", featureidkey="properties.NOMBDEP",
        color=medida, color_continuous_scale=AZULES, hover_name="DEPARTAMENTO",
        hover_data={"DEPARTAMENTO": False, "Expedientes recibidos": True,
                    "% observados": True, "Por subsanar": True})
    figura.update_geos(fitbounds="locations", visible=False, projection_type="mercator")
    figura.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=ALTO,
                         coloraxis_colorbar=dict(title=None, thickness=12))
    st.plotly_chart(figura, alt=f"Mapa del Perú por departamento: {medida.lower()}")


def observaciones_frecuentes(obs):
    st.markdown("**Observaciones más frecuentes**")
    if obs.empty:
        st.caption("No hay DJ observadas con estos filtros.")
        return
    conteo = obs["OBSERVACIÓN"].value_counts().reset_index()
    conteo.columns = ["Observación", "DJ observadas"]
    grafico = alt.Chart(conteo).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
        x=alt.X("DJ observadas:Q"),
        y=alt.Y("Observación:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
        tooltip=["Observación", "DJ observadas"]).properties(height=ALTO)
    st.altair_chart(grafico, alt=f"Observaciones más frecuentes; la primera es {conteo.iloc[0, 0]}")


def ranking_ule(df):
    ranking = df.groupby(["UBIGEO", "ULE", "COORDINADOR TERRITORIAL"]).agg(
        expedientes=("EXPEDIENTE", "size"),
        evaluados=("RESULTADO DE EVALUACIÓN", lambda r: r.isin(["CONFORME", "OBSERVADO"]).sum()),
        observados=("RESULTADO DE EVALUACIÓN", lambda r: (r == "OBSERVADO").sum()),
        por_subsanar=("ESTADO", lambda e: (e == "Observado: por subsanar").sum()),
        dias=("dias_por_subsanar", "max"),
    ).reset_index()
    ranking["pct"] = 100 * ranking["observados"] / ranking["evaluados"].clip(lower=1)
    ranking = ranking.sort_values(["por_subsanar", "dias", "pct"], ascending=False)
    st.dataframe(
        ranking, hide_index=True, height=380,
        column_order=["ULE", "COORDINADOR TERRITORIAL", "expedientes", "observados", "pct",
                      "por_subsanar", "dias"],
        column_config={
            "ULE": st.column_config.TextColumn("ULE", width="medium"),
            "COORDINADOR TERRITORIAL": "Coordinación",
            "expedientes": st.column_config.NumberColumn("Expedientes"),
            "observados": st.column_config.NumberColumn("Observados"),
            "pct": st.column_config.ProgressColumn("% observados", min_value=0, max_value=100,
                                                   format="%.0f%%"),
            "por_subsanar": st.column_config.NumberColumn("Por subsanar"),
            "dias": st.column_config.NumberColumn("Días del más antiguo", format="%d"),
        },
        alt="ULE ordenadas por expedientes por subsanar")