"""Genera las 3 matrices FICTICIAS de expedientes que usa el dashboard.

Ningún dato sale de las matrices reales. Los expedientes, DJ, oficios, RSE,
observaciones y coordinadores son inventados. Solo los ubigeos y los nombres
de los distritos son reales (municipalidades de la RENAMU 2026, INEI).

Uso:   uv run python data/generar_datos_ficticios.py
Crea:  data/ficticios/expedientes.csv                 (matriz 1)
       data/ficticios/observaciones_determinacion.csv (matriz 2)
       data/ficticios/observaciones_reevaluacion.csv  (matriz 3)
"""
from pathlib import Path

import numpy as np
import pandas as pd

CARPETA = Path(__file__).parent
RENAMU = CARPETA / "referencia" / "renamu_indicadores_2024_2026.csv"
SALIDA = CARPETA / "ficticios"

SEMILLA = 2027                    # la misma semilla da siempre los mismos datos
INICIO = pd.Timestamp("2026-01-05")
CORTE = pd.Timestamp("2026-11-06")  # "hoy" en los datos: nada ocurre después
FRACCION_ULE = 0.45   # parte de las municipalidades de cada departamento que envía expedientes
N_COORDINADORES = 6
PENDIENTE = "PENDIENTE"   # para los pasos que aún no ocurren

# ULE de los usuarios de prueba y cuántos expedientes tendrán en el demo
ULE_DEMO = {"150110": 14, "050401": 10}

COLUMNAS = [
    "N°", "EXPEDIENTE", "UBIGEO", "DEPARTAMENTO", "PROVINCIA", "DISTRITO",
    "FECHA EXPEDIENTE", "FECHA DERIVACIÓN", "¿ADJUNTA DJ FIRMADAS DIGITALMENTE?",
    "¿DÓNDE SE PROCESÓ?", "FECHA DE ASIGNACIÓN PARA SU ATENCIÓN",
    "TIPO DE SOLICITUDES", "RESULTADO DE EVALUACIÓN", "FECHA DE ENVÍO DE CORREO",
    "ESTADO DE SUBSANACIÓN", "FECHA DE SUBSANACIÓN",
    "¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?", "N° RSE",
    "FECHA DE PUBLICACIÓN DE RSE", "N° OFICIO", "FECHA DEL OFICIO",
    "FECHA ENVÍO DEL CORREO", "COORDINADOR TERRITORIAL", "OBSERVACIÓN",
]
ETAPA_EVALUACION = ["RESULTADO DE EVALUACIÓN", "FECHA DE ENVÍO DE CORREO",
                    "ESTADO DE SUBSANACIÓN", "FECHA DE SUBSANACIÓN"]
ETAPA_COMUNICACION = ["¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?", "N° RSE",
                      "FECHA DE PUBLICACIÓN DE RSE", "N° OFICIO", "FECHA DEL OFICIO",
                      "FECHA ENVÍO DEL CORREO"]
COLUMNAS_OBS = ["UBIGEO", "EXPEDIENTE", "N° DJ", "OBSERVACIÓN",
                "DETALLE DE OBSERVACIÓN", "PASOS PARA SUBSANAR OBSERVACIÓN"]

# Criterios de ejemplo, redactados para este demo (no son los textos reales).
# "aplica" dice en qué matriz puede aparecer; "peso", qué tan frecuente es;
# si "subsanable" es False, el expediente queda como NO PROCEDE.
CRITERIOS = [
    dict(obs="DJ SIN FIRMA", aplica="ambas", peso=30, subsanable=True,
         detalle="La DJ no tiene la firma manual del alcalde ni del gerente con delegación de firma.",
         pasos="1. Imprimir la DJ. 2. Hacerla firmar por el alcalde o por el gerente con delegación de firma. 3. Escanearla y enviarla nuevamente."),
    dict(obs="FALTA ANEXO", aplica="ambas", peso=22, subsanable=True,
         detalle="La DJ se envió sin su anexo.",
         pasos="1. Ubicar el anexo de la DJ. 2. Enviar la DJ y su anexo juntos en un mismo documento."),
    dict(obs="DJ MODIFICADA", aplica="ambas", peso=12, subsanable=True,
         detalle="La información impresa de la DJ fue cambiada a mano o con otro programa.",
         pasos="1. Volver a generar la DJ en el aplicativo. 2. Imprimirla sin cambios. 3. Firmarla y enviarla."),
    dict(obs="FORMATO DISTINTO AL DEL APLICATIVO", aplica="ambas", peso=12, subsanable=True,
         detalle="La DJ no tiene el formato que genera el aplicativo.",
         pasos="1. Descargar la DJ desde el aplicativo. 2. Imprimirla tal como se genera, sin editarla. 3. Firmarla y enviarla."),
    dict(obs="DOCUMENTO ILEGIBLE", aplica="ambas", peso=14, subsanable=True,
         detalle="El escaneo de la DJ no se puede leer completo.",
         pasos="1. Escanear la DJ de nuevo, con buena resolución y sin cortes. 2. Revisar que se lea antes de enviarla."),
    dict(obs="SOLICITUD DESESTIMADA", aplica="ambas", peso=4, subsanable=False,
         detalle="La solicitud ya fue desestimada y el sistema no permite evaluarla otra vez.",
         pasos="No es subsanable. La ULE debe informar al hogar que su solicitud fue desestimada."),
    dict(obs="SIN SUSTENTO DE REEVALUACIÓN", aplica="reevaluacion", peso=15, subsanable=True,
         detalle="La DJ de reevaluación no indica el motivo que justifica la solicitud.",
         pasos="1. Completar el motivo de la reevaluación. 2. Adjuntar el documento que lo sustenta. 3. Enviar ambos."),
    dict(obs="NO CUMPLE CRITERIOS DE REEVALUACIÓN", aplica="reevaluacion", peso=7, subsanable=False,
         detalle="El hogar no cumple los criterios para solicitar la reevaluación de su CSE.",
         pasos="No es subsanable. La ULE debe informar al hogar que no cumple los criterios de reevaluación."),
]

