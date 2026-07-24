"""
rpa_parser.py
Parsea los archivos .sql del RPA (dump Oracle, tabla TAB_CONSOLIDADO
en formato EAV). Soporta DATOS_JSON codificado una vez o dos veces,
y lectura eficiente linea por linea para archivos grandes (GB).
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Iterator
import pandas as pd

_INSERT_RE = re.compile(
    r"Insert\s+into\s+TAB_CONSOLIDADO\s*"
    r"\(ID,INDICADOR,FECHA_EXTRACCION,ESTADO,NECESITA_RESPALDO,"
    r"DETALLE_ERROR,DATOS_JSON,DATO_CLAVE,HASH_CONTENIDO\)\s*"
    r"values\s*\(\s*"
    r"'(?P<id>\d+)'\s*,\s*"
    r"'(?P<indicador>[^']*)'\s*,\s*"
    r"to_date\('[^']*'\s*,\s*'[^']*'\)\s*,\s*"
    r"'(?P<estado>[^']*)'\s*,\s*"
    r"'(?P<necesita_respaldo>[^']*)'\s*,\s*"
    r"(?:null|'(?P<detalle_error>[^']*)')\s*,\s*"
    r"'(?P<datos_json>[^']*)'\s*,\s*"
    r"'(?P<dato_clave>[^']*)'\s*,\s*"
    r"'(?P<hash_contenido>[^']*)'\s*"
    r"\)\s*;",
    re.IGNORECASE,
)


def _decodificar_datos_json(crudo: str) -> dict[str, Any]:
    primero = json.loads(crudo)
    if isinstance(primero, str):
        return json.loads(primero)
    return primero


def parsear_dump_oracle(ruta_sql: str) -> list[dict[str, Any]]:
    texto = Path(ruta_sql).read_text(encoding="utf-8", errors="replace")
    registros: list[dict[str, Any]] = []
    errores_json = 0

    for match in _INSERT_RE.finditer(texto):
        campos = match.groupdict()
        try:
            datos = _decodificar_datos_json(campos["datos_json"])
        except (json.JSONDecodeError, TypeError):
            errores_json += 1
            datos = {}

        registros.append({
            "id": int(campos["id"]),
            "indicador": campos["indicador"],
            "estado": campos["estado"],
            "necesita_respaldo": campos["necesita_respaldo"],
            "detalle_error": campos.get("detalle_error"),
            "dato_clave": campos["dato_clave"],
            "hash_contenido": campos["hash_contenido"],
            "datos": datos,
        })

    if errores_json:
        print(f"[rpa_parser] Advertencia: {errores_json} filas con DATOS_JSON no decodificable.")

    return registros


def iterar_registros_indicador(ruta_sql: str, indicador: str) -> Iterator[dict[str, Any]]:
    filtro = f"'{indicador}'"
    errores_json = 0
    total_lineas_filtro = 0

    with open(ruta_sql, encoding="utf-8", errors="replace") as f:
        for linea in f:
            if filtro not in linea:
                continue
            total_lineas_filtro += 1
            match = _INSERT_RE.search(linea)
            if not match:
                continue
            campos = match.groupdict()
            if campos["indicador"] != indicador:
                continue
            try:
                datos = _decodificar_datos_json(campos["datos_json"])
            except (json.JSONDecodeError, TypeError):
                errores_json += 1
                datos = {}

            yield {
                "id": int(campos["id"]),
                "dato_clave": campos["dato_clave"],
                "estado": campos["estado"],
                **datos,
            }

    if errores_json:
        print(f"[rpa_parser] Advertencia: {errores_json} filas de '{indicador}' con DATOS_JSON no decodificable.")
    print(f"[rpa_parser] Lineas que contenian '{filtro}': {total_lineas_filtro}")


def a_dataframes(registros: list[dict[str, Any]]) -> dict[str, pd.DataFrame]:
    por_indicador: dict[str, list[dict[str, Any]]] = {}
    for reg in registros:
        por_indicador.setdefault(reg["indicador"], []).append(reg)

    resultado: dict[str, pd.DataFrame] = {}
    for indicador, filas in por_indicador.items():
        base = pd.DataFrame([
            {"id": f["id"], "dato_clave": f["dato_clave"], "estado": f["estado"]}
            for f in filas
        ])
        datos_planos = pd.json_normalize([f["datos"] for f in filas], sep="_")
        df = pd.concat([base.reset_index(drop=True), datos_planos.reset_index(drop=True)], axis=1)
        resultado[indicador] = df

    return resultado
