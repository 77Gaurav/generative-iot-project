import json
from pathlib import Path
from typing import List

import logfire
from langchain_core.documents import Document

from app.config import settings


class ComponentDocumentBuilder:
    """Builds exactly one Document per component JSON object (no text splitting)."""

    def build(self, components: list[dict]) -> list[Document]:
        documents = []

        for component in components:
            documents.append(
                Document(
                    page_content=(
                        f"Component: {component['component_name']}\n"
                        f"Type: {component['type']}\n"
                        f"Description: {component['description']}"
                    ),
                    metadata={
                        "component_id": component["component_id"],
                        "component_name": component["component_name"],
                        "type": component["type"],
                    },
                )
            )

        return documents


class ObjectsLoader:
    """Loads IoT component records from DATA/components.json into LangChain Documents."""

    def __init__(self, path: str = settings.COMPONENTS_PATH) -> None:
        self.path = Path(path)

    @logfire.instrument("objects.loader.load_from_json")
    def load(self) -> List[Document]:
        if not self.path.exists():
            raise FileNotFoundError(f"Components file not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as f:
            raw_components = json.load(f)

        documents = ComponentDocumentBuilder().build(raw_components)

        logfire.info(
            "Loaded IoT components",
            component_count=len(documents),
            source=str(self.path),
        )
        return documents


objects_loader = ObjectsLoader()