# Notas de ejemplo para la columna OBSERVACIÓN (particularidades del expediente)
NOTAS_OTRO = [
    "El expediente no adjunta DJ; solo contiene un oficio de consulta.",
    "Las DJ corresponden a otra municipalidad.",
    "Expediente duplicado: las mismas DJ se enviaron en un expediente anterior.",
    "El archivo adjunto está dañado y no se puede abrir.",
]
NOTAS_PARTICULARES = [
    "La ULE envió las DJ en dos correos distintos.",
    "Se atendió de forma prioritaria a pedido de la coordinación territorial.",
    "La ULE envió una DJ de más, que no figura en su oficio.",
]

rng = np.random.default_rng(SEMILLA)
DIAS = pd.bdate_range(INICIO, CORTE)


def dia_habil(fecha, dias):
    """Suma días hábiles (de lunes a viernes)."""
    return fecha + pd.offsets.BDay(int(dias))


def viernes_siguiente(fecha):
    """Las RSE de ejemplo se publican los viernes."""
    return fecha + pd.offsets.Week(weekday=4)


def fmt(fecha):
    """Escribe la fecha como en las matrices: dd/mm/aaaa."""
    return fecha.strftime("%d/%m/%Y")


def ya_paso(fecha):
    return fecha <= CORTE


def marcar_pendiente(fila, columnas):
    fila.update(dict.fromkeys(columnas, PENDIENTE))


def elegir_ules():
    renamu = pd.read_csv(RENAMU, dtype={"Ubigeo": str})
    munis = renamu[renamu["anio"] == 2026][["Ubigeo", "Departamento", "Provincia", "Distrito"]]
    munis = munis.assign(Ubigeo=munis["Ubigeo"].str.zfill(6)).drop_duplicates("Ubigeo")

    demo = munis[munis["Ubigeo"].isin(ULE_DEMO)].copy()
    # Se sortea la misma parte de cada departamento, para que el mapa tenga datos en todo el país
    otras = (munis[~munis["Ubigeo"].isin(ULE_DEMO)]
             .groupby("Departamento", group_keys=False)
             .sample(frac=FRACCION_ULE, random_state=SEMILLA))
    otras["n"] = 1 + rng.poisson(rng.lognormal(0.4, 0.8, len(otras)))
    demo["n"] = demo["Ubigeo"].map(ULE_DEMO)
    ules = pd.concat([demo, otras])

    # Qué tan seguido observan a cada ULE: unas casi nunca, otras muy seguido
    ules["p_obs"] = rng.beta(2, 5, len(ules))
    ules.loc[ules["Ubigeo"].isin(ULE_DEMO), "p_obs"] = 0.45

    # Cada coordinador ficticio atiende un grupo de departamentos
    deptos = sorted(munis["Departamento"].unique())
    grupos = np.array_split(np.array(deptos), N_COORDINADORES)
    coordinador = {d: f"COORDINADOR(A) {chr(65 + i)}" for i, g in enumerate(grupos) for d in g}
    ules["coordinador"] = ules["Departamento"].map(coordinador)
    return ules


