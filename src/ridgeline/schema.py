"""Data contracts for the quote pipeline.

Two stages, two models:
- ExtractedRFQ: what the LLM reads out of a document. No part numbers resolved,
  and no price field exists anywhere, so the model cannot produce one.
- OutputRFQ: the final JSON deliverable written to outputs/.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

MatchMethod = Literal["ridgeline_part_number", "cross_reference", "description", "llm"]


class ExtractedLine(BaseModel):
    """One requested item, in order of appearance."""
    model_config = ConfigDict(extra="forbid")

    as_written: str = Field(description="Verbatim text of the line from the RFQ.")
    quantity: Optional[float] = Field(None, description="Numeric quantity, null if absent or unclear.")
    unit: Optional[str] = Field(None, description="Unit as written (ea, box, case...), null if absent.")
    ridgeline_part_number: Optional[str] = Field(
        None, description="A Ridgeline part number (RL + digits) written on the line, if any.")
    competitor_part_number: Optional[str] = Field(None, description="Competitor part number, if any.")
    description: Optional[str] = Field(None, description="Product description text used for matching.")
    flags: list[str] = Field(default_factory=list, description="Ambiguity flags, e.g. 'vague_quantity'.")


class ExtractedRFQ(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: Optional[str] = Field(None, description="Customer company name, used to look up customer_id.")
    lines: list[ExtractedLine]


class OutputLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line: int = Field(ge=1)
    as_written: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    ridgeline_part_number: Optional[str] = None
    match_method: Optional[MatchMethod] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    needs_review: bool
    flags: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class OutputRFQ(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rfq_id: str
    customer_id: Optional[str] = None
    lines: list[OutputLine]
