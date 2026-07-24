"""
Caja de herramientas compartida por los scripts de transform/*.py

El pipeline Bronze -> Silver se apoya en tres frentes de limpieza que se
repiten en todas las fuentes:
  a) Formatos mal tipados (texto que deberia ser numero o fecha)
  b) Registros repetidos
  c) Vacios / valores faltantes

Todas las funciones de este modulo son puras (no leen ni escriben archivos)
para poder testearlas de forma aislada.
"""
import unicodedata
import re
import pandas as pd


def convertir_numero(columna: pd.Series) -> pd.Series:
    """Castea una columna a numerico tolerando texto sucio (separadores de
    miles, simbolos de moneda, espacios). Todo lo que no sea digito, coma,
    punto o signo negativo se descarta antes de convertir."""
    texto = columna.astype(str).str.strip()
    texto = texto.str.replace(r"[^0-9,.\-]", "", regex=True)
    return pd.to_numeric(texto, errors="coerce")


def convertir_fecha(columna: pd.Series, formato_dia_primero: bool = False) -> pd.Series:
    """Normaliza una columna de fechas heterogenea (texto, datetime, celda de
    Excel) a un pandas.Timestamp. La exportacion final a AAAA-MM-DD se hace
    aparte con .dt.strftime cuando corresponda."""
    return pd.to_datetime(columna, errors="coerce", dayfirst=formato_dia_primero)


def extraer_anio(columna: pd.Series) -> pd.Series:
    """Rescata el anio (4 digitos) de celdas ruidosas como '2025(Prev)' o
    '2024 (prel)'."""
    return columna.astype(str).str.extract(r"(\d{4})")[0].astype("Int64")


def normalizar_texto(columna: pd.Series) -> pd.Series:
    """Estandar de texto para campos categoricos (nombres, provincias, etc.):
    recorta espacios, colapsa espacios dobles y pasa todo a mayusculas.
    Las variantes vacias o literales 'nan'/'none' quedan como nulo real."""
    limpio = columna.astype(str).str.strip()
    limpio = limpio.str.replace(r"\s+", " ", regex=True).str.upper()
    return limpio.replace({"NAN": None, "NONE": None, "": None})


def quitar_tildes(columna: pd.Series) -> pd.Series:
    """Elimina diacriticos, pensado para emparejar provincias/cantones que
    llegan con distinta ortografia entre fuentes."""
    def _sin_tilde(valor):
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return valor
        descompuesto = unicodedata.normalize("NFKD", str(valor))
        return "".join(ch for ch in descompuesto if not unicodedata.combining(ch))
    return columna.map(_sin_tilde)


def eliminar_duplicados_log(tabla: pd.DataFrame, claves=None, etiqueta: str = "") -> pd.DataFrame:
    """Quita duplicados (se conserva la ultima ocurrencia) y deja constancia
    en consola de cuantas filas se perdieron, como bitacora de decisiones."""
    total_inicial = len(tabla)
    tabla = tabla.drop_duplicates(subset=claves, keep="last")
    total_final = len(tabla)
    diferencia = total_inicial - total_final
    if diferencia:
        print(f"[{etiqueta}] filas duplicadas descartadas: {diferencia} -> quedan {total_final}")
    return tabla


def resumen_nulos(tabla: pd.DataFrame, etiqueta: str = "") -> None:
    """Deja impreso, columna por columna, cuantos vacios quedaron tras la
    limpieza (solo informativo, no modifica el DataFrame)."""
    conteo = tabla.isna().sum()
    conteo = conteo[conteo > 0]
    if conteo.empty:
        print(f"[{etiqueta}] no quedaron valores nulos.")
    else:
        print(f"[{etiqueta}] valores nulos detectados:\n{conteo.to_string()}")
