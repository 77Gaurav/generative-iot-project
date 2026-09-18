import json
from typing import List

import logfire
from langchain_core.messages import AIMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.agents.nodes._json import json_schema, parse_and_validate
from app.config import settings
from app.services.pins.loader import pin_layout_loader


class WiringPlan(BaseModel):
    summary: str = Field(description="Short overview of the wiring approach (2-3 sentences)")
    steps: List[str] = Field(
        description="Numbered natural-language instructions, step by step and pin by pin, "
        "in a safe order: power/ground first, then buses, then signals. Each step is one "
        "sentence naming the exact pins to connect (e.g. 'ESP32 3V3 to BME280 VIN')"
    )
    warnings: List[str] = Field(
        description="Anything that may go wrong: voltage mismatches, missing pull-ups, "
        "level shifting, current limits, common-ground requirements"
    )
    confidence: float = Field(description="Confidence 0..1 that the wiring is correct and safe")


WIRING_PROMPT = (
    "You are an electronics wiring expert. Given the project description and the pin layouts "
    "of the chosen components, produce a step-by-step, pin-by-pin wiring plan to build the "
    "circuit. Emit connections in a safe practical order: power/ground rails first, then "
    "communication buses, then remaining signals. "
    "Check every connection for problems, for example: 3.3V vs 5V logic mismatches, "
    "missing pull-up resistors on I2C/open-drain lines, HC-SR04 5V ECHO hitting a 3.3V MCU, "
    "motors/relays needing a driver, common ground between supplies, and current limits. "
    "Use only pin labels that exist in the provided pin layouts. "
    "Keep each step to one concise sentence (under 40 words) and use no more than 25 steps. "
    "Respond with a single valid JSON object matching this schema and nothing else. "
    "It must be compact JSON with no markdown code fences and no commentary. The schema:\n"
    f"{json_schema(WiringPlan)}"
)


def _pin_layout_text(layout: dict) -> str:
    name = layout.get("component_name")
    logic = layout.get("logic_level")
    power = layout.get("power", {})
    vcc_pins = ",".join(power.get("vcc_pins", []) or ["-"])
    gnd_pins = ",".join(power.get("gnd_pins", []) or ["-"])
    lines = [
        f"{name}: {logic}V logic, {layout.get('pin_count')} pins | "
        f"VCC={vcc_pins}({power.get('voltage_min')}-{power.get('voltage_max')}V) GND={gnd_pins}"
    ]
    interfaces = layout.get("interfaces", {})
    if interfaces:
        blocks = []
        for iface, pins in interfaces.items():
            blocks.append(f"{iface}:" + ",".join(f"{p.get('pin')}={p.get('function')}" for p in pins))
        lines.append("  " + "; ".join(blocks))
    for pin in layout.get("pins", []):
        lines.append(
            f"  {pin.get('pin')} = {pin.get('function')} "
            f"({pin.get('direction', '')[0:3]}; {pin.get('voltage_min')}-{pin.get('voltage_max')}V)"
        )
    notes = layout.get("notes")
    if notes:
        lines.append(f"  note: {notes}")
    return "\n".join(lines)


class WiringNode:
    def __init__(self) -> None:
        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.0,
            max_tokens=16384,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    @logfire.instrument("graph.node.wiring", record_return=False)
    def __call__(self, state: dict) -> dict:
        validation = state["validation"]
        names = [c.get("name", "") for c in validation.get("components", [])]
        layouts = pin_layout_loader.get_for_names(names)
        logfire.info(
            "Wiring: preparing pin layouts",
            selected_components=len(names),
            layouts_available=len(layouts),
        )

        payload = {
            "user_initial_query": state["current_query"],
            "user_modified_query": state["requirements"],
            "pin_layout_of_each_component": [_pin_layout_text(l) for l in layouts],
        }

        result = self._invoke(WIRING_PROMPT, json.dumps(payload, indent=2))
        logfire.info("Wiring: plan produced", confidence=result.get("confidence"))

        return {
            "wiring": result,
            "pin_layouts": layouts,
            "messages": [AIMessage(content=f"Wiring plan ready (confidence {result.get('confidence')})")],
            "plan": state["plan"]
            + [f"4. Generated wiring plan for {len(layouts)} components"],
            "status": "Wiring plan generated",
        }

    def _invoke(self, system_prompt: str, user_message: str) -> dict:
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
                return parse_and_validate(WiringPlan, response.content).model_dump()
            except Exception as exc:
                logfire.warn(
                    "Wiring: JSON parse failed, retrying",
                    attempt=attempt,
                    error=str(exc)[:200],
                )
        raise RuntimeError("Wiring node could not produce a valid wiring plan")


wiring_node = WiringNode()