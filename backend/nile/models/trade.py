"""Trade model — records every buy/sell of a soul token."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from nile.models.soul_token import SoulToken


class Trade(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trades"

    soul_token_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("soul_tokens.id"), index=True)

    # Trade details
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # buy or sell
    token_amount: Mapped[float] = mapped_column(Numeric(28, 18), nullable=False)
    sol_amount: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    price_sol: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    price_usd: Mapped[float] = mapped_column(Numeric(16, 4), nullable=False)

    # Fee breakdown
    fee_total_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_creator_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_protocol_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    fee_staker_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)

    # Blockchain reference
    tx_sig: Mapped[str | None] = mapped_column(String(96), unique=True, index=True)
    slot: Mapped[int | None] = mapped_column(Integer)
    trader_address: Mapped[str] = mapped_column(String(48), index=True)

    # Phase when trade occurred
    phase: Mapped[str] = mapped_column(String(16), default="bonding")

    # Source: "chain" (indexed from on-chain) or "backend" (off-chain matching)
    source: Mapped[str] = mapped_column(String(16), default="chain")

    # Relationships
    soul_token: Mapped[SoulToken] = relationship("SoulToken", back_populates="trades")
