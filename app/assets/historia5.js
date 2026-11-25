/* Historia del equipo 5: las figuras miden 1100 px; si la ventana es más angosta, se reducen completas (sin cortarse). */
(function () {
  var ANCHO = 1100;
  function ajusta() {
    document.querySelectorAll(".h5-figura-fija").forEach(function (cont) {
      var g = cont.firstElementChild;
      if (!g) return;
      var disponible = cont.clientWidth - 12;
      var s = disponible > 0 ? Math.min(1, disponible / ANCHO) : 1;
      g.style.transformOrigin = "0 0";
      g.style.transform = s < 1 ? "scale(" + s + ")" : "";
      cont.style.overflow = "hidden";
      cont.style.height = s < 1 ? Math.ceil(g.offsetHeight * s + 8) + "px" : "";
    });
  }
  var espera;
  function pronto() { clearTimeout(espera); espera = setTimeout(ajusta, 80); }
  window.addEventListener("resize", pronto);
  window.addEventListener("load", pronto);
  new MutationObserver(pronto).observe(document.documentElement, { childList: true, subtree: true });
})();
