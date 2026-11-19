# Los aluxes del Mayab

Repositorio de las figuras del ebook y de la aplicación web. Este archivo es para quien va a construir una gráfica.

La web y el PDF usan la misma figura. Tú escribes esa figura una sola vez, en Plotly, y la dejas en `figures/`. Producción coloca la página y exporta el PDF.

Los acuerdos completos están en [docs/requerimientos-del-cliente.md](docs/requerimientos-del-cliente.md) y [docs/arquitectura-propuesta.md](docs/arquitectura-propuesta.md).

## Estructura del repositorio

```text
ebook_vis/
├── readme.md
├── docker-compose.yml     PostgreSQL, MinIO y Airflow
├── requirements.txt       librerías de las figuras y los pipelines
├── docs/                  requerimientos y arquitectura
├── figures/{equipo}/{subtema}/figura.py
├── app/pages/{equipo}/    la página que muestra esa figura
├── pipelines/{equipo}/    el paso de los archivos a la tabla de oro
├── dags/equipo_{n}.py     el proceso de Airflow de cada equipo
├── catalog/catalog.csv    el inventario de fuentes
└── ebook/                 el proyecto Quarto que arma el PDF
```

`{equipo}` es el número del equipo, del 1 al 6. `{subtema}` es el nombre de la carpeta. El `viz_id` es `{equipo}.{subtema}`, el mismo identificador del catálogo. Cada carpeta de `figures/` ya existe y trae `figura.py`.

| Carpeta | Quién la escribe | Qué hay dentro |
| --- | --- | --- |
| `figures/` | Quien hace la gráfica | La función que construye el `go.Figure`. La web y el PDF importan esta función. |
| `app/pages/` | Producción, con la plantilla | La página de la aplicación. No redibuja la figura: la importa de `figures/`. |
| `pipelines/` | Producción | La limpieza que deja la tabla de oro de cada subtema. |
| `dags/` | Producción | Un proceso por equipo: ingesta, plata, oro, validación y catálogo. |
| `catalog/` | Producción, con los datos de cada equipo | Fuentes, papel de primaria o secundaria, fecha, responsable, valor de referencia y si la fuente va en streaming. |
| `ebook/` | Producción | El libro. Exporta la misma función de `figures/` a imagen. |
| `docs/` | Producción | Los dos documentos de acuerdo. Aquí no van gráficas. |

Los archivos crudos no viven en este repositorio. Mientras no exista el datalake, se quedan en la carpeta de Drive del curso, separados por equipo y por conjunto. La gráfica no apunta a esa carpeta: recibe la tabla preparada en `datos`. Cuando MinIO y PostgreSQL estén en Docker, esa misma tabla sale de oro y la función no cambia de ruta.

## Dónde va tu archivo

```text
figures/{equipo}/{subtema}/figura.py
```

`{equipo}` es el número de tu equipo, del 1 al 6. `{subtema}` es la carpeta que ya está creada. El `viz_id` de esa carpeta es `{equipo}.{subtema}`. No abras otra carpeta.

La página de la aplicación vive en `app/pages/{equipo}/`. Esa página no vuelve a dibujar la figura: importa `figura` desde `figures/{equipo}/{subtema}/figura.py` y la pone en la plantilla. El PDF importa la misma función.

## Qué debe devolver tu módulo

Una función que lea la tabla de oro de ese subtema y devuelva un `plotly.graph_objects.Figure`.

```python
import plotly.graph_objects as go

def figura(datos) -> go.Figure:
    fig = go.Figure(...)
    fig.update_layout(title="Título del subtema")
    return fig
```

`datos` es la tabla de oro ya filtrada: la fuente primaria, la fuente secundaria, la institución, la fecha de obtención, el responsable y las columnas de la gráfica. Si la figura es un mapa, la geometría viene en EPSG:4326.

La plantilla, alrededor de tu figura, muestra el título, la lectura breve, la fuente primaria, la fuente secundaria, la fecha de obtención y el responsable del procesamiento. Esos textos salen del catálogo y de oro. No los escribas dentro del PNG.

## Reglas de la figura

- La herramienta de la figura es Plotly. 
- Cada subtema usa una fuente primaria y al menos una secundaria. La primaria no se repite dentro del mismo equipo. La primaria de un subtema puede ser secundaria de otro.
- Cada equipo deja al menos una fuente en streaming. Si el tuyo es ese subtema, la función lee la tabla de oro vigente. La web muestra el dato actual. El PDF guarda la imagen del momento en que se genera.
- Un dato nacional se recorta a Campeche, Yucatán y Quintana Roo antes de entrar en la figura.
- La cifra publicada tiene que coincidir con su fuente, dentro del valor de referencia y la tolerancia registrados en el catálogo.
- Un formulario solo aporta conteos o categorías. La figura no publica información confidencial.
- Los polígonos pesados se simplifican antes de publicarse. El modelo de elevación de 5 m no se envía al navegador: la figura de relieve sale del mapa preparado.
- Un GLB puede acompañar la sección. La figura que se evalúa es la de Plotly.
- La sección de Memoria UPY es una línea de tiempo.



## Para levantar PostgreSQL, MinIO y Airflow

```bash
cd ebook_vis
cp .env.example .env
docker compose up
```

Estos usuarios son solo para esta máquina. Salen de `.env`, que no se versiona.

| Servicio | Dónde | Usuario | Contraseña |
| --- | --- | --- | --- |
| PostgreSQL | puerto 5432, base `vis`, esquemas `plata` y `oro` | `vis` | `vis` |
| MinIO | http://localhost:9001 | `minio` | `minioadmin123` |
| Airflow | http://localhost:8080 | `admin` | `admin` |

MinIO crea los buckets `bronze`, `bronze-restringido` y `raster`.

## Dónde subir los datos para probar

Para probar en tu máquina, sube el archivo a MinIO, en el bucket `bronze`. La consola queda en `http://localhost:9001` después de `docker compose up`. Entra con el usuario `minio` y la contraseña `minioadmin123`.

La ruta es:

```text
bronze/{equipo}/{dataset}/fecha=AAAA-MM-DD/
```

El equipo 3, por ejemplo, deja un censo en `bronze/3/censo_2020/fecha=2026-11-19/`. Lo restringido va a `bronze-restringido`, con la misma forma de ruta. El ráster va al bucket `raster`.

Ese MinIO es local: cada quien ve solo lo que subió en su Docker. El lugar compartido, mientras no haya un servidor, sigue siendo la carpeta de Drive del curso. Los DAG todavía no leen esos archivos: las tareas de ingesta, plata y oro están vacías, así que subir el archivo no dispara el proceso. La figura tampoco abre MinIO. Recibe la tabla en `datos`, y esa función no cambia de ruta cuando `datos` pase a salir de oro.

## Qué no entra en Git

No subas ráster, nubes de puntos, CSV, XLS, XLSX ni directorios masivos. Esos archivos viven en el datalake. En este repositorio van el módulo de la figura, la página y el catálogo. `catalog/catalog.csv` sí se versiona; cualquier otro CSV no.

## Antes de avisar que está lista

1. La función está en `figures/{equipo}/{subtema}/figura.py` y la página importa esa función.
2. La figura sale de la tabla de oro, con su `viz_id`.
3. La primaria de este subtema no está usada por otra visualización de tu equipo.
4. La secundaria está indicada.
5. El título de la figura es el del subtema.
6. Si tu equipo todavía no tiene fuente en streaming, esta puede ser esa fuente y queda marcada en el catálogo.

