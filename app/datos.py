"""Lee y prepara las 3 matrices FICTICIAS de expedientes.

La app las lee desde Google Sheets, así ve los cambios del día. Si no hay
conexión, usa la copia local de data/ficticios/.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Hoja de Google Sheets con los datos ficticios (compartida como "Lector")
ID_HOJA = "1ppL-ulk5g2sXUAO-GrGs9G3wqURakWwuLfZCw_zlzlY"
PESTANAS = {
    "expedientes": 532017155,
    "observaciones_determinacion": 2071434572,
    "observaciones_reevaluacion": 467774275,
}
CARPETA_LOCAL = Path(__file__).parents[1] / "data" / "ficticios"
SIN_DATO = ("", "PENDIENTE", "NO REQUIERE", "-")

# Estado que ve la ULE: (color de la insignia, ícono)
ESTADOS = {
    "En evaluación": ("gray", ":material/hourglass_top:"),
    "Conforme": ("green", ":material/check_circle:"),
    "Observado: por subsanar": ("orange", ":material/warning:"),
    "Subsanado": ("blue", ":material/task_alt:"),
    "No procede": ("red", ":material/block:"),
    "Atendido por firma digital": ("violet", ":material/draw:"),
    "No procesado (ver nota)": ("gray", ":material/info:"),
}


def leer(fuente):
    return pd.read_csv(fuente, dtype=str, keep_default_na=False).apply(lambda c: c.str.strip())


def fecha(columna):
    """Convierte dd/mm/aaaa en fecha; PENDIENTE, NO REQUIERE o "-" quedan vacíos."""
    return pd.to_datetime(columna, format="%d/%m/%Y", errors="coerce")


def estado(fila):
    resultado = fila["RESULTADO DE EVALUACIÓN"]
    if resultado == "PENDIENTE":
        return "En evaluación"
    if resultado == "CONFORME":
        return "Conforme"
    if resultado == "-":
        if fila["¿DÓNDE SE PROCESÓ?"] == "FIRMA DIGITAL":
            return "Atendido por firma digital"
        return "No procesado (ver nota)"
    subsanacion = {"OBSERVADA": "Observado: por subsanar", "SUBSANADO": "Subsanado",
                   "NO PROCEDE": "No procede"}
    return subsanacion.get(fila["ESTADO DE SUBSANACIÓN"], "Observado: por subsanar")


def documento(fila):
    """Con qué documento se atendió el expediente."""
    if fila["N° RSE"] not in SIN_DATO:
        return f"RSE N.° {fila['N° RSE']}"
    if fila["N° OFICIO"] not in SIN_DATO:
        return f"Oficio N.° {fila['N° OFICIO']}"
    if fila["¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?"] == "PENDIENTE":
        return "Pendiente"
    return fila["¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?"].capitalize()


def preparar_expedientes(df):
    hoy = pd.Timestamp.now(tz="America/Lima").tz_localize(None).normalize()
    df["ESTADO"] = df.apply(estado, axis=1)
    df["DOCUMENTO"] = df.apply(documento, axis=1)
    df["ULE"] = df["DISTRITO"] + ", " + df["PROVINCIA"] + " (" + df["DEPARTAMENTO"] + ")"

    df["f_ingreso"] = fecha(df["FECHA EXPEDIENTE"])
    df["f_observacion"] = fecha(df["FECHA DE ENVÍO DE CORREO"])
    # La respuesta final es el primer documento enviado: RSE, oficio o correo
    df["f_respuesta"] = pd.concat([fecha(df["FECHA DE PUBLICACIÓN DE RSE"]),
                                   fecha(df["FECHA DEL OFICIO"]),
                                   fecha(df["FECHA ENVÍO DEL CORREO"])], axis=1).min(axis=1)

    respondido = df["f_respuesta"].notna()
    df["dias_atencion"] = np.nan
    df.loc[respondido, "dias_atencion"] = np.busday_count(
        df.loc[respondido, "f_ingreso"].values.astype("datetime64[D]"),
        df.loc[respondido, "f_respuesta"].values.astype("datetime64[D]"))
    por_subsanar = df["ESTADO"] == "Observado: por subsanar"
    df["dias_por_subsanar"] = (hoy - df["f_observacion"]).dt.days.where(por_subsanar)
    return df


def unir_observaciones(determinacion, reevaluacion):
    return pd.concat([determinacion.assign(**{"TIPO DE DJ": "Determinación"}),
                      reevaluacion.assign(**{"TIPO DE DJ": "Reevaluación"})], ignore_index=True)


@st.cache_data(ttl="10m", show_spinner="Leyendo las matrices…")
def cargar_datos():
    """Devuelve (expedientes, observaciones, origen de los datos, hora de lectura)."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{ID_HOJA}/export?format=csv&gid="
        tablas = {nombre: leer(url + str(gid)) for nombre, gid in PESTANAS.items()}
        origen = "Google Sheets"
    except Exception:
        tablas = {nombre: leer(CARPETA_LOCAL / f"{nombre}.csv") for nombre in PESTANAS}
        origen = "copia local (sin conexión a Google Sheets)"

    expedientes = preparar_expedientes(tablas["expedientes"])
    observaciones = unir_observaciones(tablas["observaciones_determinacion"],
                                       tablas["observaciones_reevaluacion"])
    hora = pd.Timestamp.now(tz="America/Lima").strftime("%d/%m/%Y a las %H:%M")
    return expedientes, observaciones, origen, hora