from typing import Annotated, Any, Dict, List, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    current_query: str
    requirements: dict
    documents: List[dict]
    validation: dict
    plan: List[str]
    status: str