"""Los aluxes del Mayab. La portada lista los capítulos; cada vínculo abre su subtema.

Uso:  python app/app.py            # http://localhost:8050
      PORT=8060 python app/app.py  # otro puerto
"""
import os
import sys
from pathlib import Path

from dash import Dash

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
for ruta in (str(RAIZ), str(AQUI)):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

app = Dash(
    __name__,
    use_pages=True,
    pages_folder=str(AQUI / "pages"),
    title="Los aluxes del Mayab",
    assets_folder=str(AQUI / "assets"),
    suppress_callback_exceptions=True,
    external_stylesheets=["https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700"
                          "&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap"],
)
server = app.server

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)
