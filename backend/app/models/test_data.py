from typing import Literal
from pydantic import Field, model_validator
from .test_cases import StrictModel
from ..agent import Nonblank

class DataDraft(StrictModel):
    test_case_id: Nonblank
    kind: Literal['valid', 'invalid', 'edge']
    values: dict[str, str | int | bool | float | list[str]] = Field(min_length=1)
    expected_behavior: Nonblank
    needs_review: bool = True

    @model_validator(mode='after')
    def synthetic_only(self):
        # Only bounded synthetic fixture fields are accepted; never executable payloads.
        allowed = {'customer_id', 'coupon', 'cart_total', 'discount_percent',
                   'expected_discount', 'expected_payable', 'now_utc', 'expires_at_utc',
                   'redemption_history', 'quantity', 'stock', 'scenario'}
        if set(self.values) - allowed:
            raise ValueError('Unsupported synthetic fixture field')
        return self

class TestData(DataDraft):
    id: Nonblank
    synthetic: bool = True

class DataOutput(StrictModel):
    datasets: list[DataDraft] = Field(min_length=1, max_length=200)


class DataEdit(StrictModel):
    values: dict[str, str | int | bool | float | list[str]] = Field(min_length=1)
    expected_behavior: Nonblank
    needs_review: bool
