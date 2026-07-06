# Browser-MCP (Browser-MCP Navigator)

Ultra-fast browser automation server over Chrome DevTools Protocol (CDP), exposed as a Model Context Protocol (MCP) server.

No screenshots. No Playwright relay. Direct CDP WebSocket — 20–50× fewer tokens, ~10ms per action.

> **Note**: The core Python package is named `browser_mcp` internally.

## What it does

Controls a real Chrome browser from any AI agent that supports MCP. The agent receives a compact accessibility-tree snapshot with `@eN` references after every action — no pixels, no heavy HTML blobs.

```
Agent  ──MCP──►  Browser-MCP Server  ──CDP──►  Chrome
```

---

## Quick Start — Docker (Recommended)

```bash
git clone https://github.com/ingjohnfigueroablanco/browser-MCP.git
cd browser-MCP
cp .env.example .env          # optionally set MCP_API_KEY
docker compose up -d
```

Server ready at `http://localhost:3067/sse`.

## Quick Start — Local (No Docker)

```bash
git clone https://github.com/ingjohnfigueroablanco/browser-MCP.git
cd browser-MCP
python -m venv .venv 
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
python -m browser_mcp  # stdio mode
```

---

## Connecting from Claude Code

### Option A — Local subprocess / stdio

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "browser-mcp": {
      "command": "python",
      "args": ["-m", "browser_mcp"]
    }
  }
}
```

### Option B — Docker / SSE

```json
{
  "mcpServers": {
    "browser-mcp": {
      "type": "sse",
      "url": "http://localhost:3067/sse",
      "headers": { "X-API-Key": "your-key" }
    }
  }
}
```

---

## Connecting from other agents / frameworks

### Python agent (mcp SDK)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("http://localhost:3067/sse",
                      headers={"X-API-Key": "your-key"}) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("navigate", {"url": "https://example.com"})
        print(result.content[0].text)
```

---

## Testing Localhost Apps (Docker)

The browser runs **inside the container**. `localhost` inside Docker ≠ your dev machine.

| Approach | How |
|---|---|
| **Docker Desktop** | Use `http://host.docker.internal:3000` instead of `localhost:3000` |
| **ngrok** | `ngrok http 3000` → gives a public URL the container can reach |
| **Local mode** | (stdio) Chrome runs on your machine — `localhost` works normally |

---

## Available Tools

| Tool | Description |
|---|---|
| `browser_start` | Launch / reconnect Chrome |
| `browser_stop` | Close Chrome |
| `navigate` | Go to URL, wait for load / networkidle |
| `snapshot` | Accessibility tree as compact text with `@eN` refs |
| `click` | Human-like click by coordinates |
| `js_click` | `element.click()` — reliable for React / Angular SPAs |
| `fill` | Clear + type text in an input |
| `press_key` | Key press (Enter, Tab, Escape, ArrowDown…) |
| `select_option` | Select native `<select>` by value or label |
| `hover` | Mouse hover (menus, tooltips) |
| `set_value` | React/Vue/Angular-safe input setter via native JS |
| `scroll` | Scroll page or element into view |
| `js_eval` | **Run any JavaScript** — drag, events, async fetch, bulk loops |
| `js_eval_loop` | **Bulk operations** — run a JS snippet once per item |
| `cdp_call` | **Raw CDP protocol** — file upload, device emulation, network intercept |
| `get_text` | innerText of element or full page |
| `wait_for` | Wait until text appears on page |
| `read_console` | JS console logs |
| `read_network` | Network requests / responses |
| `screenshot` | PNG base64 (escape hatch) |
| `current_url` | Current URL + title |

---

## Performance & Bulk Operations

### The bottleneck is LLM round-trips, not the browser

Each tool call costs one full LLM inference + HTTP round-trip. The browser executes CDP in ~10ms.

| Pattern | Tool calls | Typical wall time |
|---|---|---|
| 20 × (click + fill + click) | 60 | ~10 min |
| 1 × js_eval_loop with 20 items | 1 | ~15 sec |

### Rule: for N > 5 repetitions, use js_eval_loop

```python
# GOOD — 1 tool call for 20 users
js_eval_loop(
    items=users,
    script="""
      document.querySelector('.agregar').click();
      await new Promise(r => setTimeout(r, 400));
      // ... fill logic ...
      document.querySelector('.crear').click();
      return item.user;
    """,
    delay_ms=300,
)
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` (local) or `sse` (Docker/remote) |
| `MCP_HOST` | `0.0.0.0` | SSE bind address |
| `MCP_PORT` | `3067` | SSE port |
| `MCP_API_KEY` | *(empty)* | API key header; empty = no auth |
| `CHROME_PATH` | auto | Explicit path to chrome.exe |
| `CHROME_EXTRA_ARGS` | *(empty)* | Extra Chrome flags |
| `Browser-MCP_HEADLESS` | `0` | `1` for headless mode |
| `Browser-MCP_HUMAN_DELAYS`| `1` | `0` removes human-like delays (faster) |

---

## Architecture

```
mcp/         FastMCP server + tool definitions
browser/     BrowserManager — lifecycle, navigate, snapshot, waits
snapshot/    AX tree → compact text with @eN refs (no screenshots)
actions/     mouse, keyboard, forms (ref → coordinates)
cdp/         Raw CDP WebSocket connection + event buffers
chrome/      Chrome launcher, port scan, reattach
```

**Why it's faster than Playwright:**
- No Node.js relay — Python speaks CDP directly.
- Chrome stays alive between calls (daemon) — 0 ms startup per tool call.
- Snapshot = compact AX text, not full YAML or heavy screenshots.
- `@eN` refs = stable `backendNodeId` — no DOM re-query per action.
