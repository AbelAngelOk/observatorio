/* Certificaciones: seccion aparte de "Cursos" -- un panel por usuario con el
 * estado de la evaluacion de cada curso y el boton de descarga del PDF una
 * vez aprobado. No duplica el examen en si (eso lo maneja cursos.js, que ya
 * tiene el contenido del curso cargado); esta pantalla es la puerta de
 * entrada y el resumen.
 */
(function () {
  "use strict";

  function api(m, u, b) { return window.ApiCuenta.api(m, u, b); }

  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto !== undefined) n.textContent = texto;
    return n;
  }

  // Misma logica que cursos.js: fetch + blob (no un <a href> directo) para
  // que la cookie de sesion viaje y un error del servidor no baje un PDF roto.
  function descargarCertificado(slug, boton) {
    var original = boton.textContent;
    boton.disabled = true; boton.textContent = "Generando…";
    fetch("/api/cursos/" + slug + "/certificado", { credentials: "same-origin" })
      .then(function (res) { if (!res.ok) throw new Error(); return res.blob(); })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url; a.download = "certificado-" + slug + ".pdf";
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        boton.disabled = false; boton.textContent = original;
      })
      .catch(function () {
        boton.disabled = false; boton.textContent = "No se pudo descargar, reintentar";
      });
  }

  function pintar(lista) {
    var cont = document.getElementById("certificaciones-lista");
    cont.innerHTML = "";
    cont.appendChild(el("h2", "titulo-seccion", "Certificaciones"));
    cont.appendChild(el("p", "catalogo-intro",
      "Terminá un curso, rendí su evaluación y, si aprobás, descargá el certificado con tu nombre."));

    if (!lista.length) {
      cont.appendChild(el("p", "catalogo-intro", "Todavía no hay cursos con evaluación disponible."));
      return;
    }

    var grid = el("div", "cert-grid");
    lista.forEach(function (c) {
      var card = el("div", "cert-item");
      if (c.grupo) card.appendChild(el("div", "grupo", c.grupo));
      card.appendChild(el("h3", null, c.titulo));

      if (c.evaluacion.aprobado) {
        card.appendChild(el("span", "cert-badge aprobado", "Aprobado · " + c.evaluacion.puntaje + "%"));
      } else if (c.evaluacion.intentos > 0) {
        card.appendChild(el("span", "cert-badge pendiente",
          "Último intento: " + c.evaluacion.puntaje + "% (no alcanzó el " + c.umbral + "%)"));
      } else {
        card.appendChild(el("span", "cert-badge pendiente", "Sin rendir"));
      }

      card.appendChild(el("div", "estado",
        c.progreso.completados.length + " de " + c.progreso.total + " capítulos completados" +
        (c.curso_completo ? "" : " — hay que terminar el curso para poder rendir")));

      if (c.evaluacion.aprobado) {
        var descargar = el("button", "cta", "Descargar certificado");
        descargar.addEventListener("click", function () { descargarCertificado(c.slug, descargar); });
        card.appendChild(descargar);
      } else if (c.curso_completo) {
        var rendir = el("button", "cta", c.evaluacion.intentos > 0 ? "Volver a rendir" : "Rendir evaluación");
        rendir.addEventListener("click", function () { Router.navegar("/cursos/" + c.slug + "/evaluacion"); });
        card.appendChild(rendir);
      } else {
        var ver = el("button", "btn-sec", "Ir al curso");
        ver.addEventListener("click", function () { Router.navegar("/cursos/" + c.slug); });
        card.appendChild(ver);
      }

      grid.appendChild(card);
    });
    cont.appendChild(grid);
  }

  // "/api/certificaciones" exige sesion y el servidor es quien decide eso
  // leyendo la cookie -- no hay que esperar a que cuenta.js resuelva su propio
  // chequeo de sesion (como si hace falta para /perfil): si la respuesta
  // falla, simplemente no hay sesion, y se redirige a /cuenta.
  document.addEventListener("ruta-certificaciones", function () {
    api("GET", "/api/certificaciones")
      .then(function (lista) {
        pintar(lista);
        Router.mostrarVista("certificaciones");
        window.scrollTo(0, 0);
      })
      .catch(function () { Router.navegar("/cuenta", { reemplazar: true }); });
  });
})();
