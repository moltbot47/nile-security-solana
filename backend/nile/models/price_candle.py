"""PriceCandle model — OHLCV data for soul token price charts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base

if TYPE_CHECKING:
    from nile.models.soul_token import SoulToken


class PriceCandle(Base):
    __tablename__ = "price_candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    soul_token_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("soul_tokens.id"), index=True)

    interval: Mapped[str] = mapped_column(String(4), nullable=False, index=True)  # 1m, 5m, 1h, 1d
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    open: Mapped[float] = mapped_column(Numeric(20, 10))
    high: Mapped[float] = mapped_column(Numeric(20, 10))
    low: Mapped[float] = mapped_column(Numeric(20, 10))
    close: Mapped[float] = mapped_column(Numeric(20, 10))
    volume_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    volume_usd: Mapped[float] = mapped_column(Numeric(16, 2), default=0)
    trade_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint(
            "soul_token_id",
            "interval",
            "open_time",
            name="uq_candle_token_interval_time",
        ),
    )

    soul_token: Mapped[SoulToken] = relationship("SoulToken", back_populates="candles")
