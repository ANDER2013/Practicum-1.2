"""
rpa_adapters.py
Reglas de limpieza por indicador, sobre los DataFrames de
rpa_parser.a_dataframes() / rpa_parser.iterar_registros_indicador().
"""
from __future__ import annotations
import pandas as pd


def limpiar_vab_rpa(df_vab: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza del indicador VAB_CANTONAL_CIIU proveniente del RPA
    (archivo tab_consolidado_export.sql).

    Regla 1 (gestion de nulos reales): 'anio' llega null en parte de
    las filas (marcadas por el RPA con DATO_CLAVE='SIN_ANIO_...').
    Este adaptador NO las descarta -> las deja con anio=NaN para que
    la etapa de verificacion/carga cuente y reporte cuantas se excluyen
    antes de insertar en fact_valor_agregado.
    """
    df = df_vab.copy()

    df["anio"] = pd.to_numeric(df.get("anio"), errors="coerce").astype("Int64")
    df["codigo_provincia"] = df.get("codigo_provincia")
    df["codigo_canton"] = df.get("codigo_canton")

    for col in ("provincia", "canton"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    columnas_sector = [c for c in df.columns if c.startswith("sectores_")]
    for col in columnas_sector:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    columnas_finales = (
        ["id", "dato_clave", "anio", "codigo_provincia", "provincia",
         "codigo_canton", "canton"]
        + columnas_sector
        + ["fuente", "ruta_logica"]
    )
    columnas_finales = [c for c in columnas_finales if c in df.columns]

    return df[columnas_finales].reset_index(drop=True)


def limpiar_ranking_rpa(df_ranking: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza del indicador SUPERCIAS_RANKING proveniente del RPA
    (archivo tab_consolidado_supercias.sql).

    - ANIO y EXPEDIENTE se normalizan a numerico (identifican empresa/periodo).
    - POSICION_GENERAL es la posicion de ranking ya calculada por la fuente;
      se conserva tal cual llega (puede ser nula en registros historicos
      2008-2011 que no tenian ranking asignado en ese periodo).
    - Se eliminan duplicados por (ANIO, EXPEDIENTE) quedandose con el
      primero, para evitar doble conteo si el dump tiene una fila repetida.
    """
    df = df_ranking.copy()

    df["ANIO"] = pd.to_numeric(df.get("ANIO"), errors="coerce").astype("Int64")
    df["EXPEDIENTE"] = pd.to_numeric(df.get("EXPEDIENTE"), errors="coerce").astype("Int64")
    df["POSICION_GENERAL"] = pd.to_numeric(df.get("POSICION_GENERAL"), errors="coerce").astype("Int64")

    columnas_numericas = [
        "PATRIMONIO", "ACTIVOS", "INGRESOS_VENTAS", "INGRESOS_TOTALES",
        "UTILIDAD_NETA", "UTILIDAD_EJERCICIO", "UTILIDAD_AN_IMP",
        "ROE", "ROA", "N_EMPLEADOS", "IMPUESTO_RENTA",
    ]
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    antes = len(df)
    df = df.drop_duplicates(subset=["ANIO", "EXPEDIENTE"], keep="first")
    duplicados_eliminados = antes - len(df)
    if duplicados_eliminados:
        print(f"[limpiar_ranking_rpa] Duplicados (ANIO+EXPEDIENTE) eliminados: {duplicados_eliminados}")

    columnas_finales = (
        ["id", "dato_clave", "ANIO", "EXPEDIENTE", "POSICION_GENERAL",
         "CIIU_N1", "CIIU_N6"]
        + columnas_numericas
    )
    columnas_finales = [c for c in columnas_finales if c in df.columns]

    return df[columnas_finales].reset_index(drop=True)
