import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, TypeAdapter

T = TypeVar("T", bound=BaseModel)


def json_schema(model: Type[T]) -> str:
    return json.dumps(TypeAdapter(model).json_schema(), indent=2)


def parse_and_validate(model: Type[T], raw: str) -> T:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    return model.model_validate(json.loads(text))