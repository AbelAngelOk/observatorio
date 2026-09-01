/* Modulo de cursos: indice, lector de capitulos y progreso.
 *
 * El contenido llega como BLOQUES TIPADOS desde la API y se renderiza creando
 * nodos, nunca con innerHTML de un string del servidor: si manana el contenido
 * incluyera texto de un usuario, no habria forma de inyectar HTML.
 */
(function () {
  "use strict";

  var curso = null;        // curso abierto (null = estamos en el catalogo)
  var indice = 0;          // capitulo abierto
  var evaluacion = null;   // evaluacion abierta: {slug, titulo, umbral, preguntas, estado}
  var respuestas = [];     // opcion elegida por pregunta (indice, o null si no eligio)

  function api(m, u, b) { return window.ApiCuenta.api(m, u, b); }
  function hayUsuario() { return !!window.ApiCuenta.quienSoy(); }

  // Descarga un archivo via fetch (no un <a href> directo) para que la cookie
  // de sesion viaje igual que en cualquier otro request y un error del
  // servidor (403/500) se pueda mostrar en el boton en vez de bajar un
  // adjunto vacio o una pagina de error como si fuera el PDF.
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

  // ------------------------------------------------------- helpers de DOM
  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto !== undefined) n.textContent = texto;   // textContent = escapado
    return n;
  }

  // Marcado inline minimo: **negrita**. Se parte el texto y se arman nodos,
  // asi que nunca se interpreta HTML que venga en el contenido.
  function conNegritas(padre, texto) {
    texto.split(/\*\*(.+?)\*\*/g).forEach(function (parte, i) {
      if (!parte) return;
      if (i % 2) padre.appendChild(el("b", null, parte));
      else padre.appendChild(document.createTextNode(parte));
    });
    return padre;
  }

  // ------------------------------------------------------- render de bloques
  function renderBloque(b) {
    if (b.tipo === "p") return conNegritas(el("p"), b.texto);
    if (b.tipo === "h3") return el("h3", null, b.texto);
    if (b.tipo === "formula") return el("div", "bloque-formula", b.texto);
    if (b.tipo === "nota") return conNegritas(el("div", "bloque-nota"), b.texto);
    if (b.tipo === "lista") {
      var ul = el("ul");
      b.items.forEach(function (it) { ul.appendChild(conNegritas(el("li"), it)); });
      return ul;
    }
    if (b.tipo === "tablero") return renderTablero(b);
    if (b.tipo === "diagrama") return renderDiagrama(b);
    return el("p", null, "");
  }

  // ------------------------------------------------------- diagramas (SVG)
  // Pequenos esquemas inline para mostrar como se relacionan las entidades
  // (ej. Estado contiene a Nacion/Provincias/Municipios, o Estado -> Tesoro).
  // Se dibujan con SVG a mano, sin libreria: son dos formas fijas y simples.
  var SVG_NS = "http://www.w3.org/2000/svg";
  function nsEl(tag, attrs) {
    var n = document.createElementNS(SVG_NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function textoSvg(x, y, texto, opts) {
    opts = opts || {};
    var t = nsEl("text", {
      x: x, y: y, "text-anchor": opts.anchor || "middle",
      "font-family": "Inter, sans-serif", "font-size": opts.size || 13,
      "font-weight": opts.weight || 500, fill: opts.color || "var(--paper)"
    });
    t.textContent = texto;
    return t;
  }
  function cajaSvg(x, y, w, h, texto, opts) {
    opts = opts || {};
    var g = nsEl("g");
    g.appendChild(nsEl("rect", {
      x: x, y: y, width: w, height: h, rx: opts.rx || 10,
      fill: opts.fill || "var(--panel)", stroke: opts.stroke || "var(--line-strong)",
      "stroke-width": 1.4
    }));
    g.appendChild(textoSvg(x + w / 2, y + h / 2 + 5, texto, { size: opts.fsize || 13.5 }));
    return g;
  }

  // "Estado" como un conjunto grande con "Nación / Provincias / Municipios"
  // como sub-recuadros adentro, en una fila.
  function diagramaConjuntos(b) {
    var partes = b.partes || [];
    var n = Math.max(partes.length, 1);
    var W = 600, gap = 16, padTop = 44, padSide = 18, boxH = 70;
    var H = padTop + boxH + 20;
    var boxW = (W - padSide * 2 - gap * (n - 1)) / n;

    var svg = nsEl("svg", { viewBox: "0 0 " + W + " " + H });
    svg.appendChild(nsEl("rect", {
      x: 6, y: 6, width: W - 12, height: H - 12, rx: 16,
      fill: "none", stroke: "var(--gold)", "stroke-width": 1.6, "stroke-dasharray": "5,4"
    }));
    svg.appendChild(textoSvg(24, 26, b.contenedor || "", {
      anchor: "start", size: 12.5, weight: 700, color: "var(--gold)"
    }));
    partes.forEach(function (p, i) {
      var x = padSide + i * (boxW + gap);
      svg.appendChild(cajaSvg(x, padTop, boxW, boxH, p));
    });
    return svg;
  }

  // Cajas con flechas: los "nodos" sin flechas entrantes van arriba (la raiz,
  // ej. Estado), el resto abajo (ej. Tesoro, Banco Central), con una flecha
  // por cada "de -> a".
  function diagramaFlujo(b) {
    var nodos = b.nodos || [];
    var flechas = b.flechas || [];
    var tieneEntrada = {};
    flechas.forEach(function (f) { tieneEntrada[f.a] = true; });
    var raiz = nodos.filter(function (n) { return !tieneEntrada[n]; });
    var hijos = nodos.filter(function (n) { return tieneEntrada[n]; });
    if (!raiz.length) { raiz = [nodos[0]]; hijos = nodos.slice(1); }

    var W = 600, boxW = 168, boxH = 54, gapX = 26;
    var yRaiz = 14, yHijos = 116;
    var H = yHijos + boxH + 14;
    var svg = nsEl("svg", { viewBox: "0 0 " + W + " " + H });

    var defs = nsEl("defs");
    var marker = nsEl("marker", {
      id: "flecha-diagrama", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto"
    });
    marker.appendChild(nsEl("path", { d: "M0,0 L8,4 L0,8 Z", fill: "var(--paper)" }));
    defs.appendChild(marker);
    svg.appendChild(defs);

    function fila(nombres, y, opts) {
      var totalW = nombres.length * boxW + (nombres.length - 1) * gapX;
      var x0 = (W - totalW) / 2;
      var pos = {};
      nombres.forEach(function (n, i) {
        var x = x0 + i * (boxW + gapX);
        svg.appendChild(cajaSvg(x, y, boxW, boxH, n, opts));
        pos[n] = { top: { x: x + boxW / 2, y: y }, bottom: { x: x + boxW / 2, y: y + boxH } };
      });
      return pos;
    }

    var posRaiz = fila(raiz, yRaiz, { fill: "var(--panel-alt)", stroke: "var(--gold)" });
    var posHijos = fila(hijos, yHijos, {});

    // las lineas van ANTES de las cajas para que las cajas queden por encima
    var lineas = nsEl("g");
    flechas.forEach(function (f) {
      var p1 = (posRaiz[f.de] || posHijos[f.de]);
      var p2 = (posHijos[f.a] || posRaiz[f.a]);
      if (!p1 || !p2) return;
      lineas.appendChild(nsEl("line", {
        x1: p1.bottom.x, y1: p1.bottom.y, x2: p2.top.x, y2: p2.top.y,
        stroke: "var(--paper)", "stroke-width": 1.6, "marker-end": "url(#flecha-diagrama)"
      }));
    });
    svg.insertBefore(lineas, svg.firstChild.nextSibling);
    return svg;
  }

  function renderDiagrama(b) {
    var box = el("div", "bloque-diagrama");
    var svg = b.forma === "conjuntos" ? diagramaConjuntos(b)
             : b.forma === "flujo" ? diagramaFlujo(b) : null;
    if (svg) box.appendChild(svg);
    return box;
  }

  function celda(titulo, items) {
    var c = el("div", "tablero-celda");
    c.appendChild(el("h4", null, titulo));
    var ul = el("ul");
    items.forEach(function (t) { ul.appendChild(conNegritas(el("li"), t)); });
    c.appendChild(ul);
    return c;
  }

  function renderTablero(t) {
    var box = el("div", "tablero");

    var tit = el("div", "tablero-tit");
    tit.appendChild(el("b", null, "Cómo se lee: " + t.titulo));
    tit.appendChild(el("span", "unidad", t.unidad));
    box.appendChild(tit);

    var grid = el("div", "tablero-grid");
    grid.appendChild(celda("Qué suma", t.suma));
    grid.appendChild(celda("Qué resta", t.resta));
    grid.appendChild(celda("Qué incluye", t.incluye));
    grid.appendChild(celda("Qué deja afuera", t.excluye));
    box.appendChild(grid);

    var lec = el("div", "tablero-lectura");
    [["sube", "▲ Si sube: ", t.si_sube], ["baja", "▼ Si baja: ", t.si_baja]].forEach(function (p) {
      var d = el("div", p[0]);
      d.appendChild(el("span", "flecha", p[1]));
      conNegritas(d, p[2]);
      lec.appendChild(d);
    });
    box.appendChild(lec);

    if (t.trampas && t.trampas.length) {
      var tr = el("div", "tablero-trampas");
      tr.appendChild(el("h4", null, "Trampas al leerlo"));
      var ul = el("ul");
      t.trampas.forEach(function (x) { ul.appendChild(conNegritas(el("li"), x)); });
      tr.appendChild(ul);
      box.appendChild(tr);
    }

    // Puente al sitio: leer el capitulo y despues mirar el grafico real.
    if (t.panel) {
      var pie = el("div", "tablero-lectura");
      var ver = el("button", "btn-sec", "Ver este gráfico en el sitio →");
      ver.addEventListener("click", function () {
        Router.navegar("/indicadores/" + t.panel);
      });
      pie.appendChild(ver);
      box.appendChild(pie);
    }
    return box;
  }

  // ------------------------------------------------------- catalogo de cursos
  // Landing de "Cursos": lista todos los cursos (GET /api/cursos) con su
  // progreso si hay sesion. El progreso sale de un segundo request
  // (GET /api/progreso) que se intenta siempre y se ignora si da 401 -- mas
  // simple que depender de si ApiCuenta.quienSoy() ya se resolvio a tiempo.
  function pintarCatalogo() {
    curso = null;
    Router.fijarRuta("/cursos");
    var cont = document.getElementById("cursos-lista");
    cont.textContent = "Cargando…";

    Promise.all([
      api("GET", "/api/cursos"),
      api("GET", "/api/progreso").catch(function () { return {}; })
    ]).then(function (r) {
      var lista = r[0], progresos = r[1] || {};
      cont.innerHTML = "";

      cont.appendChild(el("h2", "titulo-seccion", "Cursos"));
      cont.appendChild(el("p", "catalogo-intro",
        "Cursos cortos para aprender a leer los gráficos del observatorio, agrupados por tema."));

      var grid = el("div", "catalogo");
      lista.forEach(function (c) {
        var card = el("button", "catalogo-item");
        if (c.grupo) card.appendChild(el("div", "grupo", c.grupo));
        card.appendChild(el("h3", null, c.titulo));
        card.appendChild(el("p", "bajada", c.resumen));

        var p = progresos[c.slug];
        if (p) {
          var barra = el("div", "barra");
          var i = el("i"); i.style.width = p.porcentaje + "%";
          barra.appendChild(i);
          card.appendChild(barra);
          card.appendChild(el("div", "meta",
            p.completados.length + " de " + p.total + " capítulos · " + p.porcentaje + "%"));
        } else {
          card.appendChild(el("div", "meta",
            c.n_capitulos + " capítulos · ~" + c.minutos + " min de lectura"));
        }
        card.addEventListener("click", function () { abrirCurso(c.slug); });
        grid.appendChild(card);
      });
      cont.appendChild(grid);
    }).catch(function () { cont.textContent = "No se pudieron cargar los cursos."; });
  }

  function abrirCurso(slug) {
    return api("GET", "/api/cursos/" + slug).then(function (c) {
      curso = c;
      pintarIndice();
      return c;
    });
  }

  // ------------------------------------------------------- indice del curso
  function pintarIndice() {
    Router.fijarRuta("/cursos/" + curso.slug);
    var cont = document.getElementById("cursos-lista");
    cont.innerHTML = "";

    var volver = el("button", "volver-catalogo", "‹ Cursos");
    volver.addEventListener("click", pintarCatalogo);
    cont.appendChild(volver);

    var card = el("div", "curso-card");
    card.appendChild(el("h2", null, curso.titulo));
    card.appendChild(el("p", "bajada", curso.resumen));
    card.appendChild(el("div", "curso-meta",
      curso.n_capitulos + " capítulos · ~" + curso.minutos + " min de lectura · " +
      "para leer los gráficos del grupo « " + curso.grupo + " »"));

    var p = curso.progreso;
    if (p) {
      var barra = el("div", "barra");
      var i = el("i"); i.style.width = p.porcentaje + "%";
      barra.appendChild(i);
      card.appendChild(barra);
      card.appendChild(el("div", "barra-txt",
        p.completados.length + " de " + p.total + " completados · " + p.porcentaje + "%"));

      if (p.porcentaje === 100 && curso.evaluacion) {
        // Curso terminado y con evaluacion cargada (el backend solo la manda
        // en este caso): la accion natural ya no es "seguir leyendo", es
        // rendir o descargar lo que ya se gano.
        var ev = curso.evaluacion;
        if (ev.aprobado) {
          card.appendChild(el("div", "barra-txt",
            "Evaluación aprobada con " + ev.puntaje + "%."));
          var descargar = el("button", "cta", "Descargar certificado");
          descargar.style.marginTop = "16px";
          descargar.addEventListener("click", function () { descargarCertificado(curso.slug, descargar); });
          card.appendChild(descargar);
        } else {
          var rendir = el("button", "cta",
            ev.intentos > 0 ? "Volver a rendir la evaluación" : "Rendir la evaluación");
          rendir.style.marginTop = "16px";
          rendir.addEventListener("click", function () { abrirEvaluacion(curso.slug); });
          card.appendChild(rendir);
        }
      } else {
        var seguir = el("button", "cta", p.completados.length ? "Continuar donde quedaste" : "Empezar el curso");
        seguir.style.marginTop = "16px";
        seguir.addEventListener("click", function () {
          var slug = p.siguiente || curso.capitulos[0].slug;
          abrirCapitulo(curso.capitulos.findIndex(function (c) { return c.slug === slug; }));
        });
        card.appendChild(seguir);
      }
    } else {
      var empezar = el("button", "cta", "Empezar el curso");
      empezar.style.marginTop = "8px";
      empezar.addEventListener("click", function () { abrirCapitulo(0); });
      card.appendChild(empezar);

      var aviso = el("div", "aviso-login");
      aviso.appendChild(document.createTextNode("El curso es de lectura libre. "));
      var link = el("button", null, "Creá una cuenta");
      link.addEventListener("click", function () { Router.navegar("/cuenta"); });
      aviso.appendChild(link);
      aviso.appendChild(document.createTextNode(" si querés que recordemos qué capítulos completaste."));
      card.appendChild(aviso);
    }

    var ul = el("ul", "cap-lista");
    curso.capitulos.forEach(function (cap, idx) {
      var li = el("li");
      var btn = el("button", "cap-item" + (cap.completado ? " hecho" : ""));
      var tick = el("span", "tick", "✓");
      btn.appendChild(tick);
      btn.appendChild(el("span", null, cap.titulo));
      btn.appendChild(el("span", "cap-min", cap.minutos + " min"));
      btn.addEventListener("click", function () { abrirCapitulo(idx); });
      li.appendChild(btn);
      ul.appendChild(li);
    });
    card.appendChild(ul);
    cont.appendChild(card);
  }

  // ------------------------------------------------------- lector
  function abrirCapitulo(idx) {
    if (idx < 0 || idx >= curso.capitulos.length) return;
    indice = idx;
    var cap = curso.capitulos[idx];
    Router.fijarRuta("/cursos/" + curso.slug + "/capitulos/" + cap.slug);
    var cont = document.getElementById("capitulo-cuerpo");
    cont.innerHTML = "";

    var art = el("div", "lector");

    var migas = el("div", "migas");
    var volver = el("button", null, "‹ " + curso.titulo);
    volver.addEventListener("click", verIndice);
    migas.appendChild(volver);
    migas.appendChild(document.createTextNode("  ·  capítulo " + (idx + 1) + " de " + curso.capitulos.length));
    art.appendChild(migas);

    art.appendChild(el("h1", null, cap.titulo));
    art.appendChild(el("p", "resumen", cap.resumen));
    cap.bloques.forEach(function (b) { art.appendChild(renderBloque(b)); });

    // Pie: anterior / marcar / siguiente
    var pie = el("div", "lector-pie");
    var ant = el("button", "btn-sec", "← Anterior");
    ant.disabled = idx === 0;
    ant.addEventListener("click", function () { abrirCapitulo(idx - 1); });
    pie.appendChild(ant);

    var esUltimo = idx === curso.capitulos.length - 1;
    var sig = el("button", "cta", esUltimo ? "Terminar el curso ✓" : "Siguiente →");
    sig.addEventListener("click", function () {
      marcar(cap.slug, true).then(function () {
        if (esUltimo) verIndice(); else abrirCapitulo(idx + 1);
      });
    });
    pie.appendChild(sig);
    art.appendChild(pie);

    if (!hayUsuario()) {
      var aviso = el("div", "aviso-login");
      aviso.appendChild(document.createTextNode("Podés seguir leyendo sin cuenta. "));
      var link = el("button", null, "Ingresá");
      link.addEventListener("click", function () {
        // Guarda la URL real del capitulo: cuenta.js, despues del login, solo
        // hace Router.navegar(vuelta) -- no necesita saber nada de cursos.
        sessionStorage.setItem("volver_a", "/cursos/" + curso.slug + "/capitulos/" + cap.slug);
        Router.navegar("/cuenta");
      });
      aviso.appendChild(link);
      aviso.appendChild(document.createTextNode(" para que se guarde tu progreso."));
      art.appendChild(aviso);
    } else if (cap.completado) {
      var hecho = el("div", "aviso-login");
      hecho.appendChild(document.createTextNode("Ya completaste este capítulo. "));
      var des = el("button", null, "Desmarcar");
      des.addEventListener("click", function () { marcar(cap.slug, false).then(function () { abrirCapitulo(idx); }); });
      hecho.appendChild(des);
      art.appendChild(hecho);
    }

    cont.appendChild(art);
    Router.mostrarVista("capitulo");
    window.scrollTo(0, 0);
  }

  function marcar(slug, completado) {
    var cap = curso.capitulos.find(function (c) { return c.slug === slug; });
    if (!hayUsuario()) { return Promise.resolve(); }   // sin cuenta no hay progreso que guardar
    var url = "/api/cursos/" + curso.slug + "/capitulos/" + slug + "/completado";
    return api(completado ? "PUT" : "DELETE", url)
      .then(function (p) { cap.completado = completado; curso.progreso = p; })
      .catch(function () { /* si falla, seguimos leyendo igual */ });
  }

  function verIndice() { pintarIndice(); Router.mostrarVista("cursos"); window.scrollTo(0, 0); }

  // ------------------------------------------------------- evaluacion
  // El servidor rechaza esto con 403 si el curso no esta 100% completo, y con
  // 401 si no hay sesion (ver rutas_cursos.py) -- en los dos casos no hay
  // nada que rendir todavia, asi que se vuelve al indice del curso, que ya
  // explica que hace falta para avanzar.
  function abrirEvaluacion(slug) {
    return api("GET", "/api/cursos/" + slug + "/evaluacion")
      .then(function (ev) {
        evaluacion = { slug: slug, titulo: ev.titulo, umbral: ev.umbral,
                        preguntas: ev.preguntas, estado: ev.estado };
        respuestas = ev.preguntas.map(function () { return null; });
        Router.fijarRuta("/cursos/" + slug + "/evaluacion");
        pintarEvaluacion();
      })
      .catch(function () { abrirCurso(slug); });
  }

  function pintarEvaluacion() {
    var cont = document.getElementById("evaluacion-cuerpo");
    cont.innerHTML = "";
    var art = el("div", "evaluacion");

    var migas = el("div", "migas");
    var volver = el("button", null, "‹ " + evaluacion.titulo);
    volver.addEventListener("click", function () { abrirCurso(evaluacion.slug); });
    migas.appendChild(volver);
    art.appendChild(migas);

    art.appendChild(el("h1", null, "Evaluación: " + evaluacion.titulo));
    art.appendChild(el("p", "umbral",
      "Elegí una opción por pregunta. Necesitás " + evaluacion.umbral +
      "% o más de respuestas correctas para aprobar y habilitar el certificado."));
    if (evaluacion.estado.intentos > 0 && !evaluacion.estado.aprobado) {
      art.appendChild(el("p", "umbral",
        "Tu último intento fue " + evaluacion.estado.puntaje + "%. Podés volver a intentarlo."));
    }

    var errorBox = el("div", "form-error", "Respondé todas las preguntas antes de enviar.");
    errorBox.hidden = true;

    evaluacion.preguntas.forEach(function (p, i) {
      var box = el("div", "pregunta");
      box.appendChild(el("div", "enunciado", p.enunciado));
      var ops = el("div", "opciones");
      p.opciones.forEach(function (texto, j) {
        var btn = el("button", "opcion");
        btn.type = "button";
        btn.appendChild(el("span", "marca"));
        btn.appendChild(el("span", null, texto));
        btn.addEventListener("click", function () {
          respuestas[i] = j;
          box.classList.remove("falta");
          ops.querySelectorAll(".opcion").forEach(function (o) { o.classList.remove("elegida"); });
          btn.classList.add("elegida");
        });
        ops.appendChild(btn);
      });
      box.appendChild(ops);
      art.appendChild(box);
    });

    art.appendChild(errorBox);

    var enviar = el("button", "cta", "Enviar respuestas");
    enviar.addEventListener("click", function () {
      var faltan = respuestas.indexOf(null) !== -1;
      if (faltan) {
        errorBox.textContent = "Respondé todas las preguntas antes de enviar.";
        errorBox.hidden = false;
        art.querySelectorAll(".pregunta").forEach(function (box, i) {
          box.classList.toggle("falta", respuestas[i] === null);
        });
        window.scrollTo(0, 0);
        return;
      }
      errorBox.hidden = true;
      enviar.disabled = true;
      api("POST", "/api/cursos/" + evaluacion.slug + "/evaluacion", { respuestas: respuestas })
        .then(function (r) { pintarResultado(r); })
        .catch(function () {
          errorBox.textContent = "No se pudo enviar la evaluación. Probá de nuevo.";
          errorBox.hidden = false;
          enviar.disabled = false;
        });
    });
    art.appendChild(enviar);

    cont.appendChild(art);
    Router.mostrarVista("evaluacion");
    window.scrollTo(0, 0);
  }

  function pintarResultado(r) {
    var cont = document.getElementById("evaluacion-cuerpo");
    cont.innerHTML = "";
    var art = el("div", "evaluacion");

    var migas = el("div", "migas");
    var volver = el("button", null, "‹ " + evaluacion.titulo);
    volver.addEventListener("click", function () { abrirCurso(evaluacion.slug); });
    migas.appendChild(volver);
    art.appendChild(migas);

    var box = el("div", "resultado " + (r.aprobado ? "aprobado" : "rechazado"));
    box.appendChild(el("div", "puntaje", r.puntaje + "%"));
    box.appendChild(el("div", "msg",
      (r.aprobado ? "Aprobado. " : "No alcanzó. ") +
      r.correctas + " de " + r.total + " correctas · se necesita " + r.umbral + "% o más."));

    var acciones = el("div", "acciones");
    if (r.aprobado) {
      var descargar = el("button", "cta", "Descargar certificado");
      descargar.addEventListener("click", function () { descargarCertificado(evaluacion.slug, descargar); });
      acciones.appendChild(descargar);
    } else {
      var reintentar = el("button", "cta", "Volver a intentar");
      reintentar.addEventListener("click", function () { abrirEvaluacion(evaluacion.slug); });
      acciones.appendChild(reintentar);
    }
    var volverCurso = el("button", "btn-sec", "Volver al curso");
    volverCurso.addEventListener("click", function () { abrirCurso(evaluacion.slug); });
    acciones.appendChild(volverCurso);
    box.appendChild(acciones);

    art.appendChild(box);
    cont.appendChild(art);
    Router.mostrarVista("evaluacion");
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------- carga y eventos

  // El router de index.html no sabe nada de cursos/capitulos -- cuando la URL
  // cae bajo /cursos, delega aca via este evento con lo que pudo leer de la
  // URL. Cubre los tres casos a la vez: clic en "Cursos" del nav, atras/
  // adelante del navegador, y abrir un link a un curso o capitulo directo
  // (recarga de pagina incluida). Por eso ya no hace falta cargar nada de
  // arranque: si el usuario nunca visita /cursos, este archivo no pide nada.
  document.addEventListener("ruta-cursos", function (e) {
    var slugCurso = e.detail.curso, slugCap = e.detail.capitulo, esEvaluacion = e.detail.evaluacion;
    if (!slugCurso) { pintarCatalogo(); return; }
    if (esEvaluacion) { abrirEvaluacion(slugCurso); return; }
    abrirCurso(slugCurso).then(function () {
      if (!slugCap) return;                      // abrirCurso ya pinto el indice del curso
      var i = curso.capitulos.findIndex(function (c) { return c.slug === slugCap; });
      if (i >= 0) abrirCapitulo(i);
    });
  });

  // Al iniciar o cerrar sesion: refrescar lo que se este viendo para que
  // traiga o limpie el progreso.
  document.addEventListener("sesion-cambio", function () {
    if (curso) abrirCurso(curso.slug); else if (location.pathname.indexOf("/cursos") === 0) pintarCatalogo();
  });
})();