def sortear_observaciones(tipo):
    """Devuelve las DJ observadas de un expediente: (tipo de DJ, N° DJ, criterio)."""
    observadas = []
    for _ in range(min(rng.geometric(0.5), 5)):
        tipo_dj = tipo if tipo != "MIXTO" else rng.choice(["DETERMINACIÓN", "REEVALUACION"])
        candidatos = [c for c in CRITERIOS if c["aplica"] == "ambas" or tipo_dj == "REEVALUACION"]
        pesos = np.array([c["peso"] for c in candidatos], dtype=float)
        n_criterios = 1 if rng.random() < 0.8 else 2
        elegidos = rng.choice(len(candidatos), size=n_criterios, replace=False, p=pesos / pesos.sum())
        n_dj = f"DJ-{rng.integers(1, 10**6):06d}"
        observadas += [(tipo_dj, n_dj, candidatos[i]) for i in elegidos]
    return observadas


def armar_expediente(base):
    """Llena una fila de la matriz 1 siguiendo el recorrido del expediente."""
    f_exp = base["f_exp"]
    f_der = dia_habil(f_exp, rng.integers(0, 4))
    f_asig = dia_habil(f_der, rng.integers(0, 6))
    f_eval = dia_habil(f_asig, rng.integers(1, 7))

    adjunta = rng.random() < 0.25
    if rng.random() < 0.04:
        donde = "OTRO"
    elif adjunta:
        donde = "FIRMA DIGITAL" if rng.random() < 0.6 else "EVALUACIÓN Y FIRMA DIGITAL"
    else:
        donde = "EVALUACIÓN"
    tipo = rng.choice(["DETERMINACIÓN", "REEVALUACION", "MIXTO"], p=[0.6, 0.32, 0.08])

    fila = dict.fromkeys(COLUMNAS, "")
    fila.update({
        "N°": base["N°"], "EXPEDIENTE": base["EXPEDIENTE"], "UBIGEO": base["Ubigeo"],
        "DEPARTAMENTO": base["Departamento"], "PROVINCIA": base["Provincia"],
        "DISTRITO": base["Distrito"], "FECHA EXPEDIENTE": fmt(f_exp),
        "¿ADJUNTA DJ FIRMADAS DIGITALMENTE?": "SÍ" if adjunta else "NO",
        "TIPO DE SOLICITUDES": tipo, "COORDINADOR TERRITORIAL": base["coordinador"],
    })
    fila["FECHA DERIVACIÓN"] = fmt(f_der) if ya_paso(f_der) else PENDIENTE
    if ya_paso(f_asig):
        fila["FECHA DE ASIGNACIÓN PARA SU ATENCIÓN"] = fmt(f_asig)
        fila["¿DÓNDE SE PROCESÓ?"] = donde
    else:
        marcar_pendiente(fila, ["FECHA DE ASIGNACIÓN PARA SU ATENCIÓN", "¿DÓNDE SE PROCESÓ?"])
    if not ya_paso(f_eval):  # todavía en evaluación
        marcar_pendiente(fila, ETAPA_EVALUACION + ETAPA_COMUNICACION)
        return fila, []

    observadas = []
    comunicacion = None
    if donde in ("FIRMA DIGITAL", "OTRO"):
        # Las DJ firmadas digitalmente ya tienen resultado: no se evalúan aquí
        fila.update({"RESULTADO DE EVALUACIÓN": "-", "FECHA DE ENVÍO DE CORREO": "-",
                     "ESTADO DE SUBSANACIÓN": "-", "FECHA DE SUBSANACIÓN": "-"})
        if donde == "FIRMA DIGITAL":
            comunicacion, f_com = "CORREO", dia_habil(f_eval, rng.integers(0, 3))
        else:
            fila["OBSERVACIÓN"] = rng.choice(NOTAS_OTRO)
            comunicacion = "OFICIO" if rng.random() < 0.75 else "CASO ESPECIAL"
            f_com = dia_habil(f_eval, rng.integers(1, 6))
    elif rng.random() >= base["p_obs"]:
        fila.update({"RESULTADO DE EVALUACIÓN": "CONFORME", "FECHA DE ENVÍO DE CORREO": "NO REQUIERE",
                     "ESTADO DE SUBSANACIÓN": "NO REQUIERE", "FECHA DE SUBSANACIÓN": "NO REQUIERE"})
        comunicacion = rng.choice(["RSE", "RSE Y CORREO", "CORREO"], p=[0.4, 0.4, 0.2])
        f_com = f_eval
    else:
        fila.update({"RESULTADO DE EVALUACIÓN": "OBSERVADO", "FECHA DE ENVÍO DE CORREO": fmt(f_eval)})
        observadas = sortear_observaciones(tipo)
        f_sub = dia_habil(f_eval, rng.integers(2, 31))
        if not all(c["subsanable"] for _, _, c in observadas):
            fila.update({"ESTADO DE SUBSANACIÓN": "NO PROCEDE", "FECHA DE SUBSANACIÓN": "-"})
            comunicacion, f_com = "OFICIO", dia_habil(f_eval, rng.integers(2, 7))
        elif rng.random() > 0.12 and ya_paso(f_sub):
            fila.update({"ESTADO DE SUBSANACIÓN": "SUBSANADO", "FECHA DE SUBSANACIÓN": fmt(f_sub)})
            comunicacion = rng.choice(["RSE", "RSE Y CORREO"])
            f_com = dia_habil(f_sub, rng.integers(1, 6))
        else:  # la ULE aún no subsana
            fila.update({"ESTADO DE SUBSANACIÓN": "OBSERVADA", "FECHA DE SUBSANACIÓN": PENDIENTE})

    if comunicacion and "RSE" in comunicacion:
        f_com = viernes_siguiente(f_com)
    if not comunicacion or not ya_paso(f_com):
        marcar_pendiente(fila, ETAPA_COMUNICACION)
    else:
        fila["¿CÓMO SE COMUNICÓ A LA ULE EL RESULTADO?"] = comunicacion
        if "RSE" in comunicacion:
            fila["N° RSE"] = f"{f_com.isocalendar().week:04d}-2026"
            fila["FECHA DE PUBLICACIÓN DE RSE"] = fmt(f_com)
        if comunicacion == "OFICIO":
            fila["FECHA DEL OFICIO"] = fmt(f_com)
        if comunicacion in ("CORREO", "RSE Y CORREO"):
            fila["FECHA ENVÍO DEL CORREO"] = fmt(f_com)

    if not fila["OBSERVACIÓN"] and rng.random() < 0.04:
        fila["OBSERVACIÓN"] = rng.choice(NOTAS_PARTICULARES)
    return fila, observadas


