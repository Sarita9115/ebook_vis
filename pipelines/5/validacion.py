"""Equipo 5 · Validación: revisa las tablas de oro antes de publicarlas. Si algo falla, la tarea falla.

Revisa rangos, cobertura y consistencia (no compara contra valores de referencia inventados: el
catálogo guarda esos valores cuando el equipo los define).

Uso:  python pipelines/5/validacion.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _comun():
    if "equipo5_comun" not in sys.modules:
        spec = importlib.util.spec_from_file_location("equipo5_comun", Path(__file__).with_name("comun.py"))
        sys.modules["equipo5_comun"] = m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return sys.modules["equipo5_comun"]


comun = _comun()
META = ["viz_id", "fuente_primaria", "fuente_secundaria", "institucion", "fecha_obtencion", "responsable"]


def _oro(sub):
    return comun.leer_tabla("oro", f"5.{sub}")


def validar() -> dict[str, str]:
    fallas, ok = [], {}

    def chequeo(sub, cond, msg):
        if not cond:
            fallas.append(f"5.{sub}: {msg}")

    for sub in comun.SUBTEMAS:
        d = _oro(sub)
        chequeo(sub, len(d) > 0, "tabla vacía")
        chequeo(sub, all(c in d.columns for c in META), "faltan columnas de metadatos")
        chequeo(sub, d.get("viz_id", d.iloc[:, 0]).eq(f"5.{sub}").all(), "viz_id incorrecto")
        ok[sub] = f"{len(d)} filas"

    d = _oro("treinta_anos")
    chequeo("treinta_anos", d["grado_promedio"].between(0, 20).all(), "grado promedio fuera de 0-20")
    chequeo("treinta_anos", set(d["entidad"]) <= set(comun.PENINSULA.values()), "entidades fuera de la península")
    chequeo("treinta_anos", "Yucatán" in set(d["entidad"]), "falta Yucatán")
    chequeo("treinta_anos", d["anio"].min() <= 2000, "falta el dato de 2000")

    d = _oro("pobreza_rezago")
    chequeo("pobreza_rezago", d["pobreza_pct"].between(0, 100).all(), "pobreza fuera de 0-100")
    for a in (2010, 2015, 2020):
        n = (d["anio"] == a).sum()
        chequeo("pobreza_rezago", n == 106, f"{a}: {n} municipios (se esperan 106)")

    d = _oro("la_casa_cambio")
    chequeo("la_casa_cambio", d["porcentaje"].between(0, 100).all(), "porcentaje fuera de 0-100")
    chequeo("la_casa_cambio", set(d["ambito"]) == {"Rural", "Urbano"}, "faltan ámbitos Rural/Urbano")

    d = _oro("lo_que_se_invirtio")
    chequeo("lo_que_se_invirtio", (d["monto_millones"] > 0).all(), "montos no positivos")
    entra = d.groupby("destino")["monto_millones"].sum()
    sale = d.groupby("origen")["monto_millones"].sum()
    for nodo in set(entra.index) & set(sale.index):
        chequeo("lo_que_se_invirtio", abs(entra[nodo] - sale[nodo]) <= 0.01 * max(entra[nodo], 1e-9),
                f"el nodo '{nodo}' recibe {entra[nodo]:.1f} y reparte {sale[nodo]:.1f} (más de 1% de diferencia)")

    if fallas:
        raise AssertionError("Validación fallida:\n- " + "\n- ".join(fallas))
    return ok


if __name__ == "__main__":
    for k, v in validar().items():
        print(k, v)
