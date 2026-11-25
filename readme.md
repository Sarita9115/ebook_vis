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

Los archivos crudos no viven en este repositorio. La copia compartida está en la carpeta de Drive del curso. Producción los deposita en MinIO y, a partir de ahí, el código solo habla con MinIO y con PostgreSQL. La figura recibe la tabla de oro en el argumento `datos`.

## Del archivo crudo a la figura

Hay tres piezas distintas. El pipeline prepara la tabla. El DAG la manda a correr. La figura solo dibuja. Las tres siguen la estructura de este repositorio y los acuerdos de [docs/requerimientos-del-cliente.md](docs/requerimientos-del-cliente.md) y [docs/arquitectura-propuesta.md](docs/arquitectura-propuesta.md).

### Regla para Producción

Quien integra un subtema lo deja funcionando por ese pipeline. El código de `pipelines/`, `dags/` y `app/pages/` no lleva rutas de una máquina: ni `datos/`, ni una carpeta de Drive, ni `local_avances/`, ni una ruta absoluta. Drive solo sirve para recibir el archivo. Producción lo sube al prefijo de bronce del equipo y el DAG hace el resto.

Para dar por cerrada una visualización tienen que cumplirse las cuatro cosas:

1. `pipelines/{equipo}/` tiene ingesta, plata y oro. La ingesta lee el bronce en MinIO, o descarga la fuente y la deja ahí. Plata lee bronce y escribe en el esquema `plata`. Oro lee plata y escribe en el esquema `oro`.
2. `dags/equipo_{n}.py` llama esas funciones, en el orden de la arquitectura: ingesta, plata, oro, validación y catálogo. Una tarea vacía no cuenta como proceso.
3. La página importa `figura` desde `figures/{equipo}/{subtema}/figura.py` y le pasa la tabla `oro."<viz_id>"`. La figura no abre archivos ni bases de datos.
4. La cifra, las fuentes y el valor de referencia quedan en `catalog/catalog.csv` y pasan la validación descrita en la arquitectura.

Una tabla armada a mano, un parquet de prueba o una función que abre una carpeta local puede servir para revisar la gráfica en tu máquina. No es la entrega. Al correr el DAG con Docker, en una máquina que no tenga esa carpeta, la misma figura tiene que salir de oro.

### Qué es un pipeline

El pipeline es el código de `pipelines/{equipo}/`. Limpia y publica. No dibuja.

Son tres pasos, siempre en este orden. Cada uno deja el resultado en un lugar distinto.

1. **Ingesta.** Copia el archivo crudo, sin transformarlo, a MinIO, bucket `bronze`, en `bronze/{equipo}/{dataset}/fecha=AAAA-MM-DD/`. La función se llama `ingerir()`. Una fuente que solo existe como enlace no se sube a mano: esta función la descarga y la deja en ese prefijo, con la fecha de obtención.
2. **Plata.** Lee ese bronce, limpia tipos, nombres y textos, y escribe tablas en PostgreSQL, esquema `plata`. La función se llama `construir()`, en `pipelines/{equipo}/plata.py`. El ráster se queda como COG en MinIO; en PostgreSQL solo quedan su ruta y sus metadatos.
3. **Oro.** Lee plata y deja una tabla por subtema en el esquema `oro`. El nombre de la tabla es el `viz_id`, por ejemplo `oro."4.ied_por_pais"`. `construir()` las publica todas. `leer(viz_id)` lee una. La página y el PDF leen esta tabla.

Lo restringido va al bucket `bronze-restringido`, con la misma forma de ruta. El ráster va al bucket `raster`. Las tablas de las figuras viven en la base `vis`. Airflow usa otra base, `airflow`, en el mismo PostgreSQL: ahí guarda sus corridas, no los datos de las gráficas.

Hoy solo el equipo 4 tiene `ingerir()` y `construir()`, en `pipelines/4/`. Esa ingesta todavía lee `datos/4/` y escribe `bronze/4/<archivo>`, sin la partición `dataset/fecha=` de la arquitectura: hay que alinearla. Los equipos 1, 2, 3 y 6 arman la tabla con una función que abre una carpeta local. El equipo 5 todavía no tiene `pipelines/5/`. Esas funciones locales son el trabajo pendiente de Producción, no el camino a seguir.

### Qué es un DAG y dónde entra

Un DAG es el proceso que Airflow ejecuta para un equipo. El archivo es `dags/equipo_{n}.py` y dentro de Airflow se llama `equipo_{n}`. No guarda datos: llama a los scripts del pipeline, en el orden de la arquitectura.

```text
ingesta → plata → oro → validacion → catalogo
```

