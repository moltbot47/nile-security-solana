"""Agent contribution model — tracks what each agent has contributed."""

import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class AgentContribution(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_contributions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id"), nullable=False, index=True
    )

    contribution_type: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )  # detection, patch, exploit, verification

    # Optional links
    contract_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("contracts.id"))
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("scan_jobs.id"))

    # Result
    severity_found: Mapped[str | None] = mapped_column(String(16))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str | None] = mapped_column(Text)

    # Relationships
    agent = relationship("Agent", back_populates="contributions")
    contract = relationship("Contract")
    scan_job = relationship("ScanJob")
