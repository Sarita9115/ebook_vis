"""Aplicación Dash del proyecto. Sirve la historia del equipo 4 en un solo puerto.

Uso:  python app/app.py            # http://localhost:8050
      PORT=8060 python app/app.py  # otro puerto
"""
import importlib.util
import os
from pathlib import Path

from dash import Dash

AQUI = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("historia_equipo4", AQUI / "pages" / "4" / "historia.py")
historia = importlib.util.module_from_spec(spec)
spec.loader.exec_module(historia)

app = Dash(
    __name__, title="El dinero que llega de fuera · Inversión extranjera en Yucatán",
    assets_folder=str(AQUI / "assets"),
    external_stylesheets=["https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700"
                          "&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap"],
)
app.layout = historia.layout
historia.registrar(app)
server = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)
