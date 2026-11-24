/* Equipo 6 · funciones del navegador para las escenas.
   Abrir y cerrar corre en el navegador (sin ir al servidor) para que la
   animación sea fluida; el servidor solo entrega la figura la primera vez. */
(function () {
  "use strict";

  function disparo() {
    var ctx = window.dash_clientside && window.dash_clientside.callback_context;
    var t = ctx && ctx.triggered && ctx.triggered[0];
    return t ? t.prop_id : "";
  }

  function prefijo(id, sufijo) {
    var i = id.indexOf(sufijo);
    return i === -1 ? null : id.slice(0, i);
  }

  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    e6: {
      // Ventana emergente: se abre con "-abrir" y se cierra con "-cerrar" o el velo.
      ventana: function () {
        var id = disparo();
        var abrir = id.indexOf("-abrir.") !== -1;
        document.body.classList.toggle("e6-sin-scroll", abrir);
        if (abrir) {
          var p = prefijo(id, "-abrir.");
          setTimeout(function () {
            var b = document.getElementById(p + "-cerrar");
            if (b) { b.focus({ preventScroll: true }); }
          }, 60);
        }
        return abrir ? "e6-ventana e6-abierta" : "e6-ventana";
      },

      // Puertas: el botón de la escena alterna; "-cerrar" siempre cierra.
      puertas: function (nAbrir, nCerrar, clase) {
        var id = disparo();
        clase = clase || "";
        var base = clase.replace(/\s*e6-abierto/g, "");
        var estaba = clase.indexOf("e6-abierto") !== -1;
        var abrir = id.indexOf("-abrir.") !== -1 ? !estaba : false;
        if (abrir) {
          var p = prefijo(id, "-abrir.");
          setTimeout(function () {
            var panel = document.getElementById(p + "-revelado");
            if (panel) { panel.scrollIntoView({ behavior: "smooth", block: "start" }); }
          }, 1250);
        }
        return abrir ? base + " e6-abierto" : base;
      },

      // Deslizador monte -> ciudad: pasa el avance a una variable CSS.
      avance: function (arrastre, valor, clase) {
        var desdeValor = disparo().indexOf(".value") !== -1;
        var v = Math.max(0, Math.min(100, Number(desdeValor ? valor : arrastre) || 0));
        clase = (clase || "").replace(/\s*e6-completo/g, "");
        return [{ "--avance": v / 100 }, v >= 100 ? clase + " e6-completo" : clase];
      },

      // Botón "Ver la gráfica": lleva el deslizador al final.
      completar: function () {
        return 100;
      }
    }
  });

  // Escape cierra la ventana o las puertas abiertas.
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") { return; }
    var b = document.querySelector(".e6-ventana.e6-abierta .e6-cerrar, .e6-abierto .e6-revelado .e6-cerrar");
    if (b) { b.click(); }
  });
})();
