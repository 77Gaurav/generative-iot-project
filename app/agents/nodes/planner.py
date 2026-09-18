import logfire
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.agents.nodes._json import json_schema, parse_and_validate
from app.config import settings

VALID_CATEGORIES = [
    "compute", "sensor", "communication", "memory",
    "output", "actuator", "driver", "power", "input",
]


class Requirement(BaseModel):
    category: str = Field(description="One of: " + ", ".join(VALID_CATEGORIES))
    quantity: int = Field(description="Number of such components needed")
    requirement: str = Field(description="Functional need this component must satisfy")


class ModifiedQuery(BaseModel):
    requirements: list[Requirement]


PLANNER_SYSTEM_PROMPT = (
    "You are an IoT project planner. Convert the user's IoT project description into a "
    "structured list of hardware requirements. Categories must be one of: "
    f"{', '.join(VALID_CATEGORIES)}. "
    "Respond with a single valid JSON object matching this schema and nothing else. "
    "No markdown code fences, no commentary. The JSON must be exactly:\n"
    f"{json_schema(ModifiedQuery)}"
)


class PlannerNode:
    def __init__(self) -> None:
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.1,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    @logfire.instrument("graph.node.planner", record_return=False)
    def __call__(self, state: dict) -> dict:
        query = state["current_query"]
        logfire.info("Planner: rewriting query", query=query)

        requirements = self._invoke_requirements(PLANNER_SYSTEM_PROMPT, query)
        logfire.info("Planner: produced requirements", requirements=requirements)

        return {
            "requirements": requirements,
            "messages": [AIMessage(content=f"Requirements: {requirements}")],
            "plan": state["plan"] + ["1. Requirements extracted from query"],
            "status": "Requirements extracted",
        }

    def _invoke_requirements(self, system_prompt: str, query: str) -> dict:
        retry_prompt = (
            "Your previous response was not valid JSON for the schema. Respond again "
            "with ONLY a single raw JSON object matching the schema."
        )
        for attempt in range(2):
            system = retry_prompt if attempt else system_prompt
            response = self.llm.invoke(
                [
                    SystemMessage(content=system),
                    {"role": "user", "content": query},
                ]
            )
            try:
                return parse_and_validate(ModifiedQuery, response.content).model_dump()
            except Exception as exc:
                logfire.warn(
                    "Planner: JSON parse failed, retrying",
                    attempt=attempt,
                    error=str(exc)[:200],
                )
        raise RuntimeError("Planner could not produce valid requirements JSON")


planner_node = PlannerNode()