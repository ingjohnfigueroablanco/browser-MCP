"""MCP tool surface. Thin facade over BrowserManager; each call returns text/JSON.

Action tools return the fresh snapshot so the agent avoids an extra round-trip.

Escape-hatch tools for full browser control (no new Python files needed):
  js_eval   — run arbitrary JavaScript in the page (scroll, drag, custom events, …)
  cdp_call  — call any Chrome DevTools Protocol method directly
  set_value — set input value the React/Vue/Angular-safe way (native JS setter)
  scroll    — convenience wrapper around window.scrollBy / element.scrollIntoView
"""

from __future__ import annotations

import json

from .server import get_browser, mcp


def _format_snapshot(result: dict) -> str:
    return (
        f"snapshot_id={result['snapshot_id']} refs={result['refs']}\n"
        f"{result['snapshot']}"
    )


@mcp.tool()
async def browser_start(headless: bool = False) -> str:
    """Lanza (o reconecta) Chrome con CDP. Debe llamarse antes que las demas tools."""
    return json.dumps(await get_browser().start(headless=headless), ensure_ascii=False)


@mcp.tool()
async def navigate(url: str, wait: str = "load") -> str:
    """Navega a una URL y espera (none|load|networkidle). Devuelve snapshot."""
    b = get_browser()
    await b.navigate(url, wait=wait)
    return _format_snapshot(await b.snapshot())


@mcp.tool()
async def snapshot(interactive_only: bool = True) -> str:
    """Captura el arbol de accesibilidad como texto compacto con refs @eN."""
    return _format_snapshot(await get_browser().snapshot(interactive_only=interactive_only))


@mcp.tool()
async def click(ref: str) -> str:
    """Clic humano (por coordenadas) sobre el elemento @eN. Devuelve snapshot nuevo."""
    return _format_snapshot(await get_browser().click(ref))


@mcp.tool()
async def js_click(ref: str) -> str:
    """JS element.click() directo — mas confiable para React SPAs y Angular.
    Usar cuando click() no dispara el handler (ej: botones con React 17+ delegation)."""
    return _format_snapshot(await get_browser().js_click(ref))


@mcp.tool()
async def fill(ref: str, text: str, submit: bool = False) -> str:
    """Enfoca @eN, limpia y escribe text. submit=True presiona Enter al final."""
    return _format_snapshot(await get_browser().fill(ref, text, submit=submit))


@mcp.tool()
async def press_key(key: str, ref: str | None = None) -> str:
    """Presiona una tecla nombrada (Enter, Tab, ArrowDown...). ref opcional para enfocar."""
    return _format_snapshot(await get_browser().press_key(key, ref))


@mcp.tool()
async def select_option(ref: str, value: str | None = None, label: str | None = None) -> str:
    """Selecciona una opcion de un <select> por value o por label visible."""
    return _format_snapshot(await get_browser().select_option(ref, value, label))


@mcp.tool()
async def hover(ref: str) -> str:
    """Mueve el mouse al centro de @eN (dispara menus/tooltips hover)."""
    return _format_snapshot(await get_browser().hover(ref))


@mcp.tool()
async def get_text(ref: str | None = None) -> str:
    """Devuelve innerText del elemento @eN, o del body completo si ref es None."""
    return await get_browser().get_text(ref)


@mcp.tool()
async def wait_for(text: str | None = None, timeout_ms: int = 10000) -> str:
    """Espera hasta que aparezca text en la pagina (o agota timeout_ms)."""
    return json.dumps(await get_browser().wait_for(text, timeout_ms), ensure_ascii=False)


@mcp.tool()
async def read_console(clear: bool = False) -> str:
    """Devuelve los mensajes de consola capturados. clear=True vacia el buffer."""
    return "\n".join(get_browser().read_console(clear)) or "(sin mensajes)"


@mcp.tool()
async def read_network(filter: str | None = None, clear: bool = False) -> str:
    """Lista requests capturadas (opcional filtra por substring de URL)."""
    entries = get_browser().read_network(filter, clear)
    lines = [
        f"{e.method} {e.status if e.status is not None else '-'} "
        f"{'FAIL ' if e.failed else ''}{e.url}"
        for e in entries
    ]
    return "\n".join(lines) or "(sin requests)"


@mcp.tool()
async def screenshot(full_page: bool = False) -> str:
    """Escape hatch: PNG en base64 (usa snapshot de texto por defecto, no esto)."""
    data = await get_browser().screenshot(full_page=full_page)
    return f"data:image/png;base64,{data}"


@mcp.tool()
async def current_url() -> str:
    """Devuelve URL y titulo actuales (barato, sin snapshot)."""
    return json.dumps(await get_browser().current_url(), ensure_ascii=False)


@mcp.tool()
async def browser_stop(kill: bool = False) -> str:
    """Cierra la conexion CDP. kill=True ademas termina el proceso Chrome."""
    return json.dumps(await get_browser().shutdown(kill=kill), ensure_ascii=False)


# ── Escape-hatch tools: full agnostic browser control ────────────────────────
# These three tools cover 100% of browser automation without adding new Python
# files for every new action type.

@mcp.tool()
async def js_eval(script: str, ref: str | None = None) -> str:
    """Ejecuta JavaScript arbitrario en la pagina. Devuelve resultado + snapshot.

    ref=None → evalua `script` como expresion en window context.
    ref=@eN  → ejecuta `script` como funcion con el elemento como `this`.

    Ejemplos basicos:
      scroll abajo:   js_eval("window.scrollBy(0, 500)")
      drag elemento:  js_eval("el.dispatchEvent(new DragEvent('dragstart',...))", ref="@e5")
      leer atributo:  js_eval("return this.getAttribute('data-id')", ref="@e12")
      click forzado:  js_eval("this.click()", ref="@e7")
      esperar async:  js_eval("return await fetch('/api').then(r=>r.json())")

    RENDIMIENTO — operaciones en lote:
      Cada tool call = un round-trip LLM. Para crear/editar/extraer N elementos,
      escribe UN loop async en JS en lugar de llamar N veces a click/fill/js_eval.

      Ejemplo — rellenar y enviar un formulario 20 veces en UNA llamada:
        js_eval(\"\"\"
          (async () => {
            const users = [
              {name:'Ana',user:'ana01',role:'Operador'},
              {name:'Luis',user:'luis02',role:'Supervisor'},
            ];
            const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
            const fire = (el,v) => { set.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true})); };
            const results = [];
            for (const u of users) {
              document.querySelector('button.agregar, [aria-label*=gregar]').click();
              await new Promise(r => setTimeout(r, 400));
              const inp = document.querySelectorAll('input:not([type=checkbox])');
              fire(inp[0], u.name); fire(inp[1], u.user);
              document.querySelector('button[type=submit], button.crear').click();
              await new Promise(r => setTimeout(r, 300));
              results.push(u.user);
            }
            return results;
          })()
        \"\"\")

      Para datasets grandes usa js_eval_loop() que inyecta items automaticamente.
    """
    result = await get_browser().js_eval(script, ref)
    lines = [f"js_result={json.dumps(result['js_result'], ensure_ascii=False)}"]
    if result["exception"]:
        lines.append(f"exception={result['exception']}")
    lines.append(_format_snapshot(result))
    return "\n".join(lines)


@mcp.tool()
async def cdp_call(method: str, params: str = "{}", use_session: bool = True) -> str:
    """Llama cualquier metodo del protocolo CDP directamente.

    method     — dominio.metodo, ej: "Input.dispatchKeyEvent", "DOM.querySelector"
    params     — JSON string con los parametros, ej: '{"type":"keyDown","key":"Enter"}'
    use_session— True (default) para el contexto de la pagina actual; False para nivel browser

    Ejemplos de acciones que no tienen tool dedicada:
      Drag & drop real:    cdp_call("Input.dispatchDragEvent", '{"type":"dragEnter",...}')
      Subir archivo:       cdp_call("DOM.setFileInputFiles", '{"files":["/ruta/archivo.pdf"]}')
      Emular dispositivo:  cdp_call("Emulation.setDeviceMetricsOverride", '{"width":375,...}')
      Interceptar red:     cdp_call("Fetch.enable", '{"patterns":[{"urlPattern":"*"}]}')
      Geolocation:         cdp_call("Emulation.setGeolocationOverride", '{"latitude":4.7,...}')
    """
    try:
        parsed = json.loads(params)
    except json.JSONDecodeError as exc:
        return f"ERROR: params no es JSON valido — {exc}"
    result = await get_browser().cdp_call(method, parsed, use_session=use_session)
    return json.dumps(result["cdp_result"], ensure_ascii=False, indent=2)