Con `docker compose up`, Airflow monta `dags/` en `/opt/airflow/dags` y `pipelines/` en `/opt/airflow/pipelines`. La interfaz queda en http://localhost:8080, usuario `admin`. Disparar `equipo_4` corre `ingerir()` y después `construir()` de plata y de oro, cada una en un entorno virtual propio (Airflow trae SQLAlchemy 1.4 y los pipelines usan la 2). `validacion` y `catalogo` siguen vacías.

`equipo_1.py`, `equipo_2.py`, `equipo_3.py`, `equipo_5.py` y `equipo_6.py` tienen la misma cadena, pero cada tarea está vacía. Airflow la marca terminada y no lee archivos. Dejarlas así no publica la figura. Producción las conecta a las funciones del pipeline de ese equipo.

### Dónde se conecta cada ruta

Estas son las rutas del proceso. El código las usa tal cual; no las sustituye por una carpeta de tu máquina.

| Qué | Ruta |
| --- | --- |
| Copia compartida, antes de entrar al proceso | Carpeta de Drive del curso. Producción la sube a bronce. El código no la abre. |
| Bronce | MinIO, `bronze/{equipo}/{dataset}/fecha=AAAA-MM-DD/`. |
| Plata y oro | PostgreSQL, base `vis`, tablas `plata."<nombre>"` y `oro."<viz_id>"`. |
| Figura | `figures/{equipo}/{subtema}/figura.py`, función `figura(datos)`. `datos` es la tabla de oro. |
| Página | `app/pages/{equipo}/`. Importa `figura` y le pasa `oro."<viz_id>"`. |
| Menú | `/`, en `app/pages/inicio.py`. Los capítulos y el destino de cada vínculo están en `app/recorrido.py`. |
| Subtema sin página | `/v/{equipo}/{subtema}`, la ficha de `app/pages/subtema.py`. El vínculo ya existe; la figura todavía no. |

El PDF importa la misma `figura(datos)`. No tiene ruta en la web. Dash y Quarto leen el esquema `oro`; no leen bronce ni una carpeta local.

Lo que hoy está montado, y lo que todavía se sale de estas rutas:

- `/4` (`app/pages/4/historia.py`) llama a `pipelines/4/oro.py` → `leer("4.<subtema>")` y pasa esa tabla a `figura`. La ingesta de ese equipo aún parte de `datos/4/`.
- `/6/gasto_publico`, `/6/cambio_suelo`, `/6/corredor_industrial`, `/6/relieve_5m` y `/6/huella_construida` leen `oro."6.<subtema>"` si existe `ORO_DB_URL`. Si no, `app/pages/6/_e6.py` cae a un parquet de `local_avances/`. Ese respaldo no forma parte de la entrega: la página tiene que salir de oro.

## Visualizaciones

```text
figures/{equipo}/{subtema}/figura.py
```

`{equipo}` es el número de tu equipo, del 1 al 6. `{subtema}` es la carpeta que ya está creada. El `viz_id` de esa carpeta es `{equipo}.{subtema}`. No abras otra carpeta.

La página de la aplicación vive en `app/pages/{equipo}/`. Esa página no vuelve a dibujar la figura: importa `figura` desde `figures/{equipo}/{subtema}/figura.py` y la pone en la plantilla. El PDF importa la misma función.

## Qué debe devolver este módulo

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

Ese MinIO es local: cada quien ve solo lo que subió en su Docker. La copia compartida sigue en Drive hasta que Producción la deposita en ese prefijo. El código no abre Drive ni `datos/`. Solo el DAG `equipo_4` lee el bronce y publica plata y oro, y su ingesta todavía hay que pasarla a la ruta de arriba. En los otros cinco, ingesta, plata y oro están vacías, así que subir el archivo no dispara el proceso hasta que Producción conecte el DAG.

## Qué no entra en Git

No subas ráster, nubes de puntos, CSV, XLS, XLSX ni directorios masivos. Esos archivos viven en el datalake. En este repositorio van el módulo de la figura, la página y el catálogo. `catalog/catalog.csv` sí se versiona; cualquier otro CSV no.

## Antes de avisar que está lista

1. La función está en `figures/{equipo}/{subtema}/figura.py` y la página importa esa función.
2. Ingesta, plata y oro leen MinIO y PostgreSQL. En `pipelines/`, `dags/` y `app/pages/` no quedó ninguna ruta local.
3. `dags/equipo_{n}.py` corre ingesta, plata, oro, validación y catálogo, y al dispararlo la tabla `oro."<viz_id>"` se publica.
4. La figura sale de esa tabla. La página no abre un parquet ni una carpeta de respaldo.
5. La primaria de este subtema no está usada por otra visualización de tu equipo.
6. La secundaria está indicada, con valor de referencia y tolerancia en el catálogo.
7. El título de la figura es el del subtema.
8. Si tu equipo todavía no tiene fuente en streaming, esta puede ser esa fuente y queda marcada en el catálogo.