def main():
    ules = elegir_ules()
    base = ules.loc[ules.index.repeat(ules["n"])].reset_index(drop=True)
    base["f_exp"] = rng.choice(DIAS, len(base))
    # Las ULE de prueba reciben expedientes en todo el año, hasta la última semana
    for ubigeo in ULE_DEMO:
        filas_demo = base.index[base["Ubigeo"] == ubigeo]
        posiciones = np.linspace(0, len(DIAS) - 1, len(filas_demo)).round().astype(int)
        base.loc[filas_demo, "f_exp"] = DIAS[posiciones]
    base = base.sort_values("f_exp", kind="stable").reset_index(drop=True)
    base["N°"] = base.index + 1
    base["EXPEDIENTE"] = [f"EXP-2026-{n:05d}" for n in base["N°"]]

    filas, obs = [], {"DETERMINACIÓN": [], "REEVALUACION": []}
    for _, b in base.iterrows():
        fila, observadas = armar_expediente(b)
        filas.append(fila)
        for tipo_dj, n_dj, c in observadas:
            obs[tipo_dj].append([fila["UBIGEO"], fila["EXPEDIENTE"], n_dj,
                                 c["obs"], c["detalle"], c["pasos"]])
    expedientes = pd.DataFrame(filas, columns=COLUMNAS)

    # Los oficios se numeran en orden de fecha
    con_oficio = ~expedientes["FECHA DEL OFICIO"].isin(["", PENDIENTE])
    orden = pd.to_datetime(expedientes.loc[con_oficio, "FECHA DEL OFICIO"], dayfirst=True)
    numeros = orden.rank(method="first").astype(int)
    expedientes.loc[con_oficio, "N° OFICIO"] = [f"{n:05d}-2026" for n in numeros]

    SALIDA.mkdir(exist_ok=True)
    expedientes.to_csv(SALIDA / "expedientes.csv", index=False)
    pd.DataFrame(obs["DETERMINACIÓN"], columns=COLUMNAS_OBS).to_csv(
        SALIDA / "observaciones_determinacion.csv", index=False)
    pd.DataFrame(obs["REEVALUACION"], columns=COLUMNAS_OBS).to_csv(
        SALIDA / "observaciones_reevaluacion.csv", index=False)

    print(f"Expedientes: {len(expedientes)} de {expedientes['UBIGEO'].nunique()} ULE "
          f"en {expedientes['DEPARTAMENTO'].nunique()} departamentos")
    print(f"DJ observadas: {len(obs['DETERMINACIÓN'])} de determinación y {len(obs['REEVALUACION'])} de reevaluación")
    print(expedientes["RESULTADO DE EVALUACIÓN"].value_counts().to_string())


if __name__ == "__main__":
    main()