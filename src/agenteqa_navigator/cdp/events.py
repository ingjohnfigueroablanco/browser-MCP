"""Ring buffers capturing console messages and network activity via CDP events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .connection import CDPConnection

_MAX_CONSOLE = 500
_MAX_NETWORK = 1000


@dataclass
class NetEntry:
    method: str
    url: str
    status: int | None = None
    resource_type: str | None = None
    failed: bool = False


class EventBuffers:
    """Subscribes to console + network events and keeps recent entries."""

    def __init__(self, conn: CDPConnection) -> None:
        self._conn = conn
        self.console: deque[str] = deque(maxlen=_MAX_CONSOLE)
        self.network: deque[NetEntry] = deque(maxlen=_MAX_NETWORK)
        self._by_request: dict[str, NetEntry] = {}

    def attach(self) -> None:
        self._conn.on("Runtime.consoleAPICalled", self._on_console)
        self._conn.on("Log.entryAdded", self._on_log)
        self._conn.on("Network.requestWillBeSent", self._on_request)
        self._conn.on("Network.responseReceived", self._on_response)
        self._conn.on("Network.loadingFailed", self._on_failed)

    # --- console ---
    def _on_console(self, params: dict, _sid: str | None) -> None:
        level = params.get("type", "log")
        args = params.get("args", [])
        text = " ".join(str(a.get("value", a.get("description", ""))) for a in args)
        self.console.append(f"[{level}] {text}")

    def _on_log(self, params: dict, _sid: str | None) -> None:
        entry = params.get("entry", {})
        self.console.append(f"[{entry.get('level', 'log')}] {entry.get('text', '')}")

    # --- network ---
    def _on_request(self, params: dict, _sid: str | None) -> None:
        req = params.get("request", {})
        entry = NetEntry(
            method=req.get("method", ""),
            url=req.get("url", ""),
            resource_type=params.get("type"),
        )
        rid = params.get("requestId")
        if rid:
            self._by_request[rid] = entry
        self.network.append(entry)

    def _on_response(self, params: dict, _sid: str | None) -> None:
        rid = params.get("requestId")
        entry = self._by_request.get(rid) if rid else None
        if entry is not None:
            entry.status = (params.get("response") or {}).get("status")

    def _on_failed(self, params: dict, _sid: str | None) -> None:
        rid = params.get("requestId")
        entry = self._by_request.get(rid) if rid else None
        if entry is not None:
            entry.failed = True

    # --- read / clear ---
    def read_console(self, clear: bool = False) -> list[str]:
        items = list(self.console)
        if clear:
            self.console.clear()
        return items

    def read_network(self, filter_substr: str | None = None, clear: bool = False) -> list[NetEntry]:
        items = [e for e in self.network if not filter_substr or filter_substr in e.url]
        if clear:
            self.network.clear()
            self._by_request.clear()
        return items
