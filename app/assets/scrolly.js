// Lectura guiada: cuando un paso de texto llega al centro de la pantalla, se publica su número en el
// dcc.Store de su sección (data-store) y la figura resalta lo que cuenta ese paso. También revela con un
// desvanecido los bloques marcados con .revelar.
(function () {
  function publicar(paso) {
    var store = paso.getAttribute("data-store");
    var n = parseInt(paso.getAttribute("data-paso"), 10);
    if (!store || !window.dash_clientside || !window.dash_clientside.set_props) return;
    if (paso.dataset.publicado === "1" && paso.classList.contains("activo")) return;
    document.querySelectorAll('.paso[data-store="' + store + '"]').forEach(function (p) {
      p.classList.remove("activo");
      p.dataset.publicado = "0";
    });
    paso.classList.add("activo");
    paso.dataset.publicado = "1";
    window.dash_clientside.set_props(store, { data: n });
  }

  var obsPasos = new IntersectionObserver(function (entradas) {
    entradas.forEach(function (e) { if (e.isIntersecting) publicar(e.target); });
  }, { rootMargin: "-45% 0px -45% 0px" });

  var obsRevelar = new IntersectionObserver(function (entradas) {
    entradas.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("visible"); obsRevelar.unobserve(e.target); }
    });
  }, { threshold: 0.15 });

  // Dash pinta el layout después de cargar la página: se observan los elementos conforme aparecen.
  function enganchar() {
    document.querySelectorAll(".paso:not([data-observado])").forEach(function (p) {
      p.setAttribute("data-observado", "1");
      obsPasos.observe(p);
    });
    document.querySelectorAll(".revelar:not([data-observado])").forEach(function (r) {
      r.setAttribute("data-observado", "1");
      obsRevelar.observe(r);
    });
  }
  new MutationObserver(enganchar).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener("DOMContentLoaded", enganchar);
})();
