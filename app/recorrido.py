"""Recorrido de Los aluxes del Mayab, en el orden del storytelling.

Cada subtema apunta a su página. Si esa página ya existe, el vínculo va
directo. Si todavía no, va a una ficha con el título.
"""

CAPITULOS = [
    {
        "orden": "1",
        "imagen": "/assets/indice/cap1.jpg",
        "apertura": "El monte que se cuida",
        "equipo": "2",
        "titulo": "El territorio que se cuida",
        "pregunta": "¿Qué se protege y qué vive ahí?",
        "subtemas": [
            ("donde_se_cuida", "Dónde se cuida la península"),
            ("yucatan_reservas", "Yucatán, al lado de sus reservas"),
            ("herbario_cicy", "Herbario CICY, plantas vasculares"),
            ("fauna_nom059", "La fauna de la península, en tu espacio"),
            ("unidades_en_reservas", "Unidades económicas de impacto ambiental o relación con la biodiversidad"),
            ("cria_de_cerdo", "Impacto por municipio ocasionado por la cría de cerdo en la península"),
            ("negocios_en_reservas", "Cada tipo de negocio situado en cada reserva natural"),
            ("ecosistemas", "Los ecosistemas que protege la península"),
        ],
    },
    {
        "orden": "2",
        "imagen": "/assets/indice/cap2.jpg",
        "apertura": "La gente que habita el Mayab",
        "equipo": "3",
        "titulo": "La gente que llega",
        "pregunta": "¿Quién habita ese territorio y hacia dónde crece?",
        "subtemas": [
            ("crecimiento_densidad", "Crecimiento poblacional y densidad territorial"),
            ("ranking_crecimiento", "Ranking porcentual del crecimiento poblacional de los estados de México"),
            ("natalidad", "Natalidad y crecimiento poblacional de los municipios de Yucatán"),
            ("poblacion_joven", "Municipios con mayor concentración de población joven"),
            ("expansion_merida", "Expansión urbana en Mérida"),
            ("alfabetizacion", "Comparativa de población alfabetizada en los municipios de Yucatán"),
            ("educacion_superior", "Evolución de la población con educación superior"),
            ("instituciones_educativas", "Disponibilidad de instituciones educativas en Yucatán"),
        ],
    },
    {
        "orden": "3",
        "imagen": "/assets/indice/cap3.jpg",
        "apertura": "La vida en casa",
        "equipo": "5",
        "titulo": "Más años en el aula, ¿mejor vida en casa?",
        "pregunta": "¿Más años en el aula coinciden con mejor vida en casa?",
        "capitulo": ("/5", "Abrir la historia de este capítulo"),
        "subtemas": [
            ("treinta_anos", "Treinta años aprendiendo"),
            ("la_respuesta", "La respuesta"),
            ("pobreza_rezago", "Pobreza y rezago"),
            ("la_casa_cambio", "La casa cambió"),
            ("lo_que_se_invirtio", "Lo que se invirtió"),
            ("entorno_escuela", "El entorno de la escuela"),
            ("metas_estado", "Las metas del estado"),
            ("geografia_dispersion", "La geografía de la dispersión"),
        ],
    },
    {
        "orden": "4",
        "imagen": "/assets/indice/cap4.jpg",
        "apertura": "Quien llega de fuera",
        "equipo": "4",
        "titulo": "El capital que llega de fuera",
        "pregunta": "¿De dónde llega el capital y qué pasó con las empresas?",
        "capitulo": ("/4", "Abrir la historia de este capítulo"),
        "subtemas": [
            ("ied_por_pais", "Inversión extranjera directa (IED) en Yucatán por país de origen"),
            ("censos_economicos", "Unidades económicas, empleo y producción en Yucatán (Censos Económicos 2019 y 2024)"),
            ("pulso_ied", "El pulso de la inversión extranjera: ritmo de la IED en Yucatán (2020-2025)"),
            ("promesa_resultado", "Promesa contra resultado: empleos anunciados y empleo formal en el IMSS"),
            ("remesas_ied", "Sobres contra maletines: remesas e inversión extranjera en Yucatán (2020-2025)"),
            ("ied_ranking_origen", "IED hacia Yucatán por año, ranking y origen (2018-2025)"),
            ("turismo_derrama", "Turismo y derrama económica"),
            ("apertura_exterior", "Efecto económico de la apertura al exterior"),
        ],
    },
    {
        "orden": "5",
        "imagen": "/assets/indice/cap5.jpg",
        "apertura": "El suelo que cambia de forma",
        "equipo": "6",
        "titulo": "La economía sobre el suelo",
        "pregunta": "¿Dónde se asienta esa economía sobre el suelo y la ciudad?",
        "subtemas": [
            ("densidad_unidades", "Distribución y densidad nacional de unidades económicas"),
            ("aporte_pib", "Aporte del sector empresarial al PIB estatal y regional"),
            ("atraccion_capital", "Atracción de capital, empleo y evolución de las unidades económicas en Yucatán"),
            ("obra_publica", "Obra pública e infraestructura para el desarrollo económico por municipio"),
            ("gasto_publico", "Gasto público estatal y fomento económico: hacia dónde va el presupuesto de Yucatán"),
            ("cambio_suelo", "Cambio de uso del suelo y expansión urbana en Yucatán y la zona metropolitana de Mérida"),
            ("corredor_industrial", "Concentración industrial en el corredor Mérida, Umán y Hunucmá"),
            ("relieve_5m", "Relieve y altura edificada de la zona metropolitana de Mérida vistos desde modelos de elevación de 5 m"),
            ("huella_construida", "Huella construida, altura y densidad empresarial de Mérida"),
        ],
    },
    {
        "orden": "6",
        "imagen": "/assets/indice/cap6.jpg",
        "apertura": "La casa que cuenta la historia",
        "equipo": "1",
        "titulo": "La universidad en ese tiempo",
        "pregunta": "¿Qué hitos de la UPY quedan documentados en ese mismo periodo?",
        "subtemas": [
            ("gobierno_universitario", "Gobierno universitario y cambios de rectoría"),
            ("trayectoria_estudiantil", "Trayectoria estudiantil"),
            ("financiamiento_infraestructura", "Financiamiento e infraestructura"),
            ("carreras_modalidades", "Carreras, modalidades y acreditaciones"),
            ("investigacion_aplicada", "Investigación e innovación aplicada"),
            ("vinculacion_empleo", "Vinculación con la industria y empleo"),
            ("movilidad_internacional", "Movilidad y colaboración internacional"),
            ("participacion_estudiantil", "Participación estudiantil y comunidad"),
        ],
    },
]

# Páginas que ya están registradas con su propia ruta.
PAGINAS = {
    ("5", "treinta_anos"): "/5#treinta_anos",
    ("5", "pobreza_rezago"): "/5#pobreza_rezago",
    ("5", "la_casa_cambio"): "/5#la_casa_cambio",
    ("5", "lo_que_se_invirtio"): "/5#lo_que_se_invirtio",
    ("6", "gasto_publico"): "/6/gasto_publico",
    ("6", "cambio_suelo"): "/6/cambio_suelo",
    ("6", "corredor_industrial"): "/6/corredor_industrial",
    ("6", "relieve_5m"): "/6/relieve_5m",
    ("6", "huella_construida"): "/6/huella_construida",
}


def enlace(equipo: str, slug: str) -> str:
    return PAGINAS.get((equipo, slug), f"/v/{equipo}/{slug}")


def ficha(equipo: str, slug: str):
    for capitulo in CAPITULOS:
        if capitulo["equipo"] != equipo:
            continue
        for i, (s, titulo) in enumerate(capitulo["subtemas"], start=1):
            if s == slug:
                return capitulo, i, titulo
    return None, None, None
