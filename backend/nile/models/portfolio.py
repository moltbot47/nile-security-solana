"""Portfolio model — tracks user token holdings and P&L."""

import uuid

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nile.models.base import Base, TimestampMixin, UUIDMixin


class Portfolio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "portfolios"

    wallet_address: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    soul_token_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("soul_tokens.id"), index=True)

    balance: Mapped[float] = mapped_column(Numeric(28, 18), default=0)
    avg_buy_price_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    total_invested_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)
    realized_pnl_sol: Mapped[float] = mapped_column(Numeric(20, 10), default=0)

    __table_args__ = (
        UniqueConstraint(
            "wallet_address",
            "soul_token_id",
            name="uq_portfolio_wallet_token",
        ),
    )

    soul_token: Mapped["SoulToken"] = relationship("SoulToken")  # noqa: F821
