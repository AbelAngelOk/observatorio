/* Cuentas de usuario: header, ingreso, registro y perfil.
 *
 * Se apoya en window.Router (que expone index.html) porque el listener de
 * [data-view] del sitio se engancha una sola vez al arrancar: los botones que
 * este archivo inyecta despues no tendrian handler propio.
 */
(function () {
  "use strict";

  var usuario = null;                 // null = sesion cerrada
  var slot = document.getElementById("auth-slot");

  // ---------------------------------------------------------------- API
  function api(metodo, url, cuerpo) {
    return fetch(url, {
      method: metodo,
      headers: cuerpo ? { "Content-Type": "application/json" } : {},
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      credentials: "same-origin"      // manda la cookie de sesion
    }).then(function (res) {
      if (res.status === 204) return null;
      return res.json().catch(function () { return null; }).then(function (data) {
        if (!res.ok) {
          throw new Error((data && data.detail) || "No se pudo completar la operación.");
        }
        return data;
      });
    });
  }
  window.ApiCuenta = { api: api, quienSoy: function () { return usuario; } };

  // ---------------------------------------------------------------- Header
  function pintarHeader() {
    slot.textContent = "";
    var btn = document.createElement("button");
    btn.className = "navlink";
    if (usuario) {
      btn.textContent = usuario.nombre_completo.split(" ")[0];
      btn.title = usuario.email;
      btn.addEventListener("click", function () { verPerfil(); });
    } else {
      btn.textContent = "Ingresar";
      btn.addEventListener("click", function () { Router.navegar("/cuenta"); });
    }
    slot.appendChild(btn);
  }

  function setUsuario(u) {
    usuario = u;
    pintarHeader();
    // Avisa a cursos.js para que refresque tildes y progreso.
    document.dispatchEvent(new CustomEvent("sesion-cambio", { detail: u }));
  }

  // ---------------------------------------------------------------- Formularios
  function mostrarError(form, msg) {
    var box = form.querySelector(".form-error");
    box.textContent = msg;
    box.hidden = false;
  }
  function limpiarMensajes(form) {
    var e = form.querySelector(".form-error"); if (e) e.hidden = true;
    var o = form.querySelector(".form-ok"); if (o) o.hidden = true;
  }
  function datosDe(form) {
    var d = {};
    new FormData(form).forEach(function (v, k) { d[k] = v; });
    return d;
  }

  var formLogin = document.getElementById("form-login");
  var formRegistro = document.getElementById("form-registro");

  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      document.querySelectorAll(".tab").forEach(function (t) { t.classList.remove("activo"); });
      tab.classList.add("activo");
      var esLogin = tab.dataset.form === "login";
      formLogin.hidden = !esLogin;
      formRegistro.hidden = esLogin;
      limpiarMensajes(formLogin); limpiarMensajes(formRegistro);
    });
  });

  function tras(form, promesa) {
    var boton = form.querySelector("button[type=submit]");
    boton.disabled = true;
    return promesa
      .then(function (u) {
        setUsuario(u);
        form.reset();
        // Si vino desde un capitulo queriendo marcar progreso, "vuelta" ya es
        // la URL real de ese capitulo (la guardo cursos.js) -- navegar ahi
        // alcanza, el router normal se encarga de abrirlo.
        var vuelta = sessionStorage.getItem("volver_a");
        sessionStorage.removeItem("volver_a");
        Router.navegar(vuelta || "/cursos");
      })
      .catch(function (err) { mostrarError(form, err.message); })
      .finally(function () { boton.disabled = false; });
  }

  formLogin.addEventListener("submit", function (e) {
    e.preventDefault(); limpiarMensajes(formLogin);
    tras(formLogin, api("POST", "/api/auth/login", datosDe(formLogin)));
  });

  formRegistro.addEventListener("submit", function (e) {
    e.preventDefault(); limpiarMensajes(formRegistro);
    tras(formRegistro, api("POST", "/api/auth/registro", datosDe(formRegistro)));
  });

  // ---------------------------------------------------------------- Perfil
  function verPerfil() {
    if (!usuario) { Router.navegar("/cuenta", { reemplazar: true }); return; }
    Router.fijarRuta("/perfil");

    var ficha = document.getElementById("perfil-datos");
    ficha.innerHTML = "";
    [["Nombre", usuario.nombre_completo], ["Email", usuario.email]].forEach(function (par) {
      var f = document.createElement("div"); f.className = "fila";
      var a = document.createElement("span"); a.textContent = par[0];
      var b = document.createElement("span"); b.textContent = par[1];
      f.appendChild(a); f.appendChild(b); ficha.appendChild(f);
    });
    var salir = document.createElement("button");
    salir.className = "btn-sec"; salir.textContent = "Cerrar sesión";
    salir.style.marginTop = "16px";
    salir.addEventListener("click", function () {
      api("POST", "/api/auth/logout").then(function () {
        setUsuario(null);
        Router.navegar("/");
      });
    });
    ficha.appendChild(salir);

    var cont = document.getElementById("perfil-progreso");
    cont.textContent = "Cargando…";
    api("GET", "/api/progreso").then(function (p) {
      cont.innerHTML = "";
      Object.keys(p).forEach(function (slug) {
        var d = p[slug];
        var barra = document.createElement("div"); barra.className = "barra";
        var i = document.createElement("i"); i.style.width = d.porcentaje + "%";
        barra.appendChild(i);
        var txt = document.createElement("div"); txt.className = "barra-txt";
        txt.textContent = d.completados.length + " de " + d.total + " capítulos · " + d.porcentaje + "%";
        cont.appendChild(barra); cont.appendChild(txt);
      });
    }).catch(function () { cont.textContent = "No se pudo cargar el progreso."; });

    Router.mostrarVista("perfil");
  }
  window.verPerfil = verPerfil;

  var formPass = document.getElementById("form-password");
  formPass.addEventListener("submit", function (e) {
    e.preventDefault(); limpiarMensajes(formPass);
    var boton = formPass.querySelector("button[type=submit]");
    boton.disabled = true;
    api("POST", "/api/auth/password", datosDe(formPass))
      .then(function () {
        formPass.reset();
        formPass.querySelector(".form-ok").hidden = false;
      })
      .catch(function (err) { mostrarError(formPass, err.message); })
      .finally(function () { boton.disabled = false; });
  });

  // ---------------------------------------------------------------- Ruta /perfil
  // El router de index.html no decide esta vista solo: /perfil necesita saber
  // si hay sesion antes de mostrar algo (o redirige a /cuenta), y eso recien
  // se sabe cuando resuelve el chequeo de "Arranque" de mas abajo. Si el
  // evento llega antes de esa respuesta (carga directa de /perfil), se guarda
  // el pedido y se resuelve apenas se sepa.
  var sesionResuelta = false;
  var quierePerfil = false;
  document.addEventListener("ruta-perfil", function () {
    quierePerfil = true;
    if (sesionResuelta) verPerfil();
  });

  // ---------------------------------------------------------------- Arranque
  // Preguntamos si hay sesion viva (la cookie es httpOnly: el JS no puede verla).
  api("GET", "/api/auth/yo")
    .then(function (u) { setUsuario(u); })
    .catch(function () { setUsuario(null); })
    .finally(function () {
      sesionResuelta = true;
      if (quierePerfil) verPerfil();
    });
})();
