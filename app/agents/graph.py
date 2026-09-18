from langgraph.graph import END, START, StateGraph

from app.agents.nodes.planner import planner_node
from app.agents.nodes.responder import responder_node
from app.agents.nodes.retriever import retriever_node
from app.agents.state import AgentState

builder = StateGraph(AgentState)
builder.add_node("planner", planner_node)
builder.add_node("retriever", retriever_node)
builder.add_node("responder", responder_node)

builder.add_edge(START, "planner")
builder.add_edge("planner", "retriever")
builder.add_edge("retriever", "responder")
builder.add_edge("responder", END)

rag_agent = builder.compile()