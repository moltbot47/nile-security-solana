"""Pydantic schemas for contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ContractCreate(BaseModel):
    address: str | None = None
    name: str
    source_url: str | None = None
    chain: str = "solana"
    compiler_version: str | None = None
    is_verified: bool = False
    metadata: dict = {}


class ContractResponse(BaseModel):
    id: uuid.UUID
    address: str | None
    name: str
    source_url: str | None
    chain: str
    compiler_version: str | None
    is_verified: bool
    metadata: dict = Field(default={}, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContractWithScore(ContractResponse):
    latest_nile_score: "NileScoreResponse | None" = None


class VulnerabilityResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    scan_job_id: uuid.UUID | None = None
    title: str
    severity: str
    category: str
    description: str | None = None
    impact: str | None = None
    remediation: str | None = None
    confidence: float | None = None
    status: str
    detected_at: datetime

    model_config = {"from_attributes": True}


class NileScoreResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    total_score: float
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    score_details: dict
    trigger_type: str
    computed_at: datetime

    model_config = {"from_attributes": True}

    @property
    def grade(self) -> str:
        if self.total_score >= 90:
            return "A+"
        if self.total_score >= 80:
            return "A"
        if self.total_score >= 70:
            return "B"
        if self.total_score >= 60:
            return "C"
        if self.total_score >= 50:
            return "D"
        return "F"
