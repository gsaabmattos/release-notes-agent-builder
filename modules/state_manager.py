import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class StateManager:
    def __init__(self, cfg):
        self.state_dir = Path(cfg.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, version: str) -> Path:
        safe_name = version.replace("/", "_").replace(" ", "_")
        return self.state_dir / f"{safe_name}.json"

    def load(self, version: str) -> dict:
        p = self._path(version)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {}

    def save(self, version: str, tickets: list[dict]):
        state = {
            t["key"]: t["fields"].get("updated", "")
            for t in tickets
        }
        self._path(version).write_text(
            json.dumps(state, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        log.info(f"Estado salvo: {len(state)} ticket(s) em {self._path(version)}")

    def get_changed_tickets(self, version: str, tickets: list[dict]) -> list[dict]:
        prev = self.load(version)
        changed = []
        for t in tickets:
            key = t["key"]
            updated = t["fields"].get("updated", "")
            if prev.get(key) != updated:
                changed.append(t)
        if changed:
            keys = [t["key"] for t in changed]
            log.info(f"Tickets alterados: {keys}")
        return changed
