// Animación del mapa de flujos (4.ied_por_pais), con la misma mecánica que la referencia del equipo
// (flujo_animacion.html): misma velocidad para todos los billetes, todos los países sueltan un billete en los
// mismos instantes (cada INTERVALO_MS) y cada país arranca con un retraso para que su primer billete llegue al
// mismo tiempo que el de la ruta más larga; como todos sueltan el mismo número, el último también coincide.
// Cada periodo dura FRAME_MS + PAUSA_MS y luego pasa al siguiente (en acumulado, se repite).
//
// La figura de Plotly trae en layout.meta.billetes las rutas en coordenadas del lienzo de la referencia
// (Natural Earth, 1000 × 540). Aquí se calcula cada billete en ese lienzo, se convierte a lon/lat y se actualizan
// solo las capas animadas con Plotly.restyle; el mapa base no se redibuja en cada cuadro.
(function () {
  // ------------------------------------------------------------ proyección Natural Earth (igual que figura.py)
  function neInv(x, y) {
    var phi = y;
    for (var i = 0; i < 25; i++) {
      var p2 = phi * phi, p4 = p2 * p2;
      var d = (phi * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4))) - y) /
        (1.007226 + p2 * (0.015085 * 3 + p4 * (-0.044475 * 7 + 0.028874 * 9 * p2 - 0.005916 * 11 * p4)));
      phi -= d;
      if (Math.abs(d) < 1e-9) break;
    }
    var q = phi * phi;
    var lam = x / (0.8707 + q * (-0.131979 + q * (-0.013791 + q * q * q * (0.003971 - 0.001529 * q))));
    return [phi * 180 / Math.PI, lam * 180 / Math.PI];   // [lat, lon]
  }
  var L = null;
  function aGeo(px, py) { return neInv((px - L.X0) / L.K, -(py - L.Y0) / L.K); }

  // ------------------------------------------------------------ geometría de la ruta (igual que la referencia)
  function punto(a, c, b, t) {
    var u = 1 - t;
    return [u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]];
  }
  function tangente(a, c, b, t) {
    var dx = 2 * (1 - t) * (c[0] - a[0]) + 2 * t * (b[0] - c[0]);
    var dy = 2 * (1 - t) * (c[1] - a[1]) + 2 * t * (b[1] - c[1]);
    return Math.atan2(dy, dx) * 180 / Math.PI;
  }
  function medir(a, c, b) {
    var acum = [0], prev = a;
    for (var i = 1; i <= 80; i++) {
      var q = punto(a, c, b, i / 80);
      acum.push(acum[i - 1] + Math.hypot(q[0] - prev[0], q[1] - prev[1]));
      prev = q;
    }
    return acum;
  }
  function tEnDistancia(acum, dist) {
    var n = acum.length - 1, lo = 0, hi = n;
    while (lo < hi) { var m = (lo + hi) >> 1; if (acum[m] < dist) lo = m + 1; else hi = m; }
    var i = Math.max(1, lo);
    if (i > n) return 1;
    return (i - 1 + (dist - acum[i - 1]) / ((acum[i] - acum[i - 1]) || 1)) / n;
  }
  function rect(cx, cy, w, h, giro, la, lo) {
    var g = giro * Math.PI / 180, cs = Math.cos(g), sn = Math.sin(g);
    var pts = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]].map(function (p) {
      return aGeo(cx + p[0] * cs - p[1] * sn, cy + p[0] * sn + p[1] * cs);
    });
    var area = 0;
    for (var j = 0; j < 4; j++) { var p = pts[j], q = pts[(j + 1) % 4]; area += p[1] * q[0] - q[1] * p[0]; }
    if (area > 0) pts.reverse();   // plotly geo rellena según el sentido de giro
    pts.push(pts[0]);
    pts.forEach(function (p) { la.push(p[0]); lo.push(p[1]); });
    la.push(null); lo.push(null);
  }

  // ------------------------------------------------------------ estado (como en la referencia)
  var S = { gd: null, id: null, meta: null, reloj: 0, inicio: 0, idx: 0, rep: true, vel: 1, ultimo: null,
            billetes: [], emisiones: [], pulsos: [], ultimoPulso: {}, fpx: 1.25 };

  function prepararFrame(i, conReact) {
    var M = S.meta, C = M.constantes, f = M.grupos[i];
    S.idx = i; S.inicio = S.reloj; S.billetes = []; S.pulsos = []; S.ultimoPulso = {};
    f.rutas.forEach(function (d) { if (!d.acum) d.acum = medir(d.a, d.c, d.b); });
    var viaje = function (d) { return (d.fin - d.ini) / C.VELOCIDAD; };
    var maxViaje = Math.max.apply(null, f.rutas.map(viaje).concat([0]));
    var n = Math.max(1, Math.floor((C.FRAME_MS - maxViaje) / C.INTERVALO_MS) + 1);
    S.emisiones = [];
    f.rutas.forEach(function (d) {
      for (var k = 0; k < n; k++) S.emisiones.push({ d: d, t: maxViaje - viaje(d) + k * C.INTERVALO_MS });
    });
    S.emisiones.sort(function (x, y) { return x.t - y.t; });
    if (conReact) {
      var layout = Object.assign({}, S.gd.layout, { annotations: f.anotaciones });
      Plotly.react(S.gd, f.data, layout);
    }
    document.querySelectorAll("#mapa-chips .chip").forEach(function (b, j) { b.classList.toggle("activo", j === i); });
  }

  function chips() {
    var cont = document.getElementById("mapa-chips");
    if (!cont) return;
    cont.innerHTML = "";
    S.meta.grupos.forEach(function (g, j) {
      var b = document.createElement("button");
      b.className = "chip";
      b.innerHTML = g.etiqueta + "<small style='color:" + (g.neto >= 0 ? S.meta.colores.IN_OSC : S.meta.colores.OUT_OSC) +
        "'>" + g.neto_txt + "</small>";
      b.addEventListener("click", function () { prepararFrame(j, true); });
      cont.appendChild(b);
    });
  }

  function dibujar() {
    var M = S.meta, C = M.constantes, f = M.grupos[S.idx], I = f.idx;
    var capa = { in0: [[], []], in1: [[], []], in2: [[], []], out0: [[], []], out1: [[], []], out2: [[], []],
                 borde: [[], []] };
    var sig = { la: [], lo: [], tam: [], txt: [], col: [] };
    var fpx = S.fpx;
    S.billetes = S.billetes.filter(function (b) {
      var d = b.d, t = (S.reloj - b.t0) * C.VELOCIDAD / (d.fin - d.ini);
      if (t >= 1) {
        // Pulsos espaciados por destino; con un chorro continuo, uno por billete sería un parpadeo constante.
        var destino = d.entra ? "Yucatán" : d.pais;
        if (S.reloj - (S.ultimoPulso[destino] === undefined ? -Infinity : S.ultimoPulso[destino]) >= C.PULSO_MS) {
          S.ultimoPulso[destino] = S.reloj;
          var g = aGeo(d.b[0], d.b[1]);
          S.pulsos.push({ la: g[0], lo: g[1], t0: S.reloj, entra: d.entra });
        }
        return false;
      }
      var dist = d.ini + t * (d.fin - d.ini), s = tEnDistancia(d.acum, dist), xy = punto(d.a, d.c, d.b, s);
      var giro = tangente(d.a, d.c, d.b, s) * 0.25 + 9 * Math.sin(S.reloj / 260 + b.oscila);
      var op = Math.min(1, t / 0.06, (1 - t) / 0.15);
      var esc = C.ESCALA_EXTREMOS + (1 - C.ESCALA_EXTREMOS) * Math.sin(Math.PI * t);
      var w = d.w * esc, h = d.w * C.PROPORCION * esc;
      var nivel = op < 0.4 ? 0 : op < 0.8 ? 1 : 2;
      var k = (d.entra ? "in" : "out") + nivel;
      rect(xy[0], xy[1], w, h, giro, capa[k][0], capa[k][1]);
      if (d.w >= 18) {
        rect(xy[0], xy[1], w - 5 * esc, h - 5 * esc, giro, capa.borde[0], capa.borde[1]);
        var c = aGeo(xy[0], xy[1]);
        sig.la.push(c[0]); sig.lo.push(c[1]);
        sig.tam.push(h * 0.6 * fpx); sig.txt.push(Math.max(1, h * 0.48 * fpx));
        sig.col.push("rgba(255,255,255," + op.toFixed(2) + ")");
      }
      return true;
    });

    var pul = { la: [], lo: [], tam: [], col: [] };
    S.pulsos = S.pulsos.filter(function (p) {
      var u = (S.reloj - p.t0) / 700;
      if (u >= 1) return false;
      pul.la.push(p.la); pul.lo.push(p.lo); pul.tam.push(2 * (4 + 18 * u) * fpx);
      pul.col.push((p.entra ? "rgba(47,158,91," : "rgba(227,73,72,") + (0.8 * (1 - u)).toFixed(2) + ")");
      return true;
    });

    var orden = ["in0", "in1", "in2", "out0", "out1", "out2", "borde"], idx = [], la = [], lo = [], u;
    var msz = [], mcol = [], tsz = [], tcol = [];
    orden.forEach(function (k) {
      idx.push(I[k]); la.push(capa[k][0]); lo.push(capa[k][1]); msz.push(u); mcol.push(u); tsz.push(u); tcol.push(u);
    });
    idx.push(I.signo); la.push(sig.la); lo.push(sig.lo); msz.push(sig.tam); mcol.push(u); tsz.push(sig.txt); tcol.push(sig.col);
    idx.push(I.pulso); la.push(pul.la); lo.push(pul.lo); msz.push(pul.tam); mcol.push(pul.col); tsz.push(u); tcol.push(u);
    Plotly.restyle(S.gd, { lat: la, lon: lo, "marker.size": msz, "marker.color": mcol,
                           "textfont.size": tsz, "textfont.color": tcol }, idx);
  }

  function cuadro(ahora) {
    requestAnimationFrame(cuadro);
    var gd = document.querySelector("#fig-mapa .js-plotly-plot");
    if (!gd || !gd.layout || !gd.layout.meta || !gd.layout.meta.billetes || !window.Plotly || !gd._fullLayout) return;
    var meta = gd.layout.meta.billetes;
    if (gd !== S.gd || meta.id !== S.id) {             // figura nueva (otro periodo o modo)
      S.gd = gd; S.id = meta.id; S.meta = meta; L = meta.lienzo; S.reloj = 0; S.ultimo = null;
      chips();
      prepararFrame(0, true);
      return;
    }
    var dt = S.ultimo == null ? 0 : Math.min(ahora - S.ultimo, 100);
    if (dt && dt < 1000 / 30) return;                  // ~30 cuadros por segundo bastan y alivian a plotly
    S.ultimo = ahora;
    if (!S.rep) return;
    var sz = gd._fullLayout._size;
    S.fpx = Math.min(sz.w / L.W, sz.h / 528);
    S.reloj += dt * S.vel;
    var C = S.meta.constantes, enFrame = S.reloj - S.inicio;
    while (S.emisiones.length && S.emisiones[0].t <= enFrame) {
      var e = S.emisiones.shift();
      S.billetes.push({ d: e.d, t0: S.inicio + e.t, oscila: Math.random() * Math.PI * 2 });
    }
    dibujar();
    if (enFrame >= C.FRAME_MS + C.PAUSA_MS) prepararFrame((S.idx + 1) % S.meta.grupos.length, true);
  }

  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest("#mapa-pausa");
    if (!b) return;
    S.rep = !S.rep;
    S.ultimo = null;
    b.textContent = S.rep ? "⏸ Pausa" : "▶ Reproducir";
  });
  document.addEventListener("change", function (ev) {
    if (ev.target && ev.target.id === "mapa-velocidad") S.vel = parseFloat(ev.target.value) || 1;
  });
  requestAnimationFrame(cuadro);
})();
