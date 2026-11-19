# Requerimientos del cliente

**Proyecto:** Visualización integrada de la península de Yucatán  
**Asignatura:** Visual Modelling  
**Institución:** Universidad Politécnica de Yucatán  
**Cliente:** Profesor de la asignatura  
**Elabora:** Equipo de producción  
**Fecha:** 2 de noviembre de 2026  
**Versión:** 1.1  
**Estado:** Para revisión del cliente

Este documento recoge lo que el cliente espera recibir. La forma de construirlo está en el documento de arquitectura que acompaña a este archivo.

## 1. Propósito

Entregar un producto único, en un servidor local ya existente, que permita consultar las visualizaciones del curso y conservar una versión estática en PDF. El área de estudio es la península de Yucatán: Campeche, Yucatán y Quintana Roo.

## 2. Producto esperado

El cliente recibe dos piezas, generadas a partir de los mismos datos preparados:

1. Una aplicación web interactiva, publicada en el servidor local. La operación de ese servidor corresponde a IT.
2. Un ebook en PDF, con las mismas visualizaciones exportadas a imagen.

La aplicación es el visor. La visualización que se evalúa es la figura, no la página que la contiene.

## 3. Interesados


| Interesado                        | Interés                                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Profesor (cliente)                | Recibir la web y el PDF, y evaluar las visualizaciones.                                                 |
| Lector del ebook                  | Consultar las figuras y la procedencia de cada dato, si el material se hace público.                    |
| Seis equipos de tema              | Aportar las fuentes y el enfoque de su sección.                                                         |
| Producción                        | Construir los flujos de datos y las visualizaciones. Son catorce personas, tomadas de los seis equipos. |
| IT, dirección de proyecto y apoyo | Las cinco personas restantes. IT administra el servidor, el acceso y el respaldo.                       |


El curso está formado por seis equipos y diecinueve personas. No hay equipos adicionales.

## 4. Alcance

Entran al producto las secciones de los seis equipos:


| Equipo | Sección                                                    |
| ------ | ---------------------------------------------------------- |
| 1      | Memoria histórica de la Universidad Politécnica de Yucatán |
| 2      | Fauna endémica y reservas naturales de la península        |
| 3      | Crecimiento poblacional de los municipios de Yucatán       |
| 4      | Inversión extranjera en Yucatán                            |
| 5      | Educación y calidad de vida en Yucatán                     |
| 6      | Dinámica empresarial y desarrollo económico en Yucatán     |


Cada equipo aporta ocho fuentes de datos. Cada visualización usa una fuente primaria y al menos una secundaria.

- La fuente primaria no se repite dentro del mismo equipo.
- La fuente secundaria puede repetirse.
- La primaria de un subtema puede ser secundaria de otro.
- Varios enlaces que documentan la misma fuente cuentan como una sola fuente.
- Al menos una fuente de cada equipo queda conectada en streaming.

Con ocho fuentes, el máximo es de ocho visualizaciones por equipo, salvo que el equipo incorpore una fuente primaria adicional.

## 5. Requerimientos funcionales

1. El usuario abre una aplicación y, desde ella, llega a la sección de cada equipo y a cada visualización.
2. Cada visualización muestra la figura, un texto breve de lectura, la fuente primaria, la fuente secundaria, la fecha de obtención del dato y el responsable del procesamiento.
3. Las figuras incluyen, según el tema, mapas, series, barras, gráficos de doble eje, una línea de tiempo y vistas tridimensionales cuando el dato lo permite.
4. El PDF contiene las mismas figuras, exportadas a imagen, con el mismo título y las mismas fuentes.
5. Si un dato preparado cambia, la figura de la web y la del PDF se vuelven a generar desde ese dato. El PDF no se edita a mano.
6. Cada cifra publicada coincide con su fuente, dentro del criterio de validación registrado para ese conjunto de datos: un valor de referencia tomado de la fuente y una tolerancia.
7. El origen de cada dato queda registrado: institución, enlace directo, formato, fecha de descarga y persona responsable.
8. Los datos nacionales se limitan a Campeche, Yucatán y Quintana Roo antes de usarse en una visualización.
9. Los formularios no publican información confidencial. Solo se publican conteos o categorías.
10. La sección de Memoria UPY se presenta como línea de tiempo. No se le exige un mapa.
11. Cada equipo mantiene al menos una fuente conectada en streaming. La figura de esa fuente, en la web, muestra el dato vigente. El PDF conserva la imagen del momento en que se genera.



