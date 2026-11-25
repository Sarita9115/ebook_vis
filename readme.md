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
| `figures/` | Producción | La función que construye el `go.Figure`. La web y el PDF importan esta función. |
| `app/pages/` | Producción, con la plantilla | La página de la aplicación. No redibuja la figura: la importa de `figures/`. |
| `pipelines/` | Producción | La limpieza que deja la tabla de oro de cada subtema. |
| `dags/` | Producción | Un proceso por equipo: ingesta, plata, oro, validación y catálogo. |
| `catalog/` | Producción, con los datos de cada equipo | Fuentes, papel de primaria o secundaria, fecha, responsable, valor de referencia y si la fuente va en streaming. |
| `ebook/` | Producción | El libro. Exporta la misma función de `figures/` a imagen. |
| `docs/` | Producción | Los dos documentos de acuerdo. Aquí no van gráficas. |

Los archivos crudos no viven en este repositorio. La copia de trabajo de cada quien va en `datos/{equipo}/`, y la copia compartida sigue en la carpeta de Drive del curso. La gráfica no apunta a esa carpeta: recibe la tabla de oro en el argumento `datos`.

## Del archivo crudo a la figura

Hay tres piezas distintas. El pipeline prepara la tabla. El DAG la manda a correr. La figura solo dibuja.

### Qué es un pipeline

El pipeline es el código de `pipelines/{equipo}/`. Limpia y publica. No dibuja.

Son tres pasos, siempre en este orden. Cada uno deja el resultado en un lugar distinto.

1. **Ingesta.** Copia el archivo crudo, sin transformarlo, a MinIO, bucket `bronze`. La función se llama `ingerir()`. En el equipo 4 está en `pipelines/4/ingesta.py`: lee `datos/4/` (y descarga dos zip de INEGI) y los deja como objetos `bronze/4/<archivo>`.
2. **Plata.** Lee ese bronce, limpia tipos, nombres y textos, y escribe tablas en PostgreSQL, esquema `plata`. La función se llama `construir()`, en `pipelines/{equipo}/plata.py`.
3. **Oro.** Lee plata y deja una tabla por subtema en el esquema `oro`. El nombre de la tabla es el `viz_id`, por ejemplo `oro."4.ied_por_pais"`. `construir()` las publica todas. `leer(viz_id)` lee una. En el equipo 4 está en `pipelines/4/oro.py`.

Lo restringido va al bucket `bronze-restringido`. El ráster va al bucket `raster`. Las tablas de las figuras viven en la base `vis`. Airflow usa otra base, `airflow`, en el mismo PostgreSQL: ahí guarda sus corridas, no los datos de las gráficas.

Hoy solo el equipo 4 tiene las tres funciones. Los equipos 1, 2, 3 y 6 arman su tabla leyendo una carpeta local (`construir_oro` o la función equivalente de ese subtema) y esa tabla es el `datos` de la figura. El equipo 5 todavía no tiene carpeta `pipelines/5/`.

### Qué es un DAG y dónde entra

Un DAG es el proceso que Airflow ejecuta para un equipo. El archivo es `dags/equipo_{n}.py` y dentro de Airflow se llama `equipo_{n}`. No guarda datos: llama a los scripts del pipeline, en este orden.

```text
ingesta → plata → oro → validacion → catalogo
```

Con `docker compose up`, Airflow monta `dags/` en `/opt/airflow/dags` y `pipelines/` en `/opt/airflow/pipelines`. La interfaz queda en http://localhost:8080, usuario `admin`. Disparar `equipo_4` corre `ingerir()` y después `construir()` de plata y de oro, cada una en un entorno virtual propio (Airflow trae SQLAlchemy 1.4 y los pipelines usan la 2). `validacion` y `catalogo` siguen vacías.

`equipo_1.py`, `equipo_2.py`, `equipo_3.py`, `equipo_5.py` y `equipo_6.py` tienen la misma cadena, pero cada tarea está vacía. Airflow la marca terminada y no lee archivos. Subir un archivo a MinIO no dispara esos procesos.

### Dónde se conecta cada ruta

| Qué | Ruta |
| --- | --- |
| Archivo de trabajo, fuera de Git | `datos/{equipo}/` en tu máquina. La copia compartida está en Drive. |
| Bronce | MinIO, objeto `bronze/{equipo}/<archivo>`. El equipo 4 usa el prefijo `4/`. |
| Plata y oro | PostgreSQL, base `vis`, tablas `plata."<nombre>"` y `oro."<viz_id>"`. |
| Figura | `figures/{equipo}/{subtema}/figura.py`, función `figura(datos)`. `datos` es la tabla de oro. Esta función no abre MinIO ni PostgreSQL. |
| Página del equipo 4 | `/4`, en `app/pages/4/historia.py`. Llama a `pipelines/4/oro.py` → `leer("4.<subtema>")` y pasa esa tabla a `figura`. |
| Páginas del equipo 6 | `/6/gasto_publico`, `/6/cambio_suelo`, `/6/corredor_industrial`, `/6/relieve_5m`, `/6/huella_construida`. `app/pages/6/_e6.py` lee `oro."6.<subtema>"` si existe la variable `ORO_DB_URL`. Si no, usa un parquet de prueba en `local_avances/`. |
| Menú | `/`, en `app/pages/inicio.py`. Los capítulos y el destino de cada vínculo están en `app/recorrido.py`. |
| Subtema sin página | `/v/{equipo}/{subtema}`, la ficha de `app/pages/subtema.py`. El vínculo ya existe; la figura todavía no. |

El PDF importa la misma `figura(datos)`. No tiene ruta en la web.

## Visualizaciones

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

El equipo 3, por ejemplo, deja un censo en `bronze/3/censo_2020/fecha=2026-11-19/`. Lo restringido va a `bronze-restringido`, con la misma forma de ruta. El ráster va al bucket `raster`. El pipeline que ya corre, el del equipo 4, no usa esa partición por fecha: `ingesta.py` escribe y `plata.py` lee objetos `bronze/4/<archivo>`, con el nombre del archivo de `datos/4/`.

Ese MinIO es local: cada quien ve solo lo que subió en su Docker. El lugar compartido sigue siendo la carpeta de Drive del curso. Solo el DAG `equipo_4` lee el bronce y publica plata y oro. En los otros cinco, ingesta, plata y oro están vacías, así que subir el archivo no dispara el proceso. La figura tampoco abre MinIO: recibe la tabla en `datos`.

## Qué no entra en Git

No subas ráster, nubes de puntos, CSV, XLS, XLSX ni directorios masivos. Esos archivos viven en el datalake. En este repositorio van el módulo de la figura, la página y el catálogo. `catalog/catalog.csv` sí se versiona; cualquier otro CSV no.

## Antes de avisar que está lista

1. La función está en `figures/{equipo}/{subtema}/figura.py` y la página importa esa función.
2. La figura sale de la tabla de oro, con su `viz_id`.
3. La primaria de este subtema no está usada por otra visualización de tu equipo.
4. La secundaria está indicada.
5. El título de la figura es el del subtema.
6. Si tu equipo todavía no tiene fuente en streaming, esta puede ser esa fuente y queda marcada en el catálogo.

