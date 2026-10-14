from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from ..agent import Nonblank

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)

class Criterion(StrictModel):
    id: Nonblank
    text: Nonblank

class TestStep(StrictModel):
    action: Nonblank

class ExpectedResult(StrictModel):
    description: Nonblank
    needs_review: bool = True

class CaseDraft(StrictModel):
    title: Nonblank
    category: Literal['positive', 'negative', 'boundary']
    priority: Literal['high', 'medium', 'low']
    scenario_id: Nonblank
    criterion_ids: list[Nonblank] = Field(min_length=1)
    preconditions: list[Nonblank] = Field(min_length=1)
    steps: list[TestStep] = Field(min_length=1)
    expected_result: ExpectedResult

class TestCase(CaseDraft):
    id: Nonblank
    requirement_id: Nonblank
    review_status: Literal['pending', 'reviewed'] = 'pending'

class DesignOutput(StrictModel):
    cases: list[CaseDraft] = Field(min_length=1, max_length=100)

class CaseEdit(StrictModel):
    title: Nonblank
    expected_result: ExpectedResult
    review_status: Literal['pending', 'reviewed']
