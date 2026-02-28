"""Ecosystem event model — activity log for the entire NILE ecosystem."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from nile.models.base import Base


class EcosystemEvent(Base):
    __tablename__ = "ecosystem_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        index=True,
    )
