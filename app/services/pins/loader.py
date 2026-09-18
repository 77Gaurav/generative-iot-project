import json
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings


class PinLayoutLoader:
    """Loads per-type pin layout files from DATA/pins and indexes them by id/name."""

    def __init__(self, pins_dir: Optional[Path] = None) -> None:
        self._pins_dir = pins_dir or Path(settings.PINS_PATH)
        self._by_id: Dict[str, dict] = {}
        self._by_name: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        for file in sorted(self._pins_dir.glob("*.json")):
            data = json.loads(file.read_text())
            for component in data.get("components", []):
                cid = component.get("component_id")
                self._by_id[cid] = component
                name = component.get("component_name")
                if name:
                    self._by_name.setdefault(name, component)

    def get(self, component_id: str) -> Optional[dict]:
        return self._by_id.get(component_id)

    def get_by_name(self, name: str) -> Optional[dict]:
        return self._by_name.get(name)

    def get_for_names(self, names: List[str]) -> List[dict]:
        found: Dict[str, dict] = {}
        for name in names:
            layout = self.get_by_name(name)
            if layout:
                found[layout["component_id"]] = layout
        return list(found.values())


pin_layout_loader = PinLayoutLoader()