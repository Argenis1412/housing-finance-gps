"""Additive local persistence contracts; the existing result stays unchanged."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from api.schemas.comparison_v1 import ComparisonInputsV1, ComparisonSimulationResultV1


type OperationId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")]


class SavedComparisonCreationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation_id: OperationId
    comparison: ComparisonInputsV1


class SavedComparisonV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    api_version: Literal["v1"]
    kind: Literal["saved_comparison"]
    simulation_id: OperationId
    saved_at: str
    result: ComparisonSimulationResultV1


class SavedComparisonSummaryV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    simulation_id: OperationId
    saved_at: str


class SavedComparisonListV1(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    api_version: Literal["v1"]
    kind: Literal["saved_comparison_list"]
    items: list[SavedComparisonSummaryV1]
    next_offset: int | None
