from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


Architecture = Literal["baseline", "crew"]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    architecture: Architecture = "baseline"
    session_id: Optional[str] = None


class TraceStep(BaseModel):
    name: str
    role: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    latency_ms: float = 0


class AskResponse(BaseModel):
    architecture: Architecture
    answer: str
    data: dict[str, Any] = Field(default_factory=dict)
    trace: list[TraceStep] = Field(default_factory=list)
    latency_ms: float = 0
    cost_usd: float = 0
    tokens: int = 0
    warnings: list[str] = Field(default_factory=list)