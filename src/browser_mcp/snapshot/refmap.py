"""Element reference map: stable @eN refs -> CDP node identity, versioned per snapshot."""

from __future__ import annotations

from dataclasses import dataclass


class StaleRefError(Exception):
    """Raised when a ref belongs to a previous snapshot generation."""


@dataclass(frozen=True)
class RefEntry:
    ref: str
    backend_node_id: int
    session_id: str | None
    role: str
    name: str


class RefMap:
    """Holds the @eN -> RefEntry mapping for the CURRENT snapshot generation.

    Each ``begin`` bumps ``snapshot_id`` and clears entries, so refs from an
    older snapshot fail fast with StaleRefError instead of clicking the wrong node.
    """

    def __init__(self) -> None:
        self.snapshot_id = 0
        self._entries: dict[str, RefEntry] = {}
        self._counter = 0
        self.current_session: str | None = None

    def begin(self) -> int:
        self.snapshot_id += 1
        self._entries.clear()
        self._counter = 0
        return self.snapshot_id

    def assign(
        self, backend_node_id: int, role: str, name: str, session_id: str | None = None
    ) -> str:
        self._counter += 1
        ref = f"@e{self._counter}"
        self._entries[ref] = RefEntry(
            ref=ref,
            backend_node_id=backend_node_id,
            session_id=session_id if session_id is not None else self.current_session,
            role=role,
            name=name,
        )
        return ref

    def resolve(self, ref: str) -> RefEntry:
        entry = self._entries.get(ref)
        if entry is None:
            raise StaleRefError(
                f"{ref} no existe en el snapshot actual (gen {self.snapshot_id}). "
                "Vuelve a llamar snapshot."
            )
        return entry

    def __len__(self) -> int:
        return len(self._entries)