@mcp.tool()
async def set_value(ref: str, value: str) -> str:
    """Establece el valor de un input/select usando el setter nativo de JS.

    Necesario para React, Vue y Angular: los inputs controlados no responden
    a .value= directo porque el framework sobreescribe el setter. Este tool
    usa Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set
    y dispara eventos input+change para que el framework detecte el cambio.

    Usar para: date pickers, spinbuttons, selects custom, inputs con validacion.
    """
    return _format_snapshot(await get_browser().set_value(ref, value))


@mcp.tool()
async def js_eval_loop(
    items: list[dict],
    script: str,
    delay_ms: int = 300,
) -> str:
    """Ejecuta `script` una vez por cada item — UNA llamada en lugar de N.

    La variable `item` esta disponible en `script` como objeto JS plano.
    Devuelve array JSON con {ok, result, error} por item + snapshot final.

    USAR ESTO en lugar de llamar js_eval/click/fill N veces para operaciones bulk.
    Cada tool call = un round-trip LLM. Un loop aqui = 50-100x mas rapido para N>5.

    Parametros:
      items     — lista de objetos, uno por iteracion
      script    — JS a ejecutar por item; puede usar await; `item` esta en scope
      delay_ms  — espera entre iteraciones (default 300ms; bajar si la app es rapida)

    Ejemplo — crear 20 usuarios en una sola llamada:
      js_eval_loop(
        items=[
          {"name": "Ana Garcia", "user": "agarcia", "phone": "3101234567",
           "email": "ana@corp.com", "area": "TI", "role": "Operador"},
          ...
        ],
        script=\"\"\"
          document.querySelector('button[aria-label*="gregar"], button.agregar').click();
          await new Promise(r => setTimeout(r, 400));
          const inp = document.querySelectorAll('input:not([type=checkbox]):not([type=radio])');
          const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
          const fire = (el,v) => { s.call(el,v); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); };
          fire(inp[0], item.name); fire(inp[1], item.user);
          fire(inp[2], item.phone); fire(inp[3], item.email); fire(inp[4], item.area);
          const sel = document.querySelectorAll('select')[0];
          const ss = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set;
          ss.call(sel, item.role); sel.dispatchEvent(new Event('change',{bubbles:true}));
          document.querySelector('button[type=submit], button.crear').click();
          return item.user;
        \"\"\"
      )
    """
    items_json = json.dumps(items, ensure_ascii=False)
    wrapper = (
        f"(async () => {{\n"
        f"  const __items = {items_json};\n"
        f"  const __out = [];\n"
        f"  for (const item of __items) {{\n"
        f"    try {{\n"
        f"      const __r = await (async () => {{ {script} }})();\n"
        f"      __out.push({{ok: true, result: __r}});\n"
        f"    }} catch (__e) {{\n"
        f"      __out.push({{ok: false, error: __e.message}});\n"
        f"    }}\n"
        f"    if ({delay_ms} > 0) await new Promise(r => setTimeout(r, {delay_ms}));\n"
        f"  }}\n"
        f"  return __out;\n"
        f"}})()"
    )
    result = await get_browser().js_eval(wrapper)
    lines = [f"js_result={json.dumps(result['js_result'], ensure_ascii=False)}"]
    if result["exception"]:
        lines.append(f"exception={result['exception']}")
    lines.append(_format_snapshot(result))
    return "\n".join(lines)


@mcp.tool()
async def scroll(ref: str | None = None, x: int = 0, y: int = 400) -> str:
    """Desplaza la pagina o un elemento especifico.

    ref=None → window.scrollBy(x, y)
    ref=@eN  → scrollIntoView del elemento + scrollBy(x, y) relativo
    y>0 baja, y<0 sube; x>0 derecha, x<0 izquierda.

    Ejemplos:
      scroll()                    — baja 400px
      scroll(y=-400)              — sube 400px
      scroll(y=99999)             — va al final de la pagina
      scroll(ref="@e5", y=0)      — centra elemento en viewport
    """
    return _format_snapshot(await get_browser().scroll(ref, x, y))
