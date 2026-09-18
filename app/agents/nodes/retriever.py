import logfire

from app.services.retrieval.qdrant_service import qdrant_service

REQUIREMENTS_TOP_K = 4


def _requirement_search_text(category: str, requirement: str) -> str:
    return " ".join(
        part.strip()
        for part in (category, requirement)
        if part and part.strip()
    ) or "IoT components"


class RetrieverNode:
    @logfire.instrument("graph.node.retriever", record_return=False)
    def __call__(self, state: dict) -> dict:
        requirements = state["requirements"]
        logfire.info(
            "Retriever: searching per requirement",
            requirement_count=len(requirements.get("requirements", [])),
        )

        merged: dict[str, dict] = {}
        for req in requirements.get("requirements", []):
            category = req.get("category", "")
            search_text = _requirement_search_text(category, req.get("requirement", ""))
            hits = qdrant_service.search(search_text, top_k=REQUIREMENTS_TOP_K)

            for hit in hits:
                payload = hit["payload"]
                component_id = payload.get("component_id")
                score = round(hit.get("score", 0.0), 4)
                existing = merged.get(component_id)
                if existing is None or score > existing["score"]:
                    merged[component_id] = {
                        "component_id": component_id,
                        "name": payload.get("component_name"),
                        "role": payload.get("type"),
                        "text": payload.get("text"),
                        "score": score,
                    }

        documents = sorted(merged.values(), key=lambda d: d["score"], reverse=True)
        logfire.info(
            "Retriever: found candidate components",
            candidates=len(documents),
        )
        return {
            "documents": documents,
            "plan": state["plan"] + ["2. Vector search on modified query"],
            "status": "Candidate components retrieved",
        }


retriever_node = RetrieverNode()