# Practicum 1.2 - Reto Final: Macroentorno Economico Ecuador

Pipeline automatizado (RPA) de extraccion, transformacion, carga y analisis de datos del macroentorno economico del Ecuador. Integra fuentes oficiales del Banco Central del Ecuador (BCE), Ministerio de Educacion (MINEDUC) y Superintendencia de Companias, Valores y Seguros (SUPERCIAS).

## Descripcion

El proyecto construye un flujo de datos por capas (arquitectura Bronze-Silver-Gold) que automatiza la limpieza, normalizacion, consolidacion y generacion de reportes analiticos a partir de archivos crudos entregados por las instituciones fuente.

## Arquitectura del pipeline

Bronze (datos crudos .xlsx) -> Silver (datos limpios .csv) -> SQLite (base consolidada) -> Reportes (CSV finales)

## Fuentes de datos

| Fuente | Archivos procesados | Contenido |
|--------|---------------------|-----------|
| BCE | VAB, PIB, IEE, Petroleo, Riesgo Pais | Indicadores macroeconomicos nacionales |
| MINEDUC | Historico de matriculas | Estudiantes por provincia y nivel educativo |
| SUPERCIAS | Directorio de companias | Empresas registradas por provincia (217,000+ registros) |

## Estructura del proyecto

- pipeline.py : Punto de entrada unico del proyecto
- requirements.txt
- codigo_fuente/transform/bce.py : Procesa PIB, VAB, IEE, Petroleo, Riesgo Pais
- codigo_fuente/transform/mineduc.py : Procesa datos educativos
- codigo_fuente/transform/supercias.py : Procesa directorio de companias
- codigo_fuente/transform/common.py : Funciones compartidas de limpieza
- datos_macroentorno/bronze/ : Datos originales por fuente
- datos_macroentorno/rpa/rpa_macroentorno.py : Logica completa del pipeline RPA
- datos_macroentorno/rpa_silver/ : CSV limpios generados
- datos_macroentorno/rpa_db/ : Base de datos SQLite consolidada (no versionada)
- datos_macroentorno/rpa_reportes/ : Reportes analiticos finales
- documentacion/capturas_presentacion/ : Evidencia del proceso de desarrollo

## Instalacion y ejecucion

Instalar dependencias: pip install -r requirements.txt
Ejecutar el pipeline: python pipeline.py

El pipeline ejecuta automaticamente 6 etapas:

1. Creacion de directorios de trabajo
2. Procesamiento de datos BCE (5 archivos)
3. Procesamiento de datos MINEDUC
4. Procesamiento de datos SUPERCIAS
5. Carga consolidada en base de datos SQLite
6. Generacion de 6 reportes analiticos

## Reportes generados

- Resumen general de tablas cargadas
- VAB (Valor Agregado Bruto) por provincia
- Numero de empresas por provincia
- Numero de estudiantes por provincia
- Indicadores macroeconomicos (PIB, IEE, Petroleo, Riesgo Pais)
- Perfil provincial combinado (cruce de las tres fuentes)

## Visualizacion

Los reportes se consumen desde un dashboard de Power BI organizado en tres paginas:

- P1 - Panorama Macroeconomico: PIB, IEE, Petroleo, Riesgo Pais
- P2 - Analisis Provincial: VAB, empresas y estudiantes por provincia
- P3 - Perfil Provincial: vista integrada por provincia seleccionada

## Requisitos

- Python 3.13+
- pandas
- openpyxl

## Notas

Los archivos SQL originales de SUPERCIAS (mayores a 2GB) y las bases de datos generadas no se incluyen en el repositorio por su tamano; se generan automaticamente al ejecutar el pipeline.
