import json
from typing import List

import logfire
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.agents.nodes._json import json_schema, parse_and_validate
from app.config import settings


class ComponentSelection(BaseModel):
    name: str = Field(description="Component name from the retrieved catalog")
    role: str = Field(description="Role it plays, e.g. compute/sensor/...")
    compatible: bool = Field(description="Whether it satisfies the project requirements")
    reason: str = Field(description="Brief justification")


class Check(BaseModel):
    type: str = Field(description="Check type, e.g. sensor_compute")
    result: str = Field(description="'pass' or 'fail'")
    reason: str = Field(description="Why the check passed or failed")


class SystemValidation(BaseModel):
    system_valid: bool = Field(description="Whether the whole system is buildable")
    components: List[ComponentSelection] = Field(
        description="All components needed for the project, chosen from the retrieved catalog"
    )
    checks: List[Check]
    missing_requirements: List[str] = Field(
        description="Requirements that no retrieved component satisfies"
    )
    confidence: float = Field(description="Confidence 0..1")


RESPONDER_SCHEMA = json_schema(SystemValidation)

RESPONDER_SYSTEM_PROMPT = (
    "You are an IoT system architect. Use the project requirements and the retrieved "
    "component catalog to decide which components are needed and verify the system is "
    "buildable. Only choose component names that appear in the retrieved catalog. "
    "Respond with a single valid JSON object matching this schema and nothing else. "
    "No markdown code fences, no commentary. The JSON must be exactly:\n"
    f"{RESPONDER_SCHEMA}"
)


class ResponderNode:
    def __init__(self) -> None:
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    @logfire.instrument("graph.node.responder", record_return=False)
    def __call__(self, state: dict) -> dict:
        requirements = state["requirements"]
        documents = state["documents"]
        logfire.info(
            "Responder: validating system",
            requirements_count=len(requirements.get("requirements", [])),
            candidate_count=len(documents),
        )

        catalog_text = "\n".join(
            f"- {doc['name']} ({doc['role']}): {doc['text']}"
            for doc in documents
        )
        payload = {
            "requirements": requirements,
            "retrieved_catalog": catalog_text,
        }
        user_message = f"Input:\n{json.dumps(payload, indent=2)}"

        result = self._invoke_validation(RESPONDER_SYSTEM_PROMPT, user_message)
        logfire.info("Responder: validation produced", confidence=result.get("confidence"))

        return {
            "validation": result,
            "messages": [AIMessage(content=f"System validation: {result}")],
            "plan": state["plan"] + ["3. Components validated and packaged"],
            "status": "Components validated",
        }

    def _invoke_validation(self, system_prompt: str, user_message: str) -> dict:
        retry_prompt = (
            "Your previous response was not valid JSON for the schema. Respond again "
            "with ONLY a single raw JSON object matching the schema."
        )
        for attempt in range(2):
            system = retry_prompt if attempt else system_prompt
            response = self.llm.invoke(
                [
                    SystemMessage(content=system),
                    {"role": "user", "content": user_message},
                ]
            )
            try:
                return parse_and_validate(SystemValidation, response.content).model_dump()
            except Exception as exc:
                logfire.warn(
                    "Responder: JSON parse failed, retrying",
                    attempt=attempt,
                    error=str(exc)[:200],
                )
        raise RuntimeError("Responder could not produce valid validation JSON")


responder_node = ResponderNode()