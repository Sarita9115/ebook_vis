# Vistas locales del equipo 3

Desde la raíz del repositorio, con las dependencias del proyecto instaladas:

```sh
.venv/bin/python figures/3/natalidad/figura.py --vista pulso
.venv/bin/python figures/3/natalidad/figura.py --vista calendario
.venv/bin/python figures/3/alfabetizacion/figura.py
```

Cada comando abre una vista en el navegador. Sin `--vista`, natalidad abre
el mapa anual y el calendario en la misma página. Con `--sin-abrir`, los
comandos imprimen la dirección del HTML generado.

Las vistas locales leen las tablas preparadas en `figures/3/datos_locales/`.
Git ignora esa carpeta. El visor de producción sigue llamando a `figura(datos)`.

- `natalidad.csv`: nacimientos certificados agrupados por mes de nacimiento
  y municipio de residencia de la madre, 2008–2023. [SINAC, RIISP/INSP](https://riisp.insp.mx/nada/index.php/catalog/17).
  Para medir el crecimiento poblacional total hace falta una serie municipal
  de población comparable. El módulo `pipelines/3/natalidad.py` agrega la
  base consolidada y une el resultado al catálogo municipal.
- `alfabetizacion.csv`: personas alfabetizadas por el IEAEY durante 2016,
  según sus registros administrativos. El cuadro 6.22 del [Anuario 2017](https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/anuarios_2017/702825095116.pdf#page=403)
  reproduce los datos del IEAEY. El total estatal de control es 2,279. El
  indicador describe los resultados del programa. Para medir a toda la
  población alfabeta hace falta una fuente poblacional. Si la restricción
  también excluye anuarios de INEGI con registros producidos por terceros,
  esta tabla queda como referencia histórica de trabajo.
- `yucatan.geojson`: polígonos de los 106 municipios, simplificados en
  WGS84. [GeoBoundaries, Banco Mundial](https://www.geoboundaries.org/api/current/gbOpen/MEX/ADM2/).
  Los nombres y claves se cotejaron con el [Gobierno de Yucatán](https://www.yucatan.gob.mx/estado/municipios.php).
  `world_110m.json` contiene la cartografía de fondo de Plotly para la
  vista sin conexión.
