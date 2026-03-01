"""migrate_evm_to_solana

Revision ID: c3a1f8b20d5e
Revises: be8251cf9f1a
Create Date: 2026-02-28 12:00:00.000000

Migrate all EVM-specific columns to Solana equivalents:
- String(42) → String(48) for Solana base58 addresses
- String(66) → String(96) for Solana tx signatures
- Rename *_eth → *_sol columns
- Rename evmbench_* → benchmark_*
- Update default chain values
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a1f8b20d5e"
down_revision: str = "be8251cf9f1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- contracts table ---
    op.alter_column("contracts", "address", type_=sa.String(48))
    op.alter_column("contracts", "chain", server_default="solana")

    # --- soul_tokens table ---
    op.alter_column("soul_tokens", "token_address", type_=sa.String(48))
    op.alter_column("soul_tokens", "curve_address", type_=sa.String(48))
    op.alter_column("soul_tokens", "pool_address", type_=sa.String(48))
    op.alter_column("soul_tokens", "creator_address", type_=sa.String(48))
    op.alter_column("soul_tokens", "chain", server_default="solana")
    op.alter_column("soul_tokens", "current_price_eth", new_column_name="current_price_sol")
    op.alter_column("soul_tokens", "reserve_balance_eth", new_column_name="reserve_balance_sol")
    op.alter_column(
        "soul_tokens", "graduation_threshold_eth", new_column_name="graduation_threshold_sol"
    )

    # --- trades table ---
    op.alter_column("trades", "trader_address", type_=sa.String(48))
    op.alter_column("trades", "tx_hash", type_=sa.String(96), new_column_name="tx_sig")
    op.alter_column("trades", "block_number", new_column_name="slot")
    op.alter_column("trades", "eth_amount", new_column_name="sol_amount")
    op.alter_column("trades", "price_eth", new_column_name="price_sol")
    op.alter_column("trades", "fee_total_eth", new_column_name="fee_total_sol")
    op.alter_column("trades", "fee_creator_eth", new_column_name="fee_creator_sol")
    op.alter_column("trades", "fee_protocol_eth", new_column_name="fee_protocol_sol")
    op.alter_column("trades", "fee_staker_eth", new_column_name="fee_staker_sol")

    # --- oracle_events table ---
    op.alter_column("oracle_events", "on_chain_event_id", type_=sa.String(96))
    op.alter_column("oracle_events", "tx_hash", type_=sa.String(96), new_column_name="tx_sig")

    # --- portfolios table ---
    op.alter_column("portfolios", "wallet_address", type_=sa.String(48))
    op.alter_column("portfolios", "avg_buy_price_eth", new_column_name="avg_buy_price_sol")
    op.alter_column("portfolios", "total_invested_eth", new_column_name="total_invested_sol")
    op.alter_column("portfolios", "realized_pnl_eth", new_column_name="realized_pnl_sol")

    # --- price_candles table ---
    op.alter_column("price_candles", "volume_eth", new_column_name="volume_sol")

    # --- vulnerabilities table ---
    op.alter_column("vulnerabilities", "evmbench_vuln_id", new_column_name="benchmark_vuln_id")
    op.alter_column("vulnerabilities", "evmbench_audit_id", new_column_name="benchmark_audit_id")


def downgrade() -> None:
    # --- vulnerabilities table ---
    op.alter_column("vulnerabilities", "benchmark_audit_id", new_column_name="evmbench_audit_id")
    op.alter_column("vulnerabilities", "benchmark_vuln_id", new_column_name="evmbench_vuln_id")

    # --- price_candles table ---
    op.alter_column("price_candles", "volume_sol", new_column_name="volume_eth")

    # --- portfolios table ---
    op.alter_column("portfolios", "realized_pnl_sol", new_column_name="realized_pnl_eth")
    op.alter_column("portfolios", "total_invested_sol", new_column_name="total_invested_eth")
    op.alter_column("portfolios", "avg_buy_price_sol", new_column_name="avg_buy_price_eth")
    op.alter_column("portfolios", "wallet_address", type_=sa.String(42))

    # --- oracle_events table ---
    op.alter_column("oracle_events", "tx_sig", type_=sa.String(66), new_column_name="tx_hash")
    op.alter_column("oracle_events", "on_chain_event_id", type_=sa.String(66))

    # --- trades table ---
    op.alter_column("trades", "fee_staker_sol", new_column_name="fee_staker_eth")
    op.alter_column("trades", "fee_protocol_sol", new_column_name="fee_protocol_eth")
    op.alter_column("trades", "fee_creator_sol", new_column_name="fee_creator_eth")
    op.alter_column("trades", "fee_total_sol", new_column_name="fee_total_eth")
    op.alter_column("trades", "price_sol", new_column_name="price_eth")
    op.alter_column("trades", "sol_amount", new_column_name="eth_amount")
    op.alter_column("trades", "slot", new_column_name="block_number")
    op.alter_column("trades", "tx_sig", type_=sa.String(66), new_column_name="tx_hash")
    op.alter_column("trades", "trader_address", type_=sa.String(42))

    # --- soul_tokens table ---
    op.alter_column(
        "soul_tokens", "graduation_threshold_sol", new_column_name="graduation_threshold_eth"
    )
    op.alter_column("soul_tokens", "reserve_balance_sol", new_column_name="reserve_balance_eth")
    op.alter_column("soul_tokens", "current_price_sol", new_column_name="current_price_eth")
    op.alter_column("soul_tokens", "chain", server_default="base")
    op.alter_column("soul_tokens", "creator_address", type_=sa.String(42))
    op.alter_column("soul_tokens", "pool_address", type_=sa.String(42))
    op.alter_column("soul_tokens", "curve_address", type_=sa.String(42))
    op.alter_column("soul_tokens", "token_address", type_=sa.String(42))

    # --- contracts table ---
    op.alter_column("contracts", "chain", server_default="ethereum")
    op.alter_column("contracts", "address", type_=sa.String(42))