## 6. Requerimientos de datos

1. Los formatos de entrada previstos son SHP, GeoJSON, KML, GeoParquet, CSV, XLSX, XLS, HTML, PDF, ZIP, API, GRID ASCII, ráster, GeoTIFF, GLB/GLTF y, si se entrega, LAS/LAZ. También entra una fuente en streaming por equipo.
2. El archivo original se conserva con su fecha de obtención. La web y el PDF leen el dato ya preparado.
3. Un archivo comprimido se abre y su contenido queda junto al original.
4. Sin enlace directo de descarga y sin una estimación de peso, la fuente no se integra. La fuente en streaming se identifica por su enlace de conexión y por una estimación de volumen.



## 7. Requerimientos de visualización

1. La web se presenta en una sola aplicación.
2. Un modelo GLB y una nube o ráster lidar pueden acompañar la sección como archivo o como mapa de relieve. La figura que se evalúa es la gráfica, no el archivo que la acompaña.
3. Los polígonos pesados se simplifican antes de publicarse. El ráster de 5 m no se envía crudo al navegador.



## 8. Requerimientos no funcionales

1. El plazo de entrega es de tres semanas a partir del 2 de noviembre de 2026.
2. El servidor ya existe y es local. IT lo administra.
3. El procesamiento puede repetirse desde los archivos originales y produce de nuevo el dato preparado y las figuras.
4. El código y la documentación se versionan. Los archivos pesados no se versionan con el código.
5. El acceso de escritura queda limitado: cada equipo escribe en sus archivos originales; producción escribe en el dato preparado, la aplicación y el ebook.
6. Existe un respaldo de los datos y del repositorio fuera del servidor.
7. La web se consulta dentro de la red del curso.
8. Los datos de origen son públicos, salvo los formularios. Esos formularios se tratan como información confidencial hasta que el equipo demuestre lo contrario, y su archivo crudo queda en un área de acceso restringido.



## 9. Restricciones

1. No se descarga el Directorio Estadístico Nacional de Unidades Económicas en su versión nacional. La consulta se limita a la península.
2. El PDF no se actualiza en streaming. Conserva la imagen del momento en que se genera.



## 10. Criterios de aceptación

El cliente puede dar por recibido el trabajo cuando se cumpla lo siguiente:

1. La web está disponible en el servidor y reúne las secciones de los seis equipos.
2. Cada visualización publicada tiene figura, lectura, fuente primaria, fuente secundaria, fecha y responsable.
3. Ninguna fuente primaria se repite dentro de un mismo equipo.
4. El PDF muestra las mismas figuras y las mismas fuentes.
5. Una nueva ejecución desde los archivos originales regenera el dato preparado y las figuras.
6. Las cifras publicadas fueron contrastadas con el valor de referencia y la tolerancia registrados para su conjunto.
7. Ninguna tabla publicada contiene información confidencial obtenida de un formulario.
8. Cada equipo tiene al menos una fuente conectada en streaming y la figura correspondiente en la web muestra el dato vigente.



## 11. Supuestos

1. IT puede instalar en el servidor el software de infraestructura descrito en la arquitectura.
2. Los formularios pueden contener información confidencial. El supuesto se retira solo con confirmación del equipo dueño.
3. El inventario de fuentes todavía está incompleto. Educación no ha entregado su formato, y ningún equipo ha cerrado ocho fuentes con enlace directo. El requerimiento de ocho fuentes se mantiene.
4. El reparto interno del trabajo de producción se definirá después de cerrar estos requerimientos y la arquitectura. No forma parte de lo que el cliente aprueba en este documento.



## 12. Exclusiones

Quedan fuera de esta entrega:

- Aplicaciones separadas por equipo.
- Un ebook mantenido de forma manual, independiente del dato preparado.
- Publicación de información confidencial obtenida de un formulario.



## 13. Entregables hacia el cliente


| Entregable        | Descripción                                                                                                                                 |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Aplicación web    | Visor único en el servidor local, con las visualizaciones del curso.                                                                         |
| Ebook PDF         | Misma secuencia de figuras, en imagen, con sus fuentes.                                                                                     |
| Catálogo de datos | Inventario de fuentes, con primaria o secundaria, fecha, responsable, valor de referencia, tolerancia de validación y estado de validación. |